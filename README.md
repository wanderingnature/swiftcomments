# swiftcomments: the roadless comment analysis, reproducible

The public comments on the 2026 proposal to rescind the Roadless Area Conservation
Rule (regulations.gov docket FS-2025-0001, 390,064 records) were analysed with a
method of nine steps that find the copies and the campaign
letters, classify the stance, tag the places, laws and sources each comment names, read
the substance of the comments that have any, rate how answerable each one is, read the
attachments, and say who ran each campaign. This repository is that method as code
anyone can run, from a clone, on the public record.

It starts from the bulk download regulations.gov publishes for the docket, which ships
here gzipped, and does everything itself: the attachments are fetched from
regulations.gov, their text extracted, the scans read by OCR, every model reading made
afresh. Nothing we computed ships as data. The only data in the repository is the
seed lists the steps read (legal authorities, cited references, places, forests,
roadless areas, species, the vocabularies, the classification prompt) and two
hand-reviewed tables.

Everything lives in one SQLite file, `data/roadless.sqlite`. No PostgreSQL, no Docker,
no service of ours.

`docs/method-overview.md` explains the whole method on one page, with figures: what
question each stage answers, how the docket narrows, and how the method is measured.

## What you need

- Python 3.14 and `uv`. `uv sync` installs the Python dependencies, including the spaCy
  model `en_core_web_md` 3.8.0.
- For the attachments (step 8): poppler, whose `pdftotext` and `pdfinfo` read the PDFs.
  Debian and Ubuntu: `sudo apt install poppler-utils`. Fedora and RHEL:
  `sudo dnf install poppler-utils`. macOS with Homebrew: `brew install poppler`.
  The docx and rtf files are read by `python-docx` and `striprtf`, which `uv sync` installs.
- A model server, run locally, for the three steps that read a language model: see
  `docs/model-server.md`. The model is Qwen3.8-27B. Tested on Apple Silicon with LM
  Studio headless through `lms`; ollama and vLLM are documented, not yet verified.
- A MinerU server for the OCR of scanned attachments: see `docs/mineru.md`.
- Disk: about 20 GB for the attachments, and the SQLite file.

## Setting up

```
git clone https://github.com/wanderingnature/swiftcomments.git
cd swiftcomments
uv venv --python 3.14    # .python-version pins 3.14; uv downloads it if the machine has none
source .venv/bin/activate
uv sync
cp .env.example .env     # then fill in the two servers
make help
make schema              # creates data/roadless.sqlite and loads the seeds
make schema-add          # later: adds to a filled file the tables of steps added since, touching no row
```

`.env.example` documents every variable the pipeline reads.

## The nine steps, in the order they run

Run the targets top to bottom. Each prints what it is about to do, its progress and
the row counts it wrote, and each resumes where it stopped. The step numbers are the
method's; the run order interleaves them, because the floor precedes the families and
the groups precede the stance.

```
make corpus       step 1         one row per record of the docket; one row per attachment file
make dedup        step 2         exact and body hashes: the copies
make ngrams       step 2         6 to 8 word n-grams; the near-duplicate groups
make ner          step 5         spaCy named entities, read by the floor and the screen
make tag          step 4         legal authorities, cited references, forests, roadless areas, species, ZIP codes, by dictionary
make floor        step 6         the floor: which comments have substance to read
make groups       step 2         the text families; every comment in one group; the campaign-letter / own-text split
make screen       step 6         the mechanical screens: class A, B1, B2
make stance       step 3  MODEL  the stance: SUPPORT, OPPOSE or NEUTRAL, one reading per group, copied to its members
make score-model  step 6  MODEL  the MODEL reading: the v3 instrument over every class A comment
make score-model-free  step 6     the MODEL-FREE reading: the same comments scored by rules alone, no model call; beside the model's or instead of it
make assemble     step 6         inheritance along the campaigns, the delta rows, LAW from the citations
make rate         step 7         answerability, A0 to A3
```

That is the method's reading of the comments, and it stands on its own: no target
above reads an attachment. The attachments are the rest, 19 GB fetched from
regulations.gov and read for what each file is and who filed each letter:

```
make fetch        step 8         fetch every attachment file
make text         step 8         extract the text of every fetched file
make attachments  step 8  MODEL  what each file is; OCR of the scans that can hold a letter; what each comment counts as; the roster: who filed each letter
make orgs         step 9         who ran each campaign, on four bases
make facts                       one row per comment
make sentences    step 10        the sentences of the comments whose model-free gate is open, for the clusters
make embed        step 11  EMBED one vector for each distinct sentence, from the embedding server
make clusters     steps 12-14    one clustering case: clusters, topics, their names; make cases lists them
make docindex                    the 15 record documents: sections, chunks with page spans, vectors
make retrieve                    the 5 nearest record chunks per gate-opening sentence
make nli                         every retrieved pair read; each sentence and comment addressed, contested, or not_addressed
make check                       every figure beside checks/expected.json
```

`make sentences` begins the extension past the nine steps: the sentences of the
substantive comments grouped by meaning into clusters and topics, by code, with no
generative model (`docs/clusters.md`). `make embed` sends each distinct sentence once
to an embedding server named in `.env`. `make clusters` runs one clustering case and
records it beside the others, so the settings are compared on the results, not chosen
beforehand. `make docindex`, `make retrieve` and `make nli` ask what the record
already does with each gate-opening point (`docs/retrieval.md`). The methods, with
the reasons for each choice and the
measurements, are in `docs/methods-scoring.md` and `docs/methods-clustering.md`.
`docs/background.md` gives the law, the agencies' practice and the established methods.

Three targets, marked `MODEL`, send text to the language model, and they are the
three prompts of `docs/instruments/`: step 3, the stance (`make stance`); step 6, the
substance reading (`make score-model`); step 8, the roster, one of the five passes of
`make attachments` (the OCR pass in the same target goes to the OCR server instead).
Every other target is code and dictionaries. The model targets are the long ones: on
one local server the substance reading runs for days. `make score-model-free` is the
substance reading done by rules alone over the same comments; a reader without a
model server runs the method with it, and a reader with one runs both and sets them
side by side (`make score-model-compare`, below).

`make corpus` creates the file itself if `make schema` has not run. `make all` is all
of it in this order, after `make schema`, for a machine left to run. The listing is
the whole method; the Status section at the end says which targets are built at
this commit and which are still to come.

## Learning the method one step at a time: a sample, then the reference result

Nobody has to run the whole thing to understand it. Every step with a queue takes
`LIMIT=N`: it processes the first N units, writes them, says what it did and exits.
`make floor LIMIT=500` runs the floor on the first 500 comments of its population;
`make stance LIMIT=200` sends 200 groups to the model, stores and loads their replies.
The console then shows the rows beside the code that made them, which is how to read
a step: what it takes in, what it decides, what it writes.

Then, instead of running the step in full, load what it produced in the reference run:

```
make jump STEP=floor
```

loads the reference rows for the floor and for every step before it, so the next
step has what it needs. They are what this repository's own code wrote, step by
step, in a clean clone, saved after each step as one small file holding that
step's tables and nothing else: `extracts/floor.sqlite` is the one table the floor
writes, never the comment text. Put the extract files in `extracts/` and jump.

The extracts are made with the other half of the pair:

```
make extract STEP=floor
```

copies the tables the floor writes, as they stand in `data/roadless.sqlite` at that
moment, to `extracts/floor.sqlite`. It reads the file and runs nothing, so it is taken
any time after the step has run, in any order, one step at a time; a step run weeks
ago is extracted today, as long as it has not been run again since. It refuses to
overwrite an extract that exists. This is how the reference extracts are made, and how
you make your own after changing a step.

The extracts serve three purposes. To fast-forward: read the steps you care about on
a sample and take the reference result for the rest. To compare: run a step yourself
and set your rows beside the reference rows, which is how you find out whether a difference is your
machine, your text or the model. To change the method: alter the code, run the step,
and compare against the result the original code gave. `docs/limit-and-jump.md` says
what `LIMIT` means for each step and which steps have none, because their result is a
partition of every comment and a sample of it would be a different result.

## Looking at the results, and checking on a run

`make console` opens a browser of the file in a web page, usable while a
step is writing. Five of its pages show what the analysis found, each section as soon
as its step has run: an overview from the docket's records to the substance reading;
the stance and the topics, with any topic's letters to read; the copies, families and
campaigns and who ran them; the forests, roadless areas, species, legal authorities
and references the comments name, with the letters that name any one of them; and the
substance reading, the floor and the screen, with every scored comment filtered by
band, gate, answerability, stance or dimension, each opening to its text and the
evidence for its score. The Topics page takes you from the sentences to the concern map
in five stages (`docs/topics-guide.md`). Five more look into the file: one comment as the analysis read
it and every row the steps hold about it, every comparison of the two substance
readings, what every step has written so far, any table a hundred rows at a time, and
SQL typed in. It launches nothing. Its one place that writes is the Topics page, which records the choices and the concern map. `docs/console.md` describes the
eleven pages.

## Comparing the two substance readings

```
make score-model-compare LIMIT=20                         # 20 class A comments, read by the model and by the rules
make score-model-compare LIMIT=20 SERVER=LOCAL            # the same, with the second server of .env
make score-model-compare COMMENTS_OF=<run>                # the comments of an earlier comparison, read again
```

Scoring and comparing are separate. `make score-model` and `make score-model-free`
each score over their own queue; `make score-model-compare` is a command of its own,
with its own queue: it picks `LIMIT` class A comments, evenly spread over the docket,
reads each one with the model and with the rules, and sets the two readings side by
side. It writes nothing to either scoring step's tables, so both still have every
comment to read.

Every comparison is kept in the file, stamped with the code it ran (the git commit,
and whether there were uncommitted changes), the model, the instrument and the rule
set. The console's Compare page shows each run: per dimension, how many comments the
two readings agree on and which reads higher; the gate, band and strength; and every
comment that differs, opening to its text and its eight dimensions with each
reading's level and evidence side by side. It also sets any two readings of any two
runs side by side, so a change to the code, the rules, the instrument or the model is
seen against what an earlier run read; `COMMENTS_OF=<run>` reads exactly that run's
comments again for the purpose. Each run's readings are also written as one JSON file
per comment under `compare/<run>/`, with the printed comparison in
`compare/<run>/comparison.txt`. `docs/model-free-scoring.md` says how the comments
are picked and what each side's evidence is.

## The text the API serves and the text you have

The regulations.gov API serves the comment text with its markup. The bulk download
carries the same text rendered: the submission form's `<br/>` becomes a space, an HTML
entity its character, the padding `<span>` nothing. Compared comment by comment, the
two are identical once rendered for 390,048 of 390,062 comments with text; for 14 the
export's text is shorter. The floor's "longer than 100 characters" test and the
character offsets of spans are over the stored characters, so those can differ at the
margin between two sources of the text; tokens and sentence keys are not, because the
tokeniser strips markup and unescapes first.

## The model steps

| target | reading | instrument | model | what it took on this docket |
|---|---|---|---|---|
| `make stance`, step 3 | the stance | `roadless_rescission_v2`, one call per group | `qwen/qwen3.8-flash` via Together AI | 78,953 calls on the final partition (2026-10-14); 107.0 M tokens in, 80.4 M of them from cache, 17.6 M out; 1,355 in and 224 out a call; 5 calls a second at 32 in flight |

The reference run uses Qwen3.8-Flash (`qwen/qwen3.8-flash`) through an API, for cost
and speed: at the prices OpenRouter's customers pay it costs about a quarter of
Qwen3.8-27B on this method, and `docs/model-server.md` shows the arithmetic. Its rows
carry its name, and the figures of the other model steps are added to the table as
they are measured. Any model a server
behind the OpenAI chat API serves can be named in `.env`; `docs/model-server.md` says
what the two documented servers need, what another choice means for the figures, and how two
models are compared on the same comments.

A model step is proven before it is run in full: `make stance LIMIT=200` classifies
200 groups, stores and loads them and exits. The rest of that run is continued, not
restarted: `make stance-runs` lists the runs and prints the command, `make stance
RUN=<run id>`, with `LIMIT=N` for the next N groups and `CONCURRENCY=N` for the calls
in flight at most: the client starts at one call and climbs, and backs off as one
when an API answers 429 (`docs/model-server.md`).

The prompts are in the repository, readable, one file per step in `docs/instruments/`:
step 3, the stance, `stance-roadless-rescission-v2.md`; step 6, the substance
reading, `substantive-scoring-v3.md`; step 8, the roster, `organisation-roster-v1.md`;
each with the JSON schema its reply must match. `docs/prompts.md` says what each call
sends, which file to edit to change it, and how the edit takes effect.

Two runs of a model step do not match row for row, and the figures downstream of a
model step are not expected to.

## Checking the result

`checks/figures.sql` is every figure of the method as a named query. `make check` runs
it on your file and prints each figure beside `checks/expected.json`, written by the
reference run of this repository from an empty file. A deterministic figure that
differs fails the check. A figure downstream of a model step is printed beside the
reference run's; it is not expected to match.

## The reference figures, and yours

The pages in `docs/` carry the figures of the reference run, each with its date. Your
run gives its own. They differ where the export's rendering of the text reaches, where
your OCR engine reads a scan differently, and where the model varies between runs. That is not an error in the data or the
method.

## Layout

```
Makefile              the run order as targets
schema/roadless.sql   the SQLite DDL
csv/                  the bulk download, gzipped; `make corpus` extracts it
seeds/                the reference lists, the vocabularies, the prompt and topics
shared/               db.py (the one module that knows SQLite), the text normaliser, the model client
packages/             comment-sentences, the one sentence method
comments_db/          the copy-finding scripts and NER
scripts/              the loader, the substance steps, model_free/ (the rules' reading), the entity tagging, the stance chain, the attachment steps, compare_scores.py
checks/               figures.sql, expected.json, check.py
console/              the browser of the file; `make console`
tests/                the tests; `uv run pytest`
docs/                 the method and the pages it cites; instruments/ (the prompts); prompts.md; model-free-scoring.md; model-server.md; mineru.md; console.md; limit-and-jump.md
attachments/, data/   the fetched files and the SQLite file, git-ignored
```

## Status

The repository is being built in phases. At this commit it holds the skeleton, the
seeds, the schema, the loader, the steps through the substance reading, and the
extension: `make schema`, `make corpus`, `make dedup`, `make ngrams`, `make ner`,
`make tag`, `make floor`, `make groups`, `make screen`, `make stance`,
`make score-model`, `make score-model-free`, `make assemble`, `make rate`,
`make sentences`, `make embed`, `make clusters`, `make docindex`, `make retrieve`
and `make nli` are built, `make console` reads the file, and `make extract`,
`make jump` and `make score-model-compare` work. Not yet here, in run order:
`make fetch`, `make text`, `make attachments`, `make orgs`, `make facts` and
`make check`; each lands in its own commit, and this list shrinks with each.

## Licence

The code in this repository is licensed under the GNU Affero General Public
License, version 3 or any later version (AGPL-3.0-or-later); the full text is in
`LICENSE`. You may use, study, change and share it. If you distribute a changed
version, or run one as a service others use over a network, you must offer its
source under the same licence.

The seed lists and the hand-reviewed tables in `seeds/` are licensed under the
Creative Commons Attribution-NonCommercial 4.0 International licence
([CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)). The public
comments themselves, and the attachments `make fetch` downloads, are the public
record of docket FS-2025-0001 as published by regulations.gov; this
repository's licence does not cover them.

Commercial licences are available for anyone who wants to use this code under
terms other than the AGPL, for example to build it into a proprietary product
or service. Contact Nicholas Holshouser at nicholas@wanderingnature.com.

Contributions are welcome. So that the code can continue to be offered under
both licences, contributors are asked to agree to the contributor agreement in
`CONTRIBUTING.md` before a pull request is merged.

Copyright (C) 2026 Nicholas Holshouser
