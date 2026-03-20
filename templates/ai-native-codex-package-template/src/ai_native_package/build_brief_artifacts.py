from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Final, cast

_JSON_ARTIFACT_NAME: Final[str] = "build-plan.json"
_MARKDOWN_ARTIFACT_NAME: Final[str] = "build-plan.md"


def derive_default_artifacts_dir(plan: dict[str, object]) -> str | None:
    artifact_root = cast(dict[str, object], plan["artifact_root"])
    path = artifact_root.get("path")
    if path is None:
        return None
    return str(path)


def write_build_plan_json(plan: dict[str, object], output_dir: str | Path) -> str:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / _JSON_ARTIFACT_NAME
    target_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(target_path)


def render_build_plan_markdown(plan: dict[str, object]) -> str:
    plan_steps = cast(Sequence[dict[str, str]], plan["plan_steps"])
    recommended_commands = cast(Sequence[str], plan["recommended_commands"])
    friction_flags = cast(Sequence[str], plan.get("friction_flags", []))
    next_questions = cast(Sequence[str], plan.get("next_questions", []))
    project_root = cast(dict[str, object], plan["project_root"])
    artifact_root = cast(dict[str, object], plan["artifact_root"])

    lines: list[str] = [
        f"# Build Plan: {plan['brief_id']}",
        "",
        "## Summary",
        "",
        str(plan["summary"]),
        "",
        "## Inference",
        "",
        f"- Language: `{plan['inferred_language']}`",
        f"- Project shape: `{plan['inferred_project_shape']}`",
        f"- Project root mode: `{project_root['selection_mode']}`",
        f"- Project root path: `{project_root['path']}`",
        f"- Artifact root mode: `{artifact_root['selection_mode']}`",
        f"- Artifact root path: `{artifact_root['path']}`",
        "",
        "## Plan Steps",
        "",
    ]
    for step in plan_steps:
        lines.append(f"- `{step['step_id']}`: {step['title']} - {step['outcome']}")
    lines.extend(["", "## Recommended Commands", ""])
    for command in recommended_commands:
        lines.append(f"- `{command}`")
    if friction_flags:
        lines.extend(["", "## Friction Flags", ""])
        for flag in friction_flags:
            lines.append(f"- `{flag}`")
    if next_questions:
        lines.extend(["", "## Next Questions", ""])
        for question in next_questions:
            lines.append(f"- {question}")
    return "\n".join(lines) + "\n"


def write_build_plan_markdown(plan: dict[str, object], output_dir: str | Path) -> str:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / _MARKDOWN_ARTIFACT_NAME
    target_path.write_text(render_build_plan_markdown(plan), encoding="utf-8")
    return str(target_path)
