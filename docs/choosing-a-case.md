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

Use these five checks in step 1. The first two are the most important.

| Check | What to look for | Where to look | Good sign | Bad sign |
|---|---|---|---|---|
| 1. One claim per cluster | The sentences of a cluster make the same claim. | Read a case: open a cluster and read its sentences. | You can state the claim in one sentence. | The sentences make two or more different claims. |
| 2. Coverage | Few gate-open comments have no substantive sentence in a cluster. | Step 1: "Comments not covered", and the chart "Coverage against clustering". | A low number. | Many substantive comments are not in any cluster. |
| 3. No catch-all cluster | No cluster collects unrelated sentences. | Step 1: "Largest cluster". Read a case: the chart "The cluster sizes". | The largest cluster is a few hundred sentences of one claim. | One cluster has thousands of sentences on many subjects. |
| 4. Topics are subjects | Each topic is one subject that you can name. | Read a case: the topic terms, "The map of the clusters" and "The topic cut". | The terms name one subject, for example roads and wildfire. | The terms are general words, for example "rule" or "forest". |
| 5. Clusters stay together | The same groups appear with a nearby setting. | Step 1: "How stable the cases of this model are". | Dark cells between the case and the cases with nearby settings. | Light cells: a small change of setting changes the clusters. |

A case can pass check 2 and fail check 1. For example, many noise passes put every
sentence into a cluster, but some clusters then collect unrelated sentences. Do not
choose a case on coverage alone.

**The gate kinds are not a check.** The gate kind of a sentence tells how the sentence
argues: by law (LAW), by evidence (EVID), by a missing analysis (GAP) or by an
alternative (ALT). It does not tell what the claim is. Different claims can argue the
same way: claims about wildfire, sediment and habitat can each cite a law. One claim can
argue in more than one way: the maintenance backlog appears as evidence and as a missing
analysis. A cluster of one kind can therefore hold several claims, and a cluster of mixed
kinds can hold one claim. Use the kinds to see how a claim is argued. Use check 1 to see
if a cluster is one claim.

## How to choose: two steps

Choose in two steps. First find the best case of each model. Then compare the two
choices. The settings that suit one model can fail the other, so judge each model at its
own best settings.

### Step 1: the best case of each model

1. Open the tab **Step 1: The best case of each model**.
2. Select a model.
3. Read the chart "Coverage against clustering". Note the cases that are low and to the
   right, and the cases with a red ring.
4. Open each promising case in the **Read a case** tab.
5. Apply checks 1 to 4 to each case. Check 1 is the most important.
6. Turn on "Compare every pair of this model's cases" (check 5). Prefer a case that
   agrees with its neighbours: a small change of setting does not change its clusters
   much.
7. Click the point of the best case on the chart. "The selected case" shows its values.
8. Type a note that tells why you chose the case.
9. Click "Choose case N". A black ring marks the choice on the chart.
10. Do steps 2 to 9 again for the other model.

A new choice for a model replaces the old choice. The note stays with the choice. In a
terminal, `make choose CASE=<case name> NOTE="..."` records the same choice.

### Step 2: compare the two choices

1. Open the tab **Step 2: Compare the two choices**. It opens on the two choices of
   step 1.
2. Read the three figures at the top.
3. Read the chart "How the clusters of the first case hold together".
4. Read the chart "Where the largest clusters go".
5. Read the table. The clusters that break the most are at the top.
6. Open the clusters at the top in the **Read a case** tab, in both cases.
7. Decide which case groups those sentences by claim better.
8. If you change your decision, choose a different case for that model in step 1.

The figures:

- **Clustered by both** is the number of sentences that both cases put in a cluster.
  The other figures count these sentences only.
- **Adjusted Rand** measures how much the two cases agree on these sentences. A value
  of 1 means the same grouping. A value of 0 means the agreement that chance gives.
  Values from 0.6 to 0.7 mean the same main groups with different edges.
- **Clusters kept together** counts the clusters of the first case that keep 80% or
  more of their sentences in one cluster of the second case.

### How to read a case

1. Open the **Read a case** tab.
2. Select a case.
3. Read the charts: the topics by gate kind, the cluster sizes, the topic cut and the map
   of the clusters.
4. Open the largest topic.
5. Read the example sentence of each cluster.
6. Open two or three clusters in **Open a cluster**.
7. Read the sentences of each cluster.
8. Decide if each cluster makes one claim.
9. Open **Sentences in no cluster** and read some of them.
10. If many of them repeat a claim that has no cluster, record it as a weakness of the case.

## Glossary

| Term | Meaning |
|---|---|
| Adjusted Rand index | A score from 0 to 1 for how much two cases agree on the sentences that both cluster. 1 is the same grouping. 0 is chance. |
| BGE-large-en-v1.5 | An embedding model of 335 million parameters, built on BERT. It reads English only. |
| Case | One run of the clustering with one set of settings. The console keeps each case. |
| Choice | The case that you record for a model in step 1, or with `make choose`. Step 2 compares the choices. |
| Central sentence | The sentence of a cluster that is nearest to the centre of the cluster. It is the best example of the cluster. |
| Cluster | A group of sentences that HDBSCAN found close together. It is one claim if the case is good. |
| Comment instruction | The instruction "retrieve the sentence from the agency's record that addresses the specific claim". The model makes a vector for that task. |
| Comments not covered | Gate-open comments with no substantive sentence in a cluster. A substantive sentence opens the gate alone, or holds a whole-comment gate hit. A clustered subject line or thank-you line does not cover a comment. |
| eom, leaf | Two ways for HDBSCAN to select clusters. eom keeps the clusters that last longest. leaf keeps the smallest clusters. |
| Eigengap | The method that sets the number of topics. It finds the largest step between eigenvalues of the cluster graph. |
| Embedding model | A model that changes a sentence into a vector of numbers. Similar sentences get similar vectors. |
| Gate | The test that tells if a comment is substantive. It opens when GAP, EVID, ALT or LAW reaches 2. |
| Gate kind | The dimension that opens the gate for a sentence: LAW (a law), EVID (evidence), GAP (a missing analysis) or ALT (an alternative). |
| Gate-opening sentence | A sentence that opens the gate alone. |
| HDBSCAN | A clustering method. It groups the sentences in dense areas. It does not need the number of clusters. |
| Leader | A sentence that represents its near-copies after a merge. Without a merge, each sentence is its own leader. |
| Main kind | The gate kind that most sentences of a cluster have. It tells how the claim is argued, not what the claim is. |
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
