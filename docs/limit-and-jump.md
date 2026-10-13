# Running a step on a sample, then jumping to its result

A design, 2026-10-13, for the operator to decide. Nothing in it is built yet.

## What a reader wants

To learn the method, a reader runs one step on a few hundred units, looks at the rows
it wrote in the console, reads the code beside them, and then moves on without paying
for the hours the full step takes. "Moving on" means loading the step's full result
from our run, so the next step has what it needs. Running everything is still
possible, and the reference run of `make check` still comes from an empty file.

So two things per step: `LIMIT=N`, which runs the step on its first N units and
writes them; and `make jump STEP=<target>`, which loads our run's rows for that step
and every step before it.

## LIMIT, step by step

`LIMIT=N` means the same thing everywhere: the first N units of the step's queue are
processed and written, the step prints what it did and exits, and running the step
again without LIMIT does the rest (or, for a step that replaces its table, the whole).
A step whose output is a partition or an aggregate over every comment is not offered
a LIMIT: a partial result would be a different result, not a sample of this one, and
the step runs in minutes anyway.

| target | unit | LIMIT=N | today |
|---|---|---|---|
| `corpus` | record | not offered: one pass over the download, minutes; every step reads the whole corpus | |
| `dedup` | comment | not offered: copies are found across the whole corpus | |
| `ngrams` | comment | not offered: the near-duplicate groups need every comment's n-grams | |
| `ner` | comment | the first N comments of the population with no entities yet | to add; the step is already incremental |
| `tag` | comment | the first N comments not yet scanned, per pass | to add; the passes are already incremental |
| `floor` | comment | the first N of the population; the table is replaced, so the whole run later replaces the sample | to add |
| `groups` | | not offered: a partition of every comment | |
| `screen` | survivor | the first N survivors; replaced by the whole run later | to add |
| `stance` | group | the first N groups, stored and loaded; `--resume` for the rest | done (plan 5.2 edit 11) |
| `score` | comment | the first N of the queue | rtca's `--limit`; kept in the port |
| `assemble` | | not offered: inheritance over every campaign | |
| `rate` | | not offered: minutes | |
| `fetch` | file | the first N files | rtca's `--limit` |
| `text` | file | the first N pending files | rtca's `--limit` |
| `attachments` | file, letter | the OCR's first N pending scans; the roster's first N letters; the accounting runs whole, seconds | rtca's `--limit` on both |
| `orgs` | | not offered: minutes | |
| `facts` | | not offered: one query | |

Every step with a LIMIT announces it: "LIMIT=N: the first N of M; run without LIMIT
for the rest, or make jump STEP=<target> for our run's rows."

## Jump: our run's rows, one file per step

One extract per target, `extracts/<target>.sqlite`: a SQLite file holding exactly the
tables that target writes (the list in plan §1 and in the console's `queries.py`;
one registry, `steps.py`, feeds all three), with the schema's DDL for those tables and
nothing else. Built in the operator's clone as the run proceeds, after each step is
proven:

```
uv run python scripts/dump_extract.py --target floor      # writes extracts/floor.sqlite
```

Loaded by the reader:

```
make jump STEP=floor
```

which, for `corpus` up to and including `floor`, downloads the extract if it is not
under `extracts/` and loads it: ATTACH, DELETE the target's tables, INSERT each from
the extract, DETACH; `comment_facts` is CREATE TABLE AS. The jump is cumulative on
purpose: a step's rows are only right over the rows of the steps before it, so a
reader who ran step 6 on a sample and jumps to it gets steps 1 to 6 whole. Loading is
idempotent; the rows a reader already had are replaced by the same rows.

A sample is run before the jump, not after: the jump replaces the table. A model
step's rows carry our instrument and model stamps, so a row from a jump is
recognisable as ours.

## Where the extracts live, and how big they are

Not in git. The README's "nothing we computed ships as data" becomes: our run's rows
are available as extracts for jumping ahead, downloaded on request; the method stands
without them and the check is run from an empty file.

Measured on the workbench's file (corpus, dedup and n-grams loaded), table pages only,
indexes excluded:

| table | MB |
|---|---|
| `comment` | 841 |
| `long_ngrams` | 244 |
| `comment_long_ngrams` | 221 |
| `comment_dedup` | 88 |
| `attachment_file` | 2 |

The download's text compresses about nine to one (683 MB of CSV, 72 MB gzipped), so a
corpus extract gzips to under 100 MB and the n-grams to perhaps 60. The stance's
`classification_topics` (2,425,255 rows of phrases on the pilot alone, which covered
182,209 comments) will be the other large one. Every extract fits a GitHub release
asset (2 GB each); the whole file after `make facts` may not, and one file per step
is what the jump needs anyway. The corpus extract is optional: `make corpus` builds
the same table from the download in minutes, so `jump` can start at `dedup`.

Hosting is the decision: a GitHub release of this repository, or a bucket, named by
one `EXTRACTS_URL` in `.env.example`.

## What is built, in order

1. `steps.py`: the registry, target to tables written, in run order; the console's
   Steps page reads it in place of its own list.
2. `scripts/dump_extract.py` and `scripts/load_extract.py`, `make jump STEP=`, with a
   test over a temporary file: dump a step, load it into an empty schema, same rows.
3. `LIMIT=N` on `ner`, `tag`, `floor` and `screen`, each announcing it; `score`,
   `fetch`, `text` and the OCR and roster keep rtca's `--limit` as they are ported.
4. The extracts, produced in the clone after each step as the run proceeds.
5. README: the sample-then-jump paragraph in the steps section; `docs/console.md`
   unchanged; `.env.example` gains `EXTRACTS_URL`.
