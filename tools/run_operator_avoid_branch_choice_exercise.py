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
from factory_ops import isoformat_z, read_now, resolve_factory_root, schema_path, timestamp_token, validate_json_document, write_json
from run_operator_hint_branch_choice_exercise import (
    _configure_operator_hint_branch_backlog,
    _final_state,
    _load_object,
    _materialization_request,
    _reconcile_request,
)
from materialize_build_pack import materialize_build_pack
from reconcile_imported_runtime_state import reconcile_imported_runtime_state
from run_local_mid_backlog_checkpoint import run_local_mid_backlog_checkpoint
from run_remote_active_task_continuity_test import run_remote_active_task_continuity_test
from run_remote_memory_continuity_test import run_remote_memory_continuity_test


REPORT_SCHEMA_NAME = "operator-avoid-branch-choice-exercise-report.schema.json"
REPORT_SCHEMA_VERSION = "operator-avoid-branch-choice-exercise-report/v1"
EXERCISE_PREFIX = "operator-avoid-branch-choice-exercise"


def _exercise_id(target_build_pack_id: str) -> str:
    return f"{EXERCISE_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _exercise_root(factory_root: Path, exercise_id: str) -> Path:
    return factory_root / ".pack-state" / "operator-avoid-branch-choice-exercises" / exercise_id


def run_operator_avoid_branch_choice_exercise(
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
    operator_hint_branch_setup_result = _configure_operator_hint_branch_backlog(pack_root=pack_root)
    hinted_away_task_id = str(operator_hint_branch_setup_result["expected_semantic_default_task_id"])
    expected_task_id = str(operator_hint_branch_setup_result["expected_hint_override_task_id"])
    hint_application_result = apply_branch_selection_hint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        hint_id="avoid_schema_validation_refinement",
        summary="Avoid the schema-validation refinement branch for this proving-ground run and let the remaining branch continue.",
        preferred_task_ids=[],
        avoid_task_ids=[hinted_away_task_id],
        active=True,
    )

    checkpoint_run_id = f"{target_build_pack_id}-operator-avoid-branch-checkpoint-v1"
    checkpoint_result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        run_id=checkpoint_run_id,
    )
    branch_selection_path = pack_root / ".pack-state" / "autonomy-runs" / checkpoint_run_id / "branch-selection.json"
    initial_branch_selection = _load_object(branch_selection_path)
    if initial_branch_selection.get("selection_method") != "operator_hint":
        raise ValueError("operator-avoid branch exercise expected selection_method=operator_hint")
    if initial_branch_selection.get("chosen_task_id") != expected_task_id:
        raise ValueError("operator-avoid branch exercise did not choose the expected remaining task")
    if hinted_away_task_id not in cast(list[str], initial_branch_selection.get("filtered_out_task_ids", [])):
        raise ValueError("operator-avoid branch exercise expected the avoided task to appear in filtered_out_task_ids")

    remote_hops: list[dict[str, Any]] = []
    reconcile_results: list[dict[str, Any]] = []
    for hop_number in range(1, 5):
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
        raise ValueError("operator-avoid branch exercise expected at least one remote hop")

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
        "operator_hint_branch_setup_result": operator_hint_branch_setup_result,
        "hint_application_result": hint_application_result,
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
        "final_ready_for_deployment": cast(dict[str, Any], final_state["readiness"]).get("ready_for_deployment"),
        "latest_memory_run_id": cast(dict[str, Any], final_state["latest_memory"]).get("selected_run_id"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an operator-avoid branch-choice autonomy exercise on a fresh build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="operator-avoid-branch-choice-v1")
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_operator_avoid_branch_choice_exercise(
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
