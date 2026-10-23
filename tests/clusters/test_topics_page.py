"""The console's Topics page (console/topics.py) through Streamlit's AppTest,
over the case fixture: before any sentence build, before any case, and with
two cases: the guide, the cases in words, one case read from its topics to a
cluster's sentences, and two cases compared.

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


def _topics():
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.radio(key="page").set_value("Topics")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_before_any_case(casefile):
    at = _topics()
    assert any("make clusters has not run" in c.value for c in at.caption)
    conn = db.connect(casefile)
    conn.execute("DELETE FROM gate_sentence_run")
    conn.commit()
    conn.close()
    at = _topics()
    assert any("make sentences has not run" in c.value for c in at.caption)


def test_the_four_tabs(casefile):
    assert cases.main(PCA_LEAF + ["--k", "2"]) == 0
    assert cases.main(PCA_LEAF + ["--structure", "by-kind"]) == 0
    at = _topics()
    assert [t.label for t in at.tabs] == ["Guide", "Step 1: The best case of each model", "Read a case",
                                          "Step 2: Compare the two choices"]
    assert "No case is chosen for m yet." in [x.value for x in at.tabs[1].info]
    assert 'make choose CASE="' in at.tabs[1].code[0].value
    assert at.tabs[3].warning[0].value.startswith("Step 1 has not chosen a case for each model yet.")
    guide = at.tabs[0].markdown[0].value
    assert guide.startswith("# Choosing a clustering case") and "## Glossary" in guide
    # the cases in words
    descriptions = list(at.tabs[1].dataframe[0].value["case"])
    assert list(at.tabs[1].dataframe[0].value["chosen"]) == ["", ""]
    assert descriptions == ["m, comment view · gate-opening and whole-comment hit sentences · PCA, HDBSCAN 5/5 leaf"
                            " · 2 topics",
                            "m, comment view · gate-opening and whole-comment hit sentences · PCA, HDBSCAN 5/5 leaf,"
                            " by gate kind · topics at the eigengap"]
    # read the first case: its two topics, a cluster's 25 sentences, the 8 in no cluster
    at.selectbox(key="read_case").set_value(0)
    at.run()
    labels = [e.label for e in at.tabs[2].expander]
    assert sum(1 for x in labels if x.startswith("Topic ")) == 2
    texts = [m.value for m in at.tabs[2].markdown]
    assert any(t.startswith("**The sentences of cluster 1**") and "(25)" in t for t in texts)
    assert any(t.startswith("**Sentences in no cluster") and "(8)" in t for t in texts)
    # compare the two: the six groups are found both ways
    at.selectbox(key="compare_first").set_value(0)
    at.selectbox(key="compare_second").set_value(1)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    shown = {m.label: m.value for m in at.tabs[3].metric}
    assert shown["Adjusted Rand"] == "1.0" and shown["Clusters kept together"] == "6 of 6"
    # the charts: the coverage map; the topics by kind, the sizes, the cut, the cluster map; the share
    # spread and the crossing; and, once asked for, the agreement of every pair
    assert len(at.get("vega_lite_chart")) == 7
    at.toggle(key="agreement_on").set_value(True)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert len(at.get("vega_lite_chart")) == 8


def test_step_2_opens_on_the_two_choices(casefile):
    conn = db.connect(casefile)
    conn.execute("INSERT INTO sentence_embedding SELECT text_key, 'BAAI/bge-large-en-v1.5', instruction,"
                 " input_sha256, dimensions, vector, created_at FROM sentence_embedding WHERE model = 'm'")
    conn.commit()
    conn.close()
    assert cases.main(PCA_LEAF + ["--model", "m"]) == 0
    assert cases.main(PCA_LEAF + ["--model", "m", "--k", "2"]) == 0
    assert cases.main(PCA_LEAF + ["--model", "BAAI/bge-large-en-v1.5"]) == 0
    assert cases.main(["choose", "opening+hits.comment.m.m0.pca50.5-5-leaf.all.p0.k2.s0"]) == 0
    assert cases.main(["choose", "opening+hits.comment.bge-large-en-v1-5.m0.pca50.5-5-leaf.all.p0.kauto.s0"]) == 0
    at = _topics()
    assert at.radio(key="step1_model").options == ["BGE-large-en-v1.5", "m"]
    assert any(x.value.startswith("The choice for BGE-large-en-v1.5:") for x in at.tabs[1].success)
    assert any("are the choices of step 1" in c.value for c in at.tabs[3].caption)
    picked = {at.selectbox(key="compare_first").value, at.selectbox(key="compare_second").value}
    assert picked == {1, 2}      # the K=2 case of m and the BGE case
    shown = {m.label: m.value for m in at.tabs[3].metric}
    assert shown["Adjusted Rand"] == "1.0"
