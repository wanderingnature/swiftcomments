"""The console's Topics page (new): the clustering cases of make clusters set
side by side, and one case opened up, from its topics to a cluster's sentences
and the comments they come from, and its noise.

Every figure is read from data/roadless.sqlite through view.query, cached until
the file changes. Nothing here runs a case: make clusters does.
"""
import json

import streamlit as st

from console import queries as q
from console.results import CARDS, metrics, not_run, pager, pct
from console.view import query, show

MEASURES = ["case_name", "clusters", "topics", "leaders", "leaders_clustered", "largest_cluster",
            "comments_unclustered", "gate_comments", "opening_occurrences_clustered", "opening_occurrences",
            "seconds"]


def terms(cell):
    return ", ".join(json.loads(cell))


def page_topics():
    st.header("Topics")
    st.caption("The sentences of the comments whose model-free gate is open, grouped by meaning into"
               " clusters and the clusters into topics, by code: each clustering case of make clusters,"
               " side by side, and one opened up.")
    srun = query(q.SENTENCE_RUN)
    if srun.empty:
        not_run("sentences")
        return
    s = srun.iloc[0]
    metrics([("Gate-open comments", int(s["gate_comments"]), f"classes {s['classes']}"),
             ("Sentences", int(s["occurrences"]), None),
             ("Distinct sentences", int(s["distinct_sentences"]), None),
             ("No sentence opens the gate alone", int(s["gate_comments"] - s["comments_opening"]),
              "Comments the whole-comment reading opened; their hit sentences are SENTENCES=opening+hits.")])
    cases = query(q.CASES)
    if cases.empty:
        not_run("clusters")
        return

    st.subheader("The cases")
    st.caption("One row per case, named from its values (sentences.view.model.merge.reduction.mcs-ms-selection"
               ".structure.passes.k.seed). Comments unclustered: gate-open comments with no sentence in a"
               " cluster. Opening clustered: of the sentences that open the gate alone, those in a cluster.")
    show(cases[MEASURES].assign(
        leaders_clustered=[f"{a:,} ({pct(a, b)})" for a, b in zip(cases["leaders_clustered"], cases["leaders"])],
        comments_unclustered=[f"{a:,} of {b:,}" for a, b in zip(cases["comments_unclustered"], cases["gate_comments"])],
        opening_occurrences_clustered=[f"{a:,} ({pct(a, b)})" for a, b in
                                       zip(cases["opening_occurrences_clustered"], cases["opening_occurrences"])],
    ).drop(columns=["gate_comments", "opening_occurrences"]))
    with st.expander("Every value of every case"):
        show(cases)

    names = list(cases["case_name"])
    name = st.selectbox("case", names, index=len(names) - 1, key="case_pick")
    c = cases[cases["case_name"] == name].iloc[0]
    gaps = json.loads(c["eigengaps"])
    st.caption(f"Read {c['sentences_read']:,} distinct sentences ({c['occurrences']:,} occurrences), view"
               f" {c['view']}, as {c['leaders']:,} leaders. Topic cut: "
               + (f"K={int(c['k'])}" if c["k"] == c["k"] and c["k"] is not None else "the largest eigengap")
               + ("; the candidates, largest gap first: " + ", ".join(f"{k} ({g:.3f})" for k, g in gaps[:6])
                  if gaps else ""))

    topics = query(q.CASE_TOPICS, (name,))
    if topics.empty:
        st.caption("This case found no cluster.")
        return
    st.subheader("Its topics")
    show(topics.assign(terms=topics["terms"].map(terms)))
    labels = [f"Topic {r.topic}: {terms(r.terms) or '(no term)'} ({r.clusters} clusters, {r.occurrences:,})"
              for r in topics.itertuples()]
    t = st.selectbox("topic", range(len(labels)), format_func=labels.__getitem__, key="case_topic")
    topic = int(topics.iloc[t]["topic"])

    clusters = query(q.CASE_CLUSTERS, (name, topic))
    st.subheader(f"The clusters of topic {topic}")
    st.caption("Tightness: the mean cosine of a cluster's leaders to its centroid. LAW to ALT: the share of its"
               " leaders of each gate kind. Central: its two sentences nearest the centroid.")
    show(clusters.assign(terms=clusters["terms"].map(terms),
                         central=clusters["central"].map(lambda x: " / ".join(json.loads(x)))))
    clabels = [f"Cluster {r.cluster}: {terms(r.terms) or '(no term)'} ({r.leaders} leaders)"
               for r in clusters.itertuples()]
    k = st.selectbox("cluster", range(len(clabels)), format_func=clabels.__getitem__, key="case_cluster")
    cluster = int(clusters.iloc[k]["cluster"])
    leader_rows(name, cluster, f"The sentences of cluster {cluster}", "case_cluster_page")
    comments = query(q.CLUSTER_COMMENTS, (name, cluster))
    with st.expander(f"The {len(comments):,} comments its sentences come from (open one on the Comment page)"):
        st.text(", ".join(comments["comment_id"]))

    st.subheader("The noise")
    leader_rows(name, 0, "The leaders in no cluster, most-occurring first", "case_noise_page")


def leader_rows(name, cluster, title, key):
    total = int(query(q.CLUSTER_SENTENCE_COUNT, (name, name, cluster)).iloc[0]["n"])
    st.markdown(f"**{title}** ({total:,})")
    if not total:
        return
    off = pager(total, key)
    show(query(q.CLUSTER_SENTENCES, (name, name, cluster, CARDS, off)))
