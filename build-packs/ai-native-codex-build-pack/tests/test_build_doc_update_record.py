from __future__ import annotations

import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_build_doc_update_record_returns_deterministic_payload() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.doc_update_record import build_doc_update_record

    payload = build_doc_update_record(
        task_id="task-doc-001",
        change_summary="Update CLI behavior and docs.",
        code_paths=["src/ai_native_package/cli.py", "src/ai_native_package/cli.py"],
        doc_paths=["README.md", "AGENTS.md", "README.md"],
        doc_update_reason="CLI behavior changed.",
        status="updated",
        project_root="/srv/projects/example-app",
        generated_at="2026-03-16T00:00:00Z",
    )

    assert payload["schema_version"] == "doc-update-record/v1"
    assert payload["code_paths"] == ["src/ai_native_package/cli.py"]
    assert payload["doc_paths"] == ["AGENTS.md", "README.md"]
    assert payload["generated_at"] == "2026-03-16T00:00:00Z"


def test_cli_build_doc_update_record_writes_default_file(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "build-doc-update-record",
            "--task-id", "task-doc-002",
            "--change-summary", "Update CLI behavior and docs.",
            "--code-path", "src/ai_native_package/cli.py",
            "--doc-path", "README.md",
            "--doc-path", "AGENTS.md",
            "--doc-update-reason", "CLI behavior changed.",
            "--output-path", str(tmp_path / "docs" / "doc-update-record.json"),
        ],
    )

    assert result.exit_code == 0
    record_path = Path(result.output.strip())
    assert record_path.exists()


def test_generated_record_passes_validate_doc_update_record(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.doc_update_record import build_doc_update_record, write_doc_update_record
    from ai_native_package.validators.validate_doc_update_record import validate_doc_update_record

    (tmp_path / "README.md").write_text("# x\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# x\n", encoding="utf-8")
    (tmp_path / "project-context.md").write_text("# x\n", encoding="utf-8")
    (tmp_path / "src" / "ai_native_package").mkdir(parents=True)
    (tmp_path / "src" / "ai_native_package" / "cli.py").write_text("print('x')\n", encoding="utf-8")
    payload = build_doc_update_record(
        task_id="task-doc-003",
        change_summary="Update CLI behavior and docs.",
        code_paths=["src/ai_native_package/cli.py"],
        doc_paths=["README.md", "AGENTS.md", "project-context.md"],
        doc_update_reason="CLI behavior changed.",
        status="updated",
    )
    record_path = Path(write_doc_update_record(payload, output_path=tmp_path / "docs" / "doc-update-record.json"))
    schema_path = _root() / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json"

    result = validate_doc_update_record(
        project_root=tmp_path,
        record_path=record_path,
        schema_path=schema_path,
    )

    assert result["result"] == "pass"
