from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from create_template_pack import create_template_pack
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


def _request(template_pack_id: str, *, reuse_active_template: bool = False) -> dict[str, object]:
    return {
        "schema_version": "template-creation-request/v1",
        "template_pack_id": template_pack_id,
        "display_name": "Fresh Created Template Pack",
        "owning_team": "orchadmin",
        "requested_by": "pytest",
        "runtime": "python",
        "scaffold_strategy": "minimal_python_text_pack",
        "planning_summary": {
            "project_goal": "Create a fresh template for testing.",
            "delivery_shape": "component",
            "reuse_active_template": reuse_active_template,
            "new_template_rationale": "" if reuse_active_template else "The active template should remain a separate smoke baseline.",
            "initial_benchmark_intent": "Minimal created-template smoke benchmark.",
        },
    }


def test_create_template_pack_happy_path_creates_template_and_registry_entry(tmp_path: Path) -> None:
    factory_root = _copy_factory(tmp_path)

    result = create_template_pack(factory_root, _request("fresh-created-template-pack"))

    target_root = factory_root / "templates" / "fresh-created-template-pack"
    assert result["status"] == "created"
    assert target_root.exists()

    manifest = load_json(target_root / "pack.json")
    assert manifest["pack_kind"] == "template_pack"

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
    assert report["factory_mutations"]["registry_updated"] is True
    assert report["factory_mutations"]["operation_log_updated"] is True
    assert report["factory_mutations"]["post_write_factory_validation"] == "pass"
