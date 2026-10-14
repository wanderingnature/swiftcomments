#!/usr/bin/env python3
"""Make every stored LAW agree with the confirmed-citation tags, mechanically.

LAW is mechanical under v3: finalize_record sets it to 2 when the entity-tagging pass
(scripts/entity_tagging/run_pass.py) confirmed a legal-authority citation in the text the
item scored — the submitter's own text for a direct or delta item, the family's shared
text for an exemplar (score_comments.law_sets, law_cited_for) — else 0, and discards the
model's value. A score is final when written, so a comment scored before its tags existed
keeps LAW 0 after the tags land. On 2026-10-07 the tagging pass had last run on 2026-09-15
and every v3 score was written after that: 197,989 comments were unscanned, and once they
were, 804 direct rows with a confirmed citation still held LAW 0.

This step re-derives LAW for every stored v3 row from the tags as they stand, through the
same own/shared split scoring uses, and rewrites exactly what finalize_record and
apply_v3_grade derive from it: strength, gate, gate_basis, band, and the T4 target. No
model call; no other field changes. Direct rows are updated in substance_scores; exemplar
and delta parts in substance_score_parts (the columns and the stored record), and the
member rows derived from them are rebuilt by assemble_scores.py, which this step names
next, with answerability.py after it.

    uv run python scripts/substance/refresh_law.py --project roadless
    uv run python scripts/substance/refresh_law.py --project roadless --write
    make assemble        (the assembler, then this report)

Ported from rtca: reads and writes data/roadless.sqlite through shared/db.py.
In a run from empty the tags precede the scoring (make tag before make score-model),
so this finds nothing to change and says so; it is here for a file whose tags
were rebuilt after a score was written.
"""

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_HERE.parent))

from shared import db  # noqa: E402
from shared.instrument import SCORING_INSTRUMENT  # noqa: E402
from shared.project_context import add_project_argument, context_from_args  # noqa: E402

import shared_text  # noqa: E402
from score_comments import DIMS, band_for, law_cited_for, law_sets, next_steps  # noqa: E402


def derived(scores: dict) -> tuple[int, list[str]]:
    """(strength, gate_basis) as finalize_record derives them from the eight dimensions."""
    s = {d: int(scores.get(d) or 0) for d in DIMS}
    return sum(s.values()), [d for d in ("GAP", "EVID", "ALT", "LAW") if s[d] >= 2]


def refreshed(scores: dict, targets, law: int) -> dict | None:
    """The fields that follow from LAW, re-derived for `law`: None when the stored LAW
    already is `law`. The arithmetic is finalize_record's; T4 is apply_v3_grade's
    target.T4_from_law, so it is present exactly when LAW is 2."""
    s = {d: int(scores.get(d) or 0) for d in DIMS}
    if s["LAW"] == law:
        return None
    s["LAW"] = law
    strength, gate_dims = derived(s)
    kept = {t for t in (targets or []) if t != "T4"}
    if law == 2:
        kept.add("T4")
    return {"scores": s, "strength": strength, "strength_check": strength,
            "gate": len(gate_dims) > 0, "gate_basis": gate_dims,
            "band": band_for(strength), "targets": sorted(kept)}


class Change:
    """One stored row whose LAW disagrees with the tags. `part` is 'direct' for a
    substance_scores row, 'exemplar' or 'delta' for a substance_score_parts row."""

    def __init__(self, table, comment_id, part, scores, fields):
        self.table, self.comment_id, self.part = table, comment_id, part
        self.old_law = int(scores.get("LAW") or 0)
        self.old_strength, old_basis = derived(scores)
        self.old_gate = len(old_basis) > 0
        self.new_law = fields["scores"]["LAW"]
        self.fields = fields


def plan(ctx):
    """Every stored v3 row whose LAW disagrees with the tags, as Changes, plus the counts
    of direct rows and parts read."""
    print(f"make assemble, the LAW check: reading every {SCORING_INSTRUMENT} row and part,"
          " the shared text and the confirmed citations; LAW is re-derived from the tags"
          " and the rows that disagree are listed", flush=True)
    with db.connect(**ctx.db_config) as conn:
        shapes = shared_text.load_shapes(conn, ctx.render_sql)
        direct = [tuple(r) for r in conn.execute(ctx.render_sql(
            "SELECT comment_id, place, stand, doc, gap, evid, ask, alt, law, targets"
            " FROM {analysis}.substance_scores"
            " WHERE instrument_version = ? AND scored_via = 'direct'"
            " ORDER BY comment_id"), (SCORING_INSTRUMENT,))]
        parts = [(cid, part, json.loads(record)) for cid, part, record in conn.execute(ctx.render_sql(
            "SELECT comment_id, part, record"
            " FROM {analysis}.substance_score_parts"
            " WHERE instrument_version = ?"
            " ORDER BY comment_id, part"), (SCORING_INSTRUMENT,))]
    own_law, shared_law = law_sets(ctx, shapes)

    changes: list[Change] = []
    for cid, *dims, targets in direct:
        targets = json.loads(targets) if isinstance(targets, str) else targets
        scores = dict(zip(DIMS, dims))
        law = 2 if cid in law_cited_for("unique", own_law, shared_law) else 0
        fields = refreshed(scores, targets, law)
        if fields:
            changes.append(Change("substance_scores", cid, "direct", scores, fields))
    for cid, part, record in parts:
        scores = record.get("scores") or {}
        law = 2 if cid in law_cited_for(part, own_law, shared_law) else 0
        fields = refreshed(scores, record.get("targets"), law)
        if fields:
            changes.append(Change("substance_score_parts", cid, part, scores, fields))
    return changes, len(direct), len(parts)


_SCORE_UPDATE = (
    "UPDATE {analysis}.substance_scores SET law = ?, strength = ?, strength_check = ?,"
    " gate = ?, gate_basis = ?, band = ?, targets = ?"
    " WHERE comment_id = ? AND instrument_version = ? AND scored_via = 'direct'")

# jsonb's `record || patch` replaces each top-level key the patch carries;
# json_patch does the same for an object patch (RFC 7396), arrays replaced whole.
_PART_UPDATE = (
    "UPDATE {analysis}.substance_score_parts SET law = ?, strength = ?, gate = ?,"
    " band = ?, record = json_patch(record, ?)"
    " WHERE comment_id = ? AND part = ? AND instrument_version = ?")


def write(ctx, changes: list[Change]) -> None:
    """Apply every change in one transaction."""
    scores_rows, part_rows = [], []
    for c in changes:
        f = c.fields
        if c.table == "substance_scores":
            scores_rows.append((c.new_law, f["strength"], f["strength_check"], f["gate"],
                                json.dumps(f["gate_basis"]), f["band"], json.dumps(f["targets"]),
                                c.comment_id, SCORING_INSTRUMENT))
        else:
            part_rows.append((c.new_law, f["strength"], f["gate"], f["band"], json.dumps(f),
                              c.comment_id, c.part, SCORING_INSTRUMENT))
    with db.connect(**ctx.db_config) as conn:
        with conn.cursor() as cur:
            if scores_rows:
                cur.executemany(ctx.render_sql(_SCORE_UPDATE), scores_rows)
            if part_rows:
                cur.executemany(ctx.render_sql(_PART_UPDATE), part_rows)
        conn.commit()


def _gate(open_: bool) -> str:
    return "open" if open_ else "closed"


def report(changes: list[Change], n_direct: int, n_parts: int) -> None:
    """The id list first, the summary last: the list is as long as the change set."""
    print(f"{n_direct:,} direct row(s) and {n_parts:,} part(s) under instrument"
          f" {SCORING_INSTRUMENT}; {len(changes):,} disagree with the tags.")
    if not changes:
        return
    print("All of them (stored -> derived):")
    for c in changes:
        print(f"  {c.table} {c.comment_id} {c.part}: LAW {c.old_law} -> {c.new_law},"
              f" strength {c.old_strength} -> {c.fields['strength']},"
              f" gate {_gate(c.old_gate)} -> {_gate(c.fields['gate'])}")
    by: dict[tuple, list[int]] = {}
    for c in changes:
        n = by.setdefault((c.table, c.part, c.old_law, c.new_law), [0, 0, 0])
        n[0] += 1
        n[1] += int(not c.old_gate and c.fields["gate"])
        n[2] += int(c.old_gate and not c.fields["gate"])
    print("\nSummary:")
    for (table, part, old, new), (n, opened, closed) in sorted(by.items()):
        print(f"  {table} {part}: LAW {old} -> {new}: {n:,} row(s),"
              f" gate opened {opened:,}, gate closed {closed:,}")


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(p)
    p.add_argument("--write", action="store_true",
                   help="apply the changes (default: report only)")
    args = p.parse_args()
    ctx = context_from_args(args)

    changes, n_direct, n_parts = plan(ctx)
    report(changes, n_direct, n_parts)
    if not args.write:
        print("\nreport only — pass --write to apply")
        return
    if not changes:
        print("nothing to write")
        return
    write(ctx, changes)
    n_scores = sum(1 for c in changes if c.table == "substance_scores")
    print(f"\nupdated {n_scores:,} substance_scores row(s) and {len(changes) - n_scores:,}"
          f" substance_score_parts row(s) in {ctx.analysis_schema}")
    next_steps(
        ("make assemble",
         "the exemplar, delta and inherited rows in substance_scores are derived from the"
         " parts; rebuild them from the refreshed parts."),
        ("make rate",
         "A1 keys off LAW == 2 and the gate changed; re-rate every eligible comment in"
         " place."))


if __name__ == "__main__":
    main()
