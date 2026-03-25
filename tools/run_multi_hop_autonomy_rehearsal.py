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

from factory_ops import discover_pack, isoformat_z, load_json, read_now, resolve_factory_root, timestamp_token, write_json
from materialize_build_pack import materialize_build_pack
from reconcile_imported_runtime_state import reconcile_imported_runtime_state
from run_build_pack_readiness_eval import run_build_pack_readiness_eval
from run_local_mid_backlog_checkpoint import run_local_mid_backlog_checkpoint
from run_remote_active_task_continuity_test import run_remote_active_task_continuity_test
from run_remote_memory_continuity_test import run_remote_memory_continuity_test


REHEARSAL_PREFIX = "multi-hop-autonomy-rehearsal"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _rehearsal_id(target_build_pack_id: str) -> str:
    return f"{REHEARSAL_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _rehearsal_root(factory_root: Path, rehearsal_id: str) -> Path:
    return factory_root / ".pack-state" / "multi-hop-autonomy-rehearsals" / rehearsal_id


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
        "materialization_reason": "Create a fresh proving-ground build-pack for PackFactory multi-hop autonomy rehearsal.",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
    }


def _reconcile_request(*, build_pack_id: str, import_report_path: str, actor: str) -> dict[str, Any]:
    return {
        "schema_version": "imported-runtime-state-reconcile-request/v1",
        "build_pack_id": build_pack_id,
        "import_report_path": import_report_path,
        "reconcile_reason": "Adopt the successful remote active-task continuity result into local canonical state.",
        "reconciled_by": actor,
    }


def _final_state(pack_root: Path) -> dict[str, Any]:
    return {
        "readiness": _load_object(pack_root / "status/readiness.json"),
        "work_state": _load_object(pack_root / "status/work-state.json"),
        "latest_memory": _load_object(pack_root / ".pack-state/agent-memory/latest-memory.json"),
    }


def _refresh_canonical_readiness(*, pack_root: Path, rehearsal_id: str) -> dict[str, Any]:
    validation_result = run_build_pack_readiness_eval(
        pack_root=pack_root,
        mode="validation-only",
        invoked_by="multi-hop-autonomy-rehearsal",
        eval_run_id=f"{rehearsal_id}-validation-refresh",
    )
    benchmark_result = run_build_pack_readiness_eval(
        pack_root=pack_root,
        mode="benchmark-only",
        invoked_by="multi-hop-autonomy-rehearsal",
        eval_run_id=f"{rehearsal_id}-benchmark-refresh",
    )
    refreshed_state = _final_state(pack_root)
    return {
        "status": "completed",
        "validation_result": validation_result,
        "benchmark_result": benchmark_result,
        "post_refresh_readiness_state": refreshed_state["readiness"].get("readiness_state"),
        "post_refresh_ready_for_deployment": refreshed_state["readiness"].get("ready_for_deployment"),
        "post_refresh_latest_memory_run_id": refreshed_state["latest_memory"].get("selected_run_id"),
    }


def run_multi_hop_autonomy_rehearsal(
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
    rehearsal_id = _rehearsal_id(target_build_pack_id)
    rehearsal_root = _rehearsal_root(factory_root, rehearsal_id)
    rehearsal_root.mkdir(parents=True, exist_ok=False)

    materialization_request = _materialization_request(
        source_template_id=source_template_id,
        target_build_pack_id=target_build_pack_id,
        target_display_name=target_display_name,
        target_version=target_version,
        target_revision=target_revision,
        actor=actor,
    )
    materialization_request_path = rehearsal_root / "materialization-request.json"
    write_json(materialization_request_path, materialization_request)
    materialization_result = materialize_build_pack(factory_root, materialization_request)

    checkpoint_run_id = f"{target_build_pack_id}-mid-backlog-checkpoint-v1"
    checkpoint_result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        run_id=checkpoint_run_id,
    )

    active_task_result = run_remote_active_task_continuity_test(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        remote_target_label=remote_target_label,
        remote_host=remote_host,
        remote_user=remote_user,
        staged_by=actor,
        imported_by=actor,
        run_id=None,
    )

    active_task_roundtrip = cast(dict[str, Any], active_task_result["roundtrip_result"])
    active_task_import_report_path = str(active_task_roundtrip["import_report_path"])
    reconcile_request = _reconcile_request(
        build_pack_id=target_build_pack_id,
        import_report_path=active_task_import_report_path,
        actor=actor,
    )
    reconcile_request_path = rehearsal_root / "reconcile-request.json"
    write_json(reconcile_request_path, reconcile_request)
    reconcile_result = reconcile_imported_runtime_state(
        factory_root,
        reconcile_request,
        request_file_dir=reconcile_request_path.parent.resolve(),
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

    target_pack = discover_pack(factory_root, target_build_pack_id)
    canonical_readiness_refresh_result = _refresh_canonical_readiness(
        pack_root=target_pack.pack_root,
        rehearsal_id=rehearsal_id,
    )
    final_state = _final_state(target_pack.pack_root)
    report = {
        "schema_version": "multi-hop-autonomy-rehearsal-report/v1",
        "rehearsal_id": rehearsal_id,
        "generated_at": isoformat_z(read_now()),
        "status": "completed",
        "source_template_id": source_template_id,
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(target_pack.pack_root),
        "remote_target_label": remote_target_label,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "materialization_request_path": str(materialization_request_path),
        "materialization_result": materialization_result,
        "checkpoint_result": checkpoint_result,
        "active_task_continuity_result": active_task_result,
        "reconcile_request_path": str(reconcile_request_path),
        "reconcile_result": reconcile_result,
        "ready_boundary_continuity_result": ready_boundary_result,
        "canonical_readiness_refresh_result": canonical_readiness_refresh_result,
        "final_state": final_state,
    }
    report_path = rehearsal_root / "rehearsal-report.json"
    write_json(report_path, report)
    return {
        "status": "completed",
        "rehearsal_id": rehearsal_id,
        "report_path": str(report_path),
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(target_pack.pack_root),
        "ready_boundary_run_id": ready_boundary_result["run_id"],
        "active_task_run_id": active_task_result["run_id"],
        "canonical_readiness_refresh_ready_for_deployment": canonical_readiness_refresh_result[
            "post_refresh_ready_for_deployment"
        ],
        "final_readiness_state": final_state["readiness"].get("readiness_state"),
        "final_ready_for_deployment": final_state["readiness"].get("ready_for_deployment"),
        "latest_memory_run_id": final_state["latest_memory"].get("selected_run_id"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a full PackFactory multi-hop autonomy rehearsal on a fresh build-pack.",
    )
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="multi-hop-autonomy-v1")
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    result = run_multi_hop_autonomy_rehearsal(
        factory_root=factory_root,
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
