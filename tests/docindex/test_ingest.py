"""The record-document ingestion (scripts/docindex/ingest_documents.py), on
synthetic markdown in a real temporary file: the heading segmenter, the letter
segmenter, the page spans, the chunk offsets, the ingest, the re-ingest rules
and the prune.

    uv run pytest tests/docindex
"""
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db  # noqa: E402
from docindex import ingest_documents as ing  # noqa: E402

HEADED = """<!-- page 1 -->
Cover line before any heading.

# Contents

1 Introduction ... 2

# Introduction

<!-- page 2 -->
The proposal rescinds the rule. The analysis weighs road construction against
wildfire risk across the inventoried areas.

## Effects

<!-- page 3 -->
Sediment reaches the streams where roads cross them. The assessment names the
watersheds it read.
"""

LETTERS = """<!-- page 1 -->
The volume's own introduction, before the first letterhead.

# STATE OF EXAMPLE, OFFICE OF THE GOVERNOR

RE: The proposed rescission

Dear Director:

We write about the watersheds. Our agencies read the draft.

Sincerely,

# COUNTY OF SAMPLE

Dear Director:

The county's roads already fail in storms. The draft does not count them.

Sincerely,
"""


@pytest.fixture
def docdir(tmp_path, monkeypatch):
    src = tmp_path / "deis"
    src.mkdir()
    (src / "headed.md").write_text(HEADED, encoding="utf-8")
    (src / "letters.md").write_text(LETTERS, encoding="utf-8")
    monkeypatch.setattr(ing, "SOURCES", [
        ("headed.md", "A headed document", ing.seg_headings),
        ("letters.md", "The letters volume", ing.seg_letters),
    ])
    return src


@pytest.fixture
def dbfile(tmp_path):
    path = tmp_path / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    yield conn
    conn.close()


def test_seg_headings_paths_and_kinds():
    secs = ing.seg_headings(HEADED)
    paths = [(s["heading_path"], s["kind"]) for s in secs]
    assert paths == [
        (["(front matter)"], "front"),
        (["Contents"], "toc"),
        (["Introduction"], "body"),
        (["Introduction", "Effects"], "body"),
    ]
    # the sections cover the text in order, no gaps
    assert secs[0]["start"] == 0 and secs[-1]["end"] == len(HEADED)
    for a, b in zip(secs, secs[1:]):
        assert a["end"] == b["start"]


def test_seg_letters_one_section_per_letter():
    secs = ing.seg_letters(LETTERS)
    letters = [s for s in secs if s["kind"] == "letter"]
    assert len(letters) == 2
    assert letters[0]["heading_path"][0].startswith("Letter 1: STATE OF EXAMPLE")
    assert letters[1]["heading_path"][0].startswith("Letter 2: COUNTY OF SAMPLE")
    # the letter starts at its letterhead, not at the RE: line
    assert LETTERS[letters[0]["start"]:].startswith("# STATE OF EXAMPLE")
    # the intro before the first letter is front matter
    assert secs[0]["kind"] == "front"


def test_page_span_skips_markers():
    marks = ing.page_marks("headed.md", HEADED)
    assert [p for _, p in marks] == [1, 2, 3]
    secs = ing.seg_headings(HEADED)
    intro = next(s for s in secs if s["heading_path"] == ["Introduction"])
    # the Introduction heading is on page 1; its body starts after the page-2 marker
    # and its subsection ends on page 3, which belongs to Effects
    assert ing.page_span(marks, HEADED, intro["start"], intro["end"]) == (1, 2)
    effects = next(s for s in secs if s["heading_path"] == ["Introduction", "Effects"])
    assert ing.page_span(marks, HEADED, effects["start"], effects["end"]) == (2, 3)


def test_chunks_carry_their_offsets():
    secs = ing.seg_headings(HEADED)
    for sec in secs:
        for piece, a, b in ing.chunk_section("headed.md", HEADED, sec):
            assert HEADED[a:b] == piece
    # a toc section gives no chunks
    toc = next(s for s in secs if s["kind"] == "toc")
    assert ing.chunk_section("headed.md", HEADED, toc) == []


def test_ingest_prune_and_reingest(docdir, dbfile, monkeypatch, capsys):
    docs = ing.plan(docdir)
    ing.ingest(dbfile, docs, replace=False)
    n_docs = dbfile.execute("SELECT count(*) FROM doc_documents").fetchone()[0]
    assert n_docs == 2
    # heading paths stored as JSON, root first
    row = dbfile.execute(
        "SELECT heading_path, page_start, page_end FROM doc_sections s"
        " JOIN doc_documents d USING (document_id)"
        " WHERE d.source_file = 'headed.md' AND s.kind = 'body' ORDER BY s.ordinal").fetchall()
    assert json.loads(row[0][0]) == ["Introduction"] and (row[0][1], row[0][2]) == (1, 2)
    # a second run is a no-op
    ing.ingest(dbfile, docs, replace=False)
    assert "already ingested" in capsys.readouterr().out
    # a changed source is refused without --replace, re-ingested with it
    (docdir / "headed.md").write_text(HEADED + "\nA new line on page three.\n", encoding="utf-8")
    changed = ing.plan(docdir)
    with pytest.raises(SystemExit, match="changed since it was ingested"):
        ing.ingest(dbfile, changed, replace=False)
    ing.ingest(dbfile, changed, replace=True)
    assert dbfile.execute("SELECT count(*) FROM doc_documents").fetchone()[0] == 2
    # prune removes a document SOURCES no longer lists, and its rows with it
    monkeypatch.setattr(ing, "SOURCES", [("headed.md", "A headed document", ing.seg_headings)])
    ing.prune(dbfile)
    assert dbfile.execute("SELECT count(*) FROM doc_documents").fetchone()[0] == 1
    assert dbfile.execute(
        "SELECT count(*) FROM doc_sections WHERE document_id NOT IN"
        " (SELECT document_id FROM doc_documents)").fetchone()[0] == 0


def test_plan_stops_on_unknown_and_missing(docdir, monkeypatch):
    (docdir / "stranger.md").write_text("<!-- page 1 -->\n# X\nY.\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="no segmentation rule"):
        ing.plan(docdir)
    (docdir / "stranger.md").unlink()
    (docdir / "letters.md").unlink()
    with pytest.raises(SystemExit, match="missing from"):
        ing.plan(docdir)
    # --skip excuses the missing file
    assert len(ing.plan(docdir, skip=["letters.md"])) == 1


def test_no_page_markers_refused(tmp_path):
    with pytest.raises(SystemExit, match="no <!-- page N --> markers"):
        ing.page_marks("bare.md", "# A\nText with no markers.\n")
