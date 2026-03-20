from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def _write_task_record(path: Path, *, validation_commands: list[str]) -> Path:
    primary_goal_command = validation_commands[0] if validation_commands else f"{sys.executable} -c \"print('missing')\""
    payload = {
        "task_id": "goal-loop-001",
        "task_name": "goal-loop-smoke",
        "operating_root": str(path.parent.resolve()),
        "project_context_reference": [str((_root() / "project-context.md").resolve())],
        "objective": "Make the goal-loop validation pass.",
        "source_spec_reference": [str((_root() / "README.md").resolve())],
        "required_changes": ["Add a small deterministic goal-loop feature."],
        "acceptance_criteria": ["The first validation command passes."],
        "out_of_scope": ["Broad package redesign."],
        "local_evidence": [str((_root() / "AGENTS.md").resolve())],
        "task_boundary_rules": ["Stay inside files_in_scope."],
        "required_return_format": ["Return machine-readable status."],
        "declared_order": 0,
        "files_in_scope": [str((_root() / "src" / "ai_native_package" / "cli.py").resolve())],
        "validation_commands": validation_commands,
        "goal_validation": {
            "primary_goal_command": primary_goal_command,
            "safety_check_commands": validation_commands[1:],
            "completion_rule": "all_declared_commands_must_pass",
        },
        "approval_requirement": "approval_not_required",
        "approval_state": "approval_not_required",
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_validate_task_goal_passes_for_valid_task_record(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal import validate_task_goal

    task_record = _write_task_record(
        tmp_path / "task-record.json",
        validation_commands=[f"{sys.executable} -c \"print('ok')\"", "make validate"],
    )

    payload = validate_task_goal(task_record_path=task_record)

    assert payload["result"] == "pass"
    assert payload["primary_goal_command"].startswith(sys.executable)


def test_validate_task_goal_fails_when_validation_commands_are_empty(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal import validate_task_goal

    task_record = _write_task_record(tmp_path / "task-record.json", validation_commands=[])

    payload = validate_task_goal(task_record_path=task_record)

    assert payload["result"] == "fail"
    assert any(error.get("path") == "validation_commands" or error.get("field") == "validation_commands" for error in payload["errors"])


def test_validate_task_goal_fails_when_goal_validation_is_inconsistent(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal import validate_task_goal

    task_record = _write_task_record(
        tmp_path / "task-record.json",
        validation_commands=[f"{sys.executable} -c \"print('ok')\"", "make validate"],
    )
    payload = json.loads(task_record.read_text(encoding="utf-8"))
    payload["goal_validation"]["safety_check_commands"] = []
    task_record.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    result = validate_task_goal(task_record_path=task_record)

    assert result["result"] == "fail"
    assert any(error.get("field") == "goal_validation" for error in result["errors"])


def test_run_task_goal_loop_reports_continue_working_on_primary_goal_failure(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal import run_task_goal_loop

    task_record = _write_task_record(
        tmp_path / "task-record.json",
        validation_commands=[f"{sys.executable} -c \"import sys; sys.exit(1)\"", "make validate"],
    )

    payload = run_task_goal_loop(task_record_path=task_record)

    assert payload["result"] == "fail"
    assert payload["continue_working"] is True
    assert payload["primary_goal_passed"] is False


def test_cli_run_task_goal_loop_emits_json_for_success(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    task_record = _write_task_record(
        tmp_path / "task-record.json",
        validation_commands=[
            f"{sys.executable} -c \"print('goal passed')\"",
            f"{sys.executable} -c \"print('validate passed')\"",
        ],
    )
    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        ["run-task-goal-loop", "--task-record", str(task_record), "--output", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["completed"] is True
    assert payload["primary_goal_passed"] is True


def test_run_task_goal_loop_writes_telemetry_superset_with_run_correlation(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal import run_task_goal_loop

    operating_root = tmp_path / "project-root"
    operating_root.mkdir()
    task_record = _write_task_record(
        operating_root / "task-record.json",
        validation_commands=[
            f"{sys.executable} -c \"print('goal passed')\"",
            f"{sys.executable} -c \"print('validate passed')\"",
        ],
    )
    manifest_path = operating_root / ".ai-native-codex-package-template" / "run-manifests" / "run-123.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "build-run-manifest/v1",
                "run_id": "run-123",
                "task_name": "goal-loop-smoke",
                "selected_profile": "python-cli",
                "outcome": {"status": "pass", "summary": "ok"},
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    payload = run_task_goal_loop(
        task_record_path=task_record,
        build_run_manifest_path=manifest_path,
    )

    telemetry = payload["telemetry"]
    assert telemetry["written"] is True
    telemetry_path = Path(telemetry["output_path"])
    persisted = json.loads(telemetry_path.read_text(encoding="utf-8"))
    for key in (
        "command",
        "result",
        "continue_working",
        "primary_goal_passed",
        "completed",
        "operating_root",
        "command_results",
        "errors",
        "inputs",
    ):
        assert persisted[key] == payload[key]
    assert persisted["task_id"] == "goal-loop-001"
    assert persisted["task_name"] == "goal-loop-smoke"
    assert persisted["run_correlation"]["build_run_manifest_run_id"] == "run-123"
    assert telemetry_path == operating_root / ".ai-native-codex-package-template" / "task-goal-telemetry" / "goal-loop-smoke.json"


def test_cli_run_task_goal_loop_fails_closed_for_ambiguous_telemetry_root(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    task_record = _write_task_record(
        tmp_path / "task-record.json",
        validation_commands=[f"{sys.executable} -c \"print('goal passed')\""],
    )
    payload = json.loads(task_record.read_text(encoding="utf-8"))
    payload["operating_root"] = "relative-root"
    task_record.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "run-task-goal-loop",
            "--task-record",
            str(task_record),
            "--telemetry-output-path",
            "relative-output/task-goal-telemetry.json",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 1
    response = json.loads(result.output)
    assert response["result"] == "fail"
    assert response["telemetry"]["written"] is False
    assert "absolute operating_root" in response["telemetry"]["error"]


def test_run_task_goal_loop_truncates_output_tails(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal import run_task_goal_loop

    task_record = _write_task_record(
        tmp_path / "task-record.json",
        validation_commands=[
            f"{sys.executable} -c \"import sys; [print(f'line-{{i}}') for i in range(30)]; [print(f'err-{{i}}', file=sys.stderr) for i in range(30)]\""
        ],
    )

    payload = run_task_goal_loop(task_record_path=task_record)

    command_result = payload["command_results"][0]
    assert "line-29" in command_result["stdout_tail"]
    assert "line-0" not in command_result["stdout_tail"]
    assert "err-29" in command_result["stderr_tail"]
    assert "err-0" not in command_result["stderr_tail"]


def test_build_task_goal_telemetry_summary_writes_local_only_summary(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal import run_task_goal_loop
    from ai_native_package.task_goal_telemetry_summary import (
        build_task_goal_telemetry_summary,
        derive_task_goal_telemetry_summary_path,
        write_task_goal_telemetry_summary,
    )

    operating_root = tmp_path / "project-root"
    operating_root.mkdir()

    task_record_pass = _write_task_record(
        operating_root / "task-record-pass.json",
        validation_commands=[f"{sys.executable} -c \"print('goal passed')\""],
    )
    payload_pass = json.loads(task_record_pass.read_text(encoding="utf-8"))
    payload_pass["task_name"] = "task-pass"
    task_record_pass.write_text(json.dumps(payload_pass, indent=2), encoding="utf-8")
    result_pass = run_task_goal_loop(
        task_record_path=task_record_pass,
        telemetry_output_path=Path("telemetry-pass.json"),
    )

    task_record_fail = _write_task_record(
        operating_root / "task-record-fail.json",
        validation_commands=[f"{sys.executable} -c \"import sys; sys.exit(1)\""],
    )
    payload_fail = json.loads(task_record_fail.read_text(encoding="utf-8"))
    payload_fail["task_name"] = "task-fail"
    task_record_fail.write_text(json.dumps(payload_fail, indent=2), encoding="utf-8")
    result_fail = run_task_goal_loop(
        task_record_path=task_record_fail,
        telemetry_output_path=Path("telemetry-fail.json"),
    )

    telemetry_paths = [
        Path(result_pass["telemetry"]["output_path"]),
        Path(result_fail["telemetry"]["output_path"]),
    ]
    summary_payload = build_task_goal_telemetry_summary(telemetry_paths=telemetry_paths)
    summary_path = write_task_goal_telemetry_summary(
        summary_payload,
        output_path=derive_task_goal_telemetry_summary_path(project_root=operating_root),
    )
    persisted = json.loads(Path(summary_path).read_text(encoding="utf-8"))

    assert persisted["schema_version"] == "task-goal-telemetry-summary/v1"
    assert persisted["aggregate_counts"]["total_attempts"] == 2
    assert persisted["aggregate_counts"]["completed_count"] == 1
    assert persisted["aggregate_counts"]["continue_working_count"] == 1
    assert persisted["stage_breakdown"]["primary_goal_gate"] == 1
    assert persisted["summary_scope"]["project_root"] == str(operating_root.resolve())
