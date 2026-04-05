from __future__ import annotations

from pathlib import Path
from typing import Any

from .assistant_contracts import (
    load_operator_profile,
    load_partnership_policy,
    load_profile,
)


def show_alignment(project_root: Path) -> dict[str, Any]:
    profile = load_profile(project_root)
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    ambiguity_policy = partnership.get("ambiguity_policy", {})

    return {
        "status": "pass",
        "assistant_id": profile.get("assistant_id"),
        "operator_id": operator.get("operator_id") or profile.get("operator_id"),
        "preferred_name": operator.get("preferred_name"),
        "current_role": operator.get("current_role"),
        "business_direction": operator.get("business_direction"),
        "long_horizon_goals": operator.get("long_horizon_goals", []),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "grounding_principles": operator.get("grounding_principles", []),
        "working_preferences": operator.get("working_preferences", []),
        "ambiguity_preferences": operator.get("ambiguity_preferences", []),
        "known_do_not_assume": operator.get("known_do_not_assume", []),
        "success_signals": operator.get("success_signals", []),
        "relationship_mode": partnership.get("relationship_mode"),
        "primary_outcome": partnership.get("primary_outcome"),
        "ambiguity_default": ambiguity_policy.get("default_behavior"),
        "grounding_behaviors": partnership.get("grounding_behaviors", []),
        "adaptation_rules": partnership.get("adaptation_rules", []),
        "review_prompts": partnership.get("review_prompts", []),
        "boundaries": partnership.get("boundaries", []),
    }
