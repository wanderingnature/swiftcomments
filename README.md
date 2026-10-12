# Roadless comment analysis

The analysis of the public comments on docket FS-2025-0001, the proposed rescission of
the 2001 Roadless Area Conservation Rule, as code anyone can run from the public record.
It starts from the regulations.gov bulk download of the docket and does everything
itself: finds the copies, reads the stance, tags the citations, grades the substance,
rates the answerability, fetches and reads the attachments, and names who filed what.
No computed result is shipped as data. What you get at the end is your own run of the
method; the reference figures are in `docs/` with their dates, and the differences you
should expect are stated below.

## What it needs

- Python 3.14 and `uv`. `uv sync` installs the Python dependencies, including the spaCy
  model `en_core_web_md` 3.8.0, which the named-entity step depends on.
- SQLite 3.38 or newer, which the `sqlite3` module of the installed Python already has.
  There is no database server. The whole analysis is one file, `data/roadless.sqlite`.
- The bulk download of the docket from regulations.gov, placed in `csv/`. The copy we
  worked from is 683 MB, 390,064 records, 60 columns.
- About 20 GB of disk for the attachments, fetched by the pipeline from
  `downloads.regulations.gov` into `attachments/`.
- For the attachment text: `pdftotext` and `pdfinfo` (poppler), `textutil` (macOS, for
  docx and rtf), and a MinerU server for the OCR of scanned letters.
- For the four model steps: a server speaking the OpenAI chat API, local or hosted, with
  the model you choose. Set `LLM_BASE_URL` and `LLM_API_KEY` in `.env`. The models we
  used and the tokens each step took are below, so you can size the run.

## How to run it

```
make schema       create data/roadless.sqlite and load the seeds
make corpus       load the bulk download: 390,064 records, 390,060 with text, 19,903 files
make fetch        fetch the attachment files
make dedup        exact and body copies
make ngrams       long n-grams and near-duplicate groups
make ner          named entities
make tag          legal authorities, cited references, forests, roadless areas, species, ZIP codes; the citation afterstep (model); the strict pass again
make floor        the substance floor
make groups       text families and the comment groups
make screen       the mechanical screens
make stance       the stance of every comment group (model)
make score        the substance reading of class A comments (model)
make assemble     inheritance to the campaigns; the LAW column
make rate         answerability A0 to A3
make text         attachment text extraction, then OCR of the scans that can hold a letter
make attachments  the kind of every file, what each comment counts as, who filed each letter (model)
make orgs         who ran each campaign
make facts        one row per comment
make check        compare your figures with the reference run
```

`make all` runs the lot in that order. Every target prints the row counts it wrote and
can be re-run; a step that already has its rows skips them. A model step stops until
`.env` has a server. `docs/first-run.md` records the wall time, peak memory and file size
of the reference run on a clean machine.

## The method

`docs/method.md` is the whole method in nine steps, each a script over tables, each table
written by exactly one step. The pages it cites are beside it: the text families, the
comment groups, the substance instrument (v3) and its grading, the answerability rating,
the entity tagging, the attachment accounting, the organisation roster, the campaign
organisations, and the glossary.

## The models

Four steps read a language model, all through `shared/llm_client.py`. Every reply is
stored (`classification_run_items`, `substance_score_parts`, the roster's `source`), so
the grading can be audited after the run without the model.

| step | instrument | model | what it took on this docket |
|---|---|---|---|
| stance | `roadless_rescission_v2`, one call per comment group | `qwen/qwen3.8-27b` | 44,555 calls; 60.6 M tokens in, 9.4 M out |
| citation afterstep | `resolve_citations.py`, `adjudicate_bare_words.py` | `qwen/qwen3.8-27b` | 302 resolutions |
| substance | v3 over class A | `qwen/qwen3.8-27b` | 28,176 direct readings; 115 M tokens in, 6 M out; 2,096 exemplar and 26,671 delta readings; the rest inherited by code |
| roster | `roster-v1` | `qwen/qwen3.8-27b` | 3,002 letters read |

Measured repeatability of the substance instrument: 96 of 100 readings identical on a 9B
model, 65 of 100 on the 27B we scored with. Two runs do not match

## Checking the result

`checks/figures.sql` is every figure of the method as a named que
it on your file and prints each figure beside `checks/expected.json`, written by the
reference run of this repository from an empty file. A determinis
fails the check. A figure downstream of a model step is printed beside the reference
run's with the repeatability above; it is not expected to match.

## The reference figures, and yours

The pages in `docs/` carry the figures of the reference run, each with its date. Your
run gives its own. They differ where the export's rendering of the text reaches, where
your OCR engine reads a scan differently, and where the model varies between runs.
That is not an error in the data or the method.

## Layout

```
schema/roadless.sql      the SQLite DDL
seeds/                   the reference lists, vocabularies, prompt and topics, the two hand-read review tables
scripts/                 load_csv.py, the step scripts, build_fac
comments_db/             the copy-finding scripts and named-entity extraction
shared/                  db.py, text normalisation, the model cli
src/                     the classification profile and paths
checks/                  figures.sql, expected.json, check.py
tests/                   run with `uv run pytest`; no database server needed
docs/                    the method and the pages it cites; sourc
csv/, attachments/, data/   yours, git-ignored
