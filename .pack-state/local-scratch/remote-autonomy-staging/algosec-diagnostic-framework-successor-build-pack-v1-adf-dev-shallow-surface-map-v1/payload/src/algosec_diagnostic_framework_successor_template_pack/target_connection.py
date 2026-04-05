from __future__ import annotations

import json
import shlex
import shutil
import subprocess
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
        selected_path.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError("target connection profile must stay under the selected project root") from exc
    payload = _load_json(selected_path)
    if payload.get("schema_version") != "adf-target-connection-profile/v1":
        raise ValueError("target connection profile schema_version must be `adf-target-connection-profile/v1`")
    payload["_loaded_from"] = str(selected_path.relative_to(project_root.resolve()))
    return payload


def target_shell_capture(
    *,
    profile: dict[str, Any],
    command_id: str,
    command: str,
    timeout_seconds: int,
    preview_line_limit: int = 40,
) -> dict[str, Any]:
    ssh_argv = _ssh_command_argv(profile, command)
    if shutil.which("ssh") is None:
        return {
            "command_id": command_id,
            "argv": ssh_argv,
            "status": "not_available",
            "exit_code": None,
            "stdout": "",
            "stdout_preview": [],
            "stdout_line_count": 0,
            "stderr_preview": [],
        }

    completed = subprocess.run(
        ssh_argv,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout_seconds,
    )
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return {
        "command_id": command_id,
        "argv": ssh_argv,
        "status": "completed" if completed.returncode == 0 else "nonzero_exit",
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stdout_preview": stdout.splitlines()[:preview_line_limit],
        "stdout_line_count": len(stdout.splitlines()),
        "stderr_preview": stderr.splitlines()[:preview_line_limit],
    }


def _ssh_command_argv(profile: dict[str, Any], command: str) -> list[str]:
    destination = str(profile.get("ssh_destination") or "").strip()
    ssh_user = str(profile.get("ssh_user") or "").strip()
    ssh_host = str(profile.get("ssh_host") or "").strip()
    if not destination:
        if not ssh_user or not ssh_host:
            raise ValueError("profile must define ssh_destination or both ssh_user and ssh_host")
        destination = f"{ssh_user}@{ssh_host}"

    stability = profile.get("stability", {})
    shell = profile.get("shell", {})
    timeouts = profile.get("timeouts", {})
    if not isinstance(stability, dict):
        raise ValueError("profile.stability must be an object")
    if not isinstance(shell, dict):
        raise ValueError("profile.shell must be an object")
    if not isinstance(timeouts, dict):
        raise ValueError("profile.timeouts must be an object")

    server_alive_interval = int(stability.get("server_alive_interval_seconds", 15))
    server_alive_count_max = int(stability.get("server_alive_count_max", 2))
    connect_timeout = int(timeouts.get("connect_seconds", 10))
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

    launcher_argv = list(launcher_prefix)
    for key, value in launcher_env.items():
        launcher_argv.append(f"{key}={value}")
    launcher_argv.extend([shell_path, *shell_args, "-c", command])
    remote_command = " ".join(shlex.quote(part) for part in launcher_argv)

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
        remote_command,
    ]
