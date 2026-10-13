# Running a step on a sample, then jumping to its result

To learn the method, run one step on a few hundred units, look at the rows it wrote
in the console, read the code beside them, and move on without the hours the full
step takes. Moving on means loading the step's full result from the reference run of
this repository, so the next step has what it needs. Running everything is still the
reference: `make check` compares a run from the empty file.

Two things, per step: `LIMIT=N`, which runs the step on the first N units of its
queue and writes them; and `make jump STEP=<target>`, which loads the reference rows for
that step and every step before it.

The rows a jump loads are what this repository's own code produced in the reference
run, step by step, in a clone; the extracts are those tables, one file per step. A
reader can fast-forward through the steps with them, compare their own run against
the reference step by step, or change the code and compare the result with the
reference.

## LIMIT, step by step

`LIMIT=N` means the same thing everywhere: the first N units of the step's queue are
processed and written, the step prints what it did and exits. Running the step again
without LIMIT does the rest, or, for a step that replaces its table, the whole. A step
whose output is a partition or an aggregate over every comment has no LIMIT: a partial
result would be a different result, not a sample of this one, and those steps run in
minutes.

| target | unit | LIMIT=N |
|---|---|---|
| `corpus` | record | none: one pass over the download, minutes; every step reads the whole corpus |
| `dedup` | comment | none: copies are found across the whole corpus |
| `ngrams` | comment | none: the near-duplicate groups need every comment's n-grams |
| `ner` | comment | the first N comments of the population with no entities yet; the step is incremental, so the next run continues |
| `tag` | comment | about the first N unscanned comments per pass, in whole batches; the passes are incremental |
| `floor` | comment | the first N of the population by comment id; the table is replaced, so the whole run later replaces the sample |
| `groups` | | none: a partition of every comment |
| `screen` | survivor | the first N survivors; replaced by the whole run later |
| `stance` | group | the first N groups, stored and loaded; the log's closing lines give the `--resume` command |
| `score` | comment | the first N of the queue |
| `assemble` | | none: inheritance over every campaign |
| `rate` | | none: minutes |
| `fetch` | file | the first N files |
| `text` | file | the first N pending files |
| `attachments` | file, letter | the OCR's first N pending scans; the roster's first N letters; the accounting runs whole, seconds |
| `orgs` | | none: minutes |
| `facts` | | none: one query |

Every step with a LIMIT says so when it starts: how many of how many, and that the
rest comes from running without LIMIT or from `make jump`.

## Jump

One extract per target, `extracts/<target>.sqlite`: a SQLite file holding exactly the
tables that target writes, as they stood after it ran, without indexes and without
the comment text. The corpus has no extract: the repository ships the download, and
`make corpus` rebuilds the table in minutes. The fetch has none: it writes files.

```
make jump STEP=floor
```

loads, for every step from `dedup` up to and including `floor`, the extract's tables
into the file, replacing what the file holds for them. The jump is cumulative on
purpose: a step's rows are only right over the rows of the steps before it, so a
reader who ran step 6 on a sample and jumps to it gets steps 2 to 6 whole. Every
extract needed is checked before anything is written, and the foreign keys are
checked whole at the end. Loading is idempotent.

Run the sample before the jump, not after: the jump replaces the table. A model
step's rows carry the instrument and model stamps, so a row from a jump is
recognisable as the reference run's.

## Making the extracts

```
make extract STEP=floor      # writes extracts/floor.sqlite
```

copies the tables the floor writes, as they stand in `data/roadless.sqlite` now, to
`extracts/floor.sqlite`. It runs no step and reads nothing but the file, so it is
independent of every other extract: take it any time after `make floor` has finished,
before or after the later steps have run, in any order, one step at a time. The only
condition is that the step has not been run again since, because the extract is a
copy of what the tables hold at the moment it is taken. It refuses to overwrite an
extract that exists; to replace one, run the script with `--force`:

```
uv run python scripts/dump_extract.py --target floor --force
```

The corpus and the fetch are not extracted (above). This is how the reference extracts are
made, and how a reader makes their own after changing a step.

The registry of step to tables is `shared/steps.py`; the console's Steps page, the
dump and the load read it. `extracts/` is git-ignored.
