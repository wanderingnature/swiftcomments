"""The n-gram extractor on the shared tokenizer: spans, sentences, hashes.

No DB, no LLM. The extractor reads shared.text_norm since 2026-09-20; what
changed for its output is pinned here: every occurrence carries the character
span of its tokens, sentence_position comes from the same splitter the
sentence keys use, markup variants of one sentence hash identically (R2), and
numerals make '18.2 million acres' and '58 million acres' different n-grams.

The module is loaded by path: comments_db/src and the repo's top-level src
are both packages named `src`, and importing one after the other in a pytest
session resolves to whichever came first.

    uv run pytest tests/substance/test_long_ngram_extractor.py
"""
import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

_spec = importlib.util.spec_from_file_location(
    "long_ngram_extractor",
    _REPO_ROOT / "comments_db" / "src" / "extractors" / "long_ngram_extractor.py")
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
LongNgramExtractor = _mod.LongNgramExtractor

from shared import text_norm as tn  # noqa: E402


def _extractor():
    return LongNgramExtractor(min_n=6, max_n=8, remove_stopwords=False, lowercase=True)


def _flat(by_size):
    return [ng for size in sorted(by_size) for ng in by_size[size]]


def test_ngram_span_covers_exactly_its_tokens():
    text = "Roadless areas protect drinking water for millions of Americans nationwide."
    toks = tn.tokenize(text)
    out = _extractor().extract_with_positions(text, filter_stopword_redundancy=False)
    for size, ngrams in out.items():
        for ng in ngrams:
            i = ng["position"]
            assert ng["char_start"] == toks[i].start
            assert ng["char_end"] == toks[i + size - 1].end
            covered = text[ng["char_start"]:ng["char_end"]]
            assert [t.text for t in tn.tokenize(covered)] == list(ng["ngram"])


def test_edge_stopword_filter_drops_ngrams_that_start_or_end_with_one():
    text = ("the forest service must protect the roadless areas of the nation"
            " for the generations that follow")
    ex = _extractor()
    unfiltered = _flat(ex.extract_with_positions(text, filter_stopword_redundancy=False))
    filtered = _flat(ex.extract_with_positions(text, filter_stopword_redundancy=True))
    assert len(filtered) < len(unfiltered)
    for ng in filtered:
        assert ng["ngram"][0] not in ex.STOPWORDS
        assert ng["ngram"][-1] not in ex.STOPWORDS


def test_sentence_position_uses_the_shared_splitter():
    text = ("The backlog is roughly 6.9 billion dollars for maintenance today."
            " Second sentence carries enough words to make an n-gram here.")
    out = _extractor().extract_with_positions(text, filter_stopword_redundancy=False)
    second_start = text.index("Second")
    for ng in _flat(out):
        expected = 0 if ng["char_start"] < second_start else 1
        assert ng["sentence_position"] == expected, ng


def test_markup_variants_of_one_sentence_hash_identically():
    a = "Please keep the roadless rule intact for future generations<br/>Thank you"
    b = "Please keep the roadless rule intact for future generations<br/><br/>Thank you"
    ex = _extractor()
    ha = {ng["hash"] for ng in _flat(ex.extract_with_positions(a))}
    hb = {ng["hash"] for ng in _flat(ex.extract_with_positions(b))}
    assert ha == hb
    assert all("br" not in ng["ngram"] for ng in _flat(ex.extract_with_positions(a)))


def test_numerals_distinguish_ngrams():
    a = "rescission opens 18.2 million acres of roadless forest to logging"
    b = "rescission opens 58 million acres of roadless forest to logging"
    ex = _extractor()
    ha = {ng["hash"] for ng in _flat(ex.extract_with_positions(a))}
    hb = {ng["hash"] for ng in _flat(ex.extract_with_positions(b))}
    assert ha != hb
    assert any("18.2" in ng["ngram"] for ng in _flat(ex.extract_with_positions(a)))


def test_tokenize_returns_surfaces_only():
    assert _extractor().tokenize("We don't agree, USFS & BLM.") == [
        "we", "do", "not", "agree", "usfs", "and", "blm"]
