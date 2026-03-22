from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from materialize_build_pack import materialize_build_pack
from promote_build_pack import promote_build_pack
from factory_ops import load_json, write_json
from validate_factory import validate_factory


SOURCE_TEMPLATE_ID = "factory-native-smoke-template-pack"


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
    _reset_canonical_assignments(destination)
    _normalize_active_build_pack_evidence(destination)
    return destination


def _materialize(factory_root: Path, pack_id: str = "promo-pack") -> Path:
    materialize_build_pack(
        factory_root,
        {
            "schema_version": "build-pack-materialization-request/v1",
            "source_template_id": SOURCE_TEMPLATE_ID,
            "target_build_pack_id": pack_id,
            "target_display_name": "Promotion Test Pack",
            "target_version": "0.1.0",
            "target_revision": "test-revision",
            "materialized_by": "pytest",
            "materialization_reason": "Test materialization",
            "copy_mode": "copy_pack_root",
            "include_benchmark_declarations": True,
        },
    )
    pack_root = factory_root / "build-packs" / pack_id
    _seed_integrity_evidence(pack_root)
    release = {
        "schema_version": "pack-release/v1",
        "build_pack_id": pack_id,
        "release_id": "r1",
        "source_template_id": SOURCE_TEMPLATE_ID,
        "source_template_revision": "test-revision",
        "built_at": "2026-03-20T00:00:00Z",
        "release_state": "testing",
        "artifact_paths": ["src/"],
    }
    write_json(pack_root / "dist/releases/r1/release.json", release)
    write_json(pack_root / "dist/candidates/r1/release.json", release)
    return pack_root


def _request(env: str, release_id: str = "r1", pack_id: str = "promo-pack") -> dict[str, object]:
    return {
        "schema_version": "build-pack-promotion-request/v1",
        "build_pack_id": pack_id,
        "target_environment": env,
        "release_id": release_id,
        "promoted_by": "pytest",
        "promotion_reason": f"Promote to {env}",
        "verification_timestamp": "2026-03-20T00:00:00Z",
    }


def _reset_canonical_assignments(factory_root: Path) -> None:
    for environment in ("testing", "staging", "production"):
        deployment_dir = factory_root / "deployments" / environment
        for pointer in deployment_dir.glob("*.json"):
            pointer.unlink()

    registry = load_json(factory_root / "registry/build-packs.json")
    for entry in registry["entries"]:
        entry["deployment_state"] = "not_deployed"
        entry["deployment_pointer"] = None
        entry["active_release_id"] = None
    write_json(factory_root / "registry/build-packs.json", registry)

    for pack_root in (factory_root / "build-packs").iterdir():
        if not pack_root.is_dir():
            continue
        deployment_path = pack_root / "status/deployment.json"
        if not deployment_path.exists():
            continue
        deployment = load_json(deployment_path)
        deployment["deployment_state"] = "not_deployed"
        deployment["active_environment"] = "none"
        deployment["active_release_id"] = None
        deployment["active_release_path"] = None
        deployment["deployment_pointer_path"] = None
        deployment["deployment_transaction_id"] = None
        deployment["projection_state"] = "not_required"
        deployment["last_promoted_at"] = None
        deployment["last_verified_at"] = None
        write_json(deployment_path, deployment)


def test_promote_build_pack_happy_path_writes_pointer_and_updates_registry(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    _materialize(factory_root)

    result = promote_build_pack(factory_root, _request("testing"))

    assert result["status"] == "completed"
    pointer_path = factory_root / "deployments/testing/promo-pack.json"
    assert pointer_path.exists()
    deployment = load_json(factory_root / "build-packs/promo-pack/status/deployment.json")
    assert deployment["deployment_state"] == "testing"
    registry = load_json(factory_root / "registry/build-packs.json")
    assert next(entry for entry in registry["entries"] if entry["pack_id"] == "promo-pack")["deployment_pointer"] == "deployments/testing/promo-pack.json"


def test_promote_build_pack_rejects_when_latest_eval_is_missing(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    pack_root = _materialize(factory_root)
    readiness = load_json(pack_root / "status/readiness.json")
    validation_gate = next(gate for gate in readiness["required_gates"] if gate["gate_id"] == "validate_build_pack_contract")
    validation_gate["evidence_paths"] = ["eval/history/bootstrap/benchmark-result.json"]
    write_json(pack_root / "status/readiness.json", readiness)
    try:
        promote_build_pack(factory_root, _request("testing"))
    except ValueError as exc:
        assert "readiness evidence integrity failed" in str(exc)
    else:
        raise AssertionError("expected promotion to fail when readiness evidence is corrupted")

    _seed_integrity_evidence(pack_root)
    (factory_root / "build-packs/promo-pack/eval/latest/index.json").unlink()
    try:
        promote_build_pack(factory_root, _request("testing"))
    except ValueError as exc:
        assert "eval/latest/index.json" in str(exc)
    else:
        raise AssertionError("expected promotion to fail when latest eval evidence is missing")


def test_promote_build_pack_eviction_clears_prior_environment_assignment(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    _reset_canonical_assignments(factory_root)
    _materialize(factory_root, "alpha-pack")
    _materialize(factory_root, "beta-pack")
    shutil.rmtree(factory_root / "build-packs/alpha-pack/.pack-state", ignore_errors=True)

    promote_build_pack(factory_root, _request("testing", pack_id="alpha-pack"))
    result = promote_build_pack(factory_root, _request("testing", pack_id="beta-pack"))

    assert result["status"] == "completed"
    assert not (factory_root / "deployments/testing/alpha-pack.json").exists()
    assert (factory_root / "deployments/testing/beta-pack.json").exists()

    alpha_deployment = load_json(factory_root / "build-packs/alpha-pack/status/deployment.json")
    assert alpha_deployment["deployment_state"] == "not_deployed"
    assert alpha_deployment["active_environment"] == "none"
    assert alpha_deployment["deployment_pointer_path"] is None

    registry = load_json(factory_root / "registry/build-packs.json")
    alpha_entry = next(entry for entry in registry["entries"] if entry["pack_id"] == "alpha-pack")
    beta_entry = next(entry for entry in registry["entries"] if entry["pack_id"] == "beta-pack")
    assert alpha_entry["deployment_state"] == "not_deployed"
    assert alpha_entry["deployment_pointer"] is None
    assert alpha_entry["active_release_id"] is None
    assert beta_entry["deployment_pointer"] == "deployments/testing/beta-pack.json"

    report = load_json(Path(result["promotion_report_path"]))
    assert report["evicted_prior_assignment"]["pack_id"] == "alpha-pack"
    assert report["evicted_prior_assignment"]["removed_pointer_path"] == "deployments/testing/alpha-pack.json"
    assert validate_factory(factory_root)["valid"] is True


def test_validate_factory_rejects_split_brain_environment_assignments(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    _reset_canonical_assignments(factory_root)
    _materialize(factory_root, "alpha-pack")
    _materialize(factory_root, "beta-pack")

    promote_build_pack(factory_root, _request("testing", pack_id="alpha-pack"))
    alpha_pointer_payload = load_json(factory_root / "deployments/testing/alpha-pack.json")
    promote_build_pack(factory_root, _request("testing", pack_id="beta-pack"))

    write_json(factory_root / "deployments/testing/alpha-pack.json", alpha_pointer_payload)
    alpha_deployment = load_json(factory_root / "build-packs/alpha-pack/status/deployment.json")
    alpha_deployment["deployment_state"] = "testing"
    alpha_deployment["active_environment"] = "testing"
    alpha_deployment["active_release_id"] = alpha_pointer_payload["active_release_id"]
    alpha_deployment["active_release_path"] = alpha_pointer_payload["active_release_path"]
    alpha_deployment["deployment_pointer_path"] = "deployments/testing/alpha-pack.json"
    alpha_deployment["deployment_transaction_id"] = alpha_pointer_payload["deployment_transaction_id"]
    write_json(factory_root / "build-packs/alpha-pack/status/deployment.json", alpha_deployment)

    registry = load_json(factory_root / "registry/build-packs.json")
    alpha_entry = next(entry for entry in registry["entries"] if entry["pack_id"] == "alpha-pack")
    alpha_entry["deployment_state"] = "testing"
    alpha_entry["deployment_pointer"] = "deployments/testing/alpha-pack.json"
    alpha_entry["active_release_id"] = alpha_pointer_payload["active_release_id"]
    write_json(factory_root / "registry/build-packs.json", registry)

    result = validate_factory(factory_root)

    assert result["valid"] is False
    assert any("multiple active deployment pointers" in error for error in result["errors"])
    assert any("registry claims must resolve" in error for error in result["errors"])
    assert any("pack-local claims must resolve" in error for error in result["errors"])
