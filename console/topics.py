"""The console's Topics page (new): the clustering cases of make clusters, in
four tabs. Guide shows docs/choosing-a-case.md (why the cases exist, what to
look for, the glossary). Cases lists every case in words with its measures.
Read a case opens one case from its topics to a cluster's sentences. Compare
two cases sets two cases side by side.

Every figure is read from data/roadless.sqlite through view.query, cached until
the file changes. Nothing here runs a case: make clusters does.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from console import queries as q
from console.results import CARDS, metrics, not_run, pager, pct
from console.view import open_db, query, show
from shared import case_compare

GUIDE = Path(__file__).resolve().parents[1] / "docs" / "choosing-a-case.md"
SENTENCES = {"opening": "gate-opening sentences",
             "opening+hits": "gate-opening and whole-comment hit sentences",
             "all": "every sentence"}
KINDS = ("law", "evid", "gap", "alt")


def model_name(model):
    m = model.lower()
    if "qwen3-embedding" in m:
        return "Qwen3-Embedding-8B" + (" (Q4)" if "q4" in m else "")
    if "bge-large" in m:
        return "BGE-large-en-v1.5"
    return model


def method(c):
    parts = [("UMAP" if c["reduction"] == "umap5" else "PCA"),
             f"HDBSCAN {int(c['mcs'])}/{int(c['ms'])} {c['selection']}"]
    if c["merge"]:
        parts.append(f"merge {c['merge']}")
    if c["passes"]:
        parts.append(f"{int(c['passes'])} noise passes")
    if c["structure"] == "by-kind":
        parts.append("by gate kind")
    return ", ".join(parts)


def cut(c):
    return f"{int(c['k'])} topics" if c["k"] == c["k"] and c["k"] is not None else "topics at the eigengap"


def describe(c):
    """A case in words, for the tables and the pickers."""
    return (f"{model_name(c['model'])}, {c['view']} view · {SENTENCES[c['sentences']]} · {method(c)} · {cut(c)}")


def terms(cell, n=8):
    return ", ".join(json.loads(cell)[:n])


def page_topics():
    st.header("Topics")
    st.caption("The substantive sentences, grouped by claim into clusters and by subject into topics."
               " Start with the Guide tab.")
    srun = query(q.SENTENCE_RUN)
    if srun.empty:
        not_run("sentences")
        return
    cases = query(q.CASES)
    if cases.empty:
        not_run("clusters")
        return
    cases = cases.assign(description=[describe(c) for _, c in cases.iterrows()])
    guide, overview, read, compare = st.tabs(["Guide", "Cases", "Read a case", "Compare two cases"])
    with guide:
        st.markdown(GUIDE.read_text(encoding="utf-8"))
    with overview:
        tab_cases(srun.iloc[0], cases)
    with read:
        tab_read(cases)
    with compare:
        tab_compare(cases)


def tab_cases(s, cases):
    metrics([("Gate-open comments", int(s["gate_comments"]), f"Screen classes {s['classes']}."),
             ("Distinct sentences", int(s["distinct_sentences"]), "The sentences of the gate-open comments."),
             ("Cases", len(cases), "One case is one run of make clusters.")])
    st.caption("One row for each case, newest last. A lower \"comments not covered\" is better. A very large"
               " \"largest cluster\" can be a catch-all cluster. The Guide tab explains each column.")
    table = pd.DataFrame({
        "case": cases["description"],
        "clusters": cases["clusters"],
        "topics": cases["topics"],
        "sentences clustered": [pct(a, b) for a, b in zip(cases["leaders_clustered"], cases["leaders"])],
        "comments not covered": [f"{a:,} of {b:,}" for a, b in zip(cases["comments_unclustered"],
                                                                     cases["gate_comments"])],
        "largest cluster": cases["largest_cluster"],
    })
    show(table)
    with st.expander("Every value of every case"):
        show(cases.drop(columns=["description"]))


def pick_case(cases, key, label="Case", index=None):
    """A case picked by its description; returns its row."""
    opts = list(range(len(cases)))
    i = st.selectbox(label, opts, index=len(opts) - 1 if index is None else index,
                     format_func=lambda j: cases.iloc[j]["description"], key=key)
    return cases.iloc[i]


def tab_read(cases):
    c = pick_case(cases, "read_case")
    name = c["case_name"]
    st.caption(f"{c['clusters']:,} clusters in {c['topics']:,} topics. {pct(c['leaders_clustered'], c['leaders'])}"
               f" of {c['leaders']:,} sentences are in a cluster. {c['comments_unclustered']:,} of"
               f" {c['gate_comments']:,} gate-open comments have no sentence in a cluster.")
    topics = query(q.CASE_TOPICS, (name,))
    if topics.empty:
        st.caption("This case found no cluster.")
        return
    st.subheader("Topics")
    st.caption("Open a topic to see its clusters. Each cluster shows one example sentence.")
    for r in topics.itertuples():
        with st.expander(f"Topic {r.topic}: {terms(r.terms, 5) or '(no term)'} ·"
                         f" {r.clusters} clusters · {r.occurrences:,} sentences"):
            clusters = query(q.CASE_CLUSTERS, (name, int(r.topic)))
            show(pd.DataFrame({
                "cluster": clusters["cluster"],
                "sentences": clusters["leaders"],
                "main kind": [KINDS[i].upper() for i in clusters[list(KINDS)].to_numpy().argmax(1)],
                "terms": clusters["terms"].map(lambda x: terms(x, 4)),
                "example": clusters["central"].map(lambda x: json.loads(x)[0] if json.loads(x) else ""),
            }))

    st.subheader("Open a cluster")
    all_clusters = query("SELECT cluster, topic, leaders, terms FROM cluster_case_cluster WHERE case_name = ?"
                         " ORDER BY cluster", (name,))
    labels = [f"Cluster {r.cluster} (topic {r.topic}, {r.leaders} sentences): {terms(r.terms, 4)}"
              for r in all_clusters.itertuples()]
    k = st.selectbox("Cluster", range(len(labels)), format_func=labels.__getitem__, key="read_cluster")
    cluster = int(all_clusters.iloc[k]["cluster"])
    leader_rows(name, cluster, f"The sentences of cluster {cluster}", "read_cluster_page")
    comments = query(q.CLUSTER_COMMENTS, (name, cluster))
    with st.expander(f"The {len(comments):,} comments that hold these sentences"):
        st.caption("Copy an id into the Comment page to read the comment.")
        st.text(", ".join(comments["comment_id"]))
    with st.expander("Sentences in no cluster"):
        st.caption("If many of these repeat one claim, the case missed that claim.")
        leader_rows(name, 0, "Sentences in no cluster, most frequent first", "read_noise_page")


def tab_compare(cases):
    if len(cases) < 2:
        st.caption("Run a second case to compare two cases.")
        return
    st.caption("Select two cases that differ in one setting. The Guide tab explains the figures.")
    first = pick_case(cases, "compare_first", "First case", index=0)
    second = pick_case(cases, "compare_second", "Second case")
    if first["case_name"] == second["case_name"]:
        st.caption("Select two different cases.")
        return
    with open_db() as conn:
        m = case_compare.compare(case_compare.labels(conn, first["case_name"]),
                                 case_compare.labels(conn, second["case_name"]))
        names = {n: {c: terms(t, 4) for c, t in conn.execute(
            "SELECT cluster, terms FROM cluster_case_cluster WHERE case_name = ?", (n,))}
            for n in (first["case_name"], second["case_name"])}
    metrics([("Clustered by both", m["clustered_both"],
              f"First case {m['clustered_first']:,}, second case {m['clustered_second']:,}."),
             ("Adjusted Rand", m["ari"] if m["ari"] is not None else "-",
              "1 is the same grouping. 0 is the agreement that chance gives."),
             ("Clusters kept together", f"{m['clusters_80']} of {len(m['crossing'])}",
              "Clusters of the first case with 80% or more of their sentences in one cluster of the second.")])
    crossing = pd.DataFrame(m["crossing"])
    if crossing.empty:
        return
    st.caption("Each row is a cluster of the first case. \"Share\" is the part of its sentences in one cluster of"
               " the second case. The clusters that break the most are at the top.")
    show(pd.DataFrame({
        "cluster": crossing["cluster"],
        "terms": crossing["cluster"].map(names[first["case_name"]]),
        "sentences": crossing["sentences"],
        "goes mostly to": crossing["best_second"],
        "share": [f"{s:.0%}" for s in crossing["share"]],
        "its terms": crossing["best_second"].map(names[second["case_name"]]),
        "in no cluster there": crossing["noise_in_second"],
    }).iloc[crossing["share"].argsort(kind="stable")])


def leader_rows(name, cluster, title, key):
    total = int(query(q.CLUSTER_SENTENCE_COUNT, (name, name, cluster)).iloc[0]["n"])
    st.markdown(f"**{title}** ({total:,})")
    if not total:
        return
    off = pager(total, key)
    rows = query(q.CLUSTER_SENTENCES, (name, name, cluster, CARDS, off))
    show(rows.rename(columns={"text": "sentence", "variants": "near-copies joined",
                              "occurrences": "times written", "comments": "comments"}))
