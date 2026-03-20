from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final, cast

import click

from .agent_memory import build_agent_memory, build_agent_memory_snapshot, derive_agent_memory_path, persist_agent_memory
from .agent_memory_benchmark import run_agent_memory_benchmark
from .constants import (
    COMMAND_BENCHMARK_AGENT_MEMORY,
    COMMAND_READ_AGENT_MEMORY,
    COMMAND_RECORD_AGENT_MEMORY,
    COMMAND_VALIDATE_PROJECT_PACK,
    OUTPUT_MODE_JSON,
    OUTPUT_MODE_TEXT,
    OUTPUT_MODES,
    PROGRAM_HELP,
    PROGRAM_NAME,
)
from .validate_project_pack import validate_project_pack

OUTPUT_CHOICE: Final[click.Choice] = click.Choice(OUTPUT_MODES)


def _emit_json(payload: dict[str, object]) -> int:
    click.echo(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_app() -> click.Group:
    @click.group(name=PROGRAM_NAME, help=PROGRAM_HELP)
    def app() -> None:
        return None

    @app.command(COMMAND_RECORD_AGENT_MEMORY)
    @click.option("--project-root", required=True, type=str, help="Absolute project root for the local memory write.")
    @click.option("--memory-id", required=True, type=str, help="Stable memory artifact identifier.")
    @click.option("--goal", required=True, type=str, help="Current goal this memory should anchor.")
    @click.option(
        "--memory-type",
        required=True,
        type=click.Choice(("blocker", "next_step", "decision", "validation", "lesson", "context")),
        help="Memory category used by retrieval ranking.",
    )
    @click.option("--summary", required=True, type=str, help="Short agent-facing summary.")
    @click.option("--importance", type=click.Choice(("low", "normal", "high", "critical")), default="normal", show_default=True)
    @click.option("--status", type=click.Choice(("active", "resolved", "archived")), default="active", show_default=True)
    @click.option("--goal-status", type=click.Choice(("in_progress", "blocked", "completed", "superseded")), default=None)
    @click.option("--task-name", type=str, default=None)
    @click.option("--task-record-path", type=str, default=None)
    @click.option("--operating-root", type=str, default=None)
    @click.option("--delegation-brief-path", type=str, default=None)
    @click.option("--project-context-reference", "project_context_references", multiple=True, type=str)
    @click.option("--telemetry-path", "telemetry_paths", multiple=True, type=str)
    @click.option("--run-manifest-path", "run_manifest_paths", multiple=True, type=str)
    @click.option("--completion-signal", "completion_signals", multiple=True, type=str)
    @click.option("--primary-validation-command", type=str, default=None)
    @click.option("--recommended-next-command", type=str, default=None)
    @click.option("--blocked-by", "blocked_by", multiple=True, type=str)
    @click.option("--detail", "details", multiple=True, type=str)
    @click.option("--next-action", "next_actions", multiple=True, type=str)
    @click.option("--attempted-command", "attempted_commands", multiple=True, type=str)
    @click.option("--observed-outcome", "observed_outcomes", multiple=True, type=str)
    @click.option("--open-question", "open_questions", multiple=True, type=str)
    @click.option("--tag", "tags", multiple=True, type=str)
    @click.option("--file-path", "file_paths", multiple=True, type=str)
    @click.option("--evidence-path", "evidence_paths", multiple=True, type=str)
    @click.option("--supersedes-memory-id", "supersedes_memory_ids", multiple=True, type=str)
    @click.option("--conflicts-with-memory-id", "conflicts_with_memory_ids", multiple=True, type=str)
    @click.option("--history-confidence", type=click.Choice(("low", "medium", "high")), default=None)
    @click.option("--generated-at", type=str, default=None)
    @click.option("--replace-existing", is_flag=True)
    def record_agent_memory_command(
        project_root: str,
        memory_id: str,
        goal: str,
        memory_type: str,
        summary: str,
        importance: str,
        status: str,
        goal_status: str | None,
        task_name: str | None,
        task_record_path: str | None,
        operating_root: str | None,
        delegation_brief_path: str | None,
        project_context_references: tuple[str, ...],
        telemetry_paths: tuple[str, ...],
        run_manifest_paths: tuple[str, ...],
        completion_signals: tuple[str, ...],
        primary_validation_command: str | None,
        recommended_next_command: str | None,
        blocked_by: tuple[str, ...],
        details: tuple[str, ...],
        next_actions: tuple[str, ...],
        attempted_commands: tuple[str, ...],
        observed_outcomes: tuple[str, ...],
        open_questions: tuple[str, ...],
        tags: tuple[str, ...],
        file_paths: tuple[str, ...],
        evidence_paths: tuple[str, ...],
        supersedes_memory_ids: tuple[str, ...],
        conflicts_with_memory_ids: tuple[str, ...],
        history_confidence: str | None,
        generated_at: str | None,
        replace_existing: bool,
    ) -> int:
        payload = build_agent_memory(
            memory_id=memory_id,
            project_root=Path(project_root),
            goal=goal,
            summary=summary,
            memory_type=memory_type,
            importance=importance,
            status=status,
            goal_status=goal_status,
            task_name=task_name,
            task_record_path=task_record_path,
            operating_root=operating_root,
            delegation_brief_path=delegation_brief_path,
            project_context_reference=project_context_references,
            telemetry_path=telemetry_paths,
            run_manifest_path=run_manifest_paths,
            completion_signal=completion_signals,
            primary_validation_command=primary_validation_command,
            recommended_next_command=recommended_next_command,
            blocked_by=blocked_by,
            detail=details,
            next_action=next_actions,
            attempted_command=attempted_commands,
            observed_outcome=observed_outcomes,
            open_question=open_questions,
            tag=tags,
            file_path=file_paths,
            evidence_path=evidence_paths,
            supersedes_memory_id=supersedes_memory_ids,
            conflicts_with_memory_id=conflicts_with_memory_ids,
            history_confidence=history_confidence,
            generated_at=generated_at,
        )
        output_path = derive_agent_memory_path(memory_id=memory_id, project_root=Path(project_root))
        written_path, archived_path = persist_agent_memory(
            payload,
            output_path=output_path,
            replace_existing=replace_existing,
        )
        return _emit_json(
            {
                "command": COMMAND_RECORD_AGENT_MEMORY,
                "result": "written",
                "output_path": written_path,
                "archived_previous_path": archived_path,
                "replaced_existing": archived_path is not None,
                "memory_id": payload["memory_id"],
                "goal": cast(dict[str, Any], payload["goal_state"])["goal"],
                "goal_state": payload["goal_state"],
                "environment_context": payload["environment_context"],
                "history_context": payload["history_context"],
                "memory_type": payload["memory_type"],
                "status": payload["status"],
                "importance": payload["importance"],
            }
        )

    @app.command(COMMAND_READ_AGENT_MEMORY)
    @click.option("--project-root", required=True, type=str, help="Absolute project root for the local memory read.")
    @click.option("--task-name", type=str, default=None)
    @click.option("--limit", type=click.IntRange(1, None), default=7, show_default=True)
    @click.option("--output", "output_mode", type=OUTPUT_CHOICE, default=OUTPUT_MODE_JSON, show_default=True)
    def read_agent_memory_command(project_root: str, task_name: str | None, limit: int, output_mode: str) -> int:
        payload = build_agent_memory_snapshot(project_root=Path(project_root), task_name=task_name, limit=limit)
        if output_mode == OUTPUT_MODE_JSON:
            return _emit_json(payload)
        handoff_summary = cast(dict[str, Any], payload["handoff_summary"])
        local_artifact_counts = cast(dict[str, Any], payload["local_artifact_counts"])
        click.echo(
            f"memory_count={local_artifact_counts['memory_count']} "
            f"active={local_artifact_counts['active_count']} "
            f"resolved={local_artifact_counts['resolved_count']}"
        )
        for line in cast(list[str], handoff_summary["compact_handoff"]):
            click.echo(line)
        for note in cast(list[str], payload["notes"]):
            click.echo(f"note={note}")
        return 0

    @app.command(COMMAND_BENCHMARK_AGENT_MEMORY)
    @click.option("--fixture-root", type=str, default=None)
    @click.option("--output-path", type=str, default=None)
    @click.option("--snapshot-output-path", type=str, default=None)
    @click.option("--output", "output_mode", type=OUTPUT_CHOICE, default=OUTPUT_MODE_JSON, show_default=True)
    def benchmark_agent_memory_command(
        fixture_root: str | None,
        output_path: str | None,
        snapshot_output_path: str | None,
        output_mode: str,
    ) -> int:
        payload = run_agent_memory_benchmark(
            fixture_root=fixture_root,
            output_path=output_path,
            snapshot_output_path=snapshot_output_path,
        )
        if output_mode == OUTPUT_MODE_TEXT:
            click.echo(f"composite_score={payload['composite_score']}")
            click.echo(f"passed_checks={payload['passed_checks']}")
            click.echo(f"total_checks={payload['total_checks']}")
            return 0
        return _emit_json(payload)

    @app.command(COMMAND_VALIDATE_PROJECT_PACK)
    @click.option("--project-root", required=True, type=str, help="Absolute project root for the PackFactory pack validation.")
    @click.option("--output", "output_mode", type=OUTPUT_CHOICE, default=OUTPUT_MODE_JSON, show_default=True)
    def validate_project_pack_command(project_root: str, output_mode: str) -> int:
        payload = validate_project_pack(project_root=Path(project_root))
        if output_mode == OUTPUT_MODE_JSON:
            return _emit_json(payload)
        click.echo(f"result={payload['result']}")
        click.echo(f"pack_id={payload['pack_id']}")
        click.echo(f"pack_kind={payload['pack_kind']}")
        if payload["errors"]:
            for error in cast(list[str], payload["errors"]):
                click.echo(f"error={error}")
        else:
            click.echo(f"validated_paths={payload['validated_path_count']}")
        return 0

    return app


def main() -> int:
    return build_app()()
