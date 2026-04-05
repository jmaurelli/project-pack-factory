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
from import_external_runtime_evidence import import_external_runtime_evidence
from materialize_build_pack import materialize_build_pack
from remote_autonomy_roundtrip_common import canonical_local_bundle_staging_dir
from run_local_active_task_continuity import run_local_active_task_continuity
from run_local_mid_backlog_checkpoint import run_local_mid_backlog_checkpoint
from run_remote_active_task_continuity_test import (
    RUN_REQUEST_SCHEMA_NAME,
    RUN_REQUEST_SCHEMA_VERSION,
    TEST_REQUEST_SCHEMA_NAME,
    TEST_REQUEST_SCHEMA_VERSION,
    _build_run_request,
    _next_run_id,
    _request_root,
    _run_roundtrip_with_seeded_validation_artifacts,
    _write_validated,
)
from run_remote_memory_continuity_test import run_remote_memory_continuity_test
from remote_autonomy_staging_common import resolve_local_scratch_root


REPORT_SCHEMA_NAME = "degraded-connectivity-autonomy-exercise-report.schema.json"
REPORT_SCHEMA_VERSION = "degraded-connectivity-autonomy-exercise-report/v1"
EXERCISE_PREFIX = "degraded-connectivity-autonomy-exercise"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _exercise_id(target_build_pack_id: str) -> str:
    return f"{EXERCISE_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _exercise_root(factory_root: Path, exercise_id: str) -> Path:
    return factory_root / ".pack-state" / "degraded-connectivity-autonomy-exercises" / exercise_id


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
        "materialization_reason": "Create a fresh proving-ground build-pack for PackFactory degraded-connectivity autonomy testing.",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
    }


def _final_state(pack_root: Path) -> dict[str, Any]:
    return {
        "readiness": _load_object(pack_root / "status/readiness.json"),
        "work_state": _load_object(pack_root / "status/work-state.json"),
        "latest_memory": _load_object(pack_root / ".pack-state/agent-memory/latest-memory.json"),
    }


def _build_remote_only_test_request(
    *,
    factory_root: Path,
    remote_target_label: str,
    build_pack_id: str,
    run_id: str,
    remote_run_request_path: Path,
    actor: str,
    local_scratch_root: Path,
) -> dict[str, Any]:
    return {
        "schema_version": TEST_REQUEST_SCHEMA_VERSION,
        "remote_run_request_path": str(remote_run_request_path),
        "local_bundle_staging_dir": str(
            canonical_local_bundle_staging_dir(
                factory_root=factory_root,
                remote_target_label=remote_target_label,
                build_pack_id=build_pack_id,
                run_id=run_id,
                local_scratch_root=local_scratch_root,
            )
        ),
        "local_scratch_root": str(local_scratch_root),
        "pull_bundle": True,
        "import_bundle": False,
        "imported_by": actor,
        "import_reason": "Delayed import after degraded-connectivity simulation.",
        "test_reason": "Remote active-task continuity run with delayed import to simulate disconnected factory recovery.",
    }


def _run_remote_only_roundtrip(
    *,
    factory_root: Path,
    build_pack_id: str,
    remote_target_label: str,
    remote_host: str,
    remote_user: str,
    actor: str,
) -> dict[str, Any]:
    pack_root = factory_root / "build-packs" / build_pack_id
    local_scratch_root = resolve_local_scratch_root(factory_root)
    resolved_run_id = _next_run_id(factory_root, remote_target_label, build_pack_id).replace(
        "active-task-continuity-run", "degraded-connectivity-remote-run"
    )
    request_root = _request_root(factory_root, remote_target_label, build_pack_id, resolved_run_id)
    request_root.mkdir(parents=True, exist_ok=True)
    run_request_path = request_root / "remote-run-request.json"
    test_request_path = request_root / "remote-test-request.json"

    run_request = _build_run_request(
        factory_root=factory_root,
        pack_root=pack_root,
        pack_id=build_pack_id,
        run_id=resolved_run_id,
        active_task_id="run_inherited_benchmarks",
        remote_target_label=remote_target_label,
        remote_host=remote_host,
        remote_user=remote_user,
        staged_by=actor,
    )
    run_request["schema_version"] = RUN_REQUEST_SCHEMA_VERSION
    run_request["remote_reason"] = "Remote active-task continuity run with delayed import to simulate degraded factory connectivity."
    test_request = _build_remote_only_test_request(
        factory_root=factory_root,
        remote_target_label=remote_target_label,
        build_pack_id=build_pack_id,
        run_id=resolved_run_id,
        remote_run_request_path=run_request_path,
        actor=actor,
    )
    _write_validated(factory_root, run_request_path, run_request, RUN_REQUEST_SCHEMA_NAME)
    _write_validated(factory_root, test_request_path, test_request, TEST_REQUEST_SCHEMA_NAME)
    result = _run_roundtrip_with_seeded_validation_artifacts(
        factory_root=factory_root,
        test_request_path=test_request_path,
    )
    return {
        "status": "completed",
        "run_id": resolved_run_id,
        "request_root": str(request_root),
        "remote_run_request_path": str(run_request_path),
        "remote_test_request_path": str(test_request_path),
        "roundtrip_result": result,
    }


def _delayed_import(
    *,
    factory_root: Path,
    build_pack_id: str,
    bundle_manifest_path: Path,
    actor: str,
    request_root: Path,
) -> dict[str, Any]:
    import_request_payload = {
        "schema_version": "external-runtime-evidence-import-request/v1",
        "build_pack_id": build_pack_id,
        "bundle_manifest_path": str(bundle_manifest_path),
        "import_reason": "Delayed import after local disconnected progress and later factory reconnection.",
        "imported_by": actor,
    }
    import_request_path = request_root / "delayed-import-request.json"
    write_json(import_request_path, import_request_payload)
    return import_external_runtime_evidence(
        factory_root,
        import_request_payload,
        request_file_dir=import_request_path.parent.resolve(),
    )


def run_degraded_connectivity_autonomy_exercise(
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

    checkpoint_result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        run_id=f"{target_build_pack_id}-degraded-connectivity-checkpoint-v1",
    )

    remote_only_roundtrip_result = _run_remote_only_roundtrip(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        remote_target_label=remote_target_label,
        remote_host=remote_host,
        remote_user=remote_user,
        actor=actor,
        local_scratch_root=local_scratch_root,
    )

    local_disconnected_result = run_local_active_task_continuity(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        run_id=f"{target_build_pack_id}-local-disconnected-continuity-v1",
    )

    roundtrip = cast(dict[str, Any], remote_only_roundtrip_result["roundtrip_result"])
    pulled_bundle_root = Path(str(roundtrip["pull_result"]["local_bundle_root"]))
    delayed_import_result = _delayed_import(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        bundle_manifest_path=pulled_bundle_root / "bundle.json",
        actor=actor,
        request_root=exercise_root,
    )

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

    pack_root = factory_root / "build-packs" / target_build_pack_id
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
        "checkpoint_result": checkpoint_result,
        "remote_only_roundtrip_result": remote_only_roundtrip_result,
        "local_disconnected_result": local_disconnected_result,
        "delayed_import_result": delayed_import_result,
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
        "delayed_import_memory_status": cast(dict[str, Any], delayed_import_result["memory_intake"]).get("status"),
        "final_ready_for_deployment": cast(dict[str, Any], final_state["readiness"]).get("ready_for_deployment"),
        "latest_memory_run_id": cast(dict[str, Any], final_state["latest_memory"]).get("selected_run_id"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a degraded-connectivity autonomy stress exercise on a fresh build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="degraded-connectivity-autonomy-v1")
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_degraded_connectivity_autonomy_exercise(
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
