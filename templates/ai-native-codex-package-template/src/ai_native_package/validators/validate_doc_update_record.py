from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled at runtime
    validator_for = cast(Any, None)

VALIDATOR_NAME = "validate-doc-update-record"
RESULT_PASS = "pass"
RESULT_FAIL = "fail"
EXIT_CODES = {
    RESULT_PASS: 0,
    RESULT_FAIL: 2,
}
_DOCS_REQUIRED_CODE_PATTERNS = (
    "src/ai_native_package/cli.py",
    "src/ai_native_package/api.py",
    "src/ai_native_package/__init__.py",
)
_DOCS_REQUIRED_DOC_PATHS = (
    "AGENTS.md",
)


def _issue(check: str, message: str, **details: Any) -> dict[str, Any]:
    issue = {"check": check, "message": message}
    for key, value in details.items():
        if value is not None:
            issue[key] = value
    return issue


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_record_path() -> Path:
    return _package_root().parents[1] / "docs" / "doc-update-record.json"


def _default_schema_path() -> Path:
    return _package_root() / "contracts" / "doc-update-record.schema.json"


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_schema_path(path_segments: Any) -> str:
    parts = [str(segment) for segment in path_segments]
    return ".".join(parts) if parts else "$"


def _validate_with_schema(*, instance: Any, schema: dict[str, Any], source: str) -> list[dict[str, Any]]:
    if validator_for is None:
        return [
            _issue(
                "doc_update_schema",
                "The `jsonschema` dependency is required to validate doc-update records.",
                source=source,
            )
        ]
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    errors: list[dict[str, Any]] = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: (_format_schema_path(item.path), item.message)):
        errors.append(
            _issue(
                "doc_update_schema",
                error.message,
                source=source,
                path=_format_schema_path(error.path),
            )
        )
    return errors


def validate_doc_update_record(*, project_root: Path, record_path: Path, schema_path: Path) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    if not record_path.exists():
        errors.append(_issue("doc_update_record", "Doc update record is missing.", path=str(record_path)))
        return {
            "validator": VALIDATOR_NAME,
            "result": RESULT_FAIL,
            "errors": errors,
            "inputs": {
                "project_root": str(project_root.resolve()),
                "record": str(record_path),
                "schema": str(schema_path),
            },
            "summary": "Doc update record validation failed with 1 issue(s).",
        }

    record = _load_json_file(record_path)
    schema = _load_json_file(schema_path)
    errors.extend(_validate_with_schema(instance=record, schema=schema, source=str(record_path)))
    if errors:
        return {
            "validator": VALIDATOR_NAME,
            "result": RESULT_FAIL,
            "errors": errors,
            "inputs": {
                "project_root": str(project_root.resolve()),
                "record": str(record_path),
                "schema": str(schema_path),
            },
            "summary": f"Doc update record validation failed with {len(errors)} issue(s).",
        }

    code_paths = cast(list[str], record.get("code_paths", []))
    doc_paths = cast(list[str], record.get("doc_paths", []))
    status = cast(str, record.get("status"))
    reason = cast(str, record.get("doc_update_reason"))

    for rel_path in code_paths:
        if not (project_root / rel_path).exists():
            errors.append(_issue("doc_update_record", "Listed code path does not exist.", path=rel_path))
    for rel_path in doc_paths:
        if not (project_root / rel_path).exists():
            errors.append(_issue("doc_update_record", "Listed doc path does not exist.", path=rel_path))

    if code_paths:
        if status == "updated" and not doc_paths:
            errors.append(_issue("doc_update_record", "Updated code requires at least one documented doc path."))
        if status == "not_required" and not reason.strip():
            errors.append(_issue("doc_update_record", "`not_required` status requires a non-empty justification."))

    if any(path in _DOCS_REQUIRED_CODE_PATTERNS for path in code_paths):
        if status != "updated":
            errors.append(
                _issue(
                    "doc_update_record",
                    "Public or CLI-facing code changes require documentation updates.",
                    status=status,
                )
            )
        for required_doc in _DOCS_REQUIRED_DOC_PATHS:
            if required_doc not in doc_paths:
                errors.append(
                    _issue(
                        "doc_update_record",
                        "Public or CLI-facing code changes require mandatory agent docs to be listed.",
                        path=required_doc,
                    )
                )

    return {
        "validator": VALIDATOR_NAME,
        "result": RESULT_FAIL if errors else RESULT_PASS,
        "errors": errors,
        "inputs": {
            "project_root": str(project_root.resolve()),
            "record": str(record_path),
            "schema": str(schema_path),
        },
        "summary": (
            "Doc update record validation passed."
            if not errors
            else f"Doc update record validation failed with {len(errors)} issue(s)."
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the docs-with-code update record.")
    parser.add_argument("--project-root", default=".", help="Package root to validate.")
    parser.add_argument("--record", default=str(_default_record_path()), help="Path to doc-update-record JSON.")
    parser.add_argument("--schema", default=str(_default_schema_path()), help="Path to doc-update-record schema JSON.")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    payload = validate_doc_update_record(
        project_root=Path(args.project_root),
        record_path=Path(args.record),
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
