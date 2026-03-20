from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Final, cast

try:
    import yaml
except ImportError:  # pragma: no cover - handled at runtime with a deterministic error
    yaml = cast(Any, None)

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled at runtime with a deterministic error
    validator_for = cast(Any, None)

from .task_goal_telemetry import persist_task_goal_telemetry


GOAL_VALIDATOR_NAME: Final[str] = "validate-task-goal"
GOAL_LOOP_COMMAND_NAME: Final[str] = "run-task-goal-loop"
RESULT_PASS: Final[str] = "pass"
RESULT_FAIL: Final[str] = "fail"
VALIDATOR_EXIT_CODES: Final[dict[str, int]] = {
    RESULT_PASS: 0,
    RESULT_FAIL: 2,
}
LOOP_EXIT_CODES: Final[dict[str, int]] = {
    RESULT_PASS: 0,
    RESULT_FAIL: 2,
}
DEFAULT_TIMEOUT_SECONDS: Final[int] = 120
OUTPUT_TAIL_LINE_COUNT: Final[int] = 20
REQUIRED_GOAL_FIELDS: Final[tuple[str, ...]] = (
    "task_name",
    "objective",
    "acceptance_criteria",
    "task_boundary_rules",
    "validation_commands",
    "files_in_scope",
)


def _issue(check: str, message: str, **details: Any) -> dict[str, Any]:
    issue = {"check": check, "message": message}
    for key, value in details.items():
        if value is not None:
            issue[key] = value
    return issue


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _task_record_schema_path() -> Path:
    return _package_root() / "contracts" / "task-record.schema.json"


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_task_record(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return json.loads(text)


def _format_schema_path(path_segments: Any) -> str:
    parts = [str(segment) for segment in path_segments]
    return ".".join(parts) if parts else "$"


def _validate_with_schema(*, instance: Any, schema: dict[str, Any], label: str) -> list[dict[str, Any]]:
    if validator_for is None:
        return [
            _issue(
                "task_goal_schema",
                "The `jsonschema` dependency is required to validate machine-readable contracts.",
                source=label,
            )
        ]

    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    errors: list[dict[str, Any]] = []
    sorted_errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (_format_schema_path(error.path), error.message),
    )
    for error in sorted_errors:
        errors.append(
            _issue(
                "task_goal_schema",
                error.message,
                source=label,
                path=_format_schema_path(error.path),
            )
        )
    return errors


def _build_goal_summary(task_record: dict[str, Any]) -> dict[str, Any]:
    goal_validation = cast(dict[str, Any], task_record["goal_validation"])
    return {
        "task_name": task_record["task_name"],
        "objective": task_record["objective"],
        "acceptance_criteria": task_record["acceptance_criteria"],
        "files_in_scope": task_record["files_in_scope"],
        "primary_goal_command": goal_validation["primary_goal_command"],
        "broader_validation_commands": goal_validation["safety_check_commands"],
    }


def _normalize_tail(text: str, *, line_count: int = OUTPUT_TAIL_LINE_COUNT) -> str:
    lines = text.splitlines()
    if len(lines) <= line_count:
        return text
    normalized = "\n".join(lines[-line_count:])
    if text.endswith("\n"):
        normalized += "\n"
    return normalized


def _normalize_process_output(value: bytes | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _goal_validation_errors(task_record: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    goal_validation = task_record.get("goal_validation")
    validation_commands = task_record.get("validation_commands")
    if not isinstance(goal_validation, dict):
        return [
            _issue(
                "task_goal_fields",
                "The task record must declare a goal_validation object.",
                field="goal_validation",
            )
        ]

    primary_goal_command = goal_validation.get("primary_goal_command")
    safety_check_commands = goal_validation.get("safety_check_commands")
    completion_rule = goal_validation.get("completion_rule")

    if not isinstance(primary_goal_command, str) or not primary_goal_command.strip():
        errors.append(
            _issue(
                "task_goal_fields",
                "goal_validation.primary_goal_command must be a non-empty string.",
                field="goal_validation.primary_goal_command",
            )
        )
    if not isinstance(safety_check_commands, list) or any(
        not isinstance(value, str) or not value.strip() for value in safety_check_commands
    ):
        errors.append(
            _issue(
                "task_goal_fields",
                "goal_validation.safety_check_commands must be a list of non-empty strings.",
                field="goal_validation.safety_check_commands",
            )
        )
    if completion_rule != "all_declared_commands_must_pass":
        errors.append(
            _issue(
                "task_goal_fields",
                "goal_validation.completion_rule must be `all_declared_commands_must_pass`.",
                field="goal_validation.completion_rule",
            )
        )
    if isinstance(validation_commands, list) and isinstance(primary_goal_command, str) and isinstance(safety_check_commands, list):
        expected_commands = [primary_goal_command, *safety_check_commands]
        if validation_commands != expected_commands:
            errors.append(
                _issue(
                    "task_goal_fields",
                    "validation_commands must match goal_validation command order exactly.",
                    field="goal_validation",
                    expected=expected_commands,
                    actual=validation_commands,
                )
            )
    return errors


def validate_task_goal(*, task_record_path: Path, schema_path: Path | None = None) -> dict[str, Any]:
    resolved_schema_path = schema_path or _task_record_schema_path()
    payload: dict[str, Any] = {
        "validator": GOAL_VALIDATOR_NAME,
        "result": RESULT_PASS,
        "errors": [],
        "inputs": {
            "task_record": str(task_record_path.resolve()),
            "task_record_schema": str(resolved_schema_path.resolve()),
        },
        "goal_summary": None,
        "primary_goal_command": None,
        "broader_validation_commands": [],
    }

    try:
        task_record = _load_task_record(task_record_path)
    except OSError as exc:
        payload["result"] = RESULT_FAIL
        payload["errors"] = [_issue("task_goal_load", f"Unable to load the task-record input: {exc}")]
        return payload
    except json.JSONDecodeError as exc:
        payload["result"] = RESULT_FAIL
        payload["errors"] = [_issue("task_goal_load", f"Unable to parse the task-record input as JSON: {exc}")]
        return payload

    if not isinstance(task_record, dict):
        payload["result"] = RESULT_FAIL
        payload["errors"] = [_issue("task_goal_shape", "The task-record input must deserialize to a single JSON object.")]
        return payload

    schema = _load_json_file(resolved_schema_path)
    errors = _validate_with_schema(instance=task_record, schema=schema, label="task-record.schema.json")

    for field_name in REQUIRED_GOAL_FIELDS:
        value = task_record.get(field_name)
        if isinstance(value, str):
            if not value.strip():
                errors.append(_issue("task_goal_fields", "Required goal-contract string field must not be empty.", field=field_name))
            continue
        if isinstance(value, list):
            if not value:
                errors.append(_issue("task_goal_fields", "Required goal-contract list field must not be empty.", field=field_name))
            continue
        errors.append(_issue("task_goal_fields", "Required goal-contract field is missing or has the wrong type.", field=field_name))

    operating_root = task_record.get("operating_root")
    if not isinstance(operating_root, str) or not operating_root.strip():
        errors.append(_issue("task_goal_fields", "The task record must declare a non-empty operating_root.", field="operating_root"))
    elif not Path(operating_root).is_absolute():
        errors.append(_issue("task_goal_fields", "The task record operating_root must be an absolute path.", field="operating_root"))

    errors.extend(_goal_validation_errors(task_record))

    if errors:
        payload["result"] = RESULT_FAIL
        payload["errors"] = errors
        return payload

    goal_summary = _build_goal_summary(task_record)
    payload["goal_summary"] = goal_summary
    payload["primary_goal_command"] = goal_summary["primary_goal_command"]
    payload["broader_validation_commands"] = goal_summary["broader_validation_commands"]
    return payload


def _maybe_attach_telemetry(
    payload: dict[str, Any],
    *,
    telemetry_requested: bool,
    task_record: dict[str, Any] | None,
    task_record_path: Path,
    telemetry_output_path: Path | None,
    run_id: str | None,
    build_run_manifest_path: Path | None,
) -> dict[str, Any]:
    if not telemetry_requested:
        return payload
    try:
        if task_record is None:
            raise ValueError("Telemetry writing requires a loadable task record object.")
        telemetry_payload, persisted_path = persist_task_goal_telemetry(
            loop_result=payload,
            task_record=task_record,
            task_record_path=task_record_path,
            output_path=telemetry_output_path,
            run_id=run_id,
            build_run_manifest_path=build_run_manifest_path,
        )
        payload["telemetry"] = {
            "requested": True,
            "written": True,
            "output_path": persisted_path,
            "schema_version": telemetry_payload["schema_version"],
            "run_correlation": telemetry_payload["run_correlation"],
        }
    except Exception as exc:
        error_message = str(exc)
        if error_message == "operating_root must be an absolute path":
            error_message = "Telemetry output path is ambiguous without an absolute operating_root"
        payload["telemetry"] = {
            "requested": True,
            "written": False,
            "error": error_message,
        }
    return payload


def run_task_goal_loop(
    *,
    task_record_path: Path,
    schema_path: Path | None = None,
    telemetry_output_path: Path | None = None,
    run_id: str | None = None,
    build_run_manifest_path: Path | None = None,
) -> dict[str, Any]:
    telemetry_requested = (
        telemetry_output_path is not None
        or run_id is not None
        or build_run_manifest_path is not None
    )
    task_record: dict[str, Any] | None = None
    try:
        loaded_task_record = _load_task_record(task_record_path)
        if isinstance(loaded_task_record, dict):
            task_record = cast(dict[str, Any], loaded_task_record)
    except (OSError, json.JSONDecodeError):
        task_record = None

    validation_payload = validate_task_goal(task_record_path=task_record_path, schema_path=schema_path)
    if validation_payload["result"] != RESULT_PASS:
        return _maybe_attach_telemetry(
            {
            "command": GOAL_LOOP_COMMAND_NAME,
            "result": RESULT_FAIL,
            "continue_working": False,
            "primary_goal_passed": False,
            "completed": False,
            "operating_root": None,
            "command_results": [],
            "errors": validation_payload["errors"],
            "inputs": validation_payload["inputs"],
            },
            telemetry_requested=telemetry_requested,
            task_record=task_record,
            task_record_path=task_record_path,
            telemetry_output_path=telemetry_output_path,
            run_id=run_id,
            build_run_manifest_path=build_run_manifest_path,
        )

    if task_record is None:
        task_record = cast(dict[str, Any], _load_task_record(task_record_path))
    operating_root = Path(cast(str, task_record["operating_root"]))
    command_results: list[dict[str, Any]] = []

    goal_validation = cast(dict[str, Any], task_record["goal_validation"])
    command_sequence = [
        ("primary_goal_gate", cast(str, goal_validation["primary_goal_command"])),
        *[
            ("broader_validation", command)
            for command in cast(list[str], goal_validation["safety_check_commands"])
        ],
    ]

    for index, (stage, command) in enumerate(command_sequence):
        try:
            completed = subprocess.run(
                ["bash", "-lc", command],
                cwd=operating_root,
                capture_output=True,
                text=True,
                check=False,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            exit_code = 124
            stdout = _normalize_process_output(exc.stdout)
            stderr = _normalize_process_output(exc.stderr)
            timed_out = True
        command_result = {
            "command": command,
            "stage": stage,
            "exit_code": exit_code,
            "passed": exit_code == 0,
            "timed_out": timed_out,
            "stdout_tail": _normalize_tail(stdout),
            "stderr_tail": _normalize_tail(stderr),
        }
        command_results.append(command_result)
        if exit_code != 0:
            return _maybe_attach_telemetry(
                {
                "command": GOAL_LOOP_COMMAND_NAME,
                "result": RESULT_FAIL,
                "continue_working": index == 0,
                "primary_goal_passed": index > 0,
                "completed": False,
                "operating_root": str(operating_root),
                "command_results": command_results,
                "errors": [],
                "inputs": validation_payload["inputs"],
                },
                telemetry_requested=telemetry_requested,
                task_record=task_record,
                task_record_path=task_record_path,
                telemetry_output_path=telemetry_output_path,
                run_id=run_id,
                build_run_manifest_path=build_run_manifest_path,
            )

    return _maybe_attach_telemetry(
        {
        "command": GOAL_LOOP_COMMAND_NAME,
        "result": RESULT_PASS,
        "continue_working": False,
        "primary_goal_passed": True,
        "completed": True,
        "operating_root": str(operating_root),
        "command_results": command_results,
        "errors": [],
        "inputs": validation_payload["inputs"],
        },
        telemetry_requested=telemetry_requested,
        task_record=task_record,
        task_record_path=task_record_path,
        telemetry_output_path=telemetry_output_path,
        run_id=run_id,
        build_run_manifest_path=build_run_manifest_path,
    )
