"""SCORING_INSTRUMENT — the one instrument version the analysis reads.

Every substance score row carries `instrument_version`, because scores from two
instruments are not comparable: v1 invented LAW and credited generalities, and
v2 asked the model for 31 values in 15 fields, most of which it varied on
between runs of the same comment.

That version was written into eleven places as the literal `'v2'` — the
eligibility predicate, the assembler, the answerability rater, the report
queries and four CLI defaults. This is the one place now, so moving the corpus
to a new instrument is a single edit and no reader can be left behind on the
old one.

Older rows are KEPT. Nothing deletes a score; the corpus keeps its history and
`instrument_version` is what tells one generation from another. But nothing
downstream READS them: every predicate above filters on this value, so the
analysis is one instrument's work throughout.

Changing this constant asserts that the corpus has been re-scored under the new
instrument. Before that run lands, downstream readers find nothing — loudly,
and that is the intended failure. A silently mixed-instrument analysis is the
thing this constant exists to prevent.

v3 is the reduced-ask instrument: docs/instruments/substantive-scoring-v3.md.
"""

import os

SCORING_INSTRUMENT = "v3"


# One model, one server, one name: the reader's. LLM_MODEL in
# .env is the name the reader's server gives Qwen3.8-27B; it is the name a row is
# STAMPED with, the name the queue and the assembler compare, the name the corpus
# is scored with. A reader has one serving, so the name is the model.
def configured_model() -> str:
    """The model named in .env. Refuses an empty one: a row stamped with nothing
    cannot be told from a row stamped by nothing."""
    name = (os.environ.get("LLM_MODEL") or "").strip()
    if not name:
        raise SystemExit(
            "LLM_MODEL is not set: put the model's name on your server in .env"
            " (see .env.example and docs/model-server.md)")
    return name


def model_of(serving_name: str) -> str:
    """The model behind the name a call is made with — what a row is stamped
    with. One serving, so the name is the model; an empty name is refused."""
    name = (serving_name or "").strip()
    if not name:
        raise SystemExit("no model name was given: set LLM_MODEL in .env or pass --model")
    return name


def weights_of(model) -> str:
    """The model behind a STORED name, for comparing rows."""
    return (model or "").strip()


def is_measured_model(model: str) -> bool:
    """True when `model` is the name the corpus is scored with (LLM_MODEL)."""
    return same_weights(model, configured_model())


def same_weights(a, b) -> bool:
    """True when two stored names are the same model. The scoring queue counts a
    row as already called only under the model the run is using, and the
    assembler reads only such parts."""
    a = weights_of(a)
    b = weights_of(b)
    if not a or not b:
        return False
    return a == b
