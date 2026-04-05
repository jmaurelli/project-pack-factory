from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validate_project_pack(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "pack.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    required_paths = ["AGENTS.md", "project-context.md", "pack.json"]
    required_paths.extend(manifest.get("post_bootstrap_read_order", []))

    directory_contract = manifest.get("directory_contract", {})
    if isinstance(directory_contract, dict):
        required_paths.extend(
            value
            for value in directory_contract.values()
            if isinstance(value, str)
        )

    missing = sorted(
        relative_path
        for relative_path in set(required_paths)
        if not (project_root / relative_path).exists()
    )
    status = "pass" if not missing else "fail"
    return {
        "status": status,
        "project_root": str(project_root),
        "pack_id": manifest.get("pack_id"),
        "pack_kind": manifest.get("pack_kind"),
        "checked_paths": sorted(set(required_paths)),
        "missing_paths": missing,
    }
