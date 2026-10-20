# The agency side: what rtca started and eis-analysis continued

Status: assessment, 2026-10-19, for discussion; rewritten the same day after a first version that
misread both repositories. Read from rtca at `reproduction-source` and from the workbench copy of
eis-analysis (`f2598ec`, equal to GitHub `main`) with its gitignored outputs copied in from the
original (`tmp/`, `respondkit/`, `deis/`, `deis2/`, `data/`). Nothing here is decided.

The intent: rtca and eis-analysis became two pipelines when eis-analysis split from rtca;
swiftcomments is to carry them as **one pipeline**.

## Where swiftcomments stops, and what its plan left out

swiftcomments ends at rtca's step 9, substance: the v3 gate and scores, the model-free reading
(rule set 3, hybrid), the screen classes A, B1, B2, answerability. rtca's published method
(`docs/writing/methodologies.md`) stops there too.

The plan (`reproduction-repo.md` §1, "Not in the repository") left out, by name, exactly the agency
side: "the record side (`docindex/`, `record_unit`, `unit_embedding`, the DEIS Markdown), the
concern ledger, EA issues, bucket profiles". Carrying them is a §10 revision.

## The agency side as rtca built it (in rtca at the tag)

Design: rtca `docs/design/agency-response-model.md` ("BUILT AND RUN"). The agency answers
substantive comments once per concern, not per comment; the model produces the same artifacts as
the agency's response appendix.

| Piece | rtca code or file | What it is |
|---|---|---|
| Agency bins | `db/migrations_pending/agency_bins.sql`, `agency_bins_disjoint_ids.sql` | 30 bins in 7 families (process, rule, eis, resources, recreation, lands, socioeconomic), authored from the FS 2008 content-analysis code families, extended for the 2026 rescission (`docs/reference/agency-comment-bucketing-reference.md`) |
| Concern ledger | `scripts/substance/concern_ledger.py` | `extract`: every gate-open, own-scored (not inherited) v3 comment read by the model into verbatim concern excerpts, each with a bin, move, target, forum (DEIS, rule, both) and citations with the (f)(2)(iv) linkage test; `adjudicate-disposition`: per distinct excerpt, stance or concern; `respond`, `respond-strand`, `points`, `respond-point`: groupings and sampled 1b.7(f)(2) dispositions |
| Point class | `v_concern_point_class` | a point is class A when any carrier is class A (`substance_screen`); only class A points reach the response layers |
| Bucket profile | `scripts/substance/bucket_profile.py`, design `docs/design/bucket-profile.md` | per above-floor bucket, what it argues lexically and by meaning (`bucket_profile_excerpts`, `_terms`, `_clusters`) |
| Response headings | `docs/design/agency-theme-standard.md` | 36 headings T-1 to T-36, the Rescission DEIS Volume I table of contents with the DEIS Appendix 3 and 2020 Alaska FEIS Appendix H counterparts, and the placement of the 29 above-floor buckets under them; frozen by the operator 2026-09-28 |
| Record side | `scripts/docindex/` (`ingest_documents.py`, `brief.py`, `standard.py`, `phrase_curation.py`) | the agency's documents as sections and chunks with embeddings, and the heading brief (where in the record a heading's subject is addressed) |
| EA issues | `scripts/substance/extract_ea_issues.py` | the earlier authored issue space, replaced for bucketing by the agency bins; kept for the substance report's EA coverage |

## What eis-analysis did with it

**The ledger moved to eis-analysis on 2026-09-29** and rtca stopped running it
(`docs/plans/concern-ledger-in-eis-analysis.md`). Steps 1 and 2 (`extract`,
`adjudicate-disposition`) are rtca's, the extract prompt at v5 writing no label. Points were rebuilt from excerpt meaning, with no
labels and no model judge (`docs/design/excerpt-points-ledger-s0-s1.md`): per bin, complete
linkage on qwen3-embedding-8b vectors cut at 0.27, joined by shared evidence markers; ids inherited
across builds; then `point-statement`, `point-label` and five `respond-point` samples, all on
qwen3.8-27b. The tables stay in rtca's `roadless` schema.

**Respondkit** (`docs/design/respondkit/V3_DESIGN.md`, the design of record, 2026-10-02) answers the
points the way the Final EIS would:

1. **S0** (free): one cluster per class-A point in an above-floor bucket; six deterministic triggers
   choose which get a record check (latest run 2026-10-01: 2,816 class-A points in 29 buckets,
   1,380 selected).
2. **Bucket briefs**: rtca's heading brief turned per bucket; queries written from the bucket's
   response headings and its profile, run lexically and by embedding over the record documents
   (`.claude/skills/bucket-brief/scripts/brief.py all`, the query-writing call on qwen3.8-27b, about
   $0.30 for 29 buckets; `docs/design/bucket-brief-automation.md`). 30 briefs in
   `docs/indexing/briefs/`.
3. **S1** (free): each selected point's record file from its bucket's brief, plus a bucket record.
4. Two response paths over S1:
   - **prose path**, S2 to S5: the record-supported code, the S3 directive scenarios, the draft, the
     collapse to the published shape, counsel's review under the deferential and hard-look
     standards; run on buckets 2026-09-11 to 09-30;
   - **slots path**, Steps 3 to 9 (built 2026-10-01 to 10-03, the latest respondkit work): claims
     split into parts, per-part retrieval, slots of verbatim record spans with the code derived in
     code, a second look before any dismissal, prose rendered from slots, structural grouping,
     judging per part. Runs: k12px, tvm1 to tvm6, cie2 (41 selected points, 28 of 40 passed),
     rfp1, cac1 to cac3.
5. Not built: S5a (apply the review) and the response ledger.

**A separate line, 2026-10-04 to 10-10**: the comment-analysis redesign
(`docs/design/comment-analysis-redesign.md`) tried replacing bins, excerpts and points with
clusters of the comments' own sentences; `src/concerns/` wrote responses for three topics of the
2026-10-05 clustering; the model-free gate was handed over from rtca and the gate-opening sentences
clustered (tests 13 to 25). It is not wired to respondkit, and nothing in it was chosen.

## What is on disk to bring across

| Path | Holds |
|---|---|
| `deis/` | 15 record documents as PDF, Markdown and page maps |
| `deis2/` | the record units of 14 of them, 26,704 (run 1; the Volume III agency letters are not cut) |
| `docs/indexing/briefs/`, `queries/` | the 30 bucket briefs and their query files |
| `data/bucket-brief/query_embeddings.json` | the briefs' query vectors |
| `data/ledger/excerpt_points.json` | the 2026-09-29 point build report |
| `respondkit/fixtures/<batch>/` | the ledger and S0/S1 output frozen per bucket for the slots runs (cie2: 85 points with statements, excerpts, triggers and the ledger's verdict; the S1 records) |
| `respondkit/S*/`, `thread/`, `judge/`, `export/`, `reports/` | every prose and slots run, call by call |
| `tmp/model_free/` | the score stores and `gate_clusters.sqlite` of the redesign line |

The ledger's own tables (`concern_statements_llm`, `concern_strand_points`,
`concern_strand_responses_llm`, `concern_point_responses_llm`, `concern_bucket_map`), the bucket
profile, the document index (`doc_chunks`, `doc_chunk_embeddings`) and respondkit's rows are in
Postgres, not in the copy.

## What swiftcomments already has that the agency side reads

`substance_scores` (gate, `scored_via`, instrument v3), `substance_screen` (class A for the point
class), `comment_group` and its members (carriers), the authorities and references. Missing: the
agency bins, the ledger, embeddings, the record documents and their index, the bucket profile and
briefs, respondkit.

## For discussion

1. Port source for the ledger: rtca's `concern_ledger.py` at the tag, or eis-analysis's
   `src/ledger/` (rtca's steps 1 and 2 plus the excerpt-meaning points).
2. Which response path: the slots path, the prose path with the S3 directives, or both.
3. The record documents: their source for a reader (the docket's supporting documents) and the
   conversion (`deis/` was made by `scripts/convert_deis_pdfs.py`; swiftcomments has the MinerU OCR).
4. Endpoints beyond `LLM_BASE_URL`: an embedding endpoint (qwen3-embedding-8b) and a reranker
   (qwen3-reranker-8b, the slots path's second look), named by the operator.
5. The redesign line: whether any of it comes across.
