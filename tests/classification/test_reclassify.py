#!/usr/bin/env python3
"""The full re-classification path (docs/design/full-reclassification-run.md).

- The v2 prompt renders exactly the prompt tested on 96 comments (2026-09-24):
  from the seed's template as make schema loads it, and from the DB profile,
  which also checks the topic order.
- One response is judged the way the runner stores it: stop + valid answer is
  received; a cut-off, unparseable, off-taxonomy or out-of-range answer is an
  error, with the whole answer kept.
- The loader supplies sentiment_only's phrase and keeps a '|' inside a phrase.
- replace_groups on a temporary file holding one group of five, inside a
  transaction that is rolled back: every member of the group ends with exactly
  one active row, the group's.

A temporary SQLite file through shared/db.py, holding the schema and the profile
seeds (plan 5.3). No endpoint is called: the runner's client is built from two
environment values the test sets, and port 0 has nothing to answer.

    uv run pytest tests/classification/test_reclassify.py
"""
import dataclasses
import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from shared import db  # noqa: E402
from shared.project_context import ProjectContext  # noqa: E402
from src.pipeline.profile import ProjectProfile  # noqa: E402
from generate_batch_fromfile import _clean_text  # noqa: E402  # pyright: ignore[reportMissingImports]
from load_classifications import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    SENTIMENT_ONLY_PHRASE, _aggregate, replace_groups)
from parse_multi_batch_results import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    classification_rows, parse_completion)
import reclassify_groups as rg  # noqa: E402  # pyright: ignore[reportMissingImports]

PROJECT = "roadless"
FIXTURE = Path(__file__).parent / "fixtures" / "prompt_v2_rendered_user.txt"
SEEDS = _REPO_ROOT / "seeds"
TEST_COMMENT = "We must protect the roadless rule we must protect our forests and wildlife "
TOPICS_V2 = sorted([
    "climate_carbon_storage", "cultural_heritage_indigenous", "economic_impact_fiscal",
    "environmental_protection_biodiversity", "forest_management_wildfire",
    "governance_policy_process", "legal_regulatory_framework",
    "national_security_public_safety", "public_health_wellbeing",
    "public_land_access_rights", "public_opinion_support",
    "recreation_tourism_public_use", "resource_development_extraction",
    "scientific_research_evidence", "tribal_sovereignty", "water_quality_quantity",
    "wildlife_habitat"]) + ["sentiment_only"]
MEMBERS = [f"FS-2025-0001-{n}" for n in range(900001, 900006)]


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    """The project over a temporary file: the schema and the profile seeds as make
    schema loads them, and one exact group of five comments."""
    path = tmp_path_factory.mktemp("db") / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    for name in ("roadless_profile.sql", "roadless_prompt_v2.sql"):
        conn.executescript((SEEDS / name).read_text(encoding="utf-8"))
    conn.executemany("INSERT INTO comment (comment_id, comment_text) VALUES (?, ?)",
                     [(c, TEST_COMMENT * 3) for c in MEMBERS])
    conn.execute("INSERT INTO comment_group (group_id, group_kind, group_key,"
                 " canonical_comment_id, size, first_seen_at)"
                 " VALUES (1, 'exact', 'k', ?, 5, '2026-09-01')", (MEMBERS[0],))
    conn.executemany("INSERT INTO comment_group_member (comment_id, group_id, has_own_text)"
                     " VALUES (?, 1, 0)", [(c,) for c in MEMBERS])
    conn.commit()
    conn.close()
    return dataclasses.replace(ProjectContext.load(PROJECT), db_config={"path": path})


def _profile(template, topics=TOPICS_V2):
    return ProjectProfile(
        prompt_id=0, prompt_kind="sentiment_topic", prompt_name="roadless_rescission_v2",
        system_prompt="", user_prompt_template=template, model_name="qwen/qwen3.8-27b",
        model_parameters={"temperature": 0.0, "top_p": 1.0}, version=2,
        topics=[{"topic_id": i, "topic_name": n, "description": ""}
                for i, n in enumerate(topics, 1)],
        sentiment_map={"SUPPORT": 1, "OPPOSE": 2, "NEUTRAL": 3},
        analysis_schema="roadless")


def test_seed_template_renders_the_tested_prompt(ctx):
    with db.connect(**ctx.db_config) as conn:
        template = conn.execute(
            "SELECT user_prompt_template FROM prompts WHERE is_active").fetchone()[0]
    rendered = _profile(template).render_user_prompt(_clean_text(TEST_COMMENT))
    assert rendered == FIXTURE.read_text(encoding="utf-8")


def test_db_profile_renders_the_tested_prompt(ctx):
    """After seeds/roadless_prompt_v2.sql is applied: the active profile, topic order
    included, renders the tested prompt byte for byte."""
    profile = ProjectProfile.load(ctx, "sentiment_topic")
    assert profile.prompt_name == "roadless_rescission_v2"
    assert profile.render_user_prompt(_clean_text(TEST_COMMENT)) == \
        FIXTURE.read_text(encoding="utf-8")


# ---------------------------------------------------------------- one response

def _payload(content, finish="stop"):
    return {"choices": [{"message": {"content": content}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 1200, "completion_tokens": 60,
                      "prompt_tokens_details": {"cached_tokens": 784}, "cost": 0.0002}}


def _answer(topics, sentiment="OPPOSE|HIGH"):
    return json.dumps({"sentiment": sentiment, "topics": topics})


@pytest.fixture(scope="module")
def run(ctx, tmp_path_factory):
    env = pytest.MonkeyPatch()
    env.setenv("LLM_BASE_URL", "http://127.0.0.1:0/v1")
    env.setenv("LLM_MODEL", "qwen/qwen3.8-27b")
    log = rg.RunLog(tmp_path_factory.mktemp("log") / "t.log")
    yield rg.Run(ctx, _profile("{comment_text}{topics_list}"),
                 "reclass_test", None, 1, 500, log)
    env.undo()


def test_judge_receives_a_valid_answer(run):
    status, kind, _d, c = run._judge("c1", _payload(_answer(
        [{"topic_name": "wildlife_habitat", "confidence": 0.9,
          "supporting_phrases": ["elk calving", "winter range"]}])))
    assert (status, kind) == ("received", None)
    assert c["sentiment"] == "OPPOSE" and c["topics"][0]["topic_name"] == "wildlife_habitat"


def test_judge_cut_off_answer_is_truncated(run):
    status, kind, detail, _c = run._judge("c1", _payload('{"sentiment": "OPP', "length"))
    assert (status, kind) == ("error", "truncated")
    assert "finish_reason=length" in detail


def test_judge_unparseable_keeps_the_whole_answer(run):
    body = "not json " + "x" * 5000
    status, kind, detail, _c = run._judge("c1", _payload(body))
    assert (status, kind) == ("error", "unparseable")
    assert body in detail


def test_judge_unknown_topic(run):
    status, kind, detail, _c = run._judge("c1", _payload(_answer(
        [{"topic_name": "roads", "confidence": 0.9, "supporting_phrases": ["a"]}])))
    assert (status, kind) == ("error", "unknown_topic") and "roads" in detail


def test_judge_confidence_out_of_range(run):
    status, kind, _d, _c = run._judge("c1", _payload(_answer(
        [{"topic_name": "wildlife_habitat", "confidence": 1.5,
          "supporting_phrases": ["a"]}])))
    assert (status, kind) == ("error", "unparseable")


def test_judge_invalid_sentiment(run):
    status, kind, _d, _c = run._judge("c1", _payload(_answer([], sentiment="OPPOSE|VERY")))
    assert (status, kind) == ("error", "invalid_sentiment")


def test_parse_completion_reads_reasoning_channel():
    c, err = parse_completion("c1", {"choices": [{"message": {
        "content": "", "reasoning_content": "thinking... " + _answer([])}}]})
    assert err is None and c is not None and c["sentiment_strength"] == "HIGH"


# ---------------------------------------------------------------- the loader

def test_sentiment_only_gets_the_loader_phrase_and_pipes_survive():
    rows = classification_rows({"comment_id": "c1", "sentiment": "OPPOSE",
                                "sentiment_strength": "HIGH", "topics": [
        {"topic_name": "sentiment_only", "confidence": 1.0, "supporting_phrases": []},
        {"topic_name": "wildlife_habitat", "confidence": 0.8,
         "supporting_phrases": ["elk | deer", "winter range"]}]})
    _comments, topics, skipped = _aggregate(rows, {"SUPPORT": 1, "OPPOSE": 2, "NEUTRAL": 3})
    assert skipped == 0
    assert topics["c1"]["sentiment_only"] == (1.0, [SENTIMENT_ONLY_PHRASE])
    assert topics["c1"]["wildlife_habitat"][1] == ["elk | deer", "winter range"]


def test_replace_groups_gives_every_member_the_group_row(ctx):
    with db.connect(**ctx.db_config) as conn:
        row = conn.execute(ctx.render_sql(
            "SELECT g.group_id, g.canonical_comment_id, g.size"
            " FROM {analysis}.comment_group g"
            " WHERE g.size BETWEEN 3 AND 20"
            " ORDER BY g.group_id LIMIT 1")).fetchone()
        assert row, "no group of 3 to 20 members"
        gid, canonical, size = row
        rows = classification_rows({"comment_id": canonical, "sentiment": "SUPPORT",
                                    "sentiment_strength": "LOW", "topics": [
            {"topic_name": "wildlife_habitat", "confidence": 0.8,
             "supporting_phrases": ["elk calving"]}]})
        comments, topics, _ = _aggregate(rows, {"SUPPORT": 1, "OPPOSE": 2, "NEUTRAL": 3})
        batch = "reclass_test_rollback"
        with conn.transaction(force_rollback=True):
            class_id, n_topics, n_members = replace_groups(
                conn, ctx, [gid], comments, topics, batch, "qwen/qwen3.8-27b")
            assert n_topics == 1 and n_members == size - 1 and canonical in class_id
            active = conn.execute(ctx.render_sql(
                "SELECT m.comment_id, count(cc.classification_id), min(cc.batch_id = ?),"
                "       min(cc.sentiment_id = 1)"
                " FROM {analysis}.comment_group_member m"
                " LEFT JOIN {analysis}.comment_classification cc"
                "   ON cc.comment_id = m.comment_id AND cc.is_active"
                " WHERE m.group_id = ? GROUP BY 1"), (batch, gid)).fetchall()
            assert len(active) == size
            assert all(n == 1 and same and sup for _c, n, same, sup in active), \
                [tuple(a) for a in active]
            n_member_topics = conn.execute(ctx.render_sql(
                "SELECT count(*) FROM {analysis}.classification_topics ct"
                " JOIN {analysis}.comment_classification cc"
                "   ON cc.classification_id = ct.classification_id"
                " WHERE cc.batch_id = ? AND ct.is_active"), (batch,)).fetchone()
            assert tuple(n_member_topics) == (size,)
        still = conn.execute(ctx.render_sql(
            "SELECT count(*) FROM {analysis}.comment_classification WHERE batch_id = ?"),
            (batch,)).fetchone()
        assert tuple(still) == (0,)


def test_runs_listing_names_the_run_and_the_command_to_continue(ctx, capsys):
    """make stance-runs: every run with what it loaded, and the continue command for
    the latest run with groups left; a complete run or none says so."""
    with db.connect(**ctx.db_config) as conn:
        conn.execute("DELETE FROM classification_run_items")
        conn.execute("DELETE FROM classification_runs")
    rg.list_runs(ctx)
    out = capsys.readouterr().out
    assert "eligible groups today: 1" in out and "no stance run yet" in out
    with db.connect(**ctx.db_config) as conn:
        conn.execute("INSERT INTO classification_runs (run_timestamp, prompt_id, model_name, comment_count)"
                     " VALUES ('2026-10-13 21:45:34', 2, 'qwen/qwen3.8-flash', 1)")
    rg.list_runs(ctx)
    out = capsys.readouterr().out
    assert "reclass_20261013_214534  model qwen/qwen3.8-flash  prompt id 2" in out
    assert "loaded 0, errors 0, stored not loaded 0; 1 not yet sent" in out
    assert "to continue reclass_20261013_214534: make stance RUN=reclass_20261013_214534" in out
    assert "--resume reclass_20261013_214534" in out and "--retry-errors" not in out
    with db.connect(**ctx.db_config) as conn:
        conn.execute("INSERT INTO classification_run_items (run_id, group_id, attempt, comment_id,"
                     " status, seconds) VALUES ('reclass_20261013_214534', 1, 1, ?, 'loaded', 1.0)",
                     (MEMBERS[0],))
    rg.list_runs(ctx)
    out = capsys.readouterr().out
    assert "loaded 1, errors 0, stored not loaded 0; complete" in out
    assert "nothing to continue: make stance LIMIT=200 starts a new run" in out
