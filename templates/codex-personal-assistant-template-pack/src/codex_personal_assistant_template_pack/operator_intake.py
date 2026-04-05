from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assistant_contracts import load_json_object, load_memory_policy, load_operator_profile
from .memory import record_memory


INTAKE_CONTRACT_PATH = Path("contracts/operator-intake.json")
INTAKE_RECORD_SCHEMA_VERSION = "codex-personal-assistant-operator-intake-record/v1"
INTAKE_POINTER_SCHEMA_VERSION = "codex-personal-assistant-operator-intake-pointer/v1"
DEFAULT_PROFILE_FIELDS_BY_CATEGORY = {
    "goal": ("business_direction", "long_horizon_goals", "near_term_priorities"),
    "preference": ("working_preferences", "ambiguity_preferences"),
    "communication_pattern": ("working_preferences", "success_signals"),
    "alignment_risk": ("grounding_principles", "known_do_not_assume", "success_signals"),
}


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_operator_intake(project_root: Path) -> dict[str, Any]:
    return load_json_object(project_root / INTAKE_CONTRACT_PATH)


def _intake_paths(project_root: Path) -> tuple[Path, Path]:
    contract = load_operator_intake(project_root)
    storage_root = project_root / str(contract["storage_root"])
    latest_pointer_path = project_root / str(contract["latest_pointer_path"])
    return storage_root, latest_pointer_path


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _intake_categories(contract: dict[str, Any]) -> list[dict[str, Any]]:
    categories = contract.get("intake_categories", [])
    return categories if isinstance(categories, list) else []


def _category_contract(contract: dict[str, Any], category_id: str) -> dict[str, Any]:
    for category in _intake_categories(contract):
        if isinstance(category, dict) and category.get("category_id") == category_id:
            return category
    raise ValueError(f"unknown operator intake category: {category_id}")


def _latest_intake_status(latest_intake: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(latest_intake, dict):
        return {
            "latest_intake_id": None,
            "latest_intake_has_explicit_profile_refinement": False,
        }
    return {
        "latest_intake_id": latest_intake.get("intake_id"),
        "latest_intake_has_explicit_profile_refinement": latest_intake.get("refine_profile_json") is not None,
    }


def _list_merge_unique(existing: Any, additions: Any) -> list[str]:
    merged: list[str] = []
    for value in list(existing) if isinstance(existing, list) else []:
        if isinstance(value, str) and value.strip() and value not in merged:
            merged.append(value)
    for value in list(additions) if isinstance(additions, list) else []:
        if isinstance(value, str) and value.strip() and value not in merged:
            merged.append(value)
    return merged


def _apply_profile_refinement(
    operator_profile: dict[str, Any],
    refinement: dict[str, Any],
    *,
    protected_fields: set[str],
    list_fields_merge_uniquely: bool,
    string_fields_replace_only_when_explicit: bool,
) -> tuple[dict[str, Any], list[str]]:
    updated_profile = json.loads(json.dumps(operator_profile))
    changed_fields: list[str] = []
    for field_name, value in refinement.items():
        if field_name in protected_fields:
            raise ValueError(f"{field_name} is protected and cannot be refined through operator intake")
        if isinstance(value, str):
            if not value.strip():
                continue
            if not string_fields_replace_only_when_explicit:
                raise ValueError(f"{field_name} string refinement is not permitted by policy")
            if updated_profile.get(field_name) != value:
                updated_profile[field_name] = value
                changed_fields.append(field_name)
            continue
        if isinstance(value, list):
            if not list_fields_merge_uniquely:
                raise ValueError(f"{field_name} list refinement is not permitted by policy")
            merged = _list_merge_unique(updated_profile.get(field_name, []), value)
            if merged != updated_profile.get(field_name):
                updated_profile[field_name] = merged
                changed_fields.append(field_name)
            continue
        raise ValueError(f"{field_name} refinements must be strings or lists of strings")
    return updated_profile, changed_fields


def show_operator_intake(project_root: Path) -> dict[str, Any]:
    contract = load_operator_intake(project_root)
    storage_root, latest_pointer_path = _intake_paths(project_root)
    latest_pointer: dict[str, Any] | None = None
    latest_intake: dict[str, Any] | None = None
    intake_count = 0
    if storage_root.exists():
        intake_files = sorted(path for path in storage_root.glob("*.json") if path.is_file())
        intake_count = len([path for path in intake_files if path.name != latest_pointer_path.name])
    if latest_pointer_path.exists():
        latest_pointer = _load_json(latest_pointer_path)
        selected_path = latest_pointer.get("selected_intake_path")
        if isinstance(selected_path, str) and selected_path:
            candidate = project_root / selected_path
            if candidate.exists():
                latest_intake = _load_json(candidate)
    latest_status = _latest_intake_status(latest_intake)
    return {
        "status": "pass",
        "storage_root": str(storage_root.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "intake_categories": contract.get("intake_categories", []),
        "profile_refinement_rules": contract.get("profile_refinement_rules", {}),
        "latest_intake_id": latest_status["latest_intake_id"],
        "latest_intake_has_explicit_profile_refinement": latest_status[
            "latest_intake_has_explicit_profile_refinement"
        ],
        "operator_intake_status": {
            "latest_intake_id": latest_status["latest_intake_id"],
            "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
            "intake_count": intake_count,
            "latest_intake_has_explicit_profile_refinement": latest_status[
                "latest_intake_has_explicit_profile_refinement"
            ],
        },
        "latest_pointer": latest_pointer,
        "latest_intake": latest_intake,
        "intake_count": intake_count,
    }


def record_operator_intake(
    project_root: Path,
    *,
    intake_id: str,
    category: str,
    summary: str,
    tags: list[str],
    replace_existing: bool,
    source: str | None = None,
    evidence: str | None = None,
    confidence: float | None = None,
    next_action: str | None = None,
    refine_profile_json: str | None = None,
    memory_category: str | None = None,
) -> dict[str, Any]:
    contract = load_operator_intake(project_root)
    category_contract = _category_contract(contract, category)
    storage_root, latest_pointer_path = _intake_paths(project_root)
    storage_root.mkdir(parents=True, exist_ok=True)
    intake_path = storage_root / f"{intake_id}.json"
    existed = intake_path.exists()
    if existed and not replace_existing:
        raise ValueError(f"intake `{intake_id}` already exists; use replace_existing to overwrite it")
    if confidence is not None and not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")
    memory_policy = load_memory_policy(project_root)
    memory_storage_root = project_root / str(memory_policy["storage_root"])
    memory_path = memory_storage_root / f"operator-intake-{intake_id}.json"
    memory_existed = memory_path.exists()
    if memory_existed and not replace_existing:
        raise ValueError(
            f"memory `operator-intake-{intake_id}` already exists; use replace_existing to overwrite it"
        )

    explicit_refinement: dict[str, Any] | None = None
    if refine_profile_json is not None:
        loaded_refinement = json.loads(refine_profile_json)
        if not isinstance(loaded_refinement, dict):
            raise ValueError("refine_profile_json must decode to a JSON object")
        explicit_refinement = loaded_refinement

    payload = {
        "schema_version": INTAKE_RECORD_SCHEMA_VERSION,
        "intake_id": intake_id,
        "category": category,
        "category_contract": category_contract,
        "summary": summary,
        "tags": sorted({tag for tag in tags if tag}),
        "source": source,
        "evidence": evidence,
        "confidence": confidence,
        "next_action": next_action,
        "refine_profile_json": explicit_refinement,
        "recorded_at": _isoformat_z(),
    }
    _write_json(intake_path, payload)
    pointer_payload = {
        "schema_version": INTAKE_POINTER_SCHEMA_VERSION,
        "selected_intake_id": intake_id,
        "selected_intake_path": str(intake_path.relative_to(project_root).as_posix()),
        "updated_at": payload["recorded_at"],
    }
    _write_json(latest_pointer_path, pointer_payload)

    profile_refinement_fields: list[str] = []
    profile_refinement_path = None
    if explicit_refinement is not None:
        operator_profile_path = project_root / "contracts/operator-profile.json"
        operator_profile = load_operator_profile(project_root)
        rules = contract.get("profile_refinement_rules", {})
        protected_fields = set(rules.get("protected_fields", [])) if isinstance(rules, dict) else set()
        updated_profile, profile_refinement_fields = _apply_profile_refinement(
            operator_profile,
            explicit_refinement,
            protected_fields=protected_fields,
            list_fields_merge_uniquely=bool(rules.get("list_fields_merge_uniquely", True)) if isinstance(rules, dict) else True,
            string_fields_replace_only_when_explicit=bool(rules.get("string_fields_replace_only_when_explicit", True)) if isinstance(rules, dict) else True,
        )
        if profile_refinement_fields:
            _write_json(operator_profile_path, updated_profile)
            profile_refinement_path = str(operator_profile_path.relative_to(project_root).as_posix())

    stable_memory_category = category_contract.get("stable_memory_category")
    if not isinstance(stable_memory_category, str) or not stable_memory_category:
        raise ValueError(f"operator intake category `{category}` must declare stable_memory_category")
    memory_result = record_memory(
        project_root,
        memory_id=f"operator-intake-{intake_id}",
        category=memory_category or stable_memory_category,
        summary=summary,
        next_action=next_action,
        tags=[*tags, "operator-intake", category],
        replace_existing=replace_existing,
        source=source or "operator-intake",
        evidence=evidence or str(intake_path.relative_to(project_root).as_posix()),
        confidence=confidence,
    )

    return {
        "status": "pass",
        "intake_id": intake_id,
        "intake_path": str(intake_path.relative_to(project_root).as_posix()),
        "latest_pointer_path": str(latest_pointer_path.relative_to(project_root).as_posix()),
        "replaced_existing": bool(existed and replace_existing),
        "profile_refinement_applied": bool(profile_refinement_fields),
        "profile_refinement_fields": profile_refinement_fields,
        "profile_refinement_path": profile_refinement_path,
        "memory_result": memory_result,
    }
