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

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_REPO / "scripts"))

from shared import db, embeddings  # noqa: E402
from clusters import analysis, cases  # noqa: E402
from clusters.embed import VIEWS, pack  # noqa: E402

# Two families, three groups each; the family word is in every sentence of it.
GROUPS = [("wildfire", "ignition", "EVID"), ("wildfire", "smoke", "EVID"), ("wildfire", "fuel", "LAW"),
          ("water", "sediment", "GAP"), ("water", "trout", "GAP"), ("water", "intake", "LAW")]
PER_GROUP = 25
STRAYS = 8


def _vectors():
    rng = np.random.default_rng(7)
    fams = analysis.unit(rng.normal(size=(2, embeddings.DIMENSIONS)))
    out = []
    for g, (fam, _, _) in enumerate(GROUPS):
        f = fams[0 if fam == "wildfire" else 1]
        centre = analysis.unit((f + 0.45 * analysis.unit(rng.normal(size=(1, embeddings.DIMENSIONS)))[0])[None])[0]
        out.append(analysis.unit(centre + 0.012 * rng.normal(size=(PER_GROUP, embeddings.DIMENSIONS))))
    strays = analysis.unit(rng.normal(size=(STRAYS, embeddings.DIMENSIONS)))
    return out, strays


@pytest.fixture
def casefile(tmp_path, monkeypatch):
    path = tmp_path / "roadless.sqlite"
    conn = db.connect(path, create=True)
    conn.executescript(db.SCHEMA_PATH.read_text(encoding="utf-8"))
    groups, strays = _vectors()
    sent, occ, emb = [], [], []
    unit_id = 1
    for g, (fam, word, kind) in enumerate(GROUPS):
        for i in range(PER_GROUP):
            key = f"g{g}s{i:02d}"
            text = f"The {fam} {word} concern number {i} about the {fam} {word} in the forest."
            flags = {k: int(k == kind) for k in ("LAW", "EVID", "GAP", "ALT")}
            # the last two of each group only hold a whole-comment hit; the rest open the gate
            opens, holds = (0, 1) if i >= PER_GROUP - 2 else (1, 0)
            sent.append((key, text, 1, 1, flags["LAW"], flags["EVID"], flags["GAP"], flags["ALT"], opens, holds))
            occ.append((unit_id, key, f"c{g}-{i:02d}", flags["LAW"], flags["EVID"], flags["GAP"], flags["ALT"],
                        opens, holds))
            unit_id += 1
            emb.append((key, groups[g][i]))
    for i in range(STRAYS):
        key = f"stray{i}"
        sent.append((key, f"An unrelated remark number {i} on nothing.", 1, 1, 0, 1, 0, 0, 1, 0))
        occ.append((unit_id, key, f"cs-{i}", 0, 1, 0, 0, 1, 0))
        unit_id += 1
        emb.append((key, strays[i]))
    conn.executemany("INSERT INTO gate_sentence VALUES (?,?,?,?,?,?,?,?,?,?)", sent)
    conn.executemany("INSERT INTO gate_sentence_occurrence VALUES (?,?,?,?,?,?,?,?,?)", occ)
    conn.execute("INSERT INTO gate_sentence_run (ruleset_version, classes, created_at, gate_comments, occurrences,"
                 " distinct_sentences, comments_opening, comments_hit, comments_neither, sentences_unlocated,"
                 " hits_unlocated) VALUES ('3', 'A,B1', '2026-10-20', ?, ?, ?, 0, 0, 0, 0, 0)",
                 (len(occ), len(occ), len(sent)))
    conn.executemany("INSERT INTO sentence_embedding VALUES (?, 'm', ?, 'x', 1024, ?, '2026-10-20')",
                     [(k, VIEWS["comment"], pack(v)) for k, v in emb])
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


PCA_LEAF = ["run", "--reduction", "pca50", "--min-cluster-size", "5", "--min-samples", "5",
            "--selection", "leaf", "--sentences", "opening+hits"]


def _case(conn, name):
    return conn.execute("SELECT * FROM cluster_case WHERE case_name = ?", (name,)).fetchone()


def test_six_groups_two_topics(casefile, capsys):
    assert cases.main(PCA_LEAF + ["--k", "2"]) == 0
    name = "opening+hits.comment.m0.pca50.5-5-leaf.all.p0.k2.s0"
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
    c = _case(conn, "opening+hits.comment.m0.pca50.5-5-leaf.all.p0.kauto.s0")
    gaps = json.loads(c["eigengaps"])
    assert c["topics"] == gaps[0][0] and len(gaps) >= 2
    conn.close()


def test_sentences_axis_and_merge(casefile):
    # the gate-opening sentences alone: two of each group are left out
    assert cases.main(PCA_LEAF[:-2] + ["--sentences", "opening"]) == 0
    # a merge at 0.8: the members of a group (cosine about 0.87 to each other) collapse into leaders
    assert cases.main(PCA_LEAF + ["--merge", "0.8"]) == 0
    conn = db.connect(casefile)
    c = _case(conn, "opening.comment.m0.pca50.5-5-leaf.all.p0.kauto.s0")
    assert c["input_sentences"] == 146
    m = _case(conn, "opening+hits.comment.m80.pca50.5-5-leaf.all.p0.kauto.s0")
    assert m["leaders"] < m["input_sentences"] == 158
    absorbed = conn.execute("SELECT count(*) FROM cluster_case_leader WHERE case_name = ? AND text_key <> leader_key",
                            (m["case_name"],)).fetchone()[0]
    assert absorbed == m["input_sentences"] - m["leaders"]
    conn.close()


def test_by_kind_and_cases_kept_apart(casefile):
    assert cases.main(PCA_LEAF + ["--structure", "by-kind", "--k", "2"]) == 0
    first = "opening+hits.comment.m0.pca50.5-5-leaf.by-kind.p0.k2.s0"
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
    p = _case(conn, "opening+hits.comment.m0.pca50.5-5-eom.all.p3.kauto.s0")
    assert p["clusters"] >= 2 and p["noise_passes"] == 3
    u = _case(conn, "opening+hits.comment.m0.umap5.10-5-eom.all.p0.kauto.s0")
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
