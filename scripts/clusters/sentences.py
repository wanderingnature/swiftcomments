#!/usr/bin/env python3
"""The sentences of the gate set: step 10, the input of the clusters and topics.

    uv run python scripts/clusters/sentences.py [--classes A,B1]
    make sentences [CLASSES=A,B1]

The gate set is the comments whose hybrid gate the model-free reading opens
(mf_comment_score, the current rule set) in the screen classes asked for: A and
B1 by default, the operator's decision of 2026-10-20. For each of their
sentences (the sentence rows of mf_sentence_score) the step writes an
occurrence row: the comment, which of LAW, EVID, GAP and ALT the sentence
reaches 2 on, whether it opens the gate alone, and whether it holds a gate hit
of the whole comment. Then one row for each distinct sentence (the text_key):
its text, its occurrences and comments, and the same flags over its
occurrences.

A whole-comment gate hit is a hit of the whole-comment unit, at 2 or more, on
a dimension the comment's gate basis takes from the whole comment (the hybrid
takes every dimension but GAP from it, and GAP when the whole comment's is the
lower). Its span is in the normalised comment text; a sentence's span is in
the stored text. The two are joined on the letters and digits alone: each
sentence's letters and digits are found in the whole comment's, in order, and
a hit falls in the sentences whose letters and digits it overlaps. A sentence
not found there, and a hit in no found sentence, are counted, not guessed.

The sentence text is the comment-sentences package's rendering, split again
from the stored text as make score-model-free split it; a sentence whose
text_key differs from the scored row's stops the step (the text changed since
it was scored).

A build replaces gate_sentence_occurrence and gate_sentence and adds one
gate_sentence_run row with the counts. No model call.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))
sys.path.insert(0, str(_HERE.parents[2]))

from shared import db  # noqa: E402
from model_free import RULESET_VERSION  # noqa: E402
from model_free.inputs import comment_units  # noqa: E402

KINDS = ("LAW", "EVID", "GAP", "ALT")


def alnum(text: str) -> tuple[str, list[int]]:
    """The text's letters and digits, lower-cased, and the offset of each in the text."""
    pos = [i for i, ch in enumerate(text) if ch.isalnum()]
    return "".join(text[i].lower()[0] for i in pos), pos


def locate(whole: str, sentences: list[str]) -> list[tuple[int, int] | None]:
    """Each sentence's span in the whole text, found on letters and digits, in
    order; None for a sentence not found after the one before it."""
    wkey, wpos = alnum(whole)
    out: list[tuple[int, int] | None] = []
    cursor = 0
    for s in sentences:
        skey, _ = alnum(s)
        k = wkey.find(skey, cursor) if skey else -1
        if k < 0:
            out.append(None)
            continue
        out.append((wpos[k], wpos[k + len(skey) - 1] + 1))
        cursor = k + len(skey)
    return out


def gate_comments(conn, classes: tuple[str, ...]) -> list[str]:
    marks = ",".join("?" * len(classes))
    return [r[0] for r in conn.execute(
        "SELECT m.comment_id FROM mf_comment_score m JOIN substance_screen s USING (comment_id)"
        f" WHERE m.ruleset_version = ? AND m.gate = 1 AND s.screen_class IN ({marks})"
        " ORDER BY m.comment_id", (RULESET_VERSION, *classes))]


def class_counts(conn, classes: tuple[str, ...]) -> list[tuple]:
    marks = ",".join("?" * len(classes))
    return [tuple(r) for r in conn.execute(
        "SELECT s.screen_class, count(*), count(m.comment_id), coalesce(sum(m.gate), 0)"
        " FROM substance_screen s LEFT JOIN mf_comment_score m"
        "   ON m.comment_id = s.comment_id AND m.ruleset_version = ?"
        f" WHERE s.screen_class IN ({marks}) GROUP BY s.screen_class ORDER BY s.screen_class",
        (RULESET_VERSION, *classes))]


def comment_rows(conn, cid: str) -> tuple[list[dict], list[tuple[int, int]], dict]:
    """The comment's sentences (with their text and flags), its whole-comment
    gate hits, and its counts of what could not be located."""
    row = conn.execute("SELECT rowid, comment_text FROM comment WHERE comment_id = ?", (cid,)).fetchone()
    if row is None or not row[1]:
        raise SystemExit(f"{cid}: no stored text in comment")
    units = comment_units(int(row[0]), cid, row[1])
    if units is None:
        raise SystemExit(f"{cid}: scored, but its stored text now gives no sentence; run make score-model-free again")
    split, whole = units
    by_id = {u.unit_id: u for u in split}
    scored = conn.execute(
        "SELECT unit_id, text_key, law, evid, gap, alt, gate FROM mf_sentence_score"
        " WHERE ruleset_version = ? AND comment_id = ? AND unit_id > 0 ORDER BY unit_id",
        (RULESET_VERSION, cid)).fetchall()
    sentences = []
    for r in scored:
        u = by_id.get(r["unit_id"])
        if u is None or u.text_key != r["text_key"]:
            raise SystemExit(f"{cid}: sentence {r['unit_id']} is not the sentence that was scored;"
                             " the text changed since make score-model-free read it")
        sentences.append({"unit_id": r["unit_id"], "text_key": r["text_key"], "text": u.text,
                          "law": int(r["law"] >= 2), "evid": int(r["evid"] >= 2),
                          "gap": int(r["gap"] >= 2), "alt": int(r["alt"] >= 2),
                          "opens": int(r["gate"]), "holds_hit": 0})
    basis = json.loads(conn.execute(
        "SELECT gate_basis FROM mf_comment_score WHERE ruleset_version = ? AND comment_id = ?",
        (RULESET_VERSION, cid)).fetchone()[0])
    whole_dims = [b["dimension"] for b in basis if b["unit_id"] < 0]
    hits: list[tuple[int, int]] = []
    if whole_dims:
        marks = ",".join("?" * len(whole_dims))
        hits = [(h[0], h[1]) for h in conn.execute(
            "SELECT start_char, end_char FROM mf_sentence_hit WHERE ruleset_version = ? AND unit_id = ?"
            f" AND grade >= 2 AND dimension IN ({marks}) ORDER BY start_char",
            (RULESET_VERSION, whole.unit_id, *whole_dims))]
    spans = locate(whole.text, [s["text"] for s in sentences])
    missed = {"sentences_unlocated": sum(1 for sp in spans if sp is None), "hits_unlocated": 0}
    for hs, he in hits:
        holders = [s for s, sp in zip(sentences, spans) if sp is not None and sp[0] < he and hs < sp[1]]
        for s in holders:
            s["holds_hit"] = 1
        if not holders:
            missed["hits_unlocated"] += 1
    return sentences, hits, missed


def build(conn, classes: tuple[str, ...]) -> dict:
    """Write the occurrences, the distinct sentences and the run row; return the counts."""
    if not conn.execute("SELECT 1 FROM mf_comment_score WHERE ruleset_version = ? LIMIT 1",
                        (RULESET_VERSION,)).fetchone():
        raise SystemExit(f"mf_comment_score holds no score under rule set {RULESET_VERSION}:"
                         " run make score-model-free first")
    ids = gate_comments(conn, classes)
    if not ids:
        raise SystemExit(f"no class {'/'.join(classes)} comment has an open model-free gate")
    occ_rows: list[tuple] = []
    counts = {"gate_comments": len(ids), "comments_opening": 0, "comments_hit": 0, "comments_neither": 0,
              "sentences_unlocated": 0, "hits_unlocated": 0}
    for cid in ids:
        sentences, _hits, missed = comment_rows(conn, cid)
        counts["sentences_unlocated"] += missed["sentences_unlocated"]
        counts["hits_unlocated"] += missed["hits_unlocated"]
        opening = any(s["opens"] for s in sentences)
        held = any(s["holds_hit"] for s in sentences)
        counts["comments_opening"] += int(opening)
        counts["comments_hit"] += int(held)
        counts["comments_neither"] += int(not opening and not held)
        occ_rows += [(s["unit_id"], s["text_key"], cid, s["law"], s["evid"], s["gap"], s["alt"],
                      s["opens"], s["holds_hit"], s["text"]) for s in sentences]
    distinct: dict[str, dict] = {}
    for unit_id, key, cid, law, evid, gap, alt, opens, holds, text in occ_rows:
        d = distinct.setdefault(key, {"text": text, "occurrences": 0, "comments": set(), "law": 0, "evid": 0,
                                      "gap": 0, "alt": 0, "opens": 0, "holds_hit": 0})
        d["text"] = min(d["text"], text)
        d["occurrences"] += 1
        d["comments"].add(cid)
        for col, v in (("law", law), ("evid", evid), ("gap", gap), ("alt", alt), ("opens", opens),
                       ("holds_hit", holds)):
            d[col] = max(d[col], v)
    counts["occurrences"] = len(occ_rows)
    counts["distinct_sentences"] = len(distinct)
    with conn.transaction():
        conn.execute("DELETE FROM gate_sentence_occurrence")
        conn.execute("DELETE FROM gate_sentence")
        conn.executemany("INSERT INTO gate_sentence_occurrence VALUES (?,?,?,?,?,?,?,?,?)",
                         [r[:9] for r in occ_rows])
        conn.executemany("INSERT INTO gate_sentence VALUES (?,?,?,?,?,?,?,?,?,?)",
                         [(k, d["text"], d["occurrences"], len(d["comments"]), d["law"], d["evid"], d["gap"],
                           d["alt"], d["opens"], d["holds_hit"]) for k, d in sorted(distinct.items())])
        cur = conn.execute(
            "INSERT INTO gate_sentence_run (ruleset_version, classes, created_at, gate_comments, occurrences,"
            " distinct_sentences, comments_opening, comments_hit, comments_neither, sentences_unlocated,"
            " hits_unlocated) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (RULESET_VERSION, ",".join(classes), datetime.now(timezone.utc).isoformat(timespec="seconds"),
             counts["gate_comments"], counts["occurrences"], counts["distinct_sentences"],
             counts["comments_opening"], counts["comments_hit"], counts["comments_neither"],
             counts["sentences_unlocated"], counts["hits_unlocated"]))
        counts["run_id"] = int(cur.lastrowid)
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--classes", default="A,B1", help="screen classes, comma-separated (default A,B1)")
    args = ap.parse_args(argv)
    classes = tuple(c.strip() for c in args.classes.split(",") if c.strip())
    conn = db.connect(db.DB_PATH)
    for cls, n, scored, open_ in class_counts(conn, classes):
        print(f"class {cls}: {n:,} comments, {scored:,} with a model-free score under rule set {RULESET_VERSION},"
              f" gate open on {open_:,}")
    c = build(conn, classes)
    conn.close()
    print(f"make sentences: run {c['run_id']}; {c['gate_comments']:,} gate-open comments,"
          f" {c['occurrences']:,} sentences, {c['distinct_sentences']:,} distinct;"
          f" {c['comments_opening']:,} comments with a sentence that opens the gate alone,"
          f" {c['comments_hit']:,} with a sentence that holds a whole-comment gate hit,"
          f" {c['comments_neither']:,} with neither; {c['sentences_unlocated']:,} sentences and"
          f" {c['hits_unlocated']:,} hits not located in the whole comment's text")
    return 0


if __name__ == "__main__":
    sys.exit(main())
