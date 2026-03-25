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

from factory_ops import discover_pack, load_json, resolve_factory_root, schema_path, validate_json_document, write_json


SCHEMA_NAME = "work-state.schema.json"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def apply_branch_selection_hint(
    *,
    factory_root: Path,
    build_pack_id: str,
    hint_id: str,
    summary: str,
    preferred_task_ids: list[str],
    avoid_task_ids: list[str],
    remaining_applications: int | None,
    active: bool,
) -> dict[str, Any]:
    target_pack = discover_pack(factory_root, build_pack_id)
    if target_pack.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")

    work_state_path = target_pack.pack_root / "status/work-state.json"
    task_backlog_path = target_pack.pack_root / "tasks/active-backlog.json"
    work_state = _load_object(work_state_path)
    task_backlog = _load_object(task_backlog_path)
    known_task_ids = {
        str(task.get("task_id"))
        for task in cast(list[dict[str, Any]], task_backlog.get("tasks", []))
        if isinstance(task, dict) and isinstance(task.get("task_id"), str)
    }
    if not preferred_task_ids and not avoid_task_ids:
        raise ValueError("at least one of preferred_task_ids or avoid_task_ids is required")
    unknown = [task_id for task_id in preferred_task_ids + avoid_task_ids if task_id not in known_task_ids]
    if unknown:
        raise ValueError(f"branch-selection hints referenced unknown task ids: {', '.join(sorted(set(unknown)))}")
    overlap = sorted(set(preferred_task_ids).intersection(avoid_task_ids))
    if overlap:
        raise ValueError(f"task ids cannot appear in both preferred and avoid lists: {', '.join(overlap)}")
    if remaining_applications is not None and remaining_applications < 1:
        raise ValueError("remaining_applications must be at least 1 when set explicitly")

    hints = work_state.get("branch_selection_hints", [])
    if not isinstance(hints, list):
        hints = []
    existing_hint = next(
        (
            cast(dict[str, Any], hint)
            for hint in hints
            if isinstance(hint, dict) and hint.get("hint_id") == hint_id
        ),
        None,
    )
    updated_hints = [hint for hint in hints if not (isinstance(hint, dict) and hint.get("hint_id") == hint_id)]
    if remaining_applications is None and isinstance(existing_hint, dict):
        prior_remaining = existing_hint.get("remaining_applications")
        if isinstance(prior_remaining, int):
            remaining_applications = prior_remaining
    updated_hints.append(
        {
            "hint_id": hint_id,
            "summary": summary,
            "active": active,
            **({"remaining_applications": remaining_applications} if remaining_applications is not None else {}),
            **({"preferred_task_ids": preferred_task_ids} if preferred_task_ids else {}),
            **({"avoid_task_ids": avoid_task_ids} if avoid_task_ids else {}),
        }
    )
    work_state["branch_selection_hints"] = updated_hints
    write_json(work_state_path, work_state)
    errors = validate_json_document(work_state_path, schema_path(factory_root, SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "build_pack_id": build_pack_id,
        "work_state_path": str(work_state_path),
        "hint_id": hint_id,
        "preferred_task_ids": preferred_task_ids,
        "avoid_task_ids": avoid_task_ids,
        "remaining_applications": remaining_applications,
        "active": active,
        "hint_count": len(updated_hints),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply or update an operator branch-selection hint in canonical work-state.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--build-pack-id", required=True)
    parser.add_argument("--hint-id", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--preferred-task-id", dest="preferred_task_ids", action="append", default=[])
    parser.add_argument("--avoid-task-id", dest="avoid_task_ids", action="append", default=[])
    parser.add_argument("--remaining-applications", type=int)
    parser.add_argument("--inactive", action="store_true")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = apply_branch_selection_hint(
        factory_root=resolve_factory_root(args.factory_root),
        build_pack_id=args.build_pack_id,
        hint_id=args.hint_id,
        summary=args.summary,
        preferred_task_ids=args.preferred_task_ids,
        avoid_task_ids=args.avoid_task_ids,
        remaining_applications=args.remaining_applications,
        active=not args.inactive,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
