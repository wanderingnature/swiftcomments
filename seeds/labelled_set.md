# The labelled set

`labelled_set.jsonl` is a hand-reviewed table of 374 items from the class A
comments: 274 single sentences and 100 whole comments. Each item carries three
independent model readings and one final label. The set measures the two gate
instruments (the rule gate and the model reading) against labels that come from
neither. It is covered by `seeds-LICENSE` (CC BY-NC 4.0).

## How the items were drawn

- 100 sentences that the rule gate opens (`gate_sentence_occurrence.opens = 1`),
  one per text key, at even steps.
- 74 sentences from comments where the model reading opens the gate and the rule
  gate closes it. The corpus holds exactly 74 such comments; all are included.
- 100 sentences from comments where neither instrument opens the gate.
- For each comment above, the sentence is the longest scored span of 60 to 400
  characters.
- 100 whole comments, 25 from each answerability level (A0 to A3) of the
  decision table.

## How the labels were made

Three models read every item. Each call sent the coding guide below as the
system prompt and one item as the user message, with no other context. No
reader saw another reader's answer or either instrument's output.

- `reader1`: glm-5p3 (temperature 0)
- `reader2`: qwen3p8-max (temperature 0)
- `sonnet`: claude-sonnet-5-5 (no temperature override; the model does not
  accept one)

The two coders are `reader1` and `reader2`. They disagree on the gate for 48
items. A human reviewer ruled each of the 48 with all three labels in view. The
ruling adopts one reader's label whole: the reviewer took `reader1` on 14,
`reader2` on 32, and `sonnet` on 2.

Gate agreement between the two coders: kappa 0.740. Answerability agreement on
the 100 comments: kappa 0.504. The answerability labels are therefore weaker
than the gate labels; the `final` field carries an answerability level only
where the two coders agree or a ruling settled it (84 of 100 comments).

## The columns

One JSON object per line:

- `item_id` — `s-rules-<text_key>` for a rule-opened sentence,
  `s-<comment_id>` for the other sentences, `c-<level>-<comment_id>` for a
  whole comment.
- `kind` — `sentence` or `comment`.
- `stratum` — the draw stratum named above.
- `text` — the item, verbatim.
- `reader1`, `reader2`, `sonnet` — each model's label: `gate`, `kinds`, `span`,
  `note`, and for comments `answerability`.
- `ruling` — `null` where the coders agree on the gate; otherwise 1, 2 or 3 for
  the label the reviewer adopted (`reader1`, `reader2`, `sonnet`).
- `final` — the final label. Where the coders agree: the agreed gate, plus the
  answerability level where they agree on it too. Where ruled: the adopted
  reader's label whole.

## The coding guide

The system prompt of every call, verbatim:

> You read one item from a public comment on a federal agency action: a single
> sentence, or a whole comment. You judge only what is written. You are not judging
> whether it is persuasive, well written, or right.
>
> Information is **substantive** when it meaningfully informs (1) the consideration
> of reasonably foreseeable impacts, (2) the significance determination, (3)
> decisions on how to proceed — the alternatives considered, analyzed, or selected —
> or (4) compliance with applicable laws, executive orders, and regulations.
>
> One principle governs every judgment. A statement does analytical work only when
> it says something about THIS proposal, THIS place, or THIS document. A statement
> that would read the same in a comment on any similar proposal in any decade does
> none, however true and however well sourced. The reverse also holds: a figure
> taken from the agency's own record for this action and set against the proposal
> is specific to this proposal whatever its subject.
>
> The **gate is open** when the item does substantive work of at least one of these
> four kinds:
>
> - **GAP** — it names a specific deficiency in the agency's analysis: the resource,
>   species, effect, or scale that is missing or wrong. A bare conclusion ("the
>   analysis is inadequate") or a topic-level complaint ("wildlife wasn't
>   considered") is not specific, and the gate does not open on it.
> - **EVID** — it relies on a source, figure, or firsthand observation AND the
>   writer ties it to this proposal, place, or document in their own words. A
>   general study quoted with no connection drawn is not EVID, whatever its
>   credentials.
> - **ALT** — it describes an alternative the agency has not already analyzed,
>   concretely enough to evaluate. A preference for an outcome already on the
>   table, including no action, is not ALT.
> - **LAW** — it cites a legal authority: a statute, regulation, executive order,
>   or court case, by citation or by name.
>
> The writer's position, the item's length, its polish, and its emotion change no
> answer. Do not check whether the facts are true. Do not supply what the writer
> probably meant. An empty or off-topic item: the gate is closed.
>
> For a whole comment, also give the answerability level:
>
> - **A0** — the gate is closed.
> - **A1** — the comment raises compliance with a law, order, or regulation that a
>   response must address (LAW does its work).
> - **A2** — the comment states a specific deficiency or a concrete alternative
>   with a mechanism (it says how the flaw carries into the analysis or decision)
>   and a source or document citation, so "no cause and effect" is not an available
>   reply.
> - **A3** — the gate is open, but the comment defeats neither reply: substantive,
>   answerable with analysis already in hand.
>
> Reply with one JSON object and nothing else.

Each reply also received a shape instruction naming the exact JSON object to
return (the fields listed under "The columns").
