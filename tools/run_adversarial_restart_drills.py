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
from refresh_local_feedback_memory_pointer import refresh_local_feedback_memory_pointer
from run_degraded_connectivity_autonomy_exercise import run_degraded_connectivity_autonomy_exercise
from run_local_mid_backlog_checkpoint import run_local_mid_backlog_checkpoint


REPORT_SCHEMA_NAME = "adversarial-restart-drill-report.schema.json"
REPORT_SCHEMA_VERSION = "adversarial-restart-drill-report/v1"
DRILL_PREFIX = "adversarial-restart-drill"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _drill_id(target_build_pack_id: str) -> str:
    return f"{DRILL_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _drill_root(factory_root: Path, drill_id: str) -> Path:
    return factory_root / ".pack-state" / "adversarial-restart-drills" / drill_id


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
        "materialization_reason": "Create a fresh proving-ground build-pack for PackFactory adversarial restart drills.",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
    }


def _derive_conflict_pack_id(base_pack_id: str) -> str:
    marker = "-build-pack-"
    if marker in base_pack_id:
        return base_pack_id.replace(marker, "-conflicting-memory-build-pack-", 1)
    return f"{base_pack_id}-conflicting-memory"


def _partial_pointer_recovery(*, factory_root: Path, build_pack_id: str) -> dict[str, Any]:
    pack_root = factory_root / "build-packs" / build_pack_id
    pointer_path = pack_root / ".pack-state/agent-memory/latest-memory.json"
    original_pointer = _load_object(pointer_path)
    pointer_path.unlink(missing_ok=True)
    recovery_result = refresh_local_feedback_memory_pointer(
        factory_root=factory_root,
        build_pack_id=build_pack_id,
    )
    return {
        "status": "completed",
        "deleted_pointer_path": str(pointer_path),
        "deleted_selected_run_id": original_pointer.get("selected_run_id"),
        "recovery_result": recovery_result,
    }


def _expired_memory_fail_closed(*, factory_root: Path, build_pack_id: str) -> dict[str, Any]:
    pack_root = factory_root / "build-packs" / build_pack_id
    pointer_path = pack_root / ".pack-state/agent-memory/latest-memory.json"
    current_pointer = _load_object(pointer_path)
    selected_memory_rel = current_pointer.get("selected_memory_path")
    if not isinstance(selected_memory_rel, str) or not selected_memory_rel:
        raise ValueError("expected a selected_memory_path before running expired-memory drill")
    memory_path = (pack_root / selected_memory_rel).resolve()
    original_memory = _load_object(memory_path)
    mutated_memory = json.loads(json.dumps(original_memory))
    validity = mutated_memory.get("memory_validity")
    if not isinstance(validity, dict):
        raise ValueError("selected feedback memory is missing memory_validity")
    validity["expires_at"] = "2000-01-01T00:00:00Z"
    validity["summary"] = "Forced expired-memory drill payload."
    write_json(memory_path, mutated_memory)
    pointer_path.unlink(missing_ok=True)
    fail_closed_result = refresh_local_feedback_memory_pointer(
        factory_root=factory_root,
        build_pack_id=build_pack_id,
    )
    write_json(memory_path, original_memory)
    restored_pointer_result = refresh_local_feedback_memory_pointer(
        factory_root=factory_root,
        build_pack_id=build_pack_id,
    )
    return {
        "status": "completed",
        "memory_path": str(memory_path),
        "forced_expires_at": "2000-01-01T00:00:00Z",
        "fail_closed_result": fail_closed_result,
        "restored_pointer_result": restored_pointer_result,
    }


def run_adversarial_restart_drills(
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
    drill_id = _drill_id(target_build_pack_id)
    drill_root = _drill_root(factory_root, drill_id)
    drill_root.mkdir(parents=True, exist_ok=False)

    materialization_request = _materialization_request(
        source_template_id=source_template_id,
        target_build_pack_id=target_build_pack_id,
        target_display_name=target_display_name,
        target_version=target_version,
        target_revision=target_revision,
        actor=actor,
    )
    materialization_request_path = drill_root / "materialization-request.json"
    write_json(materialization_request_path, materialization_request)
    materialization_result = materialize_build_pack(factory_root, materialization_request)

    checkpoint_result = run_local_mid_backlog_checkpoint(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        run_id=f"{target_build_pack_id}-adversarial-restart-checkpoint-v1",
    )
    partial_pointer_recovery = _partial_pointer_recovery(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
    )
    expired_memory_fail_closed = _expired_memory_fail_closed(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
    )

    conflict_pack_id = _derive_conflict_pack_id(target_build_pack_id)
    conflicting_memory_exercise_result = run_degraded_connectivity_autonomy_exercise(
        factory_root=factory_root,
        source_template_id=source_template_id,
        target_build_pack_id=conflict_pack_id,
        target_display_name=f"{target_display_name} Conflicting Memory",
        target_version=target_version,
        target_revision=f"{target_revision}-conflicting-memory",
        remote_target_label=remote_target_label,
        remote_host=remote_host,
        remote_user=remote_user,
        actor=actor,
    )

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "drill_id": drill_id,
        "generated_at": isoformat_z(read_now()),
        "status": "completed",
        "source_template_id": source_template_id,
        "local_restart_pack_id": target_build_pack_id,
        "local_restart_pack_root": str(factory_root / "build-packs" / target_build_pack_id),
        "materialization_result": materialization_result,
        "checkpoint_result": checkpoint_result,
        "partial_pointer_recovery": partial_pointer_recovery,
        "expired_memory_fail_closed": {
            "status": "completed",
            "memory_path": expired_memory_fail_closed["memory_path"],
            "forced_expires_at": expired_memory_fail_closed["forced_expires_at"],
            "fail_closed_result": expired_memory_fail_closed["fail_closed_result"],
        },
        "restored_pointer_result": expired_memory_fail_closed["restored_pointer_result"],
        "conflicting_memory_exercise_result": conflicting_memory_exercise_result,
    }
    report_path = drill_root / "drill-report.json"
    write_json(report_path, report)
    errors = validate_json_document(report_path, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "drill_id": drill_id,
        "report_path": str(report_path),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run bounded adversarial restart drills on a fresh proving-ground build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="adversarial-restart-drill-v1")
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_adversarial_restart_drills(
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
