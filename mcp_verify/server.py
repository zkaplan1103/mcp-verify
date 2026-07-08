"""MCP server exposing the verify engine as a single tool.

Two modes, same JSON result shape:
- "api"      — ANTHROPIC_API_KEY set: call the core engine directly (pinned
               model, the exact path the benchmark measures).
- "sampling" — no key (the default): request MCP sampling, so the HOST's model
               does the inference and the user needs no key at all.
Set MCP_VERIFY_MODE=api|sampling to force one; otherwise auto by key presence.
"""

from __future__ import annotations

import dataclasses
import json
import os
from typing import Any, Dict

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import SamplingMessage, TextContent

from mcp_verify import core
from mcp_verify.client import build_default_client
from mcp_verify.parsing import AgentOutputError, extract_json_object
from mcp_verify.prompt import SYSTEM_PROMPT

MAX_TOKENS = 16000

server = FastMCP("verify")


def _mode() -> str:
    forced = os.environ.get("MCP_VERIFY_MODE", "").strip().lower()
    if forced in ("api", "sampling"):
        return forced
    return "api" if os.environ.get("ANTHROPIC_API_KEY") else "sampling"


def _error(message: str, hint: str) -> str:
    return json.dumps({"error": message, "hint": hint})


def _result(report: core.VerifyReport, mode: str) -> str:
    payload: Dict[str, Any] = dataclasses.asdict(report)
    payload["mode"] = mode
    return json.dumps(payload)


async def _verify_via_sampling(ctx: Context, source: str, draft: str, consistency: int = 1) -> str:
    reports = []
    for _ in range(max(1, consistency)):
        try:
            result = await ctx.session.create_message(
                messages=[
                    SamplingMessage(
                        role="user",
                        content=TextContent(type="text", text=core.build_user_message(draft)),
                    )
                ],
                system_prompt=f"{SYSTEM_PROMPT}\n\n{source}",
                max_tokens=MAX_TOKENS,
            )
        except Exception as exc:  # host rejected or doesn't support sampling
            return _error(
                f"MCP sampling failed: {exc}",
                "This host does not support MCP sampling. Set ANTHROPIC_API_KEY in the "
                "server's environment to use direct API mode instead.",
            )
        content = result.content
        text = content.text if getattr(content, "type", "") == "text" else ""
        stop_reason = "max_tokens" if result.stopReason == "maxTokens" else None
        try:
            data = extract_json_object(text, stop_reason)
        except AgentOutputError as exc:
            return _error(
                f"Could not parse the host model's reply: {exc}",
                "Retry, or set ANTHROPIC_API_KEY to use the pinned benchmark model.",
            )
        reports.append(core.report_from_data(data))
    if consistency <= 1:
        return _result(reports[0], "sampling")
    return _result(core.aggregate_reports(reports), "sampling")


@server.tool()
async def verify(source: str, draft: str, ctx: Context, consistency: int = 1) -> str:
    """Check a DRAFT text against a SOURCE (the source of truth) and report every
    factual claim the source does not support.

    Args:
        source: The trusted reference text — the source of truth to check against.
        draft: The text to verify (e.g. a summary, answer, or generated document).
        consistency: Run the check this many times and majority-vote — claims
            confirmed by a strict majority land in "failures", the rest in the
            advisory "uncertain" list (default 1: single run, no extra calls).

    Returns a JSON string: {"passed": bool, "failures": [{"claim", "reason",
    "source_fact_checked", "category", "severity"}], "uncertain": [...],
    "mode": "api"|"sampling"}.
    passed is true only when no confirmed unsupported claims were found.
    """
    mode = _mode()
    if mode == "sampling":
        return await _verify_via_sampling(ctx, source, draft, consistency)

    client = build_default_client()
    if client is None:
        return _error(
            "MCP_VERIFY_MODE=api but ANTHROPIC_API_KEY is not set.",
            "Set ANTHROPIC_API_KEY in the server's environment, or unset "
            "MCP_VERIFY_MODE to fall back to MCP sampling.",
        )
    try:
        report = core.verify(client, source=source, draft=draft, consistency=consistency)
    except AgentOutputError as exc:
        return _error(f"Could not parse the model's reply: {exc}", "Retry the call.")
    return _result(report, "api")


def main() -> None:
    server.run()  # stdio transport


if __name__ == "__main__":
    main()
