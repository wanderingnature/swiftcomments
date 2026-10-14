"""The v3 wiring in the pipeline: grade.py runs between the parse and finalize_record.

No DB, no LLM. What is pinned here is the join between the two halves — the
model object arrives with spans and yes/no answers and NO scores, apply_v3_grade
puts code's scores on it, and finalize_record derives gate, strength and band
from those. If the two halves come apart, a v3 run writes zeros without failing.

    uv run pytest tests/substance/test_v3_pipeline.py
"""
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

import score_comments as sc  # noqa: E402  # pyright: ignore[reportMissingImports]


# The shape the v3 schema requires: five spans, the GAP level, four yes/no
# answers, moves, targets, rationale. No scores anywhere in it.
def _model_object():
    return {
        "evidence": {
            "GAP": "the aquatic analysis omits the Appalachian Elktoe",
            "EVID": "the 2019 NCWRC survey found the Elktoe in Big Creek",
            "ASK": "prepare a cumulative sediment analysis before the final EIS",
            "ALT": "drop Unit 7 and keep Units 1-6",
            "STAND": "I have fished Big Creek every fall since 1994",
        },
        "gap": 2,
        "evid_applied": True,
        "ask_names_action_and_subject": True,
        "alt_distinct": True,
        "stand_this_place": True,
        "moves": ["M1", "M5"],
        "targets": ["T1"],
        "rationale": "GAP 2: names the omitted species.",
    }


_TEXT = ("The aquatic analysis omits the Appalachian Elktoe. The 2019 NCWRC survey"
         " found the Elktoe in Big Creek. Prepare a cumulative sediment analysis"
         " before the final EIS. Drop Unit 7 and keep Units 1-6. I have fished Big"
         " Creek every fall since 1994.")

_NO_TAGS = {"authorities": {}, "named_entities": {}}


def test_apply_v3_grade_puts_codes_scores_on_a_model_object_that_has_none():
    obj = _model_object()
    assert "scores" not in obj
    sc.apply_v3_grade(obj, "C1", _TEXT, _NO_TAGS, set())
    assert sorted(obj["scores"]) == ["ALT", "ASK", "DOC", "EVID", "GAP", "PLACE", "STAND"]
    assert obj["scores"]["EVID"] == 3      # named source + a year
    assert obj["scores"]["ASK"] == 3       # action and subject + a timing word
    assert obj["scores"]["ALT"] == 2       # distinct alternative
    assert obj["scores"]["STAND"] == 2     # this place + a frequency
    assert obj["scores"]["GAP"] == 2       # the model's level, span present
    assert obj["language"] == "en"
    assert obj["originality"] == "unknown"
    assert obj["rules"], "every level records the rule that produced it"


def test_finalize_record_derives_from_codes_scores_not_the_models():
    obj = _model_object()
    sc.apply_v3_grade(obj, "C1", _TEXT, _NO_TAGS, set())
    graded = dict(obj["scores"])
    sc.finalize_record(obj, "C1", False, law_cited=set())
    assert obj["scores"]["LAW"] == 0       # mechanical, and this comment cites nothing
    assert obj["strength"] == sum(graded.values())
    assert obj["gate"] is True
    assert obj["gate_basis"] == ["GAP", "EVID", "ALT"]
    assert obj["band"] == sc.band_for(obj["strength"])


def test_law_cited_sets_law_and_t4():
    obj = _model_object()
    sc.apply_v3_grade(obj, "C1", _TEXT, _NO_TAGS, {"C1"})
    assert "T4" in obj["targets"]
    sc.finalize_record(obj, "C1", False, law_cited={"C1"})
    assert obj["scores"]["LAW"] == 2


def test_m4_is_added_when_the_alternative_is_distinct():
    obj = _model_object()
    obj["moves"] = ["M1"]
    sc.apply_v3_grade(obj, "C1", _TEXT, _NO_TAGS, set())
    assert "M4" in obj["moves"]


def test_dropped_v2_fields_stay_absent():
    """v3 does not ask for them; write_score_outputs writes NULL."""
    obj = _model_object()
    sc.apply_v3_grade(obj, "C1", _TEXT, _NO_TAGS, set())
    for field in ("harm_stated", "issue_count"):
        assert field not in obj
    for flag in ("data_offered", "mischaracterization", "off_topic_content"):
        assert flag not in obj["flags"]


def test_the_schema_follows_the_instrument():
    """v3 is the one instrument here; its schema asks for spans and yes/no, no scores."""
    assert sorted(sc.SCHEMAS) == ["v3"] and sorted(sc.INSTRUMENTS) == ["v3"]
    assert "evid_applied" in sc.SCHEMAS["v3"]["properties"]
    assert "scores" not in sc.SCHEMAS["v3"]["properties"]


def test_the_system_prompt_is_the_instruments_quoted_block():
    """Plan 5.2 edit 13: the prompt is the quoted block under '# System prompt',
    up to SECTION D, one quote mark off each line; nothing of the label or the
    deployment notes is sent."""
    prompt = sc.load_system_prompt("v3")
    assert prompt.startswith("You read one public comment on a federal agency action.")
    assert "# SECTION C" in prompt and "# SECTION D" not in prompt
    assert "This is the prompt for step 6" not in prompt
    # The examples of SECTION C are quoted in the instrument itself, so one
    # quote mark is theirs and stays: byte for byte rtca's text.
    assert '> "I strongly oppose this proposal.' in prompt
    assert sc.unquote("> a\n>\n> b") == "a\n\nb"
    import pytest
    with pytest.raises(SystemExit, match="unquoted line"):
        sc.unquote("> a\nb")


def test_json_record_has_the_shared_shape():
    from shared import score_json
    obj = _model_object()
    sc.apply_v3_grade(obj, "C1", _TEXT, _NO_TAGS, set())
    sc.finalize_record(obj, "C1", False, law_cited=set())
    obj["instrument_version"] = "v3"
    rec = score_json.check(sc.json_record(obj, "qwen/qwen3.8-flash"))
    assert rec["scorer"] == "model" and rec["model"] == "qwen/qwen3.8-flash"
    assert rec["levels"]["EVID"] == 3 and rec["gate"] is True and rec["a_level"] is None
    assert [e["dimension"] for e in rec["evidence"]] == ["GAP", "EVID", "ASK", "ALT", "STAND", "rationale"]
    assert rec["evidence"][1]["span"].startswith("the 2019 NCWRC survey")


def test_v3_user_message_is_the_comment_alone():
    """The machine pre-annotation is a v2 hint. The v3 instrument never mentions
    it, and the repeatability runs were made without it."""
    bare = sc.user_message("C1", "", "body")
    assert bare == "COMMENT (comment_id=C1):\n---\nbody\n---"
    assert sc.user_message("C1", "hints", "body").startswith("hints\nCOMMENT")


def test_item_text_is_shared_on_an_exemplar_and_own_everywhere_else():
    class _Shape:
        own_text = "own"
        shared_text = "shared"

    shapes = {"C1": _Shape()}
    assert sc.item_text("exemplar", "C1", shapes) == "shared"
    assert sc.item_text("delta", "C1", shapes) == "own"
    assert sc.item_text("unique", "C1", shapes) == "own"


def test_dry_run_report_prints_the_queue_and_touches_nothing(capsys):
    """The look before a corpus run: counts by kind, the instrument actually
    loaded, and where rows would land."""
    reqs = [{"request_id": "c1#direct", "comment_id": "c1", "kind": "unique",
             "user": "COMMENT (comment_id=c1):\n---\nbody\n---"},
            {"request_id": "c2#exemplar", "comment_id": "c2", "kind": "exemplar",
             "user": "COMMENT (comment_id=c2):\n---\nlonger body here\n---"}]
    sc.dry_run_report(reqs, "v3", "SYSTEM PROMPT", "roadless.substance_scores", "make score")
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "no calls made" in out
    assert "substantive-scoring-v3.md" in out
    assert "2 call(s) over 2 comment(s)" in out
    assert re.search(r"exemplar\s+1", out) and re.search(r"unique\s+1", out)
    assert "roadless.substance_scores" in out
    assert "c1#direct" in out and "c2#exemplar" in out, "every id, not a sample"


def test_the_dry_run_ends_with_the_command_it_would_have_run(capsys):
    """House rule: a step in a chain prints the next command in full."""
    reqs = [{"request_id": "c1#direct", "comment_id": "c1", "kind": "unique",
             "user": "body"}]
    sc.dry_run_report(reqs, "v3", "P", "roadless.substance_scores", "make score")
    out = capsys.readouterr().out
    assert "NEXT: make score" in out


def test_next_steps_labels_the_first_one_next_and_the_rest_then(capsys):
    sc.next_steps(("cmd one", "because"), ("cmd two", "after that"))
    out = capsys.readouterr().out
    assert "NEXT: cmd one" in out and "THEN: cmd two" in out
    assert "because" in out and "after that" in out


# The incremental queue's done set: what a run under one model may skip.
def test_only_a_direct_row_from_the_same_weights_answers_a_unique_item():
    direct = [("c1", "nicholas-212f/eis-advanced"),   # this run's weights
              ("c2", "nicholas-212f/eis"),            # the 9B: another reader
              ("c3", None)]                           # assembled, no call
    done = sc.already_called(direct, [], "nicholas-212f/eis-advanced")
    assert done == {"c1#direct"}


def test_a_part_from_another_model_is_not_done():
    parts = [("c1", "delta", "nicholas-212f/eis"),
             ("c2", "exemplar", "nicholas-212f/eis-advanced"),
             ("c3", "delta", "nicholas-212f/eis-advanced")]
    done = sc.already_called([], parts, "nicholas-212f/eis-advanced")
    assert done == {"c2#exemplar", "c3#delta"}


def test_a_model_name_is_the_same_weights_only_as_itself():
    """One serving, one name (plan 5.2 edit 8): rtca's table of the 27B's serving
    names is gone, so two names are the same weights only when they are equal."""
    from shared.instrument import same_weights
    assert same_weights("nicholas-212f/eis", "nicholas-212f/eis")
    assert not same_weights("nicholas-212f/eis", "nicholas-212f/eis-advanced")
    assert not same_weights(None, "nicholas-212f/eis")
    assert same_weights("some/other-model", "some/other-model")
    assert not same_weights("qwen/qwen3.5-9b", "nicholas-212f/eis")
