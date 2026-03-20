from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def _build_app():
    sys.path.insert(0, str(_src()))
    from agent_memory_first.cli import build_app

    return build_app()


def _record_args(
    project_root: Path,
    memory_id: str,
    summary: str,
    *,
    memory_type: str = "next_step",
    generated_at: str = "2026-03-17T00:00:01Z",
) -> list[str]:
    return [
        "record-agent-memory",
        "--project-root",
        str(project_root),
        "--memory-id",
        memory_id,
        "--goal",
        "Restart the agent from local memory.",
        "--memory-type",
        memory_type,
        "--summary",
        summary,
        "--task-name",
        "task-a",
        "--task-record-path",
        str(project_root / "task-record.yaml"),
        "--operating-root",
        str(project_root),
        "--delegation-brief-path",
        str(project_root / "delegation-brief.md"),
        "--project-context-reference",
        str(project_root / "project-context.md"),
        "--telemetry-path",
        str(project_root / ".pack-state" / "task-goal-telemetry" / "task-a.json"),
        "--run-manifest-path",
        str(project_root / ".pack-state" / "run-manifests" / "run-001.json"),
        "--completion-signal",
        "recorded",
        "--primary-validation-command",
        "uv run python -m agent_memory_first read-agent-memory --project-root . --output json",
        "--recommended-next-command",
        "uv run python -m agent_memory_first read-agent-memory --project-root . --output json",
        "--blocked-by",
        "local validation not yet run",
        "--detail",
        "Keep the restart state local-only.",
        "--next-action",
        "Read the prioritized snapshot first.",
        "--attempted-command",
        "uv run python -m agent_memory_first read-agent-memory",
        "--observed-outcome",
        "pass",
        "--open-question",
        "Should this supersede an older restart note?",
        "--tag",
        "restart",
        "--file-path",
        "src/agent_memory_first/agent_memory.py",
        "--evidence-path",
        str(project_root / "evidence.json"),
        "--supersedes-memory-id",
        "memory-000",
        "--conflicts-with-memory-id",
        "memory-900",
        "--history-confidence",
        "high",
        "--generated-at",
        generated_at,
    ]


def test_record_agent_memory_cli_exposes_restart_state_and_lineage(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(_build_app(), _record_args(tmp_path, "memory-001", "Capture restart state."))

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"] == "written"
    assert payload["replaced_existing"] is False

    memory_path = Path(payload["output_path"])
    memory_payload = json.loads(memory_path.read_text(encoding="utf-8"))
    assert memory_payload["goal_state"]["goal_status"] == "in_progress"
    assert memory_payload["goal_state"]["primary_validation_command"].startswith("uv run python -m agent_memory_first read-agent-memory")
    assert memory_payload["goal_state"]["completion_signals"][0] == "recorded"
    assert memory_payload["goal_state"]["blocked_by"] == ["local validation not yet run"]
    assert memory_payload["environment_context"]["delegation_brief_path"] == str((tmp_path / "delegation-brief.md").resolve())
    assert memory_payload["history_context"]["supersedes_memory_id"] == "memory-000"
    assert memory_payload["history_context"]["conflicts_with"] == ["memory-900"]
    assert memory_payload["history_context"]["attempted_commands"] == ["uv run python -m agent_memory_first read-agent-memory"]
    assert memory_payload["history_context"]["observed_outcomes"] == ["pass"]
    assert memory_payload["history_context"]["open_questions"] == ["Should this supersede an older restart note?"]

    read_result = runner.invoke(
        _build_app(),
        [
            "read-agent-memory",
            "--project-root",
            str(tmp_path),
            "--limit",
            "1",
            "--output",
            "json",
        ],
    )
    assert read_result.exit_code == 0, read_result.output
    snapshot = json.loads(read_result.output)
    assert snapshot["retrieval_focus"]["importance_before_type"] is True
    assert snapshot["restart_state"]["goals"] == ["Restart the agent from local memory."]
    assert snapshot["restart_state"]["goal_statuses"] == ["in_progress"]
    assert snapshot["restart_state"]["environment_context"]["delegation_brief_paths"] == [str((tmp_path / "delegation-brief.md").resolve())]
    assert snapshot["restart_state"]["history_context"]["open_questions"] == ["Should this supersede an older restart note?"]
    assert snapshot["handoff_summary"]["active_next_steps"]


def test_record_agent_memory_cli_fails_closed_on_duplicate_memory_id(tmp_path: Path) -> None:
    runner = CliRunner()
    first = runner.invoke(_build_app(), _record_args(tmp_path, "memory-001", "Capture restart state."))
    assert first.exit_code == 0, first.output

    second = runner.invoke(_build_app(), _record_args(tmp_path, "memory-001", "Capture restart state."))
    assert second.exit_code != 0
    assert isinstance(second.exception, FileExistsError)
    assert "already exists" in str(second.exception)


def test_record_agent_memory_cli_can_replace_existing_memory(tmp_path: Path) -> None:
    runner = CliRunner()
    first = runner.invoke(_build_app(), _record_args(tmp_path, "memory-001", "Capture restart state."))
    assert first.exit_code == 0, first.output

    replacement = runner.invoke(
        _build_app(),
        _record_args(
            tmp_path,
            "memory-001",
            "Supersede the previous restart state.",
            generated_at="2026-03-17T00:00:02Z",
        )
        + ["--replace-existing"],
    )
    assert replacement.exit_code == 0, replacement.output

    payload = json.loads(replacement.output)
    assert payload["archived_previous_path"] is not None
    assert Path(payload["archived_previous_path"]).exists()
    assert payload["replaced_existing"] is True
