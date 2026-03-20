from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, cast

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled deterministically at runtime
    validator_for = cast(Any, None)

from .__about__ import DISTRIBUTION_NAME

SCHEMA_VERSION: Final[str] = "task-goal-telemetry/v1"
_DEFAULT_TELEMETRY_DIR: Final[str] = ".ai-native-codex-package-template/task-goal-telemetry"


def _utc_now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _telemetry_schema_path() -> Path:
    return _package_root() / "contracts" / "task-goal-telemetry.schema.json"


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
        for error in sorted(validator.iter_errors(instance), key=lambda error: (_format_schema_path(error.path), error.message))
    ]


def _normalize_required_string(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _resolve_required_absolute_path(value: str | Path, *, field_name: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        if field_name == "operating_root":
            raise ValueError("Telemetry writing requires an absolute operating_root")
        raise ValueError(f"{field_name} must be an absolute path")
    return candidate


def _normalize_task_name(value: str) -> str:
    task_name = _normalize_required_string(value, field_name="task_name")
    candidate = Path(task_name)
    if candidate.name != task_name:
        raise ValueError("task_name must not contain path separators")
    return task_name


def derive_task_goal_telemetry_path(*, task_name: str, project_root: str | Path) -> str:
    normalized_task_name = _normalize_task_name(task_name)
    root = Path(project_root)
    return str(root / _DEFAULT_TELEMETRY_DIR / f"{normalized_task_name}.json")


def _load_build_run_manifest(path: Path) -> dict[str, Any]:
    payload = _load_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError("build_run_manifest_path must reference a single JSON object")
    return cast(dict[str, Any], payload)


def _resolve_run_correlation(
    *,
    operating_root: Path,
    run_id: str | None,
    build_run_manifest_path: str | Path | None,
) -> dict[str, str | None]:
    normalized_run_id = _normalize_required_string(run_id, field_name="run_id") if run_id is not None else None
    manifest_path_value: str | None = None
    manifest_run_id: str | None = None

    if build_run_manifest_path is not None:
        manifest_candidate = Path(build_run_manifest_path)
        manifest_path = manifest_candidate if manifest_candidate.is_absolute() else operating_root / manifest_candidate
        manifest_path = manifest_path.resolve()
        manifest_payload = _load_build_run_manifest(manifest_path)
        manifest_run_id_value = manifest_payload.get("run_id")
        if not isinstance(manifest_run_id_value, str) or not manifest_run_id_value.strip():
            raise ValueError("build_run_manifest_path must reference a manifest with a non-empty run_id")
        manifest_run_id = manifest_run_id_value.strip()
        manifest_path_value = str(manifest_path)
        if normalized_run_id is not None and normalized_run_id != manifest_run_id:
            raise ValueError("run_id does not match the referenced build-run manifest run_id")

    return {
        "build_run_manifest_path": manifest_path_value,
        "build_run_manifest_run_id": manifest_run_id,
        "run_id": normalized_run_id,
    }


def _resolve_output_path(
    *,
    task_name: str,
    operating_root: Path,
    output_path: str | Path | None,
) -> Path:
    if output_path is None:
        return Path(derive_task_goal_telemetry_path(task_name=task_name, project_root=operating_root))
    candidate = Path(output_path)
    if candidate.is_absolute():
        return candidate
    if not operating_root.is_absolute():
        raise ValueError("Telemetry output path is ambiguous without an absolute operating_root")
    return (operating_root / candidate).resolve()


def _attempt_summary(*, result: dict[str, Any]) -> str:
    if result["result"] == "pass":
        return "Task goal loop passed the primary goal gate and all broader validation commands."
    if result["errors"]:
        return "Task goal loop did not start because task-goal validation failed."
    if result["continue_working"]:
        return "Primary goal gate failed, so the task remains incomplete and should continue."
    return "Primary goal gate passed, but a broader validation command failed before completion."


def build_task_goal_telemetry(
    *,
    loop_result: dict[str, Any],
    task_record: dict[str, Any],
    task_record_path: str | Path,
    run_id: str | None = None,
    build_run_manifest_path: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    task_id = _normalize_required_string(cast(str, task_record.get("task_id", "")), field_name="task_id")
    task_name = _normalize_task_name(cast(str, task_record.get("task_name", "")))
    operating_root = _resolve_required_absolute_path(cast(str, task_record.get("operating_root", "")), field_name="operating_root")

    payload: dict[str, object] = dict(loop_result)
    payload.update(
        {
            "schema_version": SCHEMA_VERSION,
            "task_id": task_id,
            "task_name": task_name,
            "generated_at": _normalize_required_string(generated_at, field_name="generated_at") if generated_at is not None else _utc_now_timestamp(),
            "producer": DISTRIBUTION_NAME,
            "task_record_path": str(Path(task_record_path).resolve()),
            "attempt_summary": _attempt_summary(result=loop_result),
            "run_correlation": _resolve_run_correlation(
                operating_root=operating_root,
                run_id=run_id,
                build_run_manifest_path=build_run_manifest_path,
            ),
        }
    )
    return payload


def write_task_goal_telemetry(payload: dict[str, object], *, output_path: str | Path) -> str:
    target = Path(output_path)
    schema = cast(dict[str, Any], _load_json_file(_telemetry_schema_path()))
    validation_errors = _validate_with_schema(instance=payload, schema=schema, label="task-goal-telemetry.schema.json")
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialized + "\n", encoding="utf-8")
    return str(target)


def persist_task_goal_telemetry(
    *,
    loop_result: dict[str, Any],
    task_record: dict[str, Any],
    task_record_path: str | Path,
    output_path: str | Path | None = None,
    run_id: str | None = None,
    build_run_manifest_path: str | Path | None = None,
) -> tuple[dict[str, object], str]:
    task_name = _normalize_task_name(cast(str, task_record.get("task_name", "")))
    operating_root = _resolve_required_absolute_path(cast(str, task_record.get("operating_root", "")), field_name="operating_root")
    target = _resolve_output_path(task_name=task_name, operating_root=operating_root, output_path=output_path)
    telemetry_payload = build_task_goal_telemetry(
        loop_result=loop_result,
        task_record=task_record,
        task_record_path=task_record_path,
        run_id=run_id,
        build_run_manifest_path=build_run_manifest_path,
    )
    return telemetry_payload, write_task_goal_telemetry(telemetry_payload, output_path=target)
