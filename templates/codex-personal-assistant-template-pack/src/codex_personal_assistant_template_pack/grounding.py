from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assistant_contracts import load_operator_intake, load_operator_profile, load_partnership_policy
from .context_router import route_context
from .memory import record_closeout_distillation, record_continuity_checkpoint, show_continuity_status
from .operator_intake import record_operator_intake
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


def _load_relationship_reflection_loop(partnership: dict[str, Any]) -> dict[str, Any]:
    loop = partnership.get("relationship_reflection_loop", {})
    return loop if isinstance(loop, dict) else {}


def _load_startup_collaboration_mode(partnership: dict[str, Any]) -> dict[str, Any]:
    loop = partnership.get("startup_collaboration_mode", {})
    return loop if isinstance(loop, dict) else {}


def _load_opportunity_shaping_rules(partnership: dict[str, Any]) -> dict[str, Any]:
    rules = partnership.get("opportunity_shaping_rules", {})
    return rules if isinstance(rules, dict) else {}


def _primary_next_step_anchor(operator: dict[str, Any]) -> str | None:
    for value in operator.get("near_term_priorities", []):
        if isinstance(value, str) and value.strip():
            return value.strip()
    business_direction = operator.get("business_direction")
    if isinstance(business_direction, str) and business_direction.strip():
        return business_direction.strip()
    return None


def _intake_surface_for_category(intake_contract: dict[str, Any], category_id: str) -> dict[str, Any]:
    categories = intake_contract.get("intake_categories", [])
    if not isinstance(categories, list):
        return {}
    for category in categories:
        if not isinstance(category, dict):
            continue
        if category.get("category_id") != category_id:
            continue
        prompt = category.get("prompt")
        refinement_targets = [
            value
            for value in category.get("refinement_targets", [])
            if isinstance(value, str) and value.strip()
        ]
        return {
            "category_id": category_id,
            "prompt": prompt if isinstance(prompt, str) and prompt.strip() else None,
            "refinement_targets": refinement_targets,
        }
    return {}


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


def _relationship_reflection_status(
    *,
    partnership: dict[str, Any],
    relationship_state: dict[str, Any],
    business_review_status: dict[str, Any],
    latest_review: dict[str, Any] | None,
) -> dict[str, Any]:
    loop = partnership.get("relationship_reflection_loop", {})
    if not isinstance(loop, dict):
        loop = {}
    due_conditions = [value for value in loop.get("due_conditions", []) if isinstance(value, str)]
    review_questions = [value for value in loop.get("review_questions", []) if isinstance(value, str)]
    max_prompts = loop.get("max_prompts_per_reflection", 2)
    if not isinstance(max_prompts, int) or max_prompts <= 0:
        max_prompts = 2
    record_surface = loop.get("record_surface")
    if not isinstance(record_surface, str) or not record_surface.strip():
        record_surface = "record-operator-intake"

    missing_signal_categories = [
        value for value in relationship_state.get("missing_signal_categories", []) if isinstance(value, str)
    ]
    next_learning_prompts = relationship_state.get("next_learning_prompts", [])
    prompt_by_category = {
        prompt.get("category_id"): prompt
        for prompt in next_learning_prompts
        if isinstance(prompt, dict) and isinstance(prompt.get("category_id"), str)
    }
    target_order = [value for value in loop.get("target_category_order", []) if isinstance(value, str)]
    ordered_target_categories = [
        category for category in target_order if category in missing_signal_categories
    ] + [
        category for category in missing_signal_categories if category not in target_order
    ]
    target_signal_categories = ordered_target_categories[:max_prompts]
    suggested_reflection_prompts = [
        prompt_by_category[category]
        for category in target_signal_categories
        if category in prompt_by_category
    ]
    thin_history_risk = relationship_state.get("history_enrichment_status", {}).get("thin_history_risk")

    reflection_due = bool(target_signal_categories)
    due_reason = "No missing relationship signal categories require a fresh reflection right now."
    recommended_next_step = "Keep using the assistant and refresh reflection once a new missing signal appears."
    reflection_priority = "low"
    if reflection_due:
        reflection_priority = "medium"
        due_reason = "Relationship signals are still missing; capture one bounded reflection instead of assuming personalization."
        recommended_next_step = (
            "Use record-operator-intake to capture one bounded reflection for the first missing signal category."
        )
        if business_review_status.get("review_due") is True:
            due_reason = (
                "Business review is due and relationship signals are still missing; anchor direction first, then capture one bounded reflection."
            )
            recommended_next_step = (
                "Refresh the business review, then use record-operator-intake for the first missing signal category."
            )
        if len(missing_signal_categories) >= 2 or thin_history_risk == "high":
            reflection_priority = "high"

    recommended_step_sequence: list[dict[str, Any]] = []
    if business_review_status.get("review_due") is True:
        recommended_step_sequence.append(
            {
                "step_id": "anchor_business_review",
                "surface": "record-business-review",
                "reason": "business_review_due",
                "summary": "Refresh the business review first so the next relationship signal is anchored to the current direction.",
                "question": review_questions[0] if review_questions else None,
            }
        )
    if suggested_reflection_prompts:
        first_prompt = suggested_reflection_prompts[0]
        recommended_step_sequence.append(
            {
                "step_id": "capture_missing_relationship_signal",
                "surface": record_surface,
                "reason": "missing_relationship_signal",
                "category_id": first_prompt.get("category_id"),
                "summary": "Capture one bounded reflection for the first missing relationship signal category.",
                "prompt": first_prompt.get("prompt"),
            }
        )
    if not recommended_step_sequence:
        recommended_step_sequence.append(
            {
                "step_id": "continue_observation",
                "surface": None,
                "reason": "no_reflection_due",
                "summary": "No immediate reflection write is due; keep observing real work and refresh the surfaces after the next meaningful session.",
            }
        )

    return {
        "cadence_name": loop.get("cadence_name") or "relationship-signal-reflection",
        "due_condition_count": len(due_conditions),
        "review_question_count": len(review_questions),
        "reflection_due": reflection_due,
        "due_reason": due_reason,
        "reflection_priority": reflection_priority,
        "target_signal_categories": target_signal_categories,
        "suggested_reflection_prompts": suggested_reflection_prompts,
        "max_prompts_per_reflection": max_prompts,
        "recommended_record_surface": record_surface,
        "recommended_next_step": recommended_next_step,
        "recommended_step_sequence": recommended_step_sequence,
        "latest_review_assessment": latest_review.get("assessment") if isinstance(latest_review, dict) else None,
        "business_review_anchor_present": isinstance(latest_review, dict),
        "thin_history_risk": thin_history_risk,
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
    relationship_reflection_status = _relationship_reflection_status(
        partnership=partnership,
        relationship_state=relationship_state,
        business_review_status=business_review_status,
        latest_review=latest_review,
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
        "relationship_reflection_status": relationship_reflection_status,
        "navigation_guidance_status": navigation_status,
    }


def show_startup_collaboration(project_root: Path) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    startup_mode = _load_startup_collaboration_mode(partnership)
    opportunity_rules = _load_opportunity_shaping_rules(partnership)
    business_review = show_business_review(project_root)
    business_review_status = business_review.get("business_review_status", {})
    relationship_state = show_relationship_state(project_root)
    continuity_status = show_continuity_status(project_root)

    trigger_conditions = [
        value for value in startup_mode.get("trigger_conditions", []) if isinstance(value, str) and value.strip()
    ]
    response_steps = [
        value for value in startup_mode.get("response_steps", []) if isinstance(value, str) and value.strip()
    ]
    opening_offer_shape = [
        value for value in startup_mode.get("opening_offer_shape", []) if isinstance(value, str) and value.strip()
    ]
    leadership_balance_rules = [
        value
        for value in startup_mode.get("leadership_balance_rules", [])
        if isinstance(value, str) and value.strip()
    ]
    initial_load_strategy = startup_mode.get("initial_load_strategy", {})
    if not isinstance(initial_load_strategy, dict):
        initial_load_strategy = {}
    meta_disclosure_policy = startup_mode.get("meta_disclosure_policy", {})
    if not isinstance(meta_disclosure_policy, dict):
        meta_disclosure_policy = {}
    collaboration_tone = startup_mode.get("collaboration_tone", {})
    if not isinstance(collaboration_tone, dict):
        collaboration_tone = {}
    opportunity_review_prompts = [
        value for value in opportunity_rules.get("review_prompts", []) if isinstance(value, str) and value.strip()
    ]
    opportunity_response_steps = [
        value for value in opportunity_rules.get("response_steps", []) if isinstance(value, str) and value.strip()
    ]

    business_direction = operator.get("business_direction")
    business_review_due = business_review_status.get("review_due") is True
    continuity_health = continuity_status.get("health")
    missing_signal_category_count = len(relationship_state.get("missing_signal_categories", []))
    recommended_session_posture = "adaptive-collaboration"
    due_reason = "Direction is anchored well enough for the assistant to open with a grounded frame and concrete options."
    default_next_move = "Offer a brief grounded opening and propose one or two high-value ways to begin."
    if business_review_due or continuity_health != "healthy":
        recommended_session_posture = "lead-with-structure"
        due_reason = (
            "Direction or continuity still needs anchoring, so the assistant should lead with structure before wider collaboration."
        )
        default_next_move = "Re-anchor the session to the current direction, then narrow to one grounded next step."
    elif missing_signal_category_count >= 2:
        due_reason = (
            "Direction is anchored, but relationship history is still thin, so the assistant should open with grounded options and learn carefully."
        )

    default_opening_question = "What feels most worth moving right now?"
    suggested_opening_line = "I'm here and ready. Let's make today count without pretending we have to do everything at once."
    if isinstance(business_direction, str) and business_direction.strip():
        suggested_opening_line = "I'm here and ready to help move your business direction forward in a grounded, practical way."
    load_deeper_when = [
        value
        for value in initial_load_strategy.get("load_deeper_when", [])
        if isinstance(value, str) and value.strip()
    ]
    avoid_terms = [
        value for value in meta_disclosure_policy.get("avoid_terms", []) if isinstance(value, str) and value.strip()
    ]
    disclose_when = [
        value for value in meta_disclosure_policy.get("disclose_when", []) if isinstance(value, str) and value.strip()
    ]
    tone_avoid = [
        value for value in collaboration_tone.get("avoid", []) if isinstance(value, str) and value.strip()
    ]

    return {
        "status": "pass",
        "business_direction": business_direction,
        "near_term_priorities": operator.get("near_term_priorities", []),
        "time_reality_constraints": operator.get("time_reality_constraints", []),
        "leadership_preferences": operator.get("leadership_preferences", []),
        "venture_preferences": operator.get("venture_preferences", []),
        "growth_orientation": operator.get("growth_orientation", []),
        "startup_collaboration_status": {
            "cadence_name": startup_mode.get("cadence_name") or "hello-first-grounded-collaboration",
            "trigger_condition_count": len(trigger_conditions),
            "response_step_count": len(response_steps),
            "opening_offer_count": len(opening_offer_shape),
            "leadership_balance_rule_count": len(leadership_balance_rules),
            "business_review_due": business_review_due,
            "continuity_health": continuity_health,
            "missing_signal_category_count": missing_signal_category_count,
            "recommended_session_posture": recommended_session_posture,
            "due_reason": due_reason,
            "default_next_move": default_next_move,
            "default_opening_question": default_opening_question,
            "suggested_opening_line": suggested_opening_line,
            "initial_load_mode": initial_load_strategy.get("default_mode") or "minimal-first",
            "load_deeper_when_count": len(load_deeper_when),
            "meta_disclosure_mode": meta_disclosure_policy.get("default_mode") or "operator-facing-only",
            "avoid_term_count": len(avoid_terms),
            "tone_mode": collaboration_tone.get("default_mode") or "warm-eager-plainspoken",
            "tone_avoid_count": len(tone_avoid),
        },
        "opening_offer_shape": opening_offer_shape,
        "response_steps": response_steps,
        "leadership_balance_rules": leadership_balance_rules,
        "initial_load_strategy": {
            "default_mode": initial_load_strategy.get("default_mode") or "minimal-first",
            "load_deeper_when": load_deeper_when,
        },
        "meta_disclosure_policy": {
            "default_mode": meta_disclosure_policy.get("default_mode") or "operator-facing-only",
            "avoid_terms": avoid_terms,
            "disclose_when": disclose_when,
        },
        "collaboration_tone": {
            "default_mode": collaboration_tone.get("default_mode") or "warm-eager-plainspoken",
            "care_style": collaboration_tone.get("care_style"),
            "avoid": tone_avoid,
        },
        "opportunity_shaping_status": {
            "default_lens": opportunity_rules.get("default_lens") or "mvp-and-poc-first",
            "review_prompt_count": len(opportunity_review_prompts),
            "response_step_count": len(opportunity_response_steps),
            "review_prompts": opportunity_review_prompts,
            "response_steps": opportunity_response_steps,
        },
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
    business_review_status = _business_review_status(
        project_root,
        partnership=partnership,
        relationship_state=relationship_state,
        latest_review=latest_review,
        latest_pointer_path=latest_pointer_path,
        review_count=review_count,
    )
    relationship_reflection_status = _relationship_reflection_status(
        partnership=partnership,
        relationship_state=relationship_state,
        business_review_status=business_review_status,
        latest_review=latest_review,
    )
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
        "business_review_status": business_review_status,
        "relationship_reflection_status": relationship_reflection_status,
        "recommended_step_sequence": relationship_reflection_status.get("recommended_step_sequence", []),
        "review_count": review_count,
    }


def show_relationship_reflection(project_root: Path) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    partnership = load_partnership_policy(project_root)
    intake_contract = load_operator_intake(project_root)
    relationship_state = show_relationship_state(project_root)
    business_review = show_business_review(project_root)
    loop = _load_relationship_reflection_loop(partnership)
    latest_review = business_review.get("latest_review")
    reflection_status = _relationship_reflection_status(
        partnership=partnership,
        relationship_state=relationship_state,
        business_review_status=business_review.get("business_review_status", {}),
        latest_review=latest_review if isinstance(latest_review, dict) else None,
    )
    max_prompt_count = reflection_status.get("max_prompts_per_reflection", 2)
    if not isinstance(max_prompt_count, int) or max_prompt_count < 1:
        max_prompt_count = 2
    target_categories = [
        value for value in reflection_status.get("target_signal_categories", []) if isinstance(value, str)
    ]
    prompts_by_category: dict[str, tuple[str | None, list[str]]] = {}
    for category in intake_contract.get("intake_categories", []):
        if not isinstance(category, dict):
            continue
        category_id = category.get("category_id")
        if not isinstance(category_id, str) or not category_id.strip():
            continue
        prompt = category.get("prompt") if isinstance(category.get("prompt"), str) else None
        refinement_targets = [
            value
            for value in category.get("refinement_targets", [])
            if isinstance(value, str) and value.strip()
        ]
        prompts_by_category[category_id] = (prompt, refinement_targets)
    signal_strength_by_category = {
        entry.get("category_id"): entry
        for entry in relationship_state.get("signal_strength_by_category", [])
        if isinstance(entry, dict) and isinstance(entry.get("category_id"), str)
    }
    reflection_questions = []
    target_signal_status = []
    for category_id in target_categories[:max_prompt_count]:
        signal_entry = signal_strength_by_category.get(category_id, {})
        prompt, refinement_targets = prompts_by_category.get(category_id, (None, []))
        target_signal_status.append(
            {
                "category_id": category_id,
                "signal_strength": signal_entry.get("signal_strength"),
                "ready_for_distillation_review": signal_entry.get("ready_for_distillation_review") is True,
                "refinement_targets": refinement_targets,
            }
        )
        if isinstance(prompt, str) and prompt:
            reflection_questions.append(
                {
                    "category_id": category_id,
                    "prompt": prompt,
                    "refinement_targets": refinement_targets,
                }
            )

    target_category_order = [
        value for value in loop.get("target_category_order", []) if isinstance(value, str) and value.strip()
    ]
    latest_review_id = latest_review.get("review_id") if isinstance(latest_review, dict) else None

    return {
        "status": "pass",
        "business_direction": operator.get("business_direction"),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "relationship_reflection_status": reflection_status,
        "target_signal_status": target_signal_status,
        "reflection_questions": reflection_questions,
        "review_questions": [
            value for value in loop.get("review_questions", []) if isinstance(value, str)
        ],
        "due_conditions": [
            value for value in loop.get("due_conditions", []) if isinstance(value, str)
        ],
        "target_category_order": target_category_order,
        "latest_business_review_id": latest_review_id,
        "recommended_step_sequence": reflection_status.get("recommended_step_sequence", []),
    }


def show_preference_calibration(project_root: Path) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    intake_contract = load_operator_intake(project_root)
    relationship_state = show_relationship_state(project_root)
    business_review = show_business_review(project_root)
    business_review_status = business_review.get("business_review_status", {})
    latest_review = business_review.get("latest_review")
    if not isinstance(latest_review, dict):
        latest_review = None
    review_questions = [
        value for value in business_review.get("review_questions", []) if isinstance(value, str) and value.strip()
    ]
    preference_strength_status = relationship_state.get("preference_strength_status", {})
    intake_surface = _intake_surface_for_category(intake_contract, "preference")
    preference_prompt = intake_surface.get("prompt")
    preference_refinement_targets = intake_surface.get("refinement_targets", [])
    signal_strength = preference_strength_status.get("signal_strength")
    if not isinstance(signal_strength, str) or not signal_strength.strip():
        signal_strength = "missing"

    business_review_anchor_present = latest_review is not None
    business_review_due = business_review_status.get("review_due") is True
    latest_grounded_next_step = latest_review.get("grounded_next_step") if latest_review else None
    latest_review_id = latest_review.get("review_id") if latest_review else None
    latest_review_assessment = latest_review.get("assessment") if latest_review else None

    calibration_due = signal_strength in {"missing", "tentative"}
    calibration_ready = business_review_anchor_present and not business_review_due and calibration_due
    calibration_priority = "low"
    due_reason = "Preference evidence is already strong enough to observe without a fresh calibration."
    recommended_next_step = (
        "Keep observing real work and only record another preference calibration if the operator explicitly confirms or changes a preference."
    )
    recommended_step_sequence: list[dict[str, Any]] = []

    if not business_review_anchor_present or business_review_due:
        calibration_priority = "high" if calibration_due else "medium"
        due_reason = (
            "Refresh the business review before calibrating preferences so the signal stays anchored to the current business direction."
        )
        recommended_next_step = (
            "Use record-business-review first, then capture one bounded preference with record-preference-calibration."
        )
        recommended_step_sequence.append(
            {
                "step_id": "anchor_business_review",
                "surface": "record-business-review",
                "reason": "business_review_due",
                "summary": "Refresh the business review first so any preference calibration stays anchored to the current direction.",
                "question": review_questions[0] if review_questions else None,
            }
        )
        if isinstance(preference_prompt, str) and preference_prompt:
            recommended_step_sequence.append(
                {
                    "step_id": "capture_preference_calibration",
                    "surface": "record-preference-calibration",
                    "reason": "missing_or_tentative_preference",
                    "category_id": "preference",
                    "summary": "After the business review is anchored, capture one bounded working or communication preference.",
                    "prompt": preference_prompt,
                }
            )
    elif calibration_due:
        calibration_priority = "high" if signal_strength == "missing" else "medium"
        due_reason = (
            "Preference evidence is still weak; capture one bounded preference calibration instead of assuming a working style."
        )
        recommended_next_step = (
            "Use record-preference-calibration to capture one bounded working or communication preference tied to the latest business review."
        )
        recommended_step_sequence.append(
            {
                "step_id": "capture_preference_calibration",
                "surface": "record-preference-calibration",
                "reason": "missing_or_tentative_preference",
                "category_id": "preference",
                "summary": "Capture one bounded working or communication preference while the current business direction is anchored.",
                "prompt": preference_prompt,
            }
        )
    elif signal_strength == "repeated":
        due_reason = (
            "Preference evidence is already repeated; keep using it cautiously unless the operator explicitly confirms or changes it."
        )
        recommended_step_sequence.append(
            {
                "step_id": "continue_observation",
                "surface": None,
                "reason": "preference_signal_repeated",
                "summary": "No immediate preference calibration is required; keep observing until the preference is explicitly confirmed or changes.",
            }
        )
    else:
        due_reason = "Preference evidence is already confirmed and does not need a fresh calibration right now."
        recommended_step_sequence.append(
            {
                "step_id": "continue_observation",
                "surface": None,
                "reason": "preference_signal_confirmed",
                "summary": "No fresh preference calibration is required; keep observing for meaningful changes instead.",
            }
        )

    return {
        "status": "pass",
        "business_direction": operator.get("business_direction"),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "latest_business_review_id": latest_review_id,
        "latest_business_review_assessment": latest_review_assessment,
        "latest_business_review_grounded_next_step": latest_grounded_next_step,
        "preference_prompt": preference_prompt,
        "preference_refinement_targets": preference_refinement_targets,
        "preference_strength_status": preference_strength_status,
        "preference_calibration_status": {
            "business_review_anchor_present": business_review_anchor_present,
            "business_review_due": business_review_due,
            "calibration_due": calibration_due,
            "calibration_ready": calibration_ready,
            "calibration_priority": calibration_priority,
            "due_reason": due_reason,
            "recommended_record_surface": "record-preference-calibration",
            "recommended_next_step": recommended_next_step,
            "recommended_step_sequence": recommended_step_sequence,
            "latest_business_review_id": latest_review_id,
            "latest_business_review_grounded_next_step": latest_grounded_next_step,
            "preference_signal_strength": signal_strength,
        },
        "recommended_step_sequence": recommended_step_sequence,
    }


def show_communication_calibration(project_root: Path) -> dict[str, Any]:
    operator = load_operator_profile(project_root)
    intake_contract = load_operator_intake(project_root)
    relationship_state = show_relationship_state(project_root)
    business_review = show_business_review(project_root)
    business_review_status = business_review.get("business_review_status", {})
    latest_review = business_review.get("latest_review")
    if not isinstance(latest_review, dict):
        latest_review = None
    review_questions = [
        value for value in business_review.get("review_questions", []) if isinstance(value, str) and value.strip()
    ]
    communication_strength_status = next(
        (
            entry
            for entry in relationship_state.get("signal_strength_by_category", [])
            if isinstance(entry, dict) and entry.get("category_id") == "communication_pattern"
        ),
        {
            "category_id": "communication_pattern",
            "signal_strength": "missing",
            "ready_for_durable_use": False,
            "source_counts": {
                "operator_intake": 0,
                "session_distillation": 0,
                "assistant_memory": 0,
            },
            "total_signal_count": 0,
            "next_prompt": None,
        },
    )
    intake_surface = _intake_surface_for_category(intake_contract, "communication_pattern")
    communication_prompt = intake_surface.get("prompt")
    communication_refinement_targets = intake_surface.get("refinement_targets", [])
    signal_strength = communication_strength_status.get("signal_strength")
    if not isinstance(signal_strength, str) or not signal_strength.strip():
        signal_strength = "missing"

    business_review_anchor_present = latest_review is not None
    business_review_due = business_review_status.get("review_due") is True
    latest_grounded_next_step = latest_review.get("grounded_next_step") if latest_review else None
    latest_review_id = latest_review.get("review_id") if latest_review else None
    latest_review_assessment = latest_review.get("assessment") if latest_review else None

    calibration_due = signal_strength in {"missing", "tentative"}
    calibration_ready = business_review_anchor_present and not business_review_due and calibration_due
    calibration_priority = "low"
    due_reason = "Communication-pattern evidence is already strong enough to keep observing without a fresh calibration."
    recommended_next_step = (
        "Keep observing real work and only record another communication calibration if the operator explicitly confirms or changes the pattern."
    )
    recommended_step_sequence: list[dict[str, Any]] = []

    if not business_review_anchor_present or business_review_due:
        calibration_priority = "high" if calibration_due else "medium"
        due_reason = (
            "Refresh the business review before calibrating communication patterns so the signal stays anchored to the current business direction."
        )
        recommended_next_step = (
            "Use record-business-review first, then capture one bounded communication pattern with record-communication-calibration."
        )
        recommended_step_sequence.append(
            {
                "step_id": "anchor_business_review",
                "surface": "record-business-review",
                "reason": "business_review_due",
                "summary": "Refresh the business review first so any communication calibration stays anchored to the current direction.",
                "question": review_questions[0] if review_questions else None,
            }
        )
        if isinstance(communication_prompt, str) and communication_prompt:
            recommended_step_sequence.append(
                {
                    "step_id": "capture_communication_calibration",
                    "surface": "record-communication-calibration",
                    "reason": "missing_or_tentative_communication_pattern",
                    "category_id": "communication_pattern",
                    "summary": "After the business review is anchored, capture one bounded recurring communication pattern.",
                    "prompt": communication_prompt,
                }
            )
    elif calibration_due:
        calibration_priority = "high" if signal_strength == "missing" else "medium"
        due_reason = (
            "Communication-pattern evidence is still weak; capture one bounded calibration instead of assuming how the assistant should communicate."
        )
        recommended_next_step = (
            "Use record-communication-calibration to capture one bounded recurring communication pattern tied to the latest business review."
        )
        recommended_step_sequence.append(
            {
                "step_id": "capture_communication_calibration",
                "surface": "record-communication-calibration",
                "reason": "missing_or_tentative_communication_pattern",
                "category_id": "communication_pattern",
                "summary": "Capture one bounded recurring communication pattern while the current business direction is anchored.",
                "prompt": communication_prompt,
            }
        )
    elif signal_strength == "repeated":
        due_reason = (
            "Communication-pattern evidence is already repeated; keep using it cautiously unless the operator explicitly confirms or changes it."
        )
        recommended_step_sequence.append(
            {
                "step_id": "continue_observation",
                "surface": None,
                "reason": "communication_pattern_repeated",
                "summary": "No immediate communication calibration is required; keep observing until the operator explicitly confirms or changes the pattern.",
            }
        )
    else:
        due_reason = "Communication-pattern evidence is already confirmed and does not need a fresh calibration right now."
        recommended_step_sequence.append(
            {
                "step_id": "continue_observation",
                "surface": None,
                "reason": "communication_pattern_confirmed",
                "summary": "No fresh communication calibration is required; keep observing for meaningful changes instead.",
            }
        )

    return {
        "status": "pass",
        "business_direction": operator.get("business_direction"),
        "near_term_priorities": operator.get("near_term_priorities", []),
        "latest_business_review_id": latest_review_id,
        "latest_business_review_assessment": latest_review_assessment,
        "latest_business_review_grounded_next_step": latest_grounded_next_step,
        "communication_prompt": communication_prompt,
        "communication_refinement_targets": communication_refinement_targets,
        "communication_pattern_strength_status": communication_strength_status,
        "communication_calibration_status": {
            "business_review_anchor_present": business_review_anchor_present,
            "business_review_due": business_review_due,
            "calibration_due": calibration_due,
            "calibration_ready": calibration_ready,
            "calibration_priority": calibration_priority,
            "due_reason": due_reason,
            "recommended_record_surface": "record-communication-calibration",
            "recommended_next_step": recommended_next_step,
            "recommended_step_sequence": recommended_step_sequence,
            "latest_business_review_id": latest_review_id,
            "latest_business_review_grounded_next_step": latest_grounded_next_step,
            "communication_signal_strength": signal_strength,
        },
        "recommended_step_sequence": recommended_step_sequence,
    }


def record_relationship_reflection(
    project_root: Path,
    *,
    reflection_id: str,
    category: str,
    summary: str,
    next_action: str | None,
    tags: list[str],
    replace_existing: bool,
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
    refine_profile_json: str | None = None,
) -> dict[str, Any]:
    intake_result = record_operator_intake(
        project_root,
        intake_id=reflection_id,
        category=category,
        summary=summary,
        next_action=next_action,
        tags=sorted({*tags, "relationship-reflection"}),
        replace_existing=replace_existing,
        source=source or "record-relationship-reflection",
        evidence=evidence,
        confidence=confidence,
        refine_profile_json=refine_profile_json,
    )
    return {
        "status": "pass",
        "reflection_id": reflection_id,
        "category": category,
        "intake_result": intake_result,
        "relationship_reflection_status": show_relationship_reflection(project_root).get(
            "relationship_reflection_status", {}
        ),
    }


def record_preference_calibration(
    project_root: Path,
    *,
    calibration_id: str,
    summary: str,
    next_action: str | None,
    tags: list[str],
    replace_existing: bool,
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
    refine_profile_json: str | None = None,
) -> dict[str, Any]:
    calibration = show_preference_calibration(project_root)
    calibration_status = calibration.get("preference_calibration_status", {})
    if calibration_status.get("business_review_anchor_present") is not True:
        raise ValueError("record-business-review must run before record-preference-calibration")
    if calibration_status.get("business_review_due") is True:
        raise ValueError("refresh the business review before recording preference calibration")
    resolved_next_action = next_action
    if not isinstance(resolved_next_action, str) or not resolved_next_action.strip():
        fallback = calibration_status.get("latest_business_review_grounded_next_step")
        resolved_next_action = fallback if isinstance(fallback, str) and fallback.strip() else None
    intake_result = record_operator_intake(
        project_root,
        intake_id=calibration_id,
        category="preference",
        summary=summary,
        next_action=resolved_next_action,
        tags=sorted({*tags, "preference-calibration"}),
        replace_existing=replace_existing,
        source=source or "record-preference-calibration",
        evidence=evidence,
        confidence=confidence,
        refine_profile_json=refine_profile_json,
        memory_category="preference",
    )
    return {
        "status": "pass",
        "calibration_id": calibration_id,
        "used_default_next_action": next_action is None and isinstance(resolved_next_action, str),
        "intake_result": intake_result,
        "preference_calibration_status": show_preference_calibration(project_root).get(
            "preference_calibration_status", {}
        ),
    }


def record_communication_calibration(
    project_root: Path,
    *,
    calibration_id: str,
    summary: str,
    next_action: str | None,
    tags: list[str],
    replace_existing: bool,
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
    refine_profile_json: str | None = None,
) -> dict[str, Any]:
    calibration = show_communication_calibration(project_root)
    calibration_status = calibration.get("communication_calibration_status", {})
    if calibration_status.get("business_review_anchor_present") is not True:
        raise ValueError("record-business-review must run before record-communication-calibration")
    if calibration_status.get("business_review_due") is True:
        raise ValueError("refresh the business review before recording communication calibration")
    resolved_next_action = next_action
    if not isinstance(resolved_next_action, str) or not resolved_next_action.strip():
        fallback = calibration_status.get("latest_business_review_grounded_next_step")
        resolved_next_action = fallback if isinstance(fallback, str) and fallback.strip() else None
    intake_result = record_operator_intake(
        project_root,
        intake_id=calibration_id,
        category="communication_pattern",
        summary=summary,
        next_action=resolved_next_action,
        tags=sorted({*tags, "communication-calibration"}),
        replace_existing=replace_existing,
        source=source or "record-communication-calibration",
        evidence=evidence,
        confidence=confidence,
        refine_profile_json=refine_profile_json,
        memory_category="communication_pattern",
    )
    return {
        "status": "pass",
        "calibration_id": calibration_id,
        "used_default_next_action": next_action is None and isinstance(resolved_next_action, str),
        "intake_result": intake_result,
        "communication_calibration_status": show_communication_calibration(project_root).get(
            "communication_calibration_status", {}
        ),
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
    business_review_after = show_business_review(project_root)
    return {
        "status": "pass",
        "review_id": review_id,
        "review_path": str(review_path.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "replaced_existing": bool(existed and replace_existing),
        "continuity_checkpoint": continuity_checkpoint,
        "closeout_distillation": closeout_distillation,
        "business_review_status": business_review_after.get("business_review_status", {}),
        "relationship_reflection_status": business_review_after.get("relationship_reflection_status", {}),
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
