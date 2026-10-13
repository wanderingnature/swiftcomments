#!/usr/bin/env python3
"""Model-free scoring, fully parallel to v3: the rules' reading of every class A
comment, no model call. Step 6, beside make score.

    uv run python scripts/model_free/run.py score [--limit N] [--comment-id ID ...] [--ids-file F] [--json DIR]
    uv run python scripts/model_free/run.py report
    uv run python scripts/model_free/run.py text "comment text ..."    # score ad-hoc text, print JSON
    make score-rules [LIMIT=N] [JSON=dir]

`score` reads the class A comments of the screen from data/roadless.sqlite,
scores every one that has no comment score under the current rule set
version, whole (the comment's full stored text is the one unit the rules run
over), and writes its mf_* tables in one transaction. A second run on the same
inputs writes nothing. `--json DIR` also writes one file per comment in the
shape of shared/score_json.py, for scripts/compare_scores.py.

The whole-comment mode is the only one and --mode is gone; the store is the repository's file;
the git hash is not stamped.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve()
sys.path.insert(0, str(_HERE.parents[1]))
sys.path.insert(0, str(_HERE.parents[2]))

from model_free import RULESET_VERSION  # noqa: E402
from model_free.arithmetic import Answerability, CommentScore, rate, roll_up  # noqa: E402
from model_free.detectors import Context, SentenceInput, SentenceScore, score_sentence  # noqa: E402
from model_free.nlp import parse_many  # noqa: E402
from model_free.store import Store  # noqa: E402
from model_free.text import normalize, split_sentences, text_key  # noqa: E402
from shared import score_json  # noqa: E402

INSTRUMENT = f"rules-{RULESET_VERSION}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------ ad-hoc text

def score_text(comment_id: str, text: str, ctx: Context) -> tuple[list[SentenceScore], object, object]:
    """Split raw text, score each sentence, roll up. For the instrument's
    examples and ad-hoc checks; production reads the comment whole."""
    norm = normalize(text)
    spans = split_sentences(norm)
    inputs = [SentenceInput(i + 1, comment_id, s, e, norm[s:e], text_key(norm[s:e]))
              for i, (s, e) in enumerate(spans)]
    docs = list(parse_many([u.text for u in inputs]))
    scores = [score_sentence(u, d, ctx) for u, d in zip(inputs, docs)]
    comment = roll_up(comment_id, scores)
    return scores, comment, rate(comment)


def cmd_text(args: argparse.Namespace) -> int:
    scores, comment, answer = score_text("adhoc", args.text, Context())
    print(json.dumps({
        "sentences": [{"unit_id": s.unit_id, "start": s.start_char, "end": s.end_char, "dims": s.dims,
                       "evid_applied": s.evid_applied, "ask_names": s.ask_names,
                       "alt_distinct": s.alt_distinct, "stand_this_place": s.stand_this_place,
                       "anchors": s.anchors, "moves": s.moves, "targets": s.targets,
                       "hits": [h.__dict__ for h in s.hits]} for s in scores],
        "comment": comment.__dict__, "answerability": answer.__dict__}, indent=2, default=str))
    return 0


# ------------------------------------------------------------------ score

def json_record(comment: CommentScore, answer: Answerability, sentences: list[SentenceScore]) -> dict:
    """The comment's reading in the shape shared with the model's (shared/score_json.py)."""
    return {
        "comment_id": comment.comment_id, "scorer": "rules", "instrument": INSTRUMENT, "model": None,
        "levels": dict(comment.dims), "strength": comment.strength, "gate": bool(comment.gate),
        "gate_basis": comment.gate_basis, "band": comment.band, "a_level": answer.level,
        "evidence": [{"dimension": h.dimension, "grade": h.grade, "rule": h.rule, "match": h.match,
                      "start": h.start, "end": h.end} for s in sentences for h in s.hits],
    }


def cmd_score(args: argparse.Namespace) -> int:
    from model_free import inputs as db

    conn = db.connect()
    store = Store(conn)
    t0 = time.time()
    all_ids = db.comment_ids(conn)
    done = store.scored_comment_ids(RULESET_VERSION)
    if args.comment_id or args.ids_file:
        wanted = set(args.comment_id or [])
        if args.ids_file:
            wanted |= {line.strip() for line in Path(args.ids_file).read_text().splitlines() if line.strip()}
    else:
        wanted = {c for c in all_ids if c not in done}
        if args.limit:
            wanted = set(sorted(wanted)[:args.limit])
    json_dir = Path(args.json) if args.json else None
    print(f"make score-rules: {len(all_ids):,} class A comments; {len(done):,} scored under rule set"
          f" {RULESET_VERSION}; {len(wanted):,} to score, whole, no model call"
          + (f" (--limit {args.limit})" if args.limit and not (args.comment_id or args.ids_file) else "")
          + "; writes mf_sentence_score, mf_sentence_hit, mf_comment_score, mf_comment_answerability,"
            " one mf_score_run row"
          + (f"; one JSON file per comment under {json_dir}" if json_dir else ""), flush=True)
    if not wanted:
        print("nothing to score")
        return 0
    log("loading the tags and the authority keys")
    tags = db.load_tags(conn)
    authority_keys = db.load_authority_keys(conn)
    log(f"inputs loaded in {time.time() - t0:.0f}s; parsing with spaCy en_core_web_md")

    units = 0
    comments = 0
    counts: dict[str, int] = {}
    with conn.transaction():
        run_id = store.start_run(RULESET_VERSION, now())
        for u in db.iter_comments(conn, wanted):
            ctx = Context(authority_keys=authority_keys,
                          citations=tags.citations.get(u.comment_id, []),
                          authorities=tags.authorities.get(u.comment_id, []))
            sentences = [score_sentence(u, d, ctx) for d in parse_many([u.text])]
            units += store.write_sentences(RULESET_VERSION, run_id, sentences)
            comment = roll_up(u.comment_id, sentences)
            answer = rate(comment)
            store.write_comments(RULESET_VERSION, run_id, [(comment, answer)])
            if json_dir is not None:
                score_json.write(json_dir, json_record(comment, answer, sentences))
            comments += 1
            for s in sentences:
                for h in s.hits:
                    counts[h.rule] = counts.get(h.rule, 0) + 1
            if comments % 500 == 0:
                log(f"{comments:,} of {len(wanted):,} comments, {time.time() - t0:.0f}s")
        store.finish_run(run_id, now(), units, comments, counts, {"ruleset_version": RULESET_VERSION})
    rep = store.report(RULESET_VERSION)
    print(f"done: {comments:,} comments scored in {time.time() - t0:.0f}s; run {run_id};"
          f" {rep['comments']:,} comment scores under rule set {RULESET_VERSION},"
          f" gate open on {rep['comment_gate_open']:,}; by band {rep['comment_band']};"
          f" answerability {rep['answerability']}")
    conn.close()
    return 0


# ----------------------------------------------------------------- report

def cmd_report(args: argparse.Namespace) -> int:
    from model_free import inputs as db

    conn = db.connect()
    rep = Store(conn).report(RULESET_VERSION)
    conn.close()
    print(json.dumps(rep, indent=2, default=str))
    return 0


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score")
    s.add_argument("--limit", type=int, default=0, help="score at most this many unscored comments")
    s.add_argument("--comment-id", action="append", help="score these comments (repeatable)")
    s.add_argument("--ids-file", help="score the comment ids listed one per line in this file")
    s.add_argument("--json", metavar="DIR", help="also write one JSON file per comment under DIR")
    s.set_defaults(fn=cmd_score)
    r = sub.add_parser("report")
    r.set_defaults(fn=cmd_report)
    t = sub.add_parser("text")
    t.add_argument("text")
    t.set_defaults(fn=cmd_text)
    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
