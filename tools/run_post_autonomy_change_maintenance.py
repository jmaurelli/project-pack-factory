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

from distill_autonomy_memory_across_build_packs import distill_autonomy_memory_across_build_packs
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
from refresh_factory_autonomy_memory import refresh_factory_autonomy_memory
from refresh_template_lineage_memory import refresh_template_lineage_memory
from validate_factory import validate_factory


SCHEMA_NAME = "post-autonomy-change-maintenance-report.schema.json"
SCHEMA_VERSION = "post-autonomy-change-maintenance-report/v1"
MAINTENANCE_PREFIX = "post-autonomy-change-maintenance"
VALIDATION_ERROR_MARKERS = (
    "factory-autonomy-memory",
    "template-lineage-memory",
    "instruction-surface",
    "autonomy-memory-distillation",
    "autonomy-memory-distillations",
)


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _maintenance_id() -> str:
    return f"{MAINTENANCE_PREFIX}-{timestamp_token(read_now())}"


def _maintenance_root(factory_root: Path, maintenance_id: str) -> Path:
    return factory_root / ".pack-state" / "post-autonomy-change-maintenance-runs" / maintenance_id


def _active_template_ids(factory_root: Path) -> list[str]:
    registry = _load_object(factory_root / "registry/templates.json")
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("registry/templates.json: entries must be an array")
    template_ids = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("active") is True and isinstance(entry.get("pack_id"), str):
            template_ids.append(entry["pack_id"])
    return sorted(template_ids)


def _validation_summary(factory_root: Path) -> dict[str, Any]:
    result = validate_factory(factory_root)
    errors = result.get("errors", [])
    if not isinstance(errors, list):
        raise ValueError("validate_factory returned non-list errors")
    filtered_errors = [
        error
        for error in errors
        if isinstance(error, str) and any(marker in error for marker in VALIDATION_ERROR_MARKERS)
    ]
    return {
        "status": "pass" if not filtered_errors else "fail",
        "filtered_error_count": len(filtered_errors),
        "filtered_errors": filtered_errors,
        "unrelated_error_count": len(errors) - len(filtered_errors),
    }


def run_post_autonomy_change_maintenance(
    *,
    factory_root: Path,
    actor: str,
    template_ids: list[str] | None = None,
) -> dict[str, Any]:
    maintenance_id = _maintenance_id()
    maintenance_root = _maintenance_root(factory_root, maintenance_id)
    maintenance_root.mkdir(parents=True, exist_ok=False)

    distillation_result = distill_autonomy_memory_across_build_packs(
        factory_root=factory_root,
        matrix_report_path=None,
        score_report_paths=[],
        recorded_by=actor,
    )

    lineage_results = []
    selected_template_ids = template_ids if template_ids is not None and template_ids else _active_template_ids(factory_root)
    for template_id in selected_template_ids:
        lineage_results.append(
            refresh_template_lineage_memory(
                factory_root=factory_root,
                template_id=template_id,
                actor=actor,
            )
        )

    factory_memory_result = refresh_factory_autonomy_memory(
        factory_root=factory_root,
        actor=actor,
    )

    validation_summary = _validation_summary(factory_root)
    status = "completed" if validation_summary["status"] == "pass" else "failed"
    report = {
        "schema_version": SCHEMA_VERSION,
        "maintenance_id": maintenance_id,
        "generated_at": isoformat_z(read_now()),
        "status": status,
        "factory_root": str(factory_root),
        "distillation_result": distillation_result,
        "template_lineage_results": lineage_results,
        "factory_memory_result": factory_memory_result,
        "validation_summary": validation_summary,
    }
    report_path = maintenance_root / "maintenance-report.json"
    write_json(report_path, report)
    errors = validate_json_document(report_path, schema_path(factory_root, SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": status,
        "maintenance_id": maintenance_id,
        "report_path": str(report_path),
        "filtered_error_count": validation_summary["filtered_error_count"],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh post-change autonomy baseline surfaces and fail closed if the preserved handoff state is no longer coherent.",
    )
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--actor", default="codex")
    parser.add_argument("--template-id", action="append", default=[])
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_post_autonomy_change_maintenance(
        factory_root=resolve_factory_root(args.factory_root),
        actor=args.actor,
        template_ids=list(args.template_id),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
