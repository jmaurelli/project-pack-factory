from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from materialize_build_pack import materialize_build_pack
from run_deployment_pipeline import run_deployment_pipeline
from factory_ops import load_json, write_json


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


def _prepare_build_pack(factory_root: Path, *, validation_command: str = "python -c \"print('ok')\"", benchmark_command: str = "python -c \"print('bench')\"") -> Path:
    materialize_build_pack(
        factory_root,
        {
            "schema_version": "build-pack-materialization-request/v1",
            "source_template_id": "agent-memory-first-template-pack",
            "target_build_pack_id": "pipeline-pack",
            "target_display_name": "Pipeline Test Pack",
            "target_version": "0.1.0",
            "target_revision": "test-revision",
            "materialized_by": "pytest",
            "materialization_reason": "Test materialization",
            "copy_mode": "copy_pack_root",
            "include_benchmark_declarations": True,
        },
    )
    pack_root = factory_root / "build-packs/pipeline-pack"
    pack = load_json(pack_root / "pack.json")
    pack["entrypoints"]["validation_command"] = validation_command
    pack["entrypoints"]["benchmark_command"] = benchmark_command
    write_json(pack_root / "pack.json", pack)

    readiness = load_json(pack_root / "status/readiness.json")
    readiness["readiness_state"] = "ready_for_deploy"
    readiness["ready_for_deployment"] = True
    readiness["blocking_issues"] = []
    for gate in readiness["required_gates"]:
        gate["status"] = "pass"
        gate["last_run_at"] = "2026-03-20T00:00:00Z"
        gate["evidence_paths"] = ["eval/history/bootstrap/pass.json"]
    write_json(pack_root / "status/readiness.json", readiness)
    return pack_root


def _request(*, commit: bool, verification_commands: list[str] | None = None) -> dict[str, object]:
    return {
        "schema_version": "deployment-pipeline-request/v1",
        "build_pack_id": "pipeline-pack",
        "target_environment": "testing",
        "release_id": "pipe-r1",
        "cloud_adapter_id": "local-test-adapter",
        "invoked_by": "pytest",
        "commit_promotion_on_success": commit,
        "validation_command_ref": "pack.json.entrypoints.validation_command",
        "benchmark_source": "status/readiness.json.required_gates",
        "verification_commands": verification_commands or ["python -c \"print('verify')\""],
        "secret_refs": [],
    }


def test_run_deployment_pipeline_happy_path_without_commit(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    _prepare_build_pack(factory_root)

    result = run_deployment_pipeline(factory_root, _request(commit=False))

    assert result["status"] == "completed"
    assert (factory_root / "build-packs/pipeline-pack/dist/candidates/pipe-r1/release.json").exists()
    assert (factory_root / "build-packs/pipeline-pack/dist/releases/pipe-r1/release.json").exists()
    assert not (factory_root / "deployments/testing/pipeline-pack.json").exists()
    report = load_json(Path(result["pipeline_report_path"]))
    assert report["stage_results"][6]["status"] == "completed"
    assert any(path.endswith("validation-result.json") for path in report["evidence_paths"])
    assert any(path.endswith("benchmark-result.json") for path in report["evidence_paths"])
    assert any(path.endswith("verification-result.json") for path in report["evidence_paths"])


def test_run_deployment_pipeline_happy_path_with_commit_promotes_build_pack(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    _prepare_build_pack(factory_root)

    result = run_deployment_pipeline(factory_root, _request(commit=True))

    assert result["status"] == "completed"
    assert (factory_root / "deployments/testing/pipeline-pack.json").exists()
    deployment = load_json(factory_root / "build-packs/pipeline-pack/status/deployment.json")
    assert deployment["deployment_state"] == "testing"


def test_run_deployment_pipeline_fails_on_validation_command_and_skips_later_stages(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    _prepare_build_pack(factory_root, validation_command="python -c \"import sys; sys.exit(1)\"")

    result = run_deployment_pipeline(factory_root, _request(commit=False))

    assert result["status"] == "failed"
    report = load_json(Path(result["pipeline_report_path"]))
    assert report["adapter_result"] is None
    assert report["stage_results"][1]["status"] == "failed"
    assert report["stage_results"][2]["status"] == "skipped"


def test_run_deployment_pipeline_appends_pipeline_log_event(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    _prepare_build_pack(factory_root)

    run_deployment_pipeline(factory_root, _request(commit=False))

    promotion_log = load_json(factory_root / "registry/promotion-log.json")
    assert any(event.get("event_type") == "pipeline_executed" and event.get("build_pack_id") == "pipeline-pack" for event in promotion_log["events"])
