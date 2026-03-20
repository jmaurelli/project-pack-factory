from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from shutil import copy2
from typing import Any, Final, cast

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled deterministically at runtime
    validator_for = cast(Any, None)

from .__about__ import DISTRIBUTION_NAME

SCHEMA_VERSION: Final[str] = "agent-memory/v1"
READER_SCHEMA_VERSION: Final[str] = "agent-memory-reader/v1"
READER_NAME: Final[str] = "agent-memory-reader"
_DEFAULT_MEMORY_DIR: Final[str] = ".ai-native-codex-package-template/agent-memory"
_MEMORY_NOTE_FILENAME_SUFFIX: Final[str] = ".json"
_REVISIONS_DIR: Final[str] = "revisions"

_STATUS_PRIORITY: Final[dict[str, int]] = {
    "active": 0,
    "resolved": 1,
    "archived": 2,
}
_TYPE_PRIORITY: Final[dict[str, int]] = {
    "blocker": 0,
    "next_step": 1,
    "decision": 2,
    "validation": 3,
    "lesson": 4,
    "context": 5,
}
_IMPORTANCE_PRIORITY: Final[dict[str, int]] = {
    "critical": 0,
    "high": 1,
    "normal": 2,
    "low": 3,
}
_GOAL_STATUS_VALUES: Final[tuple[str, ...]] = (
    "in_progress",
    "blocked",
    "completed",
    "superseded",
)


def _utc_now_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _memory_schema_path() -> Path:
    return _package_root() / "contracts" / "agent-memory.schema.json"


def _reader_schema_path() -> Path:
    return _package_root() / "contracts" / "agent-memory-reader.schema.json"


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_schema_path(path_segments: Any) -> str:
    parts = [str(segment) for segment in path_segments]
    return ".".join(parts) if parts else "$"


def _validate_with_schema(*, instance: Any, schema: dict[str, Any], label: str) -> list[str]:
    if validator_for is None:
        return ["The `jsonschema` dependency is required to validate machine-readable contracts."]

    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    return [
        f"{label}:{_format_schema_path(error.path)}: {error.message}"
        for error in sorted(
            validator.iter_errors(instance),
            key=lambda error: (_format_schema_path(error.path), error.message),
        )
    ]


def _normalize_required_string(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _normalize_identifier(value: str, *, field_name: str) -> str:
    normalized = _normalize_required_string(value, field_name=field_name)
    if Path(normalized).name != normalized:
        raise ValueError(f"{field_name} must not contain path separators")
    return normalized


def _normalize_optional_identifier(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _normalize_identifier(value, field_name=field_name)


def _normalize_string_list(values: list[str] | tuple[str, ...]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = value.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def _resolve_project_root(project_root: str | Path) -> Path:
    candidate = Path(project_root)
    if not candidate.is_absolute():
        raise ValueError("project_root must be an absolute path")
    return candidate.resolve()


def _normalize_optional_absolute_path(value: str | Path | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        raise ValueError(f"{field_name} must be an absolute path")
    return str(candidate.resolve())


def _normalize_absolute_path_list(values: list[str] | tuple[str, ...], *, field_name: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        candidate = _normalize_optional_absolute_path(value, field_name=field_name)
        assert candidate is not None
        if candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def _memory_dir(project_root: Path) -> Path:
    return (project_root / _DEFAULT_MEMORY_DIR).resolve()


def _revision_dir(project_root: Path) -> Path:
    return _memory_dir(project_root) / _REVISIONS_DIR


def _normalize_timestamp(value: str | None) -> str:
    if value is None:
        return _utc_now_timestamp()
    normalized = _normalize_required_string(value, field_name="generated_at")
    if not normalized.endswith("Z"):
        raise ValueError("generated_at must be a UTC timestamp ending in Z")
    parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    if parsed.tzinfo != UTC:
        raise ValueError("generated_at must be a UTC timestamp")
    return normalized


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _default_goal_status(*, memory_type: str, status: str) -> str:
    if status == "resolved":
        return "completed"
    if status == "archived":
        return "superseded"
    if memory_type == "blocker":
        return "blocked"
    return "in_progress"


def _normalize_goal_status(value: str | None, *, memory_type: str, status: str) -> str:
    candidate = value.strip() if value is not None else _default_goal_status(memory_type=memory_type, status=status)
    if candidate not in _GOAL_STATUS_VALUES:
        raise ValueError("goal_status must be one of in_progress, blocked, completed, or superseded")
    return candidate


def _validate_loaded_memory_payload(payload: dict[str, Any]) -> None:
    _normalize_timestamp(cast(str, payload["generated_at"]))
    _normalize_optional_identifier(cast(str | None, payload.get("task_name")), field_name="task_name")

    goal_state = cast(dict[str, Any], payload["goal_state"])
    goal = goal_state.get("goal")
    if goal is not None:
        _normalize_required_string(cast(str, goal), field_name="goal_state.goal")
    goal_status = goal_state.get("goal_status")
    if goal_status is not None and cast(str, goal_status) not in _GOAL_STATUS_VALUES:
        raise ValueError("goal_state.goal_status must be one of in_progress, blocked, completed, or superseded")
    _normalize_string_list(cast(list[str], goal_state.get("completion_signals", [])))
    for field_name in ("primary_validation_command", "recommended_next_command"):
        value = goal_state.get(field_name)
        if value is not None:
            _normalize_required_string(cast(str, value), field_name=f"goal_state.{field_name}")
    _normalize_string_list(cast(list[str], goal_state.get("blocked_by", [])))
    _normalize_string_list(cast(list[str], goal_state.get("goal_artifact_paths", [])))

    environment_context = cast(dict[str, Any], payload["environment_context"])
    _normalize_optional_absolute_path(cast(str | None, environment_context.get("operating_root")), field_name="environment_context.operating_root")
    _normalize_optional_absolute_path(cast(str | None, environment_context.get("task_record_path")), field_name="environment_context.task_record_path")
    _normalize_optional_absolute_path(cast(str | None, environment_context.get("delegation_brief_path")), field_name="environment_context.delegation_brief_path")
    _normalize_optional_absolute_path(cast(str | None, environment_context.get("build_run_manifest_path")), field_name="environment_context.build_run_manifest_path")
    _normalize_optional_absolute_path(cast(str | None, environment_context.get("task_goal_telemetry_path")), field_name="environment_context.task_goal_telemetry_path")
    _normalize_absolute_path_list(cast(list[str], environment_context.get("project_context_references", [])), field_name="environment_context.project_context_references")
    _normalize_string_list(cast(list[str], environment_context.get("relevant_commands", [])))
    _normalize_string_list(cast(list[str], environment_context.get("recommended_read_order", [])))

    history_context = cast(dict[str, Any], payload["history_context"])
    _normalize_optional_identifier(cast(str | None, history_context.get("supersedes_memory_id")), field_name="history_context.supersedes_memory_id")
    _normalize_string_list(cast(list[str], history_context.get("conflicts_with", [])))
    _normalize_string_list(cast(list[str], history_context.get("attempted_commands", [])))
    _normalize_string_list(cast(list[str], history_context.get("observed_outcomes", [])))
    _normalize_string_list(cast(list[str], history_context.get("open_questions", [])))
    confidence = cast(str, history_context["confidence"])
    if confidence not in {"low", "medium", "high"}:
        raise ValueError("history_context.confidence must be one of low, medium, or high")


def derive_agent_memory_path(*, memory_id: str, project_root: str | Path) -> str:
    normalized_root = _resolve_project_root(project_root)
    normalized_memory_id = _normalize_identifier(memory_id, field_name="memory_id")
    return str(_memory_dir(normalized_root) / f"{normalized_memory_id}{_MEMORY_NOTE_FILENAME_SUFFIX}")


def build_agent_memory(
    *,
    memory_id: str,
    project_root: str | Path,
    goal: str,
    summary: str,
    memory_type: str,
    importance: str = "normal",
    status: str = "active",
    goal_status: str | None = None,
    task_name: str | None = None,
    task_record_path: str | Path | None = None,
    operating_root: str | Path | None = None,
    delegation_brief_path: str | Path | None = None,
    project_context_reference: list[str] | tuple[str, ...] = (),
    telemetry_path: list[str] | tuple[str, ...] = (),
    run_manifest_path: list[str] | tuple[str, ...] = (),
    completion_signal: list[str] | tuple[str, ...] = (),
    primary_validation_command: str | None = None,
    recommended_next_command: str | None = None,
    blocked_by: list[str] | tuple[str, ...] = (),
    detail: list[str] | tuple[str, ...] = (),
    next_action: list[str] | tuple[str, ...] = (),
    attempted_command: list[str] | tuple[str, ...] = (),
    observed_outcome: list[str] | tuple[str, ...] = (),
    open_question: list[str] | tuple[str, ...] = (),
    tag: list[str] | tuple[str, ...] = (),
    file_path: list[str] | tuple[str, ...] = (),
    evidence_path: list[str] | tuple[str, ...] = (),
    supersedes_memory_id: list[str] | tuple[str, ...] = (),
    conflicts_with_memory_id: list[str] | tuple[str, ...] = (),
    history_confidence: str | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    normalized_root = _resolve_project_root(project_root)
    normalized_memory_type = _normalize_required_string(memory_type, field_name="memory_type")
    normalized_status = _normalize_required_string(status, field_name="status")
    normalized_goal = _normalize_required_string(goal, field_name="goal")
    normalized_goal_status = _normalize_goal_status(goal_status, memory_type=normalized_memory_type, status=normalized_status)
    normalized_task_record_path = _normalize_optional_absolute_path(task_record_path, field_name="task_record_path")
    normalized_operating_root = _normalize_optional_absolute_path(operating_root, field_name="operating_root")
    normalized_delegation_brief_path = _normalize_optional_absolute_path(
        delegation_brief_path,
        field_name="delegation_brief_path",
    )
    normalized_project_context_references = _normalize_absolute_path_list(
        list(project_context_reference),
        field_name="project_context_references",
    )
    normalized_telemetry_paths = _normalize_absolute_path_list(list(telemetry_path), field_name="telemetry_paths")
    normalized_run_manifest_paths = _normalize_absolute_path_list(list(run_manifest_path), field_name="run_manifest_paths")
    normalized_completion_signals = _normalize_string_list(completion_signal)
    normalized_blocked_by = _normalize_string_list(blocked_by)
    normalized_details = _normalize_string_list(detail)
    normalized_next_actions = _normalize_string_list(next_action)
    normalized_attempted_commands = _normalize_string_list(attempted_command)
    _normalized_observed_outcomes = _normalize_string_list(observed_outcome)
    normalized_open_questions = _normalize_string_list(open_question)
    normalized_tags = _normalize_string_list(tag)
    normalized_file_paths = _normalize_string_list(file_path)
    normalized_evidence_paths = _normalize_string_list(evidence_path)
    normalized_supersedes_memory_ids = [
        _normalize_identifier(value, field_name="supersedes_memory_id")
        for value in _normalize_string_list(supersedes_memory_id)
    ]
    normalized_conflicts_with_memory_ids = [
        _normalize_identifier(value, field_name="conflicts_with_memory_id")
        for value in _normalize_string_list(conflicts_with_memory_id)
    ]

    primary_validation_command = (
        _normalize_required_string(primary_validation_command, field_name="primary_validation_command")
        if primary_validation_command is not None
        else (
            normalized_attempted_commands[0]
            if normalized_attempted_commands
            else (normalized_next_actions[0] if normalized_next_actions else None)
        )
    )
    recommended_next_command = (
        _normalize_required_string(recommended_next_command, field_name="recommended_next_command")
        if recommended_next_command is not None
        else (normalized_next_actions[0] if normalized_next_actions else primary_validation_command)
    )

    goal_artifact_candidates: list[str] = []
    if normalized_task_record_path is not None:
        goal_artifact_candidates.append(normalized_task_record_path)
    if normalized_delegation_brief_path is not None:
        goal_artifact_candidates.append(normalized_delegation_brief_path)
    goal_artifact_candidates.extend(normalized_project_context_references)
    goal_artifact_candidates.extend(normalized_telemetry_paths)
    goal_artifact_candidates.extend(normalized_run_manifest_paths)
    goal_artifact_candidates.extend(normalized_file_paths)
    goal_artifact_candidates.extend(normalized_evidence_paths)
    goal_artifact_paths = _normalize_string_list(goal_artifact_candidates)
    goal_completion_signals = _normalize_string_list(normalized_completion_signals)

    goal_state = {
        "goal": normalized_goal,
        "goal_status": normalized_goal_status,
        "completion_signals": goal_completion_signals,
        "primary_validation_command": primary_validation_command,
        "recommended_next_command": recommended_next_command,
        "blocked_by": _normalize_string_list(normalized_blocked_by),
        "goal_artifact_paths": goal_artifact_paths,
    }

    environment_context = {
        "operating_root": normalized_operating_root or str(normalized_root),
        "task_record_path": normalized_task_record_path,
        "delegation_brief_path": normalized_delegation_brief_path,
        "build_run_manifest_path": normalized_run_manifest_paths[0] if normalized_run_manifest_paths else None,
        "task_goal_telemetry_path": normalized_telemetry_paths[0] if normalized_telemetry_paths else None,
        "project_context_references": normalized_project_context_references,
        "relevant_commands": _normalize_string_list(
            [
                *(normalized_attempted_commands[:3]),
                *(cmd for cmd in (primary_validation_command, recommended_next_command) if cmd is not None),
                "read-agent-memory",
            ]
        ),
        "recommended_read_order": [
            "goal_state",
            "environment_context",
            "history_context",
            "details",
            "next_actions",
        ],
    }

    normalized_history_confidence = _normalize_required_string(
        history_confidence
        if history_confidence is not None
        else ("high" if normalized_supersedes_memory_ids or normalized_task_record_path is not None else "medium"),
        field_name="history_confidence",
    )
    if normalized_history_confidence not in {"low", "medium", "high"}:
        raise ValueError("history_confidence must be one of low, medium, or high")

    history_context = {
        "supersedes_memory_id": normalized_supersedes_memory_ids[0] if normalized_supersedes_memory_ids else None,
        "conflicts_with": normalized_conflicts_with_memory_ids,
        "attempted_commands": normalized_attempted_commands,
        "observed_outcomes": _normalized_observed_outcomes,
        "open_questions": normalized_open_questions,
        "confidence": normalized_history_confidence,
    }

    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _normalize_timestamp(generated_at),
        "producer": DISTRIBUTION_NAME,
        "project_root": str(normalized_root),
        "memory_id": _normalize_identifier(memory_id, field_name="memory_id"),
        "task_name": _normalize_optional_identifier(task_name, field_name="task_name"),
        "memory_type": normalized_memory_type,
        "importance": _normalize_required_string(importance, field_name="importance"),
        "status": normalized_status,
        "summary": _normalize_required_string(summary, field_name="summary"),
        "details": normalized_details,
        "next_actions": normalized_next_actions,
        "tags": normalized_tags,
        "file_paths": normalized_file_paths,
        "evidence_paths": normalized_evidence_paths,
        "goal_state": goal_state,
        "environment_context": environment_context,
        "history_context": history_context,
    }
    schema = cast(dict[str, Any], _load_json_file(_memory_schema_path()))
    validation_errors = _validate_with_schema(
        instance=payload,
        schema=schema,
        label="agent-memory.schema.json",
    )
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    return payload


def _archive_existing_memory(*, target: Path, project_root: Path) -> str | None:
    if not target.exists():
        return None
    revision_dir = _revision_dir(project_root)
    revision_dir.mkdir(parents=True, exist_ok=True)
    revision_name = f"{target.stem}--{_utc_now_timestamp().replace(':', '-')}{_MEMORY_NOTE_FILENAME_SUFFIX}"
    revision_path = revision_dir / revision_name
    copy2(target, revision_path)
    return str(revision_path)


def write_agent_memory(
    payload: dict[str, object],
    *,
    output_path: str | Path,
    replace_existing: bool = False,
) -> str:
    target = Path(output_path)
    schema = cast(dict[str, Any], _load_json_file(_memory_schema_path()))
    validation_errors = _validate_with_schema(
        instance=payload,
        schema=schema,
        label="agent-memory.schema.json",
    )
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    _validate_loaded_memory_payload(cast(dict[str, Any], payload))
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not replace_existing:
        raise FileExistsError(
            f"Agent memory already exists at {target}. Use a new memory_id or pass replace_existing=True to archive the previous artifact first."
        )
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return str(target)


def persist_agent_memory(
    payload: dict[str, object],
    *,
    output_path: str | Path,
    replace_existing: bool = False,
) -> tuple[str, str | None]:
    target = Path(output_path)
    project_root = _resolve_project_root(cast(str, payload["project_root"]))
    archived_path = None
    if replace_existing and target.exists():
        archived_path = _archive_existing_memory(target=target, project_root=project_root)
    written_path = write_agent_memory(payload, output_path=target, replace_existing=replace_existing)
    return written_path, archived_path


def load_agent_memory(path: str | Path) -> dict[str, Any]:
    payload = _load_json_file(Path(path).expanduser().resolve())
    if not isinstance(payload, dict):
        raise ValueError("agent memory artifact must contain a JSON object")
    schema = cast(dict[str, Any], _load_json_file(_memory_schema_path()))
    validation_errors = _validate_with_schema(
        instance=payload,
        schema=schema,
        label="agent-memory.schema.json",
    )
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    normalized_payload = cast(dict[str, Any], payload)
    _validate_loaded_memory_payload(normalized_payload)
    return normalized_payload


def _discover_agent_memory_entries(
    *,
    project_root: Path,
    task_name: str | None,
) -> list[tuple[Path, dict[str, Any]]]:
    directory = _memory_dir(project_root)
    if not directory.exists():
        return []
    entries: list[tuple[Path, dict[str, Any]]] = []
    for candidate in sorted(directory.glob(f"*{_MEMORY_NOTE_FILENAME_SUFFIX}")):
        payload = load_agent_memory(candidate)
        if task_name is not None and payload.get("task_name") != task_name:
            continue
        entries.append((candidate.resolve(), payload))
    return entries


def discover_agent_memory_paths(project_root: str | Path, task_name: str | None = None) -> list[str]:
    normalized_root = _resolve_project_root(project_root)
    normalized_task_name = _normalize_optional_identifier(task_name, field_name="task_name")
    return [
        str(path)
        for path, _payload in _discover_agent_memory_entries(
            project_root=normalized_root,
            task_name=normalized_task_name,
        )
    ]


def _entry_sort_key(item: tuple[Path, dict[str, Any]]) -> tuple[int, int, int, float, str]:
    path, payload = item
    generated_at = _parse_timestamp(_normalize_required_string(cast(str, payload["generated_at"]), field_name="generated_at"))
    return (
        _STATUS_PRIORITY[_normalize_required_string(cast(str, payload["status"]), field_name="status")],
        _IMPORTANCE_PRIORITY[_normalize_required_string(cast(str, payload["importance"]), field_name="importance")],
        _TYPE_PRIORITY[_normalize_required_string(cast(str, payload["memory_type"]), field_name="memory_type")],
        -generated_at.timestamp(),
        str(path),
    )


def _prioritized_entries(entries: list[tuple[Path, dict[str, Any]]]) -> list[tuple[Path, dict[str, Any]]]:
    return sorted(entries, key=_entry_sort_key)


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _memory_card(path: Path, payload: dict[str, Any]) -> dict[str, object]:
    return {
        "memory_id": payload["memory_id"],
        "task_name": payload["task_name"],
        "memory_type": payload["memory_type"],
        "importance": payload["importance"],
        "status": payload["status"],
        "summary": payload["summary"],
        "details": payload["details"],
        "next_actions": payload["next_actions"],
        "tags": payload["tags"],
        "file_paths": payload["file_paths"],
        "evidence_paths": payload["evidence_paths"],
        "goal_state": payload["goal_state"],
        "environment_context": payload["environment_context"],
        "history_context": payload["history_context"],
        "generated_at": payload["generated_at"],
        "source_path": str(path),
    }


def _summary_cards(entries: list[tuple[Path, dict[str, Any]]], *, memory_type: str, limit: int) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for _path, payload in entries:
        if payload["memory_type"] != memory_type:
            continue
        cards.append(_memory_card(_path, payload))
        if len(cards) >= limit:
            break
    return cards


def _action_items(entries: list[tuple[Path, dict[str, Any]]], *, limit: int) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    for _path, payload in entries:
        if payload["status"] != "active":
            continue
        for action in cast(list[str], payload["next_actions"]):
            actions.append(
                {
                    "action": action,
                    "memory_id": payload["memory_id"],
                    "task_name": payload["task_name"],
                    "source_path": str(_path.resolve()),
                    "file_paths": payload["file_paths"],
                    "evidence_paths": payload["evidence_paths"],
                }
            )
        if len(actions) >= limit:
            break
    return actions[:limit]


def _file_focus(entries: list[tuple[Path, dict[str, Any]]], *, limit: int) -> list[str]:
    paths: list[str] = []
    for _path, payload in entries:
        if payload["status"] != "active":
            continue
        paths.extend(cast(list[str], payload["file_paths"]))
    return _dedupe_strings(paths)[:limit]


def _status_summary(entries: list[tuple[Path, dict[str, Any]]]) -> dict[str, int]:
    status_counts = {
        "active_count": 0,
        "resolved_count": 0,
        "archived_count": 0,
    }
    for _path, payload in entries:
        status = cast(str, payload["status"])
        key = f"{status}_count"
        status_counts[key] += 1
    return status_counts


def _omitted_active_count(entries: list[tuple[Path, dict[str, Any]]]) -> int:
    return sum(1 for _path, payload in entries if payload["status"] == "active")


def _omitted_active_memories(entries: list[tuple[Path, dict[str, Any]]], *, limit: int) -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for path, payload in entries:
        if payload["status"] != "active":
            continue
        cards.append(_memory_card(path, payload))
        if len(cards) >= limit:
            break
    return cards


def _restart_context(entries: list[tuple[Path, dict[str, Any]]]) -> dict[str, object]:
    active_entries = [entry for entry in entries if entry[1]["status"] == "active"]
    goals = _dedupe_strings([cast(str, entry[1]["goal_state"]["goal"]) for entry in active_entries])[:10]
    completion_signals: list[str] = []
    goal_statuses: list[str] = []
    primary_validation_commands: list[str] = []
    recommended_next_commands: list[str] = []
    blocked_by: list[str] = []
    goal_artifact_paths: list[str] = []
    task_record_paths: list[str] = []
    operating_roots: list[str] = []
    project_context_references: list[str] = []
    delegation_brief_paths: list[str] = []
    build_run_manifest_paths: list[str] = []
    task_goal_telemetry_paths: list[str] = []
    relevant_commands: list[str] = []
    recommended_read_order: list[str] = []
    history_warnings: list[str] = []
    attempted_commands: list[str] = []
    observed_outcomes: list[str] = []
    open_questions: list[str] = []

    for _path, payload in entries:
        goal_state = cast(dict[str, Any], payload["goal_state"])
        environment_context = cast(dict[str, Any], payload["environment_context"])
        history_context = cast(dict[str, Any], payload["history_context"])
        completion_signals.extend(cast(list[str], goal_state.get("completion_signals", [])))
        goal_status = goal_state.get("goal_status")
        if isinstance(goal_status, str) and goal_status.strip():
            goal_statuses.append(goal_status.strip())
        primary_validation_command = goal_state.get("primary_validation_command")
        if isinstance(primary_validation_command, str) and primary_validation_command.strip():
            primary_validation_commands.append(primary_validation_command.strip())
        recommended_next_command = goal_state.get("recommended_next_command")
        if isinstance(recommended_next_command, str) and recommended_next_command.strip():
            recommended_next_commands.append(recommended_next_command.strip())
        blocked_by.extend(cast(list[str], goal_state.get("blocked_by", [])))
        goal_artifact_paths.extend(cast(list[str], goal_state.get("goal_artifact_paths", [])))

        task_record_path = cast(str | None, environment_context.get("task_record_path"))
        if task_record_path is not None:
            task_record_paths.append(task_record_path)
        operating_root = cast(str | None, environment_context.get("operating_root"))
        if operating_root is not None:
            operating_roots.append(operating_root)
        project_context_references.extend(cast(list[str], environment_context.get("project_context_references", [])))
        delegation_brief_path = cast(str | None, environment_context.get("delegation_brief_path"))
        if delegation_brief_path is not None:
            delegation_brief_paths.append(delegation_brief_path)
        build_run_manifest_path = cast(str | None, environment_context.get("build_run_manifest_path"))
        if build_run_manifest_path is not None:
            build_run_manifest_paths.append(build_run_manifest_path)
        task_goal_telemetry_path = cast(str | None, environment_context.get("task_goal_telemetry_path"))
        if task_goal_telemetry_path is not None:
            task_goal_telemetry_paths.append(task_goal_telemetry_path)
        relevant_commands.extend(cast(list[str], environment_context.get("relevant_commands", [])))
        recommended_read_order.extend(cast(list[str], environment_context.get("recommended_read_order", [])))

        supersedes_memory_id = cast(str | None, history_context.get("supersedes_memory_id"))
        if supersedes_memory_id is not None:
            history_warnings.append(f"Memory `{payload['memory_id']}` supersedes `{supersedes_memory_id}`.")
        conflicts_with = cast(list[str], history_context.get("conflicts_with", []))
        if conflicts_with:
            history_warnings.append(
                f"Memory `{payload['memory_id']}` conflicts with {', '.join(conflicts_with)}."
            )
        attempted_commands.extend(cast(list[str], history_context.get("attempted_commands", [])))
        observed_outcomes.extend(cast(list[str], history_context.get("observed_outcomes", [])))
        open_questions.extend(cast(list[str], history_context.get("open_questions", [])))

    return {
        "goals": _dedupe_strings(goals),
        "goal_statuses": _dedupe_strings(goal_statuses)[:10],
        "completion_signals": _dedupe_strings(completion_signals)[:10],
        "primary_validation_commands": _dedupe_strings(primary_validation_commands)[:10],
        "recommended_next_commands": _dedupe_strings(recommended_next_commands)[:10],
        "blocked_by": _dedupe_strings(blocked_by)[:10],
        "goal_artifact_paths": _dedupe_strings(goal_artifact_paths)[:10],
        "environment_context": {
            "operating_roots": _dedupe_strings(operating_roots)[:10],
            "task_record_paths": _dedupe_strings(task_record_paths)[:10],
            "delegation_brief_paths": _dedupe_strings(delegation_brief_paths)[:10],
            "project_context_references": _dedupe_strings(project_context_references)[:10],
            "build_run_manifest_paths": _dedupe_strings(build_run_manifest_paths)[:10],
            "task_goal_telemetry_paths": _dedupe_strings(task_goal_telemetry_paths)[:10],
            "relevant_commands": _dedupe_strings(relevant_commands)[:10],
            "recommended_read_order": _dedupe_strings(recommended_read_order)[:10],
        },
        "history_context": {
            "attempted_commands": _dedupe_strings(attempted_commands)[:10],
            "observed_outcomes": _dedupe_strings(observed_outcomes)[:10],
            "open_questions": _dedupe_strings(open_questions)[:10],
        },
        "history_warnings": _dedupe_strings(history_warnings)[:10],
    }


def _handoff_lines(
    *,
    blockers: list[str],
    next_steps: list[str],
    next_actions: list[str],
    decisions: list[str],
    file_focus: list[str],
) -> list[str]:
    lines: list[str] = []
    for blocker in blockers:
        lines.append(f"Blocker: {blocker}")
    for next_step in next_steps:
        lines.append(f"Next-step: {next_step}")
    for action in next_actions:
        lines.append(f"Next: {action}")
    for decision in decisions:
        lines.append(f"Decision: {decision}")
    if file_focus:
        lines.append(f"Focus files: {', '.join(file_focus)}")
    return lines


def _notes(*, total_count: int, task_name: str | None, omitted_count: int, omitted_active_count: int) -> list[str]:
    notes: list[str] = []
    if task_name is not None:
        notes.append(f"Filtered agent memory to task `{task_name}`.")
    if total_count == 0:
        notes.append("No agent memory artifacts are present yet for this project root.")
    else:
        notes.append("The snapshot prioritizes active blockers, next steps, and decisions before older context.")
        if omitted_count > 0:
            notes.append("The selected memory slice is truncated. Inspect the omitted active memories before assuming the full history is represented.")
        if omitted_active_count > 0:
            notes.append("Omitted active memories were summarized separately so the next agent can recover missing live context.")
        notes.append("Use this memory snapshot as agent restart state for environment, history, and goals; it does not replace canonical task records or validation artifacts.")
    return notes


def read_agent_memory(
    project_root: str | Path,
    *,
    task_name: str | None = None,
    limit: int = 7,
) -> dict[str, Any]:
    if limit < 1:
        raise ValueError("limit must be at least 1")

    normalized_root = _resolve_project_root(project_root)
    normalized_task_name = _normalize_optional_identifier(task_name, field_name="task_name")
    entries = _prioritized_entries(
        _discover_agent_memory_entries(
            project_root=normalized_root,
            task_name=normalized_task_name,
        )
    )
    prioritized = entries[:limit]
    omitted = entries[limit:]
    active_prioritized = [entry for entry in prioritized if cast(str, entry[1]["status"]) == "active"]
    active_all = [entry for entry in entries if cast(str, entry[1]["status"]) == "active"]
    blockers = _summary_cards(active_prioritized, memory_type="blocker", limit=3)
    next_steps = _summary_cards(active_prioritized, memory_type="next_step", limit=3)
    decisions = _summary_cards(active_prioritized, memory_type="decision", limit=3)
    validation_learnings = _summary_cards(entries, memory_type="validation", limit=3)
    validation_learnings.extend(
        card
        for card in _summary_cards(entries, memory_type="lesson", limit=3)
        if card["memory_id"] not in {existing["memory_id"] for existing in validation_learnings}
    )
    validation_learnings = validation_learnings[:3]
    next_actions = _action_items(active_all, limit=5)
    file_focus = _file_focus(active_all, limit=5)
    omitted_active = _omitted_active_memories(omitted, limit=5)
    restart_state = _restart_context(entries)
    blocker_summaries = [cast(str, card["summary"]) for card in blockers]
    next_step_summaries = [cast(str, card["summary"]) for card in next_steps]
    next_action_strings = [cast(str, action["action"]) for action in next_actions]
    decision_summaries = [cast(str, card["summary"]) for card in decisions]
    snapshot: dict[str, Any] = {
        "schema_version": READER_SCHEMA_VERSION,
        "reader": READER_NAME,
        "project_root": str(normalized_root),
        "task_name_filter": normalized_task_name,
        "retrieval_focus": {
            "active_status_first": True,
            "importance_before_type": True,
            "priority_memory_types": ["blocker", "next_step", "decision", "validation", "lesson", "context"],
            "selected_limit": limit,
        },
        "local_artifact_counts": {
            "memory_count": len(entries),
            **_status_summary(entries),
        },
        "restart_state": restart_state,
        "prioritized_memories": [_memory_card(path, payload) for path, payload in prioritized],
        "omitted_active_memories": omitted_active,
            "handoff_summary": {
                "active_blockers": blockers,
                "active_next_steps": next_steps,
                "next_actions": next_actions,
                "active_decisions": decisions,
                "validation_learnings": validation_learnings,
                "file_focus": file_focus,
                "compact_handoff": _handoff_lines(
                    blockers=blocker_summaries,
                    next_steps=next_step_summaries,
                    next_actions=next_action_strings,
                    decisions=decision_summaries,
                    file_focus=file_focus,
                ),
            },
        "notes": _notes(
            total_count=len(entries),
            task_name=normalized_task_name,
            omitted_count=len(omitted),
            omitted_active_count=_omitted_active_count(omitted),
        ),
    }
    schema = cast(dict[str, Any], _load_json_file(_reader_schema_path()))
    validation_errors = _validate_with_schema(
        instance=snapshot,
        schema=schema,
        label="agent-memory-reader.schema.json",
    )
    if validation_errors:
        raise ValueError("; ".join(validation_errors))
    return snapshot


def build_agent_memory_snapshot(
    project_root: str | Path,
    *,
    task_name: str | None = None,
    limit: int = 7,
) -> dict[str, Any]:
    return read_agent_memory(project_root=project_root, task_name=task_name, limit=limit)
