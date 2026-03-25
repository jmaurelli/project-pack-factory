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


REPORT_SCHEMA_NAME = "autonomy-quality-score-report.schema.json"
REPORT_SCHEMA_VERSION = "autonomy-quality-score-report/v1"
SCORE_PREFIX = "autonomy-quality-score"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _score_id(report_path: Path) -> str:
    stem = report_path.parent.name.replace(".", "_")
    return f"{SCORE_PREFIX}-{stem}-{timestamp_token(read_now())}"


def _score_root(factory_root: Path, score_id: str) -> Path:
    return factory_root / ".pack-state" / "autonomy-quality-scores" / score_id


def _dimension(
    *,
    score: float | None,
    status: str,
    summary: str,
    evidence_paths: list[str],
    details: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "score": score,
        "summary": summary,
        "evidence_paths": evidence_paths,
        "details": details or [],
    }


def _imported_run_summary_path(import_report_path: Path) -> Path:
    return import_report_path.parent / "external-runtime-evidence" / "artifacts" / "run-summary.json"


def _average(values: list[float]) -> float | None:
    return None if not values else round(sum(values) / len(values), 2)


def _resolve_rehearsal_payload(report_path: Path) -> tuple[str, dict[str, Any], Path]:
    payload = _load_object(report_path)
    schema_version = payload.get("schema_version")
    if schema_version == "multi-hop-autonomy-rehearsal-report/v1":
        return "multi_hop_autonomy_rehearsal", payload, report_path
    if schema_version == "startup-compliance-rehearsal-report/v1":
        embedded = payload.get("multi_hop_rehearsal_result")
        if not isinstance(embedded, dict):
            raise ValueError(f"{report_path}: startup-compliance rehearsal missing multi_hop_rehearsal_result")
        embedded_report_path = embedded.get("report_path")
        if not isinstance(embedded_report_path, str) or not embedded_report_path:
            raise ValueError(f"{report_path}: startup-compliance rehearsal missing multi-hop report_path")
        return "startup_compliance_rehearsal", payload, Path(embedded_report_path)
    raise ValueError(f"{report_path}: unsupported report schema_version {schema_version!r}")


def score_autonomy_quality(*, factory_root: Path, report_path: Path) -> dict[str, Any]:
    source_kind, source_payload, multi_hop_report_path = _resolve_rehearsal_payload(report_path)
    multi_hop_payload = _load_object(multi_hop_report_path)
    target_build_pack_id = cast(str, multi_hop_payload["target_build_pack_id"])
    target_build_pack_root = Path(cast(str, multi_hop_payload["target_build_pack_root"]))
    score_id = _score_id(report_path)
    score_root = _score_root(factory_root, score_id)
    score_root.mkdir(parents=True, exist_ok=False)

    checkpoint_summary_path = Path(cast(str, cast(dict[str, Any], multi_hop_payload["checkpoint_result"])["run_summary_path"]))
    checkpoint_summary = _load_object(checkpoint_summary_path)
    active_import_report_path = Path(
        cast(str, cast(dict[str, Any], cast(dict[str, Any], multi_hop_payload["active_task_continuity_result"])["roundtrip_result"])["import_report_path"])
    )
    ready_import_report_path = Path(
        cast(str, cast(dict[str, Any], cast(dict[str, Any], multi_hop_payload["ready_boundary_continuity_result"])["roundtrip_result"])["import_report_path"])
    )
    active_import_report = _load_object(active_import_report_path)
    ready_import_report = _load_object(ready_import_report_path)
    active_run_summary_path = _imported_run_summary_path(active_import_report_path)
    ready_run_summary_path = _imported_run_summary_path(ready_import_report_path)
    active_run_summary = _load_object(active_run_summary_path)
    ready_run_summary = _load_object(ready_run_summary_path)
    reconcile_result = cast(dict[str, Any], multi_hop_payload["reconcile_result"])
    canonical_refresh = cast(dict[str, Any], multi_hop_payload["canonical_readiness_refresh_result"])
    final_state = cast(dict[str, Any], multi_hop_payload["final_state"])

    scored_values: list[float] = []
    dimensions: dict[str, dict[str, Any]] = {}

    handoff_values: list[float] = []
    handoff_details: list[str] = []
    for name, summary in (("checkpoint", checkpoint_summary), ("active_task_remote", active_run_summary), ("ready_boundary_remote", ready_run_summary)):
        metrics = cast(dict[str, Any], summary.get("metrics", {}))
        resume_correctness = metrics.get("resume_correctness")
        consistent_memory_use_rate = metrics.get("consistent_memory_use_rate")
        stale_memory_rate = metrics.get("stale_memory_rate")
        if isinstance(resume_correctness, (int, float)):
            handoff_values.append(float(resume_correctness) * 100.0)
            handoff_details.append(f"{name}: resume_correctness={resume_correctness}")
        if isinstance(consistent_memory_use_rate, (int, float)):
            handoff_values.append(float(consistent_memory_use_rate) * 100.0)
            handoff_details.append(f"{name}: consistent_memory_use_rate={consistent_memory_use_rate}")
        if isinstance(stale_memory_rate, (int, float)):
            handoff_values.append((1.0 - float(stale_memory_rate)) * 100.0)
            handoff_details.append(f"{name}: stale_memory_rate={stale_memory_rate}")
    handoff_score = _average(handoff_values)
    if handoff_score is not None:
        scored_values.append(handoff_score)
    dimensions["handoff_quality"] = _dimension(
        score=handoff_score,
        status="scored" if handoff_score is not None else "not_applicable",
        summary="Scores how consistently autonomy reused and trusted feedback memory across the checkpoint and remote continuity hops.",
        evidence_paths=[
            str(checkpoint_summary_path),
            str(active_run_summary_path),
            str(ready_run_summary_path),
        ],
        details=handoff_details,
    )

    replay_score = 100.0
    replay_details: list[str] = []
    ready_metrics = cast(dict[str, Any], ready_run_summary.get("metrics", {}))
    readiness_change = cast(dict[str, Any], ready_metrics.get("readiness_change_summary", {}))
    if ready_run_summary.get("failed_command_count") != 0:
        replay_score -= 25.0
        replay_details.append("ready-boundary continuity recorded failed commands")
    if readiness_change.get("state_advanced") is True:
        replay_score -= 35.0
        replay_details.append("ready-boundary continuity advanced readiness state instead of stopping cleanly")
    if ready_metrics.get("validation_evidence_gain") is True or ready_metrics.get("benchmark_evidence_gain") is True:
        replay_score -= 20.0
        replay_details.append("ready-boundary continuity generated new evidence instead of reusing the deployment boundary")
    if ready_run_summary.get("final_snapshot", {}).get("ready_for_deployment") is not True:
        replay_score -= 20.0
        replay_details.append("ready-boundary continuity did not finish at ready_for_deployment=true")
    replay_score = max(replay_score, 0.0)
    scored_values.append(replay_score)
    dimensions["replay_avoidance_quality"] = _dimension(
        score=replay_score,
        status="scored",
        summary="Scores whether the ready-boundary continuity hop stopped cleanly without replaying work or generating unnecessary evidence.",
        evidence_paths=[str(ready_run_summary_path)],
        details=replay_details,
    )

    recovery_score = 100.0
    recovery_details: list[str] = []
    active_memory_intake = cast(dict[str, Any], active_import_report.get("memory_intake", {}))
    ready_memory_intake = cast(dict[str, Any], ready_import_report.get("memory_intake", {}))
    if reconcile_result.get("memory_pointer_status") != "activated":
        recovery_score -= 40.0
        recovery_details.append(f"reconcile_result.memory_pointer_status={reconcile_result.get('memory_pointer_status')!r}")
    if ready_memory_intake.get("status") not in (None, "activated"):
        recovery_score -= 30.0
        recovery_details.append(f"ready import memory_intake.status={ready_memory_intake.get('status')!r}")
    if active_memory_intake.get("block_summary") is None:
        recovery_details.append("active import required no fail-closed memory promotion step")
    else:
        recovery_details.append("active import preserved fail-closed memory with block summary before reconcile")
    if final_state.get("latest_memory", {}).get("selected_run_id") != ready_memory_intake.get("selected_run_id"):
        recovery_score -= 30.0
        recovery_details.append("final latest-memory pointer did not match the ready-boundary imported run")
    recovery_score = max(recovery_score, 0.0)
    scored_values.append(recovery_score)
    dimensions["recovery_quality"] = _dimension(
        score=recovery_score,
        status="scored",
        summary="Scores how well imported runtime evidence and memory were preserved, reconciled, and reactivated back into canonical local state.",
        evidence_paths=[
            str(active_import_report_path),
            str(ready_import_report_path),
            cast(str, reconcile_result.get("report_path")),
        ],
        details=recovery_details,
    )

    outcome_score = 100.0
    outcome_details: list[str] = []
    if final_state.get("readiness", {}).get("ready_for_deployment") is not True:
        outcome_score -= 45.0
        outcome_details.append("final readiness was not ready_for_deployment=true")
    if canonical_refresh.get("post_refresh_ready_for_deployment") is not True:
        outcome_score -= 35.0
        outcome_details.append("canonical readiness refresh did not finish ready_for_deployment=true")
    if cast(dict[str, Any], active_run_summary.get("metrics", {})).get("task_completion_rate") != 1.0:
        outcome_score -= 20.0
        outcome_details.append("active-task remote run did not finish with task_completion_rate=1.0")
    outcome_score = max(outcome_score, 0.0)
    scored_values.append(outcome_score)
    dimensions["outcome_quality"] = _dimension(
        score=outcome_score,
        status="scored",
        summary="Scores whether the autonomy path finished with the expected canonical deployment-ready outcome.",
        evidence_paths=[
            str(multi_hop_report_path),
            str(active_run_summary_path),
        ],
        details=outcome_details,
    )

    branch_selection_paths = sorted(target_build_pack_root.glob(".pack-state/autonomy-runs/*/branch-selection.json"))
    if branch_selection_paths:
        branch_details: list[str] = []
        branch_values: list[float] = []
        for path in branch_selection_paths:
            payload = _load_object(path)
            method = payload.get("selection_method")
            if isinstance(method, str):
                branch_details.append(f"{path.name}: selection_method={method}")
                branch_values.append(100.0 if method in {"selection_priority", "operator_hint", "operator_hint_plus_semantic_alignment", "semantic_alignment"} else 70.0)
        branch_score = _average(branch_values)
        if branch_score is not None:
            scored_values.append(branch_score)
        dimensions["branch_choice_quality"] = _dimension(
            score=branch_score,
            status="scored" if branch_score is not None else "not_applicable",
            summary="Scores branch-choice evidence quality when a rehearsal traversed an explicit branch-selection decision.",
            evidence_paths=[str(path) for path in branch_selection_paths],
            details=branch_details,
        )
    else:
        dimensions["branch_choice_quality"] = _dimension(
            score=None,
            status="not_applicable",
            summary="No branch-selection artifacts were present for this rehearsal, so branch-choice quality was not scored.",
            evidence_paths=[],
        )

    block_evidence_paths = [str(active_run_summary_path), str(ready_run_summary_path), str(active_import_report_path), str(ready_import_report_path)]
    block_score: float | None = None
    block_details: list[str] = []
    block_summaries: list[dict[str, Any]] = []
    for payload in (active_run_summary, ready_run_summary):
        block_summary = payload.get("block_summary")
        if isinstance(block_summary, dict):
            block_summaries.append(cast(dict[str, Any], block_summary))
    for payload in (active_import_report, ready_import_report):
        intake = payload.get("memory_intake")
        if isinstance(intake, dict) and isinstance(intake.get("block_summary"), dict):
            block_summaries.append(cast(dict[str, Any], intake["block_summary"]))
    if block_summaries:
        valid_blocks = 0
        for summary in block_summaries:
            if isinstance(summary.get("reason"), str) and isinstance(summary.get("recommended_recovery_action"), str):
                valid_blocks += 1
                block_details.append(f"block reason={summary.get('reason')!r}")
        block_score = round((valid_blocks / len(block_summaries)) * 100.0, 2)
        scored_values.append(block_score)
        dimensions["block_reporting_quality"] = _dimension(
            score=block_score,
            status="scored",
            summary="Scores whether fail-closed block cases carried structured operator-facing summaries and recovery guidance.",
            evidence_paths=block_evidence_paths,
            details=block_details,
        )
    else:
        dimensions["block_reporting_quality"] = _dimension(
            score=None,
            status="not_applicable",
            summary="No block summaries were emitted during this rehearsal, so block-reporting quality was not scored.",
            evidence_paths=block_evidence_paths,
        )

    if source_kind == "startup_compliance_rehearsal":
        root_checks = cast(dict[str, Any], source_payload.get("root_marker_checks", {}))
        template_checks = cast(dict[str, Any], source_payload.get("template_marker_checks", {}))
        build_pack_check = cast(dict[str, Any], source_payload.get("build_pack_marker_check", {}))
        total_checks = len(root_checks) + len(template_checks) + 1
        passed_checks = sum(1 for result in [*root_checks.values(), *template_checks.values(), build_pack_check] if isinstance(result, dict) and result.get("status") == "pass")
        startup_score = round((passed_checks / total_checks) * 100.0, 2)
        scored_values.append(startup_score)
        dimensions["startup_compliance_quality"] = _dimension(
            score=startup_score,
            status="scored",
            summary="Scores whether the root, template, and generated build-pack startup surfaces all carried the required compliance markers.",
            evidence_paths=[str(report_path)],
            details=[f"passed_checks={passed_checks}", f"total_checks={total_checks}"],
        )

    overall_score = _average(scored_values)
    if overall_score is None:
        raise ValueError("autonomy quality scoring did not produce any scored dimensions")
    if overall_score >= 90:
        overall_rating = "strong"
    elif overall_score >= 75:
        overall_rating = "good"
    elif overall_score >= 60:
        overall_rating = "mixed"
    else:
        overall_rating = "weak"

    findings: list[str] = []
    for name, dimension in dimensions.items():
        score = dimension.get("score")
        if isinstance(score, (int, float)) and float(score) < 80.0:
            findings.append(f"{name} scored below 80")

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "score_id": score_id,
        "generated_at": isoformat_z(read_now()),
        "source_report_kind": source_kind,
        "source_report_path": str(report_path),
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(target_build_pack_root),
        "overall_score": overall_score,
        "overall_rating": overall_rating,
        "dimensions": dimensions,
        "findings": findings,
    }
    report_path_out = score_root / "score-report.json"
    write_json(report_path_out, report)
    errors = validate_json_document(report_path_out, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "score_id": score_id,
        "report_path": str(report_path_out),
        "target_build_pack_id": target_build_pack_id,
        "overall_score": overall_score,
        "overall_rating": overall_rating,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score PackFactory autonomy quality from an existing rehearsal report.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--report-path", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = score_autonomy_quality(
        factory_root=resolve_factory_root(args.factory_root),
        report_path=Path(args.report_path).resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
