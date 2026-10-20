#!/usr/bin/env python3
"""One vector for each distinct sentence of the gate set: step 11.

    uv run python scripts/clusters/embed.py --view comment|plain|topic [--limit N] [--dry-run]
    make embed VIEW=comment [LIMIT=N]

The view is the instruction the vector is made under. Qwen3-Embedding is
instruction-aware: the same text under two instructions gives two vectors.
The instruction is part of the input, `Instruct: <instruction>\\nQuery:<text>`,
since the endpoint has no instruction field; the plain view sends the text
alone. The three views are eis-analysis's:

    comment  the comment instruction its sentence vectors were made under
    plain    the text alone (its tests 23 to 25)
    topic    "Represent the policy issue or subject this sentence discusses" (its test 20)

Each vector is kept in sentence_embedding with the model, the instruction and
the SHA-256 of the exact input string, so a vector made another way is never
taken for this one. A sentence (text_key) that has a vector for the model and
the instruction is not sent again. Each batch is written as it comes back.

Ported from eis-analysis src/ledger/unit_embed.py (wrap, input_sha256,
embed_into) and scripts/embed_units.py (the comment side): the vectors are in
the file, packed as 1,024 little-endian float32, not pgvector; the server is
the reader's (shared/embeddings.py); the text sent for a sentence is
gate_sentence's.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[2]))
load_dotenv(_HERE.parents[2] / ".env")

from shared import db, embeddings  # noqa: E402

COMMENT_INSTRUCTION = (
    "Given a public comment on a federal rule, retrieve the sentence from the agency's record that "
    "addresses the specific claim the comment makes. A sentence that only states that the rule is "
    "being rescinded or describes the proposed action in general does not address the claim.")
VIEWS = {
    "comment": COMMENT_INSTRUCTION,
    "plain": "",
    "topic": "Represent the policy issue or subject this sentence discusses",
}
CONCURRENCY = 8


def wrap(instruction: str, text: str) -> str:
    """The input string; an empty instruction is the plain text, with no Instruct/Query frame."""
    return f"Instruct: {instruction}\nQuery:{text}" if instruction else text


def input_sha256(instruction: str, text: str) -> str:
    return hashlib.sha256(wrap(instruction, text).encode()).hexdigest()


def pack(vector) -> bytes:
    v = np.asarray(vector, dtype="<f4")
    if v.shape != (embeddings.DIMENSIONS,):
        raise ValueError(f"a vector of {v.shape} where {embeddings.DIMENSIONS} were expected")
    return v.tobytes()


def unpack(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype="<f4")


def queue(conn, model: str, instruction: str) -> list[tuple[str, str]]:
    """(text_key, text) of every distinct sentence with no vector for the model and the instruction."""
    if not conn.execute("SELECT 1 FROM gate_sentence LIMIT 1").fetchone():
        raise SystemExit("gate_sentence is empty: run make sentences first")
    return [(r[0], r[1]) for r in conn.execute(
        "SELECT s.text_key, s.text FROM gate_sentence s WHERE NOT EXISTS (SELECT 1 FROM sentence_embedding e"
        " WHERE e.text_key = s.text_key AND e.model = ? AND e.instruction = ?) ORDER BY s.text_key",
        (model, instruction))]


def write(conn, model: str, instruction: str, items: list[tuple[str, str]], vectors: list) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.executemany(
        "INSERT OR IGNORE INTO sentence_embedding (text_key, model, instruction, input_sha256, dimensions,"
        " vector, created_at) VALUES (?,?,?,?,?,?,?)",
        [(k, model, instruction, input_sha256(instruction, t), embeddings.DIMENSIONS, pack(v), now)
         for (k, t), v in zip(items, vectors)])
    conn.commit()
    return len(items)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--view", choices=sorted(VIEWS), required=True)
    ap.add_argument("--limit", type=int, default=0, help="send at most this many sentences (a pilot)")
    ap.add_argument("--dry-run", action="store_true", help="count what would be sent; send nothing")
    args = ap.parse_args(argv)
    instruction = VIEWS[args.view]
    base, key, model = embeddings.server()
    conn = db.connect(db.DB_PATH)
    missing = queue(conn, model, instruction)
    total = conn.execute("SELECT count(*) FROM gate_sentence").fetchone()[0]
    todo = missing[:args.limit] if args.limit else missing
    chars = sum(len(wrap(instruction, t)) for _, t in todo)
    print(f"make embed: view {args.view}, model {model} at {base}; {total:,} distinct sentences,"
          f" {total - len(missing):,} with a vector; {len(todo):,} to send"
          f" ({chars:,} characters)" + (f" (--limit {args.limit})" if args.limit else ""), flush=True)
    if args.dry_run or not todo:
        conn.close()
        print("nothing sent" if args.dry_run else "nothing to send")
        return 0
    batches = [todo[i:i + embeddings.BATCH] for i in range(0, len(todo), embeddings.BATCH)]
    written = tokens = 0
    with ThreadPoolExecutor(CONCURRENCY) as ex:
        results = ex.map(lambda b: embeddings.embed_batch([wrap(instruction, t) for _, t in b], base, key, model),
                         batches)
        for b, (vecs, tok) in zip(batches, results):
            written += write(conn, model, instruction, b, vecs)
            tokens += tok
            print(f"  {written:,} of {len(todo):,} written", flush=True)
    conn.close()
    print(f"done: {written:,} vectors written under view {args.view}; {tokens:,} input tokens reported")
    return 0


if __name__ == "__main__":
    sys.exit(main())
