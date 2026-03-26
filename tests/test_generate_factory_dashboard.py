from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from factory_ops import load_json, write_json


def _copy_pack(root: Path, destination_root: Path, relative_pack_root: str) -> None:
    source = root / relative_pack_root
    destination = destination_root / relative_pack_root
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)


def _prepare_pack_quality(pack_root: Path, *, evaluated_at: str) -> None:
    readiness = load_json(pack_root / "status/readiness.json")
    readiness["last_evaluated_at"] = evaluated_at
    readiness["readiness_state"] = "ready_for_deploy"
    readiness["ready_for_deployment"] = True
    readiness["blocking_issues"] = []
    for gate in readiness.get("required_gates", []):
        if isinstance(gate, dict):
            gate["status"] = "pass"
            gate["last_run_at"] = evaluated_at
    write_json(pack_root / "status/readiness.json", readiness)

    eval_index = load_json(pack_root / "eval/latest/index.json")
    eval_index["updated_at"] = evaluated_at
    for result in eval_index.get("benchmark_results", []):
        if isinstance(result, dict):
            result["status"] = "pass"
    write_json(pack_root / "eval/latest/index.json", eval_index)


def _prepare_deployment_state(
    pack_root: Path,
    *,
    environment: str | None,
    release_id: str | None,
    pointer_path: str | None,
    promoted_at: str | None,
) -> None:
    deployment_path = pack_root / "status/deployment.json"
    deployment = load_json(deployment_path) if deployment_path.exists() else {"schema_version": "pack-deployment/v2"}
    if environment is None:
        deployment["active_environment"] = None
        deployment["active_release_id"] = None
        deployment["active_release_path"] = None
        deployment["deployment_pointer_path"] = None
        deployment["deployment_state"] = "not_deployed"
        deployment["deployment_transaction_id"] = None
        deployment["last_promoted_at"] = None
        deployment["last_verified_at"] = None
        deployment["projection_state"] = "not_projected"
        deployment["deployment_notes"] = ["No active environment assignment."]
    else:
        deployment["active_environment"] = environment
        deployment["active_release_id"] = release_id
        deployment["active_release_path"] = f"dist/releases/{release_id}" if release_id else None
        deployment["deployment_pointer_path"] = pointer_path
        deployment["deployment_state"] = environment
        deployment["deployment_transaction_id"] = f"promote-{pack_root.name}-{environment}-fixture"
        deployment["last_promoted_at"] = promoted_at
        deployment["last_verified_at"] = promoted_at
        deployment["projection_state"] = "projected"
        deployment["deployment_notes"] = [f"Promoted to {environment} by fixture."]
    deployment["pack_id"] = pack_root.name
    deployment["pack_kind"] = "build_pack"
    write_json(deployment_path, deployment)


def _write_registry_files(factory_root: Path) -> None:
    write_json(
        factory_root / "registry/templates.json",
        {
            "schema_version": "project-pack-factory-registry/v1",
            "updated_at": "2026-03-26T18:00:00Z",
            "entries": [
                {
                    "active": True,
                    "active_benchmark_ids": ["factory-smoke-small-001"],
                    "latest_eval_index": "templates/factory-native-smoke-template-pack/eval/latest/index.json",
                    "lifecycle_stage": "maintained",
                    "notes": ["Fresh minimal active template for live PackFactory workflow testing."],
                    "pack_id": "factory-native-smoke-template-pack",
                    "pack_kind": "template_pack",
                    "pack_root": "templates/factory-native-smoke-template-pack",
                    "ready_for_deployment": False,
                    "retired_at": None,
                    "retirement_file": "status/retirement.json",
                    "retirement_state": "active",
                },
                {
                    "active": True,
                    "active_benchmark_ids": ["json-health-checker-template-pack-smoke-small-001"],
                    "latest_eval_index": "templates/json-health-checker-template-pack/eval/latest/index.json",
                    "lifecycle_stage": "maintained",
                    "notes": ["Created through the PackFactory template creation workflow."],
                    "pack_id": "json-health-checker-template-pack",
                    "pack_kind": "template_pack",
                    "pack_root": "templates/json-health-checker-template-pack",
                    "ready_for_deployment": False,
                    "retired_at": None,
                    "retirement_file": "status/retirement.json",
                    "retirement_state": "active",
                },
                {
                    "active": True,
                    "active_benchmark_ids": ["release-evidence-summarizer-template-pack-smoke-small-001"],
                    "latest_eval_index": "templates/release-evidence-summarizer-template-pack/eval/latest/index.json",
                    "lifecycle_stage": "maintained",
                    "notes": ["Created through the PackFactory template creation workflow."],
                    "pack_id": "release-evidence-summarizer-template-pack",
                    "pack_kind": "template_pack",
                    "pack_root": "templates/release-evidence-summarizer-template-pack",
                    "ready_for_deployment": False,
                    "retired_at": None,
                    "retirement_file": "status/retirement.json",
                    "retirement_state": "active",
                },
            ],
        },
    )

    write_json(
        factory_root / "registry/build-packs.json",
        {
            "schema_version": "project-pack-factory-registry/v1",
            "updated_at": "2026-03-26T18:00:00Z",
            "entries": [
                {
                    "active": True,
                    "active_release_id": "release-evidence-summarizer-v3-r1",
                    "deployment_pointer": "deployments/production/release-evidence-summarizer-build-pack-v3.json",
                    "deployment_state": "production",
                    "latest_eval_index": "build-packs/release-evidence-summarizer-build-pack-v3/eval/latest/index.json",
                    "lifecycle_stage": "maintained",
                    "notes": ["Main production release evidence line."],
                    "pack_id": "release-evidence-summarizer-build-pack-v3",
                    "pack_kind": "build_pack",
                    "pack_root": "build-packs/release-evidence-summarizer-build-pack-v3",
                    "ready_for_deployment": True,
                    "retired_at": None,
                    "retirement_file": "status/retirement.json",
                    "retirement_state": "active",
                },
                {
                    "active": True,
                    "active_release_id": "json-health-checker-autonomy-to-promotion-build-pack-v1-r1",
                    "deployment_pointer": "deployments/testing/json-health-checker-autonomy-to-promotion-build-pack-v1.json",
                    "deployment_state": "testing",
                    "latest_eval_index": "build-packs/json-health-checker-autonomy-to-promotion-build-pack-v1/eval/latest/index.json",
                    "lifecycle_stage": "testing",
                    "notes": ["Main testing autonomy proof line."],
                    "pack_id": "json-health-checker-autonomy-to-promotion-build-pack-v1",
                    "pack_kind": "build_pack",
                    "pack_root": "build-packs/json-health-checker-autonomy-to-promotion-build-pack-v1",
                    "ready_for_deployment": True,
                    "retired_at": None,
                    "retirement_file": "status/retirement.json",
                    "retirement_state": "active",
                },
                {
                    "active": True,
                    "active_release_id": None,
                    "deployment_pointer": None,
                    "deployment_state": "not_deployed",
                    "latest_eval_index": "build-packs/factory-native-smoke-build-pack/eval/latest/index.json",
                    "lifecycle_stage": "maintained",
                    "notes": ["Ready baseline path."],
                    "pack_id": "factory-native-smoke-build-pack",
                    "pack_kind": "build_pack",
                    "pack_root": "build-packs/factory-native-smoke-build-pack",
                    "ready_for_deployment": True,
                    "retired_at": None,
                    "retirement_file": "status/retirement.json",
                    "retirement_state": "active",
                },
            ],
        },
    )

    write_json(
        factory_root / "registry/promotion-log.json",
        {
            "schema_version": "project-pack-factory-promotion-log/v1",
            "updated_at": "2026-03-26T18:00:00Z",
            "events": [
                {
                    "event_type": "promoted",
                    "build_pack_id": "release-evidence-summarizer-build-pack-v3",
                    "promotion_id": "promote-release-evidence-summarizer-build-pack-v3-production-20260326t170000z",
                    "promotion_report_path": "eval/history/promote-release-evidence-summarizer-build-pack-v3-production-20260326t170000z/promotion-report.json",
                    "status": "completed",
                    "target_environment": "production",
                },
                {
                    "event_type": "promoted",
                    "build_pack_id": "json-health-checker-autonomy-to-promotion-build-pack-v1",
                    "promotion_id": "promote-json-health-checker-autonomy-to-promotion-build-pack-v1-testing-20260326t171500z",
                    "promotion_report_path": "eval/history/promote-json-health-checker-autonomy-to-promotion-build-pack-v1-testing-20260326t171500z/promotion-report.json",
                    "status": "completed",
                    "target_environment": "testing",
                },
                {
                    "event_type": "materialized",
                    "materialization_id": "materialize-factory-native-smoke-build-pack-20260326t172500z",
                    "materialization_report_path": "eval/history/materialize-factory-native-smoke-build-pack-20260326t172500z/materialization-report.json",
                    "source_template_id": "factory-native-smoke-template-pack",
                    "status": "completed",
                    "target_build_pack_id": "factory-native-smoke-build-pack",
                },
            ],
        },
    )


def _write_deployment_pointers(factory_root: Path) -> None:
    for environment in ("production", "staging", "testing"):
        (factory_root / "deployments" / environment).mkdir(parents=True, exist_ok=True)

    write_json(
        factory_root / "deployments/production/release-evidence-summarizer-build-pack-v3.json",
        {
            "active_release_id": "release-evidence-summarizer-v3-r1",
            "active_release_path": "dist/releases/release-evidence-summarizer-v3-r1",
            "deployment_transaction_id": "promote-release-evidence-summarizer-build-pack-v3-production-20260326t170000z",
            "environment": "production",
            "pack_id": "release-evidence-summarizer-build-pack-v3",
            "pack_kind": "build_pack",
            "pack_root": "build-packs/release-evidence-summarizer-build-pack-v3",
            "promotion_evidence_ref": "eval/history/promote-release-evidence-summarizer-build-pack-v3-production-20260326t170000z/promotion-report.json",
            "schema_version": "pack-deployment-pointer/v2",
            "source_deployment_file": "build-packs/release-evidence-summarizer-build-pack-v3/status/deployment.json",
            "updated_at": "2026-03-26T17:00:00Z",
        },
    )
    write_json(
        factory_root / "deployments/testing/json-health-checker-autonomy-to-promotion-build-pack-v1.json",
        {
            "active_release_id": "json-health-checker-autonomy-to-promotion-build-pack-v1-r1",
            "active_release_path": "dist/releases/json-health-checker-autonomy-to-promotion-build-pack-v1-r1",
            "deployment_transaction_id": "promote-json-health-checker-autonomy-to-promotion-build-pack-v1-testing-20260326t171500z",
            "environment": "testing",
            "pack_id": "json-health-checker-autonomy-to-promotion-build-pack-v1",
            "pack_kind": "build_pack",
            "pack_root": "build-packs/json-health-checker-autonomy-to-promotion-build-pack-v1",
            "promotion_evidence_ref": "eval/history/promote-json-health-checker-autonomy-to-promotion-build-pack-v1-testing-20260326t171500z/promotion-report.json",
            "schema_version": "pack-deployment-pointer/v2",
            "source_deployment_file": "build-packs/json-health-checker-autonomy-to-promotion-build-pack-v1/status/deployment.json",
            "updated_at": "2026-03-26T17:15:00Z",
        },
    )


def _write_root_memory(factory_root: Path) -> None:
    memory_dir = factory_root / ".pack-state/agent-memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    memory_relative_path = ".pack-state/agent-memory/factory-autonomy-memory-dashboard-fixture.json"
    memory_payload = {
        "schema_version": "factory-autonomy-memory/v1",
        "generated_at": "2026-03-26T18:00:00Z",
        "memory_id": "factory-autonomy-memory-dashboard-fixture",
        "current_focus": [
            "Keep factory-level autonomy discoverable from the root startup surfaces.",
            "Turn the dashboard into a fast operator-facing control room.",
        ],
        "next_action_items": [
            "Ship the first local-first dashboard.",
            "Keep the Astro upgrade optional until usefulness is proven.",
        ],
        "pending_items": [
            "Operator dashboard for factory state.",
            "Agent-instruction performance review and optimization.",
        ],
        "overdue_items": [],
        "blockers": ["Autonomy is strongest in bounded PackFactory workflows, not broad unscripted project work."],
        "known_limits": ["Imported memory is fail-closed by design, so progress can pause until reconcile happens."],
        "latest_autonomy_proof": "Latest autonomy proof includes a completed testing promotion for the JSON Health Checker autonomy path.",
        "recommended_next_step": "Build the first Python-generated static dashboard before considering Astro.",
    }
    write_json(factory_root / memory_relative_path, memory_payload)
    write_json(
        memory_dir / "latest-memory.json",
        {
            "schema_version": "factory-autonomy-memory-pointer/v1",
            "selected_generated_at": "2026-03-26T18:00:00Z",
            "selected_memory_id": "factory-autonomy-memory-dashboard-fixture",
            "selected_memory_path": memory_relative_path,
            "selected_memory_sha256": "fixture",
            "selected_memory_tier": "promoted_factory_memory",
            "source_kind": "factory_memory_refresh",
            "source_tool": "tools/refresh_factory_autonomy_memory.py",
            "updated_at": "2026-03-26T18:00:00Z",
        },
    )


def _build_minimal_factory(tmp_path: Path) -> Path:
    factory_root = tmp_path / "factory"
    factory_root.mkdir()

    for relative_path in ("AGENTS.md", "README.md"):
        destination = factory_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative_path, destination)

    shutil.copytree(ROOT / "docs", factory_root / "docs")

    for relative_pack_root in (
        "build-packs/release-evidence-summarizer-build-pack-v3",
        "build-packs/json-health-checker-autonomy-to-promotion-build-pack-v1",
        "build-packs/factory-native-smoke-build-pack",
        "templates/release-evidence-summarizer-template-pack",
        "templates/json-health-checker-template-pack",
        "templates/factory-native-smoke-template-pack",
    ):
        _copy_pack(ROOT, factory_root, relative_pack_root)

    (factory_root / "registry").mkdir(parents=True, exist_ok=True)
    _write_registry_files(factory_root)
    _write_deployment_pointers(factory_root)
    _write_root_memory(factory_root)
    (factory_root / ".pack-state/startup-benchmarks").mkdir(parents=True, exist_ok=True)

    _prepare_pack_quality(
        factory_root / "build-packs/release-evidence-summarizer-build-pack-v3",
        evaluated_at="2026-03-26T17:00:00Z",
    )
    _prepare_pack_quality(
        factory_root / "build-packs/json-health-checker-autonomy-to-promotion-build-pack-v1",
        evaluated_at="2026-03-26T17:15:00Z",
    )
    _prepare_pack_quality(
        factory_root / "build-packs/factory-native-smoke-build-pack",
        evaluated_at="2026-03-26T17:25:00Z",
    )
    _prepare_deployment_state(
        factory_root / "build-packs/release-evidence-summarizer-build-pack-v3",
        environment="production",
        release_id="release-evidence-summarizer-v3-r1",
        pointer_path="deployments/production/release-evidence-summarizer-build-pack-v3.json",
        promoted_at="2026-03-26T17:00:00Z",
    )
    _prepare_deployment_state(
        factory_root / "build-packs/json-health-checker-autonomy-to-promotion-build-pack-v1",
        environment="testing",
        release_id="json-health-checker-autonomy-to-promotion-build-pack-v1-r1",
        pointer_path="deployments/testing/json-health-checker-autonomy-to-promotion-build-pack-v1.json",
        promoted_at="2026-03-26T17:15:00Z",
    )
    _prepare_deployment_state(
        factory_root / "build-packs/factory-native-smoke-build-pack",
        environment=None,
        release_id=None,
        pointer_path=None,
        promoted_at=None,
    )

    return factory_root


def _run_generator(factory_root: Path) -> Path:
    output_dir = factory_root / ".pack-state/factory-dashboard/latest"
    env = os.environ.copy()
    env["PROJECT_PACK_FACTORY_FIXED_NOW"] = "2026-03-26T18:30:00Z"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/generate_factory_dashboard.py"),
            "--factory-root",
            str(factory_root),
            "--output-dir",
            str(output_dir),
            "--report-format",
            "json",
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return output_dir


def test_generate_factory_dashboard_writes_expected_artifacts(tmp_path: Path) -> None:
    factory_root = _build_minimal_factory(tmp_path)
    output_dir = _run_generator(factory_root)

    assert (output_dir / "index.html").exists()
    assert (output_dir / "dashboard-snapshot.json").exists()
    assert (output_dir / "dashboard-report.json").exists()
    assert (output_dir / "assets/dashboard.css").exists()
    assert (output_dir / "assets/dashboard.js").exists()

    snapshot = load_json(output_dir / "dashboard-snapshot.json")
    assert snapshot["schema_version"]
    for key in (
        "what_matters_most",
        "environment_board",
        "quality_now",
        "automation_now",
        "factory_learning",
        "agent_memory",
        "ideas_lab",
        "recent_motion",
        "focused_portfolio",
        "mismatch_warnings",
    ):
        assert key in snapshot

    report = load_json(output_dir / "dashboard-report.json")
    assert report["dashboard_build_id"]
    assert report["dashboard_build_id"] == snapshot["dashboard_build_id"]


def test_generate_factory_dashboard_prefers_production_assignment_for_top_banner(tmp_path: Path) -> None:
    factory_root = _build_minimal_factory(tmp_path)
    output_dir = _run_generator(factory_root)

    snapshot = load_json(output_dir / "dashboard-snapshot.json")
    what_matters = snapshot["what_matters_most"]

    assert what_matters["id"] == "release-evidence-summarizer-build-pack-v3"
    assert what_matters["truth_layer"] in {"canonical", "derived"}

    environment_board_json = json.dumps(snapshot["environment_board"], sort_keys=True)
    assert "production" in environment_board_json
    assert "staging" in environment_board_json
    assert "testing" in environment_board_json
    assert "ready_unassigned" in environment_board_json
    assert "release-evidence-summarizer-build-pack-v3" in environment_board_json
    assert "json-health-checker-autonomy-to-promotion-build-pack-v1" in environment_board_json
    assert "factory-native-smoke-build-pack" in environment_board_json


def test_generate_factory_dashboard_prerenders_core_sections_into_html(tmp_path: Path) -> None:
    factory_root = _build_minimal_factory(tmp_path)
    output_dir = _run_generator(factory_root)

    html = (output_dir / "index.html").read_text(encoding="utf-8")

    assert "What matters most now" in html
    assert "Quality Now" in html
    assert "Automation Now" in html
    assert "Factory Learning" in html
    assert "Agent Memory" in html
    assert "Ideas Lab" in html
    assert "release-evidence-summarizer-build-pack-v3" in html
    assert "json-health-checker-autonomy-to-promotion-build-pack-v1" in html
