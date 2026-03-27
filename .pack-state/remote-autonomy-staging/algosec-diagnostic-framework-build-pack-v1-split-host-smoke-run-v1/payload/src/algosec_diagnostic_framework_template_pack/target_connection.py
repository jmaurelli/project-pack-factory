from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

DEFAULT_TARGET_PROFILE = Path("docs/remote-targets/algosec-lab/target-connection-profile.json")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def load_target_connection_profile(
    *,
    project_root: Path,
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    selected_path = project_root / (Path(profile_path) if profile_path else DEFAULT_TARGET_PROFILE)
    selected_path = selected_path.resolve()
    try:
        selected_path.relative_to(project_root)
    except ValueError as exc:
        raise ValueError("target connection profile must stay under the selected project root") from exc
    payload = _load_json(selected_path)
    if payload.get("schema_version") != "adf-target-connection-profile/v1":
        raise ValueError("target connection profile schema_version must be `adf-target-connection-profile/v1`")
    return payload


def _profile_shell(profile: dict[str, Any]) -> dict[str, Any]:
    shell = profile.get("shell", {})
    if not isinstance(shell, dict):
        raise ValueError("profile.shell must be an object")
    return shell


def _profile_timeouts(profile: dict[str, Any]) -> dict[str, Any]:
    payload = profile.get("timeouts", {})
    if not isinstance(payload, dict):
        raise ValueError("profile.timeouts must be an object")
    return payload


def _profile_stability(profile: dict[str, Any]) -> dict[str, Any]:
    payload = profile.get("stability", {})
    if not isinstance(payload, dict):
        raise ValueError("profile.stability must be an object")
    return payload


def _shell_launcher_command(profile: dict[str, Any], command: str) -> str:
    shell = _profile_shell(profile)
    launcher_prefix = shell.get("launcher_prefix", ["env", "-i"])
    shell_path = str(shell.get("shell_path", "/bin/bash"))
    shell_args = shell.get("shell_args", ["--noprofile", "--norc"])
    launcher_env = shell.get("launcher_env", {})
    if not isinstance(launcher_prefix, list) or not all(isinstance(item, str) for item in launcher_prefix):
        raise ValueError("profile.shell.launcher_prefix must be a string array")
    if not isinstance(shell_args, list) or not all(isinstance(item, str) for item in shell_args):
        raise ValueError("profile.shell.shell_args must be a string array")
    if not isinstance(launcher_env, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in launcher_env.items()):
        raise ValueError("profile.shell.launcher_env must be an object of string pairs")

    argv = [*launcher_prefix]
    for key, value in launcher_env.items():
        argv.append(f"{key}={value}")
    argv.extend([shell_path, *shell_args, "-c", command])
    return " ".join(shlex.quote(part) for part in argv)


def _ssh_base_argv(
    *,
    profile: dict[str, Any],
    connect_timeout: int,
) -> list[str]:
    destination = str(profile.get("ssh_destination") or "").strip()
    ssh_user = str(profile.get("ssh_user") or "").strip()
    ssh_host = str(profile.get("ssh_host") or "").strip()
    if not destination:
        if not ssh_user or not ssh_host:
            raise ValueError("profile must define ssh_destination or both ssh_user and ssh_host")
        destination = f"{ssh_user}@{ssh_host}"

    stability = _profile_stability(profile)
    server_alive_interval = int(stability.get("server_alive_interval_seconds", 15))
    server_alive_count_max = int(stability.get("server_alive_count_max", 2))
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        f"ConnectTimeout={connect_timeout}",
        "-o",
        f"ServerAliveInterval={server_alive_interval}",
        "-o",
        f"ServerAliveCountMax={server_alive_count_max}",
        destination,
    ]


def _run_ssh_command(
    *,
    profile: dict[str, Any],
    remote_command: str,
    timeout_seconds: int,
    retry_limit: int,
    retry_backoff_seconds: int,
    dry_run: bool,
) -> dict[str, Any]:
    ssh_binary = shutil.which("ssh")
    ssh_argv = [
        *(_ssh_base_argv(profile=profile, connect_timeout=int(_profile_timeouts(profile).get("connect_seconds", 10)))),
        remote_command,
    ]
    attempts: list[dict[str, Any]] = []
    if ssh_binary is None:
        return {
            "status": "fail",
            "reason": "ssh is not installed",
            "ssh_argv": ssh_argv,
            "attempts": attempts,
            "dry_run": dry_run,
        }
    if dry_run:
        return {
            "status": "pass",
            "reason": "dry_run",
            "ssh_argv": ssh_argv,
            "attempts": attempts,
            "dry_run": True,
        }

    for attempt_index in range(retry_limit + 1):
        started_at = time.monotonic()
        try:
            completed = subprocess.run(
                ssh_argv,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
            latency_ms = int((time.monotonic() - started_at) * 1000)
            stdout_lines = completed.stdout.splitlines()
            stderr_lines = completed.stderr.splitlines()
            attempt = {
                "attempt_index": attempt_index,
                "status": "completed" if completed.returncode == 0 else "nonzero_exit",
                "exit_code": completed.returncode,
                "latency_ms": latency_ms,
                "stdout_preview": stdout_lines[:40],
                "stderr_preview": stderr_lines[:40],
            }
            attempts.append(attempt)
            if completed.returncode == 0:
                return {
                    "status": "pass",
                    "ssh_argv": ssh_argv,
                    "attempts": attempts,
                    "dry_run": False,
                }
        except subprocess.TimeoutExpired as exc:
            latency_ms = int((time.monotonic() - started_at) * 1000)
            attempts.append(
                {
                    "attempt_index": attempt_index,
                    "status": "timeout",
                    "exit_code": None,
                    "latency_ms": latency_ms,
                    "stdout_preview": (exc.stdout or "").splitlines()[:40],
                    "stderr_preview": (exc.stderr or "").splitlines()[:40],
                }
            )
        if attempt_index < retry_limit:
            time.sleep(retry_backoff_seconds)

    return {
        "status": "fail",
        "reason": "retry_limit_exhausted",
        "ssh_argv": ssh_argv,
        "attempts": attempts,
        "dry_run": False,
    }


def target_preflight(
    *,
    project_root: Path,
    profile_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    profile = load_target_connection_profile(project_root=project_root, profile_path=profile_path)
    timeouts = _profile_timeouts(profile)
    stability = _profile_stability(profile)
    remote_command = _shell_launcher_command(
        profile,
        "[ -x /bin/bash ] && printf 'adf-target-shell-ok\\n'",
    )
    command_result = _run_ssh_command(
        profile=profile,
        remote_command=remote_command,
        timeout_seconds=int(timeouts.get("preflight_seconds", 15)),
        retry_limit=int(stability.get("preflight_retry_limit", 1)),
        retry_backoff_seconds=int(stability.get("retry_backoff_seconds", 2)),
        dry_run=dry_run,
    )
    return {
        "status": command_result["status"],
        "target_label": profile.get("target_label"),
        "auth_mode": profile.get("auth_mode"),
        "menu_interference_expected": _profile_shell(profile).get("menu_interference_expected", True),
        "shell_mode": _profile_shell(profile).get("mode", "non_login_bash"),
        "timeout_seconds": int(timeouts.get("preflight_seconds", 15)),
        "command_result": command_result,
    }


def target_heartbeat(
    *,
    project_root: Path,
    profile_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    profile = load_target_connection_profile(project_root=project_root, profile_path=profile_path)
    timeouts = _profile_timeouts(profile)
    stability = _profile_stability(profile)
    remote_command = _shell_launcher_command(
        profile,
        "printf 'adf-target-heartbeat\\n'",
    )
    command_result = _run_ssh_command(
        profile=profile,
        remote_command=remote_command,
        timeout_seconds=int(timeouts.get("heartbeat_seconds", 10)),
        retry_limit=int(stability.get("heartbeat_retry_limit", 2)),
        retry_backoff_seconds=int(stability.get("retry_backoff_seconds", 2)),
        dry_run=dry_run,
    )
    return {
        "status": command_result["status"],
        "target_label": profile.get("target_label"),
        "timeout_seconds": int(timeouts.get("heartbeat_seconds", 10)),
        "command_result": command_result,
    }


def target_shell_command(
    *,
    project_root: Path,
    command: str,
    profile_path: str | Path | None = None,
    timeout_seconds: int | None = None,
    retry_count: int = 0,
    dry_run: bool = False,
) -> dict[str, Any]:
    profile = load_target_connection_profile(project_root=project_root, profile_path=profile_path)
    timeouts = _profile_timeouts(profile)
    stability = _profile_stability(profile)
    remote_command = _shell_launcher_command(profile, command)
    selected_timeout = timeout_seconds if timeout_seconds is not None else int(timeouts.get("command_seconds", 120))
    command_result = _run_ssh_command(
        profile=profile,
        remote_command=remote_command,
        timeout_seconds=selected_timeout,
        retry_limit=retry_count,
        retry_backoff_seconds=int(stability.get("retry_backoff_seconds", 2)),
        dry_run=dry_run,
    )
    return {
        "status": command_result["status"],
        "target_label": profile.get("target_label"),
        "timeout_seconds": selected_timeout,
        "requested_command": command,
        "command_result": command_result,
    }
