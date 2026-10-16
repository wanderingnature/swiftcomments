#!/usr/bin/env python3
"""The two substance readings of the same comments, side by side.

make score-model-compare LIMIT=N picks N class A comments, reads each one with the
model (the v3 instrument, the server of .env) and with the rules (rule set 3,
no model call), writes one JSON file per comment per reading in the shape of
shared/score_json.py, and prints the comparison. New (docs/model-free-scoring.md).

    make score-model-compare LIMIT=20
    make score-model-compare LIMIT=20 SERVER=LOCAL
    uv run python scripts/score_model_compare.py --limit 20

The comparison is its own run, apart from the two scoring steps: it has its own
queue and writes nothing to data/roadless.sqlite, so make score-model and make
score-model-free still have every comment of their own queues to read, and a
comparison never stands in for either.

The queue: the class A comments make score-model reads as themselves (its
'unique' items, a carrier outside every family, scored on its own text, which
is all of its text), sorted by comment id, N of them picked at even steps
across the list, so a pilot spans the docket rather than its first days. An
exemplar or delta item is a part of a family's score, not one comment's
reading, and is not in the queue.

The files go to compare/<run>/model/ and compare/<run>/model-free/, and the
printed comparison to compare/<run>/comparison.txt. It prints, for the
comments both readings scored: per dimension, how many agree exactly, how many
the model reads higher, how many the rules; the gate, band, strength and
answerability agreement; then every comment where the gate differs, with each
side's levels and evidence.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

from shared import db, score_json  # noqa: E402
from shared.instrument import model_of  # noqa: E402
from shared.llm_client import ChatClient, EndpointNotReady  # noqa: E402
from shared.project_context import ProjectContext  # noqa: E402

DIMS = score_json.DIMS


def describe(records: dict[str, dict]) -> str:
    scorers = sorted({r["scorer"] for r in records.values()})
    instruments = sorted({r["instrument"] for r in records.values()})
    return f"{len(records):,} comments; scorer {', '.join(scorers)}; instrument {', '.join(instruments)}"


def evidence_lines(rec: dict) -> list[str]:
    out = []
    for e in rec["evidence"]:
        if "rule" in e:
            out.append(f"    {e.get('dimension', '?')} {e.get('grade', '?')} {e['rule']}: {e.get('match', '')!s}")
        else:
            out.append("    " + ", ".join(f"{k}={v!s}" for k, v in e.items()))
    return out


def compare(a: dict[str, dict], b: dict[str, dict], limit: int, out=sys.stdout) -> int:
    both = sorted(set(a) & set(b))
    print(f"A: {describe(a)}", file=out)
    print(f"B: {describe(b)}", file=out)
    print(f"in both: {len(both):,}; only in A: {len(set(a) - set(b)):,}; only in B: {len(set(b) - set(a)):,}",
          file=out)
    if not both:
        return 1
    print("\nper dimension: same level, A higher, B higher", file=out)
    for d in DIMS:
        same = sum(1 for c in both if a[c]["levels"][d] == b[c]["levels"][d])
        up = sum(1 for c in both if a[c]["levels"][d] > b[c]["levels"][d])
        print(f"  {d:5s}  {same:7,}  {up:7,}  {len(both) - same - up:7,}", file=out)
    same_all = sum(1 for c in both if all(a[c]["levels"][d] == b[c]["levels"][d] for d in DIMS))
    print(f"identical on all eight: {same_all:,} of {len(both):,}", file=out)
    gate_same = sum(1 for c in both if a[c]["gate"] == b[c]["gate"])
    a_open = sum(1 for c in both if a[c]["gate"])
    b_open = sum(1 for c in both if b[c]["gate"])
    print(f"\ngate: same on {gate_same:,} of {len(both):,}; open in A {a_open:,}, in B {b_open:,},"
          f" in both {sum(1 for c in both if a[c]['gate'] and b[c]['gate']):,}", file=out)
    print(f"band: same on {sum(1 for c in both if a[c]['band'] == b[c]['band']):,}", file=out)
    rated = [c for c in both if a[c]["a_level"] is not None and b[c]["a_level"] is not None]
    if rated:
        print(f"answerability level: same on"
              f" {sum(1 for c in rated if a[c]['a_level'] == b[c]['a_level']):,} of {len(rated):,} rated on both sides",
              file=out)
    else:
        print("answerability level: not rated on both sides", file=out)
    diff = sum(abs(a[c]["strength"] - b[c]["strength"]) for c in both)
    print(f"strength: same on {sum(1 for c in both if a[c]['strength'] == b[c]['strength']):,};"
          f" mean absolute difference {diff / len(both):.2f}", file=out)

    disagreements = [c for c in both if a[c]["gate"] != b[c]["gate"]]
    shown = disagreements if limit == 0 else disagreements[:limit]
    print(f"\ngate disagreements: {len(disagreements):,}" + (f" (first {len(shown)})" if len(shown) < len(disagreements) else ""),
          file=out)
    for c in shown:
        print(f"\n{c}: A gate={a[c]['gate']} basis={a[c]['gate_basis']} | B gate={b[c]['gate']} basis={b[c]['gate_basis']}",
              file=out)
        print("  A " + " ".join(f"{d} {a[c]['levels'][d]}" for d in DIMS), file=out)
        for line in evidence_lines(a[c]):
            print(line, file=out)
        print("  B " + " ".join(f"{d} {b[c]['levels'][d]}" for d in DIMS), file=out)
        for line in evidence_lines(b[c]):
            print(line, file=out)
    return 0


def pick(ids: list[str], n: int) -> list[str]:
    """N of the sorted ids at even steps across the list."""
    ids = sorted(ids)
    if n > len(ids):
        raise SystemExit(f"LIMIT={n} is more than the {len(ids):,} comments the queue can hold")
    return [ids[i * len(ids) // n] for i in range(n)]


def model_reading(client, requests, ctx, shapes, out_dir: Path, concurrency: int) -> dict[str, dict]:
    """The model's reading of the picked queue items, one file each; nothing written to the file."""
    import score_comments as sc

    print(f"the model's reading: {len(requests)} call(s) to {client.model} at {client.base_url},"
          f" at most {concurrency} in flight", flush=True)
    own_law, shared_law = sc.law_sets(ctx, shapes)
    tags = sc.grading_tags(ctx)
    schema = sc.SCHEMAS[sc.SCORING_INSTRUMENT]
    records, errors = {}, []
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = {pool.submit(sc.score_request, client, r, r["system"], schema, tags, own_law,
                               shared_law): r["comment_id"] for r in requests}
        for fut in as_completed(futures):
            cid = futures[fut]
            try:
                obj = fut.result()
            except EndpointNotReady as exc:
                pool.shutdown(cancel_futures=True)
                raise SystemExit(f"ABORTED: {exc}") from None
            except Exception as exc:
                errors.append((cid, str(exc)))
                print(f"  ERROR {cid} -> {exc}", flush=True)
                continue
            rec = sc.json_record(obj, model_of(client.model))
            score_json.write(out_dir, rec)
            records[cid] = rec
            print(f"  model {len(records) + len(errors)}/{len(requests)} {cid}", flush=True)
    if errors:
        print(f"{len(errors)} model call(s) failed and are not compared:", flush=True)
        for cid, err in errors:
            print(f"  {cid}: {err}", flush=True)
    return records


def rules_reading(picked: set[str], out_dir: Path) -> dict[str, dict]:
    """The rules' reading of the picked comments, one file each; nothing written to the file."""
    from model_free import inputs, run as mf_run

    conn = inputs.connect()
    conn.execute("PRAGMA query_only = 1")
    tags = inputs.load_tags(conn)
    authority_keys = inputs.load_authority_keys(conn)
    print(f"the rules' reading: {len(picked)} comment(s), no model call", flush=True)
    records = {}
    for u in inputs.iter_comments(conn, picked):
        sentences, comment, answer = mf_run.read_comment(u, tags, authority_keys)
        rec = mf_run.json_record(comment, answer, sentences)
        score_json.write(out_dir, rec)
        records[u.comment_id] = rec
    conn.close()
    return records


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--limit", type=int, required=True,
                    help="how many class A comments to read both ways (make score-model-compare LIMIT=N)")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="the most model calls in flight; the client starts at one and climbs")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args(argv)
    if args.limit < 1:
        raise SystemExit("LIMIT must be at least 1")

    import score_comments as sc

    ctx = ProjectContext.load("roadless")
    client = ChatClient(timeout=args.timeout, max_in_flight=args.concurrency)
    print("make score-model-compare: building the model's whole class A queue to pick from",
          flush=True)
    # The queue build announces a make score-model run and the tables it writes;
    # this run writes none of them, so its lines are kept off the screen.
    with contextlib.redirect_stdout(io.StringIO()):
        requests, shapes = sc.build_scoring_requests(ctx, model=client.model, rescore=True)
    unique = {r["comment_id"]: r for r in requests if r["kind"] == "unique"}
    if not unique:
        raise SystemExit("the model's queue holds no class A comment read as itself")
    picked = pick(list(unique), args.limit)
    run_dir = _REPO_ROOT / "compare" / datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"make score-model-compare: {len(picked)} of the {len(unique):,} class A comments read as"
          f" themselves, picked at even steps by comment id; each read by the model and by the"
          f" rules; one JSON file per comment per reading under {run_dir.relative_to(_REPO_ROOT)}/;"
          f" nothing written to {db.DB_PATH.relative_to(_REPO_ROOT)}", flush=True)

    model = model_reading(client, [unique[c] for c in picked], ctx, shapes, run_dir / "model",
                          args.concurrency)
    rules = rules_reading(set(picked), run_dir / "model-free")
    out = io.StringIO()
    compare(model, rules, 0, out)
    text = out.getvalue()
    (run_dir / "comparison.txt").write_text(text, encoding="utf-8")
    print("\n" + text, end="")
    print(f"\nwritten: {run_dir.relative_to(_REPO_ROOT)}/model/ ({len(model)} files),"
          f" model-free/ ({len(rules)} files), comparison.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
