from __future__ import annotations

import json
import shutil
import socket
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .target_connection import (
    _profile_stability,
    _profile_timeouts,
    _shell_launcher_command,
    _ssh_base_argv,
    load_target_connection_profile,
)

AUTONOMY_RUNS_ROOT = Path(".pack-state") / "autonomy-runs"
TARGET_DELEGATION_ROOT = Path(".pack-state") / "delegated-codex-runs"
LOCAL_DELEGATION_DIRNAME = "delegated-codex-runs"
CHECKPOINT_BUNDLE_NAME = "adf-remote-checkpoint-bundle.json"
RUN_SUMMARY_NAME = "run-summary.json"
LOOP_EVENTS_NAME = "loop-events.jsonl"
REQUEST_NAME = "delegated-task-request.json"
RESULT_NAME = "delegated-task-result.json"
COMMANDS_LOG_NAME = "commands.jsonl"
FINDINGS_NAME = "findings.md"
PROMPT_NAME = "codex-prompt.txt"
LAUNCHER_NAME = "run-delegated-codex.sh"
LAUNCHER_LOG_NAME = "codex-launch.log"
ALLOWED_DELEGATION_TIERS = {"observe_only", "guided_change_lab"}
ALLOWED_CHECKPOINT_REASONS = {
    "paused_for_review",
    "task_slice_complete",
    "evidence_ready",
    "blocked_boundary",
    "recovery_snapshot",
}
ALLOWED_REVIEW_OUTCOMES = {"accepted", "partial", "rejected", "deferred"}


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def _pack_manifest(project_root: Path) -> dict[str, Any]:
    return _load_json(project_root / "pack.json")


def _resolve_run_root(project_root: Path, run_id: str) -> Path:
    run_root = (project_root / AUTONOMY_RUNS_ROOT / run_id).resolve()
    try:
        run_root.relative_to((project_root / AUTONOMY_RUNS_ROOT).resolve())
    except ValueError as exc:
        raise ValueError("run root must stay inside .pack-state/autonomy-runs") from exc
    if not run_root.exists():
        raise ValueError(f"{run_root}: run directory does not exist")
    summary_path = run_root / RUN_SUMMARY_NAME
    if not summary_path.exists():
        raise ValueError(f"{summary_path}: run is missing run-summary.json")
    return run_root


def _delegation_local_root(project_root: Path, run_id: str, delegation_run_id: str) -> Path:
    run_root = _resolve_run_root(project_root, run_id)
    local_root = (run_root / LOCAL_DELEGATION_DIRNAME / delegation_run_id).resolve()
    try:
        local_root.relative_to(run_root)
    except ValueError as exc:
        raise ValueError("delegation local root must stay under the run root") from exc
    return local_root


def _remote_bundle_root(delegation_run_id: str) -> Path:
    return TARGET_DELEGATION_ROOT / delegation_run_id


def _read_run_summary(run_root: Path) -> dict[str, Any]:
    payload = _load_json(run_root / RUN_SUMMARY_NAME)
    if payload.get("schema_version") != "autonomy-run-summary/v1":
        raise ValueError(f"{run_root / RUN_SUMMARY_NAME}: unsupported run-summary schema")
    return payload


def _read_feedback_memory_relative(project_root: Path, run_summary: dict[str, Any]) -> str | None:
    artifacts = run_summary.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return None
    raw_path = artifacts.get("feedback_memory_path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    candidate = Path(raw_path)
    resolved = candidate if candidate.is_absolute() else (project_root / candidate)
    resolved = resolved.resolve()
    try:
        return resolved.relative_to(project_root).as_posix()
    except ValueError:
        return None


def _make_delegation_run_id(run_id: str, task_id: str) -> str:
    safe_task = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in task_id).strip("-") or "task"
    return f"{run_id}-{safe_task}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()}"


def _target_ssh_argv(profile: dict[str, Any]) -> list[str]:
    timeouts = _profile_timeouts(profile)
    return _ssh_base_argv(profile=profile, connect_timeout=int(timeouts.get("connect_seconds", 10)))


def _ssh_write_text(
    *,
    profile: dict[str, Any],
    remote_path: Path,
    text: str,
    timeout_seconds: int,
    dry_run: bool,
) -> dict[str, Any]:
    remote_parent = remote_path.parent.as_posix()
    remote_file = remote_path.as_posix()
    remote_command = _shell_launcher_command(
        profile,
        f"mkdir -p {json.dumps(remote_parent)} && cat > {json.dumps(remote_file)}",
    )
    argv = [*_target_ssh_argv(profile), remote_command]
    if dry_run:
        return {"status": "pass", "reason": "dry_run", "ssh_argv": argv, "remote_path": remote_file}

    completed = subprocess.run(
        argv,
        input=text,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "status": "pass" if completed.returncode == 0 else "fail",
        "ssh_argv": argv,
        "remote_path": remote_file,
        "exit_code": completed.returncode,
        "stdout_preview": completed.stdout.splitlines()[:40],
        "stderr_preview": completed.stderr.splitlines()[:40],
    }


def _ssh_run_command(
    *,
    profile: dict[str, Any],
    command: str,
    timeout_seconds: int,
    dry_run: bool,
) -> dict[str, Any]:
    remote_command = _shell_launcher_command(profile, command)
    argv = [*_target_ssh_argv(profile), remote_command]
    if dry_run:
        return {"status": "pass", "reason": "dry_run", "ssh_argv": argv}

    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    return {
        "status": "pass" if completed.returncode == 0 else "fail",
        "ssh_argv": argv,
        "exit_code": completed.returncode,
        "stdout_preview": completed.stdout.splitlines()[:40],
        "stderr_preview": completed.stderr.splitlines()[:40],
    }


def _pull_remote_directory(
    *,
    profile: dict[str, Any],
    remote_bundle_root: Path,
    local_target_root: Path,
    timeout_seconds: int,
    dry_run: bool,
) -> dict[str, Any]:
    remote_command = _shell_launcher_command(
        profile,
        f"test -d {json.dumps(remote_bundle_root.as_posix())} && tar -C {json.dumps(remote_bundle_root.as_posix())} -cf - .",
    )
    ssh_argv = [*_target_ssh_argv(profile), remote_command]
    if dry_run:
        return {
            "status": "pass",
            "reason": "dry_run",
            "ssh_argv": ssh_argv,
            "remote_bundle_root": remote_bundle_root.as_posix(),
            "local_target_root": str(local_target_root),
        }

    if local_target_root.exists():
        shutil.rmtree(local_target_root)
    local_target_root.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(prefix="adf-delegated-bundle-", suffix=".tar", delete=False) as handle:
        temp_tar = Path(handle.name)

    try:
        with temp_tar.open("wb") as stream:
            completed = subprocess.run(
                ssh_argv,
                stdout=stream,
                stderr=subprocess.PIPE,
                timeout=timeout_seconds,
                check=False,
            )
        if completed.returncode != 0:
            return {
                "status": "fail",
                "remote_bundle_root": remote_bundle_root.as_posix(),
                "local_target_root": str(local_target_root),
                "ssh_argv": ssh_argv,
                "exit_code": completed.returncode,
                "stderr_preview": completed.stderr.decode("utf-8", errors="replace").splitlines()[:40],
            }
        with tarfile.open(temp_tar, "r:") as archive:
            archive.extractall(local_target_root)
    finally:
        temp_tar.unlink(missing_ok=True)

    return {
        "status": "pass",
        "remote_bundle_root": remote_bundle_root.as_posix(),
        "local_target_root": str(local_target_root),
        "ssh_argv": ssh_argv,
    }


def _validate_tier(tier: str) -> None:
    if tier not in ALLOWED_DELEGATION_TIERS:
        raise ValueError(f"delegation tier must be one of {sorted(ALLOWED_DELEGATION_TIERS)}")


def _validate_checkpoint_reason(checkpoint_reason: str) -> None:
    if checkpoint_reason not in ALLOWED_CHECKPOINT_REASONS:
        raise ValueError(f"checkpoint reason must be one of {sorted(ALLOWED_CHECKPOINT_REASONS)}")


def _validate_review_outcome(review_outcome: str) -> None:
    if review_outcome not in ALLOWED_REVIEW_OUTCOMES:
        raise ValueError(f"review outcome must be one of {sorted(ALLOWED_REVIEW_OUTCOMES)}")


def write_delegated_task_request(
    *,
    project_root: Path,
    run_id: str,
    task_id: str,
    delegation_tier: str,
    scope_summary: str,
    allowed_targets: list[str],
    expected_outputs: list[str],
    time_budget_seconds: int,
    generated_by: str,
    delegation_run_id: str | None = None,
    profile_path: str | Path | None = None,
    push_to_target: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    _validate_tier(delegation_tier)
    if time_budget_seconds <= 0:
        raise ValueError("time_budget_seconds must be positive")

    manifest = _pack_manifest(project_root)
    run_root = _resolve_run_root(project_root, run_id)
    run_summary = _read_run_summary(run_root)
    resolved_delegation_run_id = delegation_run_id or _make_delegation_run_id(run_id, task_id)
    local_root = _delegation_local_root(project_root, run_id, resolved_delegation_run_id)
    local_request_path = local_root / REQUEST_NAME
    remote_bundle_root = _remote_bundle_root(resolved_delegation_run_id)
    remote_request_path = remote_bundle_root / REQUEST_NAME
    profile = load_target_connection_profile(project_root=project_root, profile_path=profile_path)
    payload = {
        "schema_version": "adf-delegated-task-request/v1",
        "pack_id": manifest.get("pack_id"),
        "run_id": run_id,
        "delegation_run_id": resolved_delegation_run_id,
        "task_id": task_id,
        "delegation_tier": delegation_tier,
        "scope_summary": scope_summary,
        "allowed_targets": allowed_targets,
        "expected_outputs": expected_outputs,
        "time_budget_seconds": time_budget_seconds,
        "generated_at": _isoformat_z(),
        "generated_by": generated_by,
        "remote_runtime_host": socket.gethostname(),
        "remote_target_label": profile.get("target_label"),
        "target_bundle_root": remote_bundle_root.as_posix(),
        "baseline_run_summary_path": str((run_root / RUN_SUMMARY_NAME).relative_to(project_root)),
        "current_next_recommended_task_id": (run_summary.get("final_snapshot") or {}).get("next_recommended_task_id"),
    }
    _dump_json(local_request_path, payload)

    push_result = None
    if push_to_target:
        timeouts = _profile_timeouts(profile)
        push_result = _ssh_write_text(
            profile=profile,
            remote_path=remote_request_path,
            text=f"{json.dumps(payload, indent=2, sort_keys=True)}\n",
            timeout_seconds=int(timeouts.get("command_seconds", 120)),
            dry_run=dry_run,
        )
        if not dry_run and push_result["status"] != "pass":
            raise RuntimeError(
                f"failed to write delegated request to target: exit_code={push_result.get('exit_code')} stderr={push_result.get('stderr_preview')}"
            )

    return {
        "status": "pass",
        "delegation_run_id": resolved_delegation_run_id,
        "local_request_path": str(local_request_path.relative_to(project_root)),
        "target_request_path": remote_request_path.as_posix(),
        "target_bundle_root": remote_bundle_root.as_posix(),
        "pushed_to_target": push_to_target,
        "push_result": push_result,
        "request": payload,
    }


def _build_codex_prompt(request: dict[str, Any], remote_request_path: Path, remote_bundle_root: Path) -> str:
    return "\n".join(
        [
            "You are Codex CLI running on the target appliance for a bounded delegated ADF task.",
            f"Read the delegated request JSON at `{remote_request_path.as_posix()}`.",
            f"Keep all output inside `{remote_bundle_root.as_posix()}`.",
            "",
            "Rules:",
            "- Stay within the delegated scope and allowed targets from the request.",
            "- Do not modify files outside the delegated bundle root unless the request tier explicitly allows bounded lab changes.",
            "- Always write `delegated-task-result.json` even if blocked or partially complete.",
            "- Record the shell commands you ran in `commands.jsonl` as one JSON object per line.",
            "- Write a short operator-facing summary in `findings.md`.",
            "- Put any captured artifacts under `artifacts/`.",
            "- For `observe_only`, leave `intentional_mutations` as an empty array unless you truly changed the target.",
            "",
            "Required output files:",
            f"- `{(remote_bundle_root / RESULT_NAME).as_posix()}`",
            f"- `{(remote_bundle_root / COMMANDS_LOG_NAME).as_posix()}`",
            f"- `{(remote_bundle_root / FINDINGS_NAME).as_posix()}`",
            f"- `{(remote_bundle_root / 'artifacts').as_posix()}/`",
            "",
            "Suggested result schema:",
            json.dumps(
                {
                    "schema_version": "adf-delegated-task-result/v1",
                    "delegation_run_id": request["delegation_run_id"],
                    "task_id": request["task_id"],
                    "delegation_tier": request["delegation_tier"],
                    "status": "completed",
                    "summary": "Short operator-facing result summary.",
                    "returned_artifact_paths": ["artifacts/example.txt"],
                    "intentional_mutations": [],
                    "follow_up_recommendations": ["Optional next step."],
                },
                indent=2,
            ),
            "",
            "Begin by reading the request file and then complete the delegated slice.",
        ]
    ) + "\n"


def launch_target_local_codex(
    *,
    project_root: Path,
    run_id: str,
    delegation_run_id: str,
    profile_path: str | Path | None = None,
    timeout_seconds: int = 900,
    dry_run: bool = False,
) -> dict[str, Any]:
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    _resolve_run_root(project_root, run_id)
    local_root = _delegation_local_root(project_root, run_id, delegation_run_id)
    local_request_path = local_root / REQUEST_NAME
    if not local_request_path.exists():
        raise ValueError(f"{local_request_path}: write the delegated request before launching target-local Codex")

    request = _load_json(local_request_path)
    profile = load_target_connection_profile(project_root=project_root, profile_path=profile_path)
    remote_bundle_root = _remote_bundle_root(delegation_run_id)
    remote_prompt_path = remote_bundle_root / PROMPT_NAME
    remote_launcher_path = remote_bundle_root / LAUNCHER_NAME
    prompt_text = _build_codex_prompt(request, remote_bundle_root / REQUEST_NAME, remote_bundle_root)
    local_prompt_path = local_root / PROMPT_NAME
    local_launcher_path = local_root / LAUNCHER_NAME
    local_prompt_path.write_text(prompt_text, encoding="utf-8")

    launcher_text = "\n".join(
        [
            "#!/bin/bash",
            "set -euo pipefail",
            f"BUNDLE_ROOT={json.dumps(remote_bundle_root.as_posix())}",
            f"PROMPT_PATH={json.dumps(remote_prompt_path.as_posix())}",
            f"LOG_PATH={json.dumps((remote_bundle_root / LAUNCHER_LOG_NAME).as_posix())}",
            "mkdir -p \"$BUNDLE_ROOT/artifacts\"",
            "if command -v pkill >/dev/null 2>&1; then",
            "  pkill -f 'codex exec .*codex-prompt.txt' || true",
            "fi",
            "if command -v timeout >/dev/null 2>&1; then",
            f"  timeout {int(timeout_seconds)} codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox - < \"$PROMPT_PATH\" >> \"$LOG_PATH\" 2>&1",
            "else",
            "  codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox - < \"$PROMPT_PATH\" >> \"$LOG_PATH\" 2>&1",
            "fi",
            "",
        ]
    )
    local_launcher_path.write_text(launcher_text, encoding="utf-8")

    timeouts = _profile_timeouts(profile)
    prompt_push = _ssh_write_text(
        profile=profile,
        remote_path=remote_prompt_path,
        text=prompt_text,
        timeout_seconds=int(timeouts.get("command_seconds", 120)),
        dry_run=dry_run,
    )
    if not dry_run and prompt_push["status"] != "pass":
        raise RuntimeError(f"failed to push target-local Codex prompt: {prompt_push}")

    launcher_push = _ssh_write_text(
        profile=profile,
        remote_path=remote_launcher_path,
        text=launcher_text,
        timeout_seconds=int(timeouts.get("command_seconds", 120)),
        dry_run=dry_run,
    )
    if not dry_run and launcher_push["status"] != "pass":
        raise RuntimeError(f"failed to push target-local Codex launcher: {launcher_push}")

    launch_result = _ssh_run_command(
        profile=profile,
        command=f"chmod +x {json.dumps(remote_launcher_path.as_posix())} && {json.dumps(remote_launcher_path.as_posix())}",
        timeout_seconds=int(timeouts.get("command_seconds", 120)) + timeout_seconds,
        dry_run=dry_run,
    )
    if not dry_run and launch_result["status"] != "pass":
        raise RuntimeError(f"target-local Codex launch failed: {launch_result}")

    return {
        "status": "pass",
        "delegation_run_id": delegation_run_id,
        "local_prompt_path": str(local_prompt_path.relative_to(project_root)),
        "local_launcher_path": str(local_launcher_path.relative_to(project_root)),
        "remote_prompt_path": remote_prompt_path.as_posix(),
        "remote_launcher_path": remote_launcher_path.as_posix(),
        "remote_launcher_log_path": (remote_bundle_root / LAUNCHER_LOG_NAME).as_posix(),
        "prompt_push": prompt_push,
        "launcher_push": launcher_push,
        "launch_result": launch_result,
    }


def _validate_delegated_result_bundle(local_bundle_root: Path, delegation_run_id: str) -> dict[str, Any]:
    request_path = local_bundle_root / REQUEST_NAME
    result_path = local_bundle_root / RESULT_NAME
    commands_path = local_bundle_root / COMMANDS_LOG_NAME
    findings_path = local_bundle_root / FINDINGS_NAME
    artifacts_root = local_bundle_root / "artifacts"
    missing = [path.name for path in (request_path, result_path, commands_path) if not path.exists()]
    if missing:
        raise ValueError(f"{local_bundle_root}: delegated bundle missing required files {missing}")

    request = _load_json(request_path)
    result = _load_json(result_path)
    if request.get("schema_version") != "adf-delegated-task-request/v1":
        raise ValueError(f"{request_path}: unsupported delegated request schema")
    if result.get("schema_version") != "adf-delegated-task-result/v1":
        raise ValueError(f"{result_path}: unsupported delegated result schema")
    if request.get("delegation_run_id") != delegation_run_id:
        raise ValueError(f"{request_path}: delegation_run_id does not match selected id")
    if result.get("delegation_run_id") != delegation_run_id:
        raise ValueError(f"{result_path}: delegation_run_id does not match selected id")
    intentional_mutations = result.get("intentional_mutations")
    if not isinstance(intentional_mutations, list):
        raise ValueError(f"{result_path}: intentional_mutations must be an array")

    returned_artifact_paths = result.get("returned_artifact_paths")
    if not isinstance(returned_artifact_paths, list) or not all(isinstance(item, str) for item in returned_artifact_paths):
        raise ValueError(f"{result_path}: returned_artifact_paths must be a string array")

    return {
        "request_path": request_path,
        "result_path": result_path,
        "commands_path": commands_path,
        "findings_path": findings_path if findings_path.exists() else None,
        "artifacts_root": artifacts_root if artifacts_root.exists() else None,
        "request": request,
        "result": result,
    }


def pull_delegated_result_bundle(
    *,
    project_root: Path,
    run_id: str,
    delegation_run_id: str,
    profile_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    _resolve_run_root(project_root, run_id)
    local_root = _delegation_local_root(project_root, run_id, delegation_run_id)
    local_bundle_root = local_root / "target-bundle"
    remote_bundle_root = _remote_bundle_root(delegation_run_id)
    profile = load_target_connection_profile(project_root=project_root, profile_path=profile_path)
    timeouts = _profile_timeouts(profile)
    stability = _profile_stability(profile)
    pull_result = _pull_remote_directory(
        profile=profile,
        remote_bundle_root=remote_bundle_root,
        local_target_root=local_bundle_root,
        timeout_seconds=int(timeouts.get("command_seconds", 120)),
        dry_run=dry_run,
    )
    if dry_run:
        return {
            "status": "pass",
            "delegation_run_id": delegation_run_id,
            "pull_result": pull_result,
            "retry_limit": int(stability.get("heartbeat_retry_limit", 2)),
        }
    if pull_result["status"] != "pass":
        raise RuntimeError(f"failed to pull delegated bundle: {pull_result}")

    validated = _validate_delegated_result_bundle(local_bundle_root, delegation_run_id)
    artifact_paths = []
    artifacts_root = validated["artifacts_root"]
    if isinstance(artifacts_root, Path):
        artifact_paths = sorted(
            path.relative_to(project_root).as_posix()
            for path in artifacts_root.rglob("*")
            if path.is_file()
        )

    return {
        "status": "pass",
        "delegation_run_id": delegation_run_id,
        "local_bundle_root": str(local_bundle_root.relative_to(project_root)),
        "request_path": str(validated["request_path"].relative_to(project_root)),
        "result_path": str(validated["result_path"].relative_to(project_root)),
        "commands_path": str(validated["commands_path"].relative_to(project_root)),
        "findings_path": str(validated["findings_path"].relative_to(project_root)) if validated["findings_path"] else None,
        "artifact_paths": artifact_paths,
        "delegation_tier": validated["request"].get("delegation_tier"),
        "result_status": validated["result"].get("status"),
        "intentional_mutations": validated["result"].get("intentional_mutations"),
        "pull_result": pull_result,
    }


def _default_checkpoint_bundle(
    *,
    project_root: Path,
    run_id: str,
    checkpoint_reason: str,
    generated_by: str,
    remote_target_label: str | None,
) -> dict[str, Any]:
    manifest = _pack_manifest(project_root)
    run_root = _resolve_run_root(project_root, run_id)
    run_summary = _read_run_summary(run_root)
    feedback_memory_path = _read_feedback_memory_relative(project_root, run_summary)
    loop_events_path = run_root / LOOP_EVENTS_NAME
    return {
        "schema_version": "adf-remote-checkpoint-bundle/v1",
        "pack_id": manifest.get("pack_id"),
        "remote_host": socket.gethostname(),
        "remote_target_label": remote_target_label,
        "remote_build_pack_root": ".",
        "checkpoint_id": f"{run_id}-{checkpoint_reason}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()}",
        "run_id": run_id,
        "checkpoint_reason": checkpoint_reason,
        "generated_at": _isoformat_z(),
        "generated_by": generated_by,
        "source_of_truth_mode": "local_precedence_split_host",
        "local_precedence": True,
        "export_bundle": {
            "present": False,
            "bundle_manifest_path": None,
            "bundle_sha256": None,
            "authority_class": "supplementary_runtime_evidence",
            "import_ready": False,
        },
        "run_artifacts": {
            "run_summary_path": str((run_root / RUN_SUMMARY_NAME).relative_to(project_root)),
            "loop_events_path": str(loop_events_path.relative_to(project_root)) if loop_events_path.exists() else None,
            "feedback_memory_path": feedback_memory_path,
            "result_log_paths": [],
            "target_artifact_paths": [],
        },
        "candidate_changes": {
            "source_paths": [],
            "doc_paths": [],
            "prompt_paths": [],
            "work_state_fields": [],
            "backlog_task_updates": [],
            "artifact_paths": [],
        },
        "proposed_acceptance": {
            "accept_source_paths": [],
            "accept_doc_paths": [],
            "accept_artifact_paths": [],
            "accept_work_state_fields": [],
            "accept_backlog_task_updates": [],
            "defer_paths": [],
            "defer_fields": [],
            "notes": [],
        },
        "local_regeneration_required": {
            "readiness": False,
            "latest_memory_pointer": False,
            "eval_latest_index": False,
            "other_generated_surfaces": [],
        },
    }


def record_remote_checkpoint_bundle(
    *,
    project_root: Path,
    run_id: str,
    checkpoint_reason: str,
    generated_by: str,
    remote_target_label: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    _validate_checkpoint_reason(checkpoint_reason)

    run_root = _resolve_run_root(project_root, run_id)
    checkpoint_path = run_root / CHECKPOINT_BUNDLE_NAME
    if checkpoint_path.exists():
        bundle = _load_json(checkpoint_path)
    else:
        bundle = _default_checkpoint_bundle(
            project_root=project_root,
            run_id=run_id,
            checkpoint_reason=checkpoint_reason,
            generated_by=generated_by,
            remote_target_label=remote_target_label,
        )

    bundle["generated_at"] = _isoformat_z()
    bundle["generated_by"] = generated_by
    bundle["checkpoint_reason"] = checkpoint_reason
    if remote_target_label is not None:
        bundle["remote_target_label"] = remote_target_label
    bundle.setdefault("proposed_acceptance", {})
    bundle.setdefault("local_regeneration_required", {})

    notes = list(bundle["proposed_acceptance"].get("notes", []))
    if note:
        notes.append(note)
    bundle["proposed_acceptance"]["notes"] = notes

    _dump_json(checkpoint_path, bundle)
    return {
        "status": "pass",
        "checkpoint_path": str(checkpoint_path.relative_to(project_root)),
        "run_id": run_id,
        "checkpoint_reason": checkpoint_reason,
        "generated_at": bundle["generated_at"],
        "generated_by": generated_by,
        "remote_target_label": bundle.get("remote_target_label"),
        "notes": notes,
    }


def record_delegated_review(
    *,
    project_root: Path,
    run_id: str,
    delegation_run_id: str,
    checkpoint_reason: str,
    review_outcome: str,
    generated_by: str,
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    _validate_checkpoint_reason(checkpoint_reason)
    _validate_review_outcome(review_outcome)

    run_root = _resolve_run_root(project_root, run_id)
    local_root = _delegation_local_root(project_root, run_id, delegation_run_id)
    local_bundle_root = local_root / "target-bundle"
    if not local_bundle_root.exists():
        raise ValueError(f"{local_bundle_root}: pull the delegated bundle before recording review")
    validated = _validate_delegated_result_bundle(local_bundle_root, delegation_run_id)
    profile = load_target_connection_profile(project_root=project_root, profile_path=profile_path)

    checkpoint_path = run_root / CHECKPOINT_BUNDLE_NAME
    if checkpoint_path.exists():
        bundle = _load_json(checkpoint_path)
    else:
        bundle = _default_checkpoint_bundle(
            project_root=project_root,
            run_id=run_id,
            checkpoint_reason=checkpoint_reason,
            generated_by=generated_by,
            remote_target_label=str(profile.get("target_label") or ""),
        )

    bundle["generated_at"] = _isoformat_z()
    bundle["generated_by"] = generated_by
    bundle["checkpoint_reason"] = checkpoint_reason
    bundle.setdefault("run_artifacts", {})
    bundle.setdefault("candidate_changes", {})
    bundle.setdefault("proposed_acceptance", {})
    bundle.setdefault("local_regeneration_required", {})

    request_rel = validated["request_path"].relative_to(project_root).as_posix()
    result_rel = validated["result_path"].relative_to(project_root).as_posix()
    commands_rel = validated["commands_path"].relative_to(project_root).as_posix()
    findings_rel = (
        validated["findings_path"].relative_to(project_root).as_posix()
        if isinstance(validated["findings_path"], Path)
        else None
    )
    artifacts_root = validated["artifacts_root"]
    artifact_paths = sorted(
        path.relative_to(project_root).as_posix()
        for path in artifacts_root.rglob("*")
        if isinstance(artifacts_root, Path) and path.is_file()
    ) if isinstance(artifacts_root, Path) else []

    result_log_paths = list(bundle["run_artifacts"].get("result_log_paths", []))
    for candidate in [request_rel, result_rel, commands_rel, findings_rel]:
        if candidate and candidate not in result_log_paths:
            result_log_paths.append(candidate)
    bundle["run_artifacts"]["result_log_paths"] = result_log_paths

    target_artifact_paths = list(bundle["run_artifacts"].get("target_artifact_paths", []))
    for candidate in artifact_paths:
        if candidate not in target_artifact_paths:
            target_artifact_paths.append(candidate)
    bundle["run_artifacts"]["target_artifact_paths"] = target_artifact_paths

    candidate_artifact_paths = list(bundle["candidate_changes"].get("artifact_paths", []))
    for candidate in artifact_paths:
        if candidate not in candidate_artifact_paths:
            candidate_artifact_paths.append(candidate)
    bundle["candidate_changes"]["artifact_paths"] = candidate_artifact_paths

    notes = list(bundle["proposed_acceptance"].get("notes", []))
    notes.append(
        f"Delegated target-local Codex review for `{delegation_run_id}` finished with outcome `{review_outcome}` at {bundle['generated_at']}."
    )
    bundle["proposed_acceptance"]["notes"] = notes
    if review_outcome in {"accepted", "partial"}:
        accepted = list(bundle["proposed_acceptance"].get("accept_artifact_paths", []))
        for candidate in artifact_paths:
            if candidate not in accepted:
                accepted.append(candidate)
        bundle["proposed_acceptance"]["accept_artifact_paths"] = accepted
    else:
        deferred = list(bundle["proposed_acceptance"].get("defer_paths", []))
        for candidate in artifact_paths:
            if candidate not in deferred:
                deferred.append(candidate)
        bundle["proposed_acceptance"]["defer_paths"] = deferred

    bundle["delegated_codex_review"] = {
        "delegation_run_id": delegation_run_id,
        "delegation_tier": validated["request"].get("delegation_tier"),
        "delegated_result_status": validated["result"].get("status"),
        "delegated_bundle_root": str(local_bundle_root.relative_to(project_root)),
        "delegated_bundle_review_outcome": review_outcome,
        "intentional_mutations": validated["result"].get("intentional_mutations"),
        "reviewed_at": bundle["generated_at"],
        "reviewed_by": generated_by,
        "request_path": request_rel,
        "result_path": result_rel,
        "commands_path": commands_rel,
        "findings_path": findings_rel,
        "artifact_paths": artifact_paths,
        "returned_artifact_paths": validated["result"].get("returned_artifact_paths"),
        "follow_up_recommendations": validated["result"].get("follow_up_recommendations"),
        "summary": validated["result"].get("summary"),
    }

    _dump_json(checkpoint_path, bundle)
    return {
        "status": "pass",
        "checkpoint_path": str(checkpoint_path.relative_to(project_root)),
        "delegation_run_id": delegation_run_id,
        "review_outcome": review_outcome,
        "delegated_result_status": validated["result"].get("status"),
        "artifact_paths": artifact_paths,
        "intentional_mutations": validated["result"].get("intentional_mutations"),
    }
