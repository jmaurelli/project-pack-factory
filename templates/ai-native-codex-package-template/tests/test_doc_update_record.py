from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_validate_doc_update_record_passes_for_current_package() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_doc_update_record import validate_doc_update_record

    payload = validate_doc_update_record(
        project_root=_root(),
        record_path=_root() / "docs" / "doc-update-record.json",
        schema_path=_root() / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json",
    )

    assert payload["result"] == "pass"
    assert payload["errors"] == []


def test_validate_doc_update_record_fails_when_doc_paths_missing_for_public_code(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_doc_update_record import validate_doc_update_record

    (tmp_path / "src" / "ai_native_package" / "contracts").mkdir(parents=True)
    schema_path = tmp_path / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json"
    schema_path.write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package").mkdir(exist_ok=True)
    (tmp_path / "src" / "ai_native_package" / "cli.py").write_text("print('x')\n", encoding="utf-8")
    record_path = tmp_path / "docs" / "doc-update-record.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(
        json.dumps(
            {
                "schema_version": "doc-update-record/v1",
                "task_id": "task-001",
                "project_root": None,
                "change_summary": "Changed CLI behavior.",
                "code_paths": ["src/ai_native_package/cli.py"],
                "doc_paths": [],
                "doc_update_reason": "No docs updated.",
                "status": "not_required",
                "generated_at": "2026-03-16T00:00:00Z"
            }
        ),
        encoding="utf-8",
    )

    payload = validate_doc_update_record(
        project_root=tmp_path,
        record_path=record_path,
        schema_path=schema_path,
    )

    assert payload["result"] == "fail"
    assert any(error["check"] == "doc_update_record" for error in payload["errors"])


def test_validate_doc_update_record_allows_agent_docs_only_for_public_code(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_doc_update_record import validate_doc_update_record

    (tmp_path / "src" / "ai_native_package" / "contracts").mkdir(parents=True)
    schema_path = tmp_path / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json"
    schema_path.write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package").mkdir(exist_ok=True)
    (tmp_path / "src" / "ai_native_package" / "cli.py").write_text("print('x')\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("## Purpose\n\ntext\n", encoding="utf-8")
    record_path = tmp_path / "docs" / "doc-update-record.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(
        json.dumps(
            {
                "schema_version": "doc-update-record/v1",
                "task_id": "task-002",
                "project_root": None,
                "change_summary": "Changed CLI behavior.",
                "code_paths": ["src/ai_native_package/cli.py"],
                "doc_paths": ["AGENTS.md"],
                "doc_update_reason": "Agent guidance updated for the CLI change.",
                "status": "updated",
                "generated_at": "2026-03-16T00:00:00Z"
            }
        ),
        encoding="utf-8",
    )

    payload = validate_doc_update_record(
        project_root=tmp_path,
        record_path=record_path,
        schema_path=schema_path,
    )

    assert payload["result"] == "pass"
    assert payload["errors"] == []


def test_cli_validate_doc_update_record_emits_json() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        ["validate-doc-update-record", "--project-root", str(_root()), "--output", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["validator"] == "validate-doc-update-record"
    assert payload["result"] == "pass"
