from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled deterministically
    validator_for = cast(Any, None)

VALIDATOR_NAME = "validate-doc-updates"
RESULT_PASS = "pass"
RESULT_FAIL = "fail"
EXIT_CODES = {
    RESULT_PASS: 0,
    RESULT_FAIL: 2,
}
_DOC_PREFIXES = (
    "README.md",
    "AGENTS.md",
    "project-context.md",
    "docs/",
    "prompts/",
    "src/ai_native_package/USAGE.md",
    "src/ai_native_package/API.md",
    "src/ai_native_package/PACKAGING.md",
    "src/ai_native_package/TECH-SPEC.md",
)
_CODE_PREFIXES = (
    "src/",
    "tests/",
)


def _issue(check: str, message: str, **details: Any) -> dict[str, Any]:
    issue = {"check": check, "message": message}
    for key, value in details.items():
        if value is not None:
            issue[key] = value
    return issue


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_schema_path() -> Path:
    return _package_root() / "contracts" / "doc-update-record.schema.json"


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_changed_files(path: Path) -> list[str]:
    payload = _load_json_file(path)
    if not isinstance(payload, list) or not all(isinstance(item, str) for item in payload):
        raise ValueError("changed-files input must be a JSON array of strings")
    return list(payload)


def _validate_schema(instance: Any, schema_path: Path) -> list[dict[str, Any]]:
    if validator_for is None:
        return [_issue("schema", "jsonschema is required to validate doc-update records.")]
    schema = _load_json_file(schema_path)
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    errors: list[dict[str, Any]] = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: item.message):
        errors.append(_issue("schema", error.message))
    return errors


def _is_doc_path(path: str) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in _DOC_PREFIXES)


def _is_code_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _CODE_PREFIXES) and not _is_doc_path(path)


def validate_doc_updates(*, changed_files_path: Path, doc_record_path: Path, schema_path: Path) -> dict[str, Any]:
    changed_files = _load_changed_files(changed_files_path)
    doc_record = _load_json_file(doc_record_path)
    errors = _validate_schema(doc_record, schema_path)

    changed_code_paths = [path for path in changed_files if _is_code_path(path)]
    changed_doc_paths = [path for path in changed_files if _is_doc_path(path)]

    if not isinstance(doc_record, dict):
        errors.append(_issue("record", "doc-update record must be a JSON object."))
        payload: dict[str, Any] = {}
    else:
        payload = doc_record

    record_code_paths = payload.get("code_paths", [])
    if isinstance(record_code_paths, list) and changed_code_paths != record_code_paths:
        errors.append(
            _issue(
                "record_consistency",
                "code_paths in doc-update record must match the changed-files input.",
            )
        )
    record_doc_paths = payload.get("doc_paths", [])
    if isinstance(record_doc_paths, list) and changed_doc_paths != record_doc_paths:
        errors.append(
            _issue(
                "record_consistency",
                "doc_paths in doc-update record must match the changed-files input.",
            )
        )

    status = payload.get("status")
    if changed_code_paths and not changed_doc_paths and status != "not_required":
        errors.append(
            _issue(
                "documentation_impact",
                "Code changes without documentation changes must explicitly declare status = not_required.",
            )
        )
    if changed_code_paths and changed_doc_paths and status != "updated":
        errors.append(
            _issue(
                "documentation_impact",
                "Code changes with documentation updates must declare status = updated.",
            )
        )

    return {
        "validator": VALIDATOR_NAME,
        "result": RESULT_FAIL if errors else RESULT_PASS,
        "errors": errors,
        "inputs": {
            "changed_files": str(changed_files_path.resolve()),
            "doc_record": str(doc_record_path.resolve()),
            "schema": str(schema_path.resolve()),
        },
        "summary": (
            "Doc-update contract checks passed."
            if not errors
            else f"Doc-update contract checks failed with {len(errors)} issue(s)."
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate docs-with-code update records.")
    parser.add_argument("--changed-files", required=True, help="Path to canonical JSON array of changed files.")
    parser.add_argument("--doc-record", required=True, help="Path to doc-update record JSON.")
    parser.add_argument("--schema", default=str(_default_schema_path()), help="Path to doc-update record schema.")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    payload = validate_doc_updates(
        changed_files_path=Path(args.changed_files),
        doc_record_path=Path(args.doc_record),
        schema_path=Path(args.schema),
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
