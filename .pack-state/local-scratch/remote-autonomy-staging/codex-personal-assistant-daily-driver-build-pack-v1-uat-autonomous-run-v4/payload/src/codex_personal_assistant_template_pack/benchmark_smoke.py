from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from .ambiguity import check_ambiguity
from .alignment import show_alignment
from .context_router import route_context
from .doctor import run_doctor
from .grounding import check_grounding
from .memory import distill_session_memory, read_memory, record_memory, show_memory_distillation
from .operator_intake import record_operator_intake, show_operator_intake
from .profile import show_profile
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

    memory_root = project_root / ".pack-state/assistant-memory"
    intake_root = project_root / ".pack-state/operator-intake"
    distillation_root = project_root / ".pack-state/session-distillation"
    operator_profile_path = project_root / "contracts/operator-profile.json"

    previous_memory_tree = _snapshot_json_tree(memory_root)
    previous_intake_tree = _snapshot_json_tree(intake_root)
    previous_distillation_tree = _snapshot_json_tree(distillation_root)
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
    grounding = check_grounding(
        project_root,
        "I might do some random side work today without a clear link to the current business direction.",
        proposed_next_step="Maybe wander into a few unrelated tasks.",
    )
    memory_snapshot = read_memory(project_root)
    with tempfile.TemporaryDirectory() as tmp_dir:
        bootstrap_result = bootstrap_workspace(project_root, Path(tmp_dir))

    _restore_json_tree(memory_root, previous_memory_tree)
    _restore_json_tree(intake_root, previous_intake_tree)
    _restore_json_tree(distillation_root, previous_distillation_tree)
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
    grounding_status = alignment_after_distillation.get("grounding_accountability_status", {})
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

    checks = {
        "validation": validation["status"],
        "show_profile": profile["status"],
        "show_alignment": alignment["status"],
        "check_ambiguity": "pass" if ambiguity["status"] == "pass" and ambiguity.get("decision") == "clarify" else "fail",
        "route_context": routing["status"],
        "record_memory": memory_write["status"],
        "show_operator_intake": operator_intake_before["status"],
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
        "check_grounding": "pass" if grounding.get("assessment") == "drift_risk" else "fail",
        "grounding_accountability_status": "pass" if grounding_status == expected_grounding_status else "fail",
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
        "session_memory_distillation_status_after_write": distillation_status,
        "alignment_session_memory_distillation_status_after_write": alignment_distillation_status,
        "session_memory_distillation_promoted_memory_id": distillation_write.get("promoted_memory_id"),
        "grounding_assessment": grounding.get("assessment"),
        "grounding_suggested_response": grounding.get("suggested_response"),
        "grounding_accountability_status_after_write": grounding_status,
    }
