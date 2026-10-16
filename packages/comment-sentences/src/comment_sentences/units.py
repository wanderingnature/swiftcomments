"""Comment sentences by the record's method: the stored comment text rendered plain, line by
line, and each line split with `sentence_split.split_sentences` (the same terminator,
abbreviation and fragment rules the record units get).
A line that starts with a list marker (the record's markers, and the bullets comments use: `* `,
`– `, `· `, a bullet, asterisk, hyphen, plus or tilde glued to the word, `a) `, `1) `) is a list
item with the marker off; a `> ` quote marker, a markdown heading marker and stray punctuation at
the start of a line come off. Comment-form artifacts the record never has are repaired before the
split: markdown `**` and `~~` and zero-width spaces dropped; a comment submitted URL-encoded
decoded (when `%20` occurs three times or more, or `%0A` twice); a full stop with no space before the next
sentence ("gone.We live", "forest.”Please", "one!https://") given its space; lines the form joined with a bare
comma ("Sincerely,Brian") parted; and for a writer who does not capitalise, the letter after each
full stop read as upper case when the spans are found. A long line that ends
without sentence punctuation is a cut paragraph and joins the next line (REJOIN_MIN_CHARS, as the
record's step 3), unless it ends in a URL or is an attribution line ("— Source, year"). Every unit
keeps its span in the stored text. The sentence hash is sha256 of
`norm.norm_key`, the key `sentence_embedding` is stored under, so a sentence already embedded
is found and not sent again."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import unquote

from .norm import _unescape, norm_key
from .sentence_split import LIST_RE, REJOIN_MIN_CHARS, ends_sentence, split_sentences

# a tag, an entity (escaped any number of times over: '&amp;#39;'), a newline, markdown bold or
# strike markers, a zero-width space; in a URL-encoded comment, a run of %XX bytes as well
_TOKEN = re.compile(r"<[^<>]+>|&(?:amp;)*#?\w+;|\r\n|\n|\r|\*\*|~~|[\u200b\ufeff]")
_TOKEN_ENCODED = re.compile(_TOKEN.pattern + r"|(?:%[0-9A-Fa-f]{2})+")
_DROP = {"**", "~~", "\u200b", "\ufeff"}
_BLOCK = re.compile(r"</?(?:br|p|div|li|ul|ol|h[1-6]|tr|table|blockquote)\b", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z0-9]")
# the record's list markers, and the bullets comments use that the record does not
_LIST = re.compile(r"^(?:[*–·∙―▸] |-{2,} ?|[-+*•~](?=[A-Za-z])|[a-z]\) |\d{1,2}\) |#\d{1,2} )|" + LIST_RE.pattern)
# a quote or markdown heading marker, or stray punctuation a cut left at the start of a line
_PREFIX = re.compile(r"^(?:>+ |#+ |[.,;:?)]+\s*)")
# a full stop between two sentences with no space after it: 'gone.We live' (two lowercase letters
# before, a capitalised word after, so 'U.S.C' and 'e.g.' and decimals are left alone), or a
# closing quote or bracket after the full stop: 'forest.”Please keep'
_GLUED = re.compile(r"(?<=[a-z]{2}[.!?])(?=[A-Z][a-z])|(?<=[.!?][\"”’)\]])(?=[A-Z][a-z])|(?<=[.!?])(?=https?://)")
# the form joined lines with a bare comma: 'Forest Service,Stop the impunity', 'Sincerely,Brian'
_COMMA_JOIN = re.compile(r"(?<=[a-z]),(?=[A-Z][a-z])")
_URL_END = re.compile(r"https?://\S+$")
# an attribution or source line ("— Landscape Ecology (Springer Nature), 2025") stands alone
_ATTRIBUTION = re.compile(r"^[—–―] ")
_SENT_START = re.compile(r"(?<=[.!?]\s)[a-z]|(?<=[.!?][\"”’)\]]\s)[a-z]")


def plain_lines(raw: str) -> tuple[str, list[int]]:
    """The stored text rendered plain: block tags and newlines are line breaks, inline tags
    spaces, entities unescaped to a fixed point. For every plain character, the stored offset
    it came from (a tag's or entity's replacement maps to the token's first character)."""
    out: list[str] = []
    idx: list[int] = []
    pos = 0
    token = _TOKEN_ENCODED if raw.count("%20") >= 3 or raw.count("%0A") >= 2 else _TOKEN
    for m in token.finditer(raw):
        for k in range(pos, m.start()):
            out.append(raw[k])
            idx.append(k)
        t = m.group(0)
        if t in _DROP:
            rep = ""
        elif t.startswith("<"):
            rep = "\n" if _BLOCK.match(t) else " "
        elif t.startswith("&"):
            rep = _unescape(t)
        elif t.startswith("%"):
            rep = unquote(t)
        else:
            rep = "\n"
        for ch in rep:
            out.append(ch)
            idx.append(m.start())
        pos = m.end()
    for k in range(pos, len(raw)):
        out.append(raw[k])
        idx.append(k)
    return "".join(out), idx


def _lines(plain: str, idx: list[int]) -> list[tuple[str, list[int]]]:
    """Each non-blank line of the plain text with its whitespace runs collapsed to one space and
    stripped, as (text, offsets) with one stored offset per character."""
    lines = []
    start = 0
    for end in [i for i, ch in enumerate(plain) if ch == "\n"] + [len(plain)]:
        text: list[str] = []
        offs: list[int] = []
        prev_space = True
        for k in range(start, end):
            ch = plain[k]
            if ch.isspace():
                if not prev_space:
                    text.append(" ")
                    offs.append(idx[k])
                prev_space = True
            else:
                text.append(ch)
                offs.append(idx[k])
                prev_space = False
        if text and text[-1] == " ":
            text.pop()
            offs.pop()
        if text:
            lines.append(("".join(text), offs))
        start = end + 1
    return lines


def _space_glued(text: str, offs: list[int]) -> tuple[str, list[int]]:
    """A space after a full stop that has none before the next sentence; the space maps to the
    offset of the character after it."""
    out_t: list[str] = []
    out_o: list[int] = []
    pos = 0
    for m in _GLUED.finditer(text):
        out_t.append(text[pos:m.start()])
        out_o.extend(offs[pos:m.start()])
        out_t.append(" ")
        out_o.append(offs[m.start()])
        pos = m.start()
    out_t.append(text[pos:])
    out_o.extend(offs[pos:])
    return "".join(out_t), out_o


def _comma_lines(lines: list[tuple[str, list[int]]]) -> list[tuple[str, list[int]]]:
    """Lines the form joined with a bare comma, apart again (the comma stays on the first)."""
    out = []
    for text, offs in lines:
        pos = 0
        for m in _COMMA_JOIN.finditer(text):
            out.append((text[pos:m.end()], offs[pos:m.end()]))
            pos = m.end()
        out.append((text[pos:], offs[pos:]))
    return out


def _shadow(text: str) -> str:
    """For a writer who does not capitalise (the line's first letter is lowercase): the text with
    the letter after each full stop upper-cased, so the record's rule sees the sentence start.
    Same length as `text`; used only to find the spans."""
    first = re.search(r"[A-Za-z]", text)
    if not first or not first.group(0).islower():
        return text
    return _SENT_START.sub(lambda m: m.group(0).upper(), text)


def units(raw: str) -> list[tuple[int, int, str, str]]:
    """(start, end, text, kind) for every sentence of the stored comment text, in order; start
    and end are offsets into the stored text; kind is 'sentence' or 'list_item'."""
    lines = _comma_lines(_lines(*plain_lines(raw)))
    joined: list[tuple[str, list[int]]] = []
    for text, offs in lines:
        if (joined and len(joined[-1][0]) >= REJOIN_MIN_CHARS and not ends_sentence(joined[-1][0])
                and not _URL_END.search(joined[-1][0]) and not _ATTRIBUTION.match(joined[-1][0])
                and not _LIST.match(text) and not _LIST.match(joined[-1][0])):
            pt, po = joined[-1]
            joined[-1] = (pt + " " + text, po + [offs[0]] + offs)
        else:
            joined.append((text, offs))
    out = []
    for text, offs in joined:
        kind = "sentence"
        q = _PREFIX.match(text)
        if q:
            text, offs = text[q.end():], offs[q.end():]
        m = _LIST.match(text)
        if m:
            kind = "list_item"
            text, offs = text[m.end():], offs[m.end():]
        text, offs = _space_glued(text, offs)
        for a, b in split_sentences(_shadow(text)):
            while a < b and text[a].isspace():
                a += 1
            while b > a and text[b - 1].isspace():
                b -= 1
            if a < b and _WORD.search(text, a, b):
                out.append((offs[a], offs[b - 1] + 1, text[a:b], kind))
    return out


# a piece with fewer letters and digits than this is not stored ("Sincerely,", a name, a date)
MIN_PLAIN_CHARS = 25
_PLAIN = re.compile(r"[^A-Za-z0-9]")


def stored_units(raw: str) -> tuple[list[tuple[int, int, str, str]], int]:
    """The sentences of the stored comment text that are written to comment_unit: `units`, less
    every piece under MIN_PLAIN_CHARS letters and digits; and how many pieces were dropped. The one
    method that splits a comment into the units it is scored and embedded by."""
    kept, dropped = [], 0
    for u in units(raw):
        if len(_PLAIN.sub("", u[2])) < MIN_PLAIN_CHARS:
            dropped += 1
        else:
            kept.append(u)
    return kept, dropped


def sentence_hash(text: str) -> str:
    return hashlib.sha256(norm_key(text).encode()).hexdigest()
