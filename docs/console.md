# The console

A browser of `data/roadless.sqlite`: what the analysis found, and what the steps
wrote. It is not the analysis: the nine steps run from `make`, and the console
launches nothing. It opens the file with SQLite's `query_only` pragma, so nothing
typed into it can write, and it can be open while a step is writing (the file is in
write-ahead-log mode; readers do not block the writer or wait for it). The Topics page
writes two things: the choice of a case for each model (the same write as `make choose`)
and the concern map (the same write as `make concern-map`).

```
make console
```

prints a local URL (port 8501 unless taken); open it in a browser. The sidebar names
the file, its size, when it was last written, and the size of its write-ahead log,
which is non-zero while a step is writing or until SQLite folds the log back into the
file.

## The eleven pages

The first five show the results. Each section appears as soon as its step has run, and
a section whose step has not says which `make` target fills it. Their figures are read
once and kept until the file changes, so a page reopens at once and shows a step's new
rows as soon as it writes them. Most of them count two ways: comments, every record
with text, and letters, the comment groups of `make groups`, where every copy, shared
body, family and campaign is one letter however many people sent it.

**Overview.** The docket's records, with text, withdrawn and blank; the unique letters
and the comments by the kind of letter they sent (a unique letter, an exact copy, the
same body, a small family, a campaign); the comments and letters of each stance, with
what the stance means for this proposal; the screen's three classes; and each
substance reading in one row per screen class it read: the letters scored, the gate open, the mean
strength and the letters at each answerability level.

**Stance and topics.** `make stance`'s result: the
stance of the comments and the letters, how firmly each is held, the topics by
comments and letters with the model's mean confidence, each topic's split by stance,
the topics raised together, the comments a day by stance, and the received and posted
dates. Then any topic's letters, most-sent first, filtered by stance, each with the
phrases the model quoted for the topic and opening to its text.

**Coordination.** The exact copies and the shared bodies of `make dedup`; the comments
by the kind of letter they sent; the daily wave, each day's comments that head their
own letter against those that repeat one; and the campaigns, largest first, with the
distinct texts in each, the members who added words of their own, the organisation
`make orgs` found and on what basis, and the stance, each opening to its letter.

**Places and citations.** The strict layer of `make tag`, so every count traces to a matched word: the comments that name a
national forest, a roadless area, a species, cite a legal authority or a reference,
and that name none of them; the forests, areas and species named most; the states
commenters sign from; the legal authorities by family (every way of writing a citation
rolled up to the instrument it cites), whether the agency's record cites it, and each
family's variants as written; the references cited. Then the letters that name any one
forest, area, species, authority or reference, most-sent first, with the words as
written; and a random draw of comments that name nothing.

**Substance.** The floor (floored, surviving, and the four detectors), the screen's
classes, and either reading, filtered by screen class (class A, and B1 when
`make score-model-free CLASSES=B1` has read it): the rules of `make score-model-free` under the
newest rule set, or the model of `make score-model` with an answerability run of
`make rate`. One per letter by default (a letter's highest-scored comment), so a
campaign's copies do not outweigh a unique letter. The letters scored, the gate open,
the mean strength, the A1 letters; the strength and the bands; each of the eight
dimensions by level, with its meaning and how many reach 2 or 3; answerability against
the band; for the rules, on request, every rule that fired by the comments it fired
on. Then every scored comment, filtered by band, gate, answerability level, stance and
a dimension's level, strongest or weakest first, twenty to a page: its strength, band,
gate and the dimensions that opened it, its answerability, its eight levels, its
letter and stance, opening to its text and its evidence (the rules' hits by dimension
with the words they matched; the model's rationale).

**Topics.** The path from the sentences to the concern map, in five stages
(`docs/topics-guide.md`). Status lines at the top show each stage as done, next or
waiting, with its figure from the file. For the next stage, they show the command to run.

- **Guide** shows `docs/topics-guide.md`, with its screenshots: the five stages, the four
  checks, how to read a case, what the reference run found, the commands and the glossary.
- **Stage 4: Best case of each model** shows the cases of one model on a chart. Each point
  is a case, with its number from the table. A red ring marks a cluster of 1,000 or more
  sentences. A black ring marks the choice. Click a point to select the case. A note and a
  button record the selected case as the model's choice.
- **Stage 5: Concern map** shows the two choices of stage 4, and no other case. A table
  gives each cluster of the first choice, the matching cluster of the second, and the part
  of its sentences that stays together. The most split clusters are at the top. Click a
  row to read the two clusters side by side. A note and a button under each choice record
  it as the concern map.
- **What the stages found** shows the result of each stage. Stage 1: the gate-opening
  sentences by gate kind, and how each gate-open comment shows in the sentences. Stage 2:
  the vectors of each model and view. Stage 3: the cases of both models on one chart. The
  concern map: its topics by the comments that they cover, the 30 clusters that the most
  comments hold, and the number of clusters of each comment.
- **Read a case** shows the case selected in stage 4, or the concern map if no case is
  selected, or another case. Charts show the
  topics by gate kind, the cluster sizes, the topic cut and a map of the clusters. Each
  topic opens to its clusters, each with its most typical sentence. Open a cluster to
  read each of its sentences in full. A switch under a sentence lists the comments that
  hold it. Each comment opens to its full text.

The other five look into the file.

**Comment.** One comment id (`FS-2025-0001-nnnnn`): its text, then the comment as the
analysis read it: its letter (unique, or one of how many sent, its text family and the
campaign's organisation), its stance and topics with the model's phrases, what it
names, its screen class, and each reading's score with its evidence. Under that, in
one section, every row the steps hold about it, one table each: the attachment files,
the hash row, the
near-duplicate group, the text family and the comment group, the active stance and
its topics, the entity scan state and the dictionary matches, the named entities, the
floor, the screen, the substance score and its parts, the answerability, the
attachment text and kind and count, the roster row, the campaign's organisation, and its readings in every comparison run. A
table with no row for the comment says "no row".

**Steps.** Every `make` target in the README's run order, the attachments last, each
with the rows it has written: the
corpus's records and files, the hashes, the n-grams and near-duplicate groups, the
named entities by type, the six entity tables by strict and loose mode, the floor's
floored comments and survivors and its four detectors, the families and the group partition by kind, the
screen classes, the stance run's latest items by status (received, loaded, error)
with its tokens and seconds, the substance scores by how they were reached and by
band, the answerability levels, the attachment text by rendition, the file kinds, the
roster by sender and stance, the campaign organisations by basis. A step that has
written nothing says "not run". Reload the page for current counts; it caches
nothing.

**Compare.** Every `make score-model-compare` run, newest first, with the code it ran
(the git commit, and whether tracked files had uncommitted changes), the model, the
server, the instrument, the rule set, the run whose comments it read again if any, and
how many readings it kept. Under it, one run: its model reading against its rules
reading, and any call that failed. Then any two readings of any two runs, A and B,
each a run and a method (model or model-free), set side by side on the comments both
read. Either comparison is the same set of tables: per dimension, how many agree,
which side reads higher and each side's mean level; the gate, all eight levels, the
band and the strength; then every comment whose gate differs, and every one whose
gate agrees and a level does not, with both gates, both strengths and the levels that
differ. Each of those comments opens to its text and its eight dimensions, each with
both levels, a mark where they differ, and each side's evidence for it (the model's
span and the rule that graded it; the rules' rule and the words it matched), then the
model's rationale and the rules' moves. The model's reading of one run against the model's reading of a later one,
or the rules' against the rules', is how a change to the code, the instrument, the
rules or the model is seen against what was read before it.

**Tables.** Any table or view, a hundred rows at a time from any offset, with the
table's row count. Views are not counted, because two of them walk the whole file.

**Query.** SQL typed in, run read-only; the first 10,000 rows shown and downloadable
as CSV. A statement that would write is refused by SQLite with "attempt to write a
readonly database". The registered functions of `shared/db.py` (`regexp`,
`regexp_count`, `md5`, `authority_family_key`, `stddev`) are available.

## Where it lives

`console/queries.py` holds every query, with no Streamlit in it; `console/results.py`
is the five results pages, `console/app.py` the rest and the sidebar, and
`console/view.py` what they share (the read-only connection, the cached query, the
vocabulary's labels, a comment's text shown as prose). `tests/test_console.py` makes a
temporary file with `make schema`'s script, runs every query on it, fills it with a
few rows of every step and renders each page through Streamlit's test harness, the
script run in-process with the file path pointed at the temporary file. Streamlit is the
`console` dependency group of `pyproject.toml`, which the `dev` group includes, so
`uv sync` installs it and `uv run pytest` covers it.
