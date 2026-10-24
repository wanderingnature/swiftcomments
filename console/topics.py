"""The console's Topics page (new): the path from the sentences to the concern
map, in five stages (docs/topics-guide.md). The status lines at the top show
each stage done, next or waiting. Five tabs: Guide (docs/topics-guide.md, its
screenshots shown with st.image);
Stage 4, the cases of one model on a chart, a click selecting a case and a
button recording it as the model's choice; Stage 5, the two choices compared, a
click on a cluster showing it beside the other choice's cluster, and a button for
each choice recording it as the concern map; What the stages found, the figures
and charts of each stage, the concern map's last; Read a case, one case from
its topics to a cluster's sentences and the comments that hold them.

Every figure is read from data/roadless.sqlite through view.query, cached until
the file changes. Nothing here runs a case: make clusters does. The two writes are
the choice of stage 4 (cluster_case_choice, as make choose) and the concern map of
stage 5 (cluster_concern_map, as make concern-map).
"""
import contextlib
import json
import re
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from console import queries as q
from console.results import CARDS, chart, hbar, metrics, pager, pct, snippet, texts
from console.view import file_signature, open_db, query, show, show_text
from scripts.clusters.embed import VIEWS, unpack
from shared import case_compare, db

GUIDE = Path(__file__).resolve().parents[1] / "docs" / "topics-guide.md"
IMAGE = re.compile(r"!\[(.*)\]\((images/[^)]+)\)")
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
        parts.append(count(int(c["passes"]), "pass", "passes"))
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
        parts.append(count(int(c["passes"]), "noise pass", "noise passes"))
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
            show_guide()
        return
    guide, stage4, stage5, found, read = st.tabs(["Guide", "Stage 4: Best case of each model",
                                                  "Stage 5: Concern map", "What the stages found", "Read a case"])
    with guide:
        show_guide()
    with stage4:
        tab_stage4(cases, choices)
    with stage5:
        tab_stage5(cases, choices, current)
    with found:
        tab_found(srun, cases, current)
    with read:
        tab_read(cases, current)


def show_guide():
    """The guide, with its screenshots: an image line of the Markdown becomes st.image."""
    text = GUIDE.read_text(encoding="utf-8")
    part = []
    for line in text.splitlines():
        image = IMAGE.fullmatch(line.strip())
        if image:
            st.markdown("\n".join(part))
            part = []
            st.image(str(GUIDE.parent / image.group(2)), caption=image.group(1))
        else:
            part.append(line)
    st.markdown("\n".join(part))


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
    same = pts.groupby(["sentences clustered (%)", "comments not covered"], as_index=False)["number"].agg(
        lambda n: ", ".join(str(i) for i in sorted(n)))   # cases at one point share one label
    numbers = alt.Chart(same).mark_text(align="left", dx=17, dy=-15, fontSize=12, fontWeight="bold").encode(
        x=x, y=y, text="number:N")
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
        "settings": [short(c) for _, c in cases.iterrows()],
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


def tab_found(srun, cases, current):
    """What each stage wrote in the file, as figures and charts."""
    st.caption("The results of each stage, read from the file.")
    st.subheader("Stage 1: the sentences")
    r = srun.iloc[0]
    metrics([("Gate-open comments", int(r["gate_comments"]), None),
             ("Sentences", int(r["occurrences"]), "Every sentence of the gate-open comments."),
             ("Different sentences", int(r["distinct_sentences"]),
              "Two sentences are the same if they differ only in case, punctuation, spacing or markup.")])
    kinds = query(q.OPENING_KINDS).iloc[0]
    left, right = st.columns(2)
    with left:
        st.markdown("**The gate-opening sentences, by gate kind**")
        st.caption(f"{int(kinds['n']):,} sentences open the gate alone. A sentence of two kinds counts in both bars.")
        chart(alt.Chart(pd.DataFrame({"kind": ["LAW", "EVID", "GAP", "ALT"],
                                      "sentences": [int(kinds[k]) for k in ("LAW", "EVID", "GAP", "ALT")]}))
              .mark_bar().encode(x=alt.X("sentences:Q"), y=alt.Y("kind:N", sort=None, title=None),
                                 color=alt.Color("kind:N", scale=KIND_SCALE, legend=None),
                                 tooltip=["kind:N", alt.Tooltip("sentences:Q", format=",")])
              .properties(height=alt.Step(30)))
    with right:
        st.markdown("**How each gate-open comment shows in the sentences**")
        st.caption("A comment can have a gate-opening sentence and a sentence that holds a whole-comment hit. Then"
                   " it counts in both bars.")
        hbar(pd.DataFrame({"comments with": ["a gate-opening sentence", "a sentence that holds a hit",
                                             "neither"],
                           "comments": [int(r["comments_opening"]), int(r["comments_hit"]),
                                        int(r["comments_neither"])]}),
             "comments with", "comments", "gate-open comments", color="#0072B2")

    st.subheader("Stage 2: the vectors")
    view_of = {v: k for k, v in VIEWS.items()}
    vv = query(q.VECTORS_BY_VIEW)
    vv["vectors of"] = [f"{model_name(m)}, {view_of.get(i, 'other')} view"
                        for m, i in zip(vv["model"], vv["instruction"])]
    st.caption(f"Each bar is one model and view. A full bar has a vector for each of the"
               f" {int(r['distinct_sentences']):,} different sentences.")
    hbar(vv, "vectors of", "n", "vectors", color="#0072B2")

    st.subheader("Stage 3: the cases of both models")
    st.caption("Each point is a case. A good case is low and to the right. Colour: the model. Black ring: the choice"
               " of stage 4. Red ring: a cluster of 1,000 or more sentences.")
    choices = set(query(q.CHOICES)["case_name"])
    pts = pd.DataFrame({
        "case": cases["description"],
        "model": cases["model_label"],
        "sentences clustered (%)": (100 * cases["leaders_clustered"] / cases["leaders"]).round(1),
        "comments not covered": cases["comments_unclustered"],
        "largest cluster": cases["largest_cluster"],
        "choice": cases["case_name"].isin(choices)})
    models = sorted(pts["model"].unique())
    x = alt.X("sentences clustered (%):Q", scale=alt.Scale(zero=False))
    y = alt.Y("comments not covered:Q")
    tip = ["case:N", "sentences clustered (%):Q", "comments not covered:Q", "largest cluster:Q"]
    chart(alt.layer(
        alt.Chart(pts).mark_point(filled=True, size=140, opacity=0.85).encode(
            x=x, y=y, color=alt.Color("model:N", scale=alt.Scale(domain=models, range=MODEL_COLOURS[:len(models)])),
            tooltip=tip),
        alt.Chart(pts[pts["largest cluster"] >= CATCH_ALL]).mark_point(
            shape="circle", size=480, filled=False, color="#d62728", strokeWidth=2).encode(x=x, y=y, tooltip=tip),
        alt.Chart(pts[pts["choice"]]).mark_point(
            shape="circle", size=800, filled=False, color="black", strokeWidth=3).encode(x=x, y=y, tooltip=tip))
          .properties(height=380))

    st.subheader("Stage 5: the concern map")
    decided = current.iloc[0]["case_name"] if not current.empty else None
    if decided not in set(cases["case_name"]):
        st.info("No case is the concern map. Do stage 5 first.")
        return
    c = cases[cases["case_name"] == decided].iloc[0]
    st.markdown(f"The concern map is the {model_name(c['model'])} choice: {c['description']}.")
    clusters = query("SELECT cluster, topic, leaders, law, evid, gap, alt, terms, central FROM cluster_case_cluster"
                     " WHERE case_name = ?", (decided,))
    clusters = clusters.merge(query(q.CLUSTER_REACH, (decided,)), on="cluster")
    clusters["main kind"] = [KINDS[i].upper() for i in clusters[list(KINDS)].to_numpy().argmax(1)]
    clusters["words"] = [terms(t, 4) for t in clusters["terms"]]
    metrics([("Clusters", int(c["clusters"]), "Step 15 writes one concern statement for each cluster."),
             ("Topics", int(c["topics"]), None),
             (f"Comments covered, of {int(c['gate_comments']):,}",
              int(c["gate_comments"] - c["comments_unclustered"]),
              "Gate-open comments with a substantive sentence in a cluster."),
             ("Median comments", int(clusters["comments"].median()), "The median number of gate-open comments that hold a sentence of a cluster.")])

    topics = query(q.CASE_TOPICS, (decided,)).merge(query(q.TOPIC_REACH, (decided,)), on="topic")
    weight = clusters[list(KINDS)].mul(clusters["leaders"], axis=0).groupby(clusters["topic"]).sum()
    topics["main kind"] = [KINDS[i].upper() for i in weight.loc[topics["topic"]].to_numpy().argmax(1)]
    topics["topic "] = [f"Topic {t}: {terms(w, 4)}" for t, w in zip(topics["topic"], topics["terms"])]
    st.markdown("**The topics, by the comments that they cover**")
    st.caption("One bar for each topic. The length is the number of gate-open comments with a sentence in the topic."
               " The colour is the gate kind of most of its sentences.")
    chart(alt.Chart(topics).mark_bar().encode(
        x=alt.X("comments:Q", title="gate-open comments"),
        y=alt.Y("topic :N", sort="-x", title=None, axis=alt.Axis(labelLimit=420, labelOverlap=False)),
        color=alt.Color("main kind:N", scale=KIND_SCALE),
        tooltip=["topic :N", "clusters:Q", alt.Tooltip("comments:Q", format=","), "main kind:N"])
          .properties(height=alt.Step(20)))

    top = clusters.nlargest(30, "comments").copy()
    top["cluster "] = [f"Cluster {n}: {w}" for n, w in zip(top["cluster"], top["words"])]
    top["sentence"] = [(json.loads(s) or [""])[0] for s in top["central"]]
    st.markdown("**The 30 clusters that the most comments hold**")
    st.caption("One bar for each cluster. Point to a bar to read the most typical sentence of the cluster.")
    chart(alt.Chart(top).mark_bar().encode(
        x=alt.X("comments:Q", title="gate-open comments"),
        y=alt.Y("cluster :N", sort="-x", title=None, axis=alt.Axis(labelLimit=420, labelOverlap=False)),
        color=alt.Color("main kind:N", scale=KIND_SCALE),
        tooltip=["cluster :N", "topic:Q", alt.Tooltip("comments:Q", format=","), "leaders:Q", "sentence:N"])
          .properties(height=alt.Step(20)))

    spread = query(q.COMMENT_SPREAD, (decided,))
    st.markdown("**The clusters of each comment**")
    st.caption("The number of clusters that hold a sentence of a comment. A comment in five clusters makes about five"
               " claims.")
    chart(alt.Chart(spread).mark_bar(color="#0072B2").encode(
        x=alt.X("clusters:O", title="clusters that hold a sentence of the comment", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("comments:Q", title="gate-open comments"),
        tooltip=["clusters:O", alt.Tooltip("comments:Q", format=",")]).properties(height=240))

    with st.expander(f"All {len(clusters):,} clusters of the concern map"):
        show(clusters.sort_values("comments", ascending=False)[
            ["cluster", "topic", "comments", "leaders", "main kind", "words"]].rename(
            columns={"leaders": "sentences"}))


def tab_read(cases, current):
    names = list(cases["case_name"])
    selected = st.session_state.get("step1_case") or (current.iloc[0]["case_name"] if not current.empty else None)
    if selected in names and st.session_state.get("read_follows") != selected:
        st.session_state["read_case"] = names.index(selected)
        st.session_state["read_follows"] = selected
    st.caption("The case selected in stage 4 opens here. Before you select a case, the concern map opens here.")
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
            y=alt.Y("topic:O", title="topic", sort="ascending", axis=alt.Axis(labelOverlap=False)),
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
    first = cases[cases["case_name"] == picked[0].case_name].iloc[0]
    second = cases[cases["case_name"] == picked[1].case_name].iloc[0]
    left_name, right_name = model_name(first["model"]), model_name(second["model"])
    st.markdown("**What to do here**\n\n"
                "The two choices group the same sentences. This tab shows where they group them differently.\n\n"
                "1. In the table, click a row near the top. The top rows are where the two choices differ most.\n"
                f"2. Read the two clusters under the table: the {left_name} cluster on the left, the {right_name}"
                " cluster on the right.\n"
                "3. Note which side makes one claim.\n"
                "4. Do steps 1 to 3 for three or four rows.\n"
                "5. Under the choice that made one claim more often, type a note and click **Use this case as the"
                " concern map**.")
    with open_db() as conn:
        a = case_compare.labels(conn, first["case_name"])
        b = case_compare.labels(conn, second["case_name"])
        names_of = {n: {c: terms(t, 4) for c, t in conn.execute(
            "SELECT cluster, terms FROM cluster_case_cluster WHERE case_name = ?", (n,))}
            for n in (first["case_name"], second["case_name"])}
    m = case_compare.compare(a, b)
    crossing = pd.DataFrame(m["crossing"])
    if crossing.empty:
        st.caption(f"The {left_name} choice has no cluster.")
        decision(cases, picked, current)
        return
    crossing = crossing.iloc[crossing["share"].argsort(kind="stable")].reset_index(drop=True)
    order = list(crossing["cluster"])
    st.subheader("Where the two choices differ")
    st.caption(f"One row for each {left_name} cluster. \"Kept together\": the part of its sentences that the"
               f" {right_name} choice puts in one cluster. A low part means that {right_name} splits the cluster.")
    st.dataframe(pd.DataFrame({
        f"{left_name} cluster": crossing["cluster"],
        "its words": crossing["cluster"].map(names_of[first["case_name"]]),
        "sentences": crossing["sentences"],
        "kept together": [f"{s:.0%}" for s in crossing["share"]],
        f"{right_name} cluster": crossing["best_second"],
        "its words ": crossing["best_second"].map(names_of[second["case_name"]]),
        f"in no {right_name} cluster": crossing["noise_in_second"],
    }), hide_index=True, width="stretch", height=320, key="stage5_table", on_select=lambda: _row(order),
        selection_mode="single-row")
    cluster = st.session_state.get("stage5_cluster")
    if cluster not in order:
        cluster = order[0]
    row = crossing[crossing["cluster"] == cluster].iloc[0]
    other = int(row["best_second"])
    left, right = st.columns(2)
    with left:
        leader_rows(first["case_name"], int(cluster), f"{left_name} cluster {cluster}", "stage5_left")
    with right:
        if other:
            leader_rows(second["case_name"], other, f"{right_name} cluster {other}", "stage5_right")
            st.caption(f"This cluster holds {row['share']:.0%} of the sentences of {left_name} cluster {cluster}."
                       f" {int(row['noise_in_second']):,} of them are in no {right_name} cluster.")
        else:
            st.markdown(f"**{right_name}**")
            st.caption(f"The {right_name} choice puts the sentences of {left_name} cluster {cluster} in no"
                       " cluster.")

    with st.expander("How far the two choices agree overall"):
        metrics([("Clustered by both", m["clustered_both"],
                  f"{left_name} clusters {m['clustered_first']:,} sentences, {right_name} {m['clustered_second']:,}."),
                 ("Adjusted Rand", m["ari"] if m["ari"] is not None else "-",
                  "How alike the two choices cluster the same sentences. 1: the same clusters. Near 0: different"
                  " clusters."),
                 ("Clusters kept together", f"{m['clusters_80']} of {len(crossing)}",
                  f"{left_name} clusters with 80% or more of their sentences in one {right_name} cluster.")])
        dist = pd.DataFrame({"share": crossing["share"] * 100})
        st.caption(f"The {left_name} clusters, by the part of their sentences in one {right_name} cluster. Bars"
                   " right of the line: the cluster stays together.")
        chart(alt.layer(
            alt.Chart(dist).mark_bar(color="#0072B2").encode(
                x=alt.X("share:Q", bin=alt.Bin(step=5), title=f"part in one {right_name} cluster (%)"),
                y=alt.Y("count():Q", title=f"{left_name} clusters")),
            alt.Chart(pd.DataFrame({"x": [80]})).mark_rule(color="#D55E00", strokeDash=[4, 3]).encode(x="x:Q"))
              .properties(height=240))
    decision(cases, picked, current)


def _row(order):
    """The table's click: the clicked row's cluster becomes the cluster shown side by side."""
    rows = st.session_state["stage5_table"]["selection"]["rows"]
    if rows:
        st.session_state["stage5_cluster"] = order[rows[0]]


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
