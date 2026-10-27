#!/usr/bin/env python3
"""Natural-language inference over the retrieved pairs, then the labels.

    uv run python scripts/docindex/nli.py [--threshold 0.75] [--nli-model M] [--batch 32]
                                          [--limit N] [--labels-only] [--dry-run]
    make nli [THRESHOLD=0.75] [LIMIT=N] [LABELS=1] [DRY=1]

For every doc_retrieval pair at or above the similarity threshold, the
cross-encoder reads the chunk as the premise and the sentence as the hypothesis
and gives the three probabilities, stored in doc_nli. A pair with a row for the
NLI model is not read again, so the run resumes. The model runs locally
(dependency group nli: uv sync --group nli); the first run downloads it.

Then the labels, rebuilt whole from doc_retrieval and doc_nli:

  per sentence (doc_sentence_label)
    contested      a pair at or above the threshold reads contradiction (p >= 0.7)
    addressed      no contradiction; a pair reads entailment
    near           pairs at or above the threshold, none decisive
    not_addressed  no pair at or above the threshold
  per comment (doc_comment_label)
    the strongest label over its gate-opening sentences, in the order
    contested, not_addressed, near, addressed

--labels-only rebuilds the two label tables and reads no pair.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[2]))
sys.path.insert(0, str(_HERE.parents[1]))

from shared import db  # noqa: E402
from docindex import ingest_documents as ing  # noqa: E402
from docindex.retrieve import discover_model  # noqa: E402

NLI_MODEL = "MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli"
# The cosine at or above which a retrieved pair is read; test 1 of the method
# sets the final value.
THRESHOLD = 0.75
# The probability at or above which a pair's reading is entailment or
# contradiction; below it on both, the pair is neutral.
DECISIVE = 0.7
# Pairs per forward pass.
BATCH = 32
# Tokens the pair is cut to; a 600-character chunk and a sentence fit well under.
MAX_TOKENS = 512
# The comment's label is the strongest over its sentences, in this order.
ORDER = ["contested", "not_addressed", "near", "addressed"]


def label_order(id2label: dict) -> tuple[int, int, int]:
    """(entailment, neutral, contradiction) as indexes into the model's output,
    from its own config; a model whose labels are not these three names stops."""
    names = {str(v).lower(): int(k) for k, v in id2label.items()}
    want = ("entailment", "neutral", "contradiction")
    if set(names) != set(want):
        raise SystemExit(f"the NLI model's labels are {sorted(names)}, not {list(want)}:"
                         " name a three-way NLI model with --nli-model")
    return tuple(names[w] for w in want)


def queue(conn, nli_model: str, threshold: float) -> list[tuple[str, int, str, str]]:
    """(text_key, chunk_id, premise, hypothesis) of every pair at or above the
    threshold with no doc_nli row for the model. The premise is the chunk as the
    embedder saw it (ingest_documents.embed_text)."""
    rows = conn.execute(
        "SELECT DISTINCT r.text_key, r.chunk_id, d.source_file, c.chunk_text, s.text"
        " FROM doc_retrieval r"
        " JOIN gate_sentence s ON s.text_key = r.text_key"
        " JOIN doc_chunks c ON c.chunk_id = r.chunk_id"
        " JOIN doc_sections sec USING (section_id)"
        " JOIN doc_documents d USING (document_id)"
        " WHERE r.cosine >= ? AND NOT EXISTS (SELECT 1 FROM doc_nli n"
        "  WHERE n.text_key = r.text_key AND n.chunk_id = r.chunk_id AND n.nli_model = ?)"
        " ORDER BY r.text_key, r.chunk_id", (threshold, nli_model)).fetchall()
    return [(k, cid, ing.embed_text(f, chunk), text) for k, cid, f, chunk, text in rows]


def read_pairs(conn, pairs, nli_model: str, batch_size: int) -> int:
    """The cross-encoder over the pairs, written per batch, so the run resumes."""
    try:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
    except ImportError:
        raise SystemExit("the NLI dependencies are not installed: uv sync --group nli")
    device = ("mps" if torch.backends.mps.is_available()
              else "cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(nli_model)
    model = AutoModelForSequenceClassification.from_pretrained(nli_model).to(device).eval()
    i_ent, i_neu, i_con = label_order(model.config.id2label)
    print(f"model {nli_model} on {device}", flush=True)
    done = 0
    for a in range(0, len(pairs), batch_size):
        chunk = pairs[a:a + batch_size]
        enc = tokenizer([p[2] for p in chunk], [p[3] for p in chunk], truncation=True,
                        max_length=MAX_TOKENS, padding=True, return_tensors="pt").to(device)
        with torch.no_grad():
            probs = torch.softmax(model(**enc).logits, dim=1).cpu().numpy()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        conn.executemany(
            "INSERT INTO doc_nli (text_key, chunk_id, nli_model, p_entailment, p_neutral,"
            " p_contradiction, created_at) VALUES (?,?,?,?,?,?,?)",
            [(k, cid, nli_model, float(p[i_ent]), float(p[i_neu]), float(p[i_con]), now)
             for (k, cid, _, _), p in zip(chunk, probs)])
        conn.commit()
        done += len(chunk)
        print(f"  {done:,} of {len(pairs):,} pairs read", flush=True)
    return done


def sentence_label(rows: list[tuple[int, float, float | None, float | None, float | None]],
                   threshold: float):
    """(label, chunk_id, cosine, p_ent, p_neu, p_con) from one sentence's retrieved
    rows (chunk_id, cosine, and the three probabilities, None for an unread pair).
    Contradiction outranks entailment, as the comment order does."""
    above = [r for r in rows if r[1] >= threshold]
    if not above:
        top = max(rows, key=lambda r: r[1])
        return ("not_addressed", None, top[1], None, None, None)
    read = [r for r in above if r[2] is not None]
    if len(read) != len(above):
        raise SystemExit(f"{len(above) - len(read)} pairs at or above the threshold are"
                         " unread: run make nli without LABELS=1")
    contested = [r for r in read if r[4] >= DECISIVE]
    if contested:
        c, cos, pe, pn, pc = max(contested, key=lambda r: (r[4], r[1], -r[0]))
        return ("contested", c, cos, pe, pn, pc)
    entailed = [r for r in read if r[2] >= DECISIVE]
    if entailed:
        c, cos, pe, pn, pc = max(entailed, key=lambda r: (r[2], r[1], -r[0]))
        return ("addressed", c, cos, pe, pn, pc)
    c, cos, pe, pn, pc = max(read, key=lambda r: (r[1], -r[0]))
    return ("near", c, cos, pe, pn, pc)


def labels(conn, embedding_model: str, nli_model: str, threshold: float) -> tuple[int, int]:
    """Both label tables rebuilt whole for the two models."""
    by_key = {}
    for key, cid, cos, pe, pn, pc in conn.execute(
            "SELECT r.text_key, r.chunk_id, r.cosine, n.p_entailment, n.p_neutral,"
            " n.p_contradiction FROM doc_retrieval r LEFT JOIN doc_nli n"
            " ON n.text_key = r.text_key AND n.chunk_id = r.chunk_id AND n.nli_model = ?"
            " WHERE r.embedding_model = ?", (nli_model, embedding_model)):
        by_key.setdefault(key, []).append((cid, cos, pe, pn, pc))
    if not by_key:
        raise SystemExit("doc_retrieval is empty for the model: run make retrieve first")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute("DELETE FROM doc_sentence_label WHERE embedding_model = ? AND nli_model = ?",
                 (embedding_model, nli_model))
    sent = {key: sentence_label(rows, threshold) for key, rows in sorted(by_key.items())}
    conn.executemany(
        "INSERT INTO doc_sentence_label (text_key, embedding_model, nli_model, label,"
        " chunk_id, cosine, p_entailment, p_neutral, p_contradiction, threshold, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [(key, embedding_model, nli_model, *row, threshold, now) for key, row in sent.items()])
    rank = {lab: i for i, lab in enumerate(ORDER)}
    comments = {}
    for cid, key in conn.execute(
            "SELECT comment_id, text_key FROM gate_sentence_occurrence WHERE opens = 1"
            " ORDER BY comment_id, text_key"):
        if key not in sent:
            continue
        pick = (rank[sent[key][0]], key)
        if cid not in comments or pick < comments[cid]:
            comments[cid] = pick
    conn.execute("DELETE FROM doc_comment_label WHERE embedding_model = ? AND nli_model = ?",
                 (embedding_model, nli_model))
    conn.executemany(
        "INSERT INTO doc_comment_label (comment_id, embedding_model, nli_model, label,"
        " text_key, created_at) VALUES (?,?,?,?,?,?)",
        [(cid, embedding_model, nli_model, ORDER[r], key, now)
         for cid, (r, key) in sorted(comments.items())])
    conn.commit()
    return len(sent), len(comments)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--threshold", type=float, default=THRESHOLD,
                    help="the cosine at or above which a pair is read")
    ap.add_argument("--nli-model", default=NLI_MODEL)
    ap.add_argument("--model", help="the embedding model; discovered when only one fits")
    ap.add_argument("--batch", type=int, default=BATCH, help="pairs per forward pass")
    ap.add_argument("--limit", type=int, default=0, help="read at most this many pairs (a pilot)")
    ap.add_argument("--labels-only", action="store_true",
                    help="rebuild the label tables; read no pair")
    ap.add_argument("--dry-run", action="store_true", help="count what would run; write nothing")
    args = ap.parse_args(argv)
    conn = db.connect(db.DB_PATH)
    embedding_model = args.model or discover_model(conn)
    if not args.labels_only:
        pairs = queue(conn, args.nli_model, args.threshold)
        todo = pairs[:args.limit] if args.limit else pairs
        print(f"make nli: {len(todo):,} pairs to read at threshold {args.threshold}"
              + (f" (--limit {args.limit})" if args.limit else ""), flush=True)
        if args.dry_run:
            conn.close()
            print("nothing read")
            return 0
        if todo:
            read_pairs(conn, todo, args.nli_model, args.batch)
        if args.limit and len(pairs) > len(todo):
            conn.close()
            print(f"pilot done: {len(pairs) - len(todo):,} pairs remain; the labels wait"
                  " for the full run")
            return 0
    elif args.dry_run:
        conn.close()
        print("nothing written")
        return 0
    n_sent, n_com = labels(conn, embedding_model, args.nli_model, args.threshold)
    for lab, n in conn.execute(
            "SELECT label, count(*) FROM doc_comment_label WHERE embedding_model = ?"
            " AND nli_model = ? GROUP BY label ORDER BY count(*) DESC",
            (embedding_model, args.nli_model)):
        print(f"  {lab}: {n:,} comments")
    print(f"done: {n_sent:,} sentence labels, {n_com:,} comment labels")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
