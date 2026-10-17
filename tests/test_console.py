"""The console over a real temporary SQLite file made by make schema's script:
every query of console/queries.py runs on the schema, and the app renders each of
its ten pages through Streamlit's AppTest (the script run in-process, no server)
with db.DB_PATH pointed at the file, the results pages over a few rows of every
step.

    uv run pytest tests/test_console.py
"""
import json
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from shared import db, score_json  # noqa: E402
from console import queries as q  # noqa: E402
from console.queries import COMMENT, COMPARE_READINGS, COMPARE_RUNS, STEPS, TABLES  # noqa: E402
from scripts import make_schema  # noqa: E402

APP = _REPO / "console" / "app.py"
CID = "FS-2025-0001-0002"
# Every fixed query of the results pages, with parameters to bind.
RESULT_QUERIES = {
    "RECORDS": (), "GROUPS_BY_KIND": (), "STANCE": (), "STANCE_STRENGTH": (), "TOPICS": (),
    "STANCE_BY_TOPIC": (), "TOPIC_PAIRS": (), "STANCE_BY_DAY": (), "POSTED_RECEIVED": (),
    "TOPIC_LETTER_COUNT": ("t", "", ""), "TOPIC_LETTERS": ("t", "", "", 20, 0),
    "COPIES": (), "CAMPAIGNS": (), "DAILY_WAVE": (), "NAMES_NOTHING": (), "NAMES_NOTHING_SAMPLE": (10,),
    "AREAS": (), "STATES": (), "AUTHORITY_FAMILIES": (), "AUTHORITY_VARIANTS": (), "BIBLIOGRAPHY": (),
    "BIBLIOGRAPHY_ORIGINS": (), "FLOOR": (), "SCREEN": (), "RULESETS": (), "RULES_READING": ("3",),
    "ANSWERABILITY_RUNS": (), "MODEL_READING": (None,), "RULES_FIRED": ("3",),
    "RULES_EVIDENCE": ("3", CID), "MODEL_DETAIL": (CID,), "COMMENT_CARD": (CID,),
    "COMMENT_TOPICS": (CID,), "COMMENT_NAMES": (CID,) * 6,
}


@pytest.fixture
def dbfile(tmp_path, monkeypatch):
    path = tmp_path / "roadless.sqlite"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(sys, "argv", ["make_schema.py"])
    make_schema.main()
    conn = db.connect(path)
    conn.execute("INSERT INTO comment (comment_id, comment_text, posted_date, received_date)"
                 " VALUES (?, 'Keep the roadless rule. It protects the Tongass.', "
                 "'2026-08-20T04:00Z', '2026-08-19T00:00Z')", (CID,))
    conn.execute("INSERT INTO attachment_file VALUES (?, 1, 'pdf', 'https://example.test/a.pdf')", (CID,))
    conn.execute("INSERT INTO comment_dedup (comment_id, content_hash, is_original) VALUES (?, 'h', 1)", (CID,))
    conn.commit()
    conn.close()
    return path


def test_every_query_runs_on_the_schema(dbfile):
    conn = db.connect(dbfile)
    for step in STEPS:
        for label, sql in step["figures"]:
            if step["target"] == "facts":
                continue        # comment_facts is built by make facts, not the schema
            assert conn.execute(sql).fetchone() is not None, (step["target"], label)
        for label, sql in step["breakdowns"]:
            conn.execute(sql).fetchall()
    for title, sql in COMMENT:
        conn.execute(sql, (CID,) * sql.count("?")).fetchall()
    for name, params in RESULT_QUERIES.items():
        conn.execute(getattr(q, name), params).fetchall()
    for kind in q.TAGS:
        conn.execute(q.tag_comments(kind)).fetchall()
        conn.execute(q.tag_top(kind)).fetchall()
        conn.execute(q.tag_letters(kind), ("x",)).fetchall()
    conn.execute(COMPARE_RUNS).fetchall()
    conn.execute(COMPARE_READINGS, ("r",)).fetchall()
    names = [r["name"] for r in conn.execute(TABLES)]
    assert "comment" in names and "v_source_comments" in names
    conn.close()


def _run(at):
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _page(name):
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.radio(key="page").set_value(name)
    return _run(at)


def test_steps_page_renders(dbfile):
    at = _page("Steps")
    headers = [h.value for h in at.subheader]
    assert headers[0] == "make schema" and headers[-1] == "make facts"
    assert len(headers) == len(STEPS)
    # the corpus step has rows, the floor has none, comment_facts has no table
    texts = [t.value for t in at.text]
    assert any("not run" in t for t in texts)


def test_comment_page_renders(dbfile):
    at = _page("Comment")
    at.text_input[0].set_value(CID)
    _run(at)
    assert [h.value for h in at.subheader] == ["Its letter", "Stance and topics", "What it names", "Substance"]
    assert any("Tongass" in m.value for m in at.markdown)
    assert at.expander[0].label == "Every row the steps hold about it"
    assert [m.value for m in at.expander[0].markdown] == [f"**{title}**" for title, _ in COMMENT]
    at.text_input[0].set_value("FS-2025-0001-99999")
    _run(at)
    assert at.error[0].value == "no comment FS-2025-0001-99999"


def test_tables_page_renders(dbfile):
    at = _page("Tables")
    at.selectbox[0].set_value("comment (table)")
    _run(at)
    assert any(t.value == "1 rows" for t in at.text)
    assert len(at.dataframe) == 1


def test_query_page_is_read_only(dbfile):
    at = _page("Query")
    at.text_area[0].set_value("SELECT count(*) AS n FROM comment")
    at.button[0].click()
    _run(at)
    assert at.dataframe[0].value.iloc[0]["n"] == 1
    at.text_area[0].set_value("DELETE FROM comment")
    at.button[0].click()
    _run(at)
    assert "readonly" in at.error[0].value
    conn = db.connect(dbfile)
    assert conn.execute("SELECT count(*) FROM comment").fetchone()[0] == 1
    conn.close()


def _reading(scorer, gap):
    levels = {d: 0 for d in score_json.DIMS}
    levels["GAP"] = gap
    return {"comment_id": CID, "scorer": scorer, "instrument": "v3" if scorer == "model" else "rules-3",
            "model": "m" if scorer == "model" else None, "levels": levels, "strength": gap,
            "gate": gap >= 2, "gate_basis": [], "band": "minimal", "a_level": None, "evidence": []}


def test_compare_page_renders(dbfile):
    at = _page("Compare")
    assert any("no comparison run yet" in t.value for t in at.text)

    conn = db.connect(dbfile)
    for run_id, model_gap, rules_gap in (("20261016_100000", 2, 1), ("20261016_110000", 2, 2)):
        conn.execute("INSERT INTO score_compare_run (run_id, started_at, finished_at, code_version,"
                     " code_dirty, model, server, instrument_version, ruleset_version, pool, picked, report)"
                     " VALUES (?, 's', 'f', ?, 0, 'm', 'http://x', 'v3', '3', 1, 1, ?)",
                     (run_id, run_id * 2, f"report of {run_id}"))
        for method, gap in (("model", model_gap), ("model-free", rules_gap)):
            conn.execute("INSERT INTO score_compare_reading (run_id, comment_id, method, record)"
                         " VALUES (?, ?, ?, ?)",
                         (run_id, CID, method, json.dumps(_reading("model" if method == "model" else "rules", gap))))
    conn.commit()
    conn.close()
    _run(at)
    # the runs; one run's per-dimension and gate tables (it differs on nothing);
    # the two-reading pair's tables and its differing comment, opened to its eight dimensions
    texts = [t.value for t in at.text]
    assert "A: run 20261016_100000, model    B: run 20261016_110000, model-free" in texts
    assert "comments that differ: 0 on the gate, 0 more on a level" in texts
    assert len(at.dataframe) == 5
    # The rules' reading of the two runs set side by side: GAP moved from 1 to 2.
    at.selectbox(key="a_method").set_value("model-free")
    _run(at)
    texts = [t.value for t in at.text]
    assert "comments that differ: 1 on the gate, 0 more on a level" in texts
    assert at.expander[0].label == f"{CID}: A closed, B open"
    detail = at.dataframe[-1].value
    gap = detail[detail["dimension"] == "GAP"].iloc[0]
    assert (gap["A"], gap["B"], gap["differs"]) == (1, 2, "*")


# ------------------------------------------------------------ the results pages

C2, C3, C4 = "FS-2025-0001-0003", "FS-2025-0001-0004", "FS-2025-0001-0005"
CAMPAIGN_TEXT = "Rescind the roadless rule; it locks up the forest and stops management."
DISMISSALS = ["certified_not_substantive", "no_cause_effect", "outside_scope", "misinterpreted",
              "alternative_eliminated", "deferred_to_site_specific", "not_required", "policy_preference_noted"]


@pytest.fixture
def results_file(dbfile):
    """A few rows of every step over four comments: CID a unique letter that
    names the Tongass and cites 36 CFR 294, read by both substance readings;
    C2 and C3 one campaign's letter; C4 a unique letter that names nothing."""
    conn = db.connect(dbfile)
    conn.executemany("INSERT INTO comment (comment_id, comment_text, posted_date, received_date) VALUES (?, ?, ?, ?)",
                     [(C2, CAMPAIGN_TEXT, "2026-08-21T04:00Z", "2026-08-20T00:00Z"),
                      (C3, CAMPAIGN_TEXT, "2026-08-21T04:00Z", "2026-08-20T00:00Z"),
                      (C4, "I like trees.", "2026-08-22T04:00Z", "2026-08-21T00:00Z")])
    conn.executemany("INSERT INTO comment_dedup (comment_id, content_hash, is_original, original_comment_id)"
                     " VALUES (?, ?, ?, ?)", [(C2, "c", 1, None), (C3, "c", 0, C2), (C4, "d", 1, None)])
    for gid, kind, key, members in ((1, "singleton", CID, [CID]), (2, "campaign", "f1", [C2, C3]),
                                    (3, "singleton", C4, [C4])):
        conn.execute("INSERT INTO comment_group (group_id, group_kind, group_key, canonical_comment_id, size,"
                     " first_seen_at, family_id) VALUES (?, ?, ?, ?, ?, '2026-08-19', ?)",
                     (gid, kind, key, members[0], len(members), 1 if kind == "campaign" else None))
        conn.executemany("INSERT INTO comment_group_member (comment_id, group_id, has_own_text) VALUES (?, ?, 0)",
                         [(m, gid) for m in members])
    conn.execute("INSERT INTO text_family (family_id, exemplar_comment_id, core_kind, n_texts, n_comments,"
                 " is_campaign, family_text_min, params) VALUES (1, ?, 'exact', 1, 2, 1, 1, '{}')", (C2,))
    conn.executemany("INSERT INTO text_family_member (comment_id, family_id, joined_via, has_own_text)"
                     " VALUES (?, 1, 'core', 0)", [(C2,), (C3,)])
    conn.execute("INSERT INTO family_organisation (family_id, organisation, basis, evidence)"
                 " VALUES (1, 'Example Timber Association', 'letter', 'named in the letter')")
    topics = [r[0] for r in conn.execute("SELECT topic_id FROM topics ORDER BY topic_id LIMIT 2")]
    for i, (cid, stance, strength) in enumerate(((CID, 2, "HIGH"), (C2, 1, "LOW"), (C3, 1, "LOW"),
                                                 (C4, 3, "MEDIUM")), start=1):
        conn.execute("INSERT INTO comment_classification (classification_id, comment_id, sentiment_id,"
                     " sentiment_strength, batch_id) VALUES (?, ?, ?, ?, 'b')", (i, cid, stance, strength))
        for rank, topic in enumerate(topics, start=1):
            conn.execute("INSERT INTO classification_topics (classification_id, topic_id, confidence,"
                         " supporting_phrases, rank_order) VALUES (?, ?, 0.9, '[\"keep the rule\"]', ?)",
                         (i, topic, rank))
    conn.executemany("INSERT INTO entity_scan_state VALUES (?, 1, 1)", [(c,) for c in (CID, C2, C3, C4)])
    conn.execute("INSERT INTO roadless_areas (name, forest) VALUES ('Kuiu', 'Tongass National Forest')")
    conn.execute("INSERT INTO comment_forests (comment_id, forest_name, matched_text, mode)"
                 " VALUES (?, 'Tongass National Forest', 'Tongass', 'strict')", (CID,))
    conn.execute("INSERT INTO comment_areas (comment_id, area_name, matched_text, mode)"
                 " VALUES (?, 'Kuiu', 'Kuiu', 'strict')", (CID,))
    conn.execute("INSERT INTO comment_authorities (comment_id, citation, matched_text, mode, family_key)"
                 " VALUES (?, '36 CFR 294', '36 CFR 294', 'strict', '36 CFR 294')", (CID,))
    conn.execute("INSERT INTO authority_family VALUES ('36 CFR 294', 1)")
    conn.execute("INSERT INTO cited_references (seed_id, display, citation_key) VALUES ('s1', 'DEIS 2025', 'deis2025')")
    conn.execute("INSERT INTO comment_cited_references (comment_id, citation_key, matched_text, mode)"
                 " VALUES (?, 'deis2025', 'the DEIS', 'strict')", (CID,))
    conn.execute("INSERT INTO comment_zipcodes (comment_id, zipcode, city, state, matched_text, mode)"
                 " VALUES (?, '99801', 'Juneau', 'AK', 'Juneau, AK 99801', 'strict')", (CID,))
    conn.executemany("INSERT INTO substance_floor (comment_id, floored, has_entity, has_citation, has_deficiency,"
                     " has_firstperson) VALUES (?, ?, ?, ?, 0, 0)", [(CID, 0, 1, 1), (C2, 0, 0, 1), (C4, 1, 0, 0)])
    conn.execute("INSERT INTO substance_screen (comment_id, screen_class, authority, reference, doc_cite,"
                 " action_ref, deficiency, evid_ner) VALUES (?, 'A', 1, 1, 0, 0, 0, 0)", (CID,))
    conn.execute("INSERT INTO mf_score_run (ruleset_version, started_at) VALUES ('3', 's')")
    conn.execute("INSERT INTO mf_comment_score VALUES ('3', ?, 1, 2, 0, 1, 0, 0, 0, 0, 2, 5, 1,"
                 " '[{\"dimension\": \"LAW\", \"unit_id\": -100001}]', 'minimal', '[]', '[]', 1)", (CID,))
    conn.execute("INSERT INTO mf_comment_answerability VALUES ('3', ?, 1, 'A1', '[]', '[]', 0, 1)", (CID,))
    conn.execute("INSERT INTO mf_sentence_score VALUES ('3', -100001, 1, ?, 0, 48, 'k', 2, 0, 1, 0, 0, 0, 0, 2,"
                 " 5, 1, '[]', 'minimal', '[]', '[]', 0, 0, 0, 0, 0, '[]')", (CID,))
    conn.execute("INSERT INTO mf_sentence_hit (ruleset_version, unit_id, run_id, dimension, grade, rule, match,"
                 " start_char, end_char) VALUES ('3', -100001, 1, 'LAW', 2, 'LAW.2.confirmed_authority',"
                 " 'roadless rule', 9, 22)")
    conn.execute("INSERT INTO substance_scores (comment_id, was_floored, gate, strength, strength_check, band,"
                 " place, stand, doc, gap, evid, ask, alt, law, gate_basis, rationale, instrument_version)"
                 " VALUES (?, 0, 1, 4, 4, 'minimal', 2, 0, 0, 0, 0, 0, 0, 2, '[\"LAW\"]', 'cites the rule', 'v3')",
                 (CID,))
    conn.execute("INSERT INTO answerability_run (run_id, rater, evidence, weights_version, instrument_version)"
                 " VALUES (1, 'rules', 'text_only', 'w1', 'v3')")
    conn.execute("INSERT INTO substance_answerability (run_id, comment_id, a_level, gated, limbs_reached,"
                 " answerability, dismissals_defeated, dismissals_open, mechanism)"
                 " VALUES (1, ?, 'A1', 1, '[]', 1.0, '[\"addressed_in_analysis\"]', ?, 0)",
                 (CID, json.dumps(DISMISSALS)))
    conn.commit()
    conn.close()
    return dbfile


def test_overview_page(results_file):
    at = _page("Overview")
    figures = {m.label: m.value for m in at.metric}
    assert figures["Records"] == "4" and figures["Unique letters"] == "3"
    assert figures["SUPPORT"] == "2 (50.0%)" and figures["Class A"] == "1"
    readings = at.dataframe[-1].value
    assert list(readings["reading"]) == ["rules (make score-model-free, rule set 3)",
                                         "model (make score-model, instrument v3)"]
    assert list(readings["A1 strong"]) == [1, 1]


def test_stance_page(results_file):
    at = _page("Stance and topics")
    assert "Read one topic's letters" in [h.value for h in at.subheader]
    cards = [m.value for m in at.markdown if m.value.startswith("**") and "`FS-" in m.value]
    # the first topic's letters, most-sent first: the campaign's letter, then the two unique ones
    assert cards[0] == f"**SUPPORT** (LOW) · one of 2 sent (Campaign) · `{C2}`"
    assert len(cards) == 3
    at.radio(key="topic_stance").set_value("OPPOSE")
    _run(at)
    cards = [m.value for m in at.markdown if m.value.startswith("**") and "`FS-" in m.value]
    assert cards == [f"**OPPOSE** (HIGH) · a unique letter · `{CID}`"]


def test_coordination_page(results_file):
    at = _page("Coordination")
    figures = {m.label: m.value for m in at.metric}
    assert figures["Exact copies"] == "1" and figures["Campaigns"] == "1"
    assert figures["With an organisation found"] == "1"
    assert at.expander[0].label.startswith("2 comments · Example Timber Association · SUPPORT · Rescind")


def test_places_page(results_file):
    at = _page("Places and citations")
    figures = {m.label: m.value for m in at.metric}
    assert figures["Name a national forest"] == "1" and figures["Name nothing"] == "3"
    families = at.dataframe[0].value
    assert families.iloc[0]["origin"] == "in the agency record"
    assert families.iloc[0]["as written"] == "36 CFR 294 (1)"
    # the letters naming the forest, then the three comments that name nothing
    assert at.expander[0].label.startswith("1 naming · a unique letter · Keep the roadless rule")
    assert len(at.expander) == 1 + 3


def test_substance_page(results_file):
    at = _page("Substance")
    figures = {m.label: m.value for m in at.metric}
    assert figures["Floored"] == "1" and figures["Survive"] == "2"
    assert figures["Scored letters"] == "1" and figures["A1: must be answered"] == "1"
    card = [m.value for m in at.markdown if f"`{CID}`" in m.value]
    assert card == [f"**5 of 24** · Minimal · gate open (LAW) · A1 strong · `{CID}`"]
    # the rules' evidence under the comment's text
    assert at.dataframe[-1].value.iloc[0]["rule"] == "LAW.2.confirmed_authority"
    at.radio(key="reading").set_value("model (make score-model, instrument v3)")
    _run(at)
    card = [m.value for m in at.markdown if f"`{CID}`" in m.value]
    assert card == [f"**4 of 24** · Minimal · gate open (LAW) · A1 strong · `{CID}`"]
    assert "_cites the rule_" in [m.value for m in at.markdown]
    at.selectbox(key="f_gate").set_value("closed")
    _run(at)
    assert "0 letters match." in [c.value for c in at.caption]


def test_comment_page_reads_the_comment(results_file):
    at = _page("Comment")
    at.text_input[0].set_value(CID)
    _run(at)
    lines = [m.value for m in at.markdown]
    assert "a unique letter" in lines
    assert any(v.startswith("**OPPOSE** (HIGH): ") for v in lines)
    assert any(v.startswith("**rules (make score-model-free, rule set 3)**: 5 of 24") for v in lines)
    assert any(v.startswith("**model (make score-model, instrument v3)**: 4 of 24") for v in lines)
    names = at.dataframe[0].value
    assert set(names["kind"]) == {"forest", "roadless area", "legal authority", "cited reference", "zip code"}
