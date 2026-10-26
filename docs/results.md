# Method results

Each row is one measured method decision: a method proposed for this pipeline, the test
that was run, the figures, and what was decided. A refuted method stays in the table, and
its cases stay in the file. The method pages (`docs/methods-scoring.md`,
`docs/methods-clustering.md`) carry the same figures in place; this page is the ledger.
A decision is one of: **adopted**, **kept as a case**, **refuted**.

| Method | Date | Commits | Decision |
|---|---|---|---|
| The labelled set | 2026-10-26 | 60e4d6a | adopted as the measure |
| Shared-direction removal on the sentence vectors (`TOP=D`) | 2026-10-25 | a8af27e | `TOP=0` adopted; D ≥ 1 refuted |
| PaCMAP as the reduction | 2026-10-25 | 3c3392b, bcf5a41 | refuted; kept as cases |
| One gate per prong | 2026-10-26 | 9ef075a, 86587e5, 0fdfa16, 30871e8 | adopted as columns and counts; by-prong clustering refuted |

## The labelled set

374 items from the class A comments (274 sentences, 100 whole comments), each coded by
two frontier models (glm-5p3, qwen3p8-max) under one guide, blind to each other and to
the pipeline, with a third blind reading (claude-sonnet-5-5) beside them and the 48 gate
disagreements ruled by hand. Gate kappa between the coders: **0.740**. Answerability
kappa on the 100 comments: **0.504** — weaker than the gate labels, so the `final`
field carries an answerability level only where the coders agree or a ruling settled
it. The set and its guide: `seeds/labelled_set.jsonl`, `seeds/labelled_set.md`. It is
the reference the gate instruments are measured against.

## Shared-direction removal on the sentence vectors

All-but-the-top on the vectors before the merge and the clustering (`TOP=D`). The first
principal component explains 0.088 (Qwen) and 0.074 (BGE) of the variance; the spectrum
is flat. `TOP=0` (the centring alone): 14% more clusters, a smaller largest cluster,
BGE's catch-all gone — **adopted as the default**. D ≥ 1 moves known subject clusters'
sentences into other clusters (Tribal best-match share 0.25 at D = 1 on Qwen) —
**refuted**; the components past the mean carry subject. Figures:
`docs/methods-clustering.md`, section 8.

## PaCMAP as the reduction

PaCMAP to 5 dimensions beside UMAP. Cross-seed agreement is lower, not higher (mean ARI
0.497 and 0.632 against UMAP's 0.645 and 0.757 over seeds 0 to 4), and its largest
cluster collapses into a catch-all (2,578 and 4,231 against 566 and 275). **Refuted;
UMAP stays the default.** The cases are kept. Figures: `docs/methods-clustering.md`,
section 12.

## One gate per prong

Four 0-or-1 columns, one per prong of 7 CFR 1b.11(53), derived from the dimension
levels, identical for both readings; the union equals the gate and the answerability
levels reproduce. Agreement by prong (7,588 comments both readings read directly):
compliance κ 1.000, impacts 0.451, alternatives 0.148, significance −0.001 — the rules
fail by prong, not uniformly. Compliance-only comments: 503, 10.4% of the gate set; a
reading test (`seeds/prong_reading.jsonl`, coder κ 0.918) found the prong a right
description for 49/50 impacts-only but only 6/50 compliance-only comments, so the
compliance-only count is not reported as "answered by a legal reading". By-prong
clustering is not tighter than by-kind (0.7834 against 0.7908 on Qwen, 0.7446 against
0.7562 on BGE) — refuted, cases kept. **Adopted as columns and counts.** Figures:
`docs/methods-scoring.md`, sections 4.1 and 8; `docs/methods-clustering.md`, sections 7
and 8.
