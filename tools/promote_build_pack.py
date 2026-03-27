#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
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
AUTONOMY_REHEARSAL_WORKFLOW_ID = "multi_hop_autonomy_rehearsal"
AUTONOMY_QUALITY_SCORE_REPORT_VERSION = "autonomy-quality-score-report/v1"
AUTONOMY_QUALITY_RATING_ORDER = {
    "weak": 0,
    "mixed": 1,
    "good": 2,
    "strong": 3,
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
        "last_promoted_at": deployment["last_promoted_at"],
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


def _load_project_objective(pack_root: Path) -> dict[str, Any] | None:
    objective_path = pack_root / "contracts/project-objective.json"
    if not objective_path.exists():
        return None
    return _load_object(objective_path)


def _load_latest_memory_pointer(pack_root: Path) -> dict[str, Any] | None:
    latest_memory_path = pack_root / ".pack-state/agent-memory/latest-memory.json"
    if not latest_memory_path.exists():
        return None
    return _load_object(latest_memory_path)


def _normalize_task_id_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            return None
        items.append(item)
    return items


def _rehearsal_matches_current_state(
    report: dict[str, Any],
    *,
    readiness: dict[str, Any],
    work_state: dict[str, Any],
    latest_memory: dict[str, Any],
) -> bool:
    final_state = report.get("final_state")
    if not isinstance(final_state, dict):
        return False
    final_readiness = final_state.get("readiness")
    final_work_state = final_state.get("work_state")
    final_latest_memory = final_state.get("latest_memory")
    if not all(isinstance(payload, dict) for payload in (final_readiness, final_work_state, final_latest_memory)):
        return False

    current_completed = _normalize_task_id_list(work_state.get("completed_task_ids"))
    current_pending = _normalize_task_id_list(work_state.get("pending_task_ids"))
    final_completed = _normalize_task_id_list(final_work_state.get("completed_task_ids"))
    final_pending = _normalize_task_id_list(final_work_state.get("pending_task_ids"))
    if None in (current_completed, current_pending, final_completed, final_pending):
        return False

    return (
        final_readiness.get("readiness_state") == readiness.get("readiness_state")
        and final_readiness.get("ready_for_deployment") == readiness.get("ready_for_deployment")
        and final_work_state.get("autonomy_state") == work_state.get("autonomy_state")
        and final_work_state.get("active_task_id") == work_state.get("active_task_id")
        and final_work_state.get("next_recommended_task_id") == work_state.get("next_recommended_task_id")
        and final_completed == current_completed
        and final_pending == current_pending
        and final_latest_memory.get("pack_id") == latest_memory.get("pack_id")
        and final_latest_memory.get("selected_memory_id") == latest_memory.get("selected_memory_id")
        and final_latest_memory.get("selected_run_id") == latest_memory.get("selected_run_id")
        and final_latest_memory.get("selected_memory_path") == latest_memory.get("selected_memory_path")
    )


def _resolve_autonomy_rehearsal_evidence(
    *,
    factory_root: Path,
    pack_root: Path,
    pack_id: str,
    readiness: dict[str, Any],
) -> dict[str, Any] | None:
    project_objective = _load_project_objective(pack_root)
    if project_objective is None:
        return None

    requirement = project_objective.get("autonomy_rehearsal_requirement")
    if not isinstance(requirement, dict) or requirement.get("required_for_promotion") is not True:
        return None
    if requirement.get("workflow_id") != AUTONOMY_REHEARSAL_WORKFLOW_ID:
        raise ValueError("project objective autonomy rehearsal requirement declared an unsupported workflow")

    work_state = _load_object(pack_root / "status/work-state.json")
    latest_memory = _load_latest_memory_pointer(pack_root)
    if latest_memory is None:
        raise ValueError(
            "build pack requires completed multi-hop autonomy rehearsal evidence before promotion, "
            "but .pack-state/agent-memory/latest-memory.json is missing"
        )

    rehearsal_root = factory_root / ".pack-state" / "multi-hop-autonomy-rehearsals"
    if not rehearsal_root.exists():
        raise ValueError(
            "build pack requires completed multi-hop autonomy rehearsal evidence before promotion, "
            "but no rehearsal reports have been recorded yet"
        )

    rehearsal_schema = schema_path(factory_root, "multi-hop-autonomy-rehearsal-report.schema.json")
    compatible_candidates: list[tuple[str, Path, dict[str, Any]]] = []
    candidate_failures: list[str] = []
    for report_path in sorted(rehearsal_root.glob("*/rehearsal-report.json")):
        relative = relative_path(factory_root, report_path)
        report = _load_object(report_path)
        if report.get("target_build_pack_id") != pack_id:
            continue
        errors = validate_json_document(report_path, rehearsal_schema)
        if errors:
            candidate_failures.append(f"{relative}: {errors[0]}")
            continue
        if report.get("status") != "completed":
            candidate_failures.append(f"{relative}: rehearsal status was not completed")
            continue
        final_state = report.get("final_state")
        if not isinstance(final_state, dict):
            candidate_failures.append(f"{relative}: final_state must be an object")
            continue
        final_readiness = final_state.get("readiness")
        if not isinstance(final_readiness, dict) or final_readiness.get("ready_for_deployment") is not True:
            candidate_failures.append(f"{relative}: rehearsal did not finish at ready_for_deployment=true")
            continue
        if not _rehearsal_matches_current_state(
            report,
            readiness=readiness,
            work_state=work_state,
            latest_memory=latest_memory,
        ):
            candidate_failures.append(
                f"{relative}: rehearsal no longer matches the pack's current readiness, work-state, and latest-memory state"
            )
            continue
        generated_at = str(report.get("generated_at"))
        compatible_candidates.append((generated_at, report_path, report))

    if not compatible_candidates:
        if candidate_failures:
            raise ValueError(
                "build pack requires completed multi-hop autonomy rehearsal evidence before promotion, "
                f"but no compatible report was found. Latest issue: {candidate_failures[-1]}"
            )
        raise ValueError(
            "build pack requires completed multi-hop autonomy rehearsal evidence before promotion, "
            "but no report targeting this build pack was found"
        )

    compatible_candidates.sort(key=lambda item: item[0])
    _, selected_path, selected_report = compatible_candidates[-1]
    selected_relative = relative_path(factory_root, selected_path)
    final_state = selected_report["final_state"]
    final_readiness = final_state["readiness"]
    final_latest_memory = final_state["latest_memory"]
    return {
        "workflow_id": AUTONOMY_REHEARSAL_WORKFLOW_ID,
        "rehearsal_id": selected_report["rehearsal_id"],
        "report_path": selected_relative,
        "generated_at": selected_report["generated_at"],
        "status": selected_report["status"],
        "remote_target_label": selected_report["remote_target_label"],
        "latest_memory_run_id": final_latest_memory["selected_run_id"],
        "final_readiness_state": final_readiness["readiness_state"],
        "final_ready_for_deployment": final_readiness["ready_for_deployment"],
    }


def _score_matches_rehearsal(
    *,
    factory_root: Path,
    score_report: dict[str, Any],
    selected_rehearsal_path: Path,
    pack_id: str,
) -> bool:
    if score_report.get("schema_version") != AUTONOMY_QUALITY_SCORE_REPORT_VERSION:
        return False
    if score_report.get("target_build_pack_id") != pack_id:
        return False

    source_report_path = score_report.get("source_report_path")
    if not isinstance(source_report_path, str) or not source_report_path:
        return False
    source_path = Path(source_report_path)
    if not source_path.is_absolute():
        source_path = (factory_root / source_report_path).resolve()
    if source_path == selected_rehearsal_path:
        return True

    if score_report.get("source_report_kind") != "startup_compliance_rehearsal":
        return False
    if not source_path.exists():
        return False
    source_payload = _load_object(source_path)
    multi_hop_result = source_payload.get("multi_hop_rehearsal_result")
    if not isinstance(multi_hop_result, dict):
        return False
    embedded_report_path = multi_hop_result.get("report_path")
    if not isinstance(embedded_report_path, str) or not embedded_report_path:
        return False
    embedded_path = Path(embedded_report_path)
    if not embedded_path.is_absolute():
        embedded_path = (factory_root / embedded_report_path).resolve()
    return embedded_path == selected_rehearsal_path


def _resolve_autonomy_quality_evidence(
    *,
    factory_root: Path,
    pack_id: str,
    autonomy_rehearsal_evidence: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if autonomy_rehearsal_evidence is None:
        return None

    rehearsal_relative = autonomy_rehearsal_evidence.get("report_path")
    if not isinstance(rehearsal_relative, str) or not rehearsal_relative:
        return None
    selected_rehearsal_path = (factory_root / rehearsal_relative).resolve()
    score_root = factory_root / ".pack-state" / "autonomy-quality-scores"
    if not score_root.exists():
        return None

    score_schema = schema_path(factory_root, "autonomy-quality-score-report.schema.json")
    candidates: list[tuple[str, Path, dict[str, Any]]] = []
    for report_path in sorted(score_root.glob("*/score-report.json")):
        errors = validate_json_document(report_path, score_schema)
        if errors:
            continue
        report = _load_object(report_path)
        if not _score_matches_rehearsal(
            factory_root=factory_root,
            score_report=report,
            selected_rehearsal_path=selected_rehearsal_path,
            pack_id=pack_id,
        ):
            continue
        candidates.append((str(report.get("generated_at", "")), report_path, report))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    _, selected_score_path, selected_score_report = candidates[-1]
    return {
        "report_path": relative_path(factory_root, selected_score_path),
        "generated_at": selected_score_report["generated_at"],
        "source_report_kind": selected_score_report["source_report_kind"],
        "overall_score": selected_score_report["overall_score"],
        "overall_rating": selected_score_report["overall_rating"],
        "dimensions": selected_score_report["dimensions"],
        "findings": selected_score_report["findings"],
        "matched_rehearsal_report_path": rehearsal_relative,
    }


def _resolve_autonomy_quality_requirement(pack_root: Path) -> dict[str, Any] | None:
    project_objective = _load_project_objective(pack_root)
    if project_objective is None:
        return None
    requirement = project_objective.get("autonomy_quality_requirement")
    if not isinstance(requirement, dict):
        return None
    return requirement


def _evaluate_autonomy_quality_gate(
    *,
    quality_requirement: dict[str, Any] | None,
    quality_evidence: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if quality_requirement is None:
        return None

    gate: dict[str, Any] = {
        "enforcement_mode": "required" if quality_requirement.get("required_for_promotion") is True else "advisory",
        "status": "not_required",
        "summary": str(quality_requirement.get("summary", "")).strip() or "Autonomy quality is advisory.",
        "evaluated_report_path": quality_evidence.get("report_path") if isinstance(quality_evidence, dict) else None,
        "min_overall_rating": quality_requirement.get("min_overall_rating"),
        "min_overall_score": quality_requirement.get("min_overall_score"),
        "minimum_dimension_scores": quality_requirement.get("minimum_dimension_scores"),
    }

    if quality_requirement.get("required_for_promotion") is not True:
        return gate

    if quality_evidence is None:
        raise ValueError(
            "build pack requires autonomy-quality evidence before promotion, "
            "but no compatible score report was found for the selected autonomy rehearsal"
        )

    min_overall_rating = quality_requirement.get("min_overall_rating")
    actual_overall_rating = quality_evidence.get("overall_rating")
    if isinstance(min_overall_rating, str):
        if AUTONOMY_QUALITY_RATING_ORDER.get(str(actual_overall_rating), -1) < AUTONOMY_QUALITY_RATING_ORDER[min_overall_rating]:
            raise ValueError(
                "build pack requires autonomy-quality overall rating "
                f"`{min_overall_rating}` or better before promotion, but matched evidence was `{actual_overall_rating}`"
            )

    min_overall_score = quality_requirement.get("min_overall_score")
    actual_overall_score = quality_evidence.get("overall_score")
    if isinstance(min_overall_score, (int, float)):
        actual_overall_score_text = (
            f"{float(actual_overall_score):.1f}" if isinstance(actual_overall_score, (int, float)) else "missing"
        )
        if not isinstance(actual_overall_score, (int, float)) or float(actual_overall_score) < float(min_overall_score):
            raise ValueError(
                "build pack requires autonomy-quality overall score "
                f">= {float(min_overall_score):.1f} before promotion, but matched evidence was {actual_overall_score_text}"
            )

    minimum_dimension_scores = quality_requirement.get("minimum_dimension_scores")
    if isinstance(minimum_dimension_scores, dict):
        dimensions = quality_evidence.get("dimensions")
        if not isinstance(dimensions, dict):
            raise ValueError("matched autonomy-quality evidence did not include dimension scores")
        for dimension_id, minimum_score in minimum_dimension_scores.items():
            dimension = dimensions.get(dimension_id)
            if not isinstance(dimension, dict):
                raise ValueError(
                    "build pack requires autonomy-quality dimension "
                    f"`{dimension_id}` >= {float(minimum_score):.1f} before promotion, but that dimension was missing"
                )
            if dimension.get("status") != "scored":
                raise ValueError(
                    "build pack requires autonomy-quality dimension "
                    f"`{dimension_id}` >= {float(minimum_score):.1f} before promotion, but that dimension was not scored"
                )
            actual_dimension_score = dimension.get("score")
            actual_dimension_score_text = (
                f"{float(actual_dimension_score):.1f}" if isinstance(actual_dimension_score, (int, float)) else "missing"
            )
            if not isinstance(actual_dimension_score, (int, float)) or float(actual_dimension_score) < float(minimum_score):
                raise ValueError(
                    "build pack requires autonomy-quality dimension "
                    f"`{dimension_id}` >= {float(minimum_score):.1f} before promotion, but matched evidence was {actual_dimension_score_text}"
                )

    gate["status"] = "pass"
    return gate


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


def _refresh_metadata(
    *,
    requested: bool,
    performed: bool,
    mode: str,
    source_promotion_id: str,
    source_promotion_report_path: str,
) -> dict[str, Any]:
    return {
        "requested": requested,
        "performed": performed,
        "mode": mode,
        "environment_unchanged": True,
        "release_id_unchanged": True,
        "source_promotion_id": source_promotion_id,
        "source_promotion_report_path": source_promotion_report_path,
    }


def _refresh_report_is_current(report: dict[str, Any]) -> bool:
    refresh = report.get("reconcile_refresh")
    if not isinstance(refresh, dict):
        return False
    return (
        refresh.get("requested") is True
        and refresh.get("performed") is True
        and refresh.get("mode") == "canonical_evidence_refresh"
    )


def _reserve_promotion_identity(
    *,
    factory_root: Path,
    pack_root: Path,
    pack_id: str,
    target_environment: str,
    moment: datetime,
) -> tuple[str, str, str]:
    current = moment.astimezone().replace(microsecond=0)
    promotion_log_path = factory_root / PROMOTION_LOG_PATH
    existing_promotion_ids: set[str] = set()
    if promotion_log_path.exists():
        promotion_log = _load_object(promotion_log_path)
        events = promotion_log.get("events", [])
        if not isinstance(events, list):
            raise ValueError(f"{promotion_log_path}: events must be an array")
        for event in events:
            if isinstance(event, dict):
                promotion_id = event.get("promotion_id")
                if isinstance(promotion_id, str):
                    existing_promotion_ids.add(promotion_id)
    while True:
        generated_at = isoformat_z(current)
        promotion_id = f"promote-{pack_id}-{target_environment}-{timestamp_token(current)}"
        report_relative = f"eval/history/{promotion_id}/promotion-report.json"
        if promotion_id in existing_promotion_ids or (pack_root / report_relative).exists():
            current += timedelta(seconds=1)
            continue
        return generated_at, promotion_id, report_relative


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
    refresh_requested = bool(request.get("refresh_canonical_evidence", False))
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
    if refresh_requested and not (current_env == target_environment and current_release_id == release_id):
        raise ValueError("canonical evidence refresh requires an already-active same-release assignment")
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
        generated_at, promotion_id, report_relative = _reserve_promotion_identity(
            factory_root=factory_root,
            pack_root=pack_root,
            pack_id=pack_id,
            target_environment=target_environment,
            moment=read_now(),
        )
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
        if refresh_requested:
            if (
                _refresh_report_is_current(canonical_report)
                and deployment.get("deployment_transaction_id") == canonical_promotion_id
                and pointer_payload.get("deployment_transaction_id") == canonical_promotion_id
                and pointer_payload.get("promotion_evidence_ref") == canonical_report_relative
            ):
                return {
                    "status": "reconciled",
                    "promotion_id": canonical_promotion_id,
                    "promotion_report_path": str(canonical_report_path),
                }
            generated_at, promotion_id, report_relative = _reserve_promotion_identity(
                factory_root=factory_root,
                pack_root=pack_root,
                pack_id=pack_id,
                target_environment=target_environment,
                moment=read_now(),
            )
            pointer_payload = _deployment_pointer(
                pack_id=pack_id,
                release_id=release_id,
                target_environment=target_environment,
                promotion_id=promotion_id,
                report_relative=report_relative,
                generated_at=generated_at,
            )
            write_json(pointer_path, pointer_payload)
            deployment_changed = False
            if deployment.get("deployment_transaction_id") != promotion_id:
                deployment["deployment_transaction_id"] = promotion_id
                deployment_changed = True
            if deployment.get("last_promoted_at") != generated_at:
                deployment["last_promoted_at"] = generated_at
                deployment_changed = True
            if deployment.get("projection_state") != "projected":
                deployment["projection_state"] = "projected"
                deployment_changed = True
            if verification_timestamp is not None and deployment.get("last_verified_at") != verification_timestamp:
                deployment["last_verified_at"] = verification_timestamp
                deployment_changed = True
            if deployment_changed:
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
                "autonomy_rehearsal_evidence": None,
                "autonomy_quality_evidence": None,
                "autonomy_quality_gate": None,
                "reconcile_refresh": _refresh_metadata(
                    requested=True,
                    performed=True,
                    mode="canonical_evidence_refresh",
                    source_promotion_id=canonical_promotion_id,
                    source_promotion_report_path=canonical_report_relative,
                ),
                "pre_promotion_state": pre_state,
                "post_promotion_state": _state_snapshot(lifecycle, deployment),
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
                        "action_id": "update_deployment_state",
                        "status": "completed" if deployment_changed else "reconciled",
                        "target_path": f"build-packs/{pack_id}/status/deployment.json",
                        "summary": "Refreshed the canonical deployment state for the active release.",
                    },
                    {
                        "action_id": "write_deployment_pointer",
                        "status": "completed",
                        "target_path": pointer_relative,
                        "summary": "Wrote a refreshed canonical deployment pointer.",
                    },
                    {
                        "action_id": "update_registry_entry",
                        "status": "completed",
                        "target_path": "registry/build-packs.json",
                        "summary": "Refreshed the build-pack registry entry for the canonical promotion witness.",
                    },
                    {
                        "action_id": "append_operation_log",
                        "status": "completed",
                        "target_path": "registry/promotion-log.json",
                        "summary": "Appended the refreshed promotion event to the factory operation log.",
                    },
                    {
                        "action_id": "write_promotion_report",
                        "status": "completed",
                        "target_path": f"build-packs/{pack_id}/{report_relative}",
                        "summary": "Wrote the refreshed canonical promotion evidence report.",
                    },
                ],
                "evidence_paths": [
                    f"build-packs/{pack_id}/{report_relative}",
                    canonical_report_relative,
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
            "autonomy_rehearsal_evidence": None,
            "autonomy_quality_evidence": None,
            "autonomy_quality_gate": None,
            "reconcile_refresh": None,
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

    autonomy_rehearsal_evidence = _resolve_autonomy_rehearsal_evidence(
        factory_root=factory_root,
        pack_root=pack_root,
        pack_id=pack_id,
        readiness=readiness,
    )
    autonomy_quality_evidence = _resolve_autonomy_quality_evidence(
        factory_root=factory_root,
        pack_id=pack_id,
        autonomy_rehearsal_evidence=autonomy_rehearsal_evidence,
    )
    autonomy_quality_requirement = _resolve_autonomy_quality_requirement(pack_root)
    autonomy_quality_gate = _evaluate_autonomy_quality_gate(
        quality_requirement=autonomy_quality_requirement,
        quality_evidence=autonomy_quality_evidence,
    )

    generated_at, promotion_id, report_relative = _reserve_promotion_identity(
        factory_root=factory_root,
        pack_root=pack_root,
        pack_id=pack_id,
        target_environment=target_environment,
        moment=read_now(),
    )
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
        "autonomy_rehearsal_evidence": autonomy_rehearsal_evidence,
        "autonomy_quality_evidence": autonomy_quality_evidence,
        "autonomy_quality_gate": autonomy_quality_gate,
        "reconcile_refresh": None,
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
            *(
                [
                    {
                        "action_id": "verify_autonomy_rehearsal_evidence",
                        "status": "reconciled",
                        "target_path": autonomy_rehearsal_evidence["report_path"],
                        "summary": "Verified the completed multi-hop autonomy rehearsal that matched the pack's current canonical state.",
                    }
                ]
                if autonomy_rehearsal_evidence is not None
                else []
            ),
            *(
                [
                    {
                        "action_id": "verify_autonomy_quality_evidence",
                        "status": "reconciled",
                        "target_path": autonomy_quality_evidence["report_path"],
                        "summary": (
                            "Recorded bounded autonomy-quality evidence as an advisory promotion signal "
                            f"with rating `{autonomy_quality_evidence['overall_rating']}`."
                        ),
                    }
                ]
                if autonomy_quality_evidence is not None
                else []
            ),
            *(
                [
                    {
                        "action_id": "verify_autonomy_quality_gate",
                        "status": "completed",
                        "target_path": autonomy_quality_evidence["report_path"],
                        "summary": (
                            "Verified that the matched autonomy-quality evidence satisfied the "
                            "pack's bounded promotion-time autonomy-quality requirement."
                        ),
                    }
                ]
                if autonomy_quality_gate is not None and autonomy_quality_gate.get("enforcement_mode") == "required"
                else []
            ),
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
            *( [autonomy_rehearsal_evidence["report_path"]] if autonomy_rehearsal_evidence is not None else [] ),
            *( [autonomy_quality_evidence["report_path"]] if autonomy_quality_evidence is not None else [] ),
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
