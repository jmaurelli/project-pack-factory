#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import resolve_factory_root, schema_path, validate_json_document, write_json
from import_external_runtime_evidence import import_external_runtime_evidence
from prepare_remote_autonomy_target import prepare_remote_autonomy_target
from pull_remote_runtime_evidence import pull_remote_runtime_evidence
from push_build_pack_to_remote import push_build_pack_to_remote
from remote_autonomy_roundtrip_common import (
    REMOTE_ROUNDTRIP_MANIFEST_SCHEMA_VERSION,
    canonical_json_text,
    canonical_local_roundtrip_artifacts_dir,
    load_remote_autonomy_test_request,
    promote_roundtrip_audit_artifacts,
    sha256_path,
    sha256_text,
    sha256_tree,
    write_validated_roundtrip_manifest,
)
from remote_autonomy_staging_common import write_validated_scratch_lifecycle_manifest
from run_remote_autonomy_loop import run_remote_autonomy_loop


IMPORT_REQUEST_SCHEMA_NAME = "external-runtime-evidence-import-request.schema.json"
SCRATCH_LIFECYCLE_FILENAME = "scratch-lifecycle.json"
TIMEOUT_PULLBACK_DELAY_ENV = "PACKFACTORY_REMOTE_TIMEOUT_PULLBACK_DELAY_SECONDS"
DEFAULT_TIMEOUT_PULLBACK_DELAY_SECONDS = 30.0
TIMEOUT_ERROR_PREFIX = "remote command timed out after"
MANIFEST_ONLY_PULL_ERROR = "execution manifest export_status must be succeeded before pullback"


def _validate_import_request(factory_root: Path, path: Path) -> None:
    errors = validate_json_document(path, schema_path(factory_root, IMPORT_REQUEST_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))


def _is_timeout_error(exc: RuntimeError) -> bool:
    return str(exc).startswith(TIMEOUT_ERROR_PREFIX)


def _timeout_pullback_delay_seconds() -> float:
    value = os.environ.get(TIMEOUT_PULLBACK_DELAY_ENV)
    if value is None:
        return DEFAULT_TIMEOUT_PULLBACK_DELAY_SECONDS
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{TIMEOUT_PULLBACK_DELAY_ENV} must be numeric when set") from exc
    if parsed <= 0:
        raise ValueError(f"{TIMEOUT_PULLBACK_DELAY_ENV} must be greater than zero when set")
    return parsed


def _roundtrip_artifacts_root(wrapper_request) -> Path:
    return canonical_local_roundtrip_artifacts_dir(
        wrapper_request.factory_root,
        wrapper_request.remote_run_request.remote_target_label,
        wrapper_request.remote_run_request.source_build_pack_id,
        wrapper_request.remote_run_request.run_id,
    )


def _scratch_lifecycle_path(local_stage_dir: Path) -> Path:
    return local_stage_dir / SCRATCH_LIFECYCLE_FILENAME


def _unexpected_stage_entries(local_stage_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in local_stage_dir.iterdir()
        if path.name != SCRATCH_LIFECYCLE_FILENAME
    )


def _write_scratch_lifecycle_marker(*, local_stage_dir: Path, wrapper_request, status: str) -> None:
    write_validated_scratch_lifecycle_manifest(
        factory_root=wrapper_request.factory_root,
        path=_scratch_lifecycle_path(local_stage_dir),
        payload={
            "schema_version": "scratch-lifecycle/v1",
            "status": status,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "factory_root": str(wrapper_request.factory_root),
            "local_scratch_root": str(wrapper_request.local_scratch_root),
            "local_stage_root": str(local_stage_dir),
            "run_id": wrapper_request.remote_run_request.run_id,
            "source_build_pack_id": wrapper_request.remote_run_request.source_build_pack_id,
            "remote_target_label": wrapper_request.remote_run_request.remote_target_label,
            "remote_pack_dir": wrapper_request.remote_run_request.remote_pack_dir,
            "remote_run_dir": wrapper_request.remote_run_request.remote_run_dir,
            "remote_export_dir": wrapper_request.remote_run_request.remote_export_dir,
        },
    )


def _recover_manifest_only_pull_result(*, local_stage_dir: Path, remote_request) -> dict[str, Any]:
    execution_manifest_path = local_stage_dir / "execution-manifest.json"
    target_manifest_path = local_stage_dir / "target-manifest.json"
    if not execution_manifest_path.exists() or not target_manifest_path.exists():
        raise RuntimeError("manifest-only recovery requires local execution-manifest.json and target-manifest.json")
    execution_manifest = json.loads(execution_manifest_path.read_text(encoding="utf-8"))
    target_manifest = json.loads(target_manifest_path.read_text(encoding="utf-8"))
    if not isinstance(execution_manifest, dict) or not isinstance(target_manifest, dict):
        raise RuntimeError("manifest-only recovery requires JSON object manifests")
    return {
        "status": "manifest_only",
        "source_build_pack_id": remote_request.source_build_pack_id,
        "run_id": remote_request.run_id,
        "remote_target_label": remote_request.remote_target_label,
        "local_target_manifest_path": str(target_manifest_path),
        "target_manifest_sha256": sha256_path(target_manifest_path),
        "local_execution_manifest_path": str(execution_manifest_path),
        "execution_manifest_sha256": sha256_path(execution_manifest_path),
        "execution_manifest": execution_manifest,
        "target_manifest": target_manifest,
        "local_bundle_root": None,
        "pulled_bundle_sha256": None,
        "pulled_at": None,
        "transport_mode": None,
        "bundle_generated_at": None,
        "portable_helper_manifest_sha256": None,
    }


def _execution_result_from_timeout_recovery(*, remote_request, pull_result: dict[str, Any], execution_timeout_error: str | None) -> dict[str, Any]:
    target_manifest_sha256 = pull_result["target_manifest_sha256"]
    local_execution_manifest_path = pull_result["local_execution_manifest_path"]
    if pull_result.get("status") == "manifest_only":
        execution_manifest = pull_result.get("execution_manifest")
        if not isinstance(execution_manifest, dict):
            raise RuntimeError("manifest-only recovery requires execution_manifest")
        return {
            "status": "recovered_after_timeout",
            "source_build_pack_id": remote_request.source_build_pack_id,
            "run_id": remote_request.run_id,
            "remote_target_label": remote_request.remote_target_label,
            "target_manifest_sha256": target_manifest_sha256,
            "terminal_outcome": execution_manifest.get("terminal_outcome"),
            "terminal_reason": execution_manifest.get("terminal_reason"),
            "boundary_violations": [],
            "changed_paths": [],
            "execution_manifest_path": local_execution_manifest_path,
            "prompt_sha256": None,
            "prompt_artifact_path": None,
            "export_status": execution_manifest.get("export_status"),
            "export_bundle_path": execution_manifest.get("export_bundle_path"),
            "exported_run_id": execution_manifest.get("exported_run_id"),
            "timeout_recovery": {
                "recovered_after_timeout": True,
                "controller_error": execution_timeout_error,
                "pullback_delay_seconds": _timeout_pullback_delay_seconds(),
            },
        }
    return {
        "status": "recovered_after_timeout",
        "source_build_pack_id": remote_request.source_build_pack_id,
        "run_id": remote_request.run_id,
        "remote_target_label": remote_request.remote_target_label,
        "target_manifest_sha256": target_manifest_sha256,
        "terminal_outcome": "controller_timeout_recovered_by_pullback",
        "terminal_reason": "pullback_recovered_after_controller_timeout",
        "boundary_violations": [],
        "changed_paths": [],
        "execution_manifest_path": local_execution_manifest_path,
        "prompt_sha256": None,
        "prompt_artifact_path": None,
        "export_status": "succeeded",
        "export_bundle_path": pull_result["local_bundle_root"],
        "exported_run_id": remote_request.run_id,
        "timeout_recovery": {
            "recovered_after_timeout": True,
            "controller_error": execution_timeout_error,
            "pullback_delay_seconds": _timeout_pullback_delay_seconds(),
        },
    }


def run_remote_autonomy_test(factory_root: Path, request_path: Path) -> dict[str, Any]:
    wrapper_request = load_remote_autonomy_test_request(factory_root=factory_root, request_path=request_path)
    remote_request = wrapper_request.remote_run_request
    if wrapper_request.import_bundle and not wrapper_request.pull_bundle:
        raise ValueError("v1 wrapper requires pull_bundle=true when import_bundle=true")
    if (
        wrapper_request.local_bundle_staging_dir.exists()
        and _unexpected_stage_entries(wrapper_request.local_bundle_staging_dir)
    ):
        raise ValueError(
            f"local_bundle_staging_dir must be empty before the roundtrip run: {wrapper_request.local_bundle_staging_dir}"
        )

    wrapper_request_sha256 = sha256_text(canonical_json_text(wrapper_request.raw_payload))
    remote_run_request_sha256 = sha256_text(canonical_json_text(remote_request.raw_payload))

    preparation_result = prepare_remote_autonomy_target(factory_root, wrapper_request.remote_run_request_path)
    staging_result = push_build_pack_to_remote(factory_root, wrapper_request.remote_run_request_path, transport="auto")
    execution_result: dict[str, Any] | None = None
    execution_timeout_error: str | None = None
    _write_scratch_lifecycle_marker(
        local_stage_dir=wrapper_request.local_bundle_staging_dir,
        wrapper_request=wrapper_request,
        status="pull_pending",
    )
    try:
        execution_result = run_remote_autonomy_loop(factory_root, wrapper_request.remote_run_request_path)
    except RuntimeError as exc:
        if not _is_timeout_error(exc):
            raise
        if not wrapper_request.pull_bundle:
            raise
        execution_timeout_error = str(exc)
        time.sleep(_timeout_pullback_delay_seconds())

    pulled_bundle_path: str | None = None
    pulled_bundle_sha256: str | None = None
    pulled_at: str | None = None
    checkpoint_artifact_root: str | None = None
    checkpoint_artifact_paths: list[str] = []
    checkpoint_missing_paths: list[str] = []
    target_manifest_sha256 = execution_result["target_manifest_sha256"] if execution_result is not None else None
    execution_manifest_sha256: str | None = None
    portable_helper_manifest_sha256: str | None = None
    generated_import_request_path: str | None = None
    generated_import_request_sha256: str | None = None
    import_report_path: str | None = None
    pull_result: dict[str, Any] | None = None
    import_result: dict[str, Any] | None = None
    roundtrip_artifacts_root = _roundtrip_artifacts_root(wrapper_request)
    roundtrip_artifacts_root.mkdir(parents=True, exist_ok=True)
    durable_audit_artifacts: dict[str, str] = {}

    if wrapper_request.pull_bundle:
        try:
            pull_result = pull_remote_runtime_evidence(
                factory_root,
                wrapper_request.remote_run_request_path,
                local_bundle_staging_dir=wrapper_request.local_bundle_staging_dir,
                transport="auto",
            )
        except ValueError as exc:
            if str(exc) != MANIFEST_ONLY_PULL_ERROR:
                raise
            pull_result = _recover_manifest_only_pull_result(
                local_stage_dir=wrapper_request.local_bundle_staging_dir,
                remote_request=remote_request,
            )
        if pull_result["source_build_pack_id"] != remote_request.source_build_pack_id:
            raise ValueError("pull result source_build_pack_id does not match the selected remote run request")
        if pull_result["run_id"] != remote_request.run_id:
            raise ValueError("pull result run_id does not match the selected remote run request")
        if pull_result["remote_target_label"] != remote_request.remote_target_label:
            raise ValueError("pull result remote_target_label does not match the selected remote run request")
        if target_manifest_sha256 is not None and pull_result["target_manifest_sha256"] != target_manifest_sha256:
            raise ValueError("pull result target_manifest_sha256 does not match the execution result")
        if execution_result is None:
            target_manifest_sha256 = pull_result["target_manifest_sha256"]
            execution_result = _execution_result_from_timeout_recovery(
                remote_request=remote_request,
                pull_result=pull_result,
                execution_timeout_error=execution_timeout_error,
            )

        execution_manifest_sha256 = str(pull_result["execution_manifest_sha256"])
        portable_helper_manifest_sha256 = pull_result["portable_helper_manifest_sha256"]
        local_bundle_root = pull_result["local_bundle_root"]
        if local_bundle_root is not None:
            pulled_bundle_path = str(local_bundle_root)
        local_bundle_sha256 = pull_result["pulled_bundle_sha256"]
        if local_bundle_sha256 is not None:
            pulled_bundle_sha256 = str(local_bundle_sha256)
        local_pulled_at = pull_result["pulled_at"]
        if local_pulled_at is not None:
            pulled_at = str(local_pulled_at)
        local_checkpoint_artifact_root = pull_result.get("local_checkpoint_artifact_root")
        if local_checkpoint_artifact_root is not None:
            checkpoint_artifact_root = str(local_checkpoint_artifact_root)
        raw_checkpoint_artifact_paths = pull_result.get("checkpoint_artifact_paths", [])
        if isinstance(raw_checkpoint_artifact_paths, list):
            checkpoint_artifact_paths = [str(path) for path in raw_checkpoint_artifact_paths]
        raw_checkpoint_missing_paths = pull_result.get("checkpoint_missing_paths", [])
        if isinstance(raw_checkpoint_missing_paths, list):
            checkpoint_missing_paths = [str(path) for path in raw_checkpoint_missing_paths]

        if pulled_bundle_path is not None and pulled_bundle_sha256 is not None:
            if pulled_bundle_sha256 != sha256_tree(Path(pulled_bundle_path)):
                raise ValueError("pulled bundle sha256 does not match the staged local bundle directory")

        durable_audit_artifacts = promote_roundtrip_audit_artifacts(
            local_stage_dir=wrapper_request.local_bundle_staging_dir,
            durable_artifacts_dir=roundtrip_artifacts_root,
        )

        if wrapper_request.import_bundle and pulled_bundle_path is not None:
            import_request_path = roundtrip_artifacts_root / "generated-import-request.json"
            import_request_payload = {
                "schema_version": "external-runtime-evidence-import-request/v1",
                "build_pack_id": remote_request.source_build_pack_id,
                "bundle_manifest_path": str(Path(pulled_bundle_path) / "bundle.json"),
                "import_reason": wrapper_request.import_reason,
                "imported_by": wrapper_request.imported_by,
            }
            write_json(import_request_path, import_request_payload)
            _validate_import_request(factory_root, import_request_path)
            generated_import_request_path = str(import_request_path)
            generated_import_request_sha256 = sha256_path(import_request_path)
            import_result = import_external_runtime_evidence(
                factory_root,
                import_request_payload,
                request_file_dir=import_request_path.parent.resolve(),
            )
            import_report_path = str(import_result["import_report_path"])
    elif execution_timeout_error is not None:
        raise RuntimeError(execution_timeout_error)

    if execution_result is None:
        raise RuntimeError("remote execution did not produce an execution result")
    if target_manifest_sha256 is None:
        raise RuntimeError("remote execution did not resolve target_manifest_sha256")
    checkpoint_recovered_without_bundle = pulled_bundle_path is None and checkpoint_artifact_root is not None

    roundtrip_manifest_path = roundtrip_artifacts_root / "roundtrip-manifest.json"
    roundtrip_manifest = {
        "schema_version": REMOTE_ROUNDTRIP_MANIFEST_SCHEMA_VERSION,
        "wrapper_request_sha256": wrapper_request_sha256,
        "remote_run_request_sha256": remote_run_request_sha256,
        "source_build_pack_id": remote_request.source_build_pack_id,
        "run_id": remote_request.run_id,
        "remote_target_label": remote_request.remote_target_label,
        "local_scratch_root": str(wrapper_request.local_scratch_root),
        "local_bundle_staging_dir": str(wrapper_request.local_bundle_staging_dir),
        "local_roundtrip_artifacts_dir": str(roundtrip_artifacts_root),
        "target_manifest_sha256": target_manifest_sha256,
        "execution_manifest_sha256": execution_manifest_sha256,
        "portable_helper_manifest_sha256": portable_helper_manifest_sha256,
        "pulled_bundle_path": pulled_bundle_path,
        "pulled_bundle_sha256": pulled_bundle_sha256,
        "pulled_at": pulled_at,
        "generated_import_request_path": generated_import_request_path,
        "generated_import_request_sha256": generated_import_request_sha256,
        "durable_promoted_artifacts": durable_audit_artifacts,
    }
    write_validated_roundtrip_manifest(
        factory_root=factory_root,
        path=roundtrip_manifest_path,
        payload=roundtrip_manifest,
    )
    _write_scratch_lifecycle_marker(
        local_stage_dir=wrapper_request.local_bundle_staging_dir,
        wrapper_request=wrapper_request,
        status="cleanup_eligible",
    )

    return {
        "schema_version": "remote-autonomy-test-result/v1",
        "status": "completed" if (pulled_bundle_path is not None or checkpoint_recovered_without_bundle) else "stopped",
        "source_build_pack_id": remote_request.source_build_pack_id,
        "run_id": remote_request.run_id,
        "remote_target_label": remote_request.remote_target_label,
        "wrapper_request_path": str(wrapper_request.request_path),
        "remote_run_request_path": str(wrapper_request.remote_run_request_path),
        "local_bundle_staging_dir": str(wrapper_request.local_bundle_staging_dir),
        "local_scratch_root": str(wrapper_request.local_scratch_root),
        "local_roundtrip_artifacts_dir": str(roundtrip_artifacts_root),
        "preparation_result": preparation_result,
        "staging_result": staging_result,
        "execution_result": execution_result,
        "pull_result": pull_result,
        "import_result": import_result,
        "roundtrip_manifest_path": str(roundtrip_manifest_path),
        "durable_promoted_artifacts": durable_audit_artifacts,
        "local_checkpoint_artifact_root": checkpoint_artifact_root,
        "checkpoint_artifact_paths": checkpoint_artifact_paths,
        "checkpoint_missing_paths": checkpoint_missing_paths,
        "checkpoint_recovered_without_bundle": checkpoint_recovered_without_bundle,
        "generated_import_request_path": generated_import_request_path,
        "generated_import_request_sha256": generated_import_request_sha256,
        "import_report_path": import_report_path,
        "stopped_without_bundle": pulled_bundle_path is None and not checkpoint_recovered_without_bundle,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bounded remote-autonomy roundtrip workflow.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory repository root.")
    parser.add_argument("--request-file", required=True, help="Path to a remote-autonomy-test-request/v1 JSON file.")
    parser.add_argument("--output", default="json", choices=("json",), help="Output format.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    request_path = Path(args.request_file).expanduser().resolve()
    result = run_remote_autonomy_test(factory_root, request_path)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
