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

from factory_ops import resolve_factory_root, schema_path, validate_json_document, write_json
from import_external_runtime_evidence import import_external_runtime_evidence
from prepare_remote_autonomy_target import prepare_remote_autonomy_target
from pull_remote_runtime_evidence import pull_remote_runtime_evidence
from push_build_pack_to_remote import push_build_pack_to_remote
from remote_autonomy_roundtrip_common import (
    REMOTE_ROUNDTRIP_MANIFEST_SCHEMA_VERSION,
    canonical_json_text,
    load_remote_autonomy_test_request,
    sha256_path,
    sha256_text,
    sha256_tree,
    write_validated_roundtrip_manifest,
)
from run_remote_autonomy_loop import run_remote_autonomy_loop


IMPORT_REQUEST_SCHEMA_NAME = "external-runtime-evidence-import-request.schema.json"


def _validate_import_request(factory_root: Path, path: Path) -> None:
    errors = validate_json_document(path, schema_path(factory_root, IMPORT_REQUEST_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))


def run_remote_autonomy_test(factory_root: Path, request_path: Path) -> dict[str, Any]:
    wrapper_request = load_remote_autonomy_test_request(factory_root=factory_root, request_path=request_path)
    remote_request = wrapper_request.remote_run_request
    if wrapper_request.import_bundle and not wrapper_request.pull_bundle:
        raise ValueError("v1 wrapper requires pull_bundle=true when import_bundle=true")
    if wrapper_request.local_bundle_staging_dir.exists() and any(wrapper_request.local_bundle_staging_dir.iterdir()):
        raise ValueError(
            f"local_bundle_staging_dir must be empty before the roundtrip run: {wrapper_request.local_bundle_staging_dir}"
        )

    wrapper_request_sha256 = sha256_text(canonical_json_text(wrapper_request.raw_payload))
    remote_run_request_sha256 = sha256_text(canonical_json_text(remote_request.raw_payload))

    preparation_result = prepare_remote_autonomy_target(factory_root, wrapper_request.remote_run_request_path)
    staging_result = push_build_pack_to_remote(factory_root, wrapper_request.remote_run_request_path, transport="auto")
    execution_result = run_remote_autonomy_loop(factory_root, wrapper_request.remote_run_request_path)

    pulled_bundle_path: str | None = None
    pulled_bundle_sha256: str | None = None
    pulled_at: str | None = None
    target_manifest_sha256 = execution_result["target_manifest_sha256"]
    execution_manifest_sha256: str | None = None
    portable_helper_manifest_sha256: str | None = None
    generated_import_request_path: str | None = None
    generated_import_request_sha256: str | None = None
    import_report_path: str | None = None
    pull_result: dict[str, Any] | None = None
    import_result: dict[str, Any] | None = None

    if wrapper_request.pull_bundle:
        pull_result = pull_remote_runtime_evidence(
            factory_root,
            wrapper_request.remote_run_request_path,
            local_bundle_staging_dir=wrapper_request.local_bundle_staging_dir,
            transport="auto",
        )
        if pull_result["source_build_pack_id"] != remote_request.source_build_pack_id:
            raise ValueError("pull result source_build_pack_id does not match the selected remote run request")
        if pull_result["run_id"] != remote_request.run_id:
            raise ValueError("pull result run_id does not match the selected remote run request")
        if pull_result["remote_target_label"] != remote_request.remote_target_label:
            raise ValueError("pull result remote_target_label does not match the selected remote run request")
        if pull_result["target_manifest_sha256"] != target_manifest_sha256:
            raise ValueError("pull result target_manifest_sha256 does not match the execution result")

        execution_manifest_sha256 = str(pull_result["execution_manifest_sha256"])
        portable_helper_manifest_sha256 = pull_result["portable_helper_manifest_sha256"]
        pulled_bundle_path = str(pull_result["local_bundle_root"])
        pulled_bundle_sha256 = str(pull_result["pulled_bundle_sha256"])
        pulled_at = str(pull_result["pulled_at"])

        if pulled_bundle_sha256 != sha256_tree(Path(pulled_bundle_path)):
            raise ValueError("pulled bundle sha256 does not match the staged local bundle directory")

        if wrapper_request.import_bundle:
            import_request_path = wrapper_request.local_bundle_staging_dir / "generated-import-request.json"
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

    roundtrip_manifest_path = wrapper_request.local_bundle_staging_dir / "roundtrip-manifest.json"
    roundtrip_manifest = {
        "schema_version": REMOTE_ROUNDTRIP_MANIFEST_SCHEMA_VERSION,
        "wrapper_request_sha256": wrapper_request_sha256,
        "remote_run_request_sha256": remote_run_request_sha256,
        "source_build_pack_id": remote_request.source_build_pack_id,
        "run_id": remote_request.run_id,
        "remote_target_label": remote_request.remote_target_label,
        "target_manifest_sha256": target_manifest_sha256,
        "execution_manifest_sha256": execution_manifest_sha256,
        "portable_helper_manifest_sha256": portable_helper_manifest_sha256,
        "pulled_bundle_path": pulled_bundle_path,
        "pulled_bundle_sha256": pulled_bundle_sha256,
        "pulled_at": pulled_at,
        "generated_import_request_path": generated_import_request_path,
        "generated_import_request_sha256": generated_import_request_sha256,
    }
    write_validated_roundtrip_manifest(
        factory_root=factory_root,
        path=roundtrip_manifest_path,
        payload=roundtrip_manifest,
    )

    return {
        "schema_version": "remote-autonomy-test-result/v1",
        "status": "completed",
        "source_build_pack_id": remote_request.source_build_pack_id,
        "run_id": remote_request.run_id,
        "remote_target_label": remote_request.remote_target_label,
        "wrapper_request_path": str(wrapper_request.request_path),
        "remote_run_request_path": str(wrapper_request.remote_run_request_path),
        "local_bundle_staging_dir": str(wrapper_request.local_bundle_staging_dir),
        "preparation_result": preparation_result,
        "staging_result": staging_result,
        "execution_result": execution_result,
        "pull_result": pull_result,
        "import_result": import_result,
        "roundtrip_manifest_path": str(roundtrip_manifest_path),
        "import_report_path": import_report_path,
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
