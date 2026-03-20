from __future__ import annotations

import argparse
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, cast

try:
    import yaml
except ImportError:  # pragma: no cover - handled at runtime with a deterministic error
    yaml = cast(Any, None)

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled at runtime with a deterministic error
    validator_for = cast(Any, None)


VALIDATOR_NAME = "validate-task-scope"
RESULT_PASS = "pass"
RESULT_WARN = "warn"
RESULT_FAIL = "fail"
EXIT_CODES = {
    RESULT_PASS: 0,
    RESULT_WARN: 1,
    RESULT_FAIL: 2,
}
LIST_FIELDS = {
    "project_context_reference",
    "source_spec_reference",
    "files_in_scope",
    "required_changes",
    "acceptance_criteria",
    "validation_commands",
    "out_of_scope",
    "local_evidence",
    "task_boundary_rules",
    "required_return_format",
}
RUNTIME_PATH_PREFIXES = (
    "src/",
    "ai_native_package/",
)
TEST_PATH_PREFIXES = (
    "tests/",
    "test/",
)


def _issue(check: str, message: str, **details: Any) -> dict[str, Any]:
    issue = {"check": check, "message": message}
    for key, value in details.items():
        if value is not None:
            issue[key] = value
    return issue


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _task_record_schema_path() -> Path:
    return _package_root() / "contracts" / "task-record.schema.json"


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml_or_json_file(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return json.loads(text)


def _format_schema_path(path_segments: Any) -> str:
    parts = [str(segment) for segment in path_segments]
    return ".".join(parts) if parts else "$"


def _validate_with_schema(
    *,
    instance: Any,
    schema: dict[str, Any],
    check: str,
    label: str,
) -> list[dict[str, Any]]:
    if validator_for is None:
        return [
            _issue(
                check,
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
                check,
                error.message,
                source=label,
                path=_format_schema_path(error.path),
            )
        )
    return errors


def _normalize_heading(heading: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", heading.strip().lower())
    return normalized.strip("_")


def _strip_wrapping_backticks(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1].strip()
    return stripped


def _parse_brief_markdown(text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sections: dict[str, list[tuple[int, str]]] = {}
    errors: list[dict[str, Any]] = []
    current_field: str | None = None
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            current_field = _normalize_heading(stripped[3:])
            sections.setdefault(current_field, [])
            continue

        if current_field is not None:
            sections[current_field].append((line_number, raw_line))

    parsed: dict[str, Any] = {}
    for field_name, entries in sections.items():
        if field_name in LIST_FIELDS:
            items: list[str] = []
            for line_number, raw_line in entries:
                stripped = raw_line.strip()
                if not stripped:
                    continue
                if not stripped.startswith("- "):
                    errors.append(
                        _issue(
                            "brief_parse",
                            "Expected a Markdown bullet list item for this section.",
                            line=line_number,
                            field=field_name,
                        )
                    )
                    continue
                items.append(_strip_wrapping_backticks(stripped[2:]))
            parsed[field_name] = items
            continue

        value_lines = [_strip_wrapping_backticks(raw_line.strip()) for _, raw_line in entries if raw_line.strip()]
        parsed[field_name] = "\n".join(value_lines).strip()

    return parsed, errors


def _sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        issues,
        key=lambda issue: (
            str(issue.get("check", "")),
            str(issue.get("path", "")),
            str(issue.get("file", "")),
            str(issue.get("message", "")),
        ),
    )


def _validate_repo_relative_posix_path(path_value: Any) -> str | None:
    if not isinstance(path_value, str):
        return "Path entries must be strings."
    if not path_value or not path_value.strip():
        return "Path entries must be non-empty strings."
    if path_value != path_value.strip():
        return "Path entries must not include leading or trailing whitespace."
    if "\\" in path_value:
        return "Path entries must use POSIX separators (`/`) and must not contain backslashes."
    if path_value.startswith("/"):
        return "Path entries must be repo-relative, not absolute."
    if path_value.startswith("./"):
        return "Path entries must omit a leading `./` prefix."
    if path_value.endswith("/"):
        return "Path entries must reference files, not directory prefixes."
    posix_path = PurePosixPath(path_value)
    if any(segment in {"", ".", ".."} for segment in posix_path.parts):
        return "Path entries must not contain empty, `.` or `..` path segments."
    if posix_path.as_posix() != path_value:
        return "Path entries must use normalized POSIX syntax."
    return None


def _load_changed_files(changed_files_path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    try:
        payload = _load_json_file(changed_files_path)
    except OSError as exc:
        return [], [
            _issue(
                "changed_files_load",
                f"Unable to load the changed-files payload: {exc}",
                source=str(changed_files_path),
            )
        ]
    except json.JSONDecodeError as exc:
        return [], [
            _issue(
                "changed_files_load",
                f"Unable to parse the changed-files payload as a canonical JSON array: {exc}",
                source=str(changed_files_path),
            )
        ]

    if not isinstance(payload, list):
        return [], [
            _issue(
                "changed_files_shape",
                "The changed-files payload must deserialize to a JSON array of repo-relative POSIX-style path strings.",
                source=str(changed_files_path),
            )
        ]

    changed_files: list[str] = []
    for index, entry in enumerate(payload):
        path_error = _validate_repo_relative_posix_path(entry)
        if path_error is not None:
            errors.append(
                _issue(
                    "changed_files_path",
                    path_error,
                    source=str(changed_files_path),
                    path=f"$[{index}]",
                )
            )
            continue
        changed_files.append(entry)

    if len(changed_files) != len(set(changed_files)):
        errors.append(
            _issue(
                "changed_files_shape",
                "The changed-files JSON array must not contain duplicate path entries.",
                source=str(changed_files_path),
            )
        )

    if changed_files != sorted(changed_files):
        errors.append(
            _issue(
                "changed_files_shape",
                "The changed-files JSON array must be sorted lexically for deterministic comparison.",
                source=str(changed_files_path),
            )
        )

    return changed_files, errors


def _scope_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_name": payload.get("task_name"),
        "objective": payload.get("objective"),
        "required_changes": payload.get("required_changes"),
        "out_of_scope": payload.get("out_of_scope"),
    }


def _load_scope_from_task_record(task_record_path: Path) -> tuple[list[str], dict[str, Any], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    schema_path = _task_record_schema_path()
    try:
        schema = _load_json_file(schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [], {}, [
            _issue(
                "schema_load",
                f"Unable to load the authoritative task-record schema: {exc}",
                source=str(schema_path),
            )
        ]

    try:
        payload = _load_yaml_or_json_file(task_record_path)
    except OSError as exc:
        return [], {}, [
            _issue(
                "task_record_load",
                f"Unable to load the task record: {exc}",
                source=str(task_record_path),
            )
        ]
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as exc:
        return [], {}, [
            _issue(
                "task_record_load",
                f"Unable to parse the task record as canonical YAML or JSON: {exc}",
                source=str(task_record_path),
            )
        ]

    schema_errors = _validate_with_schema(
        instance=payload,
        schema=schema,
        check="task_record_schema",
        label="task-record.schema.json",
    )
    errors.extend(schema_errors)
    if schema_errors:
        return [], {}, errors

    if not isinstance(payload, dict):
        return [], {}, errors + [
            _issue(
                "task_record_schema",
                "The task record must deserialize to a JSON object.",
                source=str(task_record_path),
            )
        ]

    files_in_scope = payload.get("files_in_scope")
    if not isinstance(files_in_scope, list):
        errors.append(
            _issue(
                "task_scope",
                "The authoritative task record must declare `files_in_scope` as an array.",
                source=str(task_record_path),
            )
        )
        return [], _scope_metadata(payload), errors

    return [str(entry) for entry in files_in_scope], _scope_metadata(payload), errors


def _load_scope_from_brief(brief_path: Path) -> tuple[list[str], dict[str, Any], list[dict[str, Any]]]:
    try:
        brief_text = brief_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], {}, [
            _issue(
                "brief_load",
                f"Unable to load the delegation brief: {exc}",
                source=str(brief_path),
            )
        ]

    payload, errors = _parse_brief_markdown(brief_text)
    files_in_scope = payload.get("files_in_scope")
    if not isinstance(files_in_scope, list) or not files_in_scope:
        errors.append(
            _issue(
                "brief_scope",
                "The delegation brief must include a non-empty `Files In Scope` section to drive task-scope validation when no task record is provided.",
                source=str(brief_path),
            )
        )
        return [], _scope_metadata(payload), errors

    return [str(entry) for entry in files_in_scope], _scope_metadata(payload), errors


def _validate_declared_scope_paths(paths: list[str], *, source: str, check: str) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for index, path_value in enumerate(paths):
        path_error = _validate_repo_relative_posix_path(path_value)
        if path_error is not None:
            errors.append(
                _issue(
                    check,
                    path_error,
                    source=source,
                    path=f"files_in_scope[{index}]",
                )
            )
    if len(paths) != len(set(paths)):
        errors.append(
            _issue(
                check,
                "The declared `files_in_scope` list must not contain duplicate paths.",
                source=source,
            )
        )
    return errors


def _path_is_runtime(path_value: str) -> bool:
    if path_value.startswith(RUNTIME_PATH_PREFIXES):
        return True
    if path_value.endswith(".py") and not path_value.startswith(TEST_PATH_PREFIXES):
        return True
    return False


def _task_mode_hints(metadata: dict[str, Any]) -> set[str]:
    candidates: list[str] = []
    for key in ("task_name", "objective"):
        value = metadata.get(key)
        if isinstance(value, str):
            candidates.append(value.lower())
    for key in ("required_changes", "out_of_scope"):
        value = metadata.get(key)
        if isinstance(value, list):
            candidates.extend(str(item).lower() for item in value if isinstance(item, str))

    hints: set[str] = set()
    for candidate in candidates:
        if "docs-only" in candidate or "documentation-only" in candidate:
            hints.add("docs-only")
        if "test-only" in candidate or "tests-only" in candidate:
            hints.add("test-only")
    return hints


def _scope_mode_warnings(
    *,
    metadata: dict[str, Any],
    declared_scope: list[str],
    changed_files: list[str],
) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    hints = _task_mode_hints(metadata)
    runtime_scope_paths = [path_value for path_value in declared_scope if _path_is_runtime(path_value)]
    runtime_changed_paths = [path_value for path_value in changed_files if _path_is_runtime(path_value)]

    if "docs-only" in hints and runtime_scope_paths:
        warnings.append(
            _issue(
                "task_scope_mode",
                "The task appears to be declared as docs-only, but `files_in_scope` includes runtime-code paths.",
            )
        )
    if "docs-only" in hints and runtime_changed_paths:
        warnings.append(
            _issue(
                "task_scope_mode",
                "The task appears to be declared as docs-only, but runtime-code files were changed.",
            )
        )
    if "test-only" in hints and runtime_scope_paths:
        warnings.append(
            _issue(
                "task_scope_mode",
                "The task appears to be declared as test-only, but `files_in_scope` includes runtime-code paths.",
            )
        )
    if "test-only" in hints and runtime_changed_paths:
        warnings.append(
            _issue(
                "task_scope_mode",
                "The task appears to be declared as test-only, but runtime-code files were changed.",
            )
        )

    return warnings


def _build_result_payload(
    *,
    brief_path: Path | None,
    task_record_path: Path | None,
    changed_files_path: Path,
) -> dict[str, Any]:
    schema_path = _task_record_schema_path()
    return {
        "validator": VALIDATOR_NAME,
        "result": RESULT_PASS,
        "errors": [],
        "warnings": [],
        "inputs": {
            "brief": str(brief_path.resolve()) if brief_path is not None else None,
            "task_record": str(task_record_path.resolve()) if task_record_path is not None else None,
            "task_record_schema": str(schema_path.resolve()) if task_record_path is not None else None,
            "changed_files": str(changed_files_path.resolve()),
            "scope_source": None,
        },
    }


def validate_task_scope(
    *,
    changed_files_path: Path,
    task_record_path: Path | None = None,
    brief_path: Path | None = None,
) -> dict[str, Any]:
    result = _build_result_payload(
        brief_path=brief_path,
        task_record_path=task_record_path,
        changed_files_path=changed_files_path,
    )

    changed_files, changed_file_errors = _load_changed_files(changed_files_path)
    result["errors"].extend(changed_file_errors)

    if task_record_path is None and brief_path is None:
        result["errors"].append(
            _issue(
                "scope_input",
                "Provide `--task-record` or `--brief` so the validator can determine the declared task scope.",
            )
        )
        result["result"] = RESULT_FAIL
        result["errors"] = _sort_issues(result["errors"])
        return result

    declared_scope: list[str] = []
    metadata: dict[str, Any] = {}
    if task_record_path is not None:
        declared_scope, metadata, scope_errors = _load_scope_from_task_record(task_record_path)
        result["inputs"]["scope_source"] = "task_record"
        result["errors"].extend(scope_errors)
        if task_record_path is not None:
            result["inputs"]["task_record_schema"] = str(_task_record_schema_path().resolve())
    elif brief_path is not None:
        declared_scope, metadata, scope_errors = _load_scope_from_brief(brief_path)
        result["inputs"]["scope_source"] = "brief"
        result["errors"].extend(scope_errors)

    if declared_scope:
        scope_source_label = str(task_record_path) if task_record_path is not None else str(brief_path)
        result["errors"].extend(
            _validate_declared_scope_paths(
                declared_scope,
                source=scope_source_label,
                check="task_scope_path",
            )
        )

    if not result["errors"] and declared_scope:
        declared_scope_set = set(declared_scope)
        for changed_file in changed_files:
            if changed_file not in declared_scope_set:
                result["errors"].append(
                    _issue(
                        "out_of_scope_edit",
                        "Changed file falls outside the declared task scope.",
                        file=changed_file,
                    )
                )
        result["warnings"].extend(
            _scope_mode_warnings(
                metadata=metadata,
                declared_scope=declared_scope,
                changed_files=changed_files,
            )
        )

    result["errors"] = _sort_issues(result["errors"])
    result["warnings"] = _sort_issues(result["warnings"])
    if result["errors"]:
        result["result"] = RESULT_FAIL
    elif result["warnings"]:
        result["result"] = RESULT_WARN
    return result


def _format_text_output(result: dict[str, Any]) -> str:
    lines = [
        f"validator: {result['validator']}",
        f"result: {result['result']}",
        "inputs:",
    ]
    for key in ("brief", "task_record", "task_record_schema", "changed_files", "scope_source"):
        lines.append(f"  {key}: {result['inputs'][key]}")

    lines.append("errors:")
    if result["errors"]:
        for index, issue in enumerate(result["errors"], start=1):
            if "file" in issue:
                lines.append(f"  {index}. [{issue['check']}] {issue['message']} ({issue['file']})")
            else:
                lines.append(f"  {index}. [{issue['check']}] {issue['message']}")
    else:
        lines.append("  none")

    lines.append("warnings:")
    if result["warnings"]:
        for index, issue in enumerate(result["warnings"], start=1):
            lines.append(f"  {index}. [{issue['check']}] {issue['message']}")
    else:
        lines.append("  none")

    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate changed files against declared task scope.")
    parser.add_argument(
        "--brief",
        type=Path,
        default=None,
        help="Optional path to the rendered delegation brief Markdown file.",
    )
    parser.add_argument(
        "--task-record",
        type=Path,
        default=None,
        help="Optional path to the authoritative task record YAML file.",
    )
    parser.add_argument(
        "--changed-files",
        required=True,
        type=Path,
        help="Path to the canonical UTF-8 JSON array of repo-relative POSIX changed-file paths.",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Deterministic output mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = validate_task_scope(
        changed_files_path=args.changed_files,
        task_record_path=args.task_record,
        brief_path=args.brief,
    )
    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_format_text_output(result))
    return EXIT_CODES[result["result"]]


if __name__ == "__main__":
    raise SystemExit(main())
