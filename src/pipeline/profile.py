"""ProjectProfile — a project's classification identity, loaded from its DB profile.

The per-project profile lives in the analysis schema ({analysis}.prompts,
{analysis}.topics, {analysis}.sentiment — created by schema/roadless.sql and
seeded by make schema). Exactly one prompt per kind is active; the pipeline
refuses to run without one. user_prompt_template runtime placeholders:
{comment_text} always; {topics_list} required for sentiment_topic prompts.
Rendering uses str.replace, never str.format — prompt text legitimately
contains literal JSON braces.
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List

from shared import db
from shared.project_context import ProjectContext


# The classification response contract — ONE definition shared by every path that
# asks a model to classify: the Together batch generator bakes it into each
# request body, and the local runner sends it too. Sentiment is an enum of the
# nine STANCE|STRENGTH combinations; topic_name stays a free string (the SQL load
# maps names and flags unknowns). Enforcing it as response_format guarantees
# parseable JSON — without it, a supporting phrase that begins with a literal
# quote breaks the whole line (the failure mode that lost ~5% of a real batch).
SENTIMENT_TOPIC_SCHEMA = {
    "type": "object",
    "properties": {
        "sentiment": {
            "type": "string",
            "enum": [f"{s}|{g}" for s in ("SUPPORT", "OPPOSE", "NEUTRAL")
                     for g in ("HIGH", "MEDIUM", "LOW")],
        },
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic_name": {"type": "string"},
                    "confidence": {"type": "number"},
                    "supporting_phrases": {"type": "array",
                                           "items": {"type": "string"}},
                },
                "required": ["topic_name", "confidence", "supporting_phrases"],
            },
        },
    },
    "required": ["sentiment", "topics"],
}


def sentiment_topic_response_format(strict: bool = True) -> dict:
    """OpenAI-compatible response_format enforcing SENTIMENT_TOPIC_SCHEMA."""
    return {
        "type": "json_schema",
        "json_schema": {"name": "comment_classification", "strict": strict,
                        "schema": SENTIMENT_TOPIC_SCHEMA},
    }


@dataclass(frozen=True)
class ProjectProfile:
    prompt_id: int
    prompt_kind: str
    prompt_name: str
    system_prompt: str
    user_prompt_template: str
    model_name: str
    model_parameters: Dict[str, Any]
    version: int
    # Active topics: topic_id, topic_name, description. By name, with the no-topic
    # answer (category 'no_topic': sentiment_only) last — where the prompt lists it.
    topics: List[Dict[str, Any]]
    sentiment_map: Dict[str, int]       # e.g. {"SUPPORT": 1, "OPPOSE": 2, "NEUTRAL": 3}
    analysis_schema: str                # target schema, carried into the snapshot

    @classmethod
    def load(cls, ctx: ProjectContext, prompt_kind: str = "sentiment_topic") -> "ProjectProfile":
        """Load the active prompt, active topics, and sentiment map for one project.

        Raises RuntimeError with a project-specific message when the profile is
        incomplete — a project without an active prompt of the requested kind is
        not ready for classification.
        """
        with db.connect(**ctx.db_config) as conn:
            with conn.cursor() as cur:
                cur.execute(ctx.render_sql(
                    """
                    SELECT prompt_id, prompt_kind, prompt_name, system_prompt,
                           user_prompt_template, model_name, model_parameters, version
                    FROM {analysis}.prompts
                    WHERE prompt_kind = ? AND is_active
                    """), (prompt_kind,))
                rows = cur.fetchall()
                if not rows:
                    raise RuntimeError(
                        f"Project {ctx.slug!r} has no active {prompt_kind!r} prompt in"
                        " prompts — run make schema, which seeds the profile."
                    )
                # The partial unique index guarantees at most one; assert anyway.
                assert len(rows) == 1
                prompt = rows[0]

                cur.execute(ctx.render_sql(
                    """
                    SELECT topic_id, topic_name, description
                    FROM {analysis}.topics
                    WHERE is_active
                    ORDER BY (category IS 'no_topic'), topic_name
                    """))
                topics = cur.fetchall()

                cur.execute(ctx.render_sql(
                    "SELECT sentiment_id, sentiment FROM {analysis}.sentiment"))
                sentiment_map = {r["sentiment"]: r["sentiment_id"] for r in cur.fetchall()}

        template = prompt["user_prompt_template"]
        if "{comment_text}" not in template:
            raise RuntimeError(
                f"Active {prompt_kind!r} prompt (id {prompt['prompt_id']}) for project"
                f" {ctx.slug!r} has no {{comment_text}} placeholder."
            )
        if prompt_kind == "sentiment_topic":
            if "{topics_list}" not in template:
                raise RuntimeError(
                    f"Active sentiment_topic prompt (id {prompt['prompt_id']}) for project"
                    f" {ctx.slug!r} has no {{topics_list}} placeholder."
                )
            if not topics:
                raise RuntimeError(
                    f"Project {ctx.slug!r} has no active topics in"
                    " topics — load a taxonomy first."
                )
        for required in ("SUPPORT", "OPPOSE", "NEUTRAL"):
            if required not in sentiment_map:
                raise RuntimeError(
                    f"Project {ctx.slug!r} sentiment table is missing {required!r}"
                    " — the 1/2/3 convention is fixed and seeded at provisioning."
                )

        return cls(
            prompt_id=prompt["prompt_id"],
            prompt_kind=prompt["prompt_kind"],
            prompt_name=prompt["prompt_name"],
            system_prompt=prompt["system_prompt"],
            user_prompt_template=template,
            model_name=prompt["model_name"],
            model_parameters=json.loads(prompt["model_parameters"] or "{}"),
            version=prompt["version"],
            topics=[dict(t) for t in topics],
            sentiment_map=sentiment_map,
            analysis_schema=ctx.analysis_schema,
        )

    @property
    def topics_list_text(self) -> str:
        """The exact-name topic list block substituted for {topics_list}."""
        return "\n- " + "\n- ".join(t["topic_name"] for t in self.topics)

    def render_user_prompt(self, comment_text: str, include_snippets: bool = True) -> str:
        """Substitute the runtime placeholders (str.replace — see module docstring).

        This is the ONE construction path: the tests and every run render
        through here, so what is tested is what is sent. include_snippets is the single,
        non-divergent variation — False appends a one-line override telling the
        model to skip supporting-phrase extraction (a shorter completion for the
        cheap local sample); True is the full paid-batch prompt, unchanged.
        """
        rendered = self.user_prompt_template.replace("{comment_text}", comment_text)
        rendered = rendered.replace("{topics_list}", self.topics_list_text)
        if not include_snippets:
            rendered += (
                "\n\nFOR THIS RUN ONLY: classify sentiment and topics, but do NOT"
                ' extract supporting phrases — return "supporting_phrases": [] for'
                " every topic.")
        return rendered

    def snapshot(self) -> Dict[str, Any]:
        """The provenance snapshot written into batch metadata: everything the
        DB-free downstream steps (generate_batch_sql) need."""
        return {
            "prompt_id": self.prompt_id,
            "prompt_kind": self.prompt_kind,
            "prompt_name": self.prompt_name,
            "version": self.version,
            "model_name": self.model_name,
            "sentiment_map": self.sentiment_map,
            "analysis_schema": self.analysis_schema,
            "topics_count": len(self.topics),
        }
