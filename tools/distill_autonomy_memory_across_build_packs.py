#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


SCHEMA_NAME = "autonomy-memory-distillation-report.schema.json"
SCHEMA_VERSION = "autonomy-memory-distillation-report/v1"
DISTILLATION_ROOT = Path(".pack-state") / "autonomy-memory-distillations"
DIMENSION_SUMMARY_PATTERN = re.compile(r"[^a-z0-9]+")


def _latest_report(root: Path, relative_dir: Path, filename: str) -> Path | None:
    search_root = root / relative_dir
    if not search_root.exists():
        return None
    candidates = sorted(search_root.glob(f"*/{filename}"))
    if not candidates:
        return None
    return candidates[-1]


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _resolve_existing_path(factory_root: Path, raw_path: str | Path) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (factory_root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists():
        raise FileNotFoundError(f"path does not exist: {raw_path}")
    try:
        candidate.relative_to(factory_root)
    except ValueError as exc:
        raise ValueError(f"path must stay inside the factory root: {candidate}") from exc
    return candidate


def _lesson_slug(value: str) -> str:
    return DIMENSION_SUMMARY_PATTERN.sub("-", value.lower()).strip("-")


def _distillation_id() -> str:
    return f"autonomy-memory-distillation-{timestamp_token(read_now())}"


def _distillation_root(factory_root: Path, distillation_id: str) -> Path:
    return factory_root / DISTILLATION_ROOT / distillation_id


def _score_report_paths(factory_root: Path, requested_paths: list[str]) -> list[Path]:
    if requested_paths:
        return [_resolve_existing_path(factory_root, path) for path in requested_paths]
    score_root = factory_root / ".pack-state" / "autonomy-quality-scores"
    if not score_root.exists():
        return []
    return sorted(score_root.glob("*/score-report.json"))


def _build_cross_template_lesson(
    *,
    factory_root: Path,
    matrix_path: Path | None,
    matrix_report: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if matrix_path is None or matrix_report is None:
        return None
    rows = matrix_report.get("rows")
    if not isinstance(rows, list):
        return None
    completed_rows: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("status") != "completed":
            continue
        if row.get("final_ready_for_deployment") is not True:
            continue
        completed_rows.append(row)
    build_pack_ids = sorted(
        {
            str(row.get("target_build_pack_id"))
            for row in completed_rows
            if isinstance(row.get("target_build_pack_id"), str) and row.get("target_build_pack_id")
        }
    )
    template_ids = sorted(
        {
            str(row.get("source_template_id"))
            for row in completed_rows
            if isinstance(row.get("source_template_id"), str) and row.get("source_template_id")
        }
    )
    if len(build_pack_ids) < 2:
        return None
    evidence_paths = {relative_path(factory_root, matrix_path)}
    repeated_signals: list[str] = []
    for row in completed_rows:
        target_build_pack_id = row.get("target_build_pack_id")
        source_template_id = row.get("source_template_id")
        report_path = row.get("report_path")
        readiness = row.get("final_readiness_state")
        if isinstance(report_path, str):
            evidence_paths.add(relative_path(factory_root, _resolve_existing_path(factory_root, report_path)))
        repeated_signals.append(
            f"{source_template_id} -> {target_build_pack_id}: {readiness}"
        )
    return {
        "lesson_id": "cross-template-transfer-ready-for-deploy",
        "title": "Cross-template transfer proved",
        "pattern_kind": "cross_template_transfer",
        "confidence_rating": "strong" if len(build_pack_ids) >= 3 else "moderate",
        "summary": (
            f"Factory-default autonomy continuity reached `ready_for_deploy` across {len(build_pack_ids)}"
            f" build-packs from {len(template_ids)} active template lines."
        ),
        "proof_count": len(build_pack_ids),
        "source_build_pack_ids": build_pack_ids,
        "source_template_ids": template_ids,
        "evidence_paths": sorted(evidence_paths),
        "repeated_signals": repeated_signals,
        "suggested_factory_fields": [
            "current_capabilities",
            "latest_autonomy_proof",
            "notes",
        ],
        "recommended_default": "Treat cross-template transfer success as a promoted factory lesson instead of leaving it only in per-pack rehearsal history.",
    }


def _dimension_groups(factory_root: Path, score_paths: list[Path]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for score_path in score_paths:
        score_report = _load_object(score_path)
        target_build_pack_id = score_report.get("target_build_pack_id")
        if not isinstance(target_build_pack_id, str) or not target_build_pack_id:
            continue
        dimensions = score_report.get("dimensions")
        if not isinstance(dimensions, dict):
            continue
        for dimension_id, payload in dimensions.items():
            if not isinstance(dimension_id, str) or not isinstance(payload, dict):
                continue
            if payload.get("status") != "scored":
                continue
            score = payload.get("score")
            if not isinstance(score, (int, float)) or float(score) < 90.0:
                continue
            group = grouped.setdefault(
                dimension_id,
                {
                    "build_pack_ids": set(),
                    "evidence_paths": set(),
                    "details": [],
                    "summary": payload.get("summary"),
                },
            )
            group["build_pack_ids"].add(target_build_pack_id)
            group["evidence_paths"].add(relative_path(factory_root, score_path))
            for evidence_path in payload.get("evidence_paths", []):
                if isinstance(evidence_path, str):
                    try:
                        resolved = _resolve_existing_path(factory_root, evidence_path)
                    except Exception:
                        continue
                    group["evidence_paths"].add(relative_path(factory_root, resolved))
            group["details"].append(f"{target_build_pack_id}: score={float(score):.1f}")
    return grouped


def _build_memory_handoff_lesson(groups: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    handoff = groups.get("handoff_quality")
    if not handoff:
        return None
    build_pack_ids = sorted(handoff["build_pack_ids"])
    if len(build_pack_ids) < 2:
        return None
    return {
        "lesson_id": "memory-handoff-quality-repeatable",
        "title": "Restart-memory handoff is repeatable",
        "pattern_kind": "memory_handoff_quality",
        "confidence_rating": "strong",
        "summary": (
            f"Restart-memory handoff stayed strong across {len(build_pack_ids)} build-packs, "
            "with repeated evidence of correct resume behavior and consistent memory use."
        ),
        "proof_count": len(build_pack_ids),
        "source_build_pack_ids": build_pack_ids,
        "source_template_ids": [],
        "evidence_paths": sorted(handoff["evidence_paths"]),
        "repeated_signals": sorted(handoff["details"]),
        "suggested_factory_fields": [
            "current_capabilities",
            "notes",
        ],
        "recommended_default": "Keep feedback-memory handoff and compatibility-gated latest-memory activation as promoted factory defaults.",
    }


def _build_recovery_lesson(groups: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    recovery = groups.get("recovery_quality")
    blocks = groups.get("block_reporting_quality")
    support_ids = set()
    evidence_paths: set[str] = set()
    repeated_signals: list[str] = []
    if recovery:
        support_ids.update(recovery["build_pack_ids"])
        evidence_paths.update(recovery["evidence_paths"])
        repeated_signals.extend(sorted(recovery["details"]))
    if blocks:
        support_ids.update(blocks["build_pack_ids"])
        evidence_paths.update(blocks["evidence_paths"])
        repeated_signals.extend(sorted(blocks["details"]))
    build_pack_ids = sorted(support_ids)
    if len(build_pack_ids) < 2:
        return None
    return {
        "lesson_id": "fail-closed-import-recovery-repeatable",
        "title": "Fail-closed recovery is reusable",
        "pattern_kind": "fail_closed_import_recovery",
        "confidence_rating": "strong",
        "summary": (
            f"Imported runtime evidence repeatedly stayed fail-closed before reconcile and then re-entered canonical state cleanly across {len(build_pack_ids)} build-packs."
        ),
        "proof_count": len(build_pack_ids),
        "source_build_pack_ids": build_pack_ids,
        "source_template_ids": [],
        "evidence_paths": sorted(evidence_paths),
        "repeated_signals": repeated_signals or ["Repeated import-time block preservation before reconcile."],
        "suggested_factory_fields": [
            "known_limits",
            "notes",
        ],
        "recommended_default": "Keep imported memory compatibility-gated and preserve block summaries until reconcile clears the boundary.",
    }


def _build_operator_guided_branch_choice_lesson(factory_root: Path) -> dict[str, Any] | None:
    exercise_roots = [
        factory_root / ".pack-state" / "operator-hint-branch-choice-exercises",
        factory_root / ".pack-state" / "operator-avoid-branch-choice-exercises",
        factory_root / ".pack-state" / "operator-hint-conflict-exercises",
    ]
    build_pack_ids: set[str] = set()
    evidence_paths: set[str] = set()
    repeated_signals: list[str] = []
    for exercise_root in exercise_roots:
        if not exercise_root.exists():
            continue
        for report_path in sorted(exercise_root.glob("*/exercise-report.json")):
            report = _load_object(report_path)
            build_pack_id = report.get("target_build_pack_id")
            if not isinstance(build_pack_id, str) or not build_pack_id:
                continue
            selection = report.get("initial_branch_selection")
            if not isinstance(selection, dict):
                continue
            method = selection.get("selection_method")
            if not isinstance(method, str) or "operator_hint" not in method:
                continue
            build_pack_ids.add(build_pack_id)
            evidence_paths.add(relative_path(factory_root, report_path))
            chosen_task_id = selection.get("chosen_task_id")
            hint_ids = selection.get("applied_hint_ids", [])
            repeated_signals.append(
                f"{build_pack_id}: method={method}, chosen_task_id={chosen_task_id}, applied_hint_ids={hint_ids}"
            )
    if len(build_pack_ids) < 2:
        return None
    return {
        "lesson_id": "operator-guided-branch-choice-repeatable",
        "title": "Operator-guided branch choice is reusable",
        "pattern_kind": "operator_guided_branch_choice",
        "confidence_rating": "strong",
        "summary": (
            f"Canonical operator guidance repeatedly changed branch selection cleanly across {len(build_pack_ids)} build-packs without breaking bounded continuity."
        ),
        "proof_count": len(build_pack_ids),
        "source_build_pack_ids": sorted(build_pack_ids),
        "source_template_ids": [],
        "evidence_paths": sorted(evidence_paths),
        "repeated_signals": sorted(repeated_signals),
        "suggested_factory_fields": [
            "current_capabilities",
            "notes",
        ],
        "recommended_default": "Keep canonical branch_selection_hints, hint precedence, and hint lifecycle as promoted PackFactory operator-control defaults.",
    }


def distill_autonomy_memory_across_build_packs(
    *,
    factory_root: Path,
    matrix_report_path: str | None,
    score_report_paths: list[str],
    recorded_by: str,
) -> dict[str, Any]:
    matrix_path = (
        _resolve_existing_path(factory_root, matrix_report_path)
        if matrix_report_path
        else _latest_report(factory_root, Path(".pack-state") / "cross-template-transfer-matrices", "matrix-report.json")
    )
    matrix_report = _load_object(matrix_path) if matrix_path is not None else None
    resolved_score_paths = _score_report_paths(factory_root, score_report_paths)
    dimension_groups = _dimension_groups(factory_root, resolved_score_paths)

    lessons: list[dict[str, Any]] = []
    cross_template_lesson = _build_cross_template_lesson(
        factory_root=factory_root,
        matrix_path=matrix_path,
        matrix_report=matrix_report,
    )
    if cross_template_lesson is not None:
        lessons.append(cross_template_lesson)
    for builder in (
        _build_memory_handoff_lesson,
        _build_recovery_lesson,
    ):
        lesson = builder(dimension_groups)
        if lesson is not None:
            lessons.append(lesson)
    operator_branch_lesson = _build_operator_guided_branch_choice_lesson(factory_root)
    if operator_branch_lesson is not None:
        lessons.append(operator_branch_lesson)
    if not lessons:
        raise ValueError("no repeated autonomy lessons could be distilled from the provided evidence")

    supporting_build_pack_ids = sorted(
        {
            build_pack_id
            for lesson in lessons
            for build_pack_id in lesson["source_build_pack_ids"]
        }
    )
    report_id = _distillation_id()
    distillation_root = _distillation_root(factory_root, report_id)
    distillation_root.mkdir(parents=True, exist_ok=False)
    report_path = distillation_root / "distillation-report.json"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "generated_at": isoformat_z(read_now()),
        "overall_summary": (
            "Repeated autonomy lessons are no longer trapped inside individual build-pack artifacts. "
            "This report promotes the strongest repeated signals into one factory-level memory summary."
        ),
        "operator_summary": (
            f"Distilled {len(lessons)} repeated autonomy lessons from "
            f"{len(supporting_build_pack_ids)} build-packs into one factory-level memory artifact."
        ),
        "lesson_count": len(lessons),
        "lessons": lessons,
    }
    write_json(report_path, payload)
    errors = validate_json_document(report_path, schema_path(factory_root, SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "distillation_id": report_id,
        "report_path": str(report_path),
        "lesson_count": len(lessons),
        "supporting_build_pack_count": len(supporting_build_pack_ids),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Distill repeated autonomy lessons across multiple build-packs into one factory-level memory artifact.",
    )
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--matrix-report-path")
    parser.add_argument("--score-report-path", action="append", default=[])
    parser.add_argument("--recorded-by", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = distill_autonomy_memory_across_build_packs(
        factory_root=resolve_factory_root(args.factory_root),
        matrix_report_path=args.matrix_report_path,
        score_report_paths=list(args.score_report_path),
        recorded_by=args.recorded_by,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
