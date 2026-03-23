#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import dump_json, isoformat_z, load_json, read_now, resolve_factory_root, schema_path, validate_json_document
from remote_autonomy_staging_common import (
    PAYLOAD_MANIFEST_SCHEMA_NAME,
    REMOTE_METADATA_DIR,
    REMOTE_TARGET_MANIFEST_FILENAME,
    load_remote_autonomy_request,
    run_checked,
    sha256_path,
)


EXECUTION_MANIFEST_FILENAME = "execution-manifest.json"
EXECUTION_MANIFEST_SCHEMA_NAME = "remote-execution-manifest.schema.json"
BUNDLE_SCHEMA_NAME = "external-runtime-evidence-bundle.schema.json"
LOCAL_BUNDLE_DIRNAME = "bundle"
LOCAL_HELPER_MANIFEST_FILENAME = "portable-runtime-helper-manifest.json"


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _validate_json(factory_root: Path, path: Path, schema_name: str) -> dict[str, Any]:
    errors = validate_json_document(path, schema_path(factory_root, schema_name))
    if errors:
        raise ValueError("; ".join(errors))
    return _load_object(path)


def _sha256_text(text: str) -> str:
    digest = hashlib.sha256()
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def _directory_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative_path = path.relative_to(root).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_path(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _resolve_local_stage_dir(factory_root: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    resolved = candidate if candidate.is_absolute() else (factory_root / candidate)
    resolved = resolved.resolve()
    try:
        resolved.relative_to(factory_root)
    except ValueError as exc:
        raise ValueError("local bundle staging dir must stay under the selected factory root") from exc
    return resolved


def _incoming_dir(local_stage_dir: Path) -> Path:
    return local_stage_dir


def _incoming_target_manifest_path(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / REMOTE_TARGET_MANIFEST_FILENAME


def _incoming_execution_manifest_path(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / EXECUTION_MANIFEST_FILENAME


def _incoming_bundle_root(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / LOCAL_BUNDLE_DIRNAME


def _incoming_helper_manifest_path(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / LOCAL_HELPER_MANIFEST_FILENAME


def _transport_mode(requested: str) -> str:
    if requested != "auto":
        return requested
    if shutil.which("rsync"):
        return "rsync"
    if shutil.which("scp"):
        return "scp"
    raise RuntimeError("v1 pull requires either `rsync` or `scp` to be available")


def _scp_file(*, request, remote_path: str, local_path: Path) -> None:
    local_path.parent.mkdir(parents=True, exist_ok=True)
    run_checked(["scp", f"{request.remote_address}:{remote_path}", str(local_path)])


def _pull_directory(*, request, remote_dir: str, local_dir: Path, transport_mode: str) -> None:
    if local_dir.exists():
        shutil.rmtree(local_dir)
    local_dir.parent.mkdir(parents=True, exist_ok=True)
    if transport_mode == "rsync":
        local_dir.mkdir(parents=True, exist_ok=True)
        run_checked(["rsync", "-a", f"{request.remote_address}:{remote_dir.rstrip('/')}/", f"{local_dir}/"])
        return
    if transport_mode != "scp":
        raise RuntimeError(f"unsupported transport mode: {transport_mode}")
    local_parent = local_dir.parent
    remote_name = PurePosixPath(remote_dir).name
    pulled_dir = local_parent / remote_name
    if pulled_dir.exists():
        shutil.rmtree(pulled_dir)
    run_checked(["scp", "-r", f"{request.remote_address}:{remote_dir}", str(local_parent)])
    if local_dir.exists():
        shutil.rmtree(local_dir)
    pulled_dir.rename(local_dir)


def _ssh_json(request, script: str, *args: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["ssh", request.remote_address, "python3", "-", *args],
        input=script,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "remote python command failed")
    payload = json.loads(completed.stdout)
    if not isinstance(payload, dict):
        raise ValueError("remote command must emit a JSON object")
    return payload


def _remote_join(base: str, relative_path: str) -> str:
    candidate = PurePosixPath(relative_path)
    if candidate.is_absolute():
        raise ValueError("remote relative path must not be absolute")
    if any(part in {"..", "."} for part in candidate.parts):
        raise ValueError("remote relative path must not contain traversal segments")
    return f"{base.rstrip('/')}/{candidate.as_posix()}"


def _pull_target_and_execution_manifests(*, factory_root: Path, request, local_stage_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    incoming = _incoming_dir(local_stage_dir)
    incoming.mkdir(parents=True, exist_ok=True)
    target_path = _incoming_target_manifest_path(local_stage_dir)
    execution_path = _incoming_execution_manifest_path(local_stage_dir)
    _scp_file(
        request=request,
        remote_path=f"{request.remote_pack_dir}/{REMOTE_METADATA_DIR}/{REMOTE_TARGET_MANIFEST_FILENAME}",
        local_path=target_path,
    )
    _scp_file(
        request=request,
        remote_path=f"{request.remote_pack_dir}/{REMOTE_METADATA_DIR}/{EXECUTION_MANIFEST_FILENAME}",
        local_path=execution_path,
    )
    target_manifest = _validate_json(factory_root, target_path, PAYLOAD_MANIFEST_SCHEMA_NAME)
    execution_manifest = _validate_json(factory_root, execution_path, EXECUTION_MANIFEST_SCHEMA_NAME)
    return target_manifest, execution_manifest


def _maybe_pull_helper_manifest(*, request, local_stage_dir: Path) -> tuple[str | None, str | None]:
    pack_manifest = _load_object(request.source_build_pack_root / "pack.json")
    directory_contract = pack_manifest.get("directory_contract")
    if not isinstance(directory_contract, dict):
        raise ValueError("source pack pack.json.directory_contract must be an object")
    helper_relative_path = directory_contract.get("portable_runtime_helper_manifest")
    if not isinstance(helper_relative_path, str) or not helper_relative_path:
        return None, None
    helper_local_path = _incoming_helper_manifest_path(local_stage_dir)
    _scp_file(
        request=request,
        remote_path=_remote_join(request.remote_pack_dir, helper_relative_path),
        local_path=helper_local_path,
    )
    return str(helper_local_path), sha256_path(helper_local_path)


def _validate_request_linkage(*, request, target_manifest: dict[str, Any], execution_manifest: dict[str, Any], local_target_manifest_path: Path) -> None:
    if target_manifest.get("source_build_pack_id") != request.source_build_pack_id:
        raise ValueError("target manifest source_build_pack_id does not match the selected request")
    if target_manifest.get("run_id") != request.run_id:
        raise ValueError("target manifest run_id does not match the selected request")
    if target_manifest.get("remote_target_label") != request.remote_target_label:
        raise ValueError("target manifest remote_target_label does not match the selected request")
    if execution_manifest.get("source_build_pack_id") != request.source_build_pack_id:
        raise ValueError("execution manifest source_build_pack_id does not match the selected request")
    if execution_manifest.get("run_id") != request.run_id:
        raise ValueError("execution manifest run_id does not match the selected request")
    if execution_manifest.get("target_manifest_sha256") != sha256_path(local_target_manifest_path):
        raise ValueError("execution manifest target_manifest_sha256 does not match the pulled target manifest")
    if execution_manifest.get("export_status") != "succeeded":
        raise ValueError("execution manifest export_status must be succeeded before pullback")
    if execution_manifest.get("exported_run_id") != request.run_id:
        raise ValueError("execution manifest exported_run_id does not match the selected request")


def _pull_and_validate_bundle(
    *,
    factory_root: Path,
    request,
    local_stage_dir: Path,
    execution_manifest: dict[str, Any],
    transport_mode: str,
) -> tuple[dict[str, Any], Path, Path, str]:
    export_bundle_path = execution_manifest.get("export_bundle_path")
    if not isinstance(export_bundle_path, str) or not export_bundle_path:
        raise ValueError("execution manifest export_bundle_path must be present before pullback")
    remote_bundle_root = _remote_join(request.remote_pack_dir, export_bundle_path)
    remote_bundle_manifest_path = _remote_join(remote_bundle_root, "bundle.json")
    remote_bundle = _ssh_json(
        request,
        """
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

bundle_manifest = Path(sys.argv[1]).expanduser()
digest = hashlib.sha256()
with bundle_manifest.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
payload = json.loads(bundle_manifest.read_text(encoding="utf-8"))
print(json.dumps({"bundle_sha256": digest.hexdigest(), "bundle": payload}, sort_keys=True))
""".strip(),
        remote_bundle_manifest_path,
    )
    remote_bundle_sha256 = str(remote_bundle["bundle_sha256"])
    local_bundle_root = _incoming_bundle_root(local_stage_dir)
    _pull_directory(request=request, remote_dir=remote_bundle_root, local_dir=local_bundle_root, transport_mode=transport_mode)
    local_bundle_manifest_path = local_bundle_root / "bundle.json"
    bundle = _validate_json(factory_root, local_bundle_manifest_path, BUNDLE_SCHEMA_NAME)
    local_bundle_manifest_sha256 = sha256_path(local_bundle_manifest_path)
    if local_bundle_manifest_sha256 != remote_bundle_sha256:
        raise ValueError("pulled bundle digest does not match the remote bundle manifest digest")
    local_bundle_tree_sha256 = _directory_sha256(local_bundle_root)
    if bundle.get("pack_id") != request.source_build_pack_id:
        raise ValueError("pulled bundle pack_id does not match the selected request")
    if bundle.get("run_id") != request.run_id:
        raise ValueError("pulled bundle run_id does not match the selected request")
    if bundle.get("bundle_root") != export_bundle_path:
        raise ValueError("pulled bundle bundle_root does not match the execution manifest export path")
    if bundle.get("generated_at") != execution_manifest.get("export_completed_at"):
        raise ValueError("pulled bundle generated_at does not match execution manifest export_completed_at")
    summary = bundle.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("pulled bundle summary must be an object")
    if summary.get("stop_reason") != execution_manifest.get("terminal_reason"):
        raise ValueError("pulled bundle summary.stop_reason does not match the execution manifest terminal_reason")
    return bundle, local_bundle_root, local_bundle_manifest_path, local_bundle_tree_sha256


def pull_remote_runtime_evidence(factory_root: Path, request_path: Path, *, local_bundle_staging_dir: str, transport: str) -> dict[str, Any]:
    request = load_remote_autonomy_request(factory_root=factory_root, request_path=request_path)
    local_stage_dir = _resolve_local_stage_dir(factory_root, local_bundle_staging_dir)
    if local_stage_dir.exists() and any(local_stage_dir.iterdir()):
        raise ValueError(f"local bundle staging dir must be empty before pullback: {local_stage_dir}")
    incoming = _incoming_dir(local_stage_dir)
    if incoming.exists():
        shutil.rmtree(incoming)
    incoming.mkdir(parents=True, exist_ok=True)

    target_manifest, execution_manifest = _pull_target_and_execution_manifests(
        factory_root=factory_root,
        request=request,
        local_stage_dir=local_stage_dir,
    )
    _validate_request_linkage(
        request=request,
        target_manifest=target_manifest,
        execution_manifest=execution_manifest,
        local_target_manifest_path=_incoming_target_manifest_path(local_stage_dir),
    )
    transport_mode = _transport_mode(transport)
    helper_manifest_path, helper_manifest_sha256 = _maybe_pull_helper_manifest(
        request=request,
        local_stage_dir=local_stage_dir,
    )
    bundle, local_bundle_root, local_bundle_manifest_path, local_bundle_sha256 = _pull_and_validate_bundle(
        factory_root=factory_root,
        request=request,
        local_stage_dir=local_stage_dir,
        execution_manifest=execution_manifest,
        transport_mode=transport_mode,
    )
    pulled_at = isoformat_z(read_now())

    return {
        "schema_version": "remote-runtime-evidence-pull-result/v1",
        "status": "pulled",
        "source_build_pack_id": request.source_build_pack_id,
        "run_id": request.run_id,
        "remote_target_label": request.remote_target_label,
        "remote_host": request.remote_host,
        "remote_user": request.remote_user,
        "local_bundle_staging_dir": str(local_stage_dir),
        "incoming_dir": str(incoming),
        "local_target_manifest_path": str(_incoming_target_manifest_path(local_stage_dir)),
        "target_manifest_sha256": sha256_path(_incoming_target_manifest_path(local_stage_dir)),
        "local_execution_manifest_path": str(_incoming_execution_manifest_path(local_stage_dir)),
        "execution_manifest_sha256": sha256_path(_incoming_execution_manifest_path(local_stage_dir)),
        "local_portable_helper_manifest_path": helper_manifest_path,
        "portable_helper_manifest_sha256": helper_manifest_sha256,
        "local_bundle_root": str(local_bundle_root),
        "local_bundle_manifest_path": str(local_bundle_manifest_path),
        "pulled_bundle_sha256": local_bundle_sha256,
        "pulled_at": pulled_at,
        "transport_mode": transport_mode,
        "bundle_generated_at": bundle.get("generated_at"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pull remote runtime evidence from a staged remote autonomy run.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory repository root.")
    parser.add_argument("--request-file", required=True, help="Path to a remote-autonomy-run-request/v1 JSON file.")
    parser.add_argument(
        "--local-bundle-staging-dir",
        required=True,
        help="Local orchestration scratch directory for pulled bundle artifacts.",
    )
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
    result = pull_remote_runtime_evidence(
        factory_root,
        request_path,
        local_bundle_staging_dir=args.local_bundle_staging_dir,
        transport=args.transport,
    )
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
