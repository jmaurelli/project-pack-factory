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
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)
from materialize_build_pack import materialize_build_pack
from run_local_mid_backlog_checkpoint import run_local_mid_backlog_checkpoint


REPORT_SCHEMA_NAME = "ambiguous-branch-autonomy-exercise-report.schema.json"
REPORT_SCHEMA_VERSION = "ambiguous-branch-autonomy-exercise-report/v1"
EXERCISE_PREFIX = "ambiguous-branch-autonomy-exercise"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _exercise_id(target_build_pack_id: str) -> str:
    return f"{EXERCISE_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _exercise_root(factory_root: Path, exercise_id: str) -> Path:
    return factory_root / ".pack-state" / "ambiguous-branch-autonomy-exercises" / exercise_id


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
        "materialization_reason": "Create a fresh proving-ground build-pack for PackFactory ambiguous-branch autonomy testing.",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a bounded ambiguous-branch checkpoint artifact.")
    parser.add_argument("--pack-root", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--branch-lane", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args()

    pack_root = Path(args.pack_root).resolve()
    timestamp = now()
    artifact_dir = pack_root / "eval" / "history" / f"{args.task_id}-{timestamp.replace(':', '').replace('-', '').lower()}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = artifact_dir / "ambiguous-branch-checkpoint-result.json"
    artifact_payload = {
        "schema_version": "ambiguous-branch-checkpoint-result/v1",
        "generated_at": timestamp,
        "task_id": args.task_id,
        "branch_lane": args.branch_lane,
        "summary": "Recorded a bounded ambiguous-branch checkpoint artifact.",
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


def _configure_ambiguous_branch_backlog(*, pack_root: Path) -> dict[str, Any]:
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

    helper_relative_path = Path("src/record_ambiguous_branch_progress.py")
    helper_path = pack_root / helper_relative_path
    helper_path.write_text(_helper_script_text(), encoding="utf-8")

    branch_alpha_id = "record_ambiguous_branch_alpha"
    branch_beta_id = "record_ambiguous_branch_beta"
    common_fields = {
        "status": "pending",
        "objective_link": backlog.get("objective_id"),
        "acceptance_criteria": [
            "The helper exits successfully for the selected branch.",
            "A bounded ambiguous-branch checkpoint artifact is written under eval/history.",
        ],
        "files_in_scope": [
            helper_relative_path.as_posix(),
            "eval/history",
            "status/work-state.json",
            "status/readiness.json",
        ],
        "dependencies": ["run_build_pack_validation"],
        "blocked_by": [],
        "escalation_conditions": [
            "Operator disambiguation is required if multiple next tasks remain equally eligible.",
        ],
    }
    branch_alpha = {
        "task_id": branch_alpha_id,
        "summary": "Record ambiguous branch-alpha checkpoint evidence after validation passes.",
        **common_fields,
        "completion_signals": [
            "A bounded checkpoint artifact is recorded under eval/history for ambiguous branch alpha.",
        ],
        "validation_commands": [
            f"python3 {helper_relative_path.as_posix()} --pack-root . --task-id {branch_alpha_id} --branch-lane alpha --output json"
        ],
    }
    branch_beta = {
        "task_id": branch_beta_id,
        "summary": "Record ambiguous branch-beta checkpoint evidence after validation passes.",
        **common_fields,
        "completion_signals": [
            "A bounded checkpoint artifact is recorded under eval/history for ambiguous branch beta.",
        ],
        "validation_commands": [
            f"python3 {helper_relative_path.as_posix()} --pack-root . --task-id {branch_beta_id} --branch-lane beta --output json"
        ],
    }

    benchmark_task = json.loads(json.dumps(benchmark_task))
    benchmark_task["dependencies"] = [branch_alpha_id, branch_beta_id]

    backlog["generated_at"] = isoformat_z(read_now())
    backlog["tasks"] = [json.loads(json.dumps(validation_task)), branch_alpha, branch_beta, benchmark_task]
    write_json(backlog_path, backlog)

    work_state["pending_task_ids"] = [branch_alpha_id, branch_beta_id, "run_inherited_benchmarks"]
    work_state["last_agent_action"] = "Configured an ambiguous branching starter backlog with two equally eligible post-validation tasks and no disambiguating selection_priority metadata."
    resume_instructions = list(work_state.get("resume_instructions", []))
    ambiguity_note = "If multiple next tasks share the same highest precedence, stop fail-closed and request operator disambiguation instead of choosing by backlog order."
    if ambiguity_note not in resume_instructions:
        resume_instructions.append(ambiguity_note)
    work_state["resume_instructions"] = resume_instructions
    write_json(work_state_path, work_state)

    completion_definition = list(project_objective.get("completion_definition", []))
    ambiguity_definition = "The ambiguous branching proving ground should stop fail-closed when multiple post-validation tasks are equally eligible and no disambiguating selection_priority is present."
    if ambiguity_definition not in completion_definition:
        completion_definition.append(ambiguity_definition)
    project_objective["completion_definition"] = completion_definition
    write_json(project_objective_path, project_objective)

    return {
        "status": "completed",
        "helper_script_path": str(helper_path),
        "branch_task_ids": [branch_alpha_id, branch_beta_id],
        "branch_order_in_backlog": [branch_alpha_id, branch_beta_id],
        "branch_selection_priority": {
            branch_alpha_id: None,
            branch_beta_id: None,
        },
        "expected_blocked_task_ids": [branch_alpha_id, branch_beta_id],
        "benchmark_dependencies": [branch_alpha_id, branch_beta_id],
    }


def _final_state(pack_root: Path) -> dict[str, Any]:
    return {
        "readiness": _load_object(pack_root / "status/readiness.json"),
        "work_state": _load_object(pack_root / "status/work-state.json"),
        "task_backlog": _load_object(pack_root / "tasks/active-backlog.json"),
        "latest_memory": _load_object(pack_root / ".pack-state/agent-memory/latest-memory.json"),
    }


def run_ambiguous_branch_autonomy_exercise(
    *,
    factory_root: Path,
    source_template_id: str,
    target_build_pack_id: str,
    target_display_name: str,
    target_version: str,
    target_revision: str,
    actor: str,
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
    ambiguous_branch_setup_result = _configure_ambiguous_branch_backlog(pack_root=pack_root)
    checkpoint_run_id = f"{target_build_pack_id}-ambiguous-branch-checkpoint-v1"
    checkpoint_result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        run_id=checkpoint_run_id,
    )
    run_summary = _load_object(pack_root / ".pack-state" / "autonomy-runs" / checkpoint_run_id / "run-summary.json")
    final_state = _final_state(pack_root)
    if checkpoint_result.get("status") != "blocked":
        raise ValueError("ambiguous branch exercise expected the checkpoint to stop with status `blocked`")
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "exercise_id": exercise_id,
        "generated_at": isoformat_z(read_now()),
        "status": "completed",
        "source_template_id": source_template_id,
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(pack_root),
        "materialization_result": materialization_result,
        "ambiguous_branch_setup_result": ambiguous_branch_setup_result,
        "checkpoint_result": checkpoint_result,
        "run_summary": run_summary,
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
        "checkpoint_status": checkpoint_result.get("status"),
        "stop_reason": run_summary.get("stop_reason"),
        "blocked_task_ids": cast(dict[str, Any], final_state["work_state"]).get("blocked_task_ids"),
        "latest_memory_run_id": cast(dict[str, Any], final_state["latest_memory"]).get("selected_run_id"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an ambiguous-branch autonomy exercise on a fresh build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="ambiguous-branch-autonomy-v1")
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_ambiguous_branch_autonomy_exercise(
        factory_root=resolve_factory_root(args.factory_root),
        source_template_id=args.source_template_id,
        target_build_pack_id=args.target_build_pack_id,
        target_display_name=args.target_display_name,
        target_version=args.target_version,
        target_revision=args.target_revision,
        actor=args.actor,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
