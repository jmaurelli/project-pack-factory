#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    discover_pack,
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)
from import_external_runtime_evidence import _refresh_latest_memory_pointer


REQUEST_SCHEMA_NAME = "imported-runtime-state-reconcile-request.schema.json"
REPORT_SCHEMA_NAME = "imported-runtime-state-reconcile-report.schema.json"
REQUEST_SCHEMA_VERSION = "imported-runtime-state-reconcile-request/v1"
REPORT_SCHEMA_VERSION = "imported-runtime-state-reconcile-report/v1"
RECONCILE_PREFIX = "reconcile-imported-runtime-state"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _validate_payload(factory_root: Path, schema_name: str, payload: dict[str, Any], *, label: str) -> None:
    schema_file = schema_path(factory_root, schema_name)
    temp_root = factory_root / ".pack-state" / "reconcile-imported-runtime-state-schema-validation"
    temp_root.mkdir(parents=True, exist_ok=True)
    temp_path = temp_root / f"{label}.json"
    write_json(temp_path, payload)
    errors = validate_json_document(temp_path, schema_file)
    temp_path.unlink(missing_ok=True)
    if temp_root.exists() and not any(temp_root.iterdir()):
        temp_root.rmdir()
    if errors:
        raise ValueError("; ".join(errors))


def _resolve_reference(base: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()


def _load_request(factory_root: Path, request_path: Path) -> dict[str, Any]:
    payload = _load_object(request_path)
    _validate_payload(factory_root, REQUEST_SCHEMA_NAME, payload, label="reconcile-request")
    if payload.get("schema_version") != REQUEST_SCHEMA_VERSION:
        raise ValueError(f"request schema_version must be `{REQUEST_SCHEMA_VERSION}`")
    return payload


def _make_reconcile_id(moment: Any) -> str:
    return f"{RECONCILE_PREFIX}-{timestamp_token(moment)}"


def _read_pack_state(pack_root: Path) -> dict[str, Any]:
    return {
        "readiness": _load_object(pack_root / "status/readiness.json"),
        "eval_latest": _load_object(pack_root / "eval/latest/index.json"),
        "work_state": _load_object(pack_root / "status/work-state.json"),
        "task_backlog": _load_object(pack_root / "tasks/active-backlog.json"),
    }


def _summary_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    readiness = cast(dict[str, Any], state["readiness"])
    eval_latest = cast(dict[str, Any], state["eval_latest"])
    work_state = cast(dict[str, Any], state["work_state"])
    backlog = cast(dict[str, Any], state["task_backlog"])
    return {
        "readiness_state": readiness.get("readiness_state"),
        "ready_for_deployment": readiness.get("ready_for_deployment"),
        "gate_statuses": {
            str(gate.get("gate_id")): str(gate.get("status"))
            for gate in cast(list[dict[str, Any]], readiness.get("required_gates", []))
            if isinstance(gate, dict) and isinstance(gate.get("gate_id"), str)
        },
        "eval_result_statuses": {
            str(result.get("benchmark_id")): str(result.get("status"))
            for result in cast(list[dict[str, Any]], eval_latest.get("benchmark_results", []))
            if isinstance(result, dict) and isinstance(result.get("benchmark_id"), str)
        },
        "active_task_id": work_state.get("active_task_id"),
        "next_recommended_task_id": work_state.get("next_recommended_task_id"),
        "completed_task_ids": list(work_state.get("completed_task_ids", [])),
        "task_statuses": {
            str(task.get("task_id")): str(task.get("status"))
            for task in cast(list[dict[str, Any]], backlog.get("tasks", []))
            if isinstance(task, dict) and isinstance(task.get("task_id"), str)
        },
    }


def _autonomy_state_from_readiness(final_snapshot: dict[str, Any]) -> str:
    readiness_state = final_snapshot.get("readiness_state")
    if readiness_state == "ready_for_deploy":
        return "ready_for_deploy"
    if readiness_state == "blocked":
        return "blocked"
    if readiness_state == "ready_for_review":
        return "ready_for_review"
    return "actively_building"


def _build_validation_results(
    *,
    task_backlog: dict[str, Any],
    completed_task_ids: list[str],
    active_task_id: str | None,
    source_run_summary_relpath: str,
    source_loop_events_relpath: str | None,
    recorded_at: str | None,
) -> list[dict[str, Any]]:
    evidence_paths = [source_run_summary_relpath]
    if source_loop_events_relpath is not None:
        evidence_paths.append(source_loop_events_relpath)
    results: list[dict[str, Any]] = []
    for task in cast(list[dict[str, Any]], task_backlog.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str):
            continue
        if task_id in completed_task_ids:
            status = "pass"
        elif task_id == active_task_id:
            status = "in_progress"
        else:
            continue
        results.append(
            {
                "validation_id": task_id,
                "status": status,
                "summary": "Reconciled local canonical state from imported external runtime evidence.",
                "evidence_paths": evidence_paths,
                "recorded_at": recorded_at,
            }
        )
    return results


def reconcile_imported_runtime_state(factory_root: Path, request: dict[str, Any], *, request_file_dir: Path) -> dict[str, Any]:
    build_pack_id = str(request["build_pack_id"])
    import_report_path = _resolve_reference(request_file_dir, str(request["import_report_path"]))
    reconcile_reason = str(request["reconcile_reason"])
    reconciled_by = str(request["reconciled_by"])

    if not import_report_path.exists():
        raise FileNotFoundError(f"import report does not exist: {import_report_path}")

    target_pack = discover_pack(factory_root, build_pack_id)
    if target_pack.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")

    import_report = _load_object(import_report_path)
    if import_report.get("build_pack_id") != build_pack_id:
        raise ValueError("import report build_pack_id does not match request")
    import_id = import_report.get("import_id")
    if not isinstance(import_id, str) or not import_id:
        raise ValueError("import report must include a non-empty import_id")

    import_root = import_report_path.parent
    source_run_summary_path = import_root / "external-runtime-evidence" / "artifacts" / "run-summary.json"
    source_loop_events_path = import_root / "external-runtime-evidence" / "artifacts" / "loop-events.jsonl"
    if not source_run_summary_path.exists():
        raise FileNotFoundError(f"imported run summary does not exist: {source_run_summary_path}")

    run_summary = _load_object(source_run_summary_path)
    if run_summary.get("pack_id") != build_pack_id:
        raise ValueError("imported run summary pack_id does not match request")
    source_run_id = run_summary.get("run_id")
    if not isinstance(source_run_id, str) or not source_run_id:
        raise ValueError("imported run summary must include a non-empty run_id")

    final_snapshot = run_summary.get("final_snapshot")
    if not isinstance(final_snapshot, dict):
        raise ValueError("imported run summary must include final_snapshot")
    completed_task_ids = run_summary.get("completed_task_ids", [])
    if not isinstance(completed_task_ids, list) or not all(isinstance(item, str) for item in completed_task_ids):
        raise ValueError("imported run summary completed_task_ids must be a string array")

    now = read_now()
    generated_at = isoformat_z(now)
    reconcile_id = _make_reconcile_id(now)
    reconcile_root = target_pack.pack_root / "eval/history" / reconcile_id
    if reconcile_root.exists():
        current = now
        while reconcile_root.exists():
            current += timedelta(seconds=1)
            generated_at = isoformat_z(current)
            reconcile_id = _make_reconcile_id(current)
            reconcile_root = target_pack.pack_root / "eval/history" / reconcile_id
    reconcile_root.mkdir(parents=True, exist_ok=False)

    before_state = _read_pack_state(target_pack.pack_root)
    before_summary = _summary_snapshot(before_state)

    readiness = cast(dict[str, Any], json.loads(json.dumps(before_state["readiness"])))
    gate_statuses = final_snapshot.get("gate_statuses", {})
    if not isinstance(gate_statuses, dict):
        gate_statuses = {}
    source_run_summary_relpath = relative_path(target_pack.pack_root, source_run_summary_path)
    source_loop_events_relpath = relative_path(target_pack.pack_root, source_loop_events_path) if source_loop_events_path.exists() else None
    for gate in cast(list[dict[str, Any]], readiness.get("required_gates", [])):
        if not isinstance(gate, dict):
            continue
        gate_id = gate.get("gate_id")
        if not isinstance(gate_id, str):
            continue
        if gate_id not in gate_statuses:
            continue
        gate["status"] = gate_statuses[gate_id]
        gate["last_run_at"] = generated_at
        gate["evidence_paths"] = [source_run_summary_relpath]
    readiness["last_evaluated_at"] = generated_at
    readiness["readiness_state"] = final_snapshot.get("readiness_state", readiness.get("readiness_state"))
    readiness["ready_for_deployment"] = bool(final_snapshot.get("ready_for_deployment"))
    if readiness["ready_for_deployment"]:
        readiness["blocking_issues"] = []
    else:
        highest_risk = run_summary.get("highest_risk_observation")
        readiness["blocking_issues"] = [highest_risk] if isinstance(highest_risk, str) and highest_risk else list(readiness.get("blocking_issues", []))
    recommended_next = run_summary.get("recommended_next_action")
    if isinstance(recommended_next, str) and recommended_next:
        readiness["recommended_next_actions"] = [recommended_next]
    write_json(target_pack.pack_root / "status/readiness.json", readiness)

    eval_latest = cast(dict[str, Any], json.loads(json.dumps(before_state["eval_latest"])))
    eval_result_statuses = final_snapshot.get("eval_result_statuses", {})
    if not isinstance(eval_result_statuses, dict):
        eval_result_statuses = {}
    for result in cast(list[dict[str, Any]], eval_latest.get("benchmark_results", [])):
        if not isinstance(result, dict):
            continue
        benchmark_id = result.get("benchmark_id")
        if not isinstance(benchmark_id, str):
            continue
        if benchmark_id not in eval_result_statuses:
            continue
        result["status"] = eval_result_statuses[benchmark_id]
        result["latest_run_id"] = source_run_id
        result["run_artifact_path"] = source_run_summary_relpath
        result["summary_artifact_path"] = source_run_summary_relpath
    eval_latest["updated_at"] = generated_at
    write_json(target_pack.pack_root / "eval/latest/index.json", eval_latest)

    task_backlog = cast(dict[str, Any], json.loads(json.dumps(before_state["task_backlog"])))
    active_task_id = final_snapshot.get("active_task_id")
    next_task_id = final_snapshot.get("next_recommended_task_id")
    for task in cast(list[dict[str, Any]], task_backlog.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        if not isinstance(task_id, str):
            continue
        if task_id in completed_task_ids:
            task["status"] = "completed"
        elif not readiness["ready_for_deployment"] and task_id in {active_task_id, next_task_id}:
            task["status"] = "in_progress"
        else:
            task["status"] = "pending"
    write_json(target_pack.pack_root / "tasks/active-backlog.json", task_backlog)

    work_state = cast(dict[str, Any], json.loads(json.dumps(before_state["work_state"])))
    all_task_ids = [
        str(task.get("task_id"))
        for task in cast(list[dict[str, Any]], task_backlog.get("tasks", []))
        if isinstance(task, dict) and isinstance(task.get("task_id"), str)
    ]
    completed_set = {task_id for task_id in completed_task_ids}
    pending_task_ids = [
        task_id for task_id in all_task_ids
        if task_id not in completed_set and task_id not in {active_task_id}
    ]
    work_state.update(
        {
            "autonomy_state": _autonomy_state_from_readiness(final_snapshot),
            "active_task_id": active_task_id,
            "next_recommended_task_id": next_task_id,
            "pending_task_ids": [] if readiness["ready_for_deployment"] else pending_task_ids,
            "blocked_task_ids": [],
            "completed_task_ids": completed_task_ids,
            "last_outcome": "task_completed",
            "last_outcome_at": generated_at,
            "last_validation_results": _build_validation_results(
                task_backlog=task_backlog,
                completed_task_ids=completed_task_ids,
                active_task_id=cast(str | None, active_task_id),
                source_run_summary_relpath=source_run_summary_relpath,
                source_loop_events_relpath=source_loop_events_relpath,
                recorded_at=cast(str | None, run_summary.get("ended_at")),
            ),
            "last_agent_action": f"Reconciled local canonical state from imported external runtime evidence `{import_id}`.",
            "escalation_state": "none",
        }
    )
    write_json(target_pack.pack_root / "status/work-state.json", work_state)

    pointer_refresh = _refresh_latest_memory_pointer(
        factory_root=factory_root,
        target_pack=target_pack,
        import_generated_at=generated_at,
        import_id=import_id,
        promoted_memory_path=target_pack.pack_root / ".pack-state/agent-memory" / f"autonomy-feedback-{source_run_id}.json",
        source_bundle_path=f"external-runtime-evidence/artifacts/agent-memory/autonomy-feedback-{source_run_id}.json",
    )

    after_state = _read_pack_state(target_pack.pack_root)
    after_summary = _summary_snapshot(after_state)
    report_payload = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "reconcile_id": reconcile_id,
        "generated_at": generated_at,
        "status": "completed",
        "build_pack_id": build_pack_id,
        "build_pack_root": relative_path(factory_root, target_pack.pack_root),
        "import_report_path": str(import_report_path),
        "reconcile_reason": reconcile_reason,
        "reconciled_by": reconciled_by,
        "source_import_id": import_id,
        "source_run_id": source_run_id,
        "source_run_summary_path": source_run_summary_relpath,
        "memory_pointer_status": pointer_refresh["status"],
        "control_plane_mutations": {
            "readiness_updated": True,
            "work_state_updated": True,
            "eval_latest_updated": True,
            "task_backlog_updated": True,
            "memory_pointer_updated": True,
            "eval_history_written": True,
        },
        "before_summary": before_summary,
        "after_summary": after_summary,
    }
    _validate_payload(factory_root, REPORT_SCHEMA_NAME, report_payload, label="reconcile-report")
    report_path = reconcile_root / "reconcile-report.json"
    write_json(report_path, report_payload)

    return {
        "status": "completed",
        "reconcile_id": reconcile_id,
        "generated_at": generated_at,
        "build_pack_id": build_pack_id,
        "build_pack_root": relative_path(factory_root, target_pack.pack_root),
        "report_path": str(report_path),
        "memory_pointer_status": pointer_refresh["status"],
        "after_summary": after_summary,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile local canonical pack state from imported runtime evidence.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args(argv)

    factory_root = resolve_factory_root(args.factory_root)
    request_path = Path(args.request_file).expanduser().resolve()
    request = _load_request(factory_root, request_path)
    result = reconcile_imported_runtime_state(factory_root, request, request_file_dir=request_path.parent.resolve())
    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
