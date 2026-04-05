from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .assistant_contracts import (
    load_memory_policy,
    load_operator_intake,
    load_operator_profile,
    load_profile,
)
from .memory import show_memory_distillation
from .operator_intake import show_operator_intake


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _storage_records(project_root: Path, *, storage_root: Path, pointer_name: str) -> list[dict[str, Any]]:
    if not storage_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(storage_root.glob("*.json")):
        if not path.is_file() or path.name == pointer_name:
            continue
        payload = _load_json(path)
        payload["_relative_path"] = str(path.relative_to(project_root).as_posix())
        records.append(payload)
    return records


def _memory_records(project_root: Path) -> list[dict[str, Any]]:
    policy = load_memory_policy(project_root)
    storage_root = project_root / str(policy["storage_root"])
    latest_pointer_path = project_root / str(policy["latest_pointer_path"])
    return _storage_records(project_root, storage_root=storage_root, pointer_name=latest_pointer_path.name)


def _intake_records(project_root: Path, intake_contract: dict[str, Any]) -> list[dict[str, Any]]:
    storage_root = project_root / str(intake_contract["storage_root"])
    latest_pointer_path = project_root / str(intake_contract["latest_pointer_path"])
    return _storage_records(project_root, storage_root=storage_root, pointer_name=latest_pointer_path.name)


def _distillation_records(project_root: Path, memory_policy: dict[str, Any]) -> list[dict[str, Any]]:
    distillation_policy = memory_policy.get("session_distillation_policy", {})
    if not isinstance(distillation_policy, dict):
        return []
    storage_root_value = distillation_policy.get("storage_root")
    latest_pointer_value = distillation_policy.get("latest_pointer_path")
    if not isinstance(storage_root_value, str) or not storage_root_value.strip():
        return []
    if not isinstance(latest_pointer_value, str) or not latest_pointer_value.strip():
        return []
    storage_root = project_root / storage_root_value
    latest_pointer_path = project_root / latest_pointer_value
    return _storage_records(project_root, storage_root=storage_root, pointer_name=latest_pointer_path.name)


def _recent_memory_records(records: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    sorted_records = sorted(records, key=lambda item: str(item.get("recorded_at") or ""), reverse=True)
    return sorted_records[:limit]


def _memory_count(records: list[dict[str, Any]], category: str) -> int:
    return sum(1 for record in records if record.get("category") == category)


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _declared_signal_categories(intake_contract: dict[str, Any]) -> list[dict[str, str]]:
    declared: list[dict[str, str]] = []
    categories = intake_contract.get("intake_categories", [])
    if not isinstance(categories, list):
        return declared
    for category in categories:
        if not isinstance(category, dict):
            continue
        category_id = category.get("category_id")
        prompt = category.get("prompt")
        if not isinstance(category_id, str) or not category_id.strip():
            continue
        if not isinstance(prompt, str) or not prompt.strip():
            continue
        declared.append({"category_id": category_id, "prompt": prompt})
    return declared


def _signal_strength(*, intake_count: int, distillation_count: int, memory_count: int) -> str:
    total_signal_count = intake_count + distillation_count + memory_count
    source_kind_count = sum(
        1
        for count in (intake_count, distillation_count, memory_count)
        if count > 0
    )
    if total_signal_count == 0:
        return "missing"
    if distillation_count > 0 and memory_count > 0:
        return "confirmed"
    if source_kind_count >= 2 or total_signal_count >= 3:
        return "repeated"
    return "tentative"


def _relationship_status(
    *,
    intake_count: int,
    distillation_count: int,
    personalized_memory_count: int,
    latest_intake_id: str | None,
    latest_distillation_id: str | None,
    latest_memory_id: str | None,
    recent_signal_count: int,
) -> dict[str, Any]:
    if intake_count == 0 and distillation_count == 0 and personalized_memory_count <= 1:
        maturity = "baseline"
        genericity_risk = "high"
        improvement_focus = (
            "Capture explicit operator intake and distill repeated session signals before expecting highly tailored behavior."
        )
    elif intake_count >= 1 and distillation_count >= 1 and personalized_memory_count >= 2:
        maturity = "grounded"
        genericity_risk = "low"
        improvement_focus = (
            "Keep reinforcing stable preferences and working patterns through explicit intake and distillation rather than guessing."
        )
    else:
        maturity = "emerging"
        genericity_risk = "medium"
        improvement_focus = "Add one or two more explicit relationship signals so the assistant can rely less on the default profile."
    return {
        "maturity": maturity,
        "genericity_risk": genericity_risk,
        "improvement_focus": improvement_focus,
        "intake_count": intake_count,
        "distillation_count": distillation_count,
        "personalized_memory_count": personalized_memory_count,
        "recent_signal_count": recent_signal_count,
        "latest_intake_id": latest_intake_id,
        "latest_distillation_id": latest_distillation_id,
        "latest_memory_id": latest_memory_id,
    }


def show_relationship_state(project_root: Path) -> dict[str, Any]:
    profile = load_profile(project_root)
    operator = load_operator_profile(project_root)
    memory_policy = load_memory_policy(project_root)
    intake_contract = load_operator_intake(project_root)
    intake = show_operator_intake(project_root)
    distillation = show_memory_distillation(project_root)
    records = _memory_records(project_root)
    intake_records = _intake_records(project_root, intake_contract)
    distillation_records = _distillation_records(project_root, memory_policy)
    latest_memory = _recent_memory_records(records, limit=1)
    latest_memory_record = latest_memory[0] if latest_memory else None
    declared_signal_categories = _declared_signal_categories(intake_contract)
    declared_category_ids = [item["category_id"] for item in declared_signal_categories]
    declared_category_id_set = set(declared_category_ids)

    preference_records = [record for record in records if record.get("category") == "preference"]
    communication_records = [record for record in records if record.get("category") == "communication_pattern"]
    alignment_risk_records = [record for record in records if record.get("category") == "alignment_risk"]
    goal_records = [record for record in records if record.get("category") == "goal"]

    latest_intake = intake.get("latest_intake")
    latest_distillation = distillation.get("latest_distillation")
    recent_signals: list[dict[str, Any]] = []
    if isinstance(latest_intake, dict):
        recent_signals.append(
            {
                "signal_type": "operator_intake",
                "signal_id": latest_intake.get("intake_id"),
                "category": latest_intake.get("category"),
                "summary": latest_intake.get("summary"),
            }
        )
    if isinstance(latest_distillation, dict):
        recent_signals.append(
            {
                "signal_type": "session_distillation",
                "signal_id": latest_distillation.get("distillation_id"),
                "category": latest_distillation.get("promote_category"),
                "summary": latest_distillation.get("summary"),
            }
        )
    for record in _recent_memory_records(records):
        recent_signals.append(
            {
                "signal_type": "assistant_memory",
                "signal_id": record.get("memory_id"),
                "category": record.get("category"),
                "summary": record.get("summary"),
            }
        )

    covered_signal_category_ids: set[str] = set()
    for record in intake_records:
        category = record.get("category")
        if isinstance(category, str) and category in declared_category_id_set:
            covered_signal_category_ids.add(category)
    for record in distillation_records:
        category = record.get("promote_category")
        if isinstance(category, str) and category in declared_category_id_set:
            covered_signal_category_ids.add(category)
    for record in records:
        category = record.get("category")
        if isinstance(category, str) and category in declared_category_id_set:
            covered_signal_category_ids.add(category)

    covered_signal_categories = [
        category_id for category_id in declared_category_ids if category_id in covered_signal_category_ids
    ]
    missing_signal_categories = [
        category_id for category_id in declared_category_ids if category_id not in covered_signal_category_ids
    ]
    next_learning_prompts = [
        {
            "category_id": category["category_id"],
            "prompt": category["prompt"],
        }
        for category in declared_signal_categories
        if category["category_id"] in missing_signal_categories
    ][:3]
    signal_strength_by_category: list[dict[str, Any]] = []
    for category in declared_signal_categories:
        category_id = category["category_id"]
        intake_count = sum(1 for record in intake_records if record.get("category") == category_id)
        distillation_count = sum(1 for record in distillation_records if record.get("promote_category") == category_id)
        memory_count = sum(1 for record in records if record.get("category") == category_id)
        strength = _signal_strength(
            intake_count=intake_count,
            distillation_count=distillation_count,
            memory_count=memory_count,
        )
        signal_strength_by_category.append(
            {
                "category_id": category_id,
                "signal_strength": strength,
                "ready_for_durable_use": strength in {"repeated", "confirmed"},
                "source_counts": {
                    "operator_intake": intake_count,
                    "session_distillation": distillation_count,
                    "assistant_memory": memory_count,
                },
                "total_signal_count": intake_count + distillation_count + memory_count,
                "next_prompt": None if strength == "confirmed" else category["prompt"],
            }
        )
    preference_strength_status = next(
        (
            entry
            for entry in signal_strength_by_category
            if entry.get("category_id") == "preference"
        ),
        {
            "category_id": "preference",
            "signal_strength": "missing",
            "ready_for_durable_use": False,
            "source_counts": {
                "operator_intake": 0,
                "session_distillation": 0,
                "assistant_memory": 0,
            },
            "total_signal_count": 0,
            "next_prompt": next(
                (
                    category["prompt"]
                    for category in declared_signal_categories
                    if category["category_id"] == "preference"
                ),
                None,
            ),
        },
    )

    learned_preferences = _dedupe_strings(
        [value for value in operator.get("working_preferences", []) if isinstance(value, str)]
        + [str(record.get("summary")) for record in preference_records if isinstance(record.get("summary"), str)]
    )
    communication_patterns = _dedupe_strings(
        [str(record.get("summary")) for record in communication_records if isinstance(record.get("summary"), str)]
    )
    alignment_watch_fors = _dedupe_strings(
        [value for value in operator.get("known_do_not_assume", []) if isinstance(value, str)]
        + [value for value in operator.get("grounding_principles", []) if isinstance(value, str)]
        + [str(record.get("summary")) for record in alignment_risk_records if isinstance(record.get("summary"), str)]
    )
    goal_anchors = _dedupe_strings(
        [value for value in operator.get("near_term_priorities", []) if isinstance(value, str)]
        + [value for value in operator.get("long_horizon_goals", []) if isinstance(value, str)]
        + [str(record.get("summary")) for record in goal_records if isinstance(record.get("summary"), str)]
    )

    personalized_memory_count = sum(
        _memory_count(records, category)
        for category in ("preference", "communication_pattern", "alignment_risk", "goal")
    )
    relationship_state_status = _relationship_status(
        intake_count=int(intake.get("intake_count", 0) or 0),
        distillation_count=int(distillation.get("distillation_count", 0) or 0),
        personalized_memory_count=personalized_memory_count,
        latest_intake_id=str(intake.get("latest_intake_id")) if intake.get("latest_intake_id") else None,
        latest_distillation_id=(
            str(distillation.get("latest_distillation", {}).get("distillation_id"))
            if isinstance(distillation.get("latest_distillation"), dict)
            and distillation.get("latest_distillation", {}).get("distillation_id")
            else None
        ),
        latest_memory_id=(
            str(latest_memory_record.get("memory_id"))
            if isinstance(latest_memory_record, dict) and latest_memory_record.get("memory_id")
            else None
        ),
        recent_signal_count=len(recent_signals),
    )
    personalization_stage = {
        "baseline": "baseline",
        "emerging": "learning",
        "grounded": "grounded",
    }[relationship_state_status["maturity"]]
    relationship_state_summary = {
        "personalization_stage": personalization_stage,
        "genericity_risk": relationship_state_status["genericity_risk"],
        "improvement_focus": relationship_state_status["improvement_focus"],
        "latest_intake_id": relationship_state_status["latest_intake_id"],
        "latest_distillation_id": relationship_state_status["latest_distillation_id"],
        "latest_memory_id": relationship_state_status["latest_memory_id"],
        "recent_signal_count": relationship_state_status["recent_signal_count"],
        "covered_signal_categories": covered_signal_categories,
        "missing_signal_categories": missing_signal_categories,
        "next_learning_prompts": next_learning_prompts,
        "signal_strength_by_category": signal_strength_by_category,
        "preference_signal_strength": preference_strength_status.get("signal_strength"),
    }

    return {
        "status": "pass",
        "assistant_id": profile.get("assistant_id"),
        "operator_id": operator.get("operator_id") or profile.get("operator_id"),
        "business_direction": operator.get("business_direction"),
        "current_role": operator.get("current_role"),
        "goal_anchors": goal_anchors,
        "learned_preferences": learned_preferences,
        "communication_patterns": communication_patterns,
        "alignment_watch_fors": alignment_watch_fors,
        "recent_relationship_signals": recent_signals,
        "covered_signal_categories": covered_signal_categories,
        "missing_signal_categories": missing_signal_categories,
        "next_learning_prompts": next_learning_prompts,
        "signal_strength_by_category": signal_strength_by_category,
        "preference_strength_status": preference_strength_status,
        "personalization_stage": personalization_stage,
        "relationship_state_summary": relationship_state_summary,
        "relationship_state_status": relationship_state_status,
        "latest_memory_id": relationship_state_status["latest_memory_id"],
        "latest_memory_path": latest_memory_record.get("_relative_path") if isinstance(latest_memory_record, dict) else None,
    }
