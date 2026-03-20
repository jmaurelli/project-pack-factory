from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Final

from .agent_memory import (
    build_agent_memory,
    derive_agent_memory_path,
    read_agent_memory,
    write_agent_memory,
)

BENCHMARK_SCHEMA_VERSION: Final[str] = "agent-memory-benchmark/v1"
BENCHMARK_TASK_ID: Final[str] = "task-agent-memory-restart-small-001"
BENCHMARK_CATEGORY: Final[str] = "restart-state-retrieval"
BENCHMARK_SIZE_CLASS: Final[str] = "small"
_BENCHMARK_LIMIT: Final[int] = 2
_BENCHMARK_GOAL: Final[str] = "Restore agent restart context for the active package task."
_BENCHMARK_TASK_NAME: Final[str] = "agent-memory-restart-benchmark"


def _utc_now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(path.resolve())


def _touch(path: Path, content: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path.resolve())


def _fixture_paths(project_root: Path) -> dict[str, str]:
    return {
        "delegation_brief": _touch(
            project_root / "delegation-brief.md",
            "# Delegation brief\nUse the restart-state snapshot before editing code.\n",
        ),
        "task_record_primary": _touch(
            project_root / "task-records" / "restart-core.yaml",
            "title: Restart Core\n",
        ),
        "task_record_blocker": _touch(
            project_root / "task-records" / "restart-blocker.yaml",
            "title: Restart Blocker\n",
        ),
        "task_record_next_step": _touch(
            project_root / "task-records" / "restart-next-step.yaml",
            "title: Restart Next Step\n",
        ),
        "task_record_validation": _touch(
            project_root / "task-records" / "restart-validation.yaml",
            "title: Restart Validation\n",
        ),
        "project_context_primary": _touch(
            project_root / "project-context" / "active-project-context.md",
            "# Active project context\n",
        ),
        "project_context_omitted": _touch(
            project_root / "project-context" / "omitted-project-context.md",
            "# Omitted project context\n",
        ),
        "project_context_validation": _touch(
            project_root / "project-context" / "validation-project-context.md",
            "# Validation project context\n",
        ),
        "run_manifest_primary": _touch(
            project_root / ".pack-state" / "run-manifests" / "run-primary.json",
            "{}\n",
        ),
        "run_manifest_omitted": _touch(
            project_root / ".pack-state" / "run-manifests" / "run-omitted.json",
            "{}\n",
        ),
        "run_manifest_validation": _touch(
            project_root / ".pack-state" / "run-manifests" / "run-validation.json",
            "{}\n",
        ),
        "telemetry_primary": _touch(
            project_root / ".pack-state" / "task-goal-telemetry" / "restart-primary.json",
            "{}\n",
        ),
        "telemetry_omitted": _touch(
            project_root / ".pack-state" / "task-goal-telemetry" / "restart-omitted.json",
            "{}\n",
        ),
        "telemetry_validation": _touch(
            project_root / ".pack-state" / "task-goal-telemetry" / "restart-validation.json",
            "{}\n",
        ),
        "evidence_decision": _touch(
            project_root / "evidence" / "decision.txt",
            "Decision evidence.\n",
        ),
        "evidence_blocker": _touch(
            project_root / "evidence" / "blocker.txt",
            "Blocker evidence.\n",
        ),
        "evidence_validation": _touch(
            project_root / "evidence" / "validation.txt",
            "Validation evidence.\n",
        ),
        "operating_root_primary": str((project_root / "workspace" / "core").resolve()),
        "operating_root_blocker": str((project_root / "workspace" / "blocked").resolve()),
        "operating_root_next_step": str((project_root / "workspace" / "follow-up").resolve()),
        "operating_root_validation": str((project_root / "workspace" / "validated").resolve()),
    }


def _build_fixture(project_root: Path) -> dict[str, Any]:
    paths = _fixture_paths(project_root)
    reader_command = "uv run python -m agent_memory_first read-agent-memory --project-root . --output json"
    validation_command = "uv run python -m agent_memory_first validate-project-pack --project-root . --output json"
    benchmark_command = "uv run python -m agent_memory_first benchmark-agent-memory --output json"

    memories = [
        build_agent_memory(
            memory_id="critical-decision",
            project_root=project_root,
            task_name=_BENCHMARK_TASK_NAME,
            goal=_BENCHMARK_GOAL,
            summary="Use the active task record and local telemetry before editing code.",
            memory_type="decision",
            importance="critical",
            task_record_path=paths["task_record_primary"],
            operating_root=paths["operating_root_primary"],
            delegation_brief_path=paths["delegation_brief"],
            project_context_reference=(paths["project_context_primary"],),
            telemetry_path=(paths["telemetry_primary"],),
            run_manifest_path=(paths["run_manifest_primary"],),
            completion_signal=("critical decision captured",),
            primary_validation_command=reader_command,
            recommended_next_command=reader_command,
            detail=("The current task record is already scoped for the restart path.",),
            next_action=("Read the active task record before editing code.",),
            attempted_command=(reader_command,),
            observed_outcome=("reader output already included restart state",),
            open_question=("Should the next agent widen the selected memory limit?",),
            tag=("restart", "decision"),
            file_path=("src/agent_memory_first/agent_memory.py",),
            evidence_path=(paths["evidence_decision"],),
            generated_at="2026-03-17T00:00:01Z",
        ),
        build_agent_memory(
            memory_id="high-blocker",
            project_root=project_root,
            task_name=_BENCHMARK_TASK_NAME,
            goal=_BENCHMARK_GOAL,
            summary="The blocked branch must stay visible so the next agent does not repeat setup work.",
            memory_type="blocker",
            importance="high",
            task_record_path=paths["task_record_blocker"],
            operating_root=paths["operating_root_blocker"],
            delegation_brief_path=paths["delegation_brief"],
            project_context_reference=(paths["project_context_primary"],),
            blocked_by=("benchmark fixture verification is not recorded yet",),
            primary_validation_command=validation_command,
            recommended_next_command=validation_command,
            next_action=("Inspect the blocked fixture branch before continuing.",),
            attempted_command=(validation_command,),
            observed_outcome=("blocked on missing benchmark fixture verification",),
            tag=("restart", "blocker"),
            file_path=("src/agent_memory_first/cli.py",),
            evidence_path=(paths["evidence_blocker"],),
            generated_at="2026-03-17T00:00:02Z",
        ),
        build_agent_memory(
            memory_id="normal-next-step",
            project_root=project_root,
            task_name=_BENCHMARK_TASK_NAME,
            goal=_BENCHMARK_GOAL,
            summary="After the active slice is read, inspect the omitted active memory for environment drift.",
            memory_type="next_step",
            importance="normal",
            task_record_path=paths["task_record_next_step"],
            operating_root=paths["operating_root_next_step"],
            delegation_brief_path=paths["delegation_brief"],
            project_context_reference=(paths["project_context_omitted"],),
            telemetry_path=(paths["telemetry_omitted"],),
            run_manifest_path=(paths["run_manifest_omitted"],),
            next_action=("Inspect the omitted active memory slice.",),
            open_question=("Should the next agent re-run the benchmark after changing retrieval order?",),
            tag=("restart", "next-step"),
            file_path=("tests/test_agent_memory.py",),
            generated_at="2026-03-17T00:00:03Z",
        ),
        build_agent_memory(
            memory_id="resolved-validation",
            project_root=project_root,
            task_name=_BENCHMARK_TASK_NAME,
            goal=_BENCHMARK_GOAL,
            summary="The deterministic restart benchmark already passed once for this fixture.",
            memory_type="validation",
            importance="normal",
            status="resolved",
            task_record_path=paths["task_record_validation"],
            operating_root=paths["operating_root_validation"],
            project_context_reference=(paths["project_context_validation"],),
            telemetry_path=(paths["telemetry_validation"],),
            run_manifest_path=(paths["run_manifest_validation"],),
            completion_signal=("restart benchmark baseline passed",),
            primary_validation_command=benchmark_command,
            recommended_next_command=benchmark_command,
            attempted_command=(benchmark_command,),
            observed_outcome=("baseline restart benchmark passed",),
            tag=("restart", "validation"),
            file_path=("tests/test_agent_memory_benchmark.py",),
            evidence_path=(paths["evidence_validation"],),
            supersedes_memory_id=("prior-validation",),
            conflicts_with_memory_id=("previous-restart-note",),
            generated_at="2026-03-17T00:00:04Z",
        ),
    ]

    for payload in memories:
        write_agent_memory(
            payload,
            output_path=derive_agent_memory_path(
                memory_id=str(payload["memory_id"]),
                project_root=project_root,
            ),
        )

    return {
        "paths": paths,
        "reader_command": reader_command,
        "validation_command": validation_command,
        "benchmark_command": benchmark_command,
    }


def _build_check(
    *,
    check_id: str,
    passed: bool,
    expected: Any,
    observed: Any,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "passed": passed,
        "expected": expected,
        "observed": observed,
    }


def _score_snapshot(snapshot: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    prioritized = snapshot["prioritized_memories"]
    omitted = snapshot["omitted_active_memories"]
    restart_state = snapshot["restart_state"]
    environment_context = restart_state["environment_context"]
    history_context = restart_state["history_context"]
    handoff_summary = snapshot["handoff_summary"]
    fixture_paths = fixture["paths"]

    prioritized_ids = [card["memory_id"] for card in prioritized]
    prioritized_statuses = [card["status"] for card in prioritized]
    omitted_ids = [card["memory_id"] for card in omitted]
    next_actions = [item["action"] for item in handoff_summary["next_actions"]]

    checks = [
        _build_check(
            check_id="critical_memory_selected_first",
            passed=prioritized_ids[:1] == ["critical-decision"],
            expected=["critical-decision"],
            observed=prioritized_ids[:1],
        ),
        _build_check(
            check_id="prioritized_memories_stay_active",
            passed=prioritized_statuses == ["active", "active"],
            expected=["active", "active"],
            observed=prioritized_statuses,
        ),
        _build_check(
            check_id="omitted_active_memory_remains_visible",
            passed=omitted_ids == ["normal-next-step"],
            expected=["normal-next-step"],
            observed=omitted_ids,
        ),
        _build_check(
            check_id="goal_state_is_preserved",
            passed=restart_state["goals"] == [_BENCHMARK_GOAL],
            expected=[_BENCHMARK_GOAL],
            observed=restart_state["goals"],
        ),
        _build_check(
            check_id="goal_statuses_cover_active_and_resolved_progress",
            passed=restart_state["goal_statuses"] == ["in_progress", "blocked", "completed"],
            expected=["in_progress", "blocked", "completed"],
            observed=restart_state["goal_statuses"],
        ),
        _build_check(
            check_id="environment_context_aggregates_all_task_records",
            passed=environment_context["task_record_paths"] == [
                fixture_paths["task_record_primary"],
                fixture_paths["task_record_blocker"],
                fixture_paths["task_record_next_step"],
                fixture_paths["task_record_validation"],
            ],
            expected=[
                fixture_paths["task_record_primary"],
                fixture_paths["task_record_blocker"],
                fixture_paths["task_record_next_step"],
                fixture_paths["task_record_validation"],
            ],
            observed=environment_context["task_record_paths"],
        ),
        _build_check(
            check_id="history_context_aggregates_attempts_outcomes_and_questions",
            passed=history_context["attempted_commands"] == [
                fixture["reader_command"],
                fixture["validation_command"],
                fixture["benchmark_command"],
            ]
            and history_context["observed_outcomes"] == [
                "reader output already included restart state",
                "blocked on missing benchmark fixture verification",
                "baseline restart benchmark passed",
            ]
            and history_context["open_questions"] == [
                "Should the next agent widen the selected memory limit?",
                "Should the next agent re-run the benchmark after changing retrieval order?",
            ],
            expected={
                "attempted_commands": [
                    fixture["reader_command"],
                    fixture["validation_command"],
                    fixture["benchmark_command"],
                ],
                "observed_outcomes": [
                    "reader output already included restart state",
                    "blocked on missing benchmark fixture verification",
                    "baseline restart benchmark passed",
                ],
                "open_questions": [
                    "Should the next agent widen the selected memory limit?",
                    "Should the next agent re-run the benchmark after changing retrieval order?",
                ],
            },
            observed={
                "attempted_commands": history_context["attempted_commands"],
                "observed_outcomes": history_context["observed_outcomes"],
                "open_questions": history_context["open_questions"],
            },
        ),
        _build_check(
            check_id="next_actions_include_omitted_active_context",
            passed=next_actions == [
                "Read the active task record before editing code.",
                "Inspect the blocked fixture branch before continuing.",
                "Inspect the omitted active memory slice.",
            ],
            expected=[
                "Read the active task record before editing code.",
                "Inspect the blocked fixture branch before continuing.",
                "Inspect the omitted active memory slice.",
            ],
            observed=next_actions,
        ),
        _build_check(
            check_id="history_warnings_capture_supersession_and_conflict",
            passed=restart_state["history_warnings"] == [
                "Memory `resolved-validation` supersedes `prior-validation`.",
                "Memory `resolved-validation` conflicts with previous-restart-note.",
            ],
            expected=[
                "Memory `resolved-validation` supersedes `prior-validation`.",
                "Memory `resolved-validation` conflicts with previous-restart-note.",
            ],
            observed=restart_state["history_warnings"],
        ),
        _build_check(
            check_id="environment_commands_keep_reader_visible",
            passed="read-agent-memory" in environment_context["relevant_commands"],
            expected="read-agent-memory",
            observed=environment_context["relevant_commands"],
        ),
    ]

    passed_check_count = sum(1 for check in checks if check["passed"])
    total_check_count = len(checks)
    prioritized_file_focus = handoff_summary["file_focus"]

    return {
        "checks": checks,
        "passed_check_count": passed_check_count,
        "total_check_count": total_check_count,
        "all_checks_passed": passed_check_count == total_check_count,
        "composite_score": passed_check_count / total_check_count,
        "prioritized_memory_ids": prioritized_ids,
        "prioritized_statuses": prioritized_statuses,
        "omitted_active_memory_ids": omitted_ids,
        "goal_statuses": restart_state["goal_statuses"],
        "task_record_paths": environment_context["task_record_paths"],
        "project_context_references": environment_context["project_context_references"],
        "attempted_commands": history_context["attempted_commands"],
        "observed_outcomes": history_context["observed_outcomes"],
        "open_questions": history_context["open_questions"],
        "next_actions": next_actions,
        "next_action_count": len(next_actions),
        "file_focus": prioritized_file_focus,
        "history_warning_count": len(restart_state["history_warnings"]),
    }


def run_agent_memory_benchmark(
    *,
    fixture_root: str | Path | None = None,
    output_path: str | Path | None = None,
    snapshot_output_path: str | Path | None = None,
) -> dict[str, Any]:
    generated_at = _utc_now_timestamp()

    def _run(project_root: Path) -> dict[str, Any]:
        fixture = _build_fixture(project_root)
        snapshot = read_agent_memory(project_root=project_root, task_name=_BENCHMARK_TASK_NAME, limit=_BENCHMARK_LIMIT)
        scored = _score_snapshot(snapshot, fixture)
        payload: dict[str, Any] = {
            "schema_version": BENCHMARK_SCHEMA_VERSION,
            "benchmark_task_id": BENCHMARK_TASK_ID,
            "benchmark_category": BENCHMARK_CATEGORY,
            "benchmark_size_class": BENCHMARK_SIZE_CLASS,
            "generated_at": generated_at,
            "fixture_project_root": str(project_root.resolve()),
            "task_name_filter": _BENCHMARK_TASK_NAME,
            "selected_limit": _BENCHMARK_LIMIT,
            **scored,
            "snapshot": snapshot,
            "output_paths": {
                "scorecard_path": None,
                "snapshot_path": None,
            },
        }
        if snapshot_output_path is not None:
            payload["output_paths"]["snapshot_path"] = _write_json(Path(snapshot_output_path), snapshot)
        if output_path is not None:
            payload["output_paths"]["scorecard_path"] = str(Path(output_path).resolve())
            _write_json(Path(output_path), payload)
        return payload

    if fixture_root is not None:
        project_root = Path(fixture_root).expanduser().resolve()
        project_root.mkdir(parents=True, exist_ok=True)
        return _run(project_root)

    with TemporaryDirectory(prefix="agent-memory-benchmark-") as tmp_dir:
        return _run(Path(tmp_dir))
