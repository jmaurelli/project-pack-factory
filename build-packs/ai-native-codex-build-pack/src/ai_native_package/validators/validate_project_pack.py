from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .validate_doc_update_record import validate_doc_update_record

VALIDATOR_NAME = "validate-project-pack"
RESULT_PASS = "pass"
RESULT_FAIL = "fail"
EXIT_CODES = {
    RESULT_PASS: 0,
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


def _default_contract_path() -> Path:
    return _package_root() / "contracts" / "project-pack.contract.json"


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _contains_heading(text: str, heading: str) -> bool:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    return bool(pattern.search(text))


def _validate_required_docs(contract: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    docs = contract.get("required_docs", {})
    mandatory_files = docs.get("mandatory_files", docs.get("files", []))
    optional_files = docs.get("optional_files", [])
    required_headings = docs.get("required_headings", {})

    for rel_path in mandatory_files:
        path = project_root / rel_path
        if not path.exists():
            errors.append(
                _issue(
                    "required_docs",
                    "Required agent-facing documentation file is missing.",
                    path=rel_path,
                )
            )
            continue

    for rel_path in list(mandatory_files) + list(optional_files):
        path = project_root / rel_path
        if not path.exists():
            continue
        headings = required_headings.get(rel_path, [])
        if not headings:
            continue
        text = _read_text(path)
        for heading in headings:
            if not _contains_heading(text, heading):
                errors.append(
                    _issue(
                        "required_docs",
                        "Required documentation heading is missing.",
                        path=rel_path,
                        heading=heading,
                    )
                )
    return errors


def _validate_documentation_style(contract: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    style = contract.get("documentation_style", {})
    required_terms = tuple(style.get("required_terms", []))
    forbidden_terms = tuple(style.get("forbidden_terms", []))
    required_tone_markers = tuple(style.get("required_tone_markers", []))
    required_explanatory_headings = style.get("required_explanatory_headings", {})
    required_term_definitions = style.get("required_term_definitions", {})
    style_paths = tuple(style.get("applies_to_optional_files", ["README.md", "project-context.md"]))

    existing_texts: list[str] = []
    for rel_path in style_paths:
        path = project_root / rel_path
        if path.exists():
            existing_texts.append(_read_text(path).lower())
    if not existing_texts:
        return errors
    combined = "\n".join(existing_texts)

    for term in required_terms:
        if term.lower() not in combined:
            errors.append(_issue("documentation_style", "Required documentation term is missing from available human docs.", term=term))
    for term in required_tone_markers:
        if term.lower() not in combined:
            errors.append(_issue("documentation_style", "Required documentation tone marker is missing from available human docs.", term=term))
    for term in forbidden_terms:
        if term.lower() in combined:
            errors.append(_issue("documentation_style", "Forbidden documentation term is present.", term=term))

    for rel_path, headings in required_explanatory_headings.items():
        path = project_root / rel_path
        if not path.exists():
            continue
        text = _read_text(path)
        for heading in headings:
            if not _contains_heading(text, heading):
                errors.append(
                    _issue(
                        "documentation_style",
                        "Required explanatory heading is missing.",
                        path=rel_path,
                        heading=heading,
                    )
                )

    for rel_path, terms in required_term_definitions.items():
        path = project_root / rel_path
        if not path.exists():
            continue
        text = _read_text(path)
        for term in terms:
            if f"- {term}:" not in text and f"{term}:" not in text:
                errors.append(
                    _issue(
                        "documentation_style",
                        "Required plain-language term definition is missing.",
                        path=rel_path,
                        term=term,
                    )
                )
    return errors


def _validate_testing_policy(contract: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    testing = contract.get("testing_policy", {})
    required_dev_tools = tuple(testing.get("required_dev_tools", []))
    required_policy_markers = tuple(testing.get("required_policy_markers", []))

    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        errors.append(_issue("testing_policy", "Package pyproject.toml is missing.", path="pyproject.toml"))
        text = ""
    else:
        text = pyproject_path.read_text(encoding="utf-8")
    for tool in required_dev_tools:
        if tool not in text:
            errors.append(_issue("testing_policy", "Required dev tool is not declared.", tool=tool))

    policy_texts: list[str] = []
    for rel_path in ("AGENTS.md", "project-context.md"):
        path = project_root / rel_path
        if path.exists():
            policy_texts.append(_read_text(path).lower())
    combined_policy = "\n".join(policy_texts)
    for marker in required_policy_markers:
        if marker.lower() not in combined_policy:
            errors.append(
                _issue(
                    "testing_policy",
                    "Required testing policy marker is missing from package guidance.",
                    marker=marker,
                )
            )
    return errors


def _validate_framework_policy(contract: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    framework_policy = contract.get("framework_policy", {})
    approved = tuple(framework_policy.get("approved_python_cli_dependencies", []))
    disallowed = tuple(framework_policy.get("disallowed_python_cli_dependencies", []))
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.exists():
        errors.append(_issue("framework_policy", "Package pyproject.toml is missing.", path="pyproject.toml"))
        pyproject_text = ""
    else:
        pyproject_text = pyproject_path.read_text(encoding="utf-8").lower()

    for dependency in approved:
        if dependency.lower() not in pyproject_text:
            errors.append(
                _issue(
                    "framework_policy",
                    "Approved framework dependency is missing from the package baseline.",
                    dependency=dependency,
                )
            )
    for dependency in disallowed:
        if dependency.lower() in pyproject_text:
            errors.append(
                _issue(
                    "framework_policy",
                    "Disallowed framework dependency is present in the package baseline.",
                    dependency=dependency,
                )
            )
    return errors


def _validate_goal_loop_policy(contract: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    goal_loop_policy = contract.get("goal_loop_policy", {})
    required_policy_markers = tuple(goal_loop_policy.get("required_policy_markers", []))
    task_record_template_path = goal_loop_policy.get("task_record_template_path")
    task_record_schema_path = goal_loop_policy.get("task_record_schema_path")
    required_cli_commands = tuple(goal_loop_policy.get("required_cli_commands", []))

    policy_texts: list[str] = []
    for rel_path in ("AGENTS.md", "project-context.md"):
        path = project_root / rel_path
        if path.exists():
            policy_texts.append(_read_text(path).lower())
    combined_policy = "\n".join(policy_texts)
    for marker in required_policy_markers:
        if marker.lower() not in combined_policy:
            errors.append(
                _issue(
                    "goal_loop_policy",
                    "Required goal-loop policy marker is missing from package guidance.",
                    marker=marker,
                )
            )

    if isinstance(task_record_template_path, str) and task_record_template_path:
        template_path = project_root / task_record_template_path
        if not template_path.exists():
            errors.append(_issue("goal_loop_policy", "Task-record template is missing.", path=task_record_template_path))
        else:
            template_text = _read_text(template_path)
            if "validation_commands:" not in template_text:
                errors.append(
                    _issue(
                        "goal_loop_policy",
                        "Task-record template must expose validation_commands for the goal loop.",
                        path=task_record_template_path,
                    )
                )
            if "goal_validation:" not in template_text:
                errors.append(
                    _issue(
                        "goal_loop_policy",
                        "Task-record template must expose goal_validation metadata for the goal loop.",
                        path=task_record_template_path,
                    )
                )

    if isinstance(task_record_schema_path, str) and task_record_schema_path:
        schema_path = project_root / task_record_schema_path
        if not schema_path.exists():
            errors.append(_issue("goal_loop_policy", "Task-record schema is missing.", path=task_record_schema_path))
        else:
            schema_text = _read_text(schema_path)
            if '"goal_validation"' not in schema_text:
                errors.append(
                    _issue(
                        "goal_loop_policy",
                        "Task-record schema must declare goal_validation metadata.",
                        path=task_record_schema_path,
                    )
                )

    cli_path = project_root / "src" / "ai_native_package" / "cli.py"
    constants_path = project_root / "src" / "ai_native_package" / "constants.py"
    cli_text = _read_text(cli_path) if cli_path.exists() else ""
    constants_text = _read_text(constants_path) if constants_path.exists() else ""
    for command in required_cli_commands:
        if command not in cli_text and command not in constants_text:
            errors.append(
                _issue(
                    "goal_loop_policy",
                    "Required goal-loop CLI command is missing from the package CLI surface.",
                    command=command,
                )
            )
    return errors



def _validate_framework_profiles(contract: dict[str, Any], project_root: Path) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    framework_profiles = contract.get("framework_profiles", {})
    catalog_path_value = framework_profiles.get("catalog_path")
    if not isinstance(catalog_path_value, str) or not catalog_path_value:
        return errors
    catalog_path = project_root / catalog_path_value
    if not catalog_path.exists():
        errors.append(_issue("framework_profiles", "Framework profile catalog is missing.", path=catalog_path_value))
        return errors
    catalog = _load_json_file(catalog_path)
    if not isinstance(catalog, dict):
        errors.append(_issue("framework_profiles", "Framework profile catalog must be a JSON object.", path=catalog_path_value))
        return errors
    profiles = catalog.get("profiles")
    if not isinstance(profiles, list):
        errors.append(_issue("framework_profiles", "Framework profile catalog must define a profiles list.", path=catalog_path_value))
        return errors
    profile_ids: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            errors.append(_issue("framework_profiles", "Each framework profile must be a JSON object.", path=catalog_path_value))
            continue
        profile_id = profile.get("profile_id")
        doc_path = profile.get("doc_path")
        if not isinstance(profile_id, str) or not profile_id:
            errors.append(_issue("framework_profiles", "Framework profile is missing profile_id.", path=catalog_path_value))
            continue
        profile_ids.add(profile_id)
        if not isinstance(doc_path, str) or not doc_path:
            errors.append(_issue("framework_profiles", "Framework profile is missing doc_path.", profile_id=profile_id))
            continue
        if not (project_root / doc_path).exists():
            errors.append(_issue("framework_profiles", "Framework profile documentation file is missing.", path=doc_path, profile_id=profile_id))
    default_profile = catalog.get("default_profile")
    if not isinstance(default_profile, str) or default_profile not in profile_ids:
        errors.append(_issue("framework_profiles", "Default framework profile must exist in the catalog.", path=catalog_path_value))
    for rel_path in framework_profiles.get("required_profile_docs", []):
        if not isinstance(rel_path, str):
            continue
        if not (project_root / rel_path).exists():
            errors.append(_issue("framework_profiles", "Required framework profile document is missing.", path=rel_path))
    return errors

def validate_project_pack(*, project_root: Path, contract_path: Path) -> dict[str, Any]:
    contract = _load_json_file(contract_path)
    errors: list[dict[str, Any]] = []
    errors.extend(_validate_required_docs(contract, project_root))
    errors.extend(_validate_documentation_style(contract, project_root))
    errors.extend(_validate_testing_policy(contract, project_root))
    errors.extend(_validate_goal_loop_policy(contract, project_root))
    errors.extend(_validate_framework_policy(contract, project_root))
    errors.extend(_validate_framework_profiles(contract, project_root))
    doc_update_policy = contract.get("doc_update_policy", {})
    doc_update_payload = validate_doc_update_record(
        project_root=project_root,
        record_path=project_root / doc_update_policy.get("record_path", "docs/doc-update-record.json"),
        schema_path=project_root / doc_update_policy.get("schema_path", "src/ai_native_package/contracts/doc-update-record.schema.json"),
    )
    errors.extend(doc_update_payload["errors"])
    return {
        "validator": VALIDATOR_NAME,
        "result": RESULT_FAIL if errors else RESULT_PASS,
        "errors": errors,
        "inputs": {
            "project_root": str(project_root.resolve()),
            "contract": str(contract_path.resolve()),
        },
        "summary": (
            "Project-pack contract checks passed."
            if not errors
            else f"Project-pack contract checks failed with {len(errors)} issue(s)."
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the reusable project-pack contract.")
    parser.add_argument("--project-root", default=".", help="Package root to validate.")
    parser.add_argument("--contract", default=str(_default_contract_path()), help="Path to project-pack contract JSON.")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    payload = validate_project_pack(
        project_root=Path(args.project_root),
        contract_path=Path(args.contract),
    )
    if args.output == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{payload['summary']} result={payload['result']}")
        for error in payload["errors"]:
            print(json.dumps(error, sort_keys=True))
    return EXIT_CODES[payload["result"]]


if __name__ == "__main__":
    raise SystemExit(main())
