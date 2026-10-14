# The nine steps of the method as targets, in the order they run.
# `make all` runs every step; `make check` compares the result with the
# reference run. Every target prints the row counts it wrote.
#
# Before the first run: `uv sync`; copy .env.example to .env and fill it in;
# for the model steps and the OCR, the two servers of docs/model-server.md and
# docs/mineru.md.

PY  := uv run python
CSV := csv/mv4-z8fw-q5jx.csv
DB  := data/roadless.sqlite

.PHONY: help all schema corpus fetch dedup ngrams ner tag floor groups screen \
        stance stance-runs score score-rules assemble rate text attachments orgs \
        facts check console jump extract compare-scores

help:  ## the targets, in run order
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

all: schema corpus dedup ngrams ner tag floor groups screen stance score score-rules assemble rate fetch text attachments orgs facts check  ## every step, in order

schema:  ## create data/roadless.sqlite from schema/roadless.sql and load the seeds; refuses SQLite < 3.38
	$(PY) scripts/make_schema.py

$(CSV): $(CSV).gz
	gunzip -k $<

# The file, when a step is asked for before make schema has run.
$(DB):
	$(PY) scripts/make_schema.py

corpus: $(CSV) $(DB)  ## step 1: load the bulk download; 390,064 comments, 19,903 attachment files
	$(PY) scripts/load_csv.py $(CSV)

dedup:  ## step 2: exact and body hashes
	$(PY) comments_db/scripts/deduplicate_comments.py --project roadless
	$(PY) comments_db/scripts/deduplicate_middle_content.py --project roadless

ngrams:  ## step 2: 6 to 8 word n-grams and the near-duplicate groups at 0.85
	$(PY) comments_db/scripts/extract_long_ngrams.py --project roadless --rebuild --update-stats
	$(PY) comments_db/scripts/detect_duplicates_incremental.py --project roadless --rebuild --min-group-size 2

ner:  ## step 5: spaCy named entities over the floor's population; LIMIT=N for the first N
	$(PY) comments_db/scripts/extract_linguistic_patterns.py --project roadless $(if $(LIMIT),--limit $(LIMIT))

tag:  ## step 4: the reference lists; the strict and loose passes; LIMIT=N for about the first N per pass
	$(PY) scripts/entity_tagging/load_references.py --project roadless
	$(PY) scripts/entity_tagging/run_pass.py --project roadless --mode strict $(if $(LIMIT),--max-comments $(LIMIT))
	$(PY) scripts/entity_tagging/run_pass.py --project roadless --mode loose $(if $(LIMIT),--max-comments $(LIMIT))

floor:  ## step 6: the floor filter; LIMIT=N for the first N
	$(PY) scripts/substance/floor_filter.py --project roadless $(if $(LIMIT),--limit $(LIMIT))

groups:  ## step 2: the text families and the comment-group partition
	$(PY) scripts/substance/build_comment_groups.py --project roadless --rebuild --write

screen:  ## step 6: the mechanical screens; LIMIT=N for the first N survivors
	$(PY) scripts/substance/mechanical_screens.py --project roadless --write $(if $(LIMIT),--limit $(LIMIT))

stance:  ## step 3 (model): one classification per comment group, copied to the members; LIMIT=N sends N groups; RUN=<id> continues a run; CONCURRENCY=N
	$(PY) scripts/reclassify_groups.py --project roadless $(if $(RUN),--resume $(RUN),--new-run) $(if $(LIMIT),--limit $(LIMIT)) $(if $(CONCURRENCY),--concurrency $(CONCURRENCY))

stance-runs:  ## the stance runs so far, what each loaded, and the command that continues the latest
	$(PY) scripts/reclassify_groups.py --project roadless --runs

score:  ## step 6 (model): the v3 substance reading over class A
	$(PY) scripts/substance/score_comments.py --project roadless --classes A

score-rules:  ## step 6 (rules): the model-free reading of the same class A, no model call; LIMIT=N; JSON=dir writes one file per comment
	$(PY) scripts/model_free/run.py score $(if $(LIMIT),--limit $(LIMIT)) $(if $(JSON),--json $(JSON))

compare-scores:  ## the two readings side by side from their JSON folders: make compare-scores A=dir B=dir
	$(PY) scripts/compare_scores.py --a $(A) --b $(B)

assemble:  ## step 6: campaign inheritance and the delta rows; LAW from the citations
	$(PY) scripts/substance/assemble_scores.py --project roadless --write
	$(PY) scripts/substance/refresh_law.py --project roadless

rate:  ## step 7: the answerability rating
	$(PY) scripts/substance/answerability.py --project roadless --write

fetch:  ## step 8: fetch the 19,903 attachment files (19 GB) from downloads.regulations.gov; steps 1 to 7 need none of them
	$(PY) scripts/collect_attachments.py --project roadless

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

jump:  ## load the stored rows of a finished run for every step up to STEP from extracts/; make jump STEP=floor
	$(PY) scripts/load_extract.py --target $(STEP)

extract:  ## write extracts/STEP.sqlite, the tables STEP wrote, for make jump; make extract STEP=floor
	$(PY) scripts/dump_extract.py --target $(STEP)

console:  ## a read-only browser of the file: what each step wrote, one comment, any table, SQL
	uv run --group console streamlit run console/app.py --server.headless true
