#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
    load_pack_manifest,
    read_now,
    resolve_pack_root,
    timestamp_token,
    validate_named_payload,
    write_json,
)

LOOP_EVENT_SCHEMA_NAME: Final[str] = "autonomy-loop-event.schema.json"
RUN_SUMMARY_SCHEMA_NAME: Final[str] = "autonomy-run-summary.schema.json"
EVENTS_FILENAME: Final[str] = "loop-events.jsonl"
SUMMARY_FILENAME: Final[str] = "run-summary.json"
AUTONOMY_RUNS_DIR: Final[Path] = Path(".pack-state") / "autonomy-runs"
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
    if cast(dict[str, Any], metrics["canonical_state_integrity"])["status"] != "pass":
        return "Recommended next action: resolve canonical state integrity questions before continuing autonomous work."
    return f"Recommended next action: review stop reason `{stop_reason}` with the current work-state and backlog before continuing."


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
    artifacts = {
        "loop_events_path": str(events_path),
        "run_summary_path": str(_summary_path(pack_root, run_id)),
        "factory_validation_command": validation_command,
    }
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
        "operator_summary": _operator_summary(metrics, artifacts),
        "highest_risk_observation": _highest_risk_observation(metrics=metrics, final_snapshot=final_snapshot),
        "recommended_next_action": _recommended_next_action(
            final_snapshot=final_snapshot,
            stop_reason=stop_reason,
            metrics=metrics,
        ),
        "artifacts": artifacts,
    }
    _validate_payload(pack_root, manifest, RUN_SUMMARY_SCHEMA_NAME, summary)
    write_json(_summary_path(pack_root, run_id), summary)
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
