# The record retrieval: make retrieve, make nli

`make retrieve` finds, for every gate-opening sentence, the nearest passages of
the record documents that `make docindex` loaded. `make nli` then reads each
near pair with a natural-language-inference model and labels every sentence and
comment. The labels say what the record already does with each point: it says
the same thing, it says the opposite, it says something near, or it says
nothing.

## The retrieval

The query is the sentence's comment-view vector (`make embed VIEW=comment`).
The target is each record chunk's vector (`make docindex`). Both come from the
same embedding model, so their cosine compares them. For each distinct sentence
that opens the gate alone, the step stores the 5 nearest chunks in
`doc_retrieval`, nearest first.

Letter sections are not searched. The agency-letters volume holds letters that
commenters sent to the agency. They are not the agency's analysis, so a match
there does not mean the record addresses the point. Run
`make retrieve LETTERS=1` to measure the exclusion: it searches the letters
too, prints how many sentences take a letter chunk first, and writes nothing.

## The NLI reading

A pair is near when its cosine is 0.75 or more. For each near pair, the
cross-encoder reads the chunk as the premise and the sentence as the
hypothesis. It stores three probabilities in `doc_nli`: entailment, neutral,
contradiction. A probability of 0.7 or more is decisive.

The model is `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli`. It
runs on your machine. Install it with `uv sync --group nli`; the first run
downloads it from Hugging Face. The run resumes: a pair with a stored row is
not read again.

## The labels

Each sentence gets one label in `doc_sentence_label`, with the pair that gave
it:

| Label | Meaning | Condition |
|---|---|---|
| `contested` | The record says something the sentence disputes | a near pair reads contradiction |
| `addressed` | The record already says what the sentence says | a near pair reads entailment, none reads contradiction |
| `near` | The record is near but neither entails nor contradicts | near pairs, none decisive |
| `not_addressed` | The record says nothing near the sentence | no near pair |

Each comment gets the strongest label over its gate-opening sentences, in the
order contested, not_addressed, near, addressed (`doc_comment_label`).

## The commands

```
make retrieve DRY=1     count the sentences and chunks, write nothing
make retrieve           the 5 nearest chunks per sentence
make retrieve LETTERS=1 the letter-exclusion figure, write nothing
uv sync --group nli     install the NLI model's dependencies, once
make nli LIMIT=10       a pilot: read 10 pairs, no labels yet
make nli                read every near pair, then build the labels
make nli LABELS=1       rebuild the labels from stored rows, read nothing
```

`THRESHOLD=` changes the near line, `K=` the chunks kept per sentence, and
`MODEL=` names the embedding model when more than one fits.

## The tables

| Table | One row per |
|---|---|
| `doc_retrieval` | sentence and rank: the chunk and the cosine |
| `doc_nli` | read pair and NLI model: the three probabilities |
| `doc_sentence_label` | sentence: the label, its pair, the threshold applied |
| `doc_comment_label` | comment: the strongest label and the sentence that gave it |
