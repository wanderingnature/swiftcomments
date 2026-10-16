# The model-free reading: `make score-model-free`

Step 6 has two readings of the same comments. `make score-model` sends every class A
comment to the language model with the v3 instrument. `make score-model-free` reads the
same comments by rule alone: no model call, nothing to run but Python and spaCy, the
same eight dimensions, the same strength, gate and band, the same A0 to A3 rating. It
is the `model_free` package, rule set 3, in `scripts/model_free/`.

Both run on the same class A population from the screen, each with its own queue:
a comment one has read is still in the other's queue until that one reads it. The
two are set side by side by a third command of their own (below). A reader who has no model
server can run the whole method with this reading alone; a reader who has one can run
both and see where a rule and a model part.

## Running it

```
make score-model-free                    # every class A comment the rules have not scored
make score-model-free LIMIT=200          # the first 200 of them, then exit
```

A run scores every class A comment that has no comment score under the current rule
set version, and writes its rows in one transaction: an interrupted run leaves nothing.
A second run on the same file scores nothing. The comments are the screen's class A, so
`make screen` has to have run; the tags of `make tag` are read for the confirmed
citations and authorities. The population is read whole, one comment per unit.

Ad hoc, from the command line, any text at all:

```
uv run python scripts/model_free/run.py text "The DEIS fails to analyze sediment delivery to bull trout habitat in Wilson Creek."
uv run python scripts/model_free/run.py report      # counts by band, gate, level and rule
```

## What it reads, and what it cannot

| input | here |
|---|---|
| the comment's stored text | `comment.comment_text`, normalised as the package normalises (entities unescaped, tags out, quotes straightened, whitespace collapsed) |
| the class A population | `substance_screen`, as `make score-model` reads it |
| the confirmed citations and legal authorities of each comment | `comment_cited_references`, `comment_authorities` (`matched_text`) |
| the match keys of every known authority | `legal_authority.match_keys` |
| the place list | `seeds/entity_tagging/seed_places.csv`, the file the v3 grader reads too |
| the 27 vocabulary lists | `scripts/model_free/vocab/` |
| spaCy `en_core_web_md` | the parse: parts of speech, dependencies, entities |

Three inputs of the package are not read: the sentence table (so the whole
comment is the unit), the record's own sentences and
figures (so no sentence is marked as the agency's text, and a figure that appears in
the DEIS is not an anchor for the generality test), and the sentence vectors (so the
similarity of an alternative to the DEIS's alternatives is not measured; it was
recorded, never thresholded).

## What it writes

Five tables, schema section 9b, the package's own: `mf_score_run` (one row per run),
`mf_sentence_score` (one row per unit, here one per comment: the eight levels,
strength, gate, band, moves, targets, anchors), `mf_sentence_hit` (every rule that
fired, with the matched words and their offsets), `mf_comment_score` and
`mf_comment_answerability`. Every row carries `ruleset_version`. The console's Steps
page shows the counts; `make extract STEP=score-model-free` and `make jump STEP=score-model-free`
work as for any step.

## Setting the two readings side by side

```
make score-model-compare LIMIT=20                  # the model of .env
make score-model-compare LIMIT=20 SERVER=LOCAL     # the second server of .env
```

A command of its own, apart from the two scoring steps, with its own queue. It picks
`LIMIT` class A comments, the ones `make score-model` reads as themselves (a group's
carrier outside every family, on all of its text), sorted by comment id and taken at
even steps across the list, so twenty comments span the docket rather than its first
days. It reads each with the model and with the rules, and writes one JSON file per
comment per reading under `compare/<run>/model/` and `compare/<run>/model-free/`,
in one shape (`shared/score_json.py`): the comment id, which scorer, which instrument,
the eight levels, strength, gate, gate basis, band, the A level, and the evidence,
which is the model's spans on one side and the rules' hits on the other. It writes
nothing to `data/roadless.sqlite`: both scoring steps still have every comment of
their queues to read, and a comparison never stands in for either.

It then prints the comparison, and keeps it as `compare/<run>/comparison.txt`: per
dimension, how many agree exactly and which side reads higher; the gate, band and
strength agreement; then every comment where the gate differs, with both sides'
levels and evidence. The model's side carries no A level (that comes from
`make rate`, over the stored scores), so the level agreement reads "not rated on
both sides". A model call that fails is listed and its comment left out of the
comparison.
