from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from materialize_build_pack import materialize_build_pack
from factory_ops import load_json
from validate_factory import validate_factory


SOURCE_TEMPLATE_ID = "factory-native-smoke-template-pack"


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


def _request(
    target_build_pack_id: str,
    *,
    personality_template_selection: dict[str, object] | None = None,
) -> dict[str, object]:
    request: dict[str, object] = {
        "schema_version": "build-pack-materialization-request/v1",
        "source_template_id": SOURCE_TEMPLATE_ID,
        "target_build_pack_id": target_build_pack_id,
        "target_display_name": "Slim Derived Build Pack",
        "target_version": "0.1.0",
        "target_revision": "test-revision",
        "materialized_by": "pytest",
        "materialization_reason": "Test materialization",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
    }
    if personality_template_selection is not None:
        request["personality_template_selection"] = personality_template_selection
    return request


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

    manifest = load_json(target_root / "pack.json")
    contract = manifest["directory_contract"]
    assert contract["project_objective_file"] == "contracts/project-objective.json"
    assert contract["tasks_dir"] == "tasks"
    assert contract["task_backlog_file"] == "tasks/active-backlog.json"
    assert contract["work_state_file"] == "status/work-state.json"
    assert contract["runtime_evidence_export_dir"] == "dist/exports/runtime-evidence"
    assert contract["portable_runtime_tools_dir"] == ".packfactory-runtime/tools"
    assert contract["portable_runtime_schemas_dir"] == ".packfactory-runtime/schemas"
    assert contract["portable_runtime_helper_manifest"] == ".packfactory-runtime/manifest.json"
    assert manifest["entrypoints"]["export_runtime_evidence_command"] == (
        "python3 src/pack_export_runtime_evidence.py "
        "--pack-root . --run-id <run-id> --exported-by <actor> --output-dir dist/exports/runtime-evidence --output json"
    )
    assert manifest["post_bootstrap_read_order"][5:8] == [
        "contracts/project-objective.json",
        "tasks/active-backlog.json",
        "status/work-state.json",
    ]
    agents_text = (target_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "build pack, not a source template" in agents_text
    assert "pack.json.post_bootstrap_read_order" in agents_text
    assert "export bounded runtime evidence when running externally" in agents_text
    assert "promotion readiness also expects one completed `run_multi_hop_autonomy_rehearsal.py` report" in agents_text
    assert (target_root / "dist/exports/runtime-evidence").exists()
    assert (target_root / "src/pack_export_runtime_evidence.py").exists()

    project_objective = load_json(target_root / "contracts/project-objective.json")
    assert project_objective["pack_id"] == "slim-build-pack"
    assert project_objective["objective_id"] == "slim-build-pack_objective"
    assert project_objective["autonomy_rehearsal_requirement"]["required_for_promotion"] is True
    assert project_objective["autonomy_rehearsal_requirement"]["workflow_id"] == "multi_hop_autonomy_rehearsal"
    assert project_objective["autonomy_quality_requirement"]["required_for_promotion"] is False

    task_backlog = load_json(target_root / "tasks/active-backlog.json")
    task_ids = [task["task_id"] for task in task_backlog["tasks"]]
    assert task_ids == ["run_build_pack_validation", "run_inherited_benchmarks"]
    tasks_by_id = {task["task_id"]: task for task in task_backlog["tasks"]}
    assert tasks_by_id["run_build_pack_validation"]["validation_commands"] == [
        "python3 .packfactory-runtime/tools/run_build_pack_readiness_eval.py --pack-root . --mode validation-only --invoked-by autonomous-loop"
    ]
    assert tasks_by_id["run_inherited_benchmarks"]["validation_commands"] == [
        "python3 .packfactory-runtime/tools/run_build_pack_readiness_eval.py --pack-root . --mode benchmark-only --invoked-by autonomous-loop"
    ]
    helper_manifest = load_json(target_root / ".packfactory-runtime/manifest.json")
    assert helper_manifest["seeded_by_materializer"] is True
    assert set(helper_manifest["tools"]) == {
        ".packfactory-runtime/tools/factory_ops.py",
        ".packfactory-runtime/tools/run_build_pack_readiness_eval.py",
        ".packfactory-runtime/tools/record_autonomy_run.py",
    }
    assert set(helper_manifest["schemas"]) >= {
        ".packfactory-runtime/schemas/portable-runtime-helper-manifest.schema.json",
        ".packfactory-runtime/schemas/readiness.schema.json",
        ".packfactory-runtime/schemas/eval-latest-index.schema.json",
        ".packfactory-runtime/schemas/autonomy-loop-event.schema.json",
        ".packfactory-runtime/schemas/autonomy-run-summary.schema.json",
    }

    work_state = load_json(target_root / "status/work-state.json")
    assert work_state["active_task_id"] == "run_build_pack_validation"
    assert work_state["next_recommended_task_id"] == "run_build_pack_validation"
    assert work_state["pending_task_ids"] == ["run_inherited_benchmarks"]

    promotion_log = load_json(factory_root / "registry/promotion-log.json")
    assert any(event.get("event_type") == "materialized" and event.get("target_build_pack_id") == "slim-build-pack" for event in promotion_log["events"])


def test_materialize_build_pack_rejects_existing_target_id(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    try:
        materialize_build_pack(factory_root, _request("factory-native-smoke-build-pack"))
    except ValueError as exc:
        assert "already exists" in str(exc) or "already registered" in str(exc)
    else:
        raise AssertionError("expected materialization to fail for existing target id")


def test_materialize_build_pack_does_not_copy_local_state_contents(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    source_local_state = factory_root / f"templates/{SOURCE_TEMPLATE_ID}/.pack-state/runtime-scratch"
    source_local_state.mkdir(parents=True, exist_ok=True)
    sentinel = source_local_state / "sentinel.json"
    sentinel.write_text('{"ok": true}\n', encoding="utf-8")

    materialize_build_pack(factory_root, _request("state-clean-build-pack"))

    target_local_state = factory_root / "build-packs/state-clean-build-pack/.pack-state"
    assert target_local_state.exists()
    assert not (target_local_state / "runtime-scratch/sentinel.json").exists()


def test_materialize_build_pack_synthesizes_not_run_eval_and_required_gates(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    materialize_build_pack(factory_root, _request("gated-build-pack"))

    readiness = load_json(factory_root / "build-packs/gated-build-pack/status/readiness.json")
    gate_ids = {gate["gate_id"]: gate for gate in readiness["required_gates"]}
    assert gate_ids["validate_build_pack_contract"]["status"] == "not_run"
    non_validation_gates = [
        gate for gate_id, gate in gate_ids.items() if gate_id != "validate_build_pack_contract"
    ]
    assert non_validation_gates
    assert all(gate["status"] == "not_run" for gate in non_validation_gates)

    eval_latest = load_json(factory_root / "build-packs/gated-build-pack/eval/latest/index.json")
    assert eval_latest["benchmark_results"]
    assert all(result["status"] == "not_run" for result in eval_latest["benchmark_results"])
    assert all(
        result["latest_run_id"].startswith("materialize-gated-build-pack-")
        for result in eval_latest["benchmark_results"]
    )


def test_validate_factory_rejects_invalid_autonomy_task_reference(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    materialize_build_pack(factory_root, _request("autonomy-check-build-pack"))

    work_state_path = factory_root / "build-packs/autonomy-check-build-pack/status/work-state.json"
    work_state = load_json(work_state_path)
    work_state["next_recommended_task_id"] = "missing-task"
    work_state_path.write_text(f"{json.dumps(work_state, indent=2)}\n", encoding="utf-8")

    result = validate_factory(factory_root)

    assert result["valid"] is False
    assert any("next_recommended_task_id must reference a real task" in error for error in result["errors"])


def test_materialize_build_pack_can_apply_catalog_personality_selection(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    materialize_build_pack(
        factory_root,
        _request(
            "personality-selected-build-pack",
            personality_template_selection={
                "selection_mode": "catalog_template",
                "personality_template_id": "business-partner-concierge",
                "selection_reason": "Use the warmer operator-facing overlay for this proving ground.",
            },
        ),
    )

    manifest = load_json(factory_root / "build-packs/personality-selected-build-pack/pack.json")
    assert manifest["personality_template"]["template_id"] == "business-partner-concierge"
    assert manifest["personality_template"]["selection_origin"] == "materialization_selected"
    agents_text = (
        factory_root / "build-packs/personality-selected-build-pack/AGENTS.md"
    ).read_text(encoding="utf-8")
    assert "optional personality overlay" in agents_text
    assert "business-partner-concierge" in agents_text


def test_materialize_build_pack_inherits_template_default_personality(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    source_manifest_path = factory_root / f"templates/{SOURCE_TEMPLATE_ID}/pack.json"
    source_manifest = load_json(source_manifest_path)
    source_manifest["personality_template"] = {
        "template_id": "calm-delivery-lead",
        "display_name": "Calm Delivery Lead",
        "summary": "Steady delivery-lead posture for concise operator briefings, release coordination, and practical next-step framing.",
        "selection_origin": "template_selected",
        "selection_reason": "Make the smoke template concise by default.",
        "catalog_path": "docs/specs/project-pack-factory/agent-personality-template-catalog.json",
        "apply_to_derived_build_packs_by_default": True,
    }
    source_manifest_path.write_text(f"{json.dumps(source_manifest, indent=2)}\n", encoding="utf-8")

    materialize_build_pack(factory_root, _request("personality-inherited-build-pack"))

    manifest = load_json(factory_root / "build-packs/personality-inherited-build-pack/pack.json")
    assert manifest["personality_template"]["template_id"] == "calm-delivery-lead"
    assert manifest["personality_template"]["selection_origin"] == "materialization_inherited_default"
