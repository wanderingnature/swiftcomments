"""The console's Topics page (new): the clustering cases of make clusters, in
four tabs. Guide shows docs/choosing-a-case.md (why the cases exist, what to
look for, the glossary). Step 1 shows the cases of one model on a chart; a click
on a point selects its case, and a button records it as the model's choice.
Read a case opens one case from its topics to a cluster's sentences. Step 2
sets two cases side by side, the two choices first.

Every figure is read from data/roadless.sqlite through view.query, cached until
the file changes. Nothing here runs a case: make clusters does. The two writes are
the choice of step 1 (cluster_case_choice, as make choose) and the decision of
step 2 (cluster_concern_map, as make concern-map).
"""
import contextlib
import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from console import queries as q
from console.results import CARDS, chart, metrics, not_run, pager, pct, snippet, texts
from console.view import file_signature, open_db, query, show, show_text
from scripts.clusters.embed import VIEWS, unpack
from shared import case_compare, db

GUIDE = Path(__file__).resolve().parents[1] / "docs" / "choosing-a-case.md"
SENTENCES = {"opening": "gate-opening sentences",
             "opening+hits": "gate-opening and whole-comment hit sentences",
             "all": "every sentence"}
KINDS = ("law", "evid", "gap", "alt")
CATCH_ALL = 1000
MODEL_COLOURS = ["#D55E00", "#0072B2", "#009E73", "#CC79A7"]   # Okabe-Ito: told apart, also by colour-blind readers
VIEW_SHAPES = ["square", "circle", "triangle-up"]
KIND_SCALE = alt.Scale(domain=["LAW", "EVID", "GAP", "ALT"], range=["#0072B2", "#E69F00", "#009E73", "#CC79A7"])


def short(c):
    """A case in a few words, for the axes of a chart."""
    sel = {"opening": "opening", "opening+hits": "opening+hits", "all": "all"}[c["sentences"]]
    parts = [model_name(c["model"]).split("-")[0], c["view"], sel,
             ("UMAP" if c["reduction"] == "umap5" else "PCA") + f" {int(c['mcs'])}/{int(c['ms'])}"]
    if c["structure"] == "by-kind":
        parts.append("by kind")
    if c["passes"]:
        parts.append(f"{int(c['passes'])} passes")
    if c["k"] == c["k"] and c["k"] is not None:
        parts.append(f"K={int(c['k'])}")
    return " · ".join(parts)


@st.cache_data(show_spinner="comparing every pair of cases", max_entries=20)
def agreement_matrix(names, signature):
    """The adjusted Rand index of every pair of cases, on the sentences both cluster."""
    with open_db() as conn:
        labels = {n: case_compare.labels(conn, n) for n in names}
    rows = []
    for a in names:
        for b in names:
            m = case_compare.compare(labels[a], labels[b]) if a != b else {"ari": 1.0}
            rows.append((a, b, m["ari"]))
    return rows


@st.cache_data(show_spinner="placing the clusters", max_entries=20)
def cluster_map(case_name, model, view, signature):
    """Each cluster's centroid placed in two dimensions (the first two principal components
    of the centroids), with its topic, size and terms."""
    with open_db() as conn:
        members = conn.execute(
            "SELECT m.leader_key, m.cluster FROM cluster_case_member m WHERE m.case_name = ? AND m.cluster > 0",
            (case_name,)).fetchall()
        keys = sorted({k for k, _ in members})
        vec = {}
        for i in range(0, len(keys), 900):
            part = keys[i:i + 900]
            marks = ",".join("?" * len(part))
            vec.update(dict(conn.execute(
                f"SELECT text_key, vector FROM sentence_embedding WHERE model = ? AND instruction = ?"
                f" AND text_key IN ({marks})", (model, VIEWS[view], *part))))
        info = conn.execute("SELECT cluster, topic, leaders, terms FROM cluster_case_cluster WHERE case_name = ?",
                            (case_name,)).fetchall()
    by = {}
    for k, c in members:
        if k in vec:
            v = unpack(vec[k]).astype(np.float64)
            by.setdefault(c, []).append(v / np.linalg.norm(v))
    clusters = sorted(by)
    if len(clusters) < 3:
        return pd.DataFrame()
    C = np.array([np.mean(by[c], axis=0) for c in clusters])
    C = C / np.linalg.norm(C, axis=1, keepdims=True)
    C = C - C.mean(0)
    u, sv, vt = np.linalg.svd(C, full_matrices=False)
    xy = u[:, :2] * sv[:2]
    meta = {c: (t, n, ", ".join(json.loads(terms)[:4])) for c, t, n, terms in info}
    return pd.DataFrame({"cluster": clusters, "x": xy[:, 0], "y": xy[:, 1],
                         "topic": [f"Topic {meta[c][0]}" for c in clusters],
                         "sentences": [meta[c][1] for c in clusters],
                         "terms": [meta[c][2] for c in clusters]})


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


def count(n, one, many=None):
    return f"{n:,} {one if n == 1 else many or one + 's'}"


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
    cases = cases.assign(description=[describe(c) for _, c in cases.iterrows()],
                         model_label=lambda d: [model_name(m) for m in d["model"]])
    choices = query(q.CHOICES)
    guide, step1, read, step2 = st.tabs(["Guide", "Step 1: The best case of each model", "Read a case",
                                         "Step 2: Compare the two choices"])
    with guide:
        st.markdown(GUIDE.read_text(encoding="utf-8"))
    with step1:
        tab_step1(srun.iloc[0], cases, choices)
    with read:
        tab_read(cases)
    with step2:
        tab_compare(cases, choices)


def tab_step1(s, all_cases, choices):
    metrics([("Gate-open comments", int(s["gate_comments"]), f"Screen classes {s['classes']}."),
             ("Distinct sentences", int(s["distinct_sentences"]), "The sentences of the gate-open comments."),
             ("Cases", len(all_cases), "One case is one run of make clusters.")])
    st.caption("Select a model. Read its cases with the checks of the Guide, and choose its best case. Then do the"
               " same for the other model.")
    models = sorted(all_cases["model_label"].unique())
    label = st.radio("Model", models, horizontal=True, key="step1_model")
    cases = all_cases[all_cases["model_label"] == label].reset_index(drop=True)
    chosen = {r.model: r for r in choices.itertuples()}
    mine = next((chosen[m] for m in cases["model"].unique() if m in chosen), None)
    number = {n: i + 1 for i, n in enumerate(cases["case_name"])}
    if mine is not None:
        st.success(f"The choice for {label} is case {number[mine.case_name]}:"
                   f" {describe(cases[cases['case_name'] == mine.case_name].iloc[0])}"
                   + (f". Note: {mine.note}" if mine.note else ""))
    else:
        st.info(f"No case is chosen for {label} yet.")
    if all_cases["model"].nunique() >= 2 and all(m in chosen for m in all_cases["model"].unique()):
        st.markdown("Each model has a choice. Open the tab **Step 2: Compare the two choices** to decide between"
                    " them.")
    picked = st.session_state.get("step1_case")
    if picked not in number:
        picked = mine.case_name if mine is not None else None

    st.subheader("Coverage against clustering")
    st.caption("Each point is a case, with its number from the table below. The colour is the model and the shape"
               " is the view. A good case is low and to the right: many sentences in a cluster and few comments"
               f" not covered. A red ring marks a case whose largest cluster has {CATCH_ALL:,} or more sentences."
               " A black ring marks the choice. Click a point to select its case.")
    pts = pd.DataFrame({
        "case_name": cases["case_name"],
        "number": [number[n] for n in cases["case_name"]],
        "case": cases["description"],
        "model": [model_name(m) for m in cases["model"]],
        "view": cases["view"],
        "sentences clustered (%)": (100 * cases["leaders_clustered"] / cases["leaders"]).round(1),
        "comments not covered": cases["comments_unclustered"],
        "largest cluster": cases["largest_cluster"],
        "clusters": cases["clusters"],
    })
    models = sorted(pts["model"].unique())
    views = [v for v in ("plain", "comment", "topic") if v in set(pts["view"])]
    x = alt.X("sentences clustered (%):Q", scale=alt.Scale(zero=False))
    y = alt.Y("comments not covered:Q")
    tip = ["number:Q", "case:N", "clusters:Q", "sentences clustered (%):Q", "comments not covered:Q",
           "largest cluster:Q"]
    select = alt.selection_point(name="case", fields=["case_name"], on="click")
    dots = alt.Chart(pts).mark_point(filled=True, size=160).encode(
        x=x, y=y,
        color=alt.Color("model:N", scale=alt.Scale(domain=models, range=MODEL_COLOURS[:len(models)]),
                        legend=alt.Legend(title="model (colour)", symbolType="diamond", symbolSize=200)),
        shape=alt.Shape("view:N", scale=alt.Scale(domain=views, range=VIEW_SHAPES[:len(views)]),
                        legend=alt.Legend(title="view (shape)")),
        opacity=alt.condition(select, alt.value(0.9), alt.value(0.25)),
        tooltip=tip).add_params(select)
    numbers = alt.Chart(pts).mark_text(align="left", dx=17, dy=-15, fontSize=12, fontWeight="bold").encode(x=x, y=y, text="number:Q")
    big = pts[pts["largest cluster"] >= CATCH_ALL]
    rings = alt.Chart(big).mark_point(shape="circle", size=520, filled=False, color="#d62728",
                                      strokeWidth=2).encode(x=x, y=y, tooltip=tip)
    mark = pts[pts["case_name"] == mine.case_name] if mine is not None else pts.iloc[:0]
    ring = alt.Chart(mark).mark_point(shape="circle", size=900, filled=False, color="black",
                                      strokeWidth=3).encode(x=x, y=y, tooltip=tip)
    st.altair_chart(alt.layer(dots, numbers, rings, ring).resolve_legend(color="independent", shape="independent")
                    .properties(height=420), width="stretch", key="step1_chart", on_select=_selected,
                    selection_mode="case")

    st.subheader("The selected case")
    if picked is None:
        st.caption("Click a point on the chart to select a case.")
    else:
        c = cases[cases["case_name"] == picked].iloc[0]
        st.markdown(f"**Case {number[picked]}**: {c['description']}")
        st.caption(f"{c['clusters']:,} clusters in {c['topics']:,} topics."
                   f" {pct(c['leaders_clustered'], c['leaders'])} of {c['leaders']:,} sentences are in a cluster."
                   f" {c['comments_unclustered']:,} of {c['gate_comments']:,} gate-open comments are not covered."
                   f" The largest cluster has {c['largest_cluster']:,} sentences. Read it in the Read a case tab.")
        if mine is not None and mine.case_name == picked:
            st.success(f"This case is the choice for {label}.")
        else:
            note = st.text_input("Note: why this case", key="step1_note")
            if st.button(f"Choose case {number[picked]} for {label}", key="step1_choose"):
                record_choice(picked, note.strip() or None)
                st.rerun()

    st.caption("One row for each case of this model, newest last. A lower \"comments not covered\" is better. A"
               " very large \"largest cluster\" can be a catch-all cluster. The Guide tab explains each column.")
    show(pd.DataFrame({
        "case": [number[n] for n in cases["case_name"]],
        "chosen": ["yes" if mine is not None and n == mine.case_name else "" for n in cases["case_name"]],
        "description": cases["description"],
        "clusters": cases["clusters"],
        "topics": cases["topics"],
        "sentences clustered": [pct(a, b) for a, b in zip(cases["leaders_clustered"], cases["leaders"])],
        "comments not covered": [f"{a:,} of {b:,}" for a, b in zip(cases["comments_unclustered"],
                                                                     cases["gate_comments"])],
        "largest cluster": cases["largest_cluster"],
    }))

    st.subheader("How stable the cases of this model are")
    st.caption("The adjusted Rand index of each pair of this model's cases, on the sentences both cluster. Dark"
               " cells are cases that find the same groups. A case that agrees with its neighbours is stable: a"
               " small change of setting does not change its clusters much.")
    if st.toggle("Compare every pair of this model's cases", key="agreement_on"):
        names = list(cases["case_name"])
        tag = {n: f"{number[n]}. {short(c)}" for n, (_, c) in zip(names, cases.iterrows())}
        m = pd.DataFrame(agreement_matrix(tuple(names), file_signature()), columns=["a", "b", "ARI"])
        m["first"] = m["a"].map(tag)
        m["second"] = m["b"].map(tag)
        order = [tag[n] for n in names]
        chart(alt.Chart(m).mark_rect().encode(
            x=alt.X("second:N", sort=order, title=None,
                    axis=alt.Axis(labelAngle=-45, labelLimit=260, labelOverlap=False, labelAlign="right")),
            y=alt.Y("first:N", sort=order, title=None, axis=alt.Axis(labelLimit=260, labelOverlap=False)),
            color=alt.Color("ARI:Q", scale=alt.Scale(domain=[0, 1], scheme="greens"), title="adjusted Rand"),
            tooltip=["first:N", "second:N", alt.Tooltip("ARI:Q", format=".3f")]).properties(height=alt.Step(22)))

    with st.expander("Every value of every case of this model"):
        show(cases.drop(columns=["description", "model_label"]))


def _selected():
    """The chart's click: the clicked case becomes the selected case."""
    points = st.session_state["step1_chart"]["selection"]["case"]
    if points:
        st.session_state["step1_case"] = points[0]["case_name"]


def record_choice(case_name, note):
    """A write of the console: the selected case recorded as its model's choice (make choose)."""
    from scripts.clusters import cases as case_runs
    with contextlib.closing(db.connect(db.DB_PATH)) as conn:
        case_runs.choose(conn, case_name, note)


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
    every = query("SELECT cluster, topic, leaders, law, evid, gap, alt, terms FROM cluster_case_cluster"
                  " WHERE case_name = ?", (name,))
    every["main kind"] = [KINDS[i].upper() for i in every[list(KINDS)].to_numpy().argmax(1)]
    left, right = st.columns(2)
    with left:
        st.markdown("**The topics, by gate kind**")
        st.caption("Each bar is a topic. The colours show how its claims are argued: by law, evidence, a missing"
                   " analysis or an alternative. A mix is normal: one claim is often argued in more than one way.")
        chart(alt.Chart(every).mark_bar().encode(
            x=alt.X("sum(leaders):Q", title="sentences"),
            y=alt.Y("topic:O", title="topic", sort="ascending"),
            color=alt.Color("main kind:N", scale=KIND_SCALE, title="main kind"),
            tooltip=["topic:O", "main kind:N", alt.Tooltip("sum(leaders):Q", title="sentences")])
              .properties(height=alt.Step(18)))
    with right:
        st.markdown("**The cluster sizes**")
        st.caption("Most clusters should be small. A bar far to the right is a catch-all cluster.")
        chart(alt.Chart(every).mark_bar(color="#0072B2").encode(
            x=alt.X("leaders:Q", bin=alt.Bin(maxbins=40), title="sentences in the cluster"),
            y=alt.Y("count():Q", title="clusters"),
            tooltip=[alt.Tooltip("count():Q", title="clusters")]).properties(height=260))
        gaps = pd.DataFrame(json.loads(c["eigengaps"]), columns=["topics", "gap"])
        if not gaps.empty:
            st.markdown("**The topic cut**")
            st.caption("The gap at each number of topics. The cut is at the tallest bar unless K is set.")
            gaps["cut"] = gaps["topics"] == int(c["topics"])
            chart(alt.Chart(gaps).mark_bar().encode(
                x=alt.X("topics:O", title="number of topics"), y=alt.Y("gap:Q", title="eigengap"),
                color=alt.condition("datum.cut", alt.value("#D55E00"), alt.value("#BBBBBB")),
                tooltip=["topics:O", alt.Tooltip("gap:Q", format=".4f")]).properties(height=180))

    st.subheader("The map of the clusters")
    st.caption("Each point is a cluster, placed by its centre. Clusters near each other say similar things. The"
               " colour is the topic, the size is the number of sentences. Points of one colour should lie together.")
    cmap = cluster_map(name, c["model"], c["view"], file_signature())
    if cmap.empty:
        st.caption("Too few clusters to place.")
    else:
        chart(alt.Chart(cmap).mark_circle(opacity=0.75).encode(
            x=alt.X("x:Q", title=None, axis=None), y=alt.Y("y:Q", title=None, axis=None),
            color=alt.Color("topic:N", title="topic", sort=sorted(cmap["topic"].unique(),
                                                                   key=lambda t: int(t.split()[1]))),
            size=alt.Size("sentences:Q", scale=alt.Scale(range=[20, 700])),
            tooltip=["cluster:Q", "topic:N", "sentences:Q", "terms:N"]).properties(height=460))

    st.subheader("Topics")
    st.caption("Open a topic to see its clusters. Each cluster shows its most central sentence in full. Select"
               " the cluster under \"Open a cluster\" to read all its sentences and comments.")
    for r in topics.itertuples():
        with st.expander(f"Topic {r.topic}: {terms(r.terms, 5) or '(no term)'} ·"
                         f" {r.clusters} clusters · {r.occurrences:,} sentences"):
            clusters = query(q.CASE_CLUSTERS, (name, int(r.topic)))
            for cl in clusters.itertuples():
                kind = KINDS[int(np.argmax([cl.law, cl.evid, cl.gap, cl.alt]))].upper()
                central = json.loads(cl.central)
                with st.container(border=True):
                    st.markdown(f"**Cluster {cl.cluster}** · {cl.leaders:,} sentences · {kind} ·"
                                f" {terms(cl.terms, 4)}")
                    show_text(central[0] if central else "")

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


def tab_compare(cases, choices):
    st.markdown("**What to do in this step**")
    st.markdown("1. Read the three figures and the two charts below. They show how far the two choices agree.\n"
                "2. Read the table. The clusters that break the most are at the top.\n"
                "3. Open those clusters in the **Read a case** tab, in both cases.\n"
                "4. Decide which case groups the sentences by claim better.\n"
                "5. Under **The decision** at the bottom of this tab, type a note and click the button of that"
                " case.")
    compare_two(cases, choices)
    decision(cases, choices)


def decision(cases, choices):
    """Step 2's result: one of the two choices recorded as the concern map."""
    st.subheader("The decision")
    names = list(cases["case_name"])
    current = query(q.CONCERN_MAP)
    decided = current.iloc[0]["case_name"] if not current.empty else None
    if decided in names:
        r = current.iloc[0]
        st.success(f"The concern map is the {model_label_of(cases, decided)} case:"
                   f" {cases[cases['case_name'] == decided].iloc[0]['description']}"
                   + (f". Note: {r['note']}" if r["note"] else ""))
    else:
        st.info("No case is the concern map yet.")
    picked = [r for r in choices.itertuples() if r.case_name in names]
    if len(picked) < 2:
        st.caption("The decision needs a choice for each model. Choose them in step 1.")
        return
    note = st.text_input("Note: why this case", key="step2_note")
    for col, r in zip(st.columns(len(picked)), picked):
        c = cases[cases["case_name"] == r.case_name].iloc[0]
        with col, st.container(border=True):
            st.markdown(f"**The {model_name(r.model)} choice**")
            st.caption(f"{c['description']}. {c['clusters']:,} clusters in {c['topics']:,} topics. The largest"
                       f" cluster has {c['largest_cluster']:,} sentences. {c['comments_unclustered']:,} of"
                       f" {c['gate_comments']:,} gate-open comments are not covered.")
            if r.case_name == decided:
                st.markdown("This case is the concern map.")
            elif st.button(f"Use the {model_name(r.model)} case as the concern map", key=f"step2_use_{r.model}"):
                record_concern_map(r.case_name, note.strip() or None)
                st.rerun()
    st.caption("The concern map is the clustering that the next step reads: step 15 writes one concern statement"
               " for each cluster. Step 15 is not built yet. In a terminal, make concern-map CASE=<case name>"
               " records the same decision.")


def model_label_of(cases, case_name):
    return cases[cases["case_name"] == case_name].iloc[0]["model_label"]


def record_concern_map(case_name, note):
    """A write of the console: the decided case recorded as the concern map (make concern-map)."""
    from scripts.clusters import cases as case_runs
    with contextlib.closing(db.connect(db.DB_PATH)) as conn:
        case_runs.concern_map(conn, case_name, note)


def compare_two(cases, choices):
    if len(cases) < 2:
        st.caption("Run a second case to compare two cases.")
        return
    names = list(cases["case_name"])
    picked = [r.case_name for r in choices.itertuples() if r.case_name in names]
    if len(picked) >= 2:
        st.caption("The two cases below are the choices of step 1, one for each model. Compare them and decide"
                   " which model groups the sentences by claim better. You can select other cases.")
        i, j = names.index(picked[0]), names.index(picked[1])
    else:
        st.warning("Step 1 has not chosen a case for each model yet. Select two cases here, or choose a case for"
                   " each model in step 1.")
        i, j = 0, len(names) - 1
    first = pick_case(cases, "compare_first", "First case", index=i)
    second = pick_case(cases, "compare_second", "Second case", index=j)
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
    left, right = st.columns(2)
    with left:
        st.markdown("**How the clusters of the first case hold together**")
        st.caption("Each bar counts the clusters of the first case by the share that stays in one cluster of the"
                   " second. Bars to the right of the line stay together.")
        dist = pd.DataFrame({"share": crossing["share"] * 100})
        chart(alt.layer(
            alt.Chart(dist).mark_bar(color="#0072B2").encode(
                x=alt.X("share:Q", bin=alt.Bin(step=5), title="share in one cluster of the second case (%)"),
                y=alt.Y("count():Q", title="clusters of the first case")),
            alt.Chart(pd.DataFrame({"x": [80]})).mark_rule(color="#D55E00", strokeDash=[4, 3]).encode(x="x:Q"))
              .properties(height=260))
    with right:
        st.markdown("**Where the largest clusters go**")
        st.caption("The 20 largest clusters of the first case, and the clusters of the second case that hold their"
                   " sentences. One dark cell in a row is a cluster that stays together.")
        with open_db() as conn:
            a = case_compare.labels(conn, first["case_name"])
            b = case_compare.labels(conn, second["case_name"])
        top = list(crossing.sort_values("sentences", ascending=False)["cluster"][:20])
        cells = {}
        for k, ca in a.items():
            if ca in top and b.get(k, 0) > 0:
                cells[(ca, b[k])] = cells.get((ca, b[k]), 0) + 1
        size = dict(zip(crossing["cluster"], crossing["sentences"]))
        heat = pd.DataFrame([(f"{ca}", f"{cb}", n / size[ca]) for (ca, cb), n in cells.items()],
                            columns=["first", "second", "share"])
        if not heat.empty:
            heat = heat[heat["share"] >= 0.05]
            chart(alt.Chart(heat).mark_rect().encode(
                x=alt.X("second:N", title="cluster of the second case", sort=None),
                y=alt.Y("first:N", title="cluster of the first case", sort=[str(t) for t in top]),
                color=alt.Color("share:Q", scale=alt.Scale(domain=[0, 1], scheme="greens"), title="share"),
                tooltip=["first:N", "second:N", alt.Tooltip("share:Q", format=".0%")]).properties(height=alt.Step(16)))
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
    st.caption("Each card is one sentence, with the near-copies joined to it. Turn on \"Read the comments\" to"
               " see the comments that hold the sentence. Open a comment to read its full text.")
    off = pager(total, key)
    rows = query(q.CLUSTER_SENTENCES, (name, name, cluster, CARDS, off))
    for r in rows.itertuples():
        with st.container(border=True):
            show_text(r.text)
            st.caption(f"Written {count(r.occurrences, 'time')} in {count(r.comments, 'comment')}."
                       f" {count(r.variants, 'near-copy', 'near-copies')} joined.")
            if st.toggle("Read the comments", key=f"{key}_{r.leader_key}"):
                leader_comments(name, r.leader_key, f"{key}_{r.leader_key}_page")


def leader_comments(name, leader_key, key):
    """The comments that hold one sentence, a page at a time, each opening to its full text."""
    ids = list(query(q.LEADER_COMMENTS, (name, leader_key))["comment_id"])
    off = pager(len(ids), key)
    page = ids[off:off + CARDS]
    text_of = texts(page)
    for cid in page:
        with st.expander(f"{cid} · {snippet(text_of.get(cid))}"):
            show_text(text_of.get(cid))
