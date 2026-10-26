# The answerability reread

`answerability_reread.jsonl` is a hand-reviewed table of the 100 whole comments of
`labelled_set.jsonl`, read again by the same two coders under a revised guide. The first
guide wording did not separate A2 from A3 (answerability kappa 0.504 between the
coders). The revision names the levels in order of application and gives A2 three strict
tests. Under it the kappa is **0.615**. It is covered by `seeds-LICENSE` (CC BY-NC 4.0).

## How the labels were made

Two models read every comment. Each call sent the revised guide below as the system
prompt and one comment as the user message, with no other context. Neither reader saw
the other reader's answer, either instrument's output, or its own first-pass label.

- `reader1`: glm-5p3 (temperature 0)
- `reader2`: qwen3p8-max (temperature 0)

The readers disagree on the answerability level for 24 comments. A resolver (glm-5p3,
shown both labels) picked one label per item, and a human reviewer ruled each of the 24
with both labels and the resolver's reason in view. The reviewer sided with the resolver
on 17 and overruled it on 7.

Final levels over the 100 comments: A0 10, A1 35, A2 47, A3 8. By the stratum they were
drawn from (the decision table's level, 25 each):

| Stratum | A0 | A1 | A2 | A3 |
|---|---|---|---|---|
| table A0 | 9 | 1 | 7 | 8 |
| table A1 | 1 | 23 | 1 | 0 |
| table A2 | 0 | 8 | 17 | 0 |
| table A3 | 0 | 3 | 22 | 0 |

## The columns

One JSON object per line:

- `item_id` — `c-<level>-<comment_id>`, as in `labelled_set.jsonl`.
- `stratum` — the draw stratum: the decision table's level.
- `text` — the comment, verbatim.
- `reader1`, `reader2` — each model's label: `gate`, `kinds`, `span`, `answerability`,
  `note`.
- `resolver` — `null` where the readers agree on the level; otherwise the resolver's
  `pick` (1 or 2) and `reason`.
- `ruling` — `null` where the readers agree; otherwise 1 or 2 for the label the
  reviewer adopted.
- `final` — the final label: the agreed `answerability` (and the gate where the
  readers agree on it), or the adopted reader's label whole.

## The revised guide

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
> For a whole comment, also give the answerability level. Apply the first level
> whose test the comment meets, in this order: A1, A2, A3; A0 when the gate is
> closed.
>
> - **A1** — the comment cites a legal authority (LAW above). The citation is
>   enough; the writer does not have to argue a violation.
> - **A2** — one of three tests is met, strictly:
>   (a) a deficiency carried to its conclusion — the writer names what the flaw
>   changes in the analysis or the decision, not only that the flaw exists;
>   (b) a concrete alternative (ALT above);
>   (c) a deficiency or evidence with BOTH a stated mechanism — how it carries
>   into the analysis, in the writer's own words — AND a citation of a source or
>   document it rests on.
>   A mechanism without a citation is not A2 under (c). A flaw asserted without
>   its consequence is not A2 under (a). When a test is in doubt, the level is A3.
> - **A3** — the gate is open and no test above is met: substantive, answerable
>   with analysis already in hand.
> - **A0** — the gate is closed.
>
> Reply with one JSON object and nothing else.

Each reply also received a shape instruction naming the exact JSON object to return
(the fields listed under "The columns").
