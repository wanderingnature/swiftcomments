#!/usr/bin/env python3
"""The v3 grader — the model reads, code grades.

Design: docs/design/reduced-ask-scoring-instrument.md. The v3 model output is
five spans, one GAP level and four yes/no answers (schema
docs/instruments/substantive-scoring-v3.schema.json). Everything else in the
score comes from here: PLACE and DOC from the places list and the document
patterns, the EVID/ASK/STAND/ALT levels from span tests over the span the model
chose, T2/T4, the topic lists, the two flags, originality and language.

Pure functions over text and vocabularies — no database access. Every level
decision records the rule that produced it, so a run can be read back rule by
rule (`result["rules"]`).

    from grade import grade
    graded = grade(parsed, comment_text, own_text, tags)

`tags` carries what the pipeline already tagged for the comment:

    {"authorities": ["16 U.S.C. 1604", ...],       # comment_authorities.matched_text
     "named_entities": [("ORG", "forest service"), ...],
     "law_cited": True}                            # LAW == 2

The vocabularies are one file per list under scripts/substance/vocab/ and the
places list is seeds/entity_tagging/seed_places.csv (name,kind).
"""
from __future__ import annotations

import csv
import html
import re
import sys
import threading
from functools import lru_cache
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_HERE.parent))                        # scripts/substance
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "entity_tagging"))

from run_pass import CITATION_RES, StrictMatcher  # noqa: E402  # pyright: ignore[reportMissingImports]
from mechanical_screens import (  # noqa: E402
    DOC_CHARACTERIZED_RE, DOC_NUMBERED_RE, _ACTION_REF as ACTION_REF_RE)

VOCAB = _HERE.parent / "vocab"
PLACES_CSV = _REPO_ROOT / "seeds" / "entity_tagging" / "seed_places.csv"

GRADED_DIMS = ["PLACE", "STAND", "DOC", "GAP", "EVID", "ASK", "ALT"]
TOPIC_FILES = {"BIO": "bio.txt", "WATER": "water.txt", "FIRE": "fire.txt",
               "RECEC": "recec.txt", "CULTURAL": "cultural.txt",
               "CLIMATE": "climate.txt", "PROCEDURAL": "procedural.txt"}


# ------------------------------------------------------------------ text

_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """The evaluation's normalization: HTML entities unescaped, <br> removed,
    curly quotes straightened, en and em dashes to a hyphen, the ellipsis
    character to three periods, runs of whitespace collapsed. Case is kept —
    two span tests (named source, named section) read capitalization."""
    t = html.unescape(text or "")
    t = _BR.sub(" ", t)
    t = (t.replace("‘", "'").replace("’", "'")
         .replace("“", '"').replace("”", '"')
         .replace("–", "-").replace("—", "-")
         .replace("…", "..."))
    return _WS.sub(" ", t).strip()


def _is_none(span) -> bool:
    return not span or normalize(str(span)).strip().lower().rstrip(".") in ("", "none")


# ------------------------------------------------------------ vocabularies

def _load_list(name: str) -> list:
    """One phrase per line; '#' comments and blank lines dropped, lowercased."""
    path = VOCAB / name
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.lower())
    return out


@lru_cache(maxsize=None)
def _matcher(name: str) -> StrictMatcher:
    return StrictMatcher({"v": {p: {p} for p in _load_list(name)}})


def hits(name: str, text: str) -> list:
    """Phrases from vocabulary file `name` present in `text`, word-boundary
    guarded, longest match wins — the strict entity pass's own matcher."""
    if not text:
        return []
    return sorted({v for v, _m, _s, _e in _matcher(name).find(text)["v"]})


# ------------------------------------------------------------------ PLACE

# Levels for a national rulemaking, where the roadless area is the unit the
# decision is made about: a state or a national forest is broad (1), a ranger
# district narrower (2), and any specific named place — the roadless area
# itself, a trail, a stream — is the narrowest (3).
_PLACE_LEVEL = {"forest": 1, "district": 2}

# A single-word name is an ambiguous English word bare ("Security", "Dry",
# "Lake"), so it is matched only beside a cue word, the rule the strict pass
# already applies to roadless-area names (run_pass.build_vocabulary).
_CUES = {
    "trail": ("trail", "trailhead"),
    "stream": ("creek", "stream", "river", "fork", "branch", "run", "brook"),
    "valley": ("valley", "canyon", "hollow", "draw", "gulch"),
    "summit": ("peak", "mountain", "mount", "butte", "knob", "hill", "summit", "dome"),
    "structure": ("cabin", "lookout", "station", "campground", "ranger station"),
    "spring": ("spring", "springs"),
    "lake": ("lake",),
    "area": ("roadless area", "inventoried roadless area", "wilderness", "area"),
    "reservoir": ("reservoir",),
    "ridge": ("ridge",),
    "flat": ("flat", "flats"),
    "gap": ("gap", "pass", "saddle"),
    "forest": ("national forest", "forest"),
    "district": ("ranger district", "district"),
    "basin": ("basin",),
    "bay": ("bay",),
    "island": ("island",),
    "range": ("range", "mountains"),
    "glacier": ("glacier",),
    "cliff": ("cliff", "cliffs"),
    "falls": ("falls", "waterfall"),
    "canal": ("canal",),
    "cape": ("cape", "point"),
    "swamp": ("swamp",),
    "rapids": ("rapids",),
    "bench": ("bench",),
    "bend": ("bend",),
    "slope": ("slope",),
    "woods": ("woods",),
    "arch": ("arch",),
    "plain": ("plain", "plains"),
    "crossing": ("crossing",),
    "crater": ("crater",),
    "arroyo": ("arroyo",),
    "beach": ("beach",),
    "bar": ("bar",),
    "channel": ("channel",),
    "gut": ("gut",),
    "pillar": ("pillar",),
    "lava": ("lava flow", "lava"),
    "isthmus": ("isthmus",),
    "sea": ("sea",),
}

_NAME_OK = re.compile(r"^[A-Za-z][A-Za-z0-9 .'\-]*$")

# A locus is a place named by its coordinates on the ground rather than by a
# name on the list. Any hit is level 3.
_LOCUS = [
    ("road_number", re.compile(
        r"\b(?:forest\s+(?:service\s+)?road|fs\s*road|nfsr|fsr|road)\s*#?\s*\d{2,5}\b",
        re.IGNORECASE)),
    ("elevation", re.compile(
        r"\b\d{1,2},?\d{3}\s*(?:feet|foot|ft\b\.?|')", re.IGNORECASE)),
    ("coordinates", re.compile(
        r"\b\d{1,3}(?:\.\d+)?\s*(?:°|degrees)\s*\d{1,2}\s*'"
        r"|-?\d{2,3}\.\d{4,}\s*,\s*-?\d{2,3}\.\d{4,}", re.IGNORECASE)),
    ("unit_number", re.compile(r"\bunit\s+\d+\b", re.IGNORECASE)),
    ("map_figure", re.compile(r"\b(?:map|figure|fig\.)\s*\d+\b", re.IGNORECASE)),
]


def _usable_place(name: str) -> bool:
    return len(name) >= 3 and bool(_NAME_OK.match(name)) and any(c.isalpha() for c in name)


@lru_cache(maxsize=None)
def _places(csv_path: str = "") -> StrictMatcher:
    """The places vocabulary as one automaton: pattern -> level. A name listed
    under more than one kind takes the highest level."""
    path = Path(csv_path) if csv_path else PLACES_CSV
    levels: dict = {}
    with path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("name") or "").strip()
            kind = (row.get("kind") or "").strip().lower()
            if not _usable_place(name):
                continue
            level = _PLACE_LEVEL.get(kind, 3)
            low = name.lower()
            pats = [low] if " " in low else [f"{low} {cue}"
                                             for cue in _CUES.get(kind, (kind,))]
            for p in pats:
                levels[p] = max(levels.get(p, 0), level)
    for state in _load_list("states.txt"):
        levels[state] = max(levels.get(state, 0), 1)
    return StrictMatcher({"places": {p: {str(lv)} for p, lv in levels.items()}})


def place_level(own_text: str, csv_path: str = "") -> tuple:
    """(level, rules). Highest match in the comment's own text wins."""
    rules = []
    norm = normalize(own_text)
    best = 0
    for value, matched, _s, _e in _places(csv_path).find(norm)["places"]:
        lv = int(value)
        if lv > best:
            best = lv
        rules.append({"rule": f"PLACE.list.{lv}", "match": matched})
    for name, rx in _LOCUS:
        m = rx.search(norm)
        if m:
            best = 3
            rules.append({"rule": f"PLACE.locus.{name}", "match": m.group(0)})
    return best, rules


# -------------------------------------------------------------------- DOC

# A named chapter or section carrying no number: the name before the keyword
# must be capitalized, which "in this section" is not. Case-sensitive on
# purpose; the keyword itself may be either case.
_DOC_NAMED_SECTION = re.compile(
    r"\b(?:[A-Z][A-Za-z]+|and|of)(?:\s+(?:[A-Z][A-Za-z]+|and|of))*"
    r"\s+(?:[Ss]ection|[Cc]hapter|[Aa]ppendix)\b(?!\s*(?:\d|[IVX]+\b|[A-Z]\b))")


def doc_level(own_text: str) -> tuple:
    """(level, rules). Highest match in the comment's own text wins."""
    norm = normalize(own_text)
    m = DOC_NUMBERED_RE.search(norm)
    if m:
        return 3, [{"rule": "DOC.3.numbered_reference", "match": m.group(0)}]
    m = DOC_CHARACTERIZED_RE.search(norm) or _DOC_NAMED_SECTION.search(norm)
    if m:
        return 2, [{"rule": "DOC.2.characterized_or_named_section", "match": m.group(0)}]
    m = ACTION_REF_RE.search(norm)
    if m:
        return 1, [{"rule": "DOC.1.action_reference", "match": m.group(0)}]
    got = hits("doc_mention.txt", norm.lower())
    if got:
        return 1, [{"rule": "DOC.1.document_mention", "match": got[0]}]
    return 0, [{"rule": "DOC.0.no_reference"}]


# ------------------------------------------------------------- span tests

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_AUTHOR_YEAR = re.compile(r"\b[A-Z][A-Za-z\-]+\s*(?:et\s+al\.?\s*)?\(\s*(?:19|20)\d{2}\s*\)"
                          r"|\bet\s+al\.")
# A capitalized word or an acronym of two or more letters ("NCWRC", "USFS"):
# an acronym names a source as surely as a capitalized word does.
_CAPITALIZED = re.compile(r"\b(?:[A-Z][a-z]+|[A-Z]{2,})\b")
_MONEY_PCT = re.compile(r"[$%]\s?\d|\d\s?[$%]")
_NUMBER = re.compile(r"\b\d[\d,.]*\b")
_DATE_FORM = re.compile(
    r"\b(?:19|20)\d{2}\b"
    r"|\b(?:january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\b"
    r"|\b(?:last|this|past)\s+(?:spring|summer|fall|autumn|winter|year|month|week|season)\b",
    re.IGNORECASE)
_DURATION_NUM = re.compile(
    r"\b(?:for|over|past|last)\s+\d+\s+(?:years|decades|seasons)\b"
    r"|\bsince\s+(?:19|20)\d{2}\b"
    r"|\b\d+\s+(?:years|decades)\b"
    r"|\b\d+\s+times\s+a\s+(?:year|month|week|season)\b",
    re.IGNORECASE)


def is_legal_citation(span_norm: str, authorities) -> tuple:
    """The span is legal authority: it holds a confirmed authority's matched
    text for this comment, matches the entity pass's citation detectors, or
    names a statute in prose.

    The prose test is the third one because the first two only see citation
    FORM. A comment that writes "Clean Water Act Section 404" instead of
    "33 U.S.C. 1344" is tagged by nothing, and the span then clears the
    named-source test on a capitalized word — EVID 2 for legal authority the
    rubric gives no EVID at any level.
    """
    low = span_norm.lower()
    for a in authorities or []:
        a_low = normalize(str(a)).lower()
        if a_low and a_low in low:
            return True, a_low
    for rx, _atype in CITATION_RES:
        m = rx.search(span_norm)
        if m:
            return True, m.group(0)
    named = hits("statute_names.txt", low)
    if named:
        return True, named[0]
    return False, None


@lru_cache(maxsize=None)
def _document_names() -> frozenset:
    return frozenset(_load_list("document_names.txt"))


def names_source(span_norm: str, entities) -> tuple:
    """A capitalized word that does not open the span, an ORG, PERSON or
    WORK_OF_ART the NER record found in this comment, or an institutional noun
    from source_nouns.txt (a source named in lower case).

    The action's own document does not count. "the DEIS" inside a span is what
    the source is being applied TO; counting it would lift every unnamed
    authority aimed at this document to level 2 and leave level 1 unreachable.
    """
    low = span_norm.lower()
    docs = _document_names()
    got = hits("source_nouns.txt", low)
    if got:
        return True, got[0]
    for etype, etext in entities or []:
        if etype in ("ORG", "PERSON", "WORK_OF_ART"):
            e = normalize(str(etext)).lower()
            if len(e) >= 3 and e in low and e not in docs:
                return True, f"{etype}:{e}"
    for m in _CAPITALIZED.finditer(span_norm):
        if m.group(0).lower() in docs:
            continue
        # A capitalized word that opens the span may just be sentence casing
        # ("The scientific literature"). An acronym never is, and a span that
        # leads with its source ("NCWRC 2019 survey data") is the normal shape.
        if m.start() > 0 or m.group(0).isupper():
            return True, m.group(0)
    return False, None


def has_figure(span_norm: str) -> tuple:
    money = _MONEY_PCT.search(span_norm)
    if money:
        return True, money.group(0)
    low = span_norm.lower()
    units = set(_load_list("figure_units.txt"))
    for m in _NUMBER.finditer(low):
        tail = low[m.end():m.end() + 40]
        for word in re.findall(r"[a-z.]+", tail)[:2]:
            if word in units:
                return True, f"{m.group(0)} {word}"
    return False, None


def first_person_dated(span_norm: str) -> tuple:
    low = span_norm.lower()
    got = hits("observation_verbs.txt", low)
    if not got:
        return False, None
    m = _DATE_FORM.search(low)
    if not m:
        return False, None
    return True, f"{got[0]} + {m.group(0)}"


# ------------------------------------------------------- graded dimensions

def evid_level(span, applied, authorities, entities) -> tuple:
    if _is_none(span):
        return 0, [{"rule": "EVID.0.no_span"}]
    norm = normalize(str(span))
    cite, match = is_legal_citation(norm, authorities)
    if cite:
        return 0, [{"rule": "EVID.0.legal_citation", "match": match}]
    if not applied:
        return 0, [{"rule": "EVID.0.not_applied"}]
    # A first-person observation with a date is level 2 and stays there: level
    # 3 is a named source plus a figure, not the date on an observation.
    obs, match = first_person_dated(norm)
    if obs:
        return 2, [{"rule": "EVID.2.first_person_dated", "match": match}]
    named, source = names_source(norm, entities)
    if named:
        year = _YEAR.search(norm)
        author = _AUTHOR_YEAR.search(norm)
        fig, fig_match = has_figure(norm)
        dated = year or author
        if dated or fig:
            held = dated.group(0) if dated else fig_match
            return 3, [{"rule": "EVID.3.named_source_with_figure",
                        "match": f"{source} + {held}"}]
        return 2, [{"rule": "EVID.2.named_source", "match": source}]
    return 1, [{"rule": "EVID.1.applied_names_nothing"}]


def ask_level(span, names_action_and_subject) -> tuple:
    if _is_none(span):
        return 0, [{"rule": "ASK.0.no_span"}]
    low = normalize(str(span)).lower()
    if names_action_and_subject:
        got = hits("timing_words.txt", low)
        if got:
            return 3, [{"rule": "ASK.3.timing_word", "match": got[0]}]
        return 2, [{"rule": "ASK.2.action_and_subject"}]
    got = hits("work_verbs.txt", low)
    if got:
        return 1, [{"rule": "ASK.1.work_verb", "match": got[0]}]
    return 0, [{"rule": "ASK.0.disposition_only"}]


def stand_level(span, this_place) -> tuple:
    """The role test runs first: the rubric scores a professional role that
    bears on the subject at 3 whether or not a place is named."""
    norm = "" if _is_none(span) else normalize(str(span))
    low = norm.lower()
    got = hits("professional_roles.txt", low)
    if got:
        return 3, [{"rule": "STAND.3.professional_role", "match": got[0]}]
    if not norm:
        return 0, [{"rule": "STAND.0.no_span"}]
    if not this_place:
        return 0, [{"rule": "STAND.0.not_this_place"}]
    got = hits("duration_frequency.txt", low)
    if got:
        return 2, [{"rule": "STAND.2.duration_or_frequency", "match": got[0]}]
    m = _DURATION_NUM.search(low)
    if m:
        return 2, [{"rule": "STAND.2.duration_or_frequency", "match": m.group(0)}]
    return 1, [{"rule": "STAND.1.connection_only"}]


def alt_level(span, distinct) -> tuple:
    if _is_none(span):
        return 0, [{"rule": "ALT.0.no_span"}]
    low = normalize(str(span)).lower()
    if not distinct:
        return 1, [{"rule": "ALT.1.preference"}]
    got = hits("alt_frame.txt", low)
    if got:
        return 3, [{"rule": "ALT.3.against_the_frame", "match": got[0]}]
    return 2, [{"rule": "ALT.2.distinct_alternative"}]


def gap_level(span, level) -> tuple:
    if _is_none(span):
        return 0, [{"rule": "GAP.0.no_span"}]
    return min(3, max(0, int(level or 0))), [{"rule": "GAP.model_level"}]


# ------------------------------------------- classification fields in code

def topics_for(own_text: str) -> tuple:
    low = normalize(own_text).lower()
    out, rules = [], []
    for code, fname in TOPIC_FILES.items():
        got = hits(f"topics/{fname}", low)
        if got:
            out.append(code)
            rules.append({"rule": f"topic.{code}", "match": got[0]})
    if not out:
        out = ["OTHER"]
        rules.append({"rule": "topic.OTHER"})
    return out, rules


def flags_for(own_text: str) -> tuple:
    low = normalize(own_text).lower()
    att = hits("attachments.txt", low)
    inc = hits("incorporation.txt", low)
    rules = []
    if att:
        rules.append({"rule": "flag.attachments_referenced", "match": att[0]})
    if inc:
        rules.append({"rule": "flag.incorporates_by_reference", "match": inc[0]})
    return bool(att), bool(inc), rules


_LANGDETECT_LOCK = threading.Lock()


def detect_language(comment_text: str) -> str:
    """The two-letter code from langdetect over the comment text. Seeded so the
    same text gives the same answer on every run.

    The profiles are loaded under a lock. langdetect's init_factory publishes
    its global factory BEFORE loading the 55 profiles into it, so a second
    thread arriving during that second finds a factory with no languages and
    detect() raises "Need to load profiles." Sixteen scoring workers start
    together; six of the first calls of a run failed that way (2026-09-20)
    and those comments wrote no row."""
    try:
        from langdetect import DetectorFactory, detect
        from langdetect.detector_factory import init_factory
    except ImportError as exc:      # the dependency is declared in pyproject.toml
        raise RuntimeError(
            "langdetect is not installed; run `uv sync` (grade.detect_language)") from exc
    with _LANGDETECT_LOCK:
        init_factory()
    DetectorFactory.seed = 0
    text = normalize(comment_text)
    if len(text) < 20:
        return "en"
    return detect(text)


# ------------------------------------------------------------------ grade

def grade(parsed: dict, comment_text: str, own_text: str, tags: dict,
          places_csv: str = "") -> dict:
    """The v3 model object plus the comment's text and tags -> the seven graded
    dimensions and the classification fields code owns. LAW and the derived
    fields stay with finalize_record."""
    own = own_text if own_text is not None else comment_text
    ev = parsed.get("evidence") or {}
    auth = tags.get("authorities") or []
    ents = tags.get("named_entities") or []
    rules = []

    place, r = place_level(own, places_csv)
    rules += r
    doc, r = doc_level(own)
    rules += r
    gap, r = gap_level(ev.get("GAP"), parsed.get("gap"))
    rules += r
    evid, r = evid_level(ev.get("EVID"), bool(parsed.get("evid_applied")), auth, ents)
    rules += r
    ask, r = ask_level(ev.get("ASK"), bool(parsed.get("ask_names_action_and_subject")))
    rules += r
    alt, r = alt_level(ev.get("ALT"), bool(parsed.get("alt_distinct")))
    rules += r
    stand, r = stand_level(ev.get("STAND"), bool(parsed.get("stand_this_place")))
    rules += r

    moves = [m for m in (parsed.get("moves") or []) if m in ("M1", "M2", "M3", "M5")]
    if alt >= 2 and "M4" not in moves:
        moves.append("M4")
        rules.append({"rule": "move.M4_from_alt"})
    moves = sorted(set(moves))

    targets = [t for t in (parsed.get("targets") or []) if t in ("T1", "T3")]
    if "significan" in normalize(own).lower():
        targets.append("T2")
        rules.append({"rule": "target.T2_significance"})
    if tags.get("law_cited"):
        targets.append("T4")
        rules.append({"rule": "target.T4_from_law"})
    targets = sorted(set(targets))

    topics, r = topics_for(own)
    rules += r
    attachments, incorporates, r = flags_for(own)
    rules += r

    return {
        "scores": {"PLACE": place, "STAND": stand, "DOC": doc, "GAP": gap,
                   "EVID": evid, "ASK": ask, "ALT": alt},
        "moves": moves,
        "targets": targets,
        "topics": topics,
        "attachments_referenced": attachments,
        "incorporates_by_reference": incorporates,
        "originality": "unknown",
        "language": detect_language(comment_text),
        "rules": rules,
    }
