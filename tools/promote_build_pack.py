#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    PROMOTION_LOG_PATH,
    REGISTRY_BUILD_PATH,
    discover_pack,
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    remove_file,
    resolve_factory_root,
    scan_deployment_pointer_paths,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


ALLOWED_TRANSITIONS = {
    "not_deployed": "testing",
    "testing": "staging",
    "staging": "production",
}
LIFECYCLE_BY_ENV = {
    "testing": ("testing", "staging"),
    "staging": ("release_candidate", "production"),
    "production": ("maintained", "none"),
}


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _load_request(request_path: Path, factory_root: Path) -> dict[str, Any]:
    errors = validate_json_document(
        request_path,
        schema_path(factory_root, "promotion-request.schema.json"),
    )
    if errors:
        raise ValueError("; ".join(errors))
    return _load_object(request_path)


def _state_snapshot(lifecycle: dict[str, Any], deployment: dict[str, Any]) -> dict[str, Any]:
    return {
        "lifecycle_stage": lifecycle["lifecycle_stage"],
        "deployment_state": deployment["deployment_state"],
        "active_environment": deployment["active_environment"],
        "active_release_path": deployment["active_release_path"],
        "last_verified_at": deployment["last_verified_at"],
        "deployment_pointer_path": deployment["deployment_pointer_path"],
    }


def _all_mandatory_gates_pass(readiness: dict[str, Any]) -> bool:
    gates = readiness.get("required_gates", [])
    if not isinstance(gates, list):
        return False
    for gate in gates:
        if not isinstance(gate, dict):
            return False
        if gate.get("mandatory") is True and gate.get("status") != "pass":
            return False
    return True


def _validate_eval_latest(pack_root: Path, readiness: dict[str, Any]) -> None:
    eval_latest_path = pack_root / "eval/latest/index.json"
    if not eval_latest_path.exists():
        raise ValueError("eval/latest/index.json is required before promotion")
    eval_latest = _load_object(eval_latest_path)
    benchmark_results = eval_latest.get("benchmark_results", [])
    if not isinstance(benchmark_results, list):
        raise ValueError("eval/latest/index.json benchmark_results must be an array")
    result_by_id = {
        str(result.get("benchmark_id")): result
        for result in benchmark_results
        if isinstance(result, dict) and isinstance(result.get("benchmark_id"), str)
    }
    for gate in readiness.get("required_gates", []):
        if not isinstance(gate, dict) or gate.get("mandatory") is not True:
            continue
        gate_id = str(gate.get("gate_id"))
        if gate_id == "validate_build_pack_contract":
            continue
        benchmark_id = gate_id.replace("_", "-")
        result = result_by_id.get(benchmark_id)
        if result is None:
            raise ValueError(f"latest eval evidence is missing benchmark result for {benchmark_id}")
        if result.get("status") != "pass":
            raise ValueError(f"latest eval evidence for {benchmark_id} is not passing")


def _deployment_pointer(
    *,
    pack_id: str,
    release_id: str,
    target_environment: str,
    promotion_id: str,
    report_relative: str,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": "pack-deployment-pointer/v2",
        "environment": target_environment,
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "pack_root": f"build-packs/{pack_id}",
        "source_deployment_file": f"build-packs/{pack_id}/status/deployment.json",
        "active_release_id": release_id,
        "active_release_path": f"dist/releases/{release_id}",
        "deployment_transaction_id": promotion_id,
        "promotion_evidence_ref": report_relative,
        "updated_at": generated_at,
    }


def promote_build_pack(factory_root: Path, request: dict[str, Any]) -> dict[str, Any]:
    pack_id = str(request["build_pack_id"])
    target_environment = str(request["target_environment"])
    release_id = str(request["release_id"])
    promoted_by = str(request["promoted_by"])
    promotion_reason = str(request["promotion_reason"])
    verification_timestamp = request.get("verification_timestamp")

    location = discover_pack(factory_root, pack_id)
    if location.pack_kind != "build_pack":
        raise ValueError(f"{pack_id} is not a build_pack")
    pack_root = location.pack_root

    lifecycle_path = pack_root / "status/lifecycle.json"
    readiness_path = pack_root / "status/readiness.json"
    deployment_path = pack_root / "status/deployment.json"
    retirement_path = pack_root / "status/retirement.json"
    lifecycle = _load_object(lifecycle_path)
    readiness = _load_object(readiness_path)
    deployment = _load_object(deployment_path)
    retirement = _load_object(retirement_path)
    if retirement.get("retirement_state") != "active":
        raise ValueError("retired build packs cannot be promoted")
    if lifecycle.get("lifecycle_stage") == "retired":
        raise ValueError("retired build packs cannot be promoted")
    if readiness.get("ready_for_deployment") is not True:
        raise ValueError("build pack is not ready for deployment")
    if not _all_mandatory_gates_pass(readiness):
        raise ValueError("mandatory readiness gates must pass before promotion")
    _validate_eval_latest(pack_root, readiness)

    release_path = pack_root / "dist/releases" / release_id / "release.json"
    if not release_path.exists():
        raise ValueError("release artifact is missing")
    if target_environment == "testing":
        candidate_path = pack_root / "dist/candidates" / release_id / "release.json"
        if not candidate_path.exists():
            raise ValueError("testing promotion requires a candidate release artifact")

    current_state = str(deployment["deployment_state"])
    current_env = str(deployment["active_environment"])
    current_release_id = deployment.get("active_release_id")
    pre_state = _state_snapshot(lifecycle, deployment)
    if current_env == target_environment and current_release_id == release_id:
        expected_release_path = f"dist/releases/{release_id}"
        if deployment.get("deployment_state") != target_environment:
            raise ValueError("cannot reconcile drifted deployment_state")
        if deployment.get("active_release_path") != expected_release_path:
            raise ValueError("cannot reconcile drifted active_release_path")
        if lifecycle.get("lifecycle_stage") != LIFECYCLE_BY_ENV[target_environment][0]:
            raise ValueError("cannot reconcile drifted lifecycle stage")
        now = read_now()
        generated_at = isoformat_z(now)
        promotion_id = f"promote-{pack_id}-{target_environment}-{timestamp_token(now)}"
        report_relative = f"eval/history/{promotion_id}/promotion-report.json"
        pointer_relative = f"deployments/{target_environment}/{pack_id}.json"
        pointer_path = factory_root / pointer_relative
        registry_path = factory_root / REGISTRY_BUILD_PATH
        registry = _load_object(registry_path)
        entries = registry.get("entries", [])
        if not isinstance(entries, list):
            raise ValueError(f"{registry_path}: entries must be an array")
        registry_entry = dict(entries[location.registry_index])
        if registry_entry.get("deployment_state") != target_environment:
            raise ValueError("cannot reconcile drifted registry deployment_state")
        pointer_payload = _deployment_pointer(
            pack_id=pack_id,
            release_id=release_id,
            target_environment=target_environment,
            promotion_id=promotion_id,
            report_relative=report_relative,
            generated_at=generated_at,
        )
        write_json(pointer_path, pointer_payload)
        deployment["deployment_pointer_path"] = pointer_relative
        deployment["projection_state"] = "projected"
        write_json(deployment_path, deployment)
        report = {
            "schema_version": "build-pack-promotion-report/v1",
            "promotion_id": promotion_id,
            "generated_at": generated_at,
            "status": "reconciled",
            "build_pack_id": pack_id,
            "build_pack_root": f"build-packs/{pack_id}",
            "target_environment": target_environment,
            "release_id": release_id,
            "release_path": f"dist/releases/{release_id}",
            "promoted_by": promoted_by,
            "promotion_reason": promotion_reason,
            "pre_promotion_state": pre_state,
            "post_promotion_state": _state_snapshot(lifecycle, deployment),
            "registry_update": None,
            "operation_log_update": None,
            "actions": [
                {
                    "action_id": "write_deployment_pointer",
                    "status": "reconciled",
                    "target_path": pointer_relative,
                    "summary": "Revalidated the active deployment pointer for the current release.",
                },
                {
                    "action_id": "write_promotion_report",
                    "status": "completed",
                    "target_path": f"build-packs/{pack_id}/{report_relative}",
                    "summary": "Wrote a reconcile-mode promotion report.",
                },
            ],
            "evidence_paths": [
                f"build-packs/{pack_id}/{report_relative}",
                pointer_relative,
            ],
        }
        write_json(pack_root / report_relative, report)
        return {
            "status": "reconciled",
            "promotion_id": promotion_id,
            "promotion_report_path": str(pack_root / report_relative),
        }

    expected_environment = ALLOWED_TRANSITIONS.get(current_state)
    if expected_environment != target_environment:
        raise ValueError(f"invalid promotion transition from {current_state} to {target_environment}")

    now = read_now()
    generated_at = isoformat_z(now)
    promotion_id = f"promote-{pack_id}-{target_environment}-{timestamp_token(now)}"
    report_relative = f"eval/history/{promotion_id}/promotion-report.json"
    pointer_relative = f"deployments/{target_environment}/{pack_id}.json"
    pointer_path = factory_root / pointer_relative

    stale_actions: list[dict[str, Any]] = []
    for stale_pointer in scan_deployment_pointer_paths(factory_root, pack_id):
        stale_relative = relative_path(factory_root, stale_pointer)
        if stale_relative == pointer_relative:
            continue
        remove_file(stale_pointer)
        stale_actions.append(
            {
                "action_id": "remove_stale_pointer",
                "status": "completed",
                "target_path": stale_relative,
                "summary": "Removed a stale environment deployment pointer.",
            }
        )

    lifecycle_stage, promotion_target = LIFECYCLE_BY_ENV[target_environment]
    lifecycle["lifecycle_stage"] = lifecycle_stage
    lifecycle["promotion_target"] = promotion_target
    lifecycle["state_reason"] = promotion_reason
    lifecycle["updated_at"] = generated_at
    lifecycle["updated_by"] = promoted_by

    deployment["deployment_state"] = target_environment
    deployment["active_environment"] = target_environment
    deployment["active_release_id"] = release_id
    deployment["active_release_path"] = f"dist/releases/{release_id}"
    deployment["deployment_pointer_path"] = pointer_relative
    deployment["deployment_transaction_id"] = promotion_id
    deployment["projection_state"] = "projected"
    deployment["last_promoted_at"] = generated_at
    if verification_timestamp is not None:
        deployment["last_verified_at"] = verification_timestamp
    deployment["deployment_notes"] = [f"Promoted to {target_environment} by PackFactory."]

    pointer_payload = _deployment_pointer(
        pack_id=pack_id,
        release_id=release_id,
        target_environment=target_environment,
        promotion_id=promotion_id,
        report_relative=report_relative,
        generated_at=generated_at,
    )
    write_json(pointer_path, pointer_payload)
    write_json(lifecycle_path, lifecycle)
    write_json(deployment_path, deployment)

    registry_path = factory_root / REGISTRY_BUILD_PATH
    registry = _load_object(registry_path)
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{registry_path}: entries must be an array")
    entries[location.registry_index] = {
        **dict(entries[location.registry_index]),
        "active": True,
        "deployment_state": target_environment,
        "deployment_pointer": pointer_relative,
        "active_release_id": release_id,
        "lifecycle_stage": lifecycle_stage,
        "ready_for_deployment": True,
        "retirement_state": "active",
    }
    registry["updated_at"] = generated_at
    write_json(registry_path, registry)

    promotion_log_path = factory_root / PROMOTION_LOG_PATH
    promotion_log = _load_object(promotion_log_path)
    events = promotion_log.setdefault("events", [])
    if not isinstance(events, list):
        raise ValueError(f"{promotion_log_path}: events must be an array")
    events.append(
        {
            "event_type": "promoted",
            "promotion_id": promotion_id,
            "build_pack_id": pack_id,
            "target_environment": target_environment,
            "promotion_report_path": report_relative,
            "status": "completed",
        }
    )
    promotion_log["updated_at"] = generated_at
    write_json(promotion_log_path, promotion_log)

    post_state = _state_snapshot(lifecycle, deployment)
    report = {
        "schema_version": "build-pack-promotion-report/v1",
        "promotion_id": promotion_id,
        "generated_at": generated_at,
        "status": "completed",
        "build_pack_id": pack_id,
        "build_pack_root": f"build-packs/{pack_id}",
        "target_environment": target_environment,
        "release_id": release_id,
        "release_path": f"dist/releases/{release_id}",
        "promoted_by": promoted_by,
        "promotion_reason": promotion_reason,
        "pre_promotion_state": pre_state,
        "post_promotion_state": post_state,
        "registry_update": {
            "registry_path": "registry/build-packs.json",
            "pack_id": pack_id,
            "deployment_state": target_environment,
            "deployment_pointer": pointer_relative,
        },
        "operation_log_update": {
            "promotion_log_path": "registry/promotion-log.json",
            "event_type": "promoted",
            "promotion_id": promotion_id,
            "build_pack_id": pack_id,
            "target_environment": target_environment,
            "promotion_report_path": report_relative,
        },
        "actions": [
            {
                "action_id": "update_lifecycle_state",
                "status": "completed",
                "target_path": f"build-packs/{pack_id}/status/lifecycle.json",
                "summary": "Updated lifecycle stage and next promotion target.",
            },
            {
                "action_id": "update_deployment_state",
                "status": "completed",
                "target_path": f"build-packs/{pack_id}/status/deployment.json",
                "summary": "Updated active deployment state for the target environment.",
            },
            *stale_actions,
            {
                "action_id": "write_deployment_pointer",
                "status": "completed",
                "target_path": pointer_relative,
                "summary": "Wrote the active environment deployment pointer.",
            },
            {
                "action_id": "update_registry_entry",
                "status": "completed",
                "target_path": "registry/build-packs.json",
                "summary": "Updated the build-pack registry entry for the promoted release.",
            },
            {
                "action_id": "append_operation_log",
                "status": "completed",
                "target_path": "registry/promotion-log.json",
                "summary": "Appended the promotion event to the factory operation log.",
            },
            {
                "action_id": "write_promotion_report",
                "status": "completed",
                "target_path": f"build-packs/{pack_id}/{report_relative}",
                "summary": "Wrote the terminal promotion evidence report.",
            },
        ],
        "evidence_paths": [
            f"build-packs/{pack_id}/{report_relative}",
            pointer_relative,
            f"build-packs/{pack_id}/status/deployment.json",
        ],
    }
    write_json(pack_root / report_relative, report)
    return {
        "status": "completed",
        "promotion_id": promotion_id,
        "promotion_report_path": str(pack_root / report_relative),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote a build pack through PackFactory environments.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        factory_root = resolve_factory_root(args.factory_root)
        request = _load_request(Path(args.request_file), factory_root)
        payload = promote_build_pack(factory_root, request)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
