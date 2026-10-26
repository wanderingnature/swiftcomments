# The prong reading

`prong_reading.jsonl` is a hand-reviewed table of 100 whole comments from the
class A set. It tests the prong columns of the model reading: when the reading
opens exactly one prong, is that prong the right description of what the
comment asks the agency to do? It is covered by `seeds-LICENSE` (CC BY-NC 4.0).

## How the comments were drawn

- 50 comments where the model reading opens only the `compliance` prong
  (`substance_scores.prong_compliance = 1`, the other three 0).
- 50 comments where it opens only the `impacts` prong.
- All are class A, read directly (`scored_via = 'direct'`), one comment per
  comment group, drawn at even steps.

## How the labels were made

Two models read every comment. Each call sent the guide below as the system
prompt and one comment as the user message, with no other context. Neither
reader saw the other reader's answer or the pipeline's prong columns. Each
reader lists the kinds of ask the comment makes; the measure per item is
whether the assigned prong is in that list.

- `reader1`: glm-5p3 (temperature 0)
- `reader2`: qwen3p8-max (temperature 0)

The readers disagree on the measure for 4 items. A resolver (glm-5p3, shown
both labels) picked one label per item, and a human reviewer ruled each of the
4 with both labels and the resolver's reason in view. The reviewer sided with
the resolver on all 4.

Agreement between the two readers on the measure: kappa 0.918.

Final result: the assigned prong is a right description for 6 of the 50
compliance-only comments and 49 of the 50 impacts-only comments. The
compliance-only comments cite a law or an order, but almost all of them ask
the agency to weigh impacts. The `prong_compliance` column counts citations;
it does not identify the comments a response answers by a legal reading.

## The columns

One JSON object per line:

- `item_id` — `t5-<prong>-<comment_id>`.
- `prong` — the prong the model reading opened: `compliance` or `impacts`.
- `stratum` — the draw stratum: `compliance only` or `impacts only`.
- `text` — the comment, verbatim.
- `reader1`, `reader2` — each model's label: `prongs` (the kinds of ask, main
  first), `span`, `note`.
- `resolver` — `null` where the readers agree on the measure; otherwise the
  resolver's `pick` (1 or 2) and `reason`.
- `ruling` — `null` where the readers agree; otherwise 1 or 2 for the label
  the reviewer adopted.
- `final` — `right`: whether the assigned prong is in the final label's list.
  Where ruled, the adopted reader's label is carried whole beside it.

## The reading guide

The system prompt of every call, verbatim:

> You read one whole public comment on a federal agency action. You judge only
> what is written. You are not judging whether it is persuasive, well written,
> or right.
>
> The agency answers each comment by what the comment asks it to do. There are
> four kinds of ask:
>
> - impacts - the comment asks the agency to consider or correct a reasonably
>   foreseeable impact of the action: a resource, species, effect, or scale its
>   analysis must weigh.
> - significance - the comment asks the agency to revisit its significance
>   determination: it names a flaw in the analysis and carries it to the
>   conclusion that the effects are more significant than the agency found.
> - alternatives - the comment asks the agency to consider a different course
>   of action, described concretely enough to evaluate. A preference for an
>   outcome already on the table, including no action, is not an ask of this
>   kind.
> - compliance - the comment asks the agency to comply with a law, executive
>   order, or regulation, cited or named.
>
> A comment can make more than one kind of ask. List every kind the comment
> makes, the main one first. A bare opinion, with no ask the agency can act on,
> makes none: the list is empty.
>
> Reply with one JSON object and nothing else.

Each reply also received a shape instruction naming the exact JSON object to
return (the fields listed under "The columns").
