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
    REGISTRY_TEMPLATE_PATH,
    discover_pack,
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    remove_file,
    resolve_factory_root,
    scan_deployment_pointer_paths,
    timestamp_token,
    write_json,
)


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _snapshot(lifecycle: dict[str, Any], readiness: dict[str, Any], deployment: dict[str, Any], retirement_state: str) -> dict[str, Any]:
    return {
        "lifecycle_stage": lifecycle.get("lifecycle_stage"),
        "readiness_state": readiness.get("readiness_state"),
        "deployment_state": deployment.get("deployment_state"),
        "active_environment": deployment.get("active_environment"),
        "deployment_pointer_path": deployment.get("deployment_pointer_path"),
        "retirement_state": retirement_state,
    }


def _retained_artifacts(pack_kind: str) -> dict[str, bool]:
    if pack_kind == "template_pack":
        return {
            "eval_history": True,
            "release_artifacts": False,
            "lineage": False,
        }
    return {
        "eval_history": True,
        "release_artifacts": True,
        "lineage": True,
    }


def retire_pack(
    factory_root: Path,
    pack_id: str,
    retired_by: str,
    reason: str,
    superseded_by_pack_id: str | None,
) -> dict[str, Any]:
    location = discover_pack(factory_root, pack_id)
    pack_root = location.pack_root
    lifecycle_path = pack_root / "status/lifecycle.json"
    readiness_path = pack_root / "status/readiness.json"
    deployment_path = pack_root / "status/deployment.json"
    retirement_path = pack_root / "status/retirement.json"

    lifecycle = _load_object(lifecycle_path)
    readiness = _load_object(readiness_path)
    deployment = _load_object(deployment_path)
    retirement = _load_object(retirement_path)

    if retirement.get("retirement_state") == "retired":
        report_relative = retirement.get("retirement_report_path")
        report_path = pack_root / report_relative if isinstance(report_relative, str) else None
        return {
            "status": "reconciled",
            "pack_id": pack_id,
            "pack_kind": location.pack_kind,
            "retired_at": retirement.get("retired_at"),
            "retirement_report_path": str(report_path) if report_path is not None else None,
        }

    now = read_now()
    retired_at = isoformat_z(now)
    retirement_id = f"retire-{pack_id}-{timestamp_token(now)}"
    report_relative = Path("eval/history") / retirement_id / "retirement-report.json"
    report_path = pack_root / report_relative
    registry_path = factory_root / (REGISTRY_TEMPLATE_PATH if location.pack_kind == "template_pack" else REGISTRY_BUILD_PATH)
    promotion_log_path = factory_root / PROMOTION_LOG_PATH

    pre_state = _snapshot(lifecycle, readiness, deployment, str(retirement.get("retirement_state")))
    removed_pointer_paths: list[str] = []
    pointer_actions: list[dict[str, Any]] = []
    pointer_matches = scan_deployment_pointer_paths(factory_root, pack_id) if location.pack_kind == "build_pack" else []
    if pointer_matches:
        for pointer in pointer_matches:
            remove_file(pointer)
            removed_relative = relative_path(factory_root, pointer)
            removed_pointer_paths.append(removed_relative)
            pointer_actions.append(
                {
                    "action_id": "remove_deployment_pointer",
                    "status": "completed",
                    "target_path": removed_relative,
                    "summary": "Removed active deployment pointer.",
                }
            )
    elif location.pack_kind == "build_pack":
        pointer_actions.append(
            {
                "action_id": "remove_deployment_pointer",
                "status": "skipped",
                "target_path": "deployments/",
                "summary": "No active deployment pointers were present at retirement time.",
            }
        )

    lifecycle["lifecycle_stage"] = "retired"
    lifecycle["promotion_target"] = "none"
    lifecycle["state_reason"] = reason
    lifecycle["updated_at"] = retired_at
    lifecycle["updated_by"] = retired_by

    readiness["readiness_state"] = "retired"
    readiness["ready_for_deployment"] = False
    readiness["last_evaluated_at"] = retired_at
    blocking_issues = readiness.setdefault("blocking_issues", [])
    if isinstance(blocking_issues, list):
        message = "This build pack is retired and preserved as a historical fixture."
        if location.pack_kind == "template_pack":
            message = "This template pack is retired and preserved as a historical fixture."
        if message not in blocking_issues:
            blocking_issues.append(message)
    recommended = readiness.setdefault("recommended_next_actions", [])
    if isinstance(recommended, list) and "Consult the retirement report for terminal state details." not in recommended:
        recommended.append("Consult the retirement report for terminal state details.")

    deployment["deployment_state"] = "not_deployed"
    deployment["active_environment"] = "none"
    deployment["active_release_id"] = None
    deployment["active_release_path"] = None
    deployment["deployment_pointer_path"] = None
    deployment["deployment_transaction_id"] = None
    deployment["projection_state"] = "not_required"
    deployment["last_promoted_at"] = None
    deployment["last_verified_at"] = None
    deployment["deployment_notes"] = ["Retired fixture; no active deployment candidate."]

    retirement.update(
        {
            "schema_version": "pack-retirement/v1",
            "pack_id": pack_id,
            "pack_kind": location.pack_kind,
            "retirement_state": "retired",
            "retired_at": retired_at,
            "retired_by": retired_by,
            "retirement_reason": reason,
            "superseded_by_pack_id": superseded_by_pack_id,
            "retirement_report_path": str(report_relative),
            "removed_deployment_pointer_paths": removed_pointer_paths,
            "retained_artifacts": _retained_artifacts(location.pack_kind),
            "operator_notes": ["Retired through the PackFactory retire workflow."],
        }
    )

    registry = _load_object(registry_path)
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{registry_path}: entries must be an array")
    entry = dict(entries[location.registry_index])
    entry["active"] = False
    entry["retirement_state"] = "retired"
    entry["retirement_file"] = "status/retirement.json"
    entry["retired_at"] = retired_at
    entry["lifecycle_stage"] = "retired"
    entry["ready_for_deployment"] = False
    if location.pack_kind == "build_pack":
        entry["deployment_state"] = "not_deployed"
        entry["active_release_id"] = None
        entry["deployment_pointer"] = None
    entries[location.registry_index] = entry
    registry["updated_at"] = retired_at

    promotion_log = _load_object(promotion_log_path)
    events = promotion_log.setdefault("events", [])
    if not isinstance(events, list):
        raise ValueError(f"{promotion_log_path}: events must be an array")
    promotion_event = {
        "event_type": "retired",
        "retired_pack_id": pack_id,
        "retired_pack_kind": location.pack_kind,
        "retired_at": retired_at,
        "retirement_reason": reason,
        "retirement_report_path": str(report_relative),
        "status": "completed",
    }
    events.append(promotion_event)
    promotion_log["updated_at"] = retired_at

    post_state = _snapshot(lifecycle, readiness, deployment, "retired")
    pack_root_relative = f"{pack_root.parent.name}/{pack_root.name}"
    report = {
        "schema_version": "pack-retirement-report/v1",
        "retirement_id": retirement_id,
        "generated_at": retired_at,
        "pack_id": pack_id,
        "pack_kind": location.pack_kind,
        "pack_root": pack_root_relative,
        "retired_by": retired_by,
        "retirement_reason": reason,
        "superseded_by_pack_id": superseded_by_pack_id,
        "pre_retirement_state": pre_state,
        "post_retirement_state": post_state,
        "registry_updates": [
            {
                "registry_path": relative_path(factory_root, registry_path),
                "pack_id": pack_id,
                "pack_kind": location.pack_kind,
                "retirement_state": "retired",
                "active": False,
                "retired_at": retired_at,
            }
        ],
        "promotion_log_update": {
            "promotion_log_path": relative_path(factory_root, promotion_log_path),
            "event_type": "retired",
            "retired_pack_id": pack_id,
            "retired_pack_kind": location.pack_kind,
            "retirement_report_path": str(report_relative),
            "retired_at": retired_at,
        },
        "actions": [
            {
                "action_id": "write_retirement_state",
                "status": "completed",
                "target_path": relative_path(factory_root, retirement_path),
                "summary": "Recorded terminal retirement state.",
            },
            {
                "action_id": "update_lifecycle_state",
                "status": "completed",
                "target_path": relative_path(factory_root, lifecycle_path),
                "summary": "Marked the pack retired.",
            },
            {
                "action_id": "update_readiness_state",
                "status": "completed",
                "target_path": relative_path(factory_root, readiness_path),
                "summary": "Marked readiness retired.",
            },
            {
                "action_id": "update_deployment_state",
                "status": "completed",
                "target_path": relative_path(factory_root, deployment_path),
                "summary": "Cleared the deployment surface.",
            },
            *pointer_actions,
            {
                "action_id": "update_registry_entry",
                "status": "completed",
                "target_path": relative_path(factory_root, registry_path),
                "summary": "Marked the registry entry inactive and retired.",
            },
            {
                "action_id": "append_promotion_log",
                "status": "completed",
                "target_path": relative_path(factory_root, promotion_log_path),
                "summary": "Appended a retired event with evidence path.",
            },
            {
                "action_id": "write_retirement_report",
                "status": "completed",
                "target_path": str(report_relative),
                "summary": "Recorded terminal retirement evidence.",
            },
        ],
        "evidence_paths": [
            relative_path(factory_root, lifecycle_path),
            relative_path(factory_root, readiness_path),
            relative_path(factory_root, deployment_path),
            relative_path(factory_root, retirement_path),
            relative_path(factory_root, pack_root / "eval/latest/index.json"),
        ],
    }

    write_json(lifecycle_path, lifecycle)
    write_json(readiness_path, readiness)
    write_json(deployment_path, deployment)
    write_json(retirement_path, retirement)
    write_json(registry_path, registry)
    write_json(promotion_log_path, promotion_log)
    write_json(report_path, report)

    return {
        "status": "completed",
        "pack_id": pack_id,
        "pack_kind": location.pack_kind,
        "retired_at": retired_at,
        "retirement_report_path": str(report_path),
        "removed_deployment_pointer_paths": removed_pointer_paths,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Retire a Project Pack Factory pack deterministically.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory root.")
    parser.add_argument("--pack-id", required=True, help="Pack id to retire.")
    parser.add_argument("--retired-by", required=True, help="Operator or agent recording the retirement.")
    parser.add_argument("--reason", required=True, help="Human-readable retirement reason.")
    parser.add_argument("--superseded-by-pack-id", default=None, help="Optional replacement pack id.")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    args = parser.parse_args()

    result = retire_pack(
        resolve_factory_root(args.factory_root),
        args.pack_id,
        args.retired_by,
        args.reason,
        args.superseded_by_pack_id,
    )
    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: retired {result['pack_kind']} `{result['pack_id']}` at {result['retired_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
