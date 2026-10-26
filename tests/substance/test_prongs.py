"""The four prong gates: the mapping, its bases, and the union property."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

from prongs import PRONGS, prongs_for  # noqa: E402  # pyright: ignore[reportMissingImports]


def flags(got):
    return {p: got[p][0] for p in PRONGS}


# ------------------------------------------------------------------ model

def test_model_gap_2_opens_impacts():
    got = prongs_for(2, 0, 0, 0, [], [], 1, "model")
    assert flags(got) == {"impacts": 1, "significance": 0, "alternatives": 0, "compliance": 0}
    assert got["impacts"][1] == ["GAP 2"]


def test_model_gap_3_opens_significance_too():
    got = prongs_for(3, 0, 0, 0, [], [], 1, "model")
    assert flags(got)["impacts"] == 1
    assert flags(got)["significance"] == 1
    assert got["significance"][1] == ["GAP 3"]


def test_model_evid_with_t1_opens_impacts():
    got = prongs_for(0, 2, 0, 0, [], ["T1"], 1, "model")
    assert flags(got) == {"impacts": 1, "significance": 0, "alternatives": 0, "compliance": 0}
    assert got["impacts"][1] == ["EVID 2 T1"]


def test_model_evid_with_t3_routes_to_alternatives():
    got = prongs_for(0, 2, 0, 0, [], ["T3"], 1, "model")
    assert flags(got) == {"impacts": 0, "significance": 0, "alternatives": 1, "compliance": 0}
    assert got["alternatives"][1] == ["EVID 2 T3"]


def test_model_evid_with_both_targets_opens_both():
    got = prongs_for(0, 3, 0, 0, [], ["T1", "T3"], 1, "model")
    assert flags(got)["impacts"] == 1
    assert flags(got)["alternatives"] == 1


def test_model_untargeted_evid_opens_impacts():
    got = prongs_for(0, 2, 0, 0, [], [], 1, "model")
    assert flags(got)["impacts"] == 1
    assert got["impacts"][1] == ["EVID 2"]


def test_model_m1_t1_opens_significance_only_behind_the_gate():
    assert flags(prongs_for(0, 0, 2, 0, ["M1"], ["T1"], 1, "model"))["significance"] == 1
    assert flags(prongs_for(0, 0, 0, 0, ["M1"], ["T1"], 0, "model"))["significance"] == 0


def test_model_alt_2_opens_alternatives():
    got = prongs_for(0, 0, 2, 0, [], [], 1, "model")
    assert flags(got)["alternatives"] == 1
    assert got["alternatives"][1] == ["ALT 2"]


def test_model_law_2_opens_compliance():
    got = prongs_for(0, 0, 0, 2, [], [], 1, "model")
    assert flags(got) == {"impacts": 0, "significance": 0, "alternatives": 0, "compliance": 1}
    assert got["compliance"][1] == ["LAW 2"]


# ------------------------------------------------------------------ rules

def test_rules_evid_opens_impacts_whatever_the_targets():
    got = prongs_for(0, 2, 0, 0, [], ["T3"], 1, "rules")
    assert flags(got)["impacts"] == 1
    assert flags(got)["alternatives"] == 0
    assert got["impacts"][1] == ["EVID 2"]


def test_rules_alternatives_on_alt_alone():
    assert flags(prongs_for(0, 0, 3, 0, [], [], 1, "rules"))["alternatives"] == 1


def test_rules_moves_do_not_open_significance():
    assert flags(prongs_for(0, 0, 2, 0, ["M1"], ["T1"], 1, "rules"))["significance"] == 0


# ------------------------------------------------------------------ union

def test_union_equals_gate_both_readings():
    levels = range(4)
    for reading in ("model", "rules"):
        for gap in levels:
            for evid in levels:
                for alt in levels:
                    for law in levels:
                        for targets in ([], ["T1"], ["T3"], ["T1", "T3"]):
                            gate = int(max(gap, evid, alt, law) >= 2)
                            got = prongs_for(gap, evid, alt, law, ["M1"], targets,
                                             gate, reading)
                            union = int(any(got[p][0] for p in PRONGS))
                            assert union == gate, (reading, gap, evid, alt, law, targets)
