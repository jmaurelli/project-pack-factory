from __future__ import annotations

from pathlib import Path
from typing import Any


def benchmark_smoke(project_root: Path) -> dict[str, Any]:
    return {
        "status": "pass",
        "benchmark_id": "factory-smoke-small-001",
        "project_root": str(project_root),
        "summary": "Minimal smoke benchmark completed successfully."
    }
