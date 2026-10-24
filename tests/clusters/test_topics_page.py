"""The console's Topics page (console/topics.py) through Streamlit's AppTest,
over the case fixture: the status of the five stages, stage 4 (a case selected
and chosen), Read a case (following the selected case; a sentence opening to its
comments), and stage 5 (the two choices compared, one decided as the concern map).

    uv run pytest tests/clusters
"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db  # noqa: E402
from clusters import cases  # noqa: E402

APP = _REPO / "console" / "app.py"
PCA_LEAF = ["run", "--reduction", "pca50", "--min-cluster-size", "5", "--min-samples", "5",
            "--selection", "leaf", "--sentences", "opening+hits"]
K2 = "opening+hits.comment.m.m0.pca50.5-5-leaf.all.p0.k2.s0"
AUTO = "opening+hits.comment.m.m0.pca50.5-5-leaf.all.p0.kauto.s0"
BGE = "opening+hits.comment.bge-large-en-v1-5.m0.pca50.5-5-leaf.all.p0.kauto.s0"


def _topics():
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.radio(key="page").set_value("Topics")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def _lines(at):
    return [m.value for m in at.markdown if m.value.startswith("**") and "**: " in m.value]


def _two_models(casefile):
    conn = db.connect(casefile)
    conn.execute("INSERT INTO sentence_embedding SELECT text_key, 'BAAI/bge-large-en-v1.5', instruction,"
                 " input_sha256, dimensions, vector, created_at FROM sentence_embedding WHERE model = 'm'")
    conn.commit()
    conn.close()
    assert cases.main(PCA_LEAF + ["--model", "m"]) == 0
    assert cases.main(PCA_LEAF + ["--model", "m", "--k", "2"]) == 0
    assert cases.main(PCA_LEAF + ["--model", "BAAI/bge-large-en-v1.5"]) == 0


def test_the_status_before_any_case(casefile):
    at = _topics()
    lines = _lines(at)
    assert lines[0].startswith("**1. Sentences**: done. 158 sentences of 158 gate-open comments.")
    assert lines[1] == "**2. Vectors**: **next**. m 158 of 158"    # one model; the stage needs two
    assert at.code[0].value == "make embed VIEW=plain"
    assert [t.label for t in at.tabs] == ["Guide"]
    assert at.tabs[0].markdown[0].value.startswith("# Topics: from the sentences to the concern map")
    conn = db.connect(casefile)
    conn.execute("DELETE FROM gate_sentence_run")
    conn.commit()
    conn.close()
    at = _topics()
    assert _lines(at)[0] == "**1. Sentences**: **next**."
    assert at.code[0].value == "make sentences"


def test_stage_4_selects_and_chooses_a_case(casefile):
    assert cases.main(PCA_LEAF) == 0
    assert cases.main(PCA_LEAF + ["--k", "2"]) == 0
    at = _topics()
    assert [t.label for t in at.tabs] == ["Guide", "Stage 4: Best case of each model", "Stage 5: Concern map",
                                          "Read a case"]
    stage4 = at.tabs[1]
    assert "No case is chosen for m." in [x.value for x in stage4.info]
    assert "Click a point on the chart to select a case." in [c.value for c in stage4.caption]
    table = stage4.dataframe[0].value
    assert list(table["case"]) == [1, 2] and list(table["chosen"]) == ["", ""]
    assert list(table["description"]) == [
        "m, comment view · gate-opening and whole-comment hit sentences · PCA, HDBSCAN 5/5 leaf · topics at the eigengap",
        "m, comment view · gate-opening and whole-comment hit sentences · PCA, HDBSCAN 5/5 leaf · 2 topics"]
    assert "Stage 4 is not done." in at.tabs[2].info[0].value
    # a click on the chart's point sets step1_case; Read a case follows it
    at.session_state["step1_case"] = K2
    at.run()
    assert any(m.value.startswith("**Case 2**:") for m in at.tabs[1].markdown)
    assert at.selectbox(key="read_case").value == 1
    at.text_input(key="step1_note").set_value("two topics read best")
    at.button(key="step1_choose").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    conn = db.connect(casefile)
    assert [tuple(r) for r in conn.execute("SELECT model, case_name, note FROM cluster_case_choice")] == [
        ("m", K2, "two topics read best")]
    conn.close()
    assert any(x.value.startswith("The choice for m is case 2:") for x in at.tabs[1].success)
    assert list(at.tabs[1].dataframe[0].value["chosen"]) == ["", "yes"]
    # the chart of the cases; the four of Read a case; once asked for, how alike the cases are
    assert len(at.get("vega_lite_chart")) == 5
    at.toggle(key="agreement_on").set_value(True)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.get("vega_lite_chart")) == 6


def test_stage_5_compares_the_two_choices_and_decides(casefile):
    _two_models(casefile)
    assert cases.main(["choose", K2]) == 0
    assert cases.main(["choose", BGE]) == 0
    at = _topics()
    assert at.radio(key="step1_model").options == ["BGE-large-en-v1.5", "m"]
    lines = _lines(at)
    assert lines[3].startswith("**4. Best case of each model**: done.")
    assert lines[4] == "**5. Concern map**: **next**. Not decided."
    stage5 = at.tabs[2]
    assert "First choice" in stage5.markdown[1].value and "Second choice" in stage5.markdown[1].value
    assert not [s for s in stage5.selectbox]           # no other case can be picked here
    shown = {m.label: m.value for m in stage5.metric}
    assert shown["Adjusted Rand"] == "1.0" and shown["Clusters kept together"] == "6 of 6"
    assert "No case is the concern map." in [x.value for x in stage5.info]
    at.text_input(key="step2_note").set_value("groups by claim")
    at.button(key="step2_use_m").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    conn = db.connect(casefile)
    assert [tuple(r) for r in conn.execute("SELECT case_name, note FROM cluster_concern_map")] == [
        (K2, "groups by claim")]
    conn.close()
    assert any(x.value.startswith("The concern map is the m choice:") for x in at.tabs[2].success)
    assert "This case is the concern map." in [m.value for m in at.tabs[2].markdown]
    assert _lines(at)[4].startswith("**5. Concern map**: done.")


def test_read_a_case_opens_a_sentence_to_its_comments(casefile):
    conn = db.connect(casefile)
    conn.execute("INSERT INTO comment (comment_id, comment_text) SELECT o.comment_id, 'The whole letter of '"
                 " || o.comment_id || '. ' || s.text FROM gate_sentence_occurrence o JOIN gate_sentence s"
                 " ON s.text_key = o.text_key")
    conn.commit()
    conn.close()
    assert cases.main(PCA_LEAF) == 0
    at = _topics()
    read = at.tabs[3]
    labels = [e.label for e in read.expander]
    assert sum(1 for x in labels if x.startswith("Topic ")) == 2
    assert sum(1 for m in read.markdown if m.value.startswith("**Cluster ")) == 6
    texts = [m.value for m in read.markdown]
    assert any(t.startswith("**The sentences of cluster 1**") and "(25)" in t for t in texts)
    assert any(t.startswith("**Sentences in no cluster") and "(8)" in t for t in texts)
    toggles = [t for t in read.toggle if t.key.startswith("read_cluster_page_")]
    assert len(toggles) == 20      # one page of 25
    toggles[0].set_value(True)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    opened = [e for e in at.tabs[3].expander if e.label.startswith("c")]
    assert len(opened) == 1 and "The whole letter of" in opened[0].label
    assert opened[0].markdown[0].value.startswith("The whole letter of ")
