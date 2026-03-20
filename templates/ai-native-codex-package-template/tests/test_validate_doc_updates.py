from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_validate_doc_updates_passes_when_code_and_docs_align(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_doc_updates import validate_doc_updates

    changed_files = tmp_path / "changed-files.json"
    changed_files.write_text(
        json.dumps(["src/ai_native_package/cli.py", "README.md"]),
        encoding="utf-8",
    )
    doc_record = tmp_path / "doc-update-record.json"
    doc_record.write_text(
        json.dumps(
            {
                "schema_version": "doc-update-record/v1",
                "task_id": "task-doc-update-001",
                "project_root": None,
                "change_summary": "Update CLI behavior and README.",
                "code_paths": ["src/ai_native_package/cli.py"],
                "doc_paths": ["README.md"],
                "doc_update_reason": "README changed with the CLI update.",
                "status": "updated",
                "generated_at": "2026-03-16T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    payload = validate_doc_updates(
        changed_files_path=changed_files,
        doc_record_path=doc_record,
        schema_path=_root() / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json",
    )

    assert payload["result"] == "pass"


def test_validate_doc_updates_fails_when_code_changes_lack_doc_record_alignment(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_doc_updates import validate_doc_updates

    changed_files = tmp_path / "changed-files.json"
    changed_files.write_text(json.dumps(["src/ai_native_package/cli.py"]), encoding="utf-8")
    doc_record = tmp_path / "doc-update-record.json"
    doc_record.write_text(
        json.dumps(
            {
                "schema_version": "doc-update-record/v1",
                "task_id": "task-doc-update-002",
                "project_root": None,
                "change_summary": "Update CLI behavior.",
                "code_paths": ["src/ai_native_package/cli.py"],
                "doc_paths": [],
                "doc_update_reason": "Incorrectly marked as updated without docs.",
                "status": "updated",
                "generated_at": "2026-03-16T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    payload = validate_doc_updates(
        changed_files_path=changed_files,
        doc_record_path=doc_record,
        schema_path=_root() / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json",
    )

    assert payload["result"] == "fail"
    assert any(error["check"] == "documentation_impact" for error in payload["errors"])


def test_cli_validate_doc_updates_emits_json(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    changed_files = tmp_path / "changed-files.json"
    changed_files.write_text(
        json.dumps(["src/ai_native_package/cli.py", "README.md"]),
        encoding="utf-8",
    )
    doc_record = tmp_path / "doc-update-record.json"
    doc_record.write_text(
        json.dumps(
            {
                "schema_version": "doc-update-record/v1",
                "task_id": "task-doc-update-003",
                "project_root": None,
                "change_summary": "Update CLI behavior and README.",
                "code_paths": ["src/ai_native_package/cli.py"],
                "doc_paths": ["README.md"],
                "doc_update_reason": "README changed with the CLI update.",
                "status": "updated",
                "generated_at": "2026-03-16T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "validate-doc-updates",
            "--changed-files",
            str(changed_files),
            "--doc-record",
            str(doc_record),
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["validator"] == "validate-doc-updates"
    assert payload["result"] == "pass"
