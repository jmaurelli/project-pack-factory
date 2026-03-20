#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    PROMOTION_LOG_PATH,
    REGISTRY_BUILD_PATH,
    discover_pack,
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)

PACK_DOCUMENT_SCHEMAS = {
    "pack.json": "pack.schema.json",
    "status/lifecycle.json": "lifecycle.schema.json",
    "status/readiness.json": "readiness.schema.json",
    "status/deployment.json": "deployment.schema.json",
    "status/retirement.json": "retirement.schema.json",
    "benchmarks/active-set.json": "benchmark-active-set.schema.json",
    "eval/latest/index.json": "eval-latest-index.schema.json",
}


COPY_ROOT_NAMES = (
    "AGENTS.md",
    "project-context.md",
    "docs",
    "prompts",
    "contracts",
    "src",
    "tests",
    "benchmarks",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "Makefile",
    ".gitignore",
)
SKIP_ROOT_NAMES = {
    ".pack-state",
    "status",
}
TRANSIENT_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
}


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _load_request(request_path: Path, factory_root: Path) -> dict[str, Any]:
    errors = validate_json_document(
        request_path,
        schema_path(factory_root, "materialization-request.schema.json"),
    )
    if errors:
        raise ValueError("; ".join(errors))
    return _load_object(request_path)


def _copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {name for name in names if name in TRANSIENT_NAMES or name.endswith(".egg-info")}
    ignored.update({"eval"} if "eval" in names else set())
    ignored.update({"dist"} if "dist" in names else set())
    return ignored


def _validate_source_template(factory_root: Path, template_root: Path) -> None:
    errors: list[str] = []
    for relative_document, schema_name in PACK_DOCUMENT_SCHEMAS.items():
        document_path = template_root / relative_document
        if not document_path.exists():
            errors.append(f"missing required template document: {relative_document}")
            continue
        errors.extend(validate_json_document(document_path, schema_path(factory_root, schema_name)))
    if errors:
        raise ValueError("; ".join(errors))


def _gate_id(benchmark_id: str) -> str:
    return benchmark_id.replace("-", "_")


def _build_directory_contract() -> dict[str, Any]:
    return {
        "docs_dir": "docs",
        "prompts_dir": "prompts",
        "contracts_dir": "contracts",
        "source_dir": "src",
        "tests_dir": "tests",
        "benchmarks_dir": "benchmarks",
        "benchmark_active_set_file": "benchmarks/active-set.json",
        "eval_dir": "eval",
        "eval_latest_index_file": "eval/latest/index.json",
        "eval_history_dir": "eval/history",
        "status_dir": "status",
        "lifecycle_file": "status/lifecycle.json",
        "readiness_file": "status/readiness.json",
        "retirement_file": "status/retirement.json",
        "deployment_file": "status/deployment.json",
        "lineage_dir": "lineage",
        "lineage_file": "lineage/source-template.json",
        "dist_dir": "dist",
        "candidate_release_dir": "dist/candidates",
        "immutable_release_dir": "dist/releases",
        "template_export_dir": None,
        "local_state_dir": ".pack-state",
    }


def _copy_template_content(template_root: Path, target_root: Path) -> tuple[list[str], list[str]]:
    copied_paths: list[str] = []
    skipped_paths: list[str] = sorted(SKIP_ROOT_NAMES | {"eval", "dist"})
    for name in COPY_ROOT_NAMES:
        source = template_root / name
        if not source.exists():
            continue
        target = target_root / name
        if source.is_dir():
            shutil.copytree(source, target, ignore=_copy_ignore)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        copied_paths.append(name)
    return copied_paths, skipped_paths


def _synthesize_build_pack(
    *,
    factory_root: Path,
    template_root: Path,
    target_root: Path,
    request: dict[str, Any],
    materialization_id: str,
    generated_at: str,
) -> dict[str, Any]:
    template_manifest = _load_object(template_root / "pack.json")
    template_lifecycle = _load_object(template_root / "status/lifecycle.json")
    template_readiness = _load_object(template_root / "status/readiness.json")
    template_active_set = _load_object(template_root / "benchmarks/active-set.json")

    pack_id = str(request["target_build_pack_id"])
    display_name = str(request["target_display_name"])
    target_version = str(request["target_version"])
    target_revision = str(request["target_revision"])
    materialized_by = str(request["materialized_by"])
    reason = str(request["materialization_reason"])
    source_template_id = str(request["source_template_id"])

    pack_manifest = {
        "schema_version": "pack-manifest/v2",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "display_name": display_name,
        "owning_team": template_manifest["owning_team"],
        "runtime": template_manifest["runtime"],
        "bootstrap_read_order": template_manifest["bootstrap_read_order"],
        "post_bootstrap_read_order": [
            "status/lifecycle.json",
            "status/readiness.json",
            "status/retirement.json",
            "status/deployment.json",
            "lineage/source-template.json",
            "benchmarks/active-set.json",
            "eval/latest/index.json",
        ],
        "entrypoints": template_manifest["entrypoints"],
        "directory_contract": _build_directory_contract(),
        "identity_source": "pack.json",
        "notes": [
            f"Materialized from template `{source_template_id}`.",
            f"materialization_id={materialization_id}",
        ],
    }

    benchmarks = template_active_set.get("active_benchmarks", [])
    if not isinstance(benchmarks, list):
        raise ValueError("benchmarks/active-set.json active_benchmarks must be an array")

    required_gates: list[dict[str, Any]] = [
        {
            "gate_id": "validate_build_pack_contract",
            "mandatory": True,
            "status": "not_run",
            "summary": "Build-pack contract validation has not been executed yet.",
            "last_run_at": None,
            "evidence_paths": [],
        }
    ]
    benchmark_results: list[dict[str, Any]] = []
    report_relative = f"eval/history/{materialization_id}/materialization-report.json"
    for benchmark in benchmarks:
        if not isinstance(benchmark, dict):
            continue
        benchmark_id = str(benchmark["benchmark_id"])
        objective = str(benchmark.get("objective", "Inherited benchmark has not been executed yet."))
        required_gates.append(
            {
                "gate_id": _gate_id(benchmark_id),
                "mandatory": bool(benchmark.get("required_for_readiness", True)),
                "status": "not_run",
                "summary": objective,
                "last_run_at": None,
                "evidence_paths": [],
            }
        )
        benchmark_results.append(
            {
                "benchmark_id": benchmark_id,
                "status": "not_run",
                "latest_run_id": materialization_id,
                "run_artifact_path": report_relative,
                "summary_artifact_path": report_relative,
            }
        )

    lifecycle = {
        "schema_version": "pack-lifecycle/v2",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "lifecycle_stage": "testing",
        "state_reason": reason,
        "current_version": target_version,
        "current_revision": target_revision,
        "promotion_target": "testing",
        "updated_at": generated_at,
        "updated_by": materialized_by,
    }
    readiness = {
        "schema_version": "pack-readiness/v2",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "readiness_state": "in_progress",
        "ready_for_deployment": False,
        "last_evaluated_at": generated_at,
        "blocking_issues": [
            "This build pack has been materialized but has not been evaluated yet."
        ],
        "recommended_next_actions": [
            "Run build-pack validation before promoting this pack.",
            "Execute the inherited benchmark set to establish readiness evidence.",
        ],
        "required_gates": required_gates,
    }
    retirement = {
        "schema_version": "pack-retirement/v1",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "retirement_state": "active",
        "retired_at": None,
        "retired_by": None,
        "retirement_reason": None,
        "superseded_by_pack_id": None,
        "retirement_report_path": None,
        "removed_deployment_pointer_paths": [],
        "retained_artifacts": {
            "eval_history": True,
            "release_artifacts": True,
            "lineage": True,
        },
        "operator_notes": [],
    }
    deployment = {
        "schema_version": "pack-deployment/v2",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "deployment_state": "not_deployed",
        "active_environment": "none",
        "active_release_id": None,
        "active_release_path": None,
        "deployment_pointer_path": None,
        "deployment_transaction_id": None,
        "projection_state": "not_required",
        "last_promoted_at": None,
        "last_verified_at": None,
        "last_rollback": None,
        "deployment_notes": [
            "Newly materialized build pack; no active deployment candidate."
        ],
    }
    template_version = str(template_lifecycle["current_version"])
    template_revision = str(template_lifecycle["current_revision"])
    lineage = {
        "schema_version": "pack-lineage/v2",
        "build_pack_id": pack_id,
        "source_template_id": source_template_id,
        "source_template_version": template_version,
        "source_template_revision": template_revision,
        "derivation_mode": "copied",
        "sync_state": "current",
        "last_sync_at": generated_at,
        "last_sync_summary": f"materialization_id={materialization_id}",
        "inherited_entrypoints": sorted(template_manifest["entrypoints"].keys()),
        "inherited_contracts": sorted(
            path.stem.replace(".schema", "")
            for path in (target_root / "contracts").glob("*")
            if path.is_file()
        ),
    }
    eval_latest = {
        "schema_version": "pack-eval-index/v1",
        "pack_id": pack_id,
        "pack_kind": "build_pack",
        "updated_at": generated_at,
        "benchmark_results": benchmark_results or [
            {
                "benchmark_id": "validate_build_pack_contract",
                "status": "not_run",
                "latest_run_id": materialization_id,
                "run_artifact_path": report_relative,
                "summary_artifact_path": report_relative,
            }
        ],
    }
    return {
        "pack_manifest": pack_manifest,
        "lifecycle": lifecycle,
        "readiness": readiness,
        "retirement": retirement,
        "deployment": deployment,
        "lineage": lineage,
        "eval_latest": eval_latest,
    }


def materialize_build_pack(factory_root: Path, request: dict[str, Any]) -> dict[str, Any]:
    source_template_id = str(request["source_template_id"])
    target_build_pack_id = str(request["target_build_pack_id"])
    materialized_by = str(request["materialized_by"])
    target_version = str(request["target_version"])
    target_revision = str(request["target_revision"])

    source = discover_pack(factory_root, source_template_id)
    if source.pack_kind != "template_pack":
        raise ValueError(f"{source_template_id} is not a template_pack")
    source_retirement = _load_object(source.pack_root / "status/retirement.json")
    source_lifecycle = _load_object(source.pack_root / "status/lifecycle.json")
    if source_retirement.get("retirement_state") != "active":
        raise ValueError("source template is not active")
    if source_lifecycle.get("lifecycle_stage") == "retired":
        raise ValueError("source template is retired")
    _validate_source_template(factory_root, source.pack_root)

    target_root = factory_root / "build-packs" / target_build_pack_id
    if target_root.exists():
        raise ValueError(f"target build pack already exists: {target_build_pack_id}")
    build_registry_path = factory_root / REGISTRY_BUILD_PATH
    build_registry = _load_object(build_registry_path)
    entries = build_registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{build_registry_path}: entries must be an array")
    if any(isinstance(entry, dict) and entry.get("pack_id") == target_build_pack_id for entry in entries):
        raise ValueError(f"target build pack already registered: {target_build_pack_id}")

    now = read_now()
    generated_at = isoformat_z(now)
    materialization_id = f"materialize-{target_build_pack_id}-{timestamp_token(now)}"
    target_root.mkdir(parents=True, exist_ok=False)
    try:
        copied_paths, skipped_paths = _copy_template_content(source.pack_root, target_root)
        for relative_dir in (
            "status",
            "lineage",
            "eval/latest",
            "eval/history",
            "dist/candidates",
            "dist/releases",
            "dist/exports",
            ".pack-state",
        ):
            (target_root / relative_dir).mkdir(parents=True, exist_ok=True)
        state = _synthesize_build_pack(
            factory_root=factory_root,
            template_root=source.pack_root,
            target_root=target_root,
            request=request,
            materialization_id=materialization_id,
            generated_at=generated_at,
        )

        pack_root_relative = f"build-packs/{target_build_pack_id}"
        write_json(target_root / "pack.json", state["pack_manifest"])
        write_json(target_root / "status/lifecycle.json", state["lifecycle"])
        write_json(target_root / "status/readiness.json", state["readiness"])
        write_json(target_root / "status/retirement.json", state["retirement"])
        write_json(target_root / "status/deployment.json", state["deployment"])
        write_json(target_root / "lineage/source-template.json", state["lineage"])
        write_json(target_root / "eval/latest/index.json", state["eval_latest"])

        registry_entry = {
            "active": True,
            "active_release_id": None,
            "deployment_pointer": None,
            "deployment_state": "not_deployed",
            "latest_eval_index": f"{pack_root_relative}/eval/latest/index.json",
            "lifecycle_stage": "testing",
            "notes": [
                f"Derived from template `{source_template_id}` via PackFactory materialization.",
                f"materialization_id={materialization_id}",
            ],
            "pack_id": target_build_pack_id,
            "pack_kind": "build_pack",
            "pack_root": pack_root_relative,
            "ready_for_deployment": False,
            "retirement_file": "status/retirement.json",
            "retirement_state": "active",
            "retired_at": None,
        }
        entries.append(registry_entry)
        build_registry["updated_at"] = generated_at
        write_json(build_registry_path, build_registry)

        promotion_log_path = factory_root / PROMOTION_LOG_PATH
        promotion_log = _load_object(promotion_log_path)
        events = promotion_log.setdefault("events", [])
        if not isinstance(events, list):
            raise ValueError(f"{promotion_log_path}: events must be an array")

        report_relative = Path("eval/history") / materialization_id / "materialization-report.json"
        report = {
            "schema_version": "build-pack-materialization-report/v1",
            "materialization_id": materialization_id,
            "generated_at": generated_at,
            "source_template_id": source_template_id,
            "target_build_pack_id": target_build_pack_id,
            "source_template_root": f"templates/{source_template_id}",
            "target_build_pack_root": pack_root_relative,
            "materialized_by": materialized_by,
            "target_version": target_version,
            "target_revision": target_revision,
            "copy_summary": {
                "copied_paths": copied_paths,
                "skipped_paths": skipped_paths,
            },
            "lineage_path": f"{pack_root_relative}/lineage/source-template.json",
            "registry_update": {
                "registry_path": "registry/build-packs.json",
                "pack_id": target_build_pack_id,
                "lifecycle_stage": "testing",
                "retirement_state": "active",
                "deployment_state": "not_deployed",
            },
            "operation_log_update": {
                "promotion_log_path": "registry/promotion-log.json",
                "event_type": "materialized",
                "materialization_id": materialization_id,
                "target_build_pack_id": target_build_pack_id,
                "materialization_report_path": str(report_relative),
            },
            "actions": [
                {
                    "action_id": "copy_template_content",
                    "status": "completed",
                    "target_path": pack_root_relative,
                    "summary": "Copied bounded template content into the new build pack.",
                },
                {
                    "action_id": "write_build_pack_manifest",
                    "status": "completed",
                    "target_path": f"{pack_root_relative}/pack.json",
                    "summary": "Wrote the schema-valid build-pack manifest.",
                },
                {
                    "action_id": "write_lineage",
                    "status": "completed",
                    "target_path": f"{pack_root_relative}/lineage/source-template.json",
                    "summary": "Recorded template lineage and inherited contract metadata.",
                },
                {
                    "action_id": "write_status_files",
                    "status": "completed",
                    "target_path": f"{pack_root_relative}/status",
                    "summary": "Wrote initial lifecycle, readiness, retirement, and deployment state.",
                },
                {
                    "action_id": "update_registry_entry",
                    "status": "completed",
                    "target_path": "registry/build-packs.json",
                    "summary": "Registered the materialized build pack as active and not deployed.",
                },
                {
                    "action_id": "append_operation_log",
                    "status": "completed",
                    "target_path": "registry/promotion-log.json",
                    "summary": "Appended a materialized event for later agents.",
                },
                {
                    "action_id": "write_materialization_report",
                    "status": "completed",
                    "target_path": f"{pack_root_relative}/{report_relative}",
                    "summary": "Wrote the terminal materialization evidence report.",
                },
            ],
            "evidence_paths": [
                f"{pack_root_relative}/{report_relative}",
                f"{pack_root_relative}/eval/latest/index.json",
                f"{pack_root_relative}/lineage/source-template.json",
            ],
        }

        events.append(
            {
                "event_type": "materialized",
                "materialization_id": materialization_id,
                "source_template_id": source_template_id,
                "target_build_pack_id": target_build_pack_id,
                "materialization_report_path": str(report_relative),
                "status": "completed",
            }
        )
        promotion_log["updated_at"] = generated_at
        write_json(promotion_log_path, promotion_log)
        write_json(target_root / report_relative, report)
    except Exception as exc:
        failure_summary = {
            "materialization_id": materialization_id,
            "generated_at": generated_at,
            "source_template_id": source_template_id,
            "target_build_pack_id": target_build_pack_id,
            "status": "failed",
            "error": str(exc),
        }
        write_json(
            target_root / ".pack-state/failed-operations" / f"{materialization_id}.json",
            failure_summary,
        )
        raise

    return {
        "status": "completed",
        "materialization_id": materialization_id,
        "source_template_id": source_template_id,
        "target_build_pack_id": target_build_pack_id,
        "target_build_pack_root": str(target_root),
        "materialization_report_path": str(target_root / report_relative),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize a build pack from a template pack.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        factory_root = resolve_factory_root(args.factory_root)
        request = _load_request(Path(args.request_file), factory_root)
        payload = materialize_build_pack(factory_root, request)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
