# The concern statements of the concern map

This page gives one concern statement for each cluster of the concern map, in the order of
the topics. Step 15 is not built. These statements are the result of a trial of step 15
on every cluster (`make statement-trial`, `docs/clusters.md`). `docs/statement-trials.md`
gives the trials before it and the findings.

| Setting | Value |
|---|---|
| Trial | `trials/statements/20261024_183009.json` |
| Code | `b3f36f9` |
| Concern map | `opening.plain.text-embedding-qwen3-embedding-8b-f16.m95.umap5.10-10-eom.all.p1.kauto.s0` |
| Model | `qwen/qwen3.8-27b`, LM Studio on the local machine, 262,000 tokens of context |
| Temperature | 0, one run |
| Methods | `leaders` and `collapse` (`docs/clusters.md`); each cluster has a statement by each |
| Calls | 414: 804,570 tokens in, 28,766 out, 46 minutes, no cost |

Each cluster below has its topic, its eight terms, its number of sentences and the number
of wordings that each method sent. When the two methods gave the same statement, the
statement is given once with both.

<!-- statements 20261024_183009 -->

Case `opening.plain.text-embedding-qwen3-embedding-8b-f16.m95.umap5.10-10-eom.all.p1.kauto.s0`. Model `qwen/qwen3.8-27b`. File `trials/statements/20261024_183009.json`.

#### Cluster 10, topic 1: tribal, consulted, tribal governments, governments, consultation, sovereignty, sacred, sacred sites

115 sentences; 110 wordings as `leaders`, 110 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Department must complete meaningful government-to-government consultation with affected Tribal Nations, consistent with Executive Order 13175 and the federal trust responsibility, before finalizing the rescission, and must fully address the documented majority Tribal opposition regarding threats to treaty rights, sovereignty, sacred sites, subsistence resources, and the ecological health of ancestral homelands.
- `collapse`, run 1: The Department must complete meaningful government-to-government consultation with affected Tribal Nations, consistent with Executive Order 13175 and the federal trust responsibility, before finalizing the rescission, and must fully address the documented majority Tribal opposition to the rule, including specific threats to treaty rights, sacred sites, subsistence resources, water quality, and the ecological health of ancestral homelands.

#### Cluster 12, topic 1: rescission, agency, wildfire, wildfire rationale, rationale, offered rescission, agency record, agency data

210 sentences; 97 wordings as `leaders`, 100 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own data and findings on wildfire risk contradict the fire-safety rationale it offers to justify the nationwide rescission of the 2001 Roadless Rule.
- `collapse`, run 1: The agency's own data and findings contradict the wildfire rationale offered to justify the nationwide rescission of the 2001 Roadless Rule, rendering that justification unsupported by the administrative record.

#### Cluster 18, topic 1: cfr subpart, subpart, cfr, retain cfr, retain, withdraw, alternative, cfr rin

105 sentences; 85 wordings as `leaders`, 85 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters urge the Forest Service to withdraw the proposed rescission of 36 CFR part 294, subpart B, and select the No Action alternative to retain the rule in its entirety.
- `collapse`, run 1: Commenters request that the Forest Service withdraw the proposed rescission of 36 CFR part 294, subpart B, and select the No Action alternative to retain the rule in its entirety.

#### Cluster 20, topic 1: agency, proposal, agency record, proposal agency, record, rescission, record makes, strongest

91 sentences; 80 wordings as `leaders`, 80 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain on the record how the rescission is consistent with its own environmental review, which contains findings on fire, wildlife, and fragmentation that contradict the proposal's rationale and for which the draft environmental impact statement fails to provide adequate reconciliation or mitigation.
- `collapse`, run 1: The agency must explain on the record how the proposed rescission reconciles with its own environmental review, which contains findings on fire, wildlife, and fragmentation that contradict the proposal's rationale and demonstrate that the rule remains necessary.

#### Cluster 21, topic 1: agency explain, explain, bird, ask agency, ask, documented, agency, bird abundance

80 sentences; 79 wordings as `leaders`, 79 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain on the record how the rescission is consistent with its own documented findings on the adverse effects of roads to wildlife populations, including big game, birds, and bears, and what specific mitigation measures it proposes to prevent the resulting harm.
- `collapse`, run 1: The agency must explain on the record how the rescission is consistent with its own documented findings on road-induced harms to wildlife, including reduced bird abundance, species avoidance, and mortality of big game and other sensitive species, and what specific mitigation measures, if any, would prevent these documented impacts.

#### Cluster 31, topic 1: departs, proposal departs, ignition data, reconcile rescission, explain, agency explain, reconcile, findings reconcile

103 sentences; 53 wordings as `leaders`, 53 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain on the record why the proposal departs from its own prior findings and reconcile the rescission with the ignition data in its own DEIS, including Table 21.
- `collapse`, run 1: The agency must explain on the record why the proposal departs from its own prior findings and reconcile the rescission with the ignition data in its own DEIS, including Table 21.

#### Cluster 34, topic 1: agency record, agency, proposal, proposal agency, record, agency numbers, agency biological, numbers

54 sentences; 49 wordings as `leaders`, 49 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own record, data, and biological assessments contradict the stated purpose and need of the proposal, exposing internal inconsistencies and unsupported justifications that fail to support the action.
- `collapse`, run 1: The agency's own record, data, and biological assessments contradict the stated purpose and need of the proposal, undermining its rationale and exposing internal inconsistencies that fail to justify the action.

#### Cluster 35, topic 1: wildfire, wildfire risk, rule, rescinding, claims, wildfire management, proposal claims, risk

49 sentences; 48 wordings as `leaders`, 48 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must demonstrate that rescinding the 2001 Roadless Rule is necessary to improve wildfire outcomes, as commenters assert that the proposal’s wildfire rationale is contradicted by the agency’s own environmental analysis, empirical fire ecology data, and peer-reviewed scientific literature.
- `collapse`, run 1: The agency must demonstrate that rescinding the 2001 Roadless Rule is necessary to improve wildfire management, as commenters assert that the proposal’s wildfire rationale is contradicted by the agency’s own environmental analysis, empirical fire ecology data, and peer-reviewed scientific literature.

#### Cluster 36, topic 1: agency record, rescission, agency, record, support rescission, does support, record says, case rescission

51 sentences; 47 wordings as `leaders`, 47 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own record, data, and analysis do not support the rescission of the 2001 Roadless Rule, and the agency has failed to reconcile its proposal with its own findings.
- `collapse`, run 1: The agency's own record, including its data, analysis, and biological findings, does not support the rescission of the 2001 Roadless Rule and instead undermines the stated justifications for the proposal.

#### Cluster 38, topic 1: figure, range alternatives, draft, deis, eis, comments, source, page

50 sentences; 47 wordings as `leaders`, 47 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS relies on a comment record that is inaccessible to the public, contains uncited or unverifiable data, and uses a superseded definition of 'substantive' comments to shape the range of alternatives, resulting in a flawed analysis that fails to meet NEPA and APA requirements.
- `collapse`, run 1: The Draft EIS relies on a comment record that is inaccessible to the public, contains uncited or unverifiable data, and was screened using a superseded definition of 'substantive' comments, resulting in a range of alternatives and impact analyses that are not supported by the administrative record or substantial evidence.

#### Cluster 40, topic 1: fuels management, wildfire fuels, fuels, wildfire, management grounds, rescission, justification, management

83 sentences; 46 wordings as `leaders`, 46 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own prior findings and ignition data, which contradict the claim that rescission reduces fire risk, and explain why existing exceptions for fire, health, and safety are inadequate.
- `collapse`, run 1: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own prior findings and ignition data, which contradict the claim that rescission reduces fire risk, and explain why existing exceptions for fire, health, and safety are inadequate.

#### Cluster 41, topic 1: economic case, case rescission, economic, agency numbers, rescission, case, numbers, agency

100 sentences; 45 wordings as `leaders`, 46 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own economic analysis, cost-benefit figures, and data fail to establish that rescission produces a net benefit, instead demonstrating that the action is a net-negative financial liability that trades irreplaceable resources for unconfirmed or marginal gains.
- `collapse`, run 1: Commenters assert that the agency's own economic analysis, cost-benefit data, and fiscal records fail to establish a net benefit for rescinding the 2001 Roadless Rule, and instead demonstrate that the action is a net-negative financial liability that trades irreplaceable resources for unconfirmed or marginal economic gains.

#### Cluster 44, topic 1: cfr, substantive, correction, final eis, final, cite, corrections, compliance

46 sentences; 44 wordings as `leaders`, 44 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Final EIS and the final rule fail to comply with 42 U.S.C. 4336a and 7 CFR 1b.7 by exceeding the 150-page limit without a documented extraordinary-complexity determination, and they rely on unsupported quantitative figures and causal assertions that contradict the agency's own record, thereby failing to establish cause-and-effect relationships or provide reasoned explanations as required by 7 CFR 1b.11(a)(23) and 5 U.S.C. 706(2)(A). The agency must make factual corrections, supplement the analysis to distinguish confounding causes, and cite where each correction is accounted for in the Final EIS or supporting record, as these issues are substantive under 7 CFR 1b.11(a)(53) because they bear on compliance with applicable law and the consideration of reasonably foreseeable impacts.
- `collapse`, run 1: The Final EIS and the final rule fail to comply with 42 U.S.C. 4336a and 7 CFR 1b.7 by exceeding the 150-page limit without a documented extraordinary-complexity determination, and they rely on unsupported quantitative figures and causal assertions that contradict the agency's own record, thereby failing to establish cause-and-effect relationships under 7 CFR 1b.11(a)(23) and to provide reasoned explanations under 5 U.S.C. 706(2)(A). The agency must make factual corrections and supplement its analysis to reconcile these discrepancies, apply the amended definition of substantive information in 7 CFR 1b.11(a)(53) to ensure compliance with applicable laws, and cite where each correction is accounted for in the Final EIS or supporting record as required by 7 CFR 1b.7(f)(3).

#### Cluster 46, topic 1: nepa, nepa requires, requires, cir, programmatic, reasonable, national environmental, policy act

43 sentences; 43 wordings as `leaders`, 43 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS fails to comply with NEPA by relying on a programmatic tiering approach that improperly defers required analysis of cumulative, irreversible, and site-specific impacts to future project-level reviews, and by adopting a purpose and need statement that forecloses a reasonable range of alternatives, including retaining or amending the Roadless Rule, thereby preventing the rigorous comparative analysis and forthright disclosure of trade-offs that the statute mandates.
- `collapse`, run 1: The Draft EIS fails to comply with NEPA by relying on a programmatic tiering approach that improperly defers analysis of significant, zone-wide, and cumulative impacts to future project-level reviews, and by using a narrowly drawn purpose and need statement that forecloses a reasonable range of alternatives, including retaining the Roadless Rule or adopting geographically tailored exceptions, thereby preventing the required comparative analysis of environmental effects, trade-offs, and irreversible resource commitments.

#### Cluster 49, topic 1: agency data, data, proposal, agency, argues proposal, stop proposal, argues, data agency

65 sentences; 41 wordings as `leaders`, 42 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own fire data and analysis contradict the proposal's central safety and risk rationale, yet the document fails to reconcile this internal inconsistency or adequately account for the conflicting evidence.
- `collapse`, run 1: The agency's own fire data and analysis contradict the proposal's central safety and risk rationale, yet the document fails to reconcile this internal inconsistency or adequately account for the conflicting evidence.

#### Cluster 52, topic 1: nepa, cir, usda cir, clause, california rel, rel, rel lockyer, circuit

45 sentences; 41 wordings as `leaders`, 41 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth Circuit in Wyoming v. USDA and the Ninth Circuit in California ex rel. Lockyer v. USDA have already rejected the argument that decentralized, forest-by-forest planning is a legally sufficient substitute for a uniform national standard.
- `collapse`, run 1: The rescission of the 2001 Roadless Area Conservation Rule violates the National Environmental Policy Act, the Administrative Procedure Act, and the National Forest Management Act because the agency failed to conduct a programmatic 'hard look' at the cumulative environmental, cultural, and climate impacts of removing national protections, and because the Tenth and Ninth Circuits have already rejected the argument that decentralized, forest-by-forest planning is a legally sufficient substitute for a uniform national standard.

#### Cluster 71, topic 1: pew, survey, charitable, pew charitable, polling, support roadless, charitable trusts, trusts

38 sentences; 34 wordings as `leaders`, 34 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the Roadless Rule retains overwhelming, bipartisan public support, citing recent polls showing 75-76% approval and 99% opposition to rescission among commenters, and argue that rescinding the rule would ignore the will of the American people.
- `collapse`, run 1: Commenters assert that the Roadless Rule retains overwhelming, bipartisan public support, citing recent national polls showing approximately 75-76% approval and previous comment periods where 99% of respondents opposed rescission. They argue that rescinding the rule would ignore the clear will of the American people, including majorities across political parties, regions, and rural demographics.

#### Cluster 73, topic 1: comment, extend, tribal, comment period, extend comment, period, consultation, hearings

33 sentences; 33 wordings as `leaders`, 33 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must conduct meaningful government-to-government consultation, complete ANILCA Section 810 evaluations, and fully analyze Tribal co-stewardship, Traditional Ecological Knowledge, and subsistence rights before issuing a final rule. Additionally, the agency must extend the comment period to at least 60-120 days, hold public hearings in affected states, and prepare a complete environmental impact statement that addresses cumulative impacts, specific regional concerns, and all requested alternatives, including the No Action alternative.
- `collapse`, run 1: The agency must conduct meaningful government-to-government consultation, complete ANILCA Section 810 evaluations, and fully analyze Tribal co-stewardship, Traditional Ecological Knowledge, and subsistence rights before issuing a final rule. Additionally, the agency must extend the comment period to at least 60-120 days, hold public hearings in affected states, and prepare a complete environmental impact statement that addresses cumulative impacts, specific regional concerns, and all requested alternatives, including the No Action alternative.

#### Cluster 77, topic 1: departs, proposal departs, explain, reconcile, ignition, reconcile rescission, departs prior, prior findings

54 sentences; 32 wordings as `leaders`, 32 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain on the record why the rescission departs from its own prior findings on fire occurrence and reconcile the wildfire rationale with the ignition density data reported in its draft environmental impact statement, including DEIS Table 21.
- `collapse`, run 1: The agency must explain on the record why the rescission departs from its own prior findings on fire occurrence and reconcile the wildfire rationale with the ignition density data reported in its draft environmental impact statement, including DEIS Table 21.

#### Cluster 81, topic 1: district court, injunction, permanent injunction, court, district, exercising jurisdiction, exercising, reverse district

264 sentences; 30 wordings as `leaders`, 31 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the 2001 Roadless Rule exceeded the agency's statutory authority, but the Tenth Circuit has already reviewed this question and held that the rule was within the authority Congress granted, reversing the district court's permanent injunction.
- `collapse`, run 1: Commenters assert that the Tenth Circuit's appellate decision, which reversed the district court's permanent injunction against the 2001 Roadless Rule, constitutes a final judicial determination that the rule was within the agency's statutory authority, and they require the agency to explain how it can rescind a rule that a federal court has already held lawful.

#### Cluster 82, topic 1: comments, center western, western priorities, priorities, public, public comments, comments opposed, opposed

32 sentences; 30 wordings as `leaders`, 30 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission of the 2001 Roadless Rule ignores the overwhelming public opposition, with analyses indicating that over 99% of the hundreds of thousands of comments received in response to the proposal opposed repeal, rendering the agency's decision to proceed arbitrary and capricious.
- `collapse`, run 1: The rescission of the 2001 Roadless Rule ignores the overwhelming public opposition, with analyses indicating that over 99% of the hundreds of thousands of comments received in response to the proposal opposed repeal, rendering the agency's decision to proceed arbitrary and capricious.

#### Cluster 91, topic 1: state farm, farm, fox television, television, fox, motor vehicle, motor, cir

28 sentences; 28 wordings as `leaders`, 28 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission is arbitrary and capricious because the agency failed to articulate a rational connection between the facts found and the choice made, ignored important aspects of the problem, and did not provide a reasoned explanation for reversing a long-standing policy or addressing serious reliance interests.
- `collapse`, run 1: The rescission is arbitrary and capricious because the agency failed to articulate a rational connection between the facts found and the choice made, ignored important aspects of the problem, and did not provide a reasoned explanation for reversing a long-standing policy or addressing serious reliance interests.

#### Cluster 99, topic 1: wildfire, wildfire justification, proposal, justification proposal, wildfire rationale, agency, agency findings, justification

56 sentences; 27 wordings as `leaders`, 28 as `collapse`.

Temperature 0:

- `leaders`, run 1: The wildfire justification for the proposal is contradicted by the agency's own data, findings, and record.
- `collapse`, run 1: The wildfire justification for the proposal is contradicted by the agency's own fire data and prior findings.

#### Cluster 101, topic 1: esa, esa section, consultation, species, section, endangered, section consultation, endangered species

27 sentences; 26 wordings as `leaders`, 26 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency has failed to complete the mandatory formal consultation and conference required by ESA Section 7 with the U.S. Fish and Wildlife Service and NOAA Fisheries for the 327 listed or proposed species and 71 designated critical habitats identified as likely to be adversely affected by the rescission, rendering the action unlawful and arbitrary.
- `collapse`, run 1: The agency has failed to complete the mandatory formal consultation and conference required by ESA Section 7 with the U.S. Fish and Wildlife Service and NOAA Fisheries for the 327 listed or proposed species and 71 designated critical habitats identified as likely to be adversely affected by the rescission, rendering the action unlawful and arbitrary.

#### Cluster 106, topic 1: anilca, anilca section, subsistence, tribal, section subsistence, subsistence analysis, complete, consultation

26 sentences; 25 wordings as `leaders`, 25 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must complete meaningful Tribal consultation and a full ANILCA Section 810 subsistence analysis, including accessible public hearings and site-specific effects assessments for the Tongass, before issuing a final decision or Record of Decision. Additionally, the agency must rigorously evaluate and weigh Tribal-proposed alternatives, such as co-stewardship and traditional homelands conservation, rather than proceeding with a full rescission or exemptions without these required analyses.
- `collapse`, run 1: The agency must complete meaningful Tribal consultation and a full ANILCA Section 810 subsistence analysis, including accessible public hearings and site-specific effects assessments for the Tongass, before issuing a final decision or Record of Decision. The final rule must also adequately consider Tribal-proposed alternatives, such as co-stewardship and traditional homelands conservation, and ensure that any exemptions or changes to roadless protections are supported by rigorous, area-specific environmental analysis.

#### Cluster 111, topic 1: cir, blue mountains, kern, kake, usda cir, bureau land, bureau, village

24 sentences; 24 wordings as `leaders`, 24 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the rescission is arbitrary and capricious because the agency failed to adequately explain its departure from the material findings and scientific conclusions of the 2001 Roadless Rule, ignored contrary evidence in the record, and relied on unsupported or unexamined data, thereby violating the Administrative Procedure Act, NEPA, and the Endangered Species Act.
- `collapse`, run 1: Commenters assert that the rescission is arbitrary and capricious because the agency failed to adequately explain its departure from the material findings and scientific conclusions of the 2001 Roadless Rule, ignored contrary evidence in the record, and relied on unsupported or unexamined data, thereby violating the Administrative Procedure Act, NEPA, and the Endangered Species Act.

#### Cluster 118, topic 1: proposal claims, permitting, claims, burdens, permitting administrative, administrative burdens, administrative, accommodates

24 sentences; 22 wordings as `leaders`, 22 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency has not demonstrated that the 2001 Roadless Rule actually blocks the activities or creates the permitting and administrative burdens cited as justifications for rescission, as the rule as written already contains the flexibility and exceptions to accommodate those uses.
- `collapse`, run 1: The proposal justifies rescission by claiming the 2001 Roadless Rule imposes unworkable permitting and administrative burdens, but commenters argue the rule as written already contains the necessary flexibility and exceptions to accommodate the specific activities and uses the agency claims are being blocked.

#### Cluster 126, topic 1: comment, comment period, period, day comment, days, day, public hearings, hearings

19 sentences; 19 wordings as `leaders`, 19 as `collapse`.

Temperature 0:

- `leaders`, run 1: The 30-day public comment period and the absence of public hearings are procedurally inadequate for a rule of this magnitude, which affects approximately 45 to 58 million acres across multiple states and involves a complex Draft EIS, cost-benefit analysis, and Tribal impact statement. Commenters argue that this timeframe is significantly shorter than the periods provided during the 2001 rulemaking and the 2005 rescission attempt, fails to meet the minimum standards of the Administrative Procedure Act and Executive Order 12866, and does not allow for meaningful public review or technical input commensurate with the scale of the action.
- `collapse`, run 1: The 30-day public comment period and the absence of public hearings are procedurally inadequate for a rule of this magnitude, which affects approximately 45 to 58 million acres across multiple states and involves a complex Draft EIS, cost-benefit analysis, and Tribal impact statement. Commenters argue that this timeframe is significantly shorter than the periods provided during the 2001 rulemaking and the 2005 rescission attempt, fails to meet the minimum standards of the Administrative Procedure Act and Executive Order 12866, and does not allow for meaningful public review or technical input commensurate with the scale of the action.

#### Cluster 134, topic 1: reconcile, proposal departs, departs, occurrence, findings occurrence, occurrence roadless, explain, reconcile rescission

28 sentences; 18 wordings as `leaders`, 18 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain why the proposal departs from its own prior findings on fire occurrence and fuel treatment in roadless areas, and reconcile the rescission with the ignition and fire density data in DEIS Table 21.
- `collapse`, run 1: The agency must explain on the record why the proposal departs from its own prior findings and DEIS Table 21 data showing higher fire density on roaded land, and reconcile the rescission rationale with that ignition data.

#### Cluster 136, topic 1: reliance, reliance interests, interests current, analysis weighs, rule affected, solicits reliance, current rule, weighs

64 sentences; 18 wordings as `leaders`, 18 as `collapse`.

Temperature 0:

- `leaders`, run 1: The proposal solicits public comment on reliance interests in the current rule, yet the Cost Benefit Analysis fails to weigh or account for those interests.
- `collapse`, run 1: The proposal solicits comment on reliance interests in the current rule, yet the Cost Benefit Analysis fails to weigh or account for those interests.

#### Cluster 144, topic 1: granted, create facto, facto wilderness, did create, facto, congress granted, holding rule, authority congress

47 sentences; 17 wordings as `leaders`, 15 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must address the Tenth Circuit's holding that the 2001 rule was within the authority Congress granted under the Organic Act and the Multiple-Use Sustained-Yield Act and did not create de facto wilderness, and explain on the record the legal basis for any contrary position it now advances.
- `collapse`, run 1: The agency must address the Tenth Circuit's holding that the 2001 rule was within the authority Congress granted under the Organic Act and the Multiple-Use Sustained-Yield Act and did not create de facto wilderness, and explain on the record the legal basis for any contrary position it now advances.

#### Cluster 147, topic 1: biological assessment, species, biological, lists, assessment, species lists, usfws, count

17 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS and Biological Assessments fail to provide a complete, reconciled, and transparent accounting of the number of listed species and critical habitats, including specific omissions regarding coho salmon, DPS counting methodologies, and invasive plant exposure, rendering the 'likely to adversely affect' finding arbitrary and capricious.
- `collapse`, run 1: The Draft EIS and Biological Assessments fail to provide a complete, reconciled, and transparent accounting of the number of ESA-listed species and designated critical habitats, including specific omissions regarding coho salmon, DPS counting methodologies, and invasive plant exposure, rendering the 'likely to adversely affect' finding arbitrary and capricious.

#### Cluster 149, topic 1: certification, regulatory flexibility, regulatory, flexibility certification, flexibility, significant impact, impact small, flexibility analysis

19 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: The 5 U.S.C. 605(b) certification that the proposal has no significant impact on small entities is irreconcilable with the agency's own economic, fiscal, and environmental analyses, which quantify substantial losses concentrated in small-entity sectors, rendering the certification unsupported and requiring the preparation of an Initial Regulatory Flexibility Analysis under 5 U.S.C. 603.
- `collapse`, run 1: The agency's certification under 5 U.S.C. 605(b) that the rescission has no significant impact on small entities is irreconcilable with its own economic, fiscal, and environmental analyses, which quantify concentrated losses and severe fiscal impacts, thereby requiring the withdrawal of the certification and the preparation of an Initial Regulatory Flexibility Analysis under 5 U.S.C. 603.

#### Cluster 150, topic 1: agency numbers, numbers, proposal, economic, agency, economic case, economics, numbers proposal

20 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the agency's own economic analysis and fiscal findings are internally incoherent and fail to support the proposal's rationale, thereby undermining the economic justification for the rule.
- `collapse`, run 1: The agency's own economic analysis and fiscal findings are internally incoherent and fail to support the proposal's rationale, rendering the economic justification for the rulemaking invalid.

#### Cluster 152, topic 1: wildfire, rule necessary, wildfire risk, necessary wildfire, necessary, risk, contradicted agency, justification

16 sentences; 16 wordings as `leaders`, 16 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency’s justification that rescission is necessary for wildfire risk reduction and management is contradicted by its own data and analysis, which fails to quantify or demonstrate that repealing the rule would materially reduce wildfire risk.
- `collapse`, run 1: The agency’s justification that rescission is necessary for wildfire risk reduction and management is contradicted by its own data and analysis, which fails to quantify or demonstrate that repealing the rule would materially reduce wildfire risk.

#### Cluster 155, topic 1: agency draft, draft environmental, agency, impact statement, environmental impact, statement, draft, appears agency

16 sentences; 16 wordings as `leaders`, 16 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own Draft Environmental Impact Statement contains findings and data acknowledging significant negative environmental impacts, yet the agency has failed to treat these admissions as decisive in its analysis or to explain why it now considers them incorrect.
- `collapse`, run 1: The agency's own Draft Environmental Impact Statement contains findings and data acknowledging significant negative environmental impacts, yet the agency has failed to treat these admissions as decisive in its analysis or to explain why it now considers them incorrect.

#### Cluster 159, topic 1: arbitrary capricious, capricious, arbitrary, apa, capricious apa, counter, explanation, procedure

15 sentences; 15 wordings as `leaders`, 15 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission is arbitrary and capricious under 5 U.S.C. § 706(2)(A) because the agency failed to properly examine relevant data, relied on factors Congress did not intend, and offered an explanation that runs counter to the evidence in the record, including its own science and established conservation policy.
- `collapse`, run 1: The rescission is arbitrary and capricious under 5 U.S.C. § 706(2)(A) because the agency failed to properly examine relevant data, relied on factors Congress did not intend, and offered an explanation that runs counter to the evidence in the record, including its own science and critical infrastructure considerations.

#### Cluster 163, topic 1: million comments, public meetings, meetings, comments, public, received million, million, received

14 sentences; 14 wordings as `leaders`, 14 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission of the 2001 Roadless Rule is procedurally deficient because it lacks the extensive public participation—specifically the hundreds of public meetings and millions of comments—that established the original rule, and the agency has failed to quantify the administrative burdens cited as justification for eliminating these protections.
- `collapse`, run 1: The rescission of the 2001 Roadless Rule is procedurally deficient because it lacks the extensive public participation—specifically the hundreds of public meetings and millions of comments—that established the original rule, and the agency has failed to quantify the administrative burdens cited as justification for eliminating these protections.

#### Cluster 166, topic 1: opposed, percent generally, comment, letters received, letters, comments, approximately percent, received

14 sentences; 14 wordings as `leaders`, 14 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency failed to provide reasoned consideration to the overwhelming public opposition to the rescission, as evidenced by the fact that approximately 99% of the over 625,000 individual submissions received during the Notice of Intent comment period opposed the action, a scale of public investment that the agency is required to genuinely address under APA rulemaking standards.
- `collapse`, run 1: The agency failed to provide reasoned consideration to the overwhelming public opposition to the rescission, as evidenced by the fact that approximately 99% of the over 625,000 individual submissions received during the Notice of Intent comment period opposed the action, a scale of public investment that must be genuinely addressed under APA rulemaking standards.

#### Cluster 168, topic 1: forest service, service, case rule, service numbers, service analysis, forest, rescission, numbers make

13 sentences; 13 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Forest Service’s own analysis and findings in the Draft Environmental Impact Statement undermine the rationale for rescission, failing to provide a rational, evidence-based connection between the proposed rule change and the agency’s fiscal constraints, diminished capacity, or localized economic impacts.
- `collapse`, run 1: The Forest Service’s own analysis and findings in the Draft Environmental Impact Statement undermine the rationale for rescission, failing to provide a rational, evidence-based connection between the proposed rule change and the agency’s fiscal constraints, diminished capacity, or localized economic impacts.

#### Cluster 169, topic 1: rule puts, risk agency, puts, puts risk, rescinding rule, rescinding, analysis makes, agency record

13 sentences; 13 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the 2001 Roadless Rule would place the protected lands and their ecological values at risk, and the agency’s own record and analysis demonstrate that the proposed action is unsupported and would cause significant harm.
- `collapse`, run 1: Rescinding the 2001 Roadless Rule would place the protected lands and their ecological values at significant risk, and the agency’s own record and analysis fail to justify the decision, instead demonstrating that the proposed action is unsound and unsupported by the evidence.

#### Cluster 184, topic 1: trade, rule trades, trades, returns agency, economic returns, confirm, rescinding rule, rescinding

11 sentences; 11 wordings as `leaders`, 11 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the 2001 Roadless Rule would trade permanent, documented public and ecological benefits for short-term economic gains that the agency’s own analysis characterizes as modest, uncertain, or unconfirmed, a tradeoff that the agency’s data does not justify.
- `collapse`, run 1: Rescinding the 2001 Roadless Rule would trade documented, permanent, and nationally significant ecological, carbon, Tribal, and recreational values for short-term economic gains that the agency’s own analysis characterizes as modest, uncertain, and unconfirmed, a tradeoff that the agency’s data does not justify.

#### Cluster 190, topic 1: agency record, oppose, reason oppose, gives reason, protecting agency, oppose rescission, agency, worth protecting

11 sentences; 11 wordings as `leaders`, 11 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Forest Service proposes to rescind the 2001 Roadless Rule without adequately addressing or reconciling the agency's own record, which contains findings and data that undermine the rationale for removal and support the continued protection of these lands.
- `collapse`, run 1: Commenters oppose the rescission of the 2001 Roadless Rule because the agency’s own record and data do not support the proposed action, undermining the rationale for removing protections from ecologically significant, unroaded lands that provide irreplaceable natural, aesthetic, and recreational values.

#### Cluster 191, topic 1: modest localized, management opportunities, modest, localized, localized proposal, opportunities created, created rescission, opportunities modest

12 sentences; 11 wordings as `leaders`, 11 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission would create only modest and localized management opportunities, with near-term effects limited by existing plan direction, budgets, and operability.
- `collapse`, run 1: Commenters assert that the Department’s own analysis characterizes the additional management opportunities created by rescission as modest, localized, and limited by existing plan direction, budgets, and operability.

#### Cluster 194, topic 1: rejected, agency built, wui-targeted, nationwide rescission, alternative, address risk, nationwide, built

12 sentences; 11 wordings as `leaders`, 11 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain why it rejected its own WUI-targeted alternative, which would have addressed fire risk without dismantling nationwide protections, in favor of a wholesale rescission, particularly given that its own analysis characterizes the resulting fire benefits as modest and geographically limited.
- `collapse`, run 1: The agency must explain why it rejected its own WUI-targeted alternative, which would have addressed fire risk without dismantling nationwide protections, in favor of a wholesale rescission that trades durable protections for benefits its own analysis characterizes as modest and geographically limited.

#### Cluster 202, topic 1: deis, deis acknowledges, acknowledges science, identifies fragmentation, away deis, address climate, agency declines, does include

10 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS fails to apply its own acknowledged scientific evidence, including data on wildlife fragmentation and climate change, to draw required conclusions or perform stated analyses, resulting in an incomplete environmental assessment.
- `collapse`, run 1: The DEIS fails to apply its own acknowledged scientific evidence, including data on wildlife fragmentation and climate change, to draw required conclusions or perform stated analyses, resulting in an incomplete environmental assessment.

#### Cluster 206, topic 1: scope analysis, irreversible irretrievable, irretrievable, revise, commitments, honestly, irretrievable commitments, scope

12 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Forest Service must revise the Scope of the Analysis to honestly disclose the irreversible and irretrievable commitments its own technical chapters describe, or explain on the record how those findings are consistent with the section's disclaimer, as presenting inconsistent or unexplained figures on the resource at issue is prohibited.
- `collapse`, run 1: The Forest Service must revise the Scope of the Analysis to honestly disclose the irreversible and irretrievable commitments its own technical chapters describe, or explain on the record how those findings are consistent with the section's disclaimer, as presenting inconsistent or unexplained figures on the resource at issue is prohibited.

#### Cluster 1, topic 2: wildfire, human-caused, roads, wildfires, fires, ignitions, ignition, areas

541 sentences; 386 wordings as `leaders`, 389 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for rescission is consistent with its own draft environmental impact statement and peer-reviewed data demonstrating that road construction significantly increases human-caused wildfire ignition risk, and must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.
- `collapse`, run 1: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for rescission reconciles with its own draft environmental impact statement and peer-reviewed data demonstrating that road construction significantly increases human-caused ignition risk, and it must quantify the expected increase in human-caused ignitions from new road access to weigh against any claimed reduction in wildfire hazard.

#### Cluster 11, topic 2: hectares, aplet, density, fires, meters, fires hectares, ecology, ignition density

129 sentences; 99 wordings as `leaders`, 102 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the agency's rationale for rescinding the Roadless Rule is contradicted by peer-reviewed research, specifically a 2026 study in Fire Ecology analyzing three decades of national forest data, which found that wildfire ignition density is approximately four times higher within 50 meters of roads than in Inventoried Roadless Areas and designated wilderness, indicating that road construction increases wildfire risk rather than mitigating it.
- `collapse`, run 1: Commenters assert that the agency's rationale for rescinding the Roadless Rule is contradicted by peer-reviewed scientific evidence, specifically a 2026 study in Fire Ecology analyzing three decades of national forest data, which found that wildfire ignition density is approximately four times higher within 50 meters of roads than in Inventoried Roadless Areas, indicating that road construction increases rather than decreases wildfire risk.

#### Cluster 16, topic 2: ignition, risk, ignition risk, agency, agency prior, opening, proposal, prior findings

98 sentences; 88 wordings as `leaders`, 88 as `collapse`.

Temperature 0:

- `leaders`, run 1: The proposal justifies opening roadless areas to new road construction by citing wildfire and fuels management, but this rationale is contradicted by the agency's own data, including DEIS Table 21, which shows that roaded land has a significantly higher fire density and ignition risk than roadless areas. The agency must explain on the record how expanding the road network reduces fire risk rather than increasing it, and reconcile this departure from its prior findings that roads increase human-caused ignitions.
- `collapse`, run 1: The agency must explain how the proposal's reliance on wildfire and fuels management as a justification for opening roadless areas to new road construction reconciles with its own prior findings and DEIS Table 21 data, which demonstrate that road construction correlates with significantly higher fire density and human-caused ignition risk.

#### Cluster 22, topic 2: risk, increase, wildfire, roadless rule, wildfire risk, rule, wildfires, roadless

77 sentences; 77 wordings as `leaders`, 77 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that rescinding the 2001 Roadless Rule will increase, rather than decrease, wildfire risk and severity, citing the Forest Service’s own Draft Environmental Impact Statement, peer-reviewed research, and historical data indicating that new road construction and associated timber harvesting in Inventoried Roadless Areas lead to higher rates of human-caused ignitions, increased fire frequency, and greater fire intensity.
- `collapse`, run 1: Commenters assert that rescinding the 2001 Roadless Rule will increase, rather than decrease, wildfire risk and severity, citing the Forest Service’s own Draft Environmental Impact Statement, peer-reviewed research, and historical data indicating that new road construction and timber harvesting in Inventoried Roadless Areas lead to higher ignition rates, increased fire intensity, and greater harm to communities.

#### Cluster 26, topic 2: wildfires, human-caused, fires, roads, start, caused, ignitions, balch

72 sentences; 67 wordings as `leaders`, 67 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the agency's rationale for rescinding the Roadless Rule is contradicted by scientific evidence showing that the vast majority of wildfires are human-caused and that ignition rates are significantly higher near roads than in roadless areas, meaning that adding roads to previously roadless areas would increase, rather than decrease, wildfire risk.
- `collapse`, run 1: Commenters assert that the agency's rationale for rescinding the Roadless Rule is contradicted by scientific evidence demonstrating that roads are a primary vector for human-caused wildfires, which account for the vast majority of U.S. ignitions and occur at significantly higher rates near road corridors than in roadless areas.

#### Cluster 28, topic 2: healey, similar rates, burned similar, sean, forest, monitoring, study, forests roads

61 sentences; 60 wordings as `leaders`, 60 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the Forest Service’s own 2020 research (Healey et al.) demonstrates that roadless areas have not experienced higher fire rates, have received equal or greater fuel-management activity per unit area, and that roads are associated with invasive species, thereby contradicting the agency's justification that rescinding the rule is necessary for fire prevention or forest health.
- `collapse`, run 1: Commenters assert that the Forest Service’s own 2020 peer-reviewed study (Healey, *Environmental Research Letters*) and other agency analyses demonstrate that roadless areas have not experienced higher fire rates, that fuel-management activities occur at similar or higher per-unit-area rates in roadless lands, and that roads are associated with invasive species, thereby contradicting the agency’s justification that rescinding the Roadless Rule is necessary to improve forest health or wildfire management.

#### Cluster 39, topic 2: density roaded, ignition data, higher density, far higher, roaded land, land inside, deis table, roaded

418 sentences; 46 wordings as `leaders`, 48 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters ask the agency to explain why the proposal departs from its own prior findings on fire occurrence and fuel treatment in roadless areas, and to reconcile the rescission with the ignition data in DEIS Table 21, which reports far higher fire density on roaded land than inside the affected roadless areas.
- `collapse`, run 1: The agency must explain why the proposal departs from its own prior findings on fire occurrence and fuel treatment, and reconcile the rescission with the ignition data in DEIS Table 21, which reports far higher fire density on roaded land than inside the affected roadless areas.

#### Cluster 47, topic 2: density roaded, higher density, far higher, roaded land, land inside, density, roaded, inside affected

93 sentences; 42 wordings as `leaders`, 45 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the agency's own data in DEIS Table 21 demonstrates that roaded land has significantly higher fire density and ignition risk than roadless areas, creating a direct contradiction with the proposal's justification for opening roadless areas to new roads for fire and fuels management purposes.
- `collapse`, run 1: Commenters assert that the agency's own DEIS Table 21 data, which reports significantly higher fire ignition density on roaded land compared to roadless areas, directly contradicts the proposal's reliance on wildfire and fuels management as a justification for opening these areas to new road construction.

#### Cluster 57, topic 2: fires million, ignition density, nfs lands, acres year, density, ignition, human-caused, fires

92 sentences; 39 wordings as `leaders`, 39 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own Draft Environmental Impact Statement data demonstrates that wildfire ignition density is significantly higher on roaded National Forest System lands than in inventoried roadless areas, with human-caused ignitions increasing in abundance with proximity to roads, thereby undermining the fire-risk rationale for rescinding the Roadless Rule.
- `collapse`, run 1: The agency's own DEIS data demonstrates that wildfire ignition density is significantly higher on other National Forest System lands than in inventoried roadless areas, with human-caused ignitions increasing in abundance with proximity to roads, thereby undermining the fire-risk rationale for rescinding the Roadless Rule.

#### Cluster 64, topic 2: increase, human-caused, ignitions, access increase, human-caused ignitions, road access, roads, frequency

50 sentences; 36 wordings as `leaders`, 36 as `collapse`.

Temperature 0:

- `leaders`, run 1: The draft environmental impact statement and economic analysis acknowledge that increased road construction and human access in inventoried roadless areas will increase the frequency and hazard of human-caused wildfire ignitions, yet the agency has not quantified this increase or demonstrated that the resulting rise in fire risk is offset by the claimed benefits of improved initial attack success rates and fuels management.
- `collapse`, run 1: The draft environmental impact statement acknowledges that increased road construction and human access in roadless areas will increase the frequency and hazard of human-caused wildfire ignitions, yet the agency has not quantified this increase or demonstrated that the resulting rise in fire risk is offset by the claimed benefits of improved firefighting access and fuels treatment.

#### Cluster 66, topic 2: severity, johnston, areas, burned, developed, roadless, developed lands, rate

36 sentences; 35 wordings as `leaders`, 35 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that recent peer-reviewed research and agency data demonstrate that inventoried roadless areas do not experience significantly higher rates of wildfire ignition, burn area, or fire severity compared to roaded or developed lands, and that factors such as vegetation type, climate, and intensive plantation forestry are more significant drivers of fire outcomes than the presence or absence of roads.
- `collapse`, run 1: Commenters assert that recent peer-reviewed research and agency data demonstrate that inventoried roadless areas do not experience significantly higher rates of wildfire ignition, burn area, or fire severity compared to roaded or developed lands, and that factors such as vegetation type, climate, and intensive plantation forestry are more significant drivers of fire outcomes than the presence or absence of roads.

#### Cluster 68, topic 2: far higher, roaded land, density roaded, higher density, ignition data, land inside, inside affected, deis table

48 sentences; 35 wordings as `leaders`, 36 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain how the proposal to expand road access into roadless areas reconciles with its own draft EIS findings, specifically the ignition data in Table 21 showing far higher fire density on roaded land, and the admission that the comparative wildfire-emissions analysis was not performed.
- `collapse`, run 1: The agency must explain on the record why the rescission departs from its own prior findings and the ignition data in DEIS Table 21, which reports far higher fire density on roaded land than inside affected roadless areas, and reconcile the proposal's fire-management justification with that data.

#### Cluster 69, topic 2: interface, wildland-urban interface, wildland-urban, wui, million acres, overlap, acres percent, acres

47 sentences; 35 wordings as `leaders`, 35 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters dispute the agency's claim that 9.8 million acres (24 percent) of inventoried roadless areas overlap with the wildland-urban interface, citing independent GIS analyses that find the actual overlap is only 2.8 million acres (less than 5 percent), and argue that even the agency's own figure does not justify rescinding the rule for the remaining majority of roadless acres where benefits would be modest and localized.
- `collapse`, run 1: Commenters dispute the agency's claim that 9.8 million acres (24 percent) of inventoried roadless areas overlap with the wildland-urban interface, arguing that independent GIS analyses using Forest Service data show the actual overlap is only 2.8 million acres (less than 5 percent), and contend that even the agency's own figures demonstrate that the proposed rescission is geographically disproportionate to the localized fire protection benefits.

#### Cluster 92, topic 2: wildfires, wildfire, wildfire risk, wildfires human-caused, wildfires caused, fires, caused, start

28 sentences; 28 wordings as `leaders`, 28 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the agency's justification for rescinding the Roadless Rule based on wildfire management is scientifically invalid, citing peer-reviewed evidence that the vast majority of wildfires are human-caused and originate in close proximity to roads, thereby arguing that expanding road access would increase rather than decrease wildfire risk.
- `collapse`, run 1: Commenters assert that the agency's justification for rescinding the Roadless Rule based on wildfire management is scientifically invalid, citing peer-reviewed evidence that the vast majority of wildfires are human-caused and originate in close proximity to roads, thereby arguing that expanding road access would increase rather than decrease wildfire risk.

#### Cluster 94, topic 2: wildfires, start, times likely, wildfires times, times, likely start, likely, pacific biodiversity

30 sentences; 28 wordings as `leaders`, 28 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the rescission ignores scientific evidence and the agency's own records indicating that the vast majority of wildfires ignite near roads, with studies showing ignition rates are significantly higher in roaded areas than in roadless tracts. They argue that because roads facilitate human-caused ignitions, removing roadless protections will increase fire risk rather than improve fire management.
- `collapse`, run 1: Commenters assert that the rescission ignores scientific evidence and the agency's own records indicating that the vast majority of wildfires ignite near roads, with studies showing ignition rates are significantly higher in roaded areas than in roadless tracts, thereby undermining the proposal's claim that new roads improve fire management.

#### Cluster 115, topic 2: ignitions, human-caused, human-caused ignitions, increase, access increase, road access, increase human-caused, wildfire

23 sentences; 23 wordings as `leaders`, 23 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain how it reconciles the DEIS findings that roadless areas currently have lower wildfire ignition densities and that increased road access significantly elevates the risk of human-caused ignitions with its assertion that new roads serve as a wildfire remedy.
- `collapse`, run 1: The agency must explain how it reconciles the DEIS findings that wildfire ignition densities are currently lower in roadless areas and that increased road access significantly elevates the risk of human-caused ignitions with its assertion that new roads serve as a wildfire remedy.

#### Cluster 122, topic 2: probability number, density, probability, number frequency, increases does, does probability, road density, density roads

35 sentences; 20 wordings as `leaders`, 20 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own Draft Environmental Impact Statement acknowledges that increased road density is linked to human-caused wildfires and increases the probability, number, and frequency of ignitions, yet the rescission proceeds without adequately addressing this risk.
- `collapse`, run 1: The agency's own Draft Environmental Impact Statement acknowledges that increased road density is linked to human-caused wildfires and increases the probability, number, and frequency of ignitions, yet the rescission proceeds without adequately addressing or mitigating this documented fire risk.

#### Cluster 123, topic 2: proximity roads, proximity, ignitions increase, abundance proximity, increase abundance, human caused, human, abundance

30 sentences; 20 wordings as `leaders`, 20 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS acknowledges that human-caused wildfire ignitions increase in abundance with proximity to roads, indicating that road access facilitates human entry and thereby elevates the number and frequency of wildfires.
- `collapse`, run 1: The Draft EIS acknowledges that human-caused wildfire ignitions increase in abundance with proximity to roads because roads facilitate human access, thereby increasing the number and frequency of wildfires.

#### Cluster 130, topic 2: hazardous, fuels reduction, hazardous fuel, fuel, reduction, hazardous fuels, fuels, treatments

19 sentences; 19 wordings as `leaders`, 19 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the 2001 Roadless Rule does not prohibit or meaningfully constrain hazardous fuels reduction, prescribed fire, or forest restoration activities within Inventoried Roadless Areas, citing agency data indicating that approximately 1.8 to 2 million acres of such treatments have occurred since the rule's adoption, including specific instances where these treatments successfully mitigated wildfire risk.
- `collapse`, run 1: Commenters assert that the 2001 Roadless Rule does not prohibit or meaningfully constrain hazardous fuels reduction, prescribed fire, or forest restoration activities within Inventoried Roadless Areas, citing agency data indicating that approximately 1.8 to 2 million acres of such treatments have occurred since the rule's adoption, including specific instances where these treatments successfully mitigated wildfire risk.

#### Cluster 137, topic 2: roaded land, higher density, far higher, density roaded, land inside, inside affected, reports far, density

31 sentences; 18 wordings as `leaders`, 18 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain how it can justify rescission on wildfire and fuels management grounds when its own DEIS Table 21 reports far higher fire density on roaded land than inside the affected roadless areas.
- `collapse`, run 1: The agency must explain how it can justify rescission on wildfire and fuels management grounds when its own DEIS Table 21 reports far higher fire density on roaded land than inside the affected roadless areas.

#### Cluster 138, topic 2: access increase, increase human-caused, ignition potential, public access, greater public, acknowledges greater, human-caused, access

43 sentences; 18 wordings as `leaders`, 19 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS acknowledges that increased public access raises the potential for human-caused wildfire ignitions, but it fails to adequately quantify or weigh this increased fire risk against the claimed benefits of new roads, such as facilitated fuel treatments and suppression.
- `collapse`, run 1: The proposal acknowledges that greater public access can increase human-caused ignition potential, but fails to adequately quantify or weigh this increased fire risk against the claimed benefits of new roads.

#### Cluster 143, topic 2: fires, likely result, result fires, roads, roads roadless, building, ecology, areas likely

18 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that constructing roads in roadless areas increases the number of fire ignitions and the frequency of fires requiring suppression, thereby increasing the long-term wildfire threat to nearby communities and ecosystems without meaningfully reducing the likelihood of large fires.
- `collapse`, run 1: Commenters assert that constructing roads in roadless areas increases the number of fire ignitions and the frequency of fires requiring suppression, thereby increasing overall wildfire risk and threatening nearby communities, rather than preventing large fires.

#### Cluster 164, topic 2: initial attack, attack, strategic, initial, roads expected, roads document, suppression, comparison

19 sentences; 14 wordings as `leaders`, 14 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS’s comparison of initial attack success rates between roadless and non-roadless areas is unreliable because it fails to control for the more frequent use of less-than-full suppression strategies in roadless areas, and the anticipated new roads are primarily temporary timber spurs rather than strategic fire roads.
- `collapse`, run 1: The DEIS’s comparison of initial attack success rates between roadless and non-roadless areas is unreliable because it fails to control for the more frequent use of less-than-full suppression strategies in roadless areas, and the anticipated new roads are primarily temporary timber spurs rather than strategic fire roads that would improve suppression access.

#### Cluster 197, topic 2: similar lower, designated areas, disease, lower, insect, iras, forests outside, disease risk

13 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS data indicates that the percentage of forested acres at risk from insects and disease is similar or lower in potentially affected IRAs compared to NFS lands outside designated areas, contradicting the agency's reliance on insect and disease pressure as a primary driver for rescission.
- `collapse`, run 1: The agency cites insect and disease risk as a primary justification for rescinding the Roadless Rule, yet its own Environmental Impact Statement data indicates that the percentage of forested acres at risk from insects and disease is similar to or lower in potentially affected inventoried roadless areas (IRAs) compared to National Forest System lands outside designated areas.

#### Cluster 207, topic 2: justifies rescission, management grounds, fuels management, ignition, justifies, grounds, solution, proposal justifies

11 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads increase ignition rates, explaining how adding roads reduces fire risk when its analysis indicates the opposite.
- `collapse`, run 1: The agency must reconcile its justification for rescission based on wildfire and fuels management with its own data demonstrating that roads drive ignition rates upward, explaining how adding roads reduces fire risk when its analysis indicates the opposite.

#### Cluster 3, topic 3: cumulative, effects, cumulative effects, evaluate, fully, impacts, final, consequences

259 sentences; 255 wordings as `leaders`, 255 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft Environmental Impact Statement fails to conduct a rigorous, site-specific, and quantified analysis of the reasonably foreseeable cumulative environmental, economic, and social consequences of rescission, including habitat fragmentation, watershed degradation, wildlife connectivity loss, carbon storage reduction, wildfire risk, and long-term road maintenance liabilities, instead unlawfully deferring these landscape-scale impacts to future project-level reviews.
- `collapse`, run 1: The Draft Environmental Impact Statement fails to conduct a rigorous, site-specific, and quantified analysis of the reasonably foreseeable cumulative environmental, economic, and social consequences of rescission, including long-term road construction, maintenance liabilities, habitat fragmentation, watershed degradation, and climate impacts, instead unlawfully deferring these landscape-scale effects to future project-level reviews.

#### Cluster 7, topic 3: water, road, roads, construction, sediment, road construction, habitat, erosion

154 sentences; 145 wordings as `leaders`, 145 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the rescission of the Roadless Rule will lead to new road construction and timber harvesting in inventoried roadless areas, resulting in severe and cumulative environmental degradation that the agency has failed to adequately analyze. Specifically, they argue that roads cause significant soil erosion, sedimentation, and water quality impairment that threatens municipal drinking water supplies and aquatic ecosystems, while simultaneously fragmenting habitat, isolating wildlife populations, increasing vehicle-wildlife collisions, and facilitating the spread of invasive species and pathogens, effects that are particularly acute in steep, mountainous, or arid terrains and for sensitive species such as caribou, salmonids, and grizzly bears.
- `collapse`, run 1: Commenters assert that the rescission of the Roadless Rule will lead to new road construction and timber harvesting in inventoried roadless areas, resulting in severe and cumulative environmental degradation that the draft EIS fails to adequately analyze. Specifically, they argue that roads cause significant soil erosion, sedimentation, and water quality impairment that threatens municipal drinking water supplies and aquatic ecosystems, while simultaneously fragmenting habitat, isolating wildlife populations, increasing vehicle-wildlife collisions, and facilitating the spread of invasive species and pathogens, effects that are particularly acute in steep, mountainous, or arid terrains and for sensitive species such as caribou, salmonids, and grizzly bears.

#### Cluster 9, topic 3: water, drinking water, drinking, plos, plos water, million americans, americans, rivers

124 sentences; 114 wordings as `leaders`, 114 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that rescinding the Roadless Rule would compromise the drinking water supply for millions of Americans by removing the primary federal protection for headwaters and river systems, thereby increasing erosion, sedimentation, and contamination risks that would degrade water quality and raise treatment costs for downstream communities.
- `collapse`, run 1: Commenters assert that rescinding the Roadless Rule would degrade water quality and threaten the drinking water supplies of millions of Americans, citing studies that quantify the rule's protection of river miles, headwaters, and municipal watersheds, and argue that the Draft EIS fails to adequately analyze these specific downstream impacts and treatment costs.

#### Cluster 14, topic 3: habitat, wildlife, fragmentation, migration corridors, corridors, species, migration, fragment

91 sentences; 90 wordings as `leaders`, 90 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that road construction fragments contiguous habitats and severs critical migration corridors, causing population declines, genetic isolation, and increased mortality for a wide range of species, including big game, carnivores, aquatic species, and federally listed wildlife.
- `collapse`, run 1: Commenters assert that road construction fragments contiguous habitats and severs critical migration corridors, causing population declines, genetic isolation, and increased mortality for a wide range of species, including wide-ranging mammals, aquatic species, and federally listed wildlife.

#### Cluster 17, topic 3: roads, road, areas, degrade, fragment, wild, worth, character

86 sentences; 86 wordings as `leaders`, 86 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that rescinding the Roadless Rule would authorize new road construction and commercial logging in currently roadless areas, causing irreversible fragmentation of wildlife habitat, degradation of water quality and scenic views, and the permanent loss of the wild character, solitude, and recreation values that define these landscapes. They further argue that this expansion would impose unsustainable fiscal burdens on the agency and exacerbate existing environmental threats, including climate change impacts and invasive species, thereby harming both current and future generations.
- `collapse`, run 1: Commenters assert that rescinding the Roadless Rule would authorize new road construction and commercial logging in currently roadless areas, causing irreversible fragmentation of wildlife habitat, degradation of water quality and scenic views, and the permanent loss of the wild character and solitude that define these landscapes. They further argue that this development would impose unsustainable fiscal burdens on the agency, exacerbate existing road maintenance backlogs, and harm future generations by destroying irreplaceable natural resources.

#### Cluster 19, topic 3: sediment, intakes, water, agency, explain, agency explain, agency address, ask agency

93 sentences; 84 wordings as `leaders`, 84 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain on the record how rescinding the Roadless Rule is consistent with its own findings that road construction generates sediment that degrades water quality, harms fish habitat, and threatens drinking water sources, and must provide quantitative, watershed-specific modeling of sediment delivery to downstream municipal intakes to demonstrate that alternative protections are functionally equivalent to the rule's safeguards.
- `collapse`, run 1: Commenters assert that the agency's own analysis documents that road construction in roadless areas generates sediment that degrades water quality, harms fish habitat, and threatens municipal drinking water sources, yet the proposal lacks the required watershed-specific quantitative modeling of sediment delivery to downstream intakes and fails to identify specific, enforceable plan provisions that are functionally equivalent to the protections of 36 CFR 294.12 and 294.13. The agency must explain on the record how rescission is consistent with its own findings on road-generated sedimentation, quantify the projected sediment delivery to affected municipal intakes, and demonstrate that the remaining regulatory framework adequately protects watershed integrity and public health.

#### Cluster 30, topic 3: intakes, water intakes, watersheds containing, containing, municipal water, sit watersheds, municipal, containing affected

79 sentences; 58 wordings as `leaders`, 57 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission fails to adequately analyze the water quality and public health impacts on the more than 7,000 municipal water intakes serving approximately 24 million people, particularly given that less than 12 percent of these watersheds are currently impaired and the agency's own record documents specific regional vulnerabilities and downstream risks from road-driven erosion and sediment.
- `collapse`, run 1: The rescission would expose more than 7,000 municipal water intakes serving approximately 24 million people to permanent road construction and associated water quality degradation, a risk the agency has not adequately quantified or weighed against the $6.9 billion road maintenance backlog in its cost-benefit analysis.

#### Cluster 51, topic 3: elk, elk survival, gates, gates removed, survival rates, road closure, closure, survival

77 sentences; 41 wordings as `leaders`, 41 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own record and cited scientific literature demonstrate that roads reduce elk survival, fragment habitat, and alter behavior, yet the DEIS fails to project the population-level impacts of road expansion on big game and hunter opportunity.
- `collapse`, run 1: The agency's own DEIS record and cited research establish that roads reduce elk habitat effectiveness, lower survival rates, and fragment migration routes, yet the rescission analysis fails to project the specific impacts of new road construction on big game populations and the hunting opportunities that depend on them.

#### Cluster 55, topic 3: deer, migration routes, movement speed, deer migration, speed, altered mule, routes increased, increased movement

102 sentences; 39 wordings as `leaders`, 38 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission of the Roadless Rule would expose wildlife, including mule deer, elk, moose, and grizzly bears, to documented harms such as altered migration routes, increased movement speed, loss of unroaded security, and heightened human-wildlife conflict, while eliminating the protections that the agency's own records credit with the recovery of these populations.
- `collapse`, run 1: Road construction and resource extraction alter wildlife migration routes, increase movement speed, and disrupt unroaded security, while road corridors attract animals like moose to road salt, increasing human-wildlife conflict and mortality.

#### Cluster 56, topic 3: water, drinking water, drinking, roadless, roadless rule, rule, quality, start

39 sentences; 39 wordings as `leaders`, 39 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule will degrade drinking water quality and quantity for millions of Americans by increasing sedimentation, erosion, and contamination in headwaters and municipal source watersheds, while simultaneously increasing wildfire risk and fragmenting habitats for aquatic and terrestrial species.
- `collapse`, run 1: Rescinding the Roadless Rule will degrade drinking water quality and quantity for millions of Americans by increasing sedimentation, erosion, and contamination in headwaters and municipal source watersheds, while simultaneously increasing wildfire risk and fragmenting habitats for aquatic and terrestrial species.

#### Cluster 58, topic 3: trout, salmon, streams, spawning, sedimentation, brook trout, brook, fish

38 sentences; 38 wordings as `leaders`, 38 as `collapse`.

Temperature 0:

- `leaders`, run 1: Road construction and associated logging activities introduce sediment, increase water temperatures, and degrade riparian buffers, thereby destroying critical spawning and rearing habitat for sensitive aquatic species, including salmon, trout, and other federally listed or native fish populations.
- `collapse`, run 1: Road construction and associated logging activities introduce sediment, increase water temperatures, and degrade riparian buffers, thereby destroying critical spawning and rearing habitat for sensitive aquatic species, including salmon, trout, and other federally listed or native fish populations.

#### Cluster 59, topic 3: reduces biodiversity, fragmentation reduces, biodiversity percent, fragmentation, biodiversity, reduces, finding habitat, cites finding

86 sentences; 38 wordings as `leaders`, 41 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS cites the finding that habitat fragmentation reduces biodiversity by 13 to 75 percent and impairs ecosystem functions, yet fails to apply this quantitative range or the associated fragmentation metrics to the 40.1 million acres of potentially affected environment to project specific adverse impacts on biodiversity and ecosystem processes.
- `collapse`, run 1: The Draft EIS cites the finding that habitat fragmentation reduces biodiversity by 13 to 75 percent, yet fails to apply this quantitative range to the 40.1 million acres of potentially affected environment or connect it to the comparative effects conclusions, despite acknowledging that effects are greatest in small, isolated fragments and increase over time.

#### Cluster 65, topic 3: bird, road-noise, road-noise experiments, experiments, abundance quarter, cut bird, experiments roadless, area cut

90 sentences; 35 wordings as `leaders`, 36 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own DEIS documents that road presence and noise significantly reduce bird richness and abundance, displace species, and fragment habitat, yet the rescission proposal fails to adequately account for these documented ecological harms to bird communities in currently protected roadless areas.
- `collapse`, run 1: Commenters assert that the agency's own DEIS documents that road presence and noise significantly degrade bird habitat, reducing richness and abundance by over 25% and displacing 31% of species, including imperiled and sensitive populations. They argue that rescinding the Roadless Rule would expose these areas to the documented disturbances, causing the loss of bird communities and other wildlife that depend on unroaded, quiet habitat.

#### Cluster 76, topic 3: water, million americans, water million, drinking, drinking water, americans, million, million people

32 sentences; 32 wordings as `leaders`, 32 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule would degrade drinking water quality and increase contamination risks for millions of Americans, particularly in drought-affected regions, by allowing road construction and development in roadless areas that serve as critical watersheds and headwaters.
- `collapse`, run 1: Commenters assert that rescinding the Roadless Rule would degrade drinking water quality and increase contamination risks for millions of Americans, particularly in drought-affected regions, by allowing road construction and development in roadless areas that serve as critical watersheds and headwaters.

#### Cluster 79, topic 3: invasive, invasive plant, spread, plant species, plant, spread invasive, species, non-native

38 sentences; 31 wordings as `leaders`, 31 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that road construction and associated ground disturbance in roadless areas serve as a primary vector for the introduction and spread of invasive plant and animal species, citing scientific studies and the agency's own draft EIS and Biological Assessment to demonstrate that this leads to habitat fragmentation, increased wildfire risk, and threats to native ecosystems and listed species.
- `collapse`, run 1: Commenters assert that road construction and associated ground disturbance in roadless areas serve as a primary vector for the introduction and spread of invasive plant and animal species, citing scientific studies and the agency's own draft EIS and Biological Assessment to demonstrate that this expansion would increase infestation rates, alter habitat composition, and exacerbate wildfire risk.

#### Cluster 100, topic 3: timber sale, sale, percent sediment, sediment, facilities, skid, timber, contribute

59 sentences; 27 wordings as `leaders`, 28 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own analysis establishes that roads and their associated facilities contribute up to 90 percent of the sediment generated by timber sale activity, yet the record fails to project how this sedimentation will impact downstream municipal water supplies, fish habitat, and threatened species such as bull trout.
- `collapse`, run 1: The agency must explain how introducing roads and timber operations into roadless areas is consistent with its own analysis that these activities generate up to 90 percent of sediment, which causes excessive substrate movement, egg and juvenile mortality in fish such as bull trout, and pollution of municipal water supplies.

#### Cluster 105, topic 3: landslides, soils, erosion, road, steep, sediment, slopes, soil erosion

25 sentences; 25 wordings as `leaders`, 25 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that road construction and timber harvest in steep, erodible, or landslide-prone terrain will cause severe soil erosion, increased sedimentation, and slope failures that degrade water quality, harm aquatic habitats, and threaten downstream communities.
- `collapse`, run 1: Commenters assert that road construction and timber harvest in steep, erodible, or landslide-prone terrain will cause severe soil erosion, increased sedimentation, and slope failures that degrade water quality, harm aquatic habitats, and threaten downstream communities.

#### Cluster 110, topic 3: discharge, waters, material, water act, crossing, act section, section, stream

24 sentences; 24 wordings as `leaders`, 24 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS fails to identify jurisdictional waters, quantify fill material discharges at stream crossings, and demonstrate compliance with Clean Water Act Section 404 permitting and Section 401 certification requirements.
- `collapse`, run 1: The DEIS fails to identify jurisdictional waters, quantify fill material discharges at stream crossings, and demonstrate compliance with Clean Water Act Section 404 permitting and Section 401 certification requirements for the proposed road construction.

#### Cluster 113, topic 3: water, water quality, quality, sediment, source sediment, harvest operations, source, sediment related

33 sentences; 23 wordings as `leaders`, 23 as `collapse`.

Temperature 0:

- `leaders`, run 1: Road construction and timber harvesting in inventoried roadless areas are major sources of sediment and nutrient runoff that degrade water quality, increase turbidity, and threaten drinking water sources, as acknowledged by the Draft EIS and peer-reviewed research.
- `collapse`, run 1: Commenters assert that road construction and timber harvest in inventoried roadless areas are major sources of sediment and nutrient runoff that degrade water quality, increase turbidity, and threaten drinking water supplies, citing peer-reviewed research and the agency's own Draft EIS findings that these activities cause significant water quality degradation.

#### Cluster 135, topic 3: grizzly, open roads, habituation, reward, habituation food, food reward, contact conflict, ultimately end

63 sentences; 18 wordings as `leaders`, 18 as `collapse`.

Temperature 0:

- `leaders`, run 1: Opening the roadless lands to new roads and motorized access will increase human-wildlife contact, conflict, habituation, and food reward, ultimately leading to increased human-caused mortality for grizzly bears and other species, and impairing secure habitat and future dispersal corridors necessary for recovery.
- `collapse`, run 1: The agency must analyze how opening the roadless network to new and existing roads will increase human-caused mortality, habituation, and habitat fragmentation for grizzly bears and other wildlife, including by impairing future dispersal corridors and secure habitat essential for recovery.

#### Cluster 142, topic 3: physical, contaminants, sediment, chemical, drivers, alters, installation, introduces

17 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: Road construction destabilizes slopes and generates chronic sediment inputs that alter hydrology and deliver chemical contaminants to adjacent habitats, thereby intensifying threats from fire, invasive species, logging, mining, and utility lines.
- `collapse`, run 1: Road construction destabilizes slopes and generates chronic sediment inputs that alter hydrology and deliver chemical contaminants to adjacent habitats, thereby intensifying threats from fire, invasive species, logging, mining, and utility lines.

#### Cluster 146, topic 3: ira, impervious, runoff, surfaces, downstream floodplains, floodplains, peak, flows

18 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: Road construction and maintenance in Inventoried Roadless Areas convert permeable forest soils to impervious surfaces, intercept subsurface flow, and create direct conduits for sediment delivery, thereby accelerating runoff concentration, elevating peak discharges, and altering natural drainage patterns to increase flood risk and degrade aquatic habitats.
- `collapse`, run 1: Road construction and maintenance in Inventoried Roadless Areas convert permeable forest soils to impervious surfaces, intercept subsurface flow, and create direct conduits for sediment delivery, thereby accelerating runoff concentration, elevating peak discharges, and altering natural drainage patterns to increase flood risk and degrade aquatic habitats.

#### Cluster 151, topic 3: salem, water treatment, treatment plants, departments, avoiding, ira watersheds, treatment, highway

20 sentences; 16 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule will impose substantial financial burdens on downstream communities and public agencies by increasing sedimentation from road construction and logging, thereby raising the costs of water treatment and infrastructure maintenance.
- `collapse`, run 1: Rescinding the Roadless Rule will impose substantial financial burdens on downstream communities and public agencies by increasing sedimentation from road construction and logging, thereby raising the costs of water treatment and infrastructure maintenance.

#### Cluster 157, topic 3: sediment, logging roads, journal soil, undisturbed habitat, water conservation, forest roads, source, roads

19 sentences; 15 wordings as `leaders`, 15 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that rescinding the Roadless Rule would introduce extensive road construction into inventoried roadless areas, creating a dominant source of nonpoint source pollution that would drastically increase erosion and sediment delivery to streams, thereby degrading water quality and threatening aquatic species such as cold-water trout.
- `collapse`, run 1: Commenters assert that rescinding the Roadless Rule would introduce extensive road construction into inventoried roadless areas, creating a dominant source of nonpoint source pollution that would drastically increase erosion and sediment delivery to streams, thereby degrading water quality and threatening aquatic species such as cold-water trout.

#### Cluster 160, topic 3: flood, impervious, volume peak, runoff volume, impervious surface, runoff, hazard, surface runoff

15 sentences; 15 wordings as `leaders`, 15 as `collapse`.

Temperature 0:

- `leaders`, run 1: Executive Order 11988 requires the agency to evaluate flood hazard potential and demonstrate compliance by quantifying how road construction in the identified Inventoried Roadless Areas increases impervious surface, runoff volume, and peak flows, thereby altering watershed hydrology and affecting downstream communities and infrastructure.
- `collapse`, run 1: Executive Order 11988 requires the agency to evaluate flood hazard potential and demonstrate compliance by quantifying how road construction in the identified Inventoried Roadless Areas increases impervious surface, runoff volume, and peak flows, thereby altering watershed hydrology and affecting downstream communities and infrastructure.

#### Cluster 170, topic 3: sacred, tribal, sacred sites, rights, treaty-reserved, resources sacred, tribal rights, rights interests

14 sentences; 13 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS acknowledges that rescission of the Roadless Rule would permit road construction and timber harvest in inventoried roadless areas, which could significantly alter Tribal access to treaty-reserved resources, sacred sites, and culturally significant areas, thereby having long-term negative effects on Tribal rights, interests, and subsistence practices.
- `collapse`, run 1: The DEIS acknowledges that rescission of the Roadless Rule would permit road construction and timber harvest in inventoried roadless areas, which could significantly alter Tribal access to treaty-reserved resources, sacred sites, and culturally significant areas, thereby having long-term negative effects on Tribal rights, interests, and subsistence practices.

#### Cluster 171, topic 3: impacts, adverse, impacts threatened, effects biodiversity, wildlife plants, timber harvest, biodiversity, timber

13 sentences; 13 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS acknowledges that road construction and timber harvest under the proposed alternatives would cause long-term adverse effects on biodiversity, including habitat fragmentation, loss of connectivity, and harm to threatened and endangered species, as well as detrimental impacts to water quality, fire frequency, and non-commodity values such as recreation and tribal resources.
- `collapse`, run 1: The Draft EIS acknowledges that road construction and timber harvest under the proposed alternatives would cause long-term adverse effects on biodiversity, including habitat fragmentation, loss of connectivity, and harm to threatened and endangered species, as well as detrimental impacts to water quality, fire frequency, and non-commodity values such as recreation and tribal resources.

#### Cluster 175, topic 3: thorough environmental, analysis roadless, environmental analysis, watersheds, thorough, hydrologic, watersheds negatively, guarantee watersheds

13 sentences; 13 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must conduct a thorough, site-specific environmental analysis of the impacts of additional road construction and associated activities on watersheds, including municipal water supplies, headwater streams, and Essential Fish Habitat, to ensure that no water resources are negatively affected by the rescission.
- `collapse`, run 1: The agency must conduct a thorough, site-specific environmental analysis of the impacts of additional road construction and associated activities on watersheds, including municipal water supplies, headwater streams, and Essential Fish Habitat, to ensure that no water resources are negatively affected by the rescission.

#### Cluster 177, topic 3: roads, forest, kaibab, truck, erosion, ranger district, road, left

13 sentences; 13 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Forest Service lacks the funding and staffing to maintain its existing road system, resulting in a massive deferred maintenance backlog that causes ongoing environmental degradation, including erosion, sedimentation, and habitat loss, while also creating safety hazards for motorists and straining local emergency services.
- `collapse`, run 1: The Forest Service lacks the funding and staffing to maintain its existing road system, resulting in a massive deferred maintenance backlog that causes ongoing environmental degradation, including erosion, sedimentation, and habitat loss, while also creating safety hazards for motorists and straining local emergency services.

#### Cluster 181, topic 3: forest currently, road surfaces, sediment, channels, impervious, cut slopes, ira, delivering

12 sentences; 12 wordings as `leaders`, 12 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that specific Inventoried Roadless Areas currently lack impervious road surfaces, exposed cut or fill slopes, and stream crossings that deliver sediment to channels, resulting in zero road-generated sediment loading. They contend that the aquatic ecosystems, fishing streams, and paddling resources within these areas depend on this current absence of road-related erosion and sedimentation.
- `collapse`, run 1: Commenters assert that specific Inventoried Roadless Areas currently lack impervious road surfaces, exposed cut or fill slopes, and stream crossings that deliver sediment to channels, resulting in zero road-generated sediment loading and undisturbed watersheds. They contend that the aquatic ecosystems, fishing streams, and paddling resources within these areas depend on this current absence of road-related erosion and sedimentation.

#### Cluster 196, topic 3: bird, bird communities, roads birds, opening, acres road, statement documents, documents roads, agency explain

12 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency has not adequately explained how opening inventoried roadless areas to new roads is consistent with its own documented findings that road construction degrades bird communities, nor has it projected the site-level and cumulative impacts of this expansion on avian species richness, abundance, and migratory populations.
- `collapse`, run 1: The agency has failed to adequately explain how opening inventoried roadless areas to new roads is consistent with its own documented findings that road construction degrades bird communities, and it has not projected the site-level or cumulative impacts of this expansion on avian species richness, abundance, and migratory populations.

#### Cluster 201, topic 3: erosion landslide, increase soil, pollution watersheds, sediment pollution, landslide, million americans, supply drinking, landslide risk

10 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission of the Roadless Rule would increase soil erosion, landslide risk, and sediment pollution in watersheds that supply drinking water to millions of Americans, thereby degrading water quality and compromising public health.
- `collapse`, run 1: The rescission of the Roadless Rule would increase soil erosion, landslide risk, and sediment pollution in watersheds that supply drinking water to millions of Americans, thereby degrading water quality and compromising public health.

#### Cluster 203, topic 3: birds, bird, habitat, nest, population, bird species, declined, breeding

10 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule would authorize new road construction in roadless areas, causing habitat loss, fragmentation, and noise pollution that degrade the complex forest interior conditions required by migratory and resident bird species, thereby accelerating the documented population declines of these avian populations.
- `collapse`, run 1: Rescinding the Roadless Rule would authorize new road construction in roadless areas, causing habitat loss, fragmentation, and noise pollution that degrade the complex forest interior conditions required by migratory and resident bird species, thereby accelerating the documented population declines of these avian populations.

#### Cluster 2, topic 4: area conservation, conservation rule, cfr subpart, conservation, roadless, roadless area, subpart, rule

389 sentences; 293 wordings as `leaders`, 298 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters urge the Forest Service to withdraw the proposed rescission of the 2001 Roadless Area Conservation Rule (36 CFR Part 294, Subpart B) and select the No Action alternative, arguing that the rule provides necessary, lasting, and categorical protection for inventoried roadless areas that cannot be adequately replaced by forest-level planning or project-level review, and that rescission would result in irreversible harm to ecosystems, watersheds, and public lands.
- `collapse`, run 1: Commenters urge the Forest Service to withdraw the proposed rescission of the 2001 Roadless Area Conservation Rule (36 CFR Part 294, Subpart B) and select the No Action alternative, arguing that the rule provides necessary, lasting, and categorical protection for inventoried roadless areas that would be lost if replaced by localized or project-level management.

#### Cluster 4, topic 4: acres, million acres, million, national, acres national, national forest, forest, rule

224 sentences; 209 wordings as `leaders`, 210 as `collapse`.

Temperature 0:

- `leaders`, run 1: The proposed rescission would remove national-level protections from approximately 44.7 to 58.5 million acres of inventoried roadless areas across the National Forest System, exposing these lands to new road construction, logging, mining, and other industrial development that would cause irreversible fragmentation, habitat loss, and degradation of water quality, wildlife, and recreation resources.
- `collapse`, run 1: The proposed rescission would remove national-level protections from approximately 44.7 to 58.5 million acres of National Forest System lands, exposing these areas to road construction, logging, mining, and other industrial development that would cause irreversible fragmentation, habitat loss, and degradation of water quality, wildlife, and recreation resources.

#### Cluster 13, topic 4: roadless, rule, area conservation, conservation rule, roadless area, rescind roadless, roadless rule, conservation

104 sentences; 94 wordings as `leaders`, 95 as `collapse`.

Temperature 0:

- `leaders`, run 1: The proposed full rescission of the 2001 Roadless Rule would eliminate the uniform national prohibitions on road construction, road reconstruction, and timber harvesting in inventoried roadless areas, shifting decision-making to local forest plans without a guaranteed baseline of protection, thereby exposing approximately 58.5 million acres to increased development, mining, and ecological degradation.
- `collapse`, run 1: Rescinding the 2001 Roadless Rule would eliminate the nationwide prohibitions on road construction, road reconstruction, and timber harvesting in inventoried roadless areas, shifting decision-making to local forest plans without a consistent baseline of protection, thereby exposing approximately 45 million acres to increased development, mining, and ecological degradation.

#### Cluster 29, topic 4: conservation rule, area conservation, roadless area, conservation, area, agency record, agency, rule

91 sentences; 58 wordings as `leaders`, 59 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own record and analysis contradict the justifications for rescinding the 2001 Roadless Area Conservation Rule, documenting that the action would increase road construction, degrade habitat, and threaten the conservation values the rule was designed to protect, thereby failing to demonstrate that rescission is a responsible or legally supported management decision.
- `collapse`, run 1: The agency's own record and analysis contradict the justifications for rescinding the 2001 Roadless Area Conservation Rule, documenting significant environmental, ecological, and public use costs that the proposal fails to adequately address or reconcile.

#### Cluster 42, topic 4: docket fs-, fs-, conservation rule, area conservation, rescission roadless, docket, filing comment, oppose

59 sentences; 44 wordings as `leaders`, 44 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters oppose the rescission of the 2001 Roadless Area Conservation Rule because the agency’s own record, data, and analysis contradict the proposal’s rationale, fail to account for specific local impacts and public interests, and do not support the action.
- `collapse`, run 1: Commenters assert that the proposed rescission of the 2001 Roadless Area Conservation Rule is unsupported by the agency's own record, which contains data, economic analyses, and legal precedents that contradict the proposal and fail to adequately justify the permanent risk to roadless areas, watersheds, and public interests.

#### Cluster 43, topic 4: new hampshire, hampshire, roadless, conservation rule, rule, area conservation, new, national

44 sentences; 44 wordings as `leaders`, 44 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that rescinding the 2001 Roadless Rule would cause direct, irreversible harm to specific local ecosystems, water quality, and wildlife habitats, while simultaneously threatening the economic stability of communities that rely on outdoor recreation, tourism, and the preservation of roadless character.
- `collapse`, run 1: Commenters assert that rescinding the 2001 Roadless Rule would cause direct, irreversible harm to specific local ecosystems, water quality, and wildlife habitats, while simultaneously threatening the economic stability of communities that rely on outdoor recreation, tourism, and the preservation of roadless character.

#### Cluster 62, topic 4: rule, roadless rule, roadless, wildlife water, environmental, water, harm, deis

37 sentences; 37 wordings as `leaders`, 37 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Forest Service must conduct a full, site-specific environmental review that accurately assesses the cumulative and localized impacts of rescinding the Roadless Rule, including degradation of water quality, wildlife habitat, and scenic values, increased wildfire and invasive species risks, and negative economic and tribal consequences, rather than relying on a generalized analysis that fails to address the severe harm documented in the agency's own Draft Environmental Impact Statement.
- `collapse`, run 1: The Forest Service must conduct a full, site-specific environmental review that accurately assesses the cumulative and localized impacts of rescinding the Roadless Rule, including degradation of water quality, wildlife habitat, and scenic values, increased wildfire and invasive species risks, and economic harm to communities, rather than relying on a DEIS that commenters argue fails to adequately address these severe consequences.

#### Cluster 63, topic 4: miles, miles trails, trails, whitewater, routes, climbing, climbing routes, miles whitewater

36 sentences; 36 wordings as `leaders`, 36 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule would remove protections for approximately 45 million acres of national forest land, jeopardizing over 25,000 miles of trails, thousands of climbing routes, and hundreds of miles of whitewater and mountain biking terrain, including significant sections of the Pacific Crest, Continental Divide, and Arizona National Scenic Trails, while also threatening the integrity of wild and scenic rivers and the wilderness character of these areas.
- `collapse`, run 1: Rescinding the Roadless Rule would remove protections for approximately 45 million acres of national forest land, jeopardizing over 25,000 miles of trails, thousands of climbing routes, and hundreds of miles of whitewater and mountain biking terrain, including significant sections of the Pacific Crest, Continental Divide, and Arizona National Scenic Trails, while also threatening the integrity of wild and scenic rivers and the wilderness character of these areas.

#### Cluster 70, topic 4: tongass, tongass national, forest, logging damaging, temperate, industrial logging, industrial, rainforest

51 sentences; 34 wordings as `leaders`, 34 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule would expose irreplaceable old-growth forests, particularly the Tongass National Forest, to industrial logging and road construction, causing permanent ecological degradation, loss of carbon sequestration, and harm to wildlife and water quality.
- `collapse`, run 1: The rescission would expose irreplaceable old-growth ecosystems, particularly the Tongass National Forest, to industrial logging and road construction, causing permanent degradation of critical carbon sinks, water quality, and biodiversity.

#### Cluster 75, topic 4: retain roadless, retain, roadless, urge, long-term, rule, roadless rule, fully

32 sentences; 32 wordings as `leaders`, 32 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must retain the 2001 Roadless Area Conservation Rule or, if it proceeds with rescission, conduct a rigorous, site-specific environmental analysis that fully evaluates the long-term, cumulative impacts on watershed integrity, wildlife habitat and connectivity, fire ecology, carbon storage, recreation, and public health, while addressing the inadequacy of the current rule's exceptions, the unfunded fiscal liabilities of road construction and maintenance, and the reliance interests of local communities and stakeholders.
- `collapse`, run 1: The agency must retain the 2001 Roadless Area Conservation Rule or, if it proceeds with rescission, conduct a rigorous, site-specific environmental analysis that fully evaluates the long-term, cumulative impacts on watershed integrity, wildlife habitat and connectivity, fire ecology, carbon storage, recreation, and public health, while addressing the inadequacy of the current rule's exceptions, the unfunded fiscal liabilities of road construction and maintenance, and the reliance interests of local communities and stakeholders.

#### Cluster 83, topic 4: million acres, million, acres, rule successfully, roadless, rule, national, long-term protection

34 sentences; 30 wordings as `leaders`, 31 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the 2001 Roadless Rule has successfully provided long-term protection for approximately 45 to 58.5 million acres of inventoried roadless areas across the National Forest System by prohibiting road construction, timber harvesting, and other industrial development, and they argue that rescinding the rule would remove these established protections from these lands.
- `collapse`, run 1: Commenters assert that the 2001 Roadless Area Conservation Rule has successfully provided long-term protection for approximately 45 to 58.5 million acres of inventoried roadless areas across the National Forest System by prohibiting road construction, timber harvesting, and other industrial development, and they request that this rule remain in effect to preserve these lands from fragmentation and ecological degradation.

#### Cluster 90, topic 4: areas, roadless areas, roadless, ibisch, biodiversity, org, doi org, https doi

29 sentences; 29 wordings as `leaders`, 29 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that scientific research demonstrates inventoried roadless areas are among the nation's most ecologically valuable, least disturbed, and cost-effective landscapes for conserving biodiversity, maintaining habitat connectivity, and providing critical ecosystem services such as water quality and carbon storage. They argue that rescinding the Roadless Rule would remove essential protections for these irreplaceable intact ecosystems, exposing them to fragmentation, invasive species, and degradation that would undermine global and national conservation goals.
- `collapse`, run 1: Commenters assert that scientific research demonstrates inventoried roadless areas are among the nation's most ecologically valuable, least disturbed, and cost-effective landscapes for conserving biodiversity, maintaining habitat connectivity, and providing critical ecosystem services such as water quality and carbon storage. They argue that rescinding the Roadless Rule would remove essential protections for these irreplaceable intact ecosystems, exposing them to fragmentation, invasive species, and degradation that would undermine global conservation goals and the survival of vulnerable wildlife species.

#### Cluster 102, topic 4: species, roadless, areas, roadless areas, habitat, strongholds, wildlife species, vulnerable

29 sentences; 26 wordings as `leaders`, 26 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that inventoried roadless areas function as essential biological strongholds, refuges, and climate-adaptation corridors for a disproportionate share of vulnerable, threatened, and endangered species, as well as wide-ranging wildlife requiring large contiguous habitat blocks. They argue that rescinding the rule would fragment these critical habitats, undermine species recovery and connectivity, and fail to meet the diversity requirements of the National Forest Management Act.
- `collapse`, run 1: Commenters assert that inventoried roadless areas function as essential biological strongholds, refuges, and climate-adaptation corridors for a disproportionate share of vulnerable, threatened, and endangered species, including wide-ranging mammals and endemic populations, and that rescinding the rule would fragment this habitat, increase access for generalist species and poaching, and undermine the agency’s statutory obligations to protect biodiversity and ecosystem integrity.

#### Cluster 109, topic 4: species, dietz, conservation concern, species conservation, suitable habitat, suitable, wildlife species, concern

28 sentences; 24 wordings as `leaders`, 24 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that rescinding the Roadless Rule would harm wildlife by eliminating habitat for a significant portion of species of conservation concern, citing studies that find inventoried roadless areas provide suitable habitat for 57% of such species and that 77% of these areas have the potential to conserve threatened, endangered, or imperiled species.
- `collapse`, run 1: Commenters assert that rescinding the Roadless Rule would negatively impact wildlife by eliminating habitat for a significant proportion of species of conservation concern, citing studies that find inventoried roadless areas provide suitable habitat for 57% of such species and that 77% of these areas have the potential to conserve threatened, endangered, or imperiled species.

#### Cluster 117, topic 4: live, montana, directly affected, affected proposal, adversely affected, affected, rule, adversely

22 sentences; 22 wordings as `leaders`, 22 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission of the 2001 Roadless Rule would disproportionately and adversely impact residents, landowners, and recreationists across the United States, including those in states with high acreage designations like Montana and those in states with lower direct acreage who rely on travel to affected areas for hunting, fishing, and other outdoor recreation.
- `collapse`, run 1: The rescission of the 2001 Roadless Rule would disproportionately and adversely impact residents, landowners, and recreationists in western states such as Montana, Idaho, and Wyoming, as well as individuals in other states who travel to or recreate on affected National Forest System lands, resulting in significant local and national consequences for these communities.

#### Cluster 128, topic 4: species, fragmentation, habitat fragmentation, habitat, migratory, unfragmented, bears, native

19 sentences; 19 wordings as `leaders`, 19 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that roadless areas provide the large, contiguous, and unfragmented habitats essential for the survival, genetic dispersal, and migration of sensitive, wide-ranging, and imperiled species, including carnivores, fish, and migratory birds, which cannot tolerate the habitat fragmentation caused by new roads.
- `collapse`, run 1: Commenters assert that roadless areas provide the large, contiguous, and unfragmented habitats essential for the survival, genetic dispersal, and migration of sensitive, wide-ranging, and imperiled species, including carnivores, fish, and migratory birds, which cannot tolerate the habitat fragmentation caused by new roads.

#### Cluster 129, topic 4: million acres, acres, million, acres national, approximately million, approximately, alternative, national

19 sentences; 19 wordings as `leaders`, 19 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the rescission proposal would remove protections from a vast and specific acreage of inventoried roadless areas, citing figures ranging from 31.7 million to 58.5 million acres, and argue that the scale of this removal is disproportionate to the remaining protected lands.
- `collapse`, run 1: Commenters assert that the rescission proposal would remove protections from a vast and specific acreage of inventoried roadless areas, citing figures ranging from 31.7 million to 58.5 million acres, and argue that this scale of removal is inadequate or disproportionate relative to the total National Forest System lands.

#### Cluster 139, topic 4: iras, protected areas, talty, protected, belote, areas, conservation, iras increase

20 sentences; 18 wordings as `leaders`, 18 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that IRAs provide critical ecological functions—including serving as habitat for species of conservation concern, buffering and connecting existing protected areas, sequestering carbon, and representing underrepresented ecosystems—and argue that rescinding the Roadless Rule would expose these lands to fragmentation and degradation, thereby undermining the integrity of the national conservation network.
- `collapse`, run 1: Commenters assert that IRAs provide critical ecological functions—including serving as habitat for species of conservation concern, buffering and connecting existing protected areas, increasing the representation of underrepresented ecosystems, and sequestering carbon—that would be lost if the Roadless Rule is rescinded, and they request that the EIS evaluate these benefits.

#### Cluster 141, topic 4: rescinded lose, roadless, national forest, lose, national, rule, ridge, pisgah national

17 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the 2001 Roadless Area Conservation Rule would destroy the natural beauty, undisturbed habitats, and quiet recreational experiences that commenters value in specific National Forests, thereby causing irreparable harm to their personal enjoyment and the public trust in these lands.
- `collapse`, run 1: Rescinding the 2001 Roadless Area Conservation Rule would destroy the natural beauty, undisturbed habitats, and quiet recreational experiences that commenters value in specific National Forests, thereby causing irreparable harm to their personal enjoyment and the public trust in these lands.

#### Cluster 154, topic 4: acres, rule applies, roadless, million acres, holds inventoried, million, acres national, applies

17 sentences; 16 wordings as `leaders`, 16 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the Draft EIS fails to adequately account for the specific acreage, inventory counts, and existing state-specific or congressional designations within the 44.7 million acres of inventoried roadless areas, particularly regarding the scale of these lands in individual states and the Tongass National Forest.
- `collapse`, run 1: Commenters assert that the rescission fails to adequately account for the specific scale, geographic distribution, and existing protections of inventoried roadless areas across various states and regions, including the Tongass National Forest, and that the agency's analysis ignores the actual volume of past logging and the distinct conservation status of these lands.

#### Cluster 156, topic 4: acres, miles national, national, roadless, areas, million acres, national park, million

16 sentences; 16 wordings as `leaders`, 16 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that rescinding the rule would disproportionately impact high-value conservation assets, including old-growth forests, imperiled species, and critical habitat, particularly in regions with limited alternative recreation options such as the Northeast and Greater Yellowstone, where roadless areas constitute a significant share of forest land and serve as irreplaceable refuges.
- `collapse`, run 1: Commenters assert that rescinding the Roadless Rule would result in the loss of significant, irreplaceable natural resources, including old-growth forests, habitat for imperiled species, and wild and scenic rivers, particularly in ecologically sensitive regions such as the Greater Yellowstone Ecosystem, the White Mountains, and areas adjacent to national parks. They argue that these roadless areas constitute a critical proportion of National Forest land and provide essential outdoor recreation opportunities, and that the proposed rescission would fast-track destructive projects in lands intentionally set aside to preserve their natural values and functions.

#### Cluster 165, topic 4: integrity, highest integrity, mildrexler, forests, biological conservation, forest ecosystems, integrity forest, conservation volume

14 sentences; 14 wordings as `leaders`, 14 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that rescinding the Roadless Rule would degrade the highest-integrity forest ecosystems in the United States, specifically Inventoried Roadless Areas, by threatening old-growth structures, reducing carbon storage, and compromising biodiversity, clean water, and climate regulation benefits that recent studies and the Forest Landscape Integrity Index confirm are unique to these protected landscapes.
- `collapse`, run 1: Commenters assert that rescinding the Roadless Rule would degrade the highest-integrity forest ecosystems in the United States, specifically Inventoried Roadless Areas, by threatening old-growth structures, reducing carbon storage, and compromising biodiversity, clean water, and climate regulation benefits that recent studies and the Forest Landscape Integrity Index confirm are unique to these protected landscapes.

#### Cluster 167, topic 4: central oregon, live work, scenic views, choose, oregon, recreation areas, views, local economies

16 sentences; 14 wordings as `leaders`, 14 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule will damage local economies by degrading the recreation, scenic views, and wildlife habitat that drive tourism and support rural livelihoods, while increasing fire risks and causing long-term ecological harm.
- `collapse`, run 1: Rescinding the Roadless Rule will damage local economies by degrading the recreation, scenic views, and wildlife habitat that drive tourism and support rural livelihoods, while increasing fire risks and causing long-term ecological harm.

#### Cluster 178, topic 4: rollback, washington state, resident, pristine, concerned, coconino, state, threatens

12 sentences; 12 wordings as `leaders`, 12 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the rescission of the 2001 Roadless Rule will cause severe, irreversible harm to the ecological integrity, clean water, and public safety of roadless areas, while simultaneously devastating local economies, outdoor recreation industries, and community resources across diverse geographic regions.
- `collapse`, run 1: Commenters assert that the rescission of the 2001 Roadless Rule will cause severe, irreversible harm to the ecological integrity, clean water, and public safety of roadless areas, while simultaneously devastating local economies, outdoor recreation industries, and community resources across diverse geographic regions.

#### Cluster 179, topic 4: protects, million acres, protects million, clean, acres, acres national, million, rule protects

12 sentences; 12 wordings as `leaders`, 12 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the Roadless Rule has successfully protected approximately 45 to 58 million acres of national forest lands, thereby preserving intact habitat, clean drinking water sources, and biodiversity, while preventing the fragmentation, pollution, and fire risks associated with road construction and development.
- `collapse`, run 1: Commenters assert that the Roadless Rule has successfully protected approximately 45 to 58 million acres of national forest lands, thereby preserving intact habitat, clean drinking water sources, and biodiversity, while preventing the fragmentation, pollution, and fire risks associated with road construction and development.

#### Cluster 180, topic 4: road reconstruction, construction road, cfr subpart, reconstruction, subpart, reconstruction timber, road, remove

12 sentences; 12 wordings as `leaders`, 12 as `collapse`.

Temperature 0:

- `leaders`, run 1: The proposed rule would remove and reserve 36 CFR Part 294, Subpart B, eliminating the national prohibitions on road construction, road reconstruction, and timber harvesting in inventoried roadless areas.
- `collapse`, run 1: The proposed rule would remove and reserve 36 CFR Part 294, Subpart B, eliminating the national prohibitions on road construction, road reconstruction, and timber harvesting in inventoried roadless areas.

#### Cluster 187, topic 4: wnc, oregon, threaten, firefighter, plants animals, water, wildfires, rescinding

11 sentences; 11 wordings as `leaders`, 11 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescission of the Roadless Rule would increase wildfire risk and threaten firefighter safety, degrade water and air quality, destroy wildlife habitat and old-growth forests, and reduce public recreation opportunities.
- `collapse`, run 1: Rescinding the Roadless Rule would increase wildfire risk and threaten firefighter safety, degrade water and air quality, destroy wildlife habitat and old-growth forests, and reduce public recreation opportunities.

#### Cluster 198, topic 4: deeply, public lands, florida, deeply concerned, concerned, lands, policies, public

10 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the 2001 Roadless Rule will expose remaining intact public lands to road construction, commercial logging, and other extractive activities, causing long-term ecological degradation, habitat fragmentation, and watershed damage that threatens irreplaceable ecosystems and future generations.
- `collapse`, run 1: Rescinding the 2001 Roadless Rule will expose remaining intact public lands to road construction, commercial logging, and other extractive activities, resulting in the fragmentation of wildlife habitats, degradation of watersheds, and loss of ecosystem integrity.

#### Cluster 205, topic 4: acres inventoried, areas iras, iras, acres, million acres, commercial, inventoried, inventoried roadless

10 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the 2001 Roadless Rule would remove federal prohibitions on road construction and commercial timber harvesting from approximately 45 to 58.5 million acres of Inventoried Roadless Areas, causing irreversible degradation to wildlife habitat, clean drinking water sources, and local outdoor recreation economies, while failing to meet legal requirements and scientific standards for land management.
- `collapse`, run 1: Rescinding the 2001 Roadless Rule would remove federal prohibitions on road construction and commercial timber harvesting from approximately 45 to 58.5 million acres of Inventoried Roadless Areas, causing irreversible degradation to wildlife habitat, clean drinking water sources, and local outdoor recreation economies, while failing to meet legal requirements and scientific standards for land management.

#### Cluster 25, topic 5: spending, visitor spending, visitor, recreation, lost visitor, economic, million, communities

81 sentences; 72 wordings as `leaders`, 72 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule would degrade backcountry access and recreation settings, resulting in significant annual losses to local economies and visitor spending that outweigh the projected gains from timber sales and other resource extraction.
- `collapse`, run 1: Rescinding the Roadless Rule would degrade roadless character and backcountry access, resulting in significant annual losses to local economies from reduced visitor spending and recreation-related economic activity, which the agency's own Draft Environmental Impact Statement estimates at up to $9 million or more per year.

#### Cluster 33, topic 5: minimum million, outfitters guides, operators, guides, guides tour, tour operators, outfitters, recreation benefit

137 sentences; 51 wordings as `leaders`, 51 as `collapse`.

Temperature 0:

- `leaders`, run 1: The regulatory flexibility analysis certifies no significant impact on small entities, a conclusion that contradicts the agency's own Cost Benefit Analysis and Draft Environmental Impact Statement, which identify outfitters, guides, and tour operators as affected parties and quantify lost recreation benefits at a minimum of $6.1 million annually.
- `collapse`, run 1: The regulatory flexibility analysis certifies no significant impact on small entities, a conclusion that contradicts the agency's own DEIS and Cost Benefit Analysis, which identify outfitters, guides, and tour operators as affected parties and quantify lost recreation benefits at a minimum of $6.1 million annually, while the certification improperly dilutes these specific losses by averaging them across the entire national sector rather than assessing the specific businesses operating in the affected areas.

#### Cluster 45, topic 5: million, revenue, million year, year, timber, estimates, recreation, timber revenue

59 sentences; 43 wordings as `leaders`, 43 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the DEIS’s economic analysis is inadequate because the projected modest timber revenue gains of $5.2–$11.4 million annually are offset or exceeded by estimated recreation losses of $6.1 million, unquantified road construction and maintenance costs, and the broader economic value of intact landscapes, resulting in no net financial benefit to the government or local economies.
- `collapse`, run 1: Commenters assert that the DEIS’s economic analysis is inadequate because the projected $5.2–$11.4 million in annual timber revenue is modest, uncertain, and largely offset by estimated $6.1 million in annual recreation losses, road construction and maintenance costs, and unquantified values such as water quality and habitat, resulting in no net economic benefit.

#### Cluster 48, topic 5: self-reliant recreation, self-reliant, remote self-reliant, quiet remote, opportunities quiet, recreation, quiet, tradeoffs

47 sentences; 42 wordings as `leaders`, 42 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own analysis acknowledges that rescission would result in tradeoffs with opportunities for quiet, remote, and self-reliant recreation, increase user conflicts, and cause an estimated $6.1 million in annual lost economic benefits, yet the Final EIS fails to adequately quantify these net changes, distinguish road types, or analyze specific impacts on local communities and distinct user groups.
- `collapse`, run 1: The agency's own analysis acknowledges that rescission would result in tradeoffs with opportunities for quiet, remote, and self-reliant recreation, increase user conflicts, and cause an estimated $6.1 million in annual lost economic benefits, yet the Final EIS fails to adequately quantify these net changes at the individual IRA scale, distinguish road types, or account for the long-term degradation of recreation settings and community-dependent economies.

#### Cluster 54, topic 5: recreation, quiet remote, self-reliant recreation, acknowledges rescission, quiet, self-reliant, remote self-reliant, economic

40 sentences; 40 wordings as `leaders`, 40 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain how the rescission is consistent with its own DEIS findings that the action would result in a net economic loss, including an estimated $6.1 million annual decline in recreation revenue, diminished quiet and remote recreation opportunities, and degraded scenic and ecological values, which outweigh the modest and localized timber and mineral benefits.
- `collapse`, run 1: The agency must explain how the rescission is consistent with its own DEIS findings that the action would result in a net economic loss, including an estimated $6.1 million annual decline in recreation revenue, diminished quiet and remote recreation opportunities, and degraded scenic and ecological values, which outweigh the modest and localized timber and mineral benefits.

#### Cluster 84, topic 5: million, million year, year net, present value, net present, year, losses million, million million

52 sentences; 30 wordings as `leaders`, 30 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the agency's own Cost Benefit Analysis fails to demonstrate a net economic benefit for rescinding the Roadless Rule, as projected annual timber revenues of $5.2 to $11.4 million are offset by recreation losses of at least $6.1 million and a 15-year net present value ranging from -$92 million to +$199 million, which does not justify the action or the associated road maintenance costs.
- `collapse`, run 1: The agency must reconcile the proposal with its own Cost Benefit Analysis, which projects timber revenue of $5.2 to $11.4 million a year against recreation losses of at least $6.1 million a year and a 15-year net present value ranging from -$92 million to +$199 million, and explain how an action whose own analysis cannot establish a net benefit is justified.

#### Cluster 87, topic 5: lose receipts, firms, firms lose, concedes firms, small firm, sector nationally, firm sector, receipts

89 sentences; 29 wordings as `leaders`, 29 as `collapse`.

Temperature 0:

- `leaders`, run 1: The regulatory flexibility analysis improperly certifies no significant impact on small entities by spreading projected expenditure losses across every small firm in the sector nationally, rather than examining the specific outfitters, guides, and tour operators who actually hold permits in the affected roadless areas, despite the DEIS acknowledging that some of these firms may lose their receipts entirely.
- `collapse`, run 1: The regulatory flexibility analysis incorrectly certifies no significant impact on small entities by spreading projected expenditure losses across the national average firm, rather than assessing the specific outfitters, guides, and tour operators holding permits in the affected roadless areas, despite the DEIS acknowledging that some of these firms may lose their receipts entirely.

#### Cluster 93, topic 5: losses, recreation, million, estimates, annual, million annual, million annually, recreationists

37 sentences; 28 wordings as `leaders`, 28 as `collapse`.

Temperature 0:

- `leaders`, run 1: The draft EIS estimates annual losses to recreationists at approximately $6.1 million, a figure commenters argue is an underestimate that fails to capture the full value of quiet, remote, and self-reliant recreation, the broader degradation of backcountry character, and the substantial uncertainty regarding the magnitude and location of actual development impacts.
- `collapse`, run 1: The draft EIS estimates annual losses to recreationists at approximately $6.1 million, a figure commenters argue is an underestimate that fails to capture the full magnitude of unknown cumulative impacts, the degradation of quiet and remote recreation, and the broader value of roadless landscapes.

#### Cluster 104, topic 5: revenue, treasury, million, treasury forest, revenue treasury, million year, unlikely, timber industry

26 sentences; 26 wordings as `leaders`, 26 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, even under a full-harvest scenario that the agency itself deems unlikely due to budget, operability, and market constraints.
- `collapse`, run 1: Commenters assert that the projected economic benefits of rescinding the Roadless Rule are disproportionately small, estimating only $5.2 to $11.4 million in annual revenue to the Treasury and Forest Service and $4.6 to $10.6 million to the timber industry, even under a full-harvest scenario that the agency itself deems unlikely due to budget, operability, and market constraints.

#### Cluster 108, topic 5: outdoor, outdoor recreation, economy, gdp, recreation, billion, jobs, bureau

25 sentences; 25 wordings as `leaders`, 25 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that rescinding the Roadless Rule would harm the national and state economies by eliminating the substantial economic output, GDP contribution, and employment generated by outdoor recreation on public lands, which they argue significantly exceeds the economic value of timber production.
- `collapse`, run 1: Commenters assert that rescinding the Roadless Rule would harm the outdoor recreation economy, which they cite as a major national and state-level economic driver generating hundreds of billions of dollars in output and supporting millions of jobs, particularly in rural and gateway communities.

#### Cluster 131, topic 5: visits, substantial visitor, visitors, expenditures, recreation, visitor, receive, annual national

20 sentences; 19 wordings as `leaders`, 19 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS relies on outdated, uncited, or internally inconsistent data to quantify recreation visits and economic benefits in inventoried roadless areas, failing to provide a valid comparison between the substantial visitor spending in affected communities and the projected timber-sector gains.
- `collapse`, run 1: The Draft EIS relies on outdated, uncited, or internally inconsistent data to quantify recreation visits and economic benefits in inventoried roadless areas, failing to provide a valid comparison between the substantial visitor spending in these areas and the projected timber-sector gains.

#### Cluster 140, topic 5: production, total, timber volume, percent total, national production, affected rule, total united, rule percent

48 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the Roadless Rule has negligible economic impact because the agency's own record shows the affected timber volume is less than 0.5% of total U.S. production and oil and gas production from National Forest System lands is only 0.4% of national output, rendering the rule's cost-benefit analysis and claims of significant economic harm unsubstantiated.
- `collapse`, run 1: Commenters assert that the economic benefits of rescinding the Roadless Rule are negligible because the agency's own record indicates that the timber volume affected is less than 0.5% of total U.S. production and oil and gas production from National Forest System lands is only about 0.4% of national production, making the projected revenue gains insufficient to justify the rule's removal.

#### Cluster 145, topic 5: setting classes, classes likely, recreation section, classes, section acknowledges, likely affected, setting, percent setting

28 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: The draft EIS fails to adequately assess the long-term, cumulative degradation of primitive and semi-primitive recreation settings, as it acknowledges that a majority of affected areas are in these sensitive classes and that the magnitude of losses is unknown, yet relies on single-year estimates that ignore the permanent and accumulating nature of road construction.
- `collapse`, run 1: The agency's own analysis acknowledges that the majority of affected roadless areas are primitive or semi-primitive settings, that a significant portion of these settings are more likely to be affected, and that the magnitude of resulting losses is unknown, yet it relies on a single-year estimate to justify the permanent, cumulative degradation of these recreation resources.

#### Cluster 161, topic 5: sawtimber harvest, sawtimber, harvest, increase, alternatives increase, increase national, harvest percent, increase sawtimber

15 sentences; 14 wordings as `leaders`, 14 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS projects that rescission would increase national sawtimber harvest by 4–10% and frames this as a benefit, but fails to adequately analyze market absorption, permanent job creation, or the simultaneous operational impact of this increase alongside other statutory mandates on the same lands.
- `collapse`, run 1: The DEIS inadequately analyzes the cumulative and concurrent impacts of the projected 4–10% increase in national sawtimber harvest, the availability of approximately 5 million acres for commercial logging, and the statutory mandates for increased harvest, failing to address market absorption, permanent job creation, and the destabilization of carbon sinks.

#### Cluster 172, topic 5: timber, timber industry, industry, harvest, timber harvest, million, revenue, generating

14 sentences; 13 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own analysis indicates that rescinding the 2001 Roadless Rule would yield only modest, uncertain economic benefits—specifically a 5-10% increase in national timber harvest volume generating approximately $4.6 to $11 million in annual revenue—while removing protections from 58.5 million acres of roadless area.
- `collapse`, run 1: The agency’s own analysis indicates that rescinding the 2001 Roadless Rule would yield only modest, uncertain economic benefits—specifically a 5–10% increase in national timber harvest volume generating approximately $4.6–$11 million in annual revenue—while removing protections from 58.5 million acres of roadless area.

#### Cluster 185, topic 5: sales, timber sales, tongass, timber, taxpayers, revenue, losing, million year

12 sentences; 11 wordings as `leaders`, 11 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that timber sales in roadless areas, particularly in the Tongass National Forest, consistently result in significant net financial losses for federal taxpayers, with administrative and road construction costs far exceeding revenue, meaning the rescission of the Roadless Rule would increase costs without providing material financial benefit.
- `collapse`, run 1: Commenters assert that opening roadless areas to timber harvest will result in significant net financial losses for federal taxpayers, citing historical data from the Tongass National Forest and other units where the costs of road construction, sale preparation, and administration have consistently exceeded timber revenue, often by wide margins.

#### Cluster 195, topic 5: quantity, board feet, million board, beginning, big beautiful, directs forest, board, sold

14 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS fails to integrate the statutory timber sales mandate in the One Big Beautiful Bill Act with the National Forest Management Act’s sustainability requirements, creating a conflict between the required annual harvest increases and the legal limits on timber production.
- `collapse`, run 1: The DEIS fails to integrate the statutory timber harvest mandates of the One Big Beautiful Bill Act and Executive Order 14225 with the National Forest Management Act’s sustainability requirements, creating a conflict between the projected increases in timber production and the legal limits on allowable production.

#### Cluster 23, topic 6: billion, maintenance, deferred, backlog, deferred maintenance, billion deferred, maintenance backlog, bridges

95 sentences; 74 wordings as `leaders`, 76 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Forest Service already faces a multi-billion dollar deferred maintenance backlog on its existing road system, which is severely underfunded and understaffed, making the addition of new roads into inventoried roadless areas fiscally irresponsible and likely to exacerbate this existing burden.
- `collapse`, run 1: The Forest Service already faces a multi-billion dollar deferred maintenance backlog for its existing road system, which is severely underfunded and understaffed, making the addition of new roads into inventoried roadless areas fiscally irresponsible and environmentally damaging.

#### Cluster 37, topic 6: reconcile proposal, agency reconcile, expanding road, expanding, reconcile, net benefit, explain, establish net

60 sentences; 47 wordings as `leaders`, 47 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must reconcile the proposal with its own Cost Benefit Analysis, which cannot establish a net benefit, and explain how expanding a road system already carrying a significant maintenance backlog serves the public interest.
- `collapse`, run 1: The agency must reconcile the proposal with its own Cost Benefit Analysis, which cannot establish a net benefit, and explain on the record how expanding a road system already carrying a multi-billion-dollar maintenance backlog serves the public interest.

#### Cluster 61, topic 6: billion, backlog, funding, deferred maintenance, maintenance, maintenance backlog, deferred, bridges

47 sentences; 37 wordings as `leaders`, 37 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency cannot afford to expand its road network because it already faces a multibillion-dollar deferred maintenance backlog and annual appropriations that cover only a fraction of the estimated $1.6 billion needed to keep existing roads in good repair.
- `collapse`, run 1: The agency cannot afford to build new roads because it already faces a multibillion-dollar deferred maintenance backlog and annual appropriations that cover only a fraction of the estimated $1.6 billion needed to keep the existing road system in good repair.

#### Cluster 67, topic 6: carrying billion, carrying, road carrying, billion maintenance, backlog, expanding road, maintenance backlog, billion

64 sentences; 35 wordings as `leaders`, 35 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters contend that the rescission is unjustified because the agency's own Cost Benefit Analysis fails to establish a net benefit, yet the proposal would expand a road system already burdened by a $6.9 billion maintenance backlog and limited annual budget.
- `collapse`, run 1: The agency must explain how rescission is justified when its own Cost Benefit Analysis cannot establish a net benefit, and how expanding a road system already carrying a $6.9 billion maintenance backlog is fiscally responsible.

#### Cluster 78, topic 6: revenue, maintaining new, cover, cover costs, maintaining, sufficient cover, related project, costs constructing

36 sentences; 31 wordings as `leaders`, 31 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS acknowledges that projected timber and resource extraction revenues are insufficient to cover the costs of constructing and maintaining new roads, creating a net fiscal deficit that would require taxpayer subsidies to address the existing deferred maintenance backlog.
- `collapse`, run 1: The DEIS acknowledges that projected timber and resource extraction revenues are insufficient to cover the costs of constructing and maintaining new roads, creating a net fiscal deficit that would burden taxpayers and exacerbate the existing road maintenance backlog.

#### Cluster 80, topic 6: reconcile proposal, agency reconcile, reconcile, net benefit, benefit, proposal, explain action, analysis explain

34 sentences; 30 wordings as `leaders`, 30 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must reconcile the proposal with its own Cost Benefit Analysis and explain how an action whose own numbers cannot establish a net benefit justifies expanding a system with a significant deferred maintenance deficit.
- `collapse`, run 1: The agency must reconcile the proposal with its own Cost Benefit Analysis and explain on the record how an action whose numbers cannot demonstrate a net benefit justifies expanding a system with an unmet maintenance deficit.

#### Cluster 95, topic 6: maintenance, maintenance backlog, backlog, billion, deferred maintenance, deferred, roads, road

30 sentences; 27 wordings as `leaders`, 28 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission would exacerbate the Forest Service's existing fiscal crisis by adding new road construction and recurring maintenance costs to a system already burdened by a multi-billion dollar deferred maintenance backlog, while projected revenues from extractive activities are insufficient to cover these expenses and appropriated funding has significantly declined.
- `collapse`, run 1: The rescission would exacerbate the Forest Service's existing multi-billion dollar deferred maintenance backlog and declining funding levels, as the agency acknowledges that anticipated revenues from extractive activities would not be sufficient to cover the costs of constructing and maintaining the new roads.

#### Cluster 98, topic 6: roads, taxpayer, maintain, maintenance, maintain roads, taxpayers, maintain existing, rule

28 sentences; 27 wordings as `leaders`, 27 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule would impose a significant fiscal burden on taxpayers by requiring the construction and maintenance of new roads in remote, rugged terrain, exacerbating the Forest Service's existing multi-billion dollar maintenance backlog and diverting limited resources from critical needs such as wildfire mitigation, prescribed burns, and the repair of current infrastructure.
- `collapse`, run 1: Rescinding the Roadless Rule would impose a massive fiscal burden on taxpayers by forcing the Forest Service to construct and maintain new roads in remote, rugged terrain, exacerbating an existing multi-billion dollar maintenance backlog and diverting limited funds from critical wildfire mitigation, staff training, and the repair of current infrastructure.

#### Cluster 120, topic 6: net, million year, net benefit, benefit, million, year net, expanding, losses million

116 sentences; 21 wordings as `leaders`, 21 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must reconcile the proposal with its own Cost Benefit Analysis, which projects timber revenue of $5.2 to $11.4 million a year against recreation losses of at least $6.1 million a year and a net present value spanning -$92 million to +$199 million, and explain how an action whose own analysis cannot establish a net benefit justifies expanding a road system already carrying a $6.9 billion maintenance backlog.
- `collapse`, run 1: The agency must reconcile the proposal with its own Cost Benefit Analysis, which projects timber revenue of $5.2 to $11.4 million annually against recreation losses of at least $6.1 million annually and a net present value ranging from -$92 million to +$199 million, and explain how an action that cannot establish a net benefit justifies expanding a road system already carrying a $6.9 billion maintenance backlog.

#### Cluster 124, topic 6: maintenance management, mileage, management costs, costs likely, road mileage, deferred maintenance, deferred, likely increase

45 sentences; 20 wordings as `leaders`, 20 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own Draft Environmental Impact Statement concludes that rescinding the rule will likely increase road mileage, deferred maintenance, and management costs, yet the proposal identifies no funding source to cover these increased expenses, which will ultimately fall on taxpayers.
- `collapse`, run 1: The agency's own Draft Environmental Impact Statement projects that rescinding the rule will increase road mileage, deferred maintenance, and long-term management costs, yet the proposal identifies no funding source to cover these increased expenses, which would ultimately fall on taxpayers.

#### Cluster 127, topic 6: exceed million, impacts exceed, arithmetic, exceed, folder docket, million, file folder, folder

22 sentences; 19 wordings as `leaders`, 19 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rule fails to meet the reasoned rulemaking standards of Executive Order 12866 because its cost-benefit analysis is internally inconsistent, lacking the arithmetic to reconcile quantified annual line items under $22 million with a claimed impact exceeding $100 million, and was not properly placed on the docket for public review.
- `collapse`, run 1: The rule fails to meet the reasoned rulemaking standards of Executive Order 12866 because its cost-benefit analysis is internally inconsistent, lacking the arithmetic to reconcile quantified annual line items under $22 million with a claimed impact exceeding $100 million, and was not properly placed on the docket for public review.

#### Cluster 174, topic 6: source new, projected change, funding source, funding, maintenance, construction maintenance, backlog, new road

28 sentences; 13 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must identify the specific funding source for new road construction and maintenance enabled by the rescission and state the projected change in the deferred maintenance backlog on the record before finalizing the rule.
- `collapse`, run 1: The agency must identify the specific funding source for new road construction and maintenance enabled by the rescission and state the projected change in the deferred maintenance backlog.

#### Cluster 183, topic 6: costs, analysis account, roads, maintaining, maintenance, long-term, quantify long-term, costs maintaining

12 sentences; 12 wordings as `leaders`, 12 as `collapse`.

Temperature 0:

- `leaders`, run 1: The analysis must quantify the full lifecycle costs of new roads, including construction, maintenance, decommissioning, and associated environmental impacts, and identify the specific funding sources or responsible parties for these expenses.
- `collapse`, run 1: The draft EIS must quantify the full lifecycle costs of new and reopened roads—including construction, long-term maintenance, decommissioning, and downstream environmental impacts—over extended timeframes, and identify specific funding sources to demonstrate that the public benefits justify these costs.

#### Cluster 188, topic 6: restate, present value, net present, agency place, cost, cost column, column, arithmetic

30 sentences; 11 wordings as `leaders`, 11 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must place the Cost Benefit Analysis on the public docket, restate the net present value with its own quantified road construction, maintenance, and fuels costs included in the cost column, and show the arithmetic behind the claim that impacts could exceed $100 million.
- `collapse`, run 1: The agency must place the Cost Benefit Analysis on the public docket, restate the net present value with its own quantified road construction, maintenance, and fuels costs included in the cost column, and show the arithmetic behind the claim that impacts could exceed $100 million.

#### Cluster 204, topic 6: mile, document quantifies, cost column, column, excludes, costs, cost, quantifies

12 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's cost-benefit analysis and DEIS fail to adequately account for the full financial burden of road development, specifically omitting or underestimating the high construction costs (ranging from $80,000 to $500,000+ per mile, particularly in remote areas like Alaska), as well as ongoing maintenance and fuel treatment expenses, thereby presenting an incomplete picture of long-term fiscal sustainability.
- `collapse`, run 1: The agency's cost-benefit analysis and DEIS fail to adequately account for the full financial burden of road development, specifically omitting or underestimating the high per-mile construction costs (ranging from $80,000 to over $500,000 in remote areas like Alaska), ongoing maintenance expenses, and fuel treatment costs, thereby presenting an incomplete picture of the long-term fiscal sustainability and taxpayer impact of expanding the road system.

#### Cluster 8, topic 7: targeted, wildfire, exceptions, rule, narrower, narrowly, interface, instead

128 sentences; 126 wordings as `leaders`, 126 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must demonstrate that a full nationwide rescission of the 2001 Roadless Rule is necessary to address wildfire and forest-health needs, rather than relying on existing exceptions or analyzing narrower, targeted alternatives such as wildland-urban interface treatments, state-specific rulemaking, or streamlined approval processes that preserve national protections.
- `collapse`, run 1: Commenters assert that a full nationwide rescission of the 2001 Roadless Rule is unnecessarily broad and not narrowly tailored to the stated wildfire and forest-health needs, which can be addressed through existing exceptions, targeted amendments, or state-specific rulemaking. They request that the agency analyze and adopt narrower alternatives that retain national protections while allowing for targeted fuels treatments, particularly in the wildland-urban interface, and that it demonstrate why such targeted measures are insufficient before eliminating protections across all inventoried roadless acres.

#### Cluster 53, topic 7: small-diameter, cutting, uncharacteristic, uncharacteristic wildfire, wildfire effects, small-diameter timber, risk uncharacteristic, reduce

45 sentences; 41 wordings as `leaders`, 41 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the 2001 Roadless Rule already authorizes the cutting of generally small-diameter timber to reduce the risk of uncharacteristic wildfire effects and the construction of roads to address imminent fire threats, rendering the rescission unnecessary for fuel reduction and public safety purposes.
- `collapse`, run 1: Commenters assert that the 2001 Roadless Rule already explicitly authorizes the cutting of generally small-diameter timber to reduce the risk of uncharacteristic wildfire effects and the construction of roads to address imminent fire threats, rendering the rescission unnecessary for fuel reduction and ecosystem management.

#### Cluster 60, topic 7: rule, roadless, wildfire, fuel, management, roadless rule, allows, rule allows

38 sentences; 38 wordings as `leaders`, 38 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the 2001 Roadless Rule already contains sufficient exceptions for wildfire mitigation, fuel reduction, and forest health management, and challenge the agency to identify specific projects that the rule has actually prevented or delayed, arguing that the rule does not block these necessary actions.
- `collapse`, run 1: Commenters assert that the 2001 Roadless Rule already contains sufficient exceptions for wildfire mitigation, fuel reduction, and forest health management, and challenge the agency to identify specific projects that the rule has actually prevented or delayed, arguing that the rule does not block these necessary actions.

#### Cluster 86, topic 7: exceptions, outstanding, reserved, health safety, necessary public, construction necessary, rights, discretionary

53 sentences; 29 wordings as `leaders`, 30 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the 2001 Roadless Rule already contains specific exceptions for public health, safety, reserved rights, and other circumstances, and that the agency’s own record concedes there is no national-level tracking of their use or burden. They argue that characterizing the infrequent or inconsistent use of these existing exceptions as evidence of rule failure is unsupported, and that the appropriate remedy for slow or inconsistent review is to streamline the exception process rather than rescind the rule.
- `collapse`, run 1: The 2001 Roadless Rule already contains specific exceptions for public health and safety, reserved or outstanding rights, and other circumstances, yet the agency’s record lacks national-level tracking data to substantiate the claim that these exceptions were used infrequently or inconsistently due to administrative burden.

#### Cluster 88, topic 7: exceptions, rule contains, cfr, contains, health safety, safety, rule, contains exceptions

29 sentences; 29 wordings as `leaders`, 29 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the 2001 Roadless Rule already contains sufficient exceptions under 36 CFR §§ 294.12 and 294.13 to address wildfire mitigation, public safety, and forest health needs, making the rescission unnecessary and the stated intent to alleviate local decision-making disingenuous.
- `collapse`, run 1: Commenters assert that the 2001 Roadless Rule already contains sufficient exceptions under 36 CFR §§ 294.12 and 294.13 to address wildfire mitigation, public safety, and forest health needs, making the rescission unnecessary and the stated intent to alleviate local decision-making disingenuous.

#### Cluster 89, topic 7: flexibility, wildfire, wildfire risk, need, management, risk, management flexibility, disease

31 sentences; 29 wordings as `leaders`, 29 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Forest Service has not quantified the nationwide cumulative impacts of timber harvest, road construction, sedimentation, and fragmentation resulting from the rescission, nor has it demonstrated that the proposed action is the most effective means to address wildfire risk, insect and disease infestations, and wildland-urban interface protection, particularly given that the 2001 Rule already permits local management flexibility for these purposes and that the proposal fails to adequately account for climate change as a primary driver of these conditions.
- `collapse`, run 1: The Forest Service has not quantified the nationwide cumulative impacts of timber harvest, road construction, sedimentation, and fragmentation resulting from the rescission, nor has it demonstrated that the proposed local management flexibility is necessary or the most effective means to address wildfire risk, insect and disease infestations, and wildland-urban interface protection, given that the 2001 Roadless Rule already permits such management activities and that the action would strip protection from a significant portion of roadless areas while failing to adequately address climate change.

#### Cluster 96, topic 7: enforceable, provision, single enforceable, plans address, enforceable provision, plans, forest plans, asserts

44 sentences; 27 wordings as `leaders`, 27 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS asserts that existing forest plans will protect municipal drinking water sources after rescission, but it fails to identify a single enforceable provision in any forest plan that is equivalent to the protections currently codified at 36 CFR 294.12 and 294.13.
- `collapse`, run 1: The DEIS asserts that existing forest plans will protect municipal drinking water sources after rescission, but it fails to identify a single enforceable provision in any forest plan that is equivalent to the protections currently codified at 36 CFR 294.12 and 294.13.

#### Cluster 107, topic 7: enforceable, provision, single enforceable, cfr, plans, forest plans, equivalent, plans substitute

28 sentences; 25 wordings as `leaders`, 25 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency asserts that case-by-case forest planning will substitute for the durable protections codified at 36 CFR 294.12 and 294.13, but the DEIS fails to identify a single enforceable provision in any existing forest plan that is equivalent to those standards, nor does it provide the required forest-by-forest accounting of such equivalents.
- `collapse`, run 1: The agency asserts that case-by-case forest planning will substitute for the durable protections codified at 36 CFR 294.12 and 294.13, but the DEIS fails to identify a single enforceable provision in any existing forest plan that is equivalent to those standards, nor does it provide the required forest-by-forest accounting of such equivalents.

#### Cluster 119, topic 7: management plan, forest vegetation, health carbon, vegetation health, implications forest, percent old-growth, percent, mature

35 sentences; 21 wordings as `leaders`, 21 as `collapse`.

Temperature 0:

- `leaders`, run 1: The rescission would open timberland where the agency's own data show that old and mature stands constitute the overwhelming majority of the forest, yet the document identifies no old-growth-specific protection or safeguards beyond general land management plan compliance before these stands could be harvested.
- `collapse`, run 1: The draft EIS identifies no old-growth-specific safeguards beyond general land management plan compliance for the operable areas most likely to be affected by timber harvest, where the agency's own data show that approximately 11-16 percent is old-growth forest and 54-63 percent is mature forest.

#### Cluster 121, topic 7: sustained-yield, multiple-use sustained-yield, multiple-use, multiple use, act, management act, forest, sustained-yield act

24 sentences; 20 wordings as `leaders`, 20 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the rescission violates the National Forest Management Act, the Multiple-Use Sustained-Yield Act, and the Organic Act, which mandate that land management plans balance multiple uses—including timber, wildlife, recreation, watershed, and range—without prioritizing maximum economic return, and require the Forest Service to ensure long-term stewardship of soil, water, and other resources through interdisciplinary planning and coordination of these values.
- `collapse`, run 1: Commenters assert that the rescission violates the National Forest Management Act, the Multiple-Use Sustained-Yield Act, and the Organic Act, which mandate that land management plans balance multiple uses—including timber, wildlife, recreation, range, and watershed—without prioritizing maximum dollar return, and that the agency must adhere to these statutory planning requirements and interdisciplinary coordination rather than relying solely on broad administrative authority.

#### Cluster 125, topic 7: imminent, imminent threat, health safety, public health, protect public, threat, safety, catastrophic event

21 sentences; 19 wordings as `leaders`, 19 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the existing regulatory exceptions in 36 CFR 294.12 and 294.13, particularly those for imminent threats to public health and safety from fire, flood, or other catastrophic events, already authorize the construction, reconstruction, and maintenance of roads and associated fuel treatments, rendering the rescission of the 2001 Roadless Rule unnecessary.
- `collapse`, run 1: Commenters assert that the existing regulatory exceptions in 36 CFR 294.12 and 294.13, particularly those for imminent threats to public health and safety from fire, flood, or other catastrophic events, already authorize the construction, reconstruction, and maintenance of roads and associated fuel treatments, rendering the rescission of the 2001 Roadless Rule unnecessary.

#### Cluster 148, topic 7: forest health, health, findings rule, insect, agency reconcile, reconcile, fuel, lower

19 sentences; 17 wordings as `leaders`, 17 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must reconcile the forest health rationale for rescission with its own findings that the rule did not meaningfully constrain fuel treatments and that insect and disease risk in roadless areas is often lower than or similar to managed lands, explaining specifically how the rule caused the described forest health harm.
- `collapse`, run 1: The agency must reconcile the forest health rationale for rescission with its own findings that the rule did not meaningfully constrain fuel treatments and that roadless areas often carry lower or similar insect and disease risk than managed lands, explaining specifically how the rule caused the described forest health harm.

#### Cluster 162, topic 7: land management, management plans, plans, asserts local, management, proposal asserts, asserts, planning

18 sentences; 14 wordings as `leaders`, 14 as `collapse`.

Temperature 0:

- `leaders`, run 1: The proposal asserts that local land management planning adequately protects roadless values, but commenters argue that local planning has historically failed to prevent the incremental degradation of these nationally significant areas, and that the discretionary nature of individual plans does not provide the assured, uniform conservation standards required to protect ecological integrity, water sources, and wildlife.
- `collapse`, run 1: The proposal asserts that local land management planning adequately protects roadless values, but commenters argue that local planning is a discretionary process that has historically failed to prevent the incremental degradation of these nationally significant areas, and that a blanket rescission ignores regional differences in conservation value and risk.

#### Cluster 189, topic 7: cfr municipal, identify forest, plan provisions, municipal watersheds, provisions, forest forest, municipal, agency identify

26 sentences; 11 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must identify, forest by forest, the specific land management plan provisions that are the functional equivalent of the municipal watershed protections in 36 CFR 294.12 and 294.13, and place that identification in the record for public review before any final decision is made.
- `collapse`, run 1: The agency must identify, forest by forest, the specific land management plan provisions that constitute the functional equivalent of the municipal watershed protections in 36 CFR 294.12 and 294.13, and place that identification in the record for public and judicial review, rather than relying on a general assertion that planning processes provide equivalent protection.

#### Cluster 193, topic 7: contributed, lack active, rule limited, active management, active, forest health, asserts roadless, contributed lack

24 sentences; 11 wordings as `leaders`, 12 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS asserts that the 2001 Roadless Rule limited vegetation management and contributed to forest health challenges, but it fails to provide the necessary quantitative data, such as pre- and post-2001 comparisons, roadless-specific incidence statistics, or controls for climate and disturbance trends, to substantiate this causal claim.
- `collapse`, run 1: The DEIS asserts that the 2001 Roadless Rule limited active vegetation management and contributed to forest health challenges, but it provides no data, acreage figures, or comparative analysis to substantiate this causal link or distinguish the Rule's effects from other documented climate and disturbance trends.

#### Cluster 199, topic 7: community wildfire, leases, burdens, wildfire protection, health safety, mineral, public health, existing

10 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must identify and quantify, on the record, which specific permitting and administrative burdens are not already addressed by the rule's existing exceptions for public health and safety, existing mineral leases, and community wildfire protection, to justify the necessity of full rescission.
- `collapse`, run 1: The agency must identify and quantify, on the record, which specific permitting and administrative burdens are not already addressed by the rule's existing exceptions for public health and safety, existing mineral leases, and community wildfire protection, to justify the necessity of full rescission.

#### Cluster 5, topic 8: species, habitat, critical habitats, endangered, habitats, critical, threatened, affect

201 sentences; 190 wordings as `leaders`, 190 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must complete formal Section 7 consultation with USFWS and NMFS, prepare a Biological Opinion, and conduct a supplemental environmental analysis that addresses the likely adverse effects on 327 ESA-listed species and 71 designated critical habitats, including specific impacts to habitat connectivity, fragmentation, and water quality, before finalizing the rescission.
- `collapse`, run 1: The rescission of the Roadless Rule constitutes a federal action that is likely to adversely affect over 300 threatened and endangered species and 71 designated critical habitats by fragmenting intact ecosystems, degrading habitat connectivity, and increasing human disturbance, yet the agency has not completed the required Section 7 consultation or provided a Biological Opinion to address these impacts.

#### Cluster 6, topic 8: severity, natureserve, ira, pop, decline severity, pop decline, threat, myotis

171 sentences; 170 wordings as `leaders`, 170 as `collapse`.

Temperature 0:

- `leaders`, run 1: The programmatic DEIS fails to meet NEPA's hard-look and site-specific analysis requirements by treating distinct inventoried roadless areas as interchangeable, thereby omitting necessary individualized assessments of how road construction and other activities enabled by rescission impact specific watersheds, ecological systems, and listed or sensitive species within each area.
- `collapse`, run 1: The programmatic DEIS fails to meet NEPA's hard-look and site-specific analysis requirements by treating distinct inventoried roadless areas as interchangeable, thereby omitting necessary individualized assessments of how road construction and other activities enabled by rescission impact specific watersheds, ecological systems, and listed or sensitive species within each area.

#### Cluster 50, topic 8: fragmentation range, range million, agency apply, cited fragmentation, apply cited, apply, range, fragmentation

49 sentences; 41 wordings as `leaders`, 41 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency has failed to apply the cited 13 to 75 percent fragmentation range to the full 40.1 million acres of potentially affected environment, leaving a critical gap in the analysis of projected biodiversity losses, habitat degradation, and impacts to sensitive species and watersheds that prevents the public and decision-makers from evaluating the actual environmental consequences of the rescission.
- `collapse`, run 1: The agency has failed to apply the cited 13 to 75 percent habitat fragmentation range to the full 40.1 million acres of potentially affected environment, leaving a critical gap in the environmental analysis that prevents decision-makers and the public from understanding the projected impacts on biodiversity, wildlife, watersheds, and habitat integrity.

#### Cluster 85, topic 8: adversely affect, likely adversely, adversely, critical habitats, affect, species, species designated, endangered

32 sentences; 29 wordings as `leaders`, 29 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own preliminary biological assessment and Draft EIS determine that rescinding the 2001 Roadless Rule is likely to adversely affect 327 threatened and endangered species and 71 designated critical habitats, yet the agency has not completed the required Section 7 biological opinions or fully assessed the specific impacts on these protected populations and habitats.
- `collapse`, run 1: The agency's own preliminary biological assessment and DEIS determine that rescinding the Roadless Rule is likely to adversely affect 327 threatened and endangered species and 71 designated critical habitats, yet the agency has not completed the required Section 7 biological opinions or fully assessed the specific impacts on these protected populations.

#### Cluster 97, topic 8: alternatives, invasive, mapped, invasive plant, plant, deis, species, alternative

29 sentences; 27 wordings as `leaders`, 27 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS relies on a mapped-occurrence layer that cannot identify where infestations are absent, yet uses the resulting 'less than one percent' figure to support a minimal-effects finding, while simultaneously conceding that unmapped populations likely exist and that increased ground disturbance under Alternatives 2 and 3 could potentially increase the extent or number of invasive plant species.
- `collapse`, run 1: The DEIS relies on a mapped-occurrence layer that cannot identify where infestations are absent, yet uses the resulting 'less than one percent' figure to support a minimal-effects finding, while simultaneously conceding that unmapped populations likely exist and that the proposed alternatives could increase the extent or number of invasive plant species.

#### Cluster 112, topic 8: center biological, biological diversity, species, diversity, protected rivers, endangered, miles protected, habitat nearly

25 sentences; 24 wordings as `leaders`, 24 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescinding the Roadless Rule would expose approximately 7.4 million acres of designated critical habitat and nearly 1,800 miles of protected rivers and streams to fragmentation and pollution, thereby threatening the survival of more than 400 threatened and endangered species, including grizzly bears, Canada lynx, wolverines, salmon, and the Mexican spotted owl.
- `collapse`, run 1: Rescinding the Roadless Rule would expose approximately 7.4 million acres of designated critical habitat and nearly 1,800 miles of protected rivers and streams to new road construction, thereby fragmenting habitat and increasing the risk of decline or extinction for more than 400 threatened and endangered species, including grizzly bears, Canada lynx, wolverines, salmon, and the Mexican spotted owl.

#### Cluster 132, topic 8: critical habitats, adversely affect, adversely, affect, habitats, likely adversely, species, critical

19 sentences; 18 wordings as `leaders`, 18 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS concludes that the proposed action is likely to adversely affect 327 federally listed threatened and endangered species and 71 designated critical habitats.
- `collapse`, run 1: The Draft EIS concludes that the proposed action is likely to adversely affect 327 federally listed threatened and endangered species and 71 designated critical habitats.

#### Cluster 176, topic 8: species, adversely affect, endangered species, adversely, endangered, threatened endangered, affect threatened, affect

42 sentences; 13 wordings as `leaders`, 18 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own biological assessment and DEIS determine that rescinding the Roadless Rule is likely to adversely affect 327 threatened and endangered species, 71 designated critical habitats, and 3,409 sensitive species, yet the agency has not provided the required species-specific analysis of how the action impacts habitat, movement, reproduction, and long-term viability for these populations.
- `collapse`, run 1: The agency's own biological assessment and DEIS conclude that rescinding the Roadless Rule is likely to adversely affect 327 threatened and endangered species, 71 designated critical habitats, and thousands of sensitive species, yet the agency has not provided the required species-specific analysis of how the loss of protections will impact habitat, movement, reproduction, and long-term viability.

#### Cluster 192, topic 8: protections million, million acres, acres public, acres, million, acres national, public, alongside proposed

11 sentences; 11 wordings as `leaders`, 11 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft Environmental Impact Statement fails to adequately assess the reasonably foreseeable national and regional environmental effects of eliminating protections for approximately 45 million acres of intact backcountry forests, including the cumulative loss of protected public lands and the lack of specific projections for the potentially affected environment.
- `collapse`, run 1: The Draft Environmental Impact Statement fails to adequately assess the reasonably foreseeable national and regional environmental effects of eliminating protections for approximately 45 million acres of public land, including the cumulative loss of protected status and the lack of specific projections for the potentially affected environment.

#### Cluster 24, topic 9: state-specific, colorado, idaho, idaho colorado, rules, state-specific roadless, roadless rules, petition

77 sentences; 74 wordings as `leaders`, 74 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain why it is rescinding the 2001 Roadless Rule nationwide when the existing framework already provides a proven, lawful mechanism for state-specific tailoring through the 5 U.S.C. 553(e) and 7 CFR 1.28 petition process, as demonstrated by the retained rules for Idaho and Colorado. Commenters argue that this available pathway for local flexibility renders a wholesale repeal unnecessary and inconsistent with the agency's own acknowledgment that place-based management is superior to a national blanket approach.
- `collapse`, run 1: The agency must explain why it is rescinding the 2001 Roadless Rule nationwide when the existing framework already provides a proven, lawful mechanism for state-specific tailoring through the 5 U.S.C. 553(e) and 7 CFR 1.28 petition process, as demonstrated by the retained rules for Idaho and Colorado. Commenters argue that this available pathway for local flexibility renders a wholesale repeal unnecessary and inconsistent with the agency's own acknowledgment that place-based management is superior to a national blanket approach.

#### Cluster 72, topic 9: local, local forest, officials, burden return, decisionmaking, reduce regulatory, decision-making, service officials

36 sentences; 33 wordings as `leaders`, 33 as `collapse`.

Temperature 0:

- `leaders`, run 1: The proposal claims to return decision-making authority to local Forest Service officials to reduce regulatory burden, but commenters argue this is a false premise that ignores the original rule's creation due to local planning failures, understaffed local agencies, and the DEIS's admission that timber extraction and deregulatory executive orders are the true primary motivators.
- `collapse`, run 1: The proposal claims to return decision-making authority to local Forest Service officials, but commenters argue this is a false premise that ignores the original Roadless Rule's creation due to local planning failures, while simultaneously imposing increased burdens on understaffed local agencies, tribal resources, and public involvement processes without demonstrating that existing authorities are inadequate.

#### Cluster 74, topic 9: one-size-fits-all nationwide, inflexible one-size-fits-all, inflexible, rulemaking approach, one-size-fits-all, nationwide rulemaking, rule inflexible, approach

75 sentences; 32 wordings as `leaders`, 32 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency's own record documents that its prior rejection of the Roadless Rule as an 'inflexible one-size-fits-all' approach led to a state-by-state framework that the Ninth Circuit already reviewed and found legally deficient, raising the question of whether the current proposal repeats a legally insufficient alternative.
- `collapse`, run 1: The agency's own record documents its prior rejection of the Roadless Rule's 'inflexible one-size-fits-all' approach and its subsequent attempt to substitute state-specific rules, an approach the Ninth Circuit already reviewed and found legally deficient.

#### Cluster 114, topic 9: roadless values, nationally significant, deficiencies, decision-making, incrementally, ninth circuit, ninth, local decision-making

23 sentences; 23 wordings as `leaders`, 23 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must explain how this proposal avoids the legal deficiencies the Ninth Circuit identified in the prior state-specific framework and reconcile its current reliance on local decision-making with its own prior finding that such incremental, localized processes erode nationally significant roadless values.
- `collapse`, run 1: The agency must explain how this proposal avoids the legal deficiencies the Ninth Circuit identified in the prior state-specific framework and reconcile its current reliance on local decision-making with its own prior finding that such incremental, localized processes erode nationally significant roadless values.

#### Cluster 133, topic 9: standard, national conservation, conservation standard, national standard, consistent national, plan plan, plan, decisions

18 sentences; 18 wordings as `leaders`, 18 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters contend that rescinding the 2001 Roadless Rule replaces a durable, consistent national conservation standard with fragmented, case-by-case forest-level planning, which exposes remaining intact roadless areas to inconsistent management, political pressure, and long-term ecological degradation. They argue this shift does not eliminate regulatory burden but instead invites inconsistent outcomes, increased litigation, and the potential erosion of protections over time, without demonstrating that local decision-making better protects these finite national resources.
- `collapse`, run 1: Replacing the consistent national conservation standard of 36 CFR Part 294, Subpart B with case-by-case, forest-level planning removes a durable baseline, exposing inventoried roadless areas to inconsistent management, political pressure, and long-term ecological degradation that varies by administration and location.

#### Cluster 27, topic 10: amendments, plan amendments, harvest, amendments revisions, revisions, timber harvest, plans, construction allowed

77 sentences; 61 wordings as `leaders`, 61 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency must analyze the reasonably foreseeable environmental and economic impacts of future land management plan amendments that could expand areas for timber harvest and road construction, rather than declaring those downstream changes beyond the scope of this rulemaking while simultaneously soliciting public comment on them.
- `collapse`, run 1: The agency must analyze the reasonably foreseeable environmental and economic impacts of future land management plan amendments that could expand areas for timber harvest and road construction, rather than declaring those downstream changes beyond the scope of this rulemaking while simultaneously soliciting public comment on them.

#### Cluster 32, topic 10: plans allow, plans, million acres, permanent, million, acres, allow permanent, allow

56 sentences; 53 wordings as `leaders`, 53 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the agency's own analysis identifies approximately 18.2 million acres (45.5% of the potentially affected environment) where current land management plans allow permanent road construction that the 2001 Roadless Rule currently prohibits, and an additional 11.3 million acres for temporary roads, raising concerns about the scale of potential road construction, the lack of specific projections for road density or habitat connectivity, and the reliance on older planning regulations that may lack specific direction for inventoried roadless areas.
- `collapse`, run 1: The agency's own analysis indicates that rescission would permit permanent road construction across approximately 18.2 million acres (45.5% of the potentially affected environment) and temporary roads across 11.3 million acres, a scale that contradicts the characterization of impacts as modest and localized, and raises questions about the adequacy of the environmental review given that many underlying land management plans were developed under older regulations and lack specific direction for roadless areas.

#### Cluster 103, topic 10: million acres, acres, million, expand, permanent, rescission expand, approximately million, forested

28 sentences; 26 wordings as `leaders`, 26 as `collapse`.

Temperature 0:

- `leaders`, run 1: Rescission would expand opportunities for new permanent road construction on approximately 18.2 million acres and active timber harvest on approximately 4.8 million acres of forested inventoried roadless areas where existing forest plans currently allow such management.
- `collapse`, run 1: The agency's own analysis estimates that rescission would open approximately 18.2 million acres to new permanent road construction and expand active timber management opportunities on approximately 4.8 million acres of forested roadless areas.

#### Cluster 173, topic 10: acknowledges rescission, coal, gas coal, opportunities, oil gas, mineral energy, oil, energy

13 sentences; 13 wordings as `leaders`, 13 as `collapse`.

Temperature 0:

- `leaders`, run 1: The proposal acknowledges that rescission would expand opportunities for road construction, timber harvesting, vegetation management, and mineral or energy development in inventoried roadless areas, exposing millions of acres to increased development and management flexibility.
- `collapse`, run 1: The proposal acknowledges that rescission would create additional opportunities for road construction, timber harvesting, vegetation management, and mineral or energy development in inventoried roadless areas.

#### Cluster 15, topic 11: executive, executive order, unleashing, order, order unleashing, american timber, expansion american, immediate expansion

93 sentences; 88 wordings as `leaders`, 88 as `collapse`.

Temperature 0:

- `leaders`, run 1: Commenters assert that the rescission is primarily driven by a series of executive orders (14192, 14225, 14154, and 14153) that prioritize the extraction of timber, energy, and other natural resources for economic gain and deregulation, rather than by scientific necessity or ecological integrity. They argue that this alignment with these orders will lead to the destruction of protected forests, wildlife habitats, and wilderness areas, and that the stated goal of local control is a pretext for facilitating industrial exploitation.
- `collapse`, run 1: Commenters assert that the rescission is primarily driven by a series of executive orders (14192, 14225, 14154, and 14153) that prioritize the extraction of timber, energy, and other natural resources for economic gain and deregulation, rather than by scientific necessity or ecological integrity. They argue that this policy basis facilitates the destruction of protected forests, wildlife habitats, and wilderness areas, and that the stated goal of local control is a pretext for enabling industrial exploitation and profit for private interests.

#### Cluster 200, topic 11: executive order, executive, order, tongass, directs, alaska roadless, tongass roadless, exclude

15 sentences; 10 wordings as `leaders`, 10 as `collapse`.

Temperature 0:

- `leaders`, run 1: Executive Order 14153 directs the Forest Service to expressly exclude the Tongass National Forest from the 2001 Roadless Rule, resulting in zero acres of roadless protection under both action alternatives.
- `collapse`, run 1: Executive Order 14153 directs the Forest Service to expressly exclude the Tongass National Forest from the 2001 Roadless Rule, resulting in zero acres of roadless protection under both action alternatives.

#### Cluster 116, topic 12: carbon, stored, forest carbon, tons, coterminous, metric, roughly billion, states roughly

26 sentences; 22 wordings as `leaders`, 22 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS fails to quantify the net carbon emissions, lost sequestration, and recovery times resulting from road construction and timber harvest in inventoried roadless areas, despite acknowledging that these lands hold substantial stored carbon and that such activities would cause carbon loss.
- `collapse`, run 1: The Draft EIS fails to quantify the net carbon emissions, sequestration losses, and recovery times resulting from road construction and timber harvest in inventoried roadless areas, despite acknowledging these lands hold substantial stored carbon and that such activities would cause carbon loss.

#### Cluster 153, topic 12: continue sequester, sequester store, store carbon, lands continue, concludes lands, sequester, storage sequestration, store

25 sentences; 16 wordings as `leaders`, 16 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS concludes that the lands will continue to sequester and store carbon without quantifying the specific changes in carbon storage and sequestration resulting from the harvest and roading activities that the rescission would permit.
- `collapse`, run 1: The DEIS concludes that the lands will continue to sequester and store carbon without quantifying the specific changes in carbon storage and sequestration resulting from the harvest and roading permitted by the rescission, nor by explaining how the conclusion accounts for the loss of sequestration benefits and the uncertain offsets from timber products.

#### Cluster 158, topic 13: million-acre, figure, date, tongass, alternative, acreage, figure carries, eis

15 sentences; 15 wordings as `leaders`, 15 as `collapse`.

Temperature 0:

- `leaders`, run 1: The Draft EIS relies on acreage figures for inventoried roadless areas, designated wilderness, and alternative-specific impacts that lack identified sources, effective dates, or reconciliation with acknowledged technical corrections and internal discrepancies, thereby invalidating the baseline and comparative analysis of the alternatives.
- `collapse`, run 1: The Draft EIS relies on acreage figures for inventoried roadless areas, designated wilderness, and alternative-specific impacts that lack identified sources, effective dates, or reconciliation with acknowledged technical corrections and internal discrepancies, thereby invalidating the baseline and comparative analysis of the alternatives.

#### Cluster 182, topic 13: inventory, rare, roadless, area acres, inventory roadless, road buffer, roaded, area

13 sentences; 12 wordings as `leaders`, 12 as `collapse`.

Temperature 0:

- `leaders`, run 1: The DEIS’s methodology for excluding roaded areas from the inventory relies on a 0.5-mile road buffer that was not part of the 1979 RARE II or 2001 Roadless Rule criteria, and the agency’s justification based on mapping errors and pre-2001 construction is inconsistent with the actual metric applied, resulting in an unexplained reduction of 11 million acres.
- `collapse`, run 1: The DEIS’s alternative 3 relies on a 0.5-mile road buffer to exclude 11 million acres from the roadless inventory, a criterion absent from the 1979 RARE II and 2001 Rule, while the stated justification of mapping errors and pre-2001 construction is inconsistent with the buffer’s application and fails to explain how this reduction addresses the original evaluation criteria.

#### Cluster 186, topic 13: eliminated detailed, eliminated, detailed study, detailed, considered, alternatives considered, temporary road, responsive

17 sentences; 11 wordings as `leaders`, 11 as `collapse`.

Temperature 0:

- `leaders`, run 1: The agency eliminated from detailed study the alternative that would have maintained existing inventoried roadless area boundaries and prohibitions on permanent road construction while allowing temporary road construction and timber harvest, citing that it was not responsive to the purpose and need.
- `collapse`, run 1: The agency eliminated from detailed study the alternative that would have maintained existing inventoried roadless area boundaries and prohibitions on permanent road construction while allowing temporary road construction and timber harvest, citing that it was not responsive to the purpose and need.

<!-- end statements -->
