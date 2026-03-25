#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import discover_pack, load_json, path_is_relative_to, read_now, resolve_factory_root, schema_path, validate_json_document, write_json
from import_external_runtime_evidence import import_external_runtime_evidence
from prepare_remote_autonomy_target import prepare_remote_autonomy_target
from pull_remote_runtime_evidence import pull_remote_runtime_evidence
from push_build_pack_to_remote import push_build_pack_to_remote
from remote_autonomy_roundtrip_common import (
    canonical_json_text,
    canonical_local_bundle_staging_dir,
    load_remote_autonomy_test_request,
    sha256_path,
    sha256_text,
    sha256_tree,
    write_validated_roundtrip_manifest,
)
from remote_autonomy_staging_common import (
    canonical_remote_export_dir,
    canonical_remote_pack_dir,
    canonical_remote_parent_dir,
    canonical_remote_run_dir,
)
from run_remote_autonomy_loop import run_remote_autonomy_loop


RUN_REQUEST_SCHEMA_NAME = "remote-autonomy-run-request.schema.json"
TEST_REQUEST_SCHEMA_NAME = "remote-autonomy-test-request.schema.json"
RUN_REQUEST_SCHEMA_VERSION = "remote-autonomy-run-request/v1"
TEST_REQUEST_SCHEMA_VERSION = "remote-autonomy-test-request/v1"
RUN_ID_SUFFIX_PATTERN = re.compile(r"^(.+)-active-task-continuity-run-v(\d+)$")


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _validate_active_task_boundary(pack_root: Path, pack_id: str) -> str:
    work_state = _load_object(pack_root / "status/work-state.json")
    readiness = _load_object(pack_root / "status/readiness.json")
    pointer_path = pack_root / ".pack-state" / "agent-memory" / "latest-memory.json"
    if not pointer_path.exists():
        raise ValueError("active-task continuity requires an active latest-memory pointer")
    pointer_payload = _load_object(pointer_path)
    selected_memory_path = pointer_payload.get("selected_memory_path")
    if not isinstance(selected_memory_path, str) or not selected_memory_path:
        raise ValueError("latest-memory.json is missing selected_memory_path")
    memory_path = (pack_root / selected_memory_path).resolve()
    if not path_is_relative_to(memory_path, pack_root):
        raise ValueError("latest-memory.json selected_memory_path must stay inside the pack root")
    memory_payload = _load_object(memory_path)

    active_task_id = work_state.get("active_task_id")
    next_task_id = work_state.get("next_recommended_task_id")
    if not isinstance(active_task_id, str) or not active_task_id:
        raise ValueError("active-task continuity requires a non-empty active_task_id")
    if next_task_id != active_task_id:
        raise ValueError("active-task continuity requires next_recommended_task_id to equal active_task_id")
    if readiness.get("ready_for_deployment") is True:
        raise ValueError("active-task continuity requires a pack that is not already ready_for_deployment")
    if memory_payload.get("pack_id") != pack_id:
        raise ValueError("latest-memory.json selected memory pack_id does not match the selected build pack")
    if memory_payload.get("active_task_id") != active_task_id or memory_payload.get("next_recommended_task_id") != active_task_id:
        raise ValueError("latest-memory.json selected memory does not match the canonical active task boundary")
    return active_task_id


def _next_run_id(factory_root: Path, remote_target_label: str, pack_id: str) -> str:
    request_root = factory_root / ".pack-state" / "remote-autonomy-requests" / remote_target_label / pack_id
    max_version = 0
    if request_root.exists():
        for child in request_root.iterdir():
            if not child.is_dir():
                continue
            match = RUN_ID_SUFFIX_PATTERN.fullmatch(child.name)
            if match and match.group(1) == pack_id:
                max_version = max(max_version, int(match.group(2)))
    return f"{pack_id}-active-task-continuity-run-v{max_version + 1}"


def _request_root(factory_root: Path, remote_target_label: str, pack_id: str, run_id: str) -> Path:
    return factory_root / ".pack-state" / "remote-autonomy-requests" / remote_target_label / pack_id / run_id


def _build_remote_runner(run_id: str, expected_active_task_id: str) -> str:
    return textwrap.dedent(
        f"""
        python3 - <<'PY'
        from __future__ import annotations

        import json
        import subprocess
        import sys
        from datetime import datetime, timezone
        from pathlib import Path

        sys.path.insert(0, str((Path(".packfactory-runtime/tools")).resolve()))
        from record_autonomy_run import append_event

        RUN_ID = "{run_id}"
        EXPECTED_ACTIVE_TASK_ID = "{expected_active_task_id}"
        PACK_ROOT = Path(".").resolve()
        MEMORY_DIR = PACK_ROOT / ".pack-state" / "agent-memory"
        LATEST_MEMORY_PATH = MEMORY_DIR / "latest-memory.json"


        def now() -> str:
            return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


        def load_json(path: Path) -> dict[str, object]:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise SystemExit(f"{{path}} did not contain a JSON object")
            return payload


        def write_json(path: Path, payload: dict[str, object]) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")


        def latest_feedback_memory() -> tuple[Path, dict[str, object], str]:
            if LATEST_MEMORY_PATH.exists():
                pointer_doc = load_json(LATEST_MEMORY_PATH)
                selected_memory_path = pointer_doc.get("selected_memory_path")
                if not isinstance(selected_memory_path, str) or not selected_memory_path:
                    raise SystemExit("latest-memory.json is missing selected_memory_path")
                memory_path = (PACK_ROOT / selected_memory_path).resolve()
                if not memory_path.exists():
                    raise SystemExit(f"latest-memory.json pointed at a missing file: {{memory_path}}")
                return memory_path, load_json(memory_path), "latest_pointer"

            candidates = sorted(MEMORY_DIR.glob("autonomy-feedback-*.json"))
            if not candidates:
                raise SystemExit("expected at least one factory-default feedback-memory artifact under .pack-state/agent-memory")
            path = candidates[-1]
            return path, load_json(path), "directory_fallback"


        def run_command(command: str) -> dict[str, object]:
            completed = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                cwd=PACK_ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                raise SystemExit(completed.stderr.strip() or completed.stdout.strip() or f"command failed: {{command}}")
            stdout = completed.stdout.strip()
            if not stdout:
                return {{"status": "completed", "generated_at": now(), "evidence_paths": []}}
            payload = json.loads(stdout)
            if not isinstance(payload, dict):
                raise SystemExit(f"command output must be a JSON object: {{command}}")
            return payload


        def merge_validation_results(existing: list[dict[str, object]], fresh: dict[str, object]) -> list[dict[str, object]]:
            merged = [result for result in existing if result.get("validation_id") != fresh.get("validation_id")]
            merged.append(fresh)
            return merged


        memory_path, memory_doc, memory_source = latest_feedback_memory()
        work_state_path = PACK_ROOT / "status" / "work-state.json"
        backlog_path = PACK_ROOT / "tasks" / "active-backlog.json"
        readiness_path = PACK_ROOT / "status" / "readiness.json"
        work_state = load_json(work_state_path)
        backlog = load_json(backlog_path)
        readiness = load_json(readiness_path)
        active_task_id = work_state.get("active_task_id")
        next_task_id = work_state.get("next_recommended_task_id")
        if active_task_id != EXPECTED_ACTIVE_TASK_ID or next_task_id != EXPECTED_ACTIVE_TASK_ID:
            raise SystemExit(f"unexpected canonical active-task boundary: active={{active_task_id!r}} next={{next_task_id!r}} expected={{EXPECTED_ACTIVE_TASK_ID!r}}")
        if bool(readiness.get("ready_for_deployment")):
            raise SystemExit("expected readiness.ready_for_deployment to be false")
        if memory_doc.get("active_task_id") != EXPECTED_ACTIVE_TASK_ID or memory_doc.get("next_recommended_task_id") != EXPECTED_ACTIVE_TASK_ID:
            raise SystemExit("feedback memory did not match the canonical active task boundary")

        selected_task = None
        for task in backlog.get("tasks", []):
            if isinstance(task, dict) and task.get("task_id") == EXPECTED_ACTIVE_TASK_ID:
                selected_task = task
                break
        if not isinstance(selected_task, dict):
            raise SystemExit(f"active task {{EXPECTED_ACTIVE_TASK_ID!r}} was not found in tasks/active-backlog.json")
        commands = selected_task.get("validation_commands", [])
        if not isinstance(commands, list) or not commands or not all(isinstance(command, str) and command.strip() for command in commands):
            raise SystemExit(f"active task {{EXPECTED_ACTIVE_TASK_ID!r}} must declare non-empty validation_commands")

        memory_ingress_path = PACK_ROOT / ".pack-state" / "autonomy-runs" / RUN_ID / "memory-ingress.json"
        write_json(
            memory_ingress_path,
            {{
                "memory_path": memory_path.as_posix(),
                "memory_run_id": memory_doc.get("run_id"),
                "memory_generated_at": memory_doc.get("generated_at"),
                "memory_source": memory_source,
                "active_task_id": active_task_id,
                "next_recommended_task_id": next_task_id,
                "recorded_at": now(),
            }},
        )

        append_event(
            pack_root=PACK_ROOT,
            run_id=RUN_ID,
            event_type="task_selected",
            outcome="selected_active_task_from_feedback_memory",
            decision_source="canonical_plus_memory",
            memory_state="used_and_consistent",
            commands_attempted=[],
            notes=[
                f"Loaded factory-default feedback memory from {{memory_path.as_posix()}} via {{memory_source}}.",
                f"Memory agreed with canonical state on active task {{EXPECTED_ACTIVE_TASK_ID}}.",
            ],
            evidence_paths=[memory_ingress_path.relative_to(PACK_ROOT).as_posix()],
            stop_reason=None,
            active_task_id=EXPECTED_ACTIVE_TASK_ID,
            next_recommended_task_id=EXPECTED_ACTIVE_TASK_ID,
        )

        recorded_results: list[dict[str, object]] = []
        for command in commands:
            payload = run_command(command)
            evidence_paths = list(payload.get("evidence_paths", [])) if isinstance(payload.get("evidence_paths", []), list) else []
            recorded_results.append(
                {{
                    "validation_id": EXPECTED_ACTIVE_TASK_ID,
                    "status": "pass",
                    "summary": f"Completed `{{EXPECTED_ACTIVE_TASK_ID}}` through the declared validation_commands during remote active-task continuity.",
                    "evidence_paths": evidence_paths,
                    "recorded_at": payload.get("generated_at"),
                }}
            )
            append_event(
                pack_root=PACK_ROOT,
                run_id=RUN_ID,
                event_type="command_completed",
                outcome=f"{{EXPECTED_ACTIVE_TASK_ID}}_command_completed",
                decision_source="canonical_plus_memory",
                memory_state="used_and_consistent",
                commands_attempted=[command],
                notes=[f"Completed the declared command for active task `{{EXPECTED_ACTIVE_TASK_ID}}`."],
                evidence_paths=evidence_paths,
                stop_reason=None,
                active_task_id=EXPECTED_ACTIVE_TASK_ID,
                next_recommended_task_id=EXPECTED_ACTIVE_TASK_ID,
            )

        refreshed_readiness = load_json(readiness_path)
        refreshed_backlog = load_json(backlog_path)
        for task in refreshed_backlog.get("tasks", []):
            if isinstance(task, dict) and task.get("task_id") == EXPECTED_ACTIVE_TASK_ID:
                task["status"] = "completed"

        remaining_task_ids = [
            str(task.get("task_id"))
            for task in refreshed_backlog.get("tasks", [])
            if isinstance(task, dict)
            and isinstance(task.get("task_id"), str)
            and task.get("status") != "completed"
        ]
        next_active_task_id = None if bool(refreshed_readiness.get("ready_for_deployment")) or not remaining_task_ids else remaining_task_ids[0]
        for task in refreshed_backlog.get("tasks", []):
            if not isinstance(task, dict):
                continue
            task_id = task.get("task_id")
            if next_active_task_id is not None and task_id == next_active_task_id:
                task["status"] = "in_progress"
            elif task_id != EXPECTED_ACTIVE_TASK_ID and task.get("status") != "completed":
                task["status"] = "pending"
        write_json(backlog_path, refreshed_backlog)

        refreshed_work_state = load_json(work_state_path)
        last_validation_results = list(refreshed_work_state.get("last_validation_results", []))
        for result in recorded_results:
            if isinstance(result, dict):
                last_validation_results = merge_validation_results(last_validation_results, result)
        completed_task_ids = list(refreshed_work_state.get("completed_task_ids", []))
        if EXPECTED_ACTIVE_TASK_ID not in completed_task_ids:
            completed_task_ids.append(EXPECTED_ACTIVE_TASK_ID)
        autonomy_state = "ready_for_deploy" if bool(refreshed_readiness.get("ready_for_deployment")) else "actively_building"
        refreshed_work_state.update(
            {{
                "autonomy_state": autonomy_state,
                "active_task_id": next_active_task_id,
                "next_recommended_task_id": next_active_task_id,
                "pending_task_ids": [] if next_active_task_id is None else [task_id for task_id in remaining_task_ids if task_id != next_active_task_id],
                "blocked_task_ids": [],
                "completed_task_ids": completed_task_ids,
                "last_outcome": "task_completed",
                "last_outcome_at": now(),
                "last_validation_results": last_validation_results,
                "last_agent_action": f"Completed `{{EXPECTED_ACTIVE_TASK_ID}}` through remote active-task continuity and advanced canonical state.",
                "escalation_state": "none",
            }}
        )
        write_json(work_state_path, refreshed_work_state)

        append_event(
            pack_root=PACK_ROOT,
            run_id=RUN_ID,
            event_type="state_updated",
            outcome="active_task_continuity_completed",
            decision_source="canonical_plus_memory",
            memory_state="used_and_consistent",
            commands_attempted=[],
            notes=[
                f"Completed active task `{{EXPECTED_ACTIVE_TASK_ID}}` and advanced canonical state to next task {{next_active_task_id!r}}.",
                f"ready_for_deployment={{bool(refreshed_readiness.get('ready_for_deployment'))}}.",
            ],
            evidence_paths=[],
            stop_reason=None,
            active_task_id=next_active_task_id,
            next_recommended_task_id=next_active_task_id,
        )

        print(
            json.dumps(
                {{
                    "status": "completed",
                    "completed_task_id": EXPECTED_ACTIVE_TASK_ID,
                    "next_active_task_id": next_active_task_id,
                    "ready_for_deployment": bool(refreshed_readiness.get("ready_for_deployment")),
                }},
                sort_keys=True,
            )
        )
        PY
        """
    ).strip()


def _write_validated(factory_root: Path, path: Path, payload: dict[str, Any], schema_name: str) -> None:
    write_json(path, payload)
    errors = validate_json_document(path, schema_path(factory_root, schema_name))
    if errors:
        raise ValueError("; ".join(errors))


def _expand_remote_home(path: str, remote_user: str) -> str:
    if path == "~":
        return f"/home/{remote_user}"
    if path.startswith("~/"):
        return f"/home/{remote_user}/{path[2:]}"
    return path


def _seed_required_validation_artifacts(*, remote_request) -> list[str]:
    source_pack_root = remote_request.source_build_pack_root
    readiness = _load_object(source_pack_root / "status/readiness.json")
    required_paths: list[Path] = []
    for gate in cast(list[dict[str, Any]], readiness.get("required_gates", [])):
        if not isinstance(gate, dict) or gate.get("gate_id") != "validate_build_pack_contract":
            continue
        for evidence_path in gate.get("evidence_paths", []):
            if not isinstance(evidence_path, str) or not evidence_path:
                continue
            local_path = (source_pack_root / evidence_path).resolve()
            if local_path.exists() and path_is_relative_to(local_path, source_pack_root):
                required_paths.append(local_path)
        break

    seeded: list[str] = []
    for local_path in required_paths:
        relative = local_path.relative_to(source_pack_root).as_posix()
        remote_path = _expand_remote_home(f"{remote_request.remote_pack_dir}/{relative}", remote_request.remote_user)
        remote_dir = str(Path(remote_path).parent).replace("\\", "/")
        mkdir_command = f"mkdir -p {shlex.quote(remote_dir)}"
        completed = subprocess.run(
            ["ssh", remote_request.remote_address, f"bash -lc {shlex.quote(mkdir_command)}"],
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"failed to mkdir {remote_dir}")
        copied = subprocess.run(
            ["scp", str(local_path), f"{remote_request.remote_address}:{remote_path}"],
            text=True,
            capture_output=True,
            check=False,
        )
        if copied.returncode != 0:
            raise RuntimeError(copied.stderr.strip() or copied.stdout.strip() or f"failed to copy {relative}")
        seeded.append(relative)
    return seeded


def _run_roundtrip_with_seeded_validation_artifacts(*, factory_root: Path, test_request_path: Path) -> dict[str, Any]:
    wrapper_request = load_remote_autonomy_test_request(factory_root=factory_root, request_path=test_request_path)
    remote_request = wrapper_request.remote_run_request
    if wrapper_request.import_bundle and not wrapper_request.pull_bundle:
        raise ValueError("active-task continuity requires pull_bundle=true when import_bundle=true")
    if wrapper_request.local_bundle_staging_dir.exists() and any(wrapper_request.local_bundle_staging_dir.iterdir()):
        raise ValueError(
            f"local_bundle_staging_dir must be empty before the roundtrip run: {wrapper_request.local_bundle_staging_dir}"
        )

    wrapper_request_sha256 = sha256_text(canonical_json_text(wrapper_request.raw_payload))
    remote_run_request_sha256 = sha256_text(canonical_json_text(remote_request.raw_payload))

    preparation_result = prepare_remote_autonomy_target(factory_root, wrapper_request.remote_run_request_path)
    staging_result = push_build_pack_to_remote(factory_root, wrapper_request.remote_run_request_path, transport="auto")
    seeded_prerequisite_paths = _seed_required_validation_artifacts(remote_request=remote_request)
    execution_result = run_remote_autonomy_loop(factory_root, wrapper_request.remote_run_request_path)

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
    if pull_result["target_manifest_sha256"] != execution_result["target_manifest_sha256"]:
        raise ValueError("pull result target_manifest_sha256 does not match the execution result")

    pulled_bundle_path = Path(str(pull_result["local_bundle_root"]))
    pulled_bundle_sha256 = str(pull_result["pulled_bundle_sha256"])
    if pulled_bundle_sha256 != sha256_tree(pulled_bundle_path):
        raise ValueError("pulled bundle sha256 does not match the staged local bundle directory")

    import_request_path = wrapper_request.local_bundle_staging_dir / "generated-import-request.json"
    import_request_payload = {
        "schema_version": "external-runtime-evidence-import-request/v1",
        "build_pack_id": remote_request.source_build_pack_id,
        "bundle_manifest_path": str(pulled_bundle_path / "bundle.json"),
        "import_reason": wrapper_request.import_reason,
        "imported_by": wrapper_request.imported_by,
    }
    write_json(import_request_path, import_request_payload)
    import_result = import_external_runtime_evidence(
        factory_root,
        import_request_payload,
        request_file_dir=import_request_path.parent.resolve(),
    )

    roundtrip_manifest_path = wrapper_request.local_bundle_staging_dir / "roundtrip-manifest.json"
    roundtrip_manifest = {
        "schema_version": "remote-roundtrip-manifest/v1",
        "wrapper_request_sha256": wrapper_request_sha256,
        "remote_run_request_sha256": remote_run_request_sha256,
        "source_build_pack_id": remote_request.source_build_pack_id,
        "run_id": remote_request.run_id,
        "remote_target_label": remote_request.remote_target_label,
        "target_manifest_sha256": execution_result["target_manifest_sha256"],
        "execution_manifest_sha256": pull_result["execution_manifest_sha256"],
        "portable_helper_manifest_sha256": pull_result["portable_helper_manifest_sha256"],
        "pulled_bundle_path": str(pulled_bundle_path),
        "pulled_bundle_sha256": pulled_bundle_sha256,
        "pulled_at": pull_result["pulled_at"],
        "generated_import_request_path": str(import_request_path),
        "generated_import_request_sha256": sha256_path(import_request_path),
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
        "seeded_prerequisite_paths": seeded_prerequisite_paths,
        "execution_result": execution_result,
        "pull_result": pull_result,
        "import_result": import_result,
        "roundtrip_manifest_path": str(roundtrip_manifest_path),
        "import_report_path": str(import_result["import_report_path"]),
    }


def _build_run_request(
    *,
    factory_root: Path,
    pack_root: Path,
    pack_id: str,
    run_id: str,
    active_task_id: str,
    remote_target_label: str,
    remote_host: str,
    remote_user: str,
    staged_by: str,
) -> dict[str, Any]:
    remote_parent_dir = canonical_remote_parent_dir(remote_target_label)
    remote_pack_dir = canonical_remote_pack_dir(remote_parent_dir, pack_id)
    return {
        "schema_version": RUN_REQUEST_SCHEMA_VERSION,
        "source_factory_root": str(factory_root),
        "source_build_pack_id": pack_id,
        "source_build_pack_root": str(pack_root),
        "run_id": run_id,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "remote_target_label": remote_target_label,
        "remote_parent_dir": remote_parent_dir,
        "remote_pack_dir": remote_pack_dir,
        "remote_run_dir": canonical_remote_run_dir(remote_pack_dir, run_id),
        "remote_export_dir": canonical_remote_export_dir(remote_pack_dir),
        "remote_reason": "Factory-default active-task continuity run from canonical mid-backlog state.",
        "staged_by": staged_by,
        "remote_runner": _build_remote_runner(run_id, active_task_id),
    }


def _build_test_request(
    *,
    factory_root: Path,
    remote_target_label: str,
    pack_id: str,
    run_id: str,
    remote_run_request_path: Path,
    imported_by: str,
) -> dict[str, Any]:
    return {
        "schema_version": TEST_REQUEST_SCHEMA_VERSION,
        "remote_run_request_path": str(remote_run_request_path),
        "local_bundle_staging_dir": str(
            canonical_local_bundle_staging_dir(
                factory_root=factory_root,
                remote_target_label=remote_target_label,
                build_pack_id=pack_id,
                run_id=run_id,
            )
        ),
        "pull_bundle": True,
        "import_bundle": True,
        "imported_by": imported_by,
        "import_reason": "Factory-default active-task continuity import from canonical mid-backlog state.",
        "test_reason": "PackFactory remote continuity run that resumes the canonical active task from feedback memory.",
    }


def run_remote_active_task_continuity_test(
    *,
    factory_root: Path,
    build_pack_id: str,
    remote_target_label: str,
    remote_host: str,
    remote_user: str,
    staged_by: str,
    imported_by: str,
    run_id: str | None,
) -> dict[str, Any]:
    location = discover_pack(factory_root, build_pack_id)
    if location.pack_kind != "build_pack":
        raise ValueError(f"{build_pack_id} is not a build_pack")
    active_task_id = _validate_active_task_boundary(location.pack_root, build_pack_id)

    resolved_run_id = run_id.strip() if run_id and run_id.strip() else _next_run_id(factory_root, remote_target_label, build_pack_id)
    request_root = _request_root(factory_root, remote_target_label, build_pack_id, resolved_run_id)
    request_root.mkdir(parents=True, exist_ok=True)
    run_request_path = request_root / "remote-run-request.json"
    test_request_path = request_root / "remote-test-request.json"

    run_request = _build_run_request(
        factory_root=factory_root,
        pack_root=location.pack_root,
        pack_id=build_pack_id,
        run_id=resolved_run_id,
        active_task_id=active_task_id,
        remote_target_label=remote_target_label,
        remote_host=remote_host,
        remote_user=remote_user,
        staged_by=staged_by,
    )
    test_request = _build_test_request(
        factory_root=factory_root,
        remote_target_label=remote_target_label,
        pack_id=build_pack_id,
        run_id=resolved_run_id,
        remote_run_request_path=run_request_path,
        imported_by=imported_by,
    )
    _write_validated(factory_root, run_request_path, run_request, RUN_REQUEST_SCHEMA_NAME)
    _write_validated(factory_root, test_request_path, test_request, TEST_REQUEST_SCHEMA_NAME)

    result = _run_roundtrip_with_seeded_validation_artifacts(
        factory_root=factory_root,
        test_request_path=test_request_path,
    )
    return {
        "schema_version": "remote-active-task-continuity-test-result/v1",
        "status": "completed",
        "build_pack_id": build_pack_id,
        "run_id": resolved_run_id,
        "active_task_id": active_task_id,
        "remote_target_label": remote_target_label,
        "remote_host": remote_host,
        "remote_user": remote_user,
        "generated_at": read_now().isoformat().replace("+00:00", "Z"),
        "request_root": str(request_root),
        "remote_run_request_path": str(run_request_path),
        "remote_test_request_path": str(test_request_path),
        "roundtrip_result": result,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run remote active-task continuity from a mid-backlog feedback-memory boundary.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--build-pack-id", required=True)
    parser.add_argument("--remote-target-label", required=True)
    parser.add_argument("--remote-host", required=True)
    parser.add_argument("--remote-user", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--staged-by", default="codex")
    parser.add_argument("--imported-by", default="codex")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    result = run_remote_active_task_continuity_test(
        factory_root=factory_root,
        build_pack_id=args.build_pack_id,
        remote_target_label=args.remote_target_label,
        remote_host=args.remote_host,
        remote_user=args.remote_user,
        staged_by=args.staged_by,
        imported_by=args.imported_by,
        run_id=args.run_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
