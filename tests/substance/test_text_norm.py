"""The shared tokenizer: every token's span lands on its own characters.

No DB, no LLM. shared/text_norm.py is the one normalizer the sentence keys
and the n-gram extractor both read. What these cases pin down: offsets survive
markup blanking and entity unescaping, an expanded contraction's tokens share
one span, numerals are tokens, a URL or address yields nothing, and the
re-export through shared_text is the same function.

    uv run pytest tests/substance/test_text_norm.py
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

from shared import text_norm as tn  # noqa: E402
import shared_text  # noqa: E402  # pyright: ignore[reportMissingImports]


def _surfaces(text, **kw):
    return [t.text for t in tn.tokenize(text, **kw)]


def _slices(text):
    return [text[t.start:t.end] for t in tn.tokenize(text)]


# ---- spans ---------------------------------------------------------------

def test_plain_words_have_exact_spans():
    text = "Please keep the Roadless Rule intact."
    assert _surfaces(text) == ["please", "keep", "the", "roadless", "rule", "intact"]
    assert [s.lower() for s in _slices(text)] == _surfaces(text)


def test_markup_is_blanked_and_offsets_survive():
    text = "Please<span style='padding-left: 30px'>keep</span> the<br/>rule."
    toks = tn.tokenize(text)
    assert [t.text for t in toks] == ["please", "keep", "the", "rule"]
    assert [text[t.start:t.end] for t in toks] == ["Please", "keep", "the", "rule"]


def test_tag_prefix_is_not_a_tag():
    assert _surfaces("<bold>text</bold>") == ["bold", "text", "bold"]


def test_expanded_contraction_shares_one_span():
    text = "We don&amp;#39;t agree."
    toks = tn.tokenize(text)
    assert [t.text for t in toks] == ["we", "do", "not", "agree"]
    do, not_ = toks[1], toks[2]
    assert (do.start, do.end) == (not_.start, not_.end)
    assert text[do.start:do.end] == "don&amp;#39;t"


def test_curly_apostrophe_contraction_expands():
    assert _surfaces("They won’t listen") == ["they", "will", "not", "listen"]


def test_numerals_are_tokens_and_decimals_stay_whole():
    text = "It opens 18.2 million acres; the backlog is $6.9 billion over 6,000 miles."
    toks = tn.tokenize(text)
    surfaces = [t.text for t in toks]
    assert "18.2" in surfaces and "6.9" in surfaces and "6000" in surfaces
    t18 = toks[surfaces.index("18.2")]
    assert text[t18.start:t18.end] == "18.2"
    t6000 = toks[surfaces.index("6000")]
    assert text[t6000.start:t6000.end] == "6,000"     # a comma removed: whole candidate


def test_hyphen_and_domain_split_with_exact_subspans():
    text = "the roadless-area rule at fs.usda.gov"
    toks = tn.tokenize(text)
    assert [t.text for t in toks] == ["the", "roadless", "area", "rule", "at", "fs", "usda", "gov"]
    assert [text[t.start:t.end] for t in toks] == [t.text for t in toks]


def test_url_and_email_yield_nothing():
    text = ("See https://www.fs.usda.gov/roadless or www.example.org or write"
            " someone@gmail.com now")
    assert _surfaces(text) == ["see", "or", "or", "write", "now"]


def test_ampersand_is_and():
    text = "USFS & BLM"
    toks = tn.tokenize(text)
    assert [t.text for t in toks] == ["usfs", "and", "blm"]
    assert text[toks[1].start:toks[1].end] == "&"


def test_single_letters_are_dropped_by_default():
    assert _surfaces("I have a plan") == ["have", "plan"]
    assert _surfaces("I have a plan", min_alpha=1) == ["i", "have", "a", "plan"]


def test_nbsp_and_accent_fold():
    text = "café menu"
    assert _surfaces(text) == ["cafe", "menu"]


# ---- lines and sentences --------------------------------------------------

def test_lines_break_on_newline_and_markup():
    text = "Dear Chief,<br/>Please keep the rule.<br/><br/>Thank you,\n  Jane Smith  "
    assert [text[a:b] for a, b in tn.lines(text)] == [
        "Dear Chief,", "Please keep the rule.", "Thank you,", "Jane Smith"]


def test_sentence_index_follows_the_splitter():
    text = "First one. Second has 6.9 in it. Third"
    at = tn.sentence_index(text)
    assert at(0) == 0
    assert at(text.index("Second")) == 1
    assert at(text.index("6.9")) == 1          # a decimal is not a boundary
    assert at(text.index("Third")) == 2


# ---- the re-export --------------------------------------------------------

def test_shared_text_reexports_the_same_functions():
    assert shared_text.norm_sentence is tn.norm_sentence
    assert shared_text.unescape_text is tn.unescape_text
    assert shared_text.norm_key is tn.norm_key
    assert shared_text.sentences is tn.sentences


def test_norm_sentence_and_token_agree_on_characters():
    text = "Roadless “Areas” &amp; Watersheds"
    assert tn.norm_sentence(text) == 'roadless "areas" & watersheds'
    assert _surfaces(text) == ["roadless", "areas", "and", "watersheds"]
