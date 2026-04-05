from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .assistant_contracts import load_memory_policy


DISTILLATION_RECORD_SCHEMA_VERSION = "codex-personal-assistant-session-distillation/v1"
DISTILLATION_POINTER_SCHEMA_VERSION = "codex-personal-assistant-session-distillation-pointer/v1"


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _memory_paths(project_root: Path) -> tuple[Path, Path]:
    policy = load_memory_policy(project_root)
    storage_root = project_root / str(policy["storage_root"])
    latest_pointer_path = project_root / str(policy["latest_pointer_path"])
    return storage_root, latest_pointer_path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _session_distillation_policy(project_root: Path) -> dict[str, Any]:
    policy = load_memory_policy(project_root)
    distillation_policy = policy.get("session_distillation_policy", {})
    if not isinstance(distillation_policy, dict):
        raise ValueError("memory policy must declare session_distillation_policy")
    return distillation_policy


def _continuity_policy(project_root: Path) -> dict[str, Any]:
    policy = load_memory_policy(project_root)
    continuity_policy = policy.get("continuity_checkpoint_policy", {})
    if not isinstance(continuity_policy, dict):
        return {}
    return continuity_policy


def _closeout_followthrough_policy(project_root: Path) -> dict[str, Any]:
    policy = _session_distillation_policy(project_root)
    followthrough_policy = policy.get("closeout_followthrough_policy", {})
    if not isinstance(followthrough_policy, dict):
        return {}
    return followthrough_policy


def _session_distillation_paths(project_root: Path) -> tuple[Path, Path]:
    policy = _session_distillation_policy(project_root)
    storage_root = project_root / str(policy["storage_root"])
    latest_pointer_path = project_root / str(policy["latest_pointer_path"])
    return storage_root, latest_pointer_path


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _load_memory_record(project_root: Path, memory_id: str) -> dict[str, Any]:
    storage_root, _ = _memory_paths(project_root)
    memory_path = storage_root / f"{memory_id}.json"
    if not memory_path.exists():
        raise ValueError(f"memory `{memory_id}` does not exist")
    return _load_json(memory_path)


def _latest_memory_pointer(project_root: Path) -> tuple[Path, dict[str, Any] | None, dict[str, Any] | None]:
    _, latest_pointer_path = _memory_paths(project_root)
    latest_pointer: dict[str, Any] | None = None
    latest_memory: dict[str, Any] | None = None
    if latest_pointer_path.exists():
        latest_pointer = _load_json(latest_pointer_path)
        selected_path = latest_pointer.get("selected_memory_path")
        if isinstance(selected_path, str) and selected_path:
            candidate = project_root / selected_path
            if candidate.exists():
                latest_memory = _load_json(candidate)
    return latest_pointer_path, latest_pointer, latest_memory


def _parse_iso_z(value: str | None) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _memory_records(project_root: Path) -> list[dict[str, Any]]:
    storage_root, latest_pointer_path = _memory_paths(project_root)
    if not storage_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(storage_root.glob("*.json")):
        if not path.is_file() or path.name == latest_pointer_path.name:
            continue
        payload = _load_json(path)
        payload["_relative_path"] = str(path.relative_to(project_root).as_posix())
        records.append(payload)
    return records


def record_memory(
    project_root: Path,
    *,
    memory_id: str,
    category: str,
    summary: str,
    next_action: str | None,
    tags: list[str],
    replace_existing: bool,
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    storage_root, latest_pointer_path = _memory_paths(project_root)
    memory_path = storage_root / f"{memory_id}.json"
    existed = memory_path.exists()
    if existed and not replace_existing:
        raise ValueError(f"memory `{memory_id}` already exists; use replace_existing to overwrite it")
    if confidence is not None and not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    payload = {
        "schema_version": "codex-personal-assistant-memory/v2",
        "memory_id": memory_id,
        "category": category,
        "summary": summary,
        "next_action": next_action,
        "tags": sorted({tag for tag in tags if tag}),
        "source": source,
        "evidence": evidence,
        "confidence": confidence,
        "recorded_at": _isoformat_z(),
    }
    _write_json(memory_path, payload)
    pointer_payload = {
        "schema_version": "codex-personal-assistant-memory-pointer/v1",
        "selected_memory_id": memory_id,
        "selected_memory_path": str(memory_path.relative_to(project_root).as_posix()),
        "updated_at": payload["recorded_at"],
    }
    _write_json(latest_pointer_path, pointer_payload)
    return {
        "status": "pass",
        "memory_id": memory_id,
        "category": category,
        "memory_path": str(memory_path.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "replaced_existing": bool(existed and replace_existing),
    }


def record_continuity_checkpoint(
    project_root: Path,
    *,
    checkpoint_id: str,
    summary: str,
    next_action: str | None,
    assessment: str | None = None,
    tags: list[str] | None = None,
    replace_existing: bool = True,
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    continuity_policy = _continuity_policy(project_root)
    default_tags = [tag for tag in continuity_policy.get("default_memory_tags", []) if isinstance(tag, str)]
    assessment_tag = f"assessment-{assessment}" if isinstance(assessment, str) and assessment else None
    merged_tags = sorted({*(tags or []), *default_tags, "continuity", *( [assessment_tag] if assessment_tag else [] )})
    default_category = continuity_policy.get("default_memory_category")
    category = default_category if isinstance(default_category, str) and default_category else "goal"
    if assessment in {"drift_risk", "unclear"}:
        category = "alignment_risk"
    memory_id = f"continuity-{checkpoint_id}"
    return record_memory(
        project_root,
        memory_id=memory_id,
        category=category,
        summary=summary,
        next_action=next_action,
        tags=merged_tags,
        replace_existing=replace_existing,
        source=source or "continuity-checkpoint",
        evidence=evidence,
        confidence=confidence,
    )


def show_continuity_status(project_root: Path) -> dict[str, Any]:
    continuity_policy = _continuity_policy(project_root)
    stale_after_hours = int(continuity_policy.get("stale_after_hours", 72) or 72)
    latest_pointer_path, latest_pointer, latest_memory = _latest_memory_pointer(project_root)
    latest_recorded_at = latest_memory.get("recorded_at") if isinstance(latest_memory, dict) else None
    recorded_at = _parse_iso_z(latest_recorded_at)
    age_hours: float | None = None
    if recorded_at is not None:
        age = datetime.now(timezone.utc) - recorded_at.astimezone(timezone.utc)
        age_hours = round(age / timedelta(hours=1), 3)

    health = "missing"
    reason = "No assistant continuity pointer is present yet."
    recommended_action = "Record a business review or another continuity checkpoint before ending the session."
    if latest_pointer is not None and latest_memory is None:
        reason = "The assistant continuity pointer exists, but the selected memory file is missing."
        recommended_action = "Refresh continuity by writing a new checkpoint so the pointer references a valid memory file."
    elif latest_memory is not None:
        health = "healthy"
        reason = "Assistant continuity memory is available for the latest session."
        recommended_action = "Continue and refresh continuity again at the next meaningful session boundary."
        if age_hours is not None and age_hours > stale_after_hours:
            health = "stale"
            reason = "Assistant continuity memory exists, but it is older than the configured stale threshold."
            recommended_action = "Refresh continuity with a new business review or session closeout checkpoint."

    return {
        "status": "pass",
        "health": health,
        "reason": reason,
        "recommended_action": recommended_action,
        "latest_pointer_present": latest_pointer is not None,
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "latest_memory_id": latest_memory.get("memory_id") if isinstance(latest_memory, dict) else None,
        "latest_memory_category": latest_memory.get("category") if isinstance(latest_memory, dict) else None,
        "latest_memory_recorded_at": latest_recorded_at,
        "stale_after_hours": stale_after_hours,
        "age_hours": age_hours,
    }


def read_memory(project_root: Path) -> dict[str, Any]:
    storage_root, latest_pointer_path = _memory_paths(project_root)
    latest_pointer_name = latest_pointer_path.name
    memory_files = sorted(
        path
        for path in storage_root.glob("*.json")
        if path.is_file() and path.name != latest_pointer_name
    )
    latest_pointer: dict[str, Any] | None = None
    latest_memory: dict[str, Any] | None = None
    if latest_pointer_path.exists():
        latest_pointer = _load_json(latest_pointer_path)
        selected_path = latest_pointer.get("selected_memory_path")
        if isinstance(selected_path, str) and selected_path:
            candidate = project_root / selected_path
            if candidate.exists():
                latest_memory = _load_json(candidate)

    distillation_status = show_memory_distillation(project_root).get("session_memory_distillation_status", {})
    continuity_status = show_continuity_status(project_root)

    return {
        "status": "pass",
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "latest_pointer": latest_pointer,
        "latest_memory": latest_memory,
        "memory_count": len(memory_files),
        "available_memory_ids": [path.stem for path in memory_files],
        "session_memory_distillation_status": distillation_status,
        "continuity_status": continuity_status,
    }


def delete_memory(project_root: Path, *, memory_id: str) -> dict[str, Any]:
    storage_root, latest_pointer_path = _memory_paths(project_root)
    memory_path = storage_root / f"{memory_id}.json"
    deleted = False
    if memory_path.exists():
        memory_path.unlink()
        deleted = True

    cleared_latest_pointer = False
    if latest_pointer_path.exists():
        latest_pointer = _load_json(latest_pointer_path)
        selected_memory_id = latest_pointer.get("selected_memory_id")
        selected_memory_path = latest_pointer.get("selected_memory_path")
        expected_relative = str(memory_path.relative_to(project_root).as_posix())
        if selected_memory_id == memory_id or selected_memory_path == expected_relative:
            latest_pointer_path.unlink()
            cleared_latest_pointer = True

    return {
        "status": "pass",
        "memory_id": memory_id,
        "deleted": deleted,
        "cleared_latest_pointer": cleared_latest_pointer,
    }


def show_memory_distillation(project_root: Path) -> dict[str, Any]:
    storage_root, latest_pointer_path = _session_distillation_paths(project_root)
    latest_pointer: dict[str, Any] | None = None
    latest_distillation: dict[str, Any] | None = None
    distillation_count = 0
    if storage_root.exists():
        distillation_files = sorted(path for path in storage_root.glob("*.json") if path.is_file())
        distillation_count = len([path for path in distillation_files if path.name != latest_pointer_path.name])
    if latest_pointer_path.exists():
        latest_pointer = _load_json(latest_pointer_path)
        selected_path = latest_pointer.get("selected_distillation_path")
        if isinstance(selected_path, str) and selected_path:
            candidate = project_root / selected_path
            if candidate.exists():
                latest_distillation = _load_json(candidate)

    return {
        "status": "pass",
        "storage_root": str(storage_root.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "latest_pointer": latest_pointer,
        "latest_distillation": latest_distillation,
        "distillation_count": distillation_count,
        "session_memory_distillation_status": {
            "latest_distillation_id": latest_distillation.get("distillation_id")
            if isinstance(latest_distillation, dict)
            else None,
            "latest_distillation_classified_category": latest_distillation.get("classified_category")
            if isinstance(latest_distillation, dict)
            else None,
            "latest_distillation_signal_strength": latest_distillation.get("signal_strength")
            if isinstance(latest_distillation, dict)
            else None,
            "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
            "distillation_count": distillation_count,
            "latest_distillation_promoted_memory": bool(
                isinstance(latest_distillation, dict) and latest_distillation.get("promoted_memory_id")
            ),
            "latest_promoted_memory_id": latest_distillation.get("promoted_memory_id")
            if isinstance(latest_distillation, dict)
            else None,
        },
    }


def distill_session_memory(
    project_root: Path,
    *,
    distillation_id: str,
    summary: str,
    stable_signal_reason: str,
    source_memory_ids: list[str],
    replace_existing: bool,
    promote_category: str | None = None,
    classified_category: str | None = None,
    signal_strength: str | None = None,
    promoted_memory_id: str | None = None,
    next_action: str | None = None,
    tags: list[str],
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    if not source_memory_ids:
        raise ValueError("distillation requires at least one source_memory_id")
    if confidence is not None and not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")

    policy = _session_distillation_policy(project_root)
    allowed_source_categories = {
        category for category in policy.get("allowed_source_categories", []) if isinstance(category, str)
    }
    promotable_categories = {
        category for category in policy.get("promotable_memory_categories", []) if isinstance(category, str)
    }
    allowed_signal_strengths = {
        strength for strength in load_memory_policy(project_root).get("distillation_signal_strengths", [])
        if isinstance(strength, str)
    }
    if promote_category is not None and promote_category not in promotable_categories:
        raise ValueError(f"promote_category `{promote_category}` is not allowed by session_distillation_policy")
    if classified_category is not None and classified_category not in promotable_categories:
        raise ValueError(f"classified_category `{classified_category}` is not allowed by session_distillation_policy")

    unique_source_ids = list(dict.fromkeys(source_memory_ids))
    source_memories: list[dict[str, Any]] = []
    for memory_id in unique_source_ids:
        memory_record = _load_memory_record(project_root, memory_id)
        memory_category = memory_record.get("category")
        if allowed_source_categories and memory_category not in allowed_source_categories:
            raise ValueError(
                f"memory `{memory_id}` has category `{memory_category}` which is not allowed for distillation"
            )
        source_memories.append(memory_record)

    storage_root, latest_pointer_path = _session_distillation_paths(project_root)
    storage_root.mkdir(parents=True, exist_ok=True)
    distillation_path = storage_root / f"{distillation_id}.json"
    existed = distillation_path.exists()
    if existed and not replace_existing:
        raise ValueError(
            f"session distillation `{distillation_id}` already exists; use replace_existing to overwrite it"
        )

    resolved_promoted_memory_id = promoted_memory_id
    if promote_category is not None and not resolved_promoted_memory_id:
        resolved_promoted_memory_id = f"session-distillation-{distillation_id}"
    resolved_classified_category = promote_category or classified_category
    resolved_signal_strength = signal_strength
    if resolved_signal_strength is None:
        resolved_signal_strength = "repeated_pattern" if promote_category is not None else "session_observation"
    if allowed_signal_strengths and resolved_signal_strength not in allowed_signal_strengths:
        raise ValueError(
            f"signal_strength `{resolved_signal_strength}` is not allowed by distillation_signal_strengths"
        )

    payload = {
        "schema_version": DISTILLATION_RECORD_SCHEMA_VERSION,
        "distillation_id": distillation_id,
        "summary": summary,
        "stable_signal_reason": stable_signal_reason,
        "source_memory_ids": unique_source_ids,
        "source_memories": source_memories,
        "promote_category": promote_category,
        "classified_category": resolved_classified_category,
        "signal_strength": resolved_signal_strength,
        "promoted_memory_id": resolved_promoted_memory_id,
        "next_action": next_action,
        "tags": sorted({tag for tag in tags if tag}),
        "source": source,
        "evidence": evidence,
        "confidence": confidence,
        "recorded_at": _isoformat_z(),
    }
    _write_json(distillation_path, payload)
    pointer_payload = {
        "schema_version": DISTILLATION_POINTER_SCHEMA_VERSION,
        "selected_distillation_id": distillation_id,
        "selected_distillation_path": str(distillation_path.relative_to(project_root).as_posix()),
        "updated_at": payload["recorded_at"],
    }
    _write_json(latest_pointer_path, pointer_payload)

    memory_result = None
    if promote_category is not None and resolved_promoted_memory_id is not None:
        memory_result = record_memory(
            project_root,
            memory_id=resolved_promoted_memory_id,
            category=promote_category,
            summary=summary,
            next_action=next_action,
            tags=[*tags, "session-distillation", promote_category],
            replace_existing=replace_existing,
            source=source or "session-distillation",
            evidence=evidence or str(distillation_path.relative_to(project_root).as_posix()),
            confidence=confidence,
        )

    return {
        "status": "pass",
        "distillation_id": distillation_id,
        "distillation_path": str(distillation_path.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "replaced_existing": bool(existed and replace_existing),
        "promoted_memory_id": resolved_promoted_memory_id,
        "classified_category": resolved_classified_category,
        "signal_strength": resolved_signal_strength,
        "memory_result": memory_result,
    }


def record_closeout_distillation(
    project_root: Path,
    *,
    review_id: str,
    summary: str,
    next_action: str | None,
    assessment: str,
    continuity_memory_id: str,
    tags: list[str],
    replace_existing: bool,
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    followthrough_policy = _closeout_followthrough_policy(project_root)
    default_tags = [
        tag for tag in followthrough_policy.get("default_tags", []) if isinstance(tag, str)
    ]
    matching_rule = (
        followthrough_policy.get("matching_rule")
        if isinstance(followthrough_policy.get("matching_rule"), str)
        else "same_category_and_assessment"
    )
    max_source_memory_count = int(followthrough_policy.get("max_source_memory_count", 2) or 2)
    min_source_memory_count_for_promotion = int(
        followthrough_policy.get("min_source_memory_count_for_promotion", 2) or 2
    )
    continuity_record = _load_memory_record(project_root, continuity_memory_id)
    classified_category = continuity_record.get("category")
    if not isinstance(classified_category, str) or not classified_category:
        raise ValueError("closeout distillation requires the continuity checkpoint to declare a category")
    assessment_tag = f"assessment-{assessment}"
    matching_continuity_records: list[dict[str, Any]] = []
    for record in _memory_records(project_root):
        record_tags = record.get("tags")
        if not isinstance(record_tags, list):
            continue
        if "continuity-checkpoint" not in record_tags:
            continue
        if record.get("category") != classified_category:
            continue
        if matching_rule == "same_category_and_assessment" and assessment_tag not in record_tags:
            continue
        matching_continuity_records.append(record)
    matching_continuity_records = sorted(
        matching_continuity_records,
        key=lambda item: str(item.get("recorded_at") or ""),
        reverse=True,
    )
    source_memory_ids = [
        str(record.get("memory_id"))
        for record in matching_continuity_records[:max_source_memory_count]
        if isinstance(record.get("memory_id"), str) and record.get("memory_id")
    ]
    if continuity_memory_id not in source_memory_ids:
        source_memory_ids.insert(0, continuity_memory_id)
    source_memory_ids = list(dict.fromkeys(source_memory_ids))[:max_source_memory_count]
    repeated_closeout_signal_count = len(source_memory_ids)
    signal_strength = "repeated_pattern" if repeated_closeout_signal_count >= 2 else "session_observation"
    promote_category = (
        classified_category
        if repeated_closeout_signal_count >= min_source_memory_count_for_promotion
        else None
    )
    stable_signal_reason = (
        "Business-review closeout keeps this session visible as inspectable distillation so thin history does not depend on one continuity checkpoint alone."
        if promote_category is None
        else "Repeated business-review closeouts with the same category and assessment justify bounded carry-forward into durable relationship memory."
    )
    result = distill_session_memory(
        project_root,
        distillation_id=f"closeout-review-{review_id}",
        summary=summary,
        stable_signal_reason=stable_signal_reason,
        source_memory_ids=source_memory_ids,
        replace_existing=replace_existing,
        promote_category=promote_category,
        classified_category=classified_category,
        signal_strength=signal_strength,
        next_action=next_action,
        tags=sorted({*tags, *default_tags, "session-carry-forward", "session-closeout", assessment_tag}),
        source=source or "business-review-closeout",
        evidence=evidence or str(continuity_record.get("_relative_path") or ""),
        confidence=confidence,
    )
    result["promote_category"] = promote_category
    result["repeated_closeout_signal_count"] = repeated_closeout_signal_count
    result["matching_rule"] = matching_rule
    result["source_memory_ids"] = source_memory_ids
    return result
