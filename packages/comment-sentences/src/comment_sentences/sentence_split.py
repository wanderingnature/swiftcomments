"""The sentence splitter, on its own: the record's Step 8 split and the constants it and the comment
line handling read."""
from __future__ import annotations

import re

# A piece shorter than this many words is a fragment: joined to its neighbour (Step 8).
FRAGMENT_WORDS = 4
# A body line at least this long that ends without sentence punctuation is a cut paragraph
# and is joined to the next body line (Step 3); a shorter one is a plain-text subhead
# candidate, listed by the Step 3 check.
REJOIN_MIN_CHARS = 80
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "al", "e.g", "i.e", "seq", "p", "pp", "no", "nos", "sec",
    "secs", "fed", "reg", "vol", "vols", "ch", "fig", "figs", "approx", "pub", "gen", "tech",
    "rep", "st", "mt", "inc", "co", "corp", "v", "vs", "ed", "eds", "cf", "ca", "jan", "feb",
    "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec", "cir", "supp", "app",
    "ltd", "dept", "est", "misc", "para", "paras", "doc", "ave", "rd", "hwy", "mo", "yr", "yrs",
    "ft", "sq", "mi", "hr", "hrs", "min", "max", "dist", "fsm", "fsh", "ph", "rel", "ex",
}
LIST_RE = re.compile(r"^(?:- (?:• )?|• |■ |☒ |☐ |\d{1,2}\. |\((?:[a-z]|[ivx]+|\d{1,2})\) |[a-z]\. )")
TERMINAL = ".!?:;\"”’'”)]…"


def ends_sentence(text: str) -> bool:
    return bool(text) and text[-1] in TERMINAL


def split_sentences(s: str) -> list[tuple[int, int]]:
    """Sentence spans of a paragraph (Step 8). An end: . ? or !, closing quotes or brackets,
    whitespace, then an uppercase letter, a digit or an opening quote or bracket. Not an end: a
    listed abbreviation, a single capital and a period (initials, U.S.), a period inside a
    number or a citation. Fragments join their neighbour."""
    ends = []
    for m in re.finditer(r"([.?!]+)([\"'’””)\]]*)(\s+)(?=[\"“‘'(\[]?[A-Z0-9])", s):
        p = m.start()
        before = s[:p]
        prev_char = before[-1:] if before else ""
        if prev_char in ")]\"'’”":
            ends.append(m.end())
            continue
        token = re.split(r"\s", before)[-1] if before else ""
        core = token.rstrip(".").lower()
        core = re.sub(r"^[(\[\"'“‘]+", "", core)
        if core in ABBREVIATIONS:
            continue
        if re.search(r"(^|\.)[a-z]$", core):
            continue
        if re.fullmatch(r"\d{1,2}", core) and m.group(1) == "." and False:
            continue
        ends.append(m.end())
    bounds = [0] + ends + [len(s)]
    pieces = [(bounds[k], bounds[k + 1]) for k in range(len(bounds) - 1) if s[bounds[k]:bounds[k + 1]].strip()]

    def words(a, b):
        return len(re.findall(r"[A-Za-z0-9]+", s[a:b]))

    # a fragment joins the piece before it; one that opens the paragraph joins the piece after
    out: list[list[int]] = []
    for a, b in pieces:
        if words(a, b) < FRAGMENT_WORDS and out:
            out[-1][1] = b
        else:
            out.append([a, b])
    if len(out) >= 2 and words(*out[0]) < FRAGMENT_WORDS:
        out[1][0] = out[0][0]
        out.pop(0)
    return [(a, b) for a, b in out]
