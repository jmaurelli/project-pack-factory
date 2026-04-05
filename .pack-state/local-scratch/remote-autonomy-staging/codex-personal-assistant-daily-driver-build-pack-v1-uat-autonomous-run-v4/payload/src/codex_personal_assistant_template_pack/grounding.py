from __future__ import annotations

from pathlib import Path
from typing import Any

from .assistant_contracts import load_operator_profile, load_partnership_policy
from .context_router import route_context


DRIFT_MARKERS = (
    "side work",
    "random",
    "busywork",
    "wander",
    "drift",
    "unclear",
    "vague",
)


def _normalize(value: str) -> str:
    return value.strip().lower()


def _operator_anchors(operator: dict[str, Any]) -> list[str]:
    anchors: list[str] = []
    for value in operator.get("near_term_priorities", []):
        if isinstance(value, str) and value.strip():
            anchors.append(value.strip())
    for value in operator.get("long_horizon_goals", []):
        if isinstance(value, str) and value.strip():
            anchors.append(value.strip())
    business_direction = operator.get("business_direction")
    if isinstance(business_direction, str) and business_direction.strip():
        anchors.append(business_direction.strip())
    return anchors


def _matched_anchor(current_work: str, anchors: list[str]) -> str | None:
    normalized_work = _normalize(current_work)
    for anchor in anchors:
        for token in anchor.lower().replace(".", "").split():
            if len(token) >= 5 and token in normalized_work:
                return anchor
    return None


def _grounding_accountability_status(partnership: dict[str, Any]) -> dict[str, Any]:
    cadence = _load_accountability_cadence(partnership)
    trigger_conditions = [value for value in cadence.get("trigger_conditions", []) if isinstance(value, str)]
    response_steps = [value for value in cadence.get("response_steps", []) if isinstance(value, str)]
    review_prompts = [value for value in cadence.get("review_prompts", []) if isinstance(value, str)]
    return {
        "cadence_name": cadence.get("cadence_name") or "grounded-check-in",
        "trigger_condition_count": len(trigger_conditions),
        "response_step_count": len(response_steps),
        "review_prompt_count": len(review_prompts),
        "grounding_behavior_count": len(
            [value for value in partnership.get("grounding_behaviors", []) if isinstance(value, str)]
        ),
        "ambiguity_default": (
            partnership.get("ambiguity_policy", {}).get("default_behavior")
            if isinstance(partnership.get("ambiguity_policy"), dict)
            else None
        ),
        "trigger_conditions": trigger_conditions,
        "response_steps": response_steps,
        "review_prompts": review_prompts,
    }


def _load_accountability_cadence(partnership: dict[str, Any]) -> dict[str, Any]:
    cadence = partnership.get("grounding_accountability_cadence", {})
    if not isinstance(cadence, dict) or not cadence:
        cadence = partnership.get("accountability_cadence", {})
    if not isinstance(cadence, dict):
        return {}
    return cadence


def show_grounding_cadence(project_root: Path) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    cadence = _load_accountability_cadence(partnership)
    return {
        "status": "pass",
        "business_direction": operator.get("business_direction"),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "grounding_principles": operator.get("grounding_principles", []),
        "grounding_behaviors": partnership.get("grounding_behaviors", []),
        "review_prompts": partnership.get("review_prompts", []),
        "accountability_cadence": cadence,
        "grounding_accountability_status": _grounding_accountability_status(partnership),
    }


def check_grounding(
    project_root: Path,
    current_work: str,
    proposed_next_step: str | None = None,
) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    cadence = _load_accountability_cadence(partnership)
    normalized_work = _normalize(current_work)
    matched_goals = route_context(project_root, "goals")
    anchors = _operator_anchors(operator)
    matched_anchor = _matched_anchor(current_work, anchors)

    assessment = "aligned"
    reason = "The work appears to support the operator's stated direction."
    suggested_response = "Continue and keep the next step tied to the current business direction."

    if any(marker in normalized_work for marker in DRIFT_MARKERS):
        assessment = "drift_risk"
        reason = "The work description sounds vague or off-direction relative to the operator's stated priorities."
        suggested_response = "Name the drift plainly and propose the next grounded step that reconnects to current priorities."
    elif matched_anchor is None:
        assessment = "unclear"
        reason = "The work does not clearly tie back to a stated priority or long-term goal yet."
        suggested_response = "Ask how this work supports the operator's current business direction before committing further."

    if proposed_next_step and assessment == "aligned":
        normalized_next = _normalize(proposed_next_step)
        if any(marker in normalized_next for marker in DRIFT_MARKERS):
            assessment = "drift_risk"
            reason = "The proposed next step looks like drift even if the current work might be valid."
            suggested_response = "Pause and replace the vague next step with one concrete action that supports the stated direction."

    return {
        "status": "pass",
        "current_work": current_work,
        "proposed_next_step": proposed_next_step,
        "assessment": assessment,
        "reason": reason,
        "suggested_response": suggested_response,
        "matched_anchor": matched_anchor,
        "goal_route": matched_goals.get("matched_route"),
        "goal_paths": matched_goals.get("paths", []),
        "grounding_behaviors": partnership.get("grounding_behaviors", []),
        "review_prompts": partnership.get("review_prompts", []),
        "accountability_cadence": cadence,
        "grounding_accountability_status": _grounding_accountability_status(partnership),
        "operator_goal_anchor": anchors[0] if anchors else None,
    }


def run_grounding_check(
    project_root: Path,
    *,
    current_work_summary: str,
    intended_outcome: str | None = None,
) -> dict[str, Any]:
    return check_grounding(
        project_root,
        current_work=current_work_summary,
        proposed_next_step=intended_outcome,
    )
