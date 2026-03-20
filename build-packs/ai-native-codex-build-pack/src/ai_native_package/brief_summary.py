from __future__ import annotations

from pathlib import Path
from typing import cast

from .build_brief_plan import build_plan_from_brief


def render_brief_summary_markdown(*, brief_text: str, project_root: str | None = None) -> str:
    plan = build_plan_from_brief(brief_text, project_root=project_root)
    recommended_commands = cast(list[str], plan["recommended_commands"])
    project_root_payload = cast(dict[str, object], plan["project_root"])
    artifact_root_payload = cast(dict[str, object], plan["artifact_root"])
    next_questions = cast(list[str], plan.get("next_questions", []))

    lines: list[str] = [
        "# Project Summary",
        "",
        "## Goal",
        "",
        str(plan["summary"]),
        "",
        "## Inputs",
        "",
        "- Brief text provided: `yes`",
        f"- Inferred language: `{plan['inferred_language']}`",
        f"- Inferred project shape: `{plan['inferred_project_shape']}`",
        f"- Project root mode: `{project_root_payload['selection_mode']}`",
        f"- Project root path: `{project_root_payload['path']}`",
        "",
        "## Outputs",
        "",
        "- Markdown project summary",
        f"- Build artifact root mode: `{artifact_root_payload['selection_mode']}`",
        f"- Build artifact root path: `{artifact_root_payload['path']}`",
        "",
        "## Validation Commands",
        "",
    ]
    for command in recommended_commands:
        lines.append(f"- `{command}`")
    if next_questions:
        lines.extend(["", "## Open Questions", ""])
        for question in next_questions:
            lines.append(f"- {question}")
    return "\n".join(lines) + "\n"


def write_brief_summary(
    *,
    brief_text: str,
    output_path: str | Path,
    project_root: str | None = None,
) -> str:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_brief_summary_markdown(brief_text=brief_text, project_root=project_root),
        encoding="utf-8",
    )
    return str(target)
