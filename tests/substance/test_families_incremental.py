"""The incremental family step's pure parts, on synthetic ids and n-gram sets.

No DB, no LLM. Which stored
family a component of detector groups and middle classes joins, when two
families merge and which id survives, when free texts found a family,
raised counts and the n-grams and sentences that cross the threshold,
attach against the distinctive index, containment against fixed leaders,
and the partition diff keyed on group_key.

    uv run pytest tests/substance/test_families_incremental.py
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

import families as fm  # noqa: E402  # pyright: ignore[reportMissingImports]
import families_incremental as inc  # noqa: E402  # pyright: ignore[reportMissingImports]
import build_comment_groups as bcg  # noqa: E402  # pyright: ignore[reportMissingImports]
from shared_text import FAMILY_MIN_COMMENTS, MEMBERSHIP_FLOOR  # noqa: E402  # pyright: ignore[reportMissingImports]


# ---- components: joins, merges, new cores ------------------------------

def test_free_texts_of_a_group_join_the_family_of_its_core_texts():
    units = [("near", ["A1", "A2", "N1"])]
    joins, merges, new = inc.resolve_components(units, {"A1": 7, "A2": 7}, {"A1": 7, "A2": 7})
    assert joins == {7: ["N1"]}
    assert merges == [] and new == []


def test_a_component_spanning_two_families_merges_the_younger_into_the_older():
    units = [("near", ["A1", "N1"]), ("middle", ["N1", "B1"])]
    core = {"A1": 3, "B1": 9}
    joins, merges, new = inc.resolve_components(units, core, core)
    assert merges == [(3, 9)]
    assert joins == {3: ["N1"]}


def test_a_middle_class_pulls_through_an_attached_member_and_merges():
    """A new text N shares a body with X, attached to family 7, and
    sits in a near group whose cores are family 9's. One body cannot be two
    letters, so the middle class binds the component to 7 as well: 9 merges
    into 7 and N joins 7. A near group alone still does not pull through an
    attached member (the test below)."""
    units = [("near", ["C9", "N"]), ("middle", ["X", "N"])]
    joins, merges, new = inc.resolve_components(units, {"C9": 9}, {"C9": 9, "X": 7})
    assert merges == [(7, 9)]
    assert joins == {7: ["N"]}
    assert new == []


def test_two_free_texts_with_no_family_found_a_near_core():
    joins, merges, new = inc.resolve_components([("near", ["N1", "N2"])], {}, {})
    assert new == [("near", ["N1", "N2"])] and not joins and not merges


def test_one_free_text_founds_nothing_here():
    """A single text of enough copies is the exact rule's, not a near core."""
    joins, merges, new = inc.resolve_components([("near", ["N1"])], {}, {})
    assert new == [] and not joins


def test_an_attached_member_neither_pulls_nor_is_free():
    """The attached text stays where it is; the group's free texts, being
    two, found a family of their own rather than joining through it."""
    units = [("near", ["X", "N1", "N2"])]
    joins, merges, new = inc.resolve_components(units, {}, {"X": 5})
    assert joins == {} and new == [("near", ["N1", "N2"])]


def test_groups_sharing_a_text_are_one_component():
    units = [("near", ["A1", "N1"]), ("near", ["N1", "N2"])]
    joins, merges, new = inc.resolve_components(units, {"A1": 2}, {"A1": 2})
    assert joins == {2: ["N1", "N2"]}


# ---- raised counts ------------------------------------------------------

def test_raised_counts_split_known_from_candidate_ngrams():
    counts = {1: 3, 2: 5}
    sets = {"T": frozenset({1, 9}), "U": frozenset({2, 9, 10})}
    changed, cand = inc.raised_counts(counts, {"T": 2, "U": 1}, sets, FAMILY_MIN_COMMENTS)
    assert counts == {1: 5, 2: 6}
    assert changed == {1, 2}
    assert cand == {9: 3, 10: 1}


def test_raised_sentences_report_the_keys_that_crossed():
    counts = {"a": 2, "b": 3}
    keys_of = {"T": {"a", "c"}, "U": {"c"}}
    changed, added = inc.raised_sentences(counts, {"T": 1, "U": 2}, keys_of, 3)
    assert counts == {"a": 3, "b": 3, "c": 3}
    assert changed == {"a", "c"}
    assert added == {"a", "c"}          # b was already the family's


def test_merge_counts_sums():
    a = {1: 2, 2: 3}
    inc.merge_counts(a, {2: 1, 3: 4})
    assert a == {1: 2, 2: 4, 3: 4}


# ---- attach -------------------------------------------------------------

def _fam(fid, distinctive):
    f = fm.Family(family_id=fid, core_kind="near", core=[])
    f.distinctive = set(distinctive)
    return f


def test_attach_picks_the_family_covering_most_and_refuses_under_the_floor():
    fams = {1: _fam(1, {1, 2, 3}), 2: _fam(2, {7, 8})}
    index = {ng: fid for fid, f in fams.items() for ng in f.distinctive}
    sets = {"P": frozenset({1, 2, 3, 40}), "Q": frozenset({7, 50, 51, 52})}
    out = inc.attach_units([["P"], ["Q"]], index, fams, sets)
    assert [(f.family_id, unit) for f, unit, _cov in out] == [(1, ["P"])]
    assert out[0][2] == 0.75 >= MEMBERSHIP_FLOOR


def test_attach_moves_a_body_unit_together():
    fams = {1: _fam(1, {1, 2})}
    index = {1: 1, 2: 1}
    sets = {"P": frozenset({1, 2}), "P2": frozenset({1, 2, 3, 4, 5})}
    out = inc.attach_units([["P", "P2"]], index, fams, sets)
    assert len(out) == 1 and out[0][1] == ["P", "P2"]
    assert abs(out[0][2] - 4 / 7) < 1e-9


# ---- containment against fixed leaders ---------------------------------

def test_new_text_joins_the_old_pending_leader_it_is_contained_in():
    letter = frozenset(range(20))
    old_long = frozenset(range(60))          # carries the letter inside
    groups = inc.contain_against([("OLD", old_long, 1)], [("NEW", letter, 1)], 0.6)
    assert groups == [("OLD", {"OLD", "NEW"})]


def test_old_leaders_are_never_grouped_among_themselves():
    a = frozenset(range(30))
    b = frozenset(range(5, 35))              # 25 of 30 shared: would group in a full pass
    assert inc.contain_against([("A", a, 1), ("B", b, 1)], [], 0.6) == []


def test_new_texts_lead_and_take_each_other():
    n1 = frozenset(range(10))
    n2 = frozenset(range(2, 14))
    groups = inc.contain_against([], [("N1", n1, 1), ("N2", n2, 1)], 0.6)
    assert len(groups) == 1 and groups[0][1] == {"N1", "N2"}
    assert groups[0][0] == "N1"              # shortest leads


# ---- the partition diff ------------------------------------------------

def _group(key, kind, size, fid=None, analysis=None, seen="2026-09-01"):
    return {"group_kind": kind, "group_key": key, "canonical_comment_id": key,
            "analysis_comment_id": analysis or key, "size": size, "family_id": fid,
            "first_seen_at": seen}


def test_partition_delta_keeps_ids_by_key_and_updates_what_changed():
    stored_groups = {"C1": (10, "singleton", "C1", "C1", 1, None),
                     "C2": (11, "exact", "C2", "C2", 2, 5),
                     "C9": (12, "singleton", "C9", "C9", 1, None)}
    stored_members = {"C1": (10, True), "C2": (11, False), "C3": (11, False), "C9": (12, True)}
    groups = [_group("C1", "exact", 2, fid=-1),       # a copy arrived: singleton -> exact
              _group("C2", "exact", 2, fid=5)]        # unchanged
    members = [{"comment_id": "C1", "kind": "exact", "key": "C1", "has_own_text": False},
               {"comment_id": "C4", "kind": "exact", "key": "C1", "has_own_text": False},
               {"comment_id": "C2", "kind": "exact", "key": "C2", "has_own_text": False},
               {"comment_id": "C3", "kind": "exact", "key": "C2", "has_own_text": False}]
    ins, upd, dele, changed = bcg.partition_delta(stored_groups, stored_members, groups,
                                                  members, {-1: 77, 5: 5})
    assert ins == []
    assert upd == [(10, "exact", "C1", "C1", 2, 77, "2026-09-01")]
    assert dele == [12]
    assert changed == [("C1", "C1", False), ("C4", "C1", False)]


def test_partition_delta_inserts_a_new_key():
    groups = [_group("C5", "singleton", 1)]
    members = [{"comment_id": "C5", "kind": "singleton", "key": "C5", "has_own_text": True}]
    ins, upd, dele, changed = bcg.partition_delta({}, {}, groups, members, {})
    assert ins == [("C5", "singleton", "C5", "C5", 1, None, "2026-09-01")]
    assert changed == [("C5", "C5", True)]


# ---- sentence helpers --------------------------------------------------

def test_own_sentence_keys_are_the_sentences_outside_the_spans():
    text = "Dear Chief. Keep the rule. I hike there every summer."
    spans = [(a, b, 1) for a, b, s in __import__("shared.text_norm", fromlist=["x"]).sentences(text)
             if "hike" not in s]
    assert fm.own_sentence_keys(text, spans) == ["i hike there every summer"]


def test_family_sentence_counts_keep_every_key():
    texts = {"A": "One. Two.", "B": "One. Three."}
    counts = fm.family_sentence_counts(["A", "B"], texts, {"A": 2, "B": 1})
    assert counts == {"one": 3, "two": 2, "three": 1}
    assert fm.keys_at_threshold(counts, 3) == {"one"}


# ---- temp ids ----------------------------------------------------------

def test_temp_ids_are_negative_and_never_reused():
    """An id is never reused, even when a family fails the floor between
    two batches; the counter does not care what was kept."""
    it = inc.Increment(None, None, {}, {})
    ids = [it._temp_id() for _ in range(4)]
    assert ids == [-1, -2, -3, -4]
    assert len(set(ids)) == 4
