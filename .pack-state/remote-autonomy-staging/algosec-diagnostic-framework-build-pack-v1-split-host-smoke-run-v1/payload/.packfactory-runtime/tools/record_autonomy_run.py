#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    dump_json,
    isoformat_z,
    load_json,
    load_pack_manifest,
    read_now,
    resolve_pack_root,
    timestamp_token,
    validate_named_payload,
    write_json,
)

LOOP_EVENT_SCHEMA_NAME: Final[str] = "autonomy-loop-event.schema.json"
RUN_SUMMARY_SCHEMA_NAME: Final[str] = "autonomy-run-summary.schema.json"
FEEDBACK_MEMORY_SCHEMA_NAME: Final[str] = "autonomy-feedback-memory.schema.json"
EVENTS_FILENAME: Final[str] = "loop-events.jsonl"
SUMMARY_FILENAME: Final[str] = "run-summary.json"
AUTONOMY_RUNS_DIR: Final[Path] = Path(".pack-state") / "autonomy-runs"
AGENT_MEMORY_DIR: Final[Path] = Path(".pack-state") / "agent-memory"
READINESS_PATH: Final[Path] = Path("status/readiness.json")
WORK_STATE_PATH: Final[Path] = Path("status/work-state.json")
TASK_BACKLOG_PATH: Final[Path] = Path("tasks/active-backlog.json")
EVAL_INDEX_PATH: Final[Path] = Path("eval/latest/index.json")

DECISION_SOURCES: Final[tuple[str, ...]] = (
    "canonical_only",
    "canonical_plus_memory",
    "memory_only",
)
MEMORY_STATES: Final[tuple[str, ...]] = (
    "not_used",
    "used_and_consistent",
    "used_and_stale",
    "used_and_incomplete",
)
EVENT_TYPES: Final[tuple[str, ...]] = (
    "run_started",
    "task_selected",
    "command_completed",
    "state_updated",
    "escalation_raised",
    "run_stopped",
    "run_completed",
)
READINESS_ORDER: Final[dict[str, int]] = {
    "blocked": 0,
    "in_progress": 1,
    "ready_for_review": 2,
    "ready_for_deploy": 3,
    "deployed": 4,
    "retired": 5,
}
TERMINAL_EVAL_STATUSES: Final[frozenset[str]] = frozenset({"pass", "fail", "waived"})
TERMINAL_GATE_STATUSES: Final[frozenset[str]] = frozenset({"pass", "fail", "waived"})
DEFAULT_AUTONOMY_BUDGET_LIMITS: Final[dict[str, int]] = {
    "max_step_count": 6,
    "max_failed_command_count": 0,
    "max_escalation_count": 1,
    "max_elapsed_minutes": 30,
}


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _run_root(pack_root: Path, run_id: str) -> Path:
    return pack_root / AUTONOMY_RUNS_DIR / run_id


def _events_path(pack_root: Path, run_id: str) -> Path:
    return _run_root(pack_root, run_id) / EVENTS_FILENAME


def _summary_path(pack_root: Path, run_id: str) -> Path:
    return _run_root(pack_root, run_id) / SUMMARY_FILENAME


def _feedback_memory_path(pack_root: Path, run_id: str) -> Path:
    return pack_root / AGENT_MEMORY_DIR / f"autonomy-feedback-{run_id}.json"


def _parse_datetime_utc(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _elapsed_minutes(started_at: str, ended_at: str) -> int:
    start_dt = _parse_datetime_utc(started_at)
    end_dt = _parse_datetime_utc(ended_at)
    if start_dt is None or end_dt is None:
        return 0
    elapsed_seconds = max(0.0, (end_dt - start_dt).total_seconds())
    return int((elapsed_seconds + 59) // 60)


def _write_jsonl_line(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"{path}:{line_number}: JSONL event must be an object")
        events.append(cast(dict[str, Any], payload))
    return events


def _validate_payload(pack_root: Path, manifest: dict[str, Any], schema_name: str, payload: dict[str, Any]) -> None:
    validate_named_payload(pack_root, manifest, schema_name, payload)


def _canonical_snapshot(pack_root: Path) -> tuple[str, dict[str, Any]]:
    manifest = load_pack_manifest(pack_root)
    readiness = _load_object(pack_root / READINESS_PATH)
    work_state = _load_object(pack_root / WORK_STATE_PATH)
    eval_latest = _load_object(pack_root / EVAL_INDEX_PATH)
    pack_id = str(manifest["pack_id"])
    gate_statuses = {
        str(gate["gate_id"]): str(gate["status"])
        for gate in cast(list[dict[str, Any]], readiness.get("required_gates", []))
        if isinstance(gate, dict) and "gate_id" in gate and "status" in gate
    }
    eval_result_statuses = {
        str(result["benchmark_id"]): str(result["status"])
        for result in cast(list[dict[str, Any]], eval_latest.get("benchmark_results", []))
        if isinstance(result, dict) and "benchmark_id" in result and "status" in result
    }
    snapshot = {
        "active_task_id": work_state.get("active_task_id"),
        "next_recommended_task_id": work_state.get("next_recommended_task_id"),
        "readiness_state": str(readiness["readiness_state"]),
        "ready_for_deployment": bool(readiness["ready_for_deployment"]),
        "gate_statuses": gate_statuses,
        "eval_result_statuses": eval_result_statuses,
    }
    return pack_id, snapshot


def _task_backlog(pack_root: Path) -> dict[str, Any]:
    return _load_object(pack_root / TASK_BACKLOG_PATH)


def _dedupe_strings(values: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _normalize_run_id(run_id: str | None, pack_id: str) -> str:
    if run_id is not None and run_id.strip():
        return run_id.strip()
    return f"autonomy-run-{pack_id}-{timestamp_token()}"


def _previous_snapshot(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in reversed(events):
        snapshot = event.get("canonical_snapshot_after")
        if isinstance(snapshot, dict):
            return cast(dict[str, Any], snapshot)
    return None


def _next_step_index(events: list[dict[str, Any]]) -> int:
    if not events:
        return 1
    return max(int(event["step_index"]) for event in events) + 1


def _build_event(
    *,
    run_id: str,
    step_index: int,
    event_type: str,
    recorded_at: str,
    active_task_id: str | None,
    next_recommended_task_id: str | None,
    decision_source: str,
    memory_state: str,
    commands_attempted: list[str],
    outcome: str,
    readiness_state_before: str,
    readiness_state_after: str,
    notes: list[str],
    stop_reason: str | None,
    evidence_paths: list[str],
    baseline_snapshot: dict[str, Any] | None,
    canonical_snapshot_after: dict[str, Any],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "autonomy-loop-event/v1",
        "run_id": run_id,
        "recorded_at": recorded_at,
        "step_index": step_index,
        "event_type": event_type,
        "active_task_id": active_task_id,
        "next_recommended_task_id": next_recommended_task_id,
        "decision_source": decision_source,
        "memory_state": memory_state,
        "commands_attempted": commands_attempted,
        "outcome": outcome,
        "readiness_state_before": readiness_state_before,
        "readiness_state_after": readiness_state_after,
        "notes": notes,
    }
    if stop_reason is not None:
        payload["stop_reason"] = stop_reason
    if evidence_paths:
        payload["evidence_paths"] = evidence_paths
    if baseline_snapshot is not None:
        payload["baseline_snapshot"] = baseline_snapshot
    payload["canonical_snapshot_after"] = canonical_snapshot_after
    return payload


def _event_uses_memory(event: dict[str, Any]) -> bool:
    return event.get("decision_source") != "canonical_only" or event.get("memory_state") != "not_used"


def _outcome_is_failure(outcome: str) -> bool:
    return outcome.strip().lower() in {"fail", "failed", "error", "validation_failed"}


def _terminal_stop_reason(events: list[dict[str, Any]]) -> str:
    if not events:
        return "no_events_recorded"
    terminal = events[-1]
    stop_reason = terminal.get("stop_reason")
    if isinstance(stop_reason, str) and stop_reason.strip():
        return stop_reason.strip()
    event_type = str(terminal.get("event_type", "run_stopped"))
    if event_type == "run_completed":
        return "run_completed"
    if event_type == "escalation_raised":
        return "escalation_raised"
    return event_type


def _iterations_to_first_change(
    events: list[dict[str, Any]],
    baseline_snapshot: dict[str, Any],
    *,
    change_kind: str,
) -> int | None:
    for event in events:
        snapshot = event.get("canonical_snapshot_after")
        if not isinstance(snapshot, dict):
            continue
        if change_kind == "evidence":
            if snapshot.get("gate_statuses") != baseline_snapshot.get("gate_statuses"):
                return int(event["step_index"])
            if snapshot.get("eval_result_statuses") != baseline_snapshot.get("eval_result_statuses"):
                return int(event["step_index"])
        elif change_kind == "readiness":
            if snapshot.get("readiness_state") != baseline_snapshot.get("readiness_state"):
                return int(event["step_index"])
            if snapshot.get("ready_for_deployment") != baseline_snapshot.get("ready_for_deployment"):
                return int(event["step_index"])
    return None


def _state_advanced(before: str, after: str) -> bool:
    return READINESS_ORDER.get(after, -1) > READINESS_ORDER.get(before, -1)


def _validation_evidence_gain(baseline: dict[str, Any], final: dict[str, Any]) -> bool:
    baseline_status = cast(dict[str, Any], baseline["gate_statuses"]).get("validate_build_pack_contract")
    final_status = cast(dict[str, Any], final["gate_statuses"]).get("validate_build_pack_contract")
    return baseline_status == "not_run" and final_status in TERMINAL_GATE_STATUSES


def _benchmark_evidence_gain(baseline: dict[str, Any], final: dict[str, Any]) -> bool:
    baseline_eval = cast(dict[str, str], baseline["eval_result_statuses"])
    final_eval = cast(dict[str, str], final["eval_result_statuses"])
    for benchmark_id, final_status in final_eval.items():
        if baseline_eval.get(benchmark_id) == "not_run" and final_status in TERMINAL_EVAL_STATUSES:
            return True
    return False


def _canonical_state_integrity() -> tuple[dict[str, Any], None]:
    return {
        "status": "not_run",
        "command": None,
        "valid": None,
        "error_count": None,
    }, None


def _operator_summary(metrics: dict[str, Any], artifacts: dict[str, Any]) -> str:
    return (
        "Metrics `task_completion_rate`, `readiness_change_summary`, "
        "`validation_evidence_gain`, and `benchmark_evidence_gain` were computed from "
        f"{artifacts['loop_events_path']}, status/readiness.json, eval/latest/index.json, "
        "and tasks/active-backlog.json."
    )


def _highest_risk_observation(
    *,
    metrics: dict[str, Any],
    final_snapshot: dict[str, Any],
) -> str:
    integrity = cast(dict[str, Any], metrics["canonical_state_integrity"])
    if integrity["status"] != "pass":
        return "Highest risk: `canonical_state_integrity` did not run locally; confirm canonical state before trusting the run summary."
    if not metrics["validation_evidence_gain"] and not metrics["benchmark_evidence_gain"]:
        return "Highest risk: the run did not convert missing validation or benchmark evidence into recorded evidence."
    if not _state_advanced("in_progress", cast(str, final_snapshot["readiness_state"])) and not final_snapshot["ready_for_deployment"]:
        return "Highest risk: readiness did not materially advance, so the loop may have spent iterations without improving deployability."
    return "Highest risk: benchmark and validation gains should still be reviewed against the final canonical readiness state."


def _recommended_next_action(
    *,
    final_snapshot: dict[str, Any],
    stop_reason: str,
    metrics: dict[str, Any],
) -> str:
    next_task_id = final_snapshot.get("next_recommended_task_id")
    if final_snapshot.get("ready_for_deployment") is True:
        return "Recommended next action: use the existing bounded promotion workflow if you want to move this build-pack toward deployment."
    if isinstance(next_task_id, str) and next_task_id:
        return (
            f"Recommended next action: continue with canonical next task `{next_task_id}` from status/work-state.json "
            "and use this summary as local measurement evidence only."
        )
    if cast(dict[str, Any], metrics["canonical_state_integrity"])["status"] == "fail":
        return "Recommended next action: resolve canonical state integrity questions before continuing autonomous work."
    return f"Recommended next action: review stop reason `{stop_reason}` with the current work-state and backlog before continuing."


def _blocked_reason(stop_reason: str, final_snapshot: dict[str, Any], metrics: dict[str, Any]) -> bool:
    if final_snapshot.get("ready_for_deployment") is True:
        return False
    if isinstance(final_snapshot.get("next_recommended_task_id"), str) and final_snapshot.get("next_recommended_task_id"):
        return False
    if stop_reason in {"run_completed", "mid_backlog_checkpoint_created"}:
        return False
    return (
        stop_reason in {
            "declared_escalation_boundary",
            "unauthorized_writable_surface",
            "runtime_evidence_export_failed",
            "runner_exited_nonzero_with_incomplete_pack_state",
            "starter_tasks_completed_without_ready_boundary",
            "starter_backlog_incomplete",
        }
        or cast(dict[str, Any], metrics["canonical_state_integrity"])["status"] == "fail"
        or final_snapshot.get("readiness_state") == "blocked"
    )


def _block_summary(
    *,
    stop_reason: str,
    final_snapshot: dict[str, Any],
    metrics: dict[str, Any],
    recommended_next_action: str,
    artifacts: dict[str, Any],
) -> dict[str, Any] | None:
    if not _blocked_reason(stop_reason, final_snapshot, metrics):
        return None

    if cast(dict[str, Any], metrics["canonical_state_integrity"])["status"] == "fail":
        return {
            "status": "blocked",
            "reason": "canonical_state_integrity_failed",
            "summary": "Autonomy stopped fail-closed because canonical state integrity did not pass.",
            "blocking_artifact_kind": "factory_validation",
            "blocking_artifact_path": cast(str, artifacts["run_summary_path"]),
            "recommended_recovery_action": "Run the recorded local validation command and resolve those integrity questions before trusting or continuing the autonomy loop.",
            "details": [cast(str, artifacts["factory_validation_command"])] if artifacts.get("factory_validation_command") else [],
        }
    if stop_reason == "declared_escalation_boundary" or final_snapshot.get("readiness_state") == "blocked":
        return {
            "status": "blocked",
            "reason": stop_reason,
            "summary": "Autonomy stopped fail-closed because the pack declared a blocked or escalation boundary in canonical state.",
            "blocking_artifact_kind": "work_state",
            "blocking_artifact_path": "status/work-state.json",
            "recommended_recovery_action": recommended_next_action,
            "details": ["Inspect status/work-state.json and status/readiness.json together before resuming autonomous work."],
        }
    if stop_reason in {"starter_backlog_incomplete", "starter_tasks_completed_without_ready_boundary"}:
        return {
            "status": "blocked",
            "reason": stop_reason,
            "summary": "Autonomy stopped fail-closed because the starter backlog did not reach a promotion-ready boundary.",
            "blocking_artifact_kind": "readiness",
            "blocking_artifact_path": "status/readiness.json",
            "recommended_recovery_action": recommended_next_action,
            "details": ["Review status/readiness.json and tasks/active-backlog.json to identify the next bounded readiness step."],
        }
    if stop_reason == "runtime_evidence_export_failed":
        return {
            "status": "blocked",
            "reason": stop_reason,
            "summary": "Autonomy stopped fail-closed because runtime evidence export failed after execution.",
            "blocking_artifact_kind": "runtime_evidence_export",
            "blocking_artifact_path": cast(str, artifacts["loop_events_path"]),
            "recommended_recovery_action": "Review the final loop event and the pack export command before re-running the autonomy loop.",
            "details": [],
        }
    if stop_reason in {"unauthorized_writable_surface", "runner_exited_nonzero_with_incomplete_pack_state"}:
        return {
            "status": "blocked",
            "reason": stop_reason,
            "summary": "Autonomy stopped fail-closed because remote execution ended outside the allowed completion boundary.",
            "blocking_artifact_kind": "remote_execution",
            "blocking_artifact_path": cast(str, artifacts["loop_events_path"]),
            "recommended_recovery_action": "Review the final loop events and remote execution manifest, then rerun only after the writable-surface or runner failure is understood.",
            "details": [],
        }
    return {
        "status": "blocked",
        "reason": stop_reason,
        "summary": f"Autonomy stopped fail-closed with stop reason `{stop_reason}`.",
        "blocking_artifact_kind": "loop_events",
        "blocking_artifact_path": cast(str, artifacts["loop_events_path"]),
        "recommended_recovery_action": recommended_next_action,
        "details": [],
    }


def _feedback_handoff_summary(
    *,
    run_id: str,
    stop_reason: str,
    baseline_snapshot: dict[str, Any],
    final_snapshot: dict[str, Any],
    completed_task_ids: list[str],
    highest_risk_observation: str,
    recommended_next_action: str,
    operator_intervention_summary: dict[str, Any] | None,
    resolved_block_summary: dict[str, Any] | None,
    delta_summary: dict[str, Any] | None,
    negative_memory_summary: dict[str, Any] | None,
) -> list[str]:
    completed_summary = ", ".join(completed_task_ids) if completed_task_ids else "none"
    lines = [
        f"Run `{run_id}` ended with stop reason `{stop_reason}`.",
        (
            f"Readiness moved from `{baseline_snapshot['readiness_state']}` to "
            f"`{final_snapshot['readiness_state']}`; ready_for_deployment={final_snapshot['ready_for_deployment']}."
        ),
        f"Completed tasks: {completed_summary}.",
    ]
    if operator_intervention_summary is not None:
        lines.append(cast(str, operator_intervention_summary["learning_summary"]))
    if resolved_block_summary is not None:
        lines.append(cast(str, resolved_block_summary["recovery_summary"]))
    if delta_summary is not None:
        lines.extend(cast(list[str], delta_summary["summary_lines"]))
    if negative_memory_summary is not None:
        lines.extend(cast(list[str], negative_memory_summary["summary_lines"]))
    lines.extend([highest_risk_observation, recommended_next_action])
    return lines


def _operator_intervention_summary(pack_root: Path, run_id: str) -> tuple[dict[str, Any] | None, str | None]:
    branch_selection_path = _run_root(pack_root, run_id) / "branch-selection.json"
    if not branch_selection_path.exists():
        return None, None
    payload = _load_object(branch_selection_path)
    applied_hint_ids = payload.get("applied_hint_ids")
    if not isinstance(applied_hint_ids, list) or not applied_hint_ids:
        return None, branch_selection_path.relative_to(pack_root).as_posix()
    normalized_hint_ids = [hint_id for hint_id in applied_hint_ids if isinstance(hint_id, str) and hint_id]
    if not normalized_hint_ids:
        return None, branch_selection_path.relative_to(pack_root).as_posix()
    selection_method = str(payload.get("selection_method", "operator_hint"))
    chosen_task_id = payload.get("chosen_task_id")
    hint_summary = str(payload.get("applied_hint_summary", "")).strip() or "Operator guidance changed the branch-selection outcome."
    learning_summary = (
        f"Operator intervention observed: hints {', '.join(normalized_hint_ids)} influenced "
        f"selection method `{selection_method}` and chose `{chosen_task_id}`."
        if isinstance(chosen_task_id, str) and chosen_task_id
        else f"Operator intervention observed: hints {', '.join(normalized_hint_ids)} influenced selection method `{selection_method}`."
    )
    return {
        "status": "observed",
        "selection_method": selection_method,
        "applied_hint_ids": normalized_hint_ids,
        "applied_hint_summary": hint_summary,
        "chosen_task_id": chosen_task_id if isinstance(chosen_task_id, str) and chosen_task_id else None,
        "branch_selection_path": branch_selection_path.relative_to(pack_root).as_posix(),
        "learning_summary": learning_summary,
    }, branch_selection_path.relative_to(pack_root).as_posix()


def _load_previous_feedback_memory(pack_root: Path) -> tuple[dict[str, Any] | None, str | None]:
    pointer_path = pack_root / AGENT_MEMORY_DIR / "latest-memory.json"
    if not pointer_path.exists():
        return None, None
    pointer_payload = _load_object(pointer_path)
    selected_memory_path = pointer_payload.get("selected_memory_path")
    if not isinstance(selected_memory_path, str) or not selected_memory_path:
        return None, None
    previous_memory_path = (pack_root / selected_memory_path).resolve()
    if not previous_memory_path.exists():
        return None, selected_memory_path
    return _load_object(previous_memory_path), selected_memory_path


def _resolved_block_summary(
    *,
    pack_root: Path,
    baseline_snapshot: dict[str, Any],
    final_snapshot: dict[str, Any],
    completed_task_ids: list[str],
    block_summary: dict[str, Any] | None,
    artifacts: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    if block_summary is not None:
        return None, None

    previous_memory, selected_memory_path = _load_previous_feedback_memory(pack_root)
    if previous_memory is None or selected_memory_path is None:
        return None, selected_memory_path
    previous_block_summary = previous_memory.get("block_summary")
    if not isinstance(previous_block_summary, dict) or previous_block_summary.get("status") != "blocked":
        return None, selected_memory_path

    completed_summary = ", ".join(completed_task_ids) if completed_task_ids else "none"
    recovery_summary = (
        f"Resolved prior block `{previous_block_summary['reason']}` from `{selected_memory_path}`: "
        f"readiness moved from `{baseline_snapshot['readiness_state']}` to "
        f"`{final_snapshot['readiness_state']}` and completed tasks were {completed_summary}."
    )
    recovery_evidence_paths = [
        cast(str, artifacts["loop_events_path"]),
        cast(str, artifacts["run_summary_path"]),
    ]
    if artifacts.get("branch_selection_path"):
        recovery_evidence_paths.append(cast(str, artifacts["branch_selection_path"]))
    return {
        "status": "resolved",
        "prior_block_reason": previous_block_summary["reason"],
        "prior_blocking_artifact_kind": previous_block_summary["blocking_artifact_kind"],
        "prior_blocking_artifact_path": previous_block_summary["blocking_artifact_path"],
        "prior_recommended_recovery_action": previous_block_summary["recommended_recovery_action"],
        "prior_memory_path": selected_memory_path,
        "recovery_summary": recovery_summary,
        "recovery_evidence_paths": recovery_evidence_paths,
    }, selected_memory_path


def _canonical_state_delta_summary(
    *,
    pack_root: Path,
    final_snapshot: dict[str, Any],
    completed_task_ids: list[str],
) -> tuple[dict[str, Any] | None, str | None]:
    previous_memory, selected_memory_path = _load_previous_feedback_memory(pack_root)
    if previous_memory is None or selected_memory_path is None:
        return None, selected_memory_path

    changed_fields: list[str] = []
    summary_lines: list[str] = []
    previous_readiness = previous_memory.get("final_readiness_state")
    previous_ready = previous_memory.get("ready_for_deployment")
    previous_active = previous_memory.get("active_task_id")
    previous_next = previous_memory.get("next_recommended_task_id")
    if previous_readiness != final_snapshot.get("readiness_state"):
        changed_fields.append("final_readiness_state")
        summary_lines.append(
            f"Readiness changed from `{previous_readiness}` to `{final_snapshot.get('readiness_state')}`."
        )
    if previous_ready != final_snapshot.get("ready_for_deployment"):
        changed_fields.append("ready_for_deployment")
        summary_lines.append(
            f"Deployability changed from `{previous_ready}` to `{final_snapshot.get('ready_for_deployment')}`."
        )
    if previous_active != final_snapshot.get("active_task_id"):
        changed_fields.append("active_task_id")
        summary_lines.append(
            f"Active task changed from `{previous_active}` to `{final_snapshot.get('active_task_id')}`."
        )
    if previous_next != final_snapshot.get("next_recommended_task_id"):
        changed_fields.append("next_recommended_task_id")
        summary_lines.append(
            f"Next recommended task changed from `{previous_next}` to `{final_snapshot.get('next_recommended_task_id')}`."
        )

    previous_completed = previous_memory.get("completed_task_ids")
    previous_completed_iterable = previous_completed if isinstance(previous_completed, list) else []
    previous_completed_set = {
        task_id
        for task_id in previous_completed_iterable
        if isinstance(task_id, str) and task_id
    }
    completed_task_ids_added = [task_id for task_id in completed_task_ids if task_id not in previous_completed_set]
    if completed_task_ids_added:
        changed_fields.append("completed_task_ids")
        summary_lines.append(f"Newly completed tasks: {', '.join(completed_task_ids_added)}.")

    if not summary_lines:
        summary_lines.append("Canonical state is unchanged from the previously active feedback memory.")

    return {
        "status": "changed" if changed_fields else "unchanged",
        "previous_memory_path": selected_memory_path,
        "previous_run_id": previous_memory.get("run_id") if isinstance(previous_memory.get("run_id"), str) else None,
        "changed_fields": changed_fields,
        "completed_task_ids_added": completed_task_ids_added,
        "summary_lines": summary_lines,
    }, selected_memory_path


def _negative_memory_summary(
    *,
    metrics: dict[str, Any],
    block_summary: dict[str, Any] | None,
) -> dict[str, Any] | None:
    avoidance_ids: list[str] = []
    summary_lines: list[str] = []
    canonical_integrity = cast(dict[str, Any], metrics.get("canonical_state_integrity", {})).get("status")
    if canonical_integrity != "pass":
        avoidance_ids.append("avoid_trusting_runs_without_canonical_integrity")
        summary_lines.append(
            "Avoid trusting autonomy memory from runs where canonical state integrity did not pass; rerun bounded validation first."
        )
    stale_memory_rate = metrics.get("stale_memory_rate")
    if isinstance(stale_memory_rate, (int, float)) and stale_memory_rate > 0:
        avoidance_ids.append("avoid_reusing_stale_memory_without_reconcile")
        summary_lines.append(
            "Avoid reusing stale memory without reconciling canonical state first."
        )
    if isinstance(block_summary, dict) and block_summary.get("status") == "blocked":
        avoidance_ids.append(f"avoid_repeating_blocked_path:{block_summary['reason']}")
        summary_lines.append(
            f"Avoid repeating the blocked path `{block_summary['reason']}` without first completing the recorded recovery action."
        )
    if not avoidance_ids:
        return None
    return {
        "status": "observed",
        "avoidance_ids": avoidance_ids,
        "summary_lines": summary_lines,
    }


def _autonomy_budget_summary(
    *,
    started_at: str,
    ended_at: str,
    step_count: int,
    failed_command_count: int,
    escalation_count: int,
) -> dict[str, Any]:
    observed = {
        "max_step_count": step_count,
        "max_failed_command_count": failed_command_count,
        "max_escalation_count": escalation_count,
        "max_elapsed_minutes": _elapsed_minutes(started_at, ended_at),
    }
    exceeded: list[str] = []
    for key, limit in DEFAULT_AUTONOMY_BUDGET_LIMITS.items():
        if observed[key] > limit:
            exceeded.append(f"{key}={observed[key]}>{limit}")
    status = "budget_exceeded" if exceeded else "within_budget"
    summary = (
        "Autonomy stayed within the default bounded run budget."
        if not exceeded
        else "Autonomy exceeded the default bounded run budget: " + ", ".join(exceeded) + "."
    )
    return {
        "status": status,
        "limits": dict(DEFAULT_AUTONOMY_BUDGET_LIMITS),
        "observed": observed,
        "summary": summary,
    }


def _build_feedback_memory(
    *,
    pack_id: str,
    run_id: str,
    ended_at: str,
    stop_reason: str,
    baseline_snapshot: dict[str, Any],
    final_snapshot: dict[str, Any],
    completed_task_ids: list[str],
    artifacts: dict[str, Any],
    metrics: dict[str, Any],
    operator_summary: str,
    highest_risk_observation: str,
    recommended_next_action: str,
    autonomy_budget: dict[str, Any],
    block_summary: dict[str, Any] | None,
    operator_intervention_summary: dict[str, Any] | None,
    resolved_block_summary: dict[str, Any] | None,
    delta_summary: dict[str, Any] | None,
    negative_memory_summary: dict[str, Any] | None,
    previous_memory_path: str | None,
) -> dict[str, Any]:
    memory_validity = _memory_validity(
        ended_at=ended_at,
        final_snapshot=final_snapshot,
        metrics=metrics,
        block_summary=block_summary,
        resolved_block_summary=resolved_block_summary,
    )
    return {
        "schema_version": "autonomy-feedback-memory/v1",
        "memory_id": f"autonomy-feedback-{run_id}",
        "pack_id": pack_id,
        "run_id": run_id,
        "generated_at": ended_at,
        "memory_tier": {
            "status": "active",
            "tier": "restart_memory",
            "summary": "Pack-local restart memory for the next bounded autonomy run.",
        },
        "summary": operator_summary,
        "memory_validity": memory_validity,
        "handoff_summary": _feedback_handoff_summary(
            run_id=run_id,
            stop_reason=stop_reason,
            baseline_snapshot=baseline_snapshot,
            final_snapshot=final_snapshot,
            completed_task_ids=completed_task_ids,
            highest_risk_observation=highest_risk_observation,
            recommended_next_action=recommended_next_action,
            operator_intervention_summary=operator_intervention_summary,
            resolved_block_summary=resolved_block_summary,
            delta_summary=delta_summary,
            negative_memory_summary=negative_memory_summary,
        ),
        "highest_risk_observation": highest_risk_observation,
        "recommended_next_action": recommended_next_action,
        "autonomy_budget": autonomy_budget,
        "block_summary": block_summary,
        "resolved_block_summary": resolved_block_summary,
        "delta_summary": delta_summary,
        "negative_memory_summary": negative_memory_summary,
        "baseline_readiness_state": cast(str, baseline_snapshot["readiness_state"]),
        "final_readiness_state": cast(str, final_snapshot["readiness_state"]),
        "active_task_id": final_snapshot.get("active_task_id"),
        "next_recommended_task_id": final_snapshot.get("next_recommended_task_id"),
        "ready_for_deployment": bool(final_snapshot["ready_for_deployment"]),
        "completed_task_ids": completed_task_ids,
        "operator_intervention_summary": operator_intervention_summary,
        "evidence_paths": [
            cast(str, artifacts["loop_events_path"]),
            cast(str, artifacts["run_summary_path"]),
            *(
                [cast(str, artifacts["branch_selection_path"])]
                if artifacts.get("branch_selection_path")
                else []
            ),
            *([previous_memory_path] if previous_memory_path else []),
        ],
        "source_artifacts": {
            "loop_events_path": artifacts["loop_events_path"],
            "run_summary_path": artifacts["run_summary_path"],
            "branch_selection_path": artifacts.get("branch_selection_path"),
            "previous_memory_path": previous_memory_path,
            "factory_validation_command": artifacts.get("factory_validation_command"),
        },
    }


def _memory_validity(
    *,
    ended_at: str,
    final_snapshot: dict[str, Any],
    metrics: dict[str, Any],
    block_summary: dict[str, Any] | None,
    resolved_block_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    confidence_score = 0.9
    basis: list[str] = []
    canonical_integrity = cast(dict[str, Any], metrics.get("canonical_state_integrity", {})).get("status")
    if canonical_integrity == "pass":
        basis.append("canonical_state_integrity_passed")
    else:
        confidence_score = min(confidence_score, 0.35)
        basis.append("canonical_state_integrity_not_passed")

    stale_memory_rate = metrics.get("stale_memory_rate")
    if isinstance(stale_memory_rate, (int, float)) and stale_memory_rate > 0:
        confidence_score = min(confidence_score, 0.55)
        basis.append("stale_memory_observed")

    if block_summary is not None:
        confidence_score = min(confidence_score, 0.6)
        basis.append(f"blocked:{block_summary['reason']}")

    if resolved_block_summary is not None:
        basis.append(f"resolved_prior_block:{resolved_block_summary['prior_block_reason']}")

    active_task_id = final_snapshot.get("active_task_id")
    next_recommended_task_id = final_snapshot.get("next_recommended_task_id")
    if block_summary is not None:
        scope = "blocked_restart"
        expires_after_hours = 24
    elif final_snapshot.get("ready_for_deployment") and active_task_id is None and next_recommended_task_id is None:
        scope = "ready_boundary_restart"
        expires_after_hours = 168
    elif active_task_id is not None or next_recommended_task_id is not None:
        scope = "active_pack_restart"
        expires_after_hours = 72
    else:
        scope = "pack_local_restart"
        expires_after_hours = 48

    if confidence_score < 0.5:
        expires_after_hours = min(expires_after_hours, 12)
    elif confidence_score < 0.8:
        expires_after_hours = min(expires_after_hours, 48)

    if confidence_score >= 0.8:
        confidence_level = "high"
    elif confidence_score >= 0.55:
        confidence_level = "medium"
    else:
        confidence_level = "low"

    ended_at_dt = _parse_datetime_utc(ended_at) or read_now()
    expires_at = isoformat_z(ended_at_dt + timedelta(hours=expires_after_hours))
    summary = (
        f"{confidence_level.title()}-confidence {scope.replace('_', ' ')} memory "
        f"with {expires_after_hours}h freshness window."
    )
    return {
        "status": "active",
        "confidence_level": confidence_level,
        "confidence_score": round(confidence_score, 4),
        "scope": scope,
        "expires_at": expires_at,
        "expires_after_hours": expires_after_hours,
        "basis": basis or ["bounded_default"],
        "summary": summary,
    }


def start_run(
    *,
    pack_root: Path,
    run_id: str | None,
    notes: list[str],
) -> dict[str, Any]:
    manifest = load_pack_manifest(pack_root)
    pack_id, baseline_snapshot = _canonical_snapshot(pack_root)
    resolved_run_id = _normalize_run_id(run_id, pack_id)
    run_root = _run_root(pack_root, resolved_run_id)
    if run_root.exists():
        raise ValueError(f"autonomy run already exists: {run_root}")
    recorded_at = isoformat_z()
    event = _build_event(
        run_id=resolved_run_id,
        step_index=1,
        event_type="run_started",
        recorded_at=recorded_at,
        active_task_id=cast(str | None, baseline_snapshot["active_task_id"]),
        next_recommended_task_id=cast(str | None, baseline_snapshot["next_recommended_task_id"]),
        decision_source="canonical_only",
        memory_state="not_used",
        commands_attempted=[],
        outcome="started",
        readiness_state_before=cast(str, baseline_snapshot["readiness_state"]),
        readiness_state_after=cast(str, baseline_snapshot["readiness_state"]),
        notes=notes or ["Captured baseline canonical pack state for autonomy-run measurement."],
        stop_reason=None,
        evidence_paths=[],
        baseline_snapshot=baseline_snapshot,
        canonical_snapshot_after=baseline_snapshot,
    )
    _validate_payload(pack_root, manifest, LOOP_EVENT_SCHEMA_NAME, event)
    _write_jsonl_line(_events_path(pack_root, resolved_run_id), event)
    return {
        "status": "started",
        "pack_id": pack_id,
        "run_id": resolved_run_id,
        "run_root": str(run_root),
        "loop_events_path": str(_events_path(pack_root, resolved_run_id)),
        "baseline_snapshot": baseline_snapshot,
    }


def append_event(
    *,
    pack_root: Path,
    run_id: str,
    event_type: str,
    outcome: str,
    decision_source: str,
    memory_state: str,
    commands_attempted: list[str],
    notes: list[str],
    evidence_paths: list[str],
    stop_reason: str | None,
    active_task_id: str | None,
    next_recommended_task_id: str | None,
) -> dict[str, Any]:
    manifest = load_pack_manifest(pack_root)
    events_path = _events_path(pack_root, run_id)
    events = _load_events(events_path)
    if not events:
        raise ValueError("cannot append an autonomy event before the run is started")
    _pack_id, current_snapshot = _canonical_snapshot(pack_root)
    previous_snapshot = _previous_snapshot(events) or current_snapshot
    event = _build_event(
        run_id=run_id,
        step_index=_next_step_index(events),
        event_type=event_type,
        recorded_at=isoformat_z(),
        active_task_id=active_task_id if active_task_id is not None else cast(str | None, current_snapshot["active_task_id"]),
        next_recommended_task_id=(
            next_recommended_task_id
            if next_recommended_task_id is not None
            else cast(str | None, current_snapshot["next_recommended_task_id"])
        ),
        decision_source=decision_source,
        memory_state=memory_state,
        commands_attempted=_dedupe_strings(commands_attempted),
        outcome=outcome,
        readiness_state_before=cast(str, previous_snapshot["readiness_state"]),
        readiness_state_after=cast(str, current_snapshot["readiness_state"]),
        notes=notes,
        stop_reason=stop_reason,
        evidence_paths=_dedupe_strings(evidence_paths),
        baseline_snapshot=None,
        canonical_snapshot_after=current_snapshot,
    )
    _validate_payload(pack_root, manifest, LOOP_EVENT_SCHEMA_NAME, event)
    _write_jsonl_line(events_path, event)
    return {
        "status": "appended",
        "run_id": run_id,
        "step_index": event["step_index"],
        "loop_events_path": str(events_path),
        "event_type": event_type,
        "readiness_state_after": current_snapshot["readiness_state"],
    }


def finalize_run(
    *,
    pack_root: Path,
    run_id: str,
) -> dict[str, Any]:
    manifest = load_pack_manifest(pack_root)
    events_path = _events_path(pack_root, run_id)
    events = _load_events(events_path)
    if not events:
        raise ValueError("cannot finalize an autonomy run with no events")
    first_event = events[0]
    baseline_snapshot = first_event.get("baseline_snapshot")
    if not isinstance(baseline_snapshot, dict):
        baseline_snapshot = first_event.get("canonical_snapshot_after")
    if not isinstance(baseline_snapshot, dict):
        raise ValueError("the first autonomy event must capture a baseline snapshot")

    pack_id, final_snapshot = _canonical_snapshot(pack_root)
    backlog = _task_backlog(pack_root)
    tasks = cast(list[dict[str, Any]], backlog.get("tasks", []))
    completed_task_ids = [
        str(task["task_id"])
        for task in tasks
        if isinstance(task, dict) and task.get("status") == "completed"
    ]
    task_completion_rate = len(completed_task_ids) / len(tasks) if tasks else 0.0
    resume_events = [event for event in events if event.get("event_type") == "task_selected"]
    resume_count = len(resume_events)
    correct_resume_count = 0
    prior_next = cast(str | None, baseline_snapshot.get("next_recommended_task_id"))
    for event in resume_events:
        if event.get("active_task_id") == prior_next:
            correct_resume_count += 1
        snapshot_after = event.get("canonical_snapshot_after")
        if isinstance(snapshot_after, dict):
            prior_next = cast(str | None, snapshot_after.get("next_recommended_task_id"))

    memory_use_events = [event for event in events if _event_uses_memory(event)]
    stale_memory_events = [event for event in memory_use_events if event.get("memory_state") == "used_and_stale"]
    consistent_memory_events = [
        event
        for event in memory_use_events
        if event.get("decision_source") == "canonical_plus_memory"
        and event.get("memory_state") == "used_and_consistent"
    ]
    integrity, validation_command = _canonical_state_integrity()
    metrics: dict[str, Any] = {
        "task_completion_rate": round(task_completion_rate, 4),
        "iterations_to_first_evidence": _iterations_to_first_change(
            events,
            cast(dict[str, Any], baseline_snapshot),
            change_kind="evidence",
        ),
        "iterations_to_readiness_change": _iterations_to_first_change(
            events,
            cast(dict[str, Any], baseline_snapshot),
            change_kind="readiness",
        ),
        "readiness_change_summary": {
            "state_advanced": _state_advanced(
                cast(str, baseline_snapshot["readiness_state"]),
                cast(str, final_snapshot["readiness_state"]),
            ),
            "deployability_changed": baseline_snapshot["ready_for_deployment"] != final_snapshot["ready_for_deployment"],
            "gates_advanced_count": sum(
                1
                for gate_id, final_status in cast(dict[str, str], final_snapshot["gate_statuses"]).items()
                if cast(dict[str, str], baseline_snapshot["gate_statuses"]).get(gate_id) != final_status
            ),
        },
        "validation_evidence_gain": _validation_evidence_gain(cast(dict[str, Any], baseline_snapshot), final_snapshot),
        "benchmark_evidence_gain": _benchmark_evidence_gain(cast(dict[str, Any], baseline_snapshot), final_snapshot),
        "canonical_state_integrity": integrity,
    }
    if memory_use_events:
        metrics["resume_correctness"] = round(correct_resume_count / resume_count, 4) if resume_count else None
        metrics["stale_memory_rate"] = round(len(stale_memory_events) / len(memory_use_events), 4)
        metrics["consistent_memory_use_rate"] = round(len(consistent_memory_events) / len(memory_use_events), 4)

    stop_reason = _terminal_stop_reason(events)
    started_at = str(first_event["recorded_at"])
    ended_at = isoformat_z()
    failed_command_count = sum(
        1
        for event in events
        if event.get("event_type") == "command_completed"
        and _outcome_is_failure(str(event.get("outcome", "")))
    )
    escalation_count = sum(1 for event in events if event.get("event_type") == "escalation_raised")
    operator_intervention_summary, branch_selection_relative_path = _operator_intervention_summary(pack_root, run_id)
    artifacts = {
        "loop_events_path": str(events_path),
        "run_summary_path": str(_summary_path(pack_root, run_id)),
        "feedback_memory_path": str(_feedback_memory_path(pack_root, run_id)),
        "branch_selection_path": branch_selection_relative_path,
        "factory_validation_command": validation_command,
    }
    operator_summary = _operator_summary(metrics, artifacts)
    highest_risk_observation = _highest_risk_observation(metrics=metrics, final_snapshot=final_snapshot)
    recommended_next_action = _recommended_next_action(
        final_snapshot=final_snapshot,
        stop_reason=stop_reason,
        metrics=metrics,
    )
    autonomy_budget = _autonomy_budget_summary(
        started_at=started_at,
        ended_at=ended_at,
        step_count=len(events),
        failed_command_count=failed_command_count,
        escalation_count=escalation_count,
    )
    block_summary = _block_summary(
        stop_reason=stop_reason,
        final_snapshot=final_snapshot,
        metrics=metrics,
        recommended_next_action=recommended_next_action,
        artifacts=artifacts,
    )
    resolved_block_summary, previous_memory_path = _resolved_block_summary(
        pack_root=pack_root,
        baseline_snapshot=cast(dict[str, Any], baseline_snapshot),
        final_snapshot=final_snapshot,
        completed_task_ids=completed_task_ids,
        block_summary=block_summary,
        artifacts=artifacts,
    )
    delta_summary, delta_previous_memory_path = _canonical_state_delta_summary(
        pack_root=pack_root,
        final_snapshot=final_snapshot,
        completed_task_ids=completed_task_ids,
    )
    if previous_memory_path is None:
        previous_memory_path = delta_previous_memory_path
    negative_memory_summary = _negative_memory_summary(
        metrics=metrics,
        block_summary=block_summary,
    )
    summary = {
        "schema_version": "autonomy-run-summary/v1",
        "run_id": run_id,
        "pack_id": pack_id,
        "started_at": started_at,
        "ended_at": ended_at,
        "baseline_snapshot": baseline_snapshot,
        "final_snapshot": final_snapshot,
        "step_count": len(events),
        "resume_count": resume_count,
        "completed_task_ids": completed_task_ids,
        "failed_command_count": failed_command_count,
        "escalation_count": escalation_count,
        "stop_reason": stop_reason,
        "metrics": metrics,
        "operator_summary": operator_summary,
        "highest_risk_observation": highest_risk_observation,
        "recommended_next_action": recommended_next_action,
        "autonomy_budget": autonomy_budget,
        "block_summary": block_summary,
        "artifacts": artifacts,
    }
    _validate_payload(pack_root, manifest, RUN_SUMMARY_SCHEMA_NAME, summary)
    write_json(_summary_path(pack_root, run_id), summary)
    feedback_memory = _build_feedback_memory(
        pack_id=pack_id,
        run_id=run_id,
        ended_at=cast(str, summary["ended_at"]),
        stop_reason=stop_reason,
        baseline_snapshot=cast(dict[str, Any], baseline_snapshot),
        final_snapshot=final_snapshot,
        completed_task_ids=completed_task_ids,
        artifacts=artifacts,
        metrics=metrics,
        operator_summary=operator_summary,
        highest_risk_observation=highest_risk_observation,
        recommended_next_action=recommended_next_action,
        autonomy_budget=autonomy_budget,
        block_summary=block_summary,
        operator_intervention_summary=operator_intervention_summary,
        resolved_block_summary=resolved_block_summary,
        delta_summary=delta_summary,
        negative_memory_summary=negative_memory_summary,
        previous_memory_path=previous_memory_path,
    )
    _validate_payload(pack_root, manifest, FEEDBACK_MEMORY_SCHEMA_NAME, feedback_memory)
    write_json(_feedback_memory_path(pack_root, run_id), feedback_memory)
    return summary


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record local autonomy-loop measurement artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Create a local autonomy run and capture the baseline event.")
    start_parser.add_argument("--pack-root", required=True)
    start_parser.add_argument("--run-id")
    start_parser.add_argument("--note", dest="notes", action="append", default=[])

    append_parser = subparsers.add_parser("append-event", help="Append one loop event to a local autonomy run.")
    append_parser.add_argument("--pack-root", required=True)
    append_parser.add_argument("--run-id", required=True)
    append_parser.add_argument("--event-type", required=True, choices=EVENT_TYPES)
    append_parser.add_argument("--outcome", required=True)
    append_parser.add_argument("--decision-source", choices=DECISION_SOURCES, default="canonical_only")
    append_parser.add_argument("--memory-state", choices=MEMORY_STATES, default="not_used")
    append_parser.add_argument("--command", dest="commands_attempted", action="append", default=[])
    append_parser.add_argument("--note", dest="notes", action="append", default=[])
    append_parser.add_argument("--evidence-path", dest="evidence_paths", action="append", default=[])
    append_parser.add_argument("--stop-reason")
    append_parser.add_argument("--active-task-id")
    append_parser.add_argument("--next-recommended-task-id")

    finalize_parser = subparsers.add_parser("finalize", help="Finalize a local autonomy run summary from canonical pack state.")
    finalize_parser.add_argument("--pack-root", required=True)
    finalize_parser.add_argument("--run-id", required=True)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    pack_root = resolve_pack_root(args.pack_root)
    if args.command == "start":
        payload = start_run(
            pack_root=pack_root,
            run_id=args.run_id,
            notes=list(args.notes),
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "append-event":
        payload = append_event(
            pack_root=pack_root,
            run_id=args.run_id,
            event_type=args.event_type,
            outcome=args.outcome,
            decision_source=args.decision_source,
            memory_state=args.memory_state,
            commands_attempted=list(args.commands_attempted),
            notes=list(args.notes),
            evidence_paths=list(args.evidence_paths),
            stop_reason=args.stop_reason,
            active_task_id=args.active_task_id,
            next_recommended_task_id=args.next_recommended_task_id,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    payload = finalize_run(
        pack_root=pack_root,
        run_id=args.run_id,
    )
    print(dump_json(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
