#!/usr/bin/env python3
"""The two substance readings of the same comments, side by side.

make score-model-compare LIMIT=N picks N class A comments, reads each one with
the model (the v3 instrument, the server of .env) and with the rules (rule set
3 in hybrid mode, no model call), keeps both readings and the comparison in
data/roadless.sqlite (score_compare_run, score_compare_reading; the console's
Compare page), writes one JSON file per comment per reading in the shape of
shared/score_json.py, and prints the comparison. New (docs/model-free-scoring.md).

    make score-model-compare LIMIT=20
    make score-model-compare LIMIT=20 SERVER=LOCAL
    make score-model-compare COMMENTS_OF=20261016_141500
    uv run python scripts/score_model_compare.py --limit 20

The comparison is its own run, apart from the two scoring steps: it has its own
queue, and it writes only its own two tables, so make score-model and make
score-model-free still have every comment of their queues to read, and a
comparison never stands in for either.

The queue: the class A comments make score-model reads as themselves (its
'unique' items, a carrier outside every family, scored on its own text, which
is all of its text), sorted by comment id, N of them picked at even steps
across the list, so a pilot spans the docket rather than its first days. An
exemplar or delta item is a part of a family's score, not one comment's
reading, and is not in the queue. COMMENTS_OF=<run> reads the comments of an
earlier run again instead, so a change to the code, the instrument, the rules
or the model is measured on exactly the comments the earlier run read.

Every run is stamped with the code it ran: the git commit, and whether tracked
files had uncommitted changes. The files go to compare/<run>/model/ and
compare/<run>/model-free/, the comparison to compare/<run>/comparison.txt and
to the run's row.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

from shared import db, score_json  # noqa: E402
from shared.instrument import model_of  # noqa: E402
from shared.llm_client import ChatClient, EndpointNotReady  # noqa: E402
from shared.project_context import ProjectContext  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def code_version() -> tuple[str, int]:
    """The git commit the run's code is at, and 1 when tracked files have
    uncommitted changes (the run then read code no commit holds)."""
    try:
        head = subprocess.run(["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(_REPO_ROOT), "status", "--porcelain",
                                "--untracked-files=no"],
                               capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit("make score-model-compare stamps every run with its git commit, and"
                         f" git could not give one here: {exc}. Run it in a git clone.") from None
    return head, int(bool(dirty))


def pick(ids: list[str], n: int) -> list[str]:
    """N of the sorted ids at even steps across the list."""
    ids = sorted(ids)
    if n > len(ids):
        raise SystemExit(f"LIMIT={n} is more than the {len(ids):,} comments the queue can hold")
    return [ids[i * len(ids) // n] for i in range(n)]


def comments_of(conn, run_id: str) -> list[str]:
    """The comments an earlier comparison run read."""
    if conn.execute("SELECT 1 FROM score_compare_run WHERE run_id = ?", (run_id,)).fetchone() is None:
        raise SystemExit(f"no comparison run {run_id}; the console's Compare page lists them")
    return [r[0] for r in conn.execute(
        "SELECT DISTINCT comment_id FROM score_compare_reading WHERE run_id = ? ORDER BY comment_id",
        (run_id,))]


def store(conn, run_id: str, comment_id: str, method: str, record: dict | None, error: str | None) -> None:
    conn.execute("INSERT INTO score_compare_reading (run_id, comment_id, method, record, error)"
                 " VALUES (?, ?, ?, ?, ?)",
                 (run_id, comment_id, method, None if record is None else json.dumps(record, sort_keys=True),
                  error))
    conn.commit()


def model_reading(conn, run_id, client, requests, ctx, shapes, out_dir: Path, concurrency: int) -> dict[str, dict]:
    """The model's reading of the picked queue items: one file and one row each."""
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
                store(conn, run_id, cid, "model", None, str(exc))
                print(f"  ERROR {cid} -> {exc}", flush=True)
                continue
            rec = sc.json_record(obj, model_of(client.model))
            score_json.write(out_dir, rec)
            store(conn, run_id, cid, "model", rec, None)
            records[cid] = rec
            print(f"  model {len(records) + len(errors)}/{len(requests)} {cid}", flush=True)
    if errors:
        print(f"{len(errors)} model call(s) failed and are not compared:", flush=True)
        for cid, err in errors:
            print(f"  {cid}: {err}", flush=True)
    return records


def rules_reading(conn, run_id, picked: set[str], out_dir: Path) -> dict[str, dict]:
    """The rules' reading of the picked comments: one file and one row each."""
    from model_free import inputs, run as mf_run

    tags = inputs.load_tags(conn)
    authority_keys = inputs.load_authority_keys(conn)
    print(f"the rules' reading: {len(picked)} comment(s), no model call", flush=True)
    records = {}
    for cid, units in inputs.iter_comments(conn, picked):
        if units is None:
            store(conn, run_id, cid, "model-free", None, "no sentence of 25 or more letters and digits")
            print(f"  {cid}: no sentence to score; not compared", flush=True)
            continue
        scored, comment, answer = mf_run.read_comment(cid, units, tags, authority_keys)
        rec = mf_run.json_record(comment, answer, scored)
        score_json.write(out_dir, rec)
        store(conn, run_id, cid, "model-free", rec, None)
        records[cid] = rec
    return records


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument("--limit", type=int,
                       help="how many class A comments to read both ways (make score-model-compare LIMIT=N)")
    which.add_argument("--comments-of", metavar="RUN",
                       help="read the comments of this earlier comparison run again (COMMENTS_OF=<run>)")
    ap.add_argument("--concurrency", type=int, default=8,
                    help="the most model calls in flight; the client starts at one and climbs")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        raise SystemExit("LIMIT must be at least 1")

    import score_comments as sc
    from model_free import RULESET_VERSION

    version, dirty = code_version()
    ctx = ProjectContext.load("roadless")
    client = ChatClient(timeout=args.timeout, max_in_flight=args.concurrency)
    args.concurrency = client.max_in_flight     # the server's limit when lower
    conn = db.connect(db.DB_PATH)
    print("make score-model-compare: building the model's whole class A queue to pick from",
          flush=True)
    # The queue build announces a make score-model run and the tables it writes;
    # this run writes none of them, so its lines are kept off the screen.
    with contextlib.redirect_stdout(io.StringIO()):
        requests, shapes = sc.build_scoring_requests(ctx, model=client.model, rescore=True)
    unique = {r["comment_id"]: r for r in requests if r["kind"] == "unique"}
    if not unique:
        raise SystemExit("the model's queue holds no class A comment read as itself")
    if args.comments_of:
        picked = comments_of(conn, args.comments_of)
        gone = [c for c in picked if c not in unique]
        if gone:
            raise SystemExit(f"{len(gone)} comment(s) of run {args.comments_of} are no longer class A"
                             " comments the model reads as themselves (the screen or the groups"
                             " changed since): " + ", ".join(gone))
        how = f"the {len(picked)} comments of run {args.comments_of}"
    else:
        picked = pick(list(unique), args.limit)
        how = (f"{len(picked)} of the {len(unique):,} class A comments read as themselves,"
               " picked at even steps by comment id")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = _REPO_ROOT / "compare" / run_id
    conn.execute("INSERT INTO score_compare_run (run_id, started_at, code_version, code_dirty, model,"
                 " server, instrument_version, ruleset_version, comments_of, pool, picked)"
                 " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (run_id, now(), version, dirty, model_of(client.model), client.base_url,
                  sc.SCORING_INSTRUMENT, RULESET_VERSION, args.comments_of, len(unique), len(picked)))
    conn.commit()
    print(f"make score-model-compare: run {run_id} at commit {version[:12]}"
          + (" with uncommitted changes" if dirty else "") + f"; {how}; each read by the model"
          f" ({sc.SCORING_INSTRUMENT}) and by the rules (rule set {RULESET_VERSION}); writes"
          f" score_compare_run and score_compare_reading, and one JSON file per comment per"
          f" reading under {run_dir.relative_to(_REPO_ROOT)}/", flush=True)

    model = model_reading(conn, run_id, client, [unique[c] for c in picked], ctx, shapes,
                          run_dir / "model", args.concurrency)
    rules = rules_reading(conn, run_id, set(picked), run_dir / "model-free")
    out = io.StringIO()
    score_json.compare(model, rules, 0, out, labels=("model", "rules"))
    text = out.getvalue()
    (run_dir / "comparison.txt").write_text(text, encoding="utf-8")
    conn.execute("UPDATE score_compare_run SET report = ?, finished_at = ? WHERE run_id = ?",
                 (text, now(), run_id))
    conn.commit()
    conn.close()
    print("\n" + text, end="")
    print(f"\nrun {run_id}: {len(model)} model and {len(rules)} rules readings in score_compare_reading;"
          f" files under {run_dir.relative_to(_REPO_ROOT)}/; make console, page Compare, sets it beside"
          f" any other run; make score-model-compare COMMENTS_OF={run_id} reads the same comments again")
    return 0


if __name__ == "__main__":
    sys.exit(main())
