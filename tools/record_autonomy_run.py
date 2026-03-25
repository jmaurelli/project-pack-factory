#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Final, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    dump_json,
    isoformat_z,
    load_json,
    read_now,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
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
PACK_MANIFEST_PATH: Final[Path] = Path("pack.json")

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


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _resolve_pack_root(pack_root: str | Path) -> Path:
    root = Path(pack_root).expanduser().resolve()
    if not root.is_absolute():
        raise ValueError("pack_root must resolve to an absolute path")
    return root


def _discover_factory_root(pack_root: Path) -> Path | None:
    for candidate in (pack_root, *pack_root.parents):
        if (candidate / "registry").is_dir() and (candidate / "docs/specs/project-pack-factory/schemas").is_dir():
            return candidate
    return None


def _run_root(pack_root: Path, run_id: str) -> Path:
    return pack_root / AUTONOMY_RUNS_DIR / run_id


def _events_path(pack_root: Path, run_id: str) -> Path:
    return _run_root(pack_root, run_id) / EVENTS_FILENAME


def _summary_path(pack_root: Path, run_id: str) -> Path:
    return _run_root(pack_root, run_id) / SUMMARY_FILENAME


def _feedback_memory_path(pack_root: Path, run_id: str) -> Path:
    return pack_root / AGENT_MEMORY_DIR / f"autonomy-feedback-{run_id}.json"


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


def _validate_payload(factory_root: Path, schema_name: str, payload: dict[str, Any], *, label: str) -> None:
    temp_root = factory_root / ".pack-state" / "autonomy-run-schema-validation"
    temp_path = temp_root / f"{label}.json"
    write_json(temp_path, payload)
    errors = validate_json_document(temp_path, schema_path(factory_root, schema_name))
    temp_path.unlink(missing_ok=True)
    if temp_path.parent.exists() and not any(temp_path.parent.iterdir()):
        temp_path.parent.rmdir()
    if errors:
        raise ValueError("; ".join(errors))


def _canonical_snapshot(pack_root: Path) -> tuple[str, dict[str, Any]]:
    manifest = _load_object(pack_root / PACK_MANIFEST_PATH)
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
    return (
        event.get("decision_source") != "canonical_only"
        or event.get("memory_state") != "not_used"
    )


def _outcome_is_failure(outcome: str) -> bool:
    normalized = outcome.strip().lower()
    return normalized in {"fail", "failed", "error", "validation_failed"}


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


def _canonical_state_integrity(factory_root: Path | None) -> tuple[dict[str, Any], str | None]:
    if factory_root is None:
        return {
            "status": "not_run",
            "command": None,
            "valid": None,
            "error_count": None,
        }, None
    command = f"{sys.executable} {factory_root / 'tools/validate_factory.py'} --factory-root {factory_root} --output json"
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(factory_root / "tools/validate_factory.py"),
                "--factory-root",
                str(factory_root),
                "--output",
                "json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        payload = json.loads(completed.stdout)
        if not isinstance(payload, dict):
            raise ValueError("validate_factory output must be a JSON object")
        valid = payload.get("valid")
        error_count = payload.get("error_count")
        return {
            "status": "pass" if valid is True else "fail",
            "command": command,
            "valid": bool(valid) if isinstance(valid, bool) else False,
            "error_count": int(error_count) if isinstance(error_count, int) else 0,
        }, command
    except Exception:
        return {
            "status": "fail",
            "command": command,
            "valid": False,
            "error_count": 1,
        }, command


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
        return "Highest risk: `canonical_state_integrity` did not pass; review whole-factory validation before trusting the run summary."
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
    if cast(dict[str, Any], metrics["canonical_state_integrity"])["status"] != "pass":
        return "Recommended next action: resolve canonical state integrity issues before continuing autonomous work."
    return f"Recommended next action: review stop reason `{stop_reason}` with the current work-state and backlog before continuing."


def _feedback_handoff_summary(
    *,
    run_id: str,
    stop_reason: str,
    baseline_snapshot: dict[str, Any],
    final_snapshot: dict[str, Any],
    completed_task_ids: list[str],
    highest_risk_observation: str,
    recommended_next_action: str,
) -> list[str]:
    completed_summary = ", ".join(completed_task_ids) if completed_task_ids else "none"
    return [
        f"Run `{run_id}` ended with stop reason `{stop_reason}`.",
        (
            f"Readiness moved from `{baseline_snapshot['readiness_state']}` to "
            f"`{final_snapshot['readiness_state']}`; ready_for_deployment={final_snapshot['ready_for_deployment']}."
        ),
        f"Completed tasks: {completed_summary}.",
        highest_risk_observation,
        recommended_next_action,
    ]


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
    operator_summary: str,
    highest_risk_observation: str,
    recommended_next_action: str,
) -> dict[str, Any]:
    return {
        "schema_version": "autonomy-feedback-memory/v1",
        "memory_id": f"autonomy-feedback-{run_id}",
        "pack_id": pack_id,
        "run_id": run_id,
        "generated_at": ended_at,
        "summary": operator_summary,
        "handoff_summary": _feedback_handoff_summary(
            run_id=run_id,
            stop_reason=stop_reason,
            baseline_snapshot=baseline_snapshot,
            final_snapshot=final_snapshot,
            completed_task_ids=completed_task_ids,
            highest_risk_observation=highest_risk_observation,
            recommended_next_action=recommended_next_action,
        ),
        "highest_risk_observation": highest_risk_observation,
        "recommended_next_action": recommended_next_action,
        "baseline_readiness_state": cast(str, baseline_snapshot["readiness_state"]),
        "final_readiness_state": cast(str, final_snapshot["readiness_state"]),
        "active_task_id": final_snapshot.get("active_task_id"),
        "next_recommended_task_id": final_snapshot.get("next_recommended_task_id"),
        "ready_for_deployment": bool(final_snapshot["ready_for_deployment"]),
        "completed_task_ids": completed_task_ids,
        "evidence_paths": [
            cast(str, artifacts["loop_events_path"]),
            cast(str, artifacts["run_summary_path"]),
        ],
        "source_artifacts": {
            "loop_events_path": artifacts["loop_events_path"],
            "run_summary_path": artifacts["run_summary_path"],
            "factory_validation_command": artifacts.get("factory_validation_command"),
        },
    }


def start_run(
    *,
    pack_root: Path,
    run_id: str | None,
    notes: list[str],
    factory_root: Path,
) -> dict[str, Any]:
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
    _validate_payload(factory_root, LOOP_EVENT_SCHEMA_NAME, event, label="autonomy-loop-event")
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
    factory_root: Path,
) -> dict[str, Any]:
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
    _validate_payload(factory_root, LOOP_EVENT_SCHEMA_NAME, event, label="autonomy-loop-event")
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
    schema_factory_root: Path,
    validation_factory_root: Path | None,
) -> dict[str, Any]:
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
    task_completion_rate = (
        len(completed_task_ids) / len(tasks)
        if tasks
        else 0.0
    )
    resume_events = [
        event for event in events if event.get("event_type") == "task_selected"
    ]
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
    stale_memory_events = [
        event for event in memory_use_events if event.get("memory_state") == "used_and_stale"
    ]
    consistent_memory_events = [
        event
        for event in memory_use_events
        if event.get("decision_source") == "canonical_plus_memory"
        and event.get("memory_state") == "used_and_consistent"
    ]
    integrity, validation_command = _canonical_state_integrity(validation_factory_root)
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
            "deployability_changed": (
                baseline_snapshot["ready_for_deployment"] != final_snapshot["ready_for_deployment"]
            ),
            "gates_advanced_count": sum(
                1
                for gate_id, final_status in cast(dict[str, str], final_snapshot["gate_statuses"]).items()
                if cast(dict[str, str], baseline_snapshot["gate_statuses"]).get(gate_id) != final_status
            ),
        },
        "validation_evidence_gain": _validation_evidence_gain(
            cast(dict[str, Any], baseline_snapshot),
            final_snapshot,
        ),
        "benchmark_evidence_gain": _benchmark_evidence_gain(
            cast(dict[str, Any], baseline_snapshot),
            final_snapshot,
        ),
        "canonical_state_integrity": integrity,
    }
    if memory_use_events:
        metrics["resume_correctness"] = round(correct_resume_count / resume_count, 4) if resume_count else None
        metrics["stale_memory_rate"] = round(len(stale_memory_events) / len(memory_use_events), 4)
        metrics["consistent_memory_use_rate"] = round(len(consistent_memory_events) / len(memory_use_events), 4)

    stop_reason = _terminal_stop_reason(events)
    artifacts = {
        "loop_events_path": str(events_path),
        "run_summary_path": str(_summary_path(pack_root, run_id)),
        "feedback_memory_path": str(_feedback_memory_path(pack_root, run_id)),
        "factory_validation_command": validation_command,
    }
    operator_summary = _operator_summary(metrics, artifacts)
    highest_risk_observation = _highest_risk_observation(
        metrics=metrics,
        final_snapshot=final_snapshot,
    )
    recommended_next_action = _recommended_next_action(
        final_snapshot=final_snapshot,
        stop_reason=stop_reason,
        metrics=metrics,
    )
    summary = {
        "schema_version": "autonomy-run-summary/v1",
        "run_id": run_id,
        "pack_id": pack_id,
        "started_at": str(first_event["recorded_at"]),
        "ended_at": isoformat_z(),
        "baseline_snapshot": baseline_snapshot,
        "final_snapshot": final_snapshot,
        "step_count": len(events),
        "resume_count": resume_count,
        "completed_task_ids": completed_task_ids,
        "failed_command_count": sum(
            1
            for event in events
            if event.get("event_type") == "command_completed"
            and _outcome_is_failure(str(event.get("outcome", "")))
        ),
        "escalation_count": sum(1 for event in events if event.get("event_type") == "escalation_raised"),
        "stop_reason": stop_reason,
        "metrics": metrics,
        "operator_summary": operator_summary,
        "highest_risk_observation": highest_risk_observation,
        "recommended_next_action": recommended_next_action,
        "artifacts": artifacts,
    }
    _validate_payload(schema_factory_root, RUN_SUMMARY_SCHEMA_NAME, summary, label="autonomy-run-summary")
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
        operator_summary=operator_summary,
        highest_risk_observation=highest_risk_observation,
        recommended_next_action=recommended_next_action,
    )
    _validate_payload(
        schema_factory_root,
        FEEDBACK_MEMORY_SCHEMA_NAME,
        feedback_memory,
        label="autonomy-feedback-memory",
    )
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
    finalize_parser.add_argument("--factory-root")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    pack_root = _resolve_pack_root(args.pack_root)
    discovered_factory_root = _discover_factory_root(pack_root)
    if args.command == "start":
        if discovered_factory_root is None:
            print(json.dumps({"status": "failed", "error": "could not discover factory_root from pack_root"}, indent=2))
            return 1
        payload = start_run(
            pack_root=pack_root,
            run_id=args.run_id,
            notes=list(args.notes),
            factory_root=discovered_factory_root,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if args.command == "append-event":
        if discovered_factory_root is None:
            print(json.dumps({"status": "failed", "error": "could not discover factory_root from pack_root"}, indent=2))
            return 1
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
            factory_root=discovered_factory_root,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    validation_factory_root = (
        resolve_factory_root(args.factory_root)
        if args.factory_root is not None
        else discovered_factory_root
    )
    schema_factory_root = validation_factory_root or discovered_factory_root
    if schema_factory_root is None:
        print(json.dumps({"status": "failed", "error": "could not discover factory_root from pack_root; pass --factory-root to finalize"}, indent=2))
        return 1
    payload = finalize_run(
        pack_root=pack_root,
        run_id=args.run_id,
        schema_factory_root=schema_factory_root,
        validation_factory_root=validation_factory_root,
    )
    print(dump_json(payload), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
