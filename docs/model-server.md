# The model server

Four steps of the analysis read a language model: the stance classification (step 3),
the citation afterstep of the entity tagging (step 4), the substance reading (step 6) and
the organisation roster (step 8). All four go through `shared/llm_client.py`, which
speaks the OpenAI chat API to one server you run locally. This page says what that
server has to do and how to run one.

## What the pipeline sends

Every call is `POST <LLM_BASE_URL>/chat/completions` with:

- `model`: `LLM_MODEL`, the name your server gives the model;
- `messages`: a system prompt and one user message;
- `temperature` 0 and `max_tokens` 8192;
- `response_format` of type `json_schema` where the step wants a structured reply
  (the substance reading, the roster, the citation afterstep), so the server has to
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

Qwen3.8-27B, Apache 2.0, 27 billion parameters, 262,144 tokens of context
(https://huggingface.co/Qwen/Qwen3.8-27B). It is the model of the reference figures. A 4-bit quantisation is 16 to 17 GB on disk and runs on a machine with
24 GB of memory or more; the full-precision weights need a GPU with about 60 GB.

The measured repeatability of the substance instrument on this model is 65 of 100
readings identical between two runs, so two runs of the pipeline do not match row for
row. The method's pages say what that means for the figures.

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

What each step took on this docket in the reference run:

| step | calls | tokens |
|---|---|---|
| stance | 44,555 | 60.6 M in, 9.4 M out |
| citation afterstep | 302 resolutions | |
| substance | 28,176 direct readings | 115 M in, 6 M out |
| roster | 3,002 letters | |

On one local server the substance step is the long one: at a few seconds a reading it
runs for days. Each step resumes where it stopped, so the server can be stopped and
started between sessions.
