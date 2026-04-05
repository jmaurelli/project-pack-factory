from __future__ import annotations

from pathlib import Path
from typing import Any

from .assistant_contracts import (
    REQUIRED_SURFACE_PATHS,
    load_context_routing,
    load_memory_policy,
    load_operator_intake,
    load_operator_profile,
    load_partnership_policy,
    load_profile,
    load_skill_catalog,
)
from .memory import show_continuity_status


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def run_doctor(project_root: Path) -> dict[str, Any]:
    missing_paths = [
        str(path.as_posix()) for path in REQUIRED_SURFACE_PATHS if not (project_root / path).exists()
    ]

    errors: list[str] = []
    profile = load_profile(project_root)
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    routing = load_context_routing(project_root)
    memory_policy = load_memory_policy(project_root)
    intake_contract = load_operator_intake(project_root)
    skills = load_skill_catalog(project_root)

    if not isinstance(profile.get("assistant_id"), str) or not profile["assistant_id"].strip():
        errors.append("assistant profile must declare assistant_id")
    if not isinstance(profile.get("mission"), str) or not profile["mission"].strip():
        errors.append("assistant profile must declare mission")
    if len(_as_list(operator.get("long_horizon_goals"))) < 1:
        errors.append("operator profile must declare at least one long_horizon_goal")
    if len(_as_list(operator.get("near_term_priorities"))) < 1:
        errors.append("operator profile must declare at least one near_term_priority")
    if len(_as_list(operator.get("grounding_principles"))) < 1:
        errors.append("operator profile must declare grounding_principles")
    if not isinstance(partnership.get("relationship_mode"), str) or not partnership["relationship_mode"].strip():
        errors.append("partnership policy must declare relationship_mode")
    if len(_as_list(partnership.get("grounding_behaviors"))) < 3:
        errors.append("partnership policy must declare at least three grounding_behaviors")
    if len(_as_list(partnership.get("review_prompts"))) < 3:
        errors.append("partnership policy must declare at least three review_prompts")
    business_review_loop = partnership.get("business_review_loop", {})
    if not isinstance(business_review_loop, dict):
        errors.append("partnership policy must declare business_review_loop")
        business_review_loop = {}
    relationship_reflection_loop = partnership.get("relationship_reflection_loop", {})
    if not isinstance(relationship_reflection_loop, dict):
        errors.append("partnership policy must declare relationship_reflection_loop")
        relationship_reflection_loop = {}
    navigation_guidance_loop = partnership.get("navigation_guidance_loop", {})
    if not isinstance(navigation_guidance_loop, dict):
        errors.append("partnership policy must declare navigation_guidance_loop")
        navigation_guidance_loop = {}
    accountability_cadence = partnership.get("accountability_cadence", {})
    if not isinstance(accountability_cadence, dict):
        errors.append("partnership policy must declare accountability_cadence")
        accountability_cadence = {}
    grounding_accountability = partnership.get("grounding_accountability_cadence", {})
    if not isinstance(grounding_accountability, dict):
        errors.append("partnership policy must declare grounding_accountability_cadence")
        grounding_accountability = {}
    ambiguity_policy = partnership.get("ambiguity_policy", {})
    if not isinstance(ambiguity_policy, dict) or ambiguity_policy.get("default_behavior") != "ask-clarifying-question":
        errors.append("partnership policy must fail closed on ambiguity")
    if not isinstance(ambiguity_policy.get("question_style"), str) or not ambiguity_policy.get("question_style", "").strip():
        errors.append("partnership policy must declare ambiguity question_style")
    pause_conditions = _as_list(ambiguity_policy.get("pause_conditions"))
    if len(pause_conditions) < 1:
        errors.append("partnership policy must declare at least one ambiguity pause condition")
    checkpoints = _as_list(accountability_cadence.get("checkpoints"))
    if len(checkpoints) < 1:
        errors.append("partnership policy must declare at least one accountability checkpoint")
    drift_indicators = _as_list(accountability_cadence.get("drift_indicators"))
    if len(drift_indicators) < 1:
        errors.append("partnership policy must declare at least one accountability drift_indicator")
    if accountability_cadence.get("require_goal_anchor") is not True:
        errors.append("partnership policy must require goal anchoring in accountability_cadence")
    if not isinstance(grounding_accountability.get("cadence_name"), str) or not grounding_accountability.get("cadence_name", "").strip():
        errors.append("grounding_accountability_cadence must declare cadence_name")
    if len(_as_list(grounding_accountability.get("trigger_conditions"))) < 3:
        errors.append("grounding_accountability_cadence must declare at least three trigger_conditions")
    if len(_as_list(grounding_accountability.get("response_steps"))) < 4:
        errors.append("grounding_accountability_cadence must declare at least four response_steps")
    if len(_as_list(grounding_accountability.get("review_prompts"))) < 3:
        errors.append("grounding_accountability_cadence must declare at least three review_prompts")
    if not isinstance(business_review_loop.get("cadence_name"), str) or not business_review_loop.get("cadence_name", "").strip():
        errors.append("business_review_loop must declare cadence_name")
    if not isinstance(business_review_loop.get("storage_root"), str) or not business_review_loop.get("storage_root", "").strip():
        errors.append("business_review_loop must declare storage_root")
    if not isinstance(business_review_loop.get("latest_pointer_path"), str) or not business_review_loop.get("latest_pointer_path", "").strip():
        errors.append("business_review_loop must declare latest_pointer_path")
    if len(_as_list(business_review_loop.get("review_questions"))) < 4:
        errors.append("business_review_loop must declare at least four review_questions")
    if len(_as_list(business_review_loop.get("due_conditions"))) < 3:
        errors.append("business_review_loop must declare at least three due_conditions")
    if not isinstance(relationship_reflection_loop.get("cadence_name"), str) or not relationship_reflection_loop.get("cadence_name", "").strip():
        errors.append("relationship_reflection_loop must declare cadence_name")
    if len(_as_list(relationship_reflection_loop.get("review_questions"))) < 3:
        errors.append("relationship_reflection_loop must declare at least three review_questions")
    if len(_as_list(relationship_reflection_loop.get("due_conditions"))) < 3:
        errors.append("relationship_reflection_loop must declare at least three due_conditions")
    if len(_as_list(relationship_reflection_loop.get("target_category_order"))) < 3:
        errors.append("relationship_reflection_loop must declare target_category_order")
    if not isinstance(relationship_reflection_loop.get("max_prompts_per_reflection"), int) or relationship_reflection_loop.get("max_prompts_per_reflection", 0) < 1:
        errors.append("relationship_reflection_loop must declare max_prompts_per_reflection as a positive integer")
    if not isinstance(relationship_reflection_loop.get("record_surface"), str) or not relationship_reflection_loop.get("record_surface", "").strip():
        errors.append("relationship_reflection_loop must declare record_surface")
    if not isinstance(navigation_guidance_loop.get("cadence_name"), str) or not navigation_guidance_loop.get("cadence_name", "").strip():
        errors.append("navigation_guidance_loop must declare cadence_name")
    if len(_as_list(navigation_guidance_loop.get("trigger_conditions"))) < 3:
        errors.append("navigation_guidance_loop must declare at least three trigger_conditions")
    if len(_as_list(navigation_guidance_loop.get("response_steps"))) < 4:
        errors.append("navigation_guidance_loop must declare at least four response_steps")
    if len(_as_list(navigation_guidance_loop.get("review_prompts"))) < 3:
        errors.append("navigation_guidance_loop must declare at least three review_prompts")
    if len(_as_list(navigation_guidance_loop.get("fundamentals_gap_indicators"))) < 3:
        errors.append("navigation_guidance_loop must declare at least three fundamentals_gap_indicators")

    routes = routing.get("routes", [])
    if not isinstance(routes, list) or len(routes) < 6:
        errors.append("context routing must declare at least six routes")
    skill_entries = skills.get("skills", [])
    if not isinstance(skill_entries, list) or len(skill_entries) < 6:
        errors.append("skill catalog must declare at least six skills")

    memory_categories = _as_list(memory_policy.get("memory_categories"))
    expected_categories = {"preference", "goal", "communication_pattern", "alignment_risk"}
    if not expected_categories.issubset(set(memory_categories)):
        errors.append("memory policy must include preference, goal, communication_pattern, and alignment_risk categories")
    distillation_signal_strengths = set(_as_list(memory_policy.get("distillation_signal_strengths")))
    if not {"session_observation", "repeated_pattern", "explicit_confirmation"}.issubset(distillation_signal_strengths):
        errors.append(
            "memory policy must declare session_observation, repeated_pattern, and explicit_confirmation distillation_signal_strengths"
        )
    if not isinstance(memory_policy.get("storage_root"), str) or not memory_policy["storage_root"].strip():
        errors.append("memory policy must declare storage_root")
    distillation_policy = memory_policy.get("session_distillation_policy", {})
    if not isinstance(distillation_policy, dict):
        errors.append("memory policy must declare session_distillation_policy")
        distillation_policy = {}
    if not isinstance(distillation_policy.get("storage_root"), str) or not distillation_policy.get("storage_root", "").strip():
        errors.append("session_distillation_policy must declare storage_root")
    if not isinstance(distillation_policy.get("latest_pointer_path"), str) or not distillation_policy.get("latest_pointer_path", "").strip():
        errors.append("session_distillation_policy must declare latest_pointer_path")
    allowed_source_categories = set(_as_list(distillation_policy.get("allowed_source_categories")))
    if not expected_categories.issubset(allowed_source_categories.union({"note", "decision", "blocker"})):
        errors.append("session_distillation_policy must declare allowed source categories for bounded session distillation")
    promotable_categories = set(_as_list(distillation_policy.get("promotable_memory_categories")))
    if not expected_categories.issubset(promotable_categories):
        errors.append("session_distillation_policy must declare promotable memory categories")
    if distillation_policy.get("require_explicit_promotion") is not True:
        errors.append("session_distillation_policy must require explicit promotion")
    closeout_followthrough = distillation_policy.get("closeout_followthrough_policy", {})
    if not isinstance(closeout_followthrough, dict):
        errors.append("session_distillation_policy must declare closeout_followthrough_policy")
        closeout_followthrough = {}
    if closeout_followthrough.get("enabled") is not True:
        errors.append("closeout_followthrough_policy must be enabled")
    if not isinstance(closeout_followthrough.get("matching_rule"), str) or not closeout_followthrough.get(
        "matching_rule", ""
    ).strip():
        errors.append("closeout_followthrough_policy must declare matching_rule")
    if not isinstance(closeout_followthrough.get("max_source_memory_count"), int) or closeout_followthrough.get(
        "max_source_memory_count", 0
    ) < 1:
        errors.append("closeout_followthrough_policy must declare max_source_memory_count as a positive integer")
    if not isinstance(closeout_followthrough.get("min_source_memory_count_for_promotion"), int) or closeout_followthrough.get(
        "min_source_memory_count_for_promotion", 0
    ) < 2:
        errors.append("closeout_followthrough_policy must declare min_source_memory_count_for_promotion >= 2")
    if len(_as_list(closeout_followthrough.get("default_tags"))) < 1:
        errors.append("closeout_followthrough_policy must declare at least one default_tag")
    continuity_policy = memory_policy.get("continuity_checkpoint_policy", {})
    if not isinstance(continuity_policy, dict):
        errors.append("memory policy must declare continuity_checkpoint_policy")
        continuity_policy = {}
    if not isinstance(continuity_policy.get("default_memory_category"), str) or not continuity_policy.get(
        "default_memory_category", ""
    ).strip():
        errors.append("continuity_checkpoint_policy must declare default_memory_category")
    if not isinstance(continuity_policy.get("stale_after_hours"), int) or continuity_policy.get("stale_after_hours", 0) < 1:
        errors.append("continuity_checkpoint_policy must declare stale_after_hours as a positive integer")
    if len(_as_list(continuity_policy.get("default_memory_tags"))) < 1:
        errors.append("continuity_checkpoint_policy must declare at least one default_memory_tag")

    intake_categories = intake_contract.get("intake_categories", [])
    if not isinstance(intake_categories, list) or len(intake_categories) < 4:
        errors.append("operator intake contract must declare at least four intake categories")
    else:
        for category in intake_categories:
            if not isinstance(category, dict):
                errors.append("operator intake categories must be JSON objects")
                continue
            if not isinstance(category.get("category_id"), str) or not category["category_id"].strip():
                errors.append("operator intake categories must declare category_id")
            if not isinstance(category.get("prompt"), str) or not category["prompt"].strip():
                errors.append("operator intake categories must declare prompt")
            if not isinstance(category.get("stable_memory_category"), str) or not category["stable_memory_category"].strip():
                errors.append("operator intake categories must declare stable_memory_category")
            refinement_targets = _as_list(category.get("refinement_targets"))
            if len(refinement_targets) < 1:
                errors.append(
                    f"operator intake category `{category.get('category_id', '<unknown>')}` must declare refinement_targets"
                )
    refinement_rules = intake_contract.get("profile_refinement_rules", {})
    if not isinstance(refinement_rules, dict) or refinement_rules.get("merge_strategy") != "bounded_merge":
        errors.append("operator intake contract must declare bounded_merge profile refinement rules")
    if not isinstance(intake_contract.get("storage_root"), str) or not intake_contract["storage_root"].strip():
        errors.append("operator intake contract must declare storage_root")
    if not isinstance(intake_contract.get("latest_pointer_path"), str) or not intake_contract["latest_pointer_path"].strip():
        errors.append("operator intake contract must declare latest_pointer_path")

    continuity_status = show_continuity_status(project_root)
    return {
        "status": "pass" if not missing_paths and not errors else "fail",
        "missing_paths": missing_paths,
        "errors": errors,
        "assistant_id": profile.get("assistant_id"),
        "operator_id": operator.get("operator_id"),
        "route_count": len(routes) if isinstance(routes, list) else 0,
        "skill_count": len(skill_entries) if isinstance(skill_entries, list) else 0,
        "pause_condition_count": len(pause_conditions),
        "accountability_checkpoint_count": len(checkpoints),
        "grounding_behavior_count": len(_as_list(partnership.get("grounding_behaviors"))),
        "grounding_review_prompt_count": len(_as_list(partnership.get("review_prompts"))),
        "accountability_trigger_count": len(_as_list(grounding_accountability.get("trigger_conditions"))),
        "business_review_question_count": len(_as_list(business_review_loop.get("review_questions"))),
        "relationship_reflection_question_count": len(_as_list(relationship_reflection_loop.get("review_questions"))),
        "navigation_trigger_count": len(_as_list(navigation_guidance_loop.get("trigger_conditions"))),
        "latest_memory_pointer_present": continuity_status.get("latest_pointer_present", False),
        "continuity_health": continuity_status.get("health"),
        "continuity_reason": continuity_status.get("reason"),
        "continuity_recommended_action": continuity_status.get("recommended_action"),
        "intake_category_count": len(intake_categories) if isinstance(intake_categories, list) else 0,
        "distillation_promotable_category_count": len(promotable_categories),
    }
