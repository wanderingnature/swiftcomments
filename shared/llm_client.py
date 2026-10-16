"""The single OpenAI-compatible chat client for rtca — one place, reused everywhere.

Before this, ~13 scripts each hand-rolled their own `requests.post(.../chat/completions)`
with their own (or missing) auth, their own retry, their own structured-output wiring —
and they drifted: a local-only script copied without auth 401'd the moment it hit a
remote endpoint. This module is the one path. Every caller that talks to an
OpenAI-compatible endpoint goes through `ChatClient`.

Responsibilities, in one place:
- **the server** — one, the reader's, from .env (plan 5.2, edit 8): `LLM_BASE_URL`,
  `LLM_MODEL`, and `LLM_API_KEY` sent as a Bearer token when set, nothing when not;
  `LLM_PROVIDER`, when set, pins every call to that one provider on OpenRouter
  (`provider: {only: [name], allow_fallbacks: false}`), so the rows a run writes
  come from the weights and the prices the reader chose. docs/model-server.md says
  how to run one.
- **retry** — 429 (rate limit), 408/409, 5xx, timeouts, and truncated JSON are retried with
  backoff; a real 4xx (400/422 bad request/schema) fails fast.
- **streaming** — a provider that answers a model only as a stream (Together says
  so with a 400 `streaming_required`) gets `stream: true` from then on, and the
  stream is assembled into the one reply shape every caller reads: the message, its
  finish reason, the usage. `LLM_STREAM=1` sets it from the start.
- **the throttle** — calls in flight start at one and double per five clean answers
  while the server has never pushed back, up to `max_in_flight` (the runner's
  concurrency); calls leave at least 100 ms apart. One 429 (or 503, Together's
  high-demand signal) pauses every worker of the
  client, not just the one that got it, for the server's Retry-After or a doubling
  wait, halves the calls in flight, and marks the level that drew it: from then on
  the climb is one per five clean answers to just under that level and one per fifty
  above it. A 429 costs a call none of its retries. The server is asked for what it
  has shown it takes, never for sixteen at once to see what happens.
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

from shared.instrument import llm_var


class TruncatedResponse(RuntimeError):
    """The server stopped generating before the model was done (finish_reason=length).

    Never repaired, never salvaged, never retried — a truncated response is a lost response.
    House rule: nothing in this project is truncated.
    """


class StreamError(requests.RequestException):
    """A streamed reply that ended without a usable message: an error chunk, or
    no chunk at all. Retried like a dropped connection."""


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
    2026-10-12). A top-level `reasoning` object is never sent to a local server:
    LM Studio hangs on it — every call timing out at 180s, five retries deep,
    measured 2026-09-19. OpenRouter is the exception: its one spelling is
    `reasoning: {enabled: false}` (its own documentation, 2026-10-13), and it is
    sent that alone.

    This is not a tuning knob. The v3 instrument's repeatability was measured
    with thinking off (docs/design/reduced-ask-scoring-instrument.md); with it
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


def is_openrouter(base_url: str) -> bool:
    return "openrouter.ai" in (base_url or "").lower()


def _thinking_off_fields(model: str, base_url: str) -> dict:
    if is_openrouter(base_url):
        return {"reasoning": {"enabled": False}}
    return {"chat_template_kwargs": {"enable_thinking": False, "thinking": False},
            "reasoning_effort": "none"}


# The max_tokens every request carries unless the body sets its own. It is a
# MEMORY RESERVATION, not an output budget: without one, a server reserves the
# model's whole context for each request, fits few beside the 27B's weights on
# one GPU, and queues the rest — measured 2026-09-23 on real respond-point
# prompts, four in parallel: time to first token 9.3-11.4 s with no max_tokens,
# 0.3-0.5 s with one, identical outputs. 8192 is twice the longest output any
# task has produced (extract: 15,227 chars ≈ 4,000 tokens on the largest
# comment), and finish_reason=length still raises TruncatedResponse, so nothing
# is cut silently.
DEFAULT_MAX_TOKENS = 8192


_CLIENTS = []   # every ChatClient made in this process, for the exit spend report


class _Throttle:
    """What the client's workers share, so the server is never asked for more
    than it has shown it will take.

    Calls in flight start at ONE and climb the way TCP does: while the server
    has never pushed back, every STREAK clean answers in a row double them, up to
    the maximum the caller set (the runner's concurrency). A 429 from any worker
    sets a pause every worker honours before its next call (the server's
    Retry-After when it sends one, else 2 s doubling to 60 s on repeats), halves
    the calls in flight, and remembers the level that drew it: from then on the
    climb is one per STREAK up to just under that level and one per PROBE above
    it, so the limit is tested rarely, not leaned on. Calls leave at least
    SPACING apart, so the end of a pause or a raised cap never fires a burst at
    the same instant. A client made without a maximum (a local server) shares
    the pause and the spacing and keeps no cap.
    """
    STREAK = 5
    PROBE = 50
    MAX_PAUSE = 60.0
    SPACING = 0.1

    def __init__(self, max_in_flight=None):
        self.max = max_in_flight
        self.cap = 1 if max_in_flight is not None else None
        self.ceiling = None           # the in-flight level that last drew a 429
        self.in_flight = 0
        self.pause_until = 0.0
        self.next_start = 0.0
        self.backoff = 0.0
        self.streak = 0
        self._cv = threading.Condition()

    def acquire(self):
        with self._cv:
            while True:
                now = time.monotonic()
                until = max(self.pause_until, self.next_start)
                if now < until:
                    self._cv.wait(until - now)
                    continue
                if self.max is None or self.in_flight < self.cap:
                    self.in_flight += 1
                    self.next_start = now + self.SPACING
                    return
                self._cv.wait()

    def release(self):
        with self._cv:
            self.in_flight -= 1
            self._cv.notify_all()

    def limited(self, retry_after=None):
        """A 429 arrived. Returns (seconds every worker now waits, whether this call
        set the pause); a 429 that lands while a pause is already on extends nothing."""
        with self._cv:
            now = time.monotonic()
            if now < self.pause_until:
                return self.pause_until - now, False
            self.backoff = min(self.MAX_PAUSE, self.backoff * 2 if self.backoff else 2.0)
            wait = float(retry_after) if retry_after else self.backoff
            self.pause_until = now + wait
            if self.max is not None:
                self.ceiling = self.cap
                self.cap = max(1, self.cap // 2)
            self.streak = 0
            return wait, True

    def succeeded(self):
        with self._cv:
            self.backoff = 0.0
            self.streak += 1
            if self.max is None or self.cap >= self.max:
                return
            if self.ceiling is None:
                # Never pushed back: double, as TCP's slow start does.
                if self.streak >= self.STREAK:
                    self.cap = min(self.max, self.cap * 2)
                    self.streak = 0
                    self._cv.notify_all()
                return
            needed = self.PROBE if self.cap + 1 >= self.ceiling else self.STREAK
            if self.streak >= needed:
                self.cap += 1
                self.streak = 0
                self._cv.notify_all()


def _retry_after(value):
    """A Retry-After header as seconds, or None: servers send a number of seconds
    or an HTTP date; only the number is taken."""
    try:
        return float(value) if value is not None and float(value) > 0 else None
    except ValueError:
        return None


def _assemble_stream(lines) -> dict:
    """The one reply shape from a server-sent event stream: `data:` lines of
    chat.completion.chunk objects ended by `data: [DONE]`. The content and the
    reasoning channel are joined piece by piece, the finish reason is the last
    one sent, the usage the last one sent (OpenAI's `stream_options.include_usage`
    puts it on the final chunk; Together puts it there too). An `error` chunk, or
    a stream with no chunk, is a StreamError."""
    content, reasoning = [], []
    finish = None
    usage = {}
    head = {}
    chunks = 0
    for raw in lines:
        line = raw.decode("utf-8", "replace") if isinstance(raw, bytes) else raw
        line = line.strip()
        if not line or line.startswith(":") or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            chunk = json.loads(data)
        except ValueError:
            raise StreamError(f"stream chunk is not JSON: {data[:200]}") from None
        if "error" in chunk and not chunk.get("choices"):
            raise StreamError(f"stream error: {json.dumps(chunk['error'])}")
        chunks += 1
        for key in ("id", "model"):
            if key in chunk and key not in head:
                head[key] = chunk[key]
        if chunk.get("usage"):
            usage = chunk["usage"]
        for choice in chunk.get("choices") or []:
            delta = choice.get("delta") or {}
            if delta.get("content"):
                content.append(delta["content"])
            piece = delta.get("reasoning_content") or delta.get("reasoning")
            if piece:
                reasoning.append(piece)
            if choice.get("finish_reason"):
                finish = choice["finish_reason"]
    if chunks == 0:
        raise StreamError("the stream ended before any chunk arrived")
    message = {"role": "assistant", "content": "".join(content)}
    if reasoning:
        message["reasoning_content"] = "".join(reasoning)
    return {**head, "object": "chat.completion",
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
            "usage": usage}


def _base_url(value: str) -> str:
    """The base the client posts /chat/completions under. A value that names
    the endpoint itself (https://host/v1/chat/completions, as a provider's docs
    show it) is taken as its base, not doubled."""
    base = value.strip().rstrip("/")
    if base.lower().endswith("/chat/completions"):
        base = base[:-len("/chat/completions")].rstrip("/")
    return base


def _require_env(suffix: str) -> str:
    """LLM_<suffix> of the server the command runs against (shared.instrument.llm_var):
    the plain set, or the named set LLM_SERVER selects."""
    value = llm_var(suffix)
    if not value:
        server = (os.environ.get("LLM_SERVER") or "").strip().upper()
        name = f"LLM_{server}_{suffix}" if server else f"LLM_{suffix}"
        raise RuntimeError(
            f"{name} is not set: the model server is configured in .env"
            " (see .env.example and docs/model-server.md).")
    return value


class ChatClient:
    # How long one call keeps waiting through 429s, or through a lost connection
    # (the network down, the name unresolvable), before it gives up (seconds).
    LIMIT_PATIENCE = 600.0

    def __init__(self, base_url=None, model=None, *, api_key=None, provider=None, timeout=300,
                 max_retries=5, max_tokens=DEFAULT_MAX_TOKENS, log=None, max_in_flight=None,
                 stream=None):
        self.base_url = _base_url(base_url or _require_env("BASE_URL"))
        self.model = model or _require_env("MODEL")
        # Ask for the reply as a stream (LLM_STREAM=1, or set by the server's own
        # streaming_required answer); it is assembled into the usual reply shape.
        self.stream = bool(stream) if stream is not None else bool(llm_var("STREAM"))
        # The most calls this client ever keeps in flight: the runner's
        # concurrency, never above the server's own limit (LLM_CONCURRENCY, or
        # LLM_<NAME>_CONCURRENCY; the local server takes 2). The throttle starts
        # at one and climbs to it.
        server_max = llm_var("CONCURRENCY")
        if server_max:
            server_max = int(server_max)
            max_in_flight = server_max if max_in_flight is None else min(max_in_flight, server_max)
        self.max_in_flight = max_in_flight
        self._throttle = _Throttle(max_in_flight)
        # The one provider every call is pinned to on OpenRouter (LLM_PROVIDER);
        # empty for a local server, which has only itself.
        self.provider = (provider or llm_var("PROVIDER")).strip()
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

    @property
    def in_flight_cap(self):
        """(calls the client lets out at once now, the most it ever will), or
        (None, None) for a client with no maximum."""
        return self._throttle.cap, self._throttle.max

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
        key = api_key or llm_var("API_KEY")
        if key:
            return {"Authorization": f"Bearer {key}"}
        return {}

    def post(self, body):
        """Low-level: POST a fully-formed chat-completions body through the one authed,
        retried path, returning the parsed JSON payload (choices AND usage intact).

        This is the primitive `complete()` is built on, and the path callers that need the
        token usage or the raw envelope (the local batch runner, the workbench classifier)
        go through — so auth and retry live here alone and nowhere else. `body` may omit
        `model`; the client's model is injected. Retries 429/408/409/5xx/timeouts; a real
        4xx fails fast; a persistent failure re-raises the last exception."""
        return self.request("/chat/completions", self.chat_body(body))

    def chat_body(self, body):
        """`body` with what every chat completion carries: the client's model when
        the body names none, `max_tokens` (see DEFAULT_MAX_TOKENS) when it sets none,
        and, when a provider is pinned, OpenRouter's `provider` routing with
        fallbacks off, so a call never lands on other weights or other prices."""
        if "model" not in body:
            body = {"model": self.model, **body}
        if "max_tokens" not in body:
            body = {**body, "max_tokens": self.max_tokens}
        if self.provider and "provider" not in body:
            body = {**body, "provider": {"only": [self.provider], "allow_fallbacks": False}}
        return body

    def request(self, path, body):
        """POST `body` to `<base_url><path>` through the one authed, retried path and
        return the parsed JSON — `post()` for chat completions. The body is sent as
        given. Retry rules are post()'s."""
        last = None
        attempt = 0
        limited_since = None    # when this call first drew a 429 and began waiting
        while attempt < self.max_retries:
            self._throttle.acquire()
            t0 = time.monotonic()
            try:
                streaming = self.stream and path == "/chat/completions"
                sent = ({**body, "stream": True, "stream_options": {"include_usage": True}}
                        if streaming else body)
                r = requests.post(f"{self.base_url}{path}", json=sent, headers=self._headers,
                                  timeout=self.timeout, stream=streaming)
                r.raise_for_status()
                payload = _assemble_stream(r.iter_lines()) if streaming else r.json()
                dt = time.monotonic() - t0
                if dt > 60:
                    self._log(f"slow call: {dt:.0f}s from {self.base_url}")
                self._add_usage(payload)
                self._throttle.succeeded()
                return payload
            except (requests.HTTPError, requests.ConnectionError, requests.Timeout,
                    StreamError) as exc:
                last = exc
                dt = time.monotonic() - t0
                # Fail fast on a genuine 4xx (bad request / schema); retry 429/408/409.
                # The server's body says WHY (bad schema, context overflow,
                # unknown model, overload) — a bare "N Client/Server Error" is
                # undiagnosable. Carry it in every log line and raised error.
                detail = ""
                limited = False
                retry_after = None
                if isinstance(exc, requests.ConnectionError):
                    # No connection at all: the network is down or the name does
                    # not resolve. One worker's finding is every worker's; they
                    # wait as one, doubling to a minute, for up to LIMIT_PATIENCE,
                    # instead of each burning its retries in seconds.
                    now = time.monotonic()
                    limited_since = limited_since or now
                    if now - limited_since > self.LIMIT_PATIENCE:
                        raise requests.ConnectionError(
                            f"no connection to {self.base_url} for {now - limited_since:.0f}s,"
                            f" more than {self.LIMIT_PATIENCE:.0f}s: {exc}") from None
                    wait, first = self._throttle.limited(None)
                    if first:
                        self._log(f"no connection to {self.base_url}: every call waits"
                                  f" {wait:.0f}s and tries again ({type(exc).__name__}: {exc})")
                    continue
                if isinstance(exc, requests.HTTPError):
                    sc = exc.response.status_code
                    # The status and the body, verbatim: what the server said.
                    detail = f" — HTTP {sc} " + (exc.response.text or "").strip()
                    if sc == 400 and "streaming_required" in detail and not self.stream:
                        # The server answers this model only as a stream (Together):
                        # every call from here on asks for one. Costs no retry.
                        self.stream = True
                        self._log(f"{self.base_url} serves {self.model} only as a stream;"
                                  f" streaming every call from here on{detail}")
                        continue
                    if 400 <= sc < 500 and sc not in (408, 409, 429):
                        raise requests.HTTPError(
                            f"{exc}{detail}", response=exc.response) from None
                    if sc in (429, 503):
                        # 429 everywhere; 503 is how Together signals a model in
                        # high demand (its rate-limits page), the same thing.
                        limited = True
                        retry_after = _retry_after(exc.response.headers.get("Retry-After"))
                if limited:
                    # A 429 is the server's pace, not a failed attempt: it costs no
                    # retry. The pause is shared, every worker of this client waits
                    # it out before its next call, and fewer go at once after. A
                    # call that has been waiting on 429s for LIMIT_PATIENCE gives up
                    # with the server's own words.
                    now = time.monotonic()
                    limited_since = limited_since or now
                    if now - limited_since > self.LIMIT_PATIENCE:
                        raise requests.HTTPError(
                            f"rate limited for {now - limited_since:.0f}s, more than"
                            f" {self.LIMIT_PATIENCE:.0f}s: {exc}{detail}",
                            response=exc.response) from None
                    wait, first = self._throttle.limited(retry_after)
                    if first:
                        cap = (f", calls in flight capped at {self._throttle.cap}"
                               if self._throttle.max is not None else "")
                        self._log(f"rate limited by {self.base_url}: every call waits"
                                  f" {wait:.0f}s{cap}{detail}")
                    continue
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
            finally:
                self._throttle.release()
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
