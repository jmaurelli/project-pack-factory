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
    optional_local_paths: set[str] = set()
    if isinstance(directory_contract, dict):
        local_state_dir = directory_contract.get("local_state_dir")
        if isinstance(local_state_dir, str):
            optional_local_paths.add(local_state_dir)
        required_paths.extend(
            value
            for value in directory_contract.values()
            if isinstance(value, str)
            and value not in optional_local_paths
        )

    checked_paths = sorted(
        {
            *required_paths,
            *(
                relative_path
                for relative_path in optional_local_paths
                if (project_root / relative_path).exists()
            ),
        }
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
        "checked_paths": checked_paths,
        "missing_paths": missing,
    }
