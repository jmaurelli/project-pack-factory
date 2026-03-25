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

from factory_ops import (
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
from materialize_build_pack import materialize_build_pack
from reconcile_imported_runtime_state import reconcile_imported_runtime_state
from run_local_mid_backlog_checkpoint import run_local_mid_backlog_checkpoint
from run_remote_active_task_continuity_test import run_remote_active_task_continuity_test
from run_remote_memory_continuity_test import run_remote_memory_continuity_test


REPORT_SCHEMA_NAME = "longer-backlog-autonomy-exercise-report.schema.json"
REPORT_SCHEMA_VERSION = "longer-backlog-autonomy-exercise-report/v1"
EXERCISE_PREFIX = "longer-backlog-autonomy-exercise"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _exercise_id(target_build_pack_id: str) -> str:
    return f"{EXERCISE_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _exercise_root(factory_root: Path, exercise_id: str) -> Path:
    return factory_root / ".pack-state" / "longer-backlog-autonomy-exercises" / exercise_id


def _materialization_request(
    *,
    source_template_id: str,
    target_build_pack_id: str,
    target_display_name: str,
    target_version: str,
    target_revision: str,
    actor: str,
) -> dict[str, Any]:
    return {
        "schema_version": "build-pack-materialization-request/v1",
        "source_template_id": source_template_id,
        "target_build_pack_id": target_build_pack_id,
        "target_display_name": target_display_name,
        "target_version": target_version,
        "target_revision": target_revision,
        "materialized_by": actor,
        "materialization_reason": "Create a fresh proving-ground build-pack for PackFactory longer-backlog autonomy stress testing.",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
    }


def _reconcile_request(*, build_pack_id: str, import_report_path: str, actor: str, hop_number: int) -> dict[str, Any]:
    return {
        "schema_version": "imported-runtime-state-reconcile-request/v1",
        "build_pack_id": build_pack_id,
        "import_report_path": import_report_path,
        "reconcile_reason": f"Adopt the successful remote longer-backlog continuity result for hop {hop_number} into local canonical state.",
        "reconciled_by": actor,
    }


def _final_state(pack_root: Path) -> dict[str, Any]:
    return {
        "readiness": _load_object(pack_root / "status/readiness.json"),
        "work_state": _load_object(pack_root / "status/work-state.json"),
        "task_backlog": _load_object(pack_root / "tasks/active-backlog.json"),
        "latest_memory": _load_object(pack_root / ".pack-state/agent-memory/latest-memory.json"),
    }


def _helper_script_text() -> str:
    return """#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"{path} did not contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a bounded longer-backlog continuity checkpoint artifact.")
    parser.add_argument("--pack-root", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args()

    pack_root = Path(args.pack_root).resolve()
    work_state = load_object(pack_root / "status/work-state.json")
    readiness = load_object(pack_root / "status/readiness.json")
    pointer_path = pack_root / ".pack-state" / "agent-memory" / "latest-memory.json"
    pointer_payload = load_object(pointer_path) if pointer_path.exists() else None

    timestamp = now()
    artifact_dir = pack_root / "eval" / "history" / f"{args.task_id}-{timestamp.replace(':', '').replace('-', '').lower()}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = artifact_dir / "checkpoint-result.json"
    artifact_payload = {
        "schema_version": "longer-backlog-checkpoint-result/v1",
        "generated_at": timestamp,
        "task_id": args.task_id,
        "active_task_id": work_state.get("active_task_id"),
        "next_recommended_task_id": work_state.get("next_recommended_task_id"),
        "ready_for_deployment": readiness.get("ready_for_deployment"),
        "readiness_state": readiness.get("readiness_state"),
        "memory_pointer_present": pointer_payload is not None,
        "memory_pointer_run_id": None if pointer_payload is None else pointer_payload.get("selected_run_id"),
        "summary": "Recorded a bounded continuity checkpoint artifact without mutating canonical readiness state.",
    }
    artifact_path.write_text(json.dumps(artifact_payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "completed",
                "generated_at": timestamp,
                "evidence_paths": [artifact_path.relative_to(pack_root).as_posix()],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


def _extend_to_longer_backlog(*, pack_root: Path, extra_task_count: int) -> dict[str, Any]:
    if extra_task_count < 1:
        raise ValueError("extra_task_count must be at least 1")

    backlog_path = pack_root / "tasks/active-backlog.json"
    work_state_path = pack_root / "status/work-state.json"
    project_objective_path = pack_root / "contracts/project-objective.json"

    backlog = _load_object(backlog_path)
    work_state = _load_object(work_state_path)
    project_objective = _load_object(project_objective_path)

    tasks = cast(list[dict[str, Any]], backlog.get("tasks", []))
    validation_task = next((task for task in tasks if task.get("task_id") == "run_build_pack_validation"), None)
    benchmark_task = next((task for task in tasks if task.get("task_id") == "run_inherited_benchmarks"), None)
    if not isinstance(validation_task, dict) or not isinstance(benchmark_task, dict):
        raise ValueError("expected the default validation and benchmark starter tasks to be present")

    helper_relative_path = Path("src/record_longer_backlog_progress.py")
    helper_path = pack_root / helper_relative_path
    helper_path.write_text(_helper_script_text(), encoding="utf-8")

    extra_tasks: list[dict[str, Any]] = []
    previous_task_id = "run_build_pack_validation"
    extra_task_ids: list[str] = []
    for index in range(1, extra_task_count + 1):
        task_id = f"record_progress_checkpoint_{index:02d}"
        extra_task_ids.append(task_id)
        extra_tasks.append(
            {
                "task_id": task_id,
                "summary": f"Record bounded continuity checkpoint evidence hop {index} after the current canonical task completes.",
                "status": "pending",
                "objective_link": backlog.get("objective_id"),
                "acceptance_criteria": [
                    "The checkpoint helper exits successfully.",
                    "A checkpoint artifact is written under eval/history.",
                ],
                "validation_commands": [
                    f"python3 {helper_relative_path.as_posix()} --pack-root . --task-id {task_id} --output json"
                ],
                "files_in_scope": [
                    helper_relative_path.as_posix(),
                    "eval/history",
                    "status/work-state.json",
                    "status/readiness.json",
                ],
                "dependencies": [previous_task_id],
                "blocked_by": [],
                "escalation_conditions": [
                    "The checkpoint helper cannot read canonical state or write bounded evidence under eval/history.",
                ],
                "completion_signals": [
                    "A checkpoint-result.json artifact is recorded under eval/history.",
                    "Canonical work-state advances to the next task through the existing continuity workflow.",
                ],
            }
        )
        previous_task_id = task_id

    benchmark_task = json.loads(json.dumps(benchmark_task))
    benchmark_task["dependencies"] = [previous_task_id]

    new_tasks = [json.loads(json.dumps(validation_task)), *extra_tasks, benchmark_task]
    backlog["generated_at"] = isoformat_z(read_now())
    backlog["tasks"] = new_tasks
    write_json(backlog_path, backlog)

    work_state["pending_task_ids"] = [*extra_task_ids, "run_inherited_benchmarks"]
    work_state["last_agent_action"] = "Extended the starter backlog with bounded continuity checkpoint tasks for longer-backlog autonomy stress testing."
    resume_instructions = list(work_state.get("resume_instructions", []))
    longer_backlog_note = "Treat bounded checkpoint tasks as normal canonical starter tasks; they exist to stress continuity depth without widening scope."
    if longer_backlog_note not in resume_instructions:
        resume_instructions.append(longer_backlog_note)
    work_state["resume_instructions"] = resume_instructions
    write_json(work_state_path, work_state)

    completion_definition = list(project_objective.get("completion_definition", []))
    longer_backlog_definition = "The longer-backlog proving-ground tasks may add bounded checkpoint tasks before the final inherited benchmark task."
    if longer_backlog_definition not in completion_definition:
        completion_definition.append(longer_backlog_definition)
    project_objective["completion_definition"] = completion_definition
    write_json(project_objective_path, project_objective)

    return {
        "status": "completed",
        "helper_script_path": str(helper_path),
        "extra_task_ids": extra_task_ids,
        "final_task_count": len(new_tasks),
        "benchmark_dependencies": benchmark_task["dependencies"],
    }


def run_longer_backlog_autonomy_exercise(
    *,
    factory_root: Path,
    source_template_id: str,
    target_build_pack_id: str,
    target_display_name: str,
    target_version: str,
    target_revision: str,
    remote_target_label: str,
    remote_host: str,
    remote_user: str,
    actor: str,
    extra_task_count: int,
) -> dict[str, Any]:
    exercise_id = _exercise_id(target_build_pack_id)
    exercise_root = _exercise_root(factory_root, exercise_id)
    exercise_root.mkdir(parents=True, exist_ok=False)

    materialization_request = _materialization_request(
        source_template_id=source_template_id,
        target_build_pack_id=target_build_pack_id,
        target_display_name=target_display_name,
        target_version=target_version,
        target_revision=target_revision,
        actor=actor,
    )
    materialization_request_path = exercise_root / "materialization-request.json"
    write_json(materialization_request_path, materialization_request)
    materialization_result = materialize_build_pack(factory_root, materialization_request)

    pack_root = factory_root / "build-packs" / target_build_pack_id
    extension_result = _extend_to_longer_backlog(pack_root=pack_root, extra_task_count=extra_task_count)

    checkpoint_run_id = f"{target_build_pack_id}-longer-backlog-checkpoint-v1"
    checkpoint_result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        run_id=checkpoint_run_id,
    )

    remote_hops: list[dict[str, Any]] = []
    reconcile_results: list[dict[str, Any]] = []
    max_remote_hops = extra_task_count + 2
    for hop_number in range(1, max_remote_hops + 1):
        state = _final_state(pack_root)
        if bool(cast(dict[str, Any], state["readiness"]).get("ready_for_deployment")):
            break

        hop_result = run_remote_active_task_continuity_test(
            factory_root=factory_root,
            build_pack_id=target_build_pack_id,
            remote_target_label=remote_target_label,
            remote_host=remote_host,
            remote_user=remote_user,
            staged_by=actor,
            imported_by=actor,
            run_id=None,
        )
        remote_hops.append(hop_result)

        roundtrip = cast(dict[str, Any], hop_result["roundtrip_result"])
        reconcile_request = _reconcile_request(
            build_pack_id=target_build_pack_id,
            import_report_path=str(roundtrip["import_report_path"]),
            actor=actor,
            hop_number=hop_number,
        )
        reconcile_request_path = exercise_root / f"reconcile-request-hop-{hop_number}.json"
        write_json(reconcile_request_path, reconcile_request)
        reconcile_result = reconcile_imported_runtime_state(
            factory_root,
            reconcile_request,
            request_file_dir=reconcile_request_path.parent.resolve(),
        )
        reconcile_results.append(reconcile_result)
    else:
        raise ValueError("longer-backlog exercise exceeded the maximum expected remote hops without reaching ready_for_deployment")

    ready_boundary_result = run_remote_memory_continuity_test(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        remote_target_label=remote_target_label,
        remote_host=remote_host,
        remote_user=remote_user,
        staged_by=actor,
        imported_by=actor,
        run_id=None,
    )

    final_state = _final_state(pack_root)
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "exercise_id": exercise_id,
        "generated_at": isoformat_z(read_now()),
        "status": "completed",
        "source_template_id": source_template_id,
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(pack_root),
        "remote_target_label": remote_target_label,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "extra_task_count": extra_task_count,
        "materialization_result": materialization_result,
        "extension_result": extension_result,
        "checkpoint_result": checkpoint_result,
        "remote_hops": remote_hops,
        "reconcile_results": reconcile_results,
        "ready_boundary_continuity_result": ready_boundary_result,
        "final_state": final_state,
    }
    report_path = exercise_root / "exercise-report.json"
    write_json(report_path, report)
    errors = validate_json_document(report_path, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "exercise_id": exercise_id,
        "report_path": str(report_path),
        "target_build_pack_id": target_build_pack_id,
        "final_task_count": int(extension_result["final_task_count"]),
        "remote_hop_count": len(remote_hops),
        "final_ready_for_deployment": cast(dict[str, Any], final_state["readiness"]).get("ready_for_deployment"),
        "latest_memory_run_id": cast(dict[str, Any], final_state["latest_memory"]).get("selected_run_id"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a longer-backlog autonomy stress exercise on a fresh build-pack.",
    )
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="longer-backlog-autonomy-v1")
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--extra-task-count", type=int, default=2)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_longer_backlog_autonomy_exercise(
        factory_root=resolve_factory_root(args.factory_root),
        source_template_id=args.source_template_id,
        target_build_pack_id=args.target_build_pack_id,
        target_display_name=args.target_display_name,
        target_version=args.target_version,
        target_revision=args.target_revision,
        remote_target_label=args.remote_target_label,
        remote_host=args.remote_host,
        remote_user=args.remote_user,
        actor=args.actor,
        extra_task_count=args.extra_task_count,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
