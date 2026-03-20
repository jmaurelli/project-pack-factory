from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Final

SCHEMA_VERSION: Final[str] = "doc-update-record/v1"
DEFAULT_OUTPUT_PATH: Final[str] = "docs/doc-update-record.json"


def _normalize_optional_string(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty when provided")
    return normalized


def _normalize_required_string(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _normalize_paths(paths: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for path in paths:
        candidate = _normalize_required_string(path, field_name="path")
        posix_path = PurePosixPath(candidate).as_posix()
        if posix_path in seen:
            continue
        seen.add(posix_path)
        normalized.append(posix_path)
    return sorted(normalized)


def build_doc_update_record(
    *,
    task_id: str,
    change_summary: str,
    code_paths: list[str],
    doc_paths: list[str],
    doc_update_reason: str,
    status: str = "updated",
    project_root: str | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    normalized_status = _normalize_required_string(status, field_name="status")
    if normalized_status not in {"updated", "not_required"}:
        raise ValueError("status must be one of: updated, not_required")
    normalized_doc_paths = _normalize_paths(doc_paths)
    if normalized_status == "updated" and not normalized_doc_paths:
        raise ValueError("updated status requires at least one doc path")
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": _normalize_required_string(task_id, field_name="task_id"),
        "project_root": _normalize_optional_string(project_root, field_name="project_root"),
        "change_summary": _normalize_required_string(change_summary, field_name="change_summary"),
        "code_paths": _normalize_paths(code_paths),
        "doc_paths": normalized_doc_paths,
        "doc_update_reason": _normalize_required_string(
            doc_update_reason,
            field_name="doc_update_reason",
        ),
        "status": normalized_status,
    }
    normalized_generated_at = _normalize_optional_string(generated_at, field_name="generated_at")
    if normalized_generated_at is not None:
        payload["generated_at"] = normalized_generated_at
    return payload


def write_doc_update_record(payload: dict[str, object], output_path: str | Path = DEFAULT_OUTPUT_PATH) -> str:
    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(target_path)
