#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import dump_json, isoformat_z, load_json, read_now, resolve_factory_root, schema_path, validate_json_document, write_json
from remote_autonomy_staging_common import (
    canonical_local_roundtrip_incoming_dir,
    PAYLOAD_MANIFEST_SCHEMA_NAME,
    REMOTE_METADATA_DIR,
    REMOTE_TARGET_MANIFEST_FILENAME,
    expand_remote_home_for_scp,
    load_remote_autonomy_request,
    run_checked,
    sha256_path,
    write_validated_scratch_lifecycle_manifest,
)


EXECUTION_MANIFEST_FILENAME = "execution-manifest.json"
EXECUTION_MANIFEST_SCHEMA_NAME = "remote-execution-manifest.schema.json"
BUNDLE_SCHEMA_NAME = "external-runtime-evidence-bundle.schema.json"
LOCAL_BUNDLE_DIRNAME = "bundle"
LOCAL_CHECKPOINT_ARTIFACTS_DIRNAME = "checkpoint-artifacts"
LOCAL_HELPER_MANIFEST_FILENAME = "portable-runtime-helper-manifest.json"
SCRATCH_LIFECYCLE_FILENAME = "scratch-lifecycle.json"
RECOVERY_SNAPSHOT_FILENAME = "recovery-remote-state.json"
PROMPT_ARTIFACT_FILENAME = "invocation-prompt.txt"
BOOTSTRAP_MODE = "presence-check-only"
LATE_EXPORT_RECOVERY_ATTEMPTS_ENV = "PACKFACTORY_REMOTE_LATE_EXPORT_RECOVERY_ATTEMPTS"
DEFAULT_LATE_EXPORT_RECOVERY_ATTEMPTS = 2
LATE_EXPORT_RECOVERY_DELAY_ENV = "PACKFACTORY_REMOTE_LATE_EXPORT_RECOVERY_DELAY_SECONDS"
DEFAULT_LATE_EXPORT_RECOVERY_DELAY_SECONDS = 30.0


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


def _canonical_request_text(payload: dict[str, Any]) -> str:
    return dump_json(payload)


def _directory_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
        relative_path = path.relative_to(root).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_path(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _resolve_local_stage_dir(selected_scratch_root: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    resolved = candidate if candidate.is_absolute() else (selected_scratch_root / candidate)
    resolved = resolved.resolve()
    try:
        resolved.relative_to(selected_scratch_root)
    except ValueError as exc:
        raise ValueError("local bundle staging dir must resolve under the selected PackFactory scratch root") from exc
    return resolved


def _resolve_under_local_root(base: Path, relative_path: str) -> Path:
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise ValueError("checkpoint artifact path must be relative")
    resolved = (base / candidate).resolve()
    try:
        resolved.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError("checkpoint artifact path must stay under the local checkpoint-artifact root") from exc
    return resolved


def _incoming_dir(local_stage_dir: Path) -> Path:
    return local_stage_dir


def _incoming_target_manifest_path(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / REMOTE_TARGET_MANIFEST_FILENAME


def _incoming_execution_manifest_path(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / EXECUTION_MANIFEST_FILENAME


def _incoming_bundle_root(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / LOCAL_BUNDLE_DIRNAME


def _incoming_checkpoint_artifacts_root(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / LOCAL_CHECKPOINT_ARTIFACTS_DIRNAME


def _incoming_helper_manifest_path(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / LOCAL_HELPER_MANIFEST_FILENAME


def _incoming_recovery_snapshot_path(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / RECOVERY_SNAPSHOT_FILENAME


def _scratch_lifecycle_path(local_stage_dir: Path) -> Path:
    return _incoming_dir(local_stage_dir) / SCRATCH_LIFECYCLE_FILENAME


def _unexpected_stage_entries(local_stage_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in local_stage_dir.iterdir()
        if path.name != SCRATCH_LIFECYCLE_FILENAME
    )


def _write_scratch_lifecycle_marker(*, local_stage_dir: Path, request, status: str) -> None:
    write_validated_scratch_lifecycle_manifest(
        factory_root=request.factory_root,
        path=_scratch_lifecycle_path(local_stage_dir),
        payload={
            "schema_version": "scratch-lifecycle/v1",
            "status": status,
            "updated_at": isoformat_z(read_now()),
            "factory_root": str(request.factory_root),
            "local_scratch_root": str(request.local_scratch_root),
            "local_stage_root": str(local_stage_dir),
            "run_id": request.run_id,
            "source_build_pack_id": request.source_build_pack_id,
            "remote_target_label": request.remote_target_label,
            "remote_pack_dir": request.remote_pack_dir,
            "remote_run_dir": request.remote_run_dir,
            "remote_export_dir": request.remote_export_dir,
        },
    )


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
    resolved_remote_path = expand_remote_home_for_scp(remote_path, request.remote_user)
    run_checked(["scp", f"{request.remote_address}:{resolved_remote_path}", str(local_path)])


def _scp_file_if_present(*, request, remote_path: str, local_path: Path) -> bool:
    try:
        _scp_file(request=request, remote_path=remote_path, local_path=local_path)
    except subprocess.CalledProcessError:
        return False
    return True


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
    resolved_remote_dir = expand_remote_home_for_scp(remote_dir, request.remote_user)
    run_checked(["scp", "-r", f"{request.remote_address}:{resolved_remote_dir}", str(local_parent)])
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


def _late_export_recovery_attempts() -> int:
    value = os.environ.get(LATE_EXPORT_RECOVERY_ATTEMPTS_ENV)
    if value is None:
        return DEFAULT_LATE_EXPORT_RECOVERY_ATTEMPTS
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{LATE_EXPORT_RECOVERY_ATTEMPTS_ENV} must be an integer when set") from exc
    if parsed < 0:
        raise ValueError(f"{LATE_EXPORT_RECOVERY_ATTEMPTS_ENV} must be zero or greater when set")
    return parsed


def _late_export_recovery_delay_seconds() -> float:
    value = os.environ.get(LATE_EXPORT_RECOVERY_DELAY_ENV)
    if value is None:
        return DEFAULT_LATE_EXPORT_RECOVERY_DELAY_SECONDS
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{LATE_EXPORT_RECOVERY_DELAY_ENV} must be numeric when set") from exc
    if parsed <= 0:
        raise ValueError(f"{LATE_EXPORT_RECOVERY_DELAY_ENV} must be greater than zero when set")
    return parsed


def _fetch_recovery_remote_state(request) -> dict[str, Any]:
    return _ssh_json(
        request,
        """
from __future__ import annotations

import json
import sys
from pathlib import Path

request_path = Path(sys.argv[1]).expanduser()
context_path = Path(sys.argv[2]).expanduser()
export_dir = Path(sys.argv[3]).expanduser()
run_id = sys.argv[4]
pack_id = sys.argv[5]
run_dir = Path(sys.argv[6]).expanduser()
pack_root = Path(sys.argv[7]).expanduser()
checkpoint_run_root = pack_root / ".pack-state" / "autonomy-runs" / run_id

request_payload = json.loads(request_path.read_text(encoding="utf-8"))
if context_path.exists():
    context_payload = json.loads(context_path.read_text(encoding="utf-8"))
else:
    context_payload = {}

matches = []
for bundle_path in sorted(export_dir.glob("external-runtime-evidence-*/bundle.json")):
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    except Exception:
        continue
    if bundle.get("run_id") != run_id or bundle.get("pack_id") != pack_id:
        continue
    matches.append(
        {
            "bundle_path": str(bundle_path),
            "bundle": bundle,
        }
    )

payload = {
    "request": request_payload,
    "invocation_context": context_payload,
    "bundle": None,
    "run_summary": None,
    "remote_run_state": {
        "invocation_context_exists": context_path.exists(),
        "run_dir_exists": run_dir.exists(),
        "loop_events_exists": (run_dir / "loop-events.jsonl").exists(),
        "run_summary_exists": (run_dir / "run-summary.json").exists(),
        "checkpoint_exists": (run_dir / "adf-remote-checkpoint-bundle.json").exists(),
        "checkpoint_run_root_exists": checkpoint_run_root.exists(),
        "checkpoint_run_summary_exists": (checkpoint_run_root / "run-summary.json").exists(),
        "checkpoint_bundle_exists": (checkpoint_run_root / "adf-remote-checkpoint-bundle.json").exists(),
    },
}

run_summary_path = checkpoint_run_root / "run-summary.json"
if run_summary_path.exists():
    try:
        payload["run_summary"] = json.loads(run_summary_path.read_text(encoding="utf-8"))
    except Exception:
        payload["run_summary"] = None

if matches:
    matches.sort(key=lambda item: (item["bundle"].get("generated_at") or "", item["bundle_path"]))
    payload["bundle"] = matches[-1]["bundle"]

print(json.dumps(payload, sort_keys=True))
""".strip(),
        f"{request.remote_pack_dir}/{REMOTE_METADATA_DIR}/request.json",
        f"{request.remote_pack_dir}/{REMOTE_METADATA_DIR}/invocation-context.json",
        request.remote_export_dir,
        request.run_id,
        request.source_build_pack_id,
        request.remote_run_dir,
        request.remote_pack_dir,
    )


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
    target_manifest = _validate_json(factory_root, target_path, PAYLOAD_MANIFEST_SCHEMA_NAME)
    try:
        _scp_file(
            request=request,
            remote_path=f"{request.remote_pack_dir}/{REMOTE_METADATA_DIR}/{EXECUTION_MANIFEST_FILENAME}",
            local_path=execution_path,
        )
        execution_manifest = _validate_json(factory_root, execution_path, EXECUTION_MANIFEST_SCHEMA_NAME)
    except subprocess.CalledProcessError:
        execution_manifest = _recover_execution_manifest(
            factory_root=factory_root,
            request=request,
            local_stage_dir=local_stage_dir,
            target_manifest_path=target_path,
        )
    return target_manifest, execution_manifest


def _recover_execution_manifest(*, factory_root: Path, request, local_stage_dir: Path, target_manifest_path: Path) -> dict[str, Any]:
    recovery_attempts_remaining = _late_export_recovery_attempts()
    remote_state = _fetch_recovery_remote_state(request)
    while not isinstance(remote_state.get("bundle"), dict) and recovery_attempts_remaining > 0:
        time.sleep(_late_export_recovery_delay_seconds())
        recovery_attempts_remaining -= 1
        remote_state = _fetch_recovery_remote_state(request)
    bundle = remote_state.get("bundle")
    invocation_context = remote_state.get("invocation_context")
    if not isinstance(invocation_context, dict):
        raise ValueError("recovered invocation context must be an object")
    run_summary = remote_state.get("run_summary")
    if run_summary is not None and not isinstance(run_summary, dict):
        raise ValueError("recovered run_summary must be an object when present")
    remote_run_state = remote_state.get("remote_run_state")
    if not isinstance(remote_run_state, dict):
        raise ValueError("recovered remote_run_state must be an object")
    recovered_at = isoformat_z(read_now())

    bundle_present = isinstance(bundle, dict)
    if bundle_present:
        summary = bundle.get("summary")
        if not isinstance(summary, dict):
            raise ValueError("recovered bundle summary must be an object")
        export_bundle_path = bundle.get("bundle_root")
        if not isinstance(export_bundle_path, str) or not export_bundle_path:
            raise ValueError("recovered bundle_root must be present")

        stop_reason = summary.get("stop_reason")
        if stop_reason == "ready_for_deploy_boundary":
            terminal_outcome = "promotion_or_deployment_boundary"
        elif stop_reason == "starter_backlog_completed":
            terminal_outcome = "starter_backlog_completed"
        elif stop_reason == "escalation_raised":
            terminal_outcome = "escalated"
        else:
            terminal_outcome = "stopped"
    else:
        summary = run_summary if isinstance(run_summary, dict) else None
        export_bundle_path = None
        if (
            remote_run_state.get("run_dir_exists") is True
            and remote_run_state.get("loop_events_exists") is False
            and remote_run_state.get("run_summary_exists") is False
            and remote_run_state.get("checkpoint_exists") is False
            and remote_run_state.get("checkpoint_run_summary_exists") is False
            and remote_run_state.get("checkpoint_bundle_exists") is False
        ):
            stop_reason = "pre_invocation_control_plane_startup_stall"
        elif (
            remote_run_state.get("checkpoint_run_root_exists") is True
            and (
                remote_run_state.get("checkpoint_run_summary_exists") is True
                or remote_run_state.get("checkpoint_bundle_exists") is True
            )
        ):
            if isinstance(summary, dict) and isinstance(summary.get("stop_reason"), str) and summary.get("stop_reason"):
                stop_reason = str(summary["stop_reason"])
            else:
                stop_reason = "checkpoint_only_recovery_without_export_bundle"
        else:
            stop_reason = "no_matching_exported_runtime_bundle_after_timeout_pullback"
        terminal_outcome = "stopped"

    pack_manifest = _load_object(request.source_build_pack_root / "pack.json")
    entrypoints = pack_manifest.get("entrypoints")
    if not isinstance(entrypoints, dict):
        raise ValueError("source pack pack.json.entrypoints must be an object")
    export_command = entrypoints.get("export_runtime_evidence_command")
    if not isinstance(export_command, str) or not export_command:
        raise ValueError("source pack export_runtime_evidence_command must be present for recovered execution manifest")

    request_sha256 = _sha256_text(_canonical_request_text(request.raw_payload))
    remote_runner = invocation_context.get("remote_runner")
    if not isinstance(remote_runner, str) or not remote_runner:
        remote_runner = str(getattr(request, "remote_runner", "") or request.raw_payload.get("remote_runner") or "codex exec (synthetic-pre-invocation-manifest)")
    prompt_sha256 = invocation_context.get("prompt_sha256")
    if not isinstance(prompt_sha256, str) or not prompt_sha256:
        prompt_sha256 = _sha256_text(f"synthetic-pre-invocation-prompt:{request_sha256}:{request.run_id}")
    started_at = summary.get("started_at") if isinstance(summary, dict) else recovered_at
    stopped_at = summary.get("ended_at") if isinstance(summary, dict) else recovered_at

    execution_manifest = {
        "schema_version": "remote-execution-manifest/v1",
        "source_build_pack_id": request.source_build_pack_id,
        "run_id": request.run_id,
        "request_sha256": request_sha256,
        "target_manifest_sha256": sha256_path(target_manifest_path),
        "remote_runner": remote_runner,
        "runner_returncode": -1,
        "runner_interrupted_signal": None,
        "stale_active_run_cleanup": None,
        "prompt_sha256": prompt_sha256,
        "prompt_artifact_path": f"{REMOTE_METADATA_DIR}/{PROMPT_ARTIFACT_FILENAME}",
        "bootstrap_mode": BOOTSTRAP_MODE,
        "started_at": started_at,
        "stopped_at": stopped_at,
        "terminal_outcome": terminal_outcome,
        "terminal_reason": stop_reason,
        "export_status": "succeeded" if bundle_present else "not_attempted",
        "export_command": export_command.replace("<run-id>", request.run_id).replace("<actor>", "codex"),
        "export_bundle_path": export_bundle_path,
        "export_completed_at": bundle.get("generated_at") if bundle_present else None,
        "exported_run_id": bundle.get("run_id") if bundle_present else None,
        "export_error": None if bundle_present else "no matching exported runtime bundle found for recovered execution manifest",
        "control_plane_mutations": {
            "registry_updated": False,
            "deployment_updated": False,
            "promotion_updated": False,
            "readiness_updated": False,
            "work_state_updated": False,
            "eval_latest_updated": False,
            "release_artifacts_updated": False,
        },
    }
    execution_path = _incoming_execution_manifest_path(local_stage_dir)
    execution_path.write_text(dump_json(execution_manifest), encoding="utf-8")
    _validate_json(factory_root, execution_path, EXECUTION_MANIFEST_SCHEMA_NAME)
    recovery_snapshot = {
        "schema_version": "remote-runtime-recovery-snapshot/v1",
        "source_build_pack_id": request.source_build_pack_id,
        "run_id": request.run_id,
        "recovered_at": recovered_at,
        "request_sha256": request_sha256,
        "terminal_reason": stop_reason,
        "bundle_present": bundle_present,
        "run_summary_present": isinstance(summary, dict),
        "remote_run_state": remote_run_state,
        "invocation_context": invocation_context,
        "synthetic_manifest_fields": {
            "runner_returncode_synthetic": True,
            "runner_interrupted_signal_synthetic": True,
            "stale_active_run_cleanup_synthetic": True,
            "remote_runner_synthetic": not isinstance(invocation_context.get("remote_runner"), str) or not invocation_context.get("remote_runner"),
            "prompt_sha256_synthetic": not isinstance(invocation_context.get("prompt_sha256"), str) or not invocation_context.get("prompt_sha256"),
            "timestamps_synthetic": not isinstance(summary, dict),
        },
    }
    recovery_snapshot_path = _incoming_recovery_snapshot_path(local_stage_dir)
    recovery_snapshot_path.write_text(dump_json(recovery_snapshot), encoding="utf-8")
    return execution_manifest


def _pull_checkpoint_only_artifacts(*, request, local_stage_dir: Path) -> dict[str, Any]:
    artifacts_root = _incoming_checkpoint_artifacts_root(local_stage_dir)
    if artifacts_root.exists():
        shutil.rmtree(artifacts_root)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    local_run_summary_path = artifacts_root / "run-summary.json"
    local_loop_events_path = artifacts_root / "loop-events.jsonl"
    local_checkpoint_bundle_path = artifacts_root / "adf-remote-checkpoint-bundle.json"

    run_summary_present = _scp_file_if_present(
        request=request,
        remote_path=f"{request.remote_run_dir}/run-summary.json",
        local_path=local_run_summary_path,
    )
    loop_events_present = _scp_file_if_present(
        request=request,
        remote_path=f"{request.remote_run_dir}/loop-events.jsonl",
        local_path=local_loop_events_path,
    )
    checkpoint_bundle_present = _scp_file_if_present(
        request=request,
        remote_path=f"{request.remote_run_dir}/adf-remote-checkpoint-bundle.json",
        local_path=local_checkpoint_bundle_path,
    )

    local_feedback_memory_path: str | None = None
    recovered_artifact_paths: list[str] = []
    if checkpoint_bundle_present:
        checkpoint_bundle = _load_object(local_checkpoint_bundle_path)
        run_artifacts = checkpoint_bundle.get("run_artifacts", {})
        if isinstance(run_artifacts, dict):
            candidate_paths: list[str] = []
            for key in ("run_summary_path", "loop_events_path", "feedback_memory_path"):
                value = run_artifacts.get(key)
                if isinstance(value, str) and value:
                    candidate_paths.append(value)
            for key in ("result_log_paths", "target_artifact_paths"):
                values = run_artifacts.get(key, [])
                if isinstance(values, list):
                    candidate_paths.extend(value for value in values if isinstance(value, str) and value)

            seen: set[str] = set()
            for relative_path in candidate_paths:
                if relative_path in seen:
                    continue
                seen.add(relative_path)
                destination = artifacts_root / Path(relative_path)
                copied = _scp_file_if_present(
                    request=request,
                    remote_path=_remote_join(request.remote_pack_dir, relative_path),
                    local_path=destination,
                )
                if not copied:
                    continue
                recovered_artifact_paths.append(str(destination))
                if relative_path == run_artifacts.get("feedback_memory_path"):
                    local_feedback_memory_path = str(destination)

    return {
        "local_checkpoint_artifacts_root": str(artifacts_root),
        "local_checkpoint_run_summary_path": str(local_run_summary_path) if run_summary_present else None,
        "local_checkpoint_loop_events_path": str(local_loop_events_path) if loop_events_present else None,
        "local_checkpoint_bundle_path": str(local_checkpoint_bundle_path) if checkpoint_bundle_present else None,
        "local_checkpoint_feedback_memory_path": local_feedback_memory_path,
        "local_checkpoint_artifact_paths": recovered_artifact_paths,
    }


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


def _validate_request_linkage(
    *,
    request,
    target_manifest: dict[str, Any],
    execution_manifest: dict[str, Any],
    local_target_manifest_path: Path,
    require_bundle: bool,
) -> None:
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
    if require_bundle:
        if execution_manifest.get("export_status") != "succeeded":
            raise ValueError("execution manifest export_status must be succeeded before pullback")
        if execution_manifest.get("exported_run_id") != request.run_id:
            raise ValueError("execution manifest exported_run_id does not match the selected request")


def _manifest_only_pull_result(*, request, local_stage_dir: Path) -> dict[str, Any]:
    execution_manifest_path = _incoming_execution_manifest_path(local_stage_dir)
    target_manifest_path = _incoming_target_manifest_path(local_stage_dir)
    recovery_snapshot_path = _incoming_recovery_snapshot_path(local_stage_dir)
    execution_manifest = _load_object(execution_manifest_path)
    target_manifest = _load_object(target_manifest_path)
    return {
        "schema_version": "remote-runtime-evidence-pull-result/v1",
        "status": "manifest_only",
        "source_build_pack_id": request.source_build_pack_id,
        "local_scratch_root": str(request.local_scratch_root),
        "run_id": request.run_id,
        "remote_target_label": request.remote_target_label,
        "remote_host": request.remote_host,
        "remote_user": request.remote_user,
        "local_bundle_staging_dir": str(local_stage_dir),
        "incoming_dir": str(_incoming_dir(local_stage_dir)),
        "local_target_manifest_path": str(target_manifest_path),
        "target_manifest_sha256": sha256_path(target_manifest_path),
        "local_execution_manifest_path": str(execution_manifest_path),
        "execution_manifest_sha256": sha256_path(execution_manifest_path),
        "execution_manifest": execution_manifest,
        "target_manifest": target_manifest,
        "local_recovery_snapshot_path": str(recovery_snapshot_path) if recovery_snapshot_path.exists() else None,
        "local_checkpoint_artifact_root": None,
        "checkpoint_artifact_paths": [],
        "checkpoint_missing_paths": [],
        "local_portable_helper_manifest_path": None,
        "portable_helper_manifest_sha256": None,
        "local_bundle_root": None,
        "local_bundle_manifest_path": None,
        "pulled_bundle_sha256": None,
        "pulled_at": None,
        "bundle_generated_at": None,
        "transport_mode": None,
        "scratch_lifecycle_path": str(_scratch_lifecycle_path(local_stage_dir)),
    }


def _checkpoint_candidate_paths(checkpoint_bundle: dict[str, Any]) -> list[str]:
    run_artifacts = checkpoint_bundle.get("run_artifacts", {})
    if not isinstance(run_artifacts, dict):
        return []
    candidates: list[str] = []
    for key in ("run_summary_path", "loop_events_path", "feedback_memory_path"):
        value = run_artifacts.get(key)
        if isinstance(value, str) and value:
            candidates.append(value)
    for key in ("result_log_paths", "target_artifact_paths"):
        values = run_artifacts.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and value:
                candidates.append(value)
    return candidates


def _pull_checkpoint_only_artifacts(*, request, local_stage_dir: Path) -> tuple[str | None, list[str], list[str]]:
    checkpoint_root = _incoming_checkpoint_artifacts_root(local_stage_dir)
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    checkpoint_relative_path = f".pack-state/autonomy-runs/{request.run_id}/adf-remote-checkpoint-bundle.json"
    checkpoint_local_path = _resolve_under_local_root(checkpoint_root, checkpoint_relative_path)
    try:
        _scp_file(
            request=request,
            remote_path=_remote_join(request.remote_pack_dir, checkpoint_relative_path),
            local_path=checkpoint_local_path,
        )
    except subprocess.CalledProcessError:
        return None, [], []

    checkpoint_bundle = _load_object(checkpoint_local_path)
    pulled_paths = [str(checkpoint_local_path)]
    missing_paths: list[str] = []
    seen_relative_paths = {checkpoint_relative_path}

    for relative_path in _checkpoint_candidate_paths(checkpoint_bundle):
        if relative_path in seen_relative_paths:
            continue
        seen_relative_paths.add(relative_path)
        local_path = _resolve_under_local_root(checkpoint_root, relative_path)
        try:
            _scp_file(
                request=request,
                remote_path=_remote_join(request.remote_pack_dir, relative_path),
                local_path=local_path,
            )
        except subprocess.CalledProcessError:
            missing_paths.append(relative_path)
            continue
        pulled_paths.append(str(local_path))

    return str(checkpoint_root), sorted(pulled_paths), sorted(missing_paths)


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
    local_stage_dir = _resolve_local_stage_dir(request.local_scratch_root, local_bundle_staging_dir)
    expected_local_stage_dir = canonical_local_roundtrip_incoming_dir(
        request.local_scratch_root,
        request.remote_target_label,
        request.source_build_pack_id,
        request.run_id,
    )
    if local_stage_dir != expected_local_stage_dir:
        raise ValueError(
            "local bundle staging dir must match the deterministic roundtrip staging path "
            f"`{expected_local_stage_dir}`"
        )
    if local_stage_dir.exists() and _unexpected_stage_entries(local_stage_dir):
        raise ValueError(f"local bundle staging dir must be empty before pullback: {local_stage_dir}")
    incoming = _incoming_dir(local_stage_dir)
    if incoming.exists():
        shutil.rmtree(incoming)
    incoming.mkdir(parents=True, exist_ok=True)
    _write_scratch_lifecycle_marker(local_stage_dir=local_stage_dir, request=request, status="pulling")

    target_manifest, execution_manifest = _pull_target_and_execution_manifests(
        factory_root=factory_root,
        request=request,
        local_stage_dir=local_stage_dir,
    )
    recovery_snapshot_path = _incoming_recovery_snapshot_path(local_stage_dir)
    _validate_request_linkage(
        request=request,
        target_manifest=target_manifest,
        execution_manifest=execution_manifest,
        local_target_manifest_path=_incoming_target_manifest_path(local_stage_dir),
        require_bundle=False,
    )
    if execution_manifest.get("export_status") != "succeeded":
        checkpoint_artifact_root, checkpoint_artifact_paths, checkpoint_missing_paths = _pull_checkpoint_only_artifacts(
            request=request,
            local_stage_dir=local_stage_dir,
        )
        _write_scratch_lifecycle_marker(local_stage_dir=local_stage_dir, request=request, status="manifest_only")
        result = _manifest_only_pull_result(request=request, local_stage_dir=local_stage_dir)
        result["local_checkpoint_artifact_root"] = checkpoint_artifact_root
        result["checkpoint_artifact_paths"] = checkpoint_artifact_paths
        result["checkpoint_missing_paths"] = checkpoint_missing_paths
        return result
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
    _write_scratch_lifecycle_marker(local_stage_dir=local_stage_dir, request=request, status="pulled")

    return {
        "schema_version": "remote-runtime-evidence-pull-result/v1",
        "status": "pulled",
        "source_build_pack_id": request.source_build_pack_id,
        "local_scratch_root": str(request.local_scratch_root),
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
        "local_recovery_snapshot_path": str(recovery_snapshot_path) if recovery_snapshot_path.exists() else None,
        "local_portable_helper_manifest_path": helper_manifest_path,
        "portable_helper_manifest_sha256": helper_manifest_sha256,
        "local_bundle_root": str(local_bundle_root),
        "local_bundle_manifest_path": str(local_bundle_manifest_path),
        "pulled_bundle_sha256": local_bundle_sha256,
        "pulled_at": pulled_at,
        "transport_mode": transport_mode,
        "bundle_generated_at": bundle.get("generated_at"),
        "scratch_lifecycle_path": str(_scratch_lifecycle_path(local_stage_dir)),
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
