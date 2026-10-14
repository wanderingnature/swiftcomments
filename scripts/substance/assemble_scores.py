#!/usr/bin/env python3
"""Assemble family members' scores from the parts a scoring run produced.

A group in a family ({analysis}.comment_group.family_id IS NOT NULL: kinds
family and campaign, and an exact or middle class that is a family by
itself) is scored ONCE, on its analysis carrier's shared text. This step
writes the carrier's own row for every such group, and member rows for the
family and campaign kinds — exact and middle members are the same text as
their carrier and resolve through the group, as they always have:

  inherited  a member with no delta call of its own — the exemplar's score,
             verbatim, because that IS the text they submitted
  delta      a member whose own text was scored too — field-wise MAX of the
             exemplar's score and its own delta, per the instrument's own
             multi-issue rule (the strongest instance of each dimension
             anywhere in the comment)
  exemplar   the exemplar comment's own row, assembled the same way

Reads {analysis}.substance_score_parts (what each call actually returned,
never overwritten here) and writes {analysis}.substance_scores. Re-runnable:
the parts are the source, the member rows are derived.

Inherited rows are marked `scored_via = 'inherited'` and are EXCLUDED from
the concern ledger's gate-driven queues — a campaign's content is extracted
once, from its exemplar, not once per signer.

    python scripts/substance/assemble_scores.py --project roadless
    python scripts/substance/assemble_scores.py --project roadless --write
    make assemble        (this, then refresh_law.py's report)

Ported from rtca: reads and writes data/roadless.sqlite through shared/db.py;
the model whose parts are read is LLM_MODEL of .env unless --model says
otherwise (plan 5.2 edit 8).
"""

import argparse
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_HERE.parent))

from shared import db  # noqa: E402
from shared.instrument import SCORING_INSTRUMENT, configured_model, model_of, same_weights  # noqa: E402
from shared.project_context import add_project_argument, context_from_args  # noqa: E402

from score_comments import DIMS, band_for, next_steps, write_score_outputs  # noqa: E402


def _merge(exemplar, delta):
    """Field-wise max of two finalized records; gate/strength/band re-derived
    from the merged dimensions, exactly as finalize_record derives them."""
    base = dict(exemplar)
    ex_s, de_s = exemplar.get("scores", {}), (delta or {}).get("scores", {})
    scores = {d: max(int(ex_s.get(d) or 0), int(de_s.get(d) or 0)) for d in DIMS}
    base["scores"] = scores
    strength = sum(scores.values())
    gate_dims = [d for d in ("GAP", "EVID", "ALT", "LAW") if scores[d] >= 2]
    base["strength"] = strength
    base["strength_check"] = strength
    base["gate"] = len(gate_dims) > 0
    base["gate_basis"] = gate_dims
    base["band"] = band_for(strength)
    if delta:
        # Keep both rationales: the member's own text is what distinguishes
        # them from the rest of the campaign.
        base["rationale"] = (f"[shared text] {exemplar.get('rationale', '')}"
                             f" [own text] {delta.get('rationale', '')}")
        for key in ("moves", "targets", "topics"):
            merged = list(exemplar.get(key) or [])
            for v in (delta.get(key) or []):
                if v not in merged:
                    merged.append(v)
            base[key] = merged
        base["issue_count"] = max(int(exemplar.get("issue_count") or 0),
                                  int(delta.get("issue_count") or 0))
    return base


def parts_under(rows, model):
    """{part: {comment_id: record}} over the parts scored by the same weights
    as `model` (shared.instrument.same_weights); `rows` is (comment_id, part,
    model, record). A part from another model is another reader's answer:
    after the 2026-09-20 cutover 78 delta parts the 9B had scored under the
    old attribution still sat on current members, 72 of them on members who
    no longer own that text, and an unfiltered assembly merged them into a
    27B corpus."""
    parts = {}
    for cid, part, m, record in rows:
        if same_weights(m, model):
            parts.setdefault(part, {})[cid] = record
    return parts


def assemble(ctx, model):
    """(records, stats) — member rows derived from the scored parts, over the
    partition's campaign groups. The carrier and the membership are read from
    comment_group, the same answer the queue used, so nothing is re-clustered
    here. Only parts scored by `model`'s weights are read (parts_under)."""
    t0 = time.time()
    print(f"make assemble: reading the exemplar and delta parts under {SCORING_INSTRUMENT}"
          f" by {model_of(model)} and the partition's groups with a family; derives one"
          " row per member (exemplar, delta or inherited) for substance_scores", flush=True)
    with db.connect(**ctx.db_config) as conn:
        # PER INSTRUMENT. Unfiltered, this reads every generation's parts at
        # once and stamps each member row with whatever instrument_version its
        # EXEMPLAR part carried, so a v2 exemplar silently produces v2 member
        # rows in the middle of a v3 assembly — 193 exemplar and 668 delta
        # parts assembled into 32,849 rows of which 18 were v3.
        parts = parts_under([(cid, part, m, json.loads(record)) for cid, part, m, record
                             in conn.execute(ctx.render_sql(
                "SELECT comment_id, part, model, record"
                " FROM {analysis}.substance_score_parts"
                " WHERE instrument_version = ?"), (SCORING_INSTRUMENT,))],
            model)
        carrier_of = dict(tuple(r) for r in conn.execute(ctx.render_sql(
            "SELECT group_id, analysis_comment_id FROM {analysis}.comment_group"
            " WHERE family_id IS NOT NULL")))
        # Member rows for the family and campaign kinds only; an exact or
        # middle group with a family gets its carrier's row and nothing else.
        members = {}
        for cid, gid in conn.execute(ctx.render_sql(
                "SELECT m.comment_id, m.group_id"
                " FROM {analysis}.comment_group_member m"
                " JOIN {analysis}.comment_group g USING (group_id)"
                " WHERE g.family_id IS NOT NULL"
                " AND g.group_kind IN ('family', 'campaign')")):
            members.setdefault(gid, []).append(cid)
    if not carrier_of:
        raise SystemExit(
            "comment_group holds no groups with a family — run"
            " scripts/substance/build_comment_groups.py --rebuild --write first.")
    print(f"  {len(carrier_of):,} groups with a family, "
          + ", ".join(f"{len(v):,} {k}" for k, v in sorted(parts.items()))
          + f" part(s), loaded in {time.time() - t0:.0f}s\n", flush=True)
    ex_parts = parts.get("exemplar", {})
    de_parts = parts.get("delta", {})

    records = []
    stats = {"clusters": 0, "unscored_clusters": 0, "inherited": 0,
             "delta": 0, "exemplar": 0}
    for gid, carrier in carrier_of.items():
        stats["clusters"] += 1
        exemplar = ex_parts.get(carrier) if carrier is not None else None
        if exemplar is None:
            stats["unscored_clusters"] += 1
            continue
        for cid in sorted(members.get(gid, [carrier])):
            delta = de_parts.get(cid)
            rec = _merge(exemplar, delta)
            rec["comment_id"] = cid
            rec["was_floored"] = False
            rec["exemplar_id"] = carrier
            rec["instrument_version"] = exemplar.get("instrument_version")
            if cid == carrier:
                rec["scored_via"] = "exemplar"
                # substance_scores_exemplar_presence is an EQUIVALENCE: only
                # inherited/delta rows may carry an exemplar_id. The exemplar
                # IS the exemplar — a self-reference is rejected.
                rec["exemplar_id"] = None
                stats["exemplar"] += 1
            elif delta:
                rec["scored_via"] = "delta"
                stats["delta"] += 1
            else:
                rec["scored_via"] = "inherited"
                stats["inherited"] += 1
            records.append(rec)
    return records, stats


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(p)
    p.add_argument("--write", action="store_true",
                   help="upsert the assembled member rows into"
                        " substance_scores (default: report only)")
    p.add_argument("--model", default=None,
                   help="the model the parts were scored by (default LLM_MODEL of .env);"
                        " parts from other weights are not read (shared.instrument.same_weights)")
    args = p.parse_args()
    ctx = context_from_args(args)
    args.model = args.model or configured_model()

    records, stats = assemble(ctx, args.model)
    print(f"clusters {stats['clusters']} ({stats['unscored_clusters']} with no"
          f" scored exemplar — nothing written for those)")
    print(f"member rows: exemplar {stats['exemplar']}, delta {stats['delta']},"
          f" inherited {stats['inherited']} = {len(records)}")
    if records:
        gated = sum(1 for r in records if r["gate"])
        print(f"gate=true after assembly: {gated} ({100 * gated / len(records):.1f}%)")

    if not args.write:
        print("report only — pass --write to upsert into substance_scores")
        return
    if not records:
        raise SystemExit("Nothing to assemble — score the exemplars first.")
    # A comment scored in its own right that now sits in a cluster without
    # a delta part would be written 'inherited' — and inherited rows leave
    # the concern ledger. For a class-A comment that is a delta call the
    # scoring queue owes and has not landed: refuse, no override. For a
    # comment the screen does not class A, it is the screen taking effect on
    # a row scored before the screen was final: say so and proceed
    # (docs/plans/corpus-growth-incremental-ledger.md, E).
    with db.connect(**ctx.db_config) as conn:
        existing = dict(tuple(r) for r in conn.execute(ctx.render_sql(
            "SELECT comment_id, scored_via FROM {analysis}.substance_scores"
            " WHERE instrument_version = ?"), (SCORING_INSTRUMENT,)))
        screen = dict(tuple(r) for r in conn.execute(ctx.render_sql(
            "SELECT comment_id, screen_class FROM {analysis}.substance_screen")))
        own = dict(tuple(r) for r in conn.execute(ctx.render_sql(
            "SELECT comment_id, has_own_text FROM {analysis}.comment_group_member")))
    demoted = [r["comment_id"] for r in records
               if r["scored_via"] == "inherited"
               and existing.get(r["comment_id"]) in ("direct", "delta")]
    # A delta is owed only to a member with own text; a member whose whole
    # text is the family's is inherited by design, whatever its class. After
    # the cutover two class-A members held a delta from the old attribution
    # and no own text under the new one, and the refusal named them.
    demoted_a = [c for c in demoted if screen.get(c) == "A" and own.get(c)]
    if demoted_a:
        raise SystemExit(
            f"{len(demoted_a)} class-A comment(s) with own text would be demoted"
            " to inherited: their delta call has not landed. Run the scoring"
            " batch to completion before assembling. All of them:\n  "
            + "\n  ".join(demoted_a))
    if demoted:
        print(f"{len(demoted)} comment(s) leave the ledger as inherited: not"
              " class A, or no own text under the current attribution."
              " All of them:\n  " + "\n  ".join(demoted), flush=True)
    # Every assembled row is the model's whose parts it was built from —
    # stamped with the model's own name, like a direct row. Until 2026-09-22
    # these rows carried no model at all (migration 0051 backfilled them).
    write_score_outputs(ctx, records, model=model_of(args.model))
    print(f"upserted {len(records)} member rows into"
          f" {ctx.analysis_schema}.substance_scores")
    next_steps(("make rate",
                f"rate every eligible comment under instrument"
                f" {SCORING_INSTRUMENT}; the ledger and the reports read that"
                " run, and there is no rating for these rows yet."))


if __name__ == "__main__":
    main()
