from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_write_brief_summary_persists_markdown(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.brief_summary import write_brief_summary

    output_path = tmp_path / "project-summary.md"
    written = write_brief_summary(
        brief_text="Build a small Python CLI that writes a markdown project summary.",
        output_path=output_path,
        project_root=str(tmp_path / "demo-project"),
    )

    summary = Path(written).read_text(encoding="utf-8")
    assert Path(written).name == "project-summary.md"
    assert "# Project Summary" in summary
    assert "## Validation Commands" in summary
    assert "pytest -q" in summary


def test_cli_render_brief_summary_writes_json_result(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    brief_file = tmp_path / "brief.txt"
    brief_file.write_text(
        "Build a small Python CLI that writes a markdown project summary.",
        encoding="utf-8",
    )
    output_path = tmp_path / "project-summary.md"
    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "render-brief-summary",
            "--brief-file",
            str(brief_file),
            "--output-path",
            str(output_path),
            "--project-root",
            str(tmp_path / "demo-project"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["result"] == "written"
    assert payload["output_path"] == str(output_path)
    assert output_path.exists()
