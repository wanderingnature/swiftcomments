"""The console's Topics page (console/topics.py) through Streamlit's AppTest,
over the case fixture: before any sentence build, before any case, and with
two cases, one opened from its topics to a cluster's sentences and its noise.

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


def test_two_cases_and_one_opened(casefile):
    assert cases.main(PCA_LEAF + ["--k", "2"]) == 0
    assert cases.main(PCA_LEAF + ["--structure", "by-kind"]) == 0
    at = _topics()
    headers = [h.value for h in at.subheader]
    assert headers == ["The cases", "Its topics", "The clusters of topic 1", "The noise"]
    # the latest case is opened; pick the first, then its second topic and a cluster
    at.selectbox(key="case_pick").set_value("opening+hits.comment.m0.pca50.5-5-leaf.all.p0.k2.s0")
    at.run()
    at.selectbox(key="case_topic").set_value(1)
    at.run()
    at.selectbox(key="case_cluster").set_value(2)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert "The clusters of topic 2" in [h.value for h in at.subheader]
    texts = [m.value for m in at.markdown]
    assert any(t.startswith("**The sentences of cluster") and "(25)" in t for t in texts)
    assert any(t.startswith("**The leaders in no cluster") and "(8)" in t for t in texts)
