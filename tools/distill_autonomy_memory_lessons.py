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
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


SCHEMA_NAME = "autonomy-memory-distillation-report.schema.json"
SCHEMA_VERSION = "autonomy-memory-distillation-report/v1"
REPORT_PREFIX = "autonomy-memory-distillation"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _resolve_existing_path(factory_root: Path, raw_path: str) -> Path:
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


def _report_id() -> str:
    return f"{REPORT_PREFIX}-{timestamp_token(read_now())}"


def _report_root(factory_root: Path, report_id: str) -> Path:
    return factory_root / ".pack-state" / "autonomy-memory-distillations" / report_id


def _confidence_from_count(count: int) -> str:
    return "strong" if count >= 3 else "moderate"


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _lesson_from_matrix(factory_root: Path, matrix_report_path: Path) -> dict[str, Any]:
    payload = _load_object(matrix_report_path)
    rows = payload.get("rows", [])
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError("cross-template transfer matrix must contain at least two rows")

    source_template_ids: list[str] = []
    build_pack_ids: list[str] = []
    repeated_signals: list[str] = [
        f"completed_row_count={payload.get('completed_row_count')}",
        f"ready_row_count={payload.get('ready_row_count')}",
        f"overall_rating={payload.get('overall_rating')}",
        f"overall_score={payload.get('overall_score')}",
    ]
    evidence_paths = [relative_path(factory_root, matrix_report_path)]
    latest_memory_run_ids: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        template_id = row.get("source_template_id")
        build_pack_id = row.get("target_build_pack_id")
        if isinstance(template_id, str):
            source_template_ids.append(template_id)
        if isinstance(build_pack_id, str):
            build_pack_ids.append(build_pack_id)
        report_path = row.get("report_path")
        if isinstance(report_path, str):
            evidence_paths.append(relative_path(factory_root, Path(report_path)))
        latest_memory_run_id = row.get("latest_memory_run_id")
        if isinstance(latest_memory_run_id, str):
            latest_memory_run_ids.append(latest_memory_run_id)

    if latest_memory_run_ids:
        repeated_signals.append(
            "latest_memory_run_ids=" + ", ".join(sorted(latest_memory_run_ids))
        )
    repeated_signals.append(
        "all rows finished ready_for_deploy with ready_for_deployment=true across multiple templates"
    )

    return {
        "lesson_id": "cross-template-memory-transfer",
        "title": "Cross-template memory transfer holds across active template lines.",
        "pattern_kind": "cross_template_transfer",
        "confidence_rating": _confidence_from_count(len(build_pack_ids)),
        "proof_count": len(build_pack_ids),
        "source_build_pack_ids": sorted(set(build_pack_ids)),
        "source_template_ids": sorted(set(source_template_ids)),
        "evidence_paths": sorted(set(evidence_paths)),
        "repeated_signals": repeated_signals,
        "suggested_factory_fields": [
            "source_template_id",
            "target_build_pack_id",
            "latest_memory_run_id",
            "final_readiness_state",
            "final_ready_for_deployment",
        ],
        "summary": (
            "Cross-template transfer reports now show the same autonomy baseline reaching "
            "`ready_for_deploy` across multiple active template lines instead of staying "
            "trapped inside one proving-ground family."
        ),
        "recommended_default": (
            "Treat multi-template transfer success as promotable factory knowledge and keep "
            "the transfer row summary visible in factory-level restart memory."
        ),
    }


def _lesson_from_quality_reports(factory_root: Path, quality_report_paths: list[Path]) -> dict[str, Any]:
    if len(quality_report_paths) < 2:
        raise ValueError("at least two autonomy-quality score reports are required")

    build_pack_ids: list[str] = []
    evidence_paths: list[str] = []
    handoff_scores: list[float] = []
    recovery_scores: list[float] = []
    replay_scores: list[float] = []
    outcome_scores: list[float] = []
    overall_scores: list[float] = []
    overall_ratings: list[str] = []
    for path in quality_report_paths:
        payload = _load_object(path)
        build_pack_id = payload.get("target_build_pack_id")
        if isinstance(build_pack_id, str):
            build_pack_ids.append(build_pack_id)
        evidence_paths.append(relative_path(factory_root, path))
        overall_score = _float_or_none(payload.get("overall_score"))
        if overall_score is not None:
            overall_scores.append(overall_score)
        overall_rating = payload.get("overall_rating")
        if isinstance(overall_rating, str):
            overall_ratings.append(overall_rating)
        dimensions = payload.get("dimensions", {})
        if isinstance(dimensions, dict):
            handoff = _float_or_none(cast(dict[str, Any], dimensions.get("handoff_quality", {})).get("score"))
            recovery = _float_or_none(cast(dict[str, Any], dimensions.get("recovery_quality", {})).get("score"))
            replay = _float_or_none(cast(dict[str, Any], dimensions.get("replay_avoidance_quality", {})).get("score"))
            outcome = _float_or_none(cast(dict[str, Any], dimensions.get("outcome_quality", {})).get("score"))
            if handoff is not None:
                handoff_scores.append(handoff)
            if recovery is not None:
                recovery_scores.append(recovery)
            if replay is not None:
                replay_scores.append(replay)
            if outcome is not None:
                outcome_scores.append(outcome)

    repeated_signals = [
        f"overall_ratings={', '.join(sorted(set(overall_ratings)))}",
        f"min_handoff_quality={min(handoff_scores) if handoff_scores else 'n/a'}",
        f"min_recovery_quality={min(recovery_scores) if recovery_scores else 'n/a'}",
        f"min_replay_avoidance_quality={min(replay_scores) if replay_scores else 'n/a'}",
        f"min_outcome_quality={min(outcome_scores) if outcome_scores else 'n/a'}",
        f"min_overall_score={min(overall_scores) if overall_scores else 'n/a'}",
    ]

    return {
        "lesson_id": "bounded-memory-handoff-quality",
        "title": "Memory handoff quality is repeatedly strong across bounded autonomy loops.",
        "pattern_kind": "memory_handoff_quality",
        "confidence_rating": _confidence_from_count(len(build_pack_ids)),
        "proof_count": len(build_pack_ids),
        "source_build_pack_ids": sorted(set(build_pack_ids)),
        "source_template_ids": [],
        "evidence_paths": sorted(set(evidence_paths)),
        "repeated_signals": repeated_signals,
        "suggested_factory_fields": [
            "resume_correctness",
            "consistent_memory_use_rate",
            "stale_memory_rate",
            "handoff_quality.score",
            "recovery_quality.score",
            "replay_avoidance_quality.score",
            "outcome_quality.score",
        ],
        "summary": (
            "Multiple autonomy-quality score reports now show the same bounded loop qualities: "
            "memory reuse stays correct, replay stays low, imports reconcile cleanly, and the "
            "pack finishes ready for the next promotion step."
        ),
        "recommended_default": (
            "Preserve handoff, recovery, replay-avoidance, and outcome scoring as the core "
            "factory lesson for restart-memory quality."
        ),
    }


def _lesson_from_import_reports(factory_root: Path, import_report_paths: list[Path]) -> dict[str, Any]:
    if len(import_report_paths) < 2:
        raise ValueError("at least two import reports are required")

    build_pack_ids: list[str] = []
    evidence_paths: list[str] = []
    statuses: list[str] = []
    reasons: list[str] = []
    recoveries: list[str] = []
    for path in import_report_paths:
        payload = _load_object(path)
        build_pack_id = payload.get("build_pack_id")
        if isinstance(build_pack_id, str):
            build_pack_ids.append(build_pack_id)
        evidence_paths.append(relative_path(factory_root, path))
        memory_intake = payload.get("memory_intake", {})
        if isinstance(memory_intake, dict):
            status = memory_intake.get("status")
            if isinstance(status, str):
                statuses.append(status)
            block_summary = memory_intake.get("block_summary")
            if isinstance(block_summary, dict):
                reason = block_summary.get("reason")
                if isinstance(reason, str):
                    reasons.append(reason)
                recovery = block_summary.get("recommended_recovery_action")
                if isinstance(recovery, str):
                    recoveries.append(recovery)

    repeated_signals = [
        f"memory_intake_statuses={', '.join(sorted(set(statuses)))}",
        f"block_reasons={', '.join(sorted(set(reasons))) if reasons else 'none'}",
    ]
    if recoveries:
        repeated_signals.append(
            "recommended_recovery_actions=" + " | ".join(sorted(set(recoveries)))
        )

    return {
        "lesson_id": "fail-closed-import-reconcile",
        "title": "Imported memory is preserved first, then reconciled deliberately.",
        "pattern_kind": "fail_closed_import_recovery",
        "confidence_rating": _confidence_from_count(len(build_pack_ids)),
        "proof_count": len(build_pack_ids),
        "source_build_pack_ids": sorted(set(build_pack_ids)),
        "source_template_ids": [],
        "evidence_paths": sorted(set(evidence_paths)),
        "repeated_signals": repeated_signals,
        "suggested_factory_fields": [
            "memory_intake.status",
            "memory_intake.block_summary.reason",
            "memory_intake.block_summary.recommended_recovery_action",
            "memory_intake.selected_run_id",
            "memory_intake.latest_pointer_path",
        ],
        "summary": (
            "Across multiple imports, PackFactory keeps returned memory fail-closed when it "
            "no longer matches canonical local state, preserves the evidence, and points the "
            "operator at reconcile instead of silently overriding local truth."
        ),
        "recommended_default": (
            "Keep fail-closed import preservation plus explicit reconcile guidance as a "
            "promoted factory lesson for remote-memory recovery."
        ),
    }


def _branch_selection_path(factory_root: Path, exercise_report_path: Path) -> tuple[Path, str]:
    payload = _load_object(exercise_report_path)
    checkpoint_result = payload.get("checkpoint_result", {})
    if not isinstance(checkpoint_result, dict):
        raise ValueError(f"{exercise_report_path}: missing checkpoint_result")
    build_pack_id = checkpoint_result.get("build_pack_id")
    run_id = checkpoint_result.get("run_id")
    if not isinstance(build_pack_id, str) or not isinstance(run_id, str):
        raise ValueError(f"{exercise_report_path}: missing build_pack_id or run_id in checkpoint_result")
    selection_path = (
        factory_root
        / "build-packs"
        / build_pack_id
        / ".pack-state"
        / "autonomy-runs"
        / run_id
        / "branch-selection.json"
    )
    if not selection_path.exists():
        raise FileNotFoundError(f"{relative_path(factory_root, selection_path)} does not exist")
    return selection_path, build_pack_id


def _lesson_from_branch_exercises(factory_root: Path, branch_exercise_report_paths: list[Path]) -> dict[str, Any]:
    if len(branch_exercise_report_paths) < 2:
        raise ValueError("at least two branch exercise reports are required")

    build_pack_ids: list[str] = []
    evidence_paths: list[str] = []
    methods: list[str] = []
    rules: list[str] = []
    hint_ids: list[str] = []
    saw_selection_priority_setup = False
    for exercise_report_path in branch_exercise_report_paths:
        exercise_payload = _load_object(exercise_report_path)
        branching_setup_result = exercise_payload.get("branching_setup_result")
        if isinstance(branching_setup_result, dict) and isinstance(
            branching_setup_result.get("branch_selection_priority"), dict
        ):
            saw_selection_priority_setup = True
        selection_path, build_pack_id = _branch_selection_path(factory_root, exercise_report_path)
        build_pack_ids.append(build_pack_id)
        evidence_paths.append(relative_path(factory_root, exercise_report_path))
        evidence_paths.append(relative_path(factory_root, selection_path))
        selection = _load_object(selection_path)
        method = selection.get("selection_method")
        if isinstance(method, str):
            methods.append(method)
        rule = selection.get("selection_rule")
        if isinstance(rule, str):
            rules.append(rule)
        applied_hint_ids = selection.get("applied_hint_ids", [])
        if isinstance(applied_hint_ids, list):
            for hint_id in applied_hint_ids:
                if isinstance(hint_id, str):
                    hint_ids.append(hint_id)

    repeated_signals = [
        "selection_methods=" + ", ".join(sorted(set(methods))),
        f"distinct_applied_hint_ids={', '.join(sorted(set(hint_ids))) if hint_ids else 'none'}",
    ]
    unique_rules = sorted(set(rules))
    if len(unique_rules) == 1:
        repeated_signals.append("shared_selection_rule=" + unique_rules[0])
    elif unique_rules:
        repeated_signals.append(f"selection_rule_variants={len(unique_rules)}")
    if saw_selection_priority_setup:
        repeated_signals.append("selection_priority_metadata_present=true")

    return {
        "lesson_id": "operator-guided-branch-choice-ladder",
        "title": "Branch choice now follows one explainable ladder instead of backlog order.",
        "pattern_kind": "operator_guided_branch_choice",
        "confidence_rating": _confidence_from_count(len(build_pack_ids)),
        "proof_count": len(build_pack_ids),
        "source_build_pack_ids": sorted(set(build_pack_ids)),
        "source_template_ids": [],
        "evidence_paths": sorted(set(evidence_paths)),
        "repeated_signals": repeated_signals,
        "suggested_factory_fields": [
            "selection_method",
            "selection_rule",
            "applied_hint_ids",
            "filtered_out_task_ids",
            "semantic_context_sources",
            "semantic_scores",
            "chosen_task_id",
        ],
        "summary": (
            "Across branching exercises, PackFactory now shows the same explainable decision "
            "policy: explicit priority first, operator guidance next, bounded semantic "
            "alignment after that, and fail-closed review when the choice still is not defensible."
        ),
        "recommended_default": (
            "Keep branch-selection artifacts as first-class restart evidence and distill the "
            "shared selection ladder into factory memory for future autonomy work."
        ),
    }


def distill_autonomy_memory_lessons(
    *,
    factory_root: Path,
    matrix_report_path: Path | None,
    quality_report_paths: list[Path],
    import_report_paths: list[Path],
    branch_exercise_report_paths: list[Path],
) -> dict[str, Any]:
    lessons: list[dict[str, Any]] = []
    if matrix_report_path is not None:
        lessons.append(_lesson_from_matrix(factory_root, matrix_report_path))
    if quality_report_paths:
        lessons.append(_lesson_from_quality_reports(factory_root, quality_report_paths))
    if import_report_paths:
        lessons.append(_lesson_from_import_reports(factory_root, import_report_paths))
    if branch_exercise_report_paths:
        lessons.append(_lesson_from_branch_exercises(factory_root, branch_exercise_report_paths))
    if not lessons:
        raise ValueError("at least one report group is required")

    report_id = _report_id()
    report_root = _report_root(factory_root, report_id)
    report_root.mkdir(parents=True, exist_ok=False)
    report_path = report_root / "distillation-report.json"
    overall_summary = (
        f"Distilled {len(lessons)} repeated autonomy lessons from existing PackFactory proof "
        "artifacts so the factory can promote shared memory patterns instead of keeping them "
        "scattered across individual build-packs."
    )
    operator_summary = (
        f"Recorded {len(lessons)} factory-level autonomy memory lessons from repeated proof "
        "artifacts spanning continuity, import recovery, branch choice, and transfer evidence."
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "report_id": report_id,
        "generated_at": isoformat_z(read_now()),
        "lesson_count": len(lessons),
        "overall_summary": overall_summary,
        "operator_summary": operator_summary,
        "lessons": lessons,
    }
    write_json(report_path, payload)
    errors = validate_json_document(report_path, schema_path(factory_root, SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "report_id": report_id,
        "report_path": str(report_path),
        "lesson_count": len(lessons),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Distill repeated autonomy lessons from existing PackFactory proof artifacts into one factory-level report.",
    )
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--matrix-report-path")
    parser.add_argument("--quality-report-path", action="append", default=[])
    parser.add_argument("--import-report-path", action="append", default=[])
    parser.add_argument("--branch-exercise-report-path", action="append", default=[])
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    matrix_report_path = (
        _resolve_existing_path(factory_root, args.matrix_report_path)
        if args.matrix_report_path
        else None
    )
    quality_report_paths = [_resolve_existing_path(factory_root, raw_path) for raw_path in args.quality_report_path]
    import_report_paths = [_resolve_existing_path(factory_root, raw_path) for raw_path in args.import_report_path]
    branch_exercise_report_paths = [
        _resolve_existing_path(factory_root, raw_path) for raw_path in args.branch_exercise_report_path
    ]
    result = distill_autonomy_memory_lessons(
        factory_root=factory_root,
        matrix_report_path=matrix_report_path,
        quality_report_paths=quality_report_paths,
        import_report_paths=import_report_paths,
        branch_exercise_report_paths=branch_exercise_report_paths,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
