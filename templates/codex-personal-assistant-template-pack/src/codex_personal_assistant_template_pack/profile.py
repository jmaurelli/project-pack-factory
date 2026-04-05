from __future__ import annotations

from pathlib import Path
from typing import Any

from .assistant_contracts import (
    load_operator_profile,
    load_partnership_policy,
    load_profile,
)


def show_profile(project_root: Path) -> dict[str, Any]:
    profile = load_profile(project_root)
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    ambiguity_policy = partnership.get("ambiguity_policy", {})

    return {
        "status": "pass",
        "assistant_id": profile.get("assistant_id"),
        "display_name": profile.get("display_name"),
        "runtime": profile.get("runtime"),
        "operator_id": operator.get("operator_id") or profile.get("operator_id"),
        "preferred_name": operator.get("preferred_name"),
        "current_role": operator.get("current_role"),
        "mission": profile.get("mission"),
        "business_direction": operator.get("business_direction"),
        "long_horizon_goals": operator.get("long_horizon_goals", []),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "time_reality_constraints": operator.get("time_reality_constraints", []),
        "grounding_principles": operator.get("grounding_principles", []),
        "leadership_preferences": operator.get("leadership_preferences", []),
        "venture_preferences": operator.get("venture_preferences", []),
        "growth_orientation": operator.get("growth_orientation", []),
        "partnership_mode": partnership.get("relationship_mode"),
        "primary_outcome": partnership.get("primary_outcome"),
        "ambiguity_default": ambiguity_policy.get("default_behavior"),
        "behavior_principles": profile.get("behavior_principles", []),
        "default_capabilities": profile.get("default_capabilities", []),
        "startup_sequence": profile.get("startup_sequence", []),
        "startup_partner_behavior": profile.get("startup_partner_behavior", {}),
    }
