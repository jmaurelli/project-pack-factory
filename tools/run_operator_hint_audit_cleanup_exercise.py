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

from audit_branch_selection_hints import audit_branch_selection_hints
from factory_ops import isoformat_z, load_json, read_now, resolve_factory_root, schema_path, timestamp_token, validate_json_document, write_json
from run_ordered_hint_lifecycle_exercise import run_ordered_hint_lifecycle_exercise


REPORT_SCHEMA_NAME = "operator-hint-audit-cleanup-exercise-report.schema.json"
REPORT_SCHEMA_VERSION = "operator-hint-audit-cleanup-exercise-report/v1"
EXERCISE_PREFIX = "operator-hint-audit-cleanup-exercise"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _exercise_id(target_build_pack_id: str) -> str:
    return f"{EXERCISE_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _exercise_root(factory_root: Path, exercise_id: str) -> Path:
    return factory_root / ".pack-state" / "operator-hint-audit-cleanup-exercises" / exercise_id


def run_operator_hint_audit_cleanup_exercise(
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

    ordered_hint_lifecycle_result = run_ordered_hint_lifecycle_exercise(
        factory_root=factory_root,
        source_template_id=source_template_id,
        target_build_pack_id=target_build_pack_id,
        target_display_name=target_display_name,
        target_version=target_version,
        target_revision=target_revision,
        actor=actor,
    )

    pre_cleanup_audit_result = audit_branch_selection_hints(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        cleanup_exhausted=False,
        audited_by=actor,
    )
    if not cast(list[str], pre_cleanup_audit_result.get("cleanup_candidate_hint_ids", [])):
        raise ValueError("operator hint audit cleanup exercise expected an exhausted cleanup candidate before cleanup")

    post_cleanup_audit_result = audit_branch_selection_hints(
        factory_root=factory_root,
        build_pack_id=target_build_pack_id,
        cleanup_exhausted=True,
        audited_by=actor,
    )
    removed_hint_ids = cast(list[str], post_cleanup_audit_result.get("removed_hint_ids", []))
    if not removed_hint_ids:
        raise ValueError("operator hint audit cleanup exercise expected cleanup to remove at least one exhausted hint")

    work_state_path = factory_root / "build-packs" / target_build_pack_id / "status" / "work-state.json"
    final_work_state = _load_object(work_state_path)
    remaining_hints = final_work_state.get("branch_selection_hints", [])
    if not isinstance(remaining_hints, list):
        raise ValueError("operator hint audit cleanup exercise expected branch_selection_hints to remain a list")
    if remaining_hints:
        raise ValueError("operator hint audit cleanup exercise expected exhausted hints to be pruned from work-state")

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "exercise_id": exercise_id,
        "generated_at": isoformat_z(read_now()),
        "status": "completed",
        "ordered_hint_lifecycle_result": ordered_hint_lifecycle_result,
        "pre_cleanup_audit_result": pre_cleanup_audit_result,
        "post_cleanup_audit_result": post_cleanup_audit_result,
        "final_work_state": final_work_state,
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
        "cleanup_candidate_hint_ids": pre_cleanup_audit_result.get("cleanup_candidate_hint_ids", []),
        "removed_hint_ids": removed_hint_ids,
        "remaining_hint_count": len(remaining_hints),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an operator-hint audit and cleanup exercise on a fresh build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="operator-hint-audit-cleanup-v1")
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_operator_hint_audit_cleanup_exercise(
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
