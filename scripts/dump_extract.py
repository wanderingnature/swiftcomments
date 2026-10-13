#!/usr/bin/env python3
"""Write extracts/<target>.sqlite: the tables that target writes, as they stand in
data/roadless.sqlite now, for `make jump` (docs/limit-and-jump.md). New.

Run in the clone after a step is proven, so a reader can load its rows
 instead of running it:

    uv run python scripts/dump_extract.py --target floor
    make extract STEP=floor

The extract holds each table as CREATE TABLE AS over the file's rows (the
columns a reader can insert; the one generated column is left out), no
indexes. The file is refused if it exists; --force replaces it.
"""
import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from shared import db, steps  # noqa: E402

EXTRACTS_DIR = _REPO_ROOT / "extracts"


def dump(target, force=False):
    tables = steps.TABLES.get(target)
    if tables is None:
        raise SystemExit(f"no step {target!r}; the steps are: {', '.join(steps.TARGETS)}")
    if target in steps.NOT_EXTRACTED:
        raise SystemExit(f"make {target} is not extracted: the corpus is rebuilt from the"
                         " download in csv/, and the fetch writes files")
    EXTRACTS_DIR.mkdir(exist_ok=True)
    out = EXTRACTS_DIR / f"{target}.sqlite"
    if out.exists():
        if not force:
            raise SystemExit(f"{out} exists; pass --force to replace it")
        out.unlink()
    conn = db.connect(db.DB_PATH)
    present = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    missing = [t for t in tables if t not in present]
    if missing:
        raise SystemExit(f"{', '.join(missing)}: not in {db.DB_PATH}; run make {target} first")
    print(f"extract of make {target}: {len(tables)} table(s) from {db.DB_PATH} to {out}", flush=True)
    conn.execute("ATTACH ? AS ext", (str(out),))
    for t in tables:
        cols = ", ".join(f'"{c}"' for c in steps.columns(conn, t))
        conn.execute(f'CREATE TABLE ext."{t}" AS SELECT {cols} FROM main."{t}"')
        n = conn.execute(f'SELECT count(*) FROM ext."{t}"').fetchone()[0]
        print(f"  {t}: {n:,} rows", flush=True)
    conn.commit()
    conn.execute("DETACH ext")
    conn.close()
    print(f"wrote {out}: {os.path.getsize(out) / 1e6:,.1f} MB")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--target", required=True, choices=steps.TARGETS, metavar="STEP",
                    help="the make target whose tables to extract")
    ap.add_argument("--force", action="store_true", help="replace an existing extract")
    args = ap.parse_args(argv)
    dump(args.target, force=args.force)


if __name__ == "__main__":
    main()
