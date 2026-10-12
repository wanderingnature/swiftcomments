#!/usr/bin/env python3
"""
Together.ai batch request generator — project-scoped.

Builds per-comment classification requests for one project, driven entirely by
that project's DB profile ({analysis}.prompts / topics / sentiment via
ProjectProfile): prompt text, topic taxonomy, model, and model parameters all
come from the profile, never from code.

Selection: by default one comment per unclassified comment group — the canonical
comment of every {analysis}.comment_group with no member holding an active row in
{analysis}.comment_classification; the loader propagates the result to the
group's members. --id-file selects explicit comment
ids instead (one per line). --random N selects N uniformly-random source
comments (>= MIN_COMMENT_LENGTH chars, duplicates included) regardless of
classification state — a repeatable way to run a random trial batch.

Outputs to batch_requests/<slug>/: batch_requests_<TS>_<n>.jsonl plus
batch_metadata_<TS>.json carrying the profile snapshot (prompt_id, version,
model, sentiment map, analysis schema) that the DB-free downstream steps
(generate_batch_sql.py) rely on. Records the run in
{analysis}.classification_runs.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import db  # noqa: E402
from shared.llm_client import no_thinking  # noqa: E402
from shared.project_context import add_project_argument, context_from_args  # noqa: E402
from src.pipeline.profile import ProjectProfile, sentiment_topic_response_format  # noqa: E402
from src.pipeline.paths import project_paths  # noqa: E402
from src.utils.logging_config import setup_logging  # noqa: E402

# CLI aliases only — the model of record is the profile's model_name.
TOGETHER_MODELS = {
    'qwen': 'Qwen/Qwen2.5-7B-Instruct-Turbo',
    'gpt': 'openai/gpt-oss-120b',
    'llama': 'meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo',
}

MIN_COMMENT_LENGTH = 30


def _one(cur):
    """The single row a count query must return. No row means the query is wrong."""
    row = cur.fetchone()
    if row is None:
        raise RuntimeError("expected one row, got none")
    return row


def _clean_text(comment_text: str) -> str:
    """Basic HTML entity cleanup (same as the predecessor)."""
    comment_text = comment_text.replace('&mdash;', '—').replace('&rsquo;', "'").replace('&nbsp;', ' ')
    return comment_text.replace('<br/>', ' ').replace('<br>', ' ')


class BatchRequestsGenerator:
    """Generate individual batch requests for Together.ai batch inference."""

    def __init__(self, ctx, model_alias=None, batch_size=1000):
        self.logger = setup_logging()
        self.ctx = ctx
        self.paths = project_paths(ctx.slug)
        self.profile = ProjectProfile.load(ctx, "sentiment_topic")
        self.model = TOGETHER_MODELS[model_alias] if model_alias else self.profile.model_name
        self.batch_size = batch_size
        self.logger.info(
            f"Batch generator for project {ctx.slug!r}: prompt"
            f" {self.profile.prompt_name!r} v{self.profile.version}"
            f" (id {self.profile.prompt_id}), model {self.model},"
            f" {len(self.profile.topics)} topics")

    def _create_batch_request(self, comment_id, comment_text):
        params = self.profile.model_parameters
        return {
            "custom_id": str(comment_id),
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.profile.system_prompt},
                    {"role": "user",
                     "content": self.profile.render_user_prompt(_clean_text(comment_text))},
                ],
                "temperature": params.get("temperature", 0.0),
                "top_p": params.get("top_p", 1.0),
                "response_format": sentiment_topic_response_format(),
                # Thinking OFF for a hybrid reasoner, in the Batch API's (Together's)
                # spelling; run_batch_local swaps in the endpoint's when it sends
                # the file elsewhere (shared.llm_client.thinking_off).
                **no_thinking(self.model),
            },
        }

    def _fetch_delta(self, limit=None, offset=0):
        """One comment per UNCLASSIFIED COMMENT GROUP — the default selection: the
        canonical comment of every group in {analysis}.comment_group (exact,
        middle-content, family, campaign or singleton; every comment is in exactly
        one) where no member has an active classification. The loader propagates the
        result to every member of the group. A copied template carries the template's
        stance whatever the commenter added around it, so one call answers the whole
        group.
        """
        query = """
            SELECT c.comment_id, c.comment_text
            FROM {analysis}.comment_group g
            JOIN {analysis}.v_source_comments c ON c.comment_id = g.canonical_comment_id
            WHERE LENGTH(c.comment_text) >= ?
              AND NOT EXISTS (
                  SELECT 1 FROM {analysis}.comment_group_member m
                  JOIN {analysis}.comment_classification cc
                    ON cc.comment_id = m.comment_id AND cc.is_active
                  WHERE m.group_id = g.group_id
              )
            ORDER BY c.comment_id
        """
        params = [MIN_COMMENT_LENGTH]
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        if offset:
            query += " OFFSET ?"
            params.append(offset)
        with db.connect(**self.ctx.db_config) as conn:
            if _one(conn.execute(self.ctx.render_sql(
                    "SELECT count(*) FROM {analysis}.comment_group")))[0] == 0:
                raise RuntimeError(
                    "comment_group is empty — build the comment groups"
                    " (build_comment_groups.py) before classifying. Classification sends"
                    " one comment per group and propagates it to the members; with no"
                    " groups there is nothing to select.")
            rows = conn.execute(self.ctx.render_sql(query), params).fetchall()
        return [{"comment_id": r[0], "comment_text": r[1]} for r in rows]

    def _fetch_by_ids(self, id_file, limit=None, offset=0):
        with open(id_file) as f:
            all_ids = [line.strip() for line in f if line.strip()]
        self.logger.info(f"Loaded {len(all_ids)} comment ids from {id_file}")
        if offset:
            all_ids = all_ids[offset:]
        if limit:
            all_ids = all_ids[:limit]
        if not all_ids:
            return []
        query = """
            SELECT comment_id, comment_text
            FROM {analysis}.v_source_comments
            WHERE comment_id IN (SELECT value FROM json_each(?)) AND LENGTH(comment_text) >= ?
            ORDER BY comment_id
        """
        with db.connect(**self.ctx.db_config) as conn:
            rows = conn.execute(self.ctx.render_sql(query),
                                (json.dumps(all_ids), MIN_COMMENT_LENGTH)).fetchall()
        found = {r[0] for r in rows}
        missing = [i for i in all_ids if i not in found]
        if missing:
            raise RuntimeError(
                f"{len(missing)} ids from {id_file} are not in"
                f" {self.ctx.analysis_schema}.v_source_comments (or are shorter than"
                f" {MIN_COMMENT_LENGTH} chars). All of them:\n  " + "\n  ".join(missing))
        return [{"comment_id": r[0], "comment_text": r[1]} for r in rows]

    def _fetch_random(self, n):
        """N uniformly-random source comments (duplicates included), ignoring
        classification state — a random trial sample."""
        query = """
            SELECT comment_id, comment_text
            FROM {analysis}.v_source_comments
            WHERE LENGTH(comment_text) >= ?
            ORDER BY RANDOM() LIMIT ?
        """
        with db.connect(**self.ctx.db_config) as conn:
            rows = conn.execute(self.ctx.render_sql(query),
                                (MIN_COMMENT_LENGTH, n)).fetchall()
        return [{"comment_id": r[0], "comment_text": r[1]} for r in rows]

    def _record_run(self, run_timestamp, comment_count):
        with db.connect(**self.ctx.db_config) as conn:
            conn.execute(self.ctx.render_sql(
                """
                INSERT INTO {analysis}.classification_runs
                    (run_timestamp, prompt_id, model_name, comment_count)
                VALUES (?, ?, ?, ?)
                """), (run_timestamp.isoformat(sep=' '), self.profile.prompt_id, self.model, comment_count))

    def generate(self, id_file=None, limit=None, offset=0, random_n=None):
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M%S')

        if random_n:
            comments = self._fetch_random(random_n)
            selection = 'random'
        elif id_file:
            comments = self._fetch_by_ids(id_file, limit=limit, offset=offset)
            selection = 'id_file'
        else:
            comments = self._fetch_delta(limit=limit, offset=offset)
            selection = 'unclassified_delta'
        self.logger.info(f"Selected {len(comments)} comments ({selection})")
        if not comments:
            self.logger.warning("Nothing to classify — no batch files generated")
            return []

        batch_files = []
        for file_idx in range(0, len(comments), self.batch_size):
            file_comments = comments[file_idx:file_idx + self.batch_size]
            filename = self.paths.batch_requests / (
                f"batch_requests_{timestamp}_{file_idx // self.batch_size + 1}.jsonl")
            with open(filename, 'w', encoding='utf-8') as f:
                for comment in file_comments:
                    request = self._create_batch_request(
                        comment['comment_id'], comment['comment_text'])
                    f.write(json.dumps(request, ensure_ascii=False) + '\n')
            batch_files.append(str(filename))
            self.logger.info(f"Generated {filename.name} ({len(file_comments)} requests)")

        metadata = {
            'generation_date': now.isoformat(),
            'project': self.ctx.slug,
            'profile': self.profile.snapshot(),
            'model': self.model,
            'selection': selection,
            'id_file': id_file,
            'total_comments': len(comments),
            'batch_size': self.batch_size,
            'batch_files': batch_files,
        }
        metadata_file = self.paths.batch_requests / f"batch_metadata_{timestamp}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Generated metadata file: {metadata_file}")

        self._record_run(now, len(comments))

        print(f"\nGenerated {len(batch_files)} batch file(s) for project {self.ctx.slug!r},"
              f" timestamp {timestamp}")
        print("Next step: the stance run sends one call per group itself:")
        print(f"  python scripts/reclassify_groups.py --project {self.ctx.slug} --new-run")
        return batch_files


def main():
    parser = argparse.ArgumentParser(
        description="Generate Together.ai batch classification requests for one project")
    add_project_argument(parser)
    parser.add_argument('--model', choices=sorted(TOGETHER_MODELS),
                        help='Model alias override (default: the profile model)')
    parser.add_argument('--batch-size', type=int, default=1000,
                        help='Comments per JSONL file (default: 1000)')
    parser.add_argument('--limit', type=int, help='Maximum comments to process')
    parser.add_argument('--offset', type=int, default=0, help='Selection offset')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--id-file',
                           help='File of comment ids (one per line); default selection is'
                                ' the unclassified delta')
    selection.add_argument('--random', type=int, metavar='N',
                           help='Select N uniformly-random source comments (duplicates'
                                ' included), ignoring classification state — a random'
                                ' trial batch')
    args = parser.parse_args()

    ctx = context_from_args(args)
    if ctx.status == "archived":
        raise SystemExit(f"Project {ctx.slug!r} is archived — restore it first.")
    generator = BatchRequestsGenerator(ctx, model_alias=args.model,
                                       batch_size=args.batch_size)
    batch_files = generator.generate(id_file=args.id_file, limit=args.limit,
                                     offset=args.offset, random_n=args.random)
    if not batch_files:
        sys.exit(0)


if __name__ == "__main__":
    main()
