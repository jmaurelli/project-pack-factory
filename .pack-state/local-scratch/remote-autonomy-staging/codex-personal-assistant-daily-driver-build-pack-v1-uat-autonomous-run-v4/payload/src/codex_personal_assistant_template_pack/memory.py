from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assistant_contracts import load_memory_policy


DISTILLATION_RECORD_SCHEMA_VERSION = "codex-personal-assistant-session-distillation/v1"
DISTILLATION_POINTER_SCHEMA_VERSION = "codex-personal-assistant-session-distillation-pointer/v1"


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


def _session_distillation_policy(project_root: Path) -> dict[str, Any]:
    policy = load_memory_policy(project_root)
    distillation_policy = policy.get("session_distillation_policy", {})
    if not isinstance(distillation_policy, dict):
        raise ValueError("memory policy must declare session_distillation_policy")
    return distillation_policy


def _session_distillation_paths(project_root: Path) -> tuple[Path, Path]:
    policy = _session_distillation_policy(project_root)
    storage_root = project_root / str(policy["storage_root"])
    latest_pointer_path = project_root / str(policy["latest_pointer_path"])
    return storage_root, latest_pointer_path


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _load_memory_record(project_root: Path, memory_id: str) -> dict[str, Any]:
    storage_root, _ = _memory_paths(project_root)
    memory_path = storage_root / f"{memory_id}.json"
    if not memory_path.exists():
        raise ValueError(f"memory `{memory_id}` does not exist")
    return _load_json(memory_path)


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
        latest_pointer = _load_json(latest_pointer_path)
        selected_path = latest_pointer.get("selected_memory_path")
        if isinstance(selected_path, str) and selected_path:
            candidate = project_root / selected_path
            if candidate.exists():
                latest_memory = _load_json(candidate)

    distillation_status = show_memory_distillation(project_root).get("session_memory_distillation_status", {})

    return {
        "status": "pass",
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "latest_pointer": latest_pointer,
        "latest_memory": latest_memory,
        "memory_count": len(memory_files),
        "available_memory_ids": [path.stem for path in memory_files],
        "session_memory_distillation_status": distillation_status,
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
        latest_pointer = _load_json(latest_pointer_path)
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


def show_memory_distillation(project_root: Path) -> dict[str, Any]:
    storage_root, latest_pointer_path = _session_distillation_paths(project_root)
    latest_pointer: dict[str, Any] | None = None
    latest_distillation: dict[str, Any] | None = None
    distillation_count = 0
    if storage_root.exists():
        distillation_files = sorted(path for path in storage_root.glob("*.json") if path.is_file())
        distillation_count = len([path for path in distillation_files if path.name != latest_pointer_path.name])
    if latest_pointer_path.exists():
        latest_pointer = _load_json(latest_pointer_path)
        selected_path = latest_pointer.get("selected_distillation_path")
        if isinstance(selected_path, str) and selected_path:
            candidate = project_root / selected_path
            if candidate.exists():
                latest_distillation = _load_json(candidate)

    return {
        "status": "pass",
        "storage_root": str(storage_root.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "latest_pointer": latest_pointer,
        "latest_distillation": latest_distillation,
        "distillation_count": distillation_count,
        "session_memory_distillation_status": {
            "latest_distillation_id": latest_distillation.get("distillation_id")
            if isinstance(latest_distillation, dict)
            else None,
            "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
            "distillation_count": distillation_count,
            "latest_distillation_promoted_memory": bool(
                isinstance(latest_distillation, dict) and latest_distillation.get("promoted_memory_id")
            ),
            "latest_promoted_memory_id": latest_distillation.get("promoted_memory_id")
            if isinstance(latest_distillation, dict)
            else None,
        },
    }


def distill_session_memory(
    project_root: Path,
    *,
    distillation_id: str,
    summary: str,
    stable_signal_reason: str,
    source_memory_ids: list[str],
    replace_existing: bool,
    promote_category: str | None = None,
    promoted_memory_id: str | None = None,
    next_action: str | None = None,
    tags: list[str],
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    if not source_memory_ids:
        raise ValueError("distillation requires at least one source_memory_id")
    if confidence is not None and not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    policy = _session_distillation_policy(project_root)
    allowed_source_categories = {
        category for category in policy.get("allowed_source_categories", []) if isinstance(category, str)
    }
    promotable_categories = {
        category for category in policy.get("promotable_memory_categories", []) if isinstance(category, str)
    }
    if promote_category is not None and promote_category not in promotable_categories:
        raise ValueError(f"promote_category `{promote_category}` is not allowed by session_distillation_policy")

    unique_source_ids = list(dict.fromkeys(source_memory_ids))
    source_memories: list[dict[str, Any]] = []
    for memory_id in unique_source_ids:
        memory_record = _load_memory_record(project_root, memory_id)
        memory_category = memory_record.get("category")
        if allowed_source_categories and memory_category not in allowed_source_categories:
            raise ValueError(
                f"memory `{memory_id}` has category `{memory_category}` which is not allowed for distillation"
            )
        source_memories.append(memory_record)

    storage_root, latest_pointer_path = _session_distillation_paths(project_root)
    storage_root.mkdir(parents=True, exist_ok=True)
    distillation_path = storage_root / f"{distillation_id}.json"
    existed = distillation_path.exists()
    if existed and not replace_existing:
        raise ValueError(
            f"session distillation `{distillation_id}` already exists; use replace_existing to overwrite it"
        )

    resolved_promoted_memory_id = promoted_memory_id
    if promote_category is not None and not resolved_promoted_memory_id:
        resolved_promoted_memory_id = f"session-distillation-{distillation_id}"

    payload = {
        "schema_version": DISTILLATION_RECORD_SCHEMA_VERSION,
        "distillation_id": distillation_id,
        "summary": summary,
        "stable_signal_reason": stable_signal_reason,
        "source_memory_ids": unique_source_ids,
        "source_memories": source_memories,
        "promote_category": promote_category,
        "promoted_memory_id": resolved_promoted_memory_id,
        "next_action": next_action,
        "tags": sorted({tag for tag in tags if tag}),
        "source": source,
        "evidence": evidence,
        "confidence": confidence,
        "recorded_at": _isoformat_z(),
    }
    _write_json(distillation_path, payload)
    pointer_payload = {
        "schema_version": DISTILLATION_POINTER_SCHEMA_VERSION,
        "selected_distillation_id": distillation_id,
        "selected_distillation_path": str(distillation_path.relative_to(project_root).as_posix()),
        "updated_at": payload["recorded_at"],
    }
    _write_json(latest_pointer_path, pointer_payload)

    memory_result = None
    if promote_category is not None and resolved_promoted_memory_id is not None:
        memory_result = record_memory(
            project_root,
            memory_id=resolved_promoted_memory_id,
            category=promote_category,
            summary=summary,
            next_action=next_action,
            tags=[*tags, "session-distillation", promote_category],
            replace_existing=replace_existing,
            source=source or "session-distillation",
            evidence=evidence or str(distillation_path.relative_to(project_root).as_posix()),
            confidence=confidence,
        )

    return {
        "status": "pass",
        "distillation_id": distillation_id,
        "distillation_path": str(distillation_path.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "replaced_existing": bool(existed and replace_existing),
        "promoted_memory_id": resolved_promoted_memory_id,
        "memory_result": memory_result,
    }
