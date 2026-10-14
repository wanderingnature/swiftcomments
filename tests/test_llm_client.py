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
