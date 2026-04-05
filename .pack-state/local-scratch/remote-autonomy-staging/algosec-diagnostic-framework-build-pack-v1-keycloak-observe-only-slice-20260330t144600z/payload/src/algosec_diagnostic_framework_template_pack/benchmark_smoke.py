from __future__ import annotations

from pathlib import Path
from typing import Any

from .runtime_baseline import (
    RUNTIME_EVIDENCE_NAME,
    SERVICE_INVENTORY_NAME,
    SUPPORT_BASELINE_HTML_NAME,
    SUPPORT_BASELINE_NAME,
    generate_support_baseline,
)


def benchmark_smoke(project_root: Path) -> dict[str, Any]:
    manifest_path = project_root / "pack.json"
    readiness_path = project_root / "status/readiness.json"
    benchmark_path = project_root / "benchmarks/active-set.json"
    artifact_root = Path("dist/candidates/benchmark-smoke-baseline")

    missing = [
        str(path.relative_to(project_root))
        for path in (manifest_path, readiness_path, benchmark_path)
        if not path.exists()
    ]
    generated_result = None
    generated_files: list[str] = []
    if not missing:
        generated_result = generate_support_baseline(
            project_root=project_root,
            target_label="benchmark-smoke",
            artifact_root=artifact_root,
        )
        expected_artifacts = [
            artifact_root / RUNTIME_EVIDENCE_NAME,
            artifact_root / SERVICE_INVENTORY_NAME,
            artifact_root / SUPPORT_BASELINE_NAME,
            artifact_root / SUPPORT_BASELINE_HTML_NAME,
        ]
        missing.extend(
            str(path)
            for path in expected_artifacts
            if not (project_root / path).exists()
        )
        generated_files = [str(path) for path in expected_artifacts]

    return {
        "status": "pass" if not missing else "fail",
        "project_root": str(project_root),
        "benchmark_id": "algosec-diagnostic-framework-template-pack-smoke-small-001",
        "checked_paths": [
            "pack.json",
            "status/readiness.json",
            "benchmarks/active-set.json",
            *generated_files,
        ],
        "generated_result": generated_result,
        "missing_paths": missing,
    }
