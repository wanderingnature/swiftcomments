#!/usr/bin/env python3
"""Run one entity-tagging pass (strict or loose) over a project's comments.

Design: docs/design/comment-entity-tagging.md.

- strict: Aho-Corasick over lowercased raw text (exact vocabulary, word-boundary
  guarded, longest-match-wins per entity type), plus the deterministic detectors:
  legal-citation regexes (discovering authorities not in the seed), DOI regex
  (discovering references not in the seed), and zip tri-match ("Brevard, NC 28712",
  tried before the bare-zip pattern).
- loose: spaCy blank tokenizer + PhraseMatcher on LOWER (no models) over the same
  vocabulary — tokenizer-aware recall; gazetteer types only.

Each mode keeps its own queue (entity_scan_state.is_tagged_<mode> IS NULL), writes
everything it finds (no cross-mode dedup — the mode column is the provenance), and
marks every scanned comment whether or not anything matched. Same-mode re-runs are
idempotent via the tag tables' UNIQUE constraints.

Usage:
    python scripts/entity_tagging/run_pass.py --project roadless --mode strict
"""

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared import db  # noqa: E402
from shared.project_context import ProjectContext, add_project_argument, context_from_args  # noqa: E402

# Tag table + value column per gazetteer entity type.
TAG_SPECS = {
    "forests": ("comment_forests", "forest_name"),
    "areas": ("comment_areas", "area_name"),
    "species": ("comment_species", "species_name"),
    "authorities": ("comment_authorities", "citation"),
    "cited_references": ("comment_cited_references", "citation_key"),
}

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC", "PR",
}

# Zip: tri-match first (one signature line = one tag, city+state captured), then bare.
TRI_RE = re.compile(
    r"\b([A-Z][A-Za-z.'\-]+(?: [A-Z][A-Za-z.'\-]+){0,3}),\s*([A-Z]{2})\s+(\d{5})(?:-\d{4})?\b")
BARE_ZIP_RE = re.compile(r"(?<![\w-])(\d{5})(?:-\d{4})?(?![\w-])")

DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"<>)\],;]+", re.IGNORECASE)

# Structural legal-citation detectors, each with the authority type it implies.
CITATION_RES = [
    (re.compile(r"\b\d{1,3}\s+C\.?\s?F\.?\s?R\.?,?\s*(?:§+\s*|[Ss]ections?\s+|[Ss]ec\.?\s+"
                r"|[Pp]arts?\s+|[Pp]t\.?\s+)?"
                r"\d+(?:\.\d+)?[a-z]?\b"), "regulation"),
    (re.compile(r"\b\d{1,3}\s+U\.?\s?S\.?\s?C\.?\s*(?:§+\s*|[Ss]ections?\s+|[Ss]ec\.?\s+)?"
                r"\d+[a-z]?(?:\([a-zA-Z0-9]+\))*\b"), "statute"),
    (re.compile(r"\b\d{1,4}\s+(?:U\.S\.|S\.\s?Ct\.|F\.\s?(?:2d|3d|4th)|"
                r"F\.\s?Supp\.(?:\s?2d|\s?3d)?)\s+\d{1,5}\b"), "case"),
    (re.compile(r"\b\d{1,3}\s+Fed\.?\s?Reg\.?\s+\d{1,6}\b", re.IGNORECASE), "regulation"),
    (re.compile(r"\b(?:Executive\s+Order|E\.?\s?O\.?)\s*(?:No\.?\s*)?\d{4,5}\b",
                re.IGNORECASE), "executive_order"),
]


def forest_abbrev(name: str):
    """The NF/NFs surface form for a canonical forest name (None where N/A)."""
    if name.endswith(" National Forests"):
        return name[: -len(" National Forests")] + " NFs"
    if name.endswith(" National Forest"):
        return name[: -len(" National Forest")] + " NF"
    return None


def build_vocabulary(cur) -> dict:
    """Per entity type: {lowercased pattern: set of canonical values}, straight from
    the reference tables (discovered authority/reference rows have no match_keys and
    are naturally excluded). Also returns the DOI -> seed citation_key map."""
    vocab = {t: defaultdict(set) for t in TAG_SPECS}

    cur.execute("SELECT name FROM {analysis}.forests")
    for (name,) in cur.fetchall():
        vocab["forests"][name.lower()].add(name)
        ab = forest_abbrev(name)
        if ab:
            vocab["forests"][ab.lower()].add(name)

    # Single-word area names are ambiguous English words in comment prose
    # ("Security", "Dry", "Johnson", "Lake") — bare, they stay out of the
    # vocabulary. Context-gated forms are unambiguous and match instead:
    # "Security roadless area" resolves to the area name, with the cue phrase
    # preserved in matched_text. High-confidence bare names can still be
    # promoted to plain aliases later (design: aliases earned through
    # iteration; scripts/entity_tagging/bare_word_review.py is the evidence).
    cur.execute("SELECT DISTINCT name FROM {analysis}.roadless_areas")
    for (name,) in cur.fetchall():
        if " " in name.strip():
            vocab["areas"][name.lower()].add(name)
        else:
            for cue in (" roadless area", " inventoried roadless area"):
                vocab["areas"][name.lower() + cue].add(name)

    cur.execute("SELECT primary_common_name, scientific_name FROM {analysis}.species")
    for common, scientific in cur.fetchall():
        vocab["species"][common.lower()].add(common)
        vocab["species"][scientific.lower()].add(scientific)

    cur.execute("SELECT display, citation, match_keys FROM {analysis}.legal_authority"
                " WHERE match_keys IS NOT NULL")
    for display, citation, match_keys in cur.fetchall():
        value = citation or display
        for key in match_keys.split("|"):
            key = key.strip()
            if key:
                vocab["authorities"][key.lower()].add(value)

    doi_to_key = {}
    cur.execute("SELECT display, citation_key, match_keys, url"
                " FROM {analysis}.cited_references WHERE match_keys IS NOT NULL")
    for display, citation_key, match_keys, url in cur.fetchall():
        value = citation_key or display
        for key in match_keys.split("|"):
            key = key.strip()
            if key:
                vocab["cited_references"][key.lower()].add(value)
        if url:
            m = DOI_RE.search(url)
            if m:
                doi_to_key[m.group(0).rstrip(".").lower()] = value

    return {"vocab": {t: dict(p) for t, p in vocab.items()}, "doi_to_key": doi_to_key}


def _boundary_ok(text: str, start: int, end: int) -> bool:
    """end is inclusive. A match must not sit inside a larger word."""
    before = text[start - 1] if start > 0 else " "
    after = text[end + 1] if end + 1 < len(text) else " "
    return not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_")


def longest_wins(matches):
    """Drop matches fully contained in a longer kept match (per entity type):
    'Idaho Panhandle National Forests' must not also fire shorter overlaps.
    matches: [(start, end_inclusive, value)]."""
    keep = []
    for m in sorted(matches, key=lambda m: (-(m[1] - m[0]), m[0], m[2])):
        if not any(k[0] <= m[0] and m[1] <= k[1] for k in keep):
            keep.append(m)
    return keep


class StrictMatcher:
    """Aho-Corasick over lowercased text; exact vocabulary, boundary-guarded."""

    def __init__(self, vocab: dict):
        import ahocorasick  # pyahocorasick

        self.automatons = {}
        for etype, patterns in vocab.items():
            if not patterns:
                continue
            auto = ahocorasick.Automaton()
            for pat, values in patterns.items():
                auto.add_word(pat, (len(pat), tuple(sorted(values))))
            auto.make_automaton()
            self.automatons[etype] = auto

    def find(self, text: str) -> dict:
        """{entity_type: [(value, matched_text, start, end_inclusive)]}"""
        lowered = text.lower()
        out = {}
        for etype, auto in self.automatons.items():
            raw = []
            for end, (plen, values) in auto.iter(lowered):
                start = end - plen + 1
                if _boundary_ok(lowered, start, end):
                    for value in values:
                        raw.append((start, end, value))
            kept = longest_wins(raw)
            out[etype] = [(v, text[s:e + 1], s, e) for s, e, v in kept]
        return out


class LooseMatcher:
    """spaCy blank tokenizer + PhraseMatcher on LOWER — no models, deterministic
    under pinned settings; tokenizer-aware recall over the same vocabulary."""

    def __init__(self, vocab: dict):
        import spacy
        from spacy.matcher import PhraseMatcher

        self.nlp = spacy.blank("en")
        self.matchers = {}
        self.values = {}  # (etype, pattern) -> tuple of canonical values
        for etype, patterns in vocab.items():
            if not patterns:
                continue
            matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
            for pat, values in patterns.items():
                matcher.add(f"{etype}|{pat}", [self.nlp.make_doc(pat)])
                self.values[(etype, pat)] = tuple(sorted(values))
            self.matchers[etype] = matcher

    def find(self, text: str) -> dict:
        doc = self.nlp.make_doc(text)
        out = {}
        for etype, matcher in self.matchers.items():
            raw = []
            for match_id, tok_start, tok_end in matcher(doc):
                span = doc[tok_start:tok_end]
                pat = self.nlp.vocab.strings[match_id].split("|", 1)[1]
                for value in self.values[(etype, pat)]:
                    raw.append((span.start_char, span.end_char - 1, value))
            kept = longest_wins(raw)
            out[etype] = [(v, text[s:e + 1], s, e) for s, e, v in kept]
        return out


def _normalize_citation(s: str) -> str:
    return " ".join(s.split())


def run_detectors(text: str, authority_spans, doi_to_key: dict):
    """The strict pass's deterministic structural detectors. Returns
    (authority_tags, discovered_authorities, reference_tags, discovered_references,
    zip_tags, discovered_zips). A detector citation overlapping a gazetteer authority
    match is skipped — the seed already matched it 1-1."""
    authority_tags, discovered_authorities = [], []
    for rx, atype in CITATION_RES:
        for m in rx.finditer(text):
            s, e = m.start(), m.end() - 1
            if any(not (e < gs or s > ge) for gs, ge in authority_spans):
                continue
            value = _normalize_citation(m.group(0))
            authority_tags.append((value, m.group(0)))
            discovered_authorities.append((atype, value))

    reference_tags, discovered_references = [], []
    for m in DOI_RE.finditer(text):
        doi = m.group(0).rstrip(".").lower()
        seeded = doi_to_key.get(doi)
        if seeded:
            reference_tags.append((seeded, m.group(0)))
        else:
            reference_tags.append((doi, m.group(0)))
            discovered_references.append(doi)

    zip_tags, consumed = [], []
    for m in TRI_RE.finditer(text):
        city, state, zip5 = m.group(1).strip(), m.group(2), m.group(3)
        if state not in US_STATES:
            continue
        zip_tags.append((zip5, city, state, m.group(0)))
        consumed.append((m.start(), m.end() - 1))
    for m in BARE_ZIP_RE.finditer(text):
        s, e = m.start(), m.end() - 1
        if any(not (e < cs or s > ce) for cs, ce in consumed):
            continue
        zip_tags.append((m.group(1), None, None, m.group(0)))
    discovered_zips = sorted({t[0] for t in zip_tags})

    return (authority_tags, discovered_authorities, reference_tags,
            discovered_references, zip_tags, discovered_zips)


QUEUE_SQL = """
SELECT s.comment_id, s.comment_text
FROM {analysis}.v_source_comments s
LEFT JOIN {analysis}.entity_scan_state st ON st.comment_id = s.comment_id
WHERE st.MODE_FLAG IS NULL
ORDER BY s.comment_id
LIMIT ?
"""


def tag_insert(etype: str, mode: str, rows_):
    """The insert for one tag table: (sql, params) for executemany. The authority
    table also carries family_key, NOT NULL since migration 0069, computed in the
    database by {analysis}.authority_family_key from the citation as written."""
    table, value_col = TAG_SPECS[etype]
    columns = f"comment_id, {value_col}, matched_text, mode"
    values = "?, ?, ?, ?"
    if table == "comment_authorities":
        columns += ", family_key"
        values += ", {analysis}.authority_family_key(?)"
        params = [(cid, v, mt, mode, v) for cid, v, mt in rows_]
    else:
        params = [(cid, v, mt, mode) for cid, v, mt in rows_]
    sql = (f"INSERT INTO {{analysis}}.{table} ({columns}) VALUES ({values})"
           " ON CONFLICT DO NOTHING")
    return sql, params


def process_batch(cur, rows, matcher, mode, doi_to_key):
    tags = defaultdict(list)          # entity type -> [(comment_id, value, matched_text)]
    zip_rows = []                     # (comment_id, zip, city, state, matched_text)
    discovered_auth, discovered_refs, discovered_zips = set(), set(), set()

    for comment_id, text in rows:
        if not text:
            continue
        found = matcher.find(text)
        for etype, hits in found.items():
            for value, matched_text, _s, _e in hits:
                tags[etype].append((comment_id, value, matched_text))
        if mode == "strict":
            authority_spans = [(s, e) for _v, _m, s, e in found.get("authorities", [])]
            (auth_tags, d_auth, ref_tags, d_refs,
             z_tags, d_zips) = run_detectors(text, authority_spans, doi_to_key)
            for value, matched_text in auth_tags:
                tags["authorities"].append((comment_id, value, matched_text))
            for value, matched_text in ref_tags:
                tags["cited_references"].append((comment_id, value, matched_text))
            for zip5, city, state, matched_text in z_tags:
                zip_rows.append((comment_id, zip5, city, state, matched_text))
            discovered_auth.update(d_auth)
            discovered_refs.update(d_refs)
            discovered_zips.update(d_zips)

    # Discovered reference rows first (capture everything; idempotent on re-run).
    if discovered_auth:
        cur.executemany(
            "INSERT INTO {analysis}.legal_authority (type, display, citation)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT (citation) WHERE seed_id IS NULL DO NOTHING",
            [(atype, value, value) for atype, value in sorted(discovered_auth)])
    if discovered_refs:
        cur.executemany(
            "INSERT INTO {analysis}.cited_references (display, citation_key, url)"
            " VALUES (?, ?, ?)"
            " ON CONFLICT (citation_key) WHERE seed_id IS NULL DO NOTHING",
            [(doi, doi, f"https://doi.org/{doi}") for doi in sorted(discovered_refs)])
    if discovered_zips:
        cur.executemany(
            "INSERT INTO {analysis}.zipcodes (zipcode) VALUES (?)"
            " ON CONFLICT (zipcode) DO NOTHING",
            [(z,) for z in sorted(discovered_zips)])

    n_tags = 0
    for etype, rows_ in tags.items():
        sql, params = tag_insert(etype, mode, rows_)
        cur.executemany(sql, params)
        n_tags += len(rows_)
    if zip_rows:
        cur.executemany(
            "INSERT INTO {analysis}.comment_zipcodes"
            " (comment_id, zipcode, city, state, matched_text, mode)"
            " VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
            [(cid, z, c, st, mt, mode) for cid, z, c, st, mt in zip_rows])
        n_tags += len(zip_rows)

    # Every comment in the batch is now scanned by this mode, matches or not.
    flag = f"is_tagged_{mode}"
    cur.executemany(
        f"INSERT INTO {{analysis}}.entity_scan_state (comment_id, {flag})"
        " VALUES (?, true)"
        f" ON CONFLICT (comment_id) DO UPDATE SET {flag} = true",
        [(cid,) for cid, _ in rows])
    return n_tags


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    add_project_argument(parser)
    parser.add_argument("--mode", required=True, choices=("strict", "loose"))
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--max-comments", type=int, default=None,
                        help="Stop after roughly this many comments (whole batches)")
    args = parser.parse_args()
    ctx = context_from_args(args)

    with db.connect(**ctx.db_config) as conn:
        with conn.cursor() as cur:
            rendering = _Rendering(cur, ctx)
            built = build_vocabulary(rendering)
        conn.commit()

    vocab, doi_to_key = built["vocab"], built["doi_to_key"]
    n_patterns = sum(len(p) for p in vocab.values())
    matcher = StrictMatcher(vocab) if args.mode == "strict" else LooseMatcher(vocab)
    print(f"{args.mode} pass, {n_patterns} vocabulary patterns"
          f" across {len(vocab)} entity types")

    queue_sql = QUEUE_SQL.replace("MODE_FLAG", f"is_tagged_{args.mode}")
    total_comments = total_tags = 0
    while True:
        if args.max_comments is not None and total_comments >= args.max_comments:
            print(f"Stopping at --max-comments {args.max_comments}")
            break
        with db.connect(**ctx.db_config) as conn:
            with conn.cursor() as cur:
                rendering = _Rendering(cur, ctx)
                rendering.execute(queue_sql, (args.batch_size,))
                rows = rendering.fetchall()
                if not rows:
                    break
                n_tags = process_batch(rendering, rows, matcher, args.mode, doi_to_key)
            conn.commit()
        total_comments += len(rows)
        total_tags += n_tags
        print(f"batch: {len(rows)} comments, {n_tags} tag writes"
              f" (cumulative {total_comments} / {total_tags})")

    print(f"Done: {total_comments} comments scanned ({args.mode}),"
          f" {total_tags} tag writes attempted (uniques deduplicate on conflict).")


class _Rendering:
    """Token-rendering cursor wrapper ({analysis} / {src})."""

    def __init__(self, cursor, ctx: ProjectContext):
        self._cursor = cursor
        self._ctx = ctx

    def execute(self, query: str, params=None):
        return self._cursor.execute(self._ctx.render_sql(query), params or ())

    def executemany(self, query: str, params_seq):
        return self._cursor.executemany(self._ctx.render_sql(query), params_seq)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


if __name__ == "__main__":
    main()
