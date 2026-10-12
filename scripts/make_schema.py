#!/usr/bin/env python3
"""Create data/roadless.sqlite from schema/roadless.sql and load the seeds that are
rows of the profile: the sentiment meanings, the topics, the two prompts
(seeds/roadless_profile.sql, seeds/roadless_prompt_v2.sql) and the vocabulary
(seeds/vocabulary.csv). The reference lists and the entity seeds are loaded by
scripts/entity_tagging/load_references.py in `make tag`.

    uv run python scripts/make_schema.py            # refuses an existing file
    uv run python scripts/make_schema.py --force    # replaces it

Refuses a SQLite library older than 3.38 (shared/db.py). Prints what it made.
"""
import argparse
import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import db  # noqa: E402

SEEDS = db.REPO_ROOT / "seeds"
PROFILE_SEEDS = ("roadless_profile.sql", "roadless_prompt_v2.sql")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--force", action="store_true",
                        help="replace an existing data/roadless.sqlite")
    args = parser.parse_args()
    db.require_sqlite()

    path = db.DB_PATH
    if path.exists():
        if not args.force:
            raise SystemExit(f"{path} exists; delete it or pass --force to start over.")
        for p in (path, path.with_name(path.name + "-wal"), path.with_name(path.name + "-shm")):
            if p.exists():
                p.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    for name in PROFILE_SEEDS:
        conn.executescript((SEEDS / name).read_text(encoding="utf-8"))
    with open(SEEDS / "vocabulary.csv", newline="", encoding="utf-8") as fh:
        rows = [(r["kind"], r["code"], r["label"], r["meaning"], int(r["ordinal"]),
                 int(r["lo"]) if r["lo"] else None, int(r["hi"]) if r["hi"] else None)
                for r in csv.DictReader(fh)]
    conn.executemany(
        "INSERT INTO vocabulary (kind, code, label, meaning, ordinal, lo, hi)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    conn.commit()

    tables = conn.execute("SELECT count(*) FROM sqlite_master WHERE type = 'table'").fetchone()[0]
    views = conn.execute("SELECT count(*) FROM sqlite_master WHERE type = 'view'").fetchone()[0]
    topics = conn.execute("SELECT count(*) FROM topics WHERE is_active").fetchone()[0]
    prompt = conn.execute("SELECT prompt_name FROM prompts WHERE is_active").fetchone()[0]
    vocab = conn.execute("SELECT count(*) FROM vocabulary").fetchone()[0]
    conn.close()
    print(f"{path}: SQLite {sqlite3.sqlite_version}, {tables} tables, {views} views;"
          f" {topics} active topics, active prompt {prompt}, {vocab} vocabulary rows")


if __name__ == "__main__":
    main()
