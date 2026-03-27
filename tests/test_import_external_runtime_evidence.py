from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from factory_ops import load_json
from import_external_runtime_evidence import _select_active_memory_candidate


SOURCE_PACK_ID = "release-evidence-summarizer-build-pack-v3"
SOURCE_RUN_ID = "release-evidence-summarizer-loop-002"
TARGET_PACK_ID = "external-runtime-evidence-import-smoke-pack"
SELECTOR_PACK_ID = "json-health-checker-feedback-baseline-build-pack-v1"


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


def _run_importer(factory_root: Path, request_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            str(factory_root / "tools/import_external_runtime_evidence.py"),
            "--factory-root",
            str(factory_root),
            "--request-file",
            str(request_path),
            "--output",
            "json",
        ],
        cwd=factory_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_import_external_runtime_evidence_smoke_success_and_rejects_control_plane_drift(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    materialization_request = factory_root / "materialize-request.json"
    materialization_request.write_text(
        json.dumps(
            {
                "schema_version": "build-pack-materialization-request/v1",
                "source_template_id": "release-evidence-summarizer-template-pack",
                "target_build_pack_id": TARGET_PACK_ID,
                "target_display_name": "External Runtime Evidence Import Smoke Pack",
                "target_version": "0.1.0",
                "target_revision": "import-smoke",
                "materialized_by": "pytest",
                "materialization_reason": "Smoke test source pack for external runtime evidence import",
                "copy_mode": "copy_pack_root",
                "include_benchmark_declarations": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    subprocess.run(
        [
            "python3",
            str(factory_root / "tools/materialize_build_pack.py"),
            "--factory-root",
            str(factory_root),
            "--request-file",
            str(materialization_request),
            "--output",
            "json",
        ],
        cwd=factory_root,
        capture_output=True,
        text=True,
        check=True,
    )

    pack_root = factory_root / "build-packs" / TARGET_PACK_ID
    run_root = pack_root / ".pack-state" / "autonomy-runs" / SOURCE_RUN_ID
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "run-summary.json").write_text(
        json.dumps(
            {
                "schema_version": "autonomy-run-summary/v1",
                "pack_id": TARGET_PACK_ID,
                "run_id": SOURCE_RUN_ID,
                "started_at": "2026-03-23T00:00:00Z",
                "ended_at": "2026-03-23T00:01:00Z",
                "resume_count": 0,
                "escalation_count": 0,
                "stop_reason": "ready_for_deploy_boundary_reached",
                "metrics": {"task_completion_rate": 1.0},
                "final_snapshot": {
                    "readiness_state": "ready_for_deploy",
                    "ready_for_deployment": True,
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_root / "loop-events.jsonl").write_text(
        json.dumps(
            {
                "schema_version": "autonomy-loop-event/v1",
                "run_id": SOURCE_RUN_ID,
                "step_index": 1,
                "event_type": "run_completed",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    exporter = [
        "python3",
        "src/pack_export_runtime_evidence.py",
        "--pack-root",
        ".",
        "--run-id",
        SOURCE_RUN_ID,
        "--exported-by",
        "pytest",
        "--output-dir",
        "dist/exports/runtime-evidence",
        "--output",
        "json",
    ]

    export_result = subprocess.run(exporter, cwd=pack_root, capture_output=True, text=True, check=True)
    export_payload = json.loads(export_result.stdout)
    bundle_root = pack_root / export_payload["bundle_root"]
    bundle_manifest_path = bundle_root / "bundle.json"
    assert bundle_manifest_path.exists()

    readiness_before = load_json(pack_root / "status/readiness.json")
    work_state_before = load_json(pack_root / "status/work-state.json")
    eval_latest_before = load_json(pack_root / "eval/latest/index.json")
    deployment_before = load_json(pack_root / "status/deployment.json")

    request_path = factory_root / "import-request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema_version": "external-runtime-evidence-import-request/v1",
                "build_pack_id": TARGET_PACK_ID,
                "bundle_manifest_path": str(bundle_manifest_path),
                "import_reason": "Smoke test import of external runtime evidence",
                "imported_by": "pytest",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    success_result = _run_importer(factory_root, request_path)
    assert success_result.returncode == 0, success_result.stderr

    import_dirs = sorted(pack_root.glob("eval/history/import-external-runtime-evidence-*"))
    assert import_dirs
    latest_import_dir = import_dirs[-1]
    assert (latest_import_dir / "import-report.json").exists()
    assert (latest_import_dir / "external-runtime-evidence/bundle.json").exists()
    assert load_json(pack_root / "status/readiness.json") == readiness_before
    assert load_json(pack_root / "eval/latest/index.json") == eval_latest_before

    bad_bundle_root = pack_root / "dist/exports/runtime-evidence/bad-bundle"
    shutil.copytree(bundle_root, bad_bundle_root)
    bundle = load_json(bad_bundle_root / "bundle.json")
    bundle["authority_class"] = "canonical_runtime_evidence"
    (bad_bundle_root / "bundle.json").write_text(f"{json.dumps(bundle, indent=2)}\n", encoding="utf-8")

    bad_request_path = factory_root / "bad-import-request.json"
    bad_request_path.write_text(
        json.dumps(
            {
                "schema_version": "external-runtime-evidence-import-request/v1",
                "build_pack_id": TARGET_PACK_ID,
                "bundle_manifest_path": str(bad_bundle_root / "bundle.json"),
                "import_reason": "Smoke test import rejection",
                "imported_by": "pytest",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    before_rejection_dirs = set(pack_root.glob("eval/history/import-external-runtime-evidence-*"))
    failure_result = _run_importer(factory_root, bad_request_path)
    assert failure_result.returncode != 0
    assert set(pack_root.glob("eval/history/import-external-runtime-evidence-*")) == before_rejection_dirs
    assert load_json(pack_root / "status/readiness.json") == readiness_before
    assert load_json(pack_root / "status/work-state.json") == work_state_before
    assert load_json(pack_root / "eval/latest/index.json") == eval_latest_before
    assert load_json(pack_root / "status/deployment.json") == deployment_before


def test_select_active_memory_candidate_skips_expired_memory_and_keeps_fresh_candidate(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    pack_root = factory_root / "build-packs" / SELECTOR_PACK_ID
    readiness = load_json(pack_root / "status/readiness.json")
    work_state = load_json(pack_root / "status/work-state.json")
    memory_root = pack_root / ".pack-state" / "agent-memory"
    shutil.rmtree(memory_root, ignore_errors=True)
    memory_root.mkdir(parents=True, exist_ok=True)

    expired_memory = {
        "schema_version": "autonomy-feedback-memory/v1",
        "memory_id": "autonomy-feedback-expired-001",
        "pack_id": SELECTOR_PACK_ID,
        "run_id": "expired-001",
        "generated_at": "2026-03-20T00:00:00Z",
        "summary": "Expired ready-boundary memory.",
        "memory_validity": {
            "status": "active",
            "confidence_level": "high",
            "confidence_score": 0.9,
            "scope": "ready_boundary_restart",
            "expires_at": "2026-03-20T12:00:00Z",
            "expires_after_hours": 12,
            "basis": ["synthetic_test_memory"],
            "summary": "Expired synthetic test memory."
        },
        "handoff_summary": ["Expired memory should not be selected."],
        "highest_risk_observation": "Expired memory may be stale.",
        "recommended_next_action": "Ignore expired memory.",
        "block_summary": None,
        "resolved_block_summary": None,
        "baseline_readiness_state": readiness["readiness_state"],
        "final_readiness_state": readiness["readiness_state"],
        "active_task_id": work_state.get("active_task_id"),
        "next_recommended_task_id": work_state.get("next_recommended_task_id"),
        "ready_for_deployment": readiness["ready_for_deployment"],
        "completed_task_ids": [],
        "operator_intervention_summary": None,
        "evidence_paths": [],
        "source_artifacts": {
            "loop_events_path": ".pack-state/autonomy-runs/expired-001/loop-events.jsonl",
            "run_summary_path": ".pack-state/autonomy-runs/expired-001/run-summary.json",
            "branch_selection_path": None,
            "previous_memory_path": None,
            "factory_validation_command": None,
        },
    }
    fresh_memory = {
        **expired_memory,
        "memory_id": "autonomy-feedback-fresh-001",
        "run_id": "fresh-001",
        "generated_at": "2026-03-26T11:00:00Z",
        "summary": "Fresh ready-boundary memory.",
        "memory_validity": {
            "status": "active",
            "confidence_level": "high",
            "confidence_score": 0.9,
            "scope": "ready_boundary_restart",
            "expires_at": "2026-03-29T11:00:00Z",
            "expires_after_hours": 72,
            "basis": ["synthetic_test_memory"],
            "summary": "Fresh synthetic test memory."
        },
        "handoff_summary": ["Fresh memory should be selected."],
        "source_artifacts": {
            "loop_events_path": ".pack-state/autonomy-runs/fresh-001/loop-events.jsonl",
            "run_summary_path": ".pack-state/autonomy-runs/fresh-001/run-summary.json",
            "branch_selection_path": None,
            "previous_memory_path": None,
            "factory_validation_command": None,
        },
    }
    (memory_root / "autonomy-feedback-expired-001.json").write_text(json.dumps(expired_memory, indent=2) + "\n", encoding="utf-8")
    (memory_root / "autonomy-feedback-fresh-001.json").write_text(json.dumps(fresh_memory, indent=2) + "\n", encoding="utf-8")

    old_now = os.environ.get("PROJECT_PACK_FACTORY_FIXED_NOW")
    os.environ["PROJECT_PACK_FACTORY_FIXED_NOW"] = "2026-03-26T12:00:00Z"
    try:
        selected = _select_active_memory_candidate(pack_root, SELECTOR_PACK_ID)
    finally:
        if old_now is None:
            os.environ.pop("PROJECT_PACK_FACTORY_FIXED_NOW", None)
        else:
            os.environ["PROJECT_PACK_FACTORY_FIXED_NOW"] = old_now

    assert selected is not None
    selected_path, selected_payload, _selected_sha = selected
    assert selected_path.name == "autonomy-feedback-fresh-001.json"
    assert selected_payload["memory_id"] == "autonomy-feedback-fresh-001"
