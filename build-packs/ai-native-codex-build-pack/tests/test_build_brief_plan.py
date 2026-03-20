from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_plan_build_brief_returns_stable_python_cli_plan() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.build_brief_plan import build_plan_from_brief

    payload = build_plan_from_brief(
        "Build a small Python CLI that normalizes project briefs and prints a JSON plan."
    )

    assert payload["brief_id"] == "build-a-small-python-cli-that-normalizes-project-briefs-and-prints-a-json-plan"
    assert payload["inferred_language"] == "python"
    assert payload["inferred_project_shape"] == "cli"
    assert payload["project_root"]["selection_mode"] == "agent_deferred"
    assert payload["artifact_root"]["path"] is None
    assert [step["step_id"] for step in payload["plan_steps"]] == [
        "clarify-scope",
        "select-project-root",
        "implement-core",
        "wire-cli",
        "validate",
    ]
    assert any("--project-root /path/to/project" in command for command in payload["recommended_commands"])


def test_plan_build_brief_derives_project_and_artifact_roots() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.build_brief_plan import build_plan_from_brief

    payload = build_plan_from_brief(
        "Build a small Python CLI that prints a JSON plan.",
        project_root="/srv/projects/example-app",
    )

    assert payload["project_root"]["selection_mode"] == "user_provided"
    assert payload["project_root"]["path"] == "/srv/projects/example-app"
    assert payload["artifact_root"]["selection_mode"] == "derived_from_project_root"
    assert payload["artifact_root"]["path"] == "/srv/projects/example-app/.ai-native-codex-package-template/build-plans/build-a-small-python-cli-that-prints-a-json-plan"


def test_plan_build_brief_adapts_to_yaml_and_markdown_brief() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.build_brief_plan import build_plan_from_brief

    payload = build_plan_from_brief(
        "Create a package that reads a YAML build brief and generates a markdown implementation checklist with pytest coverage."
    )

    assert payload["inferred_project_shape"] == "package"
    assert [step["step_id"] for step in payload["plan_steps"]] == [
        "clarify-scope",
        "select-project-root",
        "parse-input",
        "render-output",
        "implement-core",
        "validate",
    ]
    assert payload["friction_flags"] == ["missing_acceptance_criteria", "project_root_deferred"]
    assert "pytest -q tests/test_build_brief_plan.py" in payload["recommended_commands"]


def test_plan_build_brief_flags_missing_acceptance_details() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.build_brief_plan import build_plan_from_brief

    payload = build_plan_from_brief("Build a tool for project setup")

    assert payload["friction_flags"] == [
        "missing_acceptance_criteria",
        "missing_output_definition",
        "missing_validation_hint",
        "project_root_deferred",
    ]
    assert payload["next_questions"][0] == "What project root should this build plan target?"


def test_cli_plan_build_brief_emits_machine_readable_json() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "plan-build-brief",
            "--brief",
            "Build a small Python CLI that normalizes project briefs and prints JSON.",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["brief_id"]
    assert payload["plan_steps"]
    assert payload["recommended_commands"]
    assert payload["artifact_persistence"] == {
        "mode": "deferred_until_project_root",
        "path": None,
    }
