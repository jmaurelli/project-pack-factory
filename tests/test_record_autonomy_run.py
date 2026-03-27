from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from factory_ops import load_json
from record_autonomy_run import append_event, finalize_run, start_run


SOURCE_PACK_ID = "release-evidence-summarizer-build-pack-v2"
READY_PACK_ID = "json-health-checker-feedback-baseline-build-pack-v1"


def _copy_factory(tmp_path: Path) -> Path:
    destination = tmp_path / "factory"

    def _ignore(_dir: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
            or name.endswith(".egg-info")
        }

    shutil.copytree(ROOT, destination, ignore=_ignore)
    return destination


def test_record_autonomy_run_happy_path(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    pack_root = factory_root / "build-packs" / SOURCE_PACK_ID
    os.environ["PROJECT_PACK_FACTORY_FIXED_NOW"] = "2026-03-23T03:00:00Z"
    try:
        start_payload = start_run(
            pack_root=pack_root,
            run_id="loop-run-001",
            notes=[],
            factory_root=factory_root,
        )
        run_root = Path(start_payload["run_root"])
        summary_path = run_root / "run-summary.json"
        events_path = run_root / "loop-events.jsonl"

        assert events_path.exists()
        assert not summary_path.exists()

        append_payload = append_event(
            pack_root=pack_root,
            run_id="loop-run-001",
            event_type="task_selected",
            outcome="selected",
            decision_source="canonical_only",
            memory_state="not_used",
            commands_attempted=[],
            notes=["Selected the canonical task from status/work-state.json."],
            evidence_paths=[],
            stop_reason=None,
            active_task_id="run_build_pack_validation",
            next_recommended_task_id="run_build_pack_validation",
            factory_root=factory_root,
        )
        assert append_payload["step_index"] == 2

        finalize_payload = finalize_run(
            pack_root=pack_root,
            run_id="loop-run-001",
            schema_factory_root=factory_root,
            validation_factory_root=factory_root,
        )
        assert finalize_payload["schema_version"] == "autonomy-run-summary/v1"
        assert finalize_payload["run_id"] == "loop-run-001"

        summary = load_json(summary_path)
        assert summary["schema_version"] == "autonomy-run-summary/v1"
        assert summary["step_count"] == 2
        assert summary["autonomy_budget"]["status"] == "within_budget"
        assert summary["autonomy_budget"]["observed"]["max_step_count"] == 2
        assert 0 <= summary["metrics"]["task_completion_rate"] <= 1
        assert summary["metrics"]["validation_evidence_gain"] is False
        assert summary["metrics"]["benchmark_evidence_gain"] is False
        assert summary["metrics"]["canonical_state_integrity"]["status"] == "fail"
        assert summary["recommended_next_action"]
        feedback = load_json(Path(finalize_payload["artifacts"]["feedback_memory_path"]))
        assert feedback["autonomy_budget"]["status"] == "within_budget"
        assert feedback["memory_tier"]["tier"] == "restart_memory"
        negative = feedback["negative_memory_summary"]
        assert negative["status"] == "observed"
        assert "avoid_trusting_runs_without_canonical_integrity" in negative["avoidance_ids"]
        assert any("Avoid trusting autonomy memory" in line for line in negative["summary_lines"])
    finally:
        os.environ.pop("PROJECT_PACK_FACTORY_FIXED_NOW", None)


def test_record_autonomy_run_carries_operator_intervention_learning_into_feedback_memory(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    pack_root = factory_root / "build-packs" / SOURCE_PACK_ID
    os.environ["PROJECT_PACK_FACTORY_FIXED_NOW"] = "2026-03-23T03:00:00Z"
    try:
        start_payload = start_run(
            pack_root=pack_root,
            run_id="loop-run-operator-001",
            notes=[],
            factory_root=factory_root,
        )
        run_root = Path(start_payload["run_root"])
        branch_selection_path = run_root / "branch-selection.json"
        branch_selection_path.write_text(
            """{
  "schema_version": "branch-selection-summary/v1",
  "run_id": "loop-run-operator-001",
  "recorded_at": "2026-03-23T03:00:00Z",
  "status": "selected",
  "selection_method": "operator_hint",
  "selection_rule": "operator hints before semantic alignment",
  "candidate_task_ids": ["run_build_pack_validation", "run_inherited_benchmarks"],
  "top_candidate_task_ids": ["run_build_pack_validation", "run_inherited_benchmarks"],
  "chosen_task_id": "run_build_pack_validation",
  "applied_hint_ids": ["prefer_validation_first"],
  "applied_hint_summary": "Prefer the validation branch before benchmark work on this run.",
  "semantic_context_sources": ["work_state_branch_selection_hints"],
  "semantic_scores": [],
  "ambiguity_reason": null
}
""",
            encoding="utf-8",
        )

        finalize_payload = finalize_run(
            pack_root=pack_root,
            run_id="loop-run-operator-001",
            schema_factory_root=factory_root,
            validation_factory_root=None,
        )

        feedback_path = Path(finalize_payload["artifacts"]["feedback_memory_path"])
        feedback = load_json(feedback_path)
        assert feedback["autonomy_budget"]["status"] == "within_budget"
        assert feedback["memory_tier"]["tier"] == "restart_memory"
        validity = feedback["memory_validity"]
        assert validity["confidence_level"] == "low"
        assert validity["scope"] == "active_pack_restart"
        assert validity["expires_after_hours"] == 12
        assert "canonical_state_integrity_not_passed" in validity["basis"]
        operator_intervention_summary = feedback["operator_intervention_summary"]
        assert operator_intervention_summary["selection_method"] == "operator_hint"
        assert operator_intervention_summary["applied_hint_ids"] == ["prefer_validation_first"]
        assert operator_intervention_summary["chosen_task_id"] == "run_build_pack_validation"
        assert operator_intervention_summary["branch_selection_path"].endswith("branch-selection.json")
        assert "Operator intervention observed" in operator_intervention_summary["learning_summary"]
        assert operator_intervention_summary["branch_selection_path"] in feedback["evidence_paths"]
        assert feedback["source_artifacts"]["branch_selection_path"] == operator_intervention_summary["branch_selection_path"]
        assert feedback["resolved_block_summary"] is None
        assert feedback["delta_summary"] is None
        negative = feedback["negative_memory_summary"]
        assert negative["status"] == "observed"
        assert "avoid_trusting_runs_without_canonical_integrity" in negative["avoidance_ids"]
        assert any("Avoid trusting autonomy memory" in line for line in negative["summary_lines"])
        assert any(
            "Operator intervention observed" in line
            for line in feedback["handoff_summary"]
        )
    finally:
        os.environ.pop("PROJECT_PACK_FACTORY_FIXED_NOW", None)


def test_record_autonomy_run_carries_block_resolution_learning_into_feedback_memory(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    pack_root = factory_root / "build-packs" / READY_PACK_ID
    agent_memory_root = pack_root / ".pack-state" / "agent-memory"
    agent_memory_root.mkdir(parents=True, exist_ok=True)
    previous_memory_path = agent_memory_root / "autonomy-feedback-prior-block-001.json"
    previous_memory_path.write_text(
        """{
  "schema_version": "autonomy-feedback-memory/v1",
  "memory_id": "autonomy-feedback-prior-block-001",
  "pack_id": "json-health-checker-feedback-baseline-build-pack-v1",
  "run_id": "prior-block-001",
  "generated_at": "2026-03-23T02:55:00Z",
  "memory_tier": {
    "status": "active",
    "tier": "restart_memory",
    "summary": "Synthetic prior restart memory."
  },
  "summary": "Prior run blocked at the validation boundary.",
  "autonomy_budget": {
    "status": "within_budget",
    "limits": {
      "max_step_count": 6,
      "max_failed_command_count": 0,
      "max_escalation_count": 1,
      "max_elapsed_minutes": 30
    },
    "observed": {
      "max_step_count": 2,
      "max_failed_command_count": 0,
      "max_escalation_count": 0,
      "max_elapsed_minutes": 1
    },
    "summary": "Synthetic prior budget summary."
  },
  "handoff_summary": ["Prior run blocked at the validation boundary."],
  "highest_risk_observation": "Validation evidence had not yet been refreshed.",
  "recommended_next_action": "Run the bounded validation surface before resuming autonomy.",
  "block_summary": {
    "status": "blocked",
    "reason": "starter_backlog_incomplete",
    "summary": "Autonomy stopped fail-closed because the starter backlog did not reach a promotion-ready boundary.",
    "blocking_artifact_kind": "readiness",
    "blocking_artifact_path": "status/readiness.json",
    "recommended_recovery_action": "Run the bounded validation surface before resuming autonomy.",
    "details": []
  },
  "resolved_block_summary": null,
  "delta_summary": null,
  "negative_memory_summary": null,
  "baseline_readiness_state": "in_progress",
  "final_readiness_state": "in_progress",
  "active_task_id": "run_build_pack_validation",
  "next_recommended_task_id": "run_build_pack_validation",
  "ready_for_deployment": false,
  "completed_task_ids": [],
  "operator_intervention_summary": null,
  "evidence_paths": [
    ".pack-state/autonomy-runs/prior-block-001/loop-events.jsonl",
    ".pack-state/autonomy-runs/prior-block-001/run-summary.json"
  ],
  "source_artifacts": {
    "loop_events_path": ".pack-state/autonomy-runs/prior-block-001/loop-events.jsonl",
    "run_summary_path": ".pack-state/autonomy-runs/prior-block-001/run-summary.json",
    "branch_selection_path": null,
    "previous_memory_path": null,
    "factory_validation_command": null
  }
}
""",
        encoding="utf-8",
    )
    (agent_memory_root / "latest-memory.json").write_text(
        """{
  "schema_version": "autonomy-feedback-memory-pointer/v1",
  "updated_at": "2026-03-23T02:56:00Z",
  "pack_id": "json-health-checker-feedback-baseline-build-pack-v1",
  "selected_memory_id": "autonomy-feedback-prior-block-001",
  "selected_run_id": "prior-block-001",
  "selected_generated_at": "2026-03-23T02:55:00Z",
  "selected_memory_path": ".pack-state/agent-memory/autonomy-feedback-prior-block-001.json",
  "selected_memory_tier": "restart_memory",
  "selected_memory_sha256": "placeholder",
  "source_kind": "local_autonomy_run",
  "source_import_id": null,
  "source_artifact_path": ".pack-state/agent-memory/autonomy-feedback-prior-block-001.json",
  "source_import_report_path": null
}
""",
        encoding="utf-8",
    )

    os.environ["PROJECT_PACK_FACTORY_FIXED_NOW"] = "2026-03-23T03:05:00Z"
    try:
        start_payload = start_run(
            pack_root=pack_root,
            run_id="loop-run-resolution-001",
            notes=[],
            factory_root=factory_root,
        )
        run_root = Path(start_payload["run_root"])
        assert run_root.exists()

        finalize_payload = finalize_run(
            pack_root=pack_root,
            run_id="loop-run-resolution-001",
            schema_factory_root=factory_root,
            validation_factory_root=None,
        )

        feedback_path = Path(finalize_payload["artifacts"]["feedback_memory_path"])
        feedback = load_json(feedback_path)
        assert feedback["autonomy_budget"]["status"] == "within_budget"
        assert feedback["memory_tier"]["tier"] == "restart_memory"
        validity = feedback["memory_validity"]
        assert validity["confidence_level"] == "low"
        assert validity["scope"] == "ready_boundary_restart"
        assert validity["expires_after_hours"] == 12
        assert "resolved_prior_block:starter_backlog_incomplete" in validity["basis"]
        resolved = feedback["resolved_block_summary"]
        assert resolved["status"] == "resolved"
        assert resolved["prior_block_reason"] == "starter_backlog_incomplete"
        assert resolved["prior_blocking_artifact_kind"] == "readiness"
        assert resolved["prior_memory_path"] == ".pack-state/agent-memory/autonomy-feedback-prior-block-001.json"
        assert "Resolved prior block" in resolved["recovery_summary"]
        delta = feedback["delta_summary"]
        assert delta["status"] == "changed"
        assert delta["previous_memory_path"] == ".pack-state/agent-memory/autonomy-feedback-prior-block-001.json"
        assert delta["previous_run_id"] == "prior-block-001"
        assert "final_readiness_state" in delta["changed_fields"]
        assert "ready_for_deployment" in delta["changed_fields"]
        assert any("Readiness changed" in line for line in delta["summary_lines"])
        assert any("Deployability changed" in line for line in delta["summary_lines"])
        negative = feedback["negative_memory_summary"]
        assert negative["status"] == "observed"
        assert "avoid_trusting_runs_without_canonical_integrity" in negative["avoidance_ids"]
        assert "avoid_repeating_blocked_path:starter_backlog_incomplete" not in negative["avoidance_ids"]
        assert feedback["source_artifacts"]["previous_memory_path"] == ".pack-state/agent-memory/autonomy-feedback-prior-block-001.json"
        assert ".pack-state/agent-memory/autonomy-feedback-prior-block-001.json" in feedback["evidence_paths"]
        assert any(
            "Resolved prior block" in line
            for line in feedback["handoff_summary"]
        )
        assert any(
            "Readiness changed" in line
            for line in feedback["handoff_summary"]
        )
        assert any(
            "Avoid trusting autonomy memory" in line
            for line in feedback["handoff_summary"]
        )
    finally:
        os.environ.pop("PROJECT_PACK_FACTORY_FIXED_NOW", None)


def test_record_autonomy_run_marks_budget_exceeded_when_step_budget_is_surpassed(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    pack_root = factory_root / "build-packs" / SOURCE_PACK_ID
    os.environ["PROJECT_PACK_FACTORY_FIXED_NOW"] = "2026-03-23T03:00:00Z"
    try:
        start_run(
            pack_root=pack_root,
            run_id="loop-run-budget-001",
            notes=[],
            factory_root=factory_root,
        )
        for index in range(6):
            append_event(
                pack_root=pack_root,
                run_id="loop-run-budget-001",
                event_type="task_selected",
                outcome="selected",
                decision_source="canonical_only",
                memory_state="not_used",
                commands_attempted=[],
                notes=[f"Budget exercise step {index + 1}."],
                evidence_paths=[],
                stop_reason=None,
                active_task_id="run_build_pack_validation",
                next_recommended_task_id="run_build_pack_validation",
                factory_root=factory_root,
            )
        finalize_payload = finalize_run(
            pack_root=pack_root,
            run_id="loop-run-budget-001",
            schema_factory_root=factory_root,
            validation_factory_root=None,
        )
        summary_path = Path(finalize_payload["artifacts"]["run_summary_path"])
        feedback_path = Path(finalize_payload["artifacts"]["feedback_memory_path"])
        summary = load_json(summary_path)
        feedback = load_json(feedback_path)
        assert summary["step_count"] == 7
        assert summary["autonomy_budget"]["status"] == "budget_exceeded"
        assert summary["autonomy_budget"]["observed"]["max_step_count"] == 7
        assert "max_step_count=7>6" in summary["autonomy_budget"]["summary"]
        assert feedback["autonomy_budget"]["status"] == "budget_exceeded"
        assert feedback["autonomy_budget"]["observed"]["max_step_count"] == 7
    finally:
        os.environ.pop("PROJECT_PACK_FACTORY_FIXED_NOW", None)
