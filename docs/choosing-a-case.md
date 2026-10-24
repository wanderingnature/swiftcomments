# Topics: from the sentences to the concern map

This guide tells you how to make the concern map. The concern map is one clustering of
the substantive sentences. In a good concern map, each cluster is one claim that
commenters make.

The work has five stages. Do them in order. The status lines at the top of the Topics
page show the stages that are done and the stage that is next.

| Stage | You do | Where | Result |
|---|---|---|---|
| 1. Sentences | Run `make sentences`. | terminal | The substantive sentences. |
| 2. Vectors | Run `make embed VIEW=plain` for each model. | terminal | One vector for each sentence and model. |
| 3. Cases | Run `make case-set MODEL=<model>` for each model. | terminal | Nine clustering cases for each model. |
| 4. Best case of each model | Read the cases of one model and choose the best case. Do it again for the other model. | console | One choice for each model. |
| 5. Concern map | Compare the two choices and decide on one. | console | The concern map. |

The next step of the method writes one concern statement for each cluster of the concern
map. That step is not built yet.

## Stage 1: Sentences

1. Run `make sentences`.

The step splits each gate-open comment into sentences. It keeps one row for each
different sentence.

## Stage 2: Vectors

1. In `.env`, set `EMBED_BASE_URL`, `EMBED_API_KEY` and `EMBED_MODEL` for the first model.
2. Run `make embed VIEW=plain LIMIT=200`.
3. Read the output. It shows the vectors written and the time.
4. Run `make embed VIEW=plain`.
5. Do steps 1 to 4 again for the second model.

The step sends each sentence to the model and keeps the vector that the model returns.
Sentences with the same meaning get similar vectors.

## Stage 3: Cases

A case is one clustering with one set of settings. You cannot know the best settings
before you see the result. Thus you run a set of cases and compare them.

1. Run `make case-set MODEL=<model>` for the first model.
2. Run `make case-set MODEL=<model>` for the second model.

`MODEL` is the model name that `make embed` wrote, for example
`text-embedding-qwen3-embedding-8b@f16`. `make cases` lists the cases. One case takes
from 4 seconds to 3 minutes.

The case set has nine cases. Each case changes one setting of the base case:

| Case | Setting changed | What it tests |
|---|---|---|
| Base | none: gate-opening sentences, UMAP, HDBSCAN 10/10 eom | the starting point |
| Opening and hits | `SENTENCES=opening+hits` | also the sentences that hold a whole-comment hit |
| All sentences | `SENTENCES=all` | every sentence of the gate-open comments |
| By gate kind | `STRUCTURE=by-kind` | one clustering for each gate kind |
| Noise passes | `PASSES=3` | three more clusterings of the sentences in no cluster |
| 21 topics | `K=21` | a fixed number of topics |
| 23 topics | `K=23` | a fixed number of topics |
| PCA | `REDUCTION=pca50 MCS=20 MS=10` | the settings of the first eis-analysis run |
| Small clusters | `MCS=5 MS=1` | smaller clusters |

Qwen also accepts an instruction. To test it, run `make embed VIEW=comment`, then
`make case-set MODEL=<model> VIEW=comment`. To test another setting, run `make clusters`
with that setting. `docs/clusters.md` lists the settings.

## Stage 4: Best case of each model

Open the console. Go to Topics, then the tab **Stage 4: Best case of each model**.

1. Select a model.
2. Read the chart. Each point is a case.
3. Find the cases low and to the right. These cases put many sentences in clusters and
   leave few comments out.
4. Click a point. The case shows under the chart.
5. Open the tab **Read a case**. It shows the case that you clicked.
6. Do the four checks below.
7. Do steps 4 to 6 for the other good cases.
8. Go back to the tab of stage 4. Click the point of the best case.
9. Type a note that tells why the case is best.
10. Click **Choose case N**. A black ring marks the choice on the chart.
11. Do steps 1 to 10 for the other model.

A new choice for a model replaces the old choice.

### The four checks

| Check | Where | Good | Bad |
|---|---|---|---|
| 1. One claim in each cluster | Read a case: open a cluster and read its sentences. | You can say the claim in one sentence. | The sentences make two or more claims. |
| 2. No catch-all cluster | Stage 4: the column "largest cluster", and a red ring on the chart. | The largest cluster has a few hundred sentences. | One cluster has thousands of sentences on many subjects. |
| 3. Few comments not covered | Stage 4: the column "comments not covered". | A low number. | Many gate-open comments have no sentence in a cluster. |
| 4. Topics that you can name | Read a case: the list of topics. | The words of each topic name one subject. | The words are general, for example "rule" or "forest". |

Check 1 is the most important. A case can pass check 3 and fail check 1. For example,
noise passes put almost every sentence in a cluster, but some clusters then mix claims.

## Stage 5: Concern map

Go to the tab **Stage 5: Concern map**. The tab shows the two choices of stage 4.

1. Read the three numbers at the top.
2. Read the table. Each row is a cluster of the first choice. The second choice splits
   the clusters at the top of the table most.
3. Open two or three of these clusters in **Read a case**, in both choices.
4. Decide which choice keeps one claim in each cluster.
5. Type a note that tells why.
6. Click **Use this case as the concern map** under that choice.

A new decision replaces the old decision.

The three numbers:

- **Clustered by both**: the sentences that both choices put in a cluster. The other two
  numbers use these sentences only.
- **Adjusted Rand**: how alike the two choices cluster these sentences. 1 means the same
  clusters. Near 0 means different clusters.
- **Clusters kept together**: the clusters of the first choice that keep 80% or more of
  their sentences in one cluster of the second choice.

## Read a case

The tab **Read a case** shows one case.

- **The topics, by gate kind**: one bar for each topic. The colours show how its
  sentences argue: by law, evidence, a missing analysis or an alternative.
- **The cluster sizes**: the number of clusters of each size. A bar far to the right is a
  catch-all cluster.
- **The topic cut**: the score for each number of topics. The orange bar is the number
  that the case uses.
- **The map of the clusters**: one point for each cluster. Clusters near each other say
  similar things.
- **Topics**: open a topic to see its clusters. Each cluster shows its most typical
  sentence.
- **Open a cluster**: select a cluster to read all its sentences. Turn on **Read the
  comments** under a sentence to see the comments that hold it. Click a comment to read
  all of it.
- **Sentences in no cluster**: the sentences that the case left out. If many of them make
  one claim, the case missed that claim.

## The terminal commands

| Command | What it does |
|---|---|
| `make cases` | Lists every case with its numbers. |
| `make choose CASE=<case> NOTE="..."` | Records a choice of stage 4, as the button does. |
| `make concern-map CASE=<case> NOTE="..."` | Records the concern map of stage 5, as the button does. |
| `make compare-cases A=<case> B=<case>` | Compares two cases, cluster by cluster. |

## Glossary

| Term | Meaning |
|---|---|
| Adjusted Rand index | How alike two cases cluster the same sentences. 1 means the same clusters. Near 0 means different clusters. |
| BGE-large-en-v1.5 | An embedding model with 335 million parameters. It reads English only. |
| Case | One clustering with one set of settings. |
| Catch-all cluster | A very large cluster with sentences on many subjects. |
| Choice | The best case of one model, recorded in stage 4. |
| Cluster | A group of sentences that are close together. In a good case, a cluster is one claim. |
| Comment view | Each sentence goes to the model with an instruction: find the agency text that answers the claim. Only Qwen accepts an instruction. |
| Comments not covered | Gate-open comments with no substantive sentence in a cluster. |
| Concern map | The case that you decide on in stage 5. It is one of the two choices. |
| eom, leaf | Two ways for HDBSCAN to select clusters. eom keeps the clusters that last longest. leaf keeps the smallest clusters. |
| Gate | The test that tells if a comment is substantive. |
| Gate kind | How a sentence argues: LAW (a law), EVID (evidence), GAP (a missing analysis) or ALT (an alternative). |
| Gate-opening sentence | A sentence that opens the gate alone. |
| HDBSCAN | The clustering method. It finds groups of sentences that are close together. It needs no number of clusters. |
| Leader | A sentence that stands for its near-copies when a case merges them. |
| MCS, MS | Two HDBSCAN settings. MCS is the smallest cluster size. MS sets how close the sentences of a cluster must be. |
| Noise | The sentences that a case puts in no cluster. |
| Noise pass | One more clustering of the noise. It puts more sentences in clusters, but it can make catch-all clusters. |
| PCA, UMAP | Two methods that make the vectors shorter before HDBSCAN. |
| Plain view | Each sentence goes to the model with no instruction. |
| Qwen3-Embedding-8B | An embedding model with 8 billion parameters. It reads more than 100 languages and accepts an instruction. |
| Sentences clustered | The part of the sentences of a case that is in a cluster. |
| Substantive sentence | A sentence that opens the gate alone, or holds a whole-comment gate hit. |
| Terms | The words that are frequent in one cluster or topic and rare in the others. |
| Topic | A group of clusters on one subject. |
| Vector | A list of numbers that a model makes for a sentence. |
| Whole-comment hit | A rule hit that opened the gate when the rules read the whole comment. |
