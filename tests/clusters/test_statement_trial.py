"""The step 15 trial (scripts/clusters/statement_trial.py): eis-analysis's fold of
near-duplicate wordings, and the wordings of a concern-map cluster both ways, in a
real temporary file with real vectors. The model call is not made here.

    uv run pytest tests/clusters
"""
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db  # noqa: E402
from clusters import cases, statement_trial  # noqa: E402

MERGE_CASE = ["run", "--reduction", "pca50", "--min-cluster-size", "5", "--min-samples", "5",
              "--selection", "leaf", "--sentences", "opening+hits", "--merge", "0.88"]
NAME = "opening+hits.comment.m.m88.pca50.5-5-leaf.all.p0.kauto.s0"


def test_collapse_folds_at_the_threshold_and_keeps_the_longest():
    a = np.array([1.0, 0.0, 0.0])
    near = np.array([1.0, 0.1, 0.0])            # cosine 0.995 to a
    far = np.array([0.0, 1.0, 0.0])
    vecs = {"short": a, "the longer one": near, "other": far}
    groups = statement_trial.collapse(["short", "the longer one", "other"], vecs)
    assert groups == [["the longer one", "short"], ["other"]]
    # below the threshold nothing folds
    assert len(statement_trial.collapse(["short", "the longer one"], vecs, threshold=0.999)) == 2


def test_the_wordings_of_a_cluster_both_ways(casefile):
    assert cases.main(MERGE_CASE) == 0
    conn = db.connect(casefile)
    with pytest.raises(SystemExit, match="no concern map is recorded"):
        statement_trial.concern_map(conn)
    conn.close()
    assert cases.main(["choose", NAME]) == 0
    assert cases.main(["concern-map", NAME]) == 0
    conn = db.connect(casefile)
    case = statement_trial.concern_map(conn)
    w = statement_trial.cluster_wordings(conn, case, 1)
    leaders = w["methods"]["leaders"]["wordings"]
    folded = w["methods"]["collapse"]
    # the case merged at 0.88, so its leaders are fewer than the cluster's sentences; the members of a
    # group sit near 0.87 to each other, so the fold at 0.95 keeps every sentence its own wording
    assert len(leaders) == w["leaders"] < w["texts"] == len(folded["wordings"])
    assert sum(len(g) for g in folded["stands_for"]) == w["texts"]
    assert set(leaders) <= set(folded["wordings"])
    with pytest.raises(SystemExit, match="has no cluster 99"):
        statement_trial.cluster_wordings(conn, case, 99)
    conn.close()


def test_a_case_named_on_the_command_line(casefile):
    with pytest.raises(SystemExit, match="no case 'nope'"):
        statement_trial.main(["--clusters", "1", "--runs", "1", "--temperatures", "0", "--case", "nope",
                                   "--db", str(casefile)])
