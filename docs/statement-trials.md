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
| Model | `qwen/qwen3.8-27b`, LM Studio on the local machine (MLX, 4 bit) |
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
