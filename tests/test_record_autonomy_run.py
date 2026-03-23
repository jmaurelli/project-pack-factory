from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from factory_ops import load_json
from record_autonomy_run import append_event, finalize_run, start_run


SOURCE_PACK_ID = "release-evidence-summarizer-build-pack-v2"


def _copy_factory(tmp_path: Path) -> Path:
    destination = tmp_path / "factory"

    def _ignore(_dir: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
            or name.endswith(".egg-info")
        }

    shutil.copytree(ROOT, destination, ignore=_ignore)
    return destination


def test_record_autonomy_run_happy_path(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    pack_root = factory_root / "build-packs" / SOURCE_PACK_ID
    os.environ["PROJECT_PACK_FACTORY_FIXED_NOW"] = "2026-03-23T03:00:00Z"
    try:
        start_payload = start_run(
            pack_root=pack_root,
            run_id="loop-run-001",
            notes=[],
            factory_root=factory_root,
        )
        run_root = Path(start_payload["run_root"])
        summary_path = run_root / "run-summary.json"
        events_path = run_root / "loop-events.jsonl"

        assert events_path.exists()
        assert not summary_path.exists()

        append_payload = append_event(
            pack_root=pack_root,
            run_id="loop-run-001",
            event_type="task_selected",
            outcome="selected",
            decision_source="canonical_only",
            memory_state="not_used",
            commands_attempted=[],
            notes=["Selected the canonical task from status/work-state.json."],
            evidence_paths=[],
            stop_reason=None,
            active_task_id="run_build_pack_validation",
            next_recommended_task_id="run_build_pack_validation",
            factory_root=factory_root,
        )
        assert append_payload["step_index"] == 2

        finalize_payload = finalize_run(
            pack_root=pack_root,
            run_id="loop-run-001",
            schema_factory_root=factory_root,
            validation_factory_root=factory_root,
        )
        assert finalize_payload["schema_version"] == "autonomy-run-summary/v1"
        assert finalize_payload["run_id"] == "loop-run-001"

        summary = load_json(summary_path)
        assert summary["schema_version"] == "autonomy-run-summary/v1"
        assert summary["step_count"] == 2
        assert summary["metrics"]["task_completion_rate"] == 0
        assert summary["metrics"]["validation_evidence_gain"] is False
        assert summary["metrics"]["benchmark_evidence_gain"] is False
        assert summary["metrics"]["canonical_state_integrity"]["status"] == "pass"
        assert summary["recommended_next_action"].endswith("`run_build_pack_validation` from status/work-state.json and use this summary as local measurement evidence only.")
    finally:
        os.environ.pop("PROJECT_PACK_FACTORY_FIXED_NOW", None)
