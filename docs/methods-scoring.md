# The model-free reading: the method

This page explains how `make score-model-free` reads a comment, and why each part has
its form. `docs/model-free-scoring.md` explains how to run the step. The rules are
`scripts/model_free/`, rule set 3.

## 1. Purpose

The agency must answer the comments that raise substantive issues (7 CFR 1b.7(f)(1)).
The terms "substantive" and "issue" have definitions in 7 CFR 1b.11(53) and (23). The
model-free reading decides which comments are substantive, by rule, with no language
model.

The reading has three properties:

- **Reproducible.** The same text gives the same score on every run.
- **Traceable.** Each level comes from a rule hit. The hit keeps the rule, the matched
  words and their offsets.
- **Free to run.** It needs Python and spaCy only, on one CPU core.

The reading has one failure that matters. If the gate stays closed on a substantive
comment, the agency never considers that issue. If the gate opens on a comment that is
not substantive, a reader spends a few seconds on it. The rules are therefore built for
recall: they open the gate when in doubt.

## 2. The sentences

### 2.1 The sentence method

One package splits every comment into sentences: `packages/comment-sentences`.

1. The package renders the stored HTML to plain text, line by line. It keeps the offset
   of each character in the stored text.
2. It repairs comment-form problems. It rejoins a long line that has no closing
   punctuation, removes quote and heading marks, and spaces full stops glued to the next
   sentence.
3. It splits each line with the splitter of the agency's record documents. A sentence
   ends at `.`, `?` or `!` before a capital letter, a digit or an opening quote.
4. It does not split after one of 79 abbreviations (Mr., e.g., No., Fed., Reg., Mt.,
   St.), after a single letter, or inside a number.
5. It joins a piece of fewer than four words to a neighbour.
6. It drops a piece of fewer than 25 letters and digits, for example "Sincerely," or a
   name.

**Why the record's splitter.** A comment sentence and a record sentence are then the
same kind of unit. A later step can compare a comment's claim with the record's text.

**Why offsets.** Each sentence is a span of the stored comment. A reader can trace every
sentence back to the comment.

### 2.2 The identity of a sentence

Two sentences are the same when they differ only in case, punctuation, spacing, markup
or encoding. The key is

$$\kappa(s) = \text{the letters and digits of } \mathrm{lower}(\mathrm{unescape}(\mathrm{strip\_markup}(s))), \qquad \mathrm{text\_key}(s) = \mathrm{SHA256}(\kappa(s)).$$

A form letter sent 3,000 times is one distinct sentence with 3,000 occurrences.

## 3. The eight dimensions

The rules grade a unit of text on eight dimensions. Each dimension has a level from 0
to 3. The dimensions follow the coding scheme of the v3 instrument
(`docs/instruments/substantive-scoring-v3.md`).

| Dimension | What it measures | Level 2 or 3, in short |
|---|---|---|
| PLACE | A place named. | 2 for a ranger district. 3 for a specific named place, a road number, an elevation or coordinates. |
| STAND | The commenter's connection to the place. | 3 for a professional role. 2 for a first-person connection with a duration or frequency. |
| DOC | A reference to the agency's documents. | 2 for a characterization ("the DEIS states") or a named section. 3 for a numbered section, page, table or figure. |
| GAP | A deficiency in the analysis. | 2 for a deficiency with a specific name, a missing analysis asked or requested, or a stated effect on a named resource. 3 adds a consequence. |
| EVID | A source applied to this proposal. | 2 for a named source or the agency's own record, applied. 3 adds a year, an author or a figure. |
| ASK | A request with an action and a subject. | 2 when the request names its object. 3 adds a time. |
| ALT | A distinct alternative. | 2 for alternative language with a concrete element. 3 adds purpose and need. |
| LAW | A legal authority. | 2 for a confirmed authority, a case, or a citation form (CFR, USC, Federal Register, executive order). |

### 3.1 Rules that apply to all dimensions

- **Quotations.** The rules remove quoted text from the commenter's own words. GAP, ASK,
  ALT and STAND read the own words only. A commenter who pastes the DEIS does not get GAP
  for the DEIS's words.
- **The generality test.** GAP, EVID and DOC are 0 unless the unit has an anchor: the
  document, a place, this action, a figure that the record contains, a demonstrative aimed
  at a claim ("that is wrong"), or a proper noun that is not the document, the agency or
  a state. A general complaint about the environment has no anchor.
- **The parse.** spaCy `en_core_web_md` gives the parts of speech, the dependencies and
  the entities. ASK reads the object of a work verb from the parse.

### 3.2 Why some rules have their form

- **A statute named in prose is not LAW 2.** "NEPA" alone is not a citation. The v3 guide
  keeps LAW for a confirmed citation.
- **A place is not a specific name for GAP.** The v3 guide keeps "water quality" at
  level 1 beside "Wilson Creek". A place tells where, not what is missing.
- **A proper noun that is not a species is not a specific name.** "The White House"
  names an actor, not the thing that is wrong.
- **"Exceptions" and "exemptions" are not alternative language.** In this docket they
  describe the existing rule.
- **A source must be applied.** A source counts for EVID only when the sentence ties it to
  a place, the document, this action, or what this action does. A citation with no tie
  does not inform the analysis of this proposal.

## 4. The score of a unit

For the levels $d = (d_i)$ of a unit:

$$\text{strength}(d) = \sum_i d_i \in [0, 24], \qquad g(d) = \mathbb{1}\Big[\max_{i \in \mathcal{G}} d_i \ge 2\Big], \quad \mathcal{G} = \{\text{GAP}, \text{EVID}, \text{ALT}, \text{LAW}\}.$$

- The **gate** $g$ opens when GAP, EVID, ALT or LAW reaches 2.
- The **gate basis** names each gate dimension at 2 or more, and the unit that reached it.
- The **band** is minimal (strength 0 to 5), marginal (6 to 11), developed (12 to 17) or
  strong (18 and more).

The four gate dimensions follow the regulation. GAP and EVID are issues and new
information. ALT is an alternative. LAW is compliance with law, which 7 CFR 1b.11(53)
makes substantive by definition.

## 5. Three ways to read a comment

The rules read a unit. A comment can be read as one unit or as many sentences.

| Mode | The comment's score | Bias |
|---|---|---|
| Whole | The rules read the full comment once. | A rule can pair words from two sentences. It opens the gate too often. |
| Sentence | Each sentence is scored alone. The comment takes the maximum of each dimension. | A claim that spans two sentences is lost. It opens the gate too rarely. |
| Hybrid | The whole comment's score, with GAP held to what one sentence reaches. | The step uses this mode. |

In hybrid mode, with $d^W$ the whole comment's levels and $d^S$ the sentence maximum:

$$d^H_{\text{GAP}} = \min\big(d^W_{\text{GAP}},\ d^S_{\text{GAP}}\big), \qquad d^H_i = d^W_i \text{ for every other } i.$$

**Why hybrid.** The GAP rule "a stated effect on a named resource" pairs an effect verb
with a named thing. In whole mode it paired them across sentences, often on a U.S. state
alone. For example, "I live in Tennessee" and "this could increase road construction" in
two sentences gave GAP 2. Hybrid mode keeps the whole reading for EVID, ALT and LAW, where a tie across
sentences is often real. It keeps GAP to a single sentence.

## 6. Answerability

Answerability tells which of the agency's no-action replies a comment defeats
(7 CFR 1b.7(f)(2)(vi)). With $\mu$ = "a move and a target are both present" (a
mechanism) and $\gamma$ = "DOC is 2 or more, or a source is named" (a citation):

$$A(d) = \begin{cases}
\text{A0} & \text{the gate is closed} \\
\text{A1} & d_{\text{LAW}} = 2 \\
\text{A2} & d_{\text{GAP}} = 3 \ \vee\ d_{\text{ALT}} \ge 2 \ \vee\ \big((d_{\text{GAP}} = 2 \vee d_{\text{EVID}} \ge 2) \wedge \mu \wedge \gamma\big) \\
\text{A3} & \text{otherwise}
\end{cases}$$

The cases are tested from top to bottom.

- A1 defeats "addressed in the analysis" and "certified not substantive". The analysis
  must address the law.
- A2 defeats "no cause and effect". The comment states a mechanism and cites a source.
- A3 is an open gate that defeats neither.

## 7. How the rules were built

Each rule set came from reading the sentences behind the disagreements with v3.

| Rule set | What it adds | Why |
|---|---|---|
| 1 | The first rules, with these exclusions: "USDA" is not a source, "2001" in the rule's name is not a source year, "Roadless Rule" is not a specific name, a bare "NEPA" is not LAW 2. | Each exclusion removes a false hit. |
| 2 | Four wide rules: the agency's own record as a source; a missing analysis asked or requested; a stated effect on a named resource; named measures as concrete alternatives. | Rule set 1 left comments closed that v3 opened. |
| 3 | EVID also ties a source to what the action does: road construction, roaded land, roadless areas. | A comment that cites a nationwide study of fire in roadless areas would score EVID 0. |

## 8. Against the model reading

v3 is the model-based reading of the same scheme. It is a reference, not the truth.

The comments that v3 opens and the rules do not are the failure that matters. Whole mode
has the fewest of them and opens the most extra comments; sentence mode has the most;
hybrid mode lies between.

The rule reading of law depends on the citation and authority tables, so `make tag` must
run before this step.

`make score-model-compare` sets the two readings side by side on any comments of this
repository and gives these measures (`docs/model-free-scoring.md`).

## 9. What this repository does not read

Two inputs of the rules are not read.

- **The record's sentences and figures.** A sentence that is the agency's own text is not
  marked, so it can score GAP. A figure from the DEIS is not an anchor for the generality
  test.
- **The sentence vectors.** The similarity of an alternative to the DEIS's alternatives is
  not measured. No rule uses it as a threshold.

## 10. Limits

- The rules are compared with another instrument, not with people. Agreement with v3 is
  not accuracy. A hand-labelled set is the next measure to make.
- The word lists are written by hand (`scripts/model_free/vocab/`). A list misses the
  words it does not contain.
- The scheme is the v3 scheme. Its definitions of the eight dimensions are a choice, made
  from the regulation's terms.
