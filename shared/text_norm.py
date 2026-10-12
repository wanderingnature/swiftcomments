"""One normalizer for every reading of comment text.

Comment text arrives carrying the submission form's markup and HTML entities.
That is not content. Until 2026-09-20 two modules decided independently what
to strip: scripts/substance/shared_text.py for sentence keys and
comments_db/src/extractors/long_ngram_extractor.py for n-grams, and they
disagreed. The n-gram side tokenized raw markup, so `br please keep the
roadless rule` was the corpus's most frequent 6-gram (df 21,185) and two
copies of one sentence differing only in `<br/>` never matched (R2 in
docs/reviews/shared-text-detection-review.md). This module is the one place
both sides read, so they cannot drift apart again.

Three normal forms of a string and one tokenizer:

  norm_sentence   the boilerplate KEY: markup out, entities unescaped to a
                  fixed point, NFKD, quotes and dashes folded, lowercased,
                  whitespace collapsed, trailing punctuation dropped
  unescape_text   the DISPLAY form: markup and entities repaired, spacing
                  collapsed, case and punctuation untouched
  norm_key        the COMPARISON key: unescape_text, lowercased, every
                  non-alphanumeric character removed
  tokenize        the n-gram tokens, each carrying (start, end) offsets into
                  the ORIGINAL text, so an n-gram occurrence can be mapped
                  back to the characters it covers

plus `sentences`, the splitter that yields spans over the original text, and
`lines`, the line spans the trivial-own-text rule reads.

See docs/reference/shared-text.md and
docs/design/shared-text-families-implementation.md section 4.1.
"""

import html
import re
import unicodedata
from bisect import bisect_right
from dataclasses import dataclass

# ---------------------------------------------------------------- markup

# Comment text carries the submission form's markup. Two copies of ONE campaign
# sentence differing only in '<br/>' vs '<br/><br/>' normalized to two
# different keys, so neither reached BOILER_K and the cluster key came out
# different per copy — scattering one letter across several sub-10 clusters,
# each member then paying for its own call. Markup and entities are not
# content: strip them before the sentence becomes a key. A tag may carry
# attributes ("<span style='padding-left: 30px'>"): 2,665 roadless survivors
# do, and an unstripped one held copies of a campaign sentence apart.
_MARKUP = re.compile(
    r"</?(?:br|p|div|span|b|i|u|em|strong|li|ul|ol)(?:\s[^<>]*)?/?>",
    re.IGNORECASE)
# Typographic variants of one character are one character: curly quotes and
# en/em dashes to their ASCII forms, everything else through NFKD (which also
# turns a non-breaking space into a space). 19,958 of the 277,794 long keys on
# roadless carried a curly quote or a dash.
_FOLD = str.maketrans({"‘": "'", "’": "'", "“": '"',
                       "”": '"', "–": "-", "—": "-"})
# Punctuation left dangling at the end of a piece once the splitter took the
# terminator: 'people,' and 'people' are the same sentence.
_TRAILING_PUNCT = " ,;:'\"-)]"


def _unescape(s):
    """html.unescape to a fixed point. The submission form escaped some text
    twice ('&amp;#39;', '&amp;quot;' — six roadless survivors), and one pass
    leaves a literal '&#39;' behind."""
    while True:
        t = html.unescape(s)
        if t == s:
            return t
        s = t


def _fold(s):
    """NFKD, then the quote/dash fold, then lowercase — the character-level
    part of norm_sentence, shared with the tokenizer so a token and a
    sentence key agree on what a character is."""
    return unicodedata.normalize("NFKD", s).translate(_FOLD).lower()


def norm_sentence(s):
    return " ".join(_fold(_unescape(_MARKUP.sub(" ", s))).split()).rstrip(_TRAILING_PUNCT)


def unescape_text(s):
    """The DISPLAY form of a string the submission form encoded: markup and
    entities repaired, spacing collapsed, punctuation and case untouched.
    'DeVelice &amp; Martin(2001)' -> 'DeVelice & Martin(2001)'."""
    return " ".join(_unescape(_MARKUP.sub(" ", s)).split())


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def norm_key(s):
    """The COMPARISON key: two strings differing only in encoding, markup,
    case, punctuation or spacing are the same claim.

    The entity fix that landed in norm_sentence (see above) applied only to
    boilerplate sentences; every other place that asked "is this the same
    text?" still compared raw bytes, so one sentence encoded three ways
    ('&rsquo;', '&#39;', a literal apostrophe) counted as three distinct
    claims and was adjudicated three times. This is that comparison, once,
    for excerpts, synthesized statements and citation references alike.

    Never stored and never shown — the original text is what goes to the
    model and to the reader."""
    return _NON_ALNUM.sub("", unescape_text(s).lower())


def strip_markup(text):
    """The original with every markup match replaced by spaces of the same
    length. Every offset into the result is an offset into the original,
    which is what lets the tokenizer carry spans."""
    return _MARKUP.sub(lambda m: " " * len(m.group(0)), text)


# -------------------------------------------------------------- sentences

_SENT_SPLIT = re.compile(r"[.!?\n]+")
# A '.' does not end a sentence when it sits inside a decimal ('6.9 billion'),
# after a lone letter ('U.S.', 'e.g.', 'p. 12', an initial), after a title or
# citation abbreviation ('Ms. Smith', 'et al.'), or inside a token such as a
# domain or an e-mail address ('fs.usda.gov'). The bare split cut every one of
# those: on roadless (69,005 floor survivors) it broke 24,779 decimals, and
# 10,753 of those cuts left a piece under MIN_SENT_CHARS that was then counted
# nowhere — 'roughly 6.9 billion dollars' lost its '9 billion dollars' half.
# The list is what the corpus uses mid-sentence ('et al.' 1,097 times, 'Ms.'
# 4,016, 'pp.' 59, 'Dept.' 11). 'etc.' is left out on purpose: it ends a
# sentence 279 times for every 130 it sits inside one, and protecting it would
# merge more sentences than it mends.
_ABBREVIATIONS = frozenset((
    "mr", "mrs", "ms", "dr", "jr", "sr", "vs", "al", "pp", "inc", "dept",
    "approx"))
_WORD_BEFORE = re.compile(r"([A-Za-z]+)$")


def _protected(text, m):
    """Is this split match a '.' that does not end a sentence?"""
    if m.group(0) != ".":
        return False
    i, j = m.start(), m.end()
    before = text[i - 1] if i else ""
    after = text[j] if j < len(text) else ""
    if before.isdigit() and after.isdigit():
        return True                                    # 6.9 billion
    if after.islower():
        return True                                    # fs.usda.gov
    # Searched over a window, not from the start of the text: the engine scans
    # forward from pos, so a search from 0 is O(i) per period and O(n²) over a
    # long text (a 100 KB attachment body took minutes). A word longer than
    # the window is not an abbreviation either way.
    w = _WORD_BEFORE.search(text, max(0, i - 64), i)
    if not w:
        return False
    word = w.group(1)
    return len(word) == 1 or word.lower() in _ABBREVIATIONS   # U.S., Ms. Smith


def sentences(text):
    """(start, end, sentence) spans over the original text."""
    out = []
    pos = 0
    for m in _SENT_SPLIT.finditer(text):
        if _protected(text, m):
            continue
        if m.start() > pos:
            out.append((pos, m.start(), text[pos:m.start()]))
        pos = m.end()
    if pos < len(text):
        out.append((pos, len(text), text[pos:]))
    return out


def sentence_index(text):
    """A function mapping a character offset to the index of the sentence
    span (from `sentences`) that contains it. Offsets in the gap between two
    sentences belong to the sentence before them."""
    starts = [a for a, _b, _s in sentences(text)]

    def at(pos):
        return max(0, bisect_right(starts, pos) - 1)
    return at


# ------------------------------------------------------------------ lines

_LINE = re.compile(r"[^\n]+")


def lines(text):
    """(start, end) of every non-blank line of the original text, where a
    line ends at a newline or at a markup tag (the form's '<br/>' is a line
    break). Leading and trailing whitespace is outside the span."""
    broken = _MARKUP.sub(lambda m: "\n" + " " * (len(m.group(0)) - 1), text)
    out = []
    for m in _LINE.finditer(broken):
        piece = m.group(0)
        lead = len(piece) - len(piece.lstrip())
        trail = len(piece) - len(piece.rstrip())
        a, b = m.start() + lead, m.end() - trail
        if b > a:
            out.append((a, b))
    return out


# ----------------------------------------------------------------- tokens

@dataclass(frozen=True)
class Token:
    """One n-gram token: its normalized surface and its span in the original.

    The span is exact when the surface is a one-to-one image of the original
    characters. When it is not — an entity was unescaped, a contraction was
    expanded, NFKD changed the length, a thousands comma was removed — every
    token from that candidate carries the whole candidate's span, so a span
    always contains its token and never lands on a neighbour."""
    text: str
    start: int
    end: int


# A candidate is a maximal run of letters, digits, entities, apostrophes,
# periods, hyphens, ampersands and the characters a URL or address is written
# with. Everything else (spaces, most punctuation, tags already blanked) is a
# boundary. What a candidate becomes is decided on its normalized surface.
# An entity may be escaped more than once ('&amp;#39;'), so the entity
# alternative admits any number of leading 'amp;'.
_CANDIDATE = re.compile(
    r"(?:&(?:amp;)*#?[A-Za-z0-9]+;|[^\W_]|[‘’'.\-&@/:,])+")
_URL = re.compile(r"://|^www\.", re.IGNORECASE)
_EMAIL = re.compile(r"@[^@]*\.")
# The extractor's contraction table, applied on the normalized surface.
_CONTRACTIONS = (
    (re.compile(r"\bwon't\b"), "will not"),
    (re.compile(r"\bcan't\b"), "cannot"),
    (re.compile(r"n't\b"), " not"),
    (re.compile(r"'re\b"), " are"),
    (re.compile(r"'ve\b"), " have"),
    (re.compile(r"'ll\b"), " will"),
    (re.compile(r"'d\b"), " would"),
    (re.compile(r"'m\b"), " am"),
)
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}\b)")
# Numerals are tokens: '18.2' and '58' are not the same n-gram once the
# figure is part of it. Letters are the extractor's [a-z]{min,} rule.
_SUBTOKEN = re.compile(r"[a-z]+|\d+(?:\.\d+)?")


def _expand(surface):
    for pat, rep in _CONTRACTIONS:
        surface = pat.sub(rep, surface)
    return surface.replace("&", " and ")


def tokenize(text, min_alpha=2):
    """The n-gram tokens of `text`, in order, with offsets into `text`.

    Markup is blanked, never removed, so offsets survive. A URL or e-mail
    address yields no token. '&' yields 'and'. A contraction yields its
    expansion. Alphabetic tokens need `min_alpha` letters (2 drops 'a' and
    'I', as the extractor always has); numerals of any length are tokens."""
    out = []
    for m in _CANDIDATE.finditer(strip_markup(text)):
        raw = m.group(0)
        if _URL.search(raw) or _EMAIL.search(raw):
            continue
        surface = _fold(_unescape(raw))
        expanded = _THOUSANDS.sub("", _expand(surface))
        exact = expanded == surface and len(surface) == len(raw) and "&" not in raw
        for sm in _SUBTOKEN.finditer(expanded):
            tok = sm.group(0)
            if not tok[0].isdigit() and len(tok) < min_alpha:
                continue
            if exact:
                out.append(Token(tok, m.start() + sm.start(), m.start() + sm.end()))
            else:
                out.append(Token(tok, m.start(), m.end()))
    return out
