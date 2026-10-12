#!/usr/bin/env python3
"""Load the entity-tagging reference tables for one project.

Design: docs/design/comment-entity-tagging.md. Truncate-and-reload (idempotent —
nothing references these tables; tags carry values, not FKs):

- forests / roadless_areas / species: the lists in seeds/ (plan 5.2, edit 4),
  read once from the upstream roadless database with the canonical forest-name
  transform applied; here they are loaded as they are.
- legal_authority / cited_references: the DEIS-derived seed CSVs in
  seeds/entity_tagging/.
- zipcodes: purely discovered at enrichment time — nothing to load, left alone.

Usage:
    python scripts/entity_tagging/load_references.py --project roadless
"""

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared import db  # noqa: E402
from shared.project_context import ProjectContext, add_project_argument, context_from_args  # noqa: E402

SEED_DIR = REPO_ROOT / "seeds" / "entity_tagging"
LIST_DIR = REPO_ROOT / "seeds"


def canonical_forest(name: str) -> str:
    """The canonical rule: spelled-out National Forest(s), never NF/NFs, and the
    Idaho Panhandle merge (one USFS entity under two source spellings)."""
    if name.endswith(" NFs"):
        name = name[: -len(" NFs")] + " National Forests"
    elif name.endswith(" NF"):
        name = name[: -len(" NF")] + " National Forest"
    if name == "Idaho Panhandle National Forest":
        name = "Idaho Panhandle National Forests"
    return name


def _read_list(filename: str) -> list[dict]:
    path = LIST_DIR / filename
    if not path.exists():
        raise SystemExit(f"Reference list missing: {path}")
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_from_source(ctx: ProjectContext, cur) -> None:
    forests = _read_list("forests.csv")
    areas = _read_list("roadless_areas.csv")
    species = _read_list("species.csv")

    cur.execute("DELETE FROM {analysis}.forests")
    cur.executemany(
        "INSERT INTO {analysis}.forests (id, name) VALUES (?, ?)",
        [(int(f["id"]), f["name"]) for f in forests])

    cur.execute("DELETE FROM {analysis}.roadless_areas")
    cur.executemany(
        "INSERT INTO {analysis}.roadless_areas"
        " (id, name, forest, state, state_name, acres)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        [(int(a["id"]), a["name"], canonical_forest(a["forest"]), a["state"] or None,
          a["state_name"] or None, float(a["acres"]) if a["acres"] else None) for a in areas])

    cur.execute("DELETE FROM {analysis}.species")
    cur.executemany(
        "INSERT INTO {analysis}.species"
        " (id, primary_common_name, scientific_name, usesa_code, rounded_g_rank,"
        "  area_count, state_count, states)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(int(s["id"]), s["primary_common_name"], s["scientific_name"],
          s["usesa_code"] or None, s["rounded_g_rank"] or None,
          int(s["area_count"]) if s["area_count"] else None,
          int(s["state_count"]) if s["state_count"] else None,
          s["states"] or None) for s in species])

    print(f"forests: {len(forests)} rows")
    print(f"roadless_areas: {len(areas)} rows")
    print(f"species: {len(species)} rows")


def _read_seed(filename: str) -> list[dict]:
    path = SEED_DIR / filename
    if not path.exists():
        raise SystemExit(f"Seed file missing: {path}")
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def load_seeds(cur) -> None:
    # Seed rows only — discovered rows (seed_id IS NULL) are enrichment output,
    # not seed data, and must survive a reload.
    rows = _read_seed("seed_legal_authority.csv")
    cur.execute("DELETE FROM {analysis}.legal_authority WHERE seed_id IS NOT NULL")
    cur.executemany(
        "INSERT INTO {analysis}.legal_authority"
        " (seed_id, type, display, citation, case_name, match_keys, cite_role,"
        "  status, summary)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(r["seed_id"], r["type"] or None, r["display"], r["citation"] or None,
          r["case_name"] or None, r["match_keys"] or None, r["cite_role"] or None,
          r["status"] or None, r["summary"] or None) for r in rows])
    print(f"legal_authority: {len(rows)} seed rows")

    rows = _read_seed("seed_reference.csv")
    cur.execute("DELETE FROM {analysis}.cited_references WHERE seed_id IS NOT NULL")
    cur.executemany(
        "INSERT INTO {analysis}.cited_references"
        " (seed_id, type, display, citation_key, match_keys, authors, year,"
        "  title, publisher, url, raw_text)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(r["seed_id"], r["type"] or None, r["display"], r["citation_key"] or None,
          r["match_keys"] or None, r["authors"] or None, r["year"] or None,
          r["title"] or None, r["publisher"] or None, r["url"] or None,
          r["raw_text"] or None) for r in rows])
    print(f"cited_references: {len(rows)} seed rows")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(parser)
    args = parser.parse_args()
    ctx = context_from_args(args)

    with db.connect(**ctx.db_config) as conn:
        with conn.cursor() as raw_cur:
            cur = _Rendering(raw_cur, ctx)
            load_from_source(ctx, cur)
            load_seeds(cur)
        conn.commit()
    print("Reference load complete (single transaction, committed).")


class _Rendering:
    """Token-rendering cursor wrapper ({analysis} / {src})."""

    def __init__(self, cursor, ctx: ProjectContext):
        self._cursor = cursor
        self._ctx = ctx

    def execute(self, query: str, params=None):
        return self._cursor.execute(self._ctx.render_sql(query), params or ())

    def executemany(self, query: str, params_seq):
        return self._cursor.executemany(self._ctx.render_sql(query), params_seq)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


if __name__ == "__main__":
    main()
