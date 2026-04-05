from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assistant_contracts import (
    ALIGNMENT_MODEL_DOC_PATH,
    ARCHITECTURE_DOC_PATH,
    BOOTSTRAP_GUIDE_PATH,
    CONTEXT_ROUTING_PATH,
    MEMORY_POLICY_PATH,
    OPERATOR_DISCOVERY_GUIDE_PATH,
    OPERATOR_PROFILE_PATH,
    PARTNERSHIP_POLICY_PATH,
    PROFILE_PATH,
    RESTART_MEMORY_GUIDE_PATH,
    SKILL_CATALOG_PATH,
    SKILLS_GUIDE_PATH,
)


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bootstrap_workspace(project_root: Path, target_dir: Path) -> dict[str, Any]:
    target_dir = target_dir.resolve()
    bundle_root = target_dir / "codex-personal-assistant"
    contracts_dir = bundle_root / "contracts"
    prompts_dir = bundle_root / "prompts"
    specs_dir = bundle_root / "docs" / "specs"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    prompts_dir.mkdir(parents=True, exist_ok=True)
    specs_dir.mkdir(parents=True, exist_ok=True)

    copies = [
        (project_root / PROFILE_PATH, contracts_dir / PROFILE_PATH.name),
        (project_root / OPERATOR_PROFILE_PATH, contracts_dir / OPERATOR_PROFILE_PATH.name),
        (project_root / PARTNERSHIP_POLICY_PATH, contracts_dir / PARTNERSHIP_POLICY_PATH.name),
        (project_root / CONTEXT_ROUTING_PATH, contracts_dir / CONTEXT_ROUTING_PATH.name),
        (project_root / MEMORY_POLICY_PATH, contracts_dir / MEMORY_POLICY_PATH.name),
        (project_root / SKILL_CATALOG_PATH, contracts_dir / SKILL_CATALOG_PATH.name),
        (project_root / BOOTSTRAP_GUIDE_PATH, prompts_dir / BOOTSTRAP_GUIDE_PATH.name),
        (project_root / RESTART_MEMORY_GUIDE_PATH, prompts_dir / RESTART_MEMORY_GUIDE_PATH.name),
        (project_root / SKILLS_GUIDE_PATH, prompts_dir / SKILLS_GUIDE_PATH.name),
        (project_root / OPERATOR_DISCOVERY_GUIDE_PATH, prompts_dir / OPERATOR_DISCOVERY_GUIDE_PATH.name),
        (project_root / ARCHITECTURE_DOC_PATH, specs_dir / ARCHITECTURE_DOC_PATH.name),
        (project_root / ALIGNMENT_MODEL_DOC_PATH, specs_dir / ALIGNMENT_MODEL_DOC_PATH.name),
    ]
    copied_paths: list[str] = []
    for source, destination in copies:
        shutil.copy2(source, destination)
        copied_paths.append(str(destination.relative_to(target_dir).as_posix()))

    readme_path = bundle_root / "README.md"
    readme_path.write_text(
        "# Codex Personal Assistant Workspace Preview\n\n"
        "This preview bundle was exported from the PackFactory assistant line.\n"
        "Start with the assistant, operator, and partnership contracts before\n"
        "adapting the bundle to a live Codex home.\n",
        encoding="utf-8",
    )
    copied_paths.append(str(readme_path.relative_to(target_dir).as_posix()))

    report = {
        "schema_version": "codex-personal-assistant-bootstrap-report/v2",
        "generated_at": _isoformat_z(),
        "bundle_root": str(bundle_root.relative_to(target_dir).as_posix()),
        "copied_paths": copied_paths,
    }
    report_path = target_dir / "assistant-bootstrap-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": "pass",
        "bundle_root": str(bundle_root),
        "report_path": str(report_path),
        "copied_paths": copied_paths,
    }


def bootstrap_workspace_in_temp(project_root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp_dir:
        return bootstrap_workspace(project_root, Path(tmp_dir))
