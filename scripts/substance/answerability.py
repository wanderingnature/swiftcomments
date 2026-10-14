#!/usr/bin/env python3
"""The answerability rating — a READ-TIME transform over the scores already stored.

It does not re-score, and it changes nothing it reads: not the rubric, the 0-3
assignment, the gate rule, the stored columns, raw strength or its four bands.
It reads {analysis}.substance_scores and computes a second rating on top of it,
per tmp/answerability-rating.md.

Why a second rating: raw strength answers HOW MUCH IS IN THIS COMMENT. It does
not answer CAN THE AGENCY DISMISS IT. The substantive gate (7 CFR 1b.11(a)(53))
is disjunctive -- finalize_record fires it when any one of GAP/EVID/ALT/LAW
reaches 2 -- but the four limbs are unequally able to survive the dismissal
repertoire, and raw strength sums an OR-test together with a conjunctive form
test, so a 3 on one dimension covers a 0 on another.

Two modes. The default samples per band and prints each comment with its full
derivation, so the ratings can be judged against real comments. --write rates
every eligible comment into {analysis}.answerability_run /
substance_answerability (0040/0041) and prints the corpus grid.

  uv run python scripts/substance/answerability.py --project <slug> --limit 3
  uv run python scripts/substance/answerability.py --project <slug> --write
  make rate

Nothing in substance_scores is ever written: the rating reads it and writes only
its own two tables. Run by the operator.

Ported from rtca: reads and writes data/roadless.sqlite through shared/db.py;
the JSON columns (moves, targets, gate_basis; the stored lists) are read and
written as JSON text; --seed is gone, SQLite's random() takes no seed.
"""

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from shared.instrument import SCORING_INSTRUMENT
from shared.project_context import dict_connect, add_project_argument, context_from_args

DIMS = ["PLACE", "STAND", "DOC", "GAP", "EVID", "ASK", "ALT", "LAW"]
BANDS = ["minimal", "marginal", "developed", "strong"]
SAMPLE_DEFAULT = 3

# Which limb of (a)(53) each dimension reaches, at which value. THE single
# source of limb truth: the booleans rate() decides on and the labels the
# derivation prints both come from here, so a display and a stored value cannot
# drift apart — the way GAP 3 was limb 2 in the table and limb 1+2 in the array
# until they were hand-synced.
#
# GAP is the one dimension that changes limb with its level: limb 1 at 2, limb 2
# at 3 (and NOT limb 1 as well), because the instrument's own GAP-3 definition
# requires the consequence to propagate into a conclusion or significance
# determination. LAW emits only 0 or 2 once it is mechanical.
LIMB_AT = {
    "GAP": {2: 1, 3: 2},
    "EVID": {2: 1, 3: 1},
    "ALT": {2: 3, 3: 3},
    "LAW": {2: 4},
}
LIMB_LABEL = {
    1: "limb 1 (deficiency named / evidence offered)",
    2: "limb 2 (consequence propagates)",
    3: "limb 3 (alternative)",
    4: "limb 4 (legal authority)",
}


def limbs_reached(scores):
    """{1..4: bool} — which limbs of (a)(53) this comment's scores reach.

    LIMB_AT is an exact-value lookup, so a gate-firing value it does not cover
    would silently reach no limb and surface later as a gate disagreement that
    blames the gate. A value at or above 2 with no mapping fails here instead,
    naming itself — LAW 3 is the live case: the instrument makes LAW mechanical
    (0 or 2) from v2, so a 3 means something upstream stopped doing that.
    """
    hit = {n: False for n in LIMB_LABEL}
    for d, by_value in LIMB_AT.items():
        if scores[d] >= 2 and scores[d] not in by_value:
            raise SystemExit(
                f"{d} = {scores[d]} fires the gate but reaches no limb:"
                f" LIMB_AT[{d!r}] covers {sorted(by_value)}. The rating cannot"
                " say which limb that is, and guessing one would invent the"
                " answer.")
        limb = by_value.get(scores[d])
        if limb is not None:
            hit[limb] = True
    return hit
FORM_TEST = {
    "PLACE": "form -- specificity / direct relationship (36 CFR 219.62, 218.2)",
    "DOC": "form -- nexus to the proposal",
    "ASK": "1b.7(f)(1) recommendation trigger",
    "STAND": "no regulatory test",
}

# CALIBRATION POINT 1 of 2 -- the weights.
#
# The four choices the document fixes: STAND contributes nothing (it serves no
# regulatory test, and excluding it stops sentiment inflating the rating); LAW
# takes the top weight (limb 4 defeats addressed_in_analysis, no_cause_effect
# and 1b.7(j) at once) and must carry its 0-or-2 ceiling or it under-contributes
# by a third; GAP splits by level; PLACE/DOC/ASK stay at or near 1 because they
# defeat specific dismissals without making a comment answerable.
#
# The magnitudes below satisfy those four constraints and nothing more. Their
# empirical source is the ledger's own predicted dispositions per bucket, which
# is a calibration run, not a guess to be defended -- this table is the single
# edit that calibration changes.
WEIGHTS = {"PLACE": 1.0, "STAND": 0.0, "DOC": 1.0, "ASK": 1.0,
           "EVID": 2.0, "ALT": 2.0, "LAW": 3.0}
# Bump this whenever WEIGHTS or GAP_CONTRIB changes. It is stored on every run
# (answerability_run.weights_version), which is what makes a stored rating
# readable later -- the same job instrument_version does for a score.
WEIGHTS_VERSION = "w1"
# GAP is not value x weight: level 3 is a different limb than level 2, so it
# contributes by level. Level 2 matches EVID at 2 (both reach limb 1); level 3
# is weighted above limb 1 because limb 2 survives no_cause_effect.
GAP_CONTRIB = {0: 0.0, 1: 2.0, 2: 4.0, 3: 7.5}

# CALIBRATION POINT 2 of 2 -- the A2 limb-1 branch.
#
# A1/A2-via-limb-2-or-3/A3/A0 read straight off the stored dimension values.
# The remaining branch -- "limb 1 with a stated mechanism and a cite" -- needs
# two signals the eight dimensions do not carry directly. Both are taken from
# data the pipeline already persists, never re-derived from text:
#   mechanism: substance_scores.moves / .targets, the instrument's M1-M5 / T1-T4
#              taxonomy. A causal or analytic move (accuracy questioned, new
#              information, missing analysis) aimed at effects or the
#              significance determination.
#   cite:      DOC >= 2 (the comment cites the EA) or substance_floor.has_citation
#              (the mechanical scan found a citation). NOT the legal-authority
#              citation -- that is LAW, and LAW == 2 is already A1.
# Every run prints which of these fired, so the operationalization is judged on
# real comments rather than asserted here.
MECHANISM_MOVES = {"M1", "M3", "M5"}
MECHANISM_TARGETS = {"T1", "T2"}

# The nine no-action dispositions of the v6 vocabulary, in the concession
# ordering the rollup view uses (ranks 6-14 of concern_v6_regime.sql; ranks 1-5
# are concessions and rank 15 is the legacy umbrella `no_action_needed`, kept
# valid for v2/v3 rows and not a v6 outcome).
#
# The A-level is a claim about WHICH of these a comment's text defeats. That set
# is the finding; the level is a label over it. Both are computed and both are
# emitted -- a comment that defeats three codes and one that defeats one are not
# the same comment, and collapsing them into a level would discard the
# difference at the point it is made.
NO_ACTION_CODES = [
    "alternative_eliminated", "addressed_in_analysis", "deferred_to_site_specific",
    "misinterpreted", "not_required", "policy_preference_noted",
    "no_cause_effect", "outside_scope", "certified_not_substantive",
]
# Codes the design defines no text-only test for. They are reported OPEN with
# that stated as the reason, never silently omitted: a later run with the DEIS
# in hand is what gives them a test (deferral needs the document's tiering
# language, alternative_eliminated needs its (h)(3) reasons), and the open/
# defeated delta between the two runs is only readable if this run records
# which codes it could not reach.
NO_TEXT_ONLY_TEST = {"alternative_eliminated", "deferred_to_site_specific",
                     "not_required", "policy_preference_noted"}


# WHO gets rated. The same predicate every other queue over substance_scores
# uses (concern_ledger.ELIGIBLE_SQL, build_comment_groups, extract_gold): an
# 'inherited' row is a campaign signer holding its EXEMPLAR's score, so rating
# it would rate the organizer's text once per signer and count one campaign
# tens of thousands of times in the corpus grid.
#
# Deliberately "<> 'inherited'", NOT "IN ('direct','exemplar')": a delta row is
# the member's own text max'd with its exemplar's — that IS the member's own
# analysis, not a copy wearing its name.
ELIGIBLE = "s.scored_via <> 'inherited'"

# v1 is not ratable. A1 — the top level — keys entirely off LAW == 2, and LAW is
# mechanical only from v2 onward (finalize_record takes it from the confirmed-
# citation scan and discards the model's). Under v1 the model invented LAW:
# validated 2026-09-08, only ~3-22% of v1 LAW scores had any detectable
# citation, so a v1 run would mint A1s out of register rather than law. The
# concern ledger pins SCORING_INSTRUMENT = 'v2' for the neighbouring reason —
# v1 and v2 gates are not comparable.
UNRATABLE_INSTRUMENTS = {"v1"}


def band_for(strength: int) -> str:
    """The stored band rule, recomputed for the derivation display.

    Copied deliberately from score_comments.band_for rather than imported: this
    script prints the arithmetic that produced the STORED value, and importing
    it would hide a drift between the two instead of showing it. The printed
    line compares against the stored band every time.
    """
    if strength <= 5:
        return "minimal"
    if strength <= 11:
        return "marginal"
    if strength <= 17:
        return "developed"
    return "strong"


def weighted(scores):
    """[(dimension, value, limb-or-test, weight, contribution)], total.

    The per-dimension trace IS the output -- the caller prints it. A bare total
    would be the thing the document says a single number hides.
    """
    rows, total = [], 0.0
    for d in DIMS:
        v = scores[d]
        if d == "GAP":
            contrib = GAP_CONTRIB[v]
            weight = "by level"
        else:
            contrib = v * WEIGHTS[d]
            weight = f"{WEIGHTS[d]:.1f}"
        limb = LIMB_AT.get(d, {}).get(v)
        reaches = LIMB_LABEL[limb] if limb else (FORM_TEST.get(d) or "-")
        rows.append((d, v, reaches, weight, contrib))
        total += contrib
    return rows, total


def rate(scores, moves, targets, has_citation):
    """The full rating for one comment.

    Returns a dict carrying everything the calculation produced: which limbs the
    text reaches, which of the nine no-action codes that defeats and WHY, which
    remain open and why, the two limb-1 signals, and the A-level derived from
    the defeated set.

    The order is deliberate: the dismissal codes are computed FIRST and the
    A-level falls out of them. The level is a label over the code set, not a
    parallel judgment -- so it can never disagree with the codes, and the codes
    survive whether or not anything reads the level.
    """
    s = scores
    hit = limbs_reached(s)
    limb1, limb2, limb3, limb4 = hit[1], hit[2], hit[3], hit[4]
    # Equivalent to finalize_record's gate (any of GAP/EVID/ALT/LAW >= 2), since
    # LIMB_AT maps every one of those values to a limb. Checked against the
    # stored gate by rating_row rather than assumed.
    gated = any(hit.values())

    mv = sorted(set(moves or []) & MECHANISM_MOVES)
    tg = sorted(set(targets or []) & MECHANISM_TARGETS)
    mechanism = bool(mv and tg)
    cite = s["DOC"] >= 2 or bool(has_citation)
    form = s["PLACE"] >= 2 or s["DOC"] >= 2

    # Each entry: code -> (defeated?, why). Every one of the nine is decided;
    # none is skipped, and a code with no text-only test says so in its reason.
    verdict = {}
    verdict["addressed_in_analysis"] = (
        limb4,
        "limb 4 -- there is no analysis to cite against a statutory claim" if limb4
        else "open -- only the DEIS itself can show whether the analysis addresses it")
    verdict["certified_not_substantive"] = (
        limb4,
        "1b.7(j) foreclosed -- alleging illegality is substantive by the definition"
        " the certification runs on" if limb4
        else "open -- the (j) certification is available to the agency")
    nce = limb4 or limb2 or limb3 or (limb1 and mechanism and cite)
    verdict["no_cause_effect"] = (
        nce,
        ("reaches a limb a no-cause-effect rationale cannot touch"
         f" (limb4 {limb4}, limb2 {limb2}, limb3 {limb3},"
         f" limb1+mechanism+cite {limb1 and mechanism and cite})") if nce
        else "open -- limb 1 alone, with no stated mechanism carrying a cite")
    for code in ("outside_scope", "misinterpreted"):
        verdict[code] = (
            form,
            f"PLACE {s['PLACE']} / DOC {s['DOC']} -- specific and tied to the proposal"
            if form else f"open -- PLACE {s['PLACE']}, DOC {s['DOC']}")
    for code in sorted(NO_TEXT_ONLY_TEST):
        verdict[code] = (False, "open -- no text-only test; needs the DEIS")

    if not gated:
        # Nothing is defeated by a comment that is not substantive at all.
        verdict = {c: (False, "open -- gate false, the comment is counted, not answered")
                   for c in NO_ACTION_CODES}

    defeated = [c for c in NO_ACTION_CODES if verdict[c][0]]
    still_open = [c for c in NO_ACTION_CODES if not verdict[c][0]]

    if not gated:
        level = "A0"
    elif "addressed_in_analysis" in defeated:
        level = "A1"
    elif "no_cause_effect" in defeated:
        level = "A2"
    else:
        level = "A3"

    return {
        "level": level,
        "gated": gated,
        "limbs": {"limb1": limb1, "limb2": limb2, "limb3": limb3, "limb4": limb4},
        "mechanism": mechanism, "mechanism_moves": mv, "mechanism_targets": tg,
        "cite": cite,
        "cite_via": ([c for c in ("doc" if s["DOC"] >= 2 else None,
                                  "floor_citation" if has_citation else None) if c]),
        "defeated": defeated, "open": still_open, "verdict": verdict,
    }


A_MEANING = {
    "A1": "addressed_in_analysis and certified_not_substantive both defeated",
    "A2": "no_cause_effect defeated; addressed_in_analysis still open",
    "A3": "substantive, but no no-action code is defeated",
    "A0": "gate false -- counted, not answered",
}


def sample(conn, render_sql, band, limit, instrument):
    """`limit` eligible comments from one band, with their full text.

    Filtered by the SAME eligibility AND instrument as a --write run, so what
    is eyeballed here is drawn from exactly the population that gets rated.

    Joined to v_source_comments the way shared_text.load_corpus does it, and to
    substance_floor for the mechanical citation flag.
    """
    return conn.execute(render_sql(
        "SELECT s.comment_id, s.band, s.strength, s.strength_check, s.gate,"
        " s.gate_basis, s.was_floored, s.scored_via, s.instrument_version,"
        " s.place, s.stand, s.doc, s.gap, s.evid, s.ask, s.alt, s.law,"
        " s.moves, s.targets, s.rationale,"
        " f.has_citation, v.comment_text"
        " FROM {analysis}.substance_scores s"
        " JOIN {analysis}.v_source_comments v USING (comment_id)"
        " LEFT JOIN {analysis}.substance_floor f USING (comment_id)"
        " WHERE " + ELIGIBLE
        + " AND s.instrument_version = ? AND s.band = ?"
        " ORDER BY random() LIMIT ?"), (instrument, band, limit)).fetchall()


_RUN_FIND = (
    "SELECT run_id FROM {analysis}.answerability_run"
    " WHERE rater = ? AND evidence = ? AND coalesce(deis_ref, '') = ?"
    "   AND weights_version = ? AND instrument_version = ?")

_RUN_INSERT = (
    "INSERT INTO {analysis}.answerability_run"
    " (rater, evidence, deis_ref, weights_version, instrument_version, note)"
    " VALUES (?, ?, ?, ?, ?, ?) RETURNING run_id")

_RATING_UPSERT = (
    "INSERT INTO {analysis}.substance_answerability"
    " (run_id, comment_id, a_level, gated, limbs_reached, answerability,"
    "  dismissals_defeated, dismissals_open, mechanism, mechanism_moves,"
    "  mechanism_targets, cite_via)"
    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    " ON CONFLICT (run_id, comment_id) DO UPDATE SET"
    " a_level=EXCLUDED.a_level, gated=EXCLUDED.gated,"
    " limbs_reached=EXCLUDED.limbs_reached, answerability=EXCLUDED.answerability,"
    " dismissals_defeated=EXCLUDED.dismissals_defeated,"
    " dismissals_open=EXCLUDED.dismissals_open, mechanism=EXCLUDED.mechanism,"
    " mechanism_moves=EXCLUDED.mechanism_moves,"
    " mechanism_targets=EXCLUDED.mechanism_targets, cite_via=EXCLUDED.cite_via")

# Small on purpose. Unlike a scoring run, nothing here costs anything per item
# -- it is arithmetic over values already in hand -- so the batch exists only to
# make executemany worth calling, and there is no reason to let a crash discard
# more than a few hundred rows of it.
FLUSH_EVERY = 500


def _list(value):
    """A stored JSON array (moves, targets, gate_basis) as a list; a list as given."""
    if value is None:
        return []
    return json.loads(value) if isinstance(value, str) else list(value)


def gate_drift(row, scores, r):
    """A message if the stored gate disagrees with the gate rule, else None.

    One comparison used by both modes: --write refuses to store a rating built
    on a drifted gate, and the sample prints the same finding instead of quietly
    showing an A-level that could never be stored.
    """
    if bool(row["gate"]) == r["gated"]:
        return None
    return (f"comment {row['comment_id']}: substance_scores.gate is"
            f" {row['gate']} but the gate rule over the stored dimensions gives"
            f" {r['gated']} (GAP {scores['GAP']}, EVID {scores['EVID']},"
            f" ALT {scores['ALT']}, LAW {scores['LAW']}). The scores and the"
            " gate have drifted; rating on either one would be a guess.")


def citation_flag(row):
    """substance_floor.has_citation for a scored comment, or a loud failure.

    The join to substance_floor is LEFT because a missing floor row is a broken
    invariant, not a case to absorb: every scored comment came through the floor
    filter. Treating NULL as False would quietly withhold the cite half of the
    A2 limb-1 test from that comment and it would rate A3 for no stated reason.
    """
    v = row["has_citation"]
    if v is None:
        raise SystemExit(
            f"comment {row['comment_id']} is scored but has no"
            " {analysis}.substance_floor row, so has_citation is unknown."
            " Run the floor filter over the current corpus before rating —"
            " a missing flag is not the same as 'no citation'.")
    return v


def rating_row(row):
    """The _RATING_UPSERT payload for one scores row, minus its run_id.

    Deliberately independent of the run: every rating is computed and checked
    before the run header is created, so a bad row cannot leave an empty run
    behind.

    `gated` is the STORED gate, not the recomputed one. The column exists to
    record the gate as of rating time, so it has to be what substance_scores
    actually says; recomputing it would make the rating agree with itself
    instead of with the score it rates. The recomputation still runs, as a
    check — if the two disagree the scores are drifting from the gate rule and
    the run stops rather than storing a number nothing produced.
    """
    scores = {d: int(row[d.lower()]) for d in DIMS}
    r = rate(scores, _list(row["moves"]), _list(row["targets"]), citation_flag(row))
    stored_gate = row["gate"]
    drift = gate_drift(row, scores, r)
    if drift:
        raise SystemExit(drift + " Nothing was written.")
    _, total = weighted(scores)
    return (row["comment_id"], r["level"], stored_gate,
            json.dumps([k for k, v in r["limbs"].items() if v]), round(total, 1),
            json.dumps(r["defeated"]), json.dumps(r["open"]), r["mechanism"],
            json.dumps(r["mechanism_moves"]), json.dumps(r["mechanism_targets"]),
            json.dumps(r["cite_via"]))


def write_run(conn, render_sql, instrument, note, dry_run=False):
    """Rate every eligible comment under `instrument` into a run.

    The population is read FIRST: an instrument nothing was scored under must
    not leave a run header behind that rates nothing.

    A run is identified by (rater, evidence, deis_ref, weights_version,
    instrument_version) and the table enforces that with a unique index, so
    re-running the same rating REUSES its run and upserts the ratings in place
    rather than failing on the index or minting a second run that says the same
    thing. Changing the weights means bumping WEIGHTS_VERSION, which is a
    different run by definition — the old one stays readable.

    Everything is rated and checked before anything is written; then the write
    commits in batches, so a long pass is crash-safe and peekable and a bad row
    cannot abort a half-written one.

    `dry_run` returns None after reporting what would happen — the checks have
    all run by then, so it reports the real run's outcome rather than a cheaper
    guess at it.
    """
    print(f"make rate: reading every substance_scores row under {instrument} that is"
          f" not inherited ({ELIGIBLE}) with its floor flag; rates each from its eight"
          " dimensions, moves and targets; writes one answerability_run row and one"
          " substance_answerability row per comment", flush=True)
    rows = conn.execute(render_sql(
        "SELECT s.comment_id, s.gate, s.band, s.place, s.stand, s.doc, s.gap,"
        " s.evid, s.ask, s.alt, s.law, s.moves, s.targets, f.has_citation"
        " FROM {analysis}.substance_scores s"
        " LEFT JOIN {analysis}.substance_floor f USING (comment_id)"
        " WHERE " + ELIGIBLE
        + " AND s.instrument_version = ?"
        " ORDER BY s.comment_id"), (instrument,)).fetchall()
    if not rows:
        raise SystemExit(
            f"Nothing to rate: no {ELIGIBLE} row in substance_scores carries"
            f" instrument_version {instrument!r}. Score under that instrument"
            " first, or name the one the corpus was scored under. No run was"
            " created.")

    # Rate and check EVERY row before the run exists, so a drifted gate or a
    # missing floor row can neither abort a half-written pass nor leave an empty
    # run header behind. These are arithmetic over rows already in hand.
    payloads = [rating_row(row) for row in rows]

    found = conn.execute(render_sql(_RUN_FIND), (
        "rtca", "text_only", "", WEIGHTS_VERSION, instrument)).fetchone()

    if dry_run:
        # Every check above has already run over every row — the population, the
        # gate agreement, the floor flag, the limb coverage — so this reports
        # what the real run would do, not a cheaper approximation of it. The
        # grid is computed from the ratings in hand rather than read back.
        where = (f"upserted into existing run {found['run_id']}" if found
                 else "written to a new run")
        print(f"dry run — nothing written.\n"
              f"  {len(payloads):,} eligible comment(s) under instrument"
              f" {instrument} ({ELIGIBLE}) would be {where},"
              f" rater rtca, evidence text_only, weights {WEIGHTS_VERSION}.")
        if found:
            stale = conn.execute(render_sql(
                "SELECT count(*) AS n FROM {analysis}.substance_answerability a"
                " WHERE a.run_id = ? AND NOT EXISTS ("
                "   SELECT 1 FROM {analysis}.substance_scores s"
                "   WHERE s.comment_id = a.comment_id AND " + ELIGIBLE
                + "     AND s.instrument_version = ?)"),
                (found["run_id"], instrument)).fetchone()["n"]
            print(f"  {stale:,} rating(s) in that run are for comments no longer"
                  " eligible; the real run would delete them, naming each one."
                  if stale else "  no stale ratings in that run.")
        counts = {}
        for r, p in zip(rows, payloads):
            key = (r["band"], p[1])
            counts[key] = counts.get(key, 0) + 1
        render_grid(counts, "GRID AS IT WOULD LAND -- strength band against"
                            " A-level (dry run)")
        return None

    if found:
        run_id = found["run_id"]
        print(f"run {run_id}: reusing the existing rtca/text_only run at"
              f" weights {WEIGHTS_VERSION}, instrument {instrument}"
              " — ratings are upserted in place")
        if note is not None:
            # The note describes the run, and the run already exists. Silently
            # dropping what the operator typed is worse than refusing it.
            raise SystemExit(
                f"--note was given but run {run_id} already exists and its note"
                " is not rewritten by a re-rate. Drop --note to refresh this"
                " run's ratings, or bump WEIGHTS_VERSION if this is meant to be"
                " a different rating.")
    else:
        run_id = conn.execute(render_sql(_RUN_INSERT), (
            "rtca", "text_only", None, WEIGHTS_VERSION, instrument,
            note)).fetchone()["run_id"]
        conn.commit()
        print(f"run {run_id}: rater rtca, evidence text_only,"
              f" weights {WEIGHTS_VERSION}, instrument {instrument}")

    # Ratings for comments that have since LEFT the eligible population. The run
    # means "this weights_version's rating of this instrument's corpus", so a
    # leftover row makes it describe a corpus that no longer exists — and the
    # count check below would blame the write for it.
    #
    # They are DELETED, not refused. A comment leaves the population by being
    # re-assembled as inherited when its campaign grows, which happens on every
    # hourly run that collects new signers; refusing there stops the scheduled
    # chain on a routine event and leaves the corpus scored but unrated. This
    # write rewrites the whole run — every eligible comment is rated in the same
    # transaction below — so removing the rows that are no longer part of it is
    # what keeps the run meaning what it says.
    if found:
        stale = conn.execute(render_sql(
            "SELECT count(*) AS n FROM {analysis}.substance_answerability a"
            " WHERE a.run_id = ? AND NOT EXISTS ("
            "   SELECT 1 FROM {analysis}.substance_scores s"
            "   WHERE s.comment_id = a.comment_id AND " + ELIGIBLE
            + "     AND s.instrument_version = ?)"),
            (run_id, instrument)).fetchone()["n"]
        if stale:
            # SQLite's DELETE takes no table alias: the table is named in full.
            gone = conn.execute(render_sql(
                "DELETE FROM {analysis}.substance_answerability"
                " WHERE run_id = ? AND NOT EXISTS ("
                "   SELECT 1 FROM {analysis}.substance_scores s"
                "   WHERE s.comment_id = substance_answerability.comment_id AND " + ELIGIBLE
                + "     AND s.instrument_version = ?)"
                " RETURNING comment_id"),
                (run_id, instrument)).fetchall()
            conn.commit()
            print(f"  dropped {len(gone)} rating(s) for comments no longer"
                  f" eligible under instrument {instrument} (rescored,"
                  " re-assembled as inherited, or removed). All of them:")
            for r in gone:
                print(f"    {r['comment_id']}")

    written = 0
    with conn.cursor() as cur:
        for i in range(0, len(payloads), FLUSH_EVERY):
            batch = [(run_id, *p) for p in payloads[i:i + FLUSH_EVERY]]
            cur.executemany(render_sql(_RATING_UPSERT), batch)
            conn.commit()
            written += len(batch)
            print(f"  {written}/{len(payloads)}", flush=True)

    # What is in the table, not what the loop counted. An upsert that silently
    # collapsed two rows onto one key, or a batch that never reached the server,
    # shows up here and nowhere else.
    stored = conn.execute(render_sql(
        "SELECT count(*) AS n FROM {analysis}.substance_answerability"
        " WHERE run_id = ?"), (run_id,)).fetchone()["n"]
    if stored != written:
        raise SystemExit(
            f"run {run_id} wrote {written} rating(s) but the table holds"
            f" {stored}. The ratings written and the ratings stored disagree —"
            " do not read this run.")
    print(f"  {written}/{len(rows)} rated, {stored} stored")
    print(f"\nDONE: the corpus is rated under instrument {SCORING_INSTRUMENT}."
          " The concern ledger and the reports read this run; no further step"
          " in this chain.")
    return run_id


LEVELS = ["A1", "A2", "A3", "A0"]


def render_grid(counts, title):
    """Strength band against A-level, from {(band, level): n}.

    The ONE renderer. Both modes print their grid through it, so the sample and
    the corpus cannot disagree about what the table means — and neither can skip
    the accounting check below.
    """
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)
    print(f"  {'band':<12}" + "".join(f"{lv:>9}" for lv in LEVELS) + f"{'total':>11}")
    for band in BANDS:
        n = [counts.get((band, lv), 0) for lv in LEVELS]
        print(f"  {band:<12}" + "".join(f"{c:>9,}" for c in n) + f"{sum(n):>11,}")
    tot = [sum(counts.get((b, lv), 0) for b in BANDS) for lv in LEVELS]
    print(f"  {'all':<12}" + "".join(f"{c:>9,}" for c in tot) + f"{sum(tot):>11,}")
    print("\n  The off-diagonal cells are the point: a low-strength A1 must be"
          " answered, a high-strength A3 leaves every dismissal available.")
    # The grid only walks the four known bands and levels, so a row carrying
    # anything else would vanish from every cell AND from the total.
    missing = sum(counts.values()) - sum(tot)
    if missing:
        raise SystemExit(
            f"the grid accounts for {sum(tot)} of {sum(counts.values())}"
            f" comments — {missing} carry a band or A-level outside"
            f" {BANDS} / {LEVELS} and are not displayed anywhere above.")


def print_grid(conn, render_sql, run_id):
    """The corpus grid for a stored run."""
    counts = {(r["band"], r["a_level"]): r["n"] for r in conn.execute(render_sql(
        "SELECT band, a_level, count(*) AS n"
        " FROM {analysis}.v_substance_answerability"
        " WHERE run_id = ? GROUP BY 1, 2"), (run_id,))}
    render_grid(counts, f"CORPUS GRID -- run {run_id}: strength band against A-level")


def report(row):
    """One comment, printed whole: the text, the stored score with the
    arithmetic that produced it, the answerability calculation line by line,
    and the composite."""
    scores = {d: int(row[d.lower()]) for d in DIMS}
    text = row["comment_text"] or ""
    cid = row["comment_id"]

    print("=" * 100)
    print(f"comment_id {cid}   stored band {row['band']}   scored_via"
          f" {row['scored_via']}   instrument {row['instrument_version']}"
          f"   was_floored {row['was_floored']}")
    print("=" * 100)
    print(f"COMMENT -- full text, {len(text):,} chars, NOT truncated")
    print("-" * 100)
    print(text)
    print("-" * 100)

    print("\nRAW STRENGTH  (as stored; score_comments.finalize_record)")
    print("  " + " + ".join(f"{d} {scores[d]}" for d in DIMS)
          + f" = {sum(scores.values())}")
    computed = sum(scores.values())
    stored = row["strength"]
    agree = "agrees with stored" if computed == stored else f"MISMATCH -- stored {stored}"
    print(f"  sum {computed}  ({agree})")
    b = band_for(computed)
    bagree = "agrees" if b == row["band"] else f"MISMATCH -- stored {row['band']}"
    print(f"  band_for({computed}) -> {b}   ({bagree})"
          "   [minimal <=5, marginal <=11, developed <=17, strong >17]")
    basis = _list(row["gate_basis"])
    why = ", ".join(f"{d} {scores[d]}" for d in basis) if basis else \
        "no dimension among GAP/EVID/ALT/LAW reached 2"
    print(f"  gate {row['gate']}   gate_basis {basis or '[]'}   ({why})")
    print("  raw maximum is 23, not 24: LAW is mechanical and emits 0 or 2,"
          " so the top of `strong` is unreachable")

    print("\nANSWERABILITY  (read-time; nothing above is changed)")
    rows, total = weighted(scores)
    print(f"  {'dim':<6} {'val':>3}  {'reaches':<46} {'weight':>8} {'contrib':>8}")
    for d, v, reaches, weight, contrib in rows:
        print(f"  {d:<6} {v:>3}  {reaches:<46} {weight:>8} {contrib:>8.1f}")
    print(f"  {'':<6} {'':>3}  {'weighted total':<46} {'':>8} {total:>8.1f}")

    r = rate(scores, _list(row["moves"]), _list(row["targets"]), citation_flag(row))
    drift = gate_drift(row, scores, r)
    if drift:
        print(f"\n  GATE MISMATCH -- {drift}"
              "\n  --write would refuse this comment; the rating below is shown"
              " from the dimensions.")
    lim = r["limbs"]
    print("\n  limbs reached: " + ", ".join(
        f"{k} {'yes' if v else 'no'}" for k, v in lim.items())
        + f"   |  mechanism {r['mechanism']} (moves {r['mechanism_moves'] or '-'},"
          f" targets {r['mechanism_targets'] or '-'})"
          f"   cite {r['cite']} (via {r['cite_via'] or '-'})")

    print("\n  the nine no-action codes -- what this text defeats:")
    for code in NO_ACTION_CODES:
        won, why_c = r["verdict"][code]
        print(f"    [{'DEFEATED' if won else '  open  '}] {code:<28} {why_c}")
    print(f"\n  defeated {r['defeated'] or '[]'}")
    print(f"  open     {r['open']}")

    level = r["level"]
    print(f"\n  -> {level}  -- {A_MEANING[level]}")

    print(f"\nCOMPOSITE  {stored}{level}")
    rat = (row["rationale"] or "").strip()
    if rat:
        print(f"\n  scorer's rationale: {rat}")
    print()
    return row["band"], level


def main():
    parser = argparse.ArgumentParser(
        description="Answerability rating over stored substance scores. Reads"
                    " substance_scores; --write stores into"
                    " answerability_run / substance_answerability.")
    add_project_argument(parser)
    parser.add_argument("--limit", type=int, default=None,
                        help=f"comments sampled PER BAND (default"
                             f" {SAMPLE_DEFAULT})")
    parser.add_argument("--write", action="store_true",
                        help="rate the WHOLE corpus into a new run in"
                             " {analysis}.answerability_run /"
                             " substance_answerability, instead of printing a"
                             " sample. Prints the corpus grid when it lands.")
    parser.add_argument("--instrument", default=SCORING_INSTRUMENT,
                        help="rate the scores stored under this instrument"
                             f" version (default {SCORING_INSTRUMENT}). A run"
                             " records one instrument, because scores from two"
                             " are not comparable.")
    parser.add_argument("--note", default=None,
                        help="free text recorded on the run")
    parser.add_argument("--dry-run", action="store_true",
                        help="with --write: rate and check every eligible"
                             " comment, report the counts and the grid as it"
                             " would land, and write nothing")
    args = parser.parse_args()
    ctx = context_from_args(args)

    # Both modes, not just --write: a sampled v1 comment would print an A-level
    # computed from an invented LAW and a "raw maximum is 23" line that is false
    # for it, which is no better on screen than in the table.
    if args.instrument in UNRATABLE_INSTRUMENTS:
        raise SystemExit(
            f"instrument {args.instrument!r} is not ratable: A1 keys entirely"
            " off LAW == 2, and LAW is mechanical only from v2 onward"
            " (finalize_record takes it from the confirmed-citation scan and"
            " discards the model's). Under v1 the model invented LAW, so the"
            " rating would mint A1s out of register rather than law.")

    # A flag that belongs to the other mode means the caller expects something
    # this run will not do. Refuse rather than ignore it — both directions.
    wrong_mode = ([f for f, v in (("--limit", args.limit is not None),) if v]
                  if args.write else
                  [f for f, v in (("--note", args.note is not None),
                                  ("--dry-run", args.dry_run)) if v])
    if wrong_mode:
        raise SystemExit(
            f"{' and '.join(wrong_mode)} belongs to the"
            f" {'sample' if args.write else '--write'} mode."
            + (" --write rates every eligible comment, it does not sample."
               if args.write else
               " Sampling writes nothing and creates no run."))

    if args.write:
        with dict_connect(ctx.db_config) as conn:
            run_id = write_run(conn, ctx.render_sql, args.instrument, args.note,
                               dry_run=args.dry_run)
            if run_id is not None:  # a dry run printed its own grid
                print_grid(conn, ctx.render_sql, run_id)
        return

    limit = SAMPLE_DEFAULT if args.limit is None else args.limit
    grid = {}
    with dict_connect(ctx.db_config) as conn:
        for band in BANDS:
            rows = sample(conn, ctx.render_sql, band, limit, args.instrument)
            print("\n" + "#" * 100)
            print(f"# BAND {band.upper()} -- {len(rows)} of {limit} requested")
            print("#" * 100 + "\n")
            if not rows:
                print(f"no eligible comment in band {band} under instrument"
                      f" {args.instrument} ({ELIGIBLE})\n")
                continue
            for row in rows:
                b, level = report(row)
                grid[(b, level)] = grid.get((b, level), 0) + 1

    render_grid(grid, "SAMPLE GRID -- strength band against A-level, over this"
                      " sample")


if __name__ == "__main__":
    main()
