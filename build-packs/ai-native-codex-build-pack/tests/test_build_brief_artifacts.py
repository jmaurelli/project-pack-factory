from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_write_build_plan_artifacts_persists_json_and_markdown(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.build_brief_artifacts import (
        write_build_plan_json,
        write_build_plan_markdown,
    )
    from ai_native_package.build_brief_plan import build_plan_from_brief

    plan = build_plan_from_brief(
        "Build a small Python CLI that prints a JSON plan.",
        project_root=str(tmp_path / "example-project"),
    )

    json_path = write_build_plan_json(plan, tmp_path)
    markdown_path = write_build_plan_markdown(plan, tmp_path)

    assert Path(json_path).name == "build-plan.json"
    assert Path(markdown_path).name == "build-plan.md"
    assert json.loads(Path(json_path).read_text(encoding="utf-8"))["brief_id"] == plan["brief_id"]
    assert "# Build Plan:" in Path(markdown_path).read_text(encoding="utf-8")


def test_cli_plan_build_brief_derives_artifact_root_from_project_root(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    project_root = tmp_path / "example-project"
    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "plan-build-brief",
            "--brief",
            "Build a small Python CLI that prints a JSON plan.",
            "--project-root",
            str(project_root),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    artifact_files = payload["artifact_files"]
    assert Path(artifact_files["json"]).exists()
    assert Path(artifact_files["markdown"]).exists()
    assert payload["artifact_persistence"]["mode"] == "derived_from_project_root"
