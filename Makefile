# The nine steps of the method as targets, in the order they run.
# `make all` runs every step; `make check` compares the result with the
# reference run. Every target prints the row counts it wrote.
#
# Before the first run: `uv sync`; copy .env.example to .env and fill it in;
# for the model steps and the OCR, the two servers of docs/model-server.md and
# docs/mineru.md.

# SERVER=<NAME> runs a command against the named server set of .env
# (LLM_<NAME>_BASE_URL and so on) instead of the plain one.
PY  := LLM_SERVER=$(SERVER) uv run python
CSV := csv/mv4-z8fw-q5jx.csv
DB  := data/roadless.sqlite

.PHONY: help all schema schema-add corpus fetch dedup ngrams ner tag floor groups screen \
        stance stance-runs score-model score-model-free assemble rate text attachments orgs \
        facts check console jump extract score-model-compare sentences embed clusters cases case-set compare-cases choose concern-map cases-remeasure

help:  ## the targets, in run order
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

all: schema corpus dedup ngrams ner tag floor groups screen stance score-model score-model-free assemble rate fetch text attachments orgs facts sentences embed clusters check  ## every step, in order

schema:  ## create data/roadless.sqlite from schema/roadless.sql and load the seeds; refuses SQLite < 3.38
	$(PY) scripts/make_schema.py

schema-add:  ## add to an existing data/roadless.sqlite the tables, indexes and views of steps added since it was made; no row is touched
	$(PY) scripts/make_schema.py --add

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

stance:  ## step 3 (model): one classification per comment group, copied to the members; LIMIT=N sends N groups; RUN=<id> continues a run, RETRY=1 resends its errors; REFUSED_IN=<id> a new run over the groups that run's provider refused; CONCURRENCY=N
	$(PY) scripts/reclassify_groups.py --project roadless $(if $(REFUSED_IN),--refused-in $(REFUSED_IN),$(if $(RUN),--resume $(RUN),--new-run)) $(if $(RETRY),--retry-errors) $(if $(LIMIT),--limit $(LIMIT)) $(if $(CONCURRENCY),--concurrency $(CONCURRENCY))

stance-runs:  ## the stance runs so far, what each loaded, and the command that continues the latest
	$(PY) scripts/reclassify_groups.py --project roadless --runs

stance-refused:  ## the comments a provider refused in a stance run, as docs/refused-<RUN>.md with the texts in full
	$(PY) scripts/refused_report.py --run $(RUN) --out docs/refused-$(RUN).md

score-model:  ## step 6 (model): the MODEL reading, the v3 instrument over class A; LIMIT=N for a pilot
	$(PY) scripts/substance/score_comments.py --project roadless --classes A $(if $(LIMIT),--limit $(LIMIT)) $(if $(CONCURRENCY),--concurrency $(CONCURRENCY))

score-model-free:  ## step 6 (model-free): the MODEL-FREE reading of the same class A by rules, no model call; CLASSES=B1 or A,B1 for other screen classes; LIMIT=N for a pilot
	$(PY) scripts/model_free/run.py score $(if $(CLASSES),--classes $(CLASSES)) $(if $(LIMIT),--limit $(LIMIT))

score-model-compare:  ## LIMIT=N class A comments read by both methods, or COMMENTS_OF=<run> the comments of an earlier run; kept for the console's Compare page, JSON under compare/
	$(PY) scripts/score_model_compare.py $(if $(LIMIT),--limit $(LIMIT)) $(if $(COMMENTS_OF),--comments-of $(COMMENTS_OF)) $(if $(CONCURRENCY),--concurrency $(CONCURRENCY))

assemble:  ## step 6: campaign inheritance and the delta rows; then the LAW check (a report; --write if it lists rows)
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

sentences:  ## step 10 (clusters): the sentences of the comments whose model-free gate is open, classes A and B1; CLASSES= for others; no model call
	$(PY) scripts/clusters/sentences.py $(if $(CLASSES),--classes $(CLASSES))

embed:  ## step 11 (clusters): one vector for each distinct sentence, from the embedding server of .env; VIEW=comment (the default), plain or topic; LIMIT=N for a pilot
	$(PY) scripts/clusters/embed.py --view $(or $(VIEW),comment) $(if $(LIMIT),--limit $(LIMIT))

clusters:  ## steps 12 to 14: one clustering case, its clusters, topics and names; SENTENCES= VIEW= MERGE= REDUCTION= MCS= MS= SELECTION= STRUCTURE= PASSES= K= SEED= (docs/clusters.md); no model call
	$(PY) scripts/clusters/cases.py run $(if $(SENTENCES),--sentences $(SENTENCES)) $(if $(VIEW),--view $(VIEW)) $(if $(MODEL),--model $(MODEL)) $(if $(MERGE),--merge $(MERGE)) $(if $(REDUCTION),--reduction $(REDUCTION)) $(if $(MCS),--min-cluster-size $(MCS)) $(if $(MS),--min-samples $(MS)) $(if $(SELECTION),--selection $(SELECTION)) $(if $(STRUCTURE),--structure $(STRUCTURE)) $(if $(PASSES),--noise-passes $(PASSES)) $(if $(K),--k $(K)) $(if $(SEED),--seed $(SEED))

statement-trial:  ## step 15 trial (model): CLUSTERS="207 104 52" of the concern map or of CASE=<case>, RUNS=N calls at each of TEMPERATURES="0 0.7", wordings two ways; JSON under trials/statements/
	$(PY) scripts/clusters/statement_trial.py --clusters $(CLUSTERS) --runs $(RUNS) --temperatures $(TEMPERATURES) $(if $(CASE),--case "$(CASE)")

CASE_RUN =$(PY) scripts/clusters/cases.py run --model "$(MODEL)" --view $(or $(VIEW),plain)

case-set:  ## stage 3 of docs/topics-guide.md: the nine cases of the case set for one model; MODEL=<model> [VIEW=plain]
	@test -n "$(MODEL)" || { echo "make case-set needs MODEL=<model>, the model name that make embed wrote"; exit 1; }
	$(CASE_RUN)
	$(CASE_RUN) --sentences opening+hits
	$(CASE_RUN) --sentences all
	$(CASE_RUN) --structure by-kind
	$(CASE_RUN) --noise-passes 3
	$(CASE_RUN) --k 21
	$(CASE_RUN) --k 23
	$(CASE_RUN) --reduction pca50 --min-cluster-size 20 --min-samples 10
	$(CASE_RUN) --min-cluster-size 5 --min-samples 1

cases:  ## the clustering cases so far, each with its measures
	$(PY) scripts/clusters/cases.py list

compare-cases:  ## A=<case> B=<case>: how far two cases group the same sentences the same way, cluster by cluster
	$(PY) scripts/clusters/cases.py compare "$(A)" "$(B)"

cases-remeasure:  ## count the coverage of every stored case again from its stored rows (comments not covered, on substantive sentences); no case runs again
	$(PY) scripts/clusters/cases.py remeasure

choose:  ## CASE=<case> [NOTE="..."]: record the case as the choice of its embedding model (stage 4 of docs/topics-guide.md)
	$(PY) scripts/clusters/cases.py choose "$(CASE)" $(if $(NOTE),--note "$(NOTE)")

concern-map:  ## CASE=<case> [NOTE="..."]: record one of the two choices as the concern map (stage 5 of docs/topics-guide.md)
	$(PY) scripts/clusters/cases.py concern-map "$(CASE)" $(if $(NOTE),--note "$(NOTE)")

check:  ## every figure of the method beside checks/expected.json
	$(PY) checks/check.py

jump:  ## load the stored rows of a finished run for every step up to STEP from extracts/; make jump STEP=floor
	$(PY) scripts/load_extract.py --target $(STEP)

extract:  ## write extracts/STEP.sqlite, the tables STEP wrote, for make jump; make extract STEP=floor
	$(PY) scripts/dump_extract.py --target $(STEP)

console:  ## a read-only browser of the file: what each step wrote, one comment, any table, SQL
	uv run --group console streamlit run console/app.py --server.headless true
