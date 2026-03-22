from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from materialize_build_pack import materialize_build_pack
from run_deployment_pipeline import run_deployment_pipeline
from factory_ops import load_json, write_json
from validate_factory import validate_factory


def _seed_integrity_evidence(pack_root: Path, *, run_id: str = "bootstrap") -> None:
    generated_at = "2026-03-20T00:00:00Z"
    readiness = load_json(pack_root / "status/readiness.json")
    eval_latest = load_json(pack_root / "eval/latest/index.json")
    benchmark_results = [
        {
            "benchmark_id": result["benchmark_id"],
            "status": "pass",
        }
        for result in eval_latest.get("benchmark_results", [])
        if isinstance(result, dict) and isinstance(result.get("benchmark_id"), str)
    ]
    run_dir = pack_root / "eval/history" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    validation_relative = f"eval/history/{run_id}/validation-result.json"
    benchmark_relative = f"eval/history/{run_id}/benchmark-result.json"
    write_json(
        pack_root / validation_relative,
        {
            "build_pack_id": pack_root.name,
            "gate_id": "validate_build_pack_contract",
            "status": "pass",
            "command": "python3 -c \"print('ok')\"",
            "returncode": 0,
            "stdout": "ok\n",
            "stderr": "",
        },
    )
    write_json(
        pack_root / benchmark_relative,
        {
            "build_pack_id": pack_root.name,
            "status": "pass",
            "benchmark_results": benchmark_results,
            "command": "python3 -c \"print('bench')\"",
            "mandatory_gate_ids": [
                gate["gate_id"]
                for gate in readiness.get("required_gates", [])
                if isinstance(gate, dict)
                and gate.get("mandatory") is True
                and gate.get("gate_id") != "validate_build_pack_contract"
            ],
            "returncode": 0,
            "stdout": "bench\n",
            "stderr": "",
        },
    )

    eval_latest["updated_at"] = generated_at
    for result in eval_latest.get("benchmark_results", []):
        if not isinstance(result, dict):
            continue
        result["status"] = "pass"
        result["latest_run_id"] = run_id
        result["run_artifact_path"] = benchmark_relative
        result["summary_artifact_path"] = benchmark_relative
    write_json(pack_root / "eval/latest/index.json", eval_latest)

    readiness["readiness_state"] = "ready_for_deploy"
    readiness["ready_for_deployment"] = True
    readiness["last_evaluated_at"] = generated_at
    readiness["blocking_issues"] = []
    for gate in readiness.get("required_gates", []):
        if not isinstance(gate, dict):
            continue
        gate["status"] = "pass"
        gate["last_run_at"] = generated_at
        if gate.get("gate_id") == "validate_build_pack_contract":
            gate["evidence_paths"] = [validation_relative]
        else:
            gate["evidence_paths"] = ["eval/latest/index.json"]
    write_json(pack_root / "status/readiness.json", readiness)


def _normalize_active_build_pack_evidence(factory_root: Path) -> None:
    build_packs_root = factory_root / "build-packs"
    for pack_root in build_packs_root.iterdir():
        if not pack_root.is_dir() or not (pack_root / "pack.json").exists():
            continue
        retirement = load_json(pack_root / "status/retirement.json")
        if retirement.get("retirement_state") != "active":
            continue
        _seed_integrity_evidence(pack_root, run_id=f"bootstrap-{pack_root.name}")


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
    _normalize_active_build_pack_evidence(destination)
    return destination


def _prepare_build_pack(factory_root: Path, *, validation_command: str = "python3 -c \"print('ok')\"", benchmark_command: str = "python3 -c \"print('bench')\"") -> Path:
    materialize_build_pack(
        factory_root,
        {
            "schema_version": "build-pack-materialization-request/v1",
            "source_template_id": "factory-native-smoke-template-pack",
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
    benchmark_id = load_json(pack_root / "eval/latest/index.json")["benchmark_results"][0]["benchmark_id"]
    pack = load_json(pack_root / "pack.json")
    pack["entrypoints"]["validation_command"] = validation_command
    if benchmark_command == "python3 -c \"print('bench')\"":
        benchmark_command = (
            "python3 -c "
            f"\"import json; print(json.dumps({{'benchmark_id': '{benchmark_id}', 'status': 'pass'}}))\""
        )
    pack["entrypoints"]["benchmark_command"] = benchmark_command
    write_json(pack_root / "pack.json", pack)
    _seed_integrity_evidence(pack_root)
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
        "verification_commands": verification_commands or ["python3 -c \"print('verify')\""],
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

    first_result = run_deployment_pipeline(factory_root, _request(commit=True))

    assert first_result["status"] == "completed"
    assert (factory_root / "deployments/testing/pipeline-pack.json").exists()
    deployment = load_json(factory_root / "build-packs/pipeline-pack/status/deployment.json")
    assert deployment["deployment_state"] == "testing"

    release_path = factory_root / "build-packs/pipeline-pack/dist/releases/pipe-r1/release.json"
    candidate_path = factory_root / "build-packs/pipeline-pack/dist/candidates/pipe-r1/release.json"
    release_snapshot = release_path.read_bytes()
    candidate_snapshot = candidate_path.read_bytes()

    second_result = run_deployment_pipeline(factory_root, _request(commit=True))

    assert second_result["status"] == "reconciled"
    assert release_path.read_bytes() == release_snapshot
    assert candidate_path.read_bytes() == candidate_snapshot


def test_run_deployment_pipeline_fails_on_validation_command_and_skips_later_stages(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    _prepare_build_pack(factory_root, validation_command="python3 -c \"import sys; sys.exit(1)\"")

    result = run_deployment_pipeline(factory_root, _request(commit=False))

    assert result["status"] == "failed"
    report = load_json(Path(result["pipeline_report_path"]))
    assert report["adapter_result"] is None
    assert report["stage_results"][1]["status"] == "failed"
    assert report["stage_results"][2]["status"] == "skipped"


def test_run_deployment_pipeline_writes_integrity_aligned_evidence_and_log_event(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    pack_root = _prepare_build_pack(
        factory_root,
        benchmark_command=(
            "python3 -c "
            "\"import json; print(json.dumps({'benchmark_id': 'wrong-benchmark', 'status': 'pass'}))\""
        ),
    )

    failed_result = run_deployment_pipeline(factory_root, _request(commit=False))
    failed_report = load_json(Path(failed_result["pipeline_report_path"]))
    assert failed_result["status"] == "failed"
    assert failed_report["stage_results"][2]["status"] == "failed"

    benchmark_id = load_json(pack_root / "eval/latest/index.json")["benchmark_results"][0]["benchmark_id"]
    pack = load_json(pack_root / "pack.json")
    pack["entrypoints"]["benchmark_command"] = (
        "python3 -c "
        f"\"import json; print(json.dumps({{'benchmark_id': '{benchmark_id}', 'status': 'pass'}}))\""
    )
    write_json(pack_root / "pack.json", pack)

    result = run_deployment_pipeline(factory_root, _request(commit=False))

    promotion_log = load_json(factory_root / "registry/promotion-log.json")
    assert any(event.get("event_type") == "pipeline_executed" and event.get("build_pack_id") == "pipeline-pack" for event in promotion_log["events"])
    pack_root = factory_root / "build-packs/pipeline-pack"
    readiness = load_json(pack_root / "status/readiness.json")
    validation_gate = next(gate for gate in readiness["required_gates"] if gate["gate_id"] == "validate_build_pack_contract")
    benchmark_gate = next(gate for gate in readiness["required_gates"] if gate["gate_id"] != "validate_build_pack_contract")
    expected_validation_path = f"eval/history/{result['pipeline_id']}/validation-result.json"
    expected_benchmark_path = f"eval/history/{result['pipeline_id']}/benchmark-result.json"
    assert validation_gate["evidence_paths"] == [expected_validation_path]
    assert benchmark_gate["evidence_paths"] == ["eval/latest/index.json"]

    eval_latest = load_json(pack_root / "eval/latest/index.json")
    benchmark_result = eval_latest["benchmark_results"][0]
    assert benchmark_result["latest_run_id"] == result["pipeline_id"]
    assert benchmark_result["run_artifact_path"] == expected_benchmark_path
    assert benchmark_result["summary_artifact_path"] == expected_benchmark_path

    validation_artifact = load_json(pack_root / expected_validation_path)
    assert validation_artifact["gate_id"] == "validate_build_pack_contract"
    assert validation_artifact["status"] == "pass"

    benchmark_artifact = load_json(pack_root / expected_benchmark_path)
    assert any(
        entry["benchmark_id"] == benchmark_result["benchmark_id"] and entry["status"] == "pass"
        for entry in benchmark_artifact["benchmark_results"]
    )
    assert validate_factory(factory_root)["valid"] is True
