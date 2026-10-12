"""The family module's pure parts, on synthetic n-gram sets and texts.

No DB, no LLM. docs/design/shared-text-families-implementation.md, sections
5.3 to 5.7: the family-text threshold with a one-text and a ten-text core,
distinctive at exactly the share, attach choosing the best family and
refusing under the floor, a passage shared by two families attaching
nothing (rule 5), the three attribution tiers, the union of overlapping
n-gram ranges, and the trivial-own rule.

    uv run pytest tests/substance/test_families.py
"""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

import families as fm  # noqa: E402  # pyright: ignore[reportMissingImports]
from shared import text_norm  # noqa: E402
from shared_text import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    DISTINCTIVE_SHARE, MEMBERSHIP_FLOOR, MIN_OWN_CHARS, TRIVIAL_OWN_TOKENS)


# ---- family text ------------------------------------------------------

def test_one_text_core_of_three_copies_keeps_its_whole_text():
    ngrams = {"A": frozenset(range(10))}
    fam, n_min = fm.family_text(["A"], ngrams, {"A": 3})
    assert n_min == fm.FAMILY_MIN_COMMENTS == 3
    assert set(fam) == set(range(10))


def test_family_text_is_what_three_comments_share_whatever_the_core_size():
    """A pinned count, not a share of the core: in a 100-text core an n-gram
    three texts share is family text, and one that a 2-copy text alone
    carries is not."""
    core = [f"T{i}" for i in range(100)]
    ngrams = {c: frozenset({0, 1, 2, 100 + i}) for i, c in enumerate(core)}
    ngrams["T0"] = frozenset({0, 1, 2, 100, 500})
    ngrams["T1"] = frozenset({0, 1, 2, 101, 500})
    ngrams["T2"] = frozenset({0, 1, 2, 102, 500})     # 500 in three texts
    weight = {c: 1 for c in core}
    weight["T3"] = 2                                   # 103 in one text of two copies
    fam, n_min = fm.family_text(core, ngrams, weight)
    assert n_min == 3
    assert set(fam) == {0, 1, 2, 500}


# ---- distinctive ------------------------------------------------------

def test_distinctive_at_exactly_the_share():
    core = ["A", "B"]
    ngrams = {"A": frozenset({1, 2}), "B": frozenset({1, 2})}
    weight = {"A": 4, "B": 4}                 # 8 weighted occurrences inside
    fam = {1: 2, 2: 2}
    cf = {1: 10, 2: 11}                       # 0.80 and 0.727
    assert fm.distinctive_ngrams(core, fam, ngrams, weight, cf) == {1}
    assert DISTINCTIVE_SHARE == 0.8


def test_missing_comment_frequency_is_an_error():
    with pytest.raises(SystemExit):
        fm.distinctive_ngrams(["A"], {1: 1}, {"A": frozenset({1})}, {"A": 1}, {})


# ---- cores ------------------------------------------------------------

def test_middle_class_joins_the_near_cores_it_spans():
    """Two detector groups whose members share an identical body (one middle
    class) are one letter split by the detector's size buckets."""
    near = {1: ["A1", "A2"], 2: ["B1", "B2"], 3: ["C1", "C2"]}
    leader_of = {1: "A1", 2: "B1", 3: "C1"}
    original_of = {t: t for t in ("A1", "A2", "B1", "B2", "C1", "C2", "M3", "X")}
    middle_class = {"body-a": ["A2", "B1", "M3"],        # spans cores 1 and 2, brings M3
                    "body-x": ["X", "X2", "X3"]}          # in no near core: a middle core
    original_of.update({"X2": "X", "X3": "X"})
    weight = {t: 1 for t in original_of}
    weight["X"] = 3
    fams, review, assigned, body_of = fm.cores(near, leader_of, middle_class, original_of,
                                               weight)
    by_core = {tuple(f.core): f for f in fams}
    assert ("A1", "A2", "B1", "B2", "M3") in by_core
    joined = by_core[("A1", "A2", "B1", "B2", "M3")]
    assert joined.core_kind == "near" and sorted(joined.leaders) == ["A1", "B1"]
    assert ("C1", "C2") in by_core and by_core[("C1", "C2")].leaders == ["C1"]
    assert ("X",) in by_core and by_core[("X",)].core_kind == "middle"
    assert review == [("body-a", 3, ["A1", "B1"])]
    assert assigned["M3"] is joined and assigned["X"].core_kind == "middle"
    assert body_of == {"A2": "body-a", "B1": "body-a", "M3": "body-a", "X": "body-x"}


def test_two_detector_groups_sharing_a_text_are_one_core():
    """The same text cannot be two letters: detector groups that share a
    text merge, as the middle-class join merges them."""
    near = {1: ["A1", "A2"], 2: ["A2", "B1"], 3: ["C1", "C2"]}
    original_of = {t: t for t in ("A1", "A2", "B1", "C1", "C2")}
    weight = {t: 1 for t in original_of}
    fams, review, assigned, _body = fm.cores(near, {1: "A1", 2: "B1", 3: "C1"}, {},
                                             original_of, weight)
    assert sorted(tuple(f.core) for f in fams) == [("A1", "A2", "B1"), ("C1", "C2")]
    merged = next(f for f in fams if "A2" in f.core)
    assert sorted(merged.leaders) == ["A1", "B1"]
    assert assigned["A2"] is merged and review == []


def test_two_comment_middle_class_still_joins_and_binds():
    """A class of two comments cannot be a core of its own, but its texts
    are one body: with a text in a near core it joins; with none, the two
    stay bound so attach and the core floor move them together."""
    near = {1: ["A1", "A2"], 2: ["B1", "B2"]}
    original_of = {t: t for t in ("A1", "A2", "B1", "B2", "P", "Q")}
    middle_class = {"body-ab": ["A1", "B2"], "body-pq": ["P", "Q"]}
    weight = {t: 1 for t in original_of}
    fams, review, assigned, body_of = fm.cores(near, {1: "A1", 2: "B1"}, middle_class,
                                               original_of, weight)
    assert [tuple(f.core) for f in fams] == [("A1", "A2", "B1", "B2")]
    assert review == [("body-ab", 2, ["A1", "B1"])]
    assert "P" not in assigned and body_of["P"] == body_of["Q"] == "body-pq"
    assert sorted(map(sorted, fm.units(["P", "Q", "Z"], body_of))) == [["P", "Q"], ["Z"]]


def test_exact_core_takes_its_bound_sibling():
    near = {1: ["A1", "A2"]}
    original_of = {"A1": "A1", "A2": "A2", "E": "E", "F": "F"}
    middle_class = {"body-ef": ["E", "F"]}
    weight = {"A1": 5, "A2": 1, "E": 3, "F": 1}
    fams, review, assigned, _body = fm.cores(near, {1: "A1"}, middle_class, original_of, weight)
    kinds = sorted((f.core_kind, tuple(f.core)) for f in fams)
    assert kinds == [("exact", ("E", "F")), ("near", ("A1", "A2"))]
    assert review == []


# ---- second pass ------------------------------------------------------

def test_contain_cores_group_a_letter_carried_in_longer_comments():
    """Five copies of one 100-n-gram letter, each with 40 to 160 n-grams of
    its own: resemblance is 0.38 to 0.71 and sizes differ, so the first
    pass never pairs them; containment is 1.0 for every pair against the
    shortest, which leads."""
    letter = set(range(100))
    texts = {f"C{i}": frozenset(letter | set(range(1000 * (i + 1), 1000 * (i + 1) + 40 * (i + 1))))
             for i in range(5)}
    texts["X"] = frozenset(range(5000, 5300))          # unrelated
    fams = fm.contain_cores(sorted(texts), texts, {t: 1 for t in texts}, start_id=7)
    assert len(fams) == 1
    fam = fams[0]
    assert fam.core_kind == "contain" and fam.family_id == 7
    assert fam.core == ["C0", "C1", "C2", "C3", "C4"] and fam.leaders == ["C0"]


def test_contain_cores_need_two_texts():
    texts = {"A": frozenset(range(100)), "B": frozenset(range(500, 600))}
    assert fm.contain_cores(["A", "B"], texts, {}, start_id=1) == []


# ---- exemplar after the core floor ------------------------------------

def test_exemplar_is_chosen_from_what_the_floor_kept():
    """A contain core's leader L whose members each contain a different
    60 percent of it: the family text (shared by 10 percent of the core) is
    what the members share, L is under half covered and leaves, and the
    exemplar must be one of the members that stayed."""
    letter = list(range(100))
    members = {f"M{i}": frozenset(set(letter[:40]) | set(range(1000 + 100 * i, 1000 + 100 * i + 30)))
               for i in range(9)}                      # 40 of the letter, 30 of their own
    ngrams = dict(members)
    ngrams["L"] = frozenset(letter)                    # the leader, all 100
    fam = fm.Family(family_id=1, core_kind="contain", core=sorted(ngrams), leaders=["L"])
    fam.ngrams, fam.family_text_min = fm.family_text(fam.core, ngrams, {c: 1 for c in fam.core})
    assert set(fam.ngrams) == set(letter[:40])         # L: 40 of 100 covered, under the floor
    assigned = {c: fam for c in fam.core}
    fm.set_weights({c: 1 for c in fam.core})
    fm._core_floor([fam], ngrams, {}, assigned)
    assert "L" not in fam.members and "L" not in assigned
    assert fam.exemplar_id in fam.members


# ---- families with nothing to score -----------------------------------

def test_family_with_no_attributed_text_is_dropped():
    a = fm.Family(family_id=1, core_kind="contain", core=["A", "B"])
    a.members = {"A": fm.Member("A", "core", 0.7, spans=[], shared_chars=0, own_chars=190),
                 "B": fm.Member("B", "core", 0.7, spans=[], shared_chars=0, own_chars=195)}
    b = fm.Family(family_id=2, core_kind="near", core=["C", "D"])
    b.members = {"C": fm.Member("C", "core", 0.9, spans=[(0, 40, 1)], shared_chars=40, own_chars=0),
                 "D": fm.Member("D", "core", 0.9)}                    # not a survivor
    c = fm.Family(family_id=3, core_kind="exact", core=["E"])
    c.members = {"E": fm.Member("E", "core", 1.0)}                    # no survivors: kept
    kept, dropped = fm.drop_unattributed([a, b, c])
    assert dropped == 1
    assert [f.core for f in kept] == [["C", "D"], ["E"]]
    assert [f.family_id for f in kept] == [1, 2]


# ---- coverage and exemplar --------------------------------------------

def test_coverage():
    assert fm.coverage(frozenset({1, 2, 3, 4}), {1, 2}) == 0.5
    assert fm.coverage(frozenset(), {1}) == 0.0


def test_unit_coverage_is_not_the_union():
    """A thousand copies of one letter, each with its own name n-grams: the
    union's coverage collapses, the unit's does not."""
    body = set(range(100))
    sets = [frozenset(body | {1000 + 5 * i + k for k in range(5)}) for i in range(1000)]
    assert fm.unit_coverage(sets, body) == 100 / 105
    union = frozenset().union(*sets)
    assert fm.coverage(union, body) < 0.05


def test_exemplar_is_the_most_copied_text():
    ngrams = {"A": frozenset({1}), "B": frozenset({2})}
    assert fm.choose_exemplar(["A", "B"], ngrams, {"A": 1, "B": 50}) == "B"


def test_exemplar_by_mean_jaccard_when_nothing_repeats():
    centre = frozenset(range(100))
    ngrams = {"X": centre,                                        # 0.82 to each other
              "Y": centre - set(range(0, 10)) | set(range(200, 210)),
              "Z": centre - set(range(90, 100)) | set(range(300, 310))}   # Y, Z: 0.67 to each other
    assert fm.choose_exemplar(["X", "Y", "Z"], ngrams, {}) == "X"


# ---- family sentence keys ---------------------------------------------

def test_family_sentence_keys_are_the_shared_ones():
    letter = "Please keep the Roadless Rule intact. Thank you."
    texts = {"A": letter + " I have been a firefighter for 20 years.",
             "B": letter + " Sincerely, Julene Freitas",
             "C": letter}
    weight = {"A": 1, "B": 1, "C": 1}
    keys = fm.family_sentence_keys(["A", "B", "C"], texts, weight, fm.FAMILY_MIN_COMMENTS)
    assert keys == {"please keep the roadless rule intact", "thank you"}


def test_one_text_core_keeps_every_sentence_and_copies_count():
    texts = {"A": "Please keep the rule. I hike there. Jane Smith",
             "B": "Please keep the rule. Different closing."}
    # A 5-copy text in a two-text core: its sentences are shared by five comments.
    keys = fm.family_sentence_keys(["A", "B"], texts, {"A": 5, "B": 1}, fm.FAMILY_MIN_COMMENTS)
    assert "i hike there" in keys and "jane smith" in keys and "different closing" not in keys
    keys = fm.family_sentence_keys(["A"], texts, {"A": 3}, fm.FAMILY_MIN_COMMENTS)
    assert keys == {"please keep the rule", "i hike there", "jane smith"}


# ---- attribution ------------------------------------------------------

LETTER = ("Dear Chief.\nPlease keep the Roadless Rule intact for future generations."
          " These forests protect drinking water for millions of people.\nThank you.")


def _keys(text):
    from shared_text import norm_sentence  # pyright: ignore[reportMissingImports]
    return {norm_sentence(s) for _a, _b, s in text_norm.sentences(text)
            if norm_sentence(s)}


def _occurrences(text, fam_ngrams=None):
    """Every 6-gram occurrence of `text` as (id, start, end); ids are the
    joined tokens, so two texts share an id when they share the words."""
    toks = text_norm.tokenize(text)
    out = []
    for i in range(len(toks) - 5):
        ng = " ".join(t.text for t in toks[i:i + 6])
        out.append((ng, toks[i].start, toks[i + 5].end))
    return out


def test_tier_1_takes_a_short_copied_sentence():
    member = LETTER.replace(" These forests",
                            " I hike there every summer with my kids and grandkids."
                            " These forests")
    spans, shared, own, own_tokens, in_margin, has_own = fm.attribute(
        member, _keys(LETTER), set(), [])
    tiers = {member[a:b].strip(): t for a, b, t in spans}
    assert tiers.get("Thank you") == 1
    assert tiers.get("Dear Chief") == 1
    assert "I hike there every summer with my kids and grandkids" not in tiers
    assert has_own and not in_margin
    assert own > 0 and shared > own


def test_tier_2_takes_an_edited_sentence_and_leaves_a_rewritten_one():
    edited = ("Please keep the Roadless Rule intact for all future generations."
              " These forests protect drinking water for millions of people.")
    rewritten = "Water for millions comes from these forests, so keep the rule."
    member = edited + " " + rewritten
    fam_ngrams = {ng for ng, _a, _b in _occurrences(LETTER)}
    occ = _occurrences(member)
    spans, _shared, _own, _tok, _margin, has_own = fm.attribute(
        member, set(), fam_ngrams, occ)
    tiers = {member[a:b].strip(): t for a, b, t in spans}
    assert tiers.get("Please keep the Roadless Rule intact for all future generations") == 2
    assert tiers.get("These forests protect drinking water for millions of people") == 2
    assert rewritten.rstrip(".") not in tiers
    assert has_own


def test_tier_2_is_measured_over_tokens_not_markup():
    """'<br/><br/>Besides, more roads mean more wildfire risk': the template's
    six-gram covers six of the seven tokens; measured over characters the
    markup pushed it under the rule."""
    letter = "More roads mean more wildfire risk everywhere."
    member = "I agree with all of this.<br/><br/>Besides, more roads mean more wildfire risk."
    fam_ngrams = {ng for ng, _a, _b in _occurrences(letter)}
    occ = _occurrences(member)
    spans, _s, _o, _t, _m, _h = fm.attribute(member, set(), fam_ngrams, occ)
    tiers = {member[a:b].strip(): t for a, b, t in spans}
    assert tiers == {"<br/><br/>Besides, more roads mean more wildfire risk": 2}


def test_union_bridges_the_stopword_filter():
    assert fm._union([(0, 10), (5, 12), (20, 25)]) == [(0, 12), (20, 25)]
    assert fm._covered([(0, 12), (20, 25)], 4, 22) == 8 + 2


def test_trivial_own_text_in_the_last_line():
    member = LETTER + "\nJane Smith, Asheville NC"
    keys = _keys(LETTER)
    spans, _s, _o, own_tokens, in_margin, has_own = fm.attribute(member, keys, set(), [])
    assert in_margin and own_tokens < TRIVIAL_OWN_TOKENS
    assert not has_own


def test_own_text_under_min_own_chars_is_not_own_text_anywhere():
    """Under 50 characters of own text carries no substance worth a scoring
    call, in the body as much as in a greeting or signature: the member is the
    campaign's text."""
    assert MIN_OWN_CHARS == 50
    member = LETTER.replace(" These forests", " I hike there. These forests")
    spans, _s, _o, own_tokens, in_margin, has_own = fm.attribute(member, _keys(LETTER), set(), [])
    assert not in_margin and own_tokens > 0
    assert not has_own


def test_own_text_at_min_own_chars_in_the_body_counts():
    own = "I hike there every summer with my family and friends."
    assert len(own) >= MIN_OWN_CHARS
    member = LETTER.replace(" These forests", " " + own + " These forests")
    spans, _s, _o, own_tokens, in_margin, has_own = fm.attribute(member, _keys(LETTER), set(), [])
    assert not in_margin
    assert has_own


def test_single_line_comment_is_all_margin():
    """The rule as written: the margin is the first and the last line, and a
    comment with one line is both. Its short own text is trivial wherever it
    sits. The shadow run's trivial-own bucket reports how often this happens
    (docs/design/shared-text-families-implementation.md, section 5.7)."""
    one_line = LETTER.replace("\n", " ")
    member = one_line.replace(" These forests", " I hike there. These forests")
    spans, _s, _o, own_tokens, in_margin, has_own = fm.attribute(
        member, _keys(one_line), set(), [])
    assert in_margin and own_tokens < TRIVIAL_OWN_TOKENS
    assert not has_own


def test_closing_across_a_tag_is_margin():
    member = LETTER + "<br/>Thank you,<br/>Julie Helgeson"
    keys = _keys(LETTER)
    spans, _s, _o, own_tokens, in_margin, has_own = fm.attribute(member, keys, set(), [])
    assert in_margin and 0 < own_tokens < TRIVIAL_OWN_TOKENS
    assert not has_own


def test_markup_only_own_text_is_not_own_text():
    member = LETTER.replace("\nThank you.", "<br/><br/>\nThank you.")
    spans, _s, own, own_tokens, _m, has_own = fm.attribute(member, _keys(LETTER), set(), [])
    assert own_tokens == 0 and not has_own


def test_blank_own_text_has_no_own_text():
    spans, shared, own, own_tokens, in_margin, has_own = fm.attribute(
        LETTER, _keys(LETTER), set(), [])
    assert own == 0 and not has_own and own_tokens == 0
    assert len(spans) == len(text_norm.sentences(LETTER))


def test_membership_floor_constant():
    assert MEMBERSHIP_FLOOR == 0.5
