# swiftcomments: the roadless comment analysis, reproducible

The public comments on the 2026 proposal to rescind the Roadless Area Conservation
Rule (regulations.gov docket FS-2025-0001, 390,064 records) were analysed with the
method in `docs/reference/method.md`: nine steps that find the copies and the campaign
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
make score        step 6  MODEL  the substance reading: the v3 instrument over every class A comment
make score-rules  step 6         the same reading by rule alone, no model call, for a run without a server or beside the model's
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
make check                       every figure beside checks/expected.json
```

Three targets, marked `MODEL`, send text to the language model, and they are the
three prompts of `docs/instruments/`: step 3, the stance (`make stance`); step 6, the
substance reading (`make score`); step 8, the roster, one of the five passes of
`make attachments` (the OCR pass in the same target goes to the OCR server instead).
Every other target is code and dictionaries. The model targets are the long ones: on
one local server the substance reading runs for days. `make score-rules` is the
substance reading done by rules alone over the same comments; a reader without a
model server runs the method with it, and a reader with one runs both and sets them
side by side (`docs/model-free-scoring.md`).

`make corpus` creates the file itself if `make schema` has not run. `make all` is all
of it in this order, after `make schema`, for a machine left to run.

## Learning the method one step at a time: a sample, then our result

Nobody has to run the whole thing to understand it. Every step with a queue takes
`LIMIT=N`: it processes the first N units, writes them, says what it did and exits.
`make floor LIMIT=500` runs the floor on the first 500 comments of its population;
`make stance LIMIT=200` sends 200 groups to the model, stores and loads their replies.
The console then shows the rows beside the code that made them, which is how to read
a step: what it takes in, what it decides, what it writes.

Then, instead of running the step in full, load what it produced when we ran it:

```
make jump STEP=floor
```

loads our rows for the floor and for every step before it, so the next step has
what it needs. The rows are not exported from any database of ours. They are what
this repository's own code wrote, step by step, when we ran it in a clean clone to
prove the method and the code, saved after each step as one small file holding that
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
overwrite an extract that exists. This is how we made ours, and how you make your own
after changing a step.

We provide them for three reasons. To fast-forward: read the steps you care about on
a sample and take our result for the rest. To compare: run a step yourself and set
your rows beside ours, which is how you find out whether a difference is your
machine, your text or the model. To change the method: alter the code, run the step,
and compare against the result the original code gave. `docs/limit-and-jump.md` says
what `LIMIT` means for each step and which steps have none, because their result is a
partition of every comment and a sample of it would be a different result.

## Checking on a run

`make console` opens a read-only browser of the file in a web page, usable while a
step is writing: what every step has written so far, one comment across every table,
any table a hundred rows at a time, and SQL typed in. It launches nothing and cannot
write. `docs/console.md` describes the four pages.

## The text we analysed and the text you have

We analysed the comments as the regulations.gov API serves them. The bulk download
carries the same text rendered: the submission form's `<br/>` becomes a space, an HTML
entity its character, the padding `<span>` nothing. Compared comment by comment, the
two are identical once rendered for 390,048 of 390,062 comments with text; for 14 the
export's text is shorter. The floor's "longer than 100 characters" test and the
character offsets of spans are over the stored characters, so those can differ at the
margin between our run and yours; tokens and sentence keys are not, because the
tokeniser strips markup and unescapes first.

## The model steps

| target | reading | instrument | model | what it took on this docket |
|---|---|---|---|---|
| `make stance`, step 3 | the stance | `roadless_rescission_v2`, one call per group | `qwen/qwen3.8-27b` | 44,555 calls; 60.6 M tokens in, 9.4 M out |
| `make score`, step 6 | the substance reading | v3, `score_comments.py` over class A | `qwen/qwen3.8-27b` | 28,176 direct readings; 115 M tokens in, 6 M out; 2,096 exemplar and 26,671 delta readings; the rest inherited by code |
| `make attachments`, step 8 | the roster | `roster-v1`, `organisation_roster.py`, the target's fourth pass | `qwen/qwen3.8-27b` | 3,002 letters read |

Those are the figures of the model we used, Qwen3.8-27B through a paid API, for the
analysis published at roadless.org. The runs of this repository use Qwen3.8-Flash
(`qwen/qwen3.8-flash`) through an API, chosen for speed and its lower output price;
on this method's token mix it costs more than the 27B, and `docs/model-server.md` shows
the arithmetic. Its rows carry its name, and its figures are added to the table as
they are measured. Any model a server
behind the OpenAI chat API serves can be named in `.env`; `docs/model-server.md` says
what the two we know need, what another choice means for the figures, and how two
models are compared on the same comments.

A model step is proven before it is run in full: `make stance LIMIT=200` classifies
200 groups, stores and loads them and exits, and the log's closing lines give the
`--resume` command that sends the rest.

The prompts are in the repository, readable, one file per step in `docs/instruments/`:
step 3, the stance, `stance-roadless-rescission-v2.md`; step 6, the substance
reading, `substantive-scoring-v3.md`; step 8, the roster, `organisation-roster-v1.md`;
each with the JSON schema its reply must match. `docs/prompts.md` says what each call
sends, which file to edit to change it, and how the edit takes effect.

Measured repeatability of the substance instrument on this model: 65 of 100 readings
identical between two runs. Two runs do not match row for row, and the figures
downstream of a model step are not expected to.

## Checking the result

`checks/figures.sql` is every figure of the method as a named query. `make check` runs
it on your file and prints each figure beside `checks/expected.json`, written by our
reference run of this repository from an empty file. A deterministic figure that
differs fails the check. A figure downstream of a model step is printed beside the
reference run's with the repeatability above; it is not expected to match.

## Our figures, and yours

The pages in `docs/` carry the figures we published, each with its date, stated as what
our run found. Your run gives its own. They differ from ours where the export's
rendering of the text reaches, where your OCR engine reads a scan differently from
ours, and where the model varies between runs. That is not an error in the data or the
method.

## Layout

```
Makefile              the run order as targets
schema/roadless.sql   the SQLite DDL
csv/                  the bulk download, gzipped; `make corpus` extracts it
seeds/                the reference lists, the vocabularies, the prompt and topics
shared/               db.py (the one module that knows SQLite), the text normaliser, the model client
comments_db/          the copy-finding scripts and NER
scripts/              the loader, the substance steps, model_free/ (the rules' reading), the entity tagging, the stance chain, the attachment steps, compare_scores.py
checks/               figures.sql, expected.json, check.py
console/              the read-only browser of the file; `make console`
tests/                the tests; `uv run pytest`
docs/                 the method and the pages it cites; instruments/ (the prompts); prompts.md; model-free-scoring.md; model-server.md; mineru.md; console.md; limit-and-jump.md; sources.md; first-run.md
attachments/, data/   the fetched files and the SQLite file, git-ignored
```

## Where this came from

The method and every step's code were developed in a private repository that ran the
analysis against PostgreSQL. Each file here is a port of its original to SQLite;
`docs/sources.md` names the original of every file. The method's pages in `docs/` are
the originals with the remarks that only made sense there edited out.

## Status

The repository is being built in phases. At this commit it holds the skeleton, the
seeds, the schema, the loader and the steps through the stance run: `make schema`,
`make corpus`, `make dedup`, `make ngrams`, `make ner`, `make tag`, `make floor`,
`make groups`, `make screen` and `make stance` are ported, and `make console` reads
the file. The scoring, the answerability rating, the attachments, the organisations
and the facts table follow, one commit per file.
