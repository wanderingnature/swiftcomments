#!/usr/bin/env python3
"""LLM afterstep — resolve discovered citations/references against the canonical seeds.

NOT part of the deterministic tagging pipeline. A discovered legal-authority citation
("36 C.F.R. 294") or cited-reference key may be an imperfect form of something already
in the agency's DEIS record. Per discovered VALUE (the answer applies to every comment
that wrote it), a deterministic pre-filter picks plausible canonical candidates
(shared numbers / name tokens), and the model picks one or "none of these". Every
verdict lands in citation_resolutions_llm; resolved_seed_id NULL = genuinely new
information. A value with NO candidate overlap is recorded as new by the pre-filter
itself (model 'prefilter') — there is nothing for a model to compare.

This step enables the downstream analysis (correct-vs-imperfect counts, the citizens'
bibliography); it does not compute it.

Usage:
    python scripts/entity_tagging/resolve_citations.py --project roadless \
        --kind authorities [--limit 50]
"""

import argparse
import re
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

PROMPT_VERSION = "v1"
MAX_CANDIDATES = 15

SYSTEM_PROMPT = (
    "You resolve citations from public comments against a fixed list of canonical"
    " authorities/references from an agency's rulemaking record. Citizens cite"
    " imperfectly — abbreviated, partial, misformatted. Decide whether the citation"
    " is a form of ONE of the numbered candidates. Answer with candidate_index (the"
    " matching candidate's number, or 0 if it matches none of them) and a"
    " one-sentence rationale. Only pick a candidate when the citation plausibly"
    " denotes that specific authority; a merely related one is 0.")

RESOLVE_SCHEMA = {
    "type": "object",
    "properties": {
        "candidate_index": {"type": "integer"},
        "rationale": {"type": "string"},
    },
    "required": ["candidate_index", "rationale"],
    "additionalProperties": False,
}

_STOPWORDS = {"the", "and", "for", "act", "national", "united", "states", "federal",
              "section", "sections"}


def _tokens(s):
    digits = set(re.findall(r"\d+", s or ""))
    words = {w.lower() for w in re.findall(r"[A-Za-z]{4,}", s or "")} - _STOPWORDS
    return digits, words


def _candidates(value, seeds):
    """Deterministic pre-filter: canonical rows sharing a number (weighted) or a
    significant word with the discovered value, best-overlap first, capped."""
    vd, vw = _tokens(value)
    scored = []
    for seed in seeds:
        sd, sw = seed["digits"], seed["words"]
        score = 2 * len(vd & sd) + len(vw & sw)
        if score > 0:
            scored.append((score, seed))
    scored.sort(key=lambda t: (-t[0], t[1]["display"]))
    return [s for _, s in scored[:MAX_CANDIDATES]]


def _load_seeds(conn, ctx, kind):
    if kind == "authority":
        rows = conn.execute(ctx.render_sql(
            "SELECT seed_id, display, citation, case_name, match_keys"
            " FROM {analysis}.legal_authority WHERE seed_id IS NOT NULL")).fetchall()
        seeds = [{"seed_id": r[0], "display": r[1],
                  "text": " ".join(filter(None, r[1:5]))} for r in rows]
    else:
        rows = conn.execute(ctx.render_sql(
            "SELECT seed_id, display, citation_key, match_keys, authors, year, title"
            " FROM {analysis}.cited_references WHERE seed_id IS NOT NULL")).fetchall()
        seeds = [{"seed_id": r[0], "display": r[1],
                  "text": " ".join(str(x) for x in r[1:7] if x)} for r in rows]
    for s in seeds:
        s["digits"], s["words"] = _tokens(s["text"])
    return seeds


def _pending(conn, ctx, kind, model):
    value_col = "citation" if kind == "authority" else "citation_key"
    table = "legal_authority" if kind == "authority" else "cited_references"
    return [v for (v,) in conn.execute(ctx.render_sql(f"""
        SELECT d.{value_col} FROM {{analysis}}.{table} d
        WHERE d.seed_id IS NULL AND d.{value_col} IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM {{analysis}}.citation_resolutions_llm r
                          WHERE r.kind = ? AND r.discovered_value = d.{value_col}
                            AND r.model IN (?, 'prefilter')
                            AND r.prompt_version = ?)
        ORDER BY d.{value_col}"""), (kind, model, PROMPT_VERSION))]


def user_prompt(value, cands):
    lines = "\n".join(f"{i + 1}. {c['display']}" + (
        f" [{c['text'][:160]}]" if c["text"] != c["display"] else "")
        for i, c in enumerate(cands))
    return (f'CITATION FROM A PUBLIC COMMENT: "{value}"\n\n'
            f"CANONICAL CANDIDATES:\n{lines}\n\n"
            "Which candidate (1-N) is this a form of, or 0 for none?")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(parser)
    parser.add_argument("--kind", default="both",
                        choices=("authorities", "references", "both"))
    parser.add_argument("--model", help="the model name (default: LLM_MODEL in .env)")
    parser.add_argument("--base-url", help="the server (default: LLM_BASE_URL in .env)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Values to resolve this run (default 50;"
                             " 0 = no cap, the whole queue)")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()
    ctx = context_from_args(args)

    client = ChatClient(args.base_url, args.model, timeout=args.timeout)
    base_url, model = client.base_url, client.model
    stamp = model_of(model)  # rows and the done-check carry the model, never the endpoint

    kinds = ["authority", "reference"] if args.kind == "both" else [
        "authority" if args.kind == "authorities" else "reference"]

    for kind in kinds:
        with db.connect(**ctx.db_config) as conn:
            seeds = _load_seeds(conn, ctx, kind)
            pending = _pending(conn, ctx, kind, stamp)
        if not pending:
            print(f"{kind}: nothing pending.")
            continue

        work, prefilter_new = [], []
        for value in pending:
            cands = _candidates(value, seeds)
            if cands:
                work.append((value, cands))
            else:
                prefilter_new.append(
                    (kind, value, None, None,
                     "No canonical candidate shares a number or name token.",
                     "prefilter", PROMPT_VERSION))
        work = work[:args.limit] if args.limit else work
        print(f"{kind}: {len(pending)} pending; {len(prefilter_new)} new by"
              f" pre-filter (no candidates); adjudicating {len(work)} stamped {stamp}"
              f" @ {PROMPT_VERSION}, via {model} at {base_url}")

        queue = Queue()
        for item in work:
            queue.put(item)
        results, errors = [], []
        lock = threading.Lock()
        done_n = [0]

        def worker():
            while True:
                try:
                    value, cands = queue.get_nowait()
                except Empty:
                    return
                try:
                    obj = client.complete(system=SYSTEM_PROMPT,
                                          user=user_prompt(value, cands),
                                          schema=RESOLVE_SCHEMA)
                    idx = int(obj["candidate_index"])
                    picked = cands[idx - 1] if 1 <= idx <= len(cands) else None
                    row = (kind, value,
                           picked["seed_id"] if picked else None,
                           picked["display"] if picked else None,
                           obj.get("rationale"), stamp, PROMPT_VERSION)
                    with lock:
                        results.append(row)
                except Exception as exc:
                    with lock:
                        errors.append((value, str(exc)))
                with lock:
                    done_n[0] += 1
                    if done_n[0] % 10 == 0 or done_n[0] == len(work):
                        print(f"  {done_n[0]}/{len(work)} (ok {len(results)},"
                              f" err {len(errors)})", flush=True)

        threads = [threading.Thread(target=worker, daemon=True)
                   for _ in range(args.concurrency)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        rows = prefilter_new + results
        if rows:
            with db.connect(**ctx.db_config) as conn:
                with conn.cursor() as cur:
                    cur.executemany(ctx.render_sql(
                        "INSERT INTO {analysis}.citation_resolutions_llm"
                        " (kind, discovered_value, resolved_seed_id,"
                        "  resolved_display, rationale, model, prompt_version)"
                        " VALUES (?, ?, ?, ?, ?, ?, ?)"
                        " ON CONFLICT DO NOTHING"), rows)
                conn.commit()
        resolved = sum(1 for r in results if r[2] is not None)
        print(f"{kind}: wrote {len(rows)} resolutions ({resolved} matched a"
              f" canonical, {len(results) - resolved} judged new,"
              f" {len(prefilter_new)} new by pre-filter), {len(errors)} errors")
        for value, err in errors:
            print(f"  ERROR {value!r}: {err}")


if __name__ == "__main__":
    main()
