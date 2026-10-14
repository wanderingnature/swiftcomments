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

v3 is the reduced-ask instrument: docs/design/reduced-ask-scoring-instrument.md.
"""

import os

SCORING_INSTRUMENT = "v3"


def llm_var(suffix: str) -> str:
    """The value of an LLM_* variable for the server the command runs against.
    One server is the plain set (LLM_BASE_URL, LLM_API_KEY, LLM_MODEL,
    LLM_PROVIDER, LLM_STREAM). A second server is a named set in the same .env,
    LLM_<NAME>_BASE_URL and so on, chosen for one command with LLM_SERVER=<NAME>
    (make's SERVER=<NAME>), so a run against another server is one word on the
    command line and .env is never edited back and forth."""
    server = (os.environ.get("LLM_SERVER") or "").strip().upper()
    name = f"LLM_{server}_{suffix}" if server else f"LLM_{suffix}"
    return (os.environ.get(name) or "").strip()


def llm_server_label() -> str:
    """How a log names the server a run used: the named set, or the plain one."""
    server = (os.environ.get("LLM_SERVER") or "").strip().upper()
    return f"server {server} of .env" if server else "the server of .env"


# One model, one server, one name: the reader's (plan 5.2, edit 8). LLM_MODEL in
# .env is the name the reader's server gives Qwen3.8-27B; it is the name a row is
# STAMPED with, the name the queue and the assembler compare, the name the corpus
# is scored with. rtca kept a table of every serving name of the model it was run
# through; a reader has one serving, so the name is the model.
def configured_model() -> str:
    """The model named in .env. Refuses an empty one: a row stamped with nothing
    cannot be told from a row stamped by nothing."""
    name = llm_var("MODEL")
    if not name:
        server = (os.environ.get("LLM_SERVER") or "").strip().upper()
        var = f"LLM_{server}_MODEL" if server else "LLM_MODEL"
        raise SystemExit(
            f"{var} is not set: put the model's name on your server in .env"
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
