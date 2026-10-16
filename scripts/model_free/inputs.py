"""Read-only inputs from data/roadless.sqlite: the class A comments the screen
chose (the population make score-model reads), each comment's stored text split
into its units, its confirmed citations and legal authorities, and the match
keys of every known authority.

Ported from the operator's model_free/inputs.py, which read the eis-analysis
database. Its sentences were the rows of comment_unit, written by the
comment-sentences package (stored_units); there is no such table here, so the
same package splits each comment's stored text as it is read (comment_units),
giving the same sentences. Two of its inputs do not exist in this repository
and are not read: the record's sentences and figures (record_unit), and the
sentence vectors. The Context's record sets stay empty and no ALT similarity is
measured (docs/model-free-scoring.md).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from shared import db  # noqa: E402

from comment_sentences import stored_units

from .detectors import SentenceInput
from .text import normalize, text_key

# A sentence's unit id is the comment row's rowid times this, plus its index
# from one: unique across the file, and ordered within a comment.
UNIT_STRIDE = 100_000


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
    """The population: every class A comment of the screen, as make score-model reads it."""
    ids = [r[0] for r in conn.execute(
        "SELECT comment_id FROM substance_screen WHERE screen_class = 'A' ORDER BY comment_id")]
    if not ids:
        raise SystemExit("substance_screen holds no class A comment: run make screen first")
    return ids


def comment_units(row_id: int, comment_id: str, raw: str) -> tuple[list[SentenceInput], SentenceInput] | None:
    """The comment's units for hybrid mode: its sentences as the
    comment-sentences package splits the stored text (stored_units: each
    sentence's rendered text, its span in the stored text), and the whole
    comment, normalised, as one more unit numbered the negative of its first
    sentence's, as the operator's package numbers it. None when stored_units
    keeps no sentence (every piece under 25 letters and digits): such a comment
    has no sentence to score, as it has no comment_unit row in eis-analysis."""
    kept, _dropped = stored_units(raw)
    if not kept:
        return None
    if len(kept) >= UNIT_STRIDE:
        raise SystemExit(f"{comment_id}: {len(kept):,} sentences, more than unit ids allow ({UNIT_STRIDE:,})")
    sentences = [SentenceInput(row_id * UNIT_STRIDE + i + 1, comment_id, a, b, t, text_key(t))
                 for i, (a, b, t, _kind) in enumerate(kept)]
    norm = normalize(raw)
    whole = SentenceInput(-sentences[0].unit_id, comment_id, 0, len(norm), norm, text_key(norm))
    return sentences, whole


def iter_comments(conn: db.Connection, wanted: set[str]) -> Iterator[tuple[str, tuple[list[SentenceInput], SentenceInput] | None]]:
    """Each wanted comment, by id, with its units (comment_units), or None when
    it has no sentence to score."""
    for cid in sorted(wanted):
        row = conn.execute("SELECT rowid, comment_text FROM comment WHERE comment_id = ?",
                           (cid,)).fetchone()
        if row is None or not row[1]:
            raise SystemExit(f"{cid}: no stored text in comment")
        yield cid, comment_units(int(row[0]), cid, row[1])
