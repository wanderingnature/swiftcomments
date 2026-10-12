"""ProjectContext — the shared per-project primitive for every rtca entry point.

One project and one SQLite file (plan 4.2): the context is a dataclass of constants
with the attribute names and methods the scripts use, in place of a row of
registry.projects. Pipeline SQL is written with {analysis}./{src}. tokens and rendered
through render_sql(), which renders both to nothing, so every query addresses the one
file; {scores} and {score_parts} keep scoping to shared.instrument.SCORING_INSTRUMENT.
"""

import re
from typing import LiteralString, cast
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from shared import db

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Load .env from the repo root at import, so every entry point gets the model server
# and the MinerU server (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, MINERU_BASE_URL,
# MINERU_API_KEY) without the caller having to pre-export them. Real exported env
# vars win (override=False); a missing .env is silently skipped and config comes
# from the real env.
load_dotenv(_REPO_ROOT / ".env")

SLUG = "roadless"
DOCKET_ID = "FS-2025-0001"

# Tokens rendered by render_sql(). SQL may contain other literal braces (e.g. in strings
# or JSON); only these bare tokens are recognized, and any left unrendered is an error.
_SQL_TOKEN_RE = re.compile(r"\{(analysis|src|scores|score_parts)\}")


@dataclass(frozen=True)
class ProjectContext:
    slug: str
    project_id: int
    display_name: str
    source_schema: str
    analysis_schema: str
    source_kind: str
    source_config: dict
    status: str
    db_config: dict = field(repr=False)
    root: Path

    @classmethod
    def load(cls, slug: str) -> "ProjectContext":
        """The one project. KeyError on any other slug."""
        if slug != SLUG:
            raise KeyError(f"No project with slug {slug!r}; this repository is {SLUG!r}")
        return cls(
            slug=SLUG,
            project_id=1,
            display_name="Roadless Rule rescission, FS-2025-0001",
            source_schema="",
            analysis_schema="",
            source_kind="regulations_gov",
            source_config={"identifier_value": DOCKET_ID},
            status="active",
            db_config={"path": db.DB_PATH},
            root=_REPO_ROOT / "data" / SLUG,
        )

    def render_sql(self, sql: str) -> LiteralString:
        """Replace {analysis}. / {src}. / {scores} / {score_parts} tokens.

        str.replace, not str.format — pipeline SQL contains literal braces. Raises if a
        recognized token somehow survives rendering (defense against malformed input).

        {scores} and {score_parts} are the score tables ALREADY SCOPED to
        shared.instrument.SCORING_INSTRUMENT. Scores from two instruments are not
        comparable and every generation's rows stay in the table forever, so a read
        that names the bare table is a read over a mixed population — and that is a
        defect grep cannot see, because a query with no instrument clause mentions no
        version at all. Measured on roadless 2026-09-19, after the v3 re-score:
        `count(*) WHERE gate` returned 8,628 against 1,036, and `NOT was_floored`
        61,656 against 38,969.

        These tokens are the default for anything that counts, averages, ranks or
        gates. Naming `{analysis}.substance_scores` directly still works and means
        "every generation on purpose" — the scorers' own done-set, the assembler and
        the provenance tooling.
        """
        from shared.instrument import SCORING_INSTRUMENT
        scoped = ("(SELECT * FROM {t} WHERE instrument_version = '{v}')"
                  "".format(t="{t}", v=SCORING_INSTRUMENT))
        rendered = (
            sql.replace("{scores}", scoped.format(t="substance_scores"))
               .replace("{score_parts}", scoped.format(t="substance_score_parts"))
               .replace("{analysis}.", "")
               .replace("{src}.", "")
        )
        leftover = _SQL_TOKEN_RE.search(rendered)
        if leftover:
            raise ValueError(f"Unrendered SQL token {leftover.group(0)} after rendering")
        return cast(LiteralString, rendered)

    # Per-project filesystem state (gitignored under data/; created lazily by entry points).

    @property
    def lexical_dir(self) -> Path:
        return self.root / "lexical"

    @property
    def models_dir(self) -> Path:
        return self.lexical_dir / "models"

    @property
    def cache_dir(self) -> Path:
        return self.lexical_dir / "cache"

    @property
    def logs_dir(self) -> Path:
        return self.lexical_dir / "logs"

    @property
    def checkpoint_file(self) -> Path:
        return self.lexical_dir / "checkpoint.json"

    @property
    def status_file(self) -> Path:
        return self.lexical_dir / "STATUS.md"

    @property
    def reports_dir(self) -> Path:
        return self.root / "reports"


def add_project_argument(parser) -> None:
    """Add the required --project argument to an argparse parser."""
    parser.add_argument(
        "--project",
        required=True,
        metavar="SLUG",
        help=f"Project slug; this repository is {SLUG!r}",
    )


def context_from_args(args) -> ProjectContext:
    """ProjectContext for the --project argument added by add_project_argument."""
    return ProjectContext.load(args.project)


def dict_connect(config: dict):
    """A connection whose rows are mappings (sqlite3.Row), opened through shared/db.py.

    `psycopg.connect(**config, row_factory=dict_row)` is what the call sites did; this
    is the one place that says what the connection actually yields.
    """
    return db.connect(**config)
