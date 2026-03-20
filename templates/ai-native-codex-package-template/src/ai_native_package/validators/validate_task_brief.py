from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, cast

try:
    import yaml
except ImportError:  # pragma: no cover - handled at runtime with a deterministic error
    yaml = cast(Any, None)

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled at runtime with a deterministic error
    validator_for = cast(Any, None)


VALIDATOR_NAME = "validate-task-brief"
RESULT_PASS = "pass"
RESULT_WARN = "warn"
RESULT_FAIL = "fail"

CANONICAL_FIELDS = (
    "task_name",
    "operating_root",
    "project_context_reference",
    "source_spec_reference",
    "objective",
    "files_in_scope",
    "required_changes",
    "acceptance_criteria",
    "validation_commands",
    "out_of_scope",
    "local_evidence",
    "task_boundary_rules",
    "required_return_format",
)
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
EXIT_CODES = {
    RESULT_PASS: 0,
    RESULT_WARN: 1,
    RESULT_FAIL: 2,
}


def _issue(check: str, message: str, **details: Any) -> dict[str, Any]:
    issue = {"check": check, "message": message}
    for key, value in details.items():
        if value is not None:
            issue[key] = value
    return issue


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _schema_paths() -> tuple[Path, Path]:
    contracts_dir = _package_root() / "contracts"
    return (
        contracts_dir / "delegation-brief.schema.json",
        contracts_dir / "task-record.schema.json",
    )


def _normalize_heading(heading: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", heading.strip().lower())
    return normalized.strip("_")


def _strip_wrapping_backticks(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1].strip()
    return stripped


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value


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


def _parse_brief_markdown(text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sections: dict[str, list[tuple[int, str]]] = {}
    errors: list[dict[str, Any]] = []
    current_field: str | None = None
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            field_name = _normalize_heading(stripped[3:])
            if field_name not in CANONICAL_FIELDS:
                errors.append(
                    _issue(
                        "brief_parse",
                        f"Unexpected brief section heading `{stripped[3:]}`.",
                        line=line_number,
                        field=field_name,
                    )
                )
                current_field = None
                continue
            if field_name in sections:
                errors.append(
                    _issue(
                        "brief_parse",
                        f"Duplicate brief section heading `{stripped[3:]}`.",
                        line=line_number,
                        field=field_name,
                    )
                )
                current_field = None
                continue
            sections[field_name] = []
            current_field = field_name
            continue

        if current_field is not None:
            sections[current_field].append((line_number, raw_line))

    if not sections:
        errors.append(
            _issue(
                "brief_parse",
                "No canonical delegation-brief sections were found in the Markdown input.",
            )
        )

    parsed: dict[str, Any] = {}
    for field_name in CANONICAL_FIELDS:
        if field_name not in sections:
            continue

        entries = sections[field_name]
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


def _compare_with_task_record(
    brief_payload: dict[str, Any],
    task_record_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for field_name in CANONICAL_FIELDS:
        brief_value = _normalize_value(brief_payload.get(field_name))
        task_record_value = _normalize_value(task_record_payload.get(field_name))
        if brief_value != task_record_value:
            errors.append(
                _issue(
                    "brief_task_record_match",
                    f"Brief field `{field_name}` does not match the authoritative task record.",
                    field=field_name,
                    expected=task_record_value,
                    actual=brief_value,
                )
            )
    return errors


def _build_result_payload(
    *,
    brief_path: Path,
    task_record_path: Path | None,
    delegation_brief_schema_path: Path,
    task_record_schema_path: Path,
) -> dict[str, Any]:
    return {
        "validator": VALIDATOR_NAME,
        "result": RESULT_PASS,
        "errors": [],
        "warnings": [],
        "inputs": {
            "brief": str(brief_path.resolve()),
            "task_record": str(task_record_path.resolve()) if task_record_path is not None else None,
            "delegation_brief_schema": str(delegation_brief_schema_path.resolve()),
            "task_record_schema": str(task_record_schema_path.resolve()) if task_record_path is not None else None,
        },
    }


def validate_task_brief(brief_path: Path, task_record_path: Path | None = None) -> dict[str, Any]:
    delegation_brief_schema_path, task_record_schema_path = _schema_paths()
    result = _build_result_payload(
        brief_path=brief_path,
        task_record_path=task_record_path,
        delegation_brief_schema_path=delegation_brief_schema_path,
        task_record_schema_path=task_record_schema_path,
    )

    try:
        delegation_brief_schema = _load_json_file(delegation_brief_schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        result["errors"].append(
            _issue(
                "schema_load",
                f"Unable to load the canonical delegation-brief schema: {exc}",
                source=str(delegation_brief_schema_path),
            )
        )
        result["result"] = RESULT_FAIL
        return result

    try:
        brief_text = brief_path.read_text(encoding="utf-8")
    except OSError as exc:
        result["errors"].append(
            _issue(
                "brief_load",
                f"Unable to load the delegation brief: {exc}",
                source=str(brief_path),
            )
        )
        result["result"] = RESULT_FAIL
        return result

    brief_payload, parse_errors = _parse_brief_markdown(brief_text)
    result["errors"].extend(parse_errors)
    result["errors"].extend(
        _validate_with_schema(
            instance=brief_payload,
            schema=delegation_brief_schema,
            check="brief_schema",
            label="delegation-brief.schema.json",
        )
    )

    task_record_payload: Any = None
    task_record_valid = False
    if task_record_path is not None:
        try:
            task_record_schema = _load_json_file(task_record_schema_path)
        except (OSError, json.JSONDecodeError) as exc:
            result["errors"].append(
                _issue(
                    "schema_load",
                    f"Unable to load the authoritative task-record schema: {exc}",
                    source=str(task_record_schema_path),
                )
            )
            result["result"] = RESULT_FAIL
            return result

        try:
            task_record_payload = _load_task_record(task_record_path)
        except OSError as exc:
            result["errors"].append(
                _issue(
                    "task_record_load",
                    f"Unable to load the task record: {exc}",
                    source=str(task_record_path),
                )
            )
        except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as exc:
            result["errors"].append(
                _issue(
                    "task_record_load",
                    f"Unable to parse the task record as canonical YAML or JSON: {exc}",
                    source=str(task_record_path),
                )
            )
        else:
            task_record_schema_errors = _validate_with_schema(
                instance=task_record_payload,
                schema=task_record_schema,
                check="task_record_schema",
                label="task-record.schema.json",
            )
            result["errors"].extend(task_record_schema_errors)
            task_record_valid = not task_record_schema_errors

        if task_record_valid and isinstance(task_record_payload, dict):
            result["errors"].extend(_compare_with_task_record(brief_payload, task_record_payload))
        elif task_record_payload is not None and not isinstance(task_record_payload, dict):
            result["errors"].append(
                _issue(
                    "task_record_schema",
                    "The task record must deserialize to a JSON object.",
                    source=str(task_record_path),
                )
            )

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
    for key in ("brief", "task_record", "delegation_brief_schema", "task_record_schema"):
        lines.append(f"  {key}: {result['inputs'][key]}")

    lines.append("errors:")
    if result["errors"]:
        for index, issue in enumerate(result["errors"], start=1):
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
    parser = argparse.ArgumentParser(description="Validate a canonical delegation brief.")
    parser.add_argument("--brief", required=True, type=Path, help="Path to the rendered delegation brief Markdown file.")
    parser.add_argument(
        "--task-record",
        type=Path,
        default=None,
        help="Optional path to the authoritative task record YAML file.",
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
    result = validate_task_brief(brief_path=args.brief, task_record_path=args.task_record)
    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_format_text_output(result))
    return EXIT_CODES[result["result"]]


if __name__ == "__main__":
    raise SystemExit(main())
