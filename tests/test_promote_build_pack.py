from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from materialize_build_pack import materialize_build_pack
from promote_build_pack import promote_build_pack
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


def _materialize(factory_root: Path, pack_id: str = "promo-pack") -> Path:
    materialize_build_pack(
        factory_root,
        {
            "schema_version": "build-pack-materialization-request/v1",
            "source_template_id": "agent-memory-first-template-pack",
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
    readiness = load_json(pack_root / "status/readiness.json")
    readiness["readiness_state"] = "ready_for_deploy"
    readiness["ready_for_deployment"] = True
    readiness["blocking_issues"] = []
    for gate in readiness["required_gates"]:
        gate["status"] = "pass"
        gate["last_run_at"] = "2026-03-20T00:00:00Z"
        gate["evidence_paths"] = ["eval/history/bootstrap/pass.json"]
    write_json(pack_root / "status/readiness.json", readiness)
    eval_latest = load_json(pack_root / "eval/latest/index.json")
    for result in eval_latest["benchmark_results"]:
        result["status"] = "pass"
    write_json(pack_root / "eval/latest/index.json", eval_latest)
    release = {
        "schema_version": "pack-release/v1",
        "build_pack_id": pack_id,
        "release_id": "r1",
        "source_template_id": "agent-memory-first-template-pack",
        "source_template_revision": "test-revision",
        "built_at": "2026-03-20T00:00:00Z",
        "release_state": "testing",
        "artifact_paths": ["src/"],
    }
    write_json(pack_root / "dist/releases/r1/release.json", release)
    write_json(pack_root / "dist/candidates/r1/release.json", release)
    return pack_root


def _request(env: str, release_id: str = "r1") -> dict[str, object]:
    return {
        "schema_version": "build-pack-promotion-request/v1",
        "build_pack_id": "promo-pack",
        "target_environment": env,
        "release_id": release_id,
        "promoted_by": "pytest",
        "promotion_reason": f"Promote to {env}",
        "verification_timestamp": "2026-03-20T00:00:00Z",
    }


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
    _materialize(factory_root)
    (factory_root / "build-packs/promo-pack/eval/latest/index.json").unlink()
    try:
        promote_build_pack(factory_root, _request("testing"))
    except ValueError as exc:
        assert "eval/latest/index.json" in str(exc)
    else:
        raise AssertionError("expected promotion to fail when latest eval evidence is missing")


def test_promote_build_pack_reconciles_same_environment_and_release(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    _materialize(factory_root)

    promote_build_pack(factory_root, _request("testing"))
    promotion_log_before = load_json(factory_root / "registry/promotion-log.json")
    promoted_before = sum(1 for event in promotion_log_before["events"] if event.get("event_type") == "promoted")

    result = promote_build_pack(factory_root, _request("testing"))

    assert result["status"] == "reconciled"
    promotion_log_after = load_json(factory_root / "registry/promotion-log.json")
    promoted_after = sum(1 for event in promotion_log_after["events"] if event.get("event_type") == "promoted")
    assert promoted_after == promoted_before


def test_promote_build_pack_moves_from_testing_to_staging_and_removes_stale_pointer(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    pack_root = _materialize(factory_root)

    promote_build_pack(factory_root, _request("testing"))
    write_json(pack_root / "dist/releases/r2/release.json", load_json(pack_root / "dist/releases/r1/release.json") | {"release_id": "r2", "release_state": "staging"})

    result = promote_build_pack(factory_root, _request("staging", "r2"))

    assert result["status"] == "completed"
    assert not (factory_root / "deployments/testing/promo-pack.json").exists()
    assert (factory_root / "deployments/staging/promo-pack.json").exists()
