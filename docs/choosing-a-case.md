# Choosing a clustering case

This guide explains the clustering cases on the console's Topics page. It tells you why
the cases exist, what to look for, and how to compare two cases. The glossary at the end
defines each term.

## Why we cluster

Thousands of comments make the same claim in different words. The agency answers each
claim once, not each comment. Clustering puts sentences that make the same claim into
one group. A reader can then see each claim once, with every wording and every comment
that makes it.

The clustering reads only substantive sentences. These are sentences from comments that
the gate opened. No language model reads the comments in this step. The grouping comes
from sentence vectors and from density.

## Why we run cases

The clustering has settings: the sentences, the model, the instruction, the reduction
and the HDBSCAN values. Each setting changes the clusters. There is no correct value
that we can know before we look. Each run with one set of settings is a case. The
console keeps every case, so you can compare the results and choose one.

A run costs no money and takes less than three minutes. If you have a question about a
setting, run a new case to answer it.

## What a good case looks like

Use these six checks. The first two are the most important.

| Check | What to look for | Where to look | Good sign | Bad sign |
|---|---|---|---|---|
| 1. One claim per cluster | The sentences of a cluster make the same claim. | Read a case: open a cluster and read its sentences. | You can state the claim in one sentence. | The sentences make two or more different claims. |
| 2. Coverage | Few gate-open comments have no sentence in a cluster. | Cases: "Comments not covered". | A low number. | Many substantive comments are not in any cluster. |
| 3. No catch-all cluster | No cluster collects unrelated sentences. | Cases: "Largest cluster". Read a case: the largest cluster. | The largest cluster is a few hundred sentences of one claim. | One cluster has thousands of sentences on many subjects. |
| 4. Topics are subjects | Each topic is one subject that you can name. | Read a case: the topic terms and its clusters. | The terms name one subject, for example roads and wildfire. | The terms are general words, for example "rule" or "forest". |
| 5. Clusters keep one kind | Most sentences of a cluster have the same gate kind. | Read a case: "Main kind" of each cluster. | Most clusters are mostly one kind. | Many clusters mix LAW, EVID, GAP and ALT. |
| 6. Clusters stay together | The same groups appear with another model or setting. | Compare two cases. | Most clusters stay 80% or more in one cluster of the other case. | Most clusters break into many pieces. |

A case can pass check 2 and fail check 1. For example, many noise passes put every
sentence into a cluster, but some clusters then collect unrelated sentences. Do not
choose a case on coverage alone.

## How to read a case

1. Open the **Read a case** tab.
2. Select a case.
3. Open the largest topic.
4. Read the example sentence of each cluster.
5. Open two or three clusters in **Open a cluster**.
6. Read the sentences of each cluster.
7. Decide if each cluster makes one claim.
8. Open **Sentences in no cluster** and read some of them.
9. If many of them repeat a claim that has no cluster, record it as a weakness of the case.

## How to compare two cases

1. Open the **Compare two cases** tab.
2. Select the first case.
3. Select the second case.
4. Read the three figures at the top.
5. Read the table. The clusters that break the most are at the top.
6. Open the clusters at the top in the **Read a case** tab.
7. Decide which case groups those sentences better.

Compare cases that differ in one setting only. Then the difference comes from that
setting. For example, compare the same settings on two models.

The figures:

- **Clustered by both** is the number of sentences that both cases put in a cluster.
  The other figures count these sentences only.
- **Adjusted Rand** measures how much the two cases agree on these sentences. A value
  of 1 means the same grouping. A value of 0 means the agreement that chance gives.
  Values from 0.6 to 0.7 mean the same main groups with different edges.
- **Clusters kept together** counts the clusters of the first case that keep 80% or
  more of their sentences in one cluster of the second case.

## Glossary

| Term | Meaning |
|---|---|
| Adjusted Rand index | A score from 0 to 1 for how much two cases agree on the sentences that both cluster. 1 is the same grouping. 0 is chance. |
| BGE-large-en-v1.5 | An embedding model of 335 million parameters, built on BERT. It reads English only. |
| Case | One run of the clustering with one set of settings. The console keeps each case. |
| Central sentence | The sentence of a cluster that is nearest to the centre of the cluster. It is the best example of the cluster. |
| Cluster | A group of sentences that HDBSCAN found close together. It is one claim if the case is good. |
| Comment instruction | The instruction "retrieve the sentence from the agency's record that addresses the specific claim". The model makes a vector for that task. |
| Comments not covered | Gate-open comments that have no sentence in any cluster. |
| eom, leaf | Two ways for HDBSCAN to select clusters. eom keeps the clusters that last longest. leaf keeps the smallest clusters. |
| Eigengap | The method that sets the number of topics. It finds the largest step between eigenvalues of the cluster graph. |
| Embedding model | A model that changes a sentence into a vector of numbers. Similar sentences get similar vectors. |
| Gate | The test that tells if a comment is substantive. It opens when GAP, EVID, ALT or LAW reaches 2. |
| Gate kind | The dimension that opens the gate for a sentence: LAW (a law), EVID (evidence), GAP (a missing analysis) or ALT (an alternative). |
| Gate-opening sentence | A sentence that opens the gate alone. |
| HDBSCAN | A clustering method. It groups the sentences in dense areas. It does not need the number of clusters. |
| Leader | A sentence that represents its near-copies after a merge. Without a merge, each sentence is its own leader. |
| Main kind | The gate kind that most sentences of a cluster have. |
| Merge | A step that joins near-copies into one leader before the clustering. |
| min cluster size, min samples | Two HDBSCAN values. The first is the smallest cluster. The second sets how dense an area must be. |
| Noise | The sentences that HDBSCAN puts in no cluster. |
| Noise pass | A second clustering of the noise. It puts more sentences into clusters, but it can make catch-all clusters. |
| NMI | Normalized mutual information. A second score from 0 to 1 for the agreement of two cases. |
| PCA, UMAP | Two methods that reduce a vector to fewer dimensions before HDBSCAN. UMAP keeps the near neighbours of each sentence. |
| Plain view | The sentence goes to the model with no instruction. |
| Qwen3-Embedding-8B | An embedding model of 8 billion parameters. It reads more than 100 languages and accepts an instruction. |
| Sentences clustered | The share of the sentences of a case that are in a cluster. |
| Terms | The eight words or two-word phrases that are frequent in a cluster or topic and rare in the others. |
| Tightness | The mean similarity of the sentences of a cluster to its centre. A higher value is a closer cluster. |
| Topic | A group of clusters on one subject. |
| View | The instruction that the model receives with each sentence: plain, comment or topic. |
| Whole-comment hit sentence | A sentence that holds a rule hit that opened the gate when the rules read the whole comment. |
