"""shared/db.py: the connection and the four registered functions, against a real
temporary SQLite file.

The regexp cases are the floor filter's three patterns
(scripts/substance/floor_filter.py) on fixed strings, case-insensitive with (?i); regexp_count's are the attachment accounting's record markers; md5
is checked against hashlib; authority_family_key against the expected family_key of every
citation of legal_authority and comment_authorities (tests/fixtures/
authority_family_key.csv).

    uv run pytest tests/test_db.py
"""
import csv
import hashlib
import sqlite3
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from shared import db  # noqa: E402

FIXTURE = _REPO / "tests" / "fixtures" / "authority_family_key.csv"

CITATION_RE = "(?i)" + (
    r"(section|sec\.|§|table|figure|fig\.|appendix|chapter)\s*\d"
    r"|\yp+\.?\s*\d"
    r"|\d+\s*(c\.?f\.?r\.?|u\.?s\.?c\.?)"
    r"|\y(c\.?f\.?r\.?|u\.?s\.?c\.?)\s*\d"
    r"|\yNEPA\y|National Environmental Policy Act"
    r"|\yESA\y|Endangered Species Act"
    r"|\yFLPMA\y|Federal Land Policy"
    r"|\yNHPA\y|National Historic Preservation Act"
    r"|Clean Water Act|Clean Air Act|Antiquities Act|Migratory Bird"
    r"|Executive Order\s*\d|\yAPD\y"
)
DEFICIENCY_RE = "(?i)" + (
    r"fail(ed|s)? to|did not (consider|analyze|address|look|account|study|evaluate|examine)"
    r"|does(n'?t| not) (consider|address|account|analyze|evaluate|examine)"
    r"|not (adequately|sufficiently|properly) (consider|analyz|address|evaluat|studi)"
    r"|ignore[sd]?|overlook(ed|s|ing)?|inadequate|insufficient"
    r"|no analysis of|lack(s|ing)? (of )?analysis|missing (analysis|data)"
    r"|should have (considered|analyzed|studied|evaluated|examined)"
    r"|without (considering|analyzing|evaluating)|underestimat|fails to account"
)
FIRSTPERSON_RE = "(?i)" + (
    r"\y(i|we|my|our)\y[^.!?]{0,60}\y"
    r"(saw|seen|see|noticed?|watch(ed)?|observ(ed)?|witness(ed)?|"
    r"fish(ed)?|hunt(ed)?|hik(ed|e)?|walk(ed)?|camp(ed)?|rode|ride|drove|drive|"
    r"live[sd]?|lived|visit(ed)?|remember|grew up|breathe|drink|rely|depend)\y"
    r"|\y(saw|seen|noticed|watched|observed|witnessed|hunted|fished|hiked)\y"
    r"[^.!?]{0,30}\y(i|we|my|our)\y"
)


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "t.sqlite", create=True)
    yield c
    c.close()


def one(conn, sql, *params):
    return conn.execute(sql, params).fetchone()[0]


# ---- the connection -------------------------------------------------------

def test_a_missing_file_is_refused_with_the_command_that_makes_one(tmp_path):
    with pytest.raises(SystemExit, match="make schema"):
        db.connect(tmp_path / "absent.sqlite")


def test_pragmas_and_row_factory(conn):
    assert one(conn, "PRAGMA journal_mode") == "wal"
    assert one(conn, "PRAGMA synchronous") == 1          # NORMAL
    assert one(conn, "PRAGMA foreign_keys") == 1
    row = conn.execute("SELECT 1 AS a, 'x' AS b").fetchone()
    assert isinstance(row, sqlite3.Row) and row["a"] == 1 and row["b"] == "x"


def test_the_schema_applies_and_foreign_keys_are_enforced(conn):
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO attachment_file VALUES ('nobody', 1, 'pdf', 'u')")


def test_the_deferred_canonical_constraint_fires_at_commit(conn):
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO comment_group (group_kind, group_key, canonical_comment_id, size,"
                 " first_seen_at) VALUES ('singleton', 'k', 'absent', 1, '2026-09-01')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.commit()
    conn.rollback()


# ---- regexp --------------------------------------------------------------

@pytest.mark.parametrize("text, hit", [
    ("see 36 CFR 294.12 and keep the rule", 1),
    ("the National Environmental Policy Act requires a hard look", 1),
    ("as in Section 3 of the proposal", 1),
    ("NEPA demands it", 1),
    ("my grandfather hunted here", 0),
    ("the nepal trip was nice", 0),               # \yNEPA\y, not a substring
])
def test_the_floors_citation_pattern(conn, text, hit):
    assert one(conn, "SELECT ? REGEXP ?", text, CITATION_RE) == hit


@pytest.mark.parametrize("text, hit", [
    ("The agency failed to consider sediment.", 1),
    ("The DEIS does not address the lynx.", 1),
    ("an inadequate range of alternatives", 1),
    ("Please keep the roadless rule intact.", 0),
])
def test_the_floors_deficiency_pattern(conn, text, hit):
    assert one(conn, "SELECT ? REGEXP ?", text, DEFICIENCY_RE) == hit


@pytest.mark.parametrize("text, hit", [
    ("I have hiked there every summer since 1994.", 1),
    ("We saw elk on the ridge last fall.", 1),
    ("Noticed the erosion, my neighbor and I did.", 1),
    ("The forest is beautiful and should be kept.", 0),
])
def test_the_floors_firstperson_pattern(conn, text, hit):
    assert one(conn, "SELECT ? REGEXP ?", text, FIRSTPERSON_RE) == hit


def test_regexp_is_case_sensitive_unless_the_pattern_says(conn):
    assert one(conn, "SELECT 'Attached are 20 comments' REGEXP 'Attached are'") == 1
    assert one(conn, "SELECT 'attached are 20 comments' REGEXP 'Attached are'") == 0
    assert one(conn, "SELECT 'attached are 20 comments' REGEXP '(?i)Attached are'") == 1


def test_regexp_translates_the_postgres_word_boundaries(conn):
    assert one(conn, r"SELECT 'Brevard, NC 28712' REGEXP '\m[0-9]{5}\M'") == 1
    assert one(conn, r"SELECT 'order 287123 now' REGEXP '\m[0-9]{5}\M'") == 0
    assert one(conn, r"SELECT 'zip code here' REGEXP '\yzip\y'") == 1
    assert one(conn, r"SELECT 'unzipped' REGEXP '\yzip\y'") == 0


def test_regexp_is_null_on_a_null_side(conn):
    assert conn.execute("SELECT NULL REGEXP 'a'").fetchone()[0] is None
    assert conn.execute("SELECT 'a' REGEXP NULL").fetchone()[0] is None


# ---- regexp_count ---------------------------------------------------------

def test_regexp_count_counts_the_accountings_markers(conn):
    packet = ("First Name: Ann Date Submitted: 2026-09-01 First_Name: Bo Date Submitted: 2026-09-02"
              " First Name: Cy (zip code: 28712) ann@example.org bo@mail.example.com")
    assert one(conn, "SELECT regexp_count(?, 'First[ _]Name:')", packet) == 3
    assert one(conn, "SELECT regexp_count(?, 'Date Submitted:')", packet) == 2
    assert one(conn, r"SELECT regexp_count(?, '\(zip code: ?[0-9]')", packet) == 1
    assert one(conn, r"SELECT regexp_count(?, '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}')", packet) == 2
    assert one(conn, r"SELECT regexp_count(?, '\m[0-9]{5}(-[0-9]{4})?\M')", packet) == 1
    assert one(conn, "SELECT regexp_count('nothing here', 'Dear (Secretary|Chief)')") == 0
    assert conn.execute("SELECT regexp_count(NULL, 'a')").fetchone()[0] is None


# ---- md5 ---------------------------------------------------------------------

def test_md5_is_postgres_md5(conn):
    for text in ("abc", "", "Roadless “Areas” &amp; Watersheds"):
        assert one(conn, "SELECT md5(?)", text) == hashlib.md5(text.encode("utf-8")).hexdigest()
    assert conn.execute("SELECT md5(NULL)").fetchone()[0] is None


# ---- authority_family_key ------------------------------------------------------

def test_authority_family_key_returns_the_fixture_key_on_every_citation(conn):
    with open(FIXTURE, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 447
    wrong = [(r["citation"], r["family_key"], got)
             for r in rows
             if (got := one(conn, "SELECT authority_family_key(?)", r["citation"])) != r["family_key"]]
    assert not wrong, f"{len(wrong)} of {len(rows)} differ from the fixture; first: {wrong[0]}"
    assert db.authority_family_key(rows[0]["citation"]) == rows[0]["family_key"]


@pytest.mark.parametrize("citation, key", [
    ("36 C.F.R. Part 294", "36 CFR 294"),
    ("36 CFR 294.12(b)", "36 CFR 294"),
    ("16 U.S.C. § 1604(g)", "16 U.S.C. 1604"),
    ("16 USC 1604", "16 U.S.C. 1604"),
    ("66 Fed. Reg. 3244", "66 FR 3244"),
    ("66 FR 3244", "66 FR 3244"),
    ("E.O. 13175", "Executive Order 13175"),
    ("executive order no. 14225", "Executive Order 14225"),
    ("Clean Water Act", "Clean Water Act"),
    ("  Seminole   Nation v.  United States ", "Seminole Nation v. United States"),
])
def test_authority_family_key_rules(citation, key):
    assert db.authority_family_key(citation) == key


def test_authority_family_key_is_null_on_null(conn):
    assert conn.execute("SELECT authority_family_key(NULL)").fetchone()[0] is None
