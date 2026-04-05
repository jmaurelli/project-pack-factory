from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assistant_contracts import load_operator_profile, load_partnership_policy
from .context_router import route_context
from .memory import record_closeout_distillation, record_continuity_checkpoint
from .relationship_state import show_relationship_state


DRIFT_MARKERS = (
    "side work",
    "random",
    "busywork",
    "wander",
    "drift",
    "unclear",
    "vague",
)
UNCERTAINTY_MARKERS = (
    "not sure",
    "unclear",
    "uncertain",
    "maybe",
    "direction",
    "curvy",
    "roadmap",
    "where i'm going",
    "where i am going",
)
FUNDAMENTALS_MARKERS = (
    "fundamental",
    "fundamentals",
    "basics",
    "deep knowledge",
    "depth",
    "learning",
    "don't know",
    "do not know",
)
BUSINESS_REVIEW_SCHEMA_VERSION = "codex-personal-assistant-business-review/v1"
BUSINESS_REVIEW_POINTER_SCHEMA_VERSION = "codex-personal-assistant-business-review-pointer/v1"


def _normalize(value: str) -> str:
    return value.strip().lower()


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def _load_business_review_loop(partnership: dict[str, Any]) -> dict[str, Any]:
    loop = partnership.get("business_review_loop", {})
    return loop if isinstance(loop, dict) else {}


def _load_navigation_guidance_loop(partnership: dict[str, Any]) -> dict[str, Any]:
    loop = partnership.get("navigation_guidance_loop", {})
    return loop if isinstance(loop, dict) else {}


def _primary_next_step_anchor(operator: dict[str, Any]) -> str | None:
    for value in operator.get("near_term_priorities", []):
        if isinstance(value, str) and value.strip():
            return value.strip()
    business_direction = operator.get("business_direction")
    if isinstance(business_direction, str) and business_direction.strip():
        return business_direction.strip()
    return None


def _business_review_paths(project_root: Path, partnership: dict[str, Any]) -> tuple[dict[str, Any], Path, Path]:
    loop = _load_business_review_loop(partnership)
    storage_root_value = loop.get("storage_root", ".pack-state/business-grounding-reviews")
    latest_pointer_value = loop.get("latest_pointer_path", ".pack-state/business-grounding-reviews/latest-review.json")
    return (
        loop,
        project_root / str(storage_root_value),
        project_root / str(latest_pointer_value),
    )


def _load_latest_business_review(
    project_root: Path,
    latest_pointer_path: Path,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    latest_pointer: dict[str, Any] | None = None
    latest_review: dict[str, Any] | None = None
    if latest_pointer_path.exists():
        latest_pointer = _load_json(latest_pointer_path)
        selected_path = latest_pointer.get("selected_review_path")
        if isinstance(selected_path, str) and selected_path:
            candidate = project_root / selected_path
            if candidate.exists():
                latest_review = _load_json(candidate)
    return latest_pointer, latest_review


def _review_count(storage_root: Path, latest_pointer_path: Path) -> int:
    if not storage_root.exists():
        return 0
    return len([path for path in sorted(storage_root.glob("*.json")) if path.is_file() and path.name != latest_pointer_path.name])


def _business_review_status(
    project_root: Path,
    *,
    partnership: dict[str, Any],
    relationship_state: dict[str, Any],
    latest_review: dict[str, Any] | None,
    latest_pointer_path: Path,
    review_count: int,
) -> dict[str, Any]:
    loop = _load_business_review_loop(partnership)
    review_questions = [value for value in loop.get("review_questions", []) if isinstance(value, str)]
    due_conditions = [value for value in loop.get("due_conditions", []) if isinstance(value, str)]
    latest_assessment = latest_review.get("assessment") if isinstance(latest_review, dict) else None
    review_due = False
    due_reason = "Recent business grounding review is available."
    if review_count == 0 or not isinstance(latest_review, dict):
        review_due = True
        due_reason = "No recorded business grounding review exists yet."
    elif latest_assessment in {"drift_risk", "unclear"}:
        review_due = True
        due_reason = "The latest business grounding review still flags drift or unclear direction."
    return {
        "cadence_name": loop.get("cadence_name") or "weekly-business-grounding-review",
        "latest_review_id": latest_review.get("review_id") if isinstance(latest_review, dict) else None,
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "review_count": review_count,
        "review_question_count": len(review_questions),
        "due_condition_count": len(due_conditions),
        "review_due": review_due,
        "due_reason": due_reason,
        "latest_review_assessment": latest_assessment,
        "missing_signal_category_count": len(relationship_state.get("missing_signal_categories", [])),
    }


def _load_accountability_cadence(partnership: dict[str, Any]) -> dict[str, Any]:
    cadence = partnership.get("grounding_accountability_cadence", {})
    if not isinstance(cadence, dict) or not cadence:
        cadence = partnership.get("accountability_cadence", {})
    if not isinstance(cadence, dict):
        return {}
    return cadence


def _navigation_status(
    project_root: Path,
    *,
    operator: dict[str, Any],
    partnership: dict[str, Any],
    relationship_state: dict[str, Any],
    latest_review: dict[str, Any] | None,
) -> dict[str, Any]:
    loop = _load_navigation_guidance_loop(partnership)
    trigger_conditions = [value for value in loop.get("trigger_conditions", []) if isinstance(value, str)]
    response_steps = [value for value in loop.get("response_steps", []) if isinstance(value, str)]
    review_prompts = [value for value in loop.get("review_prompts", []) if isinstance(value, str)]
    fundamentals_gap_indicators = [
        value for value in loop.get("fundamentals_gap_indicators", []) if isinstance(value, str)
    ]
    sample = check_navigation_guidance(
        project_root,
        "I know the general direction I want to go, but the path feels curvy and I do not have deep fundamentals yet.",
    )
    latest_assessment = latest_review.get("assessment") if isinstance(latest_review, dict) else None
    return {
        "cadence_name": loop.get("cadence_name") or "direction-to-decision-guidance",
        "trigger_condition_count": len(trigger_conditions),
        "response_step_count": len(response_steps),
        "review_prompt_count": len(review_prompts),
        "fundamentals_gap_indicator_count": len(fundamentals_gap_indicators),
        "trigger_conditions": trigger_conditions,
        "response_steps": response_steps,
        "review_prompts": review_prompts,
        "fundamentals_gap_indicators": fundamentals_gap_indicators,
        "business_direction": operator.get("business_direction"),
        "primary_next_step_anchor": _primary_next_step_anchor(operator),
        "supports_curvy_path": True,
        "north_star_present": bool(operator.get("business_direction")),
        "latest_business_review_assessment": latest_assessment,
        "missing_signal_category_count": len(relationship_state.get("missing_signal_categories", [])),
        "sample_assessment": sample.get("assessment"),
        "sample_work_mode": sample.get("work_mode"),
        "sample_recommended_action": sample.get("recommended_action"),
        "sample_clarifying_question": sample.get("clarifying_question"),
        "sample_reason": sample.get("reason"),
    }


def show_grounding_cadence(project_root: Path) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    cadence = _load_accountability_cadence(partnership)
    relationship_state = show_relationship_state(project_root)
    _, storage_root, latest_pointer_path = _business_review_paths(project_root, partnership)
    _, latest_review = _load_latest_business_review(project_root, latest_pointer_path)
    business_review_status = _business_review_status(
        project_root,
        partnership=partnership,
        relationship_state=relationship_state,
        latest_review=latest_review,
        latest_pointer_path=latest_pointer_path,
        review_count=_review_count(storage_root, latest_pointer_path),
    )
    navigation_status = _navigation_status(
        project_root,
        operator=operator,
        partnership=partnership,
        relationship_state=relationship_state,
        latest_review=latest_review,
    )
    return {
        "status": "pass",
        "business_direction": operator.get("business_direction"),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "grounding_principles": operator.get("grounding_principles", []),
        "grounding_behaviors": partnership.get("grounding_behaviors", []),
        "review_prompts": partnership.get("review_prompts", []),
        "accountability_cadence": cadence,
        "grounding_accountability_status": _grounding_accountability_status(partnership),
        "business_review_status": business_review_status,
        "navigation_guidance_status": navigation_status,
    }


def show_business_review(project_root: Path) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    relationship_state = show_relationship_state(project_root)
    loop, storage_root, latest_pointer_path = _business_review_paths(project_root, partnership)
    latest_pointer, latest_review = _load_latest_business_review(project_root, latest_pointer_path)
    review_questions = [value for value in loop.get("review_questions", []) if isinstance(value, str)]
    missing_signal_categories = relationship_state.get("missing_signal_categories", [])
    next_learning_prompts = relationship_state.get("next_learning_prompts", [])
    suggested_focus_areas: list[str] = []
    business_direction = operator.get("business_direction")
    if isinstance(business_direction, str) and business_direction.strip():
        suggested_focus_areas.append(f"Reconnect current work to: {business_direction.strip()}")
    for priority in operator.get("near_term_priorities", []):
        if isinstance(priority, str) and priority.strip():
            suggested_focus_areas.append(priority.strip())
        if len(suggested_focus_areas) >= 3:
            break
    for prompt in next_learning_prompts:
        if not isinstance(prompt, dict):
            continue
        prompt_text = prompt.get("prompt")
        if isinstance(prompt_text, str) and prompt_text.strip():
            suggested_focus_areas.append(prompt_text.strip())
        if len(suggested_focus_areas) >= 5:
            break
    review_count = _review_count(storage_root, latest_pointer_path)
    return {
        "status": "pass",
        "business_direction": operator.get("business_direction"),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "long_horizon_goals": operator.get("long_horizon_goals", []),
        "grounding_principles": operator.get("grounding_principles", []),
        "review_questions": review_questions,
        "relationship_missing_signal_categories": missing_signal_categories,
        "relationship_next_learning_prompts": next_learning_prompts,
        "suggested_focus_areas": suggested_focus_areas,
        "latest_pointer": latest_pointer,
        "latest_review": latest_review,
        "business_review_status": _business_review_status(
            project_root,
            partnership=partnership,
            relationship_state=relationship_state,
            latest_review=latest_review,
            latest_pointer_path=latest_pointer_path,
            review_count=review_count,
        ),
        "review_count": review_count,
    }


def check_navigation_guidance(
    project_root: Path,
    scenario: str,
) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    relationship_state = show_relationship_state(project_root)
    business_review = show_business_review(project_root)
    loop = _load_navigation_guidance_loop(partnership)
    normalized_scenario = _normalize(scenario)
    business_direction = operator.get("business_direction")
    near_term_priorities = [value for value in operator.get("near_term_priorities", []) if isinstance(value, str)]
    long_horizon_goals = [value for value in operator.get("long_horizon_goals", []) if isinstance(value, str)]
    next_step_anchor = _primary_next_step_anchor(operator)

    uncertainty_detected = any(marker in normalized_scenario for marker in UNCERTAINTY_MARKERS)
    fundamentals_gap_detected = any(marker in normalized_scenario for marker in FUNDAMENTALS_MARKERS)
    drift_risk_detected = any(marker in normalized_scenario for marker in DRIFT_MARKERS)

    work_mode = "execution"
    if uncertainty_detected and not drift_risk_detected:
        work_mode = "exploration"
    if fundamentals_gap_detected:
        work_mode = "learning"

    assessment = "grounded_execution"
    recommended_action = "Pick one concrete next step tied to the current business direction and do that next."
    reason = "The scenario is specific enough to support a grounded next step."
    clarifying_question: str | None = None
    path_shape = "direct"
    fundamentals_explanation = None
    if uncertainty_detected:
        path_shape = "curvy"

    if drift_risk_detected:
        assessment = "drift_risk"
        recommended_action = (
            f"Stop and reconnect the work to one near-term priority before spending more time on it: {next_step_anchor}."
            if next_step_anchor
            else "Stop and reconnect the work to one near-term priority before spending more time on it."
        )
        reason = "The scenario suggests motion that may not support the stated business direction."
        clarifying_question = "What concrete outcome should this work advance for the small-business direction right now?"
    elif fundamentals_gap_detected and uncertainty_detected:
        assessment = "fundamentals_gap_with_unclear_path"
        recommended_action = (
            "Name the one concept that feels thin, get a plain-language fundamentals explanation, "
            "then choose the smallest next step that teaches or de-risks the path."
        )
        reason = "The scenario signals both roadmap uncertainty and limited fundamentals depth, so a teaching-first step is safer than a bigger bet."
        clarifying_question = "Which specific concept or system feels thin enough that a short fundamentals explanation would unblock the next step?"
        fundamentals_explanation = "Explain the thinnest concept in plain language before committing to a larger build or workflow choice."
    elif fundamentals_gap_detected:
        assessment = "fundamentals_gap"
        recommended_action = "Pause for a brief fundamentals explanation before committing to a larger implementation step."
        reason = "The scenario suggests the operator is working above current fundamentals depth."
        clarifying_question = "What concept do you want explained plainly before we choose the next implementation step?"
        fundamentals_explanation = "Explain the concept in plain language, then return to one bounded implementation step."
    elif uncertainty_detected:
        assessment = "curvy_path"
        recommended_action = (
            f"Treat this as exploration, not failure. Keep the stable direction, then choose the smallest next step that advances: {next_step_anchor}."
            if next_step_anchor
            else "Treat this as exploration, not failure. Keep the stable direction, then choose the smallest next step that teaches or advances it."
        )
        reason = "The operator has direction, but not a full roadmap yet."
        clarifying_question = "What outcome matters most right now, and what is the smallest step that would reduce uncertainty?"

    return {
        "status": "pass",
        "scenario": scenario,
        "assessment": assessment,
        "reason": reason,
        "work_mode": work_mode,
        "path_shape": path_shape,
        "uncertainty_detected": uncertainty_detected,
        "fundamentals_gap_detected": fundamentals_gap_detected,
        "drift_risk_detected": drift_risk_detected,
        "recommended_action": recommended_action,
        "clarifying_question": clarifying_question,
        "fundamentals_explanation": fundamentals_explanation,
        "next_step_anchor": next_step_anchor,
        "business_direction": business_direction,
        "near_term_priorities": near_term_priorities,
        "long_horizon_goals": long_horizon_goals,
        "navigation_guidance_loop": loop,
        "business_review_due": business_review.get("business_review_status", {}).get("review_due"),
        "relationship_missing_signal_categories": relationship_state.get("missing_signal_categories", []),
    }


def show_navigation_guidance(project_root: Path) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    relationship_state = show_relationship_state(project_root)
    business_review = show_business_review(project_root)
    return {
        "status": "pass",
        "business_direction": operator.get("business_direction"),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "grounding_principles": operator.get("grounding_principles", []),
        "navigation_preferences": operator.get("navigation_preferences", []),
        "fundamentals_support_preferences": operator.get("fundamentals_support_preferences", []),
        "working_preferences": operator.get("working_preferences", []),
        "known_do_not_assume": operator.get("known_do_not_assume", []),
        "navigation_guidance_status": _navigation_status(
            project_root,
            operator=operator,
            partnership=partnership,
            relationship_state=relationship_state,
            latest_review=business_review.get("latest_review"),
        ),
    }


def record_business_review(
    project_root: Path,
    *,
    review_id: str,
    summary: str,
    current_focus: str,
    grounded_next_step: str,
    assessment: str,
    tags: list[str],
    replace_existing: bool,
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    if assessment not in {"aligned", "unclear", "drift_risk"}:
        raise ValueError("assessment must be one of aligned, unclear, or drift_risk")
    if confidence is not None and not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    relationship_state = show_relationship_state(project_root)
    loop, storage_root, latest_pointer_path = _business_review_paths(project_root, partnership)
    storage_root.mkdir(parents=True, exist_ok=True)
    review_path = storage_root / f"{review_id}.json"
    existed = review_path.exists()
    if existed and not replace_existing:
        raise ValueError(f"business review `{review_id}` already exists; use replace_existing to overwrite it")
    payload = {
        "schema_version": BUSINESS_REVIEW_SCHEMA_VERSION,
        "review_id": review_id,
        "summary": summary,
        "current_focus": current_focus,
        "grounded_next_step": grounded_next_step,
        "assessment": assessment,
        "business_direction": operator.get("business_direction"),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "review_questions": [value for value in loop.get("review_questions", []) if isinstance(value, str)],
        "relationship_missing_signal_categories": relationship_state.get("missing_signal_categories", []),
        "relationship_next_learning_prompts": relationship_state.get("next_learning_prompts", []),
        "tags": sorted({tag for tag in tags if tag}),
        "source": source,
        "evidence": evidence,
        "confidence": confidence,
        "recorded_at": _isoformat_z(),
    }
    _write_json(review_path, payload)
    pointer_payload = {
        "schema_version": BUSINESS_REVIEW_POINTER_SCHEMA_VERSION,
        "selected_review_id": review_id,
        "selected_review_path": str(review_path.relative_to(project_root).as_posix()),
        "updated_at": payload["recorded_at"],
    }
    _write_json(latest_pointer_path, pointer_payload)
    continuity_checkpoint = record_continuity_checkpoint(
        project_root,
        checkpoint_id=review_id,
        summary=summary,
        next_action=grounded_next_step,
        assessment=assessment,
        tags=sorted({*tags, "business-review"}),
        replace_existing=replace_existing,
        source=source or "record-business-review",
        evidence=evidence,
        confidence=confidence,
    )
    closeout_distillation = record_closeout_distillation(
        project_root,
        review_id=review_id,
        summary=summary,
        next_action=grounded_next_step,
        assessment=assessment,
        continuity_memory_id=continuity_checkpoint["memory_id"],
        tags=sorted({*tags, "business-review"}),
        replace_existing=replace_existing,
        source=source or "record-business-review",
        evidence=evidence,
        confidence=confidence,
    )
    return {
        "status": "pass",
        "review_id": review_id,
        "review_path": str(review_path.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "replaced_existing": bool(existed and replace_existing),
        "continuity_checkpoint": continuity_checkpoint,
        "closeout_distillation": closeout_distillation,
        "business_review_status": show_business_review(project_root).get("business_review_status", {}),
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


def run_navigation_check(
    project_root: Path,
    *,
    scenario: str,
) -> dict[str, Any]:
    return check_navigation_guidance(project_root, scenario)
