#!/usr/bin/env python3
"""The four gates, one per prong of 7 CFR 1b.11(53) ("substantive").

The combined gate is one test: a dimension of GAP, EVID, ALT or LAW at 2 or
more. This step splits it into four gates, one per prong of the regulation's
definition, and keeps the combined gate as their union:

  impacts        GAP 2+, or EVID 2+ aimed at the impacts (T1, or no T3)
  significance   GAP 3, or move M1 with target T1 on a gated comment
  alternatives   ALT 2+, or EVID 2+ aimed at an alternative (T3)
  compliance     LAW 2+

The model reading records moves and targets, so its EVID routes by target.
The rules' reading does not aim its dimensions: its `impacts` opens on any
GAP or EVID at 2+, its `alternatives` on ALT alone. That difference is part
of what the compare runs measure.

Each gate stores a basis: the dimension and level (and target or move) that
opened it, as a JSON array.

The columns are pure derivations of each row's stored dimensions, moves and
targets. This script recomputes them for every row of substance_scores (the
model reading) and mf_comment_score (the rules), reports the counts, checks
that the union of the four gates equals the stored gate on every row, and
with --write stores them. Re-runnable; no model call.

    python scripts/substance/prongs.py --project roadless
    python scripts/substance/prongs.py --project roadless --write
    make assemble   (assembly, then this, then the LAW check)
"""

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from shared import db  # noqa: E402
from shared.project_context import add_project_argument, context_from_args  # noqa: E402

PRONGS = ("impacts", "significance", "alternatives", "compliance")


def prongs_for(gap, evid, alt, law, moves, targets, gate, reading):
    """{prong: (0 or 1, basis list)} from one comment row's stored fields.

    `reading` is 'model' (moves and targets route EVID and add the M1 path)
    or 'rules' (levels alone). The union of the four flags equals `gate` for
    the levels alone; the M1 path is guarded by the gate so it cannot widen
    the union.
    """
    out = {p: [0, []] for p in PRONGS}
    if gap >= 2:
        out["impacts"] = [1, [f"GAP {gap}"]]
    if reading == "model":
        if evid >= 2 and ("T1" in targets or "T3" not in targets):
            out["impacts"][0] = 1
            out["impacts"][1].append(f"EVID {evid} T1" if "T1" in targets else f"EVID {evid}")
        if evid >= 2 and "T3" in targets:
            out["alternatives"] = [1, [f"EVID {evid} T3"]]
        if "M1" in moves and "T1" in targets and gate:
            out["significance"][0] = 1
            out["significance"][1].append("M1 T1")
    elif evid >= 2:
        out["impacts"][0] = 1
        out["impacts"][1].append(f"EVID {evid}")
    if gap >= 3:
        out["significance"][0] = 1
        out["significance"][1].insert(0, f"GAP {gap}")
    if alt >= 2:
        out["alternatives"][0] = 1
        out["alternatives"][1].insert(0, f"ALT {alt}")
    if law >= 2:
        out["compliance"] = [1, [f"LAW {law}"]]
    return {p: (flag, basis) for p, (flag, basis) in out.items()}


def recompute(conn, ctx, table, key_cols, reading):
    """(updates, counts) for one table: every row's four gates and bases."""
    sql = (f"SELECT {', '.join(key_cols)}, gap, evid, alt, law, moves, targets, gate"
           f" FROM {{analysis}}.{table}")
    updates, counts = [], {p: 0 for p in PRONGS}
    counts["rows"] = counts["union_ne_gate"] = 0
    for row in conn.execute(ctx.render_sql(sql)):
        keys = row[:len(key_cols)]
        gap, evid, alt, law, moves, targets, gate = row[len(key_cols):]
        got = prongs_for(int(gap or 0), int(evid or 0), int(alt or 0), int(law or 0),
                         json.loads(moves or "[]"), json.loads(targets or "[]"),
                         int(gate or 0), reading)
        counts["rows"] += 1
        for p in PRONGS:
            counts[p] += got[p][0]
        if int(any(got[p][0] for p in PRONGS)) != int(bool(gate)):
            counts["union_ne_gate"] += 1
        updates.append(tuple(got[p][0] for p in PRONGS)
                       + tuple(json.dumps(got[p][1]) for p in PRONGS) + keys)
    return updates, counts


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(p)
    p.add_argument("--write", action="store_true",
                   help="store the recomputed gates (default: report only)")
    args = p.parse_args()
    ctx = context_from_args(args)

    tables = (("substance_scores", ("comment_id",), "model"),
              ("mf_comment_score", ("ruleset_version", "comment_id"), "rules"))
    with db.connect(**ctx.db_config) as conn:
        for table, key_cols, reading in tables:
            updates, counts = recompute(conn, ctx, table, key_cols, reading)
            print(f"{table} ({reading}): {counts['rows']:,} rows; "
                  + ", ".join(f"{p} {counts[p]:,}" for p in PRONGS))
            if counts["union_ne_gate"]:
                raise SystemExit(
                    f"{table}: the union of the four gates differs from the stored"
                    f" gate on {counts['union_ne_gate']:,} row(s) — the mapping is"
                    " wrong (method test 1); nothing written.")
            print(f"  union of the four gates = stored gate on every row")
            if args.write and updates:
                set_cols = [f"prong_{p} = ?" for p in PRONGS] \
                    + [f"prong_{p}_basis = ?" for p in PRONGS]
                where = " AND ".join(f"{k} = ?" for k in key_cols)
                with conn.cursor() as cur:
                    cur.executemany(ctx.render_sql(
                        f"UPDATE {{analysis}}.{table} SET {', '.join(set_cols)}"
                        f" WHERE {where}"), updates)
                conn.commit()
                print(f"  stored")
    if not args.write:
        print("report only — pass --write to store the gates")


if __name__ == "__main__":
    main()
