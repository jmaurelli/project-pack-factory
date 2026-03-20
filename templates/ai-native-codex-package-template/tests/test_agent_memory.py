from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def _import_memory_module():
    sys.path.insert(0, str(_src()))
    from ai_native_package.agent_memory import (
        build_agent_memory,
        derive_agent_memory_path,
        load_agent_memory,
        persist_agent_memory,
        read_agent_memory,
        write_agent_memory,
    )

    return {
        "build_agent_memory": build_agent_memory,
        "derive_agent_memory_path": derive_agent_memory_path,
        "load_agent_memory": load_agent_memory,
        "persist_agent_memory": persist_agent_memory,
        "read_agent_memory": read_agent_memory,
        "write_agent_memory": write_agent_memory,
    }


def test_build_agent_memory_embeds_goal_environment_and_history_context(tmp_path: Path) -> None:
    module = _import_memory_module()
    build_agent_memory = module["build_agent_memory"]
    assert callable(build_agent_memory)

    payload = build_agent_memory(
        memory_id="memory-001",
        project_root=tmp_path,
        goal="Restart the agent from local memory.",
        summary="Capture the environment and goal state.",
        memory_type="decision",
        importance="high",
        status="active",
        task_name="task-a",
        task_record_path=tmp_path / "task-record.yaml",
        operating_root=tmp_path,
        project_context_reference=(str(tmp_path / "project-context.md"),),
        telemetry_path=(str(tmp_path / ".ai-native-codex-package-template" / "task-goal-telemetry" / "task-a.json"),),
        run_manifest_path=(str(tmp_path / ".ai-native-codex-package-template" / "run-manifests" / "run-001.json"),),
        detail=("Keep the memory local-only.",),
        next_action=("Inspect read-agent-memory output first.",),
        attempted_command=("uv run python -m ai_native_package read-agent-memory",),
        observed_outcome=("pass",),
        open_question=("Do we need a superseding memory?",),
        tag=("restart",),
        file_path=("src/ai_native_package/agent_memory.py",),
        evidence_path=(str(tmp_path / "evidence.json"),),
        supersedes_memory_id=("memory-000",),
        conflicts_with_memory_id=("memory-900",),
        generated_at="2026-03-17T00:00:01Z",
    )

    assert payload["goal_state"]["goal"] == "Restart the agent from local memory."
    assert payload["goal_state"]["goal_status"] == "in_progress"
    assert payload["goal_state"]["primary_validation_command"] == "uv run python -m ai_native_package read-agent-memory"
    assert payload["goal_state"]["blocked_by"] == []
    assert payload["environment_context"]["operating_root"] == str(tmp_path)
    assert payload["environment_context"]["task_record_path"] == str((tmp_path / "task-record.yaml").resolve())
    assert payload["environment_context"]["project_context_references"] == [str((tmp_path / "project-context.md").resolve())]
    assert payload["environment_context"]["task_goal_telemetry_path"].endswith("task-a.json")
    assert payload["environment_context"]["build_run_manifest_path"].endswith("run-001.json")
    assert payload["history_context"]["supersedes_memory_id"] == "memory-000"
    assert payload["history_context"]["conflicts_with"] == ["memory-900"]
    assert payload["history_context"]["attempted_commands"] == ["uv run python -m ai_native_package read-agent-memory"]
    assert payload["history_context"]["observed_outcomes"] == ["pass"]
    assert payload["history_context"]["open_questions"] == ["Do we need a superseding memory?"]
    assert str((tmp_path / "task-record.yaml").resolve()) in payload["goal_state"]["goal_artifact_paths"]
    assert str((tmp_path / "project-context.md").resolve()) in payload["goal_state"]["goal_artifact_paths"]
    assert str((tmp_path / "evidence.json").resolve()) in payload["goal_state"]["goal_artifact_paths"]


def test_write_agent_memory_rejects_duplicate_memory_id_and_persists_supersession(tmp_path: Path) -> None:
    module = _import_memory_module()
    build_agent_memory = module["build_agent_memory"]
    derive_agent_memory_path = module["derive_agent_memory_path"]
    persist_agent_memory = module["persist_agent_memory"]
    write_agent_memory = module["write_agent_memory"]
    load_agent_memory = module["load_agent_memory"]

    output_path = Path(derive_agent_memory_path(memory_id="memory-001", project_root=tmp_path))
    original = build_agent_memory(
        memory_id="memory-001",
        project_root=tmp_path,
        goal="Maintain restart continuity.",
        summary="Original memory state.",
        memory_type="decision",
        generated_at="2026-03-17T00:00:01Z",
    )
    write_agent_memory(original, output_path=output_path)

    with pytest.raises(FileExistsError):
        write_agent_memory(original, output_path=output_path)

    replacement = build_agent_memory(
        memory_id="memory-001",
        project_root=tmp_path,
        goal="Maintain restart continuity.",
        summary="Superseding memory state.",
        memory_type="decision",
        supersedes_memory_id=("memory-001",),
        generated_at="2026-03-17T00:00:02Z",
    )
    written_path, archived_path = persist_agent_memory(
        replacement,
        output_path=output_path,
        replace_existing=True,
    )

    assert Path(written_path).exists()
    assert archived_path is not None
    assert Path(archived_path).exists()
    assert load_agent_memory(written_path)["history_context"]["supersedes_memory_id"] == "memory-001"


def test_read_agent_memory_prioritizes_importance_and_surfaces_omitted_active_memories(tmp_path: Path) -> None:
    module = _import_memory_module()
    build_agent_memory = module["build_agent_memory"]
    derive_agent_memory_path = module["derive_agent_memory_path"]
    write_agent_memory = module["write_agent_memory"]
    read_agent_memory = module["read_agent_memory"]

    entries = [
        build_agent_memory(
            memory_id="low-blocker",
            project_root=tmp_path,
            goal="Keep the agent restartable.",
            summary="Low-priority blocker.",
            memory_type="blocker",
            importance="low",
            next_action=("Fix a tiny blocker.",),
            file_path=("src/ai_native_package/agent_memory.py",),
            generated_at="2026-03-17T00:00:01Z",
        ),
        build_agent_memory(
            memory_id="critical-decision",
            project_root=tmp_path,
            goal="Keep the agent restartable.",
            summary="Critical decision.",
            memory_type="decision",
            importance="critical",
            next_action=("Use the restart state first.",),
            file_path=("src/ai_native_package/contracts/agent-memory-reader.schema.json",),
            generated_at="2026-03-17T00:00:02Z",
        ),
        build_agent_memory(
            memory_id="normal-next-step",
            project_root=tmp_path,
            goal="Keep the agent restartable.",
            summary="Normal next step.",
            memory_type="next_step",
            importance="normal",
            next_action=("Inspect the omitted memory slice.",),
            file_path=("tests/test_agent_memory.py",),
            generated_at="2026-03-17T00:00:03Z",
        ),
    ]
    for payload in entries:
        write_agent_memory(payload, output_path=Path(derive_agent_memory_path(memory_id=payload["memory_id"], project_root=tmp_path)))

    snapshot = read_agent_memory(tmp_path, limit=1)

    assert snapshot["local_artifact_counts"]["memory_count"] == 3
    assert snapshot["local_artifact_counts"]["active_count"] == 3
    assert snapshot["local_artifact_counts"]["resolved_count"] == 0
    assert snapshot["local_artifact_counts"]["archived_count"] == 0
    assert snapshot["prioritized_memories"][0]["memory_id"] == "critical-decision"
    assert [memory["memory_id"] for memory in snapshot["omitted_active_memories"]] == ["normal-next-step", "low-blocker"]
    assert any(action["action"] == "Inspect the omitted memory slice." for action in snapshot["handoff_summary"]["next_actions"])
    assert snapshot["retrieval_focus"]["importance_before_type"] is True


def test_read_agent_memory_surfaces_restart_environment_from_all_active_entries(tmp_path: Path) -> None:
    module = _import_memory_module()
    build_agent_memory = module["build_agent_memory"]
    derive_agent_memory_path = module["derive_agent_memory_path"]
    write_agent_memory = module["write_agent_memory"]
    read_agent_memory = module["read_agent_memory"]

    selected = build_agent_memory(
        memory_id="selected-memory",
        project_root=tmp_path,
        goal="Resume the current task.",
        summary="Selected active memory.",
        memory_type="decision",
        importance="high",
        task_name="task-a",
        task_record_path=tmp_path / "task-record-a.yaml",
        operating_root=tmp_path / "task-a",
        project_context_reference=(str(tmp_path / "project-context-a.md"),),
        telemetry_path=(str(tmp_path / ".ai-native-codex-package-template" / "task-goal-telemetry" / "task-a.json"),),
        run_manifest_path=(str(tmp_path / ".ai-native-codex-package-template" / "run-manifests" / "run-a.json"),),
        next_action=("Read the omitted memory.",),
        generated_at="2026-03-17T00:00:01Z",
    )
    omitted = build_agent_memory(
        memory_id="omitted-memory",
        project_root=tmp_path,
        goal="Resume the current task.",
        summary="Omitted active memory with unique environment refs.",
        memory_type="next_step",
        importance="normal",
        task_name="task-b",
        task_record_path=tmp_path / "task-record-b.yaml",
        operating_root=tmp_path / "task-b",
        project_context_reference=(str(tmp_path / "project-context-b.md"),),
        telemetry_path=(str(tmp_path / ".ai-native-codex-package-template" / "task-goal-telemetry" / "task-b.json"),),
        run_manifest_path=(str(tmp_path / ".ai-native-codex-package-template" / "run-manifests" / "run-b.json"),),
        next_action=("Use the second environment anchor.",),
        generated_at="2026-03-17T00:00:02Z",
    )

    write_agent_memory(selected, output_path=Path(derive_agent_memory_path(memory_id="selected-memory", project_root=tmp_path)))
    write_agent_memory(omitted, output_path=Path(derive_agent_memory_path(memory_id="omitted-memory", project_root=tmp_path)))

    snapshot = read_agent_memory(tmp_path, limit=1)

    environment_context = snapshot["restart_state"]["environment_context"]
    assert snapshot["local_artifact_counts"]["memory_count"] == 2
    assert snapshot["local_artifact_counts"]["active_count"] == 2
    assert environment_context["task_record_paths"] == [
        str((tmp_path / "task-record-a.yaml").resolve()),
        str((tmp_path / "task-record-b.yaml").resolve()),
    ]
    assert snapshot["restart_state"]["goal_statuses"] == ["in_progress"]
    assert str((tmp_path / "project-context-b.md").resolve()) in environment_context["project_context_references"]
    assert str((tmp_path / ".ai-native-codex-package-template" / "task-goal-telemetry" / "task-b.json").resolve()) in environment_context["task_goal_telemetry_paths"]
    assert str((tmp_path / ".ai-native-codex-package-template" / "run-manifests" / "run-b.json").resolve()) in environment_context["build_run_manifest_paths"]
    assert snapshot["restart_state"]["goal_artifact_paths"]
    assert snapshot["restart_state"]["history_context"]["attempted_commands"] == []
    assert any("agent restart state" in note for note in snapshot["notes"])


def test_load_agent_memory_rejects_malformed_timestamp(tmp_path: Path) -> None:
    module = _import_memory_module()
    build_agent_memory = module["build_agent_memory"]
    load_agent_memory = module["load_agent_memory"]

    payload = build_agent_memory(
        memory_id="bad-timestamp",
        project_root=tmp_path,
        goal="Validate read-time timestamp parsing.",
        summary="Invalid timestamp should fail closed.",
        memory_type="decision",
        generated_at="2026-03-17T00:00:01Z",
    )
    payload["generated_at"] = "2026-02-30T00:00:00Z"
    path = tmp_path / "bad-timestamp.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_agent_memory(path)
