"""The single OpenAI-compatible chat client — one place, reused everywhere.

This module is the one path. Every caller that talks to an
OpenAI-compatible endpoint goes through `ChatClient`.

Responsibilities, in one place:
- **the server** — one, the reader's, from .env: `LLM_BASE_URL`,
  `LLM_MODEL`, and `LLM_API_KEY` sent as a Bearer token when set, nothing when not.
  docs/model-server.md says how to run one.
- **retry** — 429 (rate limit), 408/409, 5xx, timeouts, and truncated JSON are retried with
  backoff; a real 4xx (400/422 bad request/schema) fails fast.
- **structured output** — pass a JSON Schema and get back the parsed object (the endpoint is
  handed an OpenAI `response_format: json_schema`); omit it and get the raw text.
- **spend** — every answered call's `usage` is summed on the client (calls, tokens, and a
  per-call `cost` when the server reports one), and every client that made a call prints
  its `spend_line()` when the process exits — a failed or aborted run included — so every
  LLM step's log carries what it cost.
"""

import atexit
import json
import os
import sys
import threading
import time

import requests
from typing import Any


class TruncatedResponse(RuntimeError):
    """The server stopped generating before the model was done (finish_reason=length).

    Never repaired, never salvaged, never retried — a truncated response is a lost response.
    House rule: nothing in this project is truncated.
    """


class EndpointNotReady(RuntimeError):
    """The server has no live model behind the name — every call in the run will
    fail identically, so the caller must abort rather than work the queue."""


def _log(msg):
    # Diagnostics go to stderr so callers parsing stdout are unaffected; a
    # silent retry loop (5 x 300s timeout) is indistinguishable from a hang.
    print(f"[llm] {msg}", file=sys.stderr, flush=True)


def is_hybrid_reasoner(model: str) -> bool:
    m = (model or "").lower()
    return "qwen3" in m or "deepseek" in m


def no_thinking(model: str, base_url: str = "") -> dict:
    """Request fields that turn thinking OFF for hybrid reasoning models (the
    Qwen3 family, DeepSeek). Empty for every other model.

    Both spellings travel together: `chat_template_kwargs.enable_thinking` /
    `.thinking`, which LM Studio, vLLM and llama.cpp take, and `reasoning_effort:
    "none"`, which ollama takes; each server ignores the one it does not know
    (LM Studio answers a request carrying `reasoning_effort` normally, checked
    2026-10-12). A top-level `reasoning` object is never sent: LM Studio hangs on
    it — every call timing out at 180s, five retries deep, measured 2026-09-19.

    This is not a tuning knob. The v3 instrument's repeatability was measured
    with thinking off; with it
    on the model answers a different way than the one that was tested, and the
    reasoning tokens are paid for in time.
    """
    if not is_hybrid_reasoner(model):
        return {}
    return _thinking_off_fields(model, base_url)


# Every spelling of the thinking switch. A body built elsewhere must not reach the
# server carrying another provider's.
THINKING_FIELDS = ("chat_template_kwargs", "reasoning", "reasoning_effort")


def thinking_off(body: dict, model: str, base_url: str) -> dict:
    """`body` with the thinking-off fields and no other spelling of them.

    For a request body built elsewhere — the generated batch files, the packed
    runner — which `complete()` cannot build itself.
    """
    out = {k: v for k, v in body.items() if k not in THINKING_FIELDS}
    out.update(no_thinking(model, base_url))
    return out


def _thinking_off_fields(model: str, base_url: str) -> dict:
    return {"chat_template_kwargs": {"enable_thinking": False, "thinking": False},
            "reasoning_effort": "none"}


# The max_tokens every request carries unless the body sets its own. It is a
# MEMORY RESERVATION, not an output budget: without one, a server reserves the
# model's whole context for each request, fits few beside the 27B's weights on
# one GPU, and queues the rest: with four calls in parallel, the time to first
# token is many times longer with no max_tokens, for identical outputs. 8192 is twice the longest output any
# task has produced (extract: 15,227 chars ≈ 4,000 tokens on the largest
# comment), and finish_reason=length still raises TruncatedResponse, so nothing
# is cut silently.
DEFAULT_MAX_TOKENS = 8192


_CLIENTS = []   # every ChatClient made in this process, for the exit spend report


@atexit.register
def _print_spend():
    for client in _CLIENTS:
        if client.calls:
            print(client.spend_line(), flush=True)


def _require_env(name: str) -> str:
    value = (os.environ.get(name) or "").strip()
    if not value:
        raise RuntimeError(
            f"{name} is not set: the model server is configured in .env"
            " (see .env.example and docs/model-server.md).")
    return value


class ChatClient:
    def __init__(self, base_url=None, model=None, *, api_key=None, timeout=300, max_retries=5,
                 max_tokens=DEFAULT_MAX_TOKENS, log=None):
        self.base_url = (base_url or _require_env("LLM_BASE_URL")).rstrip("/")
        self.model = model or _require_env("LLM_MODEL")
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_tokens = max_tokens
        # Where retry and slow-call diagnostics go: stderr by default, or a
        # caller's run log so they sit beside the lines they explain.
        self._log = log or _log
        self._headers = self._auth_headers(api_key)
        # The run's spend, summed from each answered call's usage (worker threads share
        # one client). cost stays None until a call reports one.
        self._spend_lock = threading.Lock()
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost = None
        _CLIENTS.append(self)

    def _add_usage(self, payload):
        usage = (payload.get("usage") or {}) if isinstance(payload, dict) else {}
        with self._spend_lock:
            self.calls += 1
            self.prompt_tokens += usage.get("prompt_tokens") or 0
            self.completion_tokens += usage.get("completion_tokens") or 0
            if usage.get("cost") is not None:
                self.cost = (self.cost or 0.0) + float(usage["cost"])

    def spend_line(self):
        """The run's spend in one line. A server with no auth header is the local box
        and costs nothing; one with a key that reports no cost says so rather than guess."""
        if self.cost is not None:
            cost = f"${self.cost:.4f}"
        elif not self._headers:
            cost = "$0 (local)"
        else:
            cost = f"cost not reported by {self.base_url}"
        return (f"spend: {self.calls:,} calls, {self.prompt_tokens:,} tokens in,"
                f" {self.completion_tokens:,} out, {cost} ({self.model})")

    @staticmethod
    def _auth_headers(api_key):
        """Bearer auth when a key is given or LLM_API_KEY is set; none otherwise
        (LM Studio and ollama need none)."""
        key = api_key or (os.environ.get("LLM_API_KEY") or "").strip()
        if key:
            return {"Authorization": f"Bearer {key}"}
        return {}

    def post(self, body):
        """Low-level: POST a fully-formed chat-completions body through the one authed,
        retried path, returning the parsed JSON payload (choices AND usage intact).

        This is the primitive `complete()` is built on, and the path callers that need the
        token usage or the raw envelope (the local batch runner)
        go through — so auth and retry live here alone and nowhere else. `body` may omit
        `model`; the client's model is injected. Retries 429/408/409/5xx/timeouts; a real
        4xx fails fast; a persistent failure re-raises the last exception."""
        if "model" not in body:
            body = {"model": self.model, **body}
        if "max_tokens" not in body:
            body = {**body, "max_tokens": self.max_tokens}  # see DEFAULT_MAX_TOKENS
        return self.request("/chat/completions", body)

    def request(self, path, body):
        """POST `body` to `<base_url><path>` through the one authed, retried path and
        return the parsed JSON — `post()` for chat completions. The body is sent as
        given. Retry rules are post()'s."""
        last = None
        attempt = 0
        while attempt < self.max_retries:
            t0 = time.monotonic()
            try:
                r = requests.post(f"{self.base_url}{path}", json=body,
                                  headers=self._headers, timeout=self.timeout)
                r.raise_for_status()
                dt = time.monotonic() - t0
                if dt > 60:
                    self._log(f"slow call: {dt:.0f}s from {self.base_url}")
                payload = r.json()
                self._add_usage(payload)
                return payload
            except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
                last = exc
                dt = time.monotonic() - t0
                # Fail fast on a genuine 4xx (bad request / schema); retry 429/408/409.
                # The server's body says WHY (bad schema, context overflow,
                # unknown model, overload) — a bare "N Client/Server Error" is
                # undiagnosable. Carry it in every log line and raised error.
                detail = ""
                if isinstance(exc, requests.HTTPError):
                    sc = exc.response.status_code
                    # The status and the body, verbatim: what the server said.
                    detail = f" — HTTP {sc} " + (exc.response.text or "").strip()
                    if 400 <= sc < 500 and sc not in (408, 409, 429):
                        raise requests.HTTPError(
                            f"{exc}{detail}", response=exc.response) from None
                if attempt < self.max_retries - 1:
                    wait = 2.0 * (attempt + 1)
                    self._log(f"{type(exc).__name__} after {dt:.0f}s from"
                         f" {self.base_url} — retry"
                         f" {attempt + 2}/{self.max_retries} in {wait:.0f}s"
                         f"{detail}")
                    time.sleep(wait)
                else:
                    self._log(f"{type(exc).__name__} after {dt:.0f}s from"
                         f" {self.base_url} — retries exhausted, raising"
                         f"{detail}")
                    if detail:
                        raise requests.HTTPError(
                            f"{exc}{detail}", response=exc.response) from None
                attempt += 1
        if last is None:
            raise RuntimeError(f"no attempt was made against {self.base_url}")
        raise last

    def complete(self, *, system=None, user, schema=None,
                 temperature: float = 0, with_usage=False) -> Any:
        """One authed, retried chat completion.

        Returns the parsed dict when `schema` is given (structured output), else the raw
        content string. Retries transient failures; raises on a real 4xx or after retries.

        `with_usage=True` returns `(result, usage)` where usage is the response's token
        accounting dict (`prompt_tokens` / `completion_tokens` / `total_tokens`, or {} if
        the server omitted it) — for cost/throughput estimation.

        NOTHING IS TRUNCATED. The `max_tokens` sent (DEFAULT_MAX_TOKENS, a memory
        reservation twice the longest output ever produced) is never reached by a finished
        answer, and a `finish_reason` of "length" raises `TruncatedResponse`. That holds even
        when the cut-off JSON happens to parse: these schemas emit the decisive field — the
        verdict — LAST, so a truncated object parses into a long, plausible statement carrying
        a missing or defaulted disposition. Silent, not loud. A partial result is never better
        than a loud failure.
        """
        messages = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        body = {
            "messages": messages,
            "temperature": temperature,
            **no_thinking(self.model, self.base_url),
        }
        if schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "structured_output", "schema": schema},
            }

        last = None
        last_content = None
        last_finish = None
        last_usage = {}
        for attempt in range(self.max_retries):
            try:
                payload = self.post(body)
                msg = payload["choices"][0]["message"]
                content = msg["content"]
                if schema is not None and not (content or "").strip():
                    # Reasoning models (the Qwen3 family under LM Studio) emit into the
                    # think channel: content comes back EMPTY and the structured answer is
                    # the trailing JSON object of reasoning_content. Take it from there.
                    rc = msg.get("reasoning_content") or ""
                    if "{" in rc:
                        content = rc[rc.index("{"):]
                last_content = content
                last_finish = payload["choices"][0].get("finish_reason")
                last_usage = payload.get("usage") or {}
                if last_finish == "length":
                    # The server cut it. Whether or not what arrived parses, the tail is
                    # missing, and the tail is where the verdict lives.
                    raise TruncatedResponse(
                        f"response truncated by the server (finish_reason=length,"
                        f" {len(content or '')} chars,"
                        f" completion_tokens={last_usage.get('completion_tokens')})")
                result = json.loads(content) if schema is not None else content
                if with_usage:
                    return result, last_usage
                return result
            except (json.JSONDecodeError, KeyError) as exc:
                # Truncated / malformed JSON body — retry; transport-level errors are
                # already handled (and 4xx already raised) inside post().
                last = exc
                # A deterministic call that ran to the token cap gives the SAME
                # answer every time: retrying is pure wall-clock (5 x 160s on
                # one comment, blocking a 4-worker pilot for 13 minutes). Stop
                # after the first one and let the caller record the item.
                if attempt < self.max_retries - 1:
                    wait = 2.0 * (attempt + 1)
                    self._log(f"unparseable structured response"
                         f" (finish_reason={last_finish},"
                         f" content {len(last_content or '')} chars,"
                         f" completion_tokens={last_usage.get('completion_tokens')})"
                         f" — retry {attempt + 2}/{self.max_retries} in {wait:.0f}s")
                    time.sleep(wait)
        if last_content is not None:
            # Show WHAT couldn't be parsed, not just that parsing failed.
            self._log(f"structured response never parsed from {self.base_url};"
                 f" finish_reason={last_finish}, last content"
                 f" ({len(last_content)} chars): {last_content!r}")
        if last is None:
            raise RuntimeError(f"no attempt was made against {self.base_url}")
        raise last
