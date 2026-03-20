from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def _task_record(operating_root: Path, *, task_name: str) -> dict[str, object]:
    return {
        "task_id": f"{task_name}-001",
        "task_name": task_name,
        "operating_root": str(operating_root.resolve()),
    }


def _loop_result(
    *,
    operating_root: Path,
    result: str,
    completed: bool,
    continue_working: bool,
    primary_goal_passed: bool,
    failing_stage: str | None,
) -> dict[str, object]:
    command_results: list[dict[str, object]] = [
        {
            "stage": "primary_goal_gate",
            "command": f"{sys.executable} -c \"print('goal')\"",
            "exit_code": 0,
            "passed": True,
        }
    ]
    if failing_stage is None:
        command_results.append(
            {
                "stage": "broader_validation",
                "command": f"{sys.executable} -c \"print('validate')\"",
                "exit_code": 0,
                "passed": True,
            }
        )
    else:
        command_results.append(
            {
                "stage": failing_stage,
                "command": f"{sys.executable} -c \"import sys; sys.exit(1)\"",
                "exit_code": 1,
                "passed": False,
            }
        )
    return {
        "command": "run-task-goal-loop",
        "operating_root": str(operating_root.resolve()),
        "inputs": {"task_record_path": "task-record.json"},
        "result": result,
        "completed": completed,
        "continue_working": continue_working,
        "primary_goal_passed": primary_goal_passed,
        "command_results": command_results,
        "errors": [],
    }


def _write_telemetry(
    path: Path,
    *,
    task_name: str,
    result: str,
    completed: bool,
    continue_working: bool,
    primary_goal_passed: bool,
    failing_stage: str | None,
    run_id: str | None = None,
) -> Path:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal_telemetry import build_task_goal_telemetry, write_task_goal_telemetry

    operating_root = path.parent / "project-root"
    operating_root.mkdir(parents=True, exist_ok=True)
    task_record_path = operating_root / f"{task_name}-task-record.json"
    task_record_path.write_text(json.dumps(_task_record(operating_root, task_name=task_name), indent=2), encoding="utf-8")
    payload = build_task_goal_telemetry(
        loop_result=_loop_result(
            operating_root=operating_root,
            result=result,
            completed=completed,
            continue_working=continue_working,
            primary_goal_passed=primary_goal_passed,
            failing_stage=failing_stage,
        ),
        task_record=_task_record(operating_root, task_name=task_name),
        task_record_path=task_record_path,
        run_id=run_id,
        generated_at=f"2026-03-16T00:00:0{1 if task_name.endswith('a') else 2 if task_name.endswith('b') else 3}Z",
    )
    write_task_goal_telemetry(payload, output_path=path)
    return path


def test_build_task_goal_telemetry_summary_aggregates_mixed_attempts(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal_telemetry_summary import build_task_goal_telemetry_summary

    telemetry_a = _write_telemetry(
        tmp_path / "telemetry-a.json",
        task_name="task-a",
        result="pass",
        completed=True,
        continue_working=False,
        primary_goal_passed=True,
        failing_stage=None,
        run_id="run-001",
    )
    telemetry_b = _write_telemetry(
        tmp_path / "telemetry-b.json",
        task_name="task-b",
        result="fail",
        completed=False,
        continue_working=True,
        primary_goal_passed=False,
        failing_stage="primary_goal_gate",
    )
    telemetry_c = _write_telemetry(
        tmp_path / "telemetry-c.json",
        task_name="task-b",
        result="fail",
        completed=False,
        continue_working=False,
        primary_goal_passed=True,
        failing_stage="broader_validation",
        run_id="run-003",
    )

    payload = build_task_goal_telemetry_summary(
        telemetry_paths=[telemetry_c, telemetry_a, telemetry_b],
        generated_at="2026-03-16T00:00:10Z",
    )

    assert payload["aggregate_counts"] == {
        "total_attempts": 3,
        "completed_count": 1,
        "continue_working_count": 1,
        "failed_count": 1,
        "primary_goal_passed_count": 2,
    }
    assert payload["stage_breakdown"] == {
        "primary_goal_gate": 1,
        "broader_validation": 1,
        "none": 1,
    }
    assert payload["result_breakdown"] == {
        "fail": 2,
        "pass": 1,
    }
    assert payload["correlation_summary"]["run_ids"] == ["run-001", "run-003"]
    assert payload["task_breakdown"][0]["task_name"] == "task-b"
    assert payload["task_breakdown"][0]["attempt_count"] == 2


def test_build_task_goal_telemetry_summary_rejects_malformed_telemetry(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.task_goal_telemetry_summary import build_task_goal_telemetry_summary

    malformed_path = tmp_path / "bad-telemetry.json"
    malformed_path.write_text(
        json.dumps(
            {
                "schema_version": "task-goal-telemetry/v1",
                "task_name": "bad-task",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        build_task_goal_telemetry_summary(telemetry_paths=[malformed_path])
    except ValueError as exc:
        assert "task-goal-telemetry.schema.json" in str(exc)
    else:
        raise AssertionError("expected malformed telemetry to fail closed")


def test_cli_summarize_task_goal_telemetry_writes_summary(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.cli import build_app

    telemetry_path = _write_telemetry(
        tmp_path / "telemetry.json",
        task_name="task-a",
        result="pass",
        completed=True,
        continue_working=False,
        primary_goal_passed=True,
        failing_stage=None,
        run_id="run-001",
    )
    runner = CliRunner()
    result = runner.invoke(
        build_app(),
        [
            "summarize-task-goal-telemetry",
            "--telemetry-path",
            str(telemetry_path),
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["aggregate_counts"]["total_attempts"] == 1
    summary_path = Path(payload["summary_path"])
    assert summary_path.is_file()
