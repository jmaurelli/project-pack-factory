from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_package_metadata_surface_is_explicit_and_re_exported() -> None:
    sys.path.insert(0, str(_src()))
    import ai_native_package
    from ai_native_package import __about__

    assert __about__.PACKAGE_NAME == "ai_native_package"
    assert __about__.MODULE_NAME == "ai_native_package"
    assert __about__.DISTRIBUTION_NAME == "ai-native-codex-package-template"
    assert __about__.__version__ == "0.1.0"
    assert ai_native_package.PACKAGE_NAME == __about__.PACKAGE_NAME
    assert ai_native_package.MODULE_NAME == __about__.MODULE_NAME
    assert ai_native_package.__version__ == __about__.__version__
    assert ai_native_package.get_package_metadata() == {
        "package_name": __about__.PACKAGE_NAME,
        "module_name": __about__.MODULE_NAME,
        "distribution_name": __about__.DISTRIBUTION_NAME,
        "scaffold_version": __about__.SCAFFOLD_VERSION,
        "version": ai_native_package.__version__,
    }


def test_package_root_packaging_config_scopes_build_to_ai_native_package_only() -> None:
    pyproject = tomllib.loads((_root() / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["name"] == "ai-native-codex-package-template"
    assert pyproject["project"]["requires-python"] == ">=3.12"
    assert pyproject["project"]["dependencies"] == [
        "click>=8,<9",
        "jsonschema>=4.25,<5",
        "PyYAML>=6.0.2,<7",
    ]
    assert pyproject["project"]["scripts"] == {
        "ai-native-package": "ai_native_package.cli:main",
    }
    assert pyproject["project"]["optional-dependencies"]["dev"] == [
        "mypy>=1.18,<2",
        "pytest>=9.0,<10",
        "ruff>=0.12,<0.13",
        "types-PyYAML>=6.0.12,<7",
    ]
    assert pyproject["tool"]["setuptools"]["package-dir"] == {"": "src"}
    assert pyproject["tool"]["setuptools"]["packages"]["find"] == {
        "where": ["src"],
        "include": ["ai_native_package*"],
    }


def test_delegate_command_plan_is_codex_native_and_deterministic() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.backends import build_delegate_command_plan
    from ai_native_package.models import WorkflowPlan

    plan = WorkflowPlan(
        task_name="sample-target",
        backend="delegated_worker",
        output_dir="/srv/adf/artifacts/ai-native-codex-package-template",
        contract="/ai-workflow/adf/runtime-contract.json",
        operation_class="delegated_execution",
        cycle_root="/ai-workflow/adf/artifacts/orchestration",
    )

    payload = build_delegate_command_plan(plan, prompt_file="<PROMPT_FILE>")

    assert payload["preflight"] == [
        "python3",
        "/ai-workflow/orchestration/run_adf_delegate.py",
        "--prompt-file",
        "<PROMPT_FILE>",
        "--contract",
        "/ai-workflow/adf/runtime-contract.json",
        "--intent",
        "execution_only",
        "--operation-class",
        "delegated_execution",
        "--delegation-mode",
        "codex_worker",
        "--dry-run",
        "--json",
    ]
    assert payload["dispatch"] == [
        "python3",
        "/ai-workflow/orchestration/run_adf_delegate.py",
        "--prompt-file",
        "<PROMPT_FILE>",
        "--contract",
        "/ai-workflow/adf/runtime-contract.json",
        "--intent",
        "execution_only",
        "--operation-class",
        "delegated_execution",
        "--delegation-mode",
        "codex_worker",
        "--require-preflight-evidence",
        "<PREVIEW>",
        "--json",
    ]


def test_print_plan_payload_includes_rendered_prompt_for_delegated_backend() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.workflow import build_workflow_payload

    payload = build_workflow_payload(
        task_name="sample-target",
        backend="delegated_worker",
        output_dir="/srv/adf/artifacts/ai-native-codex-package-template",
        contract="/ai-workflow/adf/runtime-contract.json",
        operation_class="delegated_execution",
        cycle_root="/ai-workflow/adf/artifacts/orchestration",
        mode="print-plan",
    )

    assert payload["task_name"] == "sample-target"
    assert "delegate_commands" in payload
    assert "rendered_prompt" in payload
    assert "Use /ai-workflow/project-context.md for code-change tasks." in payload["rendered_prompt"]


def test_package_docs_and_prompts_exist() -> None:
    expected_files = [
        _root() / "AGENTS.md",
        _root() / "Makefile",
        _root() / "README.md",
        _root() / "project-context.md",
        _root() / "docs" / "benchmark-first-task.md",
        _root() / "prompts" / "automation-template.md",
        _root() / "prompts" / "operator-short.md",
        _root() / "prompts" / "runbook-strict.md",
        _root() / "src" / "ai_native_package" / "API.md",
        _root() / "src" / "ai_native_package" / "PACKAGING.md",
        _root() / "src" / "ai_native_package" / "agent_telemetry_reader.py",
        _root() / "src" / "ai_native_package" / "brief_summary.py",
        _root() / "src" / "ai_native_package" / "project_bootstrap.py",
        _root() / "src" / "ai_native_package" / "new_project.py",
        _root() / "src" / "ai_native_package" / "run_manifest.py",
        _root() / "src" / "ai_native_package" / "task_checklist.py",
        _root() / "src" / "ai_native_package" / "task_goal.py",
        _root() / "src" / "ai_native_package" / "TEMPLATE-RENAMES.md",
        _root() / "src" / "ai_native_package" / "USAGE.md",
        _root() / "src" / "ai_native_package" / "validators" / "validate_task_goal.py",
    ]

    for path in expected_files:
        assert path.exists(), f"missing expected scaffold file: {path}"
