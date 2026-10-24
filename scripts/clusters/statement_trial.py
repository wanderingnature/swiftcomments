#!/usr/bin/env python3
"""A trial of step 15, the concern statement, on a few clusters of the concern map.

    uv run python scripts/clusters/statement_trial.py --clusters 207 104 52 1 --runs 3 --temperatures 0 0.7
    make statement-trial CLUSTERS="207 104 52 1" RUNS=3 TEMPERATURES="0 0.7" SERVER=LOCAL
    make statement-trial CASE=<case> CLUSTERS="187 94 47 1" RUNS=3 TEMPERATURES="0 0.7" SERVER=LOCAL

Step 15 is not built. This trial asks how far the statement depends on the
wordings sent and how far on the model's sampling, before the step is built.
For each cluster it builds the wordings two ways, and sends each set RUNS times
at each temperature, one call per run:

    leaders    the leader text of each leader in the cluster: the case's own
               merge already folded the near-copies under the most-copied text
    collapse   every distinct sentence of the cluster (each leader and the
               sentences it absorbed), folded by collapse() at
               cosine 0.95, each group standing as its longest text

The clusters are the concern map's, or with --case those of any stored case
(the other model's choice, for one). The system prompt and the fold: STATEMENT_SYS, Stmt, collapse,
DUPLICATE_COSINE, wordings_block. The server is the reader's (shared/llm_client.py), the
vectors the case's own (its model, its view). Nothing is written to the file.

One JSON file per trial, trials/statements/<run_id>.json: the settings, the
code version, the wordings of each cluster under each method, every call with
its statement and its tokens, and for each cluster, method and temperature the
number of distinct statements among the runs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO))
load_dotenv(_REPO / ".env")

from scripts.clusters.embed import VIEWS, unpack  # noqa: E402
from shared import db  # noqa: E402
from shared.llm_client import ChatClient  # noqa: E402

OUT = _REPO / "trials" / "statements"
METHODS = ("leaders", "collapse")

STATEMENT_SYS = (
    "You are the Forest Service writing the response to comments on the rescission of the 2001"
    " Roadless Rule. You are given the distinct wordings commenters used under one concern. Every"
    " wording counts the same. Write the concern statement the one written response answers: one or"
    " two sentences, the concern as the agency has to answer it, covering what every wording raises"
    " and nothing more. No praise, no hedging.")
STMT_SCHEMA = {"properties": {"concern": {"title": "Concern", "type": "string"}},
               "required": ["concern"], "title": "Stmt", "type": "object"}
DUPLICATE_COSINE = 0.95


def collapse(texts: list[str], vecs: dict, threshold: float = DUPLICATE_COSINE) -> list[list[str]]:
    """Groups of near-duplicate wordings: a text joins the first group whose representative is at
    or above `threshold` cosine to it, else starts a group. Each group is ordered longest first, so
    group[0] is the wording that stands for the group."""
    groups: list[list[str]] = []
    reps: list[np.ndarray] = []
    for t in texts:
        v = np.asarray(vecs[t], dtype=np.float64)
        v = v / np.linalg.norm(v)
        for g, r in zip(groups, reps):
            if float(r @ v) >= threshold:
                g.append(t)
                break
        else:
            groups.append([t])
            reps.append(v)
    for g in groups:
        g.sort(key=lambda s: (-len(s), s))
    return groups


def wordings_block(texts: list[str]) -> str:
    return "\n".join(f"W{i} {t}" for i, t in enumerate(texts, 1))


def code_version() -> tuple[str, int]:
    head = subprocess.run(["git", "-C", str(_REPO), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(_REPO), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True, check=True).stdout.strip()
    return head, int(bool(dirty))


def concern_map(conn) -> str:
    row = conn.execute("SELECT case_name FROM cluster_concern_map").fetchone()
    if row is None:
        raise SystemExit("no concern map is recorded: make concern-map CASE=<case> first (docs/topics-guide.md)")
    return row[0]


def cluster_wordings(conn, case: str, cluster: int) -> dict:
    """The cluster's names and its wordings under both methods, texts in sort order."""
    model, view = conn.execute("SELECT model, view FROM cluster_case WHERE case_name = ?", (case,)).fetchone()
    info = conn.execute("SELECT topic, leaders, terms FROM cluster_case_cluster WHERE case_name = ? AND cluster = ?",
                        (case, cluster)).fetchone()
    if info is None:
        raise SystemExit(f"case {case} has no cluster {cluster}")
    leaders = [r[0] for r in conn.execute(
        "SELECT s.text FROM cluster_case_member m JOIN gate_sentence s ON s.text_key = m.leader_key"
        " WHERE m.case_name = ? AND m.cluster = ? ORDER BY s.text", (case, cluster))]
    rows = conn.execute(
        "SELECT s.text, e.vector FROM cluster_case_member m"
        " JOIN cluster_case_leader l ON l.case_name = m.case_name AND l.leader_key = m.leader_key"
        " JOIN gate_sentence s ON s.text_key = l.text_key"
        " LEFT JOIN sentence_embedding e ON e.text_key = l.text_key AND e.model = ? AND e.instruction = ?"
        " WHERE m.case_name = ? AND m.cluster = ? ORDER BY s.text", (model, VIEWS[view], case, cluster)).fetchall()
    missing = [t for t, v in rows if v is None]
    if missing:
        raise SystemExit(f"cluster {cluster}: {len(missing)} sentences have no {model} vector under the {view} view")
    vecs = {t: unpack(v) for t, v in rows}
    groups = collapse(list(vecs), vecs)
    return {"cluster": cluster, "topic": info["topic"], "leaders": info["leaders"], "terms": json.loads(info["terms"]),
            "texts": len(vecs),
            "methods": {"leaders": {"wordings": leaders},
                        "collapse": {"wordings": [g[0] for g in groups], "stands_for": groups}}}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--clusters", type=int, nargs="+", required=True)
    ap.add_argument("--runs", type=int, required=True)
    ap.add_argument("--temperatures", type=float, nargs="+", required=True)
    ap.add_argument("--case", help="a stored case (default: the concern map)")
    ap.add_argument("--db", default=str(db.DB_PATH), help="the analysis file (default data/roadless.sqlite)")
    args = ap.parse_args(argv)

    conn = db.connect(args.db)
    case = args.case or concern_map(conn)
    if conn.execute("SELECT 1 FROM cluster_case WHERE case_name = ?", (case,)).fetchone() is None:
        raise SystemExit(f"no case {case!r}: make cases lists them")
    clusters = [cluster_wordings(conn, case, c) for c in args.clusters]
    conn.close()

    client = ChatClient()
    head, dirty = code_version()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print(f"trial {run_id}: case {case}; clusters {args.clusters}; {args.runs} runs at temperatures"
          f" {args.temperatures}; {client.model} at {client.base_url}", flush=True)
    calls = []
    for c in clusters:
        for method in METHODS:
            user = wordings_block(c["methods"][method]["wordings"])
            for temp in args.temperatures:
                for run in range(1, args.runs + 1):
                    t0 = time.monotonic()
                    obj, usage = client.complete(system=STATEMENT_SYS, user=user, schema=STMT_SCHEMA,
                                                 temperature=temp, with_usage=True)
                    calls.append({"cluster": c["cluster"], "method": method, "temperature": temp, "run": run,
                                  "concern": obj["concern"], "prompt_tokens": usage.get("prompt_tokens"),
                                  "completion_tokens": usage.get("completion_tokens"),
                                  "seconds": round(time.monotonic() - t0, 1)})
                    print(f"  cluster {c['cluster']} {method} t={temp} run {run}:"
                          f" {usage.get('prompt_tokens')} in, {calls[-1]['seconds']}s", flush=True)

    summary = []
    for c in clusters:
        for method in METHODS:
            for temp in args.temperatures:
                got = [x["concern"] for x in calls
                       if x["cluster"] == c["cluster"] and x["method"] == method and x["temperature"] == temp]
                summary.append({"cluster": c["cluster"], "method": method, "temperature": temp,
                                "runs": len(got), "distinct_statements": len(set(got))})
    record = {"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "code_version": head, "code_dirty": dirty, "model": client.model, "base_url": client.base_url,
              "case": case, "clusters_asked": args.clusters, "runs": args.runs, "temperatures": args.temperatures,
              "system_prompt": STATEMENT_SYS, "schema": STMT_SCHEMA, "duplicate_cosine": DUPLICATE_COSINE,
              "clusters": clusters, "calls": calls, "summary": summary}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{run_id}.json"
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for s in summary:
        print(f"  cluster {s['cluster']} {s['method']} t={s['temperature']}:"
              f" {s['distinct_statements']} distinct of {s['runs']}")
    print(f"wrote {path.relative_to(_REPO)}; {client.spend_line()}")


if __name__ == "__main__":
    main()
