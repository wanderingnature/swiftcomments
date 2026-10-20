"""make schema-add (scripts/make_schema.py --add) on a real temporary file: a
file made before a step's tables existed gets them, its rows are untouched, a
second run adds nothing, and a file that does not exist is refused.

    uv run pytest tests/test_make_schema_add.py
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from shared import db  # noqa: E402
from scripts import make_schema  # noqa: E402

LATER = ["cluster_case_topic", "cluster_case_cluster", "cluster_case_member", "cluster_case_leader",
         "cluster_case", "sentence_embedding", "gate_sentence", "gate_sentence_occurrence", "gate_sentence_run"]


def test_add_creates_what_the_file_lacks(tmp_path, monkeypatch, capsys):
    path = tmp_path / "roadless.sqlite"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(sys, "argv", ["make_schema.py"])
    make_schema.main()
    conn = db.connect(path)
    for t in LATER:
        conn.execute(f"DROP TABLE {t}")
    conn.execute("INSERT INTO comment (comment_id, comment_text) VALUES ('FS-2025-0001-0001', 'kept')")
    conn.commit()
    conn.close()
    capsys.readouterr()

    monkeypatch.setattr(sys, "argv", ["make_schema.py", "--add"])
    make_schema.main()
    out = capsys.readouterr().out
    assert "added 12:" in out and "table gate_sentence_run" in out and "index cluster_case_member_cluster" in out
    conn = db.connect(path)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert set(LATER) <= names
    assert conn.execute("SELECT comment_text FROM comment").fetchone()[0] == "kept"
    conn.close()
    make_schema.main()
    assert "has every object of the schema" in capsys.readouterr().out


def test_add_needs_a_file(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "none.sqlite")
    monkeypatch.setattr(sys, "argv", ["make_schema.py", "--add"])
    with pytest.raises(SystemExit, match="does not exist"):
        make_schema.main()
