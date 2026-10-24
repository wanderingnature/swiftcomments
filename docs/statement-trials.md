# Step 15 trials: the concern statement

This page records each trial of `make statement-trial` and what it found.
`docs/clusters.md` tells what the trial does. Each trial has one JSON file in
`trials/statements/`, with every statement in full.

## Trial 20261024_162538

**The question.** Do the wordings that the call gets change the statement? Or does
the model's sampling change it more?

**The settings.**

| Setting | Value |
|---|---|
| File | `trials/statements/20261024_162538.json` |
| Code | `74dd561` |
| Model | `qwen/qwen3.8-27b`, LM Studio on the local machine (MLX, 4 bit), 8,192 tokens of context configured |
| Concern map | `opening.plain.text-embedding-qwen3-embedding-8b-f16.m95.umap5.10-10-eom.all.p1.kauto.s0` |
| Clusters | 207, 104, 52, 1: by leaders, the smallest, the median, the cluster a quarter down from the top, and the largest |
| Methods | `leaders`, `collapse` |
| Temperatures | 0 and 0.7 |
| Runs | 3 for each cluster, method and temperature: 48 calls |
| Tokens | 301,560 in, 3,743 out, no cost |

**The wordings.**

| Cluster | Topic | Sentences | Leaders | Wordings after `collapse` | Input tokens, `leaders` / `collapse` |
|---|---|---|---|---|---|
| 207 | 2 | 11 | 10 | 10 | 468 / 470 |
| 104 | 5 | 26 | 26 | 26 | 1,492 / 1,492 |
| 52 | 1 | 45 | 41 | 41 | 2,302 / 2,311 |
| 1 | 2 | 541 | 386 | 389 | 20,668 / 21,057 |

**Different statements among the 3 runs.**

| Cluster | `leaders`, 0 | `leaders`, 0.7 | `collapse`, 0 | `collapse`, 0.7 |
|---|---|---|---|---|
| 207 | 1 | 3 | 1 | 3 |
| 104 | 1 | 3 | 1 | 3 |
| 52 | 1 | 3 | 1 | 3 |
| 1 | 1 | 3 | 1 | 3 |

**What the trial found.**

1. At temperature 0, the model gives the same statement in each run. At 0.7, each run
   gives a different statement.
2. At temperature 0, the two methods give almost the same statement:
   - Clusters 207 and 104 have the same statement under both methods.
   - Cluster 52 has one change. The `leaders` statement names *Wyoming v. USDA* and
     *California ex rel. Lockyer v. USDA*. The `collapse` statement says "the Tenth and
     Ninth Circuits".
   - Cluster 1 has three small changes: "is consistent with" becomes "reconciles with",
     "wildfire ignition risk" becomes "ignition risk", and "must quantify" becomes "it must
     quantify".
3. Thus the method of the wordings has a small effect. The temperature has a large
   effect. The case's merge at 0.95 already folds the near-copies, so `collapse` has
   almost nothing more to fold.
4. At 0.7, the form of the statement changes from run to run. Some statements are a
   duty of the agency ("The agency must explain..."). Some are the commenters' claim
   ("Commenters contend..."). Some are a question ("Whether the rescission...").
5. One statement at 0.7 is cut off: cluster 52, `collapse`, run 3, after 38 output
   tokens: "...the accompanying environmental analysis fails to meet the ". The server
   did not report a cut (the finish reason was not `length`), and the answer parsed as
   JSON. The cause is not known.
6. The statements at temperature 0 are the concern as the agency has to answer it.
   For example, cluster 1: "The agency must explain how the proposal's reliance on
   wildfire and fuels management as a justification for rescission is consistent
   with its own draft environmental impact statement and peer-reviewed data
   demonstrating that road construction significantly increases human-caused wildfire
   ignition risk, and must quantify the expected increase in human-caused ignitions
   from new road access to weigh against any claimed reduction in wildfire hazard."
7. Clusters 207 and 1 are in topic 2. At temperature 0, both statements ask the agency
   to reconcile the wildfire reason with the data on roads and ignitions. The concern
   map puts one concern in two clusters.
8. With a warm cache, each call took between 1.2 and 4.3 seconds. Without a cache, the
   first trial call on cluster 1 took 68 seconds.

**For step 15.**

- Use temperature 0. The statement is then the same in each run.
- Use either method. The difference is small. `leaders` reads only the case's rows.
- Check that each statement ends with a full stop, a question mark or an exclamation
  mark. Finding 5 shows that a cut statement can parse as valid JSON.
- Two clusters can give the same concern. Step 16 has to answer each concern once.

## Trials 20261024_163447 (Qwen) and 20261024_163949 (BGE)

**The question.** Is a statement cut again, with the full context configured? Do the
statements of the BGE choice differ from those of the Qwen choice?

**The settings.**

| Setting | Value |
|---|---|
| Files | `trials/statements/20261024_163447.json`, `trials/statements/20261024_163949.json` |
| Code | `9f182ee` |
| Model | `qwen/qwen3.8-27b`, LM Studio on the local machine (MLX, 4 bit), 262,000 tokens of context configured |
| Qwen case | the concern map; clusters 207, 104, 52, 1, as in the first trial |
| BGE case | `opening.plain.text-embedding-bge-large-en-v1-5.m95.umap5.10-10-eom.all.p0.kauto.s0`, the choice of BGE in stage 4 |
| BGE clusters | 187, 94, 47, 1: by leaders, the smallest, the median, the cluster a quarter down from the top, and the largest. 30, 121, 8, 12: for each Qwen cluster of the trial, the BGE cluster that holds most of its sentences (`make compare-cases`) |
| Runs | 3 for each cluster, method and temperature (0 and 0.7): 48 calls for Qwen, 96 for BGE |
| Tokens | Qwen 301,560 in, 3,789 out; BGE 343,314 in, 7,140 out; no cost |

**How the BGE clusters hold the Qwen clusters.**

| Qwen cluster | Sentences | BGE cluster with most of them | Share | In BGE noise |
|---|---|---|---|---|
| 1 | 541 | 30 | 16% | 212 |
| 52 | 45 | 121 | 4% | 37 |
| 104 | 26 | 8 | 88% | 1 |
| 207 | 11 | 12 | 9% | 8 |

**What the trials found.**

1. No statement was cut: 0 of 48 (Qwen) and 0 of 96 (BGE) fail to end with a full stop,
   a question mark or an exclamation mark. The first trial had 1 of 48.
2. At temperature 0, the runs are not always the same. In 10 of the 24 settings at
   temperature 0, the 3 runs give 2 different statements. In 8 of the 10, run 1 differs
   and runs 2 and 3 are the same. Run 1 is the first call with that prompt, so LM
   Studio has no cache of the prompt for it. In the first trial, every call of a prompt
   came after the pilots, and all runs at 0 were the same.
4. The differences at temperature 0 are small. For example, Qwen cluster 207 has "roads
   increase ignition rates" in one run and "roads drive ignition rates upward" in the
   other.
4. At temperature 0.7, each run gives a different statement, as in the first trial.
5. The two methods of the wordings again give almost the same statement at temperature 0,
   for both models.
6. BGE cluster 12 gives the Table 21 concern by name: "reconcile the proposal with the
   ignition data in DEIS Table 21, which reports far higher fire density on roaded land
   than inside the affected roadless areas." BGE cluster 30 gives the wildfire concern of
   Qwen clusters 1 and 207: "the agency's own environmental impact statement finds that
   building roads into high-risk forests increases the incidence of human-caused fires."
7. BGE cluster 8 (189 sentences, 107 leaders) holds 88% of Qwen cluster 104 (26
   sentences). Its statement adds to the timber revenue the recreation losses ($6.1
   million a year), the net present value (-$92 million to +$199 million) and the road
   maintenance backlog ($6.9 billion). The Qwen statement has the timber revenue alone.
8. Qwen cluster 52 (the legal mix) has no match in BGE: 37 of its 45 sentences are BGE
   noise, and the best BGE cluster holds 4%.
9. The BGE statements name a source more often: DEIS Table 35 (cluster 47), DEIS Table
   21 (cluster 12), 36 CFR Part 294 Subpart B (clusters 94 and 121).

**For step 15.**

- Use temperature 0, and expect small changes of words between a cold call and a
  cached call.
- Check the end of each statement, as before.
- The choice of the concern map changes the concerns more than the method of the
  wordings or the run: one BGE cluster can hold what Qwen splits into several, and the
  reverse.
