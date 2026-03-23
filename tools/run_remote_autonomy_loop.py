#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import dump_json, load_json, resolve_factory_root, schema_path, validate_json_document
from remote_autonomy_staging_common import (
    LOCAL_STAGING_ROOT,
    PAYLOAD_MANIFEST_SCHEMA_NAME,
    REMOTE_METADATA_DIR,
    REMOTE_TARGET_MANIFEST_FILENAME,
    build_control_plane_mutations,
    load_remote_autonomy_request,
    sha256_path,
)


EXECUTION_MANIFEST_SCHEMA_NAME = "remote-execution-manifest.schema.json"
EXECUTION_MANIFEST_SCHEMA_VERSION = "remote-execution-manifest/v1"
EXECUTION_MANIFEST_FILENAME = "execution-manifest.json"
PROMPT_ARTIFACT_FILENAME = "invocation-prompt.txt"
BOOTSTRAP_MODE = "presence-check-only"


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


def _local_target_manifest_path(factory_root: Path, run_id: str) -> Path:
    return factory_root / LOCAL_STAGING_ROOT / run_id / REMOTE_TARGET_MANIFEST_FILENAME


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
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        ["ssh", request.remote_address, *remote_command],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
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


def _build_remote_prompt(*, request) -> str:
    return textwrap.dedent(
        f"""
        You are running inside a staged Project Pack Factory build-pack.

        Treat the staged build-pack root as the only writable work packet.
        Read `AGENTS.md`, `project-context.md`, and `pack.json` first.
        Then follow `pack.json.post_bootstrap_read_order` and use `pack.json.directory_contract`
        as the canonical source for the objective, backlog, work-state, readiness, eval, and
        runtime-evidence paths.

        Scope:
        - starter backlog only
        - canonical bounded validation and benchmark surfaces only
        - advisory memory only when consistent with canonical pack-local state

        Do not:
        - modify `pack.json`
        - modify `.packfactory-remote/request.json`
        - modify `.packfactory-remote/target-manifest.json`
        - create deployment pointers or mutate registry truth
        - invent new tests, new backlog items, or promotion/deployment work
        - edit unrelated source, docs, prompts, or tests outside the declared starter backlog boundary

        Allowed writable surfaces are limited to:
        - the declared task backlog file
        - the declared work-state file
        - the declared readiness and eval surfaces when changed through bounded pack-local workflows
        - `.pack-state/`
        - the declared runtime-evidence export directory

        Stop when:
        - the declared starter backlog is complete and promotion or deployment is the next valid action
        - a declared escalation condition is reached

        This run id is `{request.run_id}`.
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
        import subprocess
        import sys
        from datetime import datetime, timezone
        from pathlib import Path
        from typing import Any


        EXECUTION_MANIFEST_FILENAME = "execution-manifest.json"
        PROMPT_ARTIFACT_FILENAME = "invocation-prompt.txt"
        EXECUTION_MANIFEST_SCHEMA_VERSION = "remote-execution-manifest/v1"
        BOOTSTRAP_MODE = "presence-check-only"
        REMOTE_METADATA_DIR = ".packfactory-remote"
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


        def _run_shell(command: str, *, cwd: Path, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
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
            }
            if relative_path in {value for value in allowed_exact if isinstance(value, str)}:
                return True
            allowed_prefixes = [
                ".pack-state/",
                "eval/history/",
            ]
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
            for key in ("eval_history_dir", "runtime_evidence_export_dir"):
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
            starter_ids = ("run_build_pack_validation", "run_inherited_benchmarks")
            present_starter_ids = [task_id for task_id in starter_ids if task_id in task_statuses]
            starter_complete = bool(present_starter_ids) and all(
                task_statuses.get(task_id) == "completed" for task_id in present_starter_ids
            )
            ready_boundary = (
                work_state.get("autonomy_state") == "ready_for_deploy"
                and work_state.get("next_recommended_task_id") is None
                and readiness.get("ready_for_deployment") is True
            )
            escalation_state = work_state.get("escalation_state")
            if starter_complete and ready_boundary:
                return "promotion_or_deployment_boundary", "starter_backlog_completed"
            if escalation_state not in (None, "none") or work_state.get("autonomy_state") in {"blocked", "awaiting_operator"}:
                return "escalated", "declared_escalation_boundary"
            if starter_complete:
                return "starter_backlog_completed", "starter_tasks_completed_without_ready_boundary"
            return "stopped", "starter_backlog_incomplete"


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
            prompt_artifact_path = pack_root / REMOTE_METADATA_DIR / PROMPT_ARTIFACT_FILENAME
            _dump_json(
                pack_root / REMOTE_METADATA_DIR / "invocation-context.json",
                {
                    "prompt_sha256": prompt_sha256,
                    "remote_runner": remote_runner,
                    "run_id": run_id,
                },
            )
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

            runner_completed = _run_shell(remote_runner, cwd=pack_root, input_text=prompt_text)
            after_snapshot = _snapshot_tree(pack_root)
            changed_paths = _changed_paths(before_snapshot, after_snapshot)
            boundary_violations = [
                path for path in changed_paths if not _allowed_mutation(path, contract)
            ]

            terminal_outcome, terminal_reason = _terminal_state(pack_root, contract)
            if boundary_violations:
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
                export_completed = _run_shell(export_command, cwd=pack_root)
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
                "status": "completed" if terminal_outcome in {"promotion_or_deployment_boundary", "starter_backlog_completed"} else "stopped",
                "source_build_pack_id": source_build_pack_id,
                "run_id": run_id,
                "remote_runner": remote_runner,
                "bootstrap_mode": BOOTSTRAP_MODE,
                "terminal_outcome": terminal_outcome,
                "terminal_reason": terminal_reason,
                "runner_returncode": runner_completed.returncode,
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
    local_target_manifest_path = _local_target_manifest_path(factory_root, request.run_id)
    if not local_target_manifest_path.exists():
        raise FileNotFoundError(f"missing staged target manifest: {local_target_manifest_path}")
    local_target_manifest = _validate_local_target_manifest(factory_root, local_target_manifest_path)
    request_text = _canonical_request_text(request.raw_payload)
    request_sha256 = _sha256_text(request_text)
    expected_request_sha256 = local_target_manifest.get("request_sha256")
    if request_sha256 != expected_request_sha256:
        raise ValueError("remote staged request checksum must match the local staging manifest")
    target_manifest_sha256 = sha256_path(local_target_manifest_path)

    bootstrap = _bootstrap_remote_target(request)
    prompt_text = _build_remote_prompt(request=request)
    remote_completed = _ssh_checked(
        request,
        ["python3", "-"],
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

    return {
        "schema_version": "remote-autonomy-loop-result/v1",
        "status": remote_payload.get("status"),
        "source_build_pack_id": request.source_build_pack_id,
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
