from __future__ import annotations

import re
from pathlib import Path
from typing import Final

_PROJECT_ARTIFACT_DIR = ".ai-native-codex-package-template/build-plans"
_DEFERRED_PROJECT_ROOT_QUESTION: Final[str] = "What project root should this build plan target?"

_PYTHON_KEYWORDS: Final[tuple[str, ...]] = (
    "python",
    "pytest",
    "module",
    "package",
    "cli",
    "command",
)
_CLI_KEYWORDS: Final[tuple[str, ...]] = (
    "cli",
    "command",
    "terminal",
    "script",
)
_ACCEPTANCE_KEYWORDS: Final[tuple[str, ...]] = (
    "acceptance",
    "success",
    "must",
    "should",
    "pass",
    "done",
)
_OUTPUT_KEYWORDS: Final[tuple[str, ...]] = (
    "output",
    "emit",
    "write",
    "print",
    "generate",
    "return",
    "json",
    "file",
    "plan",
    "report",
    "markdown",
    "checklist",
)
_VALIDATION_KEYWORDS: Final[tuple[str, ...]] = (
    "test",
    "pytest",
    "validate",
    "lint",
    "mypy",
    "ruff",
    "check",
)


def _normalize_brief(brief: str) -> str:
    normalized = " ".join(brief.strip().split())
    if not normalized:
        raise ValueError("brief must not be empty")
    return normalized


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    collapsed = re.sub(r"-+", "-", slug)
    return collapsed or "build-brief"


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _infer_language(text: str) -> str:
    if _contains_any(text, _PYTHON_KEYWORDS):
        return "python"
    return "python"


def _infer_project_shape(text: str) -> str:
    if _contains_any(text, _CLI_KEYWORDS):
        return "cli"
    return "package"


def derive_build_plan_artifact_dir(*, project_root: str, brief_id: str) -> str:
    resolved_project_root = str(Path(project_root).expanduser().resolve(strict=False))
    return str(Path(resolved_project_root) / _PROJECT_ARTIFACT_DIR / brief_id)


def _project_root_payload(project_root: str | None) -> dict[str, object]:
    if project_root is None:
        return {
            "selection_mode": "agent_deferred",
            "path": None,
            "status": "project_root_required",
        }
    resolved = str(Path(project_root).expanduser().resolve(strict=False))
    return {
        "selection_mode": "user_provided",
        "path": resolved,
        "status": "selected",
    }


def _artifact_root_payload(project_root_payload: dict[str, object], brief_id: str) -> dict[str, object]:
    project_root_path = project_root_payload["path"]
    if project_root_path is None:
        return {
            "selection_mode": "deferred_until_project_root",
            "path": None,
            "status": "project_root_required",
            "derivation": "requires_project_root",
        }
    return {
        "selection_mode": "derived_from_project_root",
        "path": derive_build_plan_artifact_dir(project_root=str(project_root_path), brief_id=brief_id),
        "status": "ready",
        "derivation": "<project_root>/.ai-native-codex-package-template/build-plans/<brief_id>",
    }


def _artifact_persistence_payload(artifact_root_payload: dict[str, object]) -> dict[str, object]:
    return {
        "mode": str(artifact_root_payload["selection_mode"]),
        "path": artifact_root_payload["path"],
    }


def _friction_flags(text: str, project_root_payload: dict[str, object]) -> list[str]:
    flags: list[str] = []
    if not _contains_any(text, _ACCEPTANCE_KEYWORDS):
        flags.append("missing_acceptance_criteria")
    if not _contains_any(text, _OUTPUT_KEYWORDS):
        flags.append("missing_output_definition")
    if not _contains_any(text, _VALIDATION_KEYWORDS):
        flags.append("missing_validation_hint")
    if project_root_payload["path"] is None:
        flags.append("project_root_deferred")
    return flags


def _next_questions(
    flags: list[str],
    project_shape: str,
    project_root_payload: dict[str, object],
) -> list[str]:
    questions: list[str] = []
    if project_root_payload["path"] is None:
        questions.append(_DEFERRED_PROJECT_ROOT_QUESTION)
    if "missing_output_definition" in flags:
        questions.append("What single output should the first version produce?")
    if "missing_acceptance_criteria" in flags:
        questions.append("What result will count as done for the first version?")
    if "missing_validation_hint" in flags:
        questions.append("What is the smallest command or test that should prove the feature works?")
    if not questions and project_shape == "cli":
        questions.append("Should the first version print JSON, text, or both?")
    return questions


def _recommended_commands(text: str, project_shape: str, project_root_payload: dict[str, object]) -> list[str]:
    commands = ["PYTHONPATH=src python3 -m ai_native_package --help"]
    project_root_path = project_root_payload["path"]
    if project_shape == "cli":
        if project_root_path is None:
            commands.append(
                'PYTHONPATH=src python3 -m ai_native_package plan-build-brief --brief "Build a small Python CLI that prints a JSON plan." --project-root /path/to/project'
            )
        else:
            commands.append(
                f'PYTHONPATH=src python3 -m ai_native_package plan-build-brief --brief "Build a small Python CLI that prints a JSON plan." --project-root {project_root_path}'
            )
    if "pytest" in text or "test" in text:
        commands.append("pytest -q tests/test_build_brief_plan.py")
    commands.append("pytest -q tests/test_ai_native_package_scaffold.py")
    commands.append("make validate")
    return commands


def _plan_steps(text: str, project_shape: str, project_root_payload: dict[str, object]) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = [
        {
            "step_id": "clarify-scope",
            "title": "Clarify scope and constraints",
            "outcome": "Define one small deliverable and preserve package-local scope.",
        }
    ]
    if project_root_payload["path"] is None:
        steps.append(
            {
                "step_id": "select-project-root",
                "title": "Select or confirm the project root",
                "outcome": "Use a user-provided project root or record an agent-selected root before writing project artifacts.",
            }
        )
    if "yaml" in text:
        steps.append(
            {
                "step_id": "parse-input",
                "title": "Normalize YAML input handling",
                "outcome": "Parse the declared YAML brief shape deterministically before downstream processing.",
            }
        )
    if "markdown" in text or "checklist" in text or "report" in text:
        steps.append(
            {
                "step_id": "render-output",
                "title": "Render the requested output format",
                "outcome": "Produce the requested markdown or checklist output with a stable structure.",
            }
        )
    steps.append(
        {
            "step_id": "implement-core",
            "title": "Implement core logic in a small module",
            "outcome": "Keep orchestration and parsing separate from the CLI entrypoint.",
        }
    )
    if project_shape == "cli":
        steps.append(
            {
                "step_id": "wire-cli",
                "title": "Expose the behavior through the CLI",
                "outcome": "Keep the command surface thin and machine-readable.",
            }
        )
    steps.append(
        {
            "step_id": "validate",
            "title": "Run focused validation",
            "outcome": "Confirm CLI help and the smallest useful tests pass.",
        }
    )
    return steps


def build_plan_from_brief(brief: str, *, project_root: str | None = None) -> dict[str, object]:
    summary = _normalize_brief(brief)
    lowered = summary.lower()
    brief_id = _slugify(summary)
    inferred_language = _infer_language(lowered)
    inferred_project_shape = _infer_project_shape(lowered)
    project_root_payload = _project_root_payload(project_root)
    artifact_root_payload = _artifact_root_payload(project_root_payload, brief_id)
    flags = _friction_flags(lowered, project_root_payload)
    return {
        "brief": summary,
        "brief_id": brief_id,
        "summary": summary,
        "inferred_language": inferred_language,
        "inferred_project_shape": inferred_project_shape,
        "project_root": project_root_payload,
        "artifact_root": artifact_root_payload,
        "artifact_persistence": _artifact_persistence_payload(artifact_root_payload),
        "recommended_commands": _recommended_commands(lowered, inferred_project_shape, project_root_payload),
        "plan_steps": _plan_steps(lowered, inferred_project_shape, project_root_payload),
        "friction_flags": flags,
        "next_questions": _next_questions(flags, inferred_project_shape, project_root_payload),
    }
