from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from factory_ops import load_json


SOURCE_PACK_ID = "release-evidence-summarizer-build-pack-v3"
SOURCE_RUN_ID = "release-evidence-summarizer-loop-002"
TARGET_PACK_ID = "external-runtime-evidence-import-smoke-pack"


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
