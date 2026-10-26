#!/usr/bin/env python3
"""The four gates, one per prong of 7 CFR 1b.11(53) ("substantive").

The combined gate is one test: a dimension of GAP, EVID, ALT or LAW at 2 or
more. This step splits it into four gates, one per prong of the regulation's
definition, and keeps the combined gate as their union:

  impacts        GAP 2+ or EVID 2+ (a deficiency named, or evidence offered)
  significance   GAP 3 (the deficiency carries into a conclusion)
  alternatives   ALT 2+ (a distinct alternative)
  compliance     LAW 2+ (a legal authority)

The mapping is the same for both readings and uses the dimension levels
alone. Two constraints fix it: the union of the four gates must equal the
stored gate on every row, and the answerability levels must reproduce
(A1 from compliance; A2 from significance, alternatives, or impacts with a
mechanism and a citation). A mapping that routes a dimension by its moves or
targets breaks both.

Each gate stores a basis: the dimension and level that opened it, as a JSON
array.

The columns are pure derivations of each row's stored dimensions. This
script recomputes them for every row of substance_scores (the model reading)
and mf_comment_score (the rules), reports the counts, checks the union rule
on every row, and with --write stores them. Re-runnable; no model call.

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


def prongs_for(gap, evid, alt, law):
    """{prong: (0 or 1, basis list)} from one comment row's dimension levels.

    The union of the four flags equals the combined gate (a dimension of GAP,
    EVID, ALT or LAW at 2 or more) by construction.
    """
    out = {p: (0, []) for p in PRONGS}
    if gap >= 2 or evid >= 2:
        basis = [f"GAP {gap}"] if gap >= 2 else []
        if evid >= 2:
            basis.append(f"EVID {evid}")
        out["impacts"] = (1, basis)
    if gap >= 3:
        out["significance"] = (1, [f"GAP {gap}"])
    if alt >= 2:
        out["alternatives"] = (1, [f"ALT {alt}"])
    if law >= 2:
        out["compliance"] = (1, [f"LAW {law}"])
    return out


def recompute(conn, ctx, table, key_cols):
    """(updates, counts) for one table: every row's four gates and bases."""
    sql = (f"SELECT {', '.join(key_cols)}, gap, evid, alt, law, gate"
           f" FROM {{analysis}}.{table}")
    updates, counts = [], {p: 0 for p in PRONGS}
    counts["rows"] = counts["union_ne_gate"] = 0
    for row in conn.execute(ctx.render_sql(sql)):
        keys = row[:len(key_cols)]
        gap, evid, alt, law, gate = row[len(key_cols):]
        got = prongs_for(int(gap or 0), int(evid or 0), int(alt or 0), int(law or 0))
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

    tables = (("substance_scores", ("comment_id",)),
              ("mf_comment_score", ("ruleset_version", "comment_id")))
    with db.connect(**ctx.db_config) as conn:
        for table, key_cols in tables:
            updates, counts = recompute(conn, ctx, table, key_cols)
            print(f"{table}: {counts['rows']:,} rows; "
                  + ", ".join(f"{p} {counts[p]:,}" for p in PRONGS))
            if counts["union_ne_gate"]:
                raise SystemExit(
                    f"{table}: the union of the four gates differs from the stored"
                    f" gate on {counts['union_ne_gate']:,} row(s) — the mapping is"
                    " wrong; nothing written.")
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
