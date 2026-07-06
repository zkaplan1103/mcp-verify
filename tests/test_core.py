"""Tests for the domain-agnostic verify core."""

from __future__ import annotations

import json

from mcp_verify import core as verify_core
from tests.fakes import FakeLLMClient

NEW_STYLE_FAILURE = {
    "claim": "Serves 10k people",
    "reason": "Not in source",
    "source_fact_checked": "Profile states 2k people served",
    "category": "fabrication",
    "severity": "high",
}


def test_core_parses_old_style_failures_with_defaults():
    client = FakeLLMClient(
        json.dumps({"passed": False, "failures": [{"claim": "x", "reason": "y"}]})
    )
    report = verify_core.verify(client, source="SOURCE TEXT", draft="DRAFT TEXT")

    assert report.passed is False
    f = report.failures[0]
    assert (f.claim, f.reason) == ("x", "y")
    assert f.source_fact_checked == "" and f.category == "" and f.severity == ""
    # The source rides in the cached system block.
    call = client.calls[0]
    assert call["system"][-1]["text"] == "SOURCE TEXT"
    assert call["system"][-1]["cache_control"] == {"type": "ephemeral"}


def test_core_carries_new_fields_through():
    client = FakeLLMClient(json.dumps({"passed": False, "failures": [NEW_STYLE_FAILURE]}))
    report = verify_core.verify(client, source="s", draft="d")

    f = report.failures[0]
    assert f.source_fact_checked == "Profile states 2k people served"
    assert f.category == "fabrication"
    assert f.severity == "high"


def test_core_failures_force_not_passed():
    # Even if the model says passed=true, a non-empty failures list overrides.
    client = FakeLLMClient(
        json.dumps({"passed": True, "failures": [{"claim": "x", "reason": "y"}]})
    )
    report = verify_core.verify(client, source="s", draft="d")
    assert report.passed is False
