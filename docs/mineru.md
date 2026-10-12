# MinerU, for the OCR of scanned attachments

Step 8 reads every attachment file. `attachment_text.py` reads PDFs with `pdftotext`,
and an image-only PDF, a scan, comes out with no text. `attachment_ocr.py` sends the
scans that can hold a letter nobody has read (enclosed comment packets, own letters of
two or more pages, a one-page own letter on a comment with under 100 characters of its
own text) to a MinerU server and stores the text it returns. On this docket that was 343
files and 806 pages, at about ten seconds a page.

MinerU (https://github.com/opendatalab/MinerU) is a document parser with an HTTP API.
This repository uses MinerU 4; our own run used 3.4.4, whose API MinerU 4 removed, and
the 3.x server is not supported here. It is installed with pip, in its own Python
environment, never with Docker.

## Install

MinerU runs on Python 3.10 to 3.14; the project recommends 3.12 for a new environment.

```
uv venv --python 3.12 ~/mineru
source ~/mineru/bin/activate
uv pip install -U "mineru>=4.0,<5"
mineru version --json
```

The base package includes the ONNX small-model runtime; on Apple Silicon it includes
Torch. Nothing more is needed for the OCR.

## Models

The OCR runs on MinerU's small models, its `basic` tier, with no vision language model:

```
mineru-kit models download --tier basic
mineru-kit models verify --tier basic
mineru-kit models show
```

The models go under `~/.mineru/models`. If Hugging Face is unreachable, `export
MINERU_MODEL_SOURCE=modelscope` before downloading switches the source.

## Run

```
mineru-kit api-server --host 127.0.0.1 --port 8000 --tier basic
```

MinerU's default port is 8000. Run it on any port you like and put that port in
`MINERU_BASE_URL` in `.env`:

```
MINERU_BASE_URL=http://127.0.0.1:8000
MINERU_API_KEY=
```

`--api-key <key>` makes the server require a bearer key; put the same value in
`MINERU_API_KEY`. The server documents its API at `http://127.0.0.1:8000/docs`, and
`curl http://127.0.0.1:8000/v1/health` says it is up.

The server keeps its task state in memory; a restart forgets the tasks in flight.
`attachment_ocr.py` writes each file's text as soon as it arrives and resumes where it
stopped, so the server can be restarted between runs.

## What the step sends

For each pending file, `POST /v1/tasks` with the PDF, `tier=basic` and `ocr_mode=ocr`;
the returned status URL is polled every ten seconds to a terminal state; the Markdown of
the result is read, its image references and HTML tags removed, and stored in
`comment_attachment_text.pdf_text` with `pdf_ocr` set, so the methodology can say which
letters were read from scans. A file MinerU reads as empty is stored with no text and
`pdf_ocr` set, a blank or illegible scan recorded as read. A task that fails is listed at
the end with the server's error and the run exits non-zero; its row is untouched and the
next run retries it. A server that cannot be reached stops the run before it starts.

## Hardware

The `basic` tier runs on CPU. On Apple Silicon MinerU recommends 16 GB of unified
memory; a machine with a supported GPU is faster but not needed for this step.
