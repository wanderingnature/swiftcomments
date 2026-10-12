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

## What you need

- Python 3.14 and `uv`. `uv sync` installs the Python dependencies, including the spaCy
  model `en_core_web_md` 3.8.0.
- For the attachments (step 8): poppler, whose `pdftotext` and `pdfinfo` read the PDFs.
  Debian and Ubuntu: `sudo apt install poppler-utils`. Fedora and RHEL:
  `sudo dnf install poppler-utils`. macOS with Homebrew: `brew install poppler`.
  The docx and rtf files are read with `textutil` on macOS.
- A model server, run locally, for the four steps that read a language model: see
  `docs/model-server.md`. The model is Qwen3.8-27B. Tested on Apple Silicon with LM
  Studio headless through `lms`; ollama and vLLM are documented, not yet verified.
- A MinerU server for the OCR of scanned attachments: see `docs/mineru.md`.
- Disk: about 20 GB for the attachments, and the SQLite file.

## Setting up

```
git clone https://github.com/wanderingnature/swiftcomments.git
cd swiftcomments
uv sync
cp .env.example .env     # then fill in the two servers
make help
```

`.env.example` documents every variable the pipeline reads.

## The nine steps

| step | what | target |
|---|---|---|
| 1 corpus | one row per record of the docket; one row per attachment file | `make corpus` |
| 2 copies | exact and body hashes; 6 to 8 word n-grams; near-duplicate groups; text families; the partition of every comment into one group; the campaign-letter / own-text split | `make dedup`, `make ngrams`, `make groups` |
| 3 stance | SUPPORT, OPPOSE or NEUTRAL, one reading per group, copied to its members | `make stance` (model) |
| 4 entities | legal authorities, cited references, forests, roadless areas, species, ZIP codes, by dictionary; the afterstep that resolves citations the dictionary did not know | `make tag` (afterstep: model) |
| 5 named entities | spaCy NER, read by steps 6 | `make ner` |
| 6 substance | the floor, the screens, the v3 reading of every comment with text of its own, the grading, inheritance along the campaigns, LAW | `make floor`, `make screen`, `make score` (model), `make assemble` |
| 7 answerability | A0 to A3 from the stored dimensions | `make rate` |
| 8 attachments | fetch every file; extract its text; OCR the scans that can hold a letter; what each file is, what each comment counts as, who filed each letter | `make fetch`, `make text`, `make attachments` (roster: model) |
| 9 campaign organisations | who ran each campaign, on four bases | `make orgs` |

`make all` runs them in order after `make schema`, then `make facts` (one row per
comment) and `make check`. Each target prints the row counts it wrote, and each resumes
where it stopped. The model steps are the long ones: on one local server the substance
reading runs for days.

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

| step | instrument | model | what it took on this docket |
|---|---|---|---|
| stance | `roadless_rescission_v2`, one call per group | `qwen/qwen3.8-27b` | 44,555 calls; 60.6 M tokens in, 9.4 M out |
| citation afterstep | `resolve_citations.py`, `adjudicate_bare_words.py` | `qwen/qwen3.8-27b` | 302 resolutions |
| substance | v3, `score_comments.py` over class A | `qwen/qwen3.8-27b` | 28,176 direct readings; 115 M tokens in, 6 M out; 2,096 exemplar and 26,671 delta readings; the rest inherited by code |
| roster | `roster-v1`, `organisation_roster.py` | `qwen/qwen3.8-27b` | 3,002 letters read |

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
comments_db/          the copy-finding scripts and NER
scripts/              the loader, the substance steps, the entity tagging, the stance chain, the attachment steps
checks/               figures.sql, expected.json, check.py
tests/                the tests; `uv run pytest`
docs/                 the method and the pages it cites; model-server.md; mineru.md; first-run.md
attachments/, data/   the fetched files and the SQLite file, git-ignored
```


## Status

The repository is being built in phases. At this commit it holds the skeleton, the
seeds, the schema and the loader: `make schema` creates the file and `make corpus`
loads the docket. The nine steps follow, one commit per file.
