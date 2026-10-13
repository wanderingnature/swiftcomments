"""Read-only inputs from data/roadless.sqlite: the class A comments the screen
chose (the population make score reads), each comment's stored text, its
confirmed citations and legal authorities, and the match keys of every known
authority.

Ported from the operator's model_free/inputs.py, which read the rtca database.
Three of its inputs do not exist in this repository and are not read: the
sentence table (comment_unit; the whole comment is the unit here), the
record's sentences and figures (record_unit), and the sentence vectors. The
Context's record sets stay empty and no ALT similarity is measured
(docs/model-free-scoring.md).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from shared import db  # noqa: E402

from .detectors import SentenceInput
from .text import normalize, text_key


def connect() -> db.Connection:
    return db.connect(db.DB_PATH)


@dataclass
class CommentTags:
    citations: dict[str, list[str]]
    authorities: dict[str, list[str]]


def load_tags(conn: db.Connection) -> CommentTags:
    citations: dict[str, list[str]] = {}
    for cid, mt in conn.execute("SELECT comment_id, matched_text FROM comment_cited_references"):
        citations.setdefault(cid, []).append(mt)
    authorities: dict[str, list[str]] = {}
    for cid, mt in conn.execute("SELECT comment_id, matched_text FROM comment_authorities"):
        authorities.setdefault(cid, []).append(mt)
    return CommentTags(citations, authorities)


def load_authority_keys(conn: db.Connection) -> list[str]:
    out: list[str] = []
    for (keys,) in conn.execute("SELECT match_keys FROM legal_authority WHERE match_keys IS NOT NULL"):
        for k in str(keys).split("|"):
            k = k.strip()
            if k:
                out.append(k)
    return out


def comment_ids(conn: db.Connection) -> list[str]:
    """The population: every class A comment of the screen, as make score reads it."""
    ids = [r[0] for r in conn.execute(
        "SELECT comment_id FROM substance_screen WHERE screen_class = 'A' ORDER BY comment_id")]
    if not ids:
        raise SystemExit("substance_screen holds no class A comment: run make screen first")
    return ids


def iter_comments(conn: db.Connection, wanted: set[str]) -> Iterator[SentenceInput]:
    """Each wanted comment as one unit: its stored text normalised, offsets 0 to
    its length, the comment row's rowid as the unit id (there is no sentence
    table to number from)."""
    for cid in sorted(wanted):
        row = conn.execute("SELECT rowid, comment_text FROM comment WHERE comment_id = ?",
                           (cid,)).fetchone()
        if row is None or not row[1]:
            raise SystemExit(f"{cid}: no stored text in comment")
        text = normalize(row[1])
        yield SentenceInput(int(row[0]), cid, 0, len(text), text, text_key(text), None)
