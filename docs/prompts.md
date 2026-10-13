# The model prompts, and how to change them

Three steps send text to the language model. Each has one prompt, held in a file in
this repository, and a JSON schema the reply has to satisfy. This page says, for each,
what is sent, where it lives, which file to edit, and how an edit takes effect.

A changed prompt is a new instrument. Every row a model step writes carries the
instrument's name and the model's, so rows made under an edited prompt are
distinguishable from ours, and the figures downstream of that step are not expected
to match `checks/expected.json` any more. That is the point of editing it: run the
step on a sample (`LIMIT=N`), compare its rows with ours in the console, and decide.

## Stance (step 3, `make stance`)

**What is sent.** One call per comment group: a system prompt, and a user prompt
made from a template with two placeholders filled in, `{comment_text}` (the group's
canonical comment) and `{topics_list}` (the active rows of the `topics` table, each
as its name and description). The reply is constrained to a JSON schema with the
sentiment, its strength and the topics with supporting phrases.

**Where it lives.** In the file: the `prompts` table, one active row of kind
`sentiment_topic`, and the `topics` table. Both are seeded by `make schema` from
`seeds/roadless_profile.sql` (the system prompt as prompt `roadless_rescission_v1`,
and the topics) and `seeds/roadless_prompt_v2.sql` (the user template, as prompt
`roadless_rescission_v2`, the active one, which takes its system prompt from v1).
The schema of the reply is `sentiment_topic_response_format` in
`src/pipeline/profile.py`; the rendering is `ProjectProfile.render_user_prompt`
there. The prompt as seeded is readable in
`docs/instruments/stance-roadless-rescission-v2.md`.

**To edit.** Change the template or the system prompt in
`seeds/roadless_prompt_v2.sql` (keep the two placeholders), or a topic's name or
description in `seeds/roadless_profile.sql`. Then load it into the file. The seed
deactivates the active prompt before inserting its own, so it can be run on an
existing file:

```
sqlite3 data/roadless.sqlite < seeds/roadless_prompt_v2.sql
```

A topic is different: `roadless_profile.sql` cannot be run whole on an existing file,
because it also inserts the v1 prompt as active and the file allows one active prompt
per kind. Its topic statements upsert by name, so for an existing file paste the one
topic's `INSERT ... ON CONFLICT` statement into `sqlite3 data/roadless.sqlite`; for a
fresh file, edit it before `make schema`. Then `make stance LIMIT=200`: a run reads
the active prompt when it starts and stamps its id on every row, and a `--resume`
refuses a run whose prompt is no longer the active one. The copy in
`docs/instruments/` is checked against the seeds by `tests/test_prompts_doc.py`, so
update it with the seed (the test says when they differ).

## Substance (step 6, `make score`)

**What is sent.** One call per class A comment: the instrument as the system prompt,
the text of `docs/instruments/substantive-scoring-v3.md` between its heading
`## System prompt` and the line `# SECTION D` (the label above the heading and the
deployment notes below the line are not sent), and as the user message the comment's
own text, or the campaign's shared text for an exemplar reading. The reply is
constrained to `docs/instruments/substantive-scoring-v3.schema.json`.

**Where it lives.** Those two files. `scripts/substance/score_comments.py` reads them
by path at every run; nothing is cached in the database.

**To edit.** Edit the Markdown between the heading and SECTION D, and the schema if
the reply changes shape; `scripts/substance/grade.py` turns the reply into the scores, so a new field
needs its grading there. Then `make score LIMIT=200`. The instrument version a row
carries is `instrument_version` on `substance_scores`.

## Roster (step 8, `make attachments`)

**What is sent.** One call per letter: a comment's own-letter attachment, or, for a
bundle of submissions with no letter of its own, the first page of its first enclosed
file. The text under the heading `## System prompt` in
`docs/instruments/organisation-roster-v1.md` is the system prompt, and the letter's
text, headed by the comment id, the user message. The reply is constrained to
`docs/instruments/organisation-roster-v1.schema.json`.

**Where it lives.** Those two files; `scripts/organisation_roster.py` reads them by
path at every run.

**To edit.** Edit the text under `## System prompt`, and the schema if the reply
changes shape. The roster's rows carry `instrument_version` on
`comment_organisation`; change the version string in the script when the prompt
changes, so the rows say which prompt made them. Then the roster with a `LIMIT`.

## The model and its settings

The model is one for all three steps, named in `.env` (`docs/model-server.md`).
Temperature is 0 everywhere; the stance's parameters are on its prompt row
(`model_parameters`), the substance's in SECTION D of its instrument.
