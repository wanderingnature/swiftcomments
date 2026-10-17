"""The console's results pages (new; the core of rtca's Reports, Places &
Citations and Substance pages, streamlit_organic_app/app_pages/, over the one
file): what the analysis found, rather than what each step wrote.

    Overview               the corpus, the letters, the stance, the substance in one page
    Stance and topics      make stance: the stance, its strength, the topics, by day; one topic's letters
    Coordination           the copies, the families and campaigns, who ran them, the daily wave
    Places and citations   make tag, strict layer: what comments name and cite; the letters naming one
    Substance              the floor, the screen, either reading of class A; every scored comment, filtered

Every figure is read from data/roadless.sqlite through view.query, cached until
the file changes. A section whose step has not run says which make target fills it.
"""
import json

import altair as alt
import pandas as pd
import streamlit as st

from console import queries as q
from console.view import open_db, query, show, show_text, vocab

DIMS = ("PLACE", "STAND", "DOC", "GAP", "EVID", "ASK", "ALT", "LAW")
STANCES = ("SUPPORT", "OPPOSE", "NEUTRAL")
STANCE_SCALE = alt.Scale(domain=list(STANCES), range=["#2ca02c", "#d62728", "#9e9e9e"])
BANDS = ("minimal", "marginal", "developed", "strong")
BAND_SCALE = alt.Scale(domain=list(BANDS), range=["#c6dbef", "#6baed6", "#3182bd", "#08519c"])
A_LEVELS = ("A1", "A2", "A3", "A0")
CARDS = 20      # the comments shown at a time


def not_run(target):
    st.caption(f"make {target} has not run: nothing written yet.")


def metrics(items):
    """One row of bordered figures: (label, value, help or None)."""
    for col, (label, value, help_) in zip(st.columns(len(items)), items):
        col.metric(label, f"{value:,}" if isinstance(value, int) else value, help=help_, border=True)


def chart(c):
    st.altair_chart(c, width="stretch")


def hbar(df, label, value, title, color="#2f6b4e", tooltip=None):
    """Horizontal bars, longest first, every label shown whole."""
    chart(alt.Chart(df).mark_bar(cornerRadiusEnd=3, color=color).encode(
        x=alt.X(f"{value}:Q", title=title),
        y=alt.Y(f"{label}:N", sort="-x", title=None, axis=alt.Axis(labelLimit=400, labelOverlap=False)),
        tooltip=tooltip or [f"{label}:N", f"{value}:Q"]).properties(height=alt.Step(22)))


def pct(n, of):
    return f"{100 * n / of:.1f}%" if of else "-"


def snippet(text, n=110):
    flat = " ".join((text or "").split())
    return flat[:n] + ("..." if len(flat) > n else "") if flat else "(no text)"


def texts(ids):
    """The text of each of a few comments, by id."""
    if not len(ids):
        return {}
    marks = ",".join("?" * len(ids))
    df = query(f"SELECT comment_id, comment_text FROM comment WHERE comment_id IN ({marks})", tuple(ids))
    return dict(zip(df["comment_id"], df["comment_text"]))


def sent_by(kind, size):
    """'a unique letter' or 'sent by N (Campaign)' from a comment's group."""
    if kind is None or pd.isna(kind):
        return "in no comment group"
    if kind == "singleton":
        return "a unique letter"
    label = vocab("group_kind").get(kind)
    return f"one of {int(size):,} sent ({label.label if label else kind})"


def pager(total, key):
    """The page of a long list: a number input when there is more than one page;
    returns the offset."""
    pages = max(1, -(-total // CARDS))
    if pages == 1:
        return 0
    page = st.number_input(f"page, of {pages:,} ({CARDS} to a page)", min_value=1, max_value=pages,
                           value=1, key=key)
    return (int(page) - 1) * CARDS


# --------------------------------------------------------------- overview

def page_overview():
    st.header("Overview")
    st.caption("What the analysis found, from the corpus to the substance reading. Each section is"
               " one step's result; the pages below it in the sidebar open each one up.")
    rec = query(q.RECORDS).iloc[0]
    if not rec["records"]:
        not_run("corpus")
        return
    st.subheader("The docket")
    metrics([("Records", int(rec["records"]), "Every record of the bulk download."),
             ("With text", int(rec["with_text"]), "Records with a comment's text: the corpus the steps read."),
             ("Withdrawn", int(rec["withdrawn"]), None),
             ("Blank", int(rec["blank"]), "No text and not withdrawn: an attachment alone, or nothing.")])

    st.subheader("How many letters")
    groups = query(q.GROUPS_BY_KIND)
    if groups.empty:
        not_run("groups")
    else:
        letters, comments = int(groups["letters"].sum()), int(groups["comments"].sum())
        metrics([("Unique letters", letters,
                  "One per comment group: every copy, shared body, family and campaign folded into the letter"
                  " it sent."),
                 ("Comments", comments, None),
                 ("Comments that repeat another", comments - int(groups.loc[groups["kind"] == "singleton",
                                                                            "comments"].sum()), None)])
        show(groups.assign(**{"share of comments": [pct(c, comments) for c in groups["comments"]]})
             [["label", "meaning", "letters", "comments", "share of comments"]])

    st.subheader("Stance")
    stance = query(q.STANCE)
    if stance.empty:
        not_run("stance")
    else:
        total, total_letters = int(stance["comments"].sum()), int(stance["letters"].sum())
        metrics([(f"{r.stance}", f"{r.comments:,} ({pct(r.comments, total)})",
                  f"{r.meaning} {r.letters:,} letters ({pct(r.letters, total_letters)} of the letters).")
                 for r in stance.itertuples()])
        st.caption("Comments by the stance of their letter; hover a figure for what the stance means and"
                   " its share of the unique letters.")

    st.subheader("Substance")
    screen = query(q.SCREEN)
    if screen.empty:
        not_run("screen")
    else:
        metrics([(f"Class {r.screen_class}", int(r.comments), SCREEN_CLASSES[r.screen_class])
                 for r in screen.itertuples()])
    rows = []
    for name, df in readings().items():
        if df.empty:
            continue
        one = one_per_letter(df)
        gated = int(one["gate"].sum())
        row = {"reading": name, "letters scored": len(one), "gate open": f"{gated:,} ({pct(gated, len(one))})",
               "mean strength (of 24)": round(float(one["strength"].mean()), 1)}
        for lv in A_LEVELS:
            row[f"{lv} {vocab('a_level')[lv].label}"] = int((one["a_level"] == lv).sum())
        rows.append(row)
    if rows:
        show(pd.DataFrame(rows))
        st.caption("Each reading of class A, one row per letter (the letter's highest-scored comment). The"
                   " Substance page opens either reading up, to every comment it scored.")
    else:
        st.caption("Neither reading of class A has run: make score-model-free (no model) or make score-model.")


# ------------------------------------------------------ stance and topics

def page_stance():
    st.header("Stance and topics")
    meanings = query("SELECT sentiment, meaning FROM sentiment ORDER BY sentiment_id")
    stance = query(q.STANCE)
    if stance.empty:
        not_run("stance")
        return
    with st.container(border=True):
        for r in meanings.itertuples():
            st.markdown(f"**{r.sentiment}**: {r.meaning or '(no meaning set)'}")
    st.caption("make stance classifies one comment per comment group and copies its stance and topics to"
               " every member, so each figure counts comments; letters counts the groups.")

    total = int(stance["comments"].sum())
    stance["share"] = [round(100 * c / total, 1) for c in stance["comments"]]
    left, right = st.columns([2, 3])
    with left:
        chart(alt.Chart(stance).mark_arc(innerRadius=70, stroke="white", strokeWidth=2).encode(
            theta=alt.Theta("comments:Q", stack=True),
            color=alt.Color("stance:N", scale=STANCE_SCALE, legend=alt.Legend(title="Stance")),
            tooltip=["stance:N", "comments:Q", "share:Q", "letters:Q"]).properties(height=260))
    with right:
        show(stance[["stance", "comments", "share", "letters"]].rename(columns={"share": "% of comments"}))

    st.subheader("How firmly")
    strength = query(q.STANCE_STRENGTH)
    chart(alt.Chart(strength).mark_bar().encode(
        x=alt.X("stance:N", sort=list(STANCES), title=None),
        y=alt.Y("comments:Q", title="Comments"),
        color=alt.Color("strength:N", sort=["HIGH", "MEDIUM", "LOW"], legend=alt.Legend(title="Strength"),
                        scale=alt.Scale(domain=["HIGH", "MEDIUM", "LOW"], range=["#1f4e79", "#5b9bd5", "#bdd7ee"])),
        tooltip=["stance:N", "strength:N", "comments:Q"]).properties(height=280))
    st.caption("HIGH is a clear, direct position; LOW is weak or ambiguous language.")

    topics = query(q.TOPICS)
    if not topics.empty:
        st.subheader("Topics")
        chart(alt.Chart(topics).mark_bar(cornerRadiusEnd=3).encode(
            y=alt.Y("topic:N", sort="-x", title=None, axis=alt.Axis(labelLimit=400)),
            x=alt.X("comments:Q", title="Comments"),
            color=alt.Color("avg_confidence:Q", scale=alt.Scale(scheme="teals"), legend=alt.Legend(title="Mean conf.")),
            tooltip=["topic:N", "comments:Q", "letters:Q", "avg_confidence:Q"]).properties(height=alt.Step(26)))
        show(topics[["topic", "comments", "letters", "avg_confidence", "description"]])

        st.subheader("Stance by topic")
        chart(alt.Chart(query(q.STANCE_BY_TOPIC)).mark_bar().encode(
            y=alt.Y("topic:N", sort="-x", title=None, axis=alt.Axis(labelLimit=400)),
            x=alt.X("comments:Q", stack="normalize", title="Share of the topic's comments", axis=alt.Axis(format="%")),
            color=alt.Color("stance:N", scale=STANCE_SCALE, legend=alt.Legend(title="Stance")),
            tooltip=["topic:N", "stance:N", "comments:Q"]).properties(height=alt.Step(26)))

        pairs = query(q.TOPIC_PAIRS)
        if not pairs.empty:
            st.subheader("Topics raised together")
            both = pd.concat([pairs, pairs.rename(columns={"topic_a": "topic_b", "topic_b": "topic_a"})])
            chart(alt.Chart(both).mark_rect().encode(
                x=alt.X("topic_a:N", title=None, axis=alt.Axis(labelAngle=-40, labelLimit=400)),
                y=alt.Y("topic_b:N", title=None, axis=alt.Axis(labelLimit=400)),
                color=alt.Color("comments:Q", scale=alt.Scale(scheme="teals", type="log"),
                                legend=alt.Legend(title="Comments")),
                tooltip=["topic_a:N", "topic_b:N", "comments:Q"]).properties(height=alt.Step(26)))
            st.caption("Comments that raise both topics; the colour scale is logarithmic.")

    by_day = query(q.STANCE_BY_DAY)
    if not by_day.empty:
        st.subheader("By the day received")
        by_day["day"] = pd.to_datetime(by_day["day"])
        chart(alt.Chart(by_day).mark_area(opacity=0.85).encode(
            x=alt.X("day:T", title=None), y=alt.Y("comments:Q", title="Comments a day", stack=True),
            color=alt.Color("stance:N", scale=STANCE_SCALE, legend=alt.Legend(title="Stance")),
            tooltip=[alt.Tooltip("day:T"), "stance:N", "comments:Q"]).properties(height=260))
    pv = query(q.POSTED_RECEIVED)
    if not pv.empty:
        pv["day"] = pd.to_datetime(pv["day"])
        chart(alt.Chart(pv).mark_line(point=True).encode(
            x=alt.X("day:T", title=None), y=alt.Y("comments:Q", title="Comments a day"),
            color=alt.Color("series:N", legend=alt.Legend(title=None),
                            scale=alt.Scale(domain=["Received", "Posted"], range=["#2f6b4e", "#9e9e9e"])),
            tooltip=[alt.Tooltip("day:T"), "series:N", "comments:Q"]).properties(height=220))
        st.caption("Received is when a commenter submitted; posted is when the agency published it.")

    if topics.empty:
        return
    st.subheader("Read one topic's letters")
    left, right = st.columns([3, 2])
    topic = left.selectbox("topic", list(topics["topic"]), key="topic_pick")
    which = right.radio("stance", ("any",) + STANCES, horizontal=True, key="topic_stance")
    s = "" if which == "any" else which
    n = int(query(q.TOPIC_LETTER_COUNT, (topic, s, s)).iloc[0]["n"])
    st.caption(f"{n:,} letters raise it{'' if not s else f' with the stance {s}'}, most-sent first;"
               " each with the phrases the model quoted for the topic.")
    offset = pager(n, "topic_page")
    for r in query(q.TOPIC_LETTERS, (topic, s, s, CARDS, offset)).itertuples():
        with st.container(border=True):
            st.markdown(f"**{r.stance}** ({r.strength}) · {sent_by(r.group_kind, r.size)} · `{r.comment_id}`")
            for phrase in json.loads(r.supporting_phrases):
                st.caption(f'"{phrase}"')
            with st.expander(snippet(r.comment_text)):
                show_text(r.comment_text)


# ----------------------------------------------------------- coordination

def page_coordination():
    st.header("Coordination")
    copies = query(q.COPIES).iloc[0]
    groups = query(q.GROUPS_BY_KIND)
    if not copies["hashed"]:
        not_run("dedup")
        return
    figures = [("Exact copies", int(copies["exact_copies"]),
                "Byte-identical to an earlier submission once whitespace and case are set aside."),
               ("Same body", int(copies["same_body"]),
                "A text of its own, but the same body as another: one letter under a different greeting or"
                " signature.")]
    if not groups.empty:
        figures.append(("Unique letters", int(groups["letters"].sum()),
                        "One per comment group: every repetition folded."))
    metrics(figures)
    if groups.empty:
        not_run("groups")
        return
    st.subheader("Comments by the letter they sent")
    chart(alt.Chart(groups).mark_bar(cornerRadiusEnd=3, color="#cb181d").encode(
        y=alt.Y("label:N", sort=list(groups["label"]), title=None),
        x=alt.X("comments:Q", title="Comments"),
        tooltip=["label:N", "meaning:N", "letters:Q", "comments:Q"]).properties(height=alt.Step(30)))
    show(groups[["label", "meaning", "letters", "comments"]])

    wave = query(q.DAILY_WAVE)
    if not wave.empty:
        st.subheader("The daily wave")
        wave["day"] = pd.to_datetime(wave["day"])
        long = wave.melt(id_vars="day", value_vars=["unique_letters", "repeated"], var_name="kind",
                         value_name="comments").replace({"unique_letters": "Heads its own letter",
                                                         "repeated": "Repeats a letter"})
        chart(alt.Chart(long).mark_area(opacity=0.85).encode(
            x=alt.X("day:T", title=None), y=alt.Y("comments:Q", title="Comments a day", stack=True),
            color=alt.Color("kind:N", legend=alt.Legend(title=None),
                            scale=alt.Scale(domain=["Heads its own letter", "Repeats a letter"],
                                            range=["#9e9e9e", "#cb181d"])),
            tooltip=[alt.Tooltip("day:T"), "kind:N", "comments:Q"]).properties(height=260))
        st.caption("Each day's comments: the first of its comment group, or a repeat of one. A spike in the"
                   " red band is a drive landing.")

    campaigns = query(q.CAMPAIGNS)
    if campaigns.empty:
        return
    st.subheader("The campaigns")
    in_campaigns = int(campaigns["comments"].sum())
    metrics([("Campaigns", len(campaigns), "Families of one letter sent by 10 or more people."),
             ("Comments in them", in_campaigns, None),
             ("With an organisation found", int(campaigns["organisation"].notna().sum()),
              "make orgs: the organisation that ran the campaign, on one of four bases.")])
    show(campaigns[["comments", "texts", "with_own_text", "organisation", "organisation_basis", "stance",
                    "exemplar_comment_id"]])
    st.caption("texts: the distinct texts in the family; with_own_text: members who added words of their"
               " own. Below, the largest, each opening to its letter.")
    offset = pager(len(campaigns), "campaign_page")
    for r in campaigns.iloc[offset:offset + CARDS].itertuples():
        head = f"{r.comments:,} comments" + (f" · {r.organisation}" if r.organisation else "") + \
               (f" · {r.stance}" if r.stance else "")
        with st.expander(f"{head} · {snippet(r.comment_text, 80)}"):
            st.caption(f"family {r.family_id} · {r.texts:,} distinct texts · {r.with_own_text:,} added words of"
                       f" their own · the letter as `{r.exemplar_comment_id}` sent it"
                       + (f" · organisation {r.organisation_basis.lower()}" if r.organisation_basis else ""))
            show_text(r.comment_text)


# --------------------------------------------------- places and citations

def page_places():
    st.header("Places and citations")
    scanned = query("SELECT count(*) AS n FROM entity_scan_state WHERE is_tagged_strict = 1").iloc[0]["n"]
    if not scanned:
        not_run("tag")
        return
    st.caption(f"make tag's strict pass: exact matches against the reference lists, over {scanned:,} comments."
               " Every count here traces to a matched word in a comment.")
    figures = [(label, int(query(q.tag_comments(kind)).iloc[0, 0]), None)
               for kind, (_, _, label) in q.TAGS.items() if kind != "zip code"]
    figures.append(("Name nothing", int(query(q.NAMES_NOTHING).iloc[0, 0]),
                    "Scanned comments that name no place, species, authority or reference: a position stated"
                    " without one."))
    metrics(figures)

    left, right = st.columns(2)
    with left:
        st.markdown("**National forests named** (top 25)")
        hbar(query(q.tag_top("forest")).head(25), "value", "comments", "Comments")
        st.markdown("**Species named** (top 25)")
        hbar(query(q.tag_top("species")).head(25), "value", "comments", "Comments", color="#6a51a3")
    with right:
        st.markdown("**Roadless areas named** (top 25; the forest where the name is unambiguous)")
        hbar(query(q.AREAS), "area", "comments", "Comments", color="#4c78a8")
        st.markdown("**Where commenters say they are** (a signed City, ST ZIP line)")
        hbar(query(q.STATES), "state", "comments", "Comments", color="#72b7b2")

    families = query(q.AUTHORITY_FAMILIES)
    if not families.empty:
        st.subheader("Legal authorities cited")
        st.caption("Every way of writing a citation rolled up to the instrument it cites (36 CFR 294,"
                   " 36 C.F.R. Part 294 and 36 CFR 294.12(b) are one family), and whether the agency's own"
                   " record cites it.")
        chart(alt.Chart(families.head(25)).mark_bar(cornerRadiusEnd=3).encode(
            x=alt.X("comments:Q", title="Comments"),
            y=alt.Y("family:N", sort="-x", title=None, axis=alt.Axis(labelLimit=400, labelOverlap=False)),
            color=alt.Color("origin:N", title=None, scale=alt.Scale(
                domain=["in the agency record", "brought by commenters"], range=["#2f6b4e", "#c6863d"])),
            tooltip=["family:N", "comments:Q", "origin:N", "variants:Q"]).properties(height=alt.Step(22)))
        variants = query(q.AUTHORITY_VARIANTS)
        written = variants.groupby("family").apply(
            lambda g: "; ".join(f"{w} ({n:,})" for w, n in zip(g["as_written"], g["comments"])),
            include_groups=False).rename("as written")
        show(families.join(written, on="family"))

    biblio = query(q.BIBLIOGRAPHY)
    if not biblio.empty:
        st.subheader("The references cited")
        origins = query(q.BIBLIOGRAPHY_ORIGINS)
        metrics([(f"Works {r.origin}", int(r.works), f"cited by {r.comments:,} comments")
                 for r in origins.itertuples()])
        show(biblio, column_config={"url": st.column_config.LinkColumn("url")})

    st.subheader("Read the letters that name one")
    kinds = [k for k in q.TAGS if k != "zip code"]
    left, right = st.columns([1, 3])
    kind = left.selectbox("kind", kinds, key="names_kind")
    top = query(q.tag_top(kind))
    if top.empty:
        st.caption(f"no comment names a {kind}")
    else:
        labels = [f"{r.value} ({r.comments:,} comments, {r.letters:,} letters)" for r in top.itertuples()]
        pick = right.selectbox(kind, range(len(labels)), format_func=labels.__getitem__, key="names_value")
        value = top.iloc[pick]["value"]
        letters = query(q.tag_letters(kind), (value,))
        st.caption(f"The letters naming {value}, most-sent first (the first 100): how many of each letter's"
                   " comments name it, and the words as written.")
        for r in letters.itertuples():
            with st.expander(f"{r.naming:,} naming · {sent_by(r.group_kind, r.size)} · {snippet(r.comment_text, 80)}"):
                st.caption(f"as written: {r.as_written} · `{r.comment_id}`")
                show_text(r.comment_text)

    st.subheader("Comments that name nothing")
    st.caption("A random draw of the scanned comments with no strict match of any kind; draw again for"
               " another.")
    if st.button("Draw again", key="nothing_draw") or "nothing_sample" not in st.session_state:
        with open_db() as conn:
            st.session_state["nothing_sample"] = [tuple(r) for r in conn.execute(q.NAMES_NOTHING_SAMPLE, (10,))]
    for cid, text in st.session_state["nothing_sample"]:
        with st.expander(f"{cid} · {snippet(text, 90)}"):
            show_text(text)


# -------------------------------------------------------------- substance

SCREEN_CLASSES = {
    "A": "Names a legal authority, a reference or the agency's document, or states a deficiency in the action:"
         " the class both substance readings read.",
    "B1": "Refers to the action, with a deficiency or a named entity, but cites nothing.",
    "B2": "The rest of the floor's survivors.",
}


def readings():
    """Each reading of class A that has rows, one row per scored comment in one
    shape: the eight levels, strength, gate, band, A level, and the comment's
    group and stance. The rules' under the newest rule set; the model's with the
    newest answerability run."""
    out = {}
    rulesets = query(q.RULESETS)
    if not rulesets.empty:
        rs = rulesets["ruleset_version"].iloc[-1]
        out[f"rules (make score-model-free, rule set {rs})"] = query(q.RULES_READING, (rs,))
    runs = query(q.ANSWERABILITY_RUNS)
    model = query(q.MODEL_READING, (int(runs["run_id"].iloc[0]) if not runs.empty else None,))
    if not model.empty:
        out["model (make score-model, instrument v3)"] = model
    return out


def one_per_letter(df):
    """One row per comment group: the group's highest-scored comment (a comment in
    no group stands alone)."""
    key = df["group_id"].where(df["group_id"].notna(), df["comment_id"])
    return df.assign(_key=key).sort_values(["strength", "comment_id"], ascending=[False, True]) \
        .drop_duplicates("_key").drop(columns="_key")


def gate_text(gate, basis):
    """'gate closed', or 'gate open (GAP, LAW)': the model stores the basis as
    dimension names, the rules as {dimension, unit_id}."""
    dims = [b["dimension"] if isinstance(b, dict) else b for b in json.loads(basis)]
    return ("gate open" + (f" ({', '.join(dims)})" if dims else "")) if gate else "gate closed"


def levels_line(r):
    return "  ·  ".join(f"{d} {int(getattr(r, d.lower()))}" for d in DIMS)


def evidence(reading, ruleset, cid):
    """A comment's evidence under one reading: the rules' hits by dimension, or
    the model's rationale."""
    if reading.startswith("rules"):
        hits = query(q.RULES_EVIDENCE, (ruleset, cid))
        if hits.empty:
            st.caption("no rule fired")
        else:
            show(hits)
    else:
        d = query(q.MODEL_DETAIL, (cid,))
        if not d.empty:
            r = d.iloc[0]
            st.caption(f"{r['scored_via']}" + (f" from {r['exemplar_id']}" if r["exemplar_id"] else "")
                       + f" · {r['model']} · {r['instrument_version']}")
            if r["rationale"]:
                st.markdown(f"_{r['rationale']}_")


def page_substance():
    st.header("Substance")
    floor = query(q.FLOOR).iloc[0]
    st.subheader("The floor")
    if not floor["analysed"]:
        not_run("floor")
    else:
        metrics([("Read by the floor", int(floor["analysed"]), None),
                 ("Floored", int(floor["floored"]), "Tripped none of the four detectors: minimal, read no further."),
                 ("Survive", int(floor["survivors"]), "Tripped at least one detector.")])
        hbar(pd.DataFrame({"detector": ["named entity", "citation or legal", "deficiency language",
                                        "first-person observation"],
                           "comments": [int(floor[c]) for c in ("has_entity", "has_citation", "has_deficiency",
                                                                "has_firstperson")]}),
             "detector", "comments", "Comments tripping the detector")

    st.subheader("The screen")
    screen = query(q.SCREEN)
    if screen.empty:
        not_run("screen")
    else:
        show(screen.assign(meaning=[SCREEN_CLASSES[c] for c in screen["screen_class"]])
             [["screen_class", "comments", "meaning"]])

    st.subheader("The reading of class A")
    found = readings()
    if not found:
        st.caption("Neither reading has run: make score-model-free (no model) or make score-model.")
        return
    reading = st.radio("reading", list(found), horizontal=True, key="reading")
    ruleset = reading.split("rule set ")[-1].rstrip(")") if reading.startswith("rules") else None
    df = found[reading]
    if reading.startswith("model"):
        runs = query(q.ANSWERABILITY_RUNS)
        if len(runs) > 1:
            pick = st.selectbox("answerability run", list(runs["run_id"]), key="answer_run",
                                format_func=lambda i: " · ".join(str(v) for v in runs[runs["run_id"] == i].iloc[0]))
            df = query(q.MODEL_READING, (int(pick),))
    letters = st.toggle("one per letter", value=True, key="per_letter",
                        help="Count each comment group once, by its highest-scored comment, so a campaign's"
                             " copies do not outweigh a unique letter.")
    if letters:
        df = one_per_letter(df)
    unit = "letters" if letters else "comments"
    n = len(df)
    gated = int(df["gate"].sum())
    metrics([(f"Scored {unit}", n, None),
             ("Gate open", f"{gated:,} ({pct(gated, n)})",
              "Open when any of GAP, EVID, ALT or LAW reaches level 2."),
             ("Mean strength", f"{df['strength'].mean():.1f} of 24", "The eight levels summed."),
             ("A1: must be answered", int((df["a_level"] == "A1").sum()), vocab("a_level")["A1"].meaning)])

    left, right = st.columns(2)
    with left:
        st.markdown("**Strength**")
        chart(alt.Chart(df[["strength"]]).mark_bar().encode(
            x=alt.X("strength:O", title="strength (0 to 24)", scale=alt.Scale(domain=list(range(25)))),
            y=alt.Y("count():Q", title=unit), tooltip=["strength:O", "count():Q"]).properties(height=220))
    with right:
        st.markdown("**Band**")
        bands = df["band"].value_counts().reindex(BANDS, fill_value=0).rename_axis("band").reset_index(name="n")
        bands["label"] = [f"{vocab('band')[b].label} ({vocab('band')[b].lo} to {vocab('band')[b].hi})"
                          for b in bands["band"]]
        chart(alt.Chart(bands).mark_bar().encode(
            x=alt.X("label:N", sort=list(bands["label"]), title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("n:Q", title=unit),
            color=alt.Color("band:N", scale=BAND_SCALE, legend=None),
            tooltip=["label:N", "n:Q"]).properties(height=220))

    st.markdown("**The eight dimensions**: how many reach each level, 0 to 3")
    dims = vocab("dimension")
    counts = df[[d.lower() for d in DIMS]].melt(var_name="dim", value_name="level") \
        .value_counts().rename("n").reset_index()
    counts["dimension"] = [f"{d.upper()}: {dims[d.upper()].label}" for d in counts["dim"]]
    chart(alt.Chart(counts).mark_bar().encode(
        x=alt.X("level:O", title=None, scale=alt.Scale(domain=[0, 1, 2, 3])),
        y=alt.Y("n:Q", title=unit), tooltip=["dimension:N", "level:O", "n:Q"]
    ).properties(width=150, height=130).facet(
        facet=alt.Facet("dimension:N", sort=[f"{d}: {dims[d].label}" for d in DIMS], title=None), columns=4))
    show(pd.DataFrame([{"dimension": d, "label": dims[d].label, "meaning": dims[d].meaning,
                        "mean": round(float(df[d.lower()].mean()), 2),
                        "at 2 or 3": int((df[d.lower()] >= 2).sum()),
                        "share at 2 or 3": pct(int((df[d.lower()] >= 2).sum()), n)} for d in DIMS]))

    rated = df[df["a_level"].notna()]
    if not rated.empty:
        st.markdown("**Answerability**: how hard each comment is to dismiss, against its band")
        levels = vocab("a_level")
        grid = rated.value_counts(["band", "a_level"]).rename("n").reset_index()
        chart(alt.Chart(grid).mark_rect().encode(
            x=alt.X("a_level:O", title="answerability", sort=list(A_LEVELS)),
            y=alt.Y("band:O", title="band", sort=list(reversed(BANDS))),
            color=alt.Color("n:Q", title=unit, scale=alt.Scale(scheme="blues")),
            tooltip=["band:N", "a_level:N", "n:Q"]).properties(height=170))
        show(pd.DataFrame([{"level": lv, "label": levels[lv].label, "meaning": levels[lv].meaning,
                            unit: int((rated["a_level"] == lv).sum())} for lv in A_LEVELS]))
    else:
        st.caption("No answerability rating for this reading yet: make rate.")

    if ruleset and st.toggle("Show the rules that fired, by the comments they fired on", key="rules_fired",
                             help="Counts every hit of the rule set; on the whole corpus this takes a while."):
        show(query(q.RULES_FIRED, (ruleset,)))

    st.subheader("Read the scored comments")
    c1, c2, c3, c4 = st.columns(4)
    band = c1.multiselect("band", BANDS, key="f_band")
    gate = c2.selectbox("gate", ("any", "open", "closed"), key="f_gate")
    level = c3.multiselect("answerability", A_LEVELS, key="f_level")
    stance = c4.selectbox("stance", ("any",) + STANCES, key="f_stance")
    c5, c6, c7 = st.columns([1, 1, 2])
    dim = c5.selectbox("dimension", ("any",) + DIMS, key="f_dim")
    at_least = c6.selectbox("at least", (1, 2, 3), index=1, key="f_min", disabled=dim == "any")
    order = c7.radio("order", ("strongest first", "weakest first"), horizontal=True, key="f_order")
    pick = df
    if band:
        pick = pick[pick["band"].isin(band)]
    if gate != "any":
        pick = pick[pick["gate"] == (1 if gate == "open" else 0)]
    if level:
        pick = pick[pick["a_level"].isin(level)]
    if stance != "any":
        pick = pick[pick["stance"] == stance]
    if dim != "any":
        pick = pick[pick[dim.lower()] >= at_least]
    pick = pick.sort_values(["strength", "comment_id"], ascending=[order == "weakest first", True])
    st.caption(f"{len(pick):,} {unit} match.")
    offset = pager(len(pick), "f_page")
    page = pick.iloc[offset:offset + CARDS]
    text_of = texts(list(page["comment_id"]))
    band_labels = vocab("band")
    level_labels = vocab("a_level")
    for r in page.itertuples():
        with st.container(border=True):
            lv = f" · {r.a_level} {level_labels[r.a_level].label}" if isinstance(r.a_level, str) else ""
            st.markdown(f"**{int(r.strength)} of 24** · {band_labels[r.band].label} · {gate_text(r.gate, r.gate_basis)}"
                        f"{lv} · `{r.comment_id}`")
            st.caption(f"{levels_line(r)}  |  {sent_by(r.group_kind, r.size)}"
                       + (f" · {r.stance}" if isinstance(r.stance, str) else ""))
            with st.expander(snippet(text_of.get(r.comment_id))):
                show_text(text_of.get(r.comment_id))
                evidence(reading, ruleset, r.comment_id)


# ------------------------------------------------- one comment, as read

def comment_results(cid):
    """One comment as the analysis read it, for the Comment page: its letter,
    its stance and topics, what it names, and each reading of it with its
    evidence. Returns False when there is no such comment."""
    card = query(q.COMMENT_CARD, (cid,))
    if card.empty:
        return False
    c = card.iloc[0]
    when = " · ".join(f"{k} {str(v)[:10]}" for k, v in (("received", c["received_date"]), ("posted", c["posted_date"])) if v)
    st.markdown(f"**{cid}** · {when} · {len(c['comment_text']):,} characters")
    with st.container(border=True):
        show_text(c["comment_text"])

    st.subheader("Its letter")
    line = sent_by(c["group_kind"], c["size"])
    if isinstance(c["canonical_comment_id"], str) and c["canonical_comment_id"] != cid:
        line += f"; the group's first is `{c['canonical_comment_id']}`"
    if pd.notna(c["family_id"]):
        line += f"; text family {int(c['family_id'])}" + (" (a campaign)" if c["is_campaign"] else "")
    if isinstance(c["organisation"], str):
        line += f", run by {c['organisation']}"
    st.markdown(line)

    st.subheader("Stance and topics")
    if isinstance(c["stance"], str):
        st.markdown(f"**{c['stance']}** ({c['stance_strength']}): {c['stance_meaning'] or ''}")
        for t in query(q.COMMENT_TOPICS, (cid,)).itertuples():
            st.markdown(f"- **{t.topic}** ({t.confidence:.2f}): "
                        + "; ".join(f'"{p}"' for p in json.loads(t.supporting_phrases)))
    else:
        st.caption("not classified")

    st.subheader("What it names")
    names = query(q.COMMENT_NAMES, (cid,) * len(q.TAGS))
    if names.empty:
        st.caption("nothing, in the strict pass")
    else:
        show(names)

    st.subheader("Substance")
    st.markdown(f"screen class **{c['screen_class']}**: {SCREEN_CLASSES[c['screen_class']]}"
                if isinstance(c["screen_class"], str) else "not screened (floored, or not a survivor's representative)")
    for name, df in readings().items():
        row = df[df["comment_id"] == cid]
        if row.empty:
            continue
        r = next(row.itertuples())
        lv = f" · {r.a_level} {vocab('a_level')[r.a_level].label}" if isinstance(r.a_level, str) else ""
        st.markdown(f"**{name}**: {int(r.strength)} of 24 · {vocab('band')[r.band].label} ·"
                    f" {gate_text(r.gate, r.gate_basis)}{lv}")
        st.caption(levels_line(r))
        evidence(name, name.split("rule set ")[-1].rstrip(")") if name.startswith("rules") else None, cid)
    return True


PAGES = {
    "Overview": page_overview,
    "Stance and topics": page_stance,
    "Coordination": page_coordination,
    "Places and citations": page_places,
    "Substance": page_substance,
}
