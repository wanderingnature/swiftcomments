"""The v3 grader's levels, one test per level of every graded dimension.

No DB, no LLM: grade.py is pure functions over text and the vocabulary files,
and this file holds it to the levels the design states
(docs/design/reduced-ask-scoring-instrument.md). Every test names the level it
pins, because the levels are the instrument — if one of them moves, the score
moves with it.

    uv run pytest tests/substance/test_grade.py
"""
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

import grade  # noqa: E402  # pyright: ignore[reportMissingImports]


# ------------------------------------------------------------------ EVID

def test_evid_0_no_span():
    assert grade.evid_level("none", True, [], [])[0] == 0
    assert grade.evid_level("", True, [], [])[0] == 0


def test_evid_0_legal_citation_from_tagged_authority():
    level, rules = grade.evid_level("this violates 16 U.S.C. 1604(g)", True,
                                    ["16 U.S.C. 1604"], [])
    assert level == 0
    assert rules[0]["rule"] == "EVID.0.legal_citation"


def test_evid_0_legal_citation_from_the_detectors():
    assert grade.evid_level("see 36 C.F.R. 294.12", True, [], [])[0] == 0


def test_evid_0_statute_named_in_prose():
    """The entity pass tags citation FORM only, so a statute written out in
    words reached EVID 2 on a capitalized word. This is the run that found it:
    claude-sonnet-5 on FS-2025-0001-279400, 2026-09-18."""
    level, rules = grade.evid_level(
        "each such placement constitutes a regulated discharge under Clean Water Act Section 404",
        True, [], [])
    assert level == 0
    assert rules[0]["rule"] == "EVID.0.legal_citation"
    assert rules[0]["match"] == "clean water act"


def test_evid_0_statute_by_acronym():
    assert grade.evid_level("the ESA requires consultation here", True, [], [])[0] == 0
    assert grade.evid_level("NEPA demands a hard look at this", True, [], [])[0] == 0


def test_evid_0_a_statute_anywhere_in_the_span_zeroes_it():
    """Containment, the same semantics the confirmed-authority and detector
    tests already have: a span holding legal authority earns no EVID, even
    beside something that would otherwise score."""
    assert grade.evid_level(
        "the 2018 survey found bull trout, which the Clean Water Act reaches",
        True, [], [])[0] == 0


def test_evid_0_model_says_not_applied():
    assert grade.evid_level("the 2019 NCWRC survey", False, [], [])[0] == 0


def test_evid_1_applied_names_nothing():
    level, rules = grade.evid_level("studies show this causes harm", True, [], [])
    assert level == 1
    assert rules[0]["rule"] == "EVID.1.applied_names_nothing"


def test_evid_2_named_source_without_a_figure():
    level, rules = grade.evid_level("a Forest Service study of the watershed", True, [], [])
    assert level == 2
    assert rules[0]["rule"] == "EVID.2.named_source"


def test_evid_2_first_person_observation_with_a_date_stays_at_2():
    level, rules = grade.evid_level(
        "I saw slumping on the Bear Creek crossing in 2019", True, [], [])
    assert level == 2
    assert rules[0]["rule"] == "EVID.2.first_person_dated"


def test_evid_3_named_source_with_a_year():
    assert grade.evid_level("the 2019 NCWRC survey counted them", True, [], [])[0] == 3


def test_evid_3_named_source_with_an_author_year():
    assert grade.evid_level("as Smith (2009) found for this range", True, [], [])[0] == 3


def test_evid_3_named_source_with_a_figure():
    assert grade.evid_level("the agency's $40 million estimate of the loss", True, [], [])[0] == 3
    assert grade.evid_level("a Forest Service survey of 12,000 acres", True, [], [])[0] == 3


def test_evid_a_span_that_opens_with_its_acronym_still_names_a_source():
    """"NCWRC 2019 survey data" is the normal shape of an EVID span; skipping a
    match at offset 0 to avoid sentence casing must not throw it away."""
    assert grade.evid_level("NCWRC 2019 survey data", True, [], [])[0] == 3


def test_evid_a_sentence_cased_first_word_is_not_a_named_source():
    assert grade.evid_level("The scientific literature is unambiguous", True, [], [])[0] == 1


def test_evid_the_actions_own_document_does_not_name_a_source():
    """"the DEIS" in a span is what the source is applied TO. Counting it would
    lift every unnamed authority aimed at this document to 2 and leave 1
    unreachable."""
    level, rules = grade.evid_level(
        "studies show roads raise sediment, so the DEIS finding is unsupported", True, [], [])
    assert level == 1
    assert rules[0]["rule"] == "EVID.1.applied_names_nothing"


def test_evid_a_real_source_beside_the_document_still_counts():
    assert grade.evid_level(
        "The 2018 state survey found bull trout in Pine Creek, which the DEIS lists as unoccupied",
        True, [], [])[0] == 3


def test_evid_named_source_can_come_from_the_ner_record():
    level, rules = grade.evid_level("their own survey found none", True, [],
                                    [("ORG", "their own survey")])
    assert level == 2
    assert rules[0]["match"].startswith("ORG:")


# ------------------------------------------------------------------- ASK

def test_ask_0_no_span():
    assert grade.ask_level("none", False)[0] == 0


def test_ask_0_disposition_carries_no_work_verb():
    level, rules = grade.ask_level("Please reconsider. I urge you to reject this.", False)
    assert level == 0
    assert rules[0]["rule"] == "ASK.0.disposition_only"


def test_ask_1_work_verb_without_an_action_and_subject():
    level, rules = grade.ask_level("take a harder look at this", False)
    assert level == 1
    assert rules[0]["match"] == "look"


def test_ask_2_names_an_action_and_a_subject():
    assert grade.ask_level("prepare a cumulative sediment analysis for the watershed",
                           True)[0] == 2


def test_ask_3_action_subject_and_a_timing_word():
    level, rules = grade.ask_level(
        "prepare a sediment analysis before the final decision", True)
    assert level == 3
    assert rules[0]["match"] == "before"


# ----------------------------------------------------------------- STAND

def test_stand_3_professional_role_beats_the_place_question():
    level, rules = grade.stand_level("as a wildlife biologist I know this range", False)
    assert level == 3
    assert rules[0]["rule"] == "STAND.3.professional_role"


def test_stand_0_no_span():
    assert grade.stand_level("none", True)[0] == 0


def test_stand_0_not_about_this_place():
    assert grade.stand_level("I care deeply about wild country", False)[0] == 0


def test_stand_2_duration_from_the_list():
    assert grade.stand_level("I have hunted this drainage every fall", True)[0] == 2


def test_stand_2_duration_from_a_number():
    level, rules = grade.stand_level("I have fished there since 1994", True)
    assert level == 2
    assert rules[0]["match"] == "since 1994"


def test_stand_1_connection_only():
    level, rules = grade.stand_level("I visit often and I live nearby", True)
    assert level == 1
    assert rules[0]["rule"] == "STAND.1.connection_only"


# ------------------------------------------------------------------- ALT

def test_alt_0_no_span():
    assert grade.alt_level("none", False)[0] == 0


def test_alt_1_preference_is_not_an_alternative():
    level, rules = grade.alt_level("keep the rule and select no action", False)
    assert level == 1
    assert rules[0]["rule"] == "ALT.1.preference"


def test_alt_2_distinct_alternative():
    assert grade.alt_level("drop Unit 7 while keeping Units 1-6", True)[0] == 2


def test_alt_3_set_against_the_purpose_and_need():
    level, rules = grade.alt_level(
        "an alternative that meets the purpose and need without rescission", True)
    assert level == 3
    assert rules[0]["match"] == "purpose and need"


# ------------------------------------------------------------------- GAP

def test_gap_takes_the_models_level():
    assert grade.gap_level("the DEIS omits the lynx", 3)[0] == 3
    assert grade.gap_level("the DEIS omits the lynx", 1)[0] == 1


def test_gap_none_span_forces_0():
    assert grade.gap_level("none", 3)[0] == 0


def test_gap_is_clamped_to_the_instruments_range():
    assert grade.gap_level("something", 7)[0] == 3
    assert grade.gap_level("something", -2)[0] == 0


# ------------------------------------------------------------------- DOC

def test_doc_0_no_reference():
    assert grade.doc_level("The forest belongs to all of us.")[0] == 0


def test_doc_1_action_reference():
    level, rules = grade.doc_level("I oppose this rescission of the roadless rule.")
    assert level == 1
    assert rules[0]["rule"] == "DOC.1.action_reference"


def test_doc_1_document_mention_from_the_list():
    level, rules = grade.doc_level("The analysis never looks at sediment.")
    assert level == 1
    assert rules[0]["rule"] == "DOC.1.document_mention"


def test_doc_2_document_characterized():
    level, rules = grade.doc_level("The DEIS states that impacts are minimal.")
    assert level == 2
    assert rules[0]["rule"] == "DOC.2.characterized_or_named_section"


def test_doc_2_named_section_without_a_number():
    assert grade.doc_level("The Purpose and Need section never says why.")[0] == 2


def test_doc_2_does_not_fire_on_a_bare_section_word():
    assert grade.doc_level("In this section of the country we depend on it.")[0] == 0


def test_doc_3_numbered_reference():
    assert grade.doc_level("See Table 21 and Section 3.4.1.")[0] == 3
    assert grade.doc_level("The figure on p. 45 is wrong.")[0] == 3


def test_doc_3_beats_2_and_1_in_the_same_text():
    assert grade.doc_level("The DEIS states, at Table 21, that the rescission is minor.")[0] == 3


# ----------------------------------------------------------------- PLACE

@pytest.fixture
def small_places(tmp_path):
    csv = tmp_path / "places.csv"
    csv.write_text(
        "name,kind\n"
        "Nantahala National Forest,forest\n"
        "Cheoah Ranger District,district\n"
        "Big Creek,stream\n"
        "Snowbird,area\n"
        "Slickrock,trail\n",
        encoding="utf-8")
    return str(csv)


def test_place_0_nothing_named(small_places):
    assert grade.place_level("Roadless country is worth keeping.", small_places)[0] == 0


def test_place_1_state_name(small_places):
    assert grade.place_level("I live in North Carolina.", small_places)[0] == 1


def test_place_1_national_forest(small_places):
    assert grade.place_level("the Nantahala National Forest", small_places)[0] == 1


def test_place_2_ranger_district(small_places):
    assert grade.place_level("the Cheoah Ranger District", small_places)[0] == 2


def test_place_3_specific_named_place(small_places):
    assert grade.place_level("sediment in Big Creek", small_places)[0] == 3


def test_place_3_single_word_name_needs_its_cue_word(small_places):
    assert grade.place_level("Snowbird is why I am writing.", small_places)[0] == 0
    assert grade.place_level("the Snowbird roadless area", small_places)[0] == 3
    assert grade.place_level("the Slickrock trail", small_places)[0] == 3


def test_place_3_beats_1_in_the_same_text(small_places):
    assert grade.place_level("In North Carolina, Big Creek runs red.", small_places)[0] == 3


@pytest.mark.parametrize("text,rule", [
    ("washouts on Forest Road 2074", "PLACE.locus.road_number"),
    ("above 4,800 feet the soils are thin", "PLACE.locus.elevation"),
    ("Unit 7 is the problem", "PLACE.locus.unit_number"),
    ("as Map 3 shows", "PLACE.locus.map_figure"),
])
def test_place_3_locus_patterns(text, rule, small_places):
    level, rules = grade.place_level(text, small_places)
    assert level == 3
    assert any(r["rule"] == rule for r in rules)


def test_place_reads_the_shipped_seed_list():
    """The real list, as the pipeline will load it."""
    level, _rules = grade.place_level("sediment in Big Creek below the crossing")
    assert level == 3


# ------------------------------------------------- topics, flags, targets

def test_topics_one_list_per_topic():
    topics, _rules = grade.topics_for(
        "Sediment in the creek will bury trout habitat and the elk herd suffers.")
    assert set(topics) == {"WATER", "BIO"}


def test_topics_other_when_nothing_matches():
    assert grade.topics_for("I disagree with this decision.")[0] == ["OTHER"]


def test_flags_attachments_and_incorporation():
    att, inc, _rules = grade.flags_for(
        "See the attached report. We incorporate by reference the comments of the coalition.")
    assert att is True
    assert inc is True


def test_flags_absent_by_default():
    att, inc, _rules = grade.flags_for("I oppose the rescission.")
    assert (att, inc) == (False, False)


# ----------------------------------------------------------------- grade()

def _parsed(**over):
    obj = {"evidence": {"GAP": "none", "EVID": "none", "ASK": "none",
                        "ALT": "none", "STAND": "none"},
           "gap": 0, "evid_applied": False, "ask_names_action_and_subject": False,
           "alt_distinct": False, "stand_this_place": False,
           "moves": [], "targets": [], "rationale": ""}
    obj.update(over)
    return obj


def test_grade_returns_the_seven_dimensions_law_excluded():
    out = grade.grade(_parsed(), "I oppose this.", "I oppose this.", {})
    assert set(out["scores"]) == {"PLACE", "STAND", "DOC", "GAP", "EVID", "ASK", "ALT"}


def test_grade_adds_m4_when_alt_is_2_or_more():
    out = grade.grade(
        _parsed(evidence={"GAP": "none", "EVID": "none", "ASK": "none",
                          "ALT": "drop Unit 7 while keeping Units 1-6", "STAND": "none"},
                alt_distinct=True, moves=["M1"]),
        "text", "text", {})
    assert out["scores"]["ALT"] == 2
    assert "M4" in out["moves"]


def test_grade_sets_t2_from_the_comments_own_text():
    out = grade.grade(_parsed(targets=["T2"]), "no significance is shown",
                      "no significance is shown", {})
    assert "T2" in out["targets"]
    out = grade.grade(_parsed(targets=["T2"]), "I oppose this.", "I oppose this.", {})
    assert "T2" not in out["targets"]


def test_grade_sets_t4_from_the_citation_scan_not_the_model():
    out = grade.grade(_parsed(targets=["T4"]), "text", "text", {"law_cited": False})
    assert "T4" not in out["targets"]
    out = grade.grade(_parsed(targets=[]), "text", "text", {"law_cited": True})
    assert "T4" in out["targets"]


def test_grade_keeps_only_the_models_own_moves_and_targets():
    out = grade.grade(_parsed(moves=["M1", "M4", "bogus"], targets=["T1", "T2", "T3"]),
                      "text", "text", {})
    assert out["moves"] == ["M1"]          # M4 is code's, and ALT is 0 here
    assert out["targets"] == ["T1", "T3"]  # T2 is code's, and the text has no "significan"


def test_grade_logs_a_rule_for_every_decision():
    out = grade.grade(_parsed(), "I oppose this.", "I oppose this.", {})
    fired = {r["rule"] for r in out["rules"]}
    assert {"GAP.0.no_span", "EVID.0.no_span", "ASK.0.no_span", "ALT.0.no_span",
            "STAND.0.no_span", "DOC.0.no_reference"} <= fired


def test_grade_originality_is_constant():
    assert grade.grade(_parsed(), "text", "text", {})["originality"] == "unknown"


def test_grade_uses_own_text_not_the_full_comment_for_the_code_fields():
    """The campaign's boilerplate must not lend its places to a signer."""
    out = grade.grade(_parsed(), "Big Creek runs red with sediment.", "I agree.", {})
    assert out["scores"]["PLACE"] == 0


def test_sixteen_workers_can_detect_language_from_a_cold_start():
    """langdetect publishes its factory before the profiles are loaded; a
    second thread arriving in that window got "Need to load profiles." Sixteen
    workers starting together is the scoring run's shape."""
    import threading
    import langdetect.detector_factory as df
    df._factory = None                      # cold, as at the start of a run
    text = ("The Forest Service should keep the roadless rule in place because"
            " the watersheds above Big Creek supply the town's drinking water.")
    errors, langs = [], []
    lock = threading.Lock()

    def worker():
        try:
            lang = grade.detect_language(text)
        except Exception as exc:            # what the run printed per comment
            with lock:
                errors.append(f"{type(exc).__name__}: {exc}")
            return
        with lock:
            langs.append(lang)

    threads = [threading.Thread(target=worker) for _ in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == [], errors
    assert langs == ["en"] * 16
