#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import resolve_factory_root, validate_json_document, validate_schema_file, load_json


SCHEMA_BY_RELATIVE_PATH = {
    "pack.json": "pack.schema.json",
    "status/lifecycle.json": "lifecycle.schema.json",
    "status/readiness.json": "readiness.schema.json",
    "status/deployment.json": "deployment.schema.json",
    "status/retirement.json": "retirement.schema.json",
    "lineage/source-template.json": "source-template.schema.json",
    "benchmarks/active-set.json": "benchmark-active-set.schema.json",
    "eval/latest/index.json": "eval-latest-index.schema.json",
}

PACK_ROOTS = ("templates", "build-packs")
DEPLOYMENT_ENVIRONMENTS = ("testing", "staging", "production")


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _load_registry_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load_object(path)
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{path}: entries must be an array")
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: registry entries must be objects")
        pack_id = entry.get("pack_id")
        if not isinstance(pack_id, str):
            raise ValueError(f"{path}: registry entry missing string pack_id")
        result[pack_id] = entry
    return result


def _iter_pack_roots(factory_root: Path) -> list[Path]:
    results: list[Path] = []
    for root_name in PACK_ROOTS:
        root = factory_root / root_name
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "pack.json").exists():
                results.append(child)
    return results


def _validate_contract_paths(pack_root: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    contract = manifest.get("directory_contract")
    if not isinstance(contract, dict):
        errors.append(f"{pack_root / 'pack.json'}: directory_contract must be an object")
        return
    for key, value in contract.items():
        if value is None or not isinstance(value, str):
            continue
        target = pack_root / value
        if not target.exists():
            errors.append(f"{pack_root}: directory_contract.{key} points to missing path `{value}`")


def _validate_pack_documents(pack_root: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    schema_root = pack_root.parents[1] / "docs/specs/project-pack-factory/schemas"
    for relative_path, schema_name in SCHEMA_BY_RELATIVE_PATH.items():
        document_path = pack_root / relative_path
        if not document_path.exists():
            if relative_path == "lineage/source-template.json" and manifest.get("pack_kind") != "build_pack":
                continue
            errors.append(f"{document_path}: required pack document is missing")
            continue
        errors.extend(validate_json_document(document_path, schema_root / schema_name))

    retirement_state = _load_object(pack_root / "status/retirement.json")
    report_path = retirement_state.get("retirement_report_path")
    if isinstance(report_path, str):
        errors.extend(
            validate_json_document(
                pack_root / report_path,
                schema_root / "retirement-report.schema.json",
            )
        )


def _state_snapshot(pack_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    lifecycle = _load_object(pack_root / "status/lifecycle.json")
    readiness = _load_object(pack_root / "status/readiness.json")
    deployment = _load_object(pack_root / "status/deployment.json")
    retirement = _load_object(pack_root / "status/retirement.json")
    return lifecycle, readiness, deployment, retirement


def _check_active_registry(entry: dict[str, Any], registry_path: Path, errors: list[str]) -> None:
    if entry.get("active") is not True:
        errors.append(f"{registry_path}: active pack `{entry.get('pack_id')}` must set active=true")
    if entry.get("retirement_state") != "active":
        errors.append(f"{registry_path}: active pack `{entry.get('pack_id')}` must set retirement_state=active")
    if entry.get("retired_at") is not None:
        errors.append(f"{registry_path}: active pack `{entry.get('pack_id')}` must set retired_at=null")
    if entry.get("retirement_file") != "status/retirement.json":
        errors.append(
            f"{registry_path}: active pack `{entry.get('pack_id')}` must set retirement_file=status/retirement.json"
        )


def _check_retired_registry(entry: dict[str, Any], retired_at: str, registry_path: Path, errors: list[str]) -> None:
    if entry.get("active") is not False:
        errors.append(f"{registry_path}: retired pack `{entry.get('pack_id')}` must set active=false")
    if entry.get("retirement_state") != "retired":
        errors.append(f"{registry_path}: retired pack `{entry.get('pack_id')}` must set retirement_state=retired")
    if entry.get("retired_at") != retired_at:
        errors.append(f"{registry_path}: retired pack `{entry.get('pack_id')}` retired_at does not match status/retirement.json")
    if entry.get("retirement_file") != "status/retirement.json":
        errors.append(
            f"{registry_path}: retired pack `{entry.get('pack_id')}` must set retirement_file=status/retirement.json"
        )


def _validate_pack_state(
    factory_root: Path,
    pack_root: Path,
    templates_registry: dict[str, dict[str, Any]],
    build_registry: dict[str, dict[str, Any]],
    promotion_log: dict[str, Any],
    errors: list[str],
) -> None:
    manifest = _load_object(pack_root / "pack.json")
    pack_id = manifest.get("pack_id")
    pack_kind = manifest.get("pack_kind")
    lifecycle, readiness, deployment, retirement = _state_snapshot(pack_root)
    _validate_contract_paths(pack_root, manifest, errors)
    _validate_pack_documents(pack_root, manifest, errors)

    registry_path = factory_root / ("registry/templates.json" if pack_kind == "template_pack" else "registry/build-packs.json")
    registry_map = templates_registry if pack_kind == "template_pack" else build_registry
    entry = registry_map.get(str(pack_id))
    if entry is None:
        errors.append(f"{registry_path}: missing registry entry for `{pack_id}`")
        return

    pack_root_relative = f"{pack_root.parent.name}/{pack_root.name}"
    if entry.get("pack_root") != pack_root_relative:
        errors.append(f"{registry_path}: `{pack_id}` pack_root must equal `{pack_root_relative}`")
    latest_eval_index = entry.get("latest_eval_index")
    if isinstance(latest_eval_index, str) and not (factory_root / latest_eval_index).exists():
        errors.append(f"{registry_path}: `{pack_id}` latest_eval_index points to missing path `{latest_eval_index}`")

    retirement_state = retirement.get("retirement_state")
    if retirement.get("pack_id") != pack_id:
        errors.append(f"{pack_root / 'status/retirement.json'}: pack_id does not match pack.json")
    if retirement.get("pack_kind") != pack_kind:
        errors.append(f"{pack_root / 'status/retirement.json'}: pack_kind does not match pack.json")

    superseded_by = retirement.get("superseded_by_pack_id")
    if isinstance(superseded_by, str):
        if superseded_by == pack_id:
            errors.append(f"{pack_root / 'status/retirement.json'}: superseded_by_pack_id must not equal pack_id")
        if superseded_by not in templates_registry and superseded_by not in build_registry:
            errors.append(f"{pack_root / 'status/retirement.json'}: superseded_by_pack_id `{superseded_by}` is not registered")

    if retirement_state == "active":
        if retirement.get("retired_at") is not None:
            errors.append(f"{pack_root / 'status/retirement.json'}: active pack must set retired_at=null")
        if retirement.get("retirement_report_path") is not None:
            errors.append(f"{pack_root / 'status/retirement.json'}: active pack must set retirement_report_path=null")
        if retirement.get("removed_deployment_pointer_paths") != []:
            errors.append(f"{pack_root / 'status/retirement.json'}: active pack must not list removed deployment pointers")
        _check_active_registry(entry, registry_path, errors)
        return

    retired_at = retirement.get("retired_at")
    if lifecycle.get("lifecycle_stage") != "retired":
        errors.append(f"{pack_root / 'status/lifecycle.json'}: retired pack must set lifecycle_stage=retired")
    if lifecycle.get("promotion_target") != "none":
        errors.append(f"{pack_root / 'status/lifecycle.json'}: retired pack must set promotion_target=none")
    if readiness.get("readiness_state") != "retired":
        errors.append(f"{pack_root / 'status/readiness.json'}: retired pack must set readiness_state=retired")
    if readiness.get("ready_for_deployment") is not False:
        errors.append(f"{pack_root / 'status/readiness.json'}: retired pack must set ready_for_deployment=false")
    _check_retired_registry(entry, str(retired_at), registry_path, errors)

    report_relative = retirement.get("retirement_report_path")
    if not isinstance(report_relative, str):
        errors.append(f"{pack_root / 'status/retirement.json'}: retired pack must set retirement_report_path")
        return
    report_path = pack_root / report_relative
    if not report_path.exists():
        errors.append(f"{report_path}: retirement report is missing")
        return
    report = _load_object(report_path)

    if report.get("generated_at") != retired_at:
        errors.append(f"{report_path}: generated_at must match status/retirement.json retired_at")
    if report.get("pack_id") != pack_id:
        errors.append(f"{report_path}: pack_id does not match pack.json")
    if report.get("pack_kind") != pack_kind:
        errors.append(f"{report_path}: pack_kind does not match pack.json")
    if report.get("pack_root") != pack_root_relative:
        errors.append(f"{report_path}: pack_root must equal `{pack_root_relative}`")

    post_state = report.get("post_retirement_state", {})
    if post_state.get("lifecycle_stage") != "retired":
        errors.append(f"{report_path}: post_retirement_state.lifecycle_stage must be retired")
    if post_state.get("readiness_state") != "retired":
        errors.append(f"{report_path}: post_retirement_state.readiness_state must be retired")
    if post_state.get("deployment_state") != "not_deployed":
        errors.append(f"{report_path}: post_retirement_state.deployment_state must be not_deployed")
    if post_state.get("active_environment") != "none":
        errors.append(f"{report_path}: post_retirement_state.active_environment must be none")
    if post_state.get("deployment_pointer_path") is not None:
        errors.append(f"{report_path}: post_retirement_state.deployment_pointer_path must be null")
    if post_state.get("retirement_state") != "retired":
        errors.append(f"{report_path}: post_retirement_state.retirement_state must be retired")

    actions = report.get("actions", [])
    if not actions or actions[-1].get("action_id") != "write_retirement_report":
        errors.append(f"{report_path}: write_retirement_report must be the last recorded action")
    for evidence_path in report.get("evidence_paths", []):
        if not isinstance(evidence_path, str) or not (factory_root / evidence_path).exists():
            errors.append(f"{report_path}: evidence path `{evidence_path}` does not exist")

    matching_events = [
        event
        for event in promotion_log.get("events", [])
        if isinstance(event, dict)
        and event.get("event_type") == "retired"
        and event.get("retired_pack_id") == pack_id
        and event.get("retirement_report_path") == report_relative
    ]
    if not matching_events:
        errors.append(f"{factory_root / 'registry/promotion-log.json'}: missing retired event for `{pack_id}` with report `{report_relative}`")

    if pack_kind == "build_pack":
        if deployment.get("deployment_state") != "not_deployed":
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must set deployment_state=not_deployed")
        if deployment.get("active_environment") != "none":
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must set active_environment=none")
        if deployment.get("active_release_id") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear active_release_id")
        if deployment.get("active_release_path") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear active_release_path")
        if deployment.get("deployment_pointer_path") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear deployment_pointer_path")
        if deployment.get("deployment_transaction_id") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear deployment_transaction_id")
        if deployment.get("projection_state") != "not_required":
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must set projection_state=not_required")
        if deployment.get("last_promoted_at") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear last_promoted_at")
        if deployment.get("last_verified_at") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear last_verified_at")
        for environment in DEPLOYMENT_ENVIRONMENTS:
            pointer_path = factory_root / "deployments" / environment / f"{pack_id}.json"
            if pointer_path.exists():
                errors.append(f"{pointer_path}: retired build pack must not keep active deployment pointers")


def _validate_template_creation_events(
    factory_root: Path,
    templates_registry: dict[str, dict[str, Any]],
    promotion_log: dict[str, Any],
    errors: list[str],
) -> None:
    schema_root = factory_root / "docs/specs/project-pack-factory/schemas"
    events = promotion_log.get("events", [])
    if not isinstance(events, list):
        errors.append(f"{factory_root / 'registry/promotion-log.json'}: events must be an array")
        return

    for event in events:
        if not isinstance(event, dict) or event.get("event_type") != "template_created":
            continue
        template_pack_id = event.get("template_pack_id")
        creation_id = event.get("creation_id")
        report_relative = event.get("template_creation_report_path")
        if not isinstance(template_pack_id, str):
            errors.append(f"{factory_root / 'registry/promotion-log.json'}: template_created event must include template_pack_id")
            continue
        if not isinstance(creation_id, str):
            errors.append(f"{factory_root / 'registry/promotion-log.json'}: template_created event for `{template_pack_id}` must include creation_id")
            continue
        if not isinstance(report_relative, str):
            errors.append(f"{factory_root / 'registry/promotion-log.json'}: template_created event for `{template_pack_id}` must include template_creation_report_path")
            continue

        entry = templates_registry.get(template_pack_id)
        if entry is None:
            errors.append(f"{factory_root / 'registry/promotion-log.json'}: template_created event references unknown template `{template_pack_id}`")
            continue
        pack_root_relative = entry.get("pack_root")
        if not isinstance(pack_root_relative, str):
            errors.append(f"{factory_root / 'registry/templates.json'}: template `{template_pack_id}` is missing pack_root")
            continue
        report_path = factory_root / pack_root_relative / report_relative
        if not report_path.exists():
            errors.append(f"{report_path}: template creation report referenced by promotion log is missing")
            continue

        errors.extend(
            validate_json_document(
                report_path,
                schema_root / "template-creation-report.schema.json",
            )
        )
        report = _load_object(report_path)
        if report.get("creation_id") != creation_id:
            errors.append(f"{report_path}: creation_id does not match registry/promotion-log.json")
        if report.get("template_pack_id") != template_pack_id:
            errors.append(f"{report_path}: template_pack_id does not match registry/promotion-log.json")
        artifact_paths = report.get("artifact_paths", {})
        if artifact_paths.get("template_root") != pack_root_relative:
            errors.append(f"{report_path}: artifact_paths.template_root must equal `{pack_root_relative}`")
        expected_report_artifact = f"{pack_root_relative}/{report_relative}"
        if artifact_paths.get("creation_report") != expected_report_artifact:
            errors.append(f"{report_path}: artifact_paths.creation_report must equal `{expected_report_artifact}`")
        if entry.get("lifecycle_stage") != "maintained":
            errors.append(f"{factory_root / 'registry/templates.json'}: created template `{template_pack_id}` must set lifecycle_stage=maintained")
        if entry.get("ready_for_deployment") is not False:
            errors.append(f"{factory_root / 'registry/templates.json'}: created template `{template_pack_id}` must set ready_for_deployment=false")
        active_set = _load_object(factory_root / pack_root_relative / "benchmarks/active-set.json")
        active_benchmark_ids = [
            benchmark.get("benchmark_id")
            for benchmark in active_set.get("active_benchmarks", [])
            if isinstance(benchmark, dict)
        ]
        if entry.get("active_benchmark_ids") != active_benchmark_ids:
            errors.append(f"{factory_root / 'registry/templates.json'}: created template `{template_pack_id}` active_benchmark_ids must match benchmarks/active-set.json")
        notes = entry.get("notes")
        if not isinstance(notes, list) or not any(isinstance(note, str) and creation_id in note for note in notes):
            errors.append(f"{factory_root / 'registry/templates.json'}: created template `{template_pack_id}` notes must include the creation_id")
        factory_mutations = report.get("factory_mutations", {})
        if factory_mutations.get("registry_updated") is not True:
            errors.append(f"{report_path}: factory_mutations.registry_updated must be true")
        if factory_mutations.get("operation_log_updated") is not True:
            errors.append(f"{report_path}: factory_mutations.operation_log_updated must be true")
        if event.get("status") == "completed" and factory_mutations.get("post_write_factory_validation") != "pass":
            errors.append(f"{report_path}: factory_mutations.post_write_factory_validation must be pass for completed template_created events")


def validate_factory(factory_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    schema_root = factory_root / "docs/specs/project-pack-factory/schemas"
    schema_files = sorted(schema_root.glob("*.schema.json"))
    for schema_file in schema_files:
        errors.extend(validate_schema_file(schema_file))

    registry_templates = _load_registry_map(factory_root / "registry/templates.json")
    registry_builds = _load_registry_map(factory_root / "registry/build-packs.json")
    promotion_log = _load_object(factory_root / "registry/promotion-log.json")

    for pack_root in _iter_pack_roots(factory_root):
        _validate_pack_state(factory_root, pack_root, registry_templates, registry_builds, promotion_log, errors)

    _validate_template_creation_events(factory_root, registry_templates, promotion_log, errors)

    known_pack_ids = {pack_root.name for pack_root in _iter_pack_roots(factory_root)}
    for registry_path, registry_map in (
        (factory_root / "registry/templates.json", registry_templates),
        (factory_root / "registry/build-packs.json", registry_builds),
    ):
        for pack_id in registry_map:
            if pack_id not in known_pack_ids:
                errors.append(f"{registry_path}: registry entry `{pack_id}` does not have a matching pack directory")

    pointer_schema = schema_root / "deployment-pointer.schema.json"
    for environment in DEPLOYMENT_ENVIRONMENTS:
        deployment_dir = factory_root / "deployments" / environment
        if not deployment_dir.exists():
            errors.append(f"{deployment_dir}: deployment directory is missing")
            continue
        for pointer in sorted(deployment_dir.glob("*.json")):
            errors.extend(validate_json_document(pointer, pointer_schema))

    return {
        "factory_root": str(factory_root),
        "schema_files_checked": len(schema_files),
        "pack_count": len(_iter_pack_roots(factory_root)),
        "error_count": len(errors),
        "errors": errors,
        "valid": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PackFactory state against PackFactory contracts.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory root.")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    args = parser.parse_args()

    result = validate_factory(resolve_factory_root(args.factory_root))
    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if result["valid"]:
            print(f"VALID: {result['pack_count']} packs and {result['schema_files_checked']} schemas passed")
        else:
            print(f"INVALID: {result['error_count']} errors")
            for error in result["errors"]:
                print(f"- {error}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
