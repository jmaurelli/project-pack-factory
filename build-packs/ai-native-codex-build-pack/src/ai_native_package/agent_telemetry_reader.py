from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final, cast

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled deterministically at runtime
    validator_for = cast(Any, None)

from .task_goal_telemetry_summary import derive_task_goal_telemetry_summary_path

SCHEMA_VERSION: Final[str] = "agent-telemetry-reader/v1"
READER_NAME: Final[str] = "agent-telemetry-reader"
_PACK_DIR: Final[str] = ".ai-native-codex-package-template"
_SUMMARY_FILENAME: Final[str] = "task-goal-telemetry-summary.json"
_RUN_MANIFEST_DIR: Final[str] = "run-manifests"


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _telemetry_schema_path() -> Path:
    return _package_root() / "contracts" / "task-goal-telemetry.schema.json"


def _summary_schema_path() -> Path:
    return _package_root() / "contracts" / "task-goal-telemetry-summary.schema.json"


def _reader_schema_path() -> Path:
    return _package_root() / "contracts" / "agent-telemetry-reader.schema.json"


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_schema_path(path_segments: Any) -> str:
    parts = [str(segment) for segment in path_segments]
    return ".".join(parts) if parts else "$"


def _validate_with_schema(*, instance: Any, schema: dict[str, Any], label: str) -> list[str]:
    if validator_for is None:
        return ["The `jsonschema` dependency is required to validate machine-readable contracts."]

    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    return [
        f"{label}:{_format_schema_path(error.path)}: {error.message}"
        for error in sorted(
            validator.iter_errors(instance),
            key=lambda error: (_format_schema_path(error.path), error.message),
        )
    ]


def _normalize_required_string(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _normalize_task_name_filter(task_name: str | None) -> str | None:
    if task_name is None:
        return None
    normalized = _normalize_required_string(task_name, field_name="task_name")
    if Path(normalized).name != normalized:
        raise ValueError("task_name must not contain path separators")
    return normalized


def _resolve_project_root(project_root: str | Path) -> Path:
    candidate = Path(project_root)
    if not candidate.is_absolute():
        raise ValueError("project_root must be an absolute path")
    return candidate.resolve()


def _telemetry_dir(project_root: Path) -> Path:
    return Path(derive_task_goal_telemetry_summary_path(project_root=project_root)).parent


def _summary_path(project_root: Path) -> Path:
    return Path(derive_task_goal_telemetry_summary_path(project_root=project_root)).resolve()


def _run_manifest_dir(project_root: Path) -> Path:
    return (project_root / _PACK_DIR / _RUN_MANIFEST_DIR).resolve()


def _read_validated_task_goal_telemetry(path: Path) -> dict[str, Any]:
    payload = _load_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError(f"task-goal telemetry must contain a JSON object: {path}")
    schema = cast(dict[str, Any], _load_json_file(_telemetry_schema_path()))
    validation_errors = _validate_with_schema(
        instance=payload,
        schema=schema,
        label="task-goal-telemetry.schema.json",
    )
    if validation_errors:
        raise ValueError(f"{path}: {'; '.join(validation_errors)}")
    return cast(dict[str, Any], payload)


def _read_validated_task_goal_summary(path: Path, *, project_root: Path) -> dict[str, Any]:
    payload = _load_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError(f"task-goal telemetry summary must contain a JSON object: {path}")
    schema = cast(dict[str, Any], _load_json_file(_summary_schema_path()))
    validation_errors = _validate_with_schema(
        instance=payload,
        schema=schema,
        label="task-goal-telemetry-summary.schema.json",
    )
    if validation_errors:
        raise ValueError(f"{path}: {'; '.join(validation_errors)}")
    summary_scope = cast(dict[str, Any], payload.get("summary_scope", {}))
    summary_project_root = _normalize_required_string(
        summary_scope.get("project_root"),
        field_name="summary_scope.project_root",
    )
    if Path(summary_project_root).resolve() != project_root:
        raise ValueError(f"{path}: summary_scope.project_root does not match the requested project_root")
    return cast(dict[str, Any], payload)


def _read_validated_run_manifest(path: Path) -> dict[str, Any]:
    payload = _load_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError(f"build-run manifest must contain a JSON object: {path}")
    if payload.get("schema_version") != "build-run-manifest/v1":
        raise ValueError(f"{path}: schema_version must be build-run-manifest/v1")
    _normalize_required_string(payload.get("run_id"), field_name="run_id")
    _normalize_required_string(payload.get("generated_at"), field_name="generated_at")
    _normalize_required_string(payload.get("task_name"), field_name="task_name")
    outcome = payload.get("outcome")
    if not isinstance(outcome, dict):
        raise ValueError(f"{path}: outcome must be an object")
    return cast(dict[str, Any], payload)


def _sort_entries(entries: list[tuple[Path, dict[str, Any]]]) -> list[tuple[Path, dict[str, Any]]]:
    return sorted(
        entries,
        key=lambda item: (
            _normalize_required_string(item[1].get("generated_at"), field_name="generated_at"),
            str(item[0].resolve()),
        ),
    )


def _discover_task_goal_telemetry_entries(
    *,
    project_root: Path,
    task_name: str | None,
) -> list[tuple[Path, dict[str, Any]]]:
    directory = _telemetry_dir(project_root)
    if not directory.exists():
        return []
    entries: list[tuple[Path, dict[str, Any]]] = []
    for candidate in sorted(directory.glob("*.json")):
        resolved = candidate.resolve()
        if resolved.name == _SUMMARY_FILENAME:
            continue
        payload = _read_validated_task_goal_telemetry(resolved)
        if task_name is not None and payload.get("task_name") != task_name:
            continue
        entries.append((resolved, payload))
    return _sort_entries(entries)


def _discover_build_run_manifest_entries(project_root: Path) -> list[tuple[Path, dict[str, Any]]]:
    directory = _run_manifest_dir(project_root)
    if not directory.exists():
        return []
    entries: list[tuple[Path, dict[str, Any]]] = []
    for candidate in sorted(directory.glob("*.json")):
        resolved = candidate.resolve()
        payload = _read_validated_run_manifest(resolved)
        entries.append((resolved, payload))
    return _sort_entries(entries)


def discover_task_goal_telemetry_paths(
    project_root: str | Path,
    task_name: str | None = None,
) -> list[str]:
    normalized_root = _resolve_project_root(project_root)
    normalized_task_name = _normalize_task_name_filter(task_name)
    return [
        str(path)
        for path, _payload in _discover_task_goal_telemetry_entries(
            project_root=normalized_root,
            task_name=normalized_task_name,
        )
    ]


def load_task_goal_telemetry(path: str | Path) -> dict[str, Any]:
    return _read_validated_task_goal_telemetry(Path(path).expanduser().resolve())


def load_task_goal_telemetry_summary(project_root: str | Path) -> dict[str, Any] | None:
    normalized_root = _resolve_project_root(project_root)
    path = _summary_path(normalized_root)
    if not path.exists():
        return None
    return _read_validated_task_goal_summary(path, project_root=normalized_root)


def discover_build_run_manifest_paths(project_root: str | Path) -> list[str]:
    normalized_root = _resolve_project_root(project_root)
    return [str(path) for path, _payload in _discover_build_run_manifest_entries(normalized_root)]


def load_build_run_manifest(path: str | Path) -> dict[str, Any]:
    return _read_validated_run_manifest(Path(path).expanduser().resolve())


def _artifact_slot(*, path: str | None, payload: dict[str, Any] | None) -> dict[str, object]:
    return {
        "path": path,
        "present": payload is not None,
        "payload": payload,
    }


def _task_record_slot(latest_telemetry: dict[str, Any] | None) -> dict[str, object]:
    if latest_telemetry is None:
        return {"path": None, "present": False}
    task_record_path = latest_telemetry.get("task_record_path")
    if not isinstance(task_record_path, str) or not task_record_path.strip():
        return {"path": None, "present": False}
    resolved = Path(task_record_path).expanduser().resolve()
    return {"path": str(resolved), "present": resolved.exists()}


def _build_notes(
    *,
    latest_telemetry: dict[str, Any] | None,
    summary_payload: dict[str, Any] | None,
    latest_manifest: dict[str, Any] | None,
    task_name_filter: str | None,
) -> list[str]:
    notes: list[str] = []
    if task_name_filter is not None:
        notes.append(f"Filtered local telemetry to task name `{task_name_filter}`.")
    if latest_telemetry is None:
        if task_name_filter is None:
            notes.append("No valid local task-goal telemetry was found for this project root.")
        else:
            notes.append(f"No valid local task-goal telemetry was found for task `{task_name_filter}`.")
    elif latest_telemetry.get("continue_working") is True:
        notes.append("The latest local attempt is incomplete. Read the latest task-goal telemetry before changing code.")
    elif latest_telemetry.get("completed") is True:
        notes.append("The latest local attempt completed successfully.")
    else:
        notes.append("The latest local attempt stopped after a broader validation failure.")
    if summary_payload is None:
        notes.append("No local task-goal telemetry summary is present yet.")
    if latest_manifest is None:
        notes.append("No local build-run manifest is present yet.")
    notes.append("Use local evidence first. Do not infer canonical benchmark state from this snapshot.")
    return notes


def read_agent_telemetry(project_root: str | Path, task_name: str | None = None) -> dict[str, Any]:
    normalized_root = _resolve_project_root(project_root)
    normalized_task_name = _normalize_task_name_filter(task_name)

    telemetry_entries = _discover_task_goal_telemetry_entries(
        project_root=normalized_root,
        task_name=normalized_task_name,
    )
    latest_telemetry_path: str | None = None
    latest_telemetry_payload: dict[str, Any] | None = None
    if telemetry_entries:
        latest_path_obj, latest_telemetry_payload = telemetry_entries[-1]
        latest_telemetry_path = str(latest_path_obj)

    summary_payload = load_task_goal_telemetry_summary(normalized_root)
    summary_path = str(_summary_path(normalized_root)) if summary_payload is not None else None

    manifest_entries = _discover_build_run_manifest_entries(normalized_root)
    latest_manifest_path: str | None = None
    latest_manifest_payload: dict[str, Any] | None = None
    if manifest_entries:
        latest_manifest_path_obj, latest_manifest_payload = manifest_entries[-1]
        latest_manifest_path = str(latest_manifest_path_obj)

    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "reader": READER_NAME,
        "project_root": str(normalized_root),
        "task_name_filter": normalized_task_name,
        "recommended_read_order": [
            "task_record",
            "latest_task_goal_telemetry",
            "task_goal_telemetry_summary",
            "latest_build_run_manifest",
        ],
        "task_record": _task_record_slot(latest_telemetry_payload),
        "latest_task_goal_telemetry": _artifact_slot(
            path=latest_telemetry_path,
            payload=latest_telemetry_payload,
        ),
        "task_goal_telemetry_summary": _artifact_slot(
            path=summary_path,
            payload=summary_payload,
        ),
        "latest_build_run_manifest": _artifact_slot(
            path=latest_manifest_path,
            payload=latest_manifest_payload,
        ),
        "local_artifact_counts": {
            "task_goal_telemetry_count": len(telemetry_entries),
            "build_run_manifest_count": len(manifest_entries),
        },
        "status_summary": {
            "latest_result": latest_telemetry_payload.get("result") if latest_telemetry_payload is not None else None,
            "latest_completed": latest_telemetry_payload.get("completed") if latest_telemetry_payload is not None else None,
            "latest_continue_working": latest_telemetry_payload.get("continue_working") if latest_telemetry_payload is not None else None,
            "latest_primary_goal_passed": latest_telemetry_payload.get("primary_goal_passed") if latest_telemetry_payload is not None else None,
        },
        "notes": _build_notes(
            latest_telemetry=latest_telemetry_payload,
            summary_payload=summary_payload,
            latest_manifest=latest_manifest_payload,
            task_name_filter=normalized_task_name,
        ),
    }
    schema = cast(dict[str, Any], _load_json_file(_reader_schema_path()))
    validation_errors = _validate_with_schema(
        instance=snapshot,
        schema=schema,
        label="agent-telemetry-reader.schema.json",
    )
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    return snapshot


def build_agent_telemetry_snapshot(project_root: str | Path, task_name: str | None = None) -> dict[str, Any]:
    return read_agent_telemetry(project_root=project_root, task_name=task_name)
