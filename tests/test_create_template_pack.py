from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from create_template_pack import create_template_pack
from create_template_pack import _pack_agents, _pack_manifest, _project_context
from factory_ops import load_json
from factory_ops import write_json
from validate_factory import validate_factory


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
    shutil.rmtree(destination / "build-packs", ignore_errors=True)
    (destination / "build-packs").mkdir(parents=True, exist_ok=True)

    build_registry_path = destination / "registry/build-packs.json"
    build_registry = load_json(build_registry_path)
    build_registry["entries"] = []
    write_json(build_registry_path, build_registry)

    for environment in ("testing", "staging", "production"):
        deployment_dir = destination / "deployments" / environment
        if deployment_dir.exists():
            for pointer in deployment_dir.glob("*.json"):
                pointer.unlink()

    shutil.rmtree(destination / ".pack-state/agent-memory", ignore_errors=True)

    template_report_defaults = {
        "json-health-checker-template-pack": {
            "capability_family": "json-health-checking",
            "expected_build_pack_variants": [
                "baseline proving ground",
                "memory and continuity proving ground",
            ],
            "first_materialization_purpose": "baseline proving ground",
        },
        "config-drift-checker-template-pack": {
            "capability_family": "config-drift-detection",
            "expected_build_pack_variants": [
                "baseline drift checker",
                "autonomy transfer proving ground",
            ],
            "first_materialization_purpose": "baseline drift checker",
        },
        "release-evidence-summarizer-template-pack": {
            "capability_family": "release-evidence-summarization",
            "expected_build_pack_variants": [
                "baseline release summarizer",
                "promotion-ready release summarizer",
            ],
            "first_materialization_purpose": "baseline release summarizer",
        },
        "api-contract-sentinel-template-pack": {
            "capability_family": "api-contract-validation",
            "expected_build_pack_variants": [
                "baseline contract sentinel",
                "autonomy transfer proving ground",
            ],
            "first_materialization_purpose": "baseline contract sentinel",
        },
        "algosec-diagnostic-framework-template-pack": {
            "capability_family": "support-oriented appliance diagnostics",
            "expected_build_pack_variants": [
                "baseline lab evidence collector",
                "support playbook proving ground",
            ],
            "first_materialization_purpose": "baseline lab evidence collector",
        },
    }
    for template_id, defaults in template_report_defaults.items():
        template_root = destination / "templates" / template_id
        if not template_root.exists():
            continue
        report_dir = template_root / "eval/history"
        for report_path in report_dir.glob("*/template-creation-report.json"):
            report = load_json(report_path)
            planning = dict(report.get("planning_summary", {}))
            planning.update({k: planning.get(k) or v for k, v in defaults.items()})
            report["planning_summary"] = planning
            write_json(report_path, report)
    return destination


def _request(
    template_pack_id: str,
    *,
    reuse_active_template: bool = False,
    personality_template_selection: dict[str, object] | None = None,
) -> dict[str, object]:
    planning_summary: dict[str, object] = {
        "project_goal": "Create a fresh template for testing.",
        "capability_family": "template-creation-test-family",
        "delivery_shape": "component",
        "reuse_active_template": reuse_active_template,
        "new_template_rationale": "" if reuse_active_template else "The active template should remain a separate smoke baseline.",
        "initial_benchmark_intent": "Minimal created-template smoke benchmark.",
        "expected_build_pack_variants": [
            "baseline proving ground",
            "transfer proving ground",
        ],
        "first_materialization_purpose": "baseline proving ground",
    }
    if personality_template_selection is not None:
        planning_summary["personality_template_selection"] = personality_template_selection
    return {
        "schema_version": "template-creation-request/v1",
        "template_pack_id": template_pack_id,
        "display_name": "Fresh Created Template Pack",
        "owning_team": "orchadmin",
        "requested_by": "pytest",
        "runtime": "python",
        "scaffold_strategy": "minimal_python_text_pack",
        "planning_summary": planning_summary,
    }


def test_create_template_pack_happy_path_creates_template_and_registry_entry(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    result = create_template_pack(factory_root, _request("fresh-created-template-pack"))

    target_root = factory_root / "templates" / "fresh-created-template-pack"
    assert result["status"] == "created"
    assert target_root.exists()

    manifest = load_json(target_root / "pack.json")
    assert manifest["pack_kind"] == "template_pack"
    assert any(note == "capability_family=template-creation-test-family" for note in manifest["notes"])

    lifecycle = load_json(target_root / "status/lifecycle.json")
    assert lifecycle["lifecycle_stage"] == "maintained"

    readiness = load_json(target_root / "status/readiness.json")
    assert readiness["readiness_state"] == "ready_for_review"

    deployment = load_json(target_root / "status/deployment.json")
    assert deployment["deployment_state"] == "not_deployed"

    templates_registry = load_json(factory_root / "registry/templates.json")
    assert any(
        entry["pack_id"] == "fresh-created-template-pack" and entry["active"] is True
        for entry in templates_registry["entries"]
    )


def test_create_template_pack_rejects_request_when_planning_says_reuse_active_template(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    try:
        create_template_pack(factory_root, _request("reuse-should-fail-template-pack", reuse_active_template=True))
    except ValueError as exc:
        assert "reuse_active_template" in str(exc) or "planning decision" in str(exc)
    else:
        raise AssertionError("expected create_template_pack to reject a reuse_active_template request")

    assert not (factory_root / "templates/reuse-should-fail-template-pack").exists()


def test_create_template_pack_rejects_duplicate_template_pack_id(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    try:
        create_template_pack(factory_root, _request("factory-native-smoke-template-pack"))
    except ValueError as exc:
        assert "already exists" in str(exc) or "already registered" in str(exc)
    else:
        raise AssertionError("expected duplicate template pack id to fail")


def test_create_template_pack_writes_canonical_creation_report_and_log_event(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    result = create_template_pack(factory_root, _request("reporting-template-pack"))

    promotion_log = load_json(factory_root / "registry/promotion-log.json")
    matching_events = [
        event
        for event in promotion_log["events"]
        if event.get("event_type") == "template_created"
        and event.get("template_pack_id") == "reporting-template-pack"
    ]
    assert len(matching_events) == 1

    report_path = Path(result["template_creation_report_path"])
    assert report_path.exists()
    report = load_json(report_path)
    assert report["planning_summary"]["project_goal"] == "Create a fresh template for testing."
    assert report["planning_summary"]["capability_family"] == "template-creation-test-family"
    assert report["factory_mutations"]["registry_updated"] is True
    assert report["factory_mutations"]["operation_log_updated"] is True
    assert report["factory_mutations"]["post_write_factory_validation"] == "pass"
    assert any(
        "Materialize the first build-pack proving ground" in action
        for action in report["next_recommended_actions"]
    )


def test_create_template_pack_rejects_request_when_expected_variants_are_too_narrow(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    request = _request("too-narrow-template-pack")
    request["planning_summary"]["expected_build_pack_variants"] = ["baseline proving ground"]

    try:
        create_template_pack(factory_root, request)
    except ValueError as exc:
        assert "expected_build_pack_variants" in str(exc)
    else:
        raise AssertionError("expected create_template_pack to reject a one-variant template plan")


def test_create_template_pack_rejects_request_when_first_materialization_purpose_is_missing(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    request = _request("missing-first-materialization-purpose-template-pack")
    request["planning_summary"]["first_materialization_purpose"] = ""

    try:
        create_template_pack(factory_root, request)
    except ValueError as exc:
        assert "first_materialization_purpose" in str(exc)
    else:
        raise AssertionError("expected create_template_pack to reject a missing first materialization purpose")


def test_create_template_pack_records_optional_personality_template_selection(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    request = _request(
        "personality-template-pack",
        personality_template_selection={
            "personality_template_id": "business-partner-concierge",
            "selection_reason": "Use the warmer operator-facing overlay for this template line.",
            "apply_to_derived_build_packs_by_default": True,
        },
    )

    result = create_template_pack(factory_root, request)

    manifest = load_json(factory_root / "templates/personality-template-pack/pack.json")
    assert manifest["personality_template"]["template_id"] == "business-partner-concierge"
    assert manifest["personality_template"]["selection_origin"] == "template_selected"
    assert manifest["personality_template"]["apply_to_derived_build_packs_by_default"] is True
    agents_text = (factory_root / "templates/personality-template-pack/AGENTS.md").read_text(encoding="utf-8")
    assert "optional personality overlay" in agents_text
    assert "business-partner-concierge" in agents_text

    report = load_json(Path(result["template_creation_report_path"]))
    assert report["resolved_personality_template"]["template_id"] == "business-partner-concierge"


def test_generated_template_surfaces_include_autonomy_marker_set() -> None:
    agents_text = _pack_agents("Example Template Pack")
    assert "PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md" in agents_text
    assert "PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md" in agents_text
    assert "ad hoc `ssh` prompts" in agents_text
    assert "tools/import_external_runtime_evidence.py" in agents_text

    context_text = _project_context(
        "example_template_pack",
        "example-template-pack-smoke-small-001.json",
        "Create an example template.",
    )
    assert "PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md" in context_text
    assert "PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md" in context_text
    assert "ad hoc `ssh` prompts" in context_text
    assert "external runtime-evidence import" in context_text

    manifest = _pack_manifest(
        template_pack_id="example-template-pack",
        display_name="Example Template Pack",
        owning_team="orchadmin",
        module_name="example_template_pack",
        creation_id="create-template-example-template-pack-20260326t000000z",
        project_goal="Create an example template.",
        capability_family="example-template-family",
        personality_template=None,
    )
    notes = manifest["notes"]
    assert any("factory_autonomy_baseline=" in note for note in notes)
    assert any("factory_autonomy_tracking=" in note for note in notes)
    assert any("factory_startup_compliance=" in note for note in notes)


def test_validate_factory_reports_missing_active_template_instruction_marker(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)
    agents_path = factory_root / "templates/factory-native-smoke-template-pack/AGENTS.md"
    agents_text = agents_path.read_text(encoding="utf-8")
    agents_path.write_text(
        agents_text.replace("PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md", "PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF-MISSING.md"),
        encoding="utf-8",
    )

    result = validate_factory(factory_root)

    assert any(
        "template instruction-surface drift detected" in error
        and "factory-native-smoke-template-pack/AGENTS.md" in error
        and "PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md" in error
        for error in result["errors"]
    )
