#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import discover_pack, isoformat_z, load_json, read_now, resolve_factory_root, write_json
from record_autonomy_run import append_event, finalize_run, start_run
from refresh_local_feedback_memory_pointer import refresh_local_feedback_memory_pointer


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _load_matching_memory(pack_root: Path, active_task_id: str) -> tuple[bool, str, list[str]]:
    pointer_path = pack_root / ".pack-state" / "agent-memory" / "latest-memory.json"
    if not pointer_path.exists():
        return False, "canonical_only", ["No active latest-memory pointer was present; selected the active task from canonical state."]
    pointer_payload = _load_object(pointer_path)
    selected_memory_path = pointer_payload.get("selected_memory_path")
    if not isinstance(selected_memory_path, str) or not selected_memory_path:
        return False, "canonical_only", ["The active latest-memory pointer was incomplete; used canonical state only."]
    memory_path = (pack_root / selected_memory_path).resolve()
    if not memory_path.exists():
        return False, "canonical_only", ["The active latest-memory pointer referenced a missing file; used canonical state only."]
    memory_payload = _load_object(memory_path)
    if memory_payload.get("active_task_id") != active_task_id or memory_payload.get("next_recommended_task_id") != active_task_id:
        return False, "canonical_only", ["The active latest-memory pointer did not match the current active task; used canonical state only."]
    return True, "canonical_plus_memory", [
        f"Loaded local feedback memory from {memory_path.as_posix()} and confirmed it matched active task `{active_task_id}`."
    ]


def _find_active_task(backlog: dict[str, Any], active_task_id: str) -> dict[str, Any]:
    for task in cast(list[dict[str, Any]], backlog.get("tasks", [])):
        if isinstance(task, dict) and task.get("task_id") == active_task_id:
            return task
    raise ValueError(f"active task `{active_task_id}` was not found in tasks/active-backlog.json")


def _run_task_command(pack_root: Path, command: str) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        shell=True,
        executable="/bin/bash",
        cwd=pack_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"command failed: {command}")
    stdout = completed.stdout.strip()
    if not stdout:
        return {"status": "completed", "generated_at": isoformat_z(read_now()), "evidence_paths": []}
    payload = json.loads(stdout)
    if not isinstance(payload, dict):
        raise ValueError(f"command output must be a JSON object: {command}")
    return payload


def _merge_validation_results(existing: list[dict[str, Any]], fresh: dict[str, Any]) -> list[dict[str, Any]]:
    merged = [result for result in existing if result.get("validation_id") != fresh.get("validation_id")]
    merged.append(fresh)
    return merged


def run_local_mid_backlog_checkpoint(
    *,
    factory_root: Path,
    build_pack_id: str,
    run_id: str,
) -> dict[str, Any]:
    target_pack = discover_pack(factory_root, build_pack_id)
    if target_pack.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")

    pack_root = target_pack.pack_root
    work_state_path = pack_root / "status/work-state.json"
    backlog_path = pack_root / "tasks/active-backlog.json"
    readiness_path = pack_root / "status/readiness.json"

    work_state = _load_object(work_state_path)
    backlog = _load_object(backlog_path)
    readiness = _load_object(readiness_path)

    active_task_id = work_state.get("active_task_id")
    next_task_id = work_state.get("next_recommended_task_id")
    if not isinstance(active_task_id, str) or not active_task_id:
        raise ValueError("mid-backlog checkpoint requires a non-empty active_task_id")
    if next_task_id != active_task_id:
        raise ValueError("mid-backlog checkpoint requires next_recommended_task_id to equal active_task_id")
    if readiness.get("ready_for_deployment") is True:
        raise ValueError("mid-backlog checkpoint requires a pack that is not already ready_for_deployment")

    active_task = _find_active_task(backlog, active_task_id)
    validation_commands = active_task.get("validation_commands", [])
    if not isinstance(validation_commands, list) or not validation_commands or not all(
        isinstance(command, str) and command.strip() for command in validation_commands
    ):
        raise ValueError(f"active task `{active_task_id}` must declare non-empty validation_commands")

    memory_used, decision_source, selection_notes = _load_matching_memory(pack_root, active_task_id)
    memory_state = "used_and_consistent" if memory_used else "not_used"

    start_run(
        pack_root=pack_root,
        run_id=run_id,
        notes=["Local mid-backlog checkpoint initialized before handing the next task to a future autonomy run."],
        factory_root=factory_root,
    )
    append_event(
        pack_root=pack_root,
        run_id=run_id,
        event_type="task_selected",
        outcome="selected_active_task_for_mid_backlog_checkpoint",
        decision_source=decision_source,
        memory_state=memory_state,
        commands_attempted=[],
        notes=selection_notes,
        evidence_paths=[],
        stop_reason=None,
        active_task_id=active_task_id,
        next_recommended_task_id=active_task_id,
        factory_root=factory_root,
    )

    recorded_results: list[dict[str, Any]] = []
    for command in validation_commands:
        payload = _run_task_command(pack_root, command)
        evidence_paths = list(payload.get("evidence_paths", [])) if isinstance(payload.get("evidence_paths", []), list) else []
        recorded_results.append(
            {
                "validation_id": active_task_id,
                "status": "pass",
                "summary": f"Completed `{active_task_id}` through the declared validation_commands during a local mid-backlog checkpoint.",
                "evidence_paths": evidence_paths,
                "recorded_at": payload.get("generated_at"),
            }
        )
        append_event(
            pack_root=pack_root,
            run_id=run_id,
            event_type="command_completed",
            outcome=f"{active_task_id}_command_completed",
            decision_source=decision_source,
            memory_state=memory_state,
            commands_attempted=[command],
            notes=[f"Completed the declared command for active task `{active_task_id}`."],
            evidence_paths=evidence_paths,
            stop_reason=None,
            active_task_id=active_task_id,
            next_recommended_task_id=active_task_id,
            factory_root=factory_root,
        )

    refreshed_readiness = _load_object(readiness_path)
    refreshed_backlog = _load_object(backlog_path)
    for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        if task_id == active_task_id:
            task["status"] = "completed"

    remaining_task_ids = [
        str(task.get("task_id"))
        for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", []))
        if isinstance(task, dict)
        and isinstance(task.get("task_id"), str)
        and task.get("status") != "completed"
    ]
    if refreshed_readiness.get("ready_for_deployment") is True or not remaining_task_ids:
        raise ValueError("mid-backlog checkpoint requires at least one remaining canonical task after the selected task completes")

    next_active_task_id = remaining_task_ids[0]
    for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        if task.get("task_id") == next_active_task_id:
            task["status"] = "in_progress"
        elif task.get("task_id") != active_task_id and task.get("status") != "completed":
            task["status"] = "pending"
    write_json(backlog_path, refreshed_backlog)

    refreshed_work_state = _load_object(work_state_path)
    last_validation_results = list(refreshed_work_state.get("last_validation_results", []))
    for result in recorded_results:
        if isinstance(result, dict):
            last_validation_results = _merge_validation_results(last_validation_results, result)
    completed_task_ids = list(refreshed_work_state.get("completed_task_ids", []))
    if active_task_id not in completed_task_ids:
        completed_task_ids.append(active_task_id)
    refreshed_work_state.update(
        {
            "autonomy_state": "actively_building",
            "active_task_id": next_active_task_id,
            "next_recommended_task_id": next_active_task_id,
            "pending_task_ids": [task_id for task_id in remaining_task_ids if task_id != next_active_task_id],
            "blocked_task_ids": [],
            "completed_task_ids": completed_task_ids,
            "last_outcome": "task_completed",
            "last_outcome_at": isoformat_z(read_now()),
            "last_validation_results": last_validation_results,
            "last_agent_action": f"Completed `{active_task_id}` locally and stopped at a mid-backlog checkpoint with `{next_active_task_id}` as the canonical next task.",
            "escalation_state": "none",
        }
    )
    write_json(work_state_path, refreshed_work_state)

    append_event(
        pack_root=pack_root,
        run_id=run_id,
        event_type="state_updated",
        outcome="mid_backlog_checkpoint_created",
        decision_source=decision_source,
        memory_state=memory_state,
        commands_attempted=[],
        notes=[f"Advanced canonical state so `{next_active_task_id}` became the active task for the next autonomy run."],
        evidence_paths=[],
        stop_reason=None,
        active_task_id=next_active_task_id,
        next_recommended_task_id=next_active_task_id,
        factory_root=factory_root,
    )
    append_event(
        pack_root=pack_root,
        run_id=run_id,
        event_type="run_stopped",
        outcome="mid_backlog_checkpoint_created",
        decision_source="canonical_only",
        memory_state="not_used",
        commands_attempted=[],
        notes=["Stopped intentionally after advancing canonical state to the next task so the feedback-memory handoff could be exercised."],
        evidence_paths=[],
        stop_reason="mid_backlog_checkpoint_created",
        active_task_id=next_active_task_id,
        next_recommended_task_id=next_active_task_id,
        factory_root=factory_root,
    )

    summary = finalize_run(
        pack_root=pack_root,
        run_id=run_id,
        schema_factory_root=factory_root,
        validation_factory_root=factory_root,
    )
    pointer_result = refresh_local_feedback_memory_pointer(
        factory_root=factory_root,
        build_pack_id=build_pack_id,
        updated_at=cast(str, summary.get("ended_at")),
    )
    return {
        "status": "completed",
        "build_pack_id": build_pack_id,
        "run_id": run_id,
        "completed_task_id": active_task_id,
        "next_active_task_id": next_active_task_id,
        "run_summary_path": str(pack_root / ".pack-state" / "autonomy-runs" / run_id / "run-summary.json"),
        "feedback_memory_path": str(pack_root / ".pack-state" / "agent-memory" / f"autonomy-feedback-{run_id}.json"),
        "pointer_result": pointer_result,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local mid-backlog checkpoint and refresh local feedback memory.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--build-pack-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=args.build_pack_id,
        run_id=args.run_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
