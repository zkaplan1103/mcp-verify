"""mcp-verify: domain-agnostic verification of a DRAFT against a SOURCE."""

from mcp_verify.client import LLMClient, build_default_client
from mcp_verify.core import VerifiedClaim, VerifyReport, verify
from mcp_verify.prompt import SYSTEM_PROMPT

__all__ = [
    "SYSTEM_PROMPT",
    "LLMClient",
    "VerifiedClaim",
    "VerifyReport",
    "build_default_client",
    "verify",
]
