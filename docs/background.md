# Background: the problem, the law and the established methods

This page explains the problem that the pipeline addresses. It gives the law that defines
the work, how agencies have done the work, the methods that are established, and the part
of the work that is still open. The methods of this repository are in `docs/methods-scoring.md` and
`docs/methods-clustering.md`. The numbers in brackets refer to the references at the end.

## 1. The requirement

### 1.1 Public comment

Notice and comment is how the public takes part in federal rules and environmental
reviews. The Administrative Procedure Act requires the agency, "after consideration of the
relevant matter presented," to "incorporate in the rules adopted a concise general
statement of their basis and purpose" [9]. NEPA requires the notice of intent for an
environmental impact statement to "include a request for public comment on alternatives or
impacts and on relevant information, studies, or analyses with respect to the proposed
agency action" [10].

### 1.2 What the regulations require

For decades the standard for all agencies was CEQ's. In 2024, 40 CFR 1503.4(a) read:
"An agency preparing a final environmental impact statement shall consider substantive
comments timely submitted during the public comment period. The agency shall respond to
individual comments or groups of comments" [11]. CEQ removed its NEPA regulations in 2025
and 2026 [12]. Each department now applies its own procedures. For USDA they are 7 CFR
part 1b.

7 CFR 1b.7(f), "Considering and addressing substantive comments" [13]:

> (1) Shall consider and should address in writing comments that raise substantive issues
> and/or recommendations.
>
> (i) Comments shall be analyzed to determine substantive issues raised (see § 1b.11(23)
> and (53)) and, if applicable, recommendations made to remedy the issues.
>
> (ii) Multiple comments regarding the same or similar substantive issues and/or
> recommendations may be grouped and paraphrased as one issue or recommendation. The USDA
> subcomponent need not address every comment individually. Rather, the manner and degree
> to which comments should be addressed should be commensurate with the degree to which the
> comments raise issues and/or recommendations that have bearing on the proposed action,
> development of alternatives, or analysis of the reasonably foreseeable significant
> impacts of the proposed action or alternatives.

The two terms that the standard uses are defined in 7 CFR 1b.11 [14]:

> (23) *Issue* means a logical cause-effect relationship between the actions proposed
> (cause) and the reasonably foreseeable impacts (effect) on resources found in the affected
> environment.
>
> (53) *Substantive* means information that meaningfully informs the consideration of
> reasonably foreseeable impacts on the human environment, the resulting significance
> determination, decisions on how to proceed (i.e., alternatives to be considered or
> analyzed or the alternative selected for implementation), or compliance with applicable
> laws, executive orders, and regulations.

Paragraph (f)(2) lists the actions that a response can record. One of them is "no action
needed" with a brief rationale: the comment is outside the scope, there is no cause-effect
relationship, the commenter misinterpreted the information, or the recommendation does
not comply with law or is not feasible. The record of decision must "certify that the
subcomponent has considered all the substantive alternatives, information, and analyses
submitted by State, Tribal, and local governments and public commenters" [15].

**What the pipeline takes from the law.** The gate of the model-free reading follows
1b.11(23) and (53): GAP and EVID for issues and information, ALT for alternatives, LAW
for compliance. Answerability follows the no-action rationales of (f)(2)(vi). The clusters
follow (f)(1)(ii): comments on the same issue are grouped, so that each issue is answered
once.

## 2. How agencies have done the work

The Forest Service's account of its analysis for the 2001 Roadless Rule is the fullest
public record of the manual method at this scale. The public "submitted approximately
1,155,000 separate pieces of input" [16]. "Content analysis is a systematic method of
compiling, categorizing, and capturing the full range of public viewpoints and concerns."
It "is not a vote-counting process."

The steps of that method:

1. Each response received an identifier and a class by respondent type and origin.
2. "Comment coders then read each response, highlighted substantive comments within each,
   and labeled each by subject area."
3. "Data entry personnel copied the highlighted comments verbatim into the database."
4. "Analysts organized them by topic, and divided them into separate, distinct public
   concern statements," each with "a representative variety of verbatim quotations."

From 1,155,000 responses the team identified "approximately 2,450 separate public
comments." About 97% of the responses "were duplicative of about 310 different form
letters or postcard campaigns," and "the focus of content analysis is content, not
volume" [17]. The 2008 Idaho roadless rulemaking used the same method on about 139,120
comments [18]. A 2021 review found that most agencies "use a combination of Excel, Word,
and SharePoint to conduct manual reviews and analysis of the comments they receive" [19].

## 3. Mass participation and the turn to automation

Electronic submission changed the volume. Advocacy campaigns send identical and
near-identical letters in large numbers [20]. Mass comments generally contain little that
is new [21]. Computational analysis of comments has been proposed for more than a decade
[22], and fabricated comments are a subject of study [23]. The Administrative Conference
recommends that agencies manage mass comments with de-duplication tools and show one
representative of nearly identical comments [24].

The docket of this repository is an example. The proposal to rescind the 2001 Roadless
Rule (FS-2025-0001) received 390,064 comments. Most of them are campaign letters, and the unique
comments that remain after de-duplication are still far more than the 2008 method was
staffed for.

Agencies are turning to automation, and generative AI is the method that they name most
often. USDA proposed a pilot to "develop a proof-of-concept NLP toolset" for "pre-screening
and categorization of comments" [25]. EPA states that it "may use artificial intelligence
to help sort and categorize public comments" [26]. Pacific Northwest National Laboratory
built and tested AI tools for NEPA comment review [27]. Its CommentNEPA application,
measured against expert annotations, found about 74% quote precision, about 23% quote
recall and about 50% binning recall [28].

## 4. The stages of the work

| Stage | What it asks | Maturity | In this repository |
|---|---|---|---|
| Intake | Every comment, with its text and attachments. | Established. | Steps 1 and 8. |
| De-duplication | Copies, templates and campaigns folded. | Established. | Step 2. |
| Substantive issues | The definitions of 1b.11(23) and (53) applied to each comment. | Open. The definitions are semantic. | Steps 6 and 7 (`docs/methods-scoring.md`). |
| Grouping | The same or similar issues collected and stated once. | Open. "The same issue" is a judgment. | Steps 10 to 14 (`docs/methods-clustering.md`). |
| Response | The action taken, cited to the record. | Open. It needs the record and the agency's reasoning. | Not built (steps 15 and 16). |

## 5. De-duplication: the established methods

Collecting comments and finding repeated comments are solved problems. Their techniques
are standard and well analysed. They leave the agency with choices of definition and
threshold, and those choices decide what reaches the readers.

**What counts as a duplicate.** The Forest Service defines form letters as "five or more
letters that contain identical text but are submitted by different people" [2]. It
separates them from "original responses or form letters with additional original text."
Campaigns add a third kind: one template that each sender rewords. Each relation needs a
different test.

### 5.1 The techniques

- **Exact matching.** The method normalizes each text (markup removed; whitespace, case and
  encoding made uniform) and hashes it. Equal hashes are identical texts. It finds copies
  and nothing else: a changed signature defeats it.
- **Template matching.** The method removes the variable parts of a form letter (the
  salutation, the signature, the address) before it hashes. Personalized copies of one
  body then match.
- **Shingling** [3]. A text $A$ becomes its set of $w$-word shingles $S(A)$. Two measures
  follow:

  $$r(A,B) = \frac{|S(A) \cap S(B)|}{|S(A) \cup S(B)|}, \qquad c(A,B) = \frac{|S(A) \cap S(B)|}{|S(A)|}.$$

  Resemblance $r$ (the Jaccard index) finds near-copies. Containment $c$ finds a form
  inside a longer letter. In that form-plus case, resemblance falls as the added text grows,
  and containment does not.
- **MinHash and locality-sensitive hashing** [4]. For a random permutation $\pi$ of the
  shingles,

  $$\Pr\big[\min \pi(S(A)) = \min \pi(S(B))\big] = r(A,B).$$

  $k$ independent minima estimate resemblance with a standard error of about
  $\sqrt{r(1-r)/k}$. Split the $k$ minima into $b$ bands of $s$ rows. A pair is a candidate
  when one band matches in full. The probability of a candidate is $1 - (1 - r^{s})^{b}$, an
  S-curve with its threshold near $(1/b)^{1/s}$. The method does not compare all pairs.
- **SimHash** [5]. The method projects the weighted features of a text onto random
  hyperplanes and keeps the signs as an $f$-bit fingerprint. For two vectors at angle
  $\theta$, each bit agrees with probability $1 - \theta/\pi$. The Hamming distance between
  fingerprints therefore estimates the angle. Near-duplicates are within a few bits.
- **Edit distance and alignment.** These score small variations directly. They cost
  quadratic time for each pair, so they confirm candidates and do not find them.
- **Clustering of near-duplicates.** The method turns pairwise matches into groups. Yang
  and Callan clustered near-duplicate comments from EPA and DOT dockets, with document
  metadata as constraints [6].
- **Semantic similarity.** Embedding models and cosine similarity group texts that say the
  same thing in different words. A federal pilot tested SBERT with RoBERTa and a fine-tuned
  BigBird for long comments [7].

### 5.2 What remains a choice

Every technique needs a threshold: the shingle width, the resemblance or containment
limit, the number of differing bits, the cosine. The threshold is a policy as much as a
parameter. A loose threshold folds letters that share a template but differ in what the
sender added. A tight threshold leaves near-copies for a person to read again.

Grouping pairwise matches adds one more choice. Transitive closure chains texts that are
each similar to the next but not to each other. Assignment to a representative does not
chain. Semantic similarity moves the work from copies to meaning, and there the open part
of the problem begins. Agency tools also change: the federal docket system's
de-duplication feature was valued by agencies and then discontinued [8].

### 5.3 What step 2 does

Step 2 uses four layers. Each layer folds a group into one representative.

| Layer | What it finds | How |
|---|---|---|
| Identical copies | The same text submitted more than once. | SHA-256 of the canonical full text. |
| Template letters | One body under personal openings and signatures. | A hash of the body without the opening and the closing. |
| Small families | A few copies of one letter. | Sets of 6- to 8-word n-grams, compared by resemblance and containment. A Bloom filter screens the pairs. Leader assignment at 0.85 makes the groups. |
| Campaign letters | One template, reworded. | Shared sentences. |

Step 2 assigns each text to a leader, not by transitive closure. Each member is then
within the threshold of its own leader (`shared/near_duplicates.py`).

## 6. The process, step by step

Three published accounts describe the steps of comment processing: EPA's, through its
contractor Cadmus (2026); GAO's (2021); and the Forest Service's (2000). They reduce to
eleven steps. The table places each step against the steps of this repository.

| # | Step | Forest Service, 2000 | This repository |
|---|---|---|---|
| P1 | Receipt | Each response gets an identifier. | The docket, FS-2025-0001. |
| P2 | Collection | Mail, email, web form. | `make corpus` from the bulk download; `make fetch` for attachments. |
| P3 | Conversion and metadata | Respondent type and origin. | The text rendered with each character's offset kept; `make text`, `make attachments`. |
| P4 | Tracking | A database. | One SQLite file; every run stores its counts. |
| P5 | De-duplication | About 97% of responses matched to about 310 form letters. | `make dedup`, `make ngrams`, `make groups`. |
| P6 | Segmentation | Coders highlight passages. | The comment-sentences package. |
| P7 | Reading for substance | Coders mark substantive comments. | `make score-model-free` (rules) and `make score-model` (a model), with the same scheme. |
| P8 | Verification of coding | Not described. | `make score-model-compare`: the two readings side by side. |
| P9 | Grouping by subject | Analysts organize by topic. | `make sentences`, `make embed`, `make clusters`. |
| P10 | Statement of the issue | Public concern statements with quotations. | Not built (step 15). |
| P11 | Response and publication | The agency's responses. | Not built (step 16). |

**Where automation changes the outcome.** In a manual process a coder reads each comment,
and a second coder checks the work. Each automated step replaces a judgment with a
procedure. A procedure gives the same result on each run. It also makes the same error on
every comment of one kind, where a person's errors are scattered.

| Step | What automation can change | Where this repository measures it |
|---|---|---|
| P3 Conversion | Text that the reader never sees. | The pieces under 25 letters and digits that the sentence method does not store (`docs/methods-scoring.md`). |
| P5 De-duplication | A sender's own additions folded into a template. | The families and campaigns of `make groups` (the console's Coordination page). |
| P6 Segmentation | A claim split across sentences, or words of two claims joined. | The three reading modes of the model-free reading (`docs/methods-scoring.md`). |
| P7 Reading for substance | A comment that the gate closes is not grouped. | `make score-model-compare`: the rule and model readings side by side. |
| P9 Grouping | A substantive sentence that no cluster holds. | The coverage of each clustering case (`docs/methods-clustering.md`). |

## 7. Limits of automated processing

These limits apply to any automated reader, by code or by model.

- **The unit of reading is a decision.** Read whole, the rules find many more comments
  substantive than read sentence by sentence. Whole reading joins words of different
  claims. Sentence reading loses a claim stated across two sentences.
- **The definitions are semantic.** "A logical cause-effect relationship" and "meaningfully
  informs" are judgments about meaning. Rules approximate them with word lists and
  patterns. A generative model approximates them with its training. The two disagree
  (`make score-model-compare`).
- **There is no ground truth.** At this scale the only reference is another instrument.
  Agreement with it measures consistency, not compliance with the regulation.
- **Automated reading depends on other data.** The law-dependent levels depend on the
  matched citations and authorities. A process inherits the gaps of each table that it
  reads.
- **Grouping depends on the corpus.** Form-letter variants dominate density clustering
  unless they are joined first. The number and shape of the issues depend on such choices.
- **Generative tools have measured limits.** The one published evaluation of a generative
  comment tool against expert annotations found about a quarter of the quotations and
  about half of the binning [29]. A generative model also chooses which part of a comment
  to weigh.

## 8. Future work

1. **A hand-labelled set.** Two people code a sample sentence by sentence. Then measure
   each reading against people, not against another instrument.
2. **Precision and recall for each rule** on that set.
3. **The stability of the clusters.** Run one setting with different seeds and report the
   adjusted Rand index between the runs. `make compare-cases` measures it between cases.
4. **The quality of the topics.** A coherence measure, or a human rating of the names.
5. **A benchmark against the agency's own responses** in the Final EIS.

## References

1. U.S. Department of Agriculture, *National Environmental Policy Act*, 7 C.F.R. § 1b.7(f)(1). <https://www.ecfr.gov/current/title-7/subtitle-A/part-1b/section-1b.7>
2. USDA Forest Service, *Roadless Area Conservation, National Forest System Lands in Idaho: Final Environmental Impact Statement*, August 2008, PDF p. 12, n. 1. <https://www.fs.usda.gov/sites/default/files/roadless/roadless-id-final-eis-aug-2008-fsm8-036009.pdf>
3. Andrei Z. Broder, "On the Resemblance and Containment of Documents," *Compression and Complexity of SEQUENCES 1997*, IEEE, 1997, 21–29. <https://doi.org/10.1109/SEQUEN.1997.666900>
4. Broder [3]; Andrei Z. Broder, Steven C. Glassman, Mark S. Manasse and Geoffrey Zweig, "Syntactic Clustering of the Web," *Computer Networks and ISDN Systems* 29 (1997): 1157–66. <https://doi.org/10.1016/S0169-7552(97)00031-7>
5. Moses S. Charikar, "Similarity Estimation Techniques from Rounding Algorithms," *STOC 2002*, ACM, 380–88. <https://doi.org/10.1145/509907.509965>; Gurmeet Singh Manku, Arvind Jain and Anish Das Sarma, "Detecting Near-Duplicates for Web Crawling," *WWW 2007*, ACM, 141–50. <https://doi.org/10.1145/1242572.1242592>
6. Hui Yang and Jamie Callan, "Near-Duplicate Detection by Instance-Level Constrained Clustering," *SIGIR 2006*, ACM. <https://doi.org/10.1145/1148170.1148243>
7. Chief Data Officers Council, *Implementing Federal-Wide Comment Analysis Tools: Final Recommendations*, June 2021, 3, 18–19. <https://resources.data.gov/assets/documents/CDOC_Recommendations_Report_Comment_Analysis_FINAL.pdf>
8. CDO Council [7], 18.
9. Administrative Procedure Act, 5 U.S.C. § 553(c). <https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title5-section553&num=0&edition=prelim>
10. National Environmental Policy Act § 107(c), 42 U.S.C. § 4336a(c). <https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title42-section4336a&num=0&edition=prelim>
11. Council on Environmental Quality, *Response to Comments*, 40 C.F.R. § 1503.4(a) (as of July 1, 2024). <https://www.ecfr.gov/on/2024-07-01/title-40/chapter-V/part-1503/section-1503.4>
12. CEQ, "Removal of National Environmental Policy Act Implementing Regulations," 90 Fed. Reg. 10610 (February 25, 2025) <https://www.govinfo.gov/content/pkg/FR-2025-02-25/pdf/2025-03014.pdf>; final rule, 91 Fed. Reg. 618 (January 8, 2026) <https://www.govinfo.gov/content/pkg/FR-2026-01-08/pdf/2026-00178.pdf>
13. 7 C.F.R. § 1b.7(f).
14. 7 C.F.R. § 1b.11(23), (53). <https://www.ecfr.gov/current/title-7/subtitle-A/part-1b/section-1b.11>
15. 7 C.F.R. § 1b.8(b)(2). <https://www.ecfr.gov/current/title-7/subtitle-A/part-1b/section-1b.8>
16. USDA Forest Service, *Roadless Area Conservation Final Environmental Impact Statement*, vol. 3, *Agency Responses to Public Comments*, November 2000, Introduction, 1. <https://www.fs.usda.gov/sites/default/files/roadless/roadless-feis-volume3.pdf>
17. Forest Service [16], Involvement, 42.
18. Forest Service [2], PDF p. 13.
19. CDO Council [7], 8.
20. Stuart W. Shulman, "The Case Against Mass E-mails," *Policy & Internet* 1, no. 1 (2009): 23–53 <https://doi.org/10.2202/1944-2866.1010>; Steven J. Balla et al., "Where's the Spam?," *Policy & Internet* 11, no. 4 (2019): 460–79 <https://doi.org/10.1002/poi3.224>
21. Steven J. Balla et al., "Lost in the Flood?," *Regulation & Governance* 16, no. 1 (2022): 293–308. <https://doi.org/10.1111/rego.12318>
22. Vladimir Eidelman, Brian Grom and Michael A. Livermore, "Computationally Assisted Regulatory Participation," *Notre Dame Law Review* 93, no. 3 (2018): 977–1034. <https://scholarship.law.nd.edu/ndlr/vol93/iss3/2/>
23. Cassandra Handan-Nader, "Do Fake Online Comments Pose a Threat to Regulatory Policymaking?," *Policy & Internet* 15, no. 1 (2023): 100–116. <https://doi.org/10.1002/poi3.327>
24. Administrative Conference of the United States, Recommendation 2021-1, 86 Fed. Reg. 36075 (July 8, 2021). <https://www.govinfo.gov/content/pkg/FR-2021-07-08/pdf/2021-14597.pdf>
25. CDO Council [7], 3, 7.
26. U.S. EPA, "Commenting on EPA Dockets." <https://www.epa.gov/dockets/commenting-epa-dockets>
27. M. Parker et al., *Testing Artificial Intelligence Tools to Streamline the Public Comment-Review Process for NEPA Environmental Reviews*, PNNL-35927, April 2024. <https://www.pnnl.gov/sites/default/files/media/file/PolicyAI%20Comment%20Processing%20White%20Paper%20V1.pdf>
28. Reilly Raab et al., "Audit, Alignment, and Optimization of LM-Powered Subroutines with Application to Public Comment Processing," arXiv:2507.08109, 2025. <https://arxiv.org/abs/2507.08109>
29. Raab et al. [28].
