from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assistant_contracts import load_memory_policy


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _memory_paths(project_root: Path) -> tuple[Path, Path]:
    policy = load_memory_policy(project_root)
    storage_root = project_root / str(policy["storage_root"])
    latest_pointer_path = project_root / str(policy["latest_pointer_path"])
    return storage_root, latest_pointer_path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def record_memory(
    project_root: Path,
    *,
    memory_id: str,
    category: str,
    summary: str,
    next_action: str | None,
    tags: list[str],
    replace_existing: bool,
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    storage_root, latest_pointer_path = _memory_paths(project_root)
    memory_path = storage_root / f"{memory_id}.json"
    existed = memory_path.exists()
    if existed and not replace_existing:
        raise ValueError(f"memory `{memory_id}` already exists; use replace_existing to overwrite it")
    if confidence is not None and not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    payload = {
        "schema_version": "codex-personal-assistant-memory/v2",
        "memory_id": memory_id,
        "category": category,
        "summary": summary,
        "next_action": next_action,
        "tags": sorted({tag for tag in tags if tag}),
        "source": source,
        "evidence": evidence,
        "confidence": confidence,
        "recorded_at": _isoformat_z(),
    }
    _write_json(memory_path, payload)
    pointer_payload = {
        "schema_version": "codex-personal-assistant-memory-pointer/v1",
        "selected_memory_id": memory_id,
        "selected_memory_path": str(memory_path.relative_to(project_root).as_posix()),
        "updated_at": payload["recorded_at"],
    }
    _write_json(latest_pointer_path, pointer_payload)
    return {
        "status": "pass",
        "memory_id": memory_id,
        "memory_path": str(memory_path.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "replaced_existing": bool(existed and replace_existing),
    }


def read_memory(project_root: Path) -> dict[str, Any]:
    storage_root, latest_pointer_path = _memory_paths(project_root)
    latest_pointer_name = latest_pointer_path.name
    memory_files = sorted(
        path
        for path in storage_root.glob("*.json")
        if path.is_file() and path.name != latest_pointer_name
    )
    latest_pointer: dict[str, Any] | None = None
    latest_memory: dict[str, Any] | None = None
    if latest_pointer_path.exists():
        latest_pointer = json.loads(latest_pointer_path.read_text(encoding="utf-8"))
        selected_path = latest_pointer.get("selected_memory_path")
        if isinstance(selected_path, str) and selected_path:
            candidate = project_root / selected_path
            if candidate.exists():
                latest_memory = json.loads(candidate.read_text(encoding="utf-8"))

    return {
        "status": "pass",
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "latest_pointer": latest_pointer,
        "latest_memory": latest_memory,
        "memory_count": len(memory_files),
        "available_memory_ids": [path.stem for path in memory_files],
    }


def delete_memory(project_root: Path, *, memory_id: str) -> dict[str, Any]:
    storage_root, latest_pointer_path = _memory_paths(project_root)
    memory_path = storage_root / f"{memory_id}.json"
    deleted = False
    if memory_path.exists():
        memory_path.unlink()
        deleted = True

    cleared_latest_pointer = False
    if latest_pointer_path.exists():
        latest_pointer = json.loads(latest_pointer_path.read_text(encoding="utf-8"))
        selected_memory_id = latest_pointer.get("selected_memory_id")
        selected_memory_path = latest_pointer.get("selected_memory_path")
        expected_relative = str(memory_path.relative_to(project_root).as_posix())
        if selected_memory_id == memory_id or selected_memory_path == expected_relative:
            latest_pointer_path.unlink()
            cleared_latest_pointer = True

    return {
        "status": "pass",
        "memory_id": memory_id,
        "deleted": deleted,
        "cleared_latest_pointer": cleared_latest_pointer,
    }
