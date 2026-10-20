# What eis-analysis built after rtca's nine steps

Status: assessment, 2026-10-19, for discussion. Read from the workbench copy of eis-analysis
(`/Volumes/slipper/wip/analysis/eis-analysis`, HEAD `f2598ec`) with its gitignored outputs copied
in from the original (`tmp/`, `respondkit/`, `deis/`, `deis2/`, `data/`). Nothing here is decided.

The intent: eis-analysis split from rtca and the two became two pipelines; swiftcomments is to
carry them as **one pipeline**, rtca's nine steps followed by the agency side that eis-analysis
built.

## Where swiftcomments stands

Steps 1 to 9 of rtca, ending in the substance step: the v3 model scoring, the model-free scoring
(rule set 3, ported from rtca, which built it on eis-analysis's code), the screen classes and
answerability. No embeddings, no clustering, no record documents, no response.

## What eis-analysis built, in the order it was built

| When | Work | Unit | Code | Outputs present |
|---|---|---|---|---|
| 2026-09-29 | Concern ledger, ported from rtca: extract concern excerpts per gate-open comment (model), adjudicate a disposition per claim, group excerpts into **points** inside 30 authored **agency bins**, one statement, label and 5 sampled dispositions per point | point | `src/ledger/`, `scripts/ledger/` | in Postgres `roadless.concern_*` (not in the copy) |
| 09-05 to 09-30 | Respondkit **prose path**: S0 triggers, bucket briefs, S1 record files, S2 record-supported code, S3 directive scenarios, S4 draft, S4a collapse, S5 counsel review (deferential, hard look), publish guard | point, bucket | `src/respondkit/s0..s5.py` | `respondkit/S2..S5`, `thread/`, `run/` (runs 09-12 to 09-21; k5, k10, k10px, k11px, k12px, k13px) |
| 10-01 to 10-03 | Respondkit **slots path**, Steps 3 to 9: claims split into parts, per-part record retrieval, slots of verbatim record spans with a **derived** code, a second look before any dismissal, prose rendered from slots, structural grouping, per-part judging | part of a point | `src/respondkit/s05, s1p, s2s, s6, s7, s8, s9.py`, `scripts/respondkit/slots_run.py` | `respondkit/S0.5, S1p, S2s, S6..S9`, `fixtures/`, `judge/`, `export/`; batches tvm1-6, cie2, rfp1, cac1-3 (last 10-03) |
| 10-04 to 10-07 | **Redesign** from the comments' own sentences: units, HDBSCAN clusters = concerns, topics; concern statement, one response per concern, a judge | concern | `src/concerns/`, `scripts/concerns/` | `content/concerns/map.json` (19 topics, 85 concerns); responses T03, T04, T05 (34); judgements T04, T05 |
| 10-04 to 10-06 | **Record units**: the agency documents converted and cut into units by the comment sentence method | record unit | `scripts/convert_deis_pdfs.py`, `scripts/record_units.py`, `src/ingest/record_units.py` | `deis/` (15 documents as PDF and Markdown), `deis2/` (26,704 units of 14 of them, run 1; the Volume III agency letters are not cut) |
| 10-07 to 10-10 | Clustering of the **gate-opening sentences**: 16 stored variants, then tests 16 to 25 (settings, UMAP, tone, the gate's kinds as structure, topics across kinds) | sentence | `scripts/model_free/gate_clusters.py`, `kind_clusters.py`, `cross_kind_topics.py` | `tmp/model_free/gate_clusters.sqlite` (16 variants, created 10-07 and 10-08); tests 19 to 25 as Markdown only (`kind_clusters.md`, `cross_kind_topics.md`, ...) |

## The pieces one pipeline needs, and where each one is

1. **The agency record as data.** `deis/*.md` and `deis2/*.units.jsonl`: Draft EIS Vol I (4,729
   units), the two Biological Assessments, the cost-benefit analysis, the Tribal summary, the NOI,
   the proposed rule (223869), four executive orders, the 2020 Alaska FEIS and 2023 DNA, SM 1078-006.
   Files, not Postgres: portable as they are.
2. **Embeddings** of comment sentences and record units (qwen3-embedding-8b, Fireworks, the
   instruction in the input). Every later step reads them.
3. **Concerns from the gate.** The clusters of the gate-opening sentences, within kind (LAW, EVID,
   GAP, ALT) and grouped into topics across kinds (test 25: 387 clusters, 17 topics), UMAP before
   HDBSCAN (tests 18 to 25). Stored only as reports; `gate_clusters.sqlite` holds the earlier PCA
   variants.
4. **A concern statement** per concern (`src/concerns/respond.py`, `STATEMENT_SYS`).
5. **The response.** Two implementations:
   - the redesign's single call (`src/concerns/respond.py`): nearest record passages, one code of
     the fourteen, the response text; checked for codes and locators only;
   - the slots path (Steps 3 to 9), the most developed: every claim part answered from verbatim
     record spans, the code derived in code, a dismissal tested against the strongest record support
     for the commenters, prose rendered from the slots, judged per part under both standards.
     It reads **points** (excerpts per point from S0 and S1), not clusters.
6. **The judge**: in the redesign (`src/concerns/judge.py`) and in the slots path (Step 9).

## What does not join today

- The redesign's concerns (`map.json`) are the 2026-10-05 merged-sentence clusters; nothing reads
  the gate-sentence clusters into a concern statement or a response.
- The slots path consumes points of the old ledger through fixtures frozen from Postgres
  (`respondkit/fixtures/<batch>/`); it has never run on a cluster.
- S1's record files come from the **bucket briefs** (`docs/indexing/briefs/`, 30 briefs), written by
  a Claude skill (`.claude/skills/bucket-brief`), not by a script a reader can run. The slots path's
  Step 4 retrieves per part by embedding and needs the briefs only as an added pool.
- Everything except `deis/`, `deis2/` and the SQLite stores is in Postgres.

## For discussion

1. **The concern unit**: a gate-sentence cluster (the redesign) or a point of model-extracted
   excerpts in agency bins (the ledger). A cluster's sentences can stand as a point's excerpts, which
   lets the slots path run on clusters.
2. **Bins**: the 30 authored agency bins (the agency's own method, per the bucketing reference) or
   topics found from the clusters.
3. **The response path**: the slots path (Steps 3 to 9) on clusters, or the redesign's single call.
4. **Retrieval** without the briefs: Step 4's per-part embedding search over the record units.
5. **S3 directives**: the prose path's political scenarios; the slots path has none.
6. **Endpoints**: an embedding endpoint and a reranker beside `LLM_BASE_URL`, named by the operator.
7. **The plan**: `reproduction-repo.md` §1 limits the repository to the nine steps; this is a §10
   revision.
