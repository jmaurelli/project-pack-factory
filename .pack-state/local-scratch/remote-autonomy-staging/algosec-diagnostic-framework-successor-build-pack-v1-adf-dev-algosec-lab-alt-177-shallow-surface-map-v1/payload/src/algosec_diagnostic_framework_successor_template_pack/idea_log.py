from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IDEA_LOG_PATH = Path("notes") / "idea-log.json"
IDEA_LOG_SCHEMA_VERSION = "adf-successor-idea-log/v1"
ACTIVE_STATUSES = {"active", "archived"}
REVIEW_STATES = {"unreviewed", "in_review", "reviewed", "converted_to_task"}
NOTE_KINDS = {
    "behavioral_note",
    "product_idea",
    "operator_theory",
    "workflow_note",
    "cookbook_note",
}
EVIDENCE_STATES = {
    "open_question",
    "operator_theory",
    "observed_practice",
    "validated_behavior",
}
SOURCE_KINDS = {
    "operator_chat",
    "agent_inference",
    "runtime_observation",
    "imported_evidence",
    "doc_review",
}


def record_idea_note(
    *,
    project_root: Path,
    title: str,
    summary: str,
    details: list[str] | None = None,
    tags: list[str] | None = None,
    related_paths: list[str] | None = None,
    related_task_ids: list[str] | None = None,
    related_topics: list[str] | None = None,
    captured_by: str = "operator",
    source_kind: str = "operator_chat",
    note_kind: str = "behavioral_note",
    evidence_state: str = "operator_theory",
    review_state: str = "unreviewed",
    status: str = "active",
) -> dict[str, Any]:
    payload = _load_or_initialize_idea_log(project_root)
    now = _isoformat_z()
    note_id = _build_note_id(title=title, captured_at=now)
    note = {
        "note_id": note_id,
        "captured_at": now,
        "updated_at": now,
        "captured_by": captured_by,
        "source_kind": _validate_choice(source_kind, SOURCE_KINDS, "source_kind"),
        "status": _validate_choice(status, ACTIVE_STATUSES, "status"),
        "review_state": _validate_choice(review_state, REVIEW_STATES, "review_state"),
        "note_kind": _validate_choice(note_kind, NOTE_KINDS, "note_kind"),
        "evidence_state": _validate_choice(evidence_state, EVIDENCE_STATES, "evidence_state"),
        "title": _require_non_empty(title, "title"),
        "summary": _require_non_empty(summary, "summary"),
        "details": _normalize_string_list(details),
        "tags": _normalize_string_list(tags),
        "related_paths": _normalize_string_list(related_paths),
        "related_task_ids": _normalize_string_list(related_task_ids),
        "related_topics": _normalize_string_list(related_topics),
    }
    notes = payload.setdefault("notes", [])
    if not isinstance(notes, list):
        raise ValueError("idea log notes must be a list")
    notes.append(note)
    payload["generated_at"] = now
    payload["summary"] = _build_summary(notes)
    _write_idea_log(project_root, payload)
    return {
        "status": "pass",
        "idea_log_path": str(IDEA_LOG_PATH),
        "recorded_note": note,
        "summary": payload["summary"],
    }


def list_idea_notes(
    *,
    project_root: Path,
    status: str | None = None,
    review_state: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    payload = _load_or_initialize_idea_log(project_root)
    notes = payload.get("notes", [])
    if not isinstance(notes, list):
        raise ValueError("idea log notes must be a list")
    if status is not None:
        status = _validate_choice(status, ACTIVE_STATUSES, "status")
    if review_state is not None:
        review_state = _validate_choice(review_state, REVIEW_STATES, "review_state")
    filtered: list[dict[str, Any]] = []
    for note in notes:
        if not isinstance(note, dict):
            continue
        if status is not None and note.get("status") != status:
            continue
        if review_state is not None and note.get("review_state") != review_state:
            continue
        filtered.append(note)
    filtered.sort(key=lambda note: str(note.get("captured_at", "")), reverse=True)
    if limit > 0:
        filtered = filtered[:limit]
    return {
        "status": "pass",
        "idea_log_path": str(IDEA_LOG_PATH),
        "summary": payload.get("summary", {}),
        "notes": filtered,
    }


def update_idea_note(
    *,
    project_root: Path,
    note_id: str,
    title: str | None = None,
    summary: str | None = None,
    review_state: str | None = None,
    status: str | None = None,
    evidence_state: str | None = None,
    note_kind: str | None = None,
    add_details: list[str] | None = None,
    add_tags: list[str] | None = None,
    add_related_paths: list[str] | None = None,
    add_related_task_ids: list[str] | None = None,
    add_related_topics: list[str] | None = None,
) -> dict[str, Any]:
    payload = _load_or_initialize_idea_log(project_root)
    notes = payload.get("notes", [])
    if not isinstance(notes, list):
        raise ValueError("idea log notes must be a list")
    target = _find_note(notes, note_id=note_id)
    now = _isoformat_z()
    if title is not None:
        target["title"] = _require_non_empty(title, "title")
    if summary is not None:
        target["summary"] = _require_non_empty(summary, "summary")
    if review_state is not None:
        target["review_state"] = _validate_choice(review_state, REVIEW_STATES, "review_state")
    if status is not None:
        target["status"] = _validate_choice(status, ACTIVE_STATUSES, "status")
    if evidence_state is not None:
        target["evidence_state"] = _validate_choice(evidence_state, EVIDENCE_STATES, "evidence_state")
    if note_kind is not None:
        target["note_kind"] = _validate_choice(note_kind, NOTE_KINDS, "note_kind")
    target["details"] = _merge_string_lists(target.get("details", []), add_details)
    target["tags"] = _merge_string_lists(target.get("tags", []), add_tags)
    target["related_paths"] = _merge_string_lists(target.get("related_paths", []), add_related_paths)
    target["related_task_ids"] = _merge_string_lists(target.get("related_task_ids", []), add_related_task_ids)
    target["related_topics"] = _merge_string_lists(target.get("related_topics", []), add_related_topics)
    target["updated_at"] = now
    payload["generated_at"] = now
    payload["summary"] = _build_summary(notes)
    _write_idea_log(project_root, payload)
    return {
        "status": "pass",
        "idea_log_path": str(IDEA_LOG_PATH),
        "updated_note": target,
        "summary": payload["summary"],
    }


def validate_idea_log(project_root: Path) -> dict[str, Any]:
    payload = _load_or_initialize_idea_log(project_root)
    return {
        "status": "pass",
        "idea_log_path": str(IDEA_LOG_PATH),
        "summary": payload.get("summary", {}),
    }


def _load_or_initialize_idea_log(project_root: Path) -> dict[str, Any]:
    log_path = project_root / IDEA_LOG_PATH
    if not log_path.exists():
        payload = {
            "schema_version": IDEA_LOG_SCHEMA_VERSION,
            "generated_at": _isoformat_z(),
            "pack_id": project_root.name,
            "notes": [],
            "summary": _build_summary([]),
        }
        _write_idea_log(project_root, payload)
        return payload
    payload = json.loads(log_path.read_text(encoding="utf-8"))
    _validate_idea_log(payload)
    return payload


def _validate_idea_log(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != IDEA_LOG_SCHEMA_VERSION:
        raise ValueError(f"idea log must set schema_version={IDEA_LOG_SCHEMA_VERSION}")
    _require_non_empty(str(payload.get("pack_id", "")), "pack_id")
    notes = payload.get("notes")
    if not isinstance(notes, list):
        raise ValueError("idea log notes must be a list")
    for note in notes:
        if not isinstance(note, dict):
            raise ValueError("each idea log note must be an object")
        _require_non_empty(str(note.get("note_id", "")), "note.note_id")
        _require_non_empty(str(note.get("title", "")), "note.title")
        _require_non_empty(str(note.get("summary", "")), "note.summary")
        _validate_choice(str(note.get("status", "")), ACTIVE_STATUSES, "note.status")
        _validate_choice(str(note.get("review_state", "")), REVIEW_STATES, "note.review_state")
        _validate_choice(str(note.get("note_kind", "")), NOTE_KINDS, "note.note_kind")
        _validate_choice(str(note.get("evidence_state", "")), EVIDENCE_STATES, "note.evidence_state")
        _validate_choice(str(note.get("source_kind", "")), SOURCE_KINDS, "note.source_kind")
        for key in ("details", "tags", "related_paths", "related_task_ids", "related_topics"):
            value = note.get(key, [])
            if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                raise ValueError(f"note.{key} must be a list of non-empty strings")


def _write_idea_log(project_root: Path, payload: dict[str, Any]) -> None:
    log_path = project_root / IDEA_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _find_note(notes: list[dict[str, Any]], *, note_id: str) -> dict[str, Any]:
    target_id = _require_non_empty(note_id, "note_id")
    for note in notes:
        if isinstance(note, dict) and note.get("note_id") == target_id:
            return note
    raise ValueError(f"note_id not found: {target_id}")


def _build_summary(notes: list[dict[str, Any]]) -> dict[str, Any]:
    active_notes = [note for note in notes if note.get("status") == "active"]
    review_states = Counter(str(note.get("review_state", "")) for note in notes)
    note_kinds = Counter(str(note.get("note_kind", "")) for note in notes)
    evidence_states = Counter(str(note.get("evidence_state", "")) for note in notes)
    latest_note_id = notes[-1]["note_id"] if notes else None
    return {
        "active_note_count": len(active_notes),
        "archived_note_count": sum(1 for note in notes if note.get("status") == "archived"),
        "latest_note_id": latest_note_id,
        "note_kind_counts": dict(sorted(note_kinds.items())),
        "review_state_counts": dict(sorted(review_states.items())),
        "total_note_count": len(notes),
        "evidence_state_counts": dict(sorted(evidence_states.items())),
        "unreviewed_note_count": review_states.get("unreviewed", 0),
    }


def _build_note_id(*, title: str, captured_at: str) -> str:
    stamp = captured_at.replace("-", "").replace(":", "").lower().replace(".000000", "").replace("z", "z")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    slug = slug[:48] or "note"
    return f"idea-{stamp}-{slug}"


def _normalize_string_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        item = value.strip()
        if not item or item in seen:
            continue
        normalized.append(item)
        seen.add(item)
    return normalized


def _merge_string_lists(existing: Any, additions: list[str] | None) -> list[str]:
    base = existing if isinstance(existing, list) else []
    return _normalize_string_list([*base, *(additions or [])])


def _require_non_empty(value: str, field_name: str) -> str:
    item = value.strip()
    if not item:
        raise ValueError(f"{field_name} must be a non-empty string")
    return item


def _validate_choice(value: str, allowed: set[str], field_name: str) -> str:
    if value not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(sorted(allowed))}")
    return value


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
