"""The answerability rating's derivations, over constructed score shapes.

No DB, no LLM, no corpus — every case here is arithmetic the rating does on
eight integers, and these are the ways it can break: a limb mapping that disagreed with the labels printed beside it, an
A-level judged in parallel with the codes it is supposed to summarize, a gate
recomputed instead of read, a grid that dropped rows it could not place.

Each test names the invariant it holds, not the implementation it calls.

    uv run pytest tests/substance/test_answerability.py
"""
import inspect
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

import answerability as ans  # noqa: E402  # pyright: ignore[reportMissingImports]


def scores(**kw):
    """A full eight-dimension score, zeros unless named."""
    s = {d: 0 for d in ans.DIMS}
    s.update(kw)
    return s


def row(comment_id="C1", gate=None, moves=(), targets=(), has_citation=False, **kw):
    """A substance_scores row as the rating's queries return it."""
    s = scores(**kw)
    if gate is None:  # default to the gate rule, so tests opt in to drift
        gate = any(s[d] >= 2 for d in ("GAP", "EVID", "ALT", "LAW"))
    return {"comment_id": comment_id, "gate": gate, "moves": list(moves),
            "targets": list(targets), "has_citation": has_citation,
            **{d.lower(): v for d, v in s.items()}}


# --- limbs -----------------------------------------------------------------

def test_gap_3_is_limb_2_and_not_limb_1():
    """The document is explicit that GAP's levels 2 and 3 are DIFFERENT limbs.

    GAP 3 reaching limb 1 as well would store limbs_reached {limb1, limb2},
    which is what the table is read for.
    """
    assert [n for n, hit in ans.limbs_reached(scores(GAP=3)).items() if hit] == [2]
    assert [n for n, hit in ans.limbs_reached(scores(GAP=2)).items() if hit] == [1]


def test_the_limb_mapping_matches_the_document():
    """Pinned to literals, because the test below derives its expectation from
    LIMB_AT and so cannot catch LIMB_AT itself being wrong.

    GAP 2 -> limb 1, GAP 3 -> limb 2, EVID -> limb 1, ALT -> limb 3,
    LAW 2 -> limb 4. LAW carries no other value: it is mechanical 0-or-2.
    """
    assert ans.LIMB_AT == {"GAP": {2: 1, 3: 2}, "EVID": {2: 1, 3: 1},
                           "ALT": {2: 3, 3: 3}, "LAW": {2: 4}}
    # And each label names its own limb: a label reading "limb 1" against
    # limb 2 is the exact confusion the single mapping exists to prevent.
    for limb, label in ans.LIMB_LABEL.items():
        assert label.startswith(f"limb {limb} ")


def test_limb_labels_and_booleans_come_from_one_mapping():
    """The printed 'reaches' column and the stored limb array cannot disagree.

    They were two structures, hand-synced, until one drifted.
    """
    for dim, by_value in ans.LIMB_AT.items():
        for value, limb in by_value.items():
            s = scores(**{dim: value})
            assert ans.limbs_reached(s)[limb], f"{dim} {value} should reach limb {limb}"
            printed = {d: reaches for d, _v, reaches, _w, _c in ans.weighted(s)[0]}
            assert printed[dim] == ans.LIMB_LABEL[limb]


def test_a_gate_firing_value_with_no_limb_mapping_fails_loudly():
    """LAW is mechanical 0-or-2 from v2; a 3 means something upstream broke.

    Silently reaching no limb would surface as a gate disagreement blaming the
    gate rule instead of the value.
    """
    with pytest.raises(SystemExit, match="LAW = 3"):
        ans.limbs_reached(scores(LAW=3))


def test_the_gate_matches_finalize_record_over_every_score_shape():
    """rate()'s gate must equal score_comments.finalize_record's gate rule.

    Exhaustive over the four gate dimensions, 0-3 each: 256 shapes. LAW 3 is
    excluded — the guard above owns that case.
    """
    for gap in range(4):
        for evid in range(4):
            for alt in range(4):
                for law in (0, 2):
                    s = scores(GAP=gap, EVID=evid, ALT=alt, LAW=law)
                    expected = any(s[d] >= 2 for d in ("GAP", "EVID", "ALT", "LAW"))
                    assert ans.rate(s, [], [], False)["gated"] is expected, s


# --- the nine codes and the level over them --------------------------------

def test_every_code_is_decided_exactly_once():
    """The DB CHECK requires defeated and open to partition the nine.

    A code dropped from both halves, or counted in both, is rejected by
    substance_answerability_codes_partitioned — the run would fail at the
    insert, thousands of rows in.
    """
    for s in (scores(), scores(LAW=2), scores(GAP=3, PLACE=3),
              scores(EVID=2, DOC=3), scores(ALT=3)):
        r = ans.rate(s, ["M1"], ["T1"], True)
        assert set(r["defeated"]) | set(r["open"]) == set(ans.NO_ACTION_CODES)
        assert not set(r["defeated"]) & set(r["open"])
        assert len(r["defeated"]) + len(r["open"]) == 9


def test_the_level_is_derived_from_the_defeated_set():
    """The level is a label over the codes, never a parallel judgment.

    This is the same rule substance_answerability_level_derivation enforces in
    the table, checked here against the code that has to satisfy it.
    """
    for s in (scores(), scores(GAP=1), scores(LAW=2), scores(GAP=3),
              scores(ALT=2), scores(EVID=2), scores(EVID=3, DOC=3),
              scores(GAP=2, PLACE=3, DOC=3)):
        for moves, targets, cite in (([], [], False), (["M1"], ["T1"], True)):
            r = ans.rate(s, moves, targets, cite)
            if not r["gated"]:
                expected = "A0"
            elif "addressed_in_analysis" in r["defeated"]:
                expected = "A1"
            elif "no_cause_effect" in r["defeated"]:
                expected = "A2"
            else:
                expected = "A3"
            assert r["level"] == expected, (s, moves, targets, cite)


def test_an_ungated_comment_defeats_nothing():
    """Counted, not answered — and the table's CHECK says so too.

    PLACE 3 / DOC 3 would otherwise defeat outside_scope and misinterpreted on
    the form test alone, for a comment that is not substantive at all.
    """
    r = ans.rate(scores(PLACE=3, DOC=3, STAND=3, ASK=3), ["M1"], ["T1"], True)
    assert r["level"] == "A0"
    assert r["defeated"] == []
    assert len(r["open"]) == 9


def test_law_2_is_a1_and_defeats_the_three_the_design_names():
    r = ans.rate(scores(LAW=2), [], [], False)
    assert r["level"] == "A1"
    assert set(r["defeated"]) == {"addressed_in_analysis", "no_cause_effect",
                                  "certified_not_substantive"}


def test_the_mechanism_vocabulary_is_the_documented_one():
    """Pinned: the tests below use M1/T1, so widening either set would slip
    past them. M1 accuracy questioned, M3 new information, M5 missing analysis;
    T1 impacts, T2 significance determination.
    """
    assert ans.MECHANISM_MOVES == {"M1", "M3", "M5"}
    assert ans.MECHANISM_TARGETS == {"T1", "T2"}
    # A move or target outside the set is not a mechanism.
    assert ans.rate(scores(EVID=2), ["M2"], ["T3"], True)["level"] == "A3"
    assert ans.rate(scores(EVID=2), ["M4"], ["T1"], True)["level"] == "A3"


def test_limb_1_alone_needs_both_mechanism_and_cite_for_a2():
    """A3 vs A2 on the one branch the design leaves to calibration."""
    assert ans.rate(scores(EVID=2), [], [], False)["level"] == "A3"
    assert ans.rate(scores(EVID=2), ["M1"], ["T1"], False)["level"] == "A3"
    assert ans.rate(scores(EVID=2), [], [], True)["level"] == "A3"
    assert ans.rate(scores(EVID=2), ["M1"], ["T1"], True)["level"] == "A2"
    # A move without a target, or a target without a move, is not a mechanism.
    assert ans.rate(scores(EVID=2), ["M1"], [], True)["level"] == "A3"
    assert ans.rate(scores(EVID=2), [], ["T1"], True)["level"] == "A3"


def test_codes_with_no_text_only_test_are_reported_open_with_that_reason():
    """They are never silently omitted: the later DEIS run's delta is only
    readable if this run records which codes it could not reach."""
    r = ans.rate(scores(LAW=2, PLACE=3, DOC=3), ["M1"], ["T1"], True)
    for code in ans.NO_TEXT_ONLY_TEST:
        assert code in r["open"]
        assert "needs the DEIS" in r["verdict"][code][1]


# --- the stored row -> the stored rating ------------------------------------

def test_the_rating_stores_the_stored_gate_not_its_own():
    """gated records the gate as of RATING time, so it must be what
    substance_scores says."""
    payload = ans.rating_row(row(GAP=3, gate=True))
    assert payload[2] is True


def test_a_drifted_gate_stops_the_run():
    """Rating on either value would be a guess."""
    with pytest.raises(SystemExit, match="have drifted"):
        ans.rating_row(row(GAP=3, gate=False))


def test_a_missing_floor_row_is_not_an_absent_citation():
    with pytest.raises(SystemExit, match="substance_floor"):
        ans.citation_flag({"comment_id": "C1", "has_citation": None})


def test_the_payload_matches_the_upsert_column_list():
    """Twelve placeholders: run_id prepended to an eleven-field payload.

    A column added to _RATING_UPSERT without a matching field would fail at
    execute time, mid-run, after earlier batches committed.
    """
    assert ans._RATING_UPSERT.count("?") == len(ans.rating_row(row(GAP=3))) + 1


def test_gate_drift_is_one_comparison_for_both_modes():
    s = scores(GAP=3)
    r = ans.rate(s, [], [], False)
    assert ans.gate_drift(row(GAP=3, gate=True), s, r) is None
    assert "have drifted" in ans.gate_drift(row(GAP=3, gate=False), s, r)


# --- the weighted total -----------------------------------------------------

def test_stand_never_contributes():
    """It serves no regulatory test; excluding it stops sentiment inflating
    the rating."""
    for v in range(4):
        assert ans.weighted(scores(STAND=v))[1] == 0.0


def test_gap_contributes_by_level_not_by_weight():
    """Level 3 is a different limb than level 2, so it is not 1.5x of it."""
    totals = [ans.weighted(scores(GAP=v))[1] for v in range(4)]
    assert totals == [ans.GAP_CONTRIB[v] for v in range(4)]
    assert totals[3] > totals[2] > totals[1]


def test_the_weighted_total_fits_the_stored_column():
    """numeric(5,1) — the maximum any score shape can produce."""
    top = ans.weighted(scores(**{d: 3 for d in ans.DIMS}))[1]
    assert top < 9999.9
    assert round(top, 1) == top


# --- the grid ---------------------------------------------------------------

def test_the_grid_refuses_to_drop_a_row_it_cannot_place():
    """A band or level outside the known set would vanish from every cell AND
    from the total."""
    with pytest.raises(SystemExit, match="not displayed"):
        ans.render_grid({("strong", "A9"): 4}, "TEST")


def test_the_grid_totals_every_row_it_is_given():
    counts = {("strong", "A1"): 2, ("developed", "A2"): 3, ("minimal", "A0"): 5}
    ans.render_grid(counts, "TEST")  # no SystemExit: all ten rows are placed


# --- eligibility ------------------------------------------------------------

def test_inherited_rows_are_excluded_by_the_house_predicate():
    """A campaign signer carries its EXEMPLAR's score. Rating it would rate the
    organizer's text once per signer. Same predicate as
    build_comment_groups.
    """
    assert ans.ELIGIBLE == "s.scored_via <> 'inherited'"
    for sql in (ans._RUN_FIND, ans._RATING_UPSERT):
        assert "inherited" not in sql  # eligibility belongs to the read, not the write


def test_v1_is_not_ratable():
    """A1 keys entirely off LAW == 2, and LAW is mechanical only from v2."""
    assert "v1" in ans.UNRATABLE_INSTRUMENTS


def test_a_dry_run_returns_before_any_insert():
    """--dry-run must run every check and write nothing.

    Source-level, because the guarantee is an ordering one: the dry-run branch
    has to sit after the ratings are computed (so the checks fire) and before
    the run header is inserted (so nothing lands).
    """
    src = inspect.getsource(ans.write_run)
    assert src.index("payloads = ") < src.index("if dry_run:") < src.index("_RUN_INSERT")


def test_the_stored_json_columns_are_read_and_written_as_json():
    """The port: moves, targets and gate_basis are JSON text in the file, and the
    payload's lists go in as JSON text."""
    import json
    r = row(GAP=2, moves=["M1"], targets=["T1"], has_citation=True)
    r["moves"], r["targets"] = json.dumps(r["moves"]), json.dumps(r["targets"])
    payload = ans.rating_row(r)
    assert payload[1] == "A2"
    assert json.loads(payload[3]) == ["limb1"]
    assert "no_cause_effect" in json.loads(payload[5])
    assert json.loads(payload[8]) == ["M1"] and json.loads(payload[9]) == ["T1"]
    assert ans._list(None) == [] and ans._list("[]") == [] and ans._list(["a"]) == ["a"]
