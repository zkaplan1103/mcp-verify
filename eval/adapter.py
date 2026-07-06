"""The eval's bridge from its structured fixtures to the string-in/string-out engine.

Renders a (Profile, Opportunity) pair as the SOURCE and a Draft's sections as the
DRAFT, then calls `mcp_verify.core.verify`. The JSON render is deterministic
(sorted keys) — ported byte-identical from the grant-finder prompt assembly so
the frozen benchmark cases see exactly the source text they were labeled against.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from eval.fixtures import Draft, Opportunity, Profile
from mcp_verify import core as verify_core
from mcp_verify.client import LLMClient
from mcp_verify.core import VerifyReport

# Module-level constants read at call time so the ablation runner (eval/ablation.py)
# can monkey-patch them per configuration.
MODEL = "claude-opus-4-8"
# Adaptive thinking shares this budget with the answer; an undersized cap truncates
# the JSON. Opus reasons more than Sonnet here, so give it generous headroom.
MAX_TOKENS = 16000
THINKING: Optional[Dict[str, Any]] = {"type": "adaptive"}


def profile_to_prompt_dict(profile: Profile) -> Dict[str, Any]:
    """Stable, deterministic dict for the cached prefix (no volatile fields)."""
    return profile.model_dump(mode="json")


def opportunity_to_prompt_dict(opportunity: Opportunity) -> Dict[str, Any]:
    return opportunity.model_dump(mode="json")


def shared_prefix_text(
    profile: Profile, opportunity: Optional[Opportunity] = None
) -> str:
    """The text of the shared, cacheable prefix.

    Deterministic JSON (sorted keys) so the cached prefix is byte-stable across
    requests — a varying prefix would silently defeat prompt caching.
    """
    parts: List[str] = []
    parts.append("NONPROFIT PROFILE (the applicant org):")
    parts.append(json.dumps(profile_to_prompt_dict(profile), sort_keys=True, indent=2))
    if opportunity is not None:
        parts.append("")
        parts.append("FUNDING OPPORTUNITY (with its stated requirements):")
        parts.append(
            json.dumps(opportunity_to_prompt_dict(opportunity), sort_keys=True, indent=2)
        )
    return "\n".join(parts)


class VerifyAgent:
    """Thin adapter: fixture models in, `VerifyReport` (with `.failures`) out."""

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def verify(self, profile: Profile, opportunity: Opportunity, draft: Draft) -> VerifyReport:
        source = shared_prefix_text(profile, opportunity)
        draft_text = (
            f"ELIGIBILITY SUMMARY:\n{draft.eligibility_summary}\n\n"
            f"BOILERPLATE:\n{draft.boilerplate}"
        )
        return verify_core.verify(
            self._client,
            source,
            draft_text,
            model=MODEL,
            max_tokens=MAX_TOKENS,
            thinking=THINKING,
        )
