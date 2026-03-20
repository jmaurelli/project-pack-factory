from __future__ import annotations

import json
import sys
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _src() -> Path:
    return _root() / "src"


def test_framework_profile_catalog_declares_existing_default_profile() -> None:
    catalog = json.loads(
        (_root() / "src" / "ai_native_package" / "contracts" / "framework-profiles.json").read_text(encoding="utf-8")
    )
    profile_ids = {profile["profile_id"] for profile in catalog["profiles"]}
    assert catalog["default_profile"] in profile_ids
    assert (_root() / "docs" / "framework-profiles" / "python-cli-click.md").exists()


def test_validate_project_pack_reports_missing_framework_profile_doc(tmp_path: Path) -> None:
    sys.path.insert(0, str(_src()))
    from ai_native_package.validators.validate_project_pack import validate_project_pack

    (tmp_path / "src" / "ai_native_package" / "contracts").mkdir(parents=True)
    for rel in [
        "src/ai_native_package/contracts/project-pack.contract.json",
        "src/ai_native_package/contracts/doc-update-record.schema.json",
        "src/ai_native_package/contracts/framework-profiles.json",
        "docs/doc-update-record.json",
        "README.md",
        "AGENTS.md",
        "project-context.md",
        "docs/benchmark-first-task.md",
        "pyproject.toml",
    ]:
        src = _root() / rel
        dst = tmp_path / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    payload = validate_project_pack(
        project_root=tmp_path,
        contract_path=tmp_path / "src" / "ai_native_package" / "contracts" / "project-pack.contract.json",
    )
    assert payload["result"] == "fail"
    assert any(error["check"] == "framework_profiles" for error in payload["errors"])
