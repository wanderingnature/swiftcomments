"""The labels of scripts/docindex/nli.py, on stored retrieval and NLI rows in a
real temporary file: the four sentence labels, the pair each one cites, the
comment order, and the stops. The cross-encoder itself is not run here; the
label logic reads its stored probabilities.

    uv run pytest tests/docindex
"""
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db  # noqa: E402
from docindex import nli  # noqa: E402

EMB, NLI = "test-embed", "test-nli"


@pytest.fixture
def dbfile(tmp_path):
    conn = db.connect(tmp_path / "roadless.sqlite", create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute("INSERT INTO doc_documents (document_id, title, source_file, sha256,"
                 " n_chars, ingested_at) VALUES (1, 'A document', 'doc.md', 'x', 100, 't')")
    conn.execute("INSERT INTO doc_sections (section_id, document_id, ordinal, heading_path,"
                 " kind, start_char, end_char, section_text) VALUES (1,1,0,'[\"B\"]','body',0,9,'s')")
    for cid in (10, 11):
        conn.execute("INSERT INTO doc_chunks (chunk_id, section_id, chunk_index, chunk_text,"
                     " start_char, end_char, max_chunk_size, chunk_overlap)"
                     " VALUES (?,1,?,?,0,9,600,100)", (cid, cid - 10, f"chunk {cid}"))
    yield conn
    conn.close()


def pair(conn, key, cid, rank, cosine, probs=None):
    conn.execute("INSERT INTO doc_retrieval (text_key, embedding_model, rank, chunk_id,"
                 " cosine, created_at) VALUES (?,?,?,?,?,'t')", (key, EMB, rank, cid, cosine))
    if probs:
        conn.execute("INSERT INTO doc_nli (text_key, chunk_id, nli_model, p_entailment,"
                     " p_neutral, p_contradiction, created_at) VALUES (?,?,?,?,?,?,'t')",
                     (key, cid, NLI, *probs))


def opener(conn, comment_id, key):
    conn.execute("INSERT INTO gate_sentence_occurrence (unit_id, text_key, comment_id, law,"
                 " evid, gap, alt, opens, holds_hit) VALUES (NULL,?,?,0,1,0,0,1,0)",
                 (key, comment_id))


def test_label_order_reads_the_config():
    assert nli.label_order({0: "entailment", 1: "neutral", 2: "contradiction"}) == (0, 1, 2)
    assert nli.label_order({"0": "CONTRADICTION", "1": "Neutral", "2": "entailment"}) == (2, 1, 0)
    with pytest.raises(SystemExit, match="not"):
        nli.label_order({0: "yes", 1: "no"})


def test_sentence_labels_and_comment_order(dbfile):
    # contested outranks an entailed pair of the same sentence
    pair(dbfile, "k-con", 10, 1, 0.9, (0.8, 0.1, 0.1))
    pair(dbfile, "k-con", 11, 2, 0.8, (0.1, 0.1, 0.8))
    # addressed: entailment, no contradiction
    pair(dbfile, "k-add", 10, 1, 0.85, (0.9, 0.05, 0.05))
    # not_addressed: read, nothing decisive, whatever the cosine
    pair(dbfile, "k-nd", 11, 1, 0.8, (0.3, 0.5, 0.2))
    pair(dbfile, "k-low", 10, 1, 0.4, (0.3, 0.6, 0.1))
    for cid, key in [("C1", "k-add"), ("C1", "k-con"), ("C2", "k-nd"),
                     ("C2", "k-low"), ("C3", "k-add")]:
        opener(dbfile, cid, key)
    n_sent, n_com = nli.labels(dbfile, EMB, NLI)
    assert (n_sent, n_com) == (4, 3)
    got = dict(dbfile.execute("SELECT text_key, label FROM doc_sentence_label").fetchall())
    assert got == {"k-con": "contested", "k-add": "addressed",
                   "k-nd": "not_addressed", "k-low": "not_addressed"}
    # the contested row cites the contradiction pair, not the nearer entailed one
    row = dbfile.execute("SELECT chunk_id, cosine, p_contradiction FROM doc_sentence_label"
                         " WHERE text_key = 'k-con'").fetchone()
    assert (row[0], row[1], row[2]) == (11, 0.8, 0.8)
    # not_addressed cites its nearest read pair, at any cosine
    row = dbfile.execute("SELECT chunk_id, cosine, p_entailment FROM doc_sentence_label"
                         " WHERE text_key = 'k-low'").fetchone()
    assert tuple(row) == (10, 0.4, 0.3)
    # the comment takes the strongest label: contested, not_addressed, addressed
    got = dict(dbfile.execute("SELECT comment_id, label FROM doc_comment_label").fetchall())
    assert got == {"C1": "contested", "C2": "not_addressed", "C3": "addressed"}
    # a second build replaces, not duplicates
    nli.labels(dbfile, EMB, NLI)
    assert dbfile.execute("SELECT count(*) FROM doc_sentence_label").fetchone()[0] == 4


def test_any_unread_pair_stops(dbfile):
    pair(dbfile, "k-x", 10, 1, 0.9, (0.9, 0.05, 0.05))
    pair(dbfile, "k-x", 11, 2, 0.4)
    with pytest.raises(SystemExit, match="unread"):
        nli.labels(dbfile, EMB, NLI)


def test_empty_retrieval_stops(dbfile):
    with pytest.raises(SystemExit, match="run make retrieve"):
        nli.labels(dbfile, EMB, NLI)
