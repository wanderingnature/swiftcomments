#!/usr/bin/env python3
"""The two substance readings side by side: two folders of per-comment JSON
files in the shape of shared/score_json.py, one from `make score JSON=dir`
(the model) and one from `make score-rules JSON=dir` (the rules), or any two
runs of either. New (docs/model-free-scoring.md).

    uv run python scripts/compare_scores.py --a json/model --b json/rules [--limit N]
    make compare-scores A=json/model B=json/rules

Prints, for the comments present in both: per dimension, how many agree
exactly, how many A reads higher, how many B; the gate, band and
answerability agreement; then every comment where the gate differs, with
each side's levels and evidence, up to --limit (default 20; 0 for all).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from shared import score_json  # noqa: E402

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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--a", required=True, metavar="DIR", help="a folder of score files")
    ap.add_argument("--b", required=True, metavar="DIR", help="the other")
    ap.add_argument("--limit", type=int, default=20, help="gate disagreements to print; 0 for all")
    args = ap.parse_args(argv)
    return compare(score_json.read_dir(Path(args.a)), score_json.read_dir(Path(args.b)), args.limit)


if __name__ == "__main__":
    sys.exit(main())
