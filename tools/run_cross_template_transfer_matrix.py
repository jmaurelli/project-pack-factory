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


REPORT_SCHEMA_NAME = "cross-template-transfer-matrix-report.schema.json"
REPORT_SCHEMA_VERSION = "cross-template-transfer-matrix-report/v1"
MATRIX_PREFIX = "cross-template-transfer-matrix"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _matrix_id() -> str:
    return f"{MATRIX_PREFIX}-{timestamp_token(read_now())}"


def _matrix_root(factory_root: Path, matrix_id: str) -> Path:
    return factory_root / ".pack-state" / "cross-template-transfer-matrices" / matrix_id


def _score_row(payload: dict[str, Any]) -> tuple[float, list[str]]:
    score = 100.0
    details: list[str] = []
    if payload.get("status") != "completed":
        score -= 50.0
        details.append(f"status={payload.get('status')!r}")
    active_result = cast(dict[str, Any], payload.get("active_task_continuity_result", {}))
    ready_result = cast(dict[str, Any], payload.get("ready_boundary_continuity_result", {}))
    reconcile_result = cast(dict[str, Any], payload.get("reconcile_result", {}))
    refresh_result = cast(dict[str, Any], payload.get("canonical_readiness_refresh_result", {}))
    if active_result.get("status") != "completed":
        score -= 15.0
        details.append("active-task continuity was not completed")
    if ready_result.get("status") != "completed":
        score -= 15.0
        details.append("ready-boundary continuity was not completed")
    if reconcile_result.get("status") != "completed":
        score -= 10.0
        details.append("reconcile result was not completed")
    if refresh_result.get("status") != "completed":
        score -= 10.0
        details.append("canonical readiness refresh was not completed")
    if refresh_result.get("post_refresh_ready_for_deployment") is not True:
        score -= 20.0
        details.append("post-refresh ready_for_deployment was not true")
    return max(score, 0.0), details


def run_cross_template_transfer_matrix(*, factory_root: Path, entries: list[tuple[str, str, Path]]) -> dict[str, Any]:
    matrix_id = _matrix_id()
    matrix_root = _matrix_root(factory_root, matrix_id)
    matrix_root.mkdir(parents=True, exist_ok=False)

    rows: list[dict[str, Any]] = []
    scores: list[float] = []
    for source_template_id, build_pack_id, report_path in entries:
        payload = _load_object(report_path)
        if payload.get("schema_version") != "multi-hop-autonomy-rehearsal-report/v1":
            raise ValueError(f"{report_path}: expected multi-hop-autonomy-rehearsal-report/v1")
        final_state = cast(dict[str, Any], payload.get("final_state", {}))
        latest_memory = cast(dict[str, Any], final_state.get("latest_memory", {}))
        row_score, row_details = _score_row(payload)
        scores.append(row_score)
        rows.append(
            {
                "source_template_id": source_template_id,
                "target_build_pack_id": build_pack_id,
                "report_path": str(report_path),
                "status": payload.get("status"),
                "final_readiness_state": cast(dict[str, Any], final_state.get("readiness", {})).get("readiness_state"),
                "final_ready_for_deployment": cast(dict[str, Any], final_state.get("readiness", {})).get("ready_for_deployment"),
                "latest_memory_run_id": latest_memory.get("selected_run_id"),
                "row_score": row_score,
                "row_details": row_details,
            }
        )

    overall_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    if overall_score >= 90.0:
        overall_rating = "strong"
    elif overall_score >= 75.0:
        overall_rating = "good"
    elif overall_score >= 60.0:
        overall_rating = "mixed"
    else:
        overall_rating = "weak"

    findings = [
        f"{row['source_template_id']} transfer scored below 80"
        for row in rows
        if isinstance(row.get("row_score"), (int, float)) and float(row["row_score"]) < 80.0
    ]

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "matrix_id": matrix_id,
        "generated_at": isoformat_z(read_now()),
        "row_count": len(rows),
        "completed_row_count": sum(1 for row in rows if row.get("status") == "completed"),
        "ready_row_count": sum(1 for row in rows if row.get("final_ready_for_deployment") is True),
        "overall_score": overall_score,
        "overall_rating": overall_rating,
        "rows": rows,
        "findings": findings,
    }
    report_path = matrix_root / "matrix-report.json"
    write_json(report_path, report)
    errors = validate_json_document(report_path, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "matrix_id": matrix_id,
        "report_path": str(report_path),
        "row_count": len(rows),
        "overall_score": overall_score,
        "overall_rating": overall_rating,
    }


def _parse_entry(value: str) -> tuple[str, str, Path]:
    parts = value.split("::", 2)
    if len(parts) != 3 or not all(parts):
        raise argparse.ArgumentTypeError("matrix entry must be source_template_id::target_build_pack_id::/absolute/report/path")
    source_template_id, build_pack_id, report_path = parts
    return source_template_id, build_pack_id, Path(report_path).resolve()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a PackFactory cross-template autonomy transfer matrix from existing rehearsal reports.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--entry", action="append", type=_parse_entry, required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_cross_template_transfer_matrix(
        factory_root=resolve_factory_root(args.factory_root),
        entries=cast(list[tuple[str, str, Path]], args.entry),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
