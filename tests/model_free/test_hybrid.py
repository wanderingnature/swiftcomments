"""Hybrid mode: the whole-comment score with GAP held to what one sentence
reaches. Its gate is the gate set model_free_gate_clusters.py computed before
hybrid was a scorer mode: open when the whole-comment gate basis has a
dimension other than GAP, or GAP is in it and one sentence reaches GAP 2."""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))  # the package as run.py imports it

from model_free.arithmetic import hybrid, rate, roll_up  # pyright: ignore[reportMissingImports]
from model_free.detectors import Context, SentenceScore  # pyright: ignore[reportMissingImports]
from model_free.run import score_text  # pyright: ignore[reportMissingImports]


def _unit(unit_id: int, start: int, **dims) -> SentenceScore:
    d = {"PLACE": 0, "STAND": 0, "DOC": 0, "GAP": 0, "EVID": 0, "ASK": 0, "ALT": 0, "LAW": 0}
    d.update(dims)
    return SentenceScore(unit_id=unit_id, comment_id="c", start_char=start, end_char=start + 10,
                         text_key="k", dims=d, hits=[], evid_applied=d["EVID"] > 0, ask_names=False,
                         alt_distinct=d["ALT"] >= 2, stand_this_place=False, is_record_text=False,
                         anchors=[], moves=["M2"], targets=["T1"], has_citation=False, mechanism=False)


def _old_gate(whole_basis: set[str], sentence_gap: int) -> bool:
    return bool(whole_basis - {"GAP"}) or ("GAP" in whole_basis and sentence_gap >= 2)


@pytest.mark.parametrize("w_gap,s_gap,w_evid,w_law", list(itertools.product(range(4), range(4), (0, 2), (0, 2))))
def test_hybrid_gate_is_the_old_gate_set(w_gap, s_gap, w_evid, w_law):
    whole = roll_up("c", [_unit(-1, 0, GAP=w_gap, EVID=w_evid, LAW=w_law, PLACE=3)])
    sentence = roll_up("c", [_unit(1, 0, GAP=0), _unit(2, 20, GAP=s_gap)])
    h = hybrid(whole, sentence)
    assert h.gate == _old_gate({str(b["dimension"]) for b in whole.gate_basis}, s_gap)
    assert h.dims["GAP"] == min(w_gap, s_gap)
    assert h.dims["PLACE"] == 3 and h.dims["EVID"] == w_evid and h.dims["LAW"] == w_law
    assert h.sentence_count == 2


def test_hybrid_names_the_sentence_for_gap_and_the_whole_unit_for_the_rest():
    whole = roll_up("c", [_unit(-1, 0, GAP=3, EVID=2)])
    sentence = roll_up("c", [_unit(1, 0, GAP=1), _unit(2, 20, GAP=2)])
    h = hybrid(whole, sentence)
    assert h.gate_basis == [{"dimension": "GAP", "unit_id": 2}, {"dimension": "EVID", "unit_id": -1}]
    assert rate(h).level == "A3"


def test_whole_comment_gap_alone_does_not_open_the_hybrid_gate():
    whole = roll_up("c", [_unit(-1, 0, GAP=3)])
    sentence = roll_up("c", [_unit(1, 0, GAP=1), _unit(2, 20, GAP=1)])
    h = hybrid(whole, sentence)
    assert whole.gate is True
    assert h.gate is False and h.dims["GAP"] == 1 and h.gate_basis == []
    assert rate(h).level == "A0"


def test_hybrid_of_two_comments_is_an_error():
    other = roll_up("d", [SentenceScore(**{**_unit(1, 0).__dict__, "comment_id": "d"})])
    with pytest.raises(ValueError):
        hybrid(roll_up("c", [_unit(-1, 0)]), other)


TEXT = ("From a forest management standpoint, building roads into undeveloped areas creates an "
        "unnecessary fire liability. Data show ignition density drops drastically in protected "
        "Inventoried Roadless Areas to just 1.97 fires per 1,000 hectares (Aplet et al., 2026).")


def test_score_text_runs_all_three_modes():
    s_scores, s_comment, _ = score_text("t", TEXT, Context(), "sentence")
    w_scores, w_comment, _ = score_text("t", TEXT, Context(), "whole")
    h_scores, h_comment, _ = score_text("t", TEXT, Context(), "hybrid")
    assert all(s.unit_id > 0 for s in s_scores) and len(s_scores) == 2
    assert [s.unit_id for s in w_scores] == [-1]
    assert [s.unit_id for s in h_scores] == [s.unit_id for s in s_scores] + [-1]
    assert h_comment.dims["GAP"] == min(w_comment.dims["GAP"], s_comment.dims["GAP"])  # type: ignore[attr-defined]
    for d in ("PLACE", "STAND", "DOC", "EVID", "ASK", "ALT", "LAW"):
        assert h_comment.dims[d] == w_comment.dims[d]  # type: ignore[attr-defined]
    with pytest.raises(ValueError):
        score_text("t", TEXT, Context(), "paragraph")
