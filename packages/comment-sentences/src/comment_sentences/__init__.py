"""One method for splitting a comment into sentences, and the key a sentence is identified by.

The single copy: eis-analysis (comment_unit, the model-free scorer, the record units) and rtca (the
sentence layer, roadless.sentence and sentence_occurrence) both import this package; neither keeps
its own. Standard library only.

    stored_units(raw) -> (units, dropped)
        raw      the stored comment text (v_source_comments.comment_text), HTML as stored
        units    list of (start, end, text, kind): start and end are offsets into raw, from the
                 sentence's own first character to just after its terminal punctuation (markup,
                 list markers and prefixes outside); text is the rendered sentence (entities
                 unescaped, %-decoded); kind is "sentence" or "list_item"
        dropped  int, the pieces under MIN_PLAIN_CHARS (25) letters and digits left out
    sentence_hash(text) -> str: sha256 hex of norm_key(text)
    norm_key(text) -> str: unescape_text, lowercased, every non-alphanumeric removed

Test: tests/fixtures/comment_sentences.json, stored comments with their expected units.
"""
from .norm import norm_key, unescape_text
from .sentence_split import (ABBREVIATIONS, FRAGMENT_WORDS, LIST_RE, REJOIN_MIN_CHARS, TERMINAL,
                             ends_sentence, split_sentences)
from .units import MIN_PLAIN_CHARS, plain_lines, sentence_hash, stored_units, units

__all__ = ["ABBREVIATIONS", "FRAGMENT_WORDS", "LIST_RE", "MIN_PLAIN_CHARS", "REJOIN_MIN_CHARS", "TERMINAL",
           "ends_sentence", "norm_key", "plain_lines", "sentence_hash", "split_sentences", "stored_units",
           "unescape_text", "units"]
