# The clusters and topics: the method

This page explains how steps 10 to 14 group the substantive sentences into clusters and
topics, why each method was chosen, and what the measurements show. `docs/clusters.md`
explains how to run the steps. `docs/choosing-a-case.md` explains how to choose a case.
The figures are those of the reference run of this repository, with their dates.

## 1. Purpose and constraints

Thousands of comments make the same claim in different words. The agency may group them
and answer each claim once (7 CFR 1b.7(f)(1)). The clustering finds the claims: each
cluster is one claim, with every wording and every comment that makes it. The topics
group the claims by subject.

Three constraints shape the method:

- **No generative model.** No language model reads a comment in steps 10 to 14. An
  embedding model makes one vector for each sentence. Everything else is code, and the
  same input gives the same result.
- **Recall first.** A substantive sentence that no cluster holds is a claim that a reader
  can miss. The measures count those sentences and those comments.
- **Everything is kept.** Each step writes its result to the file. Each clustering case is
  kept beside the others, with its settings and its git commit.

## 2. The input: which sentences

The clustering reads the sentences of the gate set: the comments whose hybrid gate is
open, in screen classes A and B1. In the reference run (2026-10-21) the gate set had 6,516
comments: 4,647 of class A and 1,869 of class B1. Their 152,359 sentences hold 125,825
distinct sentences.

A case reads one of three selections:

| Selection | The sentences | Reference run |
|---|---|---|
| `opening` | The sentences that open the gate alone. | 11,563 distinct sentences, 14,356 occurrences |
| `opening+hits` | Those, and the sentences that hold a gate hit of the whole-comment reading. | 14,211 distinct sentences |
| `all` | Every sentence of the gate-open comments. | 125,825 distinct sentences |

**Why the gate-opening sentences.** On every sentence of the gate-open comments, most
dense clusters are form-letter lines, thanks and contact details, and the sentences that
carry the substance are mostly noise. Section 11 shows it: the `all` selection covers
fewer comments than `opening+hits`, with five times as many clusters. Clustering only the
gate-opening sentences removes the register lines from the input.

**Why the whole-comment hit sentences.** The hybrid reading opens some comments only when
it reads the whole comment, where a rule ties words from two sentences. Such a comment has
no sentence that opens the gate alone, so `opening` leaves it out. Step 10 finds the
sentences that hold the hits that opened it, and `opening+hits` adds them. In the reference
run (2026-10-21), 5,544 of the 6,516 comments have a sentence that opens the gate alone, and
25 have neither kind of sentence. The case with `opening+hits` cut the comments with no
sentence in a cluster from 1,813 to 1,053 on BGE, and from 1,859 to 1,019 on Qwen.

**How a hit is placed in a sentence.** The whole-comment reading uses the normalized
comment text. A sentence uses the rendered text. Step 10 joins the two texts on their
letters and digits alone, in order. The reference run did not place 17 sentences and 394 hits. The
step counts them and does not guess.

## 3. The vectors

### 3.1 The model

An embedding model changes a sentence into a vector of numbers. Two sentences that say
the same thing get vectors that point the same way. The step compares vectors by cosine:

$$\cos(a, b) = \hat a \cdot \hat b, \qquad \hat v = v / \lVert v \rVert_2.$$

On unit vectors, $\lVert \hat a - \hat b \rVert_2^2 = 2(1 - \cos(a, b))$. A method that uses
Euclidean distance therefore orders neighbours as cosine does.

The step uses Qwen3-Embedding-8B. It has 8 billion parameters,
reads more than 100 languages, and accepts an instruction with each input. The step keeps
1,024 of its dimensions.

### 3.2 Fewer dimensions

The model gives 4,096 dimensions. Its reduced sizes are its leading dimensions
(Matryoshka training). A shorter vector is the first 1,024 values, re-normalized. Ollama's
server does this for a `dimensions` request. LM Studio ignores the request and returns
4,096 values, so step 11 keeps the first 1,024 and re-normalizes them.

Measured on 200 gate-opening sentences (2026-10-22):

| Comparison | Mean cosine | Lowest cosine | Ten nearest neighbours shared |
|---|---|---|---|
| Fireworks at 1,024 against Fireworks at 4,096, cut to 1,024 | 0.99997 | 0.99988 | 99.6% |
| Fireworks at 1,024 against LM Studio f16, cut to 1,024 | 0.99993 | 0.99989 | 99.2% |
| Fireworks at 1,024 against LM Studio Q4_K_M, cut to 1,024 | 0.99063 | 0.98407 | 92.0% |

The first row shows that Fireworks also cuts the vector to its leading dimensions. The
second row shows that the f16 model on a local machine gives Fireworks' vectors. The
third row shows the cost of 4-bit weights: about 1 in 12 nearest neighbours changes.

**Why f16, not Q4.** The Q4_K_M model is no faster on an M3 Ultra (13.9 sentences a
second, against 14.8 for f16), and it changes the neighbours. Use Qwen's f16 GGUF
(`Qwen/Qwen3-Embedding-8B-GGUF`).

Fireworks' Qwen vectors are not unit length. Step 12 normalizes every vector before it
compares two, so this has no effect.

### 3.3 The view: the instruction

Qwen3-Embedding reads an instruction with the text: `Instruct: <instruction>\nQuery:<text>`.
A different instruction gives a different vector. Step 11 has three views:

| View | The instruction |
|---|---|
| `plain` | None. |
| `comment` | "Given a public comment on a federal rule, retrieve the sentence from the agency's record that addresses the specific claim the comment makes ..." |
| `topic` | "Represent the policy issue or subject this sentence discusses." |

**What the reference run found (2026-10-22).** On Qwen, the comment view put more sentences in a
cluster than the plain view (79% against 73% for `opening`) and found more topics (15
against 9). The two views agree on the main groups (adjusted Rand 0.63 to 0.67).

### 3.4 A second model: BGE

BGE-large-en-v1.5 is an embedding model of 335 million parameters, built on BERT. It reads
English only and takes no instruction for clustering. It runs about 5.6 times faster than
Qwen on an M3 Ultra (83.2 sentences a second, against 14.8). The reference run uses it as a
second model, so that a reader can see what depends on the model.

## 4. Near-copies: the leader merge

Form letters give sentences that differ by one word, at cosine above 0.99. They make the
densest regions and can dominate the clusters. The leader merge joins them first.

1. Order the sentences by occurrences, most first. Break ties by text.
2. Take the first sentence that no leader holds. It becomes a leader.
3. The leader takes every free sentence at cosine $\tau$ or more to it.
4. Repeat from step 2 until every sentence has a leader.

**Why a leader, not linkage.** Each member is within $\tau$ of its leader, so two members
are within twice that angle of each other. At $\tau = 0.98$ that is 22.96°, a cosine of
0.921 or more. Single linkage at the same threshold can chain sentences that are each near
the next and far from the first.

**When it matters.** A near-copy that is not merged splits one claim over several
clusters: a sentence copied hundreds of times with small changes forms dense cores of its
own. A merge that is too wide can remove the dense cores on which `eom` splits, and the
clusters then collapse. `MERGE=` is an axis of the cases (`docs/topics-guide.md`).

## 5. Fewer dimensions before HDBSCAN: PCA or UMAP

HDBSCAN works badly in 1,024 dimensions, so the step reduces the vectors first.

- **PCA** keeps the 50 directions of largest variance.
- **UMAP** keeps the near neighbours of each sentence in 5 dimensions (15 neighbours,
  `min_dist` 0, cosine distance; the defaults of BERTopic).

**Why UMAP.** With PCA, HDBSCAN estimates density in a space that keeps only part of the
variance, and most sentences become noise. UMAP keeps the neighbours, and density
clustering needs the neighbours. In the reference run, PCA 20/10 clustered 32% (BGE) and
36% (Qwen) of the sentences, and UMAP 10/10 clustered 73% on both.

UMAP is random. The case sets its seed, so a case gives the same result on each run.

## 6. The clusters: HDBSCAN

HDBSCAN groups the sentences in dense regions and leaves the others as noise. It needs no
number of clusters. With $\mathrm{core}_k(x)$ the distance from $x$ to its $k$-th nearest
neighbour:

$$d_{\mathrm{mreach}}(a, b) = \max\{\mathrm{core}_k(a),\ \mathrm{core}_k(b),\ \lVert a - b \rVert_2\}.$$

This distance pushes sparse points away and leaves dense regions as they are. A minimum
spanning tree under this distance gives a hierarchy. A split that leaves fewer than
`min_cluster_size` points on one side is a loss of points, not a new cluster. The method
then selects clusters from the tree:

- **eom** (excess of mass) keeps the clusters that last longest in the tree.
- **leaf** keeps the smallest clusters at the bottom of the tree.

**Why density and not a cut through a hierarchy.** A dense cluster is the core of a
repeated claim. A one-off wording is noise, not a forced member of a neighbour. Forcing a count of groups chains unrelated
subjects through sparse edges.

**The settings.** `min_cluster_size` is the smallest cluster. `min_samples` sets how dense
a region must be. Smaller values give more and smaller clusters. In the reference run, 10/10 gave
261 to 264 clusters and 5/1 gave 649 to 707, with 73% and 80% of sentences clustered.

**Noise passes.** A noise pass clusters the noise again, with a new reduction fitted to
it. It puts more sentences into clusters, but it can make a catch-all cluster. In the
reference run, three noise passes on BGE put every sentence in a cluster, but one cluster held 3,076
sentences. On Qwen the largest cluster was 390. Read a noise-pass case before you trust
its coverage.

## 7. Structure by gate kind

Each gate-opening sentence has one or more gate kinds: LAW, EVID, GAP or ALT. A case can
cluster all sentences together, or cluster each kind apart and then draw topics across the
kinds.

Clustered by kind, the topics drawn across the kinds put one subject in one topic, argued
as law, as evidence and as a missing analysis.

**What the reference run found.** By kind, 79% (BGE) and 80% (Qwen) of the sentences were in a
cluster, against 73% clustered together. The comments with no sentence in a cluster fell
from 1,813 to 1,631 (BGE) and from 1,859 to 1,591 (Qwen).

## 8. The topics

The topics group the clusters by subject.

1. Take one centroid for each cluster: the mean of its unit vectors, normalized.
2. Remove the shared direction. Write each centroid as $c_k = \mu + \epsilon_k$, with
   $\mu$ the mean of all centroids. Keep $\epsilon_k$ and normalize it.
3. Build the graph of the 5 nearest neighbours of each centroid.
4. Compute the eigenvalues of its normalized Laplacian, $\mathcal{L} = I - D^{-1/2} W D^{-1/2}$.
5. Take the number of topics at the largest gap between two eigenvalues:
   $k^* = \arg\max_k (\lambda_{k+1} - \lambda_k)$.
6. Group the centroids by average linkage on cosine distance, until $k^*$ groups remain.

**Why remove the shared direction.** Almost every comment opposes the rescission and uses
the rule's words. That shared direction makes every pair of centroids look alike, and clusters on different
subjects, fire and wildlife for example, fall into one group with general opposition.

**Why the eigengap.** A large gap between eigenvalues $k$ and $k+1$ is the signature of
$k$ separate groups. The number comes from the data, not from a choice made beforehand.
The case keeps the next candidates too, and `K=` can cut at one of them.

## 9. The names

Each cluster and topic gets a name by class-based TF-IDF. Each class (a cluster or a
topic) is one document, all its sentences joined. With $n_{t,c}$ the count of term $t$ in
class $c$, and $N$ the number of classes:

$$\mathrm{score}_{t,c} = \frac{n_{t,c}}{\sum_{t'} n_{t',c}} \cdot \log\!\left(1 + \frac{N}{\mathrm{df}_t}\right), \qquad \mathrm{df}_t = |\{c : n_{t,c} > 0\}|.$$

A term scores high when it is frequent in the class and found in few classes. The name is
the eight best words and two-word phrases. Each cluster also shows its two sentences
nearest the centroid. No model writes a name.

A term must occur in two or more classes. A word that only one cluster uses does not
appear in its name.

## 10. Cases and how to compare them

### 10.1 Why cases

Each setting above changes the clusters. No value is correct before we look, and a run
costs no money. So the steps do not fix the settings. Each run is a case. The file keeps
every case with its settings, its git commit, the sentence build that it read, and its
measures. A reader compares the cases and chooses one (`docs/choosing-a-case.md`).

### 10.2 The measures of a case

| Measure | What it tells |
|---|---|
| Sentences clustered | The share of the input that is not noise. |
| Largest cluster | A sign of a catch-all cluster. |
| Comments not covered | Gate-open comments with no sentence in a cluster. |
| Gate-opening sentences clustered | The share of the substance-carrying sentences in a cluster. |
| Tightness | The mean cosine of a cluster's sentences to its centroid. |
| Gate-kind shares | How much a cluster mixes LAW, EVID, GAP and ALT. |

### 10.3 The agreement of two cases

Two cases can group the same sentences differently. `make compare-cases` measures the
agreement on the sentences that both cases put in a cluster.

- The **adjusted Rand index** counts the pairs of sentences that both cases put together
  or both put apart, corrected for chance. 1 is the same grouping. 0 is chance.
- The **normalized mutual information** measures how much one grouping tells about the
  other, from 0 to 1.
- The **crossing** takes each cluster of the first case and finds the cluster of the
  second case that holds most of its sentences. The share shows if the cluster stays
  together or breaks.

These measures give the agreement between cases.

## 11. What the reference run found

The reference run, 2026-10-21 and 2026-10-22, on the 6,516 gate-open comments. 21 cases: 9 settings
on each model with the plain view, and 3 on Qwen with the comment view.

| Setting | BGE: clusters, clustered, comments not covered | Qwen: clusters, clustered, comments not covered | BGE against Qwen: adjusted Rand |
|---|---|---|---|
| `opening`, UMAP, 10/10 eom | 261, 73%, 1,813 | 264, 73%, 1,859 | 0.644 |
| `opening+hits` | 296, 73%, 1,053 | 293, 74%, 1,019 | 0.608 |
| `all` | 1,375, 52%, 34 | 1,466, 55%, 26 | 0.552 |
| PCA-50, 20/10 | 61, 32%, 3,792 | 63, 36%, 3,555 | 0.770 |
| UMAP, 5/1 | 649, 80%, 1,507 | 707, 80%, 1,547 | 0.411 |
| By gate kind | 327, 79%, 1,631 | 332, 80%, 1,591 | 0.581 |
| 3 noise passes | 263, 100%, 956 | 331, 100%, 956 | 0.053 |

What the table shows:

- The two models find the same main subjects. Their clusters agree with an adjusted Rand
  index of 0.41 to 0.64 at the UMAP settings. They draw the edges of the clusters
  differently.
- PCA agrees most between models because it clusters only a third of the sentences, the
  densest ones.
- The noise passes on BGE made one catch-all cluster of 3,076 sentences. That is why the
  two models disagree on that case.
- The whole-comment hit sentences cut the comments not covered by 42% (BGE) and 45%
  (Qwen), with no loss of clustering.

Both models found topics on the agency's ignition and fire-density data, the economic
analysis and the road maintenance backlog, the courts, Tribal consultation, the CFR rule,
habitat and species, and timber production under the executive orders.

## 12. Limits

- **No measure of truth.** The measures tell coverage, size and agreement. They do not
  tell if a cluster is one claim. A person must read the clusters
  (`docs/choosing-a-case.md`, check 1). A hand-labelled set is the next measure to make.
- **One seed.** Each case uses one UMAP seed. The agreement between seeds of one setting is
  not yet measured.
- **The names.** Class-based TF-IDF drops a word that one cluster alone uses. A name can
  miss the most specific word of a cluster.
- **Steps 15 and 16 are not built.** A concern statement for each cluster and the response
  need a model call. They come after the choice of a case.
