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
    EnvironmentAssignment,
    PROMOTION_LOG_PATH,
    REGISTRY_BUILD_PATH,
    discover_environment_assignment,
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
from validate_factory import collect_build_pack_evidence_integrity_errors


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


def _pointer_core(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if key != "updated_at"}


def _find_canonical_promoted_event(
    promotion_log: dict[str, Any],
    *,
    pack_id: str,
    target_environment: str,
    candidate_promotion_ids: list[str],
) -> dict[str, Any]:
    events = promotion_log.get("events", [])
    if not isinstance(events, list):
        raise ValueError("registry/promotion-log.json: events must be an array")
    for promotion_id in candidate_promotion_ids:
        matches = [
            event
            for event in events
            if isinstance(event, dict)
            and event.get("event_type") == "promoted"
            and event.get("promotion_id") == promotion_id
            and event.get("build_pack_id") == pack_id
            and event.get("target_environment") == target_environment
        ]
        if len(matches) == 1:
            event = matches[0]
            if not isinstance(event.get("promotion_report_path"), str):
                raise ValueError("registry/promotion-log.json: promoted event must include promotion_report_path")
            return event
        if len(matches) > 1:
            raise ValueError(
                "registry/promotion-log.json: reconcile canonical event lookup must match exactly one promoted event"
            )
    raise ValueError("cannot reconcile canonical promotion evidence")


def _evict_prior_assignment(
    *,
    factory_root: Path,
    assignment: EnvironmentAssignment,
    registry: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    actions: list[dict[str, Any]] = []
    evidence_paths: list[str] = []

    removed_pointer = remove_file(assignment.pointer_path)
    if not removed_pointer:
        raise ValueError(
            f"inconsistent current assignee state for {assignment.environment}: "
            f"expected pointer at {assignment.pointer_relative_path}"
        )
    actions.append(
        {
            "action_id": "evict_prior_assignee",
            "status": "completed",
            "target_path": assignment.pointer_relative_path,
            "summary": (
                f"Evicted prior assignee {assignment.pack_id} from "
                f"{assignment.environment} before promotion."
            ),
        }
    )
    evidence_paths.append(assignment.pointer_relative_path)

    prior_deployment = dict(assignment.deployment_payload)
    prior_deployment["deployment_state"] = "not_deployed"
    prior_deployment["active_environment"] = "none"
    prior_deployment["active_release_id"] = None
    prior_deployment["active_release_path"] = None
    prior_deployment["deployment_pointer_path"] = None
    prior_deployment["deployment_transaction_id"] = None
    prior_deployment["projection_state"] = "not_required"
    prior_deployment["last_promoted_at"] = None
    prior_deployment["last_verified_at"] = None
    write_json(assignment.deployment_path, prior_deployment)
    actions.append(
        {
            "action_id": "clear_prior_deployment_state",
            "status": "completed",
            "target_path": f"build-packs/{assignment.pack_id}/status/deployment.json",
            "summary": "Cleared the prior assignee's canonical deployment state.",
        }
    )
    evidence_paths.append(f"build-packs/{assignment.pack_id}/status/deployment.json")

    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{factory_root / REGISTRY_BUILD_PATH}: entries must be an array")
    prior_registry_entry = dict(entries[assignment.registry_index])
    prior_registry_entry["deployment_state"] = "not_deployed"
    prior_registry_entry["deployment_pointer"] = None
    prior_registry_entry["active_release_id"] = None
    entries[assignment.registry_index] = prior_registry_entry
    actions.append(
        {
            "action_id": "clear_prior_registry_assignment",
            "status": "completed",
            "target_path": "registry/build-packs.json",
            "summary": "Cleared the prior assignee's registry deployment fields.",
        }
    )

    return (
        {
            "pack_id": assignment.pack_id,
            "environment": assignment.environment,
            "removed_pointer_path": assignment.pointer_relative_path,
            "cleared_deployment_file": f"build-packs/{assignment.pack_id}/status/deployment.json",
            "cleared_registry_fields": [
                "deployment_state",
                "deployment_pointer",
                "active_release_id",
            ],
        },
        actions,
        evidence_paths,
    )


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
    evidence_errors = collect_build_pack_evidence_integrity_errors(pack_root)
    if evidence_errors:
        raise ValueError(f"readiness evidence integrity failed: {evidence_errors[0]}")
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
        pointer_relative = f"deployments/{target_environment}/{pack_id}.json"
        if deployment.get("deployment_state") != target_environment:
            raise ValueError("cannot reconcile drifted deployment_state")
        if deployment.get("active_release_path") != expected_release_path:
            raise ValueError("cannot reconcile drifted active_release_path")
        if deployment.get("deployment_pointer_path") != pointer_relative:
            raise ValueError("cannot reconcile drifted deployment_pointer_path")
        if lifecycle.get("lifecycle_stage") != LIFECYCLE_BY_ENV[target_environment][0]:
            raise ValueError("cannot reconcile drifted lifecycle stage")
        now = read_now()
        generated_at = isoformat_z(now)
        promotion_id = f"promote-{pack_id}-{target_environment}-{timestamp_token(now)}"
        report_relative = f"eval/history/{promotion_id}/promotion-report.json"
        pointer_path = factory_root / pointer_relative
        environment_pointer_paths = sorted((factory_root / "deployments" / target_environment).glob("*.json"))
        if environment_pointer_paths != [pointer_path]:
            raise ValueError("cannot reconcile ambiguous environment assignment")
        pointer_paths = scan_deployment_pointer_paths(factory_root, pack_id)
        if pointer_paths != [pointer_path]:
            raise ValueError("cannot reconcile multiple deployment pointers")
        registry_path = factory_root / REGISTRY_BUILD_PATH
        registry = _load_object(registry_path)
        entries = registry.get("entries", [])
        if not isinstance(entries, list):
            raise ValueError(f"{registry_path}: entries must be an array")
        registry_entry = dict(entries[location.registry_index])
        if registry_entry.get("deployment_state") != target_environment:
            raise ValueError("cannot reconcile drifted registry deployment_state")
        if registry_entry.get("deployment_pointer") != pointer_relative:
            raise ValueError("cannot reconcile drifted registry deployment pointer")
        if registry_entry.get("active_release_id") != release_id:
            raise ValueError("cannot reconcile drifted registry active release")
        promotion_log = _load_object(factory_root / PROMOTION_LOG_PATH)
        pointer_payload = _load_object(pointer_path)
        candidate_promotion_ids: list[str] = []
        for candidate in (
            deployment.get("deployment_transaction_id"),
            pointer_payload.get("deployment_transaction_id"),
        ):
            if isinstance(candidate, str) and candidate and candidate not in candidate_promotion_ids:
                candidate_promotion_ids.append(candidate)
        canonical_event = _find_canonical_promoted_event(
            promotion_log,
            pack_id=pack_id,
            target_environment=target_environment,
            candidate_promotion_ids=candidate_promotion_ids,
        )
        canonical_report_relative = str(canonical_event["promotion_report_path"])
        canonical_report_path = pack_root / canonical_report_relative
        if not canonical_report_path.exists():
            raise ValueError(f"{canonical_report_path}: canonical promotion report is missing")
        canonical_promotion_id = str(canonical_event["promotion_id"])
        canonical_report = _load_object(canonical_report_path)
        if canonical_report.get("promotion_id") != canonical_promotion_id:
            raise ValueError(f"{canonical_report_path}: canonical promotion report promotion_id does not match event")
        if canonical_report.get("build_pack_id") != pack_id:
            raise ValueError(f"{canonical_report_path}: canonical promotion report build_pack_id does not match request")
        if canonical_report.get("target_environment") != target_environment:
            raise ValueError(
                f"{canonical_report_path}: canonical promotion report target_environment does not match request"
            )
        if canonical_report.get("release_id") != release_id:
            raise ValueError(f"{canonical_report_path}: canonical promotion report release_id does not match request")
        canonical_post_state = canonical_report.get("post_promotion_state")
        if not isinstance(canonical_post_state, dict):
            raise ValueError(f"{canonical_report_path}: canonical promotion report post_promotion_state must be an object")
        if canonical_post_state.get("deployment_pointer_path") != pointer_relative:
            raise ValueError(
                f"{canonical_report_path}: canonical promotion report deployment_pointer_path does not match request"
            )
        if canonical_post_state.get("active_release_path") != expected_release_path:
            raise ValueError(f"{canonical_report_path}: canonical promotion report active_release_path does not match request")
        canonical_pointer = _deployment_pointer(
            pack_id=pack_id,
            release_id=release_id,
            target_environment=target_environment,
            promotion_id=canonical_promotion_id,
            report_relative=canonical_report_relative,
            generated_at=generated_at,
        )
        pointer_reconciled = _pointer_core(pointer_payload) != _pointer_core(canonical_pointer)
        if pointer_reconciled:
            write_json(pointer_path, canonical_pointer)
        deployment_changed = False
        if deployment.get("active_environment") != target_environment:
            deployment["active_environment"] = target_environment
            deployment_changed = True
        if deployment.get("active_release_id") != release_id:
            deployment["active_release_id"] = release_id
            deployment_changed = True
        if deployment.get("active_release_path") != expected_release_path:
            deployment["active_release_path"] = expected_release_path
            deployment_changed = True
        if deployment.get("deployment_pointer_path") != pointer_relative:
            deployment["deployment_pointer_path"] = pointer_relative
            deployment_changed = True
        if deployment.get("deployment_transaction_id") != canonical_promotion_id:
            deployment["deployment_transaction_id"] = canonical_promotion_id
            deployment_changed = True
        if deployment.get("projection_state") != "projected":
            deployment["projection_state"] = "projected"
            deployment_changed = True
        if verification_timestamp is not None and deployment.get("last_verified_at") != verification_timestamp:
            deployment["last_verified_at"] = verification_timestamp
            deployment_changed = True
        if deployment_changed:
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
                    "action_id": "update_deployment_state",
                    "status": "completed" if deployment_changed else "reconciled",
                    "target_path": f"build-packs/{pack_id}/status/deployment.json",
                    "summary": (
                        "Updated pack-local deployment state while preserving canonical promotion evidence."
                        if deployment_changed
                        else "Revalidated pack-local deployment state without changing canonical promotion evidence."
                    ),
                },
                {
                    "action_id": "write_deployment_pointer",
                    "status": "completed" if pointer_reconciled else "reconciled",
                    "target_path": pointer_relative,
                    "summary": (
                        "Restored the canonical deployment pointer for the current release."
                        if pointer_reconciled
                        else "Revalidated the canonical deployment pointer without rewriting it."
                    ),
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
                pointer_relative if pointer_reconciled else None,
                f"build-packs/{pack_id}/status/deployment.json" if deployment_changed else None,
            ],
        }
        report["evidence_paths"] = [path for path in report["evidence_paths"] if path is not None]
        write_json(pack_root / report_relative, report)
        return {
            "status": "reconciled",
            "promotion_id": promotion_id,
            "promotion_report_path": str(pack_root / report_relative),
        }

    current_assignee = discover_environment_assignment(factory_root, target_environment)
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

    registry_path = factory_root / REGISTRY_BUILD_PATH
    registry = _load_object(registry_path)
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{registry_path}: entries must be an array")
    evicted_prior_assignment: dict[str, Any] | None = None
    eviction_actions: list[dict[str, Any]] = []
    eviction_evidence_paths: list[str] = []
    if current_assignee is not None and current_assignee.pack_id != pack_id:
        (
            evicted_prior_assignment,
            eviction_actions,
            eviction_evidence_paths,
        ) = _evict_prior_assignment(
            factory_root=factory_root,
            assignment=current_assignee,
            registry=registry,
        )

    write_json(lifecycle_path, lifecycle)
    write_json(deployment_path, deployment)

    pointer_payload = _deployment_pointer(
        pack_id=pack_id,
        release_id=release_id,
        target_environment=target_environment,
        promotion_id=promotion_id,
        report_relative=report_relative,
        generated_at=generated_at,
    )
    write_json(pointer_path, pointer_payload)
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
            *eviction_actions,
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
            *eviction_evidence_paths,
            pointer_relative,
            f"build-packs/{pack_id}/status/deployment.json",
        ],
    }
    if evicted_prior_assignment is not None:
        report["evicted_prior_assignment"] = evicted_prior_assignment
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
