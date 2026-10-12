"""The one module that knows SQLite (plan 5.2).

Every step opens data/roadless.sqlite through connect(): rows come back as
sqlite3.Row (so row["col"] works where psycopg's dict_row did), the file is in WAL
mode with synchronous=NORMAL and foreign keys on, and the four functions the ported
SQL calls are registered on the connection:

    regexp(pattern, text)        text REGEXP pattern; PostgreSQL's ~ and ~* (the port
                                 puts (?i) in the pattern where ~* was used), with the
                                 ARE word boundaries \\m, \\M and \\y translated
    regexp_count(text, pattern)  count(*) FROM regexp_matches(text, pattern, 'g')
    md5(text)                    PostgreSQL's md5()
    authority_family_key(cit)    roadless.authority_family_key, the family a written
                                 citation belongs to (rtca roadless_dynamic_views.sql)

The file is created by scripts/make_schema.py (connect(create=True)); a step that
finds no file stops with the command that makes one.
"""
import hashlib
import re
import sqlite3
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "roadless.sqlite"
SCHEMA_PATH = REPO_ROOT / "schema" / "roadless.sql"

# The ->> operator the ported SQL uses needs 3.38.
MIN_SQLITE = (3, 38, 0)


def require_sqlite() -> None:
    if sqlite3.sqlite_version_info < MIN_SQLITE:
        raise SystemExit(
            f"SQLite {sqlite3.sqlite_version} is too old: the SQL needs "
            f"{'.'.join(map(str, MIN_SQLITE))} or later (the ->> operator). "
            "Use a Python built against a newer SQLite.")


class Cursor(sqlite3.Cursor):
    """A cursor that is a context manager, as psycopg's is, so the ported
    `with conn.cursor() as cur:` blocks stand."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


class Connection(sqlite3.Connection):
    """sqlite3.Connection with the two psycopg conveniences the ported scripts use:
    cursors that are context managers, and `closed`."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.closed = False

    def cursor(self, factory=Cursor):
        return super().cursor(factory)

    def close(self):
        super().close()
        self.closed = True


def connect(path: Path | str = DB_PATH, *, create: bool = False,
            check_same_thread: bool = True) -> Connection:
    """Open the analysis database with the PRAGMAs of plan 4.1 and the functions
    registered. `create` is for make_schema.py alone: every other caller needs the
    file to exist already."""
    require_sqlite()
    path = Path(path)
    if not create and not path.exists():
        raise SystemExit(f"{path} does not exist: run `make schema` first.")
    conn = sqlite3.connect(path, check_same_thread=check_same_thread, factory=Connection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    register_functions(conn)
    return conn


# ---------------------------------------------------------------- functions

# PostgreSQL ARE escapes that Python's re spells differently. \m and \M are the
# start and end of a word; \y is either; \Y is a non-boundary.
_PG_ESCAPES = {r"\m": r"\b(?=\w)", r"\M": r"\b(?<=\w)", r"\y": r"\b", r"\Y": r"\B"}
_PG_ESCAPE_RE = re.compile(r"\\[mMyY]")


@lru_cache(maxsize=4096)
def _compile(pattern: str) -> re.Pattern:
    return re.compile(_PG_ESCAPE_RE.sub(lambda m: _PG_ESCAPES[m.group(0)], pattern))


def regexp(pattern, text) -> int | None:
    """`text REGEXP pattern`: 1 when the pattern matches anywhere, 0 when not, NULL
    when either side is NULL, as PostgreSQL's ~ is NULL on a NULL operand."""
    if pattern is None or text is None:
        return None
    return 1 if _compile(pattern).search(text) else 0


def regexp_count(text, pattern) -> int | None:
    """The number of non-overlapping matches, as regexp_matches(..., 'g') yields."""
    if pattern is None or text is None:
        return None
    return sum(1 for _ in _compile(pattern).finditer(text))


def md5(text) -> str | None:
    if text is None:
        return None
    return hashlib.md5(text.encode("utf-8")).hexdigest()


# roadless.authority_family_key, pattern for pattern. The guard and the capture of
# each PostgreSQL branch are one regex here; trim() strips spaces only, so a
# citation led by a tab keeps its tab, collapsed to a space, and falls through to
# the ELSE branch as it does there.
_WS = re.compile(r"\s+")
_CFR = re.compile(r"^(\d{1,3})\s+C\.?\s?F\.?\s?R\.?,?\s*(?:§+\s*|[Ss]ections?\s+|[Ss]ec\.?\s+|[Pp]arts?\s+|[Pp]t\.?\s+)?(\d+)")
_USC = re.compile(r"^(\d{1,3})\s+U\.?\s?S\.?\s?C\.?\s*(?:§+\s*|[Ss]ections?\s+|[Ss]ec\.?\s+)?(\d+[a-z]?)")
_FR = re.compile(r"^(\d{1,3})\s+(?:F\.?R\.?|Fed\.?\s?Reg\.?)\s+(\d{1,6})", re.IGNORECASE)
_EO = re.compile(r"^(?:Executive\s+Order|E\.?\s?O\.?)\s*(?:No\.?\s*)?(\d{4,5})", re.IGNORECASE)


def authority_family_key(citation) -> str | None:
    if citation is None:
        return None
    c = _WS.sub(" ", citation.strip(" "))
    m = _CFR.match(c)
    if m:
        return f"{m[1]} CFR {m[2]}"
    m = _USC.match(c)
    if m:
        return f"{m[1]} U.S.C. {m[2]}"
    m = _FR.match(c)
    if m:
        return f"{m[1]} FR {m[2]}"
    m = _EO.match(c)
    if m:
        return f"Executive Order {m[1]}"
    return c


class _Stddev:
    """PostgreSQL's STDDEV: the sample standard deviation, NULL under two values."""

    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def step(self, value):
        if value is None:
            return
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (value - self.mean)

    def finalize(self):
        if self.n < 2:
            return None
        return (self.m2 / (self.n - 1)) ** 0.5


def register_functions(conn: sqlite3.Connection) -> None:
    conn.create_function("regexp", 2, regexp, deterministic=True)
    conn.create_function("regexp_count", 2, regexp_count, deterministic=True)
    conn.create_function("md5", 1, md5, deterministic=True)
    conn.create_function("authority_family_key", 1, authority_family_key, deterministic=True)
    conn.create_aggregate("stddev", 1, _Stddev)
