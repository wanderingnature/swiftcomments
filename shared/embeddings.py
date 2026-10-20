"""The embedding server: one request of texts, their vectors back.

Ported from eis-analysis src/clients/fireworks_embeddings.py, which called
Fireworks serverless for qwen3-embedding-8b at a fixed URL with
FIREWORKS_API_KEY. Here the server is the reader's, from .env, as the model
server is (shared/instrument.py): any server speaking the OpenAI embeddings
API, `POST <EMBED_BASE_URL>/embeddings`.

    EMBED_BASE_URL   up to and including /v1, e.g. https://api.fireworks.ai/inference/v1
    EMBED_API_KEY    sent as a Bearer header when set
    EMBED_MODEL      the server's name for the model, e.g. accounts/fireworks/models/qwen3-embedding-8b

The model is Qwen3-Embedding-8B (the operator, 2026-10-20), the model of
eis-analysis, at its 1,024 dimensions. A step that needs the server and finds
no EMBED_BASE_URL or EMBED_MODEL stops.
"""
from __future__ import annotations

import os
import sys
import time

import requests

DIMENSIONS = 1024
# Texts per request.
BATCH = 128
# Tries per request: a rate limit (429), 408/409, a 5xx or a timeout is tried
# again after 2s, 4s, ...; any other 4xx fails at once.
TRIES = 5


def server() -> tuple[str, str, str]:
    """(base URL, API key, model) from .env; stops when the URL or the model is missing."""
    base = (os.environ.get("EMBED_BASE_URL") or "").strip().rstrip("/")
    model = (os.environ.get("EMBED_MODEL") or "").strip()
    key = (os.environ.get("EMBED_API_KEY") or "").strip()
    missing = [n for n, v in (("EMBED_BASE_URL", base), ("EMBED_MODEL", model)) if not v]
    if missing:
        raise SystemExit(f"{' and '.join(missing)} not set: put the embedding server in .env"
                         " (see .env.example and docs/clusters.md)")
    if base.endswith("/embeddings"):
        base = base[: -len("/embeddings")]
    return base, key, model


def embed_batch(texts: list[str], base: str, key: str, model: str) -> tuple[list[list[float]], int]:
    """One request (at most BATCH texts): the vectors in the order of `texts`,
    and the input tokens the server reports (0 when it reports none)."""
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    for attempt in range(TRIES):
        try:
            r = requests.post(f"{base}/embeddings", timeout=120, headers=headers,
                              json={"model": model, "input": texts, "dimensions": DIMENSIONS})
            if r.status_code in (408, 409, 429) or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}: {r.text}", response=r)
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as e:
            if attempt == TRIES - 1:
                raise
            print(f"embeddings: {e} - try {attempt + 2}/{TRIES} in {2 * (attempt + 1)}s", file=sys.stderr)
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code >= 400:
            raise SystemExit(f"embeddings: HTTP {r.status_code} from {base}/embeddings: {r.text}")
        body = r.json()
        data = sorted(body["data"], key=lambda d: d["index"])
        if len(data) != len(texts):
            raise RuntimeError(f"embeddings: sent {len(texts)} texts, got {len(data)} vectors")
        if any(len(d["embedding"]) != DIMENSIONS for d in data):
            raise RuntimeError(f"embeddings: the server returned vectors of another length than {DIMENSIONS}")
        return [d["embedding"] for d in data], int((body.get("usage") or {}).get("prompt_tokens") or 0)
    raise RuntimeError("unreachable")
