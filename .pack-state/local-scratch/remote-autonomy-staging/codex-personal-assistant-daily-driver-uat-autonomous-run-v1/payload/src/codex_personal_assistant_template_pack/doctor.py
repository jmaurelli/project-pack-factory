from __future__ import annotations

from pathlib import Path
from typing import Any

from .assistant_contracts import (
    REQUIRED_SURFACE_PATHS,
    load_context_routing,
    load_memory_policy,
    load_operator_profile,
    load_partnership_policy,
    load_profile,
    load_skill_catalog,
)


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
    ambiguity_policy = partnership.get("ambiguity_policy", {})
    if not isinstance(ambiguity_policy, dict) or ambiguity_policy.get("default_behavior") != "ask-clarifying-question":
        errors.append("partnership policy must fail closed on ambiguity")

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
    if not isinstance(memory_policy.get("storage_root"), str) or not memory_policy["storage_root"].strip():
        errors.append("memory policy must declare storage_root")

    latest_pointer_path = project_root / str(
        memory_policy.get("latest_pointer_path", ".pack-state/assistant-memory/latest-memory.json")
    )
    return {
        "status": "pass" if not missing_paths and not errors else "fail",
        "missing_paths": missing_paths,
        "errors": errors,
        "assistant_id": profile.get("assistant_id"),
        "operator_id": operator.get("operator_id"),
        "route_count": len(routes) if isinstance(routes, list) else 0,
        "skill_count": len(skill_entries) if isinstance(skill_entries, list) else 0,
        "latest_memory_pointer_present": latest_pointer_path.exists(),
    }
