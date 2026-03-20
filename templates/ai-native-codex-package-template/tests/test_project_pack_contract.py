from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_validate_project_pack_passes_for_current_package() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_project_pack import validate_project_pack

    payload = validate_project_pack(
        project_root=_root(),
        contract_path=_root() / "src" / "ai_native_package" / "contracts" / "project-pack.contract.json",
    )

    assert payload["result"] == "pass"
    assert payload["errors"] == []


def test_validate_project_pack_reports_missing_required_agent_doc(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_project_pack import validate_project_pack

    (tmp_path / "src" / "ai_native_package" / "contracts").mkdir(parents=True)
    contract_path = tmp_path / "src" / "ai_native_package" / "contracts" / "project-pack.contract.json"
    contract_path.write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "project-pack.contract.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    payload = validate_project_pack(project_root=tmp_path, contract_path=contract_path)

    assert payload["result"] == "fail"
    assert any(error.get("path") == "AGENTS.md" for error in payload["errors"])


def test_validate_project_pack_allows_missing_startup_human_docs(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_project_pack import validate_project_pack

    (tmp_path / "src" / "ai_native_package" / "contracts").mkdir(parents=True)
    contract_path = tmp_path / "src" / "ai_native_package" / "contracts" / "project-pack.contract.json"
    contract_path.write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "project-pack.contract.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "benchmark-first-task.md").write_text("# task\n", encoding="utf-8")
    (tmp_path / "docs" / "doc-update-record.json").write_text(
        json.dumps(
            {
                "schema_version": "doc-update-record/v1",
                "task_id": "task-early-001",
                "project_root": None,
                "change_summary": "Initial project setup.",
                "code_paths": [],
                "doc_paths": ["AGENTS.md"],
                "doc_update_reason": "Agent docs established for project startup.",
                "status": "updated",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json").write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "contracts" / "framework-profiles.json").write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "framework-profiles.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "templates").mkdir(parents=True)
    (tmp_path / "src" / "ai_native_package" / "templates" / "task-record.yaml").write_text(
        (_root() / "src" / "ai_native_package" / "templates" / "task-record.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "contracts" / "task-record.schema.json").write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "task-record.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "cli.py").write_text(
        "validate-task-goal\nrun-task-goal-loop\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "framework-profiles").mkdir(parents=True)
    for rel in ["python-cli-click.md", "python-api-fastapi.md"]:
        (tmp_path / "docs" / "framework-profiles" / rel).write_text(
            (_root() / "docs" / "framework-profiles" / rel).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (tmp_path / "AGENTS.md").write_text(
        "## Purpose\n\ntext\n\n## Working Rules\n\n- minimal\n- thin CLI\n- minimal, high-signal tests\n- test-first for new behavior when feasible\n- task record as the goal contract\n- primary goal gate\n- keep iterating if it fails\n- stop only when the declared validation path passes\n- human-facing docs are optional at project start\n\n## Done Criteria\n\ntext\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["click>=8,<9", "jsonschema>=4.25,<5"]\n[project.optional-dependencies]\ndev = ["pytest>=9.0,<10", "ruff>=0.12,<0.13", "mypy>=1.18,<2"]\n',
        encoding="utf-8",
    )

    payload = validate_project_pack(project_root=tmp_path, contract_path=contract_path)

    assert payload["result"] == "pass"
    assert payload["errors"] == []


def test_validate_project_pack_reports_missing_plain_language_definition(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_project_pack import validate_project_pack

    (tmp_path / "src" / "ai_native_package" / "contracts").mkdir(parents=True)
    contract_path = tmp_path / "src" / "ai_native_package" / "contracts" / "project-pack.contract.json"
    contract_path.write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "project-pack.contract.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs" / "benchmark-first-task.md").write_text("# task\n", encoding="utf-8")
    (tmp_path / "docs" / "doc-update-record.json").write_text(
        (_root() / "docs" / "doc-update-record.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json").write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "doc-update-record.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "contracts" / "framework-profiles.json").write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "framework-profiles.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "framework-profiles").mkdir(parents=True)
    (tmp_path / "docs" / "framework-profiles" / "python-cli-click.md").write_text(
        (_root() / "docs" / "framework-profiles" / "python-cli-click.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "## Read First\n\nplain language benchmark deterministic\n\n## Validation Surface\n\ntext\n\n## Deployment Root\n\ntext\n\n## Key Terms\n\n- Artifact: saved output file.\n",
        encoding="utf-8",
    )
    (tmp_path / "AGENTS.md").write_text(
        "## Purpose\n\ntext\n\n## Working Rules\n\n- minimal\n- thin CLI\n- minimal, high-signal tests\n- test-first for new behavior when feasible\n- task record as the goal contract\n- primary goal gate\n- keep iterating if it fails\n- stop only when the declared validation path passes\n\n## Done Criteria\n\ntext\n",
        encoding="utf-8",
    )
    (tmp_path / "project-context.md").write_text(
        "## Mission\n\nplain language benchmark deterministic\n\n## Package Standards\n\n- minimal\n- thin CLI\n- approved CLI framework baseline: click\n- test-first for new behavior when feasible\n- the first validation command is the primary goal gate\n- stop only when the declared validation path passes\n\n## Success Criteria For Small Benchmark Tasks\n\ntext\n\n## What This Means\n\ntext\n",
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["click>=8,<9", "jsonschema>=4.25,<5"]\n[project.optional-dependencies]\ndev = ["pytest>=9.0,<10", "ruff>=0.12,<0.13", "mypy>=1.18,<2"]\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "templates").mkdir(parents=True)
    (tmp_path / "src" / "ai_native_package" / "templates" / "task-record.yaml").write_text(
        (_root() / "src" / "ai_native_package" / "templates" / "task-record.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "contracts" / "task-record.schema.json").write_text(
        (_root() / "src" / "ai_native_package" / "contracts" / "task-record.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (tmp_path / "src" / "ai_native_package" / "cli.py").write_text(
        "validate-task-goal\nrun-task-goal-loop\n",
        encoding="utf-8",
    )

    payload = validate_project_pack(project_root=tmp_path, contract_path=contract_path)

    assert payload["result"] == "fail"
    assert any(error.get("term") == "Contract" for error in payload["errors"])


def test_cli_validate_project_pack_emits_json() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        ["validate-project-pack", "--project-root", str(_root()), "--output", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["validator"] == "validate-project-pack"
    assert payload["result"] == "pass"
