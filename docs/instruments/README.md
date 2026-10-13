# The prompts, by step

Three steps send text to the model. These are the prompts, one file each. The files
are what the scripts read, so a change here is a change to the run; `../prompts.md`
says how to make one and how it takes effect.

**This is the prompt for step 3, the stance (`make stance`):**
`stance-roadless-rescission-v2.md`. A copy for reading of the prompt the seeds
load into the file (`seeds/roadless_profile.sql`, `seeds/roadless_prompt_v2.sql`);
the system prompt and the user template, with the comment and the topic list filled
in at run time.

**This is the prompt for step 6, the substance reading (`make score`):**
`substantive-scoring-v3.md`. The text between its heading `## System prompt` and the
line `# SECTION D` is sent as the system prompt, word for word, with the comment's
own text as the user message; the label above the heading and SECTION D below the
line are for the person running it. The reply must match
`substantive-scoring-v3.schema.json`.

**This is the prompt for step 8, the roster (`make attachments`):**
`organisation-roster-v1.md`. The text under its heading `## System prompt` is sent as
the system prompt, with the letter's text as the user message; the paragraph above
the heading describes the population and what code does with the reply. The reply
must match `organisation-roster-v1.schema.json`.
