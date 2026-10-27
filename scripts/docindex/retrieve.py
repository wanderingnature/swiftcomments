#!/usr/bin/env python3
"""The record retrieval: the K nearest record chunks for each gate-opening sentence.

    uv run python scripts/docindex/retrieve.py [--model M] [--k 5] [--excluded] [--dry-run]
    make retrieve [MODEL=...] [K=5] [EXCLUDED=1] [DRY=1]

For every distinct sentence that opens the gate alone (gate_sentence.opens = 1),
the cosine of its comment-view vector (sentence_embedding, under the comment
instruction of make embed) against the vector of every record chunk
(doc_chunk_embeddings), under one embedding model. The K nearest chunks are
stored in doc_retrieval, nearest first; a run replaces the model's rows.

Sections that carry commenters' words instead of the agency's analysis are not
searched: the agency-letters volume (kind letter), and the sections of a
comment-summary or response-to-comments appendix, named by their headings. A
match there is the agency's paraphrase of a comment, not the record addressing
the point. --excluded searches them too, prints how many sentences take an
excluded chunk first, and writes nothing: the figure that justifies the
exclusion.

The embedding model is --model, or is discovered when exactly one model has
both the comment-view sentence vectors and the chunk vectors. A gate-opening
sentence without a vector, or a chunk in scope without one, stops the run.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[2]))
sys.path.insert(0, str(_HERE.parents[1]))

from shared import db  # noqa: E402
from clusters.embed import VIEWS, unpack  # noqa: E402

# The nearest chunks kept per sentence.
K = 5
# Sentence rows per block of the cosine products, as the merge blocks them.
BLOCK = 2048
# A section whose chunks are commenters' words, not the agency's analysis: the
# letters volume, and the appendixes that summarize or respond to comments.
EXCLUDED_SQL = ("(s.kind = 'letter' OR s.heading_path LIKE '%Comment Summary%'"
                " OR s.heading_path LIKE '%Response to Comments%')")


def discover_model(conn) -> str:
    """The one model that has both the comment-view sentence vectors and the
    chunk vectors; more than one needs --model, none stops the run."""
    rows = [r[0] for r in conn.execute(
        "SELECT DISTINCT model FROM sentence_embedding WHERE instruction = ?"
        " INTERSECT SELECT DISTINCT embedding_model FROM doc_chunk_embeddings"
        " ORDER BY 1", (VIEWS["comment"],))]
    if not rows:
        raise SystemExit("no model has both the comment-view sentence vectors and the"
                         " chunk vectors: run make embed VIEW=comment and make docindex")
    if len(rows) > 1:
        raise SystemExit(f"both vector sets exist under {len(rows)} models"
                         f" ({', '.join(rows)}): name one with --model")
    return rows[0]


def unit(m: np.ndarray) -> np.ndarray:
    return m / np.linalg.norm(m, axis=1, keepdims=True)


def sentence_matrix(conn, model: str) -> tuple[list[str], np.ndarray]:
    """(text_keys, unit vectors) of every distinct gate-opening sentence."""
    missing = conn.execute(
        "SELECT count(*) FROM gate_sentence s WHERE s.opens = 1 AND NOT EXISTS"
        " (SELECT 1 FROM sentence_embedding e WHERE e.text_key = s.text_key"
        "  AND e.model = ? AND e.instruction = ?)", (model, VIEWS["comment"])).fetchone()[0]
    if missing:
        raise SystemExit(f"{missing:,} gate-opening sentences have no comment-view vector"
                         f" under {model}: run make embed VIEW=comment")
    rows = conn.execute(
        "SELECT s.text_key, e.vector FROM gate_sentence s JOIN sentence_embedding e"
        " ON e.text_key = s.text_key AND e.model = ? AND e.instruction = ?"
        " WHERE s.opens = 1 ORDER BY s.text_key", (model, VIEWS["comment"])).fetchall()
    if not rows:
        raise SystemExit("no gate-opening sentences: run make sentences first")
    return [r[0] for r in rows], unit(np.stack([unpack(r[1]) for r in rows]))


def chunk_matrix(conn, model: str, excluded: bool) -> tuple[list[int], np.ndarray, set[int]]:
    """(chunk_ids, unit vectors, the ids of excluded-section chunks) of every record
    chunk in scope: the excluded sections only under --excluded."""
    scope = "" if excluded else " AND NOT " + EXCLUDED_SQL
    missing = conn.execute(
        "SELECT count(*) FROM doc_chunks c JOIN doc_sections s USING (section_id)"
        " WHERE NOT EXISTS (SELECT 1 FROM doc_chunk_embeddings e"
        "  WHERE e.chunk_id = c.chunk_id AND e.embedding_model = ?)" + scope,
        (model,)).fetchone()[0]
    if missing:
        raise SystemExit(f"{missing:,} chunks have no vector under {model}: run make docindex")
    rows = conn.execute(
        "SELECT c.chunk_id, e.embedding, " + EXCLUDED_SQL + " FROM doc_chunks c"
        " JOIN doc_sections s USING (section_id)"
        " JOIN doc_chunk_embeddings e ON e.chunk_id = c.chunk_id AND e.embedding_model = ?"
        " WHERE 1 = 1" + scope + " ORDER BY c.chunk_id", (model,)).fetchall()
    if not rows:
        raise SystemExit("no record chunks: run make docindex first")
    return ([r[0] for r in rows], unit(np.stack([unpack(r[1]) for r in rows])),
            {r[0] for r in rows if r[2]})


def nearest(Q: np.ndarray, C: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Per row of Q: the indexes into C of its k nearest rows, nearest first, and
    their cosines. Blocked, as the merge blocks its products."""
    k = min(k, len(C))
    idx = np.empty((len(Q), k), dtype=np.int64)
    cos = np.empty((len(Q), k), dtype=np.float32)
    for a in range(0, len(Q), BLOCK):
        sims = Q[a:a + BLOCK] @ C.T
        part = np.argpartition(-sims, k - 1, axis=1)[:, :k]
        order = np.take_along_axis(sims, part, axis=1).argsort(axis=1)[:, ::-1]
        idx[a:a + len(sims)] = np.take_along_axis(part, order, axis=1)
        cos[a:a + len(sims)] = np.take_along_axis(sims, idx[a:a + len(sims)], axis=1)
    return idx, cos


def write(conn, model: str, keys: list[str], chunk_ids: list[int],
          idx: np.ndarray, cos: np.ndarray) -> int:
    """doc_retrieval rebuilt for the model: the model's rows replaced."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute("DELETE FROM doc_retrieval WHERE embedding_model = ?", (model,))
    conn.executemany(
        "INSERT INTO doc_retrieval (text_key, embedding_model, rank, chunk_id, cosine, created_at)"
        " VALUES (?,?,?,?,?,?)",
        [(key, model, rank + 1, chunk_ids[idx[i, rank]], float(cos[i, rank]), now)
         for i, key in enumerate(keys) for rank in range(idx.shape[1])])
    conn.commit()
    return idx.size


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help="the embedding model; discovered when only one fits")
    ap.add_argument("--k", type=int, default=K, help="nearest chunks kept per sentence")
    ap.add_argument("--excluded", action="store_true",
                    help="search the excluded sections too; print how many sentences take an"
                         " excluded chunk first; write nothing")
    ap.add_argument("--dry-run", action="store_true", help="count what would run; write nothing")
    args = ap.parse_args(argv)
    conn = db.connect(db.DB_PATH)
    model = args.model or discover_model(conn)
    keys, Q = sentence_matrix(conn, model)
    chunk_ids, C, excluded_ids = chunk_matrix(conn, model, args.excluded)
    print(f"make retrieve: {len(keys):,} gate-opening sentences x {len(chunk_ids):,} record"
          f" chunks, {min(args.k, len(chunk_ids))} per sentence, model {model}"
          + (" (excluded sections included)" if args.excluded else ""), flush=True)
    if args.dry_run:
        conn.close()
        print("nothing written")
        return 0
    idx, cos = nearest(Q, C, args.k)
    if args.excluded:
        first = sum(1 for i in range(len(keys)) if chunk_ids[idx[i, 0]] in excluded_ids)
        print(f"{first:,} of {len(keys):,} sentences ({first / len(keys):.1%}) take an"
              " excluded chunk first; nothing written")
        conn.close()
        return 0
    n = write(conn, model, keys, chunk_ids, idx, cos)
    print(f"done: {n:,} pairs written to doc_retrieval under {model}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
