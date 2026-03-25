#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    discover_pack,
    load_json,
    path_is_relative_to,
    read_now,
    resolve_factory_root,
    schema_path,
    validate_json_document,
    write_json,
)
from remote_autonomy_roundtrip_common import canonical_local_bundle_staging_dir
from remote_autonomy_staging_common import (
    canonical_remote_export_dir,
    canonical_remote_pack_dir,
    canonical_remote_parent_dir,
    canonical_remote_run_dir,
)
from run_remote_autonomy_test import run_remote_autonomy_test


RUN_REQUEST_SCHEMA_NAME = "remote-autonomy-run-request.schema.json"
TEST_REQUEST_SCHEMA_NAME = "remote-autonomy-test-request.schema.json"
RUN_REQUEST_SCHEMA_VERSION = "remote-autonomy-run-request/v1"
TEST_REQUEST_SCHEMA_VERSION = "remote-autonomy-test-request/v1"
LIVE_MEMORY_ROOT = Path(".pack-state") / "agent-memory"
LATEST_MEMORY_POINTER_NAME = "latest-memory.json"
RUN_ID_SUFFIX_PATTERN = re.compile(r"^(.+)-continuity-run-v(\d+)$")


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _canonical_alignment(pack_root: Path) -> dict[str, Any]:
    work_state = _load_object(pack_root / "status/work-state.json")
    readiness = _load_object(pack_root / "status/readiness.json")
    return {
        "autonomy_state": work_state.get("autonomy_state"),
        "active_task_id": work_state.get("active_task_id"),
        "next_recommended_task_id": work_state.get("next_recommended_task_id"),
        "readiness_state": readiness.get("readiness_state"),
        "ready_for_deployment": readiness.get("ready_for_deployment"),
    }


def _load_selected_memory(pack_root: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    pointer_path = pack_root / LIVE_MEMORY_ROOT / LATEST_MEMORY_POINTER_NAME
    if not pointer_path.exists():
        raise ValueError(
            f"{pointer_path}: ready-boundary continuity requires an active latest-memory pointer"
        )
    pointer_payload = _load_object(pointer_path)
    selected_memory_path = pointer_payload.get("selected_memory_path")
    if not isinstance(selected_memory_path, str) or not selected_memory_path:
        raise ValueError(f"{pointer_path}: selected_memory_path must be a non-empty string")
    memory_path = (pack_root / selected_memory_path).resolve()
    if not path_is_relative_to(memory_path, pack_root):
        raise ValueError(f"{pointer_path}: selected_memory_path must stay inside the pack root")
    if not memory_path.exists():
        raise FileNotFoundError(f"{pointer_path}: selected memory file is missing: {memory_path}")
    memory_payload = _load_object(memory_path)
    return pointer_path, pointer_payload, memory_payload


def _validate_ready_boundary(pack_root: Path, pack_id: str) -> None:
    alignment = _canonical_alignment(pack_root)
    pointer_path, pointer_payload, memory_payload = _load_selected_memory(pack_root)

    if alignment["autonomy_state"] != "ready_for_deploy":
        raise ValueError("ready-boundary continuity requires work-state autonomy_state=ready_for_deploy")
    if alignment["active_task_id"] is not None:
        raise ValueError("ready-boundary continuity requires work-state active_task_id=null")
    if alignment["next_recommended_task_id"] is not None:
        raise ValueError("ready-boundary continuity requires work-state next_recommended_task_id=null")
    if alignment["ready_for_deployment"] is not True:
        raise ValueError("ready-boundary continuity requires readiness.ready_for_deployment=true")
    if memory_payload.get("schema_version") != "autonomy-feedback-memory/v1":
        raise ValueError(f"{pointer_path}: selected memory must declare schema_version=autonomy-feedback-memory/v1")
    if memory_payload.get("pack_id") != pack_id:
        raise ValueError(f"{pointer_path}: selected memory pack_id does not match {pack_id}")
    if memory_payload.get("active_task_id") is not None:
        raise ValueError(f"{pointer_path}: selected memory active_task_id must be null at the deployment boundary")
    if memory_payload.get("next_recommended_task_id") is not None:
        raise ValueError(
            f"{pointer_path}: selected memory next_recommended_task_id must be null at the deployment boundary"
        )
    if memory_payload.get("final_readiness_state") != alignment["readiness_state"]:
        raise ValueError(f"{pointer_path}: selected memory final_readiness_state does not match canonical readiness")
    if memory_payload.get("ready_for_deployment") is not True:
        raise ValueError(f"{pointer_path}: selected memory ready_for_deployment must be true")
    selected_run_id = pointer_payload.get("selected_run_id")
    if not isinstance(selected_run_id, str) or not selected_run_id:
        raise ValueError(f"{pointer_path}: selected_run_id must be a non-empty string")


def _next_run_id(factory_root: Path, remote_target_label: str, pack_id: str) -> str:
    request_root = (
        factory_root
        / ".pack-state"
        / "remote-autonomy-requests"
        / remote_target_label
        / pack_id
    )
    max_version = 0
    if request_root.exists():
        for child in request_root.iterdir():
            if not child.is_dir():
                continue
            match = RUN_ID_SUFFIX_PATTERN.fullmatch(child.name)
            if match and match.group(1) == pack_id:
                max_version = max(max_version, int(match.group(2)))
    return f"{pack_id}-continuity-run-v{max_version + 1}"


def _request_root(factory_root: Path, remote_target_label: str, pack_id: str, run_id: str) -> Path:
    return (
        factory_root
        / ".pack-state"
        / "remote-autonomy-requests"
        / remote_target_label
        / pack_id
        / run_id
    )


def _build_remote_runner(run_id: str) -> str:
    return textwrap.dedent(
        f"""
        python3 - <<'PY'
        from __future__ import annotations

        import json
        import sys
        from datetime import datetime, timezone
        from pathlib import Path

        sys.path.insert(0, str((Path(".packfactory-runtime/tools")).resolve()))
        from record_autonomy_run import append_event

        RUN_ID = "{run_id}"
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


        memory_path, memory_doc, memory_source = latest_feedback_memory()
        work_state = load_json(PACK_ROOT / "status/work-state.json")
        readiness = load_json(PACK_ROOT / "status/readiness.json")
        canonical_next_task = work_state.get("next_recommended_task_id")
        memory_next_task = memory_doc.get("next_recommended_task_id")
        autonomy_state = work_state.get("autonomy_state")
        ready_for_deployment = bool(readiness.get("ready_for_deployment"))

        if autonomy_state != "ready_for_deploy":
            raise SystemExit(f"unexpected autonomy_state: {{autonomy_state}}")
        if canonical_next_task is not None:
            raise SystemExit(f"expected no canonical next task at deployment boundary, found {{canonical_next_task!r}}")
        if not ready_for_deployment:
            raise SystemExit("expected readiness.ready_for_deployment to be true")
        if memory_next_task is not None:
            raise SystemExit(f"expected feedback memory to carry no next task at deployment boundary, found {{memory_next_task!r}}")

        memory_ingress_path = PACK_ROOT / ".pack-state" / "autonomy-runs" / RUN_ID / "memory-ingress.json"
        write_json(
            memory_ingress_path,
            {{
                "memory_path": memory_path.as_posix(),
                "memory_run_id": memory_doc.get("run_id"),
                "memory_generated_at": memory_doc.get("generated_at"),
                "memory_source": memory_source,
                "canonical_next_task": canonical_next_task,
                "memory_next_task": memory_next_task,
                "autonomy_state": autonomy_state,
                "ready_for_deployment": ready_for_deployment,
                "recorded_at": now(),
            }},
        )

        append_event(
            pack_root=PACK_ROOT,
            run_id=RUN_ID,
            event_type="task_selected",
            outcome="confirmed_deployment_boundary_from_feedback_memory",
            decision_source="canonical_plus_memory",
            memory_state="used_and_consistent",
            commands_attempted=[],
            notes=[
                f"Loaded factory-default feedback memory from {{memory_path.as_posix()}} via {{memory_source}}.",
                "Canonical state and feedback memory both indicated the pack was already at the deployment boundary.",
                "Stopped cleanly without replaying starter tasks.",
            ],
            evidence_paths=[memory_ingress_path.relative_to(PACK_ROOT).as_posix()],
            stop_reason=None,
            active_task_id=None,
            next_recommended_task_id=None,
        )

        print(
            json.dumps(
                {{
                    "status": "completed",
                    "memory_path": memory_path.as_posix(),
                    "memory_run_id": memory_doc.get("run_id"),
                    "memory_source": memory_source,
                    "autonomy_state": autonomy_state,
                    "ready_for_deployment": ready_for_deployment,
                    "next_recommended_task_id": canonical_next_task,
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


def _build_run_request(
    *,
    factory_root: Path,
    pack_root: Path,
    pack_id: str,
    run_id: str,
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
        "remote_reason": "Factory-default feedback-memory continuity run from canonical ready-for-deploy state.",
        "staged_by": staged_by,
        "remote_runner": _build_remote_runner(run_id),
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
        "import_reason": "Factory-default feedback-memory continuity import from canonical ready-for-deploy state.",
        "test_reason": "PackFactory remote continuity run that confirms the active feedback-memory pointer can be reused at the deployment boundary.",
    }


def run_remote_memory_continuity_test(
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

    _validate_ready_boundary(location.pack_root, build_pack_id)
    resolved_run_id = run_id.strip() if run_id and run_id.strip() else _next_run_id(
        factory_root, remote_target_label, build_pack_id
    )
    request_root = _request_root(factory_root, remote_target_label, build_pack_id, resolved_run_id)
    request_root.mkdir(parents=True, exist_ok=True)
    run_request_path = request_root / "remote-run-request.json"
    test_request_path = request_root / "remote-test-request.json"

    run_request = _build_run_request(
        factory_root=factory_root,
        pack_root=location.pack_root,
        pack_id=build_pack_id,
        run_id=resolved_run_id,
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

    result = run_remote_autonomy_test(factory_root, test_request_path)
    return {
        "schema_version": "remote-memory-continuity-test-result/v1",
        "status": "completed",
        "build_pack_id": build_pack_id,
        "run_id": resolved_run_id,
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
    parser = argparse.ArgumentParser(
        description="Run the factory-default remote feedback-memory continuity workflow for a ready-for-deploy build-pack.",
    )
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory repository root.")
    parser.add_argument("--build-pack-id", required=True, help="Registered build-pack id to test.")
    parser.add_argument("--remote-target-label", required=True, help="Remote target label, for example `adf-dev`.")
    parser.add_argument("--remote-host", required=True, help="SSH host or alias to use for the remote target.")
    parser.add_argument("--remote-user", required=True, help="SSH user for the remote target.")
    parser.add_argument("--run-id", help="Optional explicit run id. Defaults to the next continuity-run-vN id.")
    parser.add_argument("--staged-by", default="codex", help="Actor recorded in the generated remote run request.")
    parser.add_argument("--imported-by", default="codex", help="Actor recorded in the generated import request.")
    parser.add_argument("--output", default="json", choices=("json",), help="Output format.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    factory_root = resolve_factory_root(args.factory_root)
    result = run_remote_memory_continuity_test(
        factory_root=factory_root,
        build_pack_id=args.build_pack_id,
        remote_target_label=args.remote_target_label,
        remote_host=args.remote_host,
        remote_user=args.remote_user,
        staged_by=args.staged_by,
        imported_by=args.imported_by,
        run_id=args.run_id,
    )
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
