"""Steps 12 to 14, the clustering cases (scripts/clusters/cases.py and
analysis.py), in a real temporary file with real vectors: six groups of
sentences in two families, made from fixed points, and a few strays. The
leader merge, the clusters, the topics and their cut, the names, the
measures, by kind, the noise passes, UMAP, a case's rows kept apart from
another's, and the stops.

    uv run pytest tests/clusters
"""
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db  # noqa: E402
from clusters import cases  # noqa: E402

PCA_LEAF = ["run", "--reduction", "pca50", "--min-cluster-size", "5", "--min-samples", "5",
            "--selection", "leaf", "--sentences", "opening+hits"]


def _case(conn, name):
    return conn.execute("SELECT * FROM cluster_case WHERE case_name = ?", (name,)).fetchone()


def test_six_groups_two_topics(casefile, capsys):
    assert cases.main(PCA_LEAF + ["--k", "2"]) == 0
    name = "opening+hits.comment.m.m0.pca50.5-5-leaf.all.p0.k2.s0"
    assert f"case {name}" in capsys.readouterr().out
    conn = db.connect(casefile)
    c = _case(conn, name)
    assert (c["input_sentences"], c["leaders"], c["clusters"], c["topics"]) == (158, 158, 6, 2)
    assert (c["leaders_clustered"], c["largest_cluster"]) == (150, 25)
    # every comment of a group has its sentence clustered; the strays' comments do not
    assert (c["gate_comments"], c["comments_unclustered"]) == (158, 8)
    assert (c["opening_occurrences"], c["opening_occurrences_clustered"]) == (146, 138)
    assert len(c["code_version"]) == 40 and c["model"] == "m" and c["sentence_run_id"] == 1
    # each topic is one family: its clusters' sentences all carry the family word
    for t in (1, 2):
        rows = conn.execute("SELECT central FROM cluster_case_cluster WHERE case_name = ? AND topic = ?",
                            (name, t)).fetchall()
        assert len(rows) == 3
        fams = {w for r in rows for s in json.loads(r[0]) for w in ("wildfire", "water") if w in s}
        assert len(fams) == 1
    # names by class-based tf-idf: a term counts when two or more classes have it (min_df 2), so the
    # family word names each of the family's three clusters
    for r in conn.execute("SELECT terms, central FROM cluster_case_cluster WHERE case_name = ?", (name,)):
        fam = "wildfire" if "wildfire" in r[1] else "water"
        assert fam in json.loads(r[0])
    assert conn.execute("SELECT count(*) FROM cluster_case_topic WHERE case_name = ?", (name,)).fetchone()[0] == 2
    # the kind shares and tightness of a cluster
    row = conn.execute("SELECT law, evid, gap, alt, tightness, pass FROM cluster_case_cluster WHERE case_name = ?"
                       " AND cluster = 1", (name,)).fetchone()
    assert sum(row[:4]) == 1.0 and row["tightness"] > 0.9 and row["pass"] == 1
    conn.close()


def test_the_eigengap_cut_and_its_candidates(casefile):
    assert cases.main(PCA_LEAF) == 0
    conn = db.connect(casefile)
    c = _case(conn, "opening+hits.comment.m.m0.pca50.5-5-leaf.all.p0.kauto.s0")
    gaps = json.loads(c["eigengaps"])
    assert c["topics"] == gaps[0][0] and len(gaps) >= 2
    conn.close()


def test_sentences_axis_and_merge(casefile):
    # the gate-opening sentences alone: two of each group are left out
    assert cases.main(PCA_LEAF[:-2] + ["--sentences", "opening"]) == 0
    # a merge at 0.8: the members of a group (cosine about 0.87 to each other) collapse into leaders
    assert cases.main(PCA_LEAF + ["--merge", "0.8"]) == 0
    conn = db.connect(casefile)
    c = _case(conn, "opening.comment.m.m0.pca50.5-5-leaf.all.p0.kauto.s0")
    assert c["input_sentences"] == 146
    m = _case(conn, "opening+hits.comment.m.m80.pca50.5-5-leaf.all.p0.kauto.s0")
    assert m["leaders"] < m["input_sentences"] == 158
    absorbed = conn.execute("SELECT count(*) FROM cluster_case_leader WHERE case_name = ? AND text_key <> leader_key",
                            (m["case_name"],)).fetchone()[0]
    assert absorbed == m["input_sentences"] - m["leaders"]
    conn.close()


def test_by_kind_and_cases_kept_apart(casefile):
    assert cases.main(PCA_LEAF + ["--structure", "by-kind", "--k", "2"]) == 0
    first = "opening+hits.comment.m.m0.pca50.5-5-leaf.by-kind.p0.k2.s0"
    conn = db.connect(casefile)
    kinds = dict(conn.execute("SELECT kind, count(*) FROM cluster_case_cluster WHERE case_name = ? GROUP BY kind",
                              (first,)).fetchall())
    # two groups of each kind (the EVID strays too few and too scattered to cluster)
    assert kinds == {"LAW": 2, "EVID": 2, "GAP": 2}
    before = conn.execute("SELECT count(*) FROM cluster_case_member WHERE case_name = ?", (first,)).fetchone()[0]
    conn.close()
    # another case, then the first again: the first is replaced, the other stays
    assert cases.main(PCA_LEAF + ["--k", "2"]) == 0
    assert cases.main(PCA_LEAF + ["--structure", "by-kind", "--k", "2"]) == 0
    conn = db.connect(casefile)
    assert conn.execute("SELECT count(*) FROM cluster_case").fetchone()[0] == 2
    assert conn.execute("SELECT count(*) FROM cluster_case_member WHERE case_name = ?", (first,)).fetchone()[0] == before
    conn.close()


def test_noise_passes_and_umap(casefile):
    # eom on the six groups finds the two families first; a noise pass adds nothing it has not got
    assert cases.main(["run", "--reduction", "pca50", "--min-cluster-size", "5", "--min-samples", "5",
                       "--noise-passes", "3", "--sentences", "opening+hits"]) == 0
    assert cases.main(["run", "--min-cluster-size", "10", "--min-samples", "5", "--sentences", "opening+hits"]) == 0
    conn = db.connect(casefile)
    p = _case(conn, "opening+hits.comment.m.m0.pca50.5-5-eom.all.p3.kauto.s0")
    assert p["clusters"] >= 2 and p["noise_passes"] == 3
    u = _case(conn, "opening+hits.comment.m.m0.umap5.10-5-eom.all.p0.kauto.s0")
    assert u["reduction"] == "umap5" and u["clusters"] >= 2 and u["leaders_clustered"] >= 150
    conn.close()


def test_list(casefile, capsys):
    assert cases.main(["list"]) == 0
    assert "no case yet" in capsys.readouterr().out
    assert cases.main(PCA_LEAF + ["--k", "2"]) == 0
    capsys.readouterr()
    assert cases.main(["list"]) == 0
    assert "6 clusters, 2 topics; 150 of 158 leaders clustered" in capsys.readouterr().out


def test_stops(casefile):
    with pytest.raises(SystemExit, match="run make embed VIEW=plain"):
        cases.main(PCA_LEAF + ["--view", "plain"])
    conn = db.connect(casefile)
    conn.execute("DELETE FROM sentence_embedding WHERE text_key = 'g0s00'")
    conn.commit()
    conn.close()
    with pytest.raises(SystemExit, match="1 of the case's 158 sentences have no vector"):
        cases.main(PCA_LEAF)
    with pytest.raises(SystemExit, match="cosine below 1"):
        cases.main(PCA_LEAF + ["--merge", "1.0"])


def test_two_models_are_two_cases(casefile):
    conn = db.connect(casefile)
    conn.execute("INSERT INTO sentence_embedding SELECT text_key, 'BAAI/bge-large-en-v1.5', instruction,"
                 " input_sha256, dimensions, vector, created_at FROM sentence_embedding WHERE model = 'm'")
    conn.commit()
    conn.close()
    with pytest.raises(SystemExit, match="by 2 models"):
        cases.main(PCA_LEAF)
    assert cases.main(PCA_LEAF + ["--model", "m"]) == 0
    assert cases.main(PCA_LEAF + ["--model", "BAAI/bge-large-en-v1.5"]) == 0
    conn = db.connect(casefile)
    names = sorted(r[0] for r in conn.execute("SELECT case_name FROM cluster_case"))
    assert names == ["opening+hits.comment.bge-large-en-v1-5.m0.pca50.5-5-leaf.all.p0.kauto.s0",
                     "opening+hits.comment.m.m0.pca50.5-5-leaf.all.p0.kauto.s0"]
    conn.close()


def test_compare_two_cases(casefile, capsys):
    from shared import case_compare
    assert cases.main(PCA_LEAF + ["--k", "2"]) == 0
    assert cases.main(PCA_LEAF + ["--structure", "by-kind", "--k", "2"]) == 0
    first = "opening+hits.comment.m.m0.pca50.5-5-leaf.all.p0.k2.s0"
    second = "opening+hits.comment.m.m0.pca50.5-5-leaf.by-kind.p0.k2.s0"
    conn = db.connect(casefile)
    same = case_compare.compare(case_compare.labels(conn, first), case_compare.labels(conn, first))
    assert (same["ari"], same["nmi"], same["clusters_80"], same["median_share"]) == (1.0, 1.0, 6, 1.0)
    m = case_compare.compare(case_compare.labels(conn, first), case_compare.labels(conn, second))
    # the six groups are found both ways: each cluster of the first is one cluster of the second
    assert m["shared_sentences"] == 158 and m["clustered_both"] == 150 and m["ari"] == 1.0
    assert [r["share"] for r in m["crossing"]] == [1.0] * 6
    with pytest.raises(SystemExit, match="no case 'nope'"):
        case_compare.labels(conn, "nope")
    conn.close()
    capsys.readouterr()
    assert cases.main(["compare", first, second]) == 0
    out = capsys.readouterr().out
    assert "on the sentences both cluster: adjusted Rand 1.0, NMI 1.0" in out
    assert "6 of 6; median share 1.0" in out


def test_choose_a_case_for_each_model(casefile, capsys):
    conn = db.connect(casefile)
    conn.execute("INSERT INTO sentence_embedding SELECT text_key, 'BAAI/bge-large-en-v1.5', instruction,"
                 " input_sha256, dimensions, vector, created_at FROM sentence_embedding WHERE model = 'm'")
    conn.commit()
    conn.close()
    assert cases.main(PCA_LEAF + ["--model", "m"]) == 0
    assert cases.main(PCA_LEAF + ["--model", "m", "--k", "2"]) == 0
    assert cases.main(PCA_LEAF + ["--model", "BAAI/bge-large-en-v1.5"]) == 0
    first = "opening+hits.comment.m.m0.pca50.5-5-leaf.all.p0.kauto.s0"
    again = "opening+hits.comment.m.m0.pca50.5-5-leaf.all.p0.k2.s0"
    bge = "opening+hits.comment.bge-large-en-v1-5.m0.pca50.5-5-leaf.all.p0.kauto.s0"
    assert cases.main(["choose", first]) == 0
    assert cases.main(["choose", bge, "--note", "fewest comments not covered"]) == 0
    # a new choice for a model replaces the old one
    assert cases.main(["choose", again]) == 0
    assert f"make choose: {again} is the choice for m" in capsys.readouterr().out
    conn = db.connect(casefile)
    rows = [tuple(r) for r in conn.execute("SELECT model, case_name, note FROM cluster_case_choice ORDER BY model")]
    assert rows == [("BAAI/bge-large-en-v1.5", bge, "fewest comments not covered"), ("m", again, None)]
    conn.close()
    with pytest.raises(SystemExit, match="no case 'nope'"):
        cases.main(["choose", "nope"])
