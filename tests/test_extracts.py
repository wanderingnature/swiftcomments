"""The extracts (docs/limit-and-jump.md) over real temporary files: a step's tables
dumped from one file and loaded into another come back row for row, the jump is
cumulative, the generated column is handled, comment_facts is rebuilt, a missing
extract and an empty corpus are refused, and the registry agrees with the Makefile
and the console.

    uv run pytest tests/test_extracts.py
"""
import re
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db, steps  # noqa: E402
import dump_extract  # noqa: E402
import load_extract  # noqa: E402
from console.queries import STEPS as CONSOLE_STEPS  # noqa: E402

CID = ("FS-2025-0001-0002", "FS-2025-0001-0003")


def _schema_file(path):
    """The schema and the seed rows make schema loads (a prompt, a topic): the
    stance rows of an extract reference them, and the loader checks the keys."""
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO prompts (prompt_id, prompt_kind, prompt_name, system_prompt,"
                 " user_prompt_template, model_name, is_active) VALUES (1, 'sentiment_topic', 'p', 's', 'u', 'm', 1)")
    conn.execute("INSERT INTO topics (topic_id, topic_name) VALUES (1, 'Water')")
    conn.commit()
    return conn


@pytest.fixture
def source(tmp_path):
    conn = _schema_file(tmp_path / "source.sqlite")
    for cid in CID:
        conn.execute("INSERT INTO comment (comment_id, comment_text) VALUES (?, 'Keep the rule.')", (cid,))
        conn.execute("INSERT INTO comment_dedup (comment_id, content_hash, is_original) VALUES (?, 'h', 1)", (cid,))
    conn.execute("INSERT INTO classification_runs (run_timestamp, prompt_id, model_name, comment_count)"
                 " VALUES ('2026-10-13T00:00:00', 1, 'm', 2)")
    for i, cid in enumerate(CID, 1):
        conn.execute("INSERT INTO comment_classification (classification_id, comment_id, sentiment_id,"
                     " sentiment_strength, batch_id) VALUES (?, ?, 2, 'HIGH', 'run1')", (i, cid))
        conn.execute("INSERT INTO classification_topics (classification_id, topic_id, confidence,"
                     " supporting_phrases) VALUES (?, 1, 0.9, '[\"keep\", \"rule\"]')", (i,))
    conn.execute("CREATE TABLE comment_facts AS SELECT comment_id, 1 AS n FROM comment")
    conn.commit()
    conn.close()
    return tmp_path / "source.sqlite"


@pytest.fixture
def extracts(tmp_path, monkeypatch):
    d = tmp_path / "extracts"
    monkeypatch.setattr(dump_extract, "EXTRACTS_DIR", d)
    monkeypatch.setattr(load_extract, "EXTRACTS_DIR", d)
    return d


def test_dump_then_jump_restores_the_rows(source, extracts, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", source)
    for t in ("dedup", "ngrams", "ner", "tag", "floor", "groups", "screen", "stance"):
        dump_extract.main(["--target", t])
    assert sorted(p.name for p in extracts.iterdir()) == sorted(
        f"{t}.sqlite" for t in ("dedup", "ngrams", "ner", "tag", "floor", "groups", "screen", "stance"))
    with pytest.raises(SystemExit, match="exists; pass --force"):
        dump_extract.main(["--target", "dedup"])
    dump_extract.main(["--target", "dedup", "--force"])

    target = tmp_path / "target.sqlite"
    conn = _schema_file(target)
    for cid in CID:
        conn.execute("INSERT INTO comment (comment_id, comment_text) VALUES (?, 'Keep the rule.')", (cid,))
    conn.execute("INSERT INTO comment_dedup (comment_id, content_hash, is_original) VALUES ('stale', 'x', 1)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", target)
    load_extract.main(["--target", "stance"])

    conn = db.connect(target)
    assert [r[0] for r in conn.execute("SELECT comment_id FROM comment_dedup ORDER BY 1")] == list(CID)
    assert conn.execute("SELECT count(*) FROM classification_topics").fetchone()[0] == 2
    assert conn.execute("SELECT phrase_count FROM classification_topics").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM comment_classification WHERE is_active").fetchone()[0] == 2
    conn.close()


def test_jump_needs_every_extract_and_a_corpus(source, extracts, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", source)
    dump_extract.main(["--target", "dedup"])
    with pytest.raises(SystemExit, match="no extract for make ngrams, make ner"):
        load_extract.main(["--target", "ner"])
    empty = tmp_path / "empty.sqlite"
    _schema_file(empty).close()
    monkeypatch.setattr(db, "DB_PATH", empty)
    with pytest.raises(SystemExit, match="run make corpus first"):
        load_extract.main(["--target", "dedup"])


def test_corpus_and_fetch_are_not_extracted(source, extracts, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", source)
    for t in ("corpus", "fetch"):
        with pytest.raises(SystemExit, match="is not extracted"):
            dump_extract.main(["--target", t])


def test_facts_is_rebuilt_as_a_table(source, extracts, tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", source)
    for t in steps.TARGETS:
        if t not in steps.NOT_EXTRACTED:
            dump_extract.main(["--target", t])
    target = tmp_path / "target.sqlite"
    conn = _schema_file(target)
    conn.execute("INSERT INTO comment (comment_id, comment_text) VALUES (?, 'x')", (CID[0],))
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", target)
    load_extract.main(["--target", "facts"])
    conn = db.connect(target)
    assert conn.execute("SELECT count(*) FROM comment_facts").fetchone()[0] == 2
    conn.close()


def test_registry_matches_the_makefile_and_the_console():
    makefile = (_REPO / "Makefile").read_text(encoding="utf-8")
    all_line = re.search(r"^all: (.*?)  ##", makefile, re.M).group(1).split()
    assert all_line == ["schema"] + steps.TARGETS + ["check"]
    assert [s["target"] for s in CONSOLE_STEPS] == ["schema"] + steps.TARGETS
