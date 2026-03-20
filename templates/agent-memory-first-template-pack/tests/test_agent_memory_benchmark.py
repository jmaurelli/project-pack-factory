from __future__ import annotations

import json
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def _import_benchmark_module():
    sys.path.insert(0, str(_src()))
    from agent_memory_first.agent_memory_benchmark import run_agent_memory_benchmark

    return {"run_agent_memory_benchmark": run_agent_memory_benchmark}


def test_run_agent_memory_benchmark_scores_restart_state_retrieval(tmp_path: Path) -> None:
    module = _import_benchmark_module()
    run_agent_memory_benchmark = module["run_agent_memory_benchmark"]

    payload = run_agent_memory_benchmark(fixture_root=tmp_path)

    assert payload["benchmark_task_id"] == "task-agent-memory-restart-small-001"
    assert payload["benchmark_category"] == "restart-state-retrieval"
    assert payload["all_checks_passed"] is True
    assert payload["composite_score"] == 1.0
    assert payload["passed_check_count"] == payload["total_check_count"]
    assert payload["prioritized_memory_ids"] == ["critical-decision", "high-blocker"]
    assert payload["omitted_active_memory_ids"] == ["normal-next-step"]
    assert payload["goal_statuses"] == ["in_progress", "blocked", "completed"]
    assert payload["next_action_count"] == 3

    snapshot = payload["snapshot"]
    assert snapshot["local_artifact_counts"]["memory_count"] == 4
    assert snapshot["local_artifact_counts"]["active_count"] == 3
    assert snapshot["local_artifact_counts"]["resolved_count"] == 1
    assert snapshot["handoff_summary"]["file_focus"] == [
        "src/agent_memory_first/agent_memory.py",
        "src/agent_memory_first/cli.py",
        "tests/test_agent_memory.py",
    ]


def test_run_agent_memory_benchmark_writes_scorecard_and_snapshot_outputs(tmp_path: Path) -> None:
    module = _import_benchmark_module()
    run_agent_memory_benchmark = module["run_agent_memory_benchmark"]

    scorecard_path = tmp_path / "artifacts" / "agent-memory-scorecard.json"
    snapshot_path = tmp_path / "artifacts" / "agent-memory-snapshot.json"
    payload = run_agent_memory_benchmark(
        fixture_root=tmp_path / "fixture",
        output_path=scorecard_path,
        snapshot_output_path=snapshot_path,
    )

    assert payload["output_paths"]["scorecard_path"] == str(scorecard_path.resolve())
    assert payload["output_paths"]["snapshot_path"] == str(snapshot_path.resolve())

    persisted_scorecard = json.loads(scorecard_path.read_text(encoding="utf-8"))
    persisted_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert persisted_scorecard["all_checks_passed"] is True
    assert persisted_snapshot["schema_version"] == "agent-memory-reader/v1"
