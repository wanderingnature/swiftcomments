# The retrieval reading

`retrieval_reading.jsonl` is a hand-reviewed table of 200 retrieval lists: 100
gate-opening sentences that cite the record, each retrieved two ways. It tests
`make retrieve`: when a commenter points at a passage of the record, is that
passage among the 5 chunks the retrieval returns? It is covered by
`seeds-LICENSE` (CC BY-NC 4.0).

## How the sentences were drawn

- Distinct gate-opening sentences (`gate_sentence.opens = 1`) from comments the
  model reading scores DOC 2 or more.
- The sentence text names a record location: section, page, table, figure,
  chapter, appendix, EIS, or a section sign.
- One sentence per comment group, 100 drawn at even steps over the key order.

Each sentence appears twice: once with its 5 nearest chunks under the
comment-view vectors (the stored `doc_retrieval`), once with its 5 nearest
under the plain vectors, computed the same way. The excluded sections
(letters, comment summaries, responses to comments) are outside both searches.

## How the labels were made

Two models read every item. Each call sent the guide below as the system
prompt, and one sentence with its 5 passages (document title and pages with
each) as the user message. Neither reader saw the other reader's answer, the
view, or the cosines. The label is where the meant passage sits: `first`
(passage 1), `later` (in the 5, not first), or `absent`.

- `reader1`: glm-5p3 (temperature 0)
- `reader2`: qwen3p8-max (temperature 0)

The readers disagree on 39 items. A tie-breaker from a third provider
(claude-haiku-5-5, shown both labels) picked one per item, and a human
reviewer ruled every disagreement with both labels and the tie-breaker's
reason in view. The reviewer's ruling is the final label and is not limited
to the readers' two answers. 22 of the 39 disagreements are two letter-writing
campaigns (a court holding quoted in nine wordings; the record's fire-density
finding); the reviewer ruled each campaign once.

Agreement between the two readers: kappa 0.683.

Final result, comment view: the meant passage is first for 57 of 100
sentences and in the top 5 for 82 of 100. Plain view: first for 43, in the
top 5 for 71. The comment-view instruction earns its separate embedding run.
At every similarity level the meant passage is present far more often than
absent, so no cosine floor separates found from not found in this draw.

## The columns

One JSON object per line:

- `item_id` — `t1-<view>-<text_key>`; the view is `c` (comment) or `p` (plain).
- `view` — `comment` or `plain`.
- `text_key` — the sentence's key in `gate_sentence`.
- `sentence` — the sentence, verbatim.
- `top` — the 5 retrieved chunks, nearest first: `[chunk_id, cosine]`.
- `reader1`, `reader2` — each model's label: `position`, `note`.
- `resolver` — `null` where the readers agree; otherwise the tie-breaker's
  `pick` (1 or 2) and `reason`.
- `ruling` — `null` where the readers agree; otherwise the reviewer's ruling:
  a position, or 1 or 2 for the adopted reader.
- `final` — the final position: `first`, `later`, or `absent`.

## The reading guide

The system prompt of every call, verbatim:

> You read one sentence from a public comment on a federal rule, and five
> passages retrieved from the agency's environmental analysis record for that
> rule. The sentence names or points at something in that record: a section, a
> page, a table, a figure, a finding.
>
> Decide whether the passage the commenter means is among the five:
>
> - "first" - passage 1 is the passage the sentence means.
> - "later" - one of passages 2 to 5 is, and passage 1 is not.
> - "absent" - none of the five is the meant passage.
>
> The meant passage is the record text the sentence is about: the table it
> cites, the finding it disputes, the section it names. A passage on the same
> general topic is not the meant passage unless it holds the specific content
> the sentence points at. If the sentence does not point at any specific record
> content, the label is "absent"; say so in the note.
>
> Reply with one JSON object and nothing else.

Each reply also received a shape instruction naming the exact JSON object to
return (the fields listed under "The columns").
