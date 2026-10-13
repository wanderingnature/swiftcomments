"""The parser: spaCy en_core_web_md, loaded once. Everything a detector needs
from the parse is a small function here, so the detectors read as rules."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Iterator

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span, Token

MODEL = "en_core_web_md"

FIRST_PERSON = {"i", "we", "my", "our", "me", "us", "mine", "ours", "myself", "ourselves"}
FINITE_TAGS = {"VBZ", "VBP", "VBD", "MD"}


@lru_cache(maxsize=1)
def model() -> Language:
    return spacy.load(MODEL)


def parse(text: str) -> Doc:
    return model()(text)


def parse_many(texts: Iterable[str], batch_size: int = 256) -> Iterator[Doc]:
    return model().pipe(texts, batch_size=batch_size)


@dataclass(frozen=True)
class Run:
    text: str
    start: int
    end: int


def proper_noun_runs(doc: Doc) -> list[Run]:
    """Maximal runs of PROPN tokens."""
    out: list[Run] = []
    cur: list[Token] = []
    for tok in doc:
        if tok.pos_ == "PROPN":
            cur.append(tok)
            continue
        if cur:
            out.append(_run(cur))
            cur = []
    if cur:
        out.append(_run(cur))
    return out


def _run(toks: list[Token]) -> Run:
    return Run(toks[0].doc.text[toks[0].idx:toks[-1].idx + len(toks[-1].text)],
               toks[0].idx, toks[-1].idx + len(toks[-1].text))


def entities(doc: Doc, labels: set[str]) -> list[Run]:
    return [Run(e.text, e.start_char, e.end_char) for e in doc.ents if e.label_ in labels]


def has_finite_verb(doc: Doc, mask: str | None = None) -> bool:
    """A finite verb or modal in the text; with `mask` (the own-words text, same
    length as doc.text with quoted spans blanked), only verbs outside the
    blanked spans count."""
    for tok in doc:
        if tok.pos_ not in ("VERB", "AUX"):
            continue
        if tok.tag_ in FINITE_TAGS or "Fin" in tok.morph.get("VerbForm", []):
            if mask is None or mask[tok.idx:tok.idx + len(tok.text)].strip():
                return True
    return False


def first_person(doc: Doc) -> bool:
    return any(t.lower_ in FIRST_PERSON for t in doc)


def is_imperative(doc: Doc) -> bool:
    """Opens with a base-form verb ("Prepare a cumulative analysis"), or with
    "Please" and one."""
    toks = [t for t in doc if not t.is_punct and not t.is_space]
    if not toks:
        return False
    first = toks[0]
    if first.lower_ == "please" and len(toks) > 1:
        first = toks[1]
    return first.pos_ == "VERB" and first.tag_ == "VB"


def subject_text(tok: Token) -> str:
    for c in tok.children:
        if c.dep_ in ("nsubj", "nsubjpass"):
            doc = tok.doc
            return doc.text[c.left_edge.idx:c.right_edge.idx + len(c.right_edge.text)].lower()
    return ""


def root_subjects(doc: Doc) -> list[tuple[Token, str]]:
    """(root verb, its subject text) for each clause root."""
    out: list[tuple[Token, str]] = []
    for tok in doc:
        if tok.dep_ == "ROOT" or tok.dep_ == "conj" and tok.pos_ in ("VERB", "AUX"):
            out.append((tok, subject_text(tok)))
    return out


DEONTIC = {"should", "must", "ought", "need", "needs", "shall"}


def has_modal(tok: Token) -> bool:
    """A deontic modal on the clause: the commenter is saying what the agency
    should do, not describing what it would or will do."""
    return any(c.lower_ in DEONTIC for c in tok.children) or tok.lower_ in DEONTIC


@dataclass(frozen=True)
class WorkHit:
    verb: str
    verb_start: int
    verb_end: int
    obj: str | None
    obj_start: int
    obj_end: int
    named: bool


def _span_text(doc: Doc, left: Token, right: Token) -> tuple[str, int, int]:
    s = left.idx
    e = right.idx + len(right.text)
    return doc.text[s:e], s, e


def _np_named(head: Token, generic: set[str], intensifiers: set[str]) -> bool:
    """Does the noun phrase headed by `head` name something? A pronoun or a
    generic head names nothing unless a preposition attaches a named object
    ("the issue of sediment delivery"). A work noun ("look", "analysis")
    names something only through a compound, a non-intensifier adjective, or
    such an attachment."""
    if head.pos_ in ("PRON", "DET"):
        return any(_prep_named(c, generic, intensifiers) for c in head.children)
    lemma = head.lemma_.lower()
    if lemma in generic:
        return any(_prep_named(c, generic, intensifiers) for c in head.children)
    for c in head.children:
        if c.dep_ in ("compound", "nmod", "poss") and c.pos_ in ("NOUN", "PROPN", "NUM"):
            return True
        if c.dep_ == "amod" and c.lemma_.lower() not in intensifiers:
            return True
        if c.dep_ in ("prep", "acl", "relcl") and _prep_named(c, generic, intensifiers):
            return True
        if c.dep_ == "nummod":
            return True
    return False


def _prep_named(tok: Token, generic: set[str], intensifiers: set[str]) -> bool:
    if tok.dep_ == "prep":
        for p in tok.children:
            if p.dep_ in ("pobj", "pcomp"):
                if p.pos_ in ("NOUN", "PROPN", "NUM"):
                    return p.lemma_.lower() not in generic or _np_named(p, generic, intensifiers)
                if p.pos_ == "VERB":
                    return True
        return False
    if tok.dep_ in ("acl", "relcl"):
        return any(c.dep_ in ("dobj", "obj", "pobj") for c in tok.subtree)
    return False


def work_hits(doc: Doc, work_verbs: set[str], work_nouns: set[str],
              generic: set[str], intensifiers: set[str]) -> list[WorkHit]:
    """Each work verb with its object (direct, or the passive subject), and each
    work noun with its own phrase, graded named or not. The object of a verb
    that heads a work noun ("prepare an analysis of X") is judged on the noun."""
    out: list[WorkHit] = []
    seen_nouns: set[int] = set()
    for tok in doc:
        if tok.pos_ == "VERB" and tok.lemma_.lower() in work_verbs:
            objs = [c for c in tok.children if c.dep_ in ("dobj", "obj", "nsubjpass")]
            if not objs:
                for c in tok.children:
                    if c.dep_ == "prep" and c.lower_ in ("at", "into", "on", "of", "for"):
                        objs += [p for p in c.children if p.dep_ == "pobj"]
            if not objs:
                out.append(WorkHit(tok.text, tok.idx, tok.idx + len(tok.text),
                                   None, -1, -1, False))
                continue
            for o in objs:
                text, s, e = _span_text(doc, o.left_edge, o.right_edge)
                if o.lemma_.lower() in work_nouns:
                    seen_nouns.add(o.i)
                named = _np_named(o, generic, intensifiers)
                out.append(WorkHit(tok.text, tok.idx, tok.idx + len(tok.text), text, s, e, named))
    for tok in doc:
        if tok.i in seen_nouns or tok.pos_ != "NOUN" or tok.lemma_.lower() not in work_nouns:
            continue
        text, s, e = _span_text(doc, tok.left_edge, tok.right_edge)
        out.append(WorkHit(tok.text, tok.idx, tok.idx + len(tok.text), text, s, e,
                           _np_named(tok, generic, intensifiers)))
    return out


def clause_subjects_lower(doc: Doc) -> list[tuple[str, bool]]:
    """(subject text, clause has a modal) per clause root. Used by ALT: a clause
    whose subject is the agency or the proposal and that carries no modal
    attributes a position to the agency rather than stating the commenter's."""
    out: list[tuple[str, bool]] = []
    for tok, subj in root_subjects(doc):
        out.append((subj, has_modal(tok)))
    return out


def noun_chunk_texts(doc: Doc) -> list[Span]:
    return list(doc.noun_chunks)
