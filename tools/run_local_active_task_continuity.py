#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import discover_pack, isoformat_z, read_now, resolve_factory_root, write_json
from record_autonomy_run import append_event, finalize_run, start_run
from refresh_local_feedback_memory_pointer import refresh_local_feedback_memory_pointer
from run_local_mid_backlog_checkpoint import (
    _eligible_next_tasks,
    _find_active_task,
    _load_matching_memory,
    _load_object,
    _merge_validation_results,
    _record_branch_decision,
    _resolve_next_task_decision,
    _run_task_command,
)


def run_local_active_task_continuity(
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
        raise ValueError("local active-task continuity requires a non-empty active_task_id")
    if next_task_id != active_task_id:
        raise ValueError("local active-task continuity requires next_recommended_task_id to equal active_task_id")
    if readiness.get("ready_for_deployment") is True:
        raise ValueError("local active-task continuity requires a pack that is not already ready_for_deployment")

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
        notes=["Local active-task continuity initialized so the pack can continue autonomously without a factory import step."],
        factory_root=factory_root,
    )
    append_event(
        pack_root=pack_root,
        run_id=run_id,
        event_type="task_selected",
        outcome="selected_active_task_for_local_continuity",
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
                "summary": f"Completed `{active_task_id}` through the declared validation_commands during local active-task continuity.",
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
        if isinstance(task, dict) and task.get("task_id") == active_task_id:
            task["status"] = "completed"

    remaining_task_ids = [
        str(task.get("task_id"))
        for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", []))
        if isinstance(task, dict)
        and isinstance(task.get("task_id"), str)
        and task.get("status") != "completed"
    ]
    eligible_next_tasks = _eligible_next_tasks(refreshed_backlog)
    branch_selection_notes: list[str] = []
    branch_selection_path: str | None = None
    next_active_task_id = None
    if not bool(refreshed_readiness.get("ready_for_deployment")) and eligible_next_tasks:
        branch_decision = _resolve_next_task_decision(
            pack_root=pack_root,
            backlog=refreshed_backlog,
            eligible_tasks=eligible_next_tasks,
        )
        branch_selection_path = _record_branch_decision(
            pack_root=pack_root,
            run_id=run_id,
            decision=branch_decision,
        )
        if branch_decision["status"] == "ambiguous":
            ambiguous_task_ids = cast(list[str], branch_decision["top_candidate_task_ids"])
            for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", [])):
                if not isinstance(task, dict):
                    continue
                if task.get("status") != "completed":
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
                    "autonomy_state": "blocked",
                    "active_task_id": None,
                    "next_recommended_task_id": None,
                    "pending_task_ids": remaining_task_ids,
                    "blocked_task_ids": ambiguous_task_ids,
                    "completed_task_ids": completed_task_ids,
                    "last_outcome": "ambiguity_requires_operator_review",
                    "last_outcome_at": isoformat_z(read_now()),
                    "last_validation_results": last_validation_results,
                    "last_agent_action": (
                        f"Completed `{active_task_id}` locally during disconnected continuity but stopped because multiple next tasks remained ambiguous: "
                        + ", ".join(f'`{task_id}`' for task_id in ambiguous_task_ids)
                        + "."
                    ),
                    "escalation_state": "operator_review_required",
                }
            )
            write_json(work_state_path, refreshed_work_state)

            append_event(
                pack_root=pack_root,
                run_id=run_id,
                event_type="escalation_raised",
                outcome="ambiguous_next_task_selection",
                decision_source=decision_source,
                memory_state=memory_state,
                commands_attempted=[],
                notes=[
                    cast(str, branch_decision["ambiguity_reason"]),
                    f"Operator disambiguation is required before continuing: {', '.join(ambiguous_task_ids)}.",
                ],
                evidence_paths=[] if branch_selection_path is None else [branch_selection_path],
                stop_reason="declared_escalation_boundary",
                active_task_id=None,
                next_recommended_task_id=None,
                factory_root=factory_root,
            )
            summary = finalize_run(
                pack_root=pack_root,
                run_id=run_id,
                schema_factory_root=factory_root,
                validation_factory_root=None,
            )
            pointer_result = refresh_local_feedback_memory_pointer(
                factory_root=factory_root,
                build_pack_id=build_pack_id,
                updated_at=cast(str, summary.get("ended_at")),
            )
            return {
                "status": "blocked",
                "build_pack_id": build_pack_id,
                "run_id": run_id,
                "completed_task_id": active_task_id,
                "next_active_task_id": None,
                "blocked_task_ids": ambiguous_task_ids,
                "run_summary_path": str(pack_root / ".pack-state" / "autonomy-runs" / run_id / "run-summary.json"),
                "feedback_memory_path": str(pack_root / ".pack-state" / "agent-memory" / f"autonomy-feedback-{run_id}.json"),
                "pointer_result": pointer_result,
                "ready_for_deployment": bool(refreshed_readiness.get("ready_for_deployment")),
            }
        next_active_task_id = cast(str, branch_decision["chosen_task_id"])
        if cast(str | None, branch_decision.get("selection_method")) == "operator_hint":
            branch_selection_notes.append(
                f"Multiple next tasks were eligible; selected `{next_active_task_id}` using operator branch-selection hints."
            )
        elif cast(str | None, branch_decision.get("selection_method")) == "operator_hint_plus_semantic_alignment":
            branch_selection_notes.append(
                f"Multiple next tasks were eligible; operator branch-selection hints narrowed the candidates, then bounded semantic alignment selected `{next_active_task_id}`."
            )
        elif cast(str | None, branch_decision.get("selection_method")) == "semantic_alignment":
            branch_selection_notes.append(
                f"Multiple next tasks were eligible; selected `{next_active_task_id}` using bounded semantic alignment to the objective and resume context."
            )
        elif len(cast(list[str], branch_decision["candidate_task_ids"])) > 1:
            branch_selection_notes.append(
                f"Multiple next tasks were eligible; selected `{next_active_task_id}` using the lowest selection_priority."
            )
    for task in cast(list[dict[str, Any]], refreshed_backlog.get("tasks", [])):
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        if next_active_task_id is not None and task_id == next_active_task_id:
            task["status"] = "in_progress"
        elif task.get("status") != "completed":
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
    autonomy_state = "ready_for_deploy" if bool(refreshed_readiness.get("ready_for_deployment")) else "actively_building"
    refreshed_work_state.update(
        {
            "autonomy_state": autonomy_state,
            "active_task_id": next_active_task_id,
            "next_recommended_task_id": next_active_task_id,
            "pending_task_ids": [] if next_active_task_id is None else [task_id for task_id in remaining_task_ids if task_id != next_active_task_id],
            "blocked_task_ids": [],
            "completed_task_ids": completed_task_ids,
            "last_outcome": "task_completed",
            "last_outcome_at": isoformat_z(read_now()),
            "last_validation_results": last_validation_results,
            "last_agent_action": (
                f"Completed `{active_task_id}` locally during disconnected continuity and advanced canonical state."
                if not branch_selection_notes
                else f"Completed `{active_task_id}` locally during disconnected continuity and selected `{next_active_task_id}` from multiple eligible next tasks."
            ),
            "escalation_state": "none",
        }
    )
    write_json(work_state_path, refreshed_work_state)

    append_event(
        pack_root=pack_root,
        run_id=run_id,
        event_type="state_updated",
        outcome="local_active_task_continuity_completed",
        decision_source=decision_source,
        memory_state=memory_state,
        commands_attempted=[],
        notes=[
            f"Completed active task `{active_task_id}` locally and advanced canonical state to next task `{next_active_task_id}`.",
            f"ready_for_deployment={bool(refreshed_readiness.get('ready_for_deployment'))}.",
            *branch_selection_notes,
        ],
        evidence_paths=[] if branch_selection_path is None else [branch_selection_path],
        stop_reason=None,
        active_task_id=next_active_task_id,
        next_recommended_task_id=next_active_task_id,
        factory_root=factory_root,
    )

    summary = finalize_run(
        pack_root=pack_root,
        run_id=run_id,
        schema_factory_root=factory_root,
        validation_factory_root=None,
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
        "ready_for_deployment": bool(refreshed_readiness.get("ready_for_deployment")),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Continue the current canonical active task locally and refresh feedback memory.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--build-pack-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_local_active_task_continuity(
        factory_root=resolve_factory_root(args.factory_root),
        build_pack_id=args.build_pack_id,
        run_id=args.run_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
