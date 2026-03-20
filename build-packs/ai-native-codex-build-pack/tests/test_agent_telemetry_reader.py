from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def _write_task_goal_telemetry(
    path: Path,
    *,
    task_name: str,
    generated_at: str,
    result: str = "pass",
    completed: bool | None = None,
    continue_working: bool | None = None,
    primary_goal_passed: bool | None = None,
) -> Path:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal_telemetry import build_task_goal_telemetry, write_task_goal_telemetry

    operating_root = path.parents[2]
    task_record_path = operating_root / f"{task_name}-task-record.json"
    task_record = {
        "task_id": f"{task_name}-001",
        "task_name": task_name,
        "operating_root": str(operating_root.resolve()),
    }
    task_record_path.write_text(json.dumps(task_record, indent=2), encoding="utf-8")

    if completed is None:
        completed = result == "pass"
    if continue_working is None:
        continue_working = result == "fail"
    if primary_goal_passed is None:
        primary_goal_passed = result == "pass"

    loop_result = {
        "command": "run-task-goal-loop",
        "result": result,
        "completed": completed,
        "continue_working": continue_working,
        "primary_goal_passed": primary_goal_passed,
        "operating_root": str(operating_root.resolve()),
        "command_results": [],
        "errors": [],
        "inputs": {"task_record_path": str(task_record_path.resolve())},
    }
    payload = build_task_goal_telemetry(
        loop_result=loop_result,
        task_record=task_record,
        task_record_path=task_record_path,
        generated_at=generated_at,
    )
    write_task_goal_telemetry(payload, output_path=path)
    return path


def _write_task_goal_summary(path: Path, *, project_root: Path, source_path: Path) -> Path:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal_telemetry_summary import write_task_goal_telemetry_summary

    payload = {
        "schema_version": "task-goal-telemetry-summary/v1",
        "generated_at": "2026-03-17T00:00:05Z",
        "producer": "ai-native-codex-package-template",
        "summary_scope": {
            "project_root": str(project_root.resolve()),
            "telemetry_artifact_count": 1,
        },
        "source_artifacts": [
            {
                "path": str(source_path.resolve()),
                "task_name": "task-a",
                "generated_at": "2026-03-17T00:00:01Z",
            }
        ],
        "aggregate_counts": {
            "total_attempts": 1,
            "completed_count": 1,
            "continue_working_count": 0,
            "failed_count": 0,
            "primary_goal_passed_count": 1,
        },
        "result_breakdown": {"pass": 1},
        "stage_breakdown": {
            "primary_goal_gate": 0,
            "broader_validation": 0,
            "none": 1,
        },
        "task_breakdown": [
            {
                "task_name": "task-a",
                "attempt_count": 1,
                "completed_count": 1,
                "continue_working_count": 0,
                "failed_count": 0,
                "primary_goal_passed_count": 1,
            }
        ],
        "correlation_summary": {
            "run_ids": [],
            "build_run_manifest_paths": [],
        },
        "summary_notes": ["Summarized one telemetry attempt."],
    }
    write_task_goal_telemetry_summary(payload, output_path=path)
    return path


def _write_build_run_manifest(path: Path, *, generated_at: str, run_id: str) -> Path:
    payload = {
        "schema_version": "build-run-manifest/v1",
        "generated_at": generated_at,
        "producer": "ai-native-codex-package-template",
        "run_id": run_id,
        "task_name": "task-a",
        "selected_profile": "python-cli-click",
        "commands": [],
        "validations": [],
        "artifacts": [],
        "notes": [],
        "timings": {
            "setup_time_seconds": None,
            "execution_time_seconds": None,
            "validation_time_seconds": None,
        },
        "metrics": {
            "clarification_count": None,
            "validation_failures": None,
            "files_created": None,
            "files_changed": None,
        },
        "outcome": {
            "status": "pass",
            "summary": "ok",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_discover_task_goal_telemetry_paths_fails_closed_for_relative_project_root() -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.agent_telemetry_reader import discover_task_goal_telemetry_paths

    try:
        discover_task_goal_telemetry_paths("relative-root")
    except ValueError as exc:
        assert "absolute path" in str(exc)
    else:
        raise AssertionError("expected relative project_root to fail closed")


def test_build_agent_telemetry_snapshot_returns_latest_local_artifacts(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.agent_telemetry_reader import build_agent_telemetry_snapshot

    project_root = tmp_path / "project-root"
    telemetry_dir = project_root / ".ai-native-codex-package-template" / "task-goal-telemetry"
    telemetry_dir.mkdir(parents=True)
    source_path = _write_task_goal_telemetry(
        telemetry_dir / "task-a.json",
        task_name="task-a",
        generated_at="2026-03-17T00:00:01Z",
    )
    _write_task_goal_telemetry(
        telemetry_dir / "task-b.json",
        task_name="task-b",
        generated_at="2026-03-17T00:00:02Z",
        result="fail",
        completed=False,
        continue_working=True,
        primary_goal_passed=False,
    )
    _write_task_goal_summary(
        telemetry_dir / "task-goal-telemetry-summary.json",
        project_root=project_root,
        source_path=source_path,
    )
    _write_build_run_manifest(
        project_root / ".ai-native-codex-package-template" / "run-manifests" / "run-001.json",
        generated_at="2026-03-17T00:00:03Z",
        run_id="run-001",
    )

    payload = build_agent_telemetry_snapshot(project_root=project_root.resolve())

    assert payload["reader"] == "agent-telemetry-reader"
    assert payload["latest_task_goal_telemetry"]["path"] == str((telemetry_dir / "task-b.json").resolve())
    assert payload["task_goal_telemetry_summary"]["present"] is True
    assert payload["latest_build_run_manifest"]["present"] is True
    assert payload["status_summary"]["latest_result"] == "fail"


def test_read_agent_telemetry_reports_missing_local_layers(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.agent_telemetry_reader import read_agent_telemetry

    project_root = tmp_path / "project-root"
    telemetry_dir = project_root / ".ai-native-codex-package-template" / "task-goal-telemetry"
    telemetry_dir.mkdir(parents=True)
    _write_task_goal_telemetry(
        telemetry_dir / "task-a.json",
        task_name="task-a",
        generated_at="2026-03-17T00:00:01Z",
    )

    payload = read_agent_telemetry(project_root=project_root.resolve())

    assert payload["task_goal_telemetry_summary"]["present"] is False
    assert payload["latest_build_run_manifest"]["present"] is False
    assert "No local task-goal telemetry summary is present yet." in payload["notes"]
    assert "No local build-run manifest is present yet." in payload["notes"]


def test_cli_read_agent_telemetry_emits_json(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    project_root = tmp_path / "project-root"
    telemetry_dir = project_root / ".ai-native-codex-package-template" / "task-goal-telemetry"
    telemetry_dir.mkdir(parents=True)
    _write_task_goal_telemetry(
        telemetry_dir / "task-a.json",
        task_name="task-a",
        generated_at="2026-03-17T00:00:01Z",
    )

    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "read-agent-telemetry",
            "--project-root",
            str(project_root.resolve()),
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["reader"] == "agent-telemetry-reader"
    assert payload["local_artifact_counts"]["task_goal_telemetry_count"] == 1
