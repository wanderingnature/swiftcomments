# The clusters and topics

The nine steps end with the substance reading: which comments the agency owes an answer.
The extension past them finds what those comments say, and groups the same claim made
in any words into one cluster, and the clusters into topics. It is code: sentences,
vectors, density clustering (HDBSCAN) and topics from the clusters' centroids, after
eis-analysis's model-free gate clustering. No generative model reads a comment in it.

The steps run after `make score-model-free`. This page describes each step as it is built.

## Step 10: the sentences of the gate set (`make sentences`)

The gate set is the comments whose hybrid gate the model-free reading opens, in the
screen classes A and B1 (`CLASSES=` for others). `make score-model-free CLASSES=A,B1`
scores both classes first.

For each sentence of those comments, as the model-free reading split and scored it
(`mf_sentence_score`), the step writes one row in `gate_sentence_occurrence`:

- the comment;
- which of LAW, EVID, GAP and ALT the sentence reaches 2 on (its gate kinds);
- `opens`: the sentence opens the gate on its own;
- `holds_hit`: the sentence holds a gate hit of the whole comment.

Then one row in `gate_sentence` for each distinct sentence, keyed by `text_key` (two
sentences are the same when they differ only in case, punctuation, spacing, markup or
encoding): its text, its occurrences, the comments it is in, and the same flags over
its occurrences.

**Why `holds_hit`.** The hybrid reading opens some comments only by reading the whole
comment, where a rule pairs words from two sentences. Such a comment has no sentence
that opens the gate on its own. The hit that opened it has a span in the whole
comment's text; the sentences that span falls in are marked, so each gate-open comment
can be represented by a sentence. The whole comment's text is normalised and a
sentence's text is rendered, so the two are joined on their letters and digits alone.
A sentence not found in the whole text, and a hit in no found sentence, are counted in
the run row, not guessed.

**The run row.** `gate_sentence_run` keeps every build's counts: gate-open comments,
sentences, distinct sentences, the comments with a sentence that opens the gate, with a
sentence that holds a hit, with neither, and the sentences and hits not located. A
build replaces the two sentence tables.

The step stops when there is no model-free score, when no comment of the classes has
an open gate, and when a comment's text gives a different sentence from the one that
was scored (its text changed since `make score-model-free` read it).

## Step 11: the vectors (`make embed`)

One vector for each distinct sentence of `gate_sentence`, made by Qwen3-Embedding-8B at
1,024 dimensions (the model of eis-analysis) on the embedding server named in `.env`:

```
EMBED_BASE_URL=https://api.fireworks.ai/inference/v1
EMBED_API_KEY=<your key>
EMBED_MODEL=accounts/fireworks/models/qwen3-embedding-8b
```

Any server speaking the OpenAI embeddings API (`POST <EMBED_BASE_URL>/embeddings`) that
serves the model will do. Every request asks for 1,024 dimensions. Fireworks and Ollama
honour that; LM Studio (its llama.cpp engine never reads the field) returns Qwen's full
4,096, and the step keeps the first 1,024 and re-normalises them, as Ollama's server
does: Qwen3-Embedding's reduced sizes are its leading dimensions. A local run of the
full model is LM Studio with Qwen's f16 GGUF (`Qwen/Qwen3-Embedding-8B-GGUF`, 15.1 GB),
or Ollama with `qwen3-embedding:8b-fp16`; the 4.68 GB default of both is the Q4_K_M. The step stops when `EMBED_BASE_URL`
or `EMBED_MODEL` is not set.

**The view.** Qwen3-Embedding is instruction-aware: the same sentence under two
instructions gives two vectors. The instruction is part of the input,
`Instruct: <instruction>\nQuery:<text>`. `VIEW=` picks one of three, eis-analysis's:

| View | Instruction |
|---|---|
| `comment` (the default) | "Given a public comment on a federal rule, retrieve the sentence from the agency's record that addresses the specific claim the comment makes. A sentence that only states that the rule is being rescinded or describes the proposed action in general does not address the claim." |
| `plain` | none: the sentence alone |
| `topic` | "Represent the policy issue or subject this sentence discusses" |

Each vector is kept in `sentence_embedding` with the model, the instruction and the
SHA-256 of the exact string sent. A sentence that has a vector for the model and the
instruction is not sent again, so the step resumes where it stopped and a new build of
the sentences sends only the new ones. `LIMIT=N` sends the first N for a pilot.

```
make embed VIEW=comment LIMIT=200     # a pilot
make embed VIEW=comment               # the rest
make embed VIEW=plain                 # a second view, for the cases that read it
```

## Steps 12 to 14: the clustering cases (`make clusters`, `make cases`)

The clusters, the topics and their names are code with no model call, so their
choices are not decided beforehand: each set of choices is a **case**, run, recorded
and compared with the others. A case is one value on each axis:

| Axis | Variable | Values | Default |
|---|---|---|---|
| The sentences | `SENTENCES=` | `opening`: the sentences that open the gate alone; `opening+hits`: and the sentences that hold a whole-comment gate hit; `all`: every sentence of the gate-open comments | `opening` |
| The view | `VIEW=` | the vectors of `make embed VIEW=`: `comment`, `plain`, `topic` | `comment` |
| The merge | `MERGE=` | a cosine below 1: near-copies at it or more become one leader, most-copied first; 0 for none | 0 |
| The reduction | `REDUCTION=` | `pca50`: PCA to 50 dimensions; `umap5`: UMAP to 5 (15 neighbours, min_dist 0, cosine) | `umap5` |
| HDBSCAN | `MCS=` `MS=` `SELECTION=` | min_cluster_size, min_samples; `eom` or `leaf` | 10, 10, `eom` |
| The structure | `STRUCTURE=` | `all`: one clustering; `by-kind`: one for each gate kind (LAW, EVID, GAP, ALT) over the leaders of that kind, the topics drawn across the kinds | `all` |
| The noise passes | `PASSES=` | how many times the noise of the pass before is clustered again on its own, with a reduction fitted to it, until a pass finds no cluster | 0 |
| The topic cut | `K=` | the number of topics; none: the largest eigengap | the eigengap |
| The seed | `SEED=` | the seed of the reduction | 0 |

The defaults are the first case worth reading from eis-analysis's tests 18 to 25.
`MODEL=` names the embedding model when the file holds vectors of more than one.

```
make clusters                                        # the defaults
make clusters SENTENCES=opening+hits                 # the same, with the whole-comment hit sentences
make clusters REDUCTION=pca50 MCS=20 MS=10           # eis-analysis's first settings, for comparison
make clusters STRUCTURE=by-kind                      # one clustering for each gate kind
make cases                                           # every case with its measures
make compare-cases A=<case> B=<case>                 # two cases, sentence by sentence
```

**Two cases compared** (`make compare-cases`, and the Topics page under the opened
case). A sentence's cluster in a case is its leader's. On the sentences both cases
cluster, the adjusted Rand index (1 the same grouping, 0 what chance gives) and the
normalized mutual information; then, for each cluster of the first case, the cluster
of the second that holds most of its sentences and the share it holds, with the count
of clusters at 80% or more and the median share. The same settings on two models'
vectors compare the models; two settings on one model compare the settings.

**What a case does.**

1. **Sentences and vectors.** The distinct sentences its `SENTENCES=` selects, each with
   the occurrences it reads and the gate kinds of those occurrences, and their vectors
   under the view. A sentence with no vector stops the case (`make embed`).
2. **The merge** (step 12). In order of occurrences, each sentence not yet absorbed
   becomes a leader and absorbs every sentence at `MERGE=` cosine or more to it. Members
   of one group are within twice the angle of each other, so the merge does not chain.
3. **The clusters** (step 12). The leaders reduced, then HDBSCAN; a leader in no dense
   region is noise. With `PASSES=`, the noise is clustered again on its own. By kind,
   each kind's leaders are clustered apart, and a leader of two kinds is in both.
4. **The topics** (step 13). One centroid for each cluster; the mean direction of all
   centroids removed, since every comment shares the opposition to the rescission and
   the rule's vocabulary; average linkage on cosine distance, cut at the largest
   eigengap of the normalized Laplacian of the 5-nearest-neighbour graph of the
   centroids, or at `K=`. The candidates are kept.
5. **The names** (step 14). The eight most distinctive words and bigrams of each topic
   and each cluster (class-based TF-IDF: a term's frequency in the class against the
   number of classes that have it; a term in only one class is not counted), and the two
   sentences of each cluster nearest its centroid. No model writes a name.

**What a case keeps.** Its name is made from its values, the embedding model among
them, for example `opening.comment.qwen3-embedding-8b.m0.umap5.10-10-eom.all.p0.kauto.s0`,
so the same settings on two models' vectors are two cases. A run of a case replaces that
case's rows and no other's. `cluster_case` holds its values, its git commit, the
sentence build it read, its seconds, and its measures:

| Measure | What it tells |
|---|---|
| `input_sentences`, `occurrences`, `leaders` | the size of the input |
| `clusters`, `topics`, `eigengaps` | the size of the result, and the other cuts |
| `leaders_clustered`, `occurrences_clustered` | the share that is not noise |
| `largest_cluster` | a cluster that swallows the rest |
| `comments_unclustered` of `gate_comments` | gate-open comments with no sentence in a cluster: comments the topics do not show |
| `opening_occurrences_clustered` of `opening_occurrences` | the share of the substance-carrying sentences that is grouped |

`cluster_case_cluster` holds each cluster: its kind and pass, its topic, its leaders,
the sentences they absorbed, its occurrences, its tightness (the mean cosine of its
leaders to its centroid), the share of its leaders of each gate kind, its terms and its
central sentences. `cluster_case_topic` holds each topic; `cluster_case_member` the
cluster of each leader (0 for noise); `cluster_case_leader` the leader of each sentence.
