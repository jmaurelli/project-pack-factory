from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from .ambiguity import check_ambiguity
from .alignment import show_alignment
from .context_router import route_context
from .doctor import run_doctor
from .grounding import (
    check_grounding,
    check_navigation_guidance,
    record_business_review,
    show_business_review,
    show_navigation_guidance,
)
from .memory import (
    distill_session_memory,
    read_memory,
    record_memory,
    show_continuity_status,
    show_memory_distillation,
)
from .operator_intake import record_operator_intake, show_operator_intake
from .profile import show_profile
from .relationship_state import show_relationship_state
from .validate_project_pack import validate_project_pack
from .workspace_bootstrap import bootstrap_workspace


def _snapshot_json_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.json"))
        if path.is_file()
    }


def _restore_json_tree(root: Path, snapshot: dict[str, str]) -> None:
    if root.exists():
        for path in sorted(root.rglob("*.json"), reverse=True):
            path.unlink()
    for relative_path, text in snapshot.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def benchmark_smoke(project_root: Path) -> dict[str, Any]:
    validation = validate_project_pack(project_root)
    profile = show_profile(project_root)
    alignment = show_alignment(project_root)
    ambiguity = check_ambiguity(
        project_root,
        "I have a few ideas and maybe should do some side work today, but I am not sure what actually matters most.",
    )
    routing = route_context(project_root, "goals")
    doctor = run_doctor(project_root)
    operator_intake_before = show_operator_intake(project_root)
    relationship_state_before = show_relationship_state(project_root)
    business_review_before = show_business_review(project_root)
    navigation_guidance_before = show_navigation_guidance(project_root)

    memory_root = project_root / ".pack-state/assistant-memory"
    intake_root = project_root / ".pack-state/operator-intake"
    distillation_root = project_root / ".pack-state/session-distillation"
    business_review_root = project_root / ".pack-state/business-grounding-reviews"
    operator_profile_path = project_root / "contracts/operator-profile.json"

    previous_memory_tree = _snapshot_json_tree(memory_root)
    previous_intake_tree = _snapshot_json_tree(intake_root)
    previous_distillation_tree = _snapshot_json_tree(distillation_root)
    previous_business_review_tree = _snapshot_json_tree(business_review_root)
    previous_operator_profile_text = operator_profile_path.read_text(encoding="utf-8")

    memory_write = record_memory(
        project_root,
        memory_id="benchmark-smoke-memory",
        category="communication_pattern",
        summary="Smoke benchmark confirmed operator-alignment assistant surfaces.",
        next_action="Use doctor and PackFactory validation before wider rollout.",
        tags=["benchmark", "smoke"],
        replace_existing=True,
        source="benchmark_smoke",
        evidence="automated benchmark smoke run",
        confidence=1.0,
    )
    preference_memory_write = record_memory(
        project_root,
        memory_id="benchmark-preference-memory",
        category="preference",
        summary="The operator prefers concise grounded answers during daily work.",
        next_action="Keep preference evidence inspectable until repeated or confirmed.",
        tags=["benchmark", "smoke", "preference"],
        replace_existing=True,
        source="benchmark_smoke",
        evidence="automated benchmark smoke run",
        confidence=1.0,
    )

    refinement_payload = {
        "working_preferences": [
            "Use operator-intake records to refine the relationship model explicitly."
        ],
        "near_term_priorities": [
            "Keep the operator aligned with their current business direction."
        ],
    }
    intake_write = record_operator_intake(
        project_root,
        intake_id="benchmark-smoke-intake",
        category="communication_pattern",
        summary="Smoke benchmark exercised the operator intake and bounded refinement flow.",
        next_action="Review the updated operator-intake contract and preserve the new signal only if it is stable.",
        tags=["benchmark", "smoke", "operator-intake"],
        replace_existing=True,
        source="benchmark_smoke",
        evidence="automated benchmark smoke run",
        confidence=1.0,
        refine_profile_json=json.dumps(refinement_payload, sort_keys=True),
    )
    operator_intake_after = show_operator_intake(project_root)
    alignment_after_intake = show_alignment(project_root)
    distillation_before = show_memory_distillation(project_root)
    distillation_write = distill_session_memory(
        project_root,
        distillation_id="benchmark-session-distillation",
        summary="Repeated concise and grounding-oriented session signals should persist as a communication pattern.",
        stable_signal_reason="The benchmark combines a direct session memory and an intake-backed relationship signal to justify an explicit promoted pattern.",
        source_memory_ids=[
            "benchmark-smoke-memory",
            "operator-intake-benchmark-smoke-intake",
        ],
        replace_existing=True,
        promote_category="communication_pattern",
        next_action="Use the promoted relationship memory in future sessions only as advisory context.",
        tags=["benchmark", "smoke", "session-distillation"],
        source="benchmark_smoke",
        evidence="automated benchmark smoke run",
        confidence=1.0,
    )
    distillation_after = show_memory_distillation(project_root)
    alignment_after_distillation = show_alignment(project_root)
    relationship_state_after = show_relationship_state(project_root)
    business_review_write = record_business_review(
        project_root,
        review_id="benchmark-business-review",
        summary="The assistant should keep weekly work tied to the operator's business direction and surface drift early.",
        current_focus="Improve the assistant's grounded business-partner behavior in bounded slices.",
        grounded_next_step="Keep the next assistant iteration tied to business direction, relationship gaps, and the smallest high-value behavior change.",
        assessment="aligned",
        tags=["benchmark", "smoke", "business-review"],
        replace_existing=True,
        source="benchmark_smoke",
        evidence="automated benchmark smoke run",
        confidence=1.0,
    )
    business_review_after = show_business_review(project_root)
    relationship_state_after_review = show_relationship_state(project_root)
    alignment_after_review = show_alignment(project_root)
    continuity_after_review = show_continuity_status(project_root)
    doctor_after_review = run_doctor(project_root)
    grounding = check_grounding(
        project_root,
        "I might do some random side work today without a clear link to the current business direction.",
        proposed_next_step="Maybe wander into a few unrelated tasks.",
    )
    navigation_check = check_navigation_guidance(
        project_root,
        "I know the general direction I want to go, but the road is curvy and I do not have deep fundamental knowledge of every technology involved yet.",
    )
    memory_snapshot = read_memory(project_root)
    with tempfile.TemporaryDirectory() as tmp_dir:
        bootstrap_result = bootstrap_workspace(project_root, Path(tmp_dir))

    _restore_json_tree(memory_root, previous_memory_tree)
    _restore_json_tree(intake_root, previous_intake_tree)
    _restore_json_tree(distillation_root, previous_distillation_tree)
    _restore_json_tree(business_review_root, previous_business_review_tree)
    operator_profile_path.write_text(previous_operator_profile_text, encoding="utf-8")

    refined_preferences = set(alignment_after_intake.get("working_preferences", []))
    refined_priorities = set(alignment_after_intake.get("near_term_priorities", []))
    operator_intake_status = operator_intake_after.get("operator_intake_status", {})
    alignment_intake_status = alignment_after_intake.get("operator_intake_status", {})
    expected_intake_status = {
        "latest_intake_id": "benchmark-smoke-intake",
        "latest_pointer_path": operator_intake_after.get("latest_pointer_path"),
        "intake_count": operator_intake_after.get("intake_count"),
        "latest_intake_has_explicit_profile_refinement": True,
    }
    refinement_visible = (
        "Use operator-intake records to refine the relationship model explicitly." in refined_preferences
        and "Keep the operator aligned with their current business direction." in refined_priorities
    )
    distillation_status = distillation_after.get("session_memory_distillation_status", {})
    alignment_distillation_status = alignment_after_distillation.get("session_memory_distillation_status", {})
    expected_distillation_status = {
        "latest_distillation_id": "benchmark-session-distillation",
        "latest_pointer_path": distillation_after.get("latest_pointer_path"),
        "distillation_count": distillation_after.get("distillation_count"),
        "latest_distillation_promoted_memory": True,
        "latest_promoted_memory_id": "session-distillation-benchmark-session-distillation",
    }
    grounding_status = alignment_after_review.get("grounding_accountability_status", {})
    relationship_state_summary = alignment_after_review.get("relationship_state_summary", {})
    business_review_status = business_review_after.get("business_review_status", {})
    alignment_business_review_status = alignment_after_review.get("business_review_status", {})
    preference_strength_status = relationship_state_after.get("preference_strength_status", {})
    alignment_preference_strength_status = alignment_after_review.get("preference_strength_status", {})
    relationship_covered_categories = relationship_state_after.get("covered_signal_categories", [])
    relationship_missing_categories = relationship_state_after.get("missing_signal_categories", [])
    relationship_covered_categories_after_review = relationship_state_after_review.get("covered_signal_categories", [])
    relationship_missing_categories_after_review = relationship_state_after_review.get("missing_signal_categories", [])
    intake_prompt_by_category = {
        category.get("category_id"): category.get("prompt")
        for category in operator_intake_after.get("intake_categories", [])
        if isinstance(category, dict)
        and isinstance(category.get("category_id"), str)
        and isinstance(category.get("prompt"), str)
    }
    expected_next_learning_prompts = [
        {
            "category_id": category_id,
            "prompt": intake_prompt_by_category[category_id],
        }
        for category_id in relationship_missing_categories
        if category_id in intake_prompt_by_category
    ][:3]
    expected_next_learning_prompts_after_review = [
        {
            "category_id": category_id,
            "prompt": intake_prompt_by_category[category_id],
        }
        for category_id in relationship_missing_categories_after_review
        if category_id in intake_prompt_by_category
    ][:3]
    expected_grounding_status = {
        "cadence_name": "grounded-check-in",
        "trigger_condition_count": 3,
        "response_step_count": 4,
        "review_prompt_count": 3,
        "grounding_behavior_count": len(alignment.get("grounding_behaviors", [])),
        "ambiguity_default": "ask-clarifying-question",
        "trigger_conditions": [
            "work appears to drift from stated goals",
            "the operator's intent is ambiguous",
            "the assistant is about to commit to a path with hidden tradeoffs",
        ],
        "response_steps": [
            "name the current work plainly",
            "compare it to the operator's stated direction",
            "surface the mismatch or drift directly",
            "ask the minimum clarifying question needed or propose the next grounded step",
        ],
        "review_prompts": [
            "What outcome matters most right now?",
            "Does this still support the operator's larger direction?",
            "What is the smallest grounded next step?",
        ],
        "sample_assessment": "aligned",
        "sample_suggested_response": "Continue and keep the next step tied to the current business direction.",
    }
    expected_business_review_status = {
        "cadence_name": "weekly-business-grounding-review",
        "latest_review_id": "benchmark-business-review",
        "latest_pointer_path": ".pack-state/business-grounding-reviews/latest-review.json",
        "review_count": 1,
        "review_question_count": 4,
        "due_condition_count": 3,
        "review_due": False,
        "due_reason": "Recent business grounding review is available.",
        "latest_review_assessment": "aligned",
        "missing_signal_category_count": len(relationship_missing_categories_after_review),
    }
    expected_continuity_status = {
        "status": "pass",
        "health": "healthy",
        "reason": "Assistant continuity memory is available for the latest session.",
        "recommended_action": "Continue and refresh continuity again at the next meaningful session boundary.",
        "latest_pointer_present": True,
        "latest_pointer_path": ".pack-state/assistant-memory/latest-memory.json",
        "latest_memory_id": "continuity-benchmark-business-review",
        "latest_memory_category": "goal",
        "latest_memory_recorded_at": continuity_after_review.get("latest_memory_recorded_at"),
        "stale_after_hours": 168,
        "age_hours": continuity_after_review.get("age_hours"),
    }
    navigation_status = show_navigation_guidance(project_root).get("navigation_guidance_status", {})
    alignment_navigation_status = alignment_after_review.get("navigation_guidance_status", {})
    preference_source_counts = preference_strength_status.get("source_counts", {})
    preference_total_signal_count = int(preference_strength_status.get("total_signal_count", 0) or 0)
    preference_source_kind_count = sum(
        1
        for count in preference_source_counts.values()
        if isinstance(count, int) and count > 0
    )
    expected_preference_strength = "missing"
    if preference_total_signal_count > 0:
        if (
            isinstance(preference_source_counts.get("session_distillation"), int)
            and preference_source_counts.get("session_distillation", 0) > 0
            and isinstance(preference_source_counts.get("assistant_memory"), int)
            and preference_source_counts.get("assistant_memory", 0) > 0
        ):
            expected_preference_strength = "confirmed"
        elif preference_source_kind_count >= 2 or preference_total_signal_count >= 3:
            expected_preference_strength = "repeated"
        else:
            expected_preference_strength = "tentative"

    checks = {
        "validation": validation["status"],
        "show_profile": profile["status"],
        "show_alignment": alignment["status"],
        "check_ambiguity": "pass" if ambiguity["status"] == "pass" and ambiguity.get("decision") == "clarify" else "fail",
        "route_context": routing["status"],
        "record_memory": memory_write["status"],
        "record_preference_memory": preference_memory_write["status"],
        "show_operator_intake": operator_intake_before["status"],
        "show_relationship_state": relationship_state_before["status"],
        "show_business_review": business_review_before["status"],
        "show_navigation_guidance": navigation_guidance_before["status"],
        "record_operator_intake": intake_write["status"],
        "operator_intake_status": "pass" if operator_intake_status == expected_intake_status else "fail",
        "alignment_operator_intake_status": "pass" if alignment_intake_status == expected_intake_status else "fail",
        "operator_intake_refinement_visible": "pass" if refinement_visible else "fail",
        "show_memory_distillation": distillation_before["status"],
        "distill_session_memory": distillation_write["status"],
        "session_memory_distillation_status": "pass"
        if distillation_status == expected_distillation_status
        else "fail",
        "alignment_session_memory_distillation_status": "pass"
        if alignment_distillation_status == expected_distillation_status
        else "fail",
        "relationship_state_personalization_stage": "pass"
        if relationship_state_after.get("personalization_stage") in {"learning", "grounded"}
        else "fail",
        "relationship_state_signal_categories": "pass"
        if "communication_pattern" in relationship_covered_categories
        and not (set(relationship_covered_categories) & set(relationship_missing_categories))
        else "fail",
        "relationship_state_learning_prompts": "pass"
        if relationship_state_after.get("next_learning_prompts") == expected_next_learning_prompts
        else "fail",
        "preference_strength_status": "pass"
        if preference_strength_status.get("category_id") == "preference"
        and preference_strength_status.get("signal_strength") == expected_preference_strength
        and int(preference_source_counts.get("assistant_memory", 0) or 0) >= 1
        else "fail",
        "alignment_relationship_state_summary": "pass"
        if relationship_state_summary.get("personalization_stage") == relationship_state_after_review.get("personalization_stage")
        and relationship_state_summary.get("covered_signal_categories") == relationship_covered_categories_after_review
        and relationship_state_summary.get("missing_signal_categories") == relationship_missing_categories_after_review
        and relationship_state_summary.get("next_learning_prompts") == expected_next_learning_prompts_after_review
        and relationship_state_summary.get("preference_signal_strength") == expected_preference_strength
        else "fail",
        "alignment_preference_strength_status": "pass"
        if alignment_preference_strength_status == preference_strength_status
        else "fail",
        "record_business_review": business_review_write["status"],
        "business_review_status": "pass" if business_review_status == expected_business_review_status else "fail",
        "alignment_business_review_status": "pass"
        if alignment_business_review_status == expected_business_review_status
        else "fail",
        "continuity_status": "pass"
        if continuity_after_review == expected_continuity_status
        else "fail",
        "alignment_continuity_status": "pass"
        if alignment_after_review.get("continuity_status") == expected_continuity_status
        else "fail",
        "doctor_continuity_status": "pass"
        if doctor_after_review.get("continuity_health") == "healthy"
        and doctor_after_review.get("latest_memory_pointer_present") is True
        else "fail",
        "check_grounding": "pass" if grounding.get("assessment") == "drift_risk" else "fail",
        "check_navigation_guidance": "pass"
        if navigation_check.get("assessment") == "fundamentals_gap_with_unclear_path"
        and navigation_check.get("work_mode") == "learning"
        and navigation_check.get("path_shape") == "curvy"
        and navigation_check.get("next_step_anchor") == profile.get("near_term_priorities", [None])[0]
        and isinstance(navigation_check.get("fundamentals_explanation"), str)
        else "fail",
        "grounding_accountability_status": "pass" if grounding_status == expected_grounding_status else "fail",
        "navigation_guidance_status": "pass"
        if navigation_status.get("cadence_name") == "direction-to-decision-guidance"
        and navigation_status.get("trigger_condition_count") == 3
        and navigation_status.get("response_step_count") == 5
        and navigation_status.get("review_prompt_count") == 4
        and navigation_status.get("fundamentals_gap_indicator_count") == 3
        and navigation_status.get("primary_next_step_anchor") == profile.get("near_term_priorities", [None])[0]
        and navigation_status.get("supports_curvy_path") is True
        and navigation_status.get("north_star_present") is True
        and navigation_status.get("sample_assessment") == "fundamentals_gap_with_unclear_path"
        and navigation_status.get("sample_work_mode") == "learning"
        and isinstance(navigation_status.get("sample_reason"), str)
        else "fail",
        "alignment_navigation_guidance_status": "pass"
        if alignment_navigation_status.get("cadence_name") == "direction-to-decision-guidance"
        and alignment_navigation_status.get("latest_business_review_assessment") == "aligned"
        and alignment_navigation_status.get("missing_signal_category_count") == len(relationship_missing_categories_after_review)
        and alignment_navigation_status.get("sample_assessment") == "fundamentals_gap_with_unclear_path"
        and alignment_navigation_status.get("sample_work_mode") == "learning"
        else "fail",
        "read_memory": memory_snapshot["status"],
        "bootstrap_workspace": bootstrap_result["status"],
        "doctor": doctor["status"],
    }
    failed_checks = sorted(name for name, status in checks.items() if status != "pass")

    return {
        "status": "pass" if not failed_checks else "fail",
        "project_root": str(project_root),
        "benchmark_id": "codex-personal-assistant-template-pack-smoke-small-001",
        "checks": checks,
        "failed_checks": failed_checks,
        "ambiguity_decision": ambiguity.get("decision"),
        "ambiguity_question": ambiguity.get("question"),
        "matched_route": routing.get("matched_route"),
        "memory_count_after_write": memory_snapshot.get("memory_count"),
        "doctor_errors": doctor.get("errors", []),
        "operator_intake_categories": operator_intake_after.get("intake_categories", []),
        "operator_intake_count_after_write": operator_intake_after.get("intake_count"),
        "operator_intake_status_after_write": operator_intake_status,
        "alignment_operator_intake_status_after_write": alignment_intake_status,
        "operator_intake_refinement_fields": intake_write.get("profile_refinement_fields", []),
        "preference_strength_status_after_write": preference_strength_status,
        "alignment_preference_strength_status_after_write": alignment_preference_strength_status,
        "session_memory_distillation_status_after_write": distillation_status,
        "alignment_session_memory_distillation_status_after_write": alignment_distillation_status,
        "session_memory_distillation_promoted_memory_id": distillation_write.get("promoted_memory_id"),
        "relationship_state_after_write": relationship_state_after_review,
        "alignment_relationship_state_summary_after_write": relationship_state_summary,
        "business_review_status_after_write": business_review_status,
        "alignment_business_review_status_after_write": alignment_business_review_status,
        "continuity_status_after_write": continuity_after_review,
        "alignment_continuity_status_after_write": alignment_after_review.get("continuity_status", {}),
        "doctor_continuity_status_after_write": {
            "health": doctor_after_review.get("continuity_health"),
            "pointer_present": doctor_after_review.get("latest_memory_pointer_present"),
            "reason": doctor_after_review.get("continuity_reason"),
            "recommended_action": doctor_after_review.get("continuity_recommended_action"),
        },
        "grounding_assessment": grounding.get("assessment"),
        "grounding_suggested_response": grounding.get("suggested_response"),
        "grounding_accountability_status_after_write": grounding_status,
        "navigation_check_assessment": navigation_check.get("assessment"),
        "navigation_check_recommended_action": navigation_check.get("recommended_action"),
        "navigation_guidance_status_after_write": navigation_status,
        "alignment_navigation_guidance_status_after_write": alignment_navigation_status,
    }
