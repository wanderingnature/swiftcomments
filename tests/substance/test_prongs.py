"""The four prong gates: the mapping, its bases, the union rule, and the
answerability equivalence (A1 from compliance; A2 from significance,
alternatives, or impacts with a mechanism and a citation)."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

import answerability as ans  # noqa: E402  # pyright: ignore[reportMissingImports]
from prongs import PRONGS, prongs_for  # noqa: E402  # pyright: ignore[reportMissingImports]


def flags(got):
    return {p: got[p][0] for p in PRONGS}


def test_gap_2_opens_impacts_only():
    got = prongs_for(2, 0, 0, 0)
    assert flags(got) == {"impacts": 1, "significance": 0, "alternatives": 0, "compliance": 0}
    assert got["impacts"][1] == ["GAP 2"]


def test_gap_3_opens_significance_and_impacts():
    got = prongs_for(3, 0, 0, 0)
    assert flags(got)["impacts"] == 1
    assert flags(got)["significance"] == 1
    assert got["significance"][1] == ["GAP 3"]


def test_evid_opens_impacts():
    got = prongs_for(0, 2, 0, 0)
    assert flags(got) == {"impacts": 1, "significance": 0, "alternatives": 0, "compliance": 0}
    assert got["impacts"][1] == ["EVID 2"]


def test_gap_and_evid_both_in_the_impacts_basis():
    assert prongs_for(2, 3, 0, 0)["impacts"][1] == ["GAP 2", "EVID 3"]


def test_alt_opens_alternatives():
    got = prongs_for(0, 0, 2, 0)
    assert flags(got)["alternatives"] == 1
    assert got["alternatives"][1] == ["ALT 2"]


def test_law_opens_compliance():
    got = prongs_for(0, 0, 0, 2)
    assert flags(got) == {"impacts": 0, "significance": 0, "alternatives": 0, "compliance": 1}
    assert got["compliance"][1] == ["LAW 2"]


def test_level_1_opens_nothing():
    assert flags(prongs_for(1, 1, 1, 1)) == \
        {"impacts": 0, "significance": 0, "alternatives": 0, "compliance": 0}


def test_union_equals_gate():
    for gap in range(4):
        for evid in range(4):
            for alt in range(4):
                for law in range(4):
                    gate = int(max(gap, evid, alt, law) >= 2)
                    got = prongs_for(gap, evid, alt, law)
                    assert int(any(got[p][0] for p in PRONGS)) == gate, \
                        (gap, evid, alt, law)


def test_a_level_from_the_prongs_equals_the_rating():
    """Method-2 section 2.3: A1 follows from compliance; A2 from significance,
    from alternatives, or from impacts with a mechanism and a citation. The
    decision table does not change. LAW stays 0-2: it is mechanical."""
    for gap in range(4):
        for evid in range(4):
            for alt in range(4):
                for law in (0, 1, 2):
                    for moves, targets in (([], []), (["M1"], ["T1"])):
                        for doc in (0, 2):
                            for has_citation in (False, True):
                                s = {d: 0 for d in ans.DIMS}
                                s.update(GAP=gap, EVID=evid, ALT=alt, LAW=law, DOC=doc)
                                r = ans.rate(s, moves, targets, has_citation)
                                got = flags(prongs_for(gap, evid, alt, law))
                                mechanism = bool(set(moves) & ans.MECHANISM_MOVES
                                                 and set(targets) & ans.MECHANISM_TARGETS)
                                cite = doc >= 2 or has_citation
                                if not any(got.values()):
                                    level = "A0"
                                elif got["compliance"]:
                                    level = "A1"
                                elif got["significance"] or got["alternatives"] \
                                        or (got["impacts"] and mechanism and cite):
                                    level = "A2"
                                else:
                                    level = "A3"
                                assert level == r["level"], \
                                    (gap, evid, alt, law, moves, targets, doc,
                                     has_citation, level, r["level"])
