from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final, TypedDict, cast

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled deterministically at runtime
    validator_for = cast(Any, None)

from .__about__ import DISTRIBUTION_NAME

SCHEMA_VERSION: Final[str] = "task-goal-telemetry-summary/v1"
_DEFAULT_SUMMARY_PATH: Final[str] = (
    ".ai-native-codex-package-template/task-goal-telemetry/task-goal-telemetry-summary.json"
)


class _TaskCounterEntry(TypedDict):
    task_name: str
    attempt_count: int
    completed_count: int
    continue_working_count: int
    failed_count: int
    primary_goal_passed_count: int


def _utc_now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _telemetry_schema_path() -> Path:
    return _package_root() / "contracts" / "task-goal-telemetry.schema.json"


def _summary_schema_path() -> Path:
    return _package_root() / "contracts" / "task-goal-telemetry-summary.schema.json"


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


def _resolve_required_absolute_path_string(value: object, *, field_name: str) -> str:
    normalized = _normalize_required_string(value, field_name=field_name)
    path = Path(normalized)
    if not path.is_absolute():
        raise ValueError(f"{field_name} must be an absolute path")
    return str(path.resolve())


def derive_task_goal_telemetry_summary_path(*, project_root: str | Path) -> str:
    return str(Path(project_root) / _DEFAULT_SUMMARY_PATH)


def _read_validated_telemetry(path: str | Path) -> dict[str, Any]:
    telemetry_path = Path(path).expanduser().resolve()
    payload = _load_json_file(telemetry_path)
    if not isinstance(payload, dict):
        raise ValueError(f"task-goal telemetry must contain a JSON object: {telemetry_path}")
    schema = cast(dict[str, Any], _load_json_file(_telemetry_schema_path()))
    validation_errors = _validate_with_schema(
        instance=payload,
        schema=schema,
        label="task-goal-telemetry.schema.json",
    )
    if validation_errors:
        raise ValueError(f"{telemetry_path}: {'; '.join(validation_errors)}")
    payload["__resolved_path__"] = str(telemetry_path)
    return cast(dict[str, Any], payload)


def _stage_bucket(payload: dict[str, Any], *, uncertainty_notes: list[str]) -> str:
    command_results = payload.get("command_results")
    if not isinstance(command_results, list):
        uncertainty_notes.append(
            f"Telemetry for task {payload['task_name']} did not provide command_results in the expected list form."
        )
        return "none"

    for command_result in command_results:
        if not isinstance(command_result, dict):
            uncertainty_notes.append(
                f"Telemetry for task {payload['task_name']} contained a non-object command result, so the first failing stage was left as none."
            )
            return "none"
        passed = command_result.get("passed")
        if passed is True:
            continue
        if passed is False:
            stage = command_result.get("stage")
            if stage == "primary_goal_gate":
                return "primary_goal_gate"
            if isinstance(stage, str) and stage.strip():
                return "broader_validation"
            uncertainty_notes.append(
                f"Telemetry for task {payload['task_name']} had a failed command without usable stage detail."
            )
            return "none"
    return "none"


def build_task_goal_telemetry_summary(
    *,
    telemetry_paths: list[str | Path],
    generated_at: str | None = None,
) -> dict[str, object]:
    if not telemetry_paths:
        raise ValueError("At least one telemetry path is required.")

    telemetry_payloads = [_read_validated_telemetry(path) for path in telemetry_paths]
    project_roots = {
        _resolve_required_absolute_path_string(payload.get("operating_root"), field_name="operating_root")
        for payload in telemetry_payloads
    }
    if len(project_roots) != 1:
        raise ValueError("All telemetry artifacts must share the same operating_root.")
    project_root = sorted(project_roots)[0]

    sorted_payloads = sorted(
        telemetry_payloads,
        key=lambda payload: (
            _normalize_required_string(payload.get("generated_at"), field_name="generated_at"),
            _normalize_required_string(payload.get("__resolved_path__"), field_name="path"),
        ),
    )
    source_artifacts = [
        {
            "path": _normalize_required_string(payload.get("__resolved_path__"), field_name="path"),
            "task_name": _normalize_required_string(payload.get("task_name"), field_name="task_name"),
            "generated_at": _normalize_required_string(payload.get("generated_at"), field_name="generated_at"),
        }
        for payload in sorted_payloads
    ]

    result_breakdown = Counter(
        _normalize_required_string(payload.get("result"), field_name="result")
        for payload in sorted_payloads
    )
    uncertainty_notes: list[str] = []
    stage_breakdown = Counter(
        _stage_bucket(payload, uncertainty_notes=uncertainty_notes)
        for payload in sorted_payloads
    )

    task_counters: dict[str, _TaskCounterEntry] = {}
    for payload in sorted_payloads:
        task_name = _normalize_required_string(payload.get("task_name"), field_name="task_name")
        task_entry = task_counters.setdefault(
            task_name,
            {
                "task_name": task_name,
                "attempt_count": 0,
                "completed_count": 0,
                "continue_working_count": 0,
                "failed_count": 0,
                "primary_goal_passed_count": 0,
            },
        )
        task_entry["attempt_count"] += 1
        if payload.get("completed") is True:
            task_entry["completed_count"] += 1
        if payload.get("continue_working") is True:
            task_entry["continue_working_count"] += 1
        if payload.get("result") == "fail" and payload.get("continue_working") is False:
            task_entry["failed_count"] += 1
        if payload.get("primary_goal_passed") is True:
            task_entry["primary_goal_passed_count"] += 1

    task_breakdown = [
        cast(dict[str, object], task_entry)
        for task_entry in sorted(task_counters.values(), key=lambda item: (-item["attempt_count"], item["task_name"]))
    ]

    run_ids = sorted(
        {
            run_id
            for payload in sorted_payloads
            for run_id in [cast(dict[str, Any], payload.get("run_correlation", {})).get("run_id")]
            if isinstance(run_id, str) and run_id.strip()
        }
    )
    build_run_manifest_paths = sorted(
        {
            manifest_path
            for payload in sorted_payloads
            for manifest_path in [cast(dict[str, Any], payload.get("run_correlation", {})).get("build_run_manifest_path")]
            if isinstance(manifest_path, str) and manifest_path.strip()
        }
    )

    aggregate_counts = {
        "total_attempts": len(sorted_payloads),
        "completed_count": sum(1 for payload in sorted_payloads if payload.get("completed") is True),
        "continue_working_count": sum(1 for payload in sorted_payloads if payload.get("continue_working") is True),
        "failed_count": sum(
            1
            for payload in sorted_payloads
            if payload.get("result") == "fail" and payload.get("continue_working") is False
        ),
        "primary_goal_passed_count": sum(
            1 for payload in sorted_payloads if payload.get("primary_goal_passed") is True
        ),
    }

    summary_notes = [
        f"Summarized {aggregate_counts['total_attempts']} telemetry attempts across {len(task_breakdown)} task names.",
        f"Completed attempts: {aggregate_counts['completed_count']}. Continue-working attempts: {aggregate_counts['continue_working_count']}. Failed attempts: {aggregate_counts['failed_count']}.",
        f"The first failing stage was primary_goal_gate {stage_breakdown['primary_goal_gate']} times and broader_validation {stage_breakdown['broader_validation']} times.",
    ]
    summary_notes.extend(sorted(set(uncertainty_notes)))

    summary_payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _utc_now_timestamp(),
        "producer": DISTRIBUTION_NAME,
        "summary_scope": {
            "project_root": project_root,
            "telemetry_artifact_count": len(sorted_payloads),
        },
        "source_artifacts": source_artifacts,
        "aggregate_counts": aggregate_counts,
        "result_breakdown": {
            result: result_breakdown[result]
            for result in sorted(result_breakdown)
        },
        "stage_breakdown": {
            "primary_goal_gate": stage_breakdown["primary_goal_gate"],
            "broader_validation": stage_breakdown["broader_validation"],
            "none": stage_breakdown["none"],
        },
        "task_breakdown": task_breakdown,
        "correlation_summary": {
            "run_ids": run_ids,
            "build_run_manifest_paths": build_run_manifest_paths,
        },
        "summary_notes": summary_notes,
    }
    return summary_payload


def write_task_goal_telemetry_summary(
    payload: dict[str, object],
    *,
    output_path: str | Path,
) -> str:
    target = Path(output_path)
    schema = cast(dict[str, Any], _load_json_file(_summary_schema_path()))
    validation_errors = _validate_with_schema(
        instance=payload,
        schema=schema,
        label="task-goal-telemetry-summary.schema.json",
    )
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(target)
