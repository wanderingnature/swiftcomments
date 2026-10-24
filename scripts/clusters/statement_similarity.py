#!/usr/bin/env python3
"""How far the statements of step 15 trials move, by their embeddings.

    uv run python scripts/clusters/statement_similarity.py 20261024_163447 20261024_170736
    make statement-similarity TRIALS="20261024_163447 20261024_170736"

The trials of `make statement-trial` write several statements for one cluster and one
method of the wordings, at several temperatures. Two statements can use other words and
say the same thing. This step embeds every distinct statement of the trials named, with
the embedding server of .env (shared/embeddings.py: EMBED_BASE_URL, EMBED_MODEL), the
text alone, and compares each statement with the reference statement of its cluster
and method: the statement that the most runs at temperature 0 gave (the later trial's,
on a tie). The trials must be of one case.

Two measures, each 1 for the same statement:

    cosine  the cosine of the two vectors
    words   the share of words in the same order (difflib.SequenceMatcher on the words)

One JSON file, trials/statements/similarity_<run_id>.json: the trials, the embedding
model, every statement with both measures, and the median and the lowest of each
measure for each temperature, and for each cluster and temperature. Nothing is written
to the analysis file.

For scale, the file also holds the cosine between the reference statements of every
two clusters of one method: how close two different concerns are.
"""
from __future__ import annotations

import argparse
import difflib
import json
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO))
load_dotenv(_REPO / ".env")

from shared import embeddings  # noqa: E402

OUT = _REPO / "trials" / "statements"


def words(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.split(), b.split()).ratio()


def references(calls: list[dict]) -> dict[tuple[int, str], str]:
    """For each (cluster, method), the statement the most runs at temperature 0 gave; the
    later call's on a tie (calls are in trial order)."""
    refs = {}
    for key in {(x["cluster"], x["method"]) for x in calls}:
        at0 = [x["concern"] for x in calls if (x["cluster"], x["method"]) == key and x["temperature"] == 0]
        if not at0:
            raise SystemExit(f"cluster {key[0]}, {key[1]}: no statement at temperature 0 in the trials named")
        counts = Counter(at0)
        top = max(counts.values())
        refs[key] = [t for t in at0 if counts[t] == top][-1]
    return refs


def summarise(rows: list[dict], keys: tuple[str, ...]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault(tuple(r[k] for k in keys), []).append(r)
    return [{**dict(zip(keys, g)), "statements": len(rs),
             "cosine_median": round(statistics.median(r["cosine"] for r in rs), 4),
             "cosine_lowest": round(min(r["cosine"] for r in rs), 4),
             "words_median": round(statistics.median(r["words"] for r in rs), 4),
             "words_lowest": round(min(r["words"] for r in rs), 4)} for g, rs in sorted(groups.items())]


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("trials", nargs="+", help="the run ids of the trials, of one case")
    args = ap.parse_args(argv)

    records = []
    for run_id in args.trials:
        path = OUT / f"{run_id}.json"
        if not path.exists():
            raise SystemExit(f"no trial file {path.relative_to(_REPO)}")
        records.append(json.loads(path.read_text(encoding="utf-8")))
    cases = {r["case"] for r in records}
    if len(cases) != 1:
        raise SystemExit(f"the trials are of {len(cases)} cases; name trials of one case")
    calls = [dict(x, trial=r["run_id"]) for r in records for x in r["calls"]]
    refs = references(calls)

    base, key, model = embeddings.server()
    texts = sorted({x["concern"] for x in calls})
    vecs = {}
    for i in range(0, len(texts), embeddings.BATCH):
        part = texts[i:i + embeddings.BATCH]
        got, _ = embeddings.embed_batch(part, base, key, model)
        vecs.update({t: np.asarray(v) / np.linalg.norm(v) for t, v in zip(part, got)})

    rows = []
    for x in calls:
        ref = refs[(x["cluster"], x["method"])]
        rows.append({"trial": x["trial"], "cluster": x["cluster"], "method": x["method"],
                     "temperature": x["temperature"], "run": x["run"], "concern": x["concern"],
                     "cosine": round(float(vecs[x["concern"]] @ vecs[ref]), 4),
                     "words": round(words(x["concern"], ref), 4)})
    keys = sorted(refs)
    between = [{"method": a[1], "cluster_a": a[0], "cluster_b": b[0],
                "cosine": round(float(vecs[refs[a]] @ vecs[refs[b]]), 4)}
               for i, a in enumerate(keys) for b in keys[i + 1:] if a[1] == b[1]]
    by_temp = summarise(rows, ("temperature",))
    by_cluster = summarise(rows, ("cluster", "temperature"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    record = {"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "trials": args.trials, "case": cases.pop(), "embedding_model": model, "embedding_base_url": base,
              "statements_embedded": len(texts),
              "references": [{"cluster": c, "method": m, "concern": t} for (c, m), t in sorted(refs.items())],
              "between_clusters": between, "rows": rows, "by_temperature": by_temp, "by_cluster": by_cluster}
    path = OUT / f"similarity_{run_id}.json"
    path.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(texts)} distinct statements embedded by {model}")
    print("temperature  statements  cosine median  lowest  words median  lowest")
    for s in by_temp:
        print(f"{s['temperature']:<12g} {s['statements']:<11} {s['cosine_median']:<14} {s['cosine_lowest']:<7}"
              f" {s['words_median']:<13} {s['words_lowest']}")
    print("cluster  temperature  cosine median  lowest  words median")
    for s in by_cluster:
        print(f"{s['cluster']:<8} {s['temperature']:<12g} {s['cosine_median']:<14} {s['cosine_lowest']:<7}"
              f" {s['words_median']}")
    print("between the reference statements of two clusters (same method)")
    for b in between:
        print(f"  {b['method']:<9} {b['cluster_a']:>4} - {b['cluster_b']:<4} {b['cosine']}")
    print(f"wrote {path.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
