#!/usr/bin/env python3
"""Jump to a step: load the stored rows for every step up to and including it
from extracts/<step>.sqlite, replacing what the file holds for those tables
(docs/limit-and-jump.md). New.

    uv run python scripts/load_extract.py --target floor
    make jump STEP=floor

The jump is cumulative on purpose: a step's rows are only right over the rows of
the steps before it. The corpus is not an extract (make corpus rebuilds it from
the download the repository ships) and must be loaded first; the fetch writes
files and is skipped, so a jump past it leaves attachments/ as it is. Every
extract needed is checked before anything is written. Foreign keys are off for
the load and checked whole at the end.
"""
import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

from shared import db, steps  # noqa: E402

EXTRACTS_DIR = _REPO_ROOT / "extracts"


def load(target):
    targets = [t for t in steps.up_to(target) if t not in steps.NOT_EXTRACTED]
    missing = [t for t in targets if not (EXTRACTS_DIR / f"{t}.sqlite").exists()]
    if missing:
        raise SystemExit("no extract for " + ", ".join(f"make {t}" for t in missing)
                         + f" under {EXTRACTS_DIR}; every step up to {target} needs one")
    conn = db.connect(db.DB_PATH)
    n_corpus = conn.execute("SELECT count(*) FROM comment").fetchone()[0]
    if n_corpus == 0:
        raise SystemExit(f"{db.DB_PATH} holds no comments: run make corpus first;"
                         " the corpus is not an extract")
    print(f"jump to make {target}: loading the stored rows for"
          f" {', '.join(targets)} from {EXTRACTS_DIR},"
          f" replacing what {db.DB_PATH} holds for those tables"
          + ("; make fetch is skipped, attachments/ is left as it is"
             if "fetch" in steps.up_to(target) else ""), flush=True)
    conn.execute("PRAGMA foreign_keys = OFF")
    for t in targets:
        path = EXTRACTS_DIR / f"{t}.sqlite"
        print(f"make {t}: {path}", flush=True)
        conn.execute("ATTACH ? AS ext", (str(path),))
        with conn.transaction():
            for table in steps.TABLES[t]:
                cols = ", ".join(f'"{c}"' for c in steps.columns(conn, table, "ext"))
                if table in steps.CREATED_AS:
                    conn.execute(f'DROP TABLE IF EXISTS main."{table}"')
                    conn.execute(f'CREATE TABLE main."{table}" AS SELECT {cols} FROM ext."{table}"')
                    n = conn.execute(f'SELECT count(*) FROM main."{table}"').fetchone()[0]
                    print(f"  {table}: built with {n:,} rows", flush=True)
                else:
                    before = conn.execute(f'SELECT count(*) FROM main."{table}"').fetchone()[0]
                    conn.execute(f'DELETE FROM main."{table}"')
                    conn.execute(f'INSERT INTO main."{table}" ({cols}) SELECT {cols} FROM ext."{table}"')
                    n = conn.execute(f'SELECT count(*) FROM main."{table}"').fetchone()[0]
                    print(f"  {table}: {before:,} rows replaced with {n:,}", flush=True)
        conn.execute("DETACH ext")
    bad = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()
    if bad:
        shown = "; ".join(f"{r[0]} rowid {r[1]} -> {r[2]}" for r in bad[:5])
        raise SystemExit(f"{len(bad):,} foreign key violation(s) after the load: {shown}")
    print(f"jumped to make {target}: {len(targets)} step(s) loaded, foreign keys checked")


def main(argv=None):
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--target", required=True, choices=steps.TARGETS, metavar="STEP",
                    help="load every step up to and including this one")
    args = ap.parse_args(argv)
    load(args.target)


if __name__ == "__main__":
    main()
