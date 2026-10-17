"""What every console page shares: the file opened read-only, a query as a
DataFrame, the results pages' cached queries, the vocabulary's labels, and a
comment's text shown as prose.
"""
import contextlib
import html
import os
import re
import sqlite3

import pandas as pd
import streamlit as st

from shared import db


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


def show(df, **kwargs):
    st.dataframe(df, hide_index=True, width="stretch", **kwargs)


def file_signature():
    """The file's path and the modification times of it and its write-ahead log:
    a cached result is read again as soon as a step writes."""
    path = str(db.DB_PATH)
    return (path,) + tuple(os.path.getmtime(p) if os.path.exists(p) else 0
                           for p in (path, f"{path}-wal"))


@st.cache_data(show_spinner="reading the file", max_entries=500)
def _cached(sql, params, signature):
    with open_db() as conn:
        return frame(conn, sql, params)


def query(sql, params=()):
    """A results page's query, cached until the file changes: the results pages
    aggregate the whole corpus, and a rerun of the page should not do it again."""
    return _cached(sql, tuple(params), file_signature())


def vocab(kind):
    """The vocabulary's rows of one kind, by code: label, meaning, ordinal, lo, hi."""
    df = query("SELECT code, label, meaning, ordinal, lo, hi FROM vocabulary WHERE kind = ? ORDER BY ordinal",
               (kind,))
    return {r.code: r for r in df.itertuples(index=False)}


def clean_comment(text):
    """Comment text as prose: <br> and <p> as line breaks, other tags out,
    entities decoded (rtca services/text_clean.py)."""
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"(?i)<br\s*/?>", "\n", t)
    t = re.sub(r"(?i)</p\s*>", "\n\n", t)
    t = re.sub(r"(?i)<p[^>]*>", "", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


_MARKDOWN = re.compile(r"([\\`*_{}\[\]<>()#+\-.!|~$:])")


def show_text(text):
    """A comment's text as it reads: cleaned, every Markdown character escaped,
    so nothing the commenter typed is taken as formatting, and its line breaks
    kept."""
    body = _MARKDOWN.sub(r"\\\1", clean_comment(text))
    st.markdown(body.replace("\n", "  \n") if body else "(no text)")
