# Step 15 trials: the concern statement

This page records each trial of `make statement-trial` and what it found.
`docs/clusters.md` tells what the trial does. Each trial has one JSON file in
`trials/statements/`. Under each trial, **The statements** gives every statement
that the trial wrote. A statement that several runs wrote is given once, with its runs.
`uv run python scripts/clusters/statement_trial.py --render-doc` writes these lists
again from the JSON files.

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

### The statements

<!-- statements 20261024_162538 -->

Case `opening.plain.text-embedding-qwen3-embedding-8b-f16.m95.umap5.10-10-eom.all.p1.kauto.s0`. Model `qwen/qwen3.8-27b`. File `trials/statements/20261024_162538.json`.

#### Cluster 52, topic 1: nepa, cir, usda cir, clause, california rel, rel, rel lockyer, circuit

45 sentences; 41 wordings as `leaders`, 41 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth Circuit in Wyoming v. USDA and the Ninth Circuit in California ex rel. Lockyer v. USDA have already rejected the argument that decentralized, forest-by-forest planning is a legally sufficient substitute for a uniform national standard.
- `collapse`, runs 1, 2, 3: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth and Ninth Circuits have already rejected the argument that decentralized, forest-by-forest planning is a legally sufficient substitute for a uniform national standard.

Temperature 0.7:

- `leaders`, run 1: Commenters contend that the proposed rescission violates NEPA, the APA, NFMA, and NHPA because it fails to conduct a required hard look at cumulative environmental impacts and disregards prior court decisions that reaffirmed the 2001 Rule and rejected the argument that forest-level planning is the sole appropriate vehicle for roadless area protection.
- `leaders`, run 2: The proposed rescission of the 2001 Roadless Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency’s reliance on decentralized, forest-level planning ignores the legal mandates and judicial precedents (including Wyoming v. USDA and California ex rel. Lockyer v. USDA) that require a national rule to adequately address cumulative environmental impacts and prevent the piecemeal degradation of roadless areas.
- `leaders`, run 3: Commenters assert that the Forest Service's proposed rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency has failed to take a 'hard look' at the cumulative environmental, ecological, and watershed impacts of decentralizing roadless protection to fragmented local forest plans, a legal deficiency previously rejected by the Tenth and Ninth Circuits in their respective decisions upholding the national rule.
- `collapse`, run 1: Whether the rescission of the 2001 Roadless Rule violates the Administrative Procedure Act, NEPA, and the National Forest Management Act by failing to conduct a sufficient 'hard look' at the cumulative environmental and legal consequences of replacing a uniform national standard with fragmented, locally controlled forest plans that have previously been found inadequate.
- `collapse`, run 2: The rescission is legally deficient because it fails to conduct the required 'hard look' at cumulative environmental impacts under NEPA and violates the Administrative Procedure Act, while the Tenth Circuit in Wyoming v. USDA rejected the agency's argument that only local forest planning is permissible, thereby requiring the maintenance of the unified national standard to prevent piecemeal degradation of roadless areas.
- `collapse`, run 3: The Forest Service must withdraw the proposed rescission of the 2001 Roadless Area Conservation Rule because the accompanying environmental analysis fails to meet the 

#### Cluster 1, topic 2: wildfire, human-caused, roads, wildfires, fires, ignitions, ignition, areas

541 sentences; 386 wordings as `leaders`, 389 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for rescission is consistent with its own draft environmental impact statement and peer-reviewed data demonstrating that road construction significantly increases human-caused wildfire ignition risk, and must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.
- `collapse`, runs 1, 2, 3: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for rescission reconciles with its own draft environmental impact statement and peer-reviewed data demonstrating that road construction significantly increases human-caused ignition risk, and it must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.

Temperature 0.7:

- `leaders`, run 1: The agency must explain how its justification of rescission on wildfire grounds reconciles with the data in its own Draft EIS and peer-reviewed studies indicating that human-caused ignitions occur at significantly higher rates near roads than in inventoried roadless areas, and must quantify the expected increase in human-caused ignitions resulting from new road construction to demonstrate that any claimed reduction in wildfire hazard outweighs the added ignition risk.
- `leaders`, run 2: The agency must explain how the proposal’s reliance on wildfire management as a justification for rescission reconciles with the agency's own data and cited peer-reviewed research, which consistently demonstrate that human-caused wildfire ignitions are significantly more frequent near roads than in inventoried roadless areas, and must quantify the expected increase in human-caused ignitions resulting from new road construction before weighing it against any claimed reduction in wildfire hazard.
- `leaders`, run 3: Commenters contend that the proposed rescission is contradicted by the agency's own Draft EIS and peer-reviewed research, which demonstrate that new road construction in Inventoried Roadless Areas would significantly increase the risk of human-caused wildfire ignitions, thereby undermining the stated justification of enhanced wildfire mitigation.
- `collapse`, run 1: Whether the proposed rescission of the Roadless Rule, justified in part by wildfire risk reduction, is inconsistent with peer-reviewed research and the agency's own draft environmental impact statement findings, which indicate that road construction significantly increases human-caused wildfire ignition density in otherwise protected roadless areas.
- `collapse`, run 2: The proposed rescission is justified in part by the need for improved wildfire and fuels management, but the agency's own draft environmental impact statement and peer-reviewed data demonstrate that road construction increases human-caused ignition risk, creating a direct contradiction with the stated rationale. The agency must explain why it departs from these findings, quantify the expected increase in human-caused ignitions resulting from new road access, and weigh that increase against any claimed reduction in wildfire hazard.
- `collapse`, run 3: The commenters contend that the proposal's wildfire justification is invalidated by peer-reviewed and agency data demonstrating that road access increases human-caused ignition rates, and they request the final EIS quantify the net increase in ignition risk from new roads to reconcile the rescission with these findings.

#### Cluster 207, topic 2: justifies rescission, management grounds, fuels management, ignition, justifies, grounds, solution, proposal justifies

11 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `collapse`, runs 1, 2, 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.

Temperature 0.7:

- `leaders`, run 1: The agency justifies the rescission in part on wildfire and fuels management grounds, yet its own data demonstrates that roads drive ignition rates rather than reduce fire risk.
- `leaders`, run 2: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own record data, which demonstrates that road access significantly increases ignition rates, thereby failing to explain how adding roads reduces fire risk.
- `leaders`, run 3: The agency must explain how its reliance on wildfire and fuels management as justifications for rescission is consistent with its own prior data demonstrating that road construction significantly increases ignition rates.
- `collapse`, run 1: The proposal justifies rescission in part on wildfire and fuels management grounds, yet fails to reconcile this rationale with the agency’s own data establishing that roads drive ignition rates upward.
- `collapse`, run 2: The proposal justifies rescission based on wildfire and fuels management, yet the agency's own data shows that roads increase ignition rates, creating an unexplained contradiction between the stated rationale and the agency's findings.
- `collapse`, run 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own findings that road construction increases ignition rates.

#### Cluster 104, topic 5: revenue, treasury, million, treasury forest, revenue treasury, million year, unlikely, timber industry

26 sentences; 26 wordings as `leaders`, 26 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, even under a full-harvest scenario that the agency itself deems unlikely due to budget, operability, and market constraints.
- `collapse`, runs 1, 2, 3: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, even under a full-harvest scenario that the agency itself deems unlikely due to budget, operability, and market constraints.

Temperature 0.7:

- `leaders`, run 1: The projected annual revenue from expanded timber harvesting in previously roadless areas is modest, capped at $5.2 to $11.4 million for the federal government and $4.6 to $10.6 million for the timber industry, and is contingent on harvesting conditions that the Department itself acknowledges are unlikely to be fully realized due to budgetary, operability, and market constraints.
- `leaders`, run 2: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are negligible and inadequately weighed against potential losses, noting that even under the agency's own unlikely scenario of full operability, the estimated annual revenue increases are capped at $5.2 to $11.4 million for the Treasury and Forest Service and $4.6 to $10.6 million for the timber industry, representing only a 5 to 10 percent increase in national sawtimber harvest.
- `leaders`, run 3: The projected economic gains from rescinding the Roadless Rule are negligible, with annual revenue to the Treasury and Forest Service estimated at only $5.2 to $11.4 million and $4.6 to $10.6 million to the timber industry, figures that assume a 5–10% increase in harvest volume on approximately 4.8 million operable acres—a scenario the agency itself deems unlikely due to budget, operability, and market constraints.
- `collapse`, run 1: Commenters argue that the proposed rule's estimated annual timber revenue gains of $5.2 to $11.4 million for the government and $4.6 to $10.6 million for industry are disproportionately small relative to the broader economic, environmental, and social costs of expanding logging, and they are based on a 5-10 percent harvest increase that the agency itself concedes is unlikely to be fully realized due to budget, operability, and market constraints.
- `collapse`, run 2: The economic analysis projects minimal annual revenue gains of $5.2 to $11.4 million for the government and $4.6 to $10.6 million for the timber industry based on a 5-10% increase in sawtimber harvest, which the proposal itself deems unlikely to be fully realized due to budget, operability, and market constraints.
- `collapse`, run 3: The proposed rule's economic analysis is flawed because it projects a maximum annual revenue gain of $5.2 to $11.4 million for the government and $4.6 to $10.6 million for the timber industry from a 5-10% increase in harvest, while simultaneously acknowledging that full realization is unlikely due to budget, operability, and market constraints, thereby presenting a minimal and uncertain economic benefit that does not justify the broader ecological and social costs.

<!-- end statements -->

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
   and runs 2 and 3 are the same. Run 1 is the first call with that prompt, when LM
   Studio holds no cache of it. In trial 20261024_162538, every prompt had been sent
   before, and all runs at 0 were the same.
3. Most differences at temperature 0 are a few words. For example, Qwen cluster 207 has
   "roads increase ignition rates" in one run and "roads drive ignition rates upward" in
   the other. One difference changes the point: BGE cluster 187 with the `leaders`
   wordings. Run 1 says that the DEIS does not carry habitat connectivity and patch size
   into the comparison of alternatives. Runs 2 and 3 say that it ignores the shared
   habitat of 14 species between areas 418040 and 418006.
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

### The statements, Qwen (trial 20261024_163447)

<!-- statements 20261024_163447 -->

Case `opening.plain.text-embedding-qwen3-embedding-8b-f16.m95.umap5.10-10-eom.all.p1.kauto.s0`. Model `qwen/qwen3.8-27b`. File `trials/statements/20261024_163447.json`.

#### Cluster 52, topic 1: nepa, cir, usda cir, clause, california rel, rel, rel lockyer, circuit

45 sentences; 41 wordings as `leaders`, 41 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth Circuit in Wyoming v. USDA and the Ninth Circuit in California ex rel. Lockyer v. USDA have already rejected the argument that forest-level planning is a sufficient substitute for a national rule, thereby rendering the proposed action arbitrary, capricious, and legally invalid.
- `leaders`, runs 2, 3: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth Circuit in Wyoming v. USDA and the Ninth Circuit in California ex rel. Lockyer v. USDA have already rejected the argument that decentralized, forest-by-forest planning is a legally sufficient substitute for a uniform national standard.
- `collapse`, runs 1, 2, 3: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth and Ninth Circuits have already rejected the argument that decentralized, forest-by-forest planning is a legally sufficient substitute for a uniform national standard.

Temperature 0.7:

- `leaders`, run 1: The proposed rescission violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because it fails to conduct a programmatic 'hard look' analysis of cumulative environmental impacts and improperly relies on fragmented, local forest plans that courts have already found insufficient to protect roadless areas, contrary to the holdings in Wyoming v. USDA and California ex rel. Lockyer v. USDA.
- `leaders`, run 2: Commenters argue that the rescission of the 2001 Roadless Rule violates the National Environmental Policy Act (NEPA), the Administrative Procedure Act (APA), and the National Forest Management Act (NFMA) because the agency failed to conduct a programmatic 'hard look' at cumulative environmental impacts, inadequately analyzed greenhouse gas emissions, and improperly decentralized uniform national protections to local forest plans contrary to prior judicial holdings in Wyoming v. USDA and California ex rel. Lockyer v. USDA.
- `leaders`, run 3: The rescission proposal fails to satisfy the National Environmental Policy Act and other federal statutes, including the National Forest Management Act, the Endangered Species Act, and the National Historic Preservation Act, because it relies on decentralized local planning that has already been judicially rejected as inadequate for protecting roadless areas from cumulative environmental degradation.
- `collapse`, run 1: The rescission of the 2001 Roadless Area Conservation Rule violates NEPA, the NFMA, and the APA because it fails to take a 'hard look' at the cumulative environmental impacts of removing national protections, ignores the legal precedent that local planning is insufficient for this conservation issue, and disregards the agency's own findings and the extensive litigation history that established the rule's validity.
- `collapse`, run 2: The rescission of the 2001 Roadless Rule is legally deficient because it fails to comply with the National Environmental Policy Act (NEPA) and the Administrative Procedure Act (APA) by inadequately analyzing the rule's environmental and species impacts, and it improperly substitutes a litigated national standard with fragmented local plans, contrary to the holdings in Wyoming v. USDA and California ex rel. Lockyer v. USDA that reject the agency's rationale for decentralization.
- `collapse`, run 3: The rescission is legally invalid because it violates the National Environmental Policy Act, the National Forest Management Act, the Endangered Species Act, and the Administrative Procedure Act, fails to conduct the required programmatic 'hard look' at cumulative environmental impacts, and substitutes a decentralized planning model that courts have already rejected for inadequacy.

#### Cluster 1, topic 2: wildfire, human-caused, roads, wildfires, fires, ignitions, ignition, areas

541 sentences; 386 wordings as `leaders`, 389 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for rescission is consistent with its own draft environmental impact statement and peer-reviewed data demonstrating that road construction significantly increases human-caused wildfire ignition risk, and must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.
- `collapse`, runs 1, 2, 3: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for rescission reconciles with its own draft environmental impact statement and peer-reviewed data demonstrating that road construction significantly increases human-caused ignition risk, and it must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.

Temperature 0.7:

- `leaders`, run 1: New road construction in inventoried roadless areas will increase, rather than reduce, wildfire risk because roads are the primary vector for human-caused ignitions, which constitute the vast majority of wildfires and are significantly more frequent near roads than in roadless terrain. The agency must explain why it departs from its own findings that road density correlates with higher ignition rates and must quantitatively calculate the net increase in human-caused ignitions introduced by new road access to weigh against any claimed hazard reduction.
- `leaders`, run 2: Commenters assert that the proposal’s wildfire and fuels management justifications contradict the best available science and the agency’s own data, which demonstrate that road construction increases human-caused ignition risk while inventorial roadless areas exhibit the lowest ignition densities; they request that the agency quantify the net increase in human-caused ignitions resulting from new road access and reconcile this risk with the claimed reduction in wildfire hazard.
- `leaders`, run 3: The agency must explain why it is departing from its own findings that human-caused ignition density is significantly higher on roaded lands than in inventoried roadless areas, and quantify the expected increase in human-caused ignitions resulting from new road construction to demonstrate that the net wildfire risk reduction from rescission outweighs the increased ignition risk.
- `collapse`, run 1: The agency must reconcile the proposal's reliance on wildfire and fuels management as a justification for rescission with its own Draft Environmental Impact Statement findings and peer-reviewed data, which demonstrate that increased road density correlates with a significantly higher incidence of human-caused wildfire ignitions, and must quantify the expected net increase in ignition risk from new road construction rather than asserting that roads reduce fire hazard.
- `collapse`, run 2: The proposal justifies rescission on wildfire and fuels management grounds, but the agency's own draft EIS and peer-reviewed data show that new roads dramatically increase human-caused ignition risk; the agency must quantify this increase and explain how it reconciles the rescission with its own findings that roadless areas have significantly lower fire ignition densities.
- `collapse`, run 3: The proposal justifies rescission on wildfire and fuels management grounds, yet its own draft environmental impact statement and cited peer-reviewed data demonstrate that new road construction would significantly increase human-caused wildfire ignition risk, which the agency has failed to quantify or weigh against any claimed reduction in wildfire hazard.

#### Cluster 207, topic 2: justifies rescission, management grounds, fuels management, ignition, justifies, grounds, solution, proposal justifies

11 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `collapse`, run 1: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads drive ignition rates upward, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `collapse`, runs 2, 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.

Temperature 0.7:

- `leaders`, run 1: The agency must reconcile its reliance on wildfire and fuels management as justifications for the rescission with its own data demonstrating that roads drive higher ignition rates, explaining how adding roads reduces fire risk when its analysis identifies roads as an accelerant rather than a solution.
- `leaders`, run 2: The agency justifies the rescission on wildfire and fuels management grounds, yet its own data demonstrates that roads increase ignition rates rather than reduce fire risk, requiring the agency to reconcile this contradiction.
- `leaders`, run 3: The agency must reconcile the use of wildfire and fuels management as a justification for rescission with its own data establishing that roads drive ignition rates, rather than reducing fire risk.
- `collapse`, run 1: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads drive ignition rates upward, rather than reducing fire risk.
- `collapse`, run 2: The agency must reconcile its reliance on wildfire and fuels management as a justification for the rescission with its own prior data demonstrating that roads drive ignition rates upward rather than reducing fire risk.
- `collapse`, run 3: The agency must explain how it can justify the rescission on wildfire and fuels management grounds when its own data and findings establish that road construction increases ignition rates and acts as a fire accelerant rather than a solution.

#### Cluster 104, topic 5: revenue, treasury, million, treasury forest, revenue treasury, million year, unlikely, timber industry

26 sentences; 26 wordings as `leaders`, 26 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, even under a full-harvest scenario that the agency itself deems unlikely due to budget, operability, and market constraints.
- `collapse`, runs 1, 2, 3: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, even under a full-harvest scenario that the agency itself deems unlikely due to budget, operability, and market constraints.

Temperature 0.7:

- `leaders`, run 1: Commenters question the validity of the economic analysis, which projects only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry even under a fully realized, albeit unlikely, harvest scenario. They argue these modest figures are disproportionately low and cannot be honestly weighed against the projected losses to recreation, tourism, and broader economic benefits.
- `leaders`, run 2: The projected economic benefits of expanded timber harvesting are minimal, limited to an estimated $5.2 to $11.4 million in annual revenue for the federal government and $4.6 to $10.6 million for the timber industry, and are contingent on full harvest realization in operable areas that the agency itself deems unlikely due to budget, operability, and market constraints.
- `leaders`, run 3: The proposed rule projects only modest annual revenue increases of $5.2 to $11.4 million for the Treasury and Forest Service and $4.6 to $10.6 million for the timber industry, assuming a 5 to 10 percent increase in sawtimber harvest that the Department itself deems unlikely due to budget, operability, and market constraints. Commenters contend that these limited economic gains are disproportionately small and cannot honestly justify the broader losses to recreation, tourism, and local economies estimated in the billions of dollars.
- `collapse`, run 1: The Department’s economic analysis projects a maximum annual revenue gain of $5.2 to $11.4 million for the Treasury and Forest Service and $4.6 to $10.6 million for the timber industry, figures based on a 5-10% increase in harvest volume that the agency itself acknowledges is unlikely to be fully realized due to budget, operability, and market constraints.
- `collapse`, run 2: Commenters assert that the projected annual timber revenue increments of $5.2 to $11.4 million for the Treasury and Forest Service and $4.6 to $10.6 million for the industry are modest, conditional on unlikely full harvest realization due to budget, operability, and market constraints, and disproportionately small relative to the estimated economic and recreational losses from rescinding the rule.
- `collapse`, run 3: Commenters assert that the estimated incremental revenue from expanded timber harvesting is disproportionately low relative to the projected economic losses to recreation and tourism, and that the agency's own analysis identifies the full realization of these revenue figures as unlikely due to budget, operability, and market constraints.

<!-- end statements -->

### The statements, BGE (trial 20261024_163949)

The BGE clusters that hold most of a Qwen cluster's sentences: 8 for Qwen 104, 30 for
Qwen 1, 12 for Qwen 207, 121 for Qwen 52.

<!-- statements 20261024_163949 -->

Case `opening.plain.text-embedding-bge-large-en-v1-5.m95.umap5.10-10-eom.all.p0.kauto.s0`. Model `qwen/qwen3.8-27b`. File `trials/statements/20261024_163949.json`.

#### Cluster 1, topic 1: sediment, water, road, water quality, trout, roads, quality, construction

196 sentences; 181 wordings as `leaders`, 181 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: Commenters assert that road construction and associated timber harvesting in inventoried roadless areas will cause severe soil erosion, landslides, and chronic sedimentation that degrades water quality, impairs municipal drinking water supplies, and destroys critical aquatic habitats for sensitive species such as salmon, trout, and amphibians.
- `collapse`, runs 1, 2, 3: Commenters assert that rescinding the Roadless Rule would authorize new road construction and timber harvesting in steep, erosion-prone terrains, leading to severe soil erosion, chronic sedimentation, and altered hydrology that degrade water quality, threaten municipal drinking water supplies, and destroy critical aquatic habitats for sensitive species such as salmon, trout, and amphibians.

Temperature 0.7:

- `leaders`, run 1: Road construction and timber harvesting in inventoried roadless areas will increase soil erosion, sedimentation, and nonpoint source pollution, thereby degrading water quality, impairing aquatic habitats for sensitive species, and increasing the frequency of landslides and flooding.
- `leaders`, run 2: Rescission of the Roadless Rule would authorize new road construction and timber harvesting in inventoried roadless areas, which are currently characterized by limited disturbance and high water quality, leading to severe increases in soil erosion and sediment delivery. This sedimentation would degrade water quality, harm aquatic habitats and species (such as salmon, trout, and amphibians), threaten municipal drinking water supplies, and exacerbate landslides and flooding, directly contradicting the agency's own analysis that roadless areas provide the greatest protection for water resources.
- `leaders`, run 3: Road construction increases soil erosion, sedimentation, and mass wasting, which degrades water quality and threatens aquatic habitats, drinking water supplies, and downstream communities.
- `collapse`, run 1: Road construction and timber harvesting in inventoried roadless areas will exacerbate soil erosion and sedimentation, leading to chronic stream pollution, degraded water quality for municipal and ecological uses, and increased landslide and flood risks, particularly in steep and erosion-prone terrains.
- `collapse`, run 2: Road construction and associated timber harvest in inventoried roadless areas drive severe soil erosion, chronic sedimentation, landslides, and altered hydrology that degrade water quality and destroy critical aquatic habitats, directly threatening the survival of sensitive native species and municipal drinking water supplies.
- `collapse`, run 3: Commenters assert that the rescission of the 2001 Roadless Rule would authorize new road construction and timber harvesting in inventoried roadless areas, resulting in severe soil erosion, increased stream sedimentation, and altered hydrology that degrade water quality and destroy critical aquatic habitat for native species such as salmon and trout, while also threatening municipal drinking water supplies and downstream communities.

#### Cluster 30, topic 1: increase incidence, incidence human-caused, risk uncharacteristic, high risk, road forest, wildfire effects, uncharacteristic wildfire, uncharacteristic

97 sentences; 57 wordings as `leaders`, 60 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: The proposal justifies rescission on wildfire and fuels management grounds, yet the agency's own environmental impact statement finds that building roads into high-risk forests increases the incidence of human-caused fires.
- `collapse`, run 1: The proposal justifies rescission on wildfire and fuels management grounds, yet the agency's own environmental impact statement finds that building roads into high-risk forests increases the incidence of human-caused fires.
- `collapse`, runs 2, 3: The proposal justifies rescission on wildfire and fuels management grounds, but the agency's own environmental impact statement finds that building roads into high-risk forests increases the incidence of human-caused fires.

Temperature 0.7:

- `leaders`, run 1: The agency justifies rescission of the Roadless Rule on wildfire and fuels management grounds, yet its own environmental impact statement finds that building roads into roadless areas increases the incidence of human-caused fires.
- `leaders`, run 2: The proposal justifies rescission on wildfire and fuels management grounds, yet the agency's own environmental impact statement indicates that building new roads into high-risk forests increases the incidence of human-caused fires and that roaded lands carry a significantly higher ignition risk than unroaded lands.
- `leaders`, run 3: The proposal cites wildfire and fuels management as justifications for rescinding the Roadless Rule, yet the agency's own environmental impact statement findings indicate that building roads increases the incidence of human-caused fires.
- `collapse`, run 1: The proposal justifies the rescission of the Roadless Rule by citing wildfire and fuels management benefits, but this rationale conflicts with the agency's own environmental impact statement findings that building new roads into high-risk forests significantly increases the incidence of human-caused fires, creates a self-defeating cycle where timber harvest requires roads that raise fire risk, and fails to quantify the expected increase in ignitions or compare nationwide rescission against alternatives limited to areas with demonstrated significant wildfire risk.
- `collapse`, run 2: The agency justifies the rescission of the Roadless Rule partly on wildfire and fuels management grounds, yet its own environmental impact statement and prior findings indicate that building roads into forests at high risk from uncharacteristic wildfire effects could increase the incidence of human-caused fires, creating a self-defeating cycle where the primary justification for the rule change requires road construction that demonstrably increases fire risk.
- `collapse`, run 3: The proposal justifies rescission on wildfire and fuels management grounds, yet the agency's own environmental record indicates that building roads into high-risk forests increases the incidence of human-caused fires.

#### Cluster 47, topic 1: watersheds containing, water intakes, intakes, containing, containing affected, municipal water, municipal, sit watersheds

51 sentences; 43 wordings as `leaders`, 43 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 3: The rescission fails to adequately analyze the water quality and cost impacts on the more than 7,000 municipal water intakes located in watersheds containing affected roadless areas, as documented in DEIS Table 35, by relying on qualitative assertions rather than specific modeling of sediment, pathogen risk, and treatment costs.
- `leaders`, run 2: The rescission fails to adequately analyze the water quality and public health impacts on the more than 7,000 municipal water intakes located in watersheds containing affected roadless areas, as documented in DEIS Table 35, by relying on qualitative assertions rather than specific modeling of sediment loads, pathogen risks, and treatment costs.
- `collapse`, runs 1, 2, 3: The agency's own DEIS Table 35 documents that more than 7,000 municipal water intakes across all regions sit in watersheds containing potentially affected roadless areas, yet the environmental analysis fails to quantify the specific water quality, sediment, and treatment cost impacts on these downstream communities, relying instead on qualitative assertions and procedural dismissals.

Temperature 0.7:

- `leaders`, run 1: Commenters assert that the rescission proposal fails to adequately analyze the water quality and cost impacts on the more than 7,000 municipal water intakes located within watersheds containing inventoried roadless areas, arguing that the DEIS relies on qualitative or programmatic language rather than specific modeling of sediment, pathogen risks, and downstream treatment costs.
- `leaders`, run 2: The agency failed to adequately analyze the water quality and public health risks to the more than 7,000 municipal water intakes located in watersheds containing inventoried roadless areas, relying on qualitative assertions rather than specific modeling of sediment, erosion, and treatment costs.
- `leaders`, run 3: Municipal water intakes within watersheds containing roadless areas face water quality and treatment cost risks that the agency's qualitative analysis and cost-benefit assessment fail to adequately quantify or account for.
- `collapse`, run 1: Commenters assert that the rescission fails to adequately analyze the water quality impacts on the more than 7,000 municipal water intakes located in watersheds containing affected roadless areas, as the DEIS provides only qualitative and programmatic assessments rather than specific modeling of sediment loads, pathogen risks, or drinking water treatment costs. They argue that the agency has not properly weighed the downstream reliance interests of these communities or the long-term costs and risks associated with road-building in these critical watersheds.
- `collapse`, run 2: The rescission fails to adequately analyze the water quality impacts and increased costs to the more than 7,000 municipal water intakes located in watersheds containing roadless areas, relying instead on qualitative assertions and inadequate cost-benefit analysis.
- `collapse`, run 3: The DEIS acknowledges that more than 7,000 municipal water intakes are located within watersheds containing roadless areas, yet the agency fails to provide specific, quantitative analysis of the water quality impacts, sediment loads, and treatment cost increases to these communities, relying instead on qualitative assertions and procedural dismissals.

#### Cluster 187, topic 1: biodiversity percent, reduces biodiversity, fragmentation reduces, finding habitat, acres potentially, biodiversity, cites finding, reduces

19 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS fails to project the cited 13 to 75 percent biodiversity reduction from habitat fragmentation across the 40.1 million acres of potentially affected environment, and it does not carry quantitative measures of habitat connectivity and patch size into the comparison of alternatives, including the specific overlap of species between adjacent units.
- `leaders`, runs 2, 3: The DEIS fails to project the cited 13 to 75 percent biodiversity reduction range across the 40.1 million acres of potentially affected environment, and it ignores the shared habitat of 14 species between planning area 418040 and the adjacent 418006 area.
- `collapse`, runs 1, 2, 3: The DEIS fails to project the cited 13 to 75 percent biodiversity reduction range from habitat fragmentation across the 40.1 million acres of potentially affected environment, and it does not carry quantitative habitat connectivity and patch size measures into the comparison of alternatives.

Temperature 0.7:

- `leaders`, run 1: The DEIS fails to apply the cited finding that habitat fragmentation reduces biodiversity by 13 to 75 percent to the 40.1 million acres of potentially affected environment, and it isolates specific species (such as 418040) from nearby units (such as 418006) while failing to carry quantitative habitat connectivity results into the comparison of alternatives.
- `leaders`, run 2: The DEIS fails to project the cited 13 to 75 percent reduction in biodiversity due to habitat fragmentation across the 40.1 million acres of potentially affected environment, nor does it carry quantitative measures of habitat connectivity and patch size into the comparison of alternatives, including specific instances where isolated analysis ignores shared species with nearby units.
- `leaders`, run 3: The DEIS fails to project the cited 13-75 percent biodiversity reduction from habitat fragmentation across the 40.1 million acres of potentially affected environment, nor does it carry quantitative measures of habitat connectivity into the comparison of alternatives or account for specific species shared across forest units.
- `collapse`, run 1: The DEIS fails to project the cited 13 to 75 percent biodiversity reduction from habitat fragmentation across the 40.1 million acres of potentially affected environment, nor does it carry quantitative connectivity measures into the alternatives comparison or integrate them with specific species data shared with adjacent units.
- `collapse`, run 2: The DEIS fails to project the cited 13 to 75 percent reduction in biodiversity due to habitat fragmentation across the 40.1 million acres of potentially affected environment, and it analyzes specific areas in isolation while neglecting to carry quantitative fragmentation and connectivity measures through the comparison of alternatives.
- `collapse`, run 3: The DEIS fails to project the cited 13 to 75 percent reduction in biodiversity from habitat fragmentation across the 40.1 million acres of potentially affected environment, and it isolates roadless area 418040 from the 14 shared species and connectivity metrics associated with adjacent area 418006.

#### Cluster 12, topic 2: density roaded, roaded land, far higher, higher density, land inside, inside affected, reports far, deis table

206 sentences; 87 wordings as `leaders`, 86 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain on the record why the rescission departs from its own prior findings that roads increase ignition risk, and reconcile the proposal with the ignition data in DEIS Table 21, which reports far higher fire density on roaded land than inside the affected roadless areas.
- `leaders`, runs 2, 3: Commenters contend that the agency must explain on the record why the rescission departs from its own prior findings that roads increase ignition risk, and reconcile the proposal with the ignition data in DEIS Table 21, which reports far higher fire density on roaded land than inside the affected roadless areas.
- `collapse`, runs 1, 2, 3: The agency must explain why the rescission departs from its own prior findings that roads increase ignition risk, and reconcile the proposal with the ignition data in DEIS Table 21, which reports far higher fire density on roaded land than inside the affected roadless areas.

Temperature 0.7:

- `leaders`, run 1: Commenters require the agency to explain on the record why the rescission departs from its own prior findings that roads increase ignition risk, and to reconcile the proposal with the ignition data in its own draft environmental impact statement (DEIS Table 21), which reports far higher fire density on roaded land than inside the affected roadless areas.
- `leaders`, run 2: The agency must explain on the record why the rescission departs from its own prior findings that roads increase ignition risk, and reconcile the action with the data in DEIS Table 21, which reports far higher fire density on roaded land than inside the affected roadless areas.
- `leaders`, run 3: How the agency reconciles the rescission of the Roadless Rule with its own draft environmental impact statement (DEIS) findings, specifically Table 21, which reports significantly higher fire density and ignition risk on roaded land than in the affected roadless areas, and explains why expanding the road network into these protected areas advances rather than undermines fire and fuels management objectives.
- `collapse`, run 1: Commenters assert that the agency must explain why the rescission departs from its own prior findings that roads increase ignition risk and reconcile this action with DEIS Table 21, which reports far higher fire density on roaded land than inside the affected roadless areas.
- `collapse`, run 2: The agency must explain on the record why the rescission departs from its own prior findings that roads increase ignition risk and fire density, and how the justification of fire and fuels management reconciles with the data in DEIS Table 21 reporting far higher fire density on roaded land than inside the affected roadless areas.
- `collapse`, run 3: The agency must explain why the rescission departs from its own prior findings that roads increase ignition risk and reconcile the action with the data in DEIS Table 21, which reports far higher fire density on roaded land than inside the affected roadless areas.

#### Cluster 94, topic 3: cfr subpart, subpart, cfr, retain, preserve, retain cfr, remove reserve, conservation rule

28 sentences; 25 wordings as `leaders`, 25 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters urge the Forest Service to retain 36 CFR Part 294, Subpart B, and select the No Action alternative rather than rescinding the 2001 Roadless Area Conservation Rule, arguing that the national-level protections for inventoried roadless areas must remain intact to safeguard natural resources and wildlife habitat.
- `leaders`, runs 2, 3: Commenters request that the Forest Service retain 36 CFR Part 294, Subpart B, and select the No Action alternative to preserve the national-level protections for inventoried roadless areas, rather than rescinding the rule to replace them with forest-by-forest protections.
- `collapse`, runs 1, 2, 3: Commenters request that the Forest Service retain 36 CFR Part 294, Subpart B, and select the No Action alternative to preserve the national-level protections for inventoried roadless areas, rather than rescinding the rule to prevent new road construction and commercial timber harvesting.

Temperature 0.7:

- `leaders`, run 1: Commenters urge the Forest Service to retain 36 CFR Part 294, Subpart B and select the No Action alternative rather than rescinding the 2001 Roadless Area Conservation Rule, arguing that the current national-level protections for inventoried roadless areas should be preserved intact to safeguard natural resources and wildlife habitat.
- `leaders`, run 2: Commenters urge the Forest Service to retain 36 CFR Part 294, Subpart B, and the 2001 Roadless Area Conservation Rule, opposing the rescission of these national protections for inventoried roadless areas.
- `leaders`, run 3: Commenters urge the Forest Service to retain the national-level protections of the 2001 Roadless Area Conservation Rule (36 CFR Part 294, Subpart B) rather than rescinding or removing and reserving them, arguing that this rule is the most effective mechanism to safeguard inventoried roadless areas, natural resources, and wildlife habitat from new road construction and timber harvest.
- `collapse`, run 1: Commenters oppose the removal and reservation of 36 CFR Part 294, Subpart B, urging the Forest Service to retain the 2001 Roadless Area Conservation Rule and its national-level protections for inventoried roadless areas as the most effective safeguard for natural resources, wildlife habitat, and wilderness, rather than replacing them with less comprehensive forest-by-forest management or opening these lands to new road construction and commercial timber.
- `collapse`, run 2: The rescission of 36 CFR Part 294, Subpart B would eliminate the uniform national protections for inventoried roadless areas, and commenters urge the Forest Service to retain these regulations entirely rather than replacing them with forest-specific management.
- `collapse`, run 3: Commenters urge the Forest Service to retain 36 CFR Part 294, Subpart B and the 2001 Roadless Area Conservation Rule in full, arguing that the national-level protections are the most effective mechanism to safeguard inventoried roadless areas, preserve natural resources and wildlife habitat, and prevent irreversible damage from new road construction and commercial timber harvesting.

#### Cluster 121, topic 3: cfr, cfr rin, rin, federal register, register, comment, cfr comment, federal

20 sentences; 19 wordings as `leaders`, 19 as `collapse`.

Temperature 0:

- `leaders`, runs 1, 2, 3: Commenters assert that the rescission of 36 CFR Part 294, specifically sections 294.12 and 294.13, is legally invalid under the Administrative Procedure Act and the National Forest Management Act, and that the agency’s stated focus on increasing economic opportunity is inconsistent with statutory mandates.
- `collapse`, runs 1, 2: Commenters assert that the rescission of 36 CFR Part 294, specifically the prohibitions in §§ 294.12 and 294.13, is legally invalid under the Administrative Procedure Act and the National Forest Management Act, and that the agency’s stated focus on increasing economic opportunity is inconsistent with the statutory mandate to protect roadless areas.
- `collapse`, run 3: Commenters assert that the rescission of 36 CFR Part 294, specifically the prohibitions in §§ 294.12 and 294.13, is legally invalid under the Administrative Procedure Act and the National Forest Management Act, and that the agency’s stated focus on increasing economic opportunity is inconsistent with statutory mandates.

Temperature 0.7:

- `leaders`, run 1: Commenters assert that the 2001 Roadless Rule, codified at 36 CFR Part 294, is valid and enforceable, and that the Forest Service’s proposal to rescind it violates the Administrative Procedure Act and the National Environmental Policy Act by relying on an insufficient record and failing to properly account for the 178 individually received comments and public petitions.
- `leaders`, run 2: Commenters contend that the proposed rescission of 36 CFR Part 294 is procedurally and substantively flawed, asserting that the agency failed to properly count all submitted comments, ignored the statutory authority of 16 U.S.C. 1131(a), and violated the Administrative Procedure Act by prioritizing economic opportunity over the environmental protections required by the statute and existing regulations, particularly regarding the prohibitions in 36 CFR §§ 294.12 and 294.13.
- `leaders`, run 3: The 36 CFR Part 294 rulemaking, specifically Sections 294.12 and 294.13, was promulgated without adequate notice, proper identification of the affected CFR parts, or consideration of the statutory requirements of 16 USC 1131(a) and the Administrative Procedure Act, creating uncertainty regarding the legal scope and procedural validity of the proposed rescission.
- `collapse`, run 1: The commenters identify the specific regulatory action as the rescission of 36 CFR Part 294 (RIN 0596-AD66), specifically addressing Subpart B and sections 294.12–294.13, and assert that the action is subject to review under the Administrative Procedure Act and the National Forest Management Act.
- `collapse`, run 2: The rescission of 36 CFR Part 294 violates the Administrative Procedure Act and federal law, including 16 U.S.C. 1131(a), because the agency failed to adequately count individual public comments, such as those signed petitions, in its rulemaking process.
- `collapse`, run 3: Commenters assert that the proposed rule, 36 CFR Part 294 (specifically 36 CFR §§ 294.12–294.13), violates the Administrative Procedure Act, the National Forest Management Act, and other statutory requirements, and they demand that the agency count each individual signature on submitted petitions as a separate, official comment on the docket.

#### Cluster 8, topic 5: million year, million, year, revenue, analysis projects, million million, year net, losses million

189 sentences; 107 wordings as `leaders`, 109 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters contend that the agency's own cost-benefit analysis demonstrates that the projected timber revenue of $5.2 to $11.4 million per year is insufficient to offset the estimated recreation losses of at least $6.1 million per year, fails to establish a reliable net benefit given a net present value range of -$92 million to +$199 million, and is economically unjustifiable when weighed against the existing $6.9 billion road maintenance backlog.
- `leaders`, runs 2, 3: Commenters contend that the agency's own cost-benefit analysis fails to justify rescission because the projected timber revenue of $5.2 to $11.4 million annually is marginal, is offset by recreation losses of at least $6.1 million annually, and results in a net present value that ranges from negative $92 million to positive $199 million, all while expanding a road system already burdened by a $6.9 billion maintenance backlog.
- `collapse`, run 1: Commenters assert that the agency's own cost-benefit analysis fails to establish a net economic benefit for rescinding the Roadless Rule, as projected timber revenue of $5.2 to $11.4 million annually is offset by recreation losses of at least $6.1 million annually and a net present value ranging from -$92 million to +$199 million, while the action would expand a road system already carrying a $6.9 billion maintenance backlog.
- `collapse`, runs 2, 3: Commenters assert that the agency's own cost-benefit analysis fails to establish a net economic benefit for rescinding the Roadless Rule, as the projected timber revenue of $5.2 to $11.4 million annually is offset by recreation losses of at least $6.1 million annually and a net present value ranging from -$92 million to +$199 million, while the action would expand a road system already carrying a $6.9 billion maintenance backlog.

Temperature 0.7:

- `leaders`, run 1: The agency must reconcile the proposal with its own cost-benefit analysis, which projects marginal timber revenue of $5.2 to $11.4 million per year against recreation losses of at least $6.1 million per year and an unresolved net present value ranging from negative $92 million to positive $199 million, and explain how these modest and uncertain economic gains justify expanding a road system that already carries a $6.9 billion deferred maintenance backlog.
- `leaders`, run 2: The agency's own cost-benefit analysis projects modest and uncertain timber revenue gains of $5.2 to $11.4 million per year, which are offset by recreation losses of at least $6.1 million per year and a net present value ranging from -$92 million to +$199 million, failing to establish a net benefit while expanding a road system already carrying a $6.9 billion maintenance backlog.
- `leaders`, run 3: Commenters assert that the rescission's projected economic benefits are trivial relative to its costs, as the agency's own analysis estimates a maximum 5-10% increase in national sawtimber harvest generating only $5.2 to $11.4 million annually for the government and $4.6 to $10.6 million for the timber industry, which is offset by at least $6.1 million in annual recreation losses, a net present value ranging from -$92 million to +$199 million, and the permanent addition of road maintenance obligations to a system already carrying a $6.9 billion deferred maintenance backlog.
- `collapse`, run 1: The agency must reconcile the proposal with its own cost-benefit analysis, which projects $5.2 to $11.4 million in annual timber revenue against $6.1 million in annual recreation losses and a net present value ranging from -$92 million to +$199 million, and explain how an action that cannot establish a clear net benefit justifies expanding a road system already carrying a $6.9 billion maintenance backlog.
- `collapse`, run 2: The proposal rests on economic benefits that the agency's own Cost Benefit Analysis fails to establish as a net benefit, projecting only $5.2 to $11.4 million in annual timber revenue to the federal government and $4.6 to $10.6 million to the industry against recreation losses of at least $6.1 million per year, a net present value ranging from -$92 million to +$199 million, and the expansion of a road system already carrying a $6.9 billion maintenance backlog.
- `collapse`, run 3: The agency’s own cost-benefit analysis projects that rescission would yield only $5.2 to $11.4 million in annual timber revenue against estimated recreation losses of at least $6.1 million and a net present value ranging from -$92 million to +$199 million, and commenters ask the agency to reconcile this failure to establish a clear net economic benefit with the decision to expand a road system already carrying a $6.9 billion maintenance backlog.

<!-- end statements -->

## Trial 20261024_170736 (Qwen, temperatures 0.1, 0.2 and 0.4)

**The question.** Temperatures 0 and 0.7 are far apart. Where between them does the
statement start to change?

**The settings.** The Qwen concern map, clusters 207, 104, 52 and 1, both methods, 3 runs
at each of 0.1, 0.2 and 0.4: 72 calls. File `trials/statements/20261024_170736.json`.
Code `236e5b9`. The model had 262,000 tokens of context configured. 452,340 tokens in,
5,875 out, no cost.

**Different statements among the 3 runs.**

| Cluster | `leaders` 0.1 | 0.2 | 0.4 | `collapse` 0.1 | 0.2 | 0.4 |
|---|---|---|---|---|---|---|
| 207 | 1 | 2 | 3 | 2 | 2 | 3 |
| 104 | 3 | 3 | 3 | 3 | 3 | 3 |
| 52 | 3 | 3 | 3 | 3 | 3 | 3 |
| 1 | 3 | 3 | 3 | 3 | 3 | 3 |

**How far the words move.** Each statement is compared with the statement of run 3 at
temperature 0 for the same cluster and method (trial 20261024_163447). The measure is
the share of words in the same order (Python's `difflib.SequenceMatcher` on the words):
1 is the same statement. Each temperature has 24 statements.

| Temperature | Median | Lowest |
|---|---|---|
| 0 | 1.00 | 0.91 |
| 0.1 | 0.88 | 0.40 |
| 0.2 | 0.82 | 0.41 |
| 0.4 | 0.50 | 0.19 |
| 0.7 | 0.49 | 0.23 |

| Cluster | 0 | 0.1 | 0.2 | 0.4 | 0.7 |
|---|---|---|---|---|---|
| 207 | 1.00 | 1.00 | 0.92 | 0.67 | 0.52 |
| 104 | 1.00 | 0.79 | 0.83 | 0.51 | 0.49 |
| 52 | 1.00 | 0.74 | 0.80 | 0.36 | 0.43 |
| 1 | 1.00 | 0.94 | 0.59 | 0.47 | 0.41 |

**What the trial found.**

1. Only temperature 0 gives the same statement in each run (with the cold-call
   exception of the trials before). At 0.1, 6 of the 8 settings (4 clusters, 2
   methods) give a different statement in each run.
2. At 0.1 and 0.2, most statements keep most of the words of the statement at 0
   (median 0.88 and 0.82). Some do not: the lowest is 0.40 at 0.1.
3. Between 0.2 and 0.4, the statements move far: the median falls from 0.82 to 0.50.
   At 0.4 they are as far from the statement at 0 as at 0.7.
4. The smallest cluster (207, 10 wordings) holds its statement longest. The larger
   clusters move at lower temperatures.

**For step 15.** Use temperature 0. No temperature above 0 keeps the statement from
run to run.

### The statements

<!-- statements 20261024_170736 -->

Case `opening.plain.text-embedding-qwen3-embedding-8b-f16.m95.umap5.10-10-eom.all.p1.kauto.s0`. Model `qwen/qwen3.8-27b`. File `trials/statements/20261024_170736.json`.

#### Cluster 52, topic 1: nepa, cir, usda cir, clause, california rel, rel, rel lockyer, circuit

45 sentences; 41 wordings as `leaders`, 41 as `collapse`.

Temperature 0.1:

- `leaders`, run 1: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth and Ninth Circuits have already rejected the argument that decentralized, forest-by-forest planning is a legally sufficient substitute for a uniform national standard.
- `leaders`, run 2: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental impacts of removing national protections, a deficiency previously identified by the Ninth and Tenth Circuits when they vacated similar rollbacks and upheld the 2001 Rule as a necessary national standard that local forest-by-forest planning cannot adequately replace.
- `leaders`, run 3: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth Circuit in Wyoming v. USDA held that the Forest Service has the authority to enact national conservation standards, rendering the proposed shift to fragmented, discretionary local forest plans legally insufficient and likely to generate further litigation.
- `collapse`, run 1: Commenters assert that the proposed rescission violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act by failing to conduct a programmatic 'hard look' at cumulative environmental impacts, including greenhouse gas emissions and species effects, and by improperly substituting fragmented local forest plans for a uniform national standard, a legal approach previously rejected by the Tenth and Ninth Circuits in Wyoming v. USDA and California ex rel. Lockyer v. USDA.
- `collapse`, run 2: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth and Ninth Circuits have already rejected the argument that forest-level planning is the appropriate vehicle for managing roadless areas, rendering the proposed rule legally invalid and subject to vacatur.
- `collapse`, run 3: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, historic, and climate impacts of removing national protections, and because the Tenth and Ninth Circuits have already rejected the agency's argument that forest-level planning is the appropriate vehicle for managing roadless areas, thereby rendering the proposed rule arbitrary, capricious, and legally invalid.

Temperature 0.2:

- `leaders`, run 1: Commenters contend that the proposed rescission violates the National Environmental Policy Act, the Administrative Procedure Act, the National Forest Management Act, and the National Historic Preservation Act by failing to conduct a programmatic 'hard look' at cumulative environmental impacts, including greenhouse gas emissions and historic properties, and by improperly substituting fragmented local planning for a national standard that courts have previously upheld.
- `leaders`, run 2: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing nationwide protections, and because the Tenth and Ninth Circuits have already rejected the argument that decentralized, forest-by-forest planning is a legally sufficient substitute for a national rule, thereby rendering the proposed action arbitrary, capricious, and legally invalid.
- `leaders`, run 3: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth Circuit in Wyoming v. USDA and the Ninth Circuit in California ex rel. Lockyer v. USDA have already rejected the argument that forest-level planning is the appropriate vehicle for managing roadless areas, thereby rendering the proposed rule arbitrary, capricious, and legally invalid.
- `collapse`, run 1: Commenters assert that the proposed rescission violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act by failing to conduct a programmatic 'hard look' at cumulative environmental impacts and by improperly substituting fragmented local planning for a nationally uniform standard, a legal framework previously rejected by the Tenth and Ninth Circuits in Wyoming v. USDA and California ex rel. Lockyer v. USDA.
- `collapse`, run 2: The rescission of the 2001 Roadless Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and watershed impacts of removing national protections, and because the Tenth and Ninth Circuits have already rejected the agency's argument that decentralized, forest-by-forest planning is a legally sufficient substitute for a uniform national standard.
- `collapse`, run 3: The rescission violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental impacts of removing national protections, and the Tenth and Ninth Circuits have already rejected the argument that forest-level planning is the appropriate vehicle for managing roadless areas.

Temperature 0.4:

- `leaders`, run 1: Commenters assert that the proposed rescission violates NEPA, the Endangered Species Act, the National Historic Preservation Act, and the Administrative Procedure Act by failing to adequately analyze cumulative environmental impacts, relying on a flawed legal theory for decentralization that has been rejected by federal courts, and ignoring the statutory mandate for minimum road systems.
- `leaders`, run 2: Commenters assert that the rescission violates federal environmental and administrative laws, including NEPA, the APA, and NFMA, because the agency failed to take a 'hard look' at cumulative impacts and ignored prior court rulings (such as Wyoming v. USDA and California ex rel. Lockyer) that rejected forest-level planning as a sufficient substitute for national roadless protections.
- `leaders`, run 3: The rescission proposal fails to comply with NEPA, the APA, and NFMA because it relies on a flawed legal theory that forest-level planning is the exclusive vehicle for roadless protection, a position rejected by the Tenth Circuit in Wyoming v. USDA, and it fails to conduct the required programmatic 'hard look' at the cumulative environmental, watershed, and climate impacts of dismantling a national standard that has been upheld by courts as a durable, congressionally supported stewardship mechanism.
- `collapse`, run 1: Commenters argue that the proposed rescission violates NEPA, the APA, and the NFMA by failing to conduct a programmatic 'hard look' at cumulative environmental impacts, including greenhouse gas emissions and watershed degradation, and by improperly substituting fragmented local forest plans for a national standard that has been upheld in litigation.
- `collapse`, run 2: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act (NEPA), the Administrative Procedure Act (APA), and the National Forest Management Act (NFMA) because the agency’s proposed decentralization to forest-level planning fails to conduct the required 'hard look' at cumulative environmental impacts, including greenhouse gas emissions and watershed degradation, and ignores binding judicial precedents that affirmed the necessity of a national rule over fragmented local plans.
- `collapse`, run 3: The rescission of the 2001 Roadless Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act by failing to conduct a programmatic 'hard look' at the cumulative environmental, historical, and ecological impacts of removing national protections, thereby substituting a legally insufficient, fragmented local planning process for a durable, congressionally supported national standard that has been upheld by the courts.

#### Cluster 1, topic 2: wildfire, human-caused, roads, wildfires, fires, ignitions, ignition, areas

541 sentences; 386 wordings as `leaders`, 389 as `collapse`.

Temperature 0.1:

- `leaders`, run 1: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for rescission is consistent with its own Draft Environmental Impact Statement and peer-reviewed data demonstrating that road construction significantly increases human-caused wildfire ignition risk, and must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.
- `leaders`, run 2: The agency must explain how the proposal's reliance on wildfire risk reduction as a justification for rescission is consistent with its own draft environmental impact statement and peer-reviewed data demonstrating that road construction significantly increases human-caused wildfire ignition density, and must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.
- `leaders`, run 3: Commenters assert that the proposal's justification for rescission based on wildfire and fuels management is contradicted by peer-reviewed research and the agency's own Draft Environmental Impact Statement, which indicate that road construction significantly increases the density of human-caused wildfire ignitions in roadless areas. They request that the agency quantify the expected increase in human-caused ignitions resulting from new road access and reconcile this increased ignition risk with the claimed benefits of improved fire suppression and hazard reduction.
- `collapse`, run 1: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for rescission reconciles with its own draft environmental impact statement findings and peer-reviewed data demonstrating that road construction significantly increases human-caused ignition risk, and must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.
- `collapse`, run 2: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for rescission reconciles with its own draft environmental impact statement and peer-reviewed data demonstrating that road construction significantly increases human-caused ignition risk, and it must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.
- `collapse`, run 3: The proposal justifies rescission on wildfire and fuels management grounds, but the agency's own draft environmental impact statement and peer-reviewed data demonstrate that road construction increases human-caused ignition risk, creating a contradiction that the agency must resolve by quantifying the net increase in ignitions from new roads and explaining why it departs from its prior findings that roadless areas have significantly lower fire incidence.

Temperature 0.2:

- `leaders`, run 1: The agency must explain how the proposal's justification for rescission based on wildfire and fuels management is reconciled with its own draft environmental impact statement and peer-reviewed data demonstrating that road construction significantly increases human-caused wildfire ignition risk, and must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.
- `leaders`, run 2: The proposal justifies rescission on wildfire and fuels management grounds, but the agency's own draft environmental impact statement and peer-reviewed data demonstrate that road construction increases human-caused ignition risk, creating a contradiction that the agency must reconcile by quantifying the net increase in ignitions from new roads against any claimed hazard reduction.
- `leaders`, run 3: The agency must explain how its justification for rescission based on wildfire and fuels management is consistent with its own Draft Environmental Impact Statement and peer-reviewed data demonstrating that road construction and increased access significantly increase the density and likelihood of human-caused wildfire ignitions, and must quantify the expected net increase in ignition risk from new roads against any claimed reduction in wildfire hazard.
- `collapse`, run 1: The proposal justifies rescission on the grounds that new roads will improve wildfire management and reduce hazard, but the agency's own draft environmental impact statement and peer-reviewed data demonstrate that road construction significantly increases human-caused ignition risk, with ignition densities in roaded areas being up to four to seven times higher than in inventoried roadless areas. The agency must explain why it departs from these findings, quantify the expected increase in human-caused ignitions resulting from new road access, and weigh that increase against any claimed reduction in wildfire hazard.
- `collapse`, run 2: The proposal justifies rescission on wildfire and fuels management grounds, but the agency's own draft environmental impact statement and peer-reviewed data show that road construction increases human-caused ignition risk, creating a contradiction that must be quantified and reconciled.
- `collapse`, run 3: The agency must explain how the proposal's justification of rescission for wildfire and fuels management reconciles with its own draft EIS findings and peer-reviewed data showing that road construction significantly increases human-caused ignition risk, and must quantify the expected increase in ignitions from new road access to weigh against any claimed hazard reduction.

Temperature 0.4:

- `leaders`, run 1: The proposal justifies rescission on the grounds that new roads will improve wildfire management and reduce hazard, yet the agency's own draft environmental impact statement and cited peer-reviewed research demonstrate that road construction significantly increases the risk of human-caused wildfire ignitions, with ignition densities on roaded lands ranging from four to eight times higher than in inventoried roadless areas. The agency must reconcile this contradiction by quantifying the expected increase in human-caused ignitions resulting from new road access and weighing that figure against any claimed reduction in wildfire hazard, rather than asserting a net benefit without evidence.
- `leaders`, run 2: Commenters contend that the proposal's reliance on wildfire risk reduction to justify rescission is contradicted by the agency's own Draft EIS and peer-reviewed research, which demonstrate that road construction significantly increases human-caused ignition risk in currently protected areas. They request that the final EIS quantify the net increase in human-caused ignitions resulting from new road access and weigh this increased risk against any claimed reduction in wildfire hazard, rather than assuming roads function solely as fuel-reduction access points.
- `leaders`, run 3: The agency must explain how the proposal's reliance on wildfire and fuels management as a rationale for rescission is consistent with its own data and prior findings that road construction increases human-caused ignition density, and must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.
- `collapse`, run 1: The agency must explain how the proposal’s justification of rescission for wildfire and fuels management is reconciled with its own draft environmental impact statement findings and peer-reviewed data demonstrating that new road construction significantly increases human-caused ignition risk, and must quantify the expected increase in human-caused ignitions from new road access to weigh it against any claimed reduction in wildfire hazard.
- `collapse`, run 2: Commenters assert that the proposal's justification of rescission on wildfire and fuels management grounds is contradicted by peer-reviewed research and the agency's own draft EIS data, which demonstrate that road construction significantly increases human-caused ignition density and that inventoried roadless areas experience substantially lower fire rates than roaded lands. They request that the agency quantify the expected increase in human-caused ignitions from new road access, reconcile the proposal with its own ignition data and prior findings, and explain how it weighs this increased ignition risk against any claimed reduction in wildfire hazard.
- `collapse`, run 3: Commenters assert that the proposal's justification for rescission based on wildfire and fuels management is contradicted by peer-reviewed research and the agency's own Draft EIS, which indicate that road construction increases human-caused ignition risk and that inventoried roadless areas have significantly lower fire ignition densities than roaded lands. Commenters request that the agency quantify the expected increase in human-caused ignitions resulting from new road access, reconcile the proposal with its own ignition data, and explain how the claimed benefits of increased access outweigh the documented increase in fire risk.

#### Cluster 207, topic 2: justifies rescission, management grounds, fuels management, ignition, justifies, grounds, solution, proposal justifies

11 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0.1:

- `leaders`, runs 1, 2, 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `collapse`, runs 1, 2: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `collapse`, run 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads drive ignition rates upward, explaining how adding roads reduces fire risk when its analysis indicates the opposite.

Temperature 0.2:

- `leaders`, run 1: The agency must reconcile the use of wildfire and fuels management as a justification for rescission with its own data showing that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `leaders`, runs 2, 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data showing that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `collapse`, runs 1, 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data showing that roads drive ignition rates upward, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `collapse`, run 2: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads drive ignition rates upward, explaining how adding roads reduces fire risk when its analysis indicates the opposite.

Temperature 0.4:

- `leaders`, run 1: The agency must reconcile its reliance on wildfire and fuels management as a justification for rescission with its own data and findings, which establish that road construction increases ignition rates and that roads drive fire risk rather than mitigate it.
- `leaders`, run 2: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data, which demonstrates that roads increase ignition rates rather than reduce fire risk.
- `leaders`, run 3: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `collapse`, run 1: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that road construction increases ignition rates.
- `collapse`, run 2: The agency must reconcile its reliance on wildfire and fuels management as a justification for rescission with its own data demonstrating that roads drive ignition rates upward.
- `collapse`, run 3: The agency must reconcile its justification of the rescission based on wildfire and fuels management with its own data demonstrating that roads drive ignition rates upward, explaining how adding roads reduces fire risk when the record indicates they are the cause of ignition rather than the solution.

#### Cluster 104, topic 5: revenue, treasury, million, treasury forest, revenue treasury, million year, unlikely, timber industry

26 sentences; 26 wordings as `leaders`, 26 as `collapse`.

Temperature 0.1:

- `leaders`, run 1: Commenters contend that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, figures that represent a modest 5-10% increase in harvest volume and are contingent on unlikely full realization due to budget, operability, and market constraints.
- `leaders`, run 2: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, even under a full-harvest scenario that the agency itself deems unlikely due to budget, operability, and market constraints.
- `leaders`, run 3: Commenters contend that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, figures that represent a modest 5-10% increase in harvest volume and are contingent on full operability that the agency itself deems unlikely due to budget, market, and physical constraints.
- `collapse`, run 1: Commenters assert that the projected annual timber revenue gains of $5.2 to $11.4 million for the government and $4.6 to $10.6 million for the industry are disproportionately small relative to the estimated losses in recreation, tourism, and other ecosystem services, and that these figures are unreliable because they assume full harvest on all operable acres, a scenario the agency itself deems unlikely due to budget, operability, and market constraints.
- `collapse`, run 2: Commenters contend that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, figures that represent a modest 5-10% increase in harvest volume and are acknowledged by the agency as unlikely to be fully realized due to budget, operability, and market constraints.
- `collapse`, run 3: Commenters argue that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, figures the agency itself acknowledges are unlikely to be fully realized due to budget, operability, and market constraints.

Temperature 0.2:

- `leaders`, run 1: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, a figure they argue is further diminished by the agency's own acknowledgment that full harvest is unlikely due to budget, operability, and market constraints.
- `leaders`, run 2: Commenters contend that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, even under a full-harvest scenario that the agency itself deems unlikely due to budget, operability, and market constraints.
- `leaders`, run 3: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small and unlikely to be realized, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry based on a 5-10% increase in harvest volume that the agency itself deems unlikely due to budget, operability, and market constraints.
- `collapse`, run 1: Commenters contend that the projected annual revenue from expanded timber harvesting is disproportionately low relative to the anticipated losses, noting that the estimated $5.2 to $11.4 million in government revenue and $4.6 to $10.6 million in industry revenue are based on a 5-10% harvest increase that the agency itself deems unlikely to be fully realized due to budget, operability, and market constraints.
- `collapse`, run 2: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, figures the agency itself acknowledges are unlikely to be fully realized due to budget, operability, and market constraints.
- `collapse`, run 3: Commenters assert that the projected annual timber revenue of $5.2 to $11.4 million for the government and $4.6 to $10.6 million for the industry is disproportionately small relative to the estimated losses to recreation and tourism, and that these figures are unreliable because they assume full harvest on all operable acres, a scenario the agency itself deems unlikely due to budget, operability, and market constraints.

Temperature 0.4:

- `leaders`, run 1: The projected annual revenue gains from expanded timber harvesting are modest, capped at $5.2 to $11.4 million for the government and $4.6 to $10.6 million for the industry, and are contingent on full harvest realization that the agency itself deems unlikely due to budget, operability, and market constraints.
- `leaders`, run 2: Commenters contend that the projected annual revenue gains from expanded timber harvesting—estimated at $5.2 to $11.4 million for the Treasury and Forest Service and $4.6 to $10.6 million for the timber industry—are disproportionately small relative to the potential losses to recreation, tourism, and local economies, particularly because the Department itself acknowledges that full realization of these figures is unlikely due to budget, operability, and market constraints.
- `leaders`, run 3: Commenters contend that the projected economic benefits of rescinding the Roadless Rule are disproportionately small and unlikely to be realized, citing the agency's own estimates that expanded timber harvesting would yield only $5.2 to $11.4 million annually in government revenue and $4.6 to $10.6 million in industry revenue, even under a maximum scenario that the Department acknowledges is improbable due to budget, operability, and market constraints.
- `collapse`, run 1: Commenters assert that the proposed rule's economic analysis is flawed because it compares the modest, unlikely-to-be-realized annual revenue estimates of $5.2 to $11.4 million for the Treasury and Forest Service and $4.6 to $10.6 million for the timber industry against the significantly larger projected costs and losses to recreation, tourism, and local economies.
- `collapse`, run 2: Commenters contend that the projected economic benefits of rescinding the 2001 Roadless Rule are disproportionately small, noting that the estimated annual revenue gains of $5.2 to $11.4 million for the Treasury and Forest Service and $4.6 to $10.6 million for the timber industry are based on a 5 to 10 percent increase in sawtimber harvest that the agency itself acknowledges is unlikely to be fully realized due to budget, operability, and market constraints.
- `collapse`, run 3: Commenters assert that the projected annual timber revenue gains of $5.2 to $11.4 million for the government and $4.6 to $10.6 million for the industry are disproportionately small relative to the broader economic and environmental costs of roadless area development, particularly given that the agency itself acknowledges these figures are unlikely to be fully realized due to budget, operability, and market constraints.

<!-- end statements -->

## Similarity 20261024_171659: the Qwen statements by their embeddings

**The question.** The words move far above temperature 0.2. Does the meaning move too?

**The settings.** `make statement-similarity` on trials 20261024_163447 (temperatures 0
and 0.7) and 20261024_170736 (0.1, 0.2, 0.4): 120 statements, 91 different texts.
Embedding model `text-embedding-qwen3-embedding-8b@f16` (LM Studio, local), the text
alone. Each statement is compared with the reference statement of its cluster and
method: the statement that the most runs at temperature 0 gave. File
`trials/statements/similarity_20261024_171659.json`. Code `d2c72d5`.

**The scale.** The cosine between the reference statements of two clusters (the
`leaders` method; `collapse` is within 0.002):

| Clusters | What they are | Cosine |
|---|---|---|
| 1 and 207 | the same concern: the wildfire reason against the data on roads and ignitions | 0.874 |
| 1 and 52 | wildfire; the legal mix | 0.600 |
| 52 and 207 | the legal mix; wildfire | 0.593 |
| 52 and 104 | the legal mix; timber revenue | 0.586 |
| 1 and 104 | wildfire; timber revenue | 0.537 |
| 104 and 207 | timber revenue; wildfire | 0.510 |

Thus two different concerns are at 0.51 to 0.60. One concern in two clusters is at 0.87.

**Each temperature against the reference.** 24 statements at each temperature.

| Temperature | Cosine, median | Cosine, lowest | Words, median | Words, lowest |
|---|---|---|---|---|
| 0 | 1.000 | 0.987 | 1.00 | 0.91 |
| 0.1 | 0.989 | 0.826 | 0.88 | 0.40 |
| 0.2 | 0.978 | 0.721 | 0.82 | 0.41 |
| 0.4 | 0.917 | 0.734 | 0.50 | 0.19 |
| 0.7 | 0.892 | 0.756 | 0.49 | 0.23 |

| Cluster | 0 | 0.1 | 0.2 | 0.4 | 0.7 |
|---|---|---|---|---|---|
| 1 | 1.000 | 0.993 | 0.966 | 0.920 | 0.930 |
| 52 | 1.000 | 0.982 | 0.947 | 0.860 | 0.881 |
| 104 | 1.000 | 0.979 | 0.984 | 0.805 | 0.807 |
| 207 | 1.000 | 1.000 | 0.992 | 0.949 | 0.934 |

(Median cosine of each cluster at each temperature.)

**What the measure found.**

1. The meaning moves much less than the words. At 0.4 and 0.7 the words keep half of
   the reference (median 0.50 and 0.49), but the cosine stays at 0.92 and 0.89.
2. No statement at any temperature comes near another concern. The lowest cosine to
   its own reference is 0.72. The highest cosine between two different concerns is
   0.60.
3. The lowest cosine, 0.72, is not a different concern. It is cluster 104 (`collapse`,
   0.2, run 1): "Commenters contend that the projected annual revenue from expanded
   timber harvesting is disproportionately low relative to the anticipated losses,
   noting that the estimated $5.2 to $11.4 million in government revenue and $4.6 to
   $10.6 million in industry revenue are based on a 5-10% harvest increase that the
   agency itself deems unlikely to be fully realized due to budget, operability, and
   market constraints." It has the same figures and the same point as the reference.
   Thus a cosine of 0.72 can still be the same concern, and the margin between the same
   concern and a different concern is small: 0.72 against 0.60.
4. Up to 0.2, the median cosine stays at 0.98 or more.

**For step 15.** Temperature 0 is still the choice, because it gives the same text from
run to run. But the meaning of the statement does not depend much on the temperature:
at 0.7 each statement is still nearer its own concern than any other concern is.


## Trial 20261024_183009: every cluster of the concern map at temperature 0

**The settings.** The Qwen concern map, all 207 clusters, both methods, one run at
temperature 0: 414 calls, 804,570 tokens in, 28,766 out, 46 minutes on the local machine,
no cost. Code `b3f36f9`. Every statement is in `docs/concern-statements.md`, by topic.
The similarity step (`trials/statements/similarity_20261024_191714.json`, code
`dbdf73e` and later) embedded the 350 different statements with
`text-embedding-qwen3-embedding-8b@f16`.

**What the trial found.**

1. No statement was cut. All 414 end with a full stop, a question mark or an
   exclamation mark.
2. The two methods give the same statement for 64 of the 207 clusters. By the
   embeddings, the two statements of a cluster are at a median cosine of 0.978. 15
   clusters are below 0.85, and the lowest is 0.675.
3. Where the methods differ most, one statement is wider than the other. The five
   clusters with the lowest cosine between the methods:

| Cluster | Cosine | `leaders` | `collapse` |
|---|---|---|---|
| 55 | 0.675 | The rescission of the Roadless Rule would expose wildlife, including mule deer, elk, moose, and grizzly bears, to documented harms such as altered migration routes, increased movement speed, loss of unroaded security, and heightened human-wildlife conflict, while eliminating the protections that the agency's own records credit with the recovery of these populations. | Road construction and resource extraction alter wildlife migration routes, increase movement speed, and disrupt unroaded security, while road corridors attract animals like moose to road salt, increasing human-wildlife conflict and mortality. |
| 133 | 0.733 | Commenters contend that rescinding the 2001 Roadless Rule replaces a durable, consistent national conservation standard with fragmented, case-by-case forest-level planning, which exposes remaining intact roadless areas to inconsistent management, political pressure, and long-term ecological degradation. They argue this shift does not eliminate regulatory burden but instead invites inconsistent outcomes, increased litigation, and the potential erosion of protections over time, without demonstrating that local decision-making better protects these finite national resources. | Replacing the consistent national conservation standard of 36 CFR Part 294, Subpart B with case-by-case, forest-level planning removes a durable baseline, exposing inventoried roadless areas to inconsistent management, political pressure, and long-term ecological degradation that varies by administration and location. |
| 5 | 0.760 | The agency must complete formal Section 7 consultation with USFWS and NMFS, prepare a Biological Opinion, and conduct a supplemental environmental analysis that addresses the likely adverse effects on 327 ESA-listed species and 71 designated critical habitats, including specific impacts to habitat connectivity, fragmentation, and water quality, before finalizing the rescission. | The rescission of the Roadless Rule constitutes a federal action that is likely to adversely affect over 300 threatened and endangered species and 71 designated critical habitats by fragmenting intact ecosystems, degrading habitat connectivity, and increasing human disturbance, yet the agency has not completed the required Section 7 consultation or provided a Biological Opinion to address these impacts. |
| 119 | 0.769 | The rescission would open timberland where the agency's own data show that old and mature stands constitute the overwhelming majority of the forest, yet the document identifies no old-growth-specific protection or safeguards beyond general land management plan compliance before these stands could be harvested. | The draft EIS identifies no old-growth-specific safeguards beyond general land management plan compliance for the operable areas most likely to be affected by timber harvest, where the agency's own data show that approximately 11-16 percent is old-growth forest and 54-63 percent is mature forest. |
| 68 | 0.791 | The agency must explain how the proposal to expand road access into roadless areas reconciles with its own draft EIS findings, specifically the ignition data in Table 21 showing far higher fire density on roaded land, and the admission that the comparative wildfire-emissions analysis was not performed. | The agency must explain on the record why the rescission departs from its own prior findings and the ignition data in DEIS Table 21, which reports far higher fire density on roaded land than inside affected roadless areas, and reconcile the proposal's fire-management justification with that data. |


4. Some clusters give the same concern as another cluster. Of the 21,321 pairs of
   clusters (`leaders` statements), the median cosine is 0.532. 13 pairs are at 0.90 or
   more, 73 at 0.85 or more, and 291 at 0.80 or more. In the trials before, clusters 1
   and 207, one concern in two clusters, were at 0.874. The 13 pairs at 0.90 or more:

| Clusters | Topics | Cosine | Statement of the first | Statement of the second |
|---|---|---|---|---|
| 43 and 178 | 4, 4 | 0.955 | Commenters assert that rescinding the 2001 Roadless Rule would cause direct, irreversible harm to specific local ecosystems, water quality, and wildlife habitats, while simultaneously threatening the economic stability of communities that rely on outdoor recreation, tourism, and the preservation of roadless character. | Commenters assert that the rescission of the 2001 Roadless Rule will cause severe, irreversible harm to the ecological integrity, clean water, and public safety of roadless areas, while simultaneously devastating local economies, outdoor recreation industries, and community resources across diverse geographic regions. |
| 85 and 176 | 8, 8 | 0.950 | The agency's own preliminary biological assessment and Draft EIS determine that rescinding the 2001 Roadless Rule is likely to adversely affect 327 threatened and endangered species and 71 designated critical habitats, yet the agency has not completed the required Section 7 biological opinions or fully assessed the specific impacts on these protected populations and habitats. | The agency's own biological assessment and DEIS determine that rescinding the Roadless Rule is likely to adversely affect 327 threatened and endangered species, 71 designated critical habitats, and 3,409 sensitive species, yet the agency has not provided the required species-specific analysis of how the action impacts habitat, movement, reproduction, and long-term viability for these populations. |
| 39 and 134 | 2, 1 | 0.932 | Commenters ask the agency to explain why the proposal departs from its own prior findings on fire occurrence and fuel treatment in roadless areas, and to reconcile the rescission with the ignition data in DEIS Table 21, which reports far higher fire density on roaded land than inside the affected roadless areas. | The agency must explain why the proposal departs from its own prior findings on fire occurrence and fuel treatment in roadless areas, and reconcile the rescission with the ignition and fire density data in DEIS Table 21. |
| 13 and 205 | 4, 4 | 0.931 | The proposed full rescission of the 2001 Roadless Rule would eliminate the uniform national prohibitions on road construction, road reconstruction, and timber harvesting in inventoried roadless areas, shifting decision-making to local forest plans without a guaranteed baseline of protection, thereby exposing approximately 58.5 million acres to increased development, mining, and ecological degradation. | Rescinding the 2001 Roadless Rule would remove federal prohibitions on road construction and commercial timber harvesting from approximately 45 to 58.5 million acres of Inventoried Roadless Areas, causing irreversible degradation to wildlife habitat, clean drinking water sources, and local outdoor recreation economies, while failing to meet legal requirements and scientific standards for land management. |
| 9 and 76 | 3, 3 | 0.928 | Commenters assert that rescinding the Roadless Rule would compromise the drinking water supply for millions of Americans by removing the primary federal protection for headwaters and river systems, thereby increasing erosion, sedimentation, and contamination risks that would degrade water quality and raise treatment costs for downstream communities. | Rescinding the Roadless Rule would degrade drinking water quality and increase contamination risks for millions of Americans, particularly in drought-affected regions, by allowing road construction and development in roadless areas that serve as critical watersheds and headwaters. |
| 56 and 76 | 3, 3 | 0.928 | Rescinding the Roadless Rule will degrade drinking water quality and quantity for millions of Americans by increasing sedimentation, erosion, and contamination in headwaters and municipal source watersheds, while simultaneously increasing wildfire risk and fragmenting habitats for aquatic and terrestrial species. | Rescinding the Roadless Rule would degrade drinking water quality and increase contamination risks for millions of Americans, particularly in drought-affected regions, by allowing road construction and development in roadless areas that serve as critical watersheds and headwaters. |
| 9 and 56 | 3, 3 | 0.926 | Commenters assert that rescinding the Roadless Rule would compromise the drinking water supply for millions of Americans by removing the primary federal protection for headwaters and river systems, thereby increasing erosion, sedimentation, and contamination risks that would degrade water quality and raise treatment costs for downstream communities. | Rescinding the Roadless Rule will degrade drinking water quality and quantity for millions of Americans by increasing sedimentation, erosion, and contamination in headwaters and municipal source watersheds, while simultaneously increasing wildfire risk and fragmenting habitats for aquatic and terrestrial species. |
| 60 and 88 | 7, 7 | 0.925 | Commenters assert that the 2001 Roadless Rule already contains sufficient exceptions for wildfire mitigation, fuel reduction, and forest health management, and challenge the agency to identify specific projects that the rule has actually prevented or delayed, arguing that the rule does not block these necessary actions. | Commenters assert that the 2001 Roadless Rule already contains sufficient exceptions under 36 CFR §§ 294.12 and 294.13 to address wildfire mitigation, public safety, and forest health needs, making the rescission unnecessary and the stated intent to alleviate local decision-making disingenuous. |
| 16 and 47 | 2, 2 | 0.916 | The proposal justifies opening roadless areas to new road construction by citing wildfire and fuels management, but this rationale is contradicted by the agency's own data, including DEIS Table 21, which shows that roaded land has a significantly higher fire density and ignition risk than roadless areas. The agency must explain on the record how expanding the road network reduces fire risk rather than increasing it, and reconcile this departure from its prior findings that roads increase human-caused ignitions. | Commenters assert that the agency's own data in DEIS Table 21 demonstrates that roaded land has significantly higher fire density and ignition risk than roadless areas, creating a direct contradiction with the proposal's justification for opening roadless areas to new roads for fire and fuels management purposes. |
| 90 and 165 | 4, 4 | 0.912 | Commenters assert that scientific research demonstrates inventoried roadless areas are among the nation's most ecologically valuable, least disturbed, and cost-effective landscapes for conserving biodiversity, maintaining habitat connectivity, and providing critical ecosystem services such as water quality and carbon storage. They argue that rescinding the Roadless Rule would remove essential protections for these irreplaceable intact ecosystems, exposing them to fragmentation, invasive species, and degradation that would undermine global and national conservation goals. | Commenters assert that rescinding the Roadless Rule would degrade the highest-integrity forest ecosystems in the United States, specifically Inventoried Roadless Areas, by threatening old-growth structures, reducing carbon storage, and compromising biodiversity, clean water, and climate regulation benefits that recent studies and the Forest Landscape Integrity Index confirm are unique to these protected landscapes. |
| 198 and 205 | 4, 4 | 0.912 | Rescinding the 2001 Roadless Rule will expose remaining intact public lands to road construction, commercial logging, and other extractive activities, causing long-term ecological degradation, habitat fragmentation, and watershed damage that threatens irreplaceable ecosystems and future generations. | Rescinding the 2001 Roadless Rule would remove federal prohibitions on road construction and commercial timber harvesting from approximately 45 to 58.5 million acres of Inventoried Roadless Areas, causing irreversible degradation to wildlife habitat, clean drinking water sources, and local outdoor recreation economies, while failing to meet legal requirements and scientific standards for land management. |
| 56 and 201 | 3, 3 | 0.904 | Rescinding the Roadless Rule will degrade drinking water quality and quantity for millions of Americans by increasing sedimentation, erosion, and contamination in headwaters and municipal source watersheds, while simultaneously increasing wildfire risk and fragmenting habitats for aquatic and terrestrial species. | The rescission of the Roadless Rule would increase soil erosion, landslide risk, and sediment pollution in watersheds that supply drinking water to millions of Americans, thereby degrading water quality and compromising public health. |
| 26 and 94 | 2, 2 | 0.903 | Commenters assert that the agency's rationale for rescinding the Roadless Rule is contradicted by scientific evidence showing that the vast majority of wildfires are human-caused and that ignition rates are significantly higher near roads than in roadless areas, meaning that adding roads to previously roadless areas would increase, rather than decrease, wildfire risk. | Commenters assert that the rescission ignores scientific evidence and the agency's own records indicating that the vast majority of wildfires ignite near roads, with studies showing ignition rates are significantly higher in roaded areas than in roadless tracts. They argue that because roads facilitate human-caused ignitions, removing roadless protections will increase fire risk rather than improve fire management. |

5. 12 of the 13 pairs are in one topic; clusters 39 and 134 (topics 2 and 1) are the
   exception. Clusters 9, 56, 76 and 201 (topic 3) all give the
   concern about drinking water. Thus the topics hold most of the repeated concerns, and
   step 16 can find them inside a topic.

**For step 15.**

- The statements of all clusters can be written on the local machine in under an hour.
- Before step 16 answers the concerns, join the clusters whose statements are the same
  concern. A cosine of 0.90 between the statements finds 13 pairs; the right threshold
  needs a reading of the pairs between 0.85 and 0.90.
