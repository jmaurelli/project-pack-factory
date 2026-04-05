from __future__ import annotations

from pathlib import Path
from typing import Any

from .assistant_contracts import load_operator_profile, load_partnership_policy
from .context_router import route_context


AMBIGUITY_MARKERS = (
    "maybe",
    "not sure",
    "unclear",
    "something",
    "somehow",
    "random",
    "side work",
    "could",
    "should",
    "ideas",
)


def _normalize(value: str) -> str:
    return value.strip().lower()


def _unique_paths(routes: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for route in routes:
        paths = route.get("paths", [])
        if not isinstance(paths, list):
            continue
        for path in paths:
            if isinstance(path, str) and path not in seen:
                seen.add(path)
                ordered.append(path)
    return ordered


def _triggered_conditions(scenario: str) -> list[str]:
    normalized = _normalize(scenario)
    conditions: list[str] = []
    if any(marker in normalized for marker in AMBIGUITY_MARKERS):
        conditions.append("ambiguous operator intent")
    if "side work" in normalized or "tradeoff" in normalized or "priority" in normalized:
        conditions.append("possible conflict with stated goals or constraints")
    return conditions


def _build_question(*, operator: dict[str, Any], scenario: str) -> str:
    normalized = _normalize(scenario)
    business_direction = operator.get("business_direction")
    if "side work" in normalized or "random" in normalized:
        if isinstance(business_direction, str) and business_direction.strip():
            return "What concrete outcome do you want right now, and how should it rank against your current business direction?"
        return "What concrete outcome do you want right now, and how should it rank against your current priorities?"
    return "What concrete outcome do you want from this right now, and what should it outrank?"


def check_ambiguity(project_root: Path, scenario: str) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    ambiguity_policy = partnership.get("ambiguity_policy", {})

    routed_contexts: list[dict[str, Any]] = []
    for topic in ("goals", "partnership"):
        route = route_context(project_root, topic)
        if route.get("status") == "pass":
            routed_contexts.append(route)

    triggered_pause_conditions = _triggered_conditions(scenario)
    default_pause_conditions = ambiguity_policy.get("pause_conditions", [])
    if not triggered_pause_conditions and isinstance(default_pause_conditions, list) and default_pause_conditions:
        triggered_pause_conditions = [str(default_pause_conditions[0])]

    decision = "clarify" if triggered_pause_conditions else "proceed"
    question = _build_question(operator=operator, scenario=scenario) if decision == "clarify" else None
    reason = (
        "The scenario leaves the desired outcome or priority unclear relative to the operator's stated goals."
        if decision == "clarify"
        else "The scenario appears specific enough to proceed without a clarifying question."
    )

    return {
        "status": "pass",
        "scenario": scenario,
        "decision": decision,
        "question": question,
        "reason": reason,
        "question_style": ambiguity_policy.get("question_style"),
        "triggered_pause_conditions": triggered_pause_conditions,
        "routed_topics": [route.get("matched_route") for route in routed_contexts],
        "cited_paths": _unique_paths(routed_contexts),
        "operator_goal_anchor": (operator.get("long_horizon_goals") or [None])[0],
    }
