from __future__ import annotations

from pathlib import Path
from typing import cast

import yaml


def _normalize_title(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_task_entry(value: object) -> dict[str, object]:
    if isinstance(value, str):
        string_title = value.strip()
        if not string_title:
            raise ValueError("Task entries must not be empty strings.")
        return {"title": string_title, "done": False}
    if not isinstance(value, dict):
        raise ValueError("Task entries must be strings or objects with a title field.")
    object_title = _normalize_title(value.get("title"))
    if object_title is None:
        raise ValueError("Task entries must declare a non-empty title.")
    done = value.get("done", False)
    if not isinstance(done, bool):
        raise ValueError("Task entry done values must be true or false.")
    return {"title": object_title, "done": done}


def load_task_checklist_payload(task_file: str | Path) -> dict[str, object]:
    payload = yaml.safe_load(Path(task_file).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Task checklist files must contain a single YAML object.")
    tasks_raw = payload.get("tasks")
    if not isinstance(tasks_raw, list) or not tasks_raw:
        raise ValueError("Task checklist files must declare a non-empty tasks list.")
    tasks = [_normalize_task_entry(item) for item in tasks_raw]
    title = _normalize_title(payload.get("title")) or "Task Checklist"
    return {
        "title": title,
        "tasks": tasks,
    }


def render_task_checklist_markdown(
    *,
    task_payload: dict[str, object],
    title: str | None = None,
) -> str:
    tasks = cast(list[dict[str, object]], task_payload["tasks"])
    heading = title or cast(str, task_payload["title"])
    completed_count = sum(1 for item in tasks if bool(item["done"]))

    lines = [
        f"# {heading}",
        "",
        "## Summary",
        "",
        f"- Total tasks: `{len(tasks)}`",
        f"- Completed tasks: `{completed_count}`",
        "",
        "## Checklist",
        "",
    ]
    for task in tasks:
        marker = "x" if bool(task["done"]) else " "
        lines.append(f"- [{marker}] {task['title']}")
    return "\n".join(lines) + "\n"


def write_task_checklist(
    *,
    task_file: str | Path,
    output_path: str | Path,
    title: str | None = None,
) -> dict[str, object]:
    payload = load_task_checklist_payload(task_file)
    tasks = cast(list[dict[str, object]], payload["tasks"])
    rendered_title = title or cast(str, payload["title"])
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        render_task_checklist_markdown(task_payload=payload, title=title),
        encoding="utf-8",
    )
    completed_count = sum(1 for item in tasks if bool(item["done"]))
    return {
        "output_path": str(target),
        "task_count": len(tasks),
        "completed_count": completed_count,
        "title": rendered_title,
    }
