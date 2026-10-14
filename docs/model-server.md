# The model server

Three steps of the analysis read a language model: the stance classification (step 3),
the substance reading (step 6) and the organisation roster (step 8). All three go through `shared/llm_client.py`, which
speaks the OpenAI chat API to one server, a local one you run or an API. This page
says what that server has to do and how to run or name one.

## What the pipeline sends

Every call is `POST <LLM_BASE_URL>/chat/completions` with:

- `model`: `LLM_MODEL`, the name your server gives the model;
- `messages`: a system prompt and one user message;
- `temperature` 0 and `max_tokens` 8192;
- `response_format` of type `json_schema` where the step wants a structured reply
  (the substance reading, the roster), so the server has to
  support OpenAI structured output;
- the thinking switch off: `chat_template_kwargs` with `enable_thinking: false`, which
  LM Studio, vLLM and llama.cpp honour, and `reasoning_effort: "none"`, which ollama
  honours; the other side ignores the field it does not know. To OpenRouter the switch
  is sent in its own spelling, `reasoning: {"enabled": false}`, and nothing else. The
  instruments were measured with thinking off; with it on the model answers differently
  from the way that was tested, and slowly.
- `Authorization: Bearer <LLM_API_KEY>` when `LLM_API_KEY` is set.
- `provider: {"only": ["<LLM_PROVIDER>"], "allow_fallbacks": false}` when `LLM_PROVIDER`
  is set: on OpenRouter, every call goes to that one provider and fails rather than
  fall back to another, so a run's rows come from one set of weights at one price.

Every reply is stored whole, so the grading can be audited afterwards. The three
variables live in `.env` (copy `.env.example`).

## The model

The pipeline runs any model a server behind the OpenAI chat API serves, named in
`LLM_MODEL`. The three model steps need from it: a reply constrained to a JSON schema
(`response_format` of type `json_schema`), the thinking switch off, temperature 0.
Every row a model step writes is stamped with the model's name, so a file holds rows
from more than one model and says which made each. A model choice is a model choice:
a smaller model runs on a laptop and reads less well; a larger one reads better, is
slow or impossible to run locally, and costs money through an API. Three things a
reader needs to know, and this page keeps current.

**The model we used.** Qwen3.8-27B (https://huggingface.co/Qwen/Qwen3.8-27B; Apache
2.0, 27 billion parameters, 262,144 tokens of context), through a paid API, for every
model step of the analysis published at roadless.org: the 190 million tokens of the
README's model-steps table are more than a local server gets through in the time the
docket allowed. The figures in the method's pages and `docs/first-run.md`, and those
token counts, are from it. It also runs locally: a 4-bit quantisation is 16 to 17 GB
on disk and runs on a machine with 24 GB of memory or more, which is how the pilots
of this repository were made; the full-precision weights need a GPU with about 60 GB.
The measured repeatability of the substance instrument on this model is
65 of 100 readings identical between two runs, so two runs of the pipeline do not
match row for row. The method's pages say what that means for the figures.

**The model this repository's runs use.** Qwen3.8-Flash (`qwen/qwen3.8-flash`),
through a paid API, chosen on 2026-10-13 for cost and speed. OpenRouter posts, beside
each provider's list price, the weighted average price its customers actually pay,
with caching and discounts folded in. On 2026-10-13, for Alibaba International:

| model | input, per 1 M tokens | output, per 1 M tokens |
|---|---|---|
| Qwen3.8-27B | $0.08682 | $2.045 |
| Qwen3.8-Flash | $0.03094 | $0.4696 |

The two model steps whose tokens we counted, at those prices, from the README's
token counts:

| step | 27B | flash |
|---|---|---|
| stance (60.6 M in, 9.4 M out) | $24.48 | $6.29 |
| substance, direct readings (115 M in, 6 M out) | $22.25 | $6.38 |
| total | $46.74 | $12.66 |

The flash is 27 percent of the 27B's cost on this method. The roster's tokens were
not counted and the exemplar and delta readings are inside the substance figure. The
list prices tell a different story (the flash's input is listed four times the
27B's and the method sends twelve tokens in for every one out), because both prompts
put everything but the comment in a fixed prefix that a cache serves, and the
weighted average is what that comes to. The figures of our runs on the
flash are recorded in the README's model-steps table as
they are measured, and the comparison with the 27B on the same comments is made with
`make compare-scores` (`docs/model-free-scoring.md`). Its open weights are
Qwen3.8-Flash-Next (https://huggingface.co/Qwen/Qwen3.8-Flash-Next; 125 billion
parameters, 6 billion active per token, 512 experts; `qwen3.8-flash` as served is
"the official version based on Qwen3.8-Flash-Next with more production features"),
and quantisations of them run locally where the memory allows: the GSQ-RCO GGUF
builds (https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF) hold the
transformer weights in a first shard that has to be resident, 37.6 GB for the 2-bit
build and 47.0 GB for the 3-bit build the card calls the stronger operating point,
and a 28.8 GB n-gram shard that can stay memory-mapped on SSD; a 96 GB Apple Silicon
machine holds either, a 12 GB GPU holds neither. They run unmodified in LM Studio,
ollama and llama.cpp.

**Other models.** Any other model is a matter of putting its name in `.env`. Two
things follow. The instruments were measured on the 27B, so another model's reading
is a different reading: its rows carry its name, the downstream figures are not
expected to match `checks/expected.json`, and `make score-model JSON=dir` with
`make compare-scores` is how the difference is measured on the same comments. And
the thinking switch is spelled differently by different servers; the client sends
the spellings LM Studio, vLLM, llama.cpp and ollama take (above), and a pilot of a
few hundred calls shows in its tokens-out per call whether the server honoured it.
Among the Qwen3 family these two are the ones that run both locally and through an
API; a reader picking another model picks it for their own machine and budget.

## What was tested

The code was tested on Apple Silicon with LM Studio running headless through `lms`,
the path below, and is being run through OpenRouter for the runs of this repository.
The ollama and vLLM sections are written from their documentation and have not been
run against this pipeline; other local servers may behave differently, in the thinking
switch, structured output or the model's name. They will be verified when there is a
chance.

## OpenRouter

The API this repository's runs use. Make a key at https://openrouter.ai/keys, then in
`.env`:

```
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_API_KEY=<your key>
LLM_MODEL=qwen/qwen3.8-flash
LLM_PROVIDER=alibaba
```

`LLM_PROVIDER` pins every call to Alibaba International, the provider whose prices
are in the table above, with fallbacks off: OpenRouter otherwise routes each call to
whichever of a model's providers it chooses, at that provider's price and on that
provider's serving of the weights. The 27B is `qwen/qwen3.8-27b` on the same
provider. OpenRouter reports the cost of every call in its `usage`, and the spend
line each model step prints at exit carries the dollars.

## Together AI

A serverless API that lists the same model. Make a key at
https://api.together.ai/settings/api-keys, then in `.env`:

```
LLM_BASE_URL=https://api.together.ai/v1
LLM_API_KEY=<your key>
LLM_MODEL=<the model's name as Together lists it>
LLM_PROVIDER=
```

`LLM_PROVIDER` stays empty: the provider pin is OpenRouter's request field, and
Together is one provider. Together serves some models only as a stream and answers
a plain request with `400 streaming_required`; the client then streams every call
and assembles the reply, so nothing else changes (`LLM_STREAM=1` streams from the
first call). Together signals a model in high demand with a 429 or a 503 (its
rate-limits page), and the client treats both as the server's pace, as above.
Together reports no cost in its replies, so the spend line at exit carries the
tokens and says the cost was not reported.

## What differs between servers

The same request is not taken the same way everywhere; these are the differences
the client handles, by server, and the reader does not have to:

| | LM Studio, ollama, vLLM, llama.cpp | OpenRouter | Together |
|---|---|---|---|
| thinking off | `chat_template_kwargs.enable_thinking` and `reasoning_effort: "none"`, both sent; each ignores the other's | `reasoning: {"enabled": false}`, OpenRouter's own field, sent alone | the local servers' two spellings; the pilot's tokens out per call show whether they took |
| one provider | not applicable | `provider.only` with fallbacks off, from `LLM_PROVIDER` | not applicable; `LLM_PROVIDER` empty |
| streaming | not needed | not needed | required for some models; the server says so once and the client streams from then on |
| rate limits | none | 429, often from a provider's shared pool; an own provider key lifts it | 429 or 503 |
| cost | none | in every reply's `usage.cost`; the spend line shows dollars | not reported; the spend line shows tokens |
| structured output | `response_format` of type `json_schema` | the same | the same (`response_format` supported) |

## LM Studio, with `lms`

The path this repository was built and run with. Download LM Studio from
https://lmstudio.ai/ and run it once; its command line tool `lms` is then at
`~/.lmstudio/bin/lms`.

```
lms get qwen/qwen3.8-27b -y
lms load qwen/qwen3.8-27b -y
lms server start --port 1234
lms server status
```

`lms get` downloads the quantisation LM Studio picks for your hardware; `lms get
qwen/qwen3.8-27b@q8_0` names one. `lms load` takes `--context-length` and `--gpu`
(`max` for full offload) if the defaults do not suit the machine, and `--parallel N`
lets the server answer N calls at once, which the substance step uses. `lms ps` lists
what is loaded; `lms unload --all` unloads. The server keeps the port it was last
started on; `--port` sets it.

Then in `.env`:

```
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_API_KEY=
LLM_MODEL=qwen/qwen3.8-27b
```

`curl http://127.0.0.1:1234/v1/models` lists the loaded models and confirms the
server is up.

## ollama

Download from https://ollama.com/download. Then:

```
ollama pull qwen3.8:27b
```

ollama serves on port 11434 as soon as it is installed; the OpenAI endpoint is
`/v1`. It needs no key.

```
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_API_KEY=
LLM_MODEL=qwen3.8:27b
```

## vLLM

For a machine with an NVIDIA GPU. Install it in its own Python environment, following
https://docs.vllm.ai/en/latest/getting_started/quickstart/:

```
uv venv --python 3.12 --seed
source .venv/bin/activate
uv pip install vllm --torch-backend=auto
vllm serve Qwen/Qwen3.8-27B --port 8000
```

`vllm serve` downloads the weights from Hugging Face on first use and serves on port
8000 by default. `--api-key <key>` makes it require one; put the same value in
`LLM_API_KEY`.

```
LLM_BASE_URL=http://127.0.0.1:8000/v1
LLM_API_KEY=
LLM_MODEL=Qwen/Qwen3.8-27B
```

## Sizing the run

What each step took on this docket with this model, from our run:

| step | calls | tokens |
|---|---|---|
| stance | one per group of the final partition, 81,569 groups; the per-call figures are from the 44,555 calls of 2026-09-25 | 1,360 in, 211 out a call (60.6 M in, 9.4 M out on the 44,555) |
| substance | 28,176 direct readings | 115 M in, 6 M out |
| roster | 3,002 letters | |

On one local server the substance step is the long one: at a few seconds a reading it
runs for days. Each step resumes where it stopped, so the server can be stopped and
started between sessions.

## A pilot, then the rest of the run

Before a full run, send a few hundred calls and look at what came back:

```
make stance LIMIT=200
```

starts a run, sends its first 200 groups, stores and loads every reply, prints how
many were loaded and how many failed and why, and exits. The console's Steps page
(`make console`) shows the run by status, with its tokens and seconds.

A run is continued, never restarted. `make stance LIMIT=200` again would start a
second run and send the same first 200 groups again; the groups already done are
skipped only within the run that did them. So:

```
make stance-runs
```

lists every run so far, what each loaded, errored and has not sent, and prints the
command that continues the latest one with groups left. That command is

```
make stance RUN=reclass_20261013_214534 LIMIT=200     # the next 200 groups of that run
make stance RUN=reclass_20261013_214534               # the rest of it
```

`LIMIT=N` counts from where the run stopped; `CONCURRENCY=N` sets how many calls are
in flight at most (16 if not given); `RETRY=1` also sends again the groups whose call
errored. A run resumes after an interruption with the same
command, and refuses to continue if the partition was rebuilt since it started,
because its stored calls name groups that no longer exist; then a new run.

**Rate limits.** A shared API throttles on concurrency: Alibaba through OpenRouter
answered 429 `Throttling.Concurrency` the moment the pilot put 16 calls in flight.
The client therefore never starts there. Calls in flight start at one and, while
the server has never pushed back, double per five clean answers towards
`CONCURRENCY`, leaving at least a tenth of a second apart; a 429 pauses every worker
for the server's `Retry-After` or two seconds, doubling to a minute on repeats,
halves the calls in flight, and marks the level that drew it: from then on the climb
is one per five clean answers to just under that level and one per fifty above it.
A 429 is the server's pace, not a failed call: it
costs none of a call's five retries, and a call gives up only after ten minutes of
waiting on them. A lost connection, the network down or the API's name not
resolving, is handled the same way: every worker waits as one, doubling to a
minute between tries, for up to ten minutes, and the run aborts only after that,
with what was stored kept and `make stance RUN=<id>` continuing it. The log says so once per pause (`rate limited by ...: every call
waits 2s, calls in flight capped at 4`), not once per worker, and every progress
block says where the climb stands (`calls in flight 6 of 16`). `CONCURRENCY` is the
most the run will ever ask for, not where it begins.

A run's rows carry one model name. `make stance RUN=<id>` refuses to continue a run
under a changed `LLM_MODEL`, including the same weights under another provider's
name, and says so; a new run (`make stance LIMIT=200`) starts under the new name.

**Refusals.** A provider may refuse a comment's text outright: Alibaba's content
inspection, passed through by Together, answered `400 DataInspectionFailed: Input
text data may contain inappropriate content` to 690 of the 78,953 groups of this
docket on 2026-10-14, ordinary public comments every one. The runner records such
an answer as the error kind `refused`, keeps it with the comment, and never sends
it again (`RETRY=1` leaves them out); the closing block counts them and gives the
query that lists them. To classify them through another server, put that server
in `.env` and start a run confined to them:

```
make stance REFUSED_IN=<the run that refused them>
```

It is a new run under the new model name, over only those groups, and `make
stance-runs` lists it beside the others. `make stance-refused RUN=<the run>` writes
`docs/refused-<the run>.md`: every refused group with the provider's message, the
comment id, how many comments the group stands for, and the text in full, so the
refusals can be read against what was sent. Ours is in `docs/`.
