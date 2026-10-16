"""Text utilities: normalization, quotation detection, numbers and figures,
and the phrase matcher every vocabulary list runs through. No database, no
model. The package has no sentence splitter of its own: a comment's sentences
are split by the comment-sentences package (stored_units), the method that writes
roadless.comment_unit (run.score_text calls it for raw text).
"""
from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

VOCAB = Path(__file__).resolve().parent / "vocab"

_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def normalize(text: str | None) -> str:
    """HTML entities unescaped, tags removed, curly quotes straightened, en and
    em dashes to a hyphen, the ellipsis character to three periods, runs of
    whitespace collapsed. Case is kept: the proper-noun and named-source tests
    read capitalization."""
    t = html.unescape(text or "")
    t = _BR.sub(" ", t)
    t = _TAG.sub(" ", t)
    t = (t.replace("‘", "'").replace("’", "'")
         .replace("“", '"').replace("”", '"')
         .replace("–", "-").replace("—", "-")
         .replace("…", "..."))
    return _WS.sub(" ", t).strip()


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def norm_key(text: str) -> str:
    """Lowercased, every non-alphanumeric removed: the identity under which the
    same sentence in different comments is the same text."""
    return _NON_ALNUM.sub("", normalize(text).lower())


def text_key(text: str) -> str:
    return hashlib.sha256(norm_key(text).encode("utf-8")).hexdigest()


# ------------------------------------------------------------- quotations

_DQUOTE = re.compile(r'"([^"]{15,})"')
_SQUOTE = re.compile(r"(?:(?<=^)|(?<=[\s:(\[]))'([^']{15,}?)'(?=[\s.,;:)\]!?]|$)")
_ATTRIBUTION = re.compile(
    r"\s*[-]{1,2}\s*[A-Z][^.;\n]{1,80}?,?\s*(?:19|20)\d{2}[a-z]?\b\.?"
    r"|\(\s*[A-Z][A-Za-z.&\s-]+?(?:et\s+al\.?)?,?\s*(?:19|20)\d{2}[a-z]?\s*\)")


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    text: str


def quoted_spans(text: str) -> list[Span]:
    """Runs the commenter is quoting: text inside double quotes, or inside
    single quotes opened after a space or a colon, of fifteen characters or
    more, plus an attribution that follows a quotation ("- Journal, 2021",
    "(Author 2019)")."""
    spans: list[Span] = []
    for rx in (_DQUOTE, _SQUOTE):
        for m in rx.finditer(text):
            spans.append(Span(m.start(), m.end(), m.group(0)))
    spans.sort(key=lambda s: s.start)
    with_attr: list[Span] = []
    for s in spans:
        m = _ATTRIBUTION.match(text, s.end)
        if m:
            with_attr.append(Span(s.start, m.end(), text[s.start:m.end()]))
        else:
            with_attr.append(s)
    return _merge(with_attr)


def _merge(spans: list[Span]) -> list[Span]:
    out: list[Span] = []
    for s in sorted(spans, key=lambda x: (x.start, -x.end)):
        if out and s.start < out[-1].end:
            if s.end > out[-1].end:
                last = out[-1]
                out[-1] = Span(last.start, s.end, last.text + s.text[last.end - s.start:])
            continue
        out.append(s)
    return out


def own_words(text: str, quoted: list[Span]) -> str:
    """`text` with every quoted span replaced by spaces of the same length, so
    offsets into the result are offsets into the original."""
    if not quoted:
        return text
    chars = list(text)
    for s in quoted:
        for k in range(s.start, min(s.end, len(chars))):
            chars[k] = " "
    return "".join(chars)


# ---------------------------------------------------------------- numbers

NUMBER = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b")
MONEY_PCT = re.compile(r"\$\s?\d[\d,.]*|\b\d[\d,.]*\s?(?:%|percent\b)", re.IGNORECASE)
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
AUTHOR_YEAR = re.compile(
    r"\b[A-Z][A-Za-z\-]+\s*(?:(?:and|&)\s+[A-Z][A-Za-z\-]+\s*)?(?:et\s+al\.?,?\s*)?\(\s*(?:19|20)\d{2}[a-z]?\s*\)"
    r"|\b[A-Z][A-Za-z\-]+\s+et\s+al\.?,?\s*(?:19|20)\d{2}[a-z]?\b"
    r"|\bet\s+al\.")
DATE_FORM = re.compile(
    r"\b(?:19|20)\d{2}\b"
    r"|\b(?:january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\b"
    r"|\b(?:last|this|past)\s+(?:spring|summer|fall|autumn|winter|year|month|week|season)\b",
    re.IGNORECASE)
DURATION_NUM = re.compile(
    r"\b(?:for|over|past|last)\s+(?:the\s+)?(?:past\s+|last\s+)?\d+\s+(?:years|decades|seasons|summers|winters)\b"
    r"|\bsince\s+(?:19|20)\d{2}\b"
    r"|\b\d+\s+(?:years|decades)\b"
    r"|\b\d+\s+times\s+a\s+(?:year|month|week|season)\b"
    r"|\b(?:twenty|thirty|forty|fifty)\s+years\b",
    re.IGNORECASE)


def figures(text: str, units: set[str]) -> list[Span]:
    """Money, percentages, and a number followed within two words by a unit
    word from figure_units.txt."""
    out: list[Span] = []
    for m in MONEY_PCT.finditer(text):
        out.append(Span(m.start(), m.end(), m.group(0)))
    low = text.lower()
    for m in NUMBER.finditer(low):
        tail = low[m.end():m.end() + 40]
        words = re.findall(r"[a-z.]+", tail)[:2]
        for w in words:
            if w.rstrip(".") in units:
                out.append(Span(m.start(), m.end(), m.group(0) + " " + w))
                break
    return _merge(out)


def number_tokens(text: str) -> set[str]:
    """Numbers of three or more digits, or with a decimal point, commas
    removed: the figures that can be matched exactly against the record."""
    out: set[str] = set()
    for m in NUMBER.finditer(text):
        tok = m.group(0).replace(",", "")
        digits = tok.replace(".", "")
        if len(digits) >= 3 or "." in tok:
            out.add(tok)
    return out


# --------------------------------------------------------- phrase matcher

_TOKEN = re.compile(r"[a-z0-9]+(?:['\-.][a-z0-9]+)*")


@dataclass(frozen=True)
class Match:
    phrase: str
    start: int
    end: int


class PhraseMatcher:
    """Exact multi-word phrase lookup over lower-cased word tokens, longest
    match first, non-overlapping. Tokens keep internal apostrophes, hyphens
    and periods, so "u.s. forest service" and "site-specific" match whole."""

    def __init__(self, phrases: Iterable[str]) -> None:
        self._phrases: dict[tuple[str, ...], str] = {}
        self.max_len = 1
        for p in phrases:
            toks = tuple(_TOKEN.findall(p.lower()))
            if not toks:
                continue
            self._phrases[toks] = p
            self.max_len = max(self.max_len, len(toks))

    def __len__(self) -> int:
        return len(self._phrases)

    def find(self, text: str) -> list[Match]:
        low = text.lower()
        toks = [(m.group(0), m.start(), m.end()) for m in _TOKEN.finditer(low)]
        out: list[Match] = []
        i = 0
        while i < len(toks):
            hit: Match | None = None
            for n in range(min(self.max_len, len(toks) - i), 0, -1):
                key = tuple(t[0] for t in toks[i:i + n])
                phrase = self._phrases.get(key)
                if phrase is not None:
                    hit = Match(phrase, toks[i][1], toks[i + n - 1][2])
                    i += n
                    break
            if hit is None:
                i += 1
            else:
                out.append(hit)
        return out


def load_list(name: str) -> list[str]:
    """One phrase per line from vocab/<name>; '#' comments and blanks dropped,
    lower-cased."""
    path = VOCAB / name
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.lower())
    return out


@lru_cache(maxsize=None)
def matcher(name: str) -> PhraseMatcher:
    return PhraseMatcher(load_list(name))


def hits(name: str, text: str) -> list[Match]:
    if not text:
        return []
    return matcher(name).find(text)
