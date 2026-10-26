"""The record-document ingestion (scripts/docindex/ingest_documents.py), on
synthetic markdown in a real temporary file: the heading segmenter, the letter
segmenter, the page map and page spans, the chunk offsets, the ingest, the
re-ingest rules and the prune.

    uv run pytest tests/docindex
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db  # noqa: E402
from docindex import ingest_documents as ing  # noqa: E402

HEADED = """Cover line before any heading.

# Contents

1 Introduction ... 2

# Introduction

The proposal rescinds the rule. The analysis weighs road construction against
wildfire risk across the inventoried areas.

## Effects

Sediment reaches the streams where roads cross them. The assessment names the
watersheds it read.
"""
# Page 2 starts at the Introduction body, page 3 at the Effects body.
HEADED_PAGES = [(1, 0), (2, HEADED.index("The proposal rescinds")),
                (3, HEADED.index("Sediment reaches"))]

LETTERS = """The volume's own introduction, before the first letterhead.

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


def write_source(src, name, text, pages):
    """The markdown and its page map, as the conversion lays them out."""
    (src / f"{name}.md").write_text(text, encoding="utf-8")
    (src / f"{name}.pages.json").write_text(json.dumps({
        "source": f"{name}.md",
        "sha256": hashlib.sha256(text.encode()).hexdigest(),
        "pages": [{"pdf_page": p, "printed": None, "start": s} for p, s in pages],
    }), encoding="utf-8")


@pytest.fixture
def docdir(tmp_path, monkeypatch):
    src = tmp_path / "deis"
    src.mkdir()
    write_source(src, "headed", HEADED, HEADED_PAGES)
    write_source(src, "letters", LETTERS, [(1, 0)])
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


def test_page_map_and_spans(docdir):
    marks = ing.page_marks(docdir / "headed.md", HEADED)
    assert marks == [(0, 1), (HEADED_PAGES[1][1], 2), (HEADED_PAGES[2][1], 3)]
    secs = ing.seg_headings(HEADED)
    # the Introduction heading is on page 1 and its body runs on page 2; the
    # Effects subsection's body is page 3's
    intro = next(s for s in secs if s["heading_path"] == ["Introduction"])
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
    # heading paths stored as JSON, root first; the page span from the map
    row = dbfile.execute(
        "SELECT heading_path, page_start, page_end FROM doc_sections s"
        " JOIN doc_documents d USING (document_id)"
        " WHERE d.source_file = 'headed.md' AND s.kind = 'body' ORDER BY s.ordinal").fetchall()
    assert json.loads(row[0][0]) == ["Introduction"] and (row[0][1], row[0][2]) == (1, 2)
    # a second run is a no-op
    ing.ingest(dbfile, docs, replace=False)
    assert "already ingested" in capsys.readouterr().out
    # a changed source is refused without --replace, re-ingested with it
    write_source(docdir, "headed", HEADED + "\nA new line on page three.\n", HEADED_PAGES)
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


def test_plan_stops_on_unknown_and_missing(docdir):
    write_source(docdir, "stranger", "# X\nY with enough text to hold.\n", [(1, 0)])
    with pytest.raises(SystemExit, match="no segmentation rule"):
        ing.plan(docdir)
    (docdir / "stranger.md").unlink()
    (docdir / "stranger.pages.json").unlink()
    (docdir / "letters.md").unlink()
    with pytest.raises(SystemExit, match="missing from"):
        ing.plan(docdir)
    # --skip excuses the missing file
    assert len(ing.plan(docdir, skip=["letters.md"])) == 1


def test_page_map_required_and_matching(tmp_path):
    md = tmp_path / "bare.md"
    md.write_text("# A\nText with no page map beside it.\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="no bare.pages.json beside it"):
        ing.page_marks(md, md.read_text(encoding="utf-8"))
    # a map whose sha256 is another text's is refused
    write_source(tmp_path, "bare", "different text\n", [(1, 0)])
    md.write_text("# A\nText the map does not describe.\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="does not match"):
        ing.page_marks(md, md.read_text(encoding="utf-8"))
