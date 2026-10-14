"""refresh_law re-derives LAW and what follows from it exactly as finalize_record and
apply_v3_grade do. No DB.

    uv run pytest tests/substance/test_refresh_law.py
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

import refresh_law as rl  # noqa: E402  # pyright: ignore[reportMissingImports]
import score_comments as sc  # noqa: E402  # pyright: ignore[reportMissingImports]


_SCORES = {"PLACE": 1, "STAND": 0, "DOC": 1, "GAP": 1, "EVID": 1, "ASK": 0, "ALT": 1, "LAW": 0}


def test_a_stored_law_that_agrees_with_the_tags_changes_nothing():
    assert rl.refreshed(_SCORES, ["T1"], 0) is None
    assert rl.refreshed({**_SCORES, "LAW": 2}, ["T1", "T4"], 2) is None


def test_law_0_to_2_adds_two_points_opens_the_gate_on_law_and_adds_t4():
    f = rl.refreshed(_SCORES, ["T1"], 2)
    assert f is not None
    assert f["scores"]["LAW"] == 2 and f["scores"]["GAP"] == 1
    assert f["strength"] == f["strength_check"] == 7
    assert f["gate"] is True and f["gate_basis"] == ["LAW"]
    assert f["band"] == sc.band_for(7)
    assert f["targets"] == ["T1", "T4"]


def test_law_2_to_0_removes_the_points_the_basis_and_t4():
    f = rl.refreshed({**_SCORES, "LAW": 2}, ["T4", "T1"], 0)
    assert f is not None
    assert f["strength"] == 5 and f["gate"] is False and f["gate_basis"] == []
    assert f["band"] == "minimal" and f["targets"] == ["T1"]


def test_the_arithmetic_is_finalize_records():
    obj = {"scores": dict(_SCORES), "strength": 99, "gate": False}
    sc.finalize_record(obj, "C1", False, law_cited={"C1"})
    f = rl.refreshed(_SCORES, [], 2)
    assert f is not None
    assert (f["strength"], f["gate"], f["gate_basis"], f["band"]) == (
        obj["strength"], obj["gate"], obj["gate_basis"], obj["band"])


def test_a_gate_already_open_stays_open_with_law_added_to_the_basis():
    f = rl.refreshed({**_SCORES, "GAP": 2}, ["T1"], 2)
    assert f is not None
    assert f["gate_basis"] == ["GAP", "LAW"]


def test_a_change_records_the_stored_gate_and_strength():
    f = rl.refreshed(_SCORES, [], 2)
    c = rl.Change("substance_scores", "C1", "direct", _SCORES, f)
    assert (c.old_law, c.new_law) == (0, 2)
    assert c.old_strength == 5 and c.old_gate is False
    assert c.fields["gate"] is True
