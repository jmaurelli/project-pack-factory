from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROFILE_PATH = Path("contracts/assistant-profile.json")
OPERATOR_PROFILE_PATH = Path("contracts/operator-profile.json")
PARTNERSHIP_POLICY_PATH = Path("contracts/partnership-policy.json")
CONTEXT_ROUTING_PATH = Path("contracts/context-routing.json")
MEMORY_POLICY_PATH = Path("contracts/memory-policy.json")
SKILL_CATALOG_PATH = Path("contracts/skill-catalog.json")
ARCHITECTURE_DOC_PATH = Path("docs/specs/assistant-architecture.md")
ALIGNMENT_MODEL_DOC_PATH = Path("docs/specs/operator-alignment-model.md")
BOOTSTRAP_GUIDE_PATH = Path("prompts/bootstrap-checklist.md")
RESTART_MEMORY_GUIDE_PATH = Path("prompts/restart-memory-guide.md")
SKILLS_GUIDE_PATH = Path("prompts/skills-guide.md")
OPERATOR_DISCOVERY_GUIDE_PATH = Path("prompts/operator-discovery-guide.md")

REQUIRED_SURFACE_PATHS = (
    PROFILE_PATH,
    OPERATOR_PROFILE_PATH,
    PARTNERSHIP_POLICY_PATH,
    CONTEXT_ROUTING_PATH,
    MEMORY_POLICY_PATH,
    SKILL_CATALOG_PATH,
    ARCHITECTURE_DOC_PATH,
    ALIGNMENT_MODEL_DOC_PATH,
    BOOTSTRAP_GUIDE_PATH,
    RESTART_MEMORY_GUIDE_PATH,
    SKILLS_GUIDE_PATH,
    OPERATOR_DISCOVERY_GUIDE_PATH,
)


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return payload


def path_bundle(project_root: Path) -> dict[str, Path]:
    return {
        "profile": project_root / PROFILE_PATH,
        "operator_profile": project_root / OPERATOR_PROFILE_PATH,
        "partnership_policy": project_root / PARTNERSHIP_POLICY_PATH,
        "context_routing": project_root / CONTEXT_ROUTING_PATH,
        "memory_policy": project_root / MEMORY_POLICY_PATH,
        "skill_catalog": project_root / SKILL_CATALOG_PATH,
        "architecture_doc": project_root / ARCHITECTURE_DOC_PATH,
        "alignment_model_doc": project_root / ALIGNMENT_MODEL_DOC_PATH,
        "bootstrap_guide": project_root / BOOTSTRAP_GUIDE_PATH,
        "restart_memory_guide": project_root / RESTART_MEMORY_GUIDE_PATH,
        "skills_guide": project_root / SKILLS_GUIDE_PATH,
        "operator_discovery_guide": project_root / OPERATOR_DISCOVERY_GUIDE_PATH,
    }


def load_profile(project_root: Path) -> dict[str, Any]:
    return load_json_object(project_root / PROFILE_PATH)


def load_operator_profile(project_root: Path) -> dict[str, Any]:
    return load_json_object(project_root / OPERATOR_PROFILE_PATH)


def load_partnership_policy(project_root: Path) -> dict[str, Any]:
    return load_json_object(project_root / PARTNERSHIP_POLICY_PATH)


def load_context_routing(project_root: Path) -> dict[str, Any]:
    return load_json_object(project_root / CONTEXT_ROUTING_PATH)


def load_memory_policy(project_root: Path) -> dict[str, Any]:
    return load_json_object(project_root / MEMORY_POLICY_PATH)


def load_skill_catalog(project_root: Path) -> dict[str, Any]:
    return load_json_object(project_root / SKILL_CATALOG_PATH)
