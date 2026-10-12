"""run_pass: the authority tag insert writes family_key, NOT NULL since migration 0069.
No database: the insert is built by tag_insert and checked as SQL and parameters."""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from scripts.entity_tagging import run_pass  # noqa: E402

ROWS = [("FS-2025-0001-223872", "36 CFR 294.12(b)", "36 C.F.R. 294.12(b)")]


def test_authority_insert_computes_family_key_from_the_citation():
    sql, params = run_pass.tag_insert("authorities", "strict", ROWS)
    assert "INSERT INTO {analysis}.comment_authorities" in sql
    assert "family_key" in sql
    assert "{analysis}.authority_family_key(?)" in sql
    assert sql.count("?") == 5
    assert params == [("FS-2025-0001-223872", "36 CFR 294.12(b)", "36 C.F.R. 294.12(b)",
                       "strict", "36 CFR 294.12(b)")]


def test_the_other_tag_tables_do_not_carry_a_family_key():
    for etype in ("forests", "areas", "species", "cited_references"):
        sql, params = run_pass.tag_insert(etype, "loose", ROWS)
        table, value_col = run_pass.TAG_SPECS[etype]
        assert f"INSERT INTO {{analysis}}.{table} (comment_id, {value_col}, matched_text, mode)" in sql
        assert "family_key" not in sql
        assert sql.count("?") == 4
        assert params == [("FS-2025-0001-223872", "36 CFR 294.12(b)", "36 C.F.R. 294.12(b)",
                           "loose")]
