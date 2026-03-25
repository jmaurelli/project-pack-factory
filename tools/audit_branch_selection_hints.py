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
    discover_pack,
    isoformat_z,
    load_json,
    read_now,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


SCHEMA_NAME = "branch-selection-hint-audit-report.schema.json"
SCHEMA_VERSION = "branch-selection-hint-audit-report/v1"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _hint_is_active(hint: dict[str, Any]) -> bool:
    if hint.get("active") is False:
        return False
    remaining_applications = hint.get("remaining_applications")
    return not (isinstance(remaining_applications, int) and remaining_applications <= 0)


def _task_ids_from_hint(hint: dict[str, Any]) -> list[str]:
    task_ids: list[str] = []
    for field in ("preferred_task_ids", "avoid_task_ids"):
        value = hint.get(field)
        if not isinstance(value, list):
            continue
        for task_id in value:
            if isinstance(task_id, str):
                task_ids.append(task_id)
    return task_ids


def _recent_branch_evidence(pack_root: Path) -> list[dict[str, Any]]:
    autonomy_root = pack_root / ".pack-state" / "autonomy-runs"
    if not autonomy_root.exists():
        return []
    candidates: list[tuple[str, dict[str, Any]]] = []
    for branch_path in autonomy_root.glob("*/branch-selection.json"):
        try:
            payload = _load_object(branch_path)
        except Exception:
            continue
        recorded_at = payload.get("recorded_at")
        if not isinstance(recorded_at, str):
            continue
        candidates.append(
            (
                recorded_at,
                {
                    "run_id": payload.get("run_id"),
                    "recorded_at": recorded_at,
                    "selection_method": payload.get("selection_method"),
                    "chosen_task_id": payload.get("chosen_task_id"),
                    "applied_hint_ids": payload.get("applied_hint_ids", []),
                    "consumed_hint_ids": payload.get("consumed_hint_ids", []),
                    "deactivated_hint_ids": payload.get("deactivated_hint_ids", []),
                    "branch_selection_path": branch_path.relative_to(pack_root).as_posix(),
                },
            )
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in candidates[:5]]


def audit_branch_selection_hints(
    *,
    factory_root: Path,
    build_pack_id: str,
    cleanup_exhausted: bool,
    audited_by: str,
) -> dict[str, Any]:
    target_pack = discover_pack(factory_root, build_pack_id)
    if target_pack.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")

    pack_root = target_pack.pack_root
    work_state_path = pack_root / "status" / "work-state.json"
    backlog_path = pack_root / "tasks" / "active-backlog.json"
    work_state = _load_object(work_state_path)
    backlog = _load_object(backlog_path)
    tasks = cast(list[dict[str, Any]], backlog.get("tasks", []))
    known_task_ids = {
        str(task.get("task_id"))
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("task_id"), str)
    }

    raw_hints = work_state.get("branch_selection_hints", [])
    hints = [cast(dict[str, Any], hint) for hint in raw_hints if isinstance(hint, dict)]

    active_hint_ids: list[str] = []
    inactive_hint_ids: list[str] = []
    exhausted_hint_ids: list[str] = []
    cleanup_candidate_hint_ids: list[str] = []
    unknown_reference_details: list[dict[str, Any]] = []

    for hint in hints:
        hint_id = hint.get("hint_id")
        if not isinstance(hint_id, str):
            continue
        referenced_task_ids = _task_ids_from_hint(hint)
        unknown_task_ids = sorted({task_id for task_id in referenced_task_ids if task_id not in known_task_ids})
        if unknown_task_ids:
            unknown_reference_details.append(
                {
                    "hint_id": hint_id,
                    "unknown_task_ids": unknown_task_ids,
                }
            )
        remaining_applications = hint.get("remaining_applications")
        if isinstance(remaining_applications, int) and remaining_applications <= 0:
            exhausted_hint_ids.append(hint_id)
        if _hint_is_active(hint):
            active_hint_ids.append(hint_id)
        else:
            inactive_hint_ids.append(hint_id)
        if hint.get("active") is False and isinstance(remaining_applications, int) and remaining_applications <= 0:
            cleanup_candidate_hint_ids.append(hint_id)

    removed_hint_ids: list[str] = []
    if cleanup_exhausted and cleanup_candidate_hint_ids:
        work_state["branch_selection_hints"] = [
            hint
            for hint in hints
            if not (isinstance(hint, dict) and isinstance(hint.get("hint_id"), str) and hint.get("hint_id") in set(cleanup_candidate_hint_ids))
        ]
        write_json(work_state_path, work_state)
        removed_hint_ids = sorted(set(cleanup_candidate_hint_ids))
    if cleanup_exhausted:
        errors = validate_json_document(work_state_path, schema_path(factory_root, "work-state.schema.json"))
        if errors:
            raise ValueError("; ".join(errors))

    report_token = timestamp_token(read_now())
    report_dir = pack_root / "eval" / "history" / f"branch-selection-hint-audit-{report_token}"
    if report_dir.exists():
        suffix = 2
        while True:
            candidate = pack_root / "eval" / "history" / f"branch-selection-hint-audit-{report_token}-{suffix}"
            if not candidate.exists():
                report_dir = candidate
                break
            suffix += 1
    report_dir.mkdir(parents=True, exist_ok=False)
    report_path = report_dir / "branch-selection-hint-audit-report.json"
    recent_branch_evidence = _recent_branch_evidence(pack_root)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": isoformat_z(read_now()),
        "build_pack_id": build_pack_id,
        "status": "completed",
        "audited_by": audited_by,
        "work_state_path": work_state_path.relative_to(pack_root).as_posix(),
        "cleanup_requested": cleanup_exhausted,
        "hint_summary": {
            "hint_count_before_cleanup": len(hints),
            "active_hint_ids": active_hint_ids,
            "inactive_hint_ids": inactive_hint_ids,
            "exhausted_hint_ids": exhausted_hint_ids,
            "cleanup_candidate_hint_ids": cleanup_candidate_hint_ids,
            "unknown_reference_details": unknown_reference_details,
        },
        "recent_branch_evidence": recent_branch_evidence,
        "cleanup_result": {
            "removed_hint_ids": removed_hint_ids,
            "remaining_hint_count": len(cast(list[Any], work_state.get("branch_selection_hints", []))),
        },
    }
    write_json(report_path, report)
    errors = validate_json_document(report_path, schema_path(factory_root, SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "build_pack_id": build_pack_id,
        "report_path": str(report_path),
        "active_hint_ids": active_hint_ids,
        "cleanup_candidate_hint_ids": cleanup_candidate_hint_ids,
        "removed_hint_ids": removed_hint_ids,
        "recent_branch_evidence_count": len(recent_branch_evidence),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit and optionally clean up branch-selection hints for a build-pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--build-pack-id", required=True)
    parser.add_argument("--cleanup-exhausted", action="store_true")
    parser.add_argument("--audited-by", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = audit_branch_selection_hints(
        factory_root=resolve_factory_root(args.factory_root),
        build_pack_id=args.build_pack_id,
        cleanup_exhausted=args.cleanup_exhausted,
        audited_by=args.audited_by,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
