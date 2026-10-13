"""The detector rules, one sentence at a time. Each rule fires on the words of
one sentence and records a hit naming the rule, the grade, and the matched
words with their offsets within the sentence. The instrument's definitions
are quoted where they decide a rule (docs/instruments/substantive-scoring-v3.md);
the plan is docs/plans/model-free-scoring-plan-parallel.md.

Rule set 1 grades each sentence from its own words alone: no neighbour is
read. The four context grades the first draft gave a window (EVID "applied",
STAND "this place", GAP 3, ALT "distinct") are decided inside the sentence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

from spacy.tokens import Doc

from . import DIMS, GATE_DIMS
from .nlp import (entities, first_person, has_finite_verb, is_imperative,
                  proper_noun_runs, clause_subjects_lower, work_hits)
from .places import PlaceHit, places
from .text import (AUTHOR_YEAR, DATE_FORM, DURATION_NUM, YEAR, Span, figures,
                   hits, load_list, number_tokens, own_words, quoted_spans)

# --------------------------------------------------------------- patterns

# Adequacy questioned: the analysis is said to be too thin. The floor filter's
# and the screen's deficiency patterns, extended by the instrument's own
# examples ("take a much harder look", "doesn't do it justice").
DEFICIENCY_RE = re.compile(
    r"\bfail(?:s|ed|ure|ing)?\s+to\b"
    r"|\b(?:does|did|do)\s*(?:n't|\s+not)\s+(?:even\s+|adequately\s+|properly\s+|fully\s+|sufficiently\s+)?"
    r"(?:consider|address|account|analy[sz]e|evaluate|examine|assess|disclose|quantify|study|"
    r"discuss|support|justify|explain|mention|include|acknowledge|look\s+at|take\s+into\s+account)\b"
    r"|\bnot\s+(?:adequately|sufficiently|properly|fully|even|meaningfully)\s+"
    r"(?:consider|analy[sz]|address|evaluat|studi|assess|examin|disclos|discuss|account)\w*"
    r"|\bignor(?:es|ed|ing)?\b|\boverlook(?:s|ed|ing)?\b"
    r"|\binadequate\w*\b|\binsufficient\w*\b"
    r"|\bno\s+analysis\b|\bnot\s+analy[sz]ed\b|\bnever\s+analy[sz]ed\b"
    r"|\black(?:s|ing|ed)?\s+(?:of\s+)?(?:any\s+)?(?:analysis|data|evidence|study|consideration|discussion|support|basis|detail)\b"
    r"|\bmissing\s+(?:analysis|data|discussion)\b"
    r"|\bshould\s+have\s+(?:considered|analy[sz]ed|studied|evaluated|examined|addressed|disclosed|included)\b"
    r"|\bwithout\s+(?:considering|analy[sz]ing|evaluating|addressing|assessing|any\s+analysis)\b"
    r"|\bunexamined\b|\bunaddressed\b|\bunanaly[sz]ed\b|\bunstudied\b"
    r"|\bomit(?:s|ted)?\b|\bsilent\s+on\b|\bglosses\s+over\b|\bglossed\s+over\b"
    r"|\btake[sn]?\s+a\s+(?:much\s+)?(?:harder|closer|better|hard|close|careful|serious)\s+look\b"
    r"|\bdo(?:es)?\s*(?:n't|\s+not)\s+do\s+(?:it|them|this|that|the\s+\w+)\s+justice\b"
    r"|\bneeds?\s+(?:more|further|additional|better|a\s+more\s+\w+)\s+(?:study|analysis|consideration|review|evaluation|scrutiny|attention)\b"
    r"|\bneeds?\s+to\s+be\s+(?:corrected|revised|redone|updated|supplemented|reconsidered|reanaly[sz]ed)\b"
    r"|\b(?:has|have)\s+not\s+(?:been\s+)?(?:analy[sz]ed|considered|studied|addressed|evaluated|examined|assessed)\b"
    r"|\bnot\s+been\s+(?:analy[sz]ed|considered|studied|addressed|evaluated|examined|assessed)\b"
    r"|\bdeficient\b|\bdeficienc(?:y|ies)\b|\bcursory\b|\bsuperficial\b|\bperfunctory\b",
    re.IGNORECASE)

# Accuracy questioned: something in the analysis is said to be wrong.
ERROR_RE = re.compile(
    r"\bwrong\b|\bincorrect(?:ly)?\b|\berroneous(?:ly)?\b|\bin\s+error\b|\berrors?\b"
    r"|\binaccura(?:te|cies|cy)\b|\bmisstat\w*|\bmischaracteriz\w*|\bmisrepresent\w*"
    r"|\boverstat\w*|\bunderstat\w*|\bunderestimat\w*|\boverestimat\w*"
    r"|\bcontradict\w*|\bfalse(?:ly)?\b|\bflawed\b|\bnot\s+(?:true|accurate|correct)\b"
    r"|\bunsupported\b|\bis\s+not\s+supported\b|\bmisleading\b|\bmistaken\b",
    re.IGNORECASE)

# A concern stated without deficiency language: topic-level at most.
CONCERN_RE = re.compile(
    r"\bconcern(?:ed|s)?\s+(?:about|regarding|over|with|that)\b"
    r"|\bworr(?:y|ied|ies)\s+(?:about|that)\b"
    r"|\bramifications?\b|\btroubl(?:ed|ing)\s+(?:by|that)\b|\balarmed\s+(?:by|that)\b",
    re.IGNORECASE)

# Missing analysis identified: an analysis that was not done is named.
ABSENCE_RE = re.compile(
    r"\b(?:no|without\s+any|lacks?\s+any|lacks?\s+an?|there\s+is\s+no)\s+"
    r"(?:analysis|assessment|evaluation|study|discussion|consideration|survey|inventory|modeling|data)\s+(?:of|on|for)\s+(\w[\w\s\-]{2,60})"
    r"|\b(?:does|did)\s*(?:n't|\s+not)\s+(?:analy[sz]e|assess|evaluate|quantify|model|survey|inventory|consider|address)\s+(?:the\s+|any\s+|its\s+)?(\w[\w\s\-]{2,60})"
    r"|\bfail(?:s|ed)?\s+to\s+(?:analy[sz]e|assess|evaluate|quantify|model|survey|inventory|consider|address|disclose)\s+(?:the\s+|any\s+|its\s+)?(\w[\w\s\-]{2,60})"
    r"|\b(?:has|have)\s+not\s+(?:been\s+)?(?:analy[sz]ed|assessed|evaluated|quantified|modeled|surveyed|inventoried)\b",
    re.IGNORECASE)

# A reference to this action: the rule, the DEIS, an alternative, the purpose
# and need (the mechanical screen's test, copied).
ACTION_REF_RE = re.compile(
    r"(FS-2025-0001|RIN\s*0596"
    r"|\bDEIS\b|\bEIS\b|environmental impact statement"
    r"|\brescission\b|\brescind\w*"
    r"|\balternative\s*(?:1|2|3|one|two|three)\b|no.action alternative"
    r"|\bpurpose and need\b|\bproposed rule\b|\bthis rulemaking\b"
    r"|\bthe proposal\b|\bthis proposal\b|\bdocket\b"
    r"|\broadless rule\b|\broadless area conservation rule\b|\bthis rule\b|\bthe rule\b"
    r"|\brollback\b|\bthe rationale\b|\bthis administration\b)",
    re.IGNORECASE)

# What the action does, as against what it is called (rule set 3): road
# building and the road network, and the roadless areas the rule protects.
# A source set against these is set against this proposal. Used for EVID's
# "applied" tie only.
ACTION_SUBSTANCE_RE = re.compile(
    r"\broad[\s-]+(?:construction|building|network|system|footprint|density|expansion)\b"
    r"|\b(?:build(?:s|ing)?|built|construct(?:s|ed|ing)?|new|more)\s+(?:\w+\s+)?roads\b"
    r"|\broaded\b|\broadless\s+areas?\b|\binventoried\s+roadless\b|(?-i:\bIRAs?\b)",
    re.IGNORECASE)

# The action's own names and the actors around it: never a source the
# commenter cites, never the thing a gap is specific about.
EXCLUDED_SUBSTRINGS = (
    "roadless", "rule", "alternative", "forest service", "national forest", "usda", "usfs",
    "department", "agency", "administration", "congress", "senator", "representative",
    "president", "secretary", "docket", "rin ", "deis", "eis", "nepa", " act", "county",
    "governor", "commissioner", "united states", "america", "federal", "government",
    "public lands", "national", "wilderness", "trump", "biden", "republican", "democrat",
)
SOURCE_URL_RE = re.compile(r"https?://\S+|\bdoi\.org/\S+|\b10\.\d{4,}/\S+", re.IGNORECASE)
RULE_YEAR_RE = re.compile(
    r"\b(?:19|20)\d{2}\b(?=\s+(?:\w+\s+){0,3}?(?:roadless|rule|rescission|deis|eis|notice|proposal|repeal|decision|rulemaking|regulation))",
    re.IGNORECASE)


def source_years(text: str) -> list[re.Match[str]]:
    """Years that can date a source: not the year in the rule's own name
    ("the 2001 Roadless Rule", "the 2008 Idaho Roadless Rule")."""
    rule_years = {m.start() for m in RULE_YEAR_RE.finditer(text)}
    return [m for m in YEAR.finditer(text) if m.start() not in rule_years]

DOC_NUMBERED_RE = re.compile(
    r"\b(?:section|sec\.|§|page|p\.|pp\.|figure|fig\.|table|chapter|"
    r"appendix|volume|vol\.)\s*(?:\d|(?-i:[IVX]+\b|[A-Z]\b))", re.IGNORECASE)
DOC_CHARACTERIZED_RE = re.compile(
    r"\b(?:DEIS|EIS|draft environmental impact statement|environmental impact statement|the draft|the analysis|the document|"
    r"the proposal|the proposed rule|the rule|biological assessment|economic analysis)\s+"
    r"(?:(?:also|itself|even|explicitly|clearly|openly|further|then|now|simply|merely|only)\s+)?"
    r"(?:at|states|stated|acknowledges|acknowledged|concedes|conceded|admits|admitted|claims|claimed|asserts|asserted|"
    r"says|said|calls|called|lists|listed|finds|found|concludes|concluded|assumes|assumed|estimates|estimated|"
    r"projects|projected|reports|reported|shows|showed|notes|noted|indicates|indicated|identifies|identified|"
    r"recognizes|recognized|documents|documented)\b",
    re.IGNORECASE)
DOC_NAMED_SECTION_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z]+|and|of)(?:\s+(?:[A-Z][A-Za-z]+|and|of))*"
    r"\s+(?:[Ss]ection|[Cc]hapter|[Aa]ppendix)\b(?!\s*(?:\d|[IVX]+\b|[A-Z]\b))")

# Legal citation forms (the entity-tagging pass's, copied).
CITATION_RES: list[re.Pattern[str]] = [
    re.compile(r"\b\d{1,3}\s+C\.?\s?F\.?\s?R\.?,?\s*(?:§+\s*|[Ss]ections?\s+|[Ss]ec\.?\s+"
               r"|[Pp]arts?\s+|[Pp]t\.?\s+)?\d+(?:\.\d+)?[a-z]?\b"),
    re.compile(r"\b\d{1,3}\s+U\.?\s?S\.?\s?C\.?\s*(?:§+\s*|[Ss]ections?\s+|[Ss]ec\.?\s+)?"
               r"\d+[a-z]?(?:\([a-zA-Z0-9]+\))*\b"),
    re.compile(r"\b\d{1,4}\s+(?:U\.S\.|S\.\s?Ct\.|F\.\s?(?:2d|3d|4th)|"
               r"F\.\s?Supp\.(?:\s?2d|\s?3d)?)\s+\d{1,5}\b"),
    re.compile(r"\b\d{1,3}\s+Fed\.?\s?Reg\.?\s+\d{1,6}\b", re.IGNORECASE),
    re.compile(r"\b(?:Executive\s+Order|E\.?\s?O\.?)\s*(?:No\.?\s*)?\d{4,5}\b", re.IGNORECASE),
]

REQUEST_RE = re.compile(
    r"\bplease\b|\burges?\b|\burged\b|\bshould\b|\bmust\b|\bought\s+to\b|\bneeds?\s+to\b"
    r"|\bneeds?\b|\brequire[sd]?\b|\brequest(?:s|ed)?\b|\brecommend(?:s|ed)?\b"
    r"|\bask(?:s|ed)?\b|\bdemand(?:s|ed)?\b|\bcall(?:s|ed)?\s+(?:on|for)\b"
    r"|\b(?:i|we)\s+would\s+like\b|\b(?:i|we)\s+want\b|\bhas\s+to\b|\bhave\s+to\b"
    r"|\bI'?d\s+(?:also\s+)?ask\b|\bimplore\b|\binsist\b|\bexpect\b",
    re.IGNORECASE)
LOOK_RE = re.compile(
    r"\b(?:take|takes|took|taking|have|has|give|gives)\s+(?:a\s+)?(?:(?:much|far|even)\s+)?"
    r"(?:\w+\s+){0,2}?(?:look|review)\b", re.IGNORECASE)

SIGNIFICAN_RE = re.compile(r"significan", re.IGNORECASE)

# ---- rule set 2 (2026-10-06, from the 400-comment under-gating review; the
# gate is a loose first sort, so each of these reads wide).

# The agency's own record used as the source: "according to the DEIS", "by its
# own admission", "the Forest Service's own numbers", "its own 2000 FEIS",
# "the USFS biological assessment found". Applied by definition: the guide
# treats a figure from the agency's own record set against the proposal as
# specific by definition.
RECORD_SOURCE_RE = re.compile(
    r"\baccording\s+to\s+(?:the\s+)?(?:[\w,.\-]+\s+){0,8}?(?:deis|eis|draft|proposal|proposed\s+rule|agency|forest\s+service|usda|usfs|department|biological\s+assessment|economic\s+analysis|environmental\s+impact\s+statement|rule)\b"
    r"|\bby\s+(?:its|their|the\s+agency's|the\s+agency’s|usda's|usda’s)\s+own\s+(?:admission|numbers|data|figures|estimate|estimates|analysis|findings|account|words)\b"
    r"|\b(?:the\s+)?(?:agency|forest\s+service|usda|usfs|department|service)(?:'s|’s)\s+(?:own\s+)?(?:numbers|data|figures|analysis|analyses|estimate|estimates|findings|assessment|record|admission|projections|modeling|study|report|economic\s+analysis|biological\s+assessment|deis|eis)\b"
    r"|\bits\s+own\s+(?:\d{4}\s+)?(?:feis|eis|deis|analysis|assessment|data|numbers|figures|findings|estimate|estimates|study|report)\b"
    r"|\b(?:the\s+)?(?:usfs|usda|forest\s+service|agency|agency's|agency’s)\s+(?:\d{4}\s+)?(?:biological\s+assessment|economic\s+analysis|cost-benefit\s+analysis|regulatory\s+impact\s+analysis|draft\s+environmental\s+impact\s+statement|deis|eis|feis|analysis|assessment|study|report|data)\b",
    re.IGNORECASE)
RECORD_SAYS_RE = re.compile(
    r"\b(?:says|states|stated|concedes|conceded|admits|admitted|acknowledges|acknowledged|finds|found|estimates|estimated|"
    r"projects|projected|reports|reported|shows|showed|notes|noted|claims|claimed|asserts|asserted|lists|listed|calls|"
    r"assumes|assumed|indicates|indicated|identifies|identified|recognizes|recognized|documents|documented|itself)\b",
    re.IGNORECASE)

# A stated effect of the action on a named resource, species, place or
# figure, without a deficiency word: the relational gap the guide names as
# the floor filter's blind spot ("we will lose steelhead and salmon runs due to
# the increased silt").
EFFECT_RE = re.compile(
    r"\b(?:displac|los[ei]|loss\s+of|destroy|damag|harm|degrad|fragment|disrupt|increas|decreas|reduc|eliminat|"
    r"threaten|kill|pollut|silt|sediment|erod|erosion|impact|affect|jeopardi[sz]|endanger|wipe\s+out|drive\s+out|"
    r"cut\s+off|block|burn|flood|dry\s+up|warm|contaminat|sever|isolat|extirpat|decimat|devastat|imperil|"
    r"undermin|compromis|diminish|deplet)\w*",
    re.IGNORECASE)
EFFECT_ACTION_RE = re.compile(
    r"\b(?:logging|clear-?cut\w*|timber\s+harvest\w*|timber\s+sales?|roads?|road\s+(?:construction|building|reconstruction)|"
    r"road-?building|rescission|rescind\w*|repeal\w*|this\s+proposal|the\s+proposal|this\s+rule|the\s+rule|the\s+rollback|"
    r"rollback|removing\s+(?:these\s+|the\s+)?protections|remove\s+(?:these\s+|the\s+)?protections|opening\s+(?:up\s+)?(?:these|those|the)\s+areas|"
    r"open(?:ing)?\s+(?:these|those|the)\s+(?:lands|forests|areas)|lifting\s+the\s+(?:road\s+)?ban|lift\s+the\s+(?:road\s+)?ban|"
    r"mining|drilling|oil\s+and\s+gas|development|industrial\s+\w+|fragmentation)\b",
    re.IGNORECASE)

# A question to the agency about its analysis, or a request for an analysis,
# names a missing analysis ("how has USDA quantified the additional ignition
# risk", "include analysis of cumulative watershed effects").
ANALYSIS_VERB_RE = re.compile(
    r"\b(?:quantif\w*|analy[sz]\w*|evaluat\w*|assess\w*|consider\w*|demonstrat\w*|account\w*|measur\w*|model\w*|"
    r"survey\w*|disclos\w*|justif\w*|explain\w*|address\w*|examin\w*|stud\w+|inventor\w*|map\w*|document\w*|"
    r"calculat\w*|estimat\w*|determin\w*|identif\w*|show\w*|compar\w*|weigh\w*)",
    re.IGNORECASE)
ASK_ANALYSIS_STEMS = ("analy", "quantif", "evaluat", "assess", "includ", "model", "survey", "disclos", "stud",
                      "examin", "consider", "account", "measur", "inventor", "map", "document", "calculat",
                      "estimat", "compar", "identif", "determin", "explain", "justif", "address", "prepar", "conduct")
CAUSAL_RE = re.compile(
    r"\bbecause\b|\bso\s+that\b|\btherefore\b|\bthus\b|\bhence\b|\bleads?\s+to\b|\bled\s+to\b"
    r"|\bresults?\s+in\b|\bresulted\s+in\b|\bcauses?\b|\bcaused\b|\bcausing\b|\bdue\s+to\b"
    r"|\bas\s+a\s+result\b|\bconsequently\b|\bwhich\s+(?:would|will|could)\b|\bif\s+.{3,80}?\s+then\b"
    r"|\bso\s+(?:if|the|that|its|their)\b|\bmeans\s+that\b|\bincreas(?:es|ed|ing)\b|\bdecreas(?:es|ed|ing)\b"
    r"|\breduc(?:es|ed|ing)\b|\braise[sd]?\b|\blower[sd]?\b|\bdegrad(?:es|ed|ing)\b|\bharm(?:s|ed|ing)?\b",
    re.IGNORECASE)
ALT_NUMBERED_RE = re.compile(r"^\s*alternative\s+\d", re.IGNORECASE)


@lru_cache(maxsize=None)
def _set(name: str) -> set[str]:
    return set(load_list(name))


# ------------------------------------------------------------------ types

@dataclass(frozen=True)
class Hit:
    dimension: str
    grade: int
    rule: str
    match: str
    start: int
    end: int


@dataclass
class Context:
    """What a sentence is scored against beyond its own words. Everything here
    is read-only input; a test passes empty collections."""
    record_text_keys: set[str] = field(default_factory=set)
    record_figures: set[str] = field(default_factory=set)
    authority_keys: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    authorities: list[str] = field(default_factory=list)
    alt_similarity: Callable[[str], float | None] | None = None


@dataclass
class SentenceInput:
    unit_id: int
    comment_id: str
    start_char: int
    end_char: int
    text: str
    text_key: str
    sentence_hash: str | None = None


@dataclass
class SentenceScore:
    unit_id: int
    comment_id: str
    start_char: int
    end_char: int
    text_key: str
    dims: dict[str, int]
    hits: list[Hit]
    evid_applied: bool
    ask_names: bool
    alt_distinct: bool
    stand_this_place: bool
    is_record_text: bool
    anchors: list[str]
    moves: list[str]
    targets: list[str]
    has_citation: bool
    mechanism: bool


# --------------------------------------------------------------- helpers

def _inside(spans: list[Span], start: int, end: int) -> bool:
    return any(s.start <= start and end <= s.end for s in spans)


def _excluded_proper(text_lower: str) -> bool:
    t = text_lower.strip()
    if t.startswith("the "):
        t = t[4:]
    t = re.sub(r"(?:'s|’s|')$", "", t).strip()
    for name in ("document_names.txt", "agency_names.txt", "states.txt", "source_nouns.txt",
                 "statute_names.txt"):
        if t in _set(name):
            return True
    padded = f" {t} "
    return any(sub in padded for sub in EXCLUDED_SUBSTRINGS)


def _shouting(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(c.isupper() for c in letters) / len(letters) > 0.5


def _lower_set_hits(name: str, text: str) -> list[Span]:
    return [Span(m.start, m.end, text[m.start:m.end]) for m in hits(name, text)]


# ------------------------------------------------------------------ PLACE

def detect_place(own: str) -> tuple[int, list[Hit], list[PlaceHit]]:
    found = places().find(own)
    best = 0
    out: list[Hit] = []
    for p in found:
        best = max(best, p.level)
        out.append(Hit("PLACE", p.level, p.rule, p.match, p.start, p.end))
    return best, out, found


# -------------------------------------------------------------------- DOC

def detect_doc(own: str) -> tuple[int, list[Hit]]:
    m = DOC_NUMBERED_RE.search(own)
    if m:
        return 3, [Hit("DOC", 3, "DOC.3.numbered_reference", m.group(0), m.start(), m.end())]
    m = DOC_CHARACTERIZED_RE.search(own) or DOC_NAMED_SECTION_RE.search(own)
    if m:
        return 2, [Hit("DOC", 2, "DOC.2.characterized_or_named_section", m.group(0), m.start(), m.end())]
    m = ACTION_REF_RE.search(own)
    if m:
        return 1, [Hit("DOC", 1, "DOC.1.action_reference", m.group(0), m.start(), m.end())]
    got = hits("doc_mention.txt", own)
    if got:
        g = got[0]
        return 1, [Hit("DOC", 1, "DOC.1.document_mention", own[g.start:g.end], g.start, g.end)]
    return 0, []


# -------------------------------------------------------------------- LAW

def detect_law(own: str, ctx: Context) -> tuple[int, list[Hit]]:
    low = own.lower()
    for a in ctx.authorities:
        a_low = a.lower().strip()
        if a_low and a_low in low:
            s = low.find(a_low)
            return 2, [Hit("LAW", 2, "LAW.2.confirmed_authority", own[s:s + len(a_low)], s, s + len(a_low))]
    for key in ctx.authority_keys:
        k = key.lower().strip()
        if len(k) >= 6 and k in low:
            s = low.find(k)
            return 2, [Hit("LAW", 2, "LAW.2.authority_key", own[s:s + len(k)], s, s + len(k))]
    for rx in CITATION_RES:
        m = rx.search(own)
        if m:
            return 2, [Hit("LAW", 2, "LAW.2.citation_form", m.group(0), m.start(), m.end())]
    return 0, []


# -------------------------------------------------------------------- GAP

def _specific_names(own: str, doc: Doc, place_hits: list[PlaceHit],
                    quoted: list[Span]) -> list[Span]:
    """The resource, species, effect, or scale named: a species
    (vocab/species.txt), a figure, or a numbered or named section. The
    instrument's words, and no more: a place is where, not what (C2 keeps
    "water quality" at level 1 beside "Wilson Creek"), and a proper noun that
    is not a species names an actor, not the thing missing or wrong."""
    out: list[Span] = []
    out += [s for s in _lower_set_hits("species.txt", own) if not _inside(quoted, s.start, s.end)]
    out += [s for s in figures(own, _set("figure_units.txt")) if not _inside(quoted, s.start, s.end)]
    for rx in (DOC_NUMBERED_RE, DOC_NAMED_SECTION_RE):
        m = rx.search(own)
        if m:
            out.append(Span(m.start(), m.end(), m.group(0)))
    out.sort(key=lambda s: s.start)
    return out


def _gap_without_deficiency_word(own: str, doc: Doc, place_hits: list[PlaceHit], quoted: list[Span],
                                 ask: AskResult | None) -> tuple[int, list[Hit]]:
    """Rule set 2: the three ways a comment names a gap without a deficiency
    word. (a) A question to the agency carrying an analysis verb. (b) A request
    whose work verb is an analysis verb. (c) A stated effect of the action on a
    named resource, the relational gap. (a) and (b) are level 2 whether the
    thing named is specific or a category: the request names the missing
    analysis. (c) is level 2 with a specific name (species, figure, section,
    place), level 1 with a category; the instrument's C6 holds it there."""
    out: list[Hit] = []
    specific = _specific_names(own, doc, place_hits, quoted)
    categories = _lower_set_hits("resource_categories.txt", own)
    if "?" in own:
        m = ANALYSIS_VERB_RE.search(own)
        if m and (specific or categories):
            # A question naming what the analysis should cover names the
            # missing analysis, whether the object is specific or a category:
            # the next step downstream decides the edge cases.
            s = specific[0] if specific else categories[0]
            out.append(Hit("GAP", 2, "GAP.2.missing_analysis_asked", f"{m.group(0)}: {s.text}", s.start, s.end))
            return 2, out
    if ask is not None and ask.level >= 2 and ask.verb and ask.obj:
        vl = ask.verb.lower()
        if any(vl.startswith(stem) for stem in ASK_ANALYSIS_STEMS):
            in_obj = [s for s in specific if ask.obj_start <= s.start < ask.obj_end]
            cat_in_obj = [c for c in categories if ask.obj_start <= c.start < ask.obj_end]
            place_in_obj = [p for p in place_hits if ask.obj_start <= p.start < ask.obj_end]
            if in_obj or place_in_obj:
                s = in_obj[0] if in_obj else Span(place_in_obj[0].start, place_in_obj[0].end, place_in_obj[0].match)
                out.append(Hit("GAP", 2, "GAP.2.missing_analysis_requested", f"{ask.verb}: {s.text}", s.start, s.end))
                return 2, out
            if cat_in_obj:
                # A request to analyze a category names the missing analysis
                # as surely as a request to analyze a species does.
                c = cat_in_obj[0]
                out.append(Hit("GAP", 2, "GAP.2.missing_analysis_requested", f"{ask.verb}: {c.text}", c.start, c.end))
                return 2, out
    eff = EFFECT_RE.search(own)
    act = EFFECT_ACTION_RE.search(own)
    if eff and act:
        named = specific + [Span(p.start, p.end, p.match) for p in place_hits]
        named.sort(key=lambda x: x.start)
        if named:
            s = named[0]
            out.append(Hit("GAP", 2, "GAP.2.stated_effect_on_named_resource", f"{eff.group(0)} / {act.group(0)}: {s.text}", s.start, s.end))
            return 2, out
        if categories:
            c = categories[0]
            out.append(Hit("GAP", 1, "GAP.1.stated_effect_on_category", f"{eff.group(0)} / {act.group(0)}: {c.text}", c.start, c.end))
            return 1, out
    return 0, out


def detect_gap(own: str, doc: Doc, place_hits: list[PlaceHit], quoted: list[Span],
               is_record: bool, ask: AskResult | None = None) -> tuple[int, list[Hit]]:
    if is_record:
        return 0, [Hit("GAP", 0, "GAP.0.agency_text", "", 0, 0)]
    level, out = _detect_gap_by_trigger(own, doc, place_hits, quoted)
    if level >= 2:
        return level, out
    level2, out2 = _gap_without_deficiency_word(own, doc, place_hits, quoted, ask)
    if level2 > level:
        return level2, out + out2
    return level, out


def _detect_gap_by_trigger(own: str, doc: Doc, place_hits: list[PlaceHit],
                           quoted: list[Span]) -> tuple[int, list[Hit]]:
    defic = DEFICIENCY_RE.search(own)
    err = ERROR_RE.search(own)
    concern = CONCERN_RE.search(own)
    trigger = defic or err
    if not trigger and not concern:
        return 0, []
    out: list[Hit] = []
    t = trigger or concern
    assert t is not None
    out.append(Hit("GAP", 0, "GAP.trigger." + ("deficiency" if defic else "error" if err else "concern"),
                   t.group(0), t.start(), t.end()))
    specific = _specific_names(own, doc, place_hits, quoted) if trigger else []
    categories = _lower_set_hits("resource_categories.txt", own)
    if specific:
        s = specific[0]
        level = 2
        out.append(Hit("GAP", 2, "GAP.2.specific_name", s.text, s.start, s.end))
        cons = hits("consequence_phrases.txt", own)
        if cons:
            c = cons[0]
            level = 3
            out.append(Hit("GAP", 3, "GAP.3.stated_consequence", own[c.start:c.end], c.start, c.end))
        return level, out
    if categories:
        c = categories[0]
        out.append(Hit("GAP", 1, "GAP.1.topic_level", c.text, c.start, c.end))
        return 1, out
    out.append(Hit("GAP", 0, "GAP.0.nothing_named", t.group(0), t.start(), t.end()))
    return 0, out


# ------------------------------------------------------------------- EVID

def _owner_spans(text: str, doc: Doc) -> list[Span]:
    """Who a source belongs to: an organisation, person or work the parser
    found, or an acronym of three or more capitals, neither the agency, the
    action, a statute, a state, nor a place, and not shouting."""
    out: list[Span] = []
    if _shouting(text):
        return out
    for ent in entities(doc, {"ORG", "PERSON", "WORK_OF_ART"}):
        e_low = ent.text.lower()
        if len(e_low) >= 3 and not _excluded_proper(e_low) and not places().find(ent.text):
            out.append(Span(ent.start, ent.end, ent.text))
    # An acronym: three to six capitals (NCWRC, USGS, NOAA, USFWS). A longer
    # run of capitals is a shouted word.
    for m in re.finditer(r"\b[A-Z]{3,6}\b", text):
        if not _excluded_proper(m.group(0).lower()):
            out.append(Span(m.start(), m.end(), m.group(0)))
    return out


def _noun_hits(name: str, text: str, doc: Doc) -> list[Span]:
    """Vocabulary hits whose token the parser reads as a noun: "reports" the
    noun, not "reports" the verb."""
    out: list[Span] = []
    for m in hits(name, text):
        tok = next((t for t in doc if t.idx <= m.start < t.idx + len(t.text)), None)
        if tok is not None and tok.pos_ in ("NOUN", "PROPN"):
            out.append(Span(m.start, m.end, text[m.start:m.end]))
    return out


def _record_source(text: str, doc_level: int) -> Span | None:
    """The agency's own record as the source (rule set 2): a record-source
    phrase, or a document reference (DOC 2 or 3) with a verb of saying or
    finding in the sentence."""
    m = RECORD_SOURCE_RE.search(text)
    if m:
        return Span(m.start(), m.end(), m.group(0))
    if doc_level >= 2:
        for rx in (DOC_CHARACTERIZED_RE, DOC_NUMBERED_RE, DOC_NAMED_SECTION_RE):
            d = rx.search(text)
            if d and RECORD_SAYS_RE.search(text):
                return Span(d.start(), d.end(), d.group(0))
    return None


def _named_source(text: str, doc: Doc, ctx: Context, quoted: list[Span]) -> Span | None:
    """A source the commenter names. The guide's examples all carry a source
    noun with an owner or a date beside it: "NCWRC 2019 survey data", "the 2018
    state survey", "the agency's $40 million estimate". So: a confirmed cited
    reference, an author-year citation, a URL or DOI, or a source noun with an
    owner, a source year, or the agency's own possessive within forty
    characters. A bare proper noun names no source."""
    low = text.lower()
    for c in ctx.citations:
        c_low = c.lower().strip()
        if len(c_low) >= 4 and c_low in low:
            s = low.find(c_low)
            return Span(s, s + len(c_low), text[s:s + len(c_low)])
    m = AUTHOR_YEAR.search(text)
    if m:
        return Span(m.start(), m.end(), m.group(0))
    m = SOURCE_URL_RE.search(text)
    if m:
        return Span(m.start(), m.end(), m.group(0))
    nouns = _noun_hits("source_nouns_cited.txt", text, doc)
    if not nouns:
        return None
    owners = _owner_spans(text, doc)
    years = source_years(text)
    for n in nouns:
        lo, hi = max(0, n.start - 40), n.end + 40
        for o in owners:
            if lo <= o.start <= hi:
                return Span(min(o.start, n.start), max(o.end, n.end), text[min(o.start, n.start):max(o.end, n.end)])
        for y in years:
            if lo <= y.start() <= hi:
                return Span(min(y.start(), n.start), max(y.end(), n.end), text[min(y.start(), n.start):max(y.end(), n.end)])
        before = low[lo:n.start]
        if re.search(r"\b(?:agency's|agency’s|forest service's|forest service’s|usda's|usda’s|its own|their own|agency's own)\s*(?:\w+\s+)?$", before):
            return Span(n.start, n.end, text[n.start:n.end])
    return None


def detect_evid(sentence: str, own: str, doc: Doc, ctx: Context, quoted: list[Span],
                place_hits: list[PlaceHit], doc_level: int, law_level: int
                ) -> tuple[int, list[Hit], bool, bool]:
    """(level, hits, applied, source_present). A legal citation is not evidence.
    Applied, inside the sentence: the commenter's own words carry a finite verb
    and name this proposal, a place, or the document."""
    if law_level == 2 and not ctx.citations:
        legal = any(rx.search(sentence) for rx in CITATION_RES) or bool(hits("statute_names.txt", sentence))
        if legal and not _named_source(own, doc, ctx, quoted):
            return 0, [Hit("EVID", 0, "EVID.0.legal_citation", "", 0, 0)], False, False
    out: list[Hit] = []
    obs = hits("observation_verbs.txt", own)
    named = _named_source(sentence, doc, ctx, quoted)
    record = _record_source(own, doc_level)
    unnamed = hits("unnamed_authority.txt", own)
    if not obs and named is None and record is None and not unnamed:
        return 0, [], False, False
    # The tie to this proposal must be in the commenter's own words; the verb
    # may be anywhere in the sentence, quotation included. Tested against C7:
    # its pasted passages still fail the tie, so the blanking never decided it.
    applied = (has_finite_verb(doc) and
               (bool(place_hits) or doc_level >= 1 or bool(ACTION_REF_RE.search(own))
                or bool(ACTION_SUBSTANCE_RE.search(own))))
    if record is not None and named is None and not obs:
        # The agency's own record, set against the proposal: applied by definition.
        years = source_years(sentence)
        figs = figures(sentence, _set("figure_units.txt"))
        held = years[0].group(0) if years else figs[0].text if figs else None
        if held:
            out.append(Hit("EVID", 3, "EVID.3.agency_record_with_year_or_figure", f"{record.text} + {held}", record.start, record.end))
            return 3, out, True, True
        out.append(Hit("EVID", 2, "EVID.2.agency_record", record.text, record.start, record.end))
        return 2, out, True, True
    if obs:
        o = obs[0]
        dated = DATE_FORM.search(own) or DURATION_NUM.search(own)
        if dated:
            level, rule, match = 2, "EVID.2.first_person_dated", f"{own[o.start:o.end]} + {dated.group(0)}"
        else:
            level, rule, match = 1, "EVID.1.first_person_undated", own[o.start:o.end]
        start, end = o.start, o.end
    elif named is not None:
        years = source_years(sentence)
        year = years[0] if years else None
        author = AUTHOR_YEAR.search(sentence)
        figs = figures(sentence, _set("figure_units.txt"))
        if year or author or figs:
            held = year.group(0) if year else author.group(0) if author else figs[0].text
            level, rule, match = 3, "EVID.3.named_source_with_year_author_or_figure", f"{named.text} + {held}"
        else:
            level, rule, match = 2, "EVID.2.named_source", named.text
        start, end = named.start, named.end
    else:
        u = unnamed[0]
        level, rule, match = 1, "EVID.1.unnamed_authority", own[u.start:u.end]
        start, end = u.start, u.end
    if not applied:
        out.append(Hit("EVID", 0, "EVID.0.not_applied", match, start, end))
        return 0, out, False, True
    out.append(Hit("EVID", level, rule, match, start, end))
    return level, out, True, True


# -------------------------------------------------------------------- ASK

@dataclass
class AskResult:
    level: int
    hits: list[Hit]
    names: bool
    verb: str | None = None
    obj: str | None = None
    obj_start: int = -1
    obj_end: int = -1


def detect_ask(own: str, doc: Doc) -> AskResult:
    request = REQUEST_RE.search(own) or is_imperative(doc)
    if not request:
        return AskResult(0, [], False)
    out: list[Hit] = []
    works = work_hits(doc, _set("work_verbs.txt"), _set("work_nouns.txt"),
                      _set("generic_objects.txt"), _set("intensifiers.txt"))
    works = [w for w in works if own[w.verb_start:w.verb_end].strip()]
    look = LOOK_RE.search(own)
    best = 0
    names = False
    best_hit = None
    for w in works:
        if w.obj is not None and w.named:
            names = True
            best = 2
            best_hit = w
            out.append(Hit("ASK", 2, "ASK.2.action_and_subject", f"{w.verb}: {w.obj}", w.obj_start, w.obj_end))
            break
    if best == 0 and (works or look):
        if look:
            out.append(Hit("ASK", 1, "ASK.1.harder_look", look.group(0), look.start(), look.end()))
        else:
            w = works[0]
            out.append(Hit("ASK", 1, "ASK.1.work_verb_names_nothing", w.verb, w.verb_start, w.verb_end))
        best = 1
    if best == 0:
        m = request if not isinstance(request, bool) else None
        if m is not None:
            out.append(Hit("ASK", 0, "ASK.0.disposition", m.group(0), m.start(), m.end()))
        else:
            out.append(Hit("ASK", 0, "ASK.0.disposition", "", 0, 0))
        return AskResult(0, out, False)
    if best == 2:
        timing = hits("timing_words.txt", own)
        if timing:
            t = timing[0]
            best = 3
            out.append(Hit("ASK", 3, "ASK.3.timing", own[t.start:t.end], t.start, t.end))
    if best_hit is not None:
        return AskResult(best, out, names, best_hit.verb, best_hit.obj, best_hit.obj_start, best_hit.obj_end)
    return AskResult(best, out, names)


# -------------------------------------------------------------------- ALT

def _attributed_to_agency(doc: Doc) -> bool:
    """A clause whose subject is the agency or the proposal and that carries no
    modal states the agency's position, not the commenter's."""
    agency = _set("agency_names.txt") | {"the proposal", "this proposal", "the proposed rule",
                                         "the rule", "the deis", "the eis", "the draft"}
    for subj, modal in clause_subjects_lower(doc):
        if not subj or modal:
            continue
        if subj in agency or ALT_NUMBERED_RE.match(subj) or any(subj.endswith(a) for a in agency if len(a) > 6):
            return True
    return False


ON_TABLE_RE = re.compile(
    r"\b(?:keep|keeps|keeping|retain|retains|retaining|preserve|preserves|preserving|maintain|maintains|"
    r"maintaining|uphold|upholds|upholding|leave|leaves|leaving|reinstate|reinstates|restore|restores|"
    r"protect|protects|protecting|support|supports|supporting)\s+"
    r"(?:the\s+|these\s+|this\s+|our\s+|its\s+|all\s+)?(?:current\s+|existing\s+|2001\s+|nationwide\s+|national\s+|"
    r"strong\s+|full\s+|original\s+)*"
    r"(?:roadless\s+(?:area\s+conservation\s+)?rule|rule|roadless\s+protections?|protections?|roadless\s+rule\s+intact)\b"
    r"|\b(?:let|allow)\s+the\s+(?:2001\s+)?(?:roadless\s+)?rule\s+(?:to\s+)?stand\b"
    r"|\bwithdraw(?:al\s+of|s|ing)?\s+(?:the|this)\s+(?:proposal|proposed\s+rule|rescission|rule|rollback)\b"
    r"|\b(?:do\s+not|don't|not|never|should\s+not)\s+(?:be\s+)?rescind(?:ed)?\b"
    r"|\bno[\s-]action(?:\s+alternative)?\b|\balternative\s+(?:1|2|3|one|two|three)\b"
    r"|\b(?:adopt|finalize|support|implement)(?:s|ing)?\s+(?:the\s+)?(?:rescission|proposed\s+rule|proposal|proposed\s+action)\b"
    r"|\brescind(?:s|ing)?\s+(?:the\s+)?(?:2001\s+)?(?:roadless\s+(?:area\s+conservation\s+)?)?rule\b",
    re.IGNORECASE)
ALT_WINDOW = 90


def detect_alt(own: str, doc: Doc, place_hits: list[PlaceHit], ctx: Context,
               sentence_hash: str | None) -> tuple[int, list[Hit], bool]:
    out: list[Hit] = []
    on_table = ON_TABLE_RE.search(own) or hits("alt_on_table.txt", own)
    language = hits("alt_language.txt", own)
    if not on_table and not language:
        return 0, [], False
    if language and _attributed_to_agency(doc) and not on_table:
        return 0, [Hit("ALT", 0, "ALT.0.attributed_to_agency", own[language[0].start:language[0].end],
                       language[0].start, language[0].end)], False
    # The concrete element must sit with the alternative language: within
    # ALT_WINDOW characters after it. A year in the rule's own name, and a bare
    # number, are not concrete elements.
    concrete: Span | None = None
    # Every alternative-language hit is tried, in order; the first with a
    # concrete element in its window and no on-table outcome in that window
    # is the alternative. An outcome on the table takes precedence only when
    # it sits with the alternative language ("select an alternative that
    # retains the 2001 rule"); elsewhere it is a separate statement of position.
    all_candidates: list[Span] = [Span(p.start, p.end, p.match) for p in place_hits]
    all_candidates += figures(own, _set("figure_units.txt"))
    all_candidates += [Span(c.start, c.end, own[c.start:c.end]) for c in hits("condition_words.txt", own)]
    all_candidates += [Span(c.start, c.end, own[c.start:c.end]) for c in hits("alt_measures.txt", own)]
    all_candidates = [c for c in all_candidates if not RULE_YEAR_RE.match(own, c.start)]
    all_candidates.sort(key=lambda c: c.start)
    on_table_spans: list[tuple[int, int]] = [(m.start(), m.end()) for m in ON_TABLE_RE.finditer(own)]
    on_table_spans += [(m.start, m.end) for m in hits("alt_on_table.txt", own)]
    lang_hit = None
    on_table_near = False
    for lh in language:
        lo, hi = lh.start, lh.end + ALT_WINDOW
        near = [c for c in all_candidates if lo <= c.start <= hi]
        if not near:
            continue
        if any(s <= hi and e >= lo - ALT_WINDOW for s, e in on_table_spans):
            on_table_near = True
            continue
        lang_hit, concrete = lh, near[0]
        break
    if lang_hit is not None and concrete is not None and not on_table_near:
        lang = lang_hit
        out.append(Hit("ALT", 2, "ALT.2.distinct_alternative",
                       f"{own[lang.start:lang.end]} + {concrete.text}", lang.start, lang.end))
        if ctx.alt_similarity is not None and sentence_hash:
            sim = ctx.alt_similarity(sentence_hash)
            if sim is not None:
                out.append(Hit("ALT", 2, "ALT.measure.deis_alternatives_similarity", f"{sim:.4f}", 0, 0))
        frame = hits("alt_frame.txt", own)
        if frame:
            f = frame[0]
            out.append(Hit("ALT", 3, "ALT.3.against_the_frame", own[f.start:f.end], f.start, f.end))
            return 3, out, True
        return 2, out, True
    if on_table:
        if isinstance(on_table, list):
            t = on_table[0]
            s, e = t.start, t.end
        else:
            s, e = on_table.start(), on_table.end()
        out.append(Hit("ALT", 1, "ALT.1.preference_on_the_table", own[s:e], s, e))
        return 1, out, False
    lang = language[0]
    out.append(Hit("ALT", 0, "ALT.0.alternative_language_nothing_concrete",
                   own[lang.start:lang.end], lang.start, lang.end))
    return 0, out, False


# ------------------------------------------------------------------ STAND

def detect_stand(own: str, doc: Doc, place_hits: list[PlaceHit]) -> tuple[int, list[Hit], bool]:
    roles = hits("professional_roles.txt", own)
    fp = first_person(doc)
    connection = fp and (bool(hits("connection_verbs.txt", own)) or bool(hits("observation_verbs.txt", own))
                         or re.search(r"\bas\s+an?\s+(?:local|lifelong|longtime|long-time|former|retired|resident)\b", own, re.IGNORECASE) is not None)
    if roles and (fp or re.search(r"\bas\s+an?\b", own, re.IGNORECASE)):
        r = roles[0]
        this_place = bool(place_hits)
        return 3, [Hit("STAND", 3, "STAND.3.professional_role", own[r.start:r.end], r.start, r.end)], this_place
    if not connection:
        return 0, [], False
    if not place_hits:
        return 0, [Hit("STAND", 0, "STAND.0.not_this_place", "", 0, 0)], False
    got = hits("duration_frequency.txt", own)
    if got:
        g = got[0]
        return 2, [Hit("STAND", 2, "STAND.2.duration_or_frequency", own[g.start:g.end], g.start, g.end)], True
    m = DURATION_NUM.search(own)
    if m:
        return 2, [Hit("STAND", 2, "STAND.2.duration_or_frequency", m.group(0), m.start(), m.end())], True
    p = place_hits[0]
    return 1, [Hit("STAND", 1, "STAND.1.connection_to_this_place", p.match, p.start, p.end)], True


# ------------------------------------------------------- generality test

def anchors_for(own: str, doc: Doc, place_hits: list[PlaceHit], doc_level: int,
                ctx: Context, quoted: list[Span]) -> list[str]:
    """A statement that would read the same against any similar proposal in
    any decade is a generality. A sentence passes with a proposal-specific
    anchor: the document, a place, this action, a figure from the record, a
    demonstrative aimed at a claim, or a proper noun that is not the document,
    the agency, or a state."""
    out: list[str] = []
    if doc_level >= 1:
        out.append("doc")
    if place_hits:
        out.append("place")
    if ACTION_REF_RE.search(own):
        out.append("action")
    if ctx.record_figures and (number_tokens(own) & ctx.record_figures):
        out.append("record_figure")
    if re.search(r"\b(?:that|this)\s*(?:'s|is|was)\s+(?:simply\s+|just\s+|plainly\s+)?(?:wrong|incorrect|false|not\s+true|inaccurate|unsupported|misleading)\b", own, re.IGNORECASE):
        out.append("demonstrative_claim")
    for run in proper_noun_runs(doc):
        if _inside(quoted, run.start, run.end):
            continue
        low = run.text.lower()
        if _excluded_proper(low) or low in ("i", "us") or YEAR.fullmatch(run.text):
            continue
        out.append("proper_noun")
        break
    return out


# -------------------------------------------------------- the sentence

def score_sentence(s: SentenceInput, doc: Doc, ctx: Context) -> SentenceScore:
    text = s.text
    quoted = quoted_spans(text)
    own = own_words(text, quoted)
    is_record = s.text_key in ctx.record_text_keys

    place_level, place_h, place_hits = detect_place(own)
    doc_level, doc_h = detect_doc(own)
    # LAW reads the whole sentence, quotations included: a citation the
    # commenter quotes is still a citation the comment carries, as the
    # confirmed-authority pass treats it.
    law_level, law_h = detect_law(text, ctx)
    ask = detect_ask(own, doc)
    ask_level, ask_h, ask_names = ask.level, ask.hits, ask.names
    gap_level, gap_h = detect_gap(own, doc, place_hits, quoted, is_record, ask)
    evid_level, evid_h, applied, source_present = detect_evid(
        text, own, doc, ctx, quoted, place_hits, doc_level, law_level)
    alt_level, alt_h, alt_distinct = detect_alt(own, doc, place_hits, ctx, s.sentence_hash)
    stand_level, stand_h, this_place = detect_stand(own, doc, place_hits)

    anchors = anchors_for(own, doc, place_hits, doc_level, ctx, quoted)
    hits_all: list[Hit] = place_h + doc_h + law_h + gap_h + evid_h + ask_h + alt_h + stand_h
    if not anchors:
        if gap_level > 0:
            hits_all.append(Hit("GAP", 0, "GAP.0.generality", "", 0, 0))
            gap_level = 0
        if evid_level > 0:
            hits_all.append(Hit("EVID", 0, "EVID.0.generality", "", 0, 0))
            evid_level = 0
            applied = False
        if doc_level > 0:
            hits_all.append(Hit("DOC", 0, "DOC.0.generality", "", 0, 0))
            doc_level = 0

    dims = {"PLACE": place_level, "STAND": stand_level, "DOC": doc_level, "GAP": gap_level,
            "EVID": evid_level, "ASK": ask_level, "ALT": alt_level, "LAW": law_level}
    assert set(dims) == set(DIMS)

    moves: list[str] = []
    err = ERROR_RE.search(own)
    if err and (doc_level >= 1 or ACTION_REF_RE.search(own)):
        moves.append("M1")
        hits_all.append(Hit("MOVE", 0, "M1.accuracy_questioned", err.group(0), err.start(), err.end()))
    defic = DEFICIENCY_RE.search(own)
    if defic and gap_level >= 1:
        moves.append("M2")
        hits_all.append(Hit("MOVE", 0, "M2.adequacy_questioned", defic.group(0), defic.start(), defic.end()))
    if applied:
        moves.append("M3")
        hits_all.append(Hit("MOVE", 0, "M3.new_information", "", 0, 0))
    if alt_level >= 2:
        moves.append("M4")
        hits_all.append(Hit("MOVE", 0, "M4.alternative_offered", "", 0, 0))
    absent = ABSENCE_RE.search(own)
    if absent and any(g for g in absent.groups() if g):
        named_obj = next(g for g in absent.groups() if g)
        moves.append("M5")
        hits_all.append(Hit("MOVE", 0, "M5.missing_analysis_named", named_obj.strip(), absent.start(), absent.end()))

    targets: list[str] = []
    cats = _lower_set_hits("resource_categories.txt", own) + _lower_set_hits("species.txt", own)
    if cats and (gap_level >= 1 or applied):
        targets.append("T1")
    if SIGNIFICAN_RE.search(own):
        targets.append("T2")
    if alt_level >= 1:
        targets.append("T3")
    if law_level == 2:
        targets.append("T4")

    mechanism = bool(CAUSAL_RE.search(own)) and (gap_level >= 1 or applied)
    if mechanism:
        m = CAUSAL_RE.search(own)
        assert m is not None
        hits_all.append(Hit("MECH", 0, "MECH.cause_effect", m.group(0), m.start(), m.end()))
    has_citation = law_level == 2 or (source_present and any(
        h.dimension == "EVID" and ("named_source" in h.rule or h.rule == "EVID.0.not_applied") for h in hits_all))

    return SentenceScore(
        unit_id=s.unit_id, comment_id=s.comment_id, start_char=s.start_char, end_char=s.end_char,
        text_key=s.text_key, dims=dims, hits=hits_all, evid_applied=applied, ask_names=ask_names,
        alt_distinct=alt_distinct, stand_this_place=this_place, is_record_text=is_record,
        anchors=anchors, moves=sorted(set(moves)), targets=sorted(set(targets)),
        has_citation=has_citation, mechanism=mechanism)


def gate_of(dims: dict[str, int]) -> list[str]:
    return [d for d in GATE_DIMS if dims[d] >= 2]
