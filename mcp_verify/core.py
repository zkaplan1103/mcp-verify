"""Domain-agnostic verify engine.

Checks a DRAFT string against a SOURCE string (the source of truth) and returns
the specific unsupported claims, each with an explainable verdict: the source
fact it was checked against, an error category, and a severity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mcp_verify.client import LLMClient
from mcp_verify.parsing import extract_json_object
from mcp_verify.prompt import SYSTEM_PROMPT


@dataclass
class VerifiedClaim:
    claim: str
    reason: str
    source_fact_checked: str = ""
    category: str = ""
    severity: str = ""


@dataclass
class VerifyReport:
    passed: bool
    failures: List[VerifiedClaim]
    uncertain: List[VerifiedClaim] = field(default_factory=list)


_STOPWORDS = frozenset(
    "a an the of to in on at and or is are was were it its this that with by for as".split()
)
_SIMILARITY_THRESHOLD = 0.5


def _content_tokens(text: str) -> frozenset:
    return frozenset(t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS)


def _similar(a: str, b: str) -> bool:
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return ta == tb
    return len(ta & tb) / len(ta | tb) >= _SIMILARITY_THRESHOLD


def aggregate_reports(reports: List[VerifyReport]) -> VerifyReport:
    """Majority-vote aggregation over N independent runs of the same request.

    Claims are matched across runs by token-overlap similarity. A claim seen in
    a strict majority of runs (> N/2) is a CONFIRMED failure; anything else is
    UNCERTAIN (advisory — does not fail the report). Each group keeps the
    VerifiedClaim from its first occurrence.
    """
    n = len(reports)
    groups: List[Dict[str, Any]] = []  # {"first": VerifiedClaim, "runs": set of run indices}
    for i, report in enumerate(reports):
        for claim in report.failures:
            for g in groups:
                if _similar(claim.claim, g["first"].claim):
                    g["runs"].add(i)
                    break
            else:
                groups.append({"first": claim, "runs": {i}})
    confirmed = [g["first"] for g in groups if len(g["runs"]) * 2 > n]
    uncertain = [g["first"] for g in groups if len(g["runs"]) * 2 <= n]
    return VerifyReport(passed=not confirmed, failures=confirmed, uncertain=uncertain)


def build_user_message(draft: str) -> str:
    """The user-turn text. Shared by verify() and the MCP-sampling server path."""
    return (
        "Check this draft for unsupported claims.\n\n"
        f"{draft}\n\n"
        "Return the JSON object only."
    )


def report_from_data(data: Dict[str, Any]) -> VerifyReport:
    """Build a VerifyReport from the extracted model JSON. Shared with the server."""
    failures = [
        VerifiedClaim(
            claim=str(f["claim"]),
            reason=str(f["reason"]),
            source_fact_checked=str(f.get("source_fact_checked") or ""),
            category=str(f.get("category") or ""),
            severity=str(f.get("severity") or ""),
        )
        for f in (data.get("failures") or [])
    ]
    # Trust the failures list as the source of truth for pass/fail.
    passed = bool(data.get("passed", not failures)) and not failures
    return VerifyReport(passed=passed, failures=failures)


def verify(
    client: LLMClient,
    source: str,
    draft: str,
    model: str = "claude-opus-4-8",
    max_tokens: int = 16000,
    thinking: Optional[Dict[str, Any]] = {"type": "adaptive"},  # noqa: B006 — never mutated
    consistency: int = 1,
) -> VerifyReport:
    # The SOURCE block carries the cache_control breakpoint so the prompt +
    # source prefix cache together across repeated verify calls.
    system: List[Dict[str, Any]] = [
        {"type": "text", "text": SYSTEM_PROMPT},
        {"type": "text", "text": source, "cache_control": {"type": "ephemeral"}},
    ]
    messages = [{"role": "user", "content": build_user_message(draft)}]

    def one_run() -> VerifyReport:
        resp = client.complete(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            thinking=thinking,
        )
        data = extract_json_object(resp.text, resp.stop_reason)
        return report_from_data(data)

    if consistency <= 1:
        return one_run()
    return aggregate_reports([one_run() for _ in range(consistency)])
