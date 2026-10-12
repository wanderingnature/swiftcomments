#!/usr/bin/env python3
"""LLM afterstep — adjudicate bare-word roadless-area mentions.

NOT part of the deterministic tagging pipeline. Single-word area names are excluded
from the match vocabulary (ambiguous English words); this afterstep takes each bare
occurrence as a candidate and asks a model one question — does this comment use the
word to refer to that roadless area? — writing every verdict (yes AND no) to
comment_areas_llm, a table distinct from the deterministic tag tables, with full
provenance: matched word, model, prompt version, and the model's one-line rationale.

The model server and the model come from .env (LLM_BASE_URL, LLM_MODEL),
through the one ChatClient path (shared/llm_client.py).

Usage:
    python scripts/entity_tagging/adjudicate_bare_words.py --project roadless \
        [--limit 50] [--concurrency 4] [--words Security,Johnson]
"""

import argparse
import json
import sys
import threading
from pathlib import Path
from queue import Empty, Queue

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared import db  # noqa: E402
from shared.instrument import model_of  # noqa: E402
from shared.project_context import add_project_argument, context_from_args  # noqa: E402
from shared.llm_client import ChatClient  # noqa: E402
from scripts.entity_tagging.bare_words import (bare_names, build_automaton,  # noqa: E402
                                               collision_names, iter_bare_hits)

sys.path.insert(0, str(REPO_ROOT / "scripts" / "substance"))
from shared_text import norm_key  # noqa: E402  # pyright: ignore[reportMissingImports]

PROMPT_VERSION = "v2"

# One insert, used by both writers — the copied verdicts and the called ones —
# so a copied row is byte-identical in shape to one the model produced.
_VERDICT_INSERT = (
    "INSERT INTO {analysis}.comment_areas_llm"
    " (comment_id, area_name, matched_text, verdict, rationale,"
    "  model, prompt_version)"
    " VALUES (?, ?, ?, ?, ?, ?, ?)"
    " ON CONFLICT DO NOTHING")

SYSTEM_PROMPT = (
    "You adjudicate whether a word in a public comment refers to a specific USFS"
    " inventoried roadless area. Many roadless areas have names that are also"
    " ordinary English words, common proper nouns, or — critically — the name of a"
    " National Forest or mountain range. A National Forest and a roadless area are"
    " DIFFERENT things: a comment about the forest as a whole, or about a mountain"
    " range, does NOT refer to the roadless area, even though the roadless area"
    " lies inside a forest. Answer strictly from the comment's own context. Respond"
    " with refers_to_area (true only when the comment uses the name for that"
    " specific inventoried roadless area or the ground it denotes) and a"
    " one-sentence rationale.")

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "refers_to_area": {"type": "boolean"},
        "rationale": {"type": "string"},
    },
    "required": ["refers_to_area", "rationale"],
    "additionalProperties": False,
}

_PROPAGATE = (
    # A duplicate's verdict IS its original's: same text, same word, same
    # question. Both dedup layers fan out — full-text (original_comment_id) and
    # middle-content (middle_original_id) — because v_truly_unique_comments
    # excludes a comment that is a duplicate under EITHER, so either can be the
    # reason a member was never scanned.
    "INSERT INTO {analysis}.comment_areas_llm"
    " (comment_id, area_name, matched_text, verdict, rationale, model,"
    "  prompt_version)"
    " SELECT d.comment_id, l.area_name, l.matched_text, l.verdict, l.rationale,"
    "        l.model, l.prompt_version"
    "   FROM {analysis}.comment_areas_llm l"
    "   JOIN {analysis}.comment_dedup d"
    "     ON d.comment_id <> l.comment_id"
    "    AND coalesce(d.original_comment_id, d.middle_original_id) IS NOT NULL"
    "    AND l.comment_id IN (d.original_comment_id, d.middle_original_id)"
    "  WHERE l.prompt_version = ?"
    " ON CONFLICT DO NOTHING")


def propagate_to_duplicates(ctx, conn):
    """Give every duplicate its original's verdicts.

    The scan pays for the not-a-duplicate set; this is what keeps the members
    tagged. Idempotent (ON CONFLICT DO NOTHING) and cheap — set-based, no model.
    Returns the rows written.
    """
    with conn.cursor() as cur:
        cur.execute(ctx.render_sql(_PROPAGATE), (PROMPT_VERSION,))
        n = cur.rowcount
    conn.commit()
    return n


def mention_key(name, matched, text):
    """What the model is actually being asked.

    The prompt carries the name, the matched surface text and the comment — and
    nothing else. Two candidates agreeing on all three are the SAME question, so
    the second one buys an answer already in hand. Which comment carried it does
    not enter the decision, so it does not belong in the key.

    norm_key is the house normalizer (shared_text): two strings differing only
    in encoding, markup, case, punctuation or spacing are one mention. Submitters
    paste the same campaign letter through different forms, so byte equality
    misses most of the duplication.
    """
    return (name, norm_key(matched), norm_key(text))


def build_candidates(conn, ctx, words_filter=None):
    """Distinct MENTIONS not yet adjudicated at this prompt_version, each
    carrying every (comment_id, matched_text) pair that shares it.

    Returns [(mention_key, name, matched, text, [(comment_id, matched), ...])] in
    deterministic order: one model call per mention, the verdict written to every
    member.

    Keyed by mention, not by comment. Keying on comment_id asks the identical
    question once per signer of a form letter — 111,074 verdicts stood against
    60,684 distinct mentions (measured 2026-09-15), 45% of every call ever made
    paying for an answer already on hand, 62,809 of them asking whether the word
    "last" is the place "Last". This is the same fix concern_ledger's
    build_adjudicate_queue carries for excerpts.

    Two candidate sources, one lane: bare single-word names are scanned out of
    the raw text (they are excluded from the deterministic vocabulary), while
    COLLISION names (multi-word area names shadowed by a forest or range —
    "White Mountain", "Smoky Mountains") already carry deterministic tags in
    comment_areas; their candidates come from those tags."""
    bare_meta = bare_names(conn, ctx)
    coll_meta = collision_names(conn, ctx)
    names_meta = {**bare_meta, **coll_meta}
    bare = sorted(bare_meta)
    coll = sorted(coll_meta)
    if words_filter:
        wanted = {w.strip().lower() for w in words_filter}
        bare = [n for n in bare if n.lower() in wanted]
        coll = [n for n in coll if n.lower() in wanted]
        if not bare and not coll:
            raise SystemExit(f"--words matched no adjudicable area names: {words_filter}")

    # NOT filtered by model. Whether the word "Last" in this text names the
    # roadless area is a fact about the text; which model read it is provenance,
    # recorded on the row and not part of the question. Keying the done-check on
    # the model made the same corpus report 60,893 pending under the local model
    # and 2,351 under the cloud one, and made switching models discard every
    # verdict already paid for.
    #
    # prompt_version STAYS in the key: a new prompt asks a different question.
    done = {(c, a, m) for c, a, m in conn.execute(ctx.render_sql(
        "SELECT comment_id, area_name, matched_text FROM {analysis}.comment_areas_llm"
        " WHERE prompt_version = ?"), (PROMPT_VERSION,))}

    # Verdicts already decided, keyed by MENTION. Without this the dedup is
    # within-run only: a comment collected today that repeats a campaign letter
    # adjudicated last week has a new comment_id, so it misses `done`, forms a
    # fresh mention and pays for an answer sitting in the table. On a live docket
    # that is the common case, not the edge one.
    decided = {}
    for a, m, t, v, r in conn.execute(ctx.render_sql(
            "SELECT l.area_name, l.matched_text, s.comment_text, l.verdict, l.rationale"
            " FROM {analysis}.comment_areas_llm l"
            " JOIN {analysis}.v_source_comments s USING (comment_id)"
            " WHERE l.prompt_version = ?"), (PROMPT_VERSION,)):
        decided.setdefault(mention_key(a, m, t), (v, r))

    # mention -> (name, representative matched, representative text, [members])
    mentions = {}
    seen_pair = set()

    def add(comment_id, name, matched, text):
        if (comment_id, name) in seen_pair or (comment_id, name, matched) in done:
            return
        seen_pair.add((comment_id, name))
        key = mention_key(name, matched, text)
        entry = mentions.get(key)
        if entry is None:
            mentions[key] = (name, matched, text, [(comment_id, matched)])
        else:
            entry[3].append((comment_id, matched))

    if bare:
        auto = build_automaton(bare)
        for comment_id, text, name, start, end in iter_bare_hits(conn, ctx, auto):
            add(comment_id, name, text[start:end + 1], text)
    if coll:
        # Same population as the bare lane: the not-a-duplicate set, not every
        # comment. A collision name tagged on 10,000 signers of one letter is
        # one question.
        for comment_id, name, matched, text in conn.execute(ctx.render_sql(
                "SELECT DISTINCT a.comment_id, a.area_name, a.matched_text,"
                " s.comment_text"
                " FROM {analysis}.comment_areas a"
                " JOIN {analysis}.v_truly_unique_comments s USING (comment_id)"
                " WHERE a.area_name IN (SELECT value FROM json_each(?))"), (json.dumps(coll),)):
            add(comment_id, name, matched, text)
    # A mention whose members were partly adjudicated in an earlier run keeps only
    # its unadjudicated members: `done` is filtered per pair above, so the call
    # covers exactly the rows still missing a verdict.
    # A mention already decided under this (model, prompt_version) is copied to its
    # new members instead of being asked again.
    reused = [(key, name, matched, text, sorted(members), decided[key])
              for key, (name, matched, text, members) in sorted(mentions.items())
              if key in decided]
    ordered = [(key, name, matched, text, sorted(members), None)
               for key, (name, matched, text, members) in sorted(mentions.items())
               if key not in decided]
    coll_forests = {}
    for n in coll:
        coll_forests[n] = [f for (f,) in conn.execute(ctx.render_sql(
            "SELECT name FROM {analysis}.forests WHERE name LIKE ? || '%'"
            " ORDER BY name"), (n,))]
    return ordered, reused, names_meta, coll_forests


def user_prompt(name, matched, text, areas, colliding_forests=()):
    where = "; ".join(f"{forest}" + (f", {state}" if state else "")
                      for forest, state in areas)
    plural = "areas" if len(areas) > 1 else "area"
    warn = ""
    if colliding_forests:
        fl = "; ".join(colliding_forests)
        warn = (f'\n\nCAUTION: "{name}" is ALSO the name of a National Forest'
                f' ({fl}) and possibly a mountain range. A comment about that'
                " forest or range as a whole does NOT refer to the roadless"
                f" {plural} — answer true only when the comment means the"
                f" specific inventoried roadless {plural} itself.")
    return (
        f'The word "{matched}" appears in the public comment below. There is a USFS'
        f' inventoried roadless {plural} named "{name}" ({where}).{warn}\n\n'
        f"Does this comment use the word to refer to that roadless {plural}?\n\n"
        f"COMMENT:\n{text}")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(parser)
    parser.add_argument("--model", help="the model name (default: LLM_MODEL in .env)")
    parser.add_argument("--base-url", help="the server (default: LLM_BASE_URL in .env)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Candidates to adjudicate this run (default 50;"
                             " 0 = no cap, the whole queue)")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--words", help="Comma-separated bare words to restrict to")
    parser.add_argument("--count-only", action="store_true",
                        help="print 'calls copies pairs' for the pending queue"
                             " and exit — no model, no writes. For a caller"
                             " deciding whether to spend.")
    args = parser.parse_args()
    ctx = context_from_args(args)

    if args.count_only:
        # Before any client is built: the queue is a property of the corpus and
        # the prompt version, so this needs no model and no endpoint.
        words_filter = args.words.split(",") if args.words else None
        with db.connect(**ctx.db_config) as conn:
            pending, reused, _m, _f = build_candidates(conn, ctx, words_filter)
        pairs = (sum(len(c[4]) for c in pending) + sum(len(c[4]) for c in reused))
        print(f"{len(pending)} {len(reused)} {pairs}")
        return

    client = ChatClient(args.base_url, args.model, timeout=args.timeout)
    base_url, model = client.base_url, client.model
    stamp = model_of(model)  # rows carry the model, never the endpoint called

    words_filter = args.words.split(",") if args.words else None
    with db.connect(**ctx.db_config) as conn:
        candidates, reused, names_meta, coll_forests = build_candidates(
            conn, ctx, words_filter)

    # Copy the already-decided mentions first, and do it whether or not there is
    # anything left to call: these rows are owed either way, and writing them
    # before any paid work means an interrupted run still leaves them.
    #
    # The scan covers the not-a-duplicate set only, so every verdict written
    # below is fanned out to that comment's duplicate-group members by
    # propagate_to_duplicates() at the end — the members are excluded from
    # PAYING, not from being tagged.
    if reused:
        rows = [(cid, name, m, bool(v), r, stamp, PROMPT_VERSION)
                for _k, name, _matched, _text, members, (v, r) in reused
                for cid, m in members]
        with db.connect(**ctx.db_config) as conn:
            with conn.cursor() as cur:
                cur.executemany(ctx.render_sql(_VERDICT_INSERT), rows)
            conn.commit()
        print(f"{len(reused):,} mention(s) already decided at {PROMPT_VERSION}"
              f" — {len(rows):,} verdict(s) copied, no calls made")

    if not candidates:
        # Still fan out: a previous run may have been interrupted before its
        # verdicts reached the duplicates, and this is free.
        with db.connect(**ctx.db_config) as conn:
            fanned = propagate_to_duplicates(ctx, conn)
        print("Nothing to adjudicate — every candidate pair already has a"
              f" verdict at {PROMPT_VERSION}."
              + (f" {fanned:,} verdict(s) carried to duplicates." if fanned else ""))
        return
    batch = candidates[:args.limit] if args.limit else candidates
    pairs_all = sum(len(c[4]) for c in candidates)
    pairs_batch = sum(len(c[4]) for c in batch)
    print(f"{len(candidates):,} pending MENTIONS covering {pairs_all:,} comment/name"
          f" pairs; adjudicating {len(batch):,} mention(s) -> {pairs_batch:,} verdict(s)"
          f" stamped {stamp} @ {PROMPT_VERSION}, via {model} at {base_url}")
    if pairs_all > len(candidates):
        print(f"  {pairs_all - len(candidates):,} call(s) not made: same name,"
              " same matched text, same comment — one decision covers them")

    queue = Queue()
    for item in batch:
        queue.put(item)
    results, errors = [], []
    lock = threading.Lock()
    done_n = [0]

    def worker():
        while True:
            try:
                _key, name, matched, text, members, _decided = queue.get_nowait()
            except Empty:
                return
            try:
                obj = client.complete(
                    system=SYSTEM_PROMPT,
                    user=user_prompt(name, matched, text, names_meta[name],
                                     coll_forests.get(name, ())),
                    schema=VERDICT_SCHEMA)
                # One decision, written to every member of the mention. Each row
                # keeps its OWN matched_text: the members agree under norm_key,
                # which is a comparison key, and the stored value stays the text
                # that actually appears in that comment.
                verdict, rationale = bool(obj["refers_to_area"]), obj.get("rationale")
                with lock:
                    results.extend(
                        (cid, name, m, verdict, rationale, stamp, PROMPT_VERSION)
                        for cid, m in members)
            except Exception as exc:
                with lock:
                    errors.append((members[0][0], name, str(exc)))
            with lock:
                done_n[0] += 1
                if done_n[0] % 10 == 0 or done_n[0] == len(batch):
                    print(f"  {done_n[0]}/{len(batch)} (ok {len(results)},"
                          f" err {len(errors)})", flush=True)

    threads = [threading.Thread(target=worker, daemon=True)
               for _ in range(args.concurrency)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    with db.connect(**ctx.db_config) as conn:
        with conn.cursor() as cur:
            cur.executemany(ctx.render_sql(_VERDICT_INSERT), results)
        conn.commit()

    yes = sum(1 for r in results if r[3])
    print(f"\n=== {len(results)} verdicts written ({yes} refer, {len(results) - yes}"
          f" don't), {len(errors)} errors ===")
    for cid, name, err in errors:
        print(f"  ERROR {cid} / {name}: {err}")
    if errors and not results:
        raise SystemExit("All adjudication calls failed — see errors above.")

    with db.connect(**ctx.db_config) as conn:
        fanned = propagate_to_duplicates(ctx, conn)
    print(f"{fanned:,} verdict(s) carried to duplicate comments — the members are"
          " excluded from paying, not from being tagged")


if __name__ == "__main__":
    main()
