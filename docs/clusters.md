# The clusters and topics

The nine steps end with the substance reading: which comments the agency owes an answer.
The extension past them finds what those comments say, and groups the same claim made
in any words into one cluster, and the clusters into topics. It is code: sentences,
vectors, density clustering (HDBSCAN) and topics from the clusters' centroids, after
eis-analysis's model-free gate clustering. No generative model reads a comment in it.

The steps run after `make score-model-free`. This page describes each step as it is built.

## Step 10: the sentences of the gate set (`make sentences`)

The gate set is the comments whose hybrid gate the model-free reading opens, in the
screen classes A and B1 (`CLASSES=` for others). `make score-model-free CLASSES=A,B1`
scores both classes first.

For each sentence of those comments, as the model-free reading split and scored it
(`mf_sentence_score`), the step writes one row in `gate_sentence_occurrence`:

- the comment;
- which of LAW, EVID, GAP and ALT the sentence reaches 2 on (its gate kinds);
- `opens`: the sentence opens the gate on its own;
- `holds_hit`: the sentence holds a gate hit of the whole comment.

Then one row in `gate_sentence` for each distinct sentence, keyed by `text_key` (two
sentences are the same when they differ only in case, punctuation, spacing, markup or
encoding): its text, its occurrences, the comments it is in, and the same flags over
its occurrences.

**Why `holds_hit`.** The hybrid reading opens some comments only by reading the whole
comment, where a rule pairs words from two sentences. Such a comment has no sentence
that opens the gate on its own. The hit that opened it has a span in the whole
comment's text; the sentences that span falls in are marked, so each gate-open comment
can be represented by a sentence. The whole comment's text is normalised and a
sentence's text is rendered, so the two are joined on their letters and digits alone.
A sentence not found in the whole text, and a hit in no found sentence, are counted in
the run row, not guessed.

**The run row.** `gate_sentence_run` keeps every build's counts: gate-open comments,
sentences, distinct sentences, the comments with a sentence that opens the gate, with a
sentence that holds a hit, with neither, and the sentences and hits not located. A
build replaces the two sentence tables.

The step stops when there is no model-free score, when no comment of the classes has
an open gate, and when a comment's text gives a different sentence from the one that
was scored (its text changed since `make score-model-free` read it).
