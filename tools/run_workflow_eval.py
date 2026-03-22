#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import load_json, resolve_factory_root, write_json


IGNORE_NAMES = shutil.ignore_patterns(
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "*.egg-info",
)


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _copy_factory(factory_root: Path, label: str) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix=f"ppf-{label}-"))
    destination = temp_root / "factory"
    shutil.copytree(factory_root, destination, ignore=IGNORE_NAMES)
    return destination


def _run_factory_validation(factory_root: Path) -> tuple[dict[str, Any], int, str]:
    process = subprocess.run(
        [
            sys.executable,
            str(factory_root / "tools/validate_factory.py"),
            "--factory-root",
            str(factory_root),
            "--output",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    payload = json.loads(process.stdout) if process.stdout.strip() else {}
    return payload, process.returncode, process.stderr.strip()


def _run_cli(tool_path: Path, *, factory_root: Path, request_path: Path) -> tuple[dict[str, Any], int, float, str]:
    start = time.perf_counter()
    process = subprocess.run(
        [
            sys.executable,
            str(tool_path),
            "--factory-root",
            str(factory_root),
            "--request-file",
            str(request_path),
            "--output",
            "json",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    payload = json.loads(process.stdout) if process.stdout.strip() else {}
    return payload, process.returncode, duration_ms, process.stderr.strip()


def _activate_template(factory_root: Path, pack_id: str) -> None:
    registry_path = factory_root / "registry/templates.json"
    registry = _load_object(registry_path)
    entry = next(item for item in registry["entries"] if item["pack_id"] == pack_id)
    entry["active"] = True
    entry["lifecycle_stage"] = "maintained"
    entry["retirement_state"] = "active"
    entry["retired_at"] = None
    write_json(registry_path, registry)

    pack_root = factory_root / "templates" / pack_id
    lifecycle_path = pack_root / "status/lifecycle.json"
    lifecycle = _load_object(lifecycle_path)
    lifecycle["lifecycle_stage"] = "maintained"
    lifecycle["promotion_target"] = "none"
    lifecycle["state_reason"] = "Template reactivated for workflow evaluation."
    write_json(lifecycle_path, lifecycle)

    retirement_path = pack_root / "status/retirement.json"
    retirement = _load_object(retirement_path)
    retirement["retirement_state"] = "active"
    retirement["retired_at"] = None
    retirement["retired_by"] = None
    retirement["retirement_reason"] = None
    retirement["superseded_by_pack_id"] = None
    retirement["retirement_report_path"] = None
    retirement["removed_deployment_pointer_paths"] = []
    write_json(retirement_path, retirement)


def _materialization_request(pack_id: str) -> dict[str, Any]:
    return {
        "schema_version": "build-pack-materialization-request/v1",
        "source_template_id": "agent-memory-first-template-pack",
        "target_build_pack_id": pack_id,
        "target_display_name": f"{pack_id} display",
        "target_version": "0.1.0",
        "target_revision": "workflow-eval",
        "materialized_by": "codex",
        "materialization_reason": "Workflow invocation evaluation",
        "copy_mode": "copy_pack_root",
        "include_benchmark_declarations": True,
    }


def _promotion_request(pack_id: str, *, target_environment: str = "testing", release_id: str = "r1") -> dict[str, Any]:
    return {
        "schema_version": "build-pack-promotion-request/v1",
        "build_pack_id": pack_id,
        "target_environment": target_environment,
        "release_id": release_id,
        "promoted_by": "codex",
        "promotion_reason": f"Promote {pack_id} to {target_environment}",
        "verification_timestamp": "2026-03-20T00:00:00Z",
    }


def _pipeline_request(pack_id: str, *, commit_promotion: bool) -> dict[str, Any]:
    return {
        "schema_version": "deployment-pipeline-request/v1",
        "build_pack_id": pack_id,
        "target_environment": "testing",
        "release_id": "pipe-r1",
        "cloud_adapter_id": "local-test-adapter",
        "invoked_by": "codex",
        "commit_promotion_on_success": commit_promotion,
        "validation_command_ref": "pack.json.entrypoints.validation_command",
        "benchmark_source": "status/readiness.json.required_gates",
        "verification_commands": [f"{sys.executable} -c \"print('verify')\""],
        "secret_refs": [],
    }


def _write_request(path: Path, payload: dict[str, Any]) -> None:
    write_json(path, payload)


def _seed_integrity_evidence(pack_root: Path, *, run_id: str = "bootstrap") -> None:
    generated_at = "2026-03-20T00:00:00Z"
    readiness = _load_object(pack_root / "status/readiness.json")
    eval_latest = _load_object(pack_root / "eval/latest/index.json")
    benchmark_results = [
        {
            "benchmark_id": result["benchmark_id"],
            "status": "pass",
        }
        for result in eval_latest.get("benchmark_results", [])
        if isinstance(result, dict) and isinstance(result.get("benchmark_id"), str)
    ]
    mandatory_gate_ids = [
        gate["gate_id"]
        for gate in readiness.get("required_gates", [])
        if isinstance(gate, dict)
        and gate.get("mandatory") is True
        and gate.get("gate_id") != "validate_build_pack_contract"
    ]
    run_dir = pack_root / "eval/history" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    validation_relative = f"eval/history/{run_id}/validation-result.json"
    benchmark_relative = f"eval/history/{run_id}/benchmark-result.json"
    write_json(
        pack_root / validation_relative,
        {
            "build_pack_id": pack_root.name,
            "gate_id": "validate_build_pack_contract",
            "status": "pass",
            "command": f"{sys.executable} -c \"print('ok')\"",
            "returncode": 0,
            "stdout": "ok\n",
            "stderr": "",
        },
    )
    write_json(
        pack_root / benchmark_relative,
        {
            "build_pack_id": pack_root.name,
            "status": "pass",
            "benchmark_results": benchmark_results,
            "command": f"{sys.executable} -c \"print('bench')\"",
            "mandatory_gate_ids": mandatory_gate_ids,
            "returncode": 0,
            "stdout": "bench\n",
            "stderr": "",
        },
    )

    eval_latest["updated_at"] = generated_at
    for result in eval_latest.get("benchmark_results", []):
        if not isinstance(result, dict):
            continue
        result["status"] = "pass"
        result["latest_run_id"] = run_id
        result["run_artifact_path"] = benchmark_relative
        result["summary_artifact_path"] = benchmark_relative
    write_json(pack_root / "eval/latest/index.json", eval_latest)

    readiness["readiness_state"] = "ready_for_deploy"
    readiness["ready_for_deployment"] = True
    readiness["last_evaluated_at"] = generated_at
    readiness["blocking_issues"] = []
    for gate in readiness.get("required_gates", []):
        if not isinstance(gate, dict):
            continue
        gate["status"] = "pass"
        gate["last_run_at"] = generated_at
        if gate.get("gate_id") == "validate_build_pack_contract":
            gate["evidence_paths"] = [validation_relative]
        else:
            gate["evidence_paths"] = ["eval/latest/index.json"]
    write_json(pack_root / "status/readiness.json", readiness)


def _assert_factory_valid(factory_root: Path, *, context: str) -> None:
    payload, returncode, stderr = _run_factory_validation(factory_root)
    if returncode == 0 and payload.get("valid") is True:
        return
    raise RuntimeError(
        f"{context}: copied factory validation failed: payload={payload} stderr={stderr}"
    )


def _prepare_ready_build_pack(factory_root: Path, pack_id: str) -> Path:
    request_path = factory_root / f"{pack_id}-materialize.json"
    _write_request(request_path, _materialization_request(pack_id))
    payload, _returncode, _duration_ms, stderr = _run_cli(
        SCRIPT_DIR / "materialize_build_pack.py",
        factory_root=factory_root,
        request_path=request_path,
    )
    if payload.get("status") != "completed":
        raise RuntimeError(f"materialization failed for {pack_id}: {payload} stderr={stderr}")

    pack_root = factory_root / "build-packs" / pack_id
    _seed_integrity_evidence(pack_root, run_id=f"bootstrap-{pack_id}")
    return pack_root


def _prepare_release(pack_root: Path, *, release_id: str) -> None:
    release = {
        "schema_version": "pack-release/v1",
        "build_pack_id": pack_root.name,
        "release_id": release_id,
        "source_template_id": "agent-memory-first-template-pack",
        "source_template_revision": "workflow-eval",
        "built_at": "2026-03-20T00:00:00Z",
        "release_state": "testing",
        "artifact_paths": ["src/"],
    }
    write_json(pack_root / "dist/releases" / release_id / "release.json", release)
    write_json(pack_root / "dist/candidates" / release_id / "release.json", release)


def _configure_pipeline_commands(pack_root: Path) -> None:
    manifest_path = pack_root / "pack.json"
    manifest = _load_object(manifest_path)
    manifest["entrypoints"]["validation_command"] = f"{sys.executable} -c \"print('ok')\""
    eval_latest = _load_object(pack_root / "eval/latest/index.json")
    benchmark_id = next(
        str(result["benchmark_id"])
        for result in eval_latest.get("benchmark_results", [])
        if isinstance(result, dict) and isinstance(result.get("benchmark_id"), str)
    )
    manifest["entrypoints"]["benchmark_command"] = (
        f"{sys.executable} -c "
        f"\"import json; print(json.dumps({{'benchmark_id': '{benchmark_id}', 'status': 'pass'}}))\""
    )
    write_json(manifest_path, manifest)


def _evaluate_materialization_failure(factory_root: Path) -> dict[str, Any]:
    request_path = factory_root / "materialize-fail.json"
    _write_request(request_path, _materialization_request("baseline-fail-pack"))
    payload, returncode, duration_ms, stderr = _run_cli(
        SCRIPT_DIR / "materialize_build_pack.py",
        factory_root=factory_root,
        request_path=request_path,
    )
    return {
        "test_id": "materialize_fail_no_active_template",
        "expected_status": "failed",
        "observed_status": payload.get("status"),
        "pass": payload.get("status") == "failed",
        "exit_code": returncode,
        "duration_ms": duration_ms,
        "stderr": stderr,
        "result": payload,
        "note": "Clean factory baseline should fail-closed because all templates are retired.",
    }


def _evaluate_materialization_success(factory_root: Path) -> dict[str, Any]:
    _activate_template(factory_root, "agent-memory-first-template-pack")
    request_path = factory_root / "materialize-success.json"
    _write_request(request_path, _materialization_request("materialized-pack"))
    payload, returncode, duration_ms, stderr = _run_cli(
        SCRIPT_DIR / "materialize_build_pack.py",
        factory_root=factory_root,
        request_path=request_path,
    )
    registry = _load_object(factory_root / "registry/build-packs.json")
    registered = any(
        entry.get("pack_id") == "materialized-pack" and entry.get("active") is True
        for entry in registry.get("entries", [])
        if isinstance(entry, dict)
    )
    pack_exists = (factory_root / "build-packs" / "materialized-pack").exists()
    return {
        "test_id": "materialize_success_reactivated_template",
        "expected_status": "completed",
        "observed_status": payload.get("status"),
        "pass": payload.get("status") == "completed" and registered and pack_exists,
        "exit_code": returncode,
        "duration_ms": duration_ms,
        "stderr": stderr,
        "build_pack_registered": registered,
        "pack_root_exists": pack_exists,
        "result": payload,
    }


def _evaluate_promotion_success(factory_root: Path) -> dict[str, Any]:
    _activate_template(factory_root, "agent-memory-first-template-pack")
    pack_root = _prepare_ready_build_pack(factory_root, "promo-pack")
    _assert_factory_valid(factory_root, context="promotion eval setup")
    _prepare_release(pack_root, release_id="r1")
    request_path = factory_root / "promote-success.json"
    _write_request(request_path, _promotion_request("promo-pack"))
    payload, returncode, duration_ms, stderr = _run_cli(
        SCRIPT_DIR / "promote_build_pack.py",
        factory_root=factory_root,
        request_path=request_path,
    )
    pointer_exists = (factory_root / "deployments/testing/promo-pack.json").exists()
    deployment = _load_object(pack_root / "status/deployment.json")
    deployment_state = deployment.get("deployment_state")
    return {
        "test_id": "promote_success_testing",
        "expected_status": "completed",
        "observed_status": payload.get("status"),
        "pass": payload.get("status") == "completed" and pointer_exists and deployment_state == "testing",
        "exit_code": returncode,
        "duration_ms": duration_ms,
        "stderr": stderr,
        "deployment_pointer_exists": pointer_exists,
        "deployment_state": deployment_state,
        "result": payload,
    }


def _evaluate_pipeline_success(factory_root: Path, *, commit_promotion: bool) -> dict[str, Any]:
    _activate_template(factory_root, "agent-memory-first-template-pack")
    pack_root = _prepare_ready_build_pack(factory_root, "pipeline-pack")
    _configure_pipeline_commands(pack_root)
    _assert_factory_valid(factory_root, context="pipeline eval setup")
    request_path = factory_root / ("pipeline-commit.json" if commit_promotion else "pipeline-no-commit.json")
    _write_request(request_path, _pipeline_request("pipeline-pack", commit_promotion=commit_promotion))
    payload, returncode, duration_ms, stderr = _run_cli(
        SCRIPT_DIR / "run_deployment_pipeline.py",
        factory_root=factory_root,
        request_path=request_path,
    )
    report = _load_object(Path(payload["pipeline_report_path"]))
    pointer_exists = (factory_root / "deployments/testing/pipeline-pack.json").exists()
    deployment = _load_object(pack_root / "status/deployment.json")
    deployment_state = deployment.get("deployment_state")
    expected_pointer = commit_promotion
    expected_deployment_state = "testing" if commit_promotion else "not_deployed"
    return {
        "test_id": "pipeline_success_with_commit" if commit_promotion else "pipeline_success_without_commit",
        "expected_status": "completed",
        "observed_status": payload.get("status"),
        "pass": (
            payload.get("status") == "completed"
            and report.get("final_status") == "completed"
            and pointer_exists is expected_pointer
            and deployment_state == expected_deployment_state
        ),
        "exit_code": returncode,
        "duration_ms": duration_ms,
        "stderr": stderr,
        "commit_promotion": commit_promotion,
        "stage_statuses": [stage.get("status") for stage in report.get("stage_results", []) if isinstance(stage, dict)],
        "deployment_pointer_exists": pointer_exists,
        "deployment_state": deployment_state,
        "result": payload,
    }


def run_workflow_eval(factory_root: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    baseline_factory = _copy_factory(factory_root, "workflow-eval-baseline")
    cases.append(_evaluate_materialization_failure(baseline_factory))

    materialize_factory = _copy_factory(factory_root, "workflow-eval-materialize")
    cases.append(_evaluate_materialization_success(materialize_factory))

    promotion_factory = _copy_factory(factory_root, "workflow-eval-promote")
    cases.append(_evaluate_promotion_success(promotion_factory))

    pipeline_no_commit_factory = _copy_factory(factory_root, "workflow-eval-pipeline-no-commit")
    cases.append(_evaluate_pipeline_success(pipeline_no_commit_factory, commit_promotion=False))

    pipeline_commit_factory = _copy_factory(factory_root, "workflow-eval-pipeline-commit")
    cases.append(_evaluate_pipeline_success(pipeline_commit_factory, commit_promotion=True))

    passed = sum(1 for case in cases if case["pass"] is True)
    failed = len(cases) - passed
    return {
        "schema_version": "project-pack-factory-workflow-eval/v1",
        "factory_root": str(factory_root),
        "status": "completed" if failed == 0 else "failed",
        "summary": {
            "case_count": len(cases),
            "passed": passed,
            "failed": failed,
        },
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a small repeatable Project Pack Factory workflow evaluation.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    args = parser.parse_args()

    try:
        result = run_workflow_eval(resolve_factory_root(args.factory_root))
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2))
        return 1

    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
