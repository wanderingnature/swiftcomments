"""The console: a read-only Streamlit app over data/roadless.sqlite (new; plan 10,
2026-10-12). Five pages: Steps (what every make target has written), Comment (one
comment across every table), Compare (every make score-model-compare run, and any
two readings of any two runs side by side), Tables (any table or view, paged) and
Query (SQL, read-only). It launches nothing: the steps run from make. The connection is
opened with PRAGMA query_only, so nothing here can write the file, and reading
while a step writes is safe under WAL.

    make console            (uv run --group console streamlit run console/app.py)
"""
import contextlib
import datetime
import io
import json
import os
import sqlite3
import sys

import pandas as pd
import streamlit as st

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from shared import db, score_json  # noqa: E402
from console.queries import COMMENT, COMPARE_READINGS, COMPARE_RUNS, STEPS, TABLES  # noqa: E402

ATTACHMENTS_DIR = os.path.join(_REPO_ROOT, "attachments")
PAGE_ROWS = 100         # the Tables page's page
QUERY_ROWS = 10000      # the most rows the Query page fetches


def open_db():
    """The file, read-only. db.DB_PATH is looked up at call time so the test can
    point it at a temporary file."""
    try:
        conn = db.connect(db.DB_PATH)
    except SystemExit as exc:
        st.error(str(exc))
        st.stop()
    conn.execute("PRAGMA query_only = 1")
    return contextlib.closing(conn)


def frame(conn, sql, params=()):
    """A query as a DataFrame with the cursor's column names, so an empty result
    still shows its columns."""
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    return pd.DataFrame([tuple(r) for r in rows], columns=[d[0] for d in cur.description])


def scalar(conn, sql):
    try:
        return conn.execute(sql).fetchone()[0]
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return None
        raise


def show(df):
    st.dataframe(df, hide_index=True, width="stretch")


# ------------------------------------------------------------------ pages

def page_steps():
    st.header("Steps")
    st.caption("Every make target in run order, with the rows it has written. A step that"
               " has written nothing says so. Reload the page for current counts.")
    with open_db() as conn:
        for step in STEPS:
            figures = [(label, scalar(conn, sql)) for label, sql in step["figures"]]
            if step["target"] == "fetch":
                n_files = sum(len(files) for _, _, files in os.walk(ATTACHMENTS_DIR))
                figures = [("files under attachments/", n_files)]
            written = any(v for _, v in figures)
            st.subheader(f"make {step['target']}")
            st.caption(step["what"])
            if not written:
                st.text("not run: nothing written yet")
                continue
            show(pd.DataFrame(
                [(label, "no table yet" if v is None else f"{v:,}") for label, v in figures],
                columns=["figure", "rows"]))
            for label, sql in step["breakdowns"]:
                st.text(label)
                show(frame(conn, sql))


def page_comment():
    st.header("Comment")
    comment_id = st.text_input("comment id", placeholder="FS-2025-0001-0002").strip()
    if not comment_id:
        return
    with open_db() as conn:
        row = conn.execute("SELECT * FROM comment WHERE comment_id = ?", (comment_id,)).fetchone()
        if row is None:
            st.error(f"no comment {comment_id}")
            return
        st.text(f"{row['comment_id']}  posted {row['posted_date']}  received {row['received_date']}"
                f"  {len(row['comment_text']):,} characters"
                + ("  WITHDRAWN" if row["withdrawn"] else ""))
        st.text(row["comment_text"])
        for title, sql in COMMENT:
            df = frame(conn, sql, (comment_id,) * sql.count("?"))
            st.subheader(title)
            if df.empty:
                st.text("no row")
            else:
                show(df)


def readings(conn, run_id, method):
    """One run's kept readings by one method, by comment id."""
    return {r["comment_id"]: json.loads(r["record"]) for r in conn.execute(COMPARE_READINGS, (run_id,))
            if r["method"] == method and r["record"] is not None}


def show_comparison(conn, a, b, labels):
    """Two sets of readings side by side, as tables: per dimension; the gate,
    band and strength; then every comment that differs, gate first, each one
    opening to its text and its eight dimensions with both sides' evidence."""
    la, lb = labels
    both = sorted(set(a) & set(b))
    st.text(f"both read {len(both):,}; only {la} {len(set(a) - set(b)):,}; only {lb} {len(set(b) - set(a)):,}")
    if not both:
        return
    show(pd.DataFrame(score_json.dimension_rows(a, b, labels)))
    n = len(both)
    show(pd.DataFrame([
        {"measure": "gate open", la: sum(1 for c in both if a[c]["gate"]), lb: sum(1 for c in both if b[c]["gate"]),
         "same": sum(1 for c in both if a[c]["gate"] == b[c]["gate"]), "of": n},
        {"measure": "all eight levels", la: None, lb: None,
         "same": sum(1 for c in both if a[c]["levels"] == b[c]["levels"]), "of": n},
        {"measure": "band", la: None, lb: None,
         "same": sum(1 for c in both if a[c]["band"] == b[c]["band"]), "of": n},
        {"measure": "strength (mean)", la: round(sum(a[c]["strength"] for c in both) / n, 2),
         lb: round(sum(b[c]["strength"] for c in both) / n, 2),
         "same": sum(1 for c in both if a[c]["strength"] == b[c]["strength"]), "of": n},
    ]))
    gate, level = score_json.differing(a, b)
    st.text(f"comments that differ: {len(gate):,} on the gate, {len(level):,} more on a level")
    rows = []
    for c in gate + level:
        rows.append({"comment_id": c, "differs on": "gate" if c in gate else "level",
                     f"{la} gate": score_json.gate_text(a[c]), f"{lb} gate": score_json.gate_text(b[c]),
                     f"{la} strength": a[c]["strength"], f"{lb} strength": b[c]["strength"],
                     "levels that differ": " ".join(f"{d} {a[c]['levels'][d]}/{b[c]['levels'][d]}"
                                                    for d in score_json.DIMS
                                                    if a[c]["levels"][d] != b[c]["levels"][d])})
    if rows:
        show(pd.DataFrame(rows))
    for c in gate + level:
        with st.expander(f"{c}: {la} {score_json.gate_text(a[c])}, {lb} {score_json.gate_text(b[c])}"):
            text = conn.execute("SELECT comment_text FROM comment WHERE comment_id = ?", (c,)).fetchone()
            st.text(text[0] if text else "no comment row")
            show(pd.DataFrame(score_json.comment_rows(a[c], b[c], labels)))
            for side, rec in ((la, a[c]), (lb, b[c])):
                for line in score_json.evidence_by_dimension(rec)[1]:
                    st.text(f"{side}: {line}")


def page_compare():
    st.header("Compare")
    st.caption("Every make score-model-compare run, newest first, stamped with the code it ran."
               " Below: one run's two readings side by side; then any two readings of any two runs"
               " side by side on the comments both read, so a change to the code, the rules or the"
               " model shows against what an earlier run read.")
    with open_db() as conn:
        try:
            runs = frame(conn, COMPARE_RUNS)
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc):
                st.text("no score_compare_run table: the file predates schema section 9c")
                return
            raise
        if runs.empty:
            st.text("no comparison run yet: make score-model-compare LIMIT=N")
            return
        show(runs)
        ids = list(runs["run_id"])

        st.subheader("One run: the model against the rules")
        run_id = st.selectbox("run", ids, key="one_run")
        errors = [r for r in conn.execute(COMPARE_READINGS, (run_id,)) if r["error"]]
        for r in errors:
            st.text(f"{r['comment_id']} {r['method']} failed: {r['error']}")
        show_comparison(conn, readings(conn, run_id, "model"), readings(conn, run_id, "model-free"),
                        ("model", "rules"))

        st.subheader("Two readings: any run, either method")
        methods = ["model", "model-free"]
        left, right = st.columns(2)
        a_run = left.selectbox("A: run", ids, index=min(1, len(ids) - 1), key="a_run")
        a_method = left.selectbox("A: reading", methods, key="a_method")
        b_run = right.selectbox("B: run", ids, key="b_run")
        b_method = right.selectbox("B: reading", methods, index=1, key="b_method")
        a, b = readings(conn, a_run, a_method), readings(conn, b_run, b_method)
        st.text(f"A: run {a_run}, {a_method}    B: run {b_run}, {b_method}")
        if not a or not b:
            st.text("one side holds no reading")
            return
        show_comparison(conn, a, b, ("A", "B"))


def page_tables():
    st.header("Tables")
    with open_db() as conn:
        objects = conn.execute(TABLES).fetchall()
        names = [f"{r['name']} ({r['type']})" for r in objects]
        pick = st.selectbox("table or view", names)
        if not pick:
            return
        obj = objects[names.index(pick)]
        name = obj["name"]
        if obj["type"] == "table":
            n = scalar(conn, f'SELECT count(*) FROM "{name}"')
            st.text(f"{n:,} rows")
        else:
            n = None
            st.text("a view; not counted (some views walk the whole file)")
        offset = st.number_input("from row", min_value=0, step=PAGE_ROWS, value=0)
        show(frame(conn, f'SELECT * FROM "{name}" LIMIT ? OFFSET ?', (PAGE_ROWS, int(offset))))
        if n is not None:
            st.caption(f"rows {offset:,} to {min(int(offset) + PAGE_ROWS, n):,} of {n:,}")


def page_query():
    st.header("Query")
    st.caption(f"Read-only. The first {QUERY_ROWS:,} rows are shown; the download has the same rows.")
    sql = st.text_area("SQL", height=160,
                       placeholder="SELECT group_kind, count(*) FROM comment_group GROUP BY 1")
    if not st.button("Run") or not sql.strip():
        return
    with open_db() as conn:
        try:
            cur = conn.execute(sql)
            rows = cur.fetchmany(QUERY_ROWS)
            more = cur.fetchone() is not None
        except sqlite3.Error as exc:
            st.error(str(exc))
            return
        if cur.description is None:
            st.text("the statement returned no rows")
            return
        df = pd.DataFrame([tuple(r) for r in rows], columns=[d[0] for d in cur.description])
    st.text(f"{len(df):,} rows" + (f" shown; the result has more than {QUERY_ROWS:,}" if more else ""))
    show(df)
    st.download_button("Download CSV", df.to_csv(index=False), "query.csv", "text/csv")


PAGES = {
    "Steps": page_steps,
    "Comment": page_comment,
    "Compare": page_compare,
    "Tables": page_tables,
    "Query": page_query,
}


def file_status():
    path = db.DB_PATH
    if not os.path.exists(path):
        return f"{path}: no file; run make schema"
    size = os.path.getsize(path) / 1e9
    modified = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
    wal = f"{path}-wal"
    wal_mb = os.path.getsize(wal) / 1e6 if os.path.exists(wal) else 0
    return (f"{path}\n{size:.2f} GB, modified {modified}\n"
            f"write-ahead log {wal_mb:.0f} MB" + (" (a step is writing, or has not checkpointed)" if wal_mb else ""))


def main():
    st.set_page_config(page_title="swiftcomments", layout="wide")
    st.sidebar.title("swiftcomments")
    page = st.sidebar.radio("page", list(PAGES), label_visibility="collapsed")
    st.sidebar.text(file_status())
    PAGES[page]()


if __name__ == "__main__":
    main()
