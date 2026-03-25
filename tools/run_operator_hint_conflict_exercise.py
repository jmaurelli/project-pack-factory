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

from apply_branch_selection_hint import apply_branch_selection_hint
from factory_ops import isoformat_z, load_json, read_now, resolve_factory_root, schema_path, timestamp_token, validate_json_document, write_json
from materialize_build_pack import materialize_build_pack
from reconcile_imported_runtime_state import reconcile_imported_runtime_state
from run_local_mid_backlog_checkpoint import run_local_mid_backlog_checkpoint
from run_remote_active_task_continuity_test import run_remote_active_task_continuity_test
from run_remote_memory_continuity_test import run_remote_memory_continuity_test


REPORT_SCHEMA_NAME = "operator-hint-conflict-exercise-report.schema.json"
REPORT_SCHEMA_VERSION = "operator-hint-conflict-exercise-report/v1"
EXERCISE_PREFIX = "operator-hint-conflict-exercise"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _exercise_id(target_build_pack_id: str) -> str:
    return f"{EXERCISE_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _exercise_root(factory_root: Path, exercise_id: str) -> Path:
    return factory_root / ".pack-state" / "operator-hint-conflict-exercises" / exercise_id


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
        "materialization_reason": "Create a fresh proving-ground build-pack for PackFactory operator-hint conflict and precedence testing.",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
    }


def _reconcile_request(*, build_pack_id: str, import_report_path: str, actor: str, hop_number: int) -> dict[str, Any]:
    return {
        "schema_version": "imported-runtime-state-reconcile-request/v1",
        "build_pack_id": build_pack_id,
        "import_report_path": import_report_path,
        "reconcile_reason": f"Adopt the successful remote operator-hint conflict continuity result for hop {hop_number} into local canonical state.",
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a bounded operator-hint conflict checkpoint artifact.")
    parser.add_argument("--pack-root", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--branch-lane", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args()

    pack_root = Path(args.pack_root).resolve()
    timestamp = now()
    artifact_dir = pack_root / "eval" / "history" / f"{args.task_id}-{timestamp.replace(':', '').replace('-', '').lower()}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = artifact_dir / "operator-hint-conflict-checkpoint-result.json"
    artifact_payload = {
        "schema_version": "operator-hint-conflict-checkpoint-result/v1",
        "generated_at": timestamp,
        "task_id": args.task_id,
        "branch_lane": args.branch_lane,
        "summary": "Recorded a bounded operator-hint conflict checkpoint artifact without mutating canonical readiness state.",
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


def _configure_operator_hint_conflict_backlog(*, pack_root: Path) -> dict[str, Any]:
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

    helper_relative_path = Path("src/record_operator_hint_conflict_progress.py")
    helper_path = pack_root / helper_relative_path
    helper_path.write_text(_helper_script_text(), encoding="utf-8")

    branch_alpha_id = "record_conflict_branch_alpha"
    branch_beta_id = "record_conflict_branch_beta"
    branch_gamma_id = "record_conflict_branch_gamma"

    def branch_task(task_id: str, summary: str, lane: str, selection_signals: list[str]) -> dict[str, Any]:
        return {
            "task_id": task_id,
            "summary": summary,
            "status": "pending",
            "objective_link": backlog.get("objective_id"),
            "selection_signals": selection_signals,
            "acceptance_criteria": [
                f"The branch helper exits successfully for conflict branch {lane}.",
                "A branch checkpoint artifact is written under eval/history.",
            ],
            "validation_commands": [
                f"python3 {helper_relative_path.as_posix()} --pack-root . --task-id {task_id} --branch-lane {lane} --output json"
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
                "The branch helper cannot read canonical state or write bounded evidence under eval/history.",
            ],
            "completion_signals": [
                f"A operator-hint-conflict-checkpoint-result.json artifact is recorded under eval/history for branch {lane}.",
                f"Canonical work-state advances after the conflict branch {lane} checkpoint completes.",
            ],
        }

    branch_alpha = branch_task(
        branch_alpha_id,
        "Record operator-reporting refinement checkpoint evidence after validation passes.",
        "alpha",
        ["operator", "reporting", "html", "narrative"],
    )
    branch_beta = branch_task(
        branch_beta_id,
        "Record schema-validation refinement checkpoint evidence after validation passes.",
        "beta",
        ["json", "schema", "validation", "integrity"],
    )
    branch_gamma = branch_task(
        branch_gamma_id,
        "Record auxiliary inventory refinement checkpoint evidence after validation passes.",
        "gamma",
        ["inventory", "auxiliary", "catalog", "secondary"],
    )

    benchmark_task = json.loads(json.dumps(benchmark_task))
    benchmark_task["dependencies"] = [branch_alpha_id, branch_beta_id, branch_gamma_id]

    backlog["generated_at"] = isoformat_z(read_now())
    backlog["tasks"] = [json.loads(json.dumps(validation_task)), branch_alpha, branch_beta, branch_gamma, benchmark_task]
    write_json(backlog_path, backlog)

    work_state["pending_task_ids"] = [branch_alpha_id, branch_beta_id, branch_gamma_id, "run_inherited_benchmarks"]
    work_state["last_agent_action"] = "Configured an operator-hint conflict starter backlog with three equally eligible post-validation tasks and no explicit selection_priority."
    resume_instructions = list(work_state.get("resume_instructions", []))
    semantic_note = "If operator guidance filters out reporting refinement, schema-validation refinement is the stronger semantic fit than auxiliary inventory refinement."
    if semantic_note not in resume_instructions:
        resume_instructions.append(semantic_note)
    work_state["resume_instructions"] = resume_instructions
    write_json(work_state_path, work_state)

    success_criteria = list(project_objective.get("success_criteria", []))
    success_note = "When reporting refinement is ruled out, schema-validation refinement is the stronger semantic fit than auxiliary inventory refinement."
    if success_note not in success_criteria:
        success_criteria.append(success_note)
    project_objective["success_criteria"] = success_criteria
    write_json(project_objective_path, project_objective)

    return {
        "status": "completed",
        "helper_script_path": str(helper_path),
        "branch_task_ids": [branch_alpha_id, branch_beta_id, branch_gamma_id],
        "expected_preferred_task_id": branch_alpha_id,
        "expected_avoided_task_id": branch_alpha_id,
        "expected_semantic_winner_task_id": branch_beta_id,
        "secondary_semantic_candidate_task_id": branch_gamma_id,
    }


def run_operator_hint_conflict_exercise(
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
    operator_hint_conflict_setup_result = _configure_operator_hint_conflict_backlog(pack_root=pack_root)

    preferred_task_id = str(operator_hint_conflict_setup_result["expected_preferred_task_id"])
    expected_semantic_winner_task_id = str(operator_hint_conflict_setup_result["expected_semantic_winner_task_id"])
    hint_application_results = [
        apply_branch_selection_hint(
            factory_root=factory_root,
            build_pack_id=target_build_pack_id,
            hint_id="prefer_reporting_refinement",
            summary="Prefer the operator-reporting refinement branch if it remains eligible.",
            preferred_task_ids=[preferred_task_id],
            avoid_task_ids=[],
            active=True,
        ),
        apply_branch_selection_hint(
            factory_root=factory_root,
            build_pack_id=target_build_pack_id,
            hint_id="avoid_reporting_refinement",
            summary="Avoid the operator-reporting refinement branch so the remaining candidates must be resolved deterministically.",
            preferred_task_ids=[],
            avoid_task_ids=[preferred_task_id],
            active=True,
        ),
    ]

    checkpoint_run_id = f"{target_build_pack_id}-operator-hint-conflict-checkpoint-v1"
    checkpoint_result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        run_id=checkpoint_run_id,
    )
    branch_selection_path = pack_root / ".pack-state" / "autonomy-runs" / checkpoint_run_id / "branch-selection.json"
    initial_branch_selection = _load_object(branch_selection_path)
    if initial_branch_selection.get("selection_method") != "operator_hint_plus_semantic_alignment":
        raise ValueError("operator-hint conflict exercise expected selection_method=operator_hint_plus_semantic_alignment")
    if initial_branch_selection.get("chosen_task_id") != expected_semantic_winner_task_id:
        raise ValueError("operator-hint conflict exercise did not choose the expected semantic winner")
    if preferred_task_id not in cast(list[str], initial_branch_selection.get("filtered_out_task_ids", [])):
        raise ValueError("operator-hint conflict exercise expected the preferred-but-avoided task to appear in filtered_out_task_ids")

    remote_hops: list[dict[str, Any]] = []
    reconcile_results: list[dict[str, Any]] = []
    for hop_number in range(1, 6):
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
        reconcile_results.append(
            reconcile_imported_runtime_state(
                factory_root,
                reconcile_request,
                request_file_dir=exercise_root,
            )
        )
    if not remote_hops:
        raise ValueError("operator-hint conflict exercise expected at least one remote hop")

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
        "materialization_result": materialization_result,
        "operator_hint_conflict_setup_result": operator_hint_conflict_setup_result,
        "hint_application_results": hint_application_results,
        "checkpoint_result": checkpoint_result,
        "initial_branch_selection": initial_branch_selection,
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
        "selection_method": initial_branch_selection.get("selection_method"),
        "chosen_task_id": initial_branch_selection.get("chosen_task_id"),
        "filtered_out_task_ids": initial_branch_selection.get("filtered_out_task_ids"),
        "ignored_hint_ids": initial_branch_selection.get("ignored_hint_ids"),
        "final_ready_for_deployment": cast(dict[str, Any], final_state["readiness"]).get("ready_for_deployment"),
        "latest_memory_run_id": cast(dict[str, Any], final_state["latest_memory"]).get("selected_run_id"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an operator-hint conflict exercise on a fresh build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="operator-hint-conflict-v1")
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_operator_hint_conflict_exercise(
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
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
