from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .alignment import show_alignment
from .context_router import route_context
from .doctor import run_doctor
from .memory import read_memory, record_memory
from .profile import show_profile
from .validate_project_pack import validate_project_pack
from .workspace_bootstrap import bootstrap_workspace


def benchmark_smoke(project_root: Path) -> dict[str, Any]:
    validation = validate_project_pack(project_root)
    profile = show_profile(project_root)
    alignment = show_alignment(project_root)
    routing = route_context(project_root, "goals")
    doctor = run_doctor(project_root)

    memory_path = project_root / ".pack-state/assistant-memory/benchmark-smoke-memory.json"
    latest_pointer = project_root / ".pack-state/assistant-memory/latest-memory.json"
    previous_memory_text = memory_path.read_text(encoding="utf-8") if memory_path.exists() else None
    previous_pointer_text = latest_pointer.read_text(encoding="utf-8") if latest_pointer.exists() else None
    memory_write = record_memory(
        project_root,
        memory_id="benchmark-smoke-memory",
        category="communication_pattern",
        summary="Smoke benchmark confirmed operator-alignment assistant surfaces.",
        next_action="Use doctor and PackFactory validation before wider rollout.",
        tags=["benchmark", "smoke"],
        replace_existing=True,
        source="benchmark_smoke",
        evidence="automated benchmark smoke run",
        confidence=1.0,
    )
    memory_snapshot = read_memory(project_root)
    with tempfile.TemporaryDirectory() as tmp_dir:
        bootstrap_result = bootstrap_workspace(project_root, Path(tmp_dir))

    if previous_memory_text is None:
        if memory_path.exists():
            memory_path.unlink()
    else:
        memory_path.write_text(previous_memory_text, encoding="utf-8")
    if previous_pointer_text is None:
        if latest_pointer.exists():
            latest_pointer.unlink()
    else:
        latest_pointer.write_text(previous_pointer_text, encoding="utf-8")

    checks = {
        "validation": validation["status"],
        "show_profile": profile["status"],
        "show_alignment": alignment["status"],
        "route_context": routing["status"],
        "record_memory": memory_write["status"],
        "read_memory": memory_snapshot["status"],
        "bootstrap_workspace": bootstrap_result["status"],
        "doctor": doctor["status"],
    }
    failed_checks = sorted(name for name, status in checks.items() if status != "pass")

    return {
        "status": "pass" if not failed_checks else "fail",
        "project_root": str(project_root),
        "benchmark_id": "codex-personal-assistant-template-pack-smoke-small-001",
        "checks": checks,
        "failed_checks": failed_checks,
        "matched_route": routing.get("matched_route"),
        "memory_count_after_write": memory_snapshot.get("memory_count"),
        "doctor_errors": doctor.get("errors", []),
    }
