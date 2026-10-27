"""The record retrieval (scripts/docindex/retrieve.py), on synthetic vectors in a
real temporary file: the model discovery, the nearest chunks and their order, the
excluded sections (letters, comment summaries), and the stops.

    uv run pytest tests/docindex
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db, embeddings  # noqa: E402
from clusters.embed import VIEWS, pack  # noqa: E402
from docindex import retrieve  # noqa: E402

MODEL = "test-embed"


def axis(i, lean=0.0, j=1):
    """A unit vector along axis i, leaned toward axis j by `lean`."""
    v = np.zeros(embeddings.DIMENSIONS, dtype="<f4")
    v[i] = 1.0
    v[j] += lean
    return v / np.linalg.norm(v)


@pytest.fixture
def dbfile(tmp_path):
    conn = db.connect(tmp_path / "roadless.sqlite", create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    yield conn
    conn.close()


def seed(conn, model=MODEL):
    """One document: a body section with chunks on axes 0 to 2, a letter section
    with one chunk on axis 3, and a comment-summary section with one chunk on
    axis 4. Three sentences: two openers on axes 0 and 3, one non-opener."""
    conn.execute("INSERT INTO doc_documents (document_id, title, source_file, sha256,"
                 " n_chars, ingested_at) VALUES (1, 'A document', 'doc.md', 'x', 100, 't')")
    conn.executemany(
        "INSERT INTO doc_sections (section_id, document_id, ordinal, heading_path, kind,"
        " start_char, end_char, section_text) VALUES (?,1,?,?,?,0,10,'s')",
        [(1, 0, '["Body"]', "body"), (2, 1, '["Letter 1"]', "letter"),
         (3, 2, '["Appendix 3 - Notice of Intent Comment Summary", "Air"]', "body")])
    chunks = [(10, 1, 0, axis(0)), (11, 1, 1, axis(1)), (12, 1, 2, axis(2)),
              (13, 2, 0, axis(3)), (14, 3, 0, axis(4))]
    for cid, sec, i, _v in chunks:
        conn.execute("INSERT INTO doc_chunks (chunk_id, section_id, chunk_index, chunk_text,"
                     " start_char, end_char, max_chunk_size, chunk_overlap)"
                     " VALUES (?,?,?,?,0,10,600,100)", (cid, sec, i, f"chunk {cid}"))
        conn.execute("INSERT INTO doc_chunk_embeddings (chunk_id, embedding, embedding_model,"
                     " embedding_dimensions, created_at) VALUES (?,?,?,?, 't')",
                     (cid, pack(_v), MODEL, embeddings.DIMENSIONS))
    sentences = [("k-open-0", axis(0, lean=0.2), 1), ("k-open-3", axis(3), 1),
                 ("k-closed", axis(1), 0)]
    for key, v, opens in sentences:
        conn.execute("INSERT INTO gate_sentence (text_key, text, occurrences, comments, law,"
                     " evid, gap, alt, opens, holds_hit) VALUES (?,?,1,1,0,1,0,0,?,0)",
                     (key, f"sentence {key}", opens))
        conn.execute("INSERT INTO sentence_embedding (text_key, model, instruction,"
                     " input_sha256, dimensions, vector, created_at) VALUES (?,?,?,'x',?,?,'t')",
                     (key, model, VIEWS["comment"], embeddings.DIMENSIONS, pack(v)))
    conn.commit()


def test_discover_model(dbfile):
    with pytest.raises(SystemExit, match="no model has both"):
        retrieve.discover_model(dbfile)
    seed(dbfile)
    assert retrieve.discover_model(dbfile) == MODEL


def test_nearest_order_and_section_exclusion(dbfile):
    seed(dbfile)
    keys, Q = retrieve.sentence_matrix(dbfile, MODEL)
    assert keys == ["k-open-0", "k-open-3"]       # the non-opener is not retrieved for
    chunk_ids, C, excluded_ids = retrieve.chunk_matrix(dbfile, MODEL, excluded=False)
    assert chunk_ids == [10, 11, 12] and excluded_ids == set()
    idx, cos = retrieve.nearest(Q, C, k=2)
    n = retrieve.write(dbfile, MODEL, keys, chunk_ids, idx, cos)
    assert n == 4
    rows = dbfile.execute("SELECT text_key, rank, chunk_id, cosine FROM doc_retrieval"
                          " ORDER BY text_key, rank").fetchall()
    # the axis-0 opener leans toward axis 1: chunk 10 first, 11 second
    assert [(r[0], r[1], r[2]) for r in rows[:2]] == [("k-open-0", 1, 10), ("k-open-0", 2, 11)]
    assert rows[0][3] > 0.97 and rows[0][3] > rows[1][3]
    # the axis-3 opener matches only the excluded letter chunk: its best is weak
    assert rows[2][0] == "k-open-3" and rows[2][3] < 0.1
    # a second run replaces the model's rows
    retrieve.write(dbfile, MODEL, keys, chunk_ids, idx, cos)
    assert dbfile.execute("SELECT count(*) FROM doc_retrieval").fetchone()[0] == 4


def test_excluded_scope_includes_letters_and_comment_summaries(dbfile):
    seed(dbfile)
    chunk_ids, C, excluded_ids = retrieve.chunk_matrix(dbfile, MODEL, excluded=True)
    assert chunk_ids == [10, 11, 12, 13, 14] and excluded_ids == {13, 14}
    keys, Q = retrieve.sentence_matrix(dbfile, MODEL)
    idx, _ = retrieve.nearest(Q, C, k=1)
    first = [chunk_ids[idx[i, 0]] for i in range(len(keys))]
    assert first == [10, 13]                      # the axis-3 opener takes the letter first


def test_missing_vector_stops(dbfile):
    seed(dbfile)
    dbfile.execute("DELETE FROM sentence_embedding WHERE text_key = 'k-open-3'")
    with pytest.raises(SystemExit, match="no comment-view vector"):
        retrieve.sentence_matrix(dbfile, MODEL)
    dbfile.execute("DELETE FROM doc_chunk_embeddings WHERE chunk_id = 11")
    with pytest.raises(SystemExit, match="no vector under"):
        retrieve.chunk_matrix(dbfile, MODEL, excluded=False)
