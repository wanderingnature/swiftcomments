#!/usr/bin/env python3
"""Model-free scoring, fully parallel to v3: the rules' reading of every class A
comment, no model call. Step 6, beside make score-model. --classes reads other
screen classes as well or instead (B1: comments that refer to the action with a
deficiency or a named entity but cite nothing), on the same rules.

    uv run python scripts/model_free/run.py score [--classes A,B1] [--limit N] [--comment-id ID ...] [--ids-file F]
    uv run python scripts/model_free/run.py report
    uv run python scripts/model_free/run.py text [--mode sentence|whole|hybrid] "comment text ..."    # score ad-hoc text, print JSON
    make score-model-free [CLASSES=A,B1] [LIMIT=N]

`score` reads the comments of the screen classes asked for (class A by default)
from data/roadless.sqlite and scores every one that has no comment score under the current rule set version
in hybrid mode: each sentence (split by the comment-sentences package,
stored_units) and the whole comment are scored, and the comment score is the
whole comment's with GAP held to what one sentence reaches
(arithmetic.hybrid). It writes its mf_* tables in one transaction. A second run
on the same inputs writes nothing. A comment the package leaves no sentence
(every piece under 25 letters and digits) is not scored, and the run says how
many.

Ported from the operator's model_free/run.py (eis-analysis): its sentences were
comment_unit's rows, here the same package splits the stored text as it is
read; hybrid is the mode `score` runs, as the operator decided, and --mode
stays on `text`; the store is the repository's file; the git hash is not
stamped.
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
from model_free.arithmetic import Answerability, CommentScore, hybrid, rate, roll_up  # noqa: E402
from model_free.detectors import Context, SentenceInput, SentenceScore, score_sentence  # noqa: E402
from model_free.nlp import parse_many  # noqa: E402
from model_free.store import Store  # noqa: E402
from model_free.text import normalize, text_key  # noqa: E402
from comment_sentences import stored_units  # noqa: E402

INSTRUMENT = f"rules-{RULESET_VERSION}"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------ ad-hoc text

def score_text(comment_id: str, text: str, ctx: Context,
               mode: str = "sentence") -> tuple[list[SentenceScore], object, object]:
    """Score raw comment text in the given mode (sentence, whole or hybrid,
    as `score`; the whole-comment unit is id -1), roll up. The sentences are
    split by the one method that writes comment_unit
    (the comment-sentences package, stored_units), so a text scored here is
    split exactly as the same text stored as a comment is."""
    norm = normalize(text)
    sentences: list[SentenceScore] = []
    whole: SentenceScore | None = None
    if mode in ("sentence", "hybrid"):
        inputs = [SentenceInput(i + 1, comment_id, a, b, t, text_key(t))
                  for i, (a, b, t, _) in enumerate(stored_units(text)[0])]
        docs = list(parse_many([u.text for u in inputs]))
        sentences = [score_sentence(u, d, ctx) for u, d in zip(inputs, docs)]
    if mode in ("whole", "hybrid"):
        unit = SentenceInput(-1, comment_id, 0, len(norm), norm, text_key(norm))
        whole = score_sentence(unit, next(iter(parse_many([norm]))), ctx)
    if mode == "sentence":
        scores, comment = sentences, roll_up(comment_id, sentences)
    elif mode == "whole" and whole is not None:
        scores, comment = [whole], roll_up(comment_id, [whole])
    elif mode == "hybrid" and whole is not None:
        scores = sentences + [whole]
        comment = hybrid(roll_up(comment_id, [whole]), roll_up(comment_id, sentences))
    else:
        raise ValueError(f"unknown mode: {mode}")
    return scores, comment, rate(comment)


def cmd_text(args: argparse.Namespace) -> int:
    scores, comment, answer = score_text("adhoc", args.text, Context(), args.mode)
    print(json.dumps({
        "sentences": [{"unit_id": s.unit_id, "start": s.start_char, "end": s.end_char, "dims": s.dims,
                       "evid_applied": s.evid_applied, "ask_names": s.ask_names,
                       "alt_distinct": s.alt_distinct, "stand_this_place": s.stand_this_place,
                       "anchors": s.anchors, "moves": s.moves, "targets": s.targets,
                       "hits": [h.__dict__ for h in s.hits]} for s in scores],
        "comment": comment.__dict__, "answerability": answer.__dict__}, indent=2, default=str))
    return 0


# ------------------------------------------------------------------ score

def json_record(comment: CommentScore, answer: Answerability, units: list[SentenceScore]) -> dict:
    """The comment's reading in the shape shared with the model's (shared/score_json.py).
    The evidence is the hits the hybrid score is taken from: GAP's from the
    sentences, every other dimension's and the moves' from the whole comment
    (arithmetic.hybrid)."""
    return {
        "comment_id": comment.comment_id, "scorer": "rules", "instrument": INSTRUMENT, "model": None,
        "levels": dict(comment.dims), "strength": comment.strength, "gate": bool(comment.gate),
        "gate_basis": comment.gate_basis, "band": comment.band, "a_level": answer.level,
        "evidence": [{"dimension": h.dimension, "grade": h.grade, "rule": h.rule, "match": h.match,
                      "start": h.start, "end": h.end}
                     for s in units for h in s.hits if (h.dimension == "GAP") == (s.unit_id > 0)],
    }


def read_comment(comment_id: str, units: tuple[list[SentenceInput], SentenceInput], tags,
                 authority_keys: list[str]) -> tuple[list[SentenceScore], CommentScore, Answerability]:
    """One comment through the rules in hybrid mode (the operator's
    _hybrid_comments): every sentence and the whole comment scored, the
    comment score arithmetic.hybrid of the two roll-ups. Returns every unit's
    score (the sentences, then the whole comment), the comment score and its
    rating. The score run calls it, and so does make score-model-compare
    (scripts/score_model_compare.py)."""
    sentences_in, whole_in = units
    ctx = Context(authority_keys=authority_keys,
                  citations=tags.citations.get(comment_id, []),
                  authorities=tags.authorities.get(comment_id, []))
    docs = parse_many([u.text for u in sentences_in] + [whole_in.text])
    scored = [score_sentence(u, d, ctx) for u, d in zip(sentences_in + [whole_in], docs)]
    sentences, whole = scored[:-1], scored[-1]
    comment = hybrid(roll_up(comment_id, [whole]), roll_up(comment_id, sentences))
    return scored, comment, rate(comment)


def cmd_score(args: argparse.Namespace) -> int:
    from model_free import inputs as db

    conn = db.connect()
    store = Store(conn)
    t0 = time.time()
    classes = tuple(c.strip() for c in args.classes.split(",") if c.strip())
    all_ids = db.comment_ids(conn, classes)
    done = store.scored_comment_ids(RULESET_VERSION) & set(all_ids)
    if args.comment_id or args.ids_file:
        wanted = set(args.comment_id or [])
        if args.ids_file:
            wanted |= {line.strip() for line in Path(args.ids_file).read_text().splitlines() if line.strip()}
    else:
        wanted = {c for c in all_ids if c not in done}
        if args.limit:
            wanted = set(sorted(wanted)[:args.limit])
    print(f"make score-model-free: {len(all_ids):,} class {'/'.join(classes)} comments; {len(done):,} scored"
          f" under rule set"
          f" {RULESET_VERSION}; {len(wanted):,} to score in hybrid mode (each sentence and the whole"
          f" comment), no model call"
          + (f" (--limit {args.limit})" if args.limit and not (args.comment_id or args.ids_file) else "")
          + "; writes mf_sentence_score, mf_sentence_hit, mf_comment_score, mf_comment_answerability,"
            " one mf_score_run row", flush=True)
    if not wanted:
        print("nothing to score")
        return 0
    log("loading the tags and the authority keys")
    tags = db.load_tags(conn)
    authority_keys = db.load_authority_keys(conn)
    log(f"inputs loaded in {time.time() - t0:.0f}s; parsing with spaCy en_core_web_md")

    units = 0
    comments = 0
    no_sentence = 0
    counts: dict[str, int] = {}
    with conn.transaction():
        run_id = store.start_run(RULESET_VERSION, now())
        for cid, comment_units in db.iter_comments(conn, wanted):
            if comment_units is None:
                no_sentence += 1
                continue
            sentences, comment, answer = read_comment(cid, comment_units, tags, authority_keys)
            units += store.write_sentences(RULESET_VERSION, run_id, sentences)
            store.write_comments(RULESET_VERSION, run_id, [(comment, answer)])
            comments += 1
            for s in sentences:
                for h in s.hits:
                    counts[h.rule] = counts.get(h.rule, 0) + 1
            if comments % 500 == 0:
                log(f"{comments:,} of {len(wanted):,} comments, {time.time() - t0:.0f}s")
        store.finish_run(run_id, now(), units, comments, counts, {"ruleset_version": RULESET_VERSION})
    rep = store.report(RULESET_VERSION)
    print(f"done: {comments:,} comments scored in {time.time() - t0:.0f}s, {units:,} units (sentences and"
          f" whole comments); {no_sentence:,} not scored, no sentence of 25 or more letters and digits; run {run_id};"
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
    s.add_argument("--classes", default="A",
                   help="screen classes to score, comma-separated, e.g. A,B1 (default A)")
    s.add_argument("--limit", type=int, default=0, help="score at most this many unscored comments")
    s.add_argument("--comment-id", action="append", help="score these comments (repeatable)")
    s.add_argument("--ids-file", help="score the comment ids listed one per line in this file")
    s.set_defaults(fn=cmd_score)
    r = sub.add_parser("report")
    r.set_defaults(fn=cmd_report)
    t = sub.add_parser("text")
    t.add_argument("text")
    t.add_argument("--mode", choices=("sentence", "whole", "hybrid"), default="sentence")
    t.set_defaults(fn=cmd_text)
    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
