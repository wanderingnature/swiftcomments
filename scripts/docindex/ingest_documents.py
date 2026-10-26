#!/usr/bin/env python3
"""Ingest the record documents into doc_* and embed their chunks.

Sources are markdown files converted from the PDFs outside the repository, one per
document, in deis/. The conversion keeps the heading levels and marks every page with a
`<!-- page N -->` line. Each document is split into sections by its heading tree (the
agency letters, one section per letter), the sections into 600-character chunks with 100
overlap, and every chunk is embedded with the embedding server of .env
(shared/embeddings.py), so a document chunk and a comment sentence compare. Every
section and chunk records the pages it spans (page_start, page_end), read from the page
markers.

Stored text and offsets are the source file's, byte for byte: start_char/end_char index
the markdown. What is SENT to the embedder is cleaned — page markers, image references and
<sup>/<sub> tags dropped, and in the USFWS Biological Assessment the ligatures its conversion
lost restored (Efect -> Effect, fsh -> fish). A chunk with nothing left after cleaning is
not stored.

deis/ is the document set. Two passes, each resumable:
  1. remove every document whose source is no longer in SOURCES; ingest every source not
     yet in doc_documents (a source whose sha256 changed is refused unless --replace,
     which deletes the document's rows first). --skip leaves a source's rows as they are
     (a document whose new conversion has not arrived);
  2. embed every doc_chunk with no doc_chunk_embeddings row for the model.

    uv run python scripts/docindex/ingest_documents.py --dry-run
    uv run python scripts/docindex/ingest_documents.py --replace \\
        --skip Draft_EIS_Volume_III_Appendix_Agency_Letters.md
"""

import argparse
import bisect
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_REPO / ".env")

from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

from shared import db, embeddings  # noqa: E402

DEFAULT_DIR = _REPO / "deis"
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
_TOC = {"contents", "list of tables", "list of figures", "table of contents", "tables",
        "figure", "figures"}

# Running page headers the converter turned into headings: never a section boundary.
# Matched against the cleaned title (_clean_title).
_BANNERS = {
    "2020_Alaska_Roadless_Rule_FEIS.md": [r"^Appendix [A-Z]$",
                                          r"^Alternatives Including the Proposed Action 2$"],
    "2023_Alaska_Roadless_Rule_Determination_Of_NEPA_Adequacy.md":
        [r"^Alaska Roadless Rule Repeal$"],
}
_LIGATURES = [(re.compile(r"\b([Ee])fect"), r"\1ffect"),
              (re.compile(r"\b([Aa])fect"), r"\1ffect"),
              (re.compile(r"\b([Ff])sh"), r"\1ish")]
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_SUP_RE = re.compile(r"</?su[bp]>")     # <sup> and <sub> tags; their text stays
# `<!-- page N -->`, or `<!-- page N label="…" -->` when a PDF defines page labels: N,
# the 1-based PDF page, is the page recorded; a label is ignored.
_PAGE_RE = re.compile(r"<!-- page (\d+)(?: [^>]*)? -->")
_SUP_BLOCK_RE = re.compile(r"<sup>.*?</sup>")
_TAG_RE = re.compile(r"<[^>]+>")


# --------------------------------------------------------------------------- segmenters
# Each returns [{"heading_path": [...], "kind": str, "start": int, "end": int}], covering
# the text in order; text before the first boundary is a "front" section.

def _clean_title(title):
    """A heading's words: footnote marks, inline tags (<mark>, <u>), bold and outer
    italics removed."""
    t = _TAG_RE.sub("", _SUP_BLOCK_RE.sub("", title)).replace("**", "")
    return re.sub(r"\s+", " ", t).strip(" _")


def _headings(text, banners=()):
    """(level, title, offset) of every heading that is not page furniture; titles
    cleaned."""
    out, pos = [], 0
    for line in text.splitlines(keepends=True):
        m = _HEADING_RE.match(line.rstrip("\n"))
        if m:
            title = _clean_title(m.group(2))
            if title and not any(re.search(b, title) for b in banners):
                out.append((len(m.group(1)), title, pos))
        pos += len(line)
    return out


def _close(bounds, total):
    """bounds: [(start, heading_path, kind)] -> sections with ends."""
    secs = []
    for i, (start, path, kind) in enumerate(bounds):
        end = bounds[i + 1][0] if i + 1 < len(bounds) else total
        secs.append({"heading_path": path, "kind": kind, "start": start, "end": end})
    return secs


def _front(text, bounds):
    if not bounds or bounds[0][0] > 0:
        first = bounds[0][0] if bounds else len(text)
        if _PAGE_RE.sub("", text[:first]).strip():     # a page marker alone is not front matter
            return [(0, ["(front matter)"], "front")]
    return []


def seg_headings(text, banners=()):
    """The heading tree: each heading opens a section whose path is the headings above
    it by level (a heading closes every open heading at its level or deeper)."""
    bounds, stack = [], []
    for level, title, pos in _headings(text, banners):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        kind = "toc" if title.lower() in _TOC else "body"
        bounds.append((pos, [t for _, t in stack], kind))
    bounds = _front(text, bounds) + bounds
    if bounds and bounds[0][0] > 0:
        # Only page markers precede the first heading: its section starts at 0.
        bounds[0] = (0,) + bounds[0][1:]
    return _close(bounds, len(text))


_RE_LINE = re.compile(r"^(RE:|Re:|RE\s*:|Subject:|SUBJECT:)")
_DEAR = re.compile(r"^(Dear\b|To whom it (may )?concern)", re.I)
_RESOLUTION = re.compile(r"^(A RESOLUTION\b|RESOLUTION\b)")
_CLOSING = re.compile(r"^(Sincerely|Respectfully|Regards|Best regards|Thank you|"
                      r"With appreciation|Very truly|Yours)\b", re.I)
SALUTATION_GAP = 30


def _anchor_text(line):
    """The line with a level-1/2 heading marker removed: the converter made some RE:
    and salutation lines headings."""
    return re.sub(r"^#{1,2}\s+", "", line.strip())


def seg_letters(text, banners=()):
    """Agency letters: one section per letter.

    The volume's own introduction and contents run to its first level-1 heading. A letter
    opens with an RE:/Subject: line, a salutation or a resolution heading, and a new one
    starts at such a line when the current letter has
      - closed (a "Sincerely,"-type line of at most 80 characters), or
      - already had its salutation and this is an RE:/Subject: line (a letter's RE:
        comes before its salutation), or
      - already had its salutation and this is another one more than SALUTATION_GAP
        lines later — the scan lost the closing, or the signature was an image.
    The start moves back to the first level-1 heading (the scanned letterhead) since the
    previous letter closed. Level-2 headings that are not RE:/salutation lines — signature
    blocks ("FOR THE STATE OF WASHINGTON"), attachments ("References:") — stay inside the
    letter. The title is the letterhead and the opening line."""
    lines = text.splitlines(keepends=True)
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln)
    first_h1 = next((i for i, ln in enumerate(lines) if ln.startswith("# ")), None)
    if first_h1 is None:
        raise RuntimeError("agency letters: no level-1 heading — cannot find the first letter")
    bounds, n = [], 0
    closed, letterhead, last_dear = True, None, None
    for i in range(first_h1, len(lines)):
        a = _anchor_text(lines[i])
        is_re, is_dear, is_res = (bool(_RE_LINE.match(a)), bool(_DEAR.match(a)),
                                  bool(_RESOLUTION.match(a)))
        if lines[i].startswith("# ") and letterhead is None:
            letterhead = i
        if not closed and last_dear is not None and (
                is_re or (is_dear and i - last_dear > SALUTATION_GAP)):
            closed = True
        if closed and (is_re or is_dear or is_res):
            n += 1
            start = letterhead if letterhead is not None and letterhead <= i else i
            head = _anchor_text(lines[start]) if start != i else ""
            title = f"{head} — {a}" if head and head != a else a
            bounds.append((offs[start], [f"Letter {n}: {title[:200]}"], "letter"))
            closed, letterhead = False, None
            last_dear = i if is_dear else None
        elif not closed and is_dear:
            last_dear = i
        elif len(a) <= 80 and _CLOSING.match(a):
            closed, letterhead = True, None
    if not bounds or bounds[0][0] != offs[first_h1]:
        raise RuntimeError("agency letters: the first letter does not start at the first"
                           " level-1 heading — the rule does not fit this volume")
    intro = seg_headings(text[:offs[first_h1]])
    for sec in intro:
        sec["kind"] = "toc" if sec["kind"] == "toc" else "front"
    return intro + _close(bounds, len(text))


SOURCES = [
    ("Draft_EIS_Volume_I.md", "Draft EIS Volume I", seg_headings),
    ("Draft_EIS_Volume_III_Appendix_Agency_Letters.md",
     "Draft EIS Volume III: Federal, State, and Local Agency Letters", seg_letters),
    ("Draft_Biological_Assessment_USFWS_Species.md",
     "Draft Biological Assessment: USFWS Species", seg_headings),
    ("Draft_Biological_Assessment_NMFS_Species.md",
     "Draft Biological Assessment: NMFS Species", seg_headings),
    ("Economic_Analysis_RFAandCBA.md",
     "Cost Benefit Analysis and Consideration of Impacts on Small Entities", seg_headings),
    ("Tribal-Summary-Impact-Statement.md", "Tribal Summary Impact Statement", seg_headings),
    ("FS-2025-0001-0001_NOI.md",
     "Notice of Intent to Prepare an EIS (FS-2025-0001-0001)", seg_headings),
    ("FS-2025-0001-223869_content.md",
     "Proposed Rule: Rescission of the 2001 Roadless Rule", seg_headings),
    ("2020_Alaska_Roadless_Rule_FEIS.md",
     "2020 Alaska Roadless Rule Final EIS", seg_headings),
    ("2023_Alaska_Roadless_Rule_Determination_Of_NEPA_Adequacy.md",
     "2023 Alaska Roadless Rule Repeal: Determination of NEPA Adequacy", seg_headings),
    # The orders and the memorandum the NOI cites as the action's policy basis.
    ("sm-1078-006.md",
     "Secretary's Memorandum 1078-006: Increasing Timber Production and Designating an"
     " Emergency Situation on National Forest System Lands", seg_headings),
    ("eo-14153.md", "Executive Order 14153: Unleashing Alaska's Extraordinary Resource Potential",
     seg_headings),
    ("eo-14154.md", "Executive Order 14154: Unleashing American Energy", seg_headings),
    ("eo-14192.md", "Executive Order 14192: Unleashing Prosperity Through Deregulation",
     seg_headings),
    ("eo-14225.md", "Executive Order 14225: Immediate Expansion of American Timber Production",
     seg_headings),
]


def page_marks(source_file, text):
    """[(offset, page)] of every `<!-- page N -->` marker, in order. A source without
    them cannot say where a passage is, so it is refused."""
    marks = [(m.start(), int(m.group(1))) for m in _PAGE_RE.finditer(text)]
    if not marks:
        raise SystemExit(f"{source_file}: no <!-- page N --> markers — not the paged"
                         " conversion")
    return marks


def page_at(marks, pos):
    """The page holding character `pos`: the last marker at or before it (text before
    the first marker is on the first marker's page)."""
    i = bisect.bisect_right([o for o, _ in marks], pos) - 1
    return marks[max(i, 0)][1]


_EDGE = r"(?:\s|<!-- page \d+(?: [^>]*)? -->)*"
_LEAD_RE = re.compile(r"\A" + _EDGE)
_TRAIL_RE = re.compile(_EDGE + r"\Z")


def page_span(marks, text, start, end):
    """(page_start, page_end) of the text [start, end): the pages of its first and last
    characters that are not whitespace or a page marker — a chunk that ends on the next
    page's marker has not reached that page."""
    piece = text[start:end]
    lead = _LEAD_RE.match(piece)
    trail = _TRAIL_RE.search(piece)
    a = start + (lead.end() if lead else 0)
    b = start + (trail.start() if trail else len(piece))
    if b <= a:                      # nothing but markers and whitespace
        a, b = start, end
    return page_at(marks, a), page_at(marks, max(a, b - 1))


def embed_text(source_file, chunk):
    """What the embedder is sent for a chunk: page markers, images and <sup>/<sub> tags
    dropped, and the USFWS BA's lost ligatures restored."""
    t = _SUP_RE.sub("", _IMAGE_RE.sub("", _PAGE_RE.sub("", chunk)))
    if source_file == "Draft_Biological_Assessment_USFWS_Species.md":
        for rx, rep in _LIGATURES:
            t = rx.sub(rep, t)
    return t.strip()


_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", ", ", " ", ""])


def chunk_section(source_file, text, sec):
    """[(chunk_text, start, end)] with offsets into the source file; toc sections and
    chunks with no embeddable text are skipped."""
    if sec["kind"] == "toc":
        return []
    body = text[sec["start"]:sec["end"]]
    out, search = [], 0
    for piece in _SPLITTER.split_text(body):
        at = body.find(piece, search)
        if at == -1:
            raise RuntimeError(f"{source_file}: chunk not found in its section: {piece[:60]!r}")
        search = at + 1
        if embed_text(source_file, piece):
            out.append((piece, sec["start"] + at, sec["start"] + at + len(piece)))
    return out


def plan(src_dir, skip=()):
    """Every source not skipped: (file, title, text, sha, sections, chunks per section,
    page marks)."""
    on_disk = {p.name for p in src_dir.glob("*.md")}
    listed = {f for f, _, _ in SOURCES}
    if set(skip) - listed:
        raise SystemExit(f"--skip names no source: {sorted(set(skip) - listed)}")
    if on_disk - listed:
        raise SystemExit(f"{src_dir} has documents with no segmentation rule:"
                         f" {sorted(on_disk - listed)} — add them to SOURCES.")
    if listed - on_disk - set(skip):
        raise SystemExit(f"missing from {src_dir}: {sorted(listed - on_disk - set(skip))}")
    out = []
    for fname, title, seg in SOURCES:
        if fname in skip:
            continue
        text = (src_dir / fname).read_text(encoding="utf-8")
        marks = page_marks(fname, text)
        secs = seg(text, _BANNERS.get(fname, ()))
        out.append((fname, title, text, hashlib.sha256(text.encode()).hexdigest(), secs,
                    [chunk_section(fname, text, s) for s in secs], marks))
    return out


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def prune(conn):
    """Delete every document whose source is no longer in SOURCES — its sections,
    chunks and embeddings go with it (ON DELETE CASCADE)."""
    listed = [f for f, _, _ in SOURCES]
    marks = ",".join("?" * len(listed))
    gone = conn.execute(
        f"DELETE FROM doc_documents WHERE source_file NOT IN ({marks})"
        " RETURNING source_file, title", listed).fetchall()
    conn.commit()
    for fname, title in gone:
        print(f"  {fname}: removed — no longer a source ({title})")


def ingest(conn, docs, replace):
    for fname, title, text, sha, secs, chunks, marks in docs:
        row = conn.execute(
            "SELECT document_id, sha256 FROM doc_documents WHERE source_file = ?",
            (fname,)).fetchone()
        if row and row[1] == sha:
            print(f"  {fname}: already ingested")
            continue
        if row and not replace:
            raise SystemExit(f"{fname} changed since it was ingested (sha256 {row[1][:12]}"
                             f" -> {sha[:12]}); --replace deletes its rows and re-ingests.")
        if row:
            conn.execute("DELETE FROM doc_documents WHERE document_id = ?", (row[0],))
        doc_id = conn.execute(
            "INSERT INTO doc_documents (title, source_file, sha256, n_chars, ingested_at)"
            " VALUES (?, ?, ?, ?, ?) RETURNING document_id",
            (title, fname, sha, len(text), _now())).fetchone()[0]
        n_chunks = 0
        for ordinal, (sec, sec_chunks) in enumerate(zip(secs, chunks)):
            sid = conn.execute(
                "INSERT INTO doc_sections (document_id, ordinal, heading_path,"
                " kind, start_char, end_char, section_text, page_start, page_end)"
                " VALUES (?,?,?,?,?,?,?,?,?) RETURNING section_id",
                (doc_id, ordinal, json.dumps(sec["heading_path"]), sec["kind"], sec["start"],
                 sec["end"], text[sec["start"]:sec["end"]],
                 *page_span(marks, text, sec["start"], sec["end"]))).fetchone()[0]
            conn.executemany(
                "INSERT INTO doc_chunks (section_id, chunk_index, chunk_text,"
                " start_char, end_char, max_chunk_size, chunk_overlap, page_start,"
                " page_end) VALUES (?,?,?,?,?,?,?,?,?)",
                [(sid, i, c, a, b, CHUNK_SIZE, CHUNK_OVERLAP,
                  *page_span(marks, text, a, b))
                 for i, (c, a, b) in enumerate(sec_chunks)])
            n_chunks += len(sec_chunks)
        conn.commit()
        print(f"  {fname}: {len(secs)} sections, {n_chunks} chunks")


def embed(conn, base, key, model):
    todo = conn.execute("""
        SELECT ch.chunk_id, ch.chunk_text, d.source_file
        FROM doc_chunks ch
        JOIN doc_sections s ON s.section_id = ch.section_id
        JOIN doc_documents d ON d.document_id = s.document_id
        WHERE NOT EXISTS (SELECT 1 FROM doc_chunk_embeddings e
                          WHERE e.chunk_id = ch.chunk_id AND e.embedding_model = ?)
        ORDER BY ch.chunk_id
    """, (model,)).fetchall()
    print(f"Embedding {len(todo)} chunks with {model}")
    texts = [embed_text(f, t) for _, t, f in todo]
    batches = [(i, todo[i:i + embeddings.BATCH]) for i in range(0, len(todo), embeddings.BATCH)]
    done = tokens = 0
    # Each request's vectors are saved as the request returns, so a failed run
    # keeps every vector it paid for.
    with ThreadPoolExecutor(embeddings.concurrency()) as ex:
        results = ex.map(lambda b: embeddings.embed_batch(texts[b[0]:b[0] + len(b[1])],
                                                          base, key, model), batches)
        for (_, part), (X, tok) in zip(batches, results):
            conn.executemany(
                "INSERT INTO doc_chunk_embeddings (chunk_id, embedding,"
                " embedding_model, embedding_dimensions, created_at) VALUES (?,?,?,?,?)",
                [(cid, pack(x), model, embeddings.DIMENSIONS, _now())
                 for (cid, _, _), x in zip(part, X)])
            conn.commit()
            done += len(part)
            tokens += tok
            print(f"  {done}/{len(todo)} ({tokens:,} input tokens reported)", flush=True)


def pack(vector) -> bytes:
    """The vector as sentence_embedding stores one: 1,024 little-endian float32."""
    v = np.asarray(vector, dtype="<f4")
    if v.shape != (embeddings.DIMENSIONS,):
        raise ValueError(f"a vector of {v.shape} where {embeddings.DIMENSIONS} were expected")
    return v.tobytes()


def main():
    p = argparse.ArgumentParser(
        description="Ingest the record documents into doc_* and embed their chunks")
    p.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="Source markdown directory")
    p.add_argument("--replace", action="store_true",
                   help="Re-ingest a source whose sha256 changed (deletes its rows first)")
    p.add_argument("--skip", action="append", default=[], metavar="FILE",
                   help="Leave this source's rows as they are (repeatable): a document whose"
                        " new conversion has not arrived")
    p.add_argument("--dry-run", action="store_true",
                   help="Segment and chunk, print the counts, write nothing")
    args = p.parse_args()

    docs = plan(args.dir, args.skip)
    for fname, _, text, _, secs, chunks, marks in docs:
        kinds = {}
        for s in secs:
            kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
        print(f"{fname}: {len(text):,} chars, pages {marks[0][1]}-{marks[-1][1]},"
              f" {len(secs)} sections {kinds}, {sum(map(len, chunks))} chunks")
    if args.dry_run:
        return
    base, key, model = embeddings.server()
    conn = db.connect(db.DB_PATH)
    prune(conn)
    ingest(conn, docs, args.replace)
    embed(conn, base, key, model)
    conn.close()


if __name__ == "__main__":
    main()
