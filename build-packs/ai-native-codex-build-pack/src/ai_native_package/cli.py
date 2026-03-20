from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final, cast

import click

from .backends import (
    DEFAULT_CONTRACT,
    DEFAULT_CYCLE_ROOT,
    DEFAULT_OPERATION_CLASS,
    DEFAULT_OUTPUT_DIR,
)
from .constants import (
    COMMAND_BENCHMARK_AGENT_MEMORY,
    COMMAND_READ_AGENT_TELEMETRY,
    COMMAND_READ_AGENT_MEMORY,
    COMMAND_BUILD_DOC_UPDATE_RECORD,
    COMMAND_BUILD_RUN_MANIFEST,
    COMMAND_NEW_PROJECT,
    COMMAND_PLAN_BUILD_BRIEF,
    COMMAND_RECORD_AGENT_MEMORY,
    COMMAND_RUN_TASK_GOAL_LOOP,
    COMMAND_SUMMARIZE_TASK_GOAL_TELEMETRY,
    COMMAND_RENDER_BRIEF_SUMMARY,
    COMMAND_RENDER_TASK_CHECKLIST,
    COMMAND_POSTTASK,
    COMMAND_PREDISPATCH,
    COMMAND_PRINT_PLAN,
    COMMAND_RUN,
    COMMAND_VALIDATE_GENERATED_AGENT_README,
    COMMAND_VALIDATE_DOC_UPDATE_RECORD,
    COMMAND_VALIDATE_DOC_UPDATES,
    COMMAND_VALIDATE_PROJECT_PACK,
    COMMAND_VALIDATE_TASK_BRIEF,
    COMMAND_VALIDATE_TASK_GOAL,
    COMMAND_VALIDATE_TASK_ORDER_AND_APPROVAL,
    COMMAND_VALIDATE_TASK_SCOPE,
    OUTPUT_MODE_JSON,
    OUTPUT_MODE_MARKDOWN,
    OUTPUT_MODE_TEXT,
    OUTPUT_MODES,
    PROGRAM_HELP,
    PROGRAM_NAME,
)
from .agent_memory import build_agent_memory, build_agent_memory_snapshot, derive_agent_memory_path, persist_agent_memory
from .agent_memory_benchmark import run_agent_memory_benchmark
from .agent_telemetry_reader import build_agent_telemetry_snapshot
from .build_brief_artifacts import derive_default_artifacts_dir, render_build_plan_markdown, write_build_plan_json, write_build_plan_markdown
from .build_brief_plan import build_plan_from_brief
from .brief_summary import write_brief_summary
from .doc_update_record import build_doc_update_record, write_doc_update_record
from .project_bootstrap import create_project_from_template
from .run_manifest import build_run_manifest, derive_run_manifest_path, write_run_manifest
from .task_checklist import write_task_checklist
from .task_goal import LOOP_EXIT_CODES, run_task_goal_loop
from .task_goal_telemetry_summary import (
    build_task_goal_telemetry_summary,
    derive_task_goal_telemetry_summary_path,
    write_task_goal_telemetry_summary,
)
from .orchestration.posttask import main as posttask_main
from .orchestration.predispatch import main as predispatch_main
from .validators.validate_generated_agent_readme import main as validate_generated_agent_readme_main
from .validators.validate_doc_update_record import main as validate_doc_update_record_main
from .validators.validate_doc_updates import main as validate_doc_updates_main
from .validators.validate_project_pack import main as validate_project_pack_main
from .validators.validate_task_brief import main as validate_task_brief_main
from .validators.validate_task_goal import main as validate_task_goal_main
from .validators.validate_task_order_and_approval import main as validate_task_order_and_approval_main
from .validators.validate_task_scope import main as validate_task_scope_main
from .workflow import build_workflow_payload

OUTPUT_CHOICE: Final[click.Choice] = click.Choice(OUTPUT_MODES)


def _emit_json(payload: dict[str, object]) -> int:
    click.echo(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _append_option(argv: list[str], flag: str, value: str | int | None) -> None:
    if value is None:
        return None
    argv.extend((flag, str(value)))
    return None


def _task_goal_exit_code(payload: dict[str, object]) -> int:
    telemetry = payload.get("telemetry")
    if isinstance(telemetry, dict) and telemetry.get("requested") is True and telemetry.get("written") is False:
        return 1
    return LOOP_EXIT_CODES[str(payload["result"])]


def build_app() -> click.Group:
    @click.group(name=PROGRAM_NAME, help=PROGRAM_HELP)
    def app() -> None:
        return None

    @app.command(COMMAND_RUN)
    @click.option("--task", "task_name", required=True, type=str, help="Deterministic task or target name.")
    @click.option("--backend", default="delegated_worker", show_default=True, type=str)
    @click.option("--output-dir", default=DEFAULT_OUTPUT_DIR, show_default=True, type=str)
    @click.option("--contract", default=DEFAULT_CONTRACT, show_default=True, type=str)
    @click.option("--operation-class", default=DEFAULT_OPERATION_CLASS, show_default=True, type=str)
    @click.option("--cycle-root", default=DEFAULT_CYCLE_ROOT, show_default=True, type=str)
    def run(
        task_name: str,
        backend: str,
        output_dir: str,
        contract: str,
        operation_class: str,
        cycle_root: str,
    ) -> int:
        return _emit_json(
            build_workflow_payload(
                task_name=task_name,
                backend=backend,
                output_dir=output_dir,
                contract=contract,
                operation_class=operation_class,
                cycle_root=cycle_root,
                mode=COMMAND_RUN,
            )
        )

    @app.command(COMMAND_PRINT_PLAN)
    @click.option("--task", "task_name", required=True, type=str, help="Deterministic task or target name.")
    @click.option("--backend", default="delegated_worker", show_default=True, type=str)
    @click.option("--output-dir", default=DEFAULT_OUTPUT_DIR, show_default=True, type=str)
    @click.option("--contract", default=DEFAULT_CONTRACT, show_default=True, type=str)
    @click.option("--operation-class", default=DEFAULT_OPERATION_CLASS, show_default=True, type=str)
    @click.option("--cycle-root", default=DEFAULT_CYCLE_ROOT, show_default=True, type=str)
    def print_plan(
        task_name: str,
        backend: str,
        output_dir: str,
        contract: str,
        operation_class: str,
        cycle_root: str,
    ) -> int:
        return _emit_json(
            build_workflow_payload(
                task_name=task_name,
                backend=backend,
                output_dir=output_dir,
                contract=contract,
                operation_class=operation_class,
                cycle_root=cycle_root,
                mode=COMMAND_PRINT_PLAN,
            )
        )

    @app.command(COMMAND_BUILD_RUN_MANIFEST)
    @click.option("--run-id", required=True, type=str, help="Deterministic benchmark run identifier.")
    @click.option("--task-name", required=True, type=str, help="Short task or project label for the run.")
    @click.option("--selected-profile", required=True, type=str, help="Approved framework or pack profile used for the run.")
    @click.option("--project-root", default=None, type=str, help="Optional project root used to derive the default manifest path.")
    @click.option("--output-path", default=None, type=str, help="Optional explicit manifest output path.")
    @click.option("--command", multiple=True, type=str, help="Command run during the benchmark. May be repeated.")
    @click.option("--validation", multiple=True, type=str, help="Validation command run during the benchmark. May be repeated.")
    @click.option("--artifact", multiple=True, type=str, help="Artifact path produced by the run. May be repeated.")
    @click.option("--note", multiple=True, type=str, help="Optional benchmark note. May be repeated.")
    @click.option("--outcome-status", required=True, type=str, help="Outcome status such as pass, fail, or blocked.")
    @click.option("--outcome-summary", default=None, type=str, help="Optional short outcome summary.")
    @click.option("--setup-time-seconds", default=None, type=float, help="Optional setup time metric.")
    @click.option("--execution-time-seconds", default=None, type=float, help="Optional execution time metric.")
    @click.option("--validation-time-seconds", default=None, type=float, help="Optional validation time metric.")
    @click.option("--clarification-count", default=None, type=int, help="Optional clarification count metric.")
    @click.option("--validation-failures", default=None, type=int, help="Optional validation failures metric.")
    @click.option("--files-created", default=None, type=int, help="Optional created-file count metric.")
    @click.option("--files-changed", default=None, type=int, help="Optional changed-file count metric.")
    def build_run_manifest_command(
        run_id: str,
        task_name: str,
        selected_profile: str,
        project_root: str | None,
        output_path: str | None,
        command: tuple[str, ...],
        validation: tuple[str, ...],
        artifact: tuple[str, ...],
        note: tuple[str, ...],
        outcome_status: str,
        outcome_summary: str | None,
        setup_time_seconds: float | None,
        execution_time_seconds: float | None,
        validation_time_seconds: float | None,
        clarification_count: int | None,
        validation_failures: int | None,
        files_created: int | None,
        files_changed: int | None,
    ) -> int:
        payload = build_run_manifest(
            run_id=run_id,
            task_name=task_name,
            selected_profile=selected_profile,
            project_root=project_root,
            command=list(command),
            validation=list(validation),
            artifact=list(artifact),
            note=list(note),
            outcome_status=outcome_status,
            outcome_summary=outcome_summary,
            setup_time_seconds=setup_time_seconds,
            execution_time_seconds=execution_time_seconds,
            validation_time_seconds=validation_time_seconds,
            clarification_count=clarification_count,
            validation_failures=validation_failures,
            files_created=files_created,
            files_changed=files_changed,
        )
        target = output_path
        if target is None:
            if project_root is None:
                raise click.UsageError("Either --output-path or --project-root is required.")
            target = derive_run_manifest_path(run_id=run_id, project_root=project_root)
        payload["manifest_path"] = write_run_manifest(payload, output_path=target)
        return _emit_json(payload)

    @app.command(COMMAND_NEW_PROJECT)
    @click.option("--package-name", required=True, type=str, help="New package distribution name.")
    @click.option("--destination-root", required=True, type=str, help="Directory under which the new package root will be created.")
    @click.option("--module-name", default=None, type=str, help="Optional explicit Python module name.")
    @click.option("--script-name", default=None, type=str, help="Optional explicit console script name.")
    @click.option("--domain", "domain_summary", default=None, type=str, help="Optional short domain summary for the bootstrap manifest.")
    @click.option("--template-root", default=None, type=str, help="Optional explicit template root override for testing or non-default copies.")
    def new_project(
        package_name: str,
        destination_root: str,
        module_name: str | None,
        script_name: str | None,
        domain_summary: str | None,
        template_root: str | None,
    ) -> int:
        return _emit_json(
            create_project_from_template(
                package_name=package_name,
                destination_root=destination_root,
                module_name=module_name,
                script_name=script_name,
                domain_summary=domain_summary,
                template_root=template_root,
            )
        )

    @app.command(COMMAND_PLAN_BUILD_BRIEF)
    @click.option("--brief", "brief_text", type=str, default=None, help="Short natural-language build brief.")
    @click.option("--brief-file", type=str, default=None, help="Path to a UTF-8 text file containing the build brief.")
    @click.option("--project-root", type=str, default=None, help="User-provided project root for repeated pack deployment.")
    @click.option("--artifacts-dir", type=str, default=None, help="Optional directory to persist build-plan artifacts. Overrides project-root-derived artifact placement.")
    @click.option(
        "--output",
        "output_mode",
        type=click.Choice((OUTPUT_MODE_JSON, OUTPUT_MODE_MARKDOWN)),
        default=OUTPUT_MODE_JSON,
        show_default=True,
        help="Command output mode.",
    )
    def plan_build_brief(
        brief_text: str | None,
        brief_file: str | None,
        project_root: str | None,
        artifacts_dir: str | None,
        output_mode: str,
    ) -> int:
        if (brief_text is None) == (brief_file is None):
            raise click.UsageError("Provide exactly one of --brief or --brief-file.")
        if brief_file is not None:
            brief_text = Path(brief_file).read_text(encoding="utf-8")
        assert brief_text is not None
        plan = build_plan_from_brief(brief_text, project_root=project_root)
        resolved_artifacts_dir = artifacts_dir or derive_default_artifacts_dir(plan)
        if resolved_artifacts_dir is not None:
            plan["artifact_files"] = {
                "json": write_build_plan_json(plan, resolved_artifacts_dir),
                "markdown": write_build_plan_markdown(plan, resolved_artifacts_dir),
            }
            plan["artifact_persistence"] = {
                "mode": "explicit_artifacts_dir" if artifacts_dir is not None else "derived_from_project_root",
                "path": resolved_artifacts_dir,
            }
        else:
            plan["artifact_persistence"] = {
                "mode": "deferred_until_project_root",
                "path": None,
            }
        if output_mode == OUTPUT_MODE_MARKDOWN:
            click.echo(render_build_plan_markdown(plan), nl=False)
            return 0
        return _emit_json(plan)

    @app.command(COMMAND_RENDER_BRIEF_SUMMARY)
    @click.option("--brief", "brief_text", type=str, default=None, help="Short natural-language build brief.")
    @click.option("--brief-file", type=str, default=None, help="Path to a UTF-8 text file containing the build brief.")
    @click.option("--output-path", required=True, type=str, help="Markdown file path to write.")
    @click.option("--project-root", type=str, default=None, help="Optional project root for deterministic path context.")
    def render_brief_summary(
        brief_text: str | None,
        brief_file: str | None,
        output_path: str,
        project_root: str | None,
    ) -> int:
        if (brief_text is None) == (brief_file is None):
            raise click.UsageError("Provide exactly one of --brief or --brief-file.")
        if brief_file is not None:
            brief_text = Path(brief_file).read_text(encoding="utf-8")
        assert brief_text is not None
        written_path = write_brief_summary(
            brief_text=brief_text,
            output_path=output_path,
            project_root=project_root,
        )
        return _emit_json(
            {
                "command": COMMAND_RENDER_BRIEF_SUMMARY,
                "output_path": written_path,
                "project_root": project_root,
                "result": "written",
            }
        )

    @app.command(COMMAND_RENDER_TASK_CHECKLIST)
    @click.option("--task-file", required=True, type=str, help="YAML file describing the task checklist.")
    @click.option("--output-path", required=True, type=str, help="Markdown file path to write.")
    @click.option("--title", type=str, default=None, help="Optional explicit markdown title.")
    def render_task_checklist_command(
        task_file: str,
        output_path: str,
        title: str | None,
    ) -> int:
        payload = write_task_checklist(
            task_file=task_file,
            output_path=output_path,
            title=title,
        )
        payload["command"] = COMMAND_RENDER_TASK_CHECKLIST
        payload["result"] = "written"
        payload["task_file"] = str(Path(task_file))
        return _emit_json(payload)

    @app.command(COMMAND_BUILD_DOC_UPDATE_RECORD)
    @click.option("--task-id", required=True, type=str, help="Stable task identifier for the change.")
    @click.option("--change-summary", required=True, type=str, help="Short summary of the code change.")
    @click.option("--code-path", "code_paths", multiple=True, type=str, help="Repeatable repo-relative code path.")
    @click.option("--doc-path", "doc_paths", multiple=True, type=str, help="Repeatable repo-relative documentation path.")
    @click.option("--doc-update-reason", required=True, type=str, help="Why documentation was updated or not required.")
    @click.option("--status", type=click.Choice(("updated", "not_required")), default="updated", show_default=True)
    @click.option("--project-root", type=str, default=None, help="Optional runtime project root for the change context.")
    @click.option("--output-path", type=str, default="docs/doc-update-record.json", show_default=True, help="Path to write the generated doc-update record.")
    @click.option("--generated-at", type=str, default=None, help="Optional explicit timestamp string.")
    @click.option("--print", "print_output", is_flag=True, help="Emit the generated JSON to stdout after writing.")
    def build_doc_update_record_command(
        task_id: str,
        change_summary: str,
        code_paths: tuple[str, ...],
        doc_paths: tuple[str, ...],
        doc_update_reason: str,
        status: str,
        project_root: str | None,
        output_path: str,
        generated_at: str | None,
        print_output: bool,
    ) -> int:
        payload = build_doc_update_record(
            task_id=task_id,
            change_summary=change_summary,
            code_paths=list(code_paths),
            doc_paths=list(doc_paths),
            doc_update_reason=doc_update_reason,
            status=status,
            project_root=project_root,
            generated_at=generated_at,
        )
        written_path = write_doc_update_record(payload, output_path=output_path)
        payload["written_to"] = written_path
        if print_output:
            return _emit_json(payload)
        click.echo(written_path)
        return 0

    @app.command(COMMAND_VALIDATE_TASK_BRIEF)
    @click.option("--brief", required=True, type=str, help="Path to the rendered delegation brief Markdown file.")
    @click.option(
        "--task-record",
        type=str,
        default=None,
        help="Optional path to the authoritative task record YAML file.",
    )
    @click.option(
        "--output",
        "output_mode",
        type=OUTPUT_CHOICE,
        default=OUTPUT_MODE_TEXT,
        show_default=True,
        help="Deterministic output mode.",
    )
    def validate_task_brief(
        brief: str,
        task_record: str | None,
        output_mode: str,
    ) -> int:
        argv = ["--brief", brief, "--output", output_mode]
        _append_option(argv, "--task-record", task_record)
        return validate_task_brief_main(argv)

    @app.command(COMMAND_VALIDATE_TASK_GOAL)
    @click.option(
        "--task-record",
        required=True,
        type=str,
        help="Path to the canonical task-record YAML or JSON file.",
    )
    @click.option(
        "--task-record-schema",
        type=str,
        default=None,
        help="Optional explicit task-record schema path override.",
    )
    @click.option(
        "--output",
        "output_mode",
        type=OUTPUT_CHOICE,
        default=OUTPUT_MODE_TEXT,
        show_default=True,
        help="Deterministic output mode.",
    )
    def validate_task_goal(
        task_record: str,
        task_record_schema: str | None,
        output_mode: str,
    ) -> int:
        argv = ["--task-record", task_record, "--output", output_mode]
        _append_option(argv, "--task-record-schema", task_record_schema)
        return validate_task_goal_main(argv)

    @app.command(COMMAND_RUN_TASK_GOAL_LOOP)
    @click.option(
        "--task-record",
        required=True,
        type=str,
        help="Path to the canonical task-record YAML or JSON file.",
    )
    @click.option(
        "--task-record-schema",
        type=str,
        default=None,
        help="Optional explicit task-record schema path override.",
    )
    @click.option(
        "--output",
        "output_mode",
        type=OUTPUT_CHOICE,
        default=OUTPUT_MODE_TEXT,
        show_default=True,
        help="Deterministic output mode.",
    )
    @click.option(
        "--telemetry-output-path",
        type=str,
        default=None,
        help="Optional explicit task-goal telemetry output path. Relative paths resolve from the task operating_root.",
    )
    @click.option(
        "--run-id",
        type=str,
        default=None,
        help="Optional existing local run id to preserve in task-goal telemetry.",
    )
    @click.option(
        "--build-run-manifest-path",
        type=str,
        default=None,
        help="Optional local build-run-manifest JSON path to correlate into task-goal telemetry.",
    )
    def run_task_goal_loop_command(
        task_record: str,
        task_record_schema: str | None,
        output_mode: str,
        telemetry_output_path: str | None,
        run_id: str | None,
        build_run_manifest_path: str | None,
    ) -> int:
        payload = run_task_goal_loop(
            task_record_path=Path(task_record),
            schema_path=Path(task_record_schema) if task_record_schema is not None else None,
            telemetry_output_path=Path(telemetry_output_path) if telemetry_output_path is not None else None,
            run_id=run_id,
            build_run_manifest_path=Path(build_run_manifest_path) if build_run_manifest_path is not None else None,
        )
        if output_mode == OUTPUT_MODE_JSON:
            _emit_json(payload)
            raise click.exceptions.Exit(_task_goal_exit_code(payload))
        click.echo(f"Task-goal loop result={payload['result']} continue_working={payload['continue_working']}")
        for command_result in payload["command_results"]:
            click.echo(
                f"{command_result['stage']} exit_code={command_result['exit_code']} passed={command_result['passed']} command={command_result['command']}"
            )
        for error in payload["errors"]:
            click.echo(json.dumps(error, sort_keys=True))
        telemetry = payload.get("telemetry")
        if isinstance(telemetry, dict):
            if telemetry.get("written") is True:
                click.echo(f"telemetry_output={telemetry['output_path']}")
            elif telemetry.get("requested") is True:
                click.echo(f"telemetry_error={telemetry['error']}")
        raise click.exceptions.Exit(_task_goal_exit_code(payload))

    @app.command(COMMAND_SUMMARIZE_TASK_GOAL_TELEMETRY)
    @click.option(
        "--telemetry-path",
        "telemetry_paths",
        required=True,
        multiple=True,
        type=str,
        help="Path to one persisted task-goal telemetry JSON artifact. May be repeated.",
    )
    @click.option(
        "--output-path",
        type=str,
        default=None,
        help="Optional explicit summary output path. Defaults beside the pack-scoped telemetry directory.",
    )
    @click.option(
        "--output",
        "output_mode",
        type=click.Choice((OUTPUT_MODE_TEXT, OUTPUT_MODE_JSON)),
        default=OUTPUT_MODE_JSON,
        show_default=True,
        help="Deterministic output mode.",
    )
    def summarize_task_goal_telemetry_command(
        telemetry_paths: tuple[str, ...],
        output_path: str | None,
        output_mode: str,
    ) -> int:
        payload = cast(
            dict[str, Any],
            build_task_goal_telemetry_summary(
            telemetry_paths=[Path(path) for path in telemetry_paths],
            ),
        )
        target = output_path
        if target is None:
            summary_scope = cast(dict[str, Any], payload["summary_scope"])
            project_root = summary_scope["project_root"]
            assert isinstance(project_root, str)
            target = derive_task_goal_telemetry_summary_path(project_root=project_root)
        payload["summary_path"] = write_task_goal_telemetry_summary(
            payload,
            output_path=target,
        )
        if output_mode == OUTPUT_MODE_JSON:
            return _emit_json(payload)
        aggregate_counts = cast(dict[str, Any], payload["aggregate_counts"])
        click.echo(
            f"Task-goal telemetry summary attempts={aggregate_counts['total_attempts']} "
            f"completed={aggregate_counts['completed_count']} "
            f"continue_working={aggregate_counts['continue_working_count']} "
            f"failed={aggregate_counts['failed_count']}"
        )
        click.echo(f"summary_output={payload['summary_path']}")
        for note in cast(list[str], payload["summary_notes"]):
            click.echo(f"note={note}")
        return 0

    @app.command(COMMAND_RECORD_AGENT_MEMORY)
    @click.option(
        "--project-root",
        required=True,
        type=str,
        help="Absolute project root for the agent restart-state memory write.",
    )
    @click.option("--memory-id", required=True, type=str, help="Stable memory artifact identifier.")
    @click.option("--goal", required=True, type=str, help="Current machine-readable goal this memory should anchor.")
    @click.option(
        "--memory-type",
        required=True,
        type=click.Choice(("blocker", "next_step", "decision", "validation", "lesson", "context")),
        help="Memory category used by the retrieval ranking.",
    )
    @click.option("--summary", required=True, type=str, help="Short agent-facing memory summary.")
    @click.option(
        "--importance",
        type=click.Choice(("low", "normal", "high", "critical")),
        default="normal",
        show_default=True,
        help="Importance level used by memory retrieval.",
    )
    @click.option(
        "--status",
        type=click.Choice(("active", "resolved", "archived")),
        default="active",
        show_default=True,
        help="Memory lifecycle status.",
    )
    @click.option(
        "--goal-status",
        type=click.Choice(("in_progress", "blocked", "completed", "superseded")),
        default=None,
        help="Optional explicit goal status override.",
    )
    @click.option("--task-name", type=str, default=None, help="Optional task name for scoped retrieval.")
    @click.option("--task-record-path", type=str, default=None, help="Optional absolute task-record path.")
    @click.option("--operating-root", type=str, default=None, help="Optional absolute operating root.")
    @click.option("--delegation-brief-path", type=str, default=None, help="Optional absolute delegation-brief path.")
    @click.option(
        "--project-context-reference",
        "project_context_references",
        multiple=True,
        type=str,
        help="Optional absolute project-context reference. May be repeated.",
    )
    @click.option(
        "--telemetry-path",
        "--task-goal-telemetry-path",
        "telemetry_paths",
        multiple=True,
        type=str,
        help="Optional absolute task-goal telemetry path. May be repeated.",
    )
    @click.option(
        "--run-manifest-path",
        "--build-run-manifest-path",
        "run_manifest_paths",
        multiple=True,
        type=str,
        help="Optional absolute build-run manifest path. May be repeated.",
    )
    @click.option(
        "--completion-signal",
        "completion_signals",
        multiple=True,
        type=str,
        help="Optional completion signal for the current goal. May be repeated.",
    )
    @click.option(
        "--primary-validation-command",
        type=str,
        default=None,
        help="Optional explicit primary validation command.",
    )
    @click.option(
        "--recommended-next-command",
        type=str,
        default=None,
        help="Optional explicit recommended next command.",
    )
    @click.option(
        "--blocked-by",
        "blocked_by",
        multiple=True,
        type=str,
        help="Optional blocker dependency for the current goal. May be repeated.",
    )
    @click.option("--detail", "details", multiple=True, type=str, help="Optional supporting detail line. May be repeated.")
    @click.option("--next-action", "next_actions", multiple=True, type=str, help="Optional next action. May be repeated.")
    @click.option("--attempted-command", "attempted_commands", multiple=True, type=str, help="Optional attempted command. May be repeated.")
    @click.option("--observed-outcome", "observed_outcomes", multiple=True, type=str, help="Optional observed outcome. May be repeated.")
    @click.option("--open-question", "open_questions", multiple=True, type=str, help="Optional open question. May be repeated.")
    @click.option("--tag", "tags", multiple=True, type=str, help="Optional tag. May be repeated.")
    @click.option("--file-path", "file_paths", multiple=True, type=str, help="Optional related file path. May be repeated.")
    @click.option("--evidence-path", "evidence_paths", multiple=True, type=str, help="Optional supporting evidence path. May be repeated.")
    @click.option("--supersedes-memory-id", "supersedes_memory_ids", multiple=True, type=str, help="Optional superseded memory id. May be repeated.")
    @click.option(
        "--conflicts-with-memory-id",
        "--resolved-by-memory-id",
        "conflicts_with_memory_ids",
        multiple=True,
        type=str,
        help="Optional conflicting memory id for lineage tracking. May be repeated.",
    )
    @click.option(
        "--history-confidence",
        type=click.Choice(("low", "medium", "high")),
        default=None,
        help="Optional explicit lineage confidence level.",
    )
    @click.option("--generated-at", type=str, default=None, help="Optional explicit timestamp string.")
    @click.option(
        "--replace-existing",
        is_flag=True,
        help="Allow replacing an existing memory_id while archiving the previous artifact first.",
    )
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
    @click.option(
        "--project-root",
        required=True,
        type=str,
        help="Absolute project root for the agent restart-state memory read.",
    )
    @click.option(
        "--task-name",
        type=str,
        default=None,
        help="Optional task_name filter for local memory retrieval.",
    )
    @click.option(
        "--limit",
        type=click.IntRange(1, None),
        default=7,
        show_default=True,
        help="Maximum number of prioritized memory artifacts to return.",
    )
    @click.option(
        "--output",
        "output_mode",
        type=click.Choice((OUTPUT_MODE_TEXT, OUTPUT_MODE_JSON)),
        default=OUTPUT_MODE_JSON,
        show_default=True,
        help="Deterministic output mode.",
    )
    def read_agent_memory_command(
        project_root: str,
        task_name: str | None,
        limit: int,
        output_mode: str,
    ) -> int:
        payload = build_agent_memory_snapshot(
            project_root=Path(project_root),
            task_name=task_name,
            limit=limit,
        )
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
    @click.option(
        "--fixture-root",
        type=str,
        default=None,
        help="Optional absolute fixture root. Defaults to a temporary deterministic benchmark fixture.",
    )
    @click.option(
        "--output-path",
        type=str,
        default=None,
        help="Optional JSON scorecard output path.",
    )
    @click.option(
        "--snapshot-output-path",
        type=str,
        default=None,
        help="Optional JSON snapshot output path.",
    )
    def benchmark_agent_memory_command(
        fixture_root: str | None,
        output_path: str | None,
        snapshot_output_path: str | None,
    ) -> int:
        payload = run_agent_memory_benchmark(
            fixture_root=fixture_root,
            output_path=output_path,
            snapshot_output_path=snapshot_output_path,
        )
        return _emit_json(payload)

    @app.command(COMMAND_READ_AGENT_TELEMETRY)
    @click.option(
        "--project-root",
        required=True,
        type=str,
        help="Absolute project root for the local pack telemetry read.",
    )
    @click.option(
        "--task-name",
        type=str,
        default=None,
        help="Optional task_name filter for the latest local telemetry selection.",
    )
    @click.option(
        "--output",
        "output_mode",
        type=click.Choice((OUTPUT_MODE_TEXT, OUTPUT_MODE_JSON)),
        default=OUTPUT_MODE_JSON,
        show_default=True,
        help="Deterministic output mode.",
    )
    def read_agent_telemetry_command(
        project_root: str,
        task_name: str | None,
        output_mode: str,
    ) -> int:
        payload = build_agent_telemetry_snapshot(project_root=Path(project_root), task_name=task_name)
        if output_mode == OUTPUT_MODE_JSON:
            return _emit_json(payload)
        latest_task_goal_telemetry = cast(dict[str, Any], payload["latest_task_goal_telemetry"])
        task_record = cast(dict[str, Any], payload["task_record"])
        task_goal_telemetry_summary = cast(dict[str, Any], payload["task_goal_telemetry_summary"])
        latest_build_run_manifest = cast(dict[str, Any], payload["latest_build_run_manifest"])
        status_summary = cast(dict[str, Any], payload["status_summary"])
        click.echo(f"task_record={task_record['path'] or 'missing'}")
        click.echo(f"latest_task_goal_telemetry={latest_task_goal_telemetry['path'] or 'missing'}")
        click.echo(f"task_goal_telemetry_summary={task_goal_telemetry_summary['path'] or 'missing'}")
        click.echo(f"latest_build_run_manifest={latest_build_run_manifest['path'] or 'missing'}")
        click.echo(
            f"latest_result={status_summary['latest_result']} "
            f"completed={status_summary['latest_completed']} "
            f"continue_working={status_summary['latest_continue_working']}"
        )
        for note in cast(list[str], payload["notes"]):
            click.echo(f"note={note}")
        return 0

    @app.command(COMMAND_VALIDATE_TASK_ORDER_AND_APPROVAL)
    @click.option(
        "--task-record",
        required=True,
        type=str,
        help="Path to the canonical task-record YAML or JSON file.",
    )
    @click.option(
        "--output",
        "output_mode",
        type=OUTPUT_CHOICE,
        default=OUTPUT_MODE_TEXT,
        show_default=True,
        help="Deterministic output mode.",
    )
    def validate_task_order_and_approval(
        task_record: str,
        output_mode: str,
    ) -> int:
        return validate_task_order_and_approval_main(
            ["--task-record", task_record, "--output", output_mode]
        )

    @app.command(COMMAND_VALIDATE_TASK_SCOPE)
    @click.option(
        "--brief",
        type=str,
        default=None,
        help="Optional path to the rendered delegation brief Markdown file.",
    )
    @click.option(
        "--task-record",
        type=str,
        default=None,
        help="Optional path to the authoritative task record YAML file.",
    )
    @click.option(
        "--changed-files",
        required=True,
        type=str,
        help="Path to the canonical UTF-8 JSON array of repo-relative POSIX changed-file paths.",
    )
    @click.option(
        "--output",
        "output_mode",
        type=OUTPUT_CHOICE,
        default=OUTPUT_MODE_TEXT,
        show_default=True,
        help="Deterministic output mode.",
    )
    def validate_task_scope(
        brief: str | None,
        task_record: str | None,
        changed_files: str,
        output_mode: str,
    ) -> int:
        argv = ["--changed-files", changed_files, "--output", output_mode]
        _append_option(argv, "--brief", brief)
        _append_option(argv, "--task-record", task_record)
        return validate_task_scope_main(argv)

    @app.command(COMMAND_VALIDATE_GENERATED_AGENT_README)
    @click.option("--readme", required=True, type=str, help="Path to the rendered generated agent README Markdown file.")
    @click.option(
        "--output",
        "output_mode",
        type=OUTPUT_CHOICE,
        default=OUTPUT_MODE_TEXT,
        show_default=True,
        help="Deterministic output mode.",
    )
    def validate_generated_agent_readme(
        readme: str,
        output_mode: str,
    ) -> int:
        return validate_generated_agent_readme_main(
            ["--readme", readme, "--output", output_mode]
        )

    @app.command(COMMAND_VALIDATE_PROJECT_PACK)
    @click.option("--project-root", default=".", show_default=True, type=str, help="Package root to validate.")
    @click.option("--contract", default=None, type=str, help="Optional explicit project-pack contract path.")
    @click.option(
        "--output",
        "output_mode",
        type=click.Choice((OUTPUT_MODE_TEXT, OUTPUT_MODE_JSON)),
        default=OUTPUT_MODE_TEXT,
        show_default=True,
        help="Deterministic output mode.",
    )
    def validate_project_pack(
        project_root: str,
        contract: str | None,
        output_mode: str,
    ) -> int:
        argv = ["--project-root", project_root, "--output", output_mode]
        _append_option(argv, "--contract", contract)
        return validate_project_pack_main(argv)

    @app.command(COMMAND_VALIDATE_DOC_UPDATE_RECORD)
    @click.option("--project-root", default=".", show_default=True, type=str, help="Package root to validate.")
    @click.option("--record", default=None, type=str, help="Optional explicit doc-update-record path.")
    @click.option("--schema", default=None, type=str, help="Optional explicit doc-update-record schema path.")
    @click.option(
        "--output",
        "output_mode",
        type=click.Choice((OUTPUT_MODE_TEXT, OUTPUT_MODE_JSON)),
        default=OUTPUT_MODE_TEXT,
        show_default=True,
        help="Deterministic output mode.",
    )
    def validate_doc_update_record(
        project_root: str,
        record: str | None,
        schema: str | None,
        output_mode: str,
    ) -> int:
        argv = ["--project-root", project_root, "--output", output_mode]
        _append_option(argv, "--record", record)
        _append_option(argv, "--schema", schema)
        return validate_doc_update_record_main(argv)

    @app.command(COMMAND_VALIDATE_DOC_UPDATES)
    @click.option("--changed-files", required=True, type=str, help="Path to canonical JSON changed-files array.")
    @click.option("--doc-record", required=True, type=str, help="Path to doc-update record JSON.")
    @click.option("--schema", default=None, type=str, help="Optional explicit doc-update record schema path.")
    @click.option(
        "--output",
        "output_mode",
        type=click.Choice((OUTPUT_MODE_TEXT, OUTPUT_MODE_JSON)),
        default=OUTPUT_MODE_TEXT,
        show_default=True,
        help="Deterministic output mode.",
    )
    def validate_doc_updates(
        changed_files: str,
        doc_record: str,
        schema: str | None,
        output_mode: str,
    ) -> int:
        argv = ["--changed-files", changed_files, "--doc-record", doc_record, "--output", output_mode]
        _append_option(argv, "--schema", schema)
        return validate_doc_updates_main(argv)

    @app.command(COMMAND_PREDISPATCH)
    @click.option(
        "--task-record",
        required=True,
        type=str,
        help="Path to the canonical task-record YAML or JSON file.",
    )
    @click.option(
        "--delegation-brief",
        "--brief",
        "delegation_brief",
        type=str,
        default=None,
        help="Optional path to a rendered delegation brief Markdown file. If omitted, the brief is rendered from the task record.",
    )
    @click.option(
        "--artifacts-dir",
        type=str,
        default=None,
        help="Optional directory for persisted validator-result and predispatch-decision artifacts.",
    )
    @click.option(
        "--dispatch-attempt",
        type=int,
        default=1,
        show_default=True,
        help="1-based dispatch-attempt counter for the emitted predispatch-decision artifact.",
    )
    def predispatch(
        task_record: str,
        delegation_brief: str | None,
        artifacts_dir: str | None,
        dispatch_attempt: int,
    ) -> int:
        argv = ["--task-record", task_record, "--dispatch-attempt", str(dispatch_attempt)]
        _append_option(argv, "--delegation-brief", delegation_brief)
        _append_option(argv, "--artifacts-dir", artifacts_dir)
        return predispatch_main(argv)

    @app.command(COMMAND_POSTTASK)
    @click.option(
        "--task-record",
        required=True,
        type=str,
        help="Path to the canonical task-record YAML or JSON file.",
    )
    @click.option(
        "--worker-result",
        required=True,
        type=str,
        help="Path to the canonical worker-result JSON file.",
    )
    @click.option(
        "--artifacts-dir",
        type=str,
        default=None,
        help="Optional directory for persisted validator-result and posttask-decision artifacts.",
    )
    @click.option(
        "--worker-attempt",
        type=int,
        default=1,
        show_default=True,
        help="1-based worker-attempt counter for the emitted posttask-decision artifact.",
    )
    def posttask(
        task_record: str,
        worker_result: str,
        artifacts_dir: str | None,
        worker_attempt: int,
    ) -> int:
        argv = [
            "--task-record",
            task_record,
            "--worker-result",
            worker_result,
            "--worker-attempt",
            str(worker_attempt),
        ]
        _append_option(argv, "--artifacts-dir", artifacts_dir)
        return posttask_main(argv)

    return app


def main(argv: list[str] | None = None) -> int:
    app = build_app()
    return app.main(args=argv, prog_name=PROGRAM_NAME, standalone_mode=False)
