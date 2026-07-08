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


def _reply(*claims: str) -> str:
    return json.dumps(
        {
            "passed": not claims,
            "failures": [{"claim": c, "reason": "not in source"} for c in claims],
        }
    )


def test_consistency_majority_claim_confirmed():
    # Same claim, paraphrased but token-similar, in 3/3 runs -> confirmed failure.
    client = FakeLLMClient([
        _reply("The grant awards 2 million dollars annually"),
        _reply("grant awards 2 million dollars every year"),
        _reply("The grant awards 2 million dollars annually to applicants"),
    ])
    report = verify_core.verify(client, source="s", draft="d", consistency=3)

    assert len(client.calls) == 3
    assert report.passed is False
    assert [f.claim for f in report.failures] == ["The grant awards 2 million dollars annually"]
    assert report.uncertain == []


def test_consistency_minority_claim_uncertain():
    # Claim in only 1/3 runs -> uncertain, not a failure; report still passes.
    client = FakeLLMClient([_reply("The award is 2 million dollars"), _reply(), _reply()])
    report = verify_core.verify(client, source="s", draft="d", consistency=3)

    assert report.passed is True
    assert report.failures == []
    assert [f.claim for f in report.uncertain] == ["The award is 2 million dollars"]


def test_consistency_no_strict_majority_is_uncertain():
    # 1/2 runs is not a strict majority (> N/2) -> uncertain.
    client = FakeLLMClient([_reply("The award is 2 million dollars"), _reply()])
    report = verify_core.verify(client, source="s", draft="d", consistency=2)

    assert report.passed is True
    assert report.failures == []
    assert len(report.uncertain) == 1


def test_consistency_default_is_single_call_identical_report():
    reply = _reply("x")
    client = FakeLLMClient(reply)
    report = verify_core.verify(client, source="s", draft="d", consistency=1)
    baseline = verify_core.verify(FakeLLMClient(reply), source="s", draft="d")

    assert len(client.calls) == 1
    assert report == baseline
    assert report.uncertain == []
