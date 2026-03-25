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
from run_local_active_task_continuity import run_local_active_task_continuity
from run_local_mid_backlog_checkpoint import run_local_mid_backlog_checkpoint


REPORT_SCHEMA_NAME = "ordered-hint-lifecycle-exercise-report.schema.json"
REPORT_SCHEMA_VERSION = "ordered-hint-lifecycle-exercise-report/v1"
EXERCISE_PREFIX = "ordered-hint-lifecycle-exercise"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _exercise_id(target_build_pack_id: str) -> str:
    return f"{EXERCISE_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _exercise_root(factory_root: Path, exercise_id: str) -> Path:
    return factory_root / ".pack-state" / "ordered-hint-lifecycle-exercises" / exercise_id


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
        "materialization_reason": "Create a fresh proving-ground build-pack for PackFactory ordered-preference and hint-lifecycle testing.",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
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
    parser = argparse.ArgumentParser(description="Record a bounded ordered-hint lifecycle checkpoint artifact.")
    parser.add_argument("--pack-root", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--lane", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args()

    pack_root = Path(args.pack_root).resolve()
    timestamp = now()
    artifact_dir = pack_root / "eval" / "history" / f"{args.task_id}-{timestamp.replace(':', '').replace('-', '').lower()}"
    artifact_dir.mkdir(parents=True, exist_ok=False)
    artifact_path = artifact_dir / "ordered-hint-lifecycle-checkpoint-result.json"
    artifact_payload = {
        "schema_version": "ordered-hint-lifecycle-checkpoint-result/v1",
        "generated_at": timestamp,
        "task_id": args.task_id,
        "lane": args.lane,
        "summary": "Recorded a bounded ordered-hint lifecycle checkpoint artifact without mutating canonical readiness state.",
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


def _checkpoint_task(
    *,
    objective_id: str | None,
    helper_relative_path: Path,
    task_id: str,
    summary: str,
    lane: str,
    dependencies: list[str],
    selection_signals: list[str],
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "summary": summary,
        "status": "pending",
        "objective_link": objective_id,
        "selection_signals": selection_signals,
        "acceptance_criteria": [
            f"The ordered hint lifecycle helper exits successfully for lane {lane}.",
            "A checkpoint artifact is written under eval/history.",
        ],
        "validation_commands": [
            f"python3 {helper_relative_path.as_posix()} --pack-root . --task-id {task_id} --lane {lane} --output json"
        ],
        "files_in_scope": [
            helper_relative_path.as_posix(),
            "eval/history",
            "status/work-state.json",
            "status/readiness.json",
        ],
        "dependencies": dependencies,
        "blocked_by": [],
        "escalation_conditions": [
            "The helper cannot read canonical state or write bounded evidence under eval/history.",
        ],
        "completion_signals": [
            f"An ordered-hint-lifecycle-checkpoint-result.json artifact is recorded under eval/history for lane {lane}.",
            f"Canonical work-state advances after the {lane} checkpoint completes.",
        ],
    }


def _configure_ordered_hint_backlog(*, pack_root: Path) -> dict[str, Any]:
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

    helper_relative_path = Path("src/record_ordered_hint_lifecycle_progress.py")
    helper_path = pack_root / helper_relative_path
    helper_path.write_text(_helper_script_text(), encoding="utf-8")

    first_alpha_id = "record_ordered_first_alpha"
    first_beta_id = "record_ordered_first_beta"
    second_gamma_id = "record_ordered_second_gamma"
    second_delta_id = "record_ordered_second_delta"

    first_alpha = _checkpoint_task(
        objective_id=cast(str | None, backlog.get("objective_id")),
        helper_relative_path=helper_relative_path,
        task_id=first_alpha_id,
        summary="Record operator-reporting refinement checkpoint evidence after validation passes.",
        lane="first-alpha",
        dependencies=["run_build_pack_validation"],
        selection_signals=["operator", "reporting", "html", "narrative"],
    )
    first_beta = _checkpoint_task(
        objective_id=cast(str | None, backlog.get("objective_id")),
        helper_relative_path=helper_relative_path,
        task_id=first_beta_id,
        summary="Record schema-validation refinement checkpoint evidence after validation passes.",
        lane="first-beta",
        dependencies=["run_build_pack_validation"],
        selection_signals=["schema", "validation", "json", "integrity"],
    )
    second_gamma = _checkpoint_task(
        objective_id=cast(str | None, backlog.get("objective_id")),
        helper_relative_path=helper_relative_path,
        task_id=second_gamma_id,
        summary="Record semantic follow-up checkpoint evidence after both first-branch tasks complete.",
        lane="second-gamma",
        dependencies=[first_alpha_id, first_beta_id],
        selection_signals=["semantic", "schema", "validation", "follow-up"],
    )
    second_delta = _checkpoint_task(
        objective_id=cast(str | None, backlog.get("objective_id")),
        helper_relative_path=helper_relative_path,
        task_id=second_delta_id,
        summary="Record auxiliary follow-up checkpoint evidence after both first-branch tasks complete.",
        lane="second-delta",
        dependencies=[first_alpha_id, first_beta_id],
        selection_signals=["auxiliary", "inventory", "follow-up", "secondary"],
    )

    benchmark_task = json.loads(json.dumps(benchmark_task))
    benchmark_task["dependencies"] = [second_gamma_id, second_delta_id]

    backlog["generated_at"] = isoformat_z(read_now())
    backlog["tasks"] = [
        json.loads(json.dumps(validation_task)),
        first_alpha,
        first_beta,
        second_gamma,
        second_delta,
        benchmark_task,
    ]
    write_json(backlog_path, backlog)

    work_state["pending_task_ids"] = [
        first_alpha_id,
        first_beta_id,
        second_gamma_id,
        second_delta_id,
        "run_inherited_benchmarks",
    ]
    work_state["last_agent_action"] = "Configured an ordered-preference and hint-lifecycle starter backlog with one initial tied pair and one later tied pair."
    resume_instructions = list(work_state.get("resume_instructions", []))
    semantic_note = "After the ordered one-shot hint is consumed, semantic follow-up is the stronger fit than auxiliary follow-up for the second tied branch."
    if semantic_note not in resume_instructions:
        resume_instructions.append(semantic_note)
    work_state["resume_instructions"] = resume_instructions
    write_json(work_state_path, work_state)

    success_criteria = list(project_objective.get("success_criteria", []))
    success_note = "Once the one-shot reporting/schema hint is exhausted, semantic follow-up should outrank auxiliary follow-up through bounded semantic alignment."
    if success_note not in success_criteria:
        success_criteria.append(success_note)
    project_objective["success_criteria"] = success_criteria
    write_json(project_objective_path, project_objective)

    return {
        "status": "completed",
        "helper_script_path": str(helper_path),
        "first_branch_task_ids": [first_alpha_id, first_beta_id],
        "second_branch_task_ids": [second_gamma_id, second_delta_id],
        "expected_first_choice_task_id": first_beta_id,
        "expected_second_semantic_choice_task_id": second_gamma_id,
    }


def _first_hint_state(pack_root: Path, hint_id: str) -> dict[str, Any]:
    work_state = _load_object(pack_root / "status/work-state.json")
    hints = work_state.get("branch_selection_hints", [])
    if not isinstance(hints, list):
        raise ValueError("expected branch_selection_hints to be present after ordered hint application")
    for hint in hints:
        if isinstance(hint, dict) and hint.get("hint_id") == hint_id:
            return cast(dict[str, Any], hint)
    raise ValueError(f"expected hint `{hint_id}` to be present in work-state")


def run_ordered_hint_lifecycle_exercise(
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
    ordered_hint_setup_result = _configure_ordered_hint_backlog(pack_root=pack_root)

    first_hint_id = "prefer_schema_then_reporting_once"
    hint_application_result = apply_branch_selection_hint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        hint_id=first_hint_id,
        summary="Prefer schema refinement first, fall back to reporting refinement second, and only apply this guidance once.",
        preferred_task_ids=[
            str(ordered_hint_setup_result["expected_first_choice_task_id"]),
            str(cast(list[str], ordered_hint_setup_result["first_branch_task_ids"])[0]),
        ],
        avoid_task_ids=[],
        remaining_applications=1,
        active=True,
    )

    first_checkpoint_run_id = f"{target_build_pack_id}-ordered-hint-checkpoint-v1"
    first_checkpoint_result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        run_id=first_checkpoint_run_id,
    )
    first_branch_selection = _load_object(
        pack_root / ".pack-state" / "autonomy-runs" / first_checkpoint_run_id / "branch-selection.json"
    )
    if first_branch_selection.get("selection_method") != "operator_hint":
        raise ValueError("ordered hint lifecycle exercise expected selection_method=operator_hint on the first branch")
    if first_branch_selection.get("chosen_task_id") != ordered_hint_setup_result["expected_first_choice_task_id"]:
        raise ValueError("ordered hint lifecycle exercise did not choose the first-ranked ordered preference")
    if first_hint_id not in cast(list[str], first_branch_selection.get("consumed_hint_ids", [])):
        raise ValueError("ordered hint lifecycle exercise expected the one-shot hint to be consumed")
    if first_hint_id not in cast(list[str], first_branch_selection.get("deactivated_hint_ids", [])):
        raise ValueError("ordered hint lifecycle exercise expected the one-shot hint to deactivate after first use")

    post_first_hint_state = _first_hint_state(pack_root, first_hint_id)
    if post_first_hint_state.get("active") is not False or post_first_hint_state.get("remaining_applications") != 0:
        raise ValueError("ordered hint lifecycle exercise expected the one-shot hint to become inactive with 0 remaining_applications")

    continuation_results: list[dict[str, Any]] = []
    semantic_branch_selection: dict[str, Any] | None = None
    for hop_number in range(1, 8):
        readiness = _load_object(pack_root / "status/readiness.json")
        if bool(readiness.get("ready_for_deployment")):
            break
        run_id = f"{target_build_pack_id}-ordered-hint-continuity-v{hop_number}"
        result = run_local_active_task_continuity(
            factory_root=factory_root,
            build_pack_id=target_build_pack_id,
            run_id=run_id,
        )
        continuation_results.append(result)
        branch_selection_path = pack_root / ".pack-state" / "autonomy-runs" / run_id / "branch-selection.json"
        if branch_selection_path.exists():
            candidate = _load_object(branch_selection_path)
            if candidate.get("selection_method") == "semantic_alignment" and semantic_branch_selection is None:
                semantic_branch_selection = candidate

    final_state = _final_state(pack_root)
    if not bool(cast(dict[str, Any], final_state["readiness"]).get("ready_for_deployment")):
        raise ValueError("ordered hint lifecycle exercise expected the pack to reach ready_for_deploy")
    if semantic_branch_selection is None:
        raise ValueError("ordered hint lifecycle exercise expected a later semantic branch-selection proof after the one-shot hint expired")
    if semantic_branch_selection.get("chosen_task_id") != ordered_hint_setup_result["expected_second_semantic_choice_task_id"]:
        raise ValueError("ordered hint lifecycle exercise did not choose the expected semantic follow-up task")
    if cast(list[str], semantic_branch_selection.get("applied_hint_ids", [])):
        raise ValueError("ordered hint lifecycle exercise expected the later semantic branch decision to run without applied operator hints")

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "exercise_id": exercise_id,
        "generated_at": isoformat_z(read_now()),
        "status": "completed",
        "source_template_id": source_template_id,
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(pack_root),
        "materialization_result": materialization_result,
        "ordered_hint_setup_result": ordered_hint_setup_result,
        "hint_application_result": hint_application_result,
        "first_checkpoint_result": first_checkpoint_result,
        "first_branch_selection": first_branch_selection,
        "post_first_hint_state": post_first_hint_state,
        "continuation_results": continuation_results,
        "semantic_branch_selection": semantic_branch_selection,
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
        "first_choice_task_id": first_branch_selection.get("chosen_task_id"),
        "semantic_choice_task_id": semantic_branch_selection.get("chosen_task_id"),
        "hint_active_after_first_use": post_first_hint_state.get("active"),
        "remaining_applications_after_first_use": post_first_hint_state.get("remaining_applications"),
        "final_ready_for_deployment": cast(dict[str, Any], final_state["readiness"]).get("ready_for_deployment"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an ordered-preference and hint-lifecycle exercise on a fresh build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="ordered-hint-lifecycle-v1")
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_ordered_hint_lifecycle_exercise(
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
