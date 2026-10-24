"""The console's Topics page (new): the path from the sentences to the concern
map, in five stages (docs/choosing-a-case.md). The status lines at the top show
each stage done, next or waiting. Four tabs: Guide (docs/choosing-a-case.md);
Stage 4, the cases of one model on a chart, a click selecting a case and a
button recording it as the model's choice; Stage 5, the two choices compared and
a button for each recording it as the concern map; Read a case, one case from
its topics to a cluster's sentences and the comments that hold them.

Every figure is read from data/roadless.sqlite through view.query, cached until
the file changes. Nothing here runs a case: make clusters does. The two writes are
the choice of stage 4 (cluster_case_choice, as make choose) and the concern map of
stage 5 (cluster_concern_map, as make concern-map).
"""
import contextlib
import json
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from console import queries as q
from console.results import CARDS, chart, metrics, pager, pct, snippet, texts
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
    st.caption("Make the concern map in five stages. The lines below show the stages that are done and the stage"
               " that is next. The Guide tab tells you each step.")
    srun = query(q.SENTENCE_RUN)
    vectors = query(q.VECTORS)
    cases = query(q.CASES)
    cases = cases.assign(description=[describe(c) for _, c in cases.iterrows()],
                         model_label=[model_name(m) for m in cases["model"]])
    choices = query(q.CHOICES)
    current = query(q.CONCERN_MAP)
    status(srun, vectors, cases, choices, current)
    if cases.empty:
        guide, = st.tabs(["Guide"])
        with guide:
            st.markdown(GUIDE.read_text(encoding="utf-8"))
        return
    guide, stage4, stage5, read = st.tabs(["Guide", "Stage 4: Best case of each model", "Stage 5: Concern map",
                                           "Read a case"])
    with guide:
        st.markdown(GUIDE.read_text(encoding="utf-8"))
    with stage4:
        tab_stage4(cases, choices)
    with stage5:
        tab_stage5(cases, choices, current)
    with read:
        tab_read(cases)


def status(srun, vectors, cases, choices, current):
    """The five stages, each done, next or waiting, with its figure from the file."""
    sentences = int(srun.iloc[0]["distinct_sentences"]) if not srun.empty else 0
    complete = [m for m, n in zip(vectors["model"], vectors["n"]) if sentences and n == sentences]
    with_cases = sorted(cases["model"].unique()) if not cases.empty else []
    chosen = set(choices["model"])
    stages = [
        ("1. Sentences", not srun.empty,
         f"{sentences:,} sentences of {int(srun.iloc[0]['gate_comments']):,} gate-open comments."
         if not srun.empty else "", "make sentences"),
        ("2. Vectors", len(complete) >= 2,
         "; ".join(f"{model_name(m)} {n:,} of {sentences:,}" for m, n in zip(vectors["model"], vectors["n"]))
         or "No vectors.", "make embed VIEW=plain"),
        ("3. Cases", len(with_cases) >= 2,
         "; ".join(f"{model_name(m)} {int((cases['model'] == m).sum())} cases" for m in with_cases) or "No cases.",
         'make case-set MODEL="<model>"'),
        ("4. Best case of each model", len(with_cases) >= 2 and all(m in chosen for m in with_cases),
         "; ".join(f"{model_name(m)}: chosen" if m in chosen else f"{model_name(m)}: not chosen"
                   for m in with_cases), None),
        ("5. Concern map", not current.empty,
         f"The {model_name(cases[cases['case_name'] == current.iloc[0]['case_name']].iloc[0]['model'])} choice."
         if not current.empty and (cases["case_name"] == current.iloc[0]["case_name"]).any() else "Not decided.",
         None),
    ]
    nxt = next((i for i, s in enumerate(stages) if not s[1]), None)
    with st.container(border=True):
        for i, (name, done, figure, command) in enumerate(stages):
            state = "done" if done else ("**next**" if i == nxt else "waiting")
            st.markdown(f"**{name}**: {state}. {figure}".rstrip())
            if i == nxt and command:
                st.code(command, language="bash")
            elif i == nxt:
                st.markdown(f"Open the tab **Stage {name.split('.')[0]}** below.")


def tab_stage4(all_cases, choices):
    st.markdown("**What to do here**\n\n"
                "1. Select a model.\n"
                "2. Click a point on the chart. The case shows under the chart.\n"
                "3. Open the tab **Read a case** and do the four checks of the Guide.\n"
                "4. Click the point of the best case, type a note and click **Choose case N**.\n"
                "5. Do steps 1 to 4 for the other model.")
    models = sorted(all_cases["model_label"].unique())
    label = st.radio("Model", models, horizontal=True, key="step1_model")
    cases = all_cases[all_cases["model_label"] == label].reset_index(drop=True)
    chosen = {r.model: r for r in choices.itertuples()}
    mine = next((chosen[m] for m in cases["model"].unique() if m in chosen), None)
    number = {n: i + 1 for i, n in enumerate(cases["case_name"])}
    if mine is not None and mine.case_name in number:
        st.success(f"The choice for {label} is case {number[mine.case_name]}:"
                   f" {describe(cases[cases['case_name'] == mine.case_name].iloc[0])}"
                   + (f". Note: {mine.note}" if mine.note else ""))
    else:
        mine = None
        st.info(f"No case is chosen for {label}.")
    picked = st.session_state.get("step1_case")
    if picked not in number:
        picked = mine.case_name if mine is not None else None

    st.subheader("The cases of this model")
    st.caption("Each point is a case. The number is the case number in the table. A good case is low and to the"
               " right. Colour: the model. Shape: the view. Red ring: a cluster of 1,000 or more sentences. Black"
               " ring: the choice. Click a point to select the case.")
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
    numbers = alt.Chart(pts).mark_text(align="left", dx=17, dy=-15, fontSize=12, fontWeight="bold").encode(
        x=x, y=y, text="number:Q")
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
                   f" The largest cluster has {c['largest_cluster']:,} sentences. The tab Read a case shows this"
                   " case.")
        if mine is not None and mine.case_name == picked:
            st.success(f"This case is the choice for {label}.")
        else:
            note = st.text_input("Note: why this case", key="step1_note")
            if st.button(f"Choose case {number[picked]} for {label}", key="step1_choose"):
                record_choice(picked, note.strip() or None)
                st.rerun()

    st.caption("The cases of this model, oldest first. \"Comments not covered\": gate-open comments with no"
               " substantive sentence in a cluster.")
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

    if st.toggle("Show how alike the cases of this model are", key="agreement_on"):
        st.caption("Each cell is the adjusted Rand index of two cases. Dark: the two cases make the same clusters."
                   " Light: they make different clusters.")
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

    with st.expander("All the values of the cases of this model"):
        show(cases.drop(columns=["description", "model_label"]))
    st.markdown("**Next:** when each model has a choice, open the tab **Stage 5: Concern map**.")


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


def tab_read(cases):
    names = list(cases["case_name"])
    selected = st.session_state.get("step1_case")
    if selected in names and st.session_state.get("read_follows") != selected:
        st.session_state["read_case"] = names.index(selected)
        st.session_state["read_follows"] = selected
    i = st.selectbox("Case", range(len(cases)), index=len(cases) - 1,
                     format_func=lambda j: cases.iloc[j]["description"], key="read_case")
    c = cases.iloc[i]
    name = c["case_name"]
    st.caption(f"{c['clusters']:,} clusters in {c['topics']:,} topics. {pct(c['leaders_clustered'], c['leaders'])}"
               f" of {c['leaders']:,} sentences are in a cluster. {c['comments_unclustered']:,} of"
               f" {c['gate_comments']:,} gate-open comments are not covered.")
    topics = query(q.CASE_TOPICS, (name,))
    if topics.empty:
        st.caption("This case has no cluster.")
        return
    every = query("SELECT cluster, topic, leaders, law, evid, gap, alt, terms FROM cluster_case_cluster"
                  " WHERE case_name = ?", (name,))
    every["main kind"] = [KINDS[i].upper() for i in every[list(KINDS)].to_numpy().argmax(1)]
    left, right = st.columns(2)
    with left:
        st.markdown("**The topics, by gate kind**")
        st.caption("One bar for each topic. The colours show how its sentences argue: by law, evidence, a missing"
                   " analysis or an alternative.")
        chart(alt.Chart(every).mark_bar().encode(
            x=alt.X("sum(leaders):Q", title="sentences"),
            y=alt.Y("topic:O", title="topic", sort="ascending"),
            color=alt.Color("main kind:N", scale=KIND_SCALE, title="main kind"),
            tooltip=["topic:O", "main kind:N", alt.Tooltip("sum(leaders):Q", title="sentences")])
              .properties(height=alt.Step(18)))
    with right:
        st.markdown("**The cluster sizes**")
        st.caption("The number of clusters of each size. A bar far to the right is a catch-all cluster.")
        chart(alt.Chart(every).mark_bar(color="#0072B2").encode(
            x=alt.X("leaders:Q", bin=alt.Bin(maxbins=40), title="sentences in the cluster"),
            y=alt.Y("count():Q", title="clusters"),
            tooltip=[alt.Tooltip("count():Q", title="clusters")]).properties(height=260))
        gaps = pd.DataFrame(json.loads(c["eigengaps"]), columns=["topics", "gap"])
        if not gaps.empty:
            st.markdown("**The topic cut**")
            st.caption("The score for each number of topics. The orange bar is the number that the case uses.")
            gaps["cut"] = gaps["topics"] == int(c["topics"])
            chart(alt.Chart(gaps).mark_bar().encode(
                x=alt.X("topics:O", title="number of topics"), y=alt.Y("gap:Q", title="eigengap"),
                color=alt.condition("datum.cut", alt.value("#D55E00"), alt.value("#BBBBBB")),
                tooltip=["topics:O", alt.Tooltip("gap:Q", format=".4f")]).properties(height=180))

    st.subheader("The map of the clusters")
    st.caption("One point for each cluster. Clusters near each other say similar things. Colour: the topic. Size:"
               " the number of sentences.")
    cmap = cluster_map(name, c["model"], c["view"], file_signature())
    if cmap.empty:
        st.caption("The case has fewer than three clusters.")
    else:
        chart(alt.Chart(cmap).mark_circle(opacity=0.75).encode(
            x=alt.X("x:Q", title=None, axis=None), y=alt.Y("y:Q", title=None, axis=None),
            color=alt.Color("topic:N", title="topic", sort=sorted(cmap["topic"].unique(),
                                                                   key=lambda t: int(t.split()[1]))),
            size=alt.Size("sentences:Q", scale=alt.Scale(range=[20, 700])),
            tooltip=["cluster:Q", "topic:N", "sentences:Q", "terms:N"]).properties(height=460))

    st.subheader("Topics")
    st.caption("Open a topic to see its clusters. Each cluster shows its most typical sentence.")
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
    with st.expander(f"The ids of the {len(comments):,} comments that hold these sentences"):
        st.caption("Paste an id into the Comment page to read the comment with its readings.")
        st.text(", ".join(comments["comment_id"]))
    with st.expander("Sentences in no cluster"):
        st.caption("The sentences that the case left out. If many of them make one claim, the case missed that"
                   " claim.")
        leader_rows(name, 0, "Sentences in no cluster, most frequent first", "read_noise_page")


def tab_stage5(cases, choices, current):
    names = list(cases["case_name"])
    picked = [r for r in choices.itertuples() if r.case_name in names]
    if len(picked) < 2:
        st.info("Stage 4 is not done. Choose a case for each model in the tab Stage 4 first.")
        return
    st.markdown("**What to do here**\n\n"
                "1. Read the three numbers.\n"
                "2. Read the table. The second choice splits the clusters at the top most.\n"
                "3. Open two or three of these clusters in the tab **Read a case**, in both choices.\n"
                "4. Decide which choice keeps one claim in each cluster.\n"
                "5. Type a note and click **Use this case as the concern map** under that choice.")
    first = cases[cases["case_name"] == picked[0].case_name].iloc[0]
    second = cases[cases["case_name"] == picked[1].case_name].iloc[0]
    st.markdown(f"**First choice**: {first['description']}  \n**Second choice**: {second['description']}")
    with open_db() as conn:
        a = case_compare.labels(conn, first["case_name"])
        b = case_compare.labels(conn, second["case_name"])
        names_of = {n: {c: terms(t, 4) for c, t in conn.execute(
            "SELECT cluster, terms FROM cluster_case_cluster WHERE case_name = ?", (n,))}
            for n in (first["case_name"], second["case_name"])}
    m = case_compare.compare(a, b)
    metrics([("Clustered by both", m["clustered_both"],
              f"The first choice clusters {m['clustered_first']:,} sentences, the second {m['clustered_second']:,}."),
             ("Adjusted Rand", m["ari"] if m["ari"] is not None else "-",
              "How alike the two choices cluster the same sentences. 1: the same clusters. Near 0: different"
              " clusters."),
             ("Clusters kept together", f"{m['clusters_80']} of {len(m['crossing'])}",
              "Clusters of the first choice with 80% or more of their sentences in one cluster of the second.")])
    crossing = pd.DataFrame(m["crossing"])
    if not crossing.empty:
        left, right = st.columns(2)
        with left:
            st.markdown("**How much of each cluster stays together**")
            st.caption("The clusters of the first choice, by the part of their sentences in one cluster of the"
                       " second choice. Bars right of the line: the cluster stays together.")
            dist = pd.DataFrame({"share": crossing["share"] * 100})
            chart(alt.layer(
                alt.Chart(dist).mark_bar(color="#0072B2").encode(
                    x=alt.X("share:Q", bin=alt.Bin(step=5), title="part in one cluster of the second choice (%)"),
                    y=alt.Y("count():Q", title="clusters of the first choice")),
                alt.Chart(pd.DataFrame({"x": [80]})).mark_rule(color="#D55E00", strokeDash=[4, 3]).encode(x="x:Q"))
                  .properties(height=260))
        with right:
            st.markdown("**Where the 20 largest clusters go**")
            st.caption("Rows: the 20 largest clusters of the first choice. Columns: the clusters of the second"
                       " choice. One dark cell in a row: the cluster stays together.")
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
                    x=alt.X("second:N", title="cluster of the second choice", sort=None),
                    y=alt.Y("first:N", title="cluster of the first choice", sort=[str(t) for t in top]),
                    color=alt.Color("share:Q", scale=alt.Scale(domain=[0, 1], scheme="greens"), title="part"),
                    tooltip=["first:N", "second:N", alt.Tooltip("share:Q", format=".0%")])
                      .properties(height=alt.Step(16)))
        st.caption("Each row is a cluster of the first choice. \"Part\": the part of its sentences in one cluster"
                   " of the second choice. The clusters that the second choice splits most are at the top.")
        show(pd.DataFrame({
            "cluster": crossing["cluster"],
            "terms": crossing["cluster"].map(names_of[first["case_name"]]),
            "sentences": crossing["sentences"],
            "goes mostly to": crossing["best_second"],
            "part": [f"{s:.0%}" for s in crossing["share"]],
            "its terms": crossing["best_second"].map(names_of[second["case_name"]]),
            "in no cluster there": crossing["noise_in_second"],
        }).iloc[crossing["share"].argsort(kind="stable")])
    decision(cases, picked, current)


def decision(cases, picked, current):
    """Stage 5's result: one of the two choices recorded as the concern map."""
    st.subheader("The decision")
    decided = current.iloc[0]["case_name"] if not current.empty else None
    if decided in set(cases["case_name"]):
        r = current.iloc[0]
        c = cases[cases["case_name"] == decided].iloc[0]
        st.success(f"The concern map is the {model_name(c['model'])} choice: {c['description']}"
                   + (f". Note: {r['note']}" if r["note"] else ""))
    else:
        st.info("No case is the concern map.")
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
            elif st.button("Use this case as the concern map", key=f"step2_use_{r.model}"):
                record_concern_map(r.case_name, note.strip() or None)
                st.rerun()
    st.markdown("**Next:** the next step of the method writes one concern statement for each cluster of the"
                " concern map. That step is not built yet.")


def record_concern_map(case_name, note):
    """A write of the console: the decided case recorded as the concern map (make concern-map)."""
    from scripts.clusters import cases as case_runs
    with contextlib.closing(db.connect(db.DB_PATH)) as conn:
        case_runs.concern_map(conn, case_name, note)


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
