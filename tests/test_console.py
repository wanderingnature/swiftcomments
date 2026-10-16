"""The console over a real temporary SQLite file: every query of console/queries.py
runs on the schema, and the app renders each of its five pages through Streamlit's
AppTest (the script run in-process, no server) with db.DB_PATH pointed at the file.

    uv run pytest tests/test_console.py
"""
import json
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from shared import db, score_json  # noqa: E402
from console.queries import COMMENT, COMPARE_READINGS, COMPARE_RUNS, STEPS, TABLES  # noqa: E402

APP = _REPO / "console" / "app.py"
CID = "FS-2025-0001-0002"


@pytest.fixture
def dbfile(tmp_path, monkeypatch):
    path = tmp_path / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO comment (comment_id, comment_text, posted_date, received_date)"
                 " VALUES (?, 'Keep the roadless rule. It protects the Tongass.', "
                 "'2026-08-20T04:00Z', '2026-08-19T00:00Z')", (CID,))
    conn.execute("INSERT INTO attachment_file VALUES (?, 1, 'pdf', 'https://example.test/a.pdf')", (CID,))
    conn.execute("INSERT INTO comment_dedup (comment_id, content_hash, is_original) VALUES (?, 'h', 1)", (CID,))
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


def test_every_query_runs_on_the_schema(dbfile):
    conn = db.connect(dbfile)
    for step in STEPS:
        for label, sql in step["figures"]:
            if step["target"] == "facts":
                continue        # comment_facts is built by make facts, not the schema
            assert conn.execute(sql).fetchone() is not None, (step["target"], label)
        for label, sql in step["breakdowns"]:
            conn.execute(sql).fetchall()
    for title, sql in COMMENT:
        conn.execute(sql, (CID,) * sql.count("?")).fetchall()
    conn.execute(COMPARE_RUNS).fetchall()
    conn.execute(COMPARE_READINGS, ("r",)).fetchall()
    names = [r["name"] for r in conn.execute(TABLES)]
    assert "comment" in names and "v_source_comments" in names
    conn.close()


def _run(at):
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_steps_page_renders(dbfile):
    at = _run(AppTest.from_file(str(APP), default_timeout=60))
    headers = [h.value for h in at.subheader]
    assert headers[0] == "make schema" and headers[-1] == "make facts"
    assert len(headers) == len(STEPS)
    # the corpus step has rows, the floor has none, comment_facts has no table
    texts = [t.value for t in at.text]
    assert any("not run" in t for t in texts)


def test_comment_page_renders(dbfile):
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.radio[0].set_value("Comment")
    _run(at)
    at.text_input[0].set_value(CID)
    _run(at)
    assert [h.value for h in at.subheader] == [title for title, _ in COMMENT]
    assert any("Tongass" in t.value for t in at.text)
    at.text_input[0].set_value("FS-2025-0001-99999")
    _run(at)
    assert at.error[0].value == "no comment FS-2025-0001-99999"


def test_tables_page_renders(dbfile):
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.radio[0].set_value("Tables")
    _run(at)
    at.selectbox[0].set_value("comment (table)")
    _run(at)
    assert any(t.value == "1 rows" for t in at.text)
    assert len(at.dataframe) == 1


def test_query_page_is_read_only(dbfile):
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.radio[0].set_value("Query")
    _run(at)
    at.text_area[0].set_value("SELECT count(*) AS n FROM comment")
    at.button[0].click()
    _run(at)
    assert at.dataframe[0].value.iloc[0]["n"] == 1
    at.text_area[0].set_value("DELETE FROM comment")
    at.button[0].click()
    _run(at)
    assert "readonly" in at.error[0].value
    conn = db.connect(dbfile)
    assert conn.execute("SELECT count(*) FROM comment").fetchone()[0] == 1
    conn.close()


def _reading(scorer, gap):
    levels = {d: 0 for d in score_json.DIMS}
    levels["GAP"] = gap
    return {"comment_id": CID, "scorer": scorer, "instrument": "v3" if scorer == "model" else "rules-3",
            "model": "m" if scorer == "model" else None, "levels": levels, "strength": gap,
            "gate": gap >= 2, "gate_basis": [], "band": "minimal", "a_level": None, "evidence": []}


def test_compare_page_renders(dbfile):
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.radio[0].set_value("Compare")
    _run(at)
    assert any("no comparison run yet" in t.value for t in at.text)

    conn = db.connect(dbfile)
    for run_id, model_gap, rules_gap in (("20261016_100000", 2, 1), ("20261016_110000", 2, 2)):
        conn.execute("INSERT INTO score_compare_run (run_id, started_at, finished_at, code_version,"
                     " code_dirty, model, server, instrument_version, ruleset_version, pool, picked, report)"
                     " VALUES (?, 's', 'f', ?, 0, 'm', 'http://x', 'v3', '3', 1, 1, ?)",
                     (run_id, run_id * 2, f"report of {run_id}"))
        for method, gap in (("model", model_gap), ("model-free", rules_gap)):
            conn.execute("INSERT INTO score_compare_reading (run_id, comment_id, method, record)"
                         " VALUES (?, ?, ?, ?)",
                         (run_id, CID, method, json.dumps(_reading("model" if method == "model" else "rules", gap))))
    conn.commit()
    conn.close()
    _run(at)
    assert len(at.dataframe) == 2
    texts = [t.value for t in at.text]
    assert "report of 20261016_110000" in texts
    # A: the earlier run's model reading; B: the newest run's rules reading.
    pair = next(t for t in texts if t.startswith("A: run "))
    assert pair.startswith("A: run 20261016_100000, model\nB: run 20261016_110000, model-free")
    assert "identical on all eight: 1 of 1" in pair
    # The rules' reading of the two runs set side by side: GAP moved from 1 to 2.
    at.selectbox(key="a_method").set_value("model-free")
    _run(at)
    pair = next(t.value for t in at.text if t.value.startswith("A: run "))
    assert "gate disagreements: 1" in pair and "  A PLACE 0 STAND 0 DOC 0 GAP 1" in pair
