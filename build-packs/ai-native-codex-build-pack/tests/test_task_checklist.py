from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_write_task_checklist_persists_markdown(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_checklist import write_task_checklist

    task_file = tmp_path / "tasks.yaml"
    task_file.write_text(
        "title: Release Checklist\n"
        "tasks:\n"
        "  - title: Confirm tests pass\n"
        "    done: true\n"
        "  - Publish release notes\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "checklist.md"

    payload = write_task_checklist(task_file=task_file, output_path=output_path)

    markdown = output_path.read_text(encoding="utf-8")
    assert payload["task_count"] == 2
    assert payload["completed_count"] == 1
    assert "# Release Checklist" in markdown
    assert "- [x] Confirm tests pass" in markdown
    assert "- [ ] Publish release notes" in markdown


def test_cli_render_task_checklist_writes_json_result(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    task_file = tmp_path / "tasks.yaml"
    task_file.write_text(
        "title: Sprint Tasks\n"
        "tasks:\n"
        "  - Draft release note summary\n"
        "  - title: Confirm smoke test\n"
        "    done: true\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "tasks.md"
    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "render-task-checklist",
            "--task-file",
            str(task_file),
            "--output-path",
            str(output_path),
            "--title",
            "Custom Sprint Checklist",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["command"] == "render-task-checklist"
    assert payload["task_count"] == 2
    assert payload["completed_count"] == 1
    assert payload["title"] == "Custom Sprint Checklist"
    assert output_path.exists()
