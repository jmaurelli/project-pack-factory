from __future__ import annotations

from pathlib import Path
from typing import Any

from .assistant_contracts import (
    load_operator_profile,
    load_partnership_policy,
    load_profile,
)
from .grounding import check_grounding
from .memory import show_memory_distillation
from .operator_intake import show_operator_intake


def show_alignment(project_root: Path) -> dict[str, Any]:
    profile = load_profile(project_root)
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    intake = show_operator_intake(project_root)
    distillation = show_memory_distillation(project_root)
    ambiguity_policy = partnership.get("ambiguity_policy", {})
    accountability = partnership.get("grounding_accountability_cadence", {})
    if not isinstance(accountability, dict) or not accountability:
        accountability = {}
    grounding = check_grounding(
        project_root,
        "Keep the assistant aligned with the operator's current business direction and near-term priorities.",
        proposed_next_step="Propose one concrete next step tied to the operator's current business direction.",
    )

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
        "accountability_cadence": partnership.get("accountability_cadence", {}),
        "operator_intake_status": intake.get("operator_intake_status", {}),
        "grounding_accountability_status": {
            "cadence_name": accountability.get("cadence_name"),
            "trigger_condition_count": len(accountability.get("trigger_conditions", []))
            if isinstance(accountability.get("trigger_conditions"), list)
            else 0,
            "response_step_count": len(accountability.get("response_steps", []))
            if isinstance(accountability.get("response_steps"), list)
            else 0,
            "review_prompt_count": len(accountability.get("review_prompts", []))
            if isinstance(accountability.get("review_prompts"), list)
            else 0,
            "trigger_conditions": accountability.get("trigger_conditions", []),
            "response_steps": accountability.get("response_steps", []),
            "review_prompts": accountability.get("review_prompts", []),
            "grounding_behavior_count": len(partnership.get("grounding_behaviors", []))
            if isinstance(partnership.get("grounding_behaviors"), list)
            else 0,
            "ambiguity_default": ambiguity_policy.get("default_behavior"),
            "sample_assessment": grounding.get("assessment"),
            "sample_suggested_response": grounding.get("suggested_response"),
        },
        "session_memory_distillation_status": distillation.get("session_memory_distillation_status", {}),
    }
