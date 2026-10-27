# The method, end to end

This page explains the whole analysis on one page: what question each stage
answers, in the order the stages run, with the figures of the reference run.
The README says how to run it; this page says what it does and why. Each
section links to the page that holds the detail.

## The question

In 2026 the Forest Service proposed to rescind the Roadless Area Conservation
Rule. The public filed 390,064 comments on the proposal (regulations.gov
docket FS-2025-0001). An agency must read the comments, identify the
substantive points, and respond to them in the record; `background.md` gives
the law and the practice. At this scale, reading is a pipeline. This
repository is that pipeline as code: each stage answers one question, writes
its answer into one SQLite file, and can be rerun, sampled, or checked against
the reference run.

## The shape of it

![The pipeline: six stages from the corpus to the record search, with the attachment stages beside them and the record documents feeding the search.](images/overview/pipeline.svg)

The method narrows as it goes. Most comments are copies of a campaign letter.
Most distinct texts state a position without material to score. The
substantive comments carry the sentences that the clusters and the record
search read. The first two figures below are counts of the docket; the later
figures depend on the readings, and your run's will differ at the margin.

![Funnel chart: 390,064 comments; 78,953 distinct texts; 57,277 rated for answerability; 6,516 with the rules gate open; 5,544 with a sentence that opens the gate alone; 2,189 the record contests.](images/overview/funnel.svg)

## 1 · The corpus

`make corpus` loads the bulk download regulations.gov publishes for the
docket: one row per comment, one row per attachment file. The comment text is
the export's rendering of what the API serves; the two match, once rendered,
for 390,048 of the 390,062 comments with text (README, "The text the API
serves and the text you have").

## 2 · The copies and the campaigns

Most of the docket is the same letter filed many times. `make dedup` finds
the exact copies by hash. `make ngrams` finds the near-duplicates by shared
6-to-8-word n-grams. `make groups` builds the text families: every comment in
one group, each group split campaign-letter or own-text. The 390,064 comments
hold 78,953 distinct texts. The stance (`make stance`) is then read once per
text and copied to the members: SUPPORT, OPPOSE, or NEUTRAL, one model call
per group instead of one per comment.

## 3 · The mechanical reading

`make ner` reads the named entities. `make tag` finds what each comment names,
by dictionary: legal authorities, cited references, forests, roadless areas,
species, ZIP codes. `make floor` decides which comments have substance to
read. `make screen` sorts the comments into the classes the substance readings
read: class A is read directly; class B1 (refers to the action but cites
nothing) the rules can read at no cost. No stage here calls a model; every
decision is code a reader can step through.

## 4 · The substance readings

Every class A comment is scored on eight dimensions under one instrument
(`instruments/substantive-scoring-v3.md`), with the evidence spans that
justify each level. The reading exists twice. `make score-model` sends each
comment to a language model. `make score-model-free` scores the same comments
by rules alone, with no model call, so a reader without a model server still
runs the method; a reader with one sets the two readings side by side
(`make score-model-compare`). `make assemble` carries scores along the
campaigns, and `make rate` turns the dimensions into answerability, A0 to A3.
The reference run rates 57,277 comments. The instrument, the rules, and their
measurements: `methods-scoring.md`, `model-free-scoring.md`, `prompts.md`.

## 5 · The sentences and the concerns

The comments whose rules gate is open — 6,516 — are split into sentences.
Each distinct sentence gets one vector (`make embed`), and the vectors are
clustered into topics (`make clusters`), by code, with no generative model.
The settings are not chosen beforehand: every run is a recorded case, and the
cases are compared on their results. The concern map — which clusters are one
concern — is chosen in the console's Topics page and recorded. The methods and
their measurements: `clusters.md`, `methods-clustering.md`, `topics-guide.md`.

## 6 · The record search

A point is answerable when the record can answer it, so the last stage asks
what the record already does with each point. `make docindex` loads the 15
record documents, splits them by their headings into chunks, and embeds the
chunks. `make retrieve` finds, for each of the 11,563 gate-opening sentences,
the 5 nearest chunks; the sections that carry commenters' words are excluded,
so a comment cannot match another comment. `make nli` reads every retrieved
pair and labels each sentence and comment: the record already says it
(`addressed`), says something it disputes (`contested`), or its nearest
passages do neither (`not_addressed`).

![Bar chart of the 5,544 comments by label: 3,212 not_addressed, 2,189 contested, 143 addressed.](images/retrieval/comment-labels.svg)

A reading test found the NLI model's contradiction calls weak: readers confirm
5 of 30. Read the `contested` counts with that result in view. The figures:
`retrieval.md` and the two reading-test sections of `results.md`.

## The attachments

The comment texts stand on their own: no stage above reads an attachment. The
attachment stages are the rest of the docket, about 19 GB of files. `make
fetch` downloads every file, `make text` extracts the text, `make attachments`
decides what each file is, reads the scans that can hold a letter by OCR, and
reads who filed each letter; `make orgs` says who ran each campaign, on four
bases. These stages land in later commits; the README's Status section says
which targets are built at each commit.

## How the method is measured

Every method choice is a measured decision, recorded in `results.md`: the
method proposed, the test, the figures, the decision. A refuted method stays
in the ledger. Where a stage's calls need human-level judgment, the measure is
a reviewed table: two models read every item blind to each other and to the
pipeline, a third settles the disagreements, and a human reviewer rules every
one. The five reviewed tables are committed under `seeds/` (CC BY-NC 4.0), so
a reader can check every label behind every figure.

![Bar chart of reader agreement, as Cohen's kappa, over the five reviewed tables: 0.615 to 0.918.](images/overview/reader-agreement.svg)

## Reproducing, sampling, checking

Nobody has to run everything to check something. Every queue step takes
`LIMIT=N` and processes N units. `make extract` and `make jump` save and load
each step's result, so a reader runs the steps they care about and takes the
reference result for the rest (`limit-and-jump.md`). `make check` prints every
figure beside the reference run's. `make console` opens the browser of the
file: every comment as the analysis read it, every score with its evidence,
every comparison of the two readings. Figures differ between runs where the
text rendering, the OCR engine, or the model varies; deterministic figures do
not (README, "The reference figures, and yours").
