#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import dump_json, load_json, read_now, resolve_factory_root, schema_path, validate_json_document
from remote_autonomy_staging_common import (
    canonical_local_remote_autonomy_staging_root,
    PAYLOAD_MANIFEST_SCHEMA_NAME,
    REMOTE_METADATA_DIR,
    REMOTE_TARGET_MANIFEST_FILENAME,
    build_control_plane_mutations,
    load_remote_autonomy_request,
    sha256_path,
    write_validated_scratch_lifecycle_manifest,
)


EXECUTION_MANIFEST_SCHEMA_NAME = "remote-execution-manifest.schema.json"
EXECUTION_MANIFEST_SCHEMA_VERSION = "remote-execution-manifest/v1"
EXECUTION_MANIFEST_FILENAME = "execution-manifest.json"
PROMPT_ARTIFACT_FILENAME = "invocation-prompt.txt"
SCRATCH_LIFECYCLE_FILENAME = "scratch-lifecycle.json"
BOOTSTRAP_MODE = "presence-check-only"
REMOTE_SSH_TIMEOUT_ENV = "PACKFACTORY_REMOTE_SSH_TIMEOUT_SECONDS"
REMOTE_EXECUTION_TIMEOUT_ENV = "PACKFACTORY_REMOTE_EXECUTION_TIMEOUT_SECONDS"
DEFAULT_REMOTE_BOOTSTRAP_TIMEOUT_SECONDS = 60.0
DEFAULT_REMOTE_EXECUTION_TIMEOUT_SECONDS = 900.0
MIN_REMOTE_EXECUTION_TIMEOUT_SECONDS = 600.0


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _canonical_request_text(payload: dict[str, Any]) -> str:
    return dump_json(payload)


def _sha256_text(text: str) -> str:
    digest = hashlib.sha256()
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


def _local_stage_root(local_scratch_root: Path, run_id: str) -> Path:
    return canonical_local_remote_autonomy_staging_root(local_scratch_root, run_id)


def _local_target_manifest_path(local_scratch_root: Path, run_id: str) -> Path:
    return _local_stage_root(local_scratch_root, run_id) / REMOTE_TARGET_MANIFEST_FILENAME


def _scratch_lifecycle_path(local_scratch_root: Path, run_id: str) -> Path:
    return _local_stage_root(local_scratch_root, run_id) / SCRATCH_LIFECYCLE_FILENAME


def _write_scratch_lifecycle_marker(*, local_scratch_root: Path, run_id: str, request, status: str) -> None:
    write_validated_scratch_lifecycle_manifest(
        factory_root=request.factory_root,
        path=_scratch_lifecycle_path(local_scratch_root, run_id),
        payload={
            "schema_version": "scratch-lifecycle/v1",
            "status": status,
            "updated_at": read_now().isoformat().replace("+00:00", "Z"),
            "factory_root": str(request.factory_root),
            "local_scratch_root": str(request.local_scratch_root),
            "local_stage_root": str(_local_stage_root(local_scratch_root, run_id)),
            "run_id": request.run_id,
            "source_build_pack_id": request.source_build_pack_id,
            "remote_target_label": request.remote_target_label,
            "remote_pack_dir": request.remote_pack_dir,
            "remote_run_dir": request.remote_run_dir,
            "remote_export_dir": request.remote_export_dir,
        },
    )


def _validate_local_target_manifest(factory_root: Path, path: Path) -> dict[str, Any]:
    errors = validate_json_document(path, schema_path(factory_root, PAYLOAD_MANIFEST_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return _load_object(path)


def _validate_local_execution_manifest(factory_root: Path, payload: dict[str, Any]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / EXECUTION_MANIFEST_FILENAME
        path.write_text(dump_json(payload), encoding="utf-8")
        errors = validate_json_document(path, schema_path(factory_root, EXECUTION_MANIFEST_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))


def _ssh_checked(
    request,
    remote_command: list[str],
    *,
    input_text: str | None = None,
    timeout_env: str | None = None,
    default_timeout_seconds: float | None = None,
    minimum_timeout_seconds: float | None = None,
) -> subprocess.CompletedProcess[str]:
    timeout_seconds = None
    selected_timeout_env = timeout_env
    if timeout_env:
        timeout_seconds = os.environ.get(timeout_env)
    if timeout_seconds is None:
        selected_timeout_env = REMOTE_SSH_TIMEOUT_ENV
        timeout_seconds = os.environ.get(REMOTE_SSH_TIMEOUT_ENV)
    timeout_value: float | None = None
    if timeout_seconds:
        try:
            timeout_value = float(timeout_seconds)
        except ValueError as exc:
            raise ValueError(
                f"{selected_timeout_env} must be numeric when set"
            ) from exc
        if timeout_value <= 0:
            raise ValueError(f"{selected_timeout_env} must be greater than zero when set")
    elif default_timeout_seconds is not None:
        timeout_value = default_timeout_seconds
    if (
        minimum_timeout_seconds is not None
        and timeout_value is not None
        and timeout_value < minimum_timeout_seconds
    ):
        env_label = selected_timeout_env or REMOTE_SSH_TIMEOUT_ENV
        raise ValueError(
            f"{env_label} must be at least {minimum_timeout_seconds:g} seconds "
            f"for remote autonomy execution; unset it or set {REMOTE_EXECUTION_TIMEOUT_ENV} "
            f"to a value >= {minimum_timeout_seconds:g}"
        )
    try:
        completed = subprocess.run(
            ["ssh", request.remote_address, *remote_command],
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_value,
        )
    except subprocess.TimeoutExpired as exc:
        timeout_label = timeout_value if timeout_value is not None else "configured"
        raise RuntimeError(
            f"remote command timed out after {timeout_label} seconds; "
            f"set {REMOTE_EXECUTION_TIMEOUT_ENV} or {REMOTE_SSH_TIMEOUT_ENV} to adjust the bounded wait"
        ) from exc
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "remote command failed")
    return completed


def _bootstrap_remote_target(request) -> dict[str, Any]:
    completed = _ssh_checked(
        request,
        [
            "python3",
            "-",
            request.remote_pack_dir,
        ],
        timeout_env=REMOTE_SSH_TIMEOUT_ENV,
        default_timeout_seconds=DEFAULT_REMOTE_BOOTSTRAP_TIMEOUT_SECONDS,
        input_text=textwrap.dedent(
            """
            from pathlib import Path
            import shutil
            import sys

            pack_dir = Path(sys.argv[1]).expanduser()
            if not pack_dir.exists() or not pack_dir.is_dir():
                raise SystemExit(1)
            if shutil.which("python3") is None:
                raise SystemExit(1)
            print("ok")
            """
        ).strip(),
    )
    if completed.stdout.strip() != "ok":
        raise RuntimeError("remote bootstrap did not confirm the staged pack directory and python3 availability")
    return {
        "bootstrap_mode": BOOTSTRAP_MODE,
        "remote_pack_dir": request.remote_pack_dir,
        "python_verified": True,
    }


def _load_local_task_scope(source_build_pack_root: Path) -> dict[str, Any]:
    manifest = _load_object(source_build_pack_root / "pack.json")
    contract = manifest.get("directory_contract")
    if not isinstance(contract, dict):
        return {
            "active_task_id": None,
            "next_recommended_task_id": None,
            "current_task_id": None,
            "current_task_summary": None,
        }
    work_state_path = contract.get("work_state_file")
    backlog_path = contract.get("task_backlog_file")
    if not isinstance(work_state_path, str) or not isinstance(backlog_path, str):
        return {
            "active_task_id": None,
            "next_recommended_task_id": None,
            "current_task_id": None,
            "current_task_summary": None,
        }
    work_state = _load_object(source_build_pack_root / work_state_path)
    backlog = _load_object(source_build_pack_root / backlog_path)
    active_task_id = work_state.get("active_task_id")
    next_recommended_task_id = work_state.get("next_recommended_task_id")
    current_task_id = active_task_id or next_recommended_task_id
    current_task_summary = None
    tasks = backlog.get("tasks")
    if isinstance(current_task_id, str) and isinstance(tasks, list):
        for task in tasks:
            if not isinstance(task, dict):
                continue
            if task.get("task_id") == current_task_id:
                summary = task.get("summary")
                if isinstance(summary, str) and summary:
                    current_task_summary = summary
                break
    return {
        "active_task_id": active_task_id if isinstance(active_task_id, str) else None,
        "next_recommended_task_id": next_recommended_task_id if isinstance(next_recommended_task_id, str) else None,
        "current_task_id": current_task_id if isinstance(current_task_id, str) else None,
        "current_task_summary": current_task_summary,
    }


def _build_remote_prompt(*, request, task_scope: dict[str, Any]) -> str:
    current_task_id = task_scope.get("current_task_id")
    current_task_summary = task_scope.get("current_task_summary")
    current_task_line = "- current canonical task continuity only"
    if isinstance(current_task_id, str) and current_task_id:
        current_task_line = f"- current canonical task continuity only: `{current_task_id}`"
    current_task_detail = ""
    if isinstance(current_task_summary, str) and current_task_summary:
        current_task_detail = f"\nCurrent task summary: {current_task_summary}"
    run_purpose = getattr(request, "remote_reason", "")
    run_purpose_line = ""
    if isinstance(run_purpose, str) and run_purpose.strip():
        run_purpose_line = f"\nRun purpose: {run_purpose.strip()}"
    return textwrap.dedent(
        f"""
        You are running inside a staged Project Pack Factory build-pack.

        Treat the staged build-pack root as the only writable work packet.
        Read `AGENTS.md`, `project-context.md`, and `pack.json` first.
        Then follow `pack.json.post_bootstrap_read_order` and use `pack.json.directory_contract`
        as the canonical source for the objective, backlog, work-state, readiness, eval, and
        runtime-evidence paths.

        Scope:
        {current_task_line}
        - canonical bounded validation and benchmark surfaces only
        - advisory memory only when consistent with canonical pack-local state

        Do not:
        - modify `pack.json`
        - modify `.packfactory-remote/request.json`
        - modify `.packfactory-remote/target-manifest.json`
        - create deployment pointers or mutate registry truth
        - invent new tests, new backlog items, or promotion/deployment work
        - edit unrelated source, docs, prompts, or tests outside the current bounded task boundary

        Allowed writable surfaces are limited to:
        - the declared task backlog file
        - the declared work-state file
        - the declared readiness and eval surfaces when changed through bounded pack-local workflows
        - `.pack-state/`
        - the declared candidate artifact directory
        - the declared runtime-evidence export directory

        Stop when:
        - the current task reaches a meaningful bounded checkpoint, declared escalation boundary, or ready boundary
        - a declared escalation condition is reached

        When stopping at a meaningful bounded checkpoint or blocked boundary,
        write `adf-remote-checkpoint-bundle.json` into the current run root
        before exiting. Use:
        `PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack record-remote-checkpoint-bundle --project-root . --run-id {request.run_id} --checkpoint-reason <paused_for_review|task_slice_complete|evidence_ready|blocked_boundary|recovery_snapshot> --generated-by codex --note "<short checkpoint summary>"`

        For evidence-only slices, do not stop at continuity bookkeeping alone.
        A meaningful checkpoint should name at least one concrete observed
        minute, boundary, or evidence path in the checkpoint note and returned
        artifact set.

        This run id is `{request.run_id}`.{current_task_detail}
        {run_purpose_line}
        The remote runner program must remain inside the staged build-pack root.
        """
    ).strip()


def _remote_execution_script(config: dict[str, str]) -> str:
    config_b64 = base64.b64encode(json.dumps(config, sort_keys=True).encode("utf-8")).decode("ascii")
    return textwrap.dedent(
        """
        from __future__ import annotations

        import base64
        import hashlib
        import json
        import os
        import signal
        import subprocess
        import sys
        import time
        from datetime import datetime, timezone
        from pathlib import Path
        from typing import Any


        EXECUTION_MANIFEST_FILENAME = "execution-manifest.json"
        PROMPT_ARTIFACT_FILENAME = "invocation-prompt.txt"
        ACTIVE_RUN_STATE_FILENAME = "active-run-state.json"
        EXECUTION_MANIFEST_SCHEMA_VERSION = "remote-execution-manifest/v1"
        BOOTSTRAP_MODE = "presence-check-only"
        REMOTE_METADATA_DIR = ".packfactory-remote"
        RUNNER_SIGNAL_GRACE_SECONDS = 5.0
        CONFIG = json.loads(base64.b64decode("__REMOTE_EXECUTION_CONFIG_B64__").decode("utf-8"))


        def _now() -> str:
            return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


        def _load_json(path: Path) -> dict[str, Any]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError(f"{path}: JSON document must contain an object")
            return payload


        def _dump_json(path: Path, payload: dict[str, Any]) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")


        def _seal_text(path: Path, content: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")


        def _sha256_path(path: Path) -> str:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()


        def _sha256_text(text: str) -> str:
            digest = hashlib.sha256()
            digest.update(text.encode("utf-8"))
            return digest.hexdigest()


        def _active_run_state_path(pack_root: Path) -> Path:
            return pack_root / REMOTE_METADATA_DIR / ACTIVE_RUN_STATE_FILENAME


        def _write_active_run_state(pack_root: Path, payload: dict[str, Any]) -> None:
            _dump_json(_active_run_state_path(pack_root), payload)


        def _clear_active_run_state(pack_root: Path) -> None:
            state_path = _active_run_state_path(pack_root)
            if state_path.exists():
                state_path.unlink()


        def _process_exists(pid: int) -> bool:
            if pid <= 0:
                return False
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
            return True


        def _process_group_exists(pgid: int) -> bool:
            if pgid <= 0:
                return False
            try:
                os.killpg(pgid, 0)
            except ProcessLookupError:
                return False
            except PermissionError:
                return True
            return True


        def _terminate_process_group(pgid: int) -> None:
            if not _process_group_exists(pgid):
                return
            try:
                os.killpg(pgid, signal.SIGTERM)
            except ProcessLookupError:
                return
            deadline = time.monotonic() + RUNNER_SIGNAL_GRACE_SECONDS
            while time.monotonic() < deadline:
                if not _process_group_exists(pgid):
                    return
                time.sleep(0.2)
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                return


        def _cleanup_stale_active_run(pack_root: Path, *, run_id: str) -> dict[str, Any] | None:
            state_path = _active_run_state_path(pack_root)
            if not state_path.exists():
                return None
            payload = _load_json(state_path)
            active_run_id = payload.get("run_id")
            raw_pid = payload.get("pid")
            raw_pgid = payload.get("pgid")
            pid = int(raw_pid) if isinstance(raw_pid, int) else None
            pgid = int(raw_pgid) if isinstance(raw_pgid, int) else None
            cleanup_action = {
                "state_path": state_path.relative_to(pack_root).as_posix(),
                "recorded_run_id": active_run_id if isinstance(active_run_id, str) else None,
                "requested_run_id": run_id,
                "recorded_pid": pid,
                "recorded_pgid": pgid,
                "cleanup_trigger": "same_run_replay" if active_run_id == run_id else "different_run_replay",
                "cleanup_started_at": _now(),
            }
            if pgid is not None and _process_group_exists(pgid):
                _terminate_process_group(pgid)
                cleanup_action["cleanup_signal"] = "process_group"
            elif pid is not None and _process_exists(pid):
                try:
                    os.kill(pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                cleanup_action["cleanup_signal"] = "pid_sigterm"
            else:
                cleanup_action["cleanup_signal"] = "none_needed"
            cleanup_action["cleanup_finished_at"] = _now()
            state_path.unlink()
            return cleanup_action


        def _run_capture_shell(
            command: str,
            *,
            cwd: Path,
            input_text: str | None = None,
        ) -> subprocess.CompletedProcess[str]:
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            return subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                cwd=cwd,
                input=input_text,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )


        def _run_shell(
            command: str,
            *,
            cwd: Path,
            pack_root: Path,
            run_id: str,
            input_text: str | None = None,
        ) -> tuple[subprocess.CompletedProcess[str], int | None]:
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            process = subprocess.Popen(
                command,
                shell=True,
                executable="/bin/bash",
                cwd=cwd,
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                start_new_session=True,
            )
            interrupted_signal: int | None = None
            pgid = os.getpgid(process.pid)
            _write_active_run_state(
                pack_root,
                {
                    "schema_version": "remote-active-run-state/v1",
                    "run_id": run_id,
                    "pid": process.pid,
                    "pgid": pgid,
                    "status": "running",
                    "started_at": _now(),
                    "command": command,
                },
            )

            def _handle_signal(signum: int, _frame: Any) -> None:
                nonlocal interrupted_signal
                interrupted_signal = signum
                _write_active_run_state(
                    pack_root,
                    {
                        "schema_version": "remote-active-run-state/v1",
                        "run_id": run_id,
                        "pid": process.pid,
                        "pgid": pgid,
                        "status": "interrupt_requested",
                        "signal": signum,
                        "updated_at": _now(),
                        "command": command,
                    },
                )
                _terminate_process_group(pgid)

            previous_handlers = {
                sig: signal.getsignal(sig)
                for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
            }
            try:
                for sig in previous_handlers:
                    signal.signal(sig, _handle_signal)
                stdout_text, stderr_text = process.communicate(input=input_text)
            finally:
                for sig, previous_handler in previous_handlers.items():
                    signal.signal(sig, previous_handler)
                if process.poll() is None:
                    _terminate_process_group(pgid)
                    process.wait()
                _clear_active_run_state(pack_root)

            return (
                subprocess.CompletedProcess(
                    args=command,
                    returncode=int(process.returncode or 0),
                    stdout=stdout_text,
                    stderr=stderr_text,
                ),
                interrupted_signal,
            )


        def _snapshot_tree(pack_root: Path) -> dict[str, str]:
            snapshot: dict[str, str] = {}
            for path in sorted(pack_root.rglob("*")):
                if not path.is_file():
                    continue
                snapshot[path.relative_to(pack_root).as_posix()] = _sha256_path(path)
            return snapshot


        def _allowed_mutation(relative_path: str, contract: dict[str, Any]) -> bool:
            allowed_exact = {
                contract.get("task_backlog_file"),
                contract.get("work_state_file"),
                contract.get("readiness_file"),
                contract.get("eval_latest_index_file"),
                f"{REMOTE_METADATA_DIR}/{EXECUTION_MANIFEST_FILENAME}",
                f"{REMOTE_METADATA_DIR}/{ACTIVE_RUN_STATE_FILENAME}",
            }
            if relative_path in {value for value in allowed_exact if isinstance(value, str)}:
                return True
            allowed_prefixes = [
                ".pack-state/",
                "eval/history/",
            ]
            candidate_release_dir = contract.get("candidate_release_dir")
            if isinstance(candidate_release_dir, str):
                allowed_prefixes.append(f"{candidate_release_dir.rstrip('/')}/")
            runtime_evidence_export_dir = contract.get("runtime_evidence_export_dir")
            if isinstance(runtime_evidence_export_dir, str):
                allowed_prefixes.append(f"{runtime_evidence_export_dir.rstrip('/')}/")
            return any(relative_path.startswith(prefix) for prefix in allowed_prefixes)


        def _changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
            changed: list[str] = []
            for relative_path in sorted(set(before) | set(after)):
                if before.get(relative_path) != after.get(relative_path):
                    changed.append(relative_path)
            return changed


        def _load_contract(pack_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
            manifest = _load_json(pack_root / "pack.json")
            if manifest.get("pack_kind") != "build_pack":
                raise ValueError("pack.json must declare a build_pack manifest")
            contract = manifest.get("directory_contract")
            if not isinstance(contract, dict):
                raise ValueError("pack.json.directory_contract must be an object")
            return manifest, contract


        def _require_file(pack_root: Path, contract: dict[str, Any], key: str) -> Path:
            value = contract.get(key)
            if not isinstance(value, str) or not value:
                raise ValueError(f"directory_contract.{key} must be a non-empty string")
            path = (pack_root / value).resolve()
            path.relative_to(pack_root)
            if not path.exists():
                raise ValueError(f"{path}: required contract path is missing")
            return path


        def _ensure_execution_writable_dirs(pack_root: Path, contract: dict[str, Any]) -> None:
            for key in ("eval_history_dir", "runtime_evidence_export_dir", "candidate_release_dir"):
                value = contract.get(key)
                if isinstance(value, str) and value:
                    path = (pack_root / value).resolve()
                    path.relative_to(pack_root)
                    path.mkdir(parents=True, exist_ok=True)
            local_state_dir = contract.get("local_state_dir")
            if isinstance(local_state_dir, str) and local_state_dir:
                autonomy_runs_dir = (pack_root / local_state_dir / "autonomy-runs").resolve()
                autonomy_runs_dir.relative_to(pack_root)
                autonomy_runs_dir.mkdir(parents=True, exist_ok=True)


        def _terminal_state(pack_root: Path, contract: dict[str, Any]) -> tuple[str, str]:
            backlog = _load_json(_require_file(pack_root, contract, "task_backlog_file"))
            work_state = _load_json(_require_file(pack_root, contract, "work_state_file"))
            readiness = _load_json(_require_file(pack_root, contract, "readiness_file"))
            tasks = backlog.get("tasks", [])
            task_statuses = {
                str(task.get("task_id")): str(task.get("status"))
                for task in tasks
                if isinstance(task, dict) and isinstance(task.get("task_id"), str)
            }
            current_task_id = None
            active_task_id = work_state.get("active_task_id")
            if isinstance(active_task_id, str) and active_task_id in task_statuses:
                current_task_id = active_task_id
            else:
                next_recommended_task_id = work_state.get("next_recommended_task_id")
                if isinstance(next_recommended_task_id, str) and next_recommended_task_id in task_statuses:
                    current_task_id = next_recommended_task_id
            ready_boundary = (
                work_state.get("autonomy_state") == "ready_for_deploy"
                and work_state.get("next_recommended_task_id") is None
                and readiness.get("ready_for_deployment") is True
            )
            escalation_state = work_state.get("escalation_state")
            if escalation_state not in (None, "none") or work_state.get("autonomy_state") in {"blocked", "awaiting_operator"}:
                return "escalated", "declared_escalation_boundary"
            if ready_boundary:
                return "promotion_or_deployment_boundary", "ready_for_deploy_boundary"
            if current_task_id is None:
                return "stopped", "no_current_task_declared"
            if task_statuses.get(current_task_id) == "completed":
                return "current_task_completed", "current_task_completed"
            return "stopped", "current_task_incomplete"


        def _substitute_export_command(command: str, run_id: str, actor: str) -> str:
            return command.replace("<run-id>", run_id).replace("<actor>", actor)


        def _run_record_command(pack_root: Path, command: list[str]) -> dict[str, Any]:
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            completed = subprocess.run(
                command,
                cwd=pack_root,
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "record command failed")
            payload = json.loads(completed.stdout)
            if not isinstance(payload, dict):
                raise ValueError("record command output must be a JSON object")
            return payload


        def _preflight(
            *,
            pack_root: Path,
            request_sha256: str,
            target_manifest_sha256: str,
            source_build_pack_id: str,
            run_id: str,
            remote_pack_dir: str,
            remote_run_dir: str,
            remote_export_dir: str,
        ) -> dict[str, Any]:
            request_path = pack_root / REMOTE_METADATA_DIR / "request.json"
            target_manifest_path = pack_root / REMOTE_METADATA_DIR / "target-manifest.json"
            if not request_path.exists():
                raise ValueError(f"{request_path}: staged request is missing")
            if not target_manifest_path.exists():
                raise ValueError(f"{target_manifest_path}: staged target manifest is missing")
            if _sha256_path(request_path) != request_sha256:
                raise ValueError("staged request checksum does not match the selected request")
            if _sha256_path(target_manifest_path) != target_manifest_sha256:
                raise ValueError("staged target manifest checksum does not match the selected local manifest")

            request_payload = _load_json(request_path)
            target_manifest = _load_json(target_manifest_path)
            request_text = request_path.read_text(encoding="utf-8")
            target_manifest_text = target_manifest_path.read_text(encoding="utf-8")
            if request_payload.get("source_build_pack_id") != source_build_pack_id:
                raise ValueError("staged request source_build_pack_id does not match the selected request")
            if request_payload.get("run_id") != run_id:
                raise ValueError("staged request run_id does not match the selected request")
            for key, expected in (
                ("remote_pack_dir", remote_pack_dir),
                ("remote_run_dir", remote_run_dir),
                ("remote_export_dir", remote_export_dir),
            ):
                if request_payload.get(key) != expected:
                    raise ValueError(f"staged request {key} does not match the selected request")
                if target_manifest.get(key) != expected:
                    raise ValueError(f"target manifest {key} does not match the selected request")
            if target_manifest.get("source_build_pack_id") != source_build_pack_id:
                raise ValueError("target manifest source_build_pack_id does not match the selected request")
            if target_manifest.get("run_id") != run_id:
                raise ValueError("target manifest run_id does not match the selected request")

            manifest, contract = _load_contract(pack_root)
            for key in ("project_objective_file", "task_backlog_file", "work_state_file", "readiness_file", "eval_latest_index_file"):
                _require_file(pack_root, contract, key)

            portable_keys = (
                "portable_runtime_tools_dir",
                "portable_runtime_schemas_dir",
                "portable_runtime_helper_manifest",
            )
            portable_values = [contract.get(key) for key in portable_keys]
            if any(value is not None for value in portable_values):
                for key in portable_keys:
                    _require_file(pack_root, contract, key)

            task_backlog = _load_json(_require_file(pack_root, contract, "task_backlog_file"))
            tasks = task_backlog.get("tasks", [])
            if not isinstance(tasks, list):
                raise ValueError("task backlog must declare a tasks array")
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                validation_commands = task.get("validation_commands", [])
                if not isinstance(validation_commands, list):
                    raise ValueError("task validation_commands must be an array")
                for command in validation_commands:
                    if isinstance(command, str) and "../../tools/" in command:
                        raise ValueError("starter task commands must not retain factory-relative helper paths")

            entrypoints = manifest.get("entrypoints")
            if not isinstance(entrypoints, dict) or not isinstance(entrypoints.get("export_runtime_evidence_command"), str):
                raise ValueError("pack.json.entrypoints.export_runtime_evidence_command must exist")

            return {
                "pack_id": manifest.get("pack_id"),
                "export_command_template": entrypoints["export_runtime_evidence_command"],
                "contract": contract,
                "sealed_request_text": request_text,
                "sealed_target_manifest_text": target_manifest_text,
            }


        def main() -> None:
            pack_root = Path(CONFIG["pack_root"]).expanduser().resolve()
            request_sha256 = CONFIG["request_sha256"]
            target_manifest_sha256 = CONFIG["target_manifest_sha256"]
            source_build_pack_id = CONFIG["source_build_pack_id"]
            run_id = CONFIG["run_id"]
            remote_pack_dir = CONFIG["remote_pack_dir"]
            remote_run_dir = CONFIG["remote_run_dir"]
            remote_export_dir = CONFIG["remote_export_dir"]
            remote_runner = CONFIG["remote_runner"]
            actor = CONFIG["actor"]
            prompt_text = base64.b64decode(CONFIG["prompt_b64"]).decode("utf-8")
            prompt_sha256 = _sha256_text(prompt_text)

            started_at = _now()
            preflight = _preflight(
                pack_root=pack_root,
                request_sha256=request_sha256,
                target_manifest_sha256=target_manifest_sha256,
                source_build_pack_id=source_build_pack_id,
                run_id=run_id,
                remote_pack_dir=remote_pack_dir,
                remote_run_dir=remote_run_dir,
                remote_export_dir=remote_export_dir,
            )
            contract = preflight["contract"]
            _ensure_execution_writable_dirs(pack_root, contract)
            stale_active_run_cleanup = _cleanup_stale_active_run(pack_root, run_id=run_id)
            prompt_artifact_path = pack_root / REMOTE_METADATA_DIR / PROMPT_ARTIFACT_FILENAME
            _dump_json(
                pack_root / REMOTE_METADATA_DIR / "invocation-context.json",
                {
                    "prompt_sha256": prompt_sha256,
                    "remote_runner": remote_runner,
                    "run_id": run_id,
                },
            )
            invocation_context_path = pack_root / REMOTE_METADATA_DIR / "invocation-context.json"
            sealed_invocation_context_text = invocation_context_path.read_text(encoding="utf-8")
            prompt_artifact_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_artifact_path.write_text(prompt_text, encoding="utf-8")
            before_snapshot = _snapshot_tree(pack_root)

            record_helper = [
                "python3",
                ".packfactory-runtime/tools/record_autonomy_run.py",
            ]
            _run_record_command(
                pack_root,
                [
                    *record_helper,
                    "start",
                    "--pack-root",
                    ".",
                    "--run-id",
                    run_id,
                    "--note",
                    "Remote execution runner initialized the autonomy run before agent invocation.",
                ],
            )

            runner_completed, interrupted_signal = _run_shell(
                remote_runner,
                cwd=pack_root,
                pack_root=pack_root,
                run_id=run_id,
                input_text=prompt_text,
            )
            _seal_text(pack_root / REMOTE_METADATA_DIR / "request.json", str(preflight["sealed_request_text"]))
            _seal_text(
                pack_root / REMOTE_METADATA_DIR / "target-manifest.json",
                str(preflight["sealed_target_manifest_text"]),
            )
            _seal_text(invocation_context_path, sealed_invocation_context_text)
            after_snapshot = _snapshot_tree(pack_root)
            changed_paths = _changed_paths(before_snapshot, after_snapshot)
            boundary_violations = [
                path for path in changed_paths if not _allowed_mutation(path, contract)
            ]

            terminal_outcome, terminal_reason = _terminal_state(pack_root, contract)
            if interrupted_signal is not None:
                signal_name = signal.Signals(interrupted_signal).name.lower()
                terminal_outcome = "stopped"
                terminal_reason = f"remote_controller_signal_interrupted_runner:{signal_name}"
            elif boundary_violations:
                terminal_outcome = "boundary_violation"
                terminal_reason = "unauthorized_writable_surface"
            elif terminal_outcome == "stopped" and runner_completed.returncode != 0:
                terminal_reason = "runner_exited_nonzero_with_incomplete_pack_state"

            event_type = "run_completed"
            if terminal_outcome == "escalated":
                event_type = "escalation_raised"
            elif terminal_outcome in {"stopped", "boundary_violation", "export_failed"}:
                event_type = "run_stopped"

            _run_record_command(
                pack_root,
                [
                    *record_helper,
                    "append-event",
                    "--pack-root",
                    ".",
                    "--run-id",
                    run_id,
                    "--event-type",
                    event_type,
                    "--outcome",
                    terminal_outcome,
                    "--command",
                    remote_runner,
                    "--note",
                    f"runner_returncode={runner_completed.returncode}",
                    "--stop-reason",
                    terminal_reason,
                ]
                + (
                    ["--note", f"runner_interrupted_signal={interrupted_signal}"]
                    if interrupted_signal is not None
                    else []
                )
                + sum(
                    [["--note", f"boundary_violation={path}"] for path in boundary_violations],
                    [],
                ),
            )
            run_summary = _run_record_command(
                pack_root,
                [
                    *record_helper,
                    "finalize",
                    "--pack-root",
                    ".",
                    "--run-id",
                    run_id,
                ],
            )

            export_command = None
            export_bundle_path = None
            export_completed_at = None
            exported_run_id = None
            export_status = "not_attempted"
            export_error = None
            if terminal_outcome != "boundary_violation":
                export_command = _substitute_export_command(str(preflight["export_command_template"]), run_id, actor)
                export_completed = _run_capture_shell(export_command, cwd=pack_root)
                if export_completed.returncode != 0:
                    export_status = "failed"
                    export_error = export_completed.stderr.strip() or export_completed.stdout.strip() or "runtime evidence export failed"
                    terminal_outcome = "export_failed"
                    terminal_reason = "runtime_evidence_export_failed"
                else:
                    export_payload = json.loads(export_completed.stdout)
                    if not isinstance(export_payload, dict):
                        raise ValueError("runtime evidence export must emit a JSON object")
                    export_bundle_path = str(export_payload.get("bundle_root"))
                    bundle_manifest = _load_json(pack_root / export_bundle_path / "bundle.json")
                    if bundle_manifest.get("run_id") != run_id:
                        raise ValueError("exported bundle run_id does not match the executed run")
                    exported_run_id = str(bundle_manifest["run_id"])
                    export_completed_at = str(bundle_manifest.get("generated_at"))
                    export_status = "succeeded"

            execution_manifest = {
                "schema_version": EXECUTION_MANIFEST_SCHEMA_VERSION,
                "source_build_pack_id": source_build_pack_id,
                "run_id": run_id,
                "request_sha256": request_sha256,
                "target_manifest_sha256": target_manifest_sha256,
                "remote_runner": remote_runner,
                "runner_returncode": runner_completed.returncode,
                "runner_interrupted_signal": (
                    signal.Signals(interrupted_signal).name.lower() if interrupted_signal is not None else None
                ),
                "stale_active_run_cleanup": stale_active_run_cleanup,
                "prompt_sha256": prompt_sha256,
                "prompt_artifact_path": f"{REMOTE_METADATA_DIR}/{PROMPT_ARTIFACT_FILENAME}",
                "bootstrap_mode": BOOTSTRAP_MODE,
                "started_at": started_at,
                "stopped_at": _now(),
                "terminal_outcome": terminal_outcome,
                "terminal_reason": terminal_reason,
                "export_status": export_status,
                "export_command": export_command,
                "export_bundle_path": export_bundle_path,
                "export_completed_at": export_completed_at,
                "exported_run_id": exported_run_id,
                "export_error": export_error,
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
            execution_manifest_path = pack_root / REMOTE_METADATA_DIR / EXECUTION_MANIFEST_FILENAME
            _dump_json(execution_manifest_path, execution_manifest)

            result = {
                "status": "completed" if terminal_outcome in {"promotion_or_deployment_boundary", "current_task_completed"} else "stopped",
                "source_build_pack_id": source_build_pack_id,
                "run_id": run_id,
                "remote_runner": remote_runner,
                "bootstrap_mode": BOOTSTRAP_MODE,
                "terminal_outcome": terminal_outcome,
                "terminal_reason": terminal_reason,
                "runner_returncode": runner_completed.returncode,
                "runner_interrupted_signal": (
                    signal.Signals(interrupted_signal).name.lower() if interrupted_signal is not None else None
                ),
                "stale_active_run_cleanup": stale_active_run_cleanup,
                "changed_paths": changed_paths,
                "boundary_violations": boundary_violations,
                "execution_manifest_path": f"{REMOTE_METADATA_DIR}/{EXECUTION_MANIFEST_FILENAME}",
                "execution_manifest": execution_manifest,
                "export_bundle_path": export_bundle_path,
                "exported_run_id": exported_run_id,
                "run_summary_path": f".pack-state/autonomy-runs/{run_id}/run-summary.json",
                "run_summary": run_summary,
                "prompt_sha256": prompt_sha256,
                "prompt_artifact_path": f"{REMOTE_METADATA_DIR}/{PROMPT_ARTIFACT_FILENAME}",
                "runner_stdout": runner_completed.stdout,
                "runner_stderr": runner_completed.stderr,
            }
            sys.stdout.write(json.dumps(result, sort_keys=True) + "\\n")


        if __name__ == "__main__":
            main()
        """
    ).strip().replace("__REMOTE_EXECUTION_CONFIG_B64__", config_b64)


def run_remote_autonomy_loop(factory_root: Path, request_path: Path) -> dict[str, Any]:
    request = load_remote_autonomy_request(factory_root=factory_root, request_path=request_path)
    local_target_manifest_path = _local_target_manifest_path(request.local_scratch_root, request.run_id)
    if not local_target_manifest_path.exists():
        raise FileNotFoundError(f"missing staged target manifest: {local_target_manifest_path}")
    local_target_manifest = _validate_local_target_manifest(factory_root, local_target_manifest_path)
    request_text = _canonical_request_text(request.raw_payload)
    request_sha256 = _sha256_text(request_text)
    expected_request_sha256 = local_target_manifest.get("request_sha256")
    if request_sha256 != expected_request_sha256:
        raise ValueError("remote staged request checksum must match the local staging manifest")
    target_manifest_sha256 = sha256_path(local_target_manifest_path)
    _write_scratch_lifecycle_marker(
        local_scratch_root=request.local_scratch_root,
        run_id=request.run_id,
        request=request,
        status="executing",
    )

    bootstrap = _bootstrap_remote_target(request)
    task_scope = _load_local_task_scope(Path(request.source_build_pack_root).expanduser().resolve())
    prompt_text = _build_remote_prompt(request=request, task_scope=task_scope)
    remote_completed = _ssh_checked(
        request,
        ["python3", "-"],
        timeout_env=REMOTE_EXECUTION_TIMEOUT_ENV,
        default_timeout_seconds=DEFAULT_REMOTE_EXECUTION_TIMEOUT_SECONDS,
        minimum_timeout_seconds=MIN_REMOTE_EXECUTION_TIMEOUT_SECONDS,
        input_text=_remote_execution_script(
            {
                "pack_root": request.remote_pack_dir,
                "request_sha256": request_sha256,
                "target_manifest_sha256": target_manifest_sha256,
                "source_build_pack_id": request.source_build_pack_id,
                "run_id": request.run_id,
                "remote_pack_dir": request.remote_pack_dir,
                "remote_run_dir": request.remote_run_dir,
                "remote_export_dir": request.remote_export_dir,
                "remote_runner": request.remote_runner,
                "actor": request.staged_by,
                "prompt_b64": base64.b64encode(prompt_text.encode("utf-8")).decode("ascii"),
            }
        ),
    )
    remote_payload = json.loads(remote_completed.stdout)
    if not isinstance(remote_payload, dict):
        raise ValueError("remote execution result must be a JSON object")

    execution_manifest = remote_payload.get("execution_manifest")
    if not isinstance(execution_manifest, dict):
        raise ValueError("remote execution result must include execution_manifest")
    _validate_local_execution_manifest(factory_root, execution_manifest)
    if execution_manifest.get("request_sha256") != request_sha256:
        raise ValueError("execution manifest request_sha256 must match the staged request")
    if execution_manifest.get("target_manifest_sha256") != target_manifest_sha256:
        raise ValueError("execution manifest target_manifest_sha256 must match the local staging manifest")
    _write_scratch_lifecycle_marker(
        local_scratch_root=request.local_scratch_root,
        run_id=request.run_id,
        request=request,
        status="completed",
    )

    return {
        "schema_version": "remote-autonomy-loop-result/v1",
        "status": remote_payload.get("status"),
        "source_build_pack_id": request.source_build_pack_id,
        "local_scratch_root": str(request.local_scratch_root),
        "run_id": request.run_id,
        "remote_host": request.remote_host,
        "remote_user": request.remote_user,
        "remote_target_label": request.remote_target_label,
        "remote_pack_dir": request.remote_pack_dir,
        "remote_run_dir": request.remote_run_dir,
        "remote_export_dir": request.remote_export_dir,
        "bootstrap": bootstrap,
        "request_sha256": request_sha256,
        "target_manifest_sha256": target_manifest_sha256,
        "local_target_manifest_path": str(local_target_manifest_path),
        "terminal_outcome": remote_payload.get("terminal_outcome"),
        "terminal_reason": remote_payload.get("terminal_reason"),
        "boundary_violations": remote_payload.get("boundary_violations", []),
        "changed_paths": remote_payload.get("changed_paths", []),
        "execution_manifest_path": f"{request.remote_pack_dir}/{REMOTE_METADATA_DIR}/{EXECUTION_MANIFEST_FILENAME}",
        "prompt_sha256": execution_manifest.get("prompt_sha256"),
        "prompt_artifact_path": execution_manifest.get("prompt_artifact_path"),
        "export_status": execution_manifest.get("export_status"),
        "export_bundle_path": remote_payload.get("export_bundle_path"),
        "exported_run_id": remote_payload.get("exported_run_id"),
        "scratch_lifecycle_path": str(_scratch_lifecycle_path(request.local_scratch_root, request.run_id)),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded autonomous build-pack loop on a staged remote target.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory repository root.")
    parser.add_argument("--request-file", required=True, help="Path to a remote-autonomy-run-request/v1 JSON file.")
    parser.add_argument("--output", default="json", choices=("json",), help="Output format.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    request_path = Path(args.request_file).expanduser().resolve()
    result = run_remote_autonomy_loop(factory_root, request_path)
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
