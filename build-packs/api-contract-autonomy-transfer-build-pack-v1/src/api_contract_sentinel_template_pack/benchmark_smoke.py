from __future__ import annotations

from pathlib import Path
from typing import Any


def benchmark_smoke(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "pack.json"
    readiness_path = project_root / "status/readiness.json"
    benchmark_path = project_root / "benchmarks/active-set.json"

    missing = [
        str(path.relative_to(project_root))
        for path in (manifest_path, readiness_path, benchmark_path)
        if not path.exists()
    ]

    return {
        "status": "pass" if not missing else "fail",
        "project_root": str(project_root),
        "benchmark_id": "api-contract-sentinel-template-pack-smoke-small-001",
        "checked_paths": [
            "pack.json",
            "status/readiness.json",
            "benchmarks/active-set.json",
        ],
        "missing_paths": missing,
    }
