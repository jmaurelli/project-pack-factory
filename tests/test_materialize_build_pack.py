from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from materialize_build_pack import materialize_build_pack
from factory_ops import load_json


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


def _request(target_build_pack_id: str) -> dict[str, object]:
    return {
        "schema_version": "build-pack-materialization-request/v1",
        "source_template_id": "agent-memory-first-template-pack",
        "target_build_pack_id": target_build_pack_id,
        "target_display_name": "Slim Derived Build Pack",
        "target_version": "0.1.0",
        "target_revision": "test-revision",
        "materialized_by": "pytest",
        "materialization_reason": "Test materialization",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
    }


def test_materialize_build_pack_happy_path_creates_pack_and_registry(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    # An unrelated invalid historical fixture must not block source-template materialization.
    (factory_root / "build-packs/ai-native-codex-build-pack/status/readiness.json").write_text("{\n", encoding="utf-8")

    result = materialize_build_pack(factory_root, _request("slim-build-pack"))

    target_root = factory_root / "build-packs" / "slim-build-pack"
    assert result["status"] == "completed"
    assert target_root.exists()

    registry = load_json(factory_root / "registry/build-packs.json")
    entries = registry["entries"]
    assert any(entry["pack_id"] == "slim-build-pack" and entry["active"] is True for entry in entries)

    promotion_log = load_json(factory_root / "registry/promotion-log.json")
    assert any(event.get("event_type") == "materialized" and event.get("target_build_pack_id") == "slim-build-pack" for event in promotion_log["events"])


def test_materialize_build_pack_rejects_existing_target_id(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    try:
        materialize_build_pack(factory_root, _request("ai-native-codex-build-pack"))
    except ValueError as exc:
        assert "already exists" in str(exc) or "already registered" in str(exc)
    else:
        raise AssertionError("expected materialization to fail for existing target id")


def test_materialize_build_pack_does_not_copy_local_state_contents(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    source_local_state = factory_root / "templates/agent-memory-first-template-pack/.pack-state/agent-memory"
    source_local_state.mkdir(parents=True, exist_ok=True)
    sentinel = source_local_state / "sentinel.json"
    sentinel.write_text('{"ok": true}\n', encoding="utf-8")

    materialize_build_pack(factory_root, _request("state-clean-build-pack"))

    target_local_state = factory_root / "build-packs/state-clean-build-pack/.pack-state"
    assert target_local_state.exists()
    assert not (target_local_state / "agent-memory/sentinel.json").exists()


def test_materialize_build_pack_synthesizes_not_run_eval_and_required_gates(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    materialize_build_pack(factory_root, _request("gated-build-pack"))

    readiness = load_json(factory_root / "build-packs/gated-build-pack/status/readiness.json")
    gate_ids = {gate["gate_id"]: gate for gate in readiness["required_gates"]}
    assert gate_ids["validate_build_pack_contract"]["status"] == "not_run"
    assert gate_ids["agent_memory_restart_small_001"]["status"] == "not_run"

    eval_latest = load_json(factory_root / "build-packs/gated-build-pack/eval/latest/index.json")
    assert eval_latest["benchmark_results"][0]["status"] == "not_run"
    assert eval_latest["benchmark_results"][0]["latest_run_id"].startswith("materialize-gated-build-pack-")
