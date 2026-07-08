"""Tests for the MCP server tool — both modes, fully offline."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any

from mcp_verify import server
from tests.fakes import FakeLLMClient

FAILURE = {
    "claim": "Serves 10k people",
    "reason": "Not in source",
    "source_fact_checked": "Profile states 2k people served",
    "category": "fabrication",
    "severity": "high",
}
MODEL_REPLY = json.dumps({"passed": False, "failures": [FAILURE]})


class StubSession:
    """Fake ctx.session: records the sampling request, returns a canned reply."""

    def __init__(self, reply: str = MODEL_REPLY, error: Exception | None = None) -> None:
        self._reply = reply
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def create_message(self, messages, *, max_tokens, system_prompt=None, **kwargs):
        self.calls.append(
            {"messages": messages, "max_tokens": max_tokens, "system_prompt": system_prompt}
        )
        if self._error is not None:
            raise self._error
        return SimpleNamespace(
            content=SimpleNamespace(type="text", text=self._reply),
            stopReason="endTurn",
        )


def _ctx(session: StubSession) -> SimpleNamespace:
    return SimpleNamespace(session=session)


def _run(source: str, draft: str, ctx) -> dict:
    result = asyncio.run(server.verify(source, draft, ctx))
    return json.loads(result)


def test_api_mode_uses_core_engine(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("MCP_VERIFY_MODE", raising=False)
    fake = FakeLLMClient(MODEL_REPLY)
    monkeypatch.setattr(server, "build_default_client", lambda: fake)

    data = _run("SOURCE", "DRAFT", _ctx(StubSession(error=AssertionError("no sampling"))))

    assert data["mode"] == "api"
    assert data["passed"] is False
    assert data["failures"] == [FAILURE]
    # The core engine was actually called, with the source in the system block.
    assert fake.calls[0]["system"][-1]["text"] == "SOURCE"


def test_sampling_mode_uses_host_model(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MCP_VERIFY_MODE", raising=False)
    session = StubSession()

    data = _run("SOURCE", "DRAFT", _ctx(session))

    assert data["mode"] == "sampling"
    assert data["passed"] is False
    assert data["failures"] == [FAILURE]
    # Same prompt as the core engine: system prompt + source, shared user message.
    call = session.calls[0]
    assert call["system_prompt"].startswith(server.SYSTEM_PROMPT)
    assert call["system_prompt"].endswith("SOURCE")
    assert call["messages"][0].content.text == server.core.build_user_message("DRAFT")


def test_explicit_mode_env_var_wins(monkeypatch):
    # Key present, but MCP_VERIFY_MODE=sampling forces the sampling path.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("MCP_VERIFY_MODE", "sampling")

    data = _run("s", "d", _ctx(StubSession()))
    assert data["mode"] == "sampling"


def test_sampling_unsupported_returns_error_json(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MCP_VERIFY_MODE", raising=False)
    session = StubSession(error=RuntimeError("Method not found"))

    data = _run("s", "d", _ctx(session))

    assert "error" in data
    assert "ANTHROPIC_API_KEY" in data["hint"]


def test_api_mode_without_key_returns_error_json(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("MCP_VERIFY_MODE", "api")

    data = _run("s", "d", _ctx(StubSession()))

    assert "error" in data
    assert "ANTHROPIC_API_KEY" in data["error"]


def test_api_mode_consistency_splits_confirmed_and_uncertain(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("MCP_VERIFY_MODE", raising=False)
    fake = FakeLLMClient([
        json.dumps({"passed": False, "failures": [
            {"claim": "Serves 10k people", "reason": "not in source"},
            {"claim": "Founded in 1999 by two engineers", "reason": "not in source"},
        ]}),
        json.dumps({"passed": False, "failures": [
            {"claim": "It serves 10k people annually", "reason": "not in source"},
        ]}),
        json.dumps({"passed": False, "failures": [
            {"claim": "serves 10k people", "reason": "not in source"},
        ]}),
    ])
    monkeypatch.setattr(server, "build_default_client", lambda: fake)

    result = asyncio.run(
        server.verify("SOURCE", "DRAFT", _ctx(StubSession()), consistency=3)
    )
    data = json.loads(result)

    assert len(fake.calls) == 3
    assert data["mode"] == "api"
    assert data["passed"] is False
    assert [f["claim"] for f in data["failures"]] == ["Serves 10k people"]
    assert [f["claim"] for f in data["uncertain"]] == ["Founded in 1999 by two engineers"]


def test_unparseable_sampling_reply_returns_error_json(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("MCP_VERIFY_MODE", raising=False)
    session = StubSession(reply="I could not find any problems!")

    data = _run("s", "d", _ctx(session))

    assert "error" in data and "hint" in data
