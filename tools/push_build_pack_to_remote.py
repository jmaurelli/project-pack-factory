#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import dump_json, isoformat_z, read_now, resolve_factory_root
from remote_autonomy_staging_common import (
    canonical_local_remote_autonomy_staging_root,
    PAYLOAD_MANIFEST_SCHEMA_NAME,
    PAYLOAD_MANIFEST_SCHEMA_VERSION,
    PAYLOAD_POLICY_VERSION,
    REMOTE_METADATA_DIR,
    REMOTE_REQUEST_FILENAME,
    REMOTE_TARGET_MANIFEST_FILENAME,
    build_control_plane_mutations,
    load_remote_autonomy_request,
    materialize_payload_snapshot,
    push_directory_via_rsync,
    push_file_via_scp,
    run_checked,
    sha256_path,
    write_validated_scratch_lifecycle_manifest,
    write_validated_json,
)


SCRATCH_LIFECYCLE_FILENAME = "scratch-lifecycle.json"


def _transport_mode(requested: str) -> str:
    if requested != "auto":
        return requested
    if shutil.which("rsync"):
        return "rsync"
    if shutil.which("scp"):
        return "scp"
    raise RuntimeError("v1 staging requires either `rsync` or `scp` to be available")


def _canonical_request_text(payload: dict[str, Any]) -> str:
    return dump_json(payload)


def _local_stage_root(local_scratch_root: Path, run_id: str) -> Path:
    return canonical_local_remote_autonomy_staging_root(local_scratch_root, run_id)


def _local_payload_root(stage_root: Path) -> Path:
    return stage_root / "payload"


def _local_manifest_path(stage_root: Path) -> Path:
    return stage_root / REMOTE_TARGET_MANIFEST_FILENAME


def _scratch_lifecycle_path(stage_root: Path) -> Path:
    return stage_root / SCRATCH_LIFECYCLE_FILENAME


def _write_scratch_lifecycle_marker(*, stage_root: Path, request, status: str) -> None:
    write_validated_scratch_lifecycle_manifest(
        factory_root=request.factory_root,
        path=_scratch_lifecycle_path(stage_root),
        payload={
            "schema_version": "scratch-lifecycle/v1",
            "status": status,
            "updated_at": isoformat_z(read_now()),
            "factory_root": str(request.factory_root),
            "local_scratch_root": str(request.local_scratch_root),
            "local_stage_root": str(stage_root),
            "run_id": request.run_id,
            "source_build_pack_id": request.source_build_pack_id,
            "remote_target_label": request.remote_target_label,
            "remote_pack_dir": request.remote_pack_dir,
            "remote_run_dir": request.remote_run_dir,
            "remote_export_dir": request.remote_export_dir,
        },
    )


def _request_entry(snapshot_root: Path, request_text: str) -> dict[str, Any]:
    request_path = snapshot_root / REMOTE_METADATA_DIR / REMOTE_REQUEST_FILENAME
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(request_text, encoding="utf-8")
    return {
        "relative_path": f"{REMOTE_METADATA_DIR}/{REMOTE_REQUEST_FILENAME}",
        "sha256": sha256_path(request_path),
        "size_bytes": request_path.stat().st_size,
    }


def _build_manifest(
    *,
    request,
    request_sha256: str,
    local_stage_root: Path,
    transport_mode: str,
    excluded_paths: list[str],
    payload_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": PAYLOAD_MANIFEST_SCHEMA_VERSION,
        "payload_policy_version": PAYLOAD_POLICY_VERSION,
        "source_build_pack_id": request.source_build_pack_id,
        "source_build_pack_root": str(request.source_build_pack_root),
        "local_scratch_root": str(request.local_scratch_root),
        "local_staging_root": str(local_stage_root),
        "run_id": request.run_id,
        "remote_target_label": request.remote_target_label,
        "remote_parent_dir": request.remote_parent_dir,
        "remote_pack_dir": request.remote_pack_dir,
        "remote_run_dir": request.remote_run_dir,
        "remote_export_dir": request.remote_export_dir,
        "remote_host": request.remote_host,
        "remote_user": request.remote_user,
        "request_sha256": request_sha256,
        "staged_at": isoformat_z(read_now()),
        "staged_by": request.staged_by,
        "transport_mode": transport_mode,
        "excluded_paths": excluded_paths,
        "payload_entries": payload_entries,
        "control_plane_mutations": build_control_plane_mutations(),
    }


def _remote_stage_command(*, request, temp_remote_dir: str) -> str:
    commands = [
        f"rm -rf {temp_remote_dir}",
        f"mkdir -p {request.remote_parent_dir}",
        f"mkdir -p {temp_remote_dir}",
        f"rm -rf {request.remote_pack_dir}",
        f"mv {temp_remote_dir} {request.remote_pack_dir}",
        f"mkdir -p {request.remote_run_dir}",
        f"mkdir -p {request.remote_export_dir}",
    ]
    quoted = [f"set -euo pipefail", *commands]
    return "bash -lc " + subprocess.list2cmdline(["; ".join(quoted)])


def _push_snapshot(*, request, local_payload_root: Path, transport_mode: str, temp_remote_dir: str) -> None:
    mkdir_command = (
        f"bash -lc {json.dumps(f'set -euo pipefail; rm -rf {temp_remote_dir}; mkdir -p {temp_remote_dir}')}"
    )
    run_checked(["ssh", request.remote_address, mkdir_command])
    if transport_mode == "rsync":
        push_directory_via_rsync(request=request, local_dir=local_payload_root, remote_dir=temp_remote_dir)
        return
    if transport_mode != "scp":
        raise RuntimeError(f"unsupported transport_mode: {transport_mode}")
    run_checked(["scp", "-r", f"{local_payload_root}/.", f"{request.remote_address}:{temp_remote_dir}/"])


def _swap_remote_payload(*, request, temp_remote_dir: str) -> None:
    remote_script = (
        "set -euo pipefail; "
        f"rm -rf {request.remote_pack_dir}; "
        f"mv {temp_remote_dir} {request.remote_pack_dir}; "
        f"mkdir -p {request.remote_pack_dir}/{REMOTE_METADATA_DIR}; "
        f"mkdir -p {request.remote_run_dir}; "
        f"mkdir -p {request.remote_export_dir}"
    )
    run_checked(["ssh", request.remote_address, "bash", "-lc", remote_script])


def _push_manifest(*, request, local_manifest_path: Path) -> None:
    remote_manifest_path = f"{request.remote_pack_dir}/{REMOTE_METADATA_DIR}/{REMOTE_TARGET_MANIFEST_FILENAME}"
    push_file_via_scp(request=request, local_path=local_manifest_path, remote_path=remote_manifest_path)


def push_build_pack_to_remote(factory_root: Path, request_path: Path, *, transport: str) -> dict[str, Any]:
    request = load_remote_autonomy_request(factory_root=factory_root, request_path=request_path)
    transport_mode = _transport_mode(transport)
    stage_root = _local_stage_root(request.local_scratch_root, request.run_id)
    payload_root = _local_payload_root(stage_root)
    stage_root.mkdir(parents=True, exist_ok=True)
    _write_scratch_lifecycle_marker(stage_root=stage_root, request=request, status="active")

    excluded_paths, payload_entries = materialize_payload_snapshot(
        request=request,
        destination_root=payload_root,
    )
    request_text = _canonical_request_text(request.raw_payload)
    request_sha256 = _request_entry(payload_root, request_text)["sha256"]
    payload_entries.append(_request_entry(payload_root, request_text))
    payload_entries.sort(key=lambda entry: str(entry["relative_path"]))

    manifest_payload = _build_manifest(
        request=request,
        request_sha256=request_sha256,
        local_stage_root=stage_root,
        transport_mode=transport_mode,
        excluded_paths=excluded_paths,
        payload_entries=payload_entries,
    )
    local_manifest_path = _local_manifest_path(stage_root)
    write_validated_json(
        factory_root=factory_root,
        path=local_manifest_path,
        payload=manifest_payload,
        schema_name=PAYLOAD_MANIFEST_SCHEMA_NAME,
    )

    temp_remote_dir = f"{request.remote_pack_dir}.staging-{request.run_id}"
    _push_snapshot(
        request=request,
        local_payload_root=payload_root,
        transport_mode=transport_mode,
        temp_remote_dir=temp_remote_dir,
    )
    _swap_remote_payload(request=request, temp_remote_dir=temp_remote_dir)
    _push_manifest(request=request, local_manifest_path=local_manifest_path)
    _write_scratch_lifecycle_marker(stage_root=stage_root, request=request, status="staged")

    return {
        "schema_version": "remote-build-pack-stage-result/v1",
        "status": "staged",
        "source_build_pack_id": request.source_build_pack_id,
        "source_build_pack_root": str(request.source_build_pack_root),
        "local_scratch_root": str(request.local_scratch_root),
        "run_id": request.run_id,
        "remote_host": request.remote_host,
        "remote_user": request.remote_user,
        "remote_target_label": request.remote_target_label,
        "remote_parent_dir": request.remote_parent_dir,
        "remote_pack_dir": request.remote_pack_dir,
        "remote_run_dir": request.remote_run_dir,
        "remote_export_dir": request.remote_export_dir,
        "payload_policy_version": PAYLOAD_POLICY_VERSION,
        "transport_mode": transport_mode,
        "excluded_paths": excluded_paths,
        "payload_entry_count": len(payload_entries),
        "request_sha256": request_sha256,
        "target_manifest_path": f"{request.remote_pack_dir}/{REMOTE_METADATA_DIR}/{REMOTE_TARGET_MANIFEST_FILENAME}",
        "local_staging_root": str(stage_root),
        "local_manifest_path": str(local_manifest_path),
        "scratch_lifecycle_path": str(_scratch_lifecycle_path(stage_root)),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage a build-pack to a remote autonomy target.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory repository root.")
    parser.add_argument("--request-file", required=True, help="Path to a remote-autonomy-run-request/v1 JSON file.")
    parser.add_argument(
        "--transport",
        default="auto",
        choices=("auto", "rsync", "scp"),
        help="Bounded transport to use. Defaults to rsync when available, otherwise scp.",
    )
    parser.add_argument("--output", default="json", choices=("json",), help="Output format.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    request_path = Path(args.request_file).expanduser().resolve()
    result = push_build_pack_to_remote(factory_root, request_path, transport=args.transport)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
