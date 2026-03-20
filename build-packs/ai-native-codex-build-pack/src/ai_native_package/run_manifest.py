from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Final

from .__about__ import DISTRIBUTION_NAME

SCHEMA_VERSION: Final[str] = "build-run-manifest/v1"
_DEFAULT_MANIFEST_DIR: Final[str] = ".ai-native-codex-package-template/run-manifests"


def _utc_now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_required_string(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _normalize_optional_string(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _normalize_required_string(value, field_name=field_name)


def _normalize_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = value.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def derive_run_manifest_path(*, run_id: str, project_root: str | Path) -> str:
    root = Path(project_root)
    return str(root / _DEFAULT_MANIFEST_DIR / f"{run_id}.json")


def build_run_manifest(
    *,
    run_id: str,
    task_name: str,
    selected_profile: str,
    outcome_status: str,
    project_root: str | None = None,
    outcome_summary: str | None = None,
    command: list[str] | None = None,
    validation: list[str] | None = None,
    artifact: list[str] | None = None,
    note: list[str] | None = None,
    setup_time_seconds: float | None = None,
    execution_time_seconds: float | None = None,
    validation_time_seconds: float | None = None,
    clarification_count: int | None = None,
    validation_failures: int | None = None,
    files_created: int | None = None,
    files_changed: int | None = None,
) -> dict[str, object]:
    status = _normalize_required_string(outcome_status, field_name="outcome_status")
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": _normalize_required_string(run_id, field_name="run_id"),
        "generated_at": _utc_now_timestamp(),
        "producer": DISTRIBUTION_NAME,
        "task_name": _normalize_required_string(task_name, field_name="task_name"),
        "project_root": _normalize_optional_string(project_root, field_name="project_root"),
        "selected_profile": _normalize_required_string(selected_profile, field_name="selected_profile"),
        "commands": _normalize_list(command or []),
        "validations": _normalize_list(validation or []),
        "artifacts": _normalize_list(artifact or []),
        "notes": _normalize_list(note or []),
        "timings": {
            "setup_time_seconds": setup_time_seconds,
            "execution_time_seconds": execution_time_seconds,
            "validation_time_seconds": validation_time_seconds,
        },
        "metrics": {
            "clarification_count": clarification_count,
            "validation_failures": validation_failures,
            "files_created": files_created,
            "files_changed": files_changed,
        },
        "outcome": {
            "status": status,
            "summary": _normalize_optional_string(outcome_summary, field_name="outcome_summary"),
        },
    }
    return payload


def write_run_manifest(payload: dict[str, object], *, output_path: str | Path) -> str:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(target)
