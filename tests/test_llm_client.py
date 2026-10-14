"""The chat client's request body, without a server: the thinking switch in the
spelling each server takes, and the provider pin on OpenRouter.

    uv run pytest tests/test_llm_client.py
"""
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))

from shared.llm_client import ChatClient, no_thinking, thinking_off  # noqa: E402

LOCAL = "http://127.0.0.1:1234/v1"
OPENROUTER = "https://openrouter.ai/api/v1"


def test_thinking_switch_is_spelled_for_the_server():
    assert no_thinking("qwen/qwen3.8-27b", LOCAL) == {
        "chat_template_kwargs": {"enable_thinking": False, "thinking": False},
        "reasoning_effort": "none"}
    assert no_thinking("qwen/qwen3.8-flash", OPENROUTER) == {"reasoning": {"enabled": False}}
    assert no_thinking("some-other-model", OPENROUTER) == {}
    # A body built elsewhere loses every other spelling and gets the server's.
    body = {"messages": [], "reasoning_effort": "high", "chat_template_kwargs": {"enable_thinking": True}}
    assert thinking_off(body, "qwen/qwen3.8-flash", OPENROUTER) == {
        "messages": [], "reasoning": {"enabled": False}}


def test_provider_pin_is_on_every_body_only_when_set(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    local = ChatClient(base_url=LOCAL, model="qwen/qwen3.8-27b", api_key="")
    body = local.chat_body({"messages": []})
    assert body == {"model": "qwen/qwen3.8-27b", "messages": [], "max_tokens": local.max_tokens}
    monkeypatch.setenv("LLM_PROVIDER", "alibaba")
    remote = ChatClient(base_url=OPENROUTER, model="qwen/qwen3.8-flash", api_key="k")
    body = remote.chat_body({"model": "x", "messages": [], "max_tokens": 10})
    assert body["provider"] == {"only": ["alibaba"], "allow_fallbacks": False}
    assert body["model"] == "x" and body["max_tokens"] == 10
    assert remote._headers == {"Authorization": "Bearer k"}
    pinned = ChatClient(base_url=OPENROUTER, model="m", api_key="k", provider="other")
    assert pinned.chat_body({})["provider"]["only"] == ["other"]


def test_throttle_starts_at_one_climbs_and_backs_off_as_one():
    from shared.llm_client import _Throttle
    import time
    th = _Throttle(16)
    assert th.cap == 1
    for _ in range(_Throttle.STREAK * 2):
        th.succeeded()
    assert th.cap == 4                     # doubling per five clean answers, never pushed back
    for _ in range(_Throttle.STREAK * 3):
        th.succeeded()
    assert th.cap == 16                    # and never above the maximum
    th.cap = 4
    th.acquire(); th.acquire()
    wait, first = th.limited(None)
    assert first and wait == 2.0 and th.cap == 2 and th.ceiling == 4
    # A second 429 inside the pause extends nothing and is not the first.
    wait2, first2 = th.limited(None)
    assert not first2 and 0 < wait2 <= 2.0
    th.release(); th.release()
    t0 = time.monotonic()
    th.acquire()                           # waits the pause out before the next call
    assert time.monotonic() - t0 >= 1.5
    th.release()
    # Back up to just under the level that drew the 429 at the quick pace, then
    # one per PROBE above it.
    for _ in range(_Throttle.STREAK):
        th.succeeded()
    assert th.cap == 3
    for _ in range(_Throttle.STREAK):
        th.succeeded()
    assert th.cap == 3
    for _ in range(_Throttle.PROBE - _Throttle.STREAK):
        th.succeeded()
    assert th.cap == 4
    # The server's Retry-After wins over the doubling wait once the pause has passed.
    th.pause_until = 0.0
    wait3, first3 = th.limited(7)
    assert first3 and wait3 == 7.0 and th.cap == 2
    # A client with no maximum shares the pause and keeps no cap.
    free = _Throttle(None)
    assert free.cap is None and free.limited(None) == (2.0, True)


def test_calls_leave_spaced_apart():
    from shared.llm_client import _Throttle
    import time
    th = _Throttle(None)
    t0 = time.monotonic()
    th.acquire(); th.acquire(); th.acquire()
    assert time.monotonic() - t0 >= 2 * _Throttle.SPACING - 0.01


def test_client_reports_its_climb():
    c = ChatClient(base_url=LOCAL, model="m", api_key="", max_in_flight=16)
    assert c.in_flight_cap == (1, 16)
    for _ in range(5):
        c._throttle.succeeded()
    assert c.in_flight_cap == (2, 16)
    assert ChatClient(base_url=LOCAL, model="m", api_key="").in_flight_cap == (None, None)


def test_retry_after_header_is_seconds_or_nothing():
    from shared.llm_client import _retry_after
    assert _retry_after("12") == 12.0 and _retry_after(None) is None
    assert _retry_after("Wed, 21 Oct 2026 07:28:00 GMT") is None and _retry_after("0") is None


def test_base_url_takes_the_endpoint_or_its_base():
    from shared.llm_client import _base_url
    assert _base_url("https://api.together.ai/v1") == "https://api.together.ai/v1"
    assert _base_url("https://api.together.ai/v1/chat/completions") == "https://api.together.ai/v1"
    assert _base_url(" http://127.0.0.1:1234/v1/ ") == "http://127.0.0.1:1234/v1"
    assert ChatClient(base_url="https://openrouter.ai/api/v1/chat/completions/", model="m",
                      api_key="k").base_url == "https://openrouter.ai/api/v1"


def test_stream_is_assembled_into_the_one_reply_shape():
    from shared.llm_client import StreamError, _assemble_stream
    import json
    import pytest
    chunk = lambda **kw: "data: " + json.dumps({"id": "x1", "model": "m", **kw})  # noqa: E731
    lines = [
        ": keep-alive",
        chunk(choices=[{"index": 0, "delta": {"role": "assistant", "reasoning_content": "thi"}, "finish_reason": None}]),
        chunk(choices=[{"index": 0, "delta": {"reasoning_content": "nk"}, "finish_reason": None}]),
        chunk(choices=[{"index": 0, "delta": {"content": "{\"a\":"}, "finish_reason": None}]),
        "",
        chunk(choices=[{"index": 0, "delta": {"content": " 1}"}, "finish_reason": "stop"}]),
        chunk(choices=[], usage={"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14,
                                 "prompt_tokens_details": {"cached_tokens": 8}}),
        "data: [DONE]",
        chunk(choices=[{"index": 0, "delta": {"content": "never read"}, "finish_reason": None}]),
    ]
    payload = _assemble_stream(line.encode() for line in lines)
    assert payload["choices"][0]["message"] == {"role": "assistant", "content": '{"a": 1}',
                                               "reasoning_content": "think"}
    assert payload["choices"][0]["finish_reason"] == "stop"
    assert payload["usage"]["prompt_tokens_details"]["cached_tokens"] == 8 and payload["id"] == "x1"
    with pytest.raises(StreamError, match="stream error"):
        _assemble_stream(["data: " + json.dumps({"error": {"message": "boom", "code": 500}})])
    with pytest.raises(StreamError, match="before any chunk"):
        _assemble_stream(["data: [DONE]"])


def test_stream_setting_from_env_or_argument(monkeypatch):
    monkeypatch.delenv("LLM_STREAM", raising=False)
    assert ChatClient(base_url=LOCAL, model="m", api_key="").stream is False
    monkeypatch.setenv("LLM_STREAM", "1")
    assert ChatClient(base_url=LOCAL, model="m", api_key="").stream is True
    assert ChatClient(base_url=LOCAL, model="m", api_key="", stream=False).stream is False


def test_a_lost_connection_is_waited_out_as_one_then_raised(monkeypatch):
    """A name that does not resolve: the client pauses every worker and keeps
    trying for LIMIT_PATIENCE, then raises the connection error. Real DNS, no
    server; the patience is shortened so the test ends."""
    import time
    import requests
    import pytest
    from shared.llm_client import _Throttle
    monkeypatch.setattr(ChatClient, "LIMIT_PATIENCE", 0.5)
    monkeypatch.setattr(_Throttle, "MAX_PAUSE", 0.2)
    logged = []
    c = ChatClient(base_url="http://no-such-host.invalid:1/v1", model="m", api_key="",
                   timeout=2, log=logged.append)
    t0 = time.monotonic()
    with pytest.raises(requests.ConnectionError, match="no connection to http://no-such-host.invalid:1/v1"):
        c.post({"messages": []})
    assert time.monotonic() - t0 >= 0.5
    assert any(line.startswith("no connection to http://no-such-host.invalid:1/v1: every call waits")
               for line in logged)
