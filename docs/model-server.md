# The model server

Three steps of the analysis read a language model: the stance classification (step 3),
the substance reading (step 6) and the organisation roster (step 8). All three go through `shared/llm_client.py`, which
speaks the OpenAI chat API to one server you run locally. This page says what that
server has to do and how to run one.

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
  honours; the other side ignores the field it does not know. The instruments were
  measured with thinking off; with it on the model answers differently from the way that
  was tested, and slowly.
- `Authorization: Bearer <LLM_API_KEY>` when `LLM_API_KEY` is set.

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
through a paid API, chosen on 2026-10-13: it answers faster, and its output tokens
cost less than half the 27B's, which makes a result possible in hours for a reader
who cannot run a model locally. It is not the cheaper model for this method. At
OpenRouter's prices of that day, the 27B at $0.039 in and $1.25 out per million
tokens and the flash at $0.15 in and $0.47 out, the two model steps whose tokens we
counted cost, from the README's token counts:

| model, price per 1 M tokens in / out | stance (60.6 M in, 9.4 M out) | substance, direct readings (115 M in, 6 M out) | total |
|---|---|---|---|
| Qwen3.8-27B, $0.039 / $1.25 | $14.11 | $11.98 | $26.10 |
| Qwen3.8-Flash, $0.15 / $0.47 | $13.51 | $20.07 | $33.58 |

The flash is cheaper on output and dearer on input, and the method sends twelve
tokens in for every one out, so the input price decides the bill: the flash saves 60
cents on the stance, where the output share is highest, and costs $8 more on the
substance reading, 29 percent more over the two. The roster's tokens were not counted
and the exemplar and delta readings are inside the substance figure. The figures of
our runs on the flash are recorded in the README's model-steps table as
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
expected to match `checks/expected.json`, and `make score JSON=dir` with
`make compare-scores` is how the difference is measured on the same comments. And
the thinking switch is spelled differently by different servers; the client sends
the spellings LM Studio, vLLM, llama.cpp and ollama take (above), and a pilot of a
few hundred calls shows in its tokens-out per call whether the server honoured it.
Among the Qwen3 family these two are the ones that run both locally and through an
API; a reader picking another model picks it for their own machine and budget.

## What was tested

The code was tested on Apple Silicon with LM Studio running headless through `lms`,
the path below. The ollama and vLLM sections are written from their documentation and
have not been run against this pipeline; other local servers may behave differently,
in the thinking switch, structured output or the model's name. They will be verified
when there is a chance.

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
| stance | 44,555 | 60.6 M in, 9.4 M out |
| substance | 28,176 direct readings | 115 M in, 6 M out |
| roster | 3,002 letters | |

On one local server the substance step is the long one: at a few seconds a reading it
runs for days. Each step resumes where it stopped, so the server can be stopped and
started between sessions.

## Proving the server with a pilot

Before a full run, send a few hundred calls and look at what came back:

```
make stance LIMIT=200
```

sends 200 groups, stores and loads every reply, prints how many were loaded and how
many failed and why, and exits. The closing lines give the `--resume` command that
sends the rest. The console's Steps page (`make console`) shows the same run by
status, with its tokens and seconds.
