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

from factory_ops import isoformat_z, load_json, read_now, resolve_factory_root, schema_path, timestamp_token, validate_json_document, write_json
from run_build_pack_readiness_eval import run_build_pack_readiness_eval
from run_operator_hint_audit_cleanup_exercise import run_operator_hint_audit_cleanup_exercise


REPORT_SCHEMA_NAME = "operator-hint-status-surfacing-exercise-report.schema.json"
REPORT_SCHEMA_VERSION = "operator-hint-status-surfacing-exercise-report/v1"
EXERCISE_PREFIX = "operator-hint-status-surfacing-exercise"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _exercise_id(target_build_pack_id: str) -> str:
    return f"{EXERCISE_PREFIX}-{target_build_pack_id}-{timestamp_token(read_now())}"


def _exercise_root(factory_root: Path, exercise_id: str) -> Path:
    return factory_root / ".pack-state" / "operator-hint-status-surfacing-exercises" / exercise_id


def run_operator_hint_status_surfacing_exercise(
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

    audit_cleanup_result = run_operator_hint_audit_cleanup_exercise(
        factory_root=factory_root,
        source_template_id=source_template_id,
        target_build_pack_id=target_build_pack_id,
        target_display_name=target_display_name,
        target_version=target_version,
        target_revision=target_revision,
        actor=actor,
    )

    pack_root = factory_root / "build-packs" / target_build_pack_id
    readiness_refresh_result = run_build_pack_readiness_eval(
        pack_root=pack_root,
        mode="benchmark-only",
        invoked_by="operator-hint-status-surfacing-exercise",
        eval_run_id=f"readiness-eval-{target_build_pack_id}-hint-status-refresh-{timestamp_token(read_now())}",
    )
    final_readiness = _load_object(pack_root / "status/readiness.json")
    operator_hint_status = cast(dict[str, Any], final_readiness.get("operator_hint_status", {}))
    if not operator_hint_status:
        raise ValueError("operator hint status surfacing exercise expected status/readiness.json to include operator_hint_status")
    if operator_hint_status.get("hint_count") != 0:
        raise ValueError("operator hint status surfacing exercise expected hint_count=0 after cleanup")
    if cast(list[str], operator_hint_status.get("cleanup_candidate_hint_ids", [])):
        raise ValueError("operator hint status surfacing exercise expected no cleanup candidates after cleanup")
    if "prefer_schema_then_reporting_once" not in cast(list[str], operator_hint_status.get("recent_consumed_hint_ids", [])):
        raise ValueError("operator hint status surfacing exercise expected recent_consumed_hint_ids to include the consumed one-shot hint")
    if "prefer_schema_then_reporting_once" not in cast(list[str], operator_hint_status.get("recent_deactivated_hint_ids", [])):
        raise ValueError("operator hint status surfacing exercise expected recent_deactivated_hint_ids to include the deactivated one-shot hint")
    if not isinstance(operator_hint_status.get("latest_audit_report_path"), str):
        raise ValueError("operator hint status surfacing exercise expected latest_audit_report_path to be present")

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "exercise_id": exercise_id,
        "generated_at": isoformat_z(read_now()),
        "status": "completed",
        "audit_cleanup_result": audit_cleanup_result,
        "readiness_refresh_result": readiness_refresh_result,
        "final_readiness": final_readiness,
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
        "hint_count": operator_hint_status.get("hint_count"),
        "recent_consumed_hint_ids": operator_hint_status.get("recent_consumed_hint_ids", []),
        "recent_deactivated_hint_ids": operator_hint_status.get("recent_deactivated_hint_ids", []),
        "latest_audit_report_path": operator_hint_status.get("latest_audit_report_path"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an operator-hint status surfacing exercise on a fresh build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--source-template-id", default="json-health-checker-template-pack")
    parser.add_argument("--target-build-pack-id", required=True)
    parser.add_argument("--target-display-name", required=True)
    parser.add_argument("--target-version", default="0.1.0")
    parser.add_argument("--target-revision", default="operator-hint-status-surfacing-v1")
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_operator_hint_status_surfacing_exercise(
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
