# The NLI reading

`nli_reading.jsonl` is the reviewed table of the NLI reading test: 100 read
pairs from `doc_nli`, each judged by two independent readers and settled. The
test measures the cross-encoder's agreement with readers on its own calls. Its
result is why the cross-encoder's contradiction calls are not used as-is.

## How the pairs were drawn

- All 57,815 read pairs of `doc_nli`, stratified by the cross-encoder's own
  call at the 0.7 line: 30 contradiction, 30 entailment, 40 neutral.
- Per stratum, one pair per sentence (the lowest chunk id with that call), and
  one sentence per comment group, so a letter campaign fills at most one card.
- Each stratum drawn at even steps over the key order.

## How the labels were made

- The readers saw the passage (with its document title and pages) and the
  sentence. They did not see the probabilities, the cosine, or each other.
- `reader1`: glm-5p3 (temperature 0)
- `reader2`: qwen3p8-max (temperature 0)
- Where the readers disagree (8 of 100), claude-haiku-5-5 read the pair and
  both labels and picked one as a tie-breaker. The reviewer then ruled every
  disagreement; the ruling is the final label. The reviewer agreed with the
  tie-breaker on 6 of 8.

## The figures

- Coder kappa on the label: 0.822.
- The cross-encoder against the final labels, kappa per label: contradiction
  0.157, entailment 0.485; three-way 0.270.
- The cross-tab, cross-encoder (rows) against the final label (columns):

  | | entailment | contradiction | neutral |
  |---|---|---|---|
  | entailment | 16 | 2 | 12 |
  | contradiction | 0 | 5 | 25 |
  | neutral | 6 | 1 | 33 |

- Final labels over the 100: neutral 70, entailment 22, contradiction 8.

The cross-encoder's contradiction calls agree with readers on 5 of 30: it
calls contradiction where the passage is on a nearby point without disputing
the sentence. Its neutral calls hold (33 of 40).

## The columns

One JSON object per line:

- `item_id` — `t2-<text_key>-<chunk_id>`.
- `text_key` — the sentence's key in `gate_sentence`.
- `chunk_id` — the passage's key in `doc_chunks`.
- `nli` — the cross-encoder's call at the 0.7 line: `entailment`,
  `contradiction`, or `neutral`.
- `p` — the stored probabilities: `[entailment, neutral, contradiction]`.
- `pair` — the card as the readers saw it: the passage, then the sentence.
- `reader1`, `reader2` — each model's label: `label`, `note`.
- `resolver` — `null` where the readers agree; otherwise the tie-breaker's
  `pick` (1 or 2) and `reason`.
- `ruling` — `null` where the readers agree; otherwise the reviewer's final
  label.
- `final` — the final label: the readers' agreed label, or the ruling.

## The reading guide

The readers and the tie-breaker worked under this guide, verbatim:

> You read one passage from the agency's environmental analysis record for a
> federal rule, and one sentence from a public comment on that rule.
>
> Decide what the passage does to the sentence:
>
> - "entailment" - the passage says what the sentence says. A reader of the
>   passage would take the sentence to be true.
> - "contradiction" - the passage says something the sentence disputes. The
>   two cannot both be right.
> - "neutral" - neither. The passage is on another point, or on the same
>   point without confirming or disputing the sentence.
>
> Judge only what the passage states. Do not use outside knowledge of the
> rule or the record.
