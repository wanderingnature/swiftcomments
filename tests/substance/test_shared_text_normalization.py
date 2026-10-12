"""The sentence splitter and the boilerplate key, on the cases that broke them.

No DB, no LLM. Each case is a measured defect: a decimal split in two, a tag with
attributes left inside a key, an entity escaped twice, a curly quote or a
dangling comma making two keys of one sentence.

    uv run pytest tests/substance/test_shared_text_normalization.py
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "substance"))

import shared_text as st  # noqa: E402  # pyright: ignore[reportMissingImports]


def _pieces(text):
    return [s for _a, _b, s in st.sentences(text)]


# ---- splitter -----------------------------------------------------------

def test_decimal_is_not_a_boundary():
    text = "The backlog is roughly 6.9 billion dollars. It opens 18.2 million acres."
    assert _pieces(text) == ["The backlog is roughly 6.9 billion dollars",
                             " It opens 18.2 million acres"]


def test_lone_letter_abbreviations_are_not_boundaries():
    text = "The U.S. Forest Service (e.g. Region 1) cites p. 12. Next sentence."
    assert _pieces(text) == ["The U.S. Forest Service (e.g. Region 1) cites p. 12",
                             " Next sentence"]


def test_titles_and_citation_abbreviations_are_not_boundaries():
    text = "Ms. Smith and DeVelice et al. agree. Dr. Jones does not."
    assert _pieces(text) == ["Ms. Smith and DeVelice et al. agree", " Dr. Jones does not"]


def test_domains_and_addresses_stay_whole():
    text = "See www.fs.usda.gov/roadless or write to someone@gmail.com. Thanks."
    assert _pieces(text) == ["See www.fs.usda.gov/roadless or write to someone@gmail.com",
                             " Thanks"]


def test_ordinary_boundaries_still_split():
    text = "First sentence. Second!<br/>Third? Fourth.\nFifth... Sixth"
    assert _pieces(text) == ["First sentence", " Second", "<br/>Third", " Fourth",
                             "Fifth", " Sixth"]


def test_spans_index_the_original_text():
    text = "Costs 6.9 billion. Then more."
    for a, b, s in st.sentences(text):
        assert text[a:b] == s


# ---- key ----------------------------------------------------------------

def test_tag_with_attributes_is_stripped():
    plain = "Roadless areas within the National Forest System also contain watersheds"
    marked = "<span style='padding-left: 30px'></span>" + plain
    assert st.norm_sentence(marked) == st.norm_sentence(plain)


def test_tag_prefix_is_not_a_tag():
    # '<bold>' and '<brand>' are not in the whitelist; only whitespace may follow the name
    assert st.norm_sentence("<bold>x</bold>") == "<bold>x</bold>"


def test_double_escaped_entity_unescapes_to_a_fixed_point():
    assert st.norm_sentence("the agency&amp;#39;s proposal") == "the agency's proposal"
    assert st.unescape_text("&amp;quot;America First&amp;quot;") == '"America First"'


def test_curly_quotes_dashes_and_nbsp_fold():
    curly = "the agency’s plan — “bold” move"
    straight = "the agency's plan - \"bold\" move"
    assert st.norm_sentence(curly) == st.norm_sentence(straight)


def test_trailing_punctuation_is_dropped():
    assert st.norm_sentence("supply drinking water to 25 million people,") == \
        st.norm_sentence("supply drinking water to 25 million people")


def test_display_form_keeps_case_and_punctuation():
    assert st.unescape_text("DeVelice &amp; Martin(2001)") == "DeVelice & Martin(2001)"
