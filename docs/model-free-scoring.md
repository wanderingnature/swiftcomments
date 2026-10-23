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

`docs/methods-scoring.md` explains the method: the sentences, the eight dimensions and
their rules, the three reading modes, answerability, how the rules were built, and the
agreement with the model reading.

## Running it

```
make score-model-free                    # every class A comment the rules have not scored
make score-model-free LIMIT=200          # the first 200 of them, then exit
make score-model-free CLASSES=B1         # every class B1 comment instead
make score-model-free CLASSES=A,B1       # both classes
```

`CLASSES` names the screen classes to read, class A by default. Class B1 is the
comments that refer to the action with a deficiency or a named entity but cite
nothing; the model reads none of them, and the rules can, at no cost, to find the
ones that would pass the gate all the same. The rules, the tables and the queue are
the same for every class: a comment is scored once under a rule set whatever class
it was asked for under, and a B1 run leaves the class A rows as they are. The
console's Substance page filters either reading by screen class, and the Overview
gives each class its own row.

A run scores every class A comment that has no comment score under the current rule
set version, and writes its rows in one transaction: an interrupted run leaves nothing.
A second run on the same file scores nothing. The comments are the screen's class A, so
`make screen` has to have run; the tags of `make tag` are read for the confirmed
citations and authorities.

The step reads every comment in hybrid mode, the package's third mode. Each comment is split into sentences by the comment-sentences package
(`packages/comment-sentences`, `stored_units`): the stored text rendered plain line
by line, each line split by the record's sentence rule, every piece under 25 letters
and digits left out. Every sentence is scored, and the whole comment is scored as one
more unit. The comment score is the whole comment's, with GAP held to what one
sentence reaches: GAP is the lower of the whole comment's GAP and the highest
sentence GAP, so GAP opens the gate only when the whole comment and one sentence both
reach 2 (`arithmetic.hybrid`). Whole mode alone paired a GAP trigger in one sentence
with a specific name in another. A comment the package leaves no sentence is not
scored, and the run says how many.

The package's other two modes, sentence (the sentences only, rolled up by maximum) and
whole (the whole comment only), are kept for ad hoc text; `make score-model-free` runs
hybrid.

Ad hoc, from the command line, any text at all:

```
uv run python scripts/model_free/run.py text --mode hybrid "The DEIS fails to analyze sediment delivery to bull trout habitat in Wilson Creek."
uv run python scripts/model_free/run.py report      # counts by band, gate, level and rule
```

## What it reads, and what it cannot

| input | here |
|---|---|
| the comment's stored text | `comment.comment_text`: split into sentences by `stored_units`, and, for the whole-comment unit, normalised as the package normalises (entities unescaped, tags out, quotes straightened, whitespace collapsed) |
| the class A population | `substance_screen`, as `make score-model` reads it |
| the confirmed citations and legal authorities of each comment | `comment_cited_references`, `comment_authorities` (`matched_text`) |
| the match keys of every known authority | `legal_authority.match_keys` |
| the place list | `seeds/entity_tagging/seed_places.csv`, the file the v3 grader reads too |
| the 26 vocabulary lists | `scripts/model_free/vocab/` |
| spaCy `en_core_web_md` | the parse: parts of speech, dependencies, entities |

The package splits each comment as it is read. Two inputs are not read: the record's
own sentences and
figures (so no sentence is marked as the agency's text, and a figure that appears in
the DEIS is not an anchor for the generality test), and the sentence vectors (so the
similarity of an alternative to the DEIS's alternatives is not measured; it was
recorded, never thresholded).

## What it writes

Five tables, schema section 9b, the package's own: `mf_score_run` (one row per run),
`mf_sentence_score` (one row per unit, every sentence and the whole comment: the eight levels,
strength, gate, band, moves, targets, anchors), `mf_sentence_hit` (every rule that
fired, with the matched words and their offsets), `mf_comment_score` (the hybrid score) and
`mf_comment_answerability`. Every row carries `ruleset_version`. A sentence's unit id
is the comment row's rowid times 100,000 plus its place in the comment from one; the
whole comment's is the negative of its first sentence's, as the package numbers it. The console's Steps
page shows the counts; `make extract STEP=score-model-free` and `make jump STEP=score-model-free`
work as for any step.

## Setting the two readings side by side

```
make score-model-compare LIMIT=20                         # the model of .env
make score-model-compare LIMIT=20 SERVER=LOCAL            # the second server of .env
make score-model-compare COMMENTS_OF=20261016_141500      # the comments of an earlier run, again
```

A command of its own, apart from the two scoring steps, with its own queue. It picks
`LIMIT` class A comments, the ones `make score-model` reads as themselves (a group's
carrier outside every family, on all of its text), sorted by comment id and taken at
even steps across the list, so twenty comments span the docket rather than its first
days. It reads each with the model and with the rules, and writes one JSON file per
comment per reading under `compare/<run>/model/` and `compare/<run>/model-free/`,
in one shape (`shared/score_json.py`): the comment id, which scorer, which instrument,
the eight levels, strength, gate, gate basis, band, the A level, and the evidence,
which is the model's spans on one side and the rules' hits on the other.

Every run is kept in the file, in two tables of its own (schema section 9c):
`score_compare_run`, one row per run, stamped with the code it ran (the git commit,
and whether tracked files had uncommitted changes), the model, the server, the
instrument, the rule set and the comparison it printed; and `score_compare_reading`,
one row per comment per method holding the reading in the files' shape, or the error
of a failed call. The scoring steps' own tables are not touched: both still have every
comment of their queues to read, and a comparison never stands in for either.
`COMMENTS_OF=<run>` reads the comments of an earlier run again, so a change to the
code, the instrument, the rules or the model is measured on exactly the comments the
earlier run read; it stops, naming them, if any of those comments is no longer one the
model reads as itself. The console's Compare page (`docs/console.md`) lists the runs
and sets any two readings of any two runs side by side.

It then prints the comparison, and keeps it as `compare/<run>/comparison.txt` and in
the run's row: per dimension, how many agree exactly and which side reads higher; the
gate, band and strength agreement; then every comment where the gate differs, and
every comment where the gate agrees and a level does not, with both sides' levels and
evidence. The model's side carries no A level (that comes from
`make rate`, over the stored scores), so the level agreement reads "not rated on
both sides". A model call that fails is listed and its comment left out of the
comparison.
