from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALIDATOR_NAME = "validate-generated-agent-readme"
RESULT_PASS = "pass"
RESULT_WARN = "warn"
RESULT_FAIL = "fail"
EXIT_CODES = {
    RESULT_PASS: 0,
    RESULT_WARN: 1,
    RESULT_FAIL: 2,
}
CANONICAL_MODES = ("in-repo", "portable-bundle")
LIST_SECTIONS = (
    "start_here",
    "machine_readable_truth",
    "read_order",
    "primary_content_files",
)
VALIDATION_STATUS_REQUIRED_KEYS = ("result", "summary")
VALIDATION_STATUS_LIST_KEY = "evidence"
WARNING_POLICY_REQUIRED_KEYS = (
    "default_interpretation",
    "use_machine_readable_reports_for_detail",
)
WARNING_POLICY_LIST_KEY = "relevant_warning_class"
REFERENCE_PATTERN = re.compile(
    r"(`[^`]+`|\[[^\]]+\]\([^)]+\)|(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+|[A-Za-z0-9_.-]+\.(?:json|ya?ml|md|toml|txt))"
)
OPERATOR_GUIDANCE_PATTERNS = (
    re.compile(r"\bupload\b", re.IGNORECASE),
    re.compile(r"\boperator\b", re.IGNORECASE),
    re.compile(r"\bchecklist\b", re.IGNORECASE),
    re.compile(r"\bclick\b", re.IGNORECASE),
    re.compile(r"\bhandoff\b", re.IGNORECASE),
    re.compile(r"\bhand off\b", re.IGNORECASE),
    re.compile(r"\brunbook\b", re.IGNORECASE),
    re.compile(r"\bwhat to (?:run|upload|click|hand ?off)\b", re.IGNORECASE),
    re.compile(r"^\s*(?:[-*]|\d+\.)\s*(?:run|upload|click|handoff|hand off)\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class MarkdownSection:
    identifier: str
    heading: str
    line: int
    body_lines: tuple[tuple[int, str], ...]


def _issue(check: str, message: str, **details: Any) -> dict[str, Any]:
    issue = {"check": check, "message": message}
    for key, value in details.items():
        if value is not None:
            issue[key] = value
    return issue


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _contract_path() -> Path:
    return _package_root() / "contracts" / "generated-agent-readme.contract.json"


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        issues,
        key=lambda issue: (
            str(issue.get("check", "")),
            str(issue.get("line", "")),
            str(issue.get("section", "")),
            str(issue.get("path", "")),
            str(issue.get("message", "")),
        ),
    )


def _normalize_section_identifier(heading: str) -> str:
    return heading.strip()


def _strip_wrapping_backticks(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        return stripped[1:-1].strip()
    return stripped


def _non_empty_body_lines(section: MarkdownSection) -> list[tuple[int, str]]:
    return [(line, raw_line) for line, raw_line in section.body_lines if raw_line.strip()]


def _parse_markdown_sections(text: str) -> tuple[list[MarkdownSection], list[dict[str, Any]]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    sections: list[MarkdownSection] = []
    errors: list[dict[str, Any]] = []
    current_heading: str | None = None
    current_identifier: str | None = None
    current_line: int | None = None
    current_body: list[tuple[int, str]] = []

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            if current_heading is not None and current_identifier is not None and current_line is not None:
                sections.append(
                    MarkdownSection(
                        identifier=current_identifier,
                        heading=current_heading,
                        line=current_line,
                        body_lines=tuple(current_body),
                    )
                )
            current_heading = stripped[3:].strip()
            current_identifier = _normalize_section_identifier(current_heading)
            current_line = line_number
            current_body = []
            continue

        if stripped.startswith("### "):
            errors.append(
                _issue(
                    "readme_structure",
                    "Nested section headings are not allowed in the generated agent README.",
                    line=line_number,
                )
            )

        if current_heading is not None:
            current_body.append((line_number, raw_line))

    if current_heading is not None and current_identifier is not None and current_line is not None:
        sections.append(
            MarkdownSection(
                identifier=current_identifier,
                heading=current_heading,
                line=current_line,
                body_lines=tuple(current_body),
            )
        )

    if not sections:
        errors.append(
            _issue(
                "readme_structure",
                "No canonical README sections were found. Expected Markdown `## <section_id>` headings.",
            )
        )

    return sections, errors


def _load_contract(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    try:
        payload = _load_json_file(path)
    except OSError as exc:
        return None, [
            _issue(
                "contract_load",
                f"Unable to load the generated-agent README contract: {exc}",
                source=str(path),
            )
        ]
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "contract_load",
                f"Unable to parse the generated-agent README contract as JSON: {exc}",
                source=str(path),
            )
        ]

    if not isinstance(payload, dict):
        return None, [
            _issue(
                "contract_shape",
                "The generated-agent README contract must deserialize to a JSON object.",
                source=str(path),
            )
        ]

    errors: list[dict[str, Any]] = []
    canonical_section_order = payload.get("canonical_section_order")
    if not isinstance(canonical_section_order, list) or not all(isinstance(item, str) for item in canonical_section_order):
        errors.append(
            _issue(
                "contract_shape",
                "The contract must declare `canonical_section_order` as an array of exact section identifiers.",
                source=str(path),
                path="canonical_section_order",
            )
        )

    sections = payload.get("sections")
    if not isinstance(sections, list) or not all(isinstance(item, dict) for item in sections):
        errors.append(
            _issue(
                "contract_shape",
                "The contract must declare `sections` as an array of section metadata objects.",
                source=str(path),
                path="sections",
            )
        )
        return payload, errors

    section_ids: list[str] = []
    required_ids: list[str] = []
    for index, section in enumerate(sections):
        identifier = section.get("id")
        position = section.get("position")
        required = section.get("required")
        if not isinstance(identifier, str):
            errors.append(
                _issue(
                    "contract_shape",
                    "Each contract section must include a string `id`.",
                    source=str(path),
                    path=f"sections[{index}].id",
                )
            )
            continue
        section_ids.append(identifier)
        if required is True:
            required_ids.append(identifier)
        if not isinstance(position, int):
            errors.append(
                _issue(
                    "contract_shape",
                    "Each contract section must include an integer `position`.",
                    source=str(path),
                    path=f"sections[{index}].position",
                )
            )

    if isinstance(canonical_section_order, list) and section_ids and canonical_section_order != section_ids:
        errors.append(
            _issue(
                "contract_shape",
                "The contract `canonical_section_order` must exactly match the ordered `sections[].id` sequence.",
                source=str(path),
            )
        )

    if isinstance(canonical_section_order, list):
        required_order = [item for item in canonical_section_order if item in required_ids]
        if required_ids and required_order != required_ids:
            errors.append(
                _issue(
                    "contract_shape",
                    "Required contract sections must follow the declared canonical order.",
                    source=str(path),
                )
            )

    return payload, errors


def _section_map(sections: list[MarkdownSection]) -> tuple[dict[str, MarkdownSection], list[dict[str, Any]]]:
    mapped: dict[str, MarkdownSection] = {}
    errors: list[dict[str, Any]] = []
    for section in sections:
        if section.identifier in mapped:
            errors.append(
                _issue(
                    "section_heading",
                    f"Duplicate README section heading `{section.identifier}`.",
                    line=section.line,
                    section=section.identifier,
                )
            )
            continue
        mapped[section.identifier] = section
    return mapped, errors


def _validate_section_headings(
    sections: list[MarkdownSection],
    *,
    expected_order: list[str],
    required_sections: set[str],
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    actual_order = [section.identifier for section in sections]
    expected_set = set(expected_order)

    for section in sections:
        if section.identifier not in expected_set:
            errors.append(
                _issue(
                    "section_heading",
                    f"Unexpected README section `{section.identifier}`. Generated agent READMEs only support canonical contract sections.",
                    line=section.line,
                    section=section.identifier,
                )
            )

    for identifier in expected_order:
        if identifier not in actual_order and identifier in required_sections:
            errors.append(
                _issue(
                    "section_presence",
                    f"Missing required README section `{identifier}`.",
                    section=identifier,
                )
            )

    if actual_order != expected_order:
        errors.append(
            _issue(
                "section_order",
                "README sections must appear in the canonical contract order.",
                expected=expected_order,
                actual=actual_order,
            )
        )

    return errors


def _extract_markdown_bullets(section: MarkdownSection) -> tuple[list[str], list[dict[str, Any]]]:
    items: list[str] = []
    errors: list[dict[str, Any]] = []
    for line_number, raw_line in _non_empty_body_lines(section):
        stripped = raw_line.strip()
        if not stripped.startswith("- "):
            errors.append(
                _issue(
                    "section_content",
                    "Expected a Markdown bullet list item in this section.",
                    line=line_number,
                    section=section.identifier,
                )
            )
            continue
        value = _strip_wrapping_backticks(stripped[2:])
        if not value:
            errors.append(
                _issue(
                    "section_content",
                    "Markdown bullet list items must not be empty.",
                    line=line_number,
                    section=section.identifier,
                )
            )
            continue
        items.append(value)
    return items, errors


def _extract_keyed_bullets(section: MarkdownSection) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    keyed: dict[str, list[str]] = {}
    errors: list[dict[str, Any]] = []
    for line_number, raw_line in _non_empty_body_lines(section):
        stripped = raw_line.strip()
        if not stripped.startswith("- "):
            errors.append(
                _issue(
                    "section_content",
                    "Expected a Markdown bullet list item in this section.",
                    line=line_number,
                    section=section.identifier,
                )
            )
            continue
        payload = stripped[2:].strip()
        if ":" not in payload:
            errors.append(
                _issue(
                    "section_content",
                    "Expected `key: value` bullet entries in this section.",
                    line=line_number,
                    section=section.identifier,
                )
            )
            continue
        key, value = payload.split(":", 1)
        normalized_key = key.strip()
        normalized_value = _strip_wrapping_backticks(value.strip())
        if not normalized_key:
            errors.append(
                _issue(
                    "section_content",
                    "Structured bullet keys must not be empty.",
                    line=line_number,
                    section=section.identifier,
                )
            )
            continue
        if not normalized_value:
            errors.append(
                _issue(
                    "section_content",
                    f"Structured bullet `{normalized_key}` must not have an empty value.",
                    line=line_number,
                    section=section.identifier,
                )
            )
            continue
        keyed.setdefault(normalized_key, []).append(normalized_value)
    return keyed, errors


def _validate_mode_section(section: MarkdownSection) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    values = [_strip_wrapping_backticks(raw_line.strip()) for _, raw_line in _non_empty_body_lines(section)]
    if not values:
        return [
            _issue(
                "mode_section",
                "The `mode` section must contain exactly one canonical mode value.",
                section=section.identifier,
            )
        ]
    if len(values) != 1:
        errors.append(
            _issue(
                "mode_section",
                "The `mode` section must contain exactly one non-empty line.",
                section=section.identifier,
            )
        )
        return errors

    value = values[0]
    if value not in CANONICAL_MODES:
        errors.append(
            _issue(
                "mode_section",
                "The `mode` section must use one of the canonical identifiers: `in-repo` or `portable-bundle`.",
                section=section.identifier,
                actual=value,
            )
        )
    return errors


def _validate_list_section(section: MarkdownSection) -> tuple[list[str], list[dict[str, Any]]]:
    items, errors = _extract_markdown_bullets(section)
    if not items:
        errors.append(
            _issue(
                "section_content",
                f"The `{section.identifier}` section must contain at least one Markdown bullet item.",
                section=section.identifier,
            )
        )
    return items, errors


def _validate_validation_status_section(section: MarkdownSection) -> list[dict[str, Any]]:
    keyed, errors = _extract_keyed_bullets(section)
    for required_key in VALIDATION_STATUS_REQUIRED_KEYS:
        values = keyed.get(required_key, [])
        if not values:
            errors.append(
                _issue(
                    "validation_status",
                    f"The `validation_status` section must include `{required_key}: ...`.",
                    section=section.identifier,
                )
            )
        elif len(values) != 1:
            errors.append(
                _issue(
                    "validation_status",
                    f"The `validation_status` section must include `{required_key}` exactly once.",
                    section=section.identifier,
                )
            )

    if VALIDATION_STATUS_LIST_KEY in keyed and not all(keyed[VALIDATION_STATUS_LIST_KEY]):
        errors.append(
            _issue(
                "validation_status",
                "The `validation_status` evidence entries must not be empty.",
                section=section.identifier,
            )
        )

    unexpected_keys = sorted(set(keyed) - set(VALIDATION_STATUS_REQUIRED_KEYS) - {VALIDATION_STATUS_LIST_KEY})
    for key in unexpected_keys:
        errors.append(
            _issue(
                "validation_status",
                f"Unexpected `validation_status` field `{key}`.",
                section=section.identifier,
            )
        )

    return errors


def _validate_warning_policy_section(section: MarkdownSection) -> list[dict[str, Any]]:
    keyed, errors = _extract_keyed_bullets(section)
    for required_key in WARNING_POLICY_REQUIRED_KEYS:
        values = keyed.get(required_key, [])
        if not values:
            errors.append(
                _issue(
                    "warning_policy",
                    f"The `warning_policy` section must include `{required_key}: ...`.",
                    section=section.identifier,
                )
            )
        elif len(values) != 1:
            errors.append(
                _issue(
                    "warning_policy",
                    f"The `warning_policy` section must include `{required_key}` exactly once.",
                    section=section.identifier,
                )
            )

    unexpected_keys = sorted(set(keyed) - set(WARNING_POLICY_REQUIRED_KEYS) - {WARNING_POLICY_LIST_KEY})
    for key in unexpected_keys:
        errors.append(
            _issue(
                "warning_policy",
                f"Unexpected `warning_policy` field `{key}`.",
                section=section.identifier,
            )
        )

    return errors


def _validate_machine_readable_truth_references(items: list[str]) -> list[dict[str, Any]]:
    if any(REFERENCE_PATTERN.search(item) for item in items):
        return []
    return [
        _issue(
            "machine_readable_truth",
            "The `machine_readable_truth` section must include at least one machine-readable file reference in the README body.",
            section="machine_readable_truth",
        )
    ]


def _validate_role_separation(text: str, *, forbidden_terms: list[str]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lowered_terms = [term.lower() for term in forbidden_terms if isinstance(term, str)]

    for line_number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue

        lowered = stripped.lower()
        for term in lowered_terms:
            if term and term in lowered:
                errors.append(
                    _issue(
                        "role_separation",
                        "Generated agent READMEs must not include operator-facing guidance or checklist language.",
                        line=line_number,
                        term=term,
                    )
                )
                break
        else:
            for pattern in OPERATOR_GUIDANCE_PATTERNS:
                if pattern.search(stripped):
                    errors.append(
                        _issue(
                            "role_separation",
                            "Generated agent READMEs must not include obvious operator/upload/run checklist guidance.",
                            line=line_number,
                            content=stripped,
                        )
                    )
                    break

    return errors


def _build_result_payload(*, readme_path: Path, contract_path: Path) -> dict[str, Any]:
    return {
        "validator": VALIDATOR_NAME,
        "result": RESULT_PASS,
        "errors": [],
        "warnings": [],
        "inputs": {
            "readme": str(readme_path.resolve()),
            "contract": str(contract_path.resolve()),
        },
    }


def validate_generated_agent_readme(readme_path: Path) -> dict[str, Any]:
    contract_path = _contract_path()
    result = _build_result_payload(readme_path=readme_path, contract_path=contract_path)

    contract, contract_errors = _load_contract(contract_path)
    result["errors"].extend(contract_errors)
    if contract is None or contract_errors:
        result["errors"] = _sort_issues(result["errors"])
        result["result"] = RESULT_FAIL
        return result

    try:
        readme_text = readme_path.read_text(encoding="utf-8")
    except OSError as exc:
        result["errors"].append(
            _issue(
                "readme_load",
                f"Unable to load the generated agent README: {exc}",
                source=str(readme_path),
            )
        )
        result["errors"] = _sort_issues(result["errors"])
        result["result"] = RESULT_FAIL
        return result

    sections, parse_errors = _parse_markdown_sections(readme_text)
    result["errors"].extend(parse_errors)

    expected_order = [str(item) for item in contract.get("canonical_section_order", [])]
    required_sections = {
        str(section.get("id"))
        for section in contract.get("sections", [])
        if isinstance(section, dict) and section.get("required") is True and isinstance(section.get("id"), str)
    }
    result["errors"].extend(
        _validate_section_headings(
            sections,
            expected_order=expected_order,
            required_sections=required_sections,
        )
    )

    mapped_sections, map_errors = _section_map(sections)
    result["errors"].extend(map_errors)

    mode_section = mapped_sections.get("mode")
    if mode_section is not None:
        result["errors"].extend(_validate_mode_section(mode_section))

    for identifier in LIST_SECTIONS:
        section = mapped_sections.get(identifier)
        if section is None:
            continue
        items, list_errors = _validate_list_section(section)
        result["errors"].extend(list_errors)
        if identifier == "machine_readable_truth" and items:
            result["errors"].extend(_validate_machine_readable_truth_references(items))

    validation_status_section = mapped_sections.get("validation_status")
    if validation_status_section is not None:
        result["errors"].extend(_validate_validation_status_section(validation_status_section))

    warning_policy_section = mapped_sections.get("warning_policy")
    if warning_policy_section is not None:
        result["errors"].extend(_validate_warning_policy_section(warning_policy_section))

    forbidden_terms = []
    role_boundaries = contract.get("role_boundaries")
    if isinstance(role_boundaries, dict):
        raw_terms = role_boundaries.get("forbidden_operator_content")
        if isinstance(raw_terms, list):
            forbidden_terms = [str(item) for item in raw_terms if isinstance(item, str)]
    result["errors"].extend(_validate_role_separation(readme_text, forbidden_terms=forbidden_terms))

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
    for key in ("readme", "contract"):
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
    parser = argparse.ArgumentParser(description="Validate a generated agent README against the canonical contract.")
    parser.add_argument("--readme", required=True, type=Path, help="Path to the rendered generated agent README Markdown file.")
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Deterministic output mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = validate_generated_agent_readme(readme_path=args.readme)
    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_format_text_output(result))
    return EXIT_CODES[result["result"]]


if __name__ == "__main__":
    raise SystemExit(main())
