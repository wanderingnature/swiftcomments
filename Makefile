# The nine steps of docs/reference/method.md as targets, in the order they run.
# `make all` runs every step; `make check` compares the result with the
# reference run. Every target prints the row counts it wrote.
#
# Before the first run: `uv sync`; copy .env.example to .env and fill it in;
# for the model steps and the OCR, the two servers of docs/model-server.md and
# docs/mineru.md.

PY  := uv run python
CSV := csv/mv4-z8fw-q5jx.csv

.PHONY: help all schema corpus fetch dedup ngrams ner tag floor groups screen \
        stance score assemble rate text attachments orgs facts check

help:  ## the targets, in run order
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-12s %s\n", $$1, $$2}'

all: schema corpus fetch dedup ngrams ner tag floor groups screen stance score assemble rate text attachments orgs facts check  ## every step, in order

schema:  ## create data/roadless.sqlite from schema/roadless.sql and load the seeds; refuses SQLite < 3.38
	$(PY) scripts/make_schema.py

$(CSV): $(CSV).gz
	gunzip -k $<

corpus: $(CSV)  ## step 1: load the bulk download; 390,064 comments, 19,903 attachment files
	$(PY) scripts/load_csv.py $(CSV)

fetch:  ## step 8: fetch the 19,903 attachment files (19 GB) from downloads.regulations.gov
	$(PY) scripts/collect_attachments.py --project roadless

dedup:  ## step 2: exact and body hashes
	$(PY) comments_db/scripts/deduplicate_comments.py --project roadless
	$(PY) comments_db/scripts/deduplicate_middle_content.py --project roadless

ngrams:  ## step 2: 6 to 8 word n-grams and the near-duplicate groups at 0.85
	$(PY) comments_db/scripts/extract_long_ngrams.py --project roadless --rebuild --update-stats
	$(PY) comments_db/scripts/detect_duplicates_incremental.py --project roadless --rebuild --min-group-size 2

ner:  ## step 5: spaCy named entities over the floor's population
	$(PY) comments_db/scripts/extract_linguistic_patterns.py --project roadless

tag:  ## step 4: the reference lists; the strict and loose passes; the citation afterstep (model); strict again
	$(PY) scripts/entity_tagging/load_references.py --project roadless
	$(PY) scripts/entity_tagging/run_pass.py --project roadless --mode strict
	$(PY) scripts/entity_tagging/run_pass.py --project roadless --mode loose
	$(PY) scripts/entity_tagging/resolve_citations.py --project roadless
	$(PY) scripts/entity_tagging/adjudicate_bare_words.py --project roadless
	$(PY) scripts/entity_tagging/run_pass.py --project roadless --mode strict

floor:  ## step 6: the floor filter
	$(PY) scripts/substance/floor_filter.py --project roadless

groups:  ## step 2: the text families and the comment-group partition
	$(PY) scripts/substance/build_comment_groups.py --project roadless --rebuild --write

screen:  ## step 6: the mechanical screens
	$(PY) scripts/substance/mechanical_screens.py --project roadless --write

stance:  ## step 3 (model): one classification per comment group, copied to the members
	$(PY) scripts/reclassify_groups.py --project roadless --new-run

score:  ## step 6 (model): the v3 substance reading over class A
	$(PY) scripts/substance/score_comments.py --project roadless --classes A

assemble:  ## step 6: campaign inheritance and the delta rows; LAW from the citations
	$(PY) scripts/substance/assemble_scores.py --project roadless --write
	$(PY) scripts/substance/refresh_law.py --project roadless

rate:  ## step 7: the answerability rating
	$(PY) scripts/substance/answerability.py --project roadless --write

text:  ## step 8: extract the text of every fetched file
	$(PY) scripts/attachment_text.py --project roadless --write

attachments:  ## step 8: the kind of every file; OCR the scans that can hold a letter; the kinds again; the roster (model); the kinds again
	$(PY) scripts/attachment_accounting.py --project roadless --write
	$(PY) scripts/attachment_ocr.py --project roadless --write
	$(PY) scripts/attachment_accounting.py --project roadless --write
	$(PY) scripts/organisation_roster.py --project roadless --write
	$(PY) scripts/attachment_accounting.py --project roadless --write

orgs:  ## step 9: who ran each campaign, on four bases
	$(PY) scripts/campaign_organisations.py --project roadless --write

facts:  ## one row per comment: comment_facts
	$(PY) scripts/build_facts.py --project roadless

check:  ## every figure of the method beside checks/expected.json
	$(PY) checks/check.py
