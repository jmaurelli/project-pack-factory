#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    PROMOTION_LOG_PATH,
    discover_pack,
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)
from promote_build_pack import promote_build_pack


STAGE_IDS = [
    "validate_factory_state",
    "validate_build_pack",
    "run_required_benchmarks",
    "package_release",
    "deploy_release",
    "verify_deployment",
    "finalize_promotion",
]


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _load_request(request_path: Path, factory_root: Path) -> dict[str, Any]:
    errors = validate_json_document(
        request_path,
        schema_path(factory_root, "deployment-pipeline-request.schema.json"),
    )
    if errors:
        raise ValueError("; ".join(errors))
    return _load_object(request_path)


def _run_command(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        shell=True,
        executable="/bin/bash",
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def _package_release_document(
    *,
    pack_id: str,
    release_id: str,
    lineage: dict[str, Any],
    built_at: str,
    release_state: str,
) -> dict[str, Any]:
    return {
        "schema_version": "pack-release/v1",
        "build_pack_id": pack_id,
        "release_id": release_id,
        "source_template_id": lineage["source_template_id"],
        "source_template_revision": lineage["source_template_revision"],
        "built_at": built_at,
        "release_state": release_state,
        "artifact_paths": [
            "src/",
            "tests/",
            "contracts/",
            "docs/specs/",
            "benchmarks/active-set.json",
            "eval/latest/index.json",
        ],
    }


def _write_stage_evidence(path: Path, payload: dict[str, Any]) -> str:
    write_json(path, payload)
    return str(path)


def _pack_relative_path(pack_root: Path, path: Path) -> str:
    return str(path.relative_to(pack_root))


def run_deployment_pipeline(factory_root: Path, request: dict[str, Any]) -> dict[str, Any]:
    pack_id = str(request["build_pack_id"])
    target_environment = str(request["target_environment"])
    release_id = str(request["release_id"])
    cloud_adapter_id = str(request["cloud_adapter_id"])
    invoked_by = str(request["invoked_by"])
    commit_promotion = bool(request["commit_promotion_on_success"])
    verification_commands = [str(command) for command in request.get("verification_commands", [])]

    location = discover_pack(factory_root, pack_id)
    if location.pack_kind != "build_pack":
        raise ValueError(f"{pack_id} is not a build_pack")
    pack_root = location.pack_root
    manifest = _load_object(pack_root / "pack.json")
    readiness = _load_object(pack_root / "status/readiness.json")
    lineage = _load_object(pack_root / "lineage/source-template.json")

    now = read_now()
    generated_at = isoformat_z(now)
    pipeline_id = f"pipeline-{pack_id}-{target_environment}-{timestamp_token(now)}"
    report_relative = f"eval/history/{pipeline_id}/pipeline-report.json"
    report_path = pack_root / report_relative
    operation_log_update = {
        "promotion_log_path": "registry/promotion-log.json",
        "event_type": "pipeline_executed",
        "pipeline_id": pipeline_id,
        "build_pack_id": pack_id,
        "pipeline_report_path": report_relative,
    }

    stage_results: list[dict[str, Any]] = []
    final_status = "completed"
    adapter_result: dict[str, Any] | None = None
    evidence_paths: list[str] = [f"build-packs/{pack_id}/{report_relative}"]
    promotion_result: dict[str, Any] | None = None
    canonical_state_changed = False
    canonical_assignment_status = "unchanged"
    pipeline_dir = pack_root / "eval/history" / pipeline_id
    pipeline_dir.mkdir(parents=True, exist_ok=True)

    def complete(stage_id: str, summary: str) -> None:
        stage_results.append({"stage_id": stage_id, "status": "completed", "summary": summary})

    def reconcile(stage_id: str, summary: str) -> None:
        stage_results.append({"stage_id": stage_id, "status": "reconciled", "summary": summary})

    def fail(stage_id: str, summary: str) -> None:
        nonlocal final_status
        final_status = "failed"
        stage_results.append({"stage_id": stage_id, "status": "failed", "summary": summary})

    def skip_remaining(start_index: int, summary: str) -> None:
        for stage_id in STAGE_IDS[start_index:]:
            stage_results.append({"stage_id": stage_id, "status": "skipped", "summary": summary})

    try:
        factory_validation = subprocess.run(
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
        if factory_validation.returncode != 0 or json.loads(factory_validation.stdout).get("valid") is not True:
            fail("validate_factory_state", "Factory validation failed.")
            skip_remaining(1, "Skipped after factory validation failure.")
        else:
            complete("validate_factory_state", "Factory validation passed.")

        if final_status == "failed":
            raise RuntimeError("pipeline_failed")

        validation_command = str(manifest["entrypoints"]["validation_command"])
        validation_result = _run_command(validation_command, pack_root)
        if validation_result.returncode != 0:
            fail("validate_build_pack", "Build-pack validation command failed.")
            skip_remaining(2, "Skipped after build-pack validation failure.")
            raise RuntimeError("pipeline_failed")
        validation_evidence = _write_stage_evidence(
            pipeline_dir / "validation-result.json",
            {
                "command": validation_command,
                "returncode": validation_result.returncode,
                "stdout": validation_result.stdout,
                "stderr": validation_result.stderr,
            },
        )
        evidence_paths.append(relative_path(factory_root, Path(validation_evidence)))
        complete("validate_build_pack", "Build-pack validation command passed.")

        mandatory_gate_ids = [
            str(gate["gate_id"])
            for gate in readiness.get("required_gates", [])
            if isinstance(gate, dict) and gate.get("mandatory") is True
        ]
        benchmark_command = str(manifest["entrypoints"]["benchmark_command"])
        benchmark_result = _run_command(benchmark_command, pack_root)
        if benchmark_result.returncode != 0:
            fail("run_required_benchmarks", "Required benchmark command failed.")
            skip_remaining(3, "Skipped after benchmark failure.")
            raise RuntimeError("pipeline_failed")
        benchmark_evidence = _write_stage_evidence(
            pipeline_dir / "benchmark-result.json",
            {
                "command": benchmark_command,
                "mandatory_gate_ids": mandatory_gate_ids,
                "returncode": benchmark_result.returncode,
                "stdout": benchmark_result.stdout,
                "stderr": benchmark_result.stderr,
            },
        )
        evidence_paths.append(relative_path(factory_root, Path(benchmark_evidence)))
        eval_latest = _load_object(pack_root / "eval/latest/index.json")
        benchmark_pack_relative = _pack_relative_path(pack_root, Path(benchmark_evidence))
        for result in eval_latest.get("benchmark_results", []):
            if isinstance(result, dict):
                result["status"] = "pass"
                result["latest_run_id"] = pipeline_id
                result["run_artifact_path"] = benchmark_pack_relative
                result["summary_artifact_path"] = benchmark_pack_relative
        eval_latest["updated_at"] = generated_at
        write_json(pack_root / "eval/latest/index.json", eval_latest)

        readiness["last_evaluated_at"] = generated_at
        readiness["blocking_issues"] = []
        readiness["ready_for_deployment"] = True
        readiness["readiness_state"] = "ready_for_deploy"
        for gate in readiness.get("required_gates", []):
            if isinstance(gate, dict) and gate.get("mandatory") is True:
                gate["status"] = "pass"
                gate["last_run_at"] = generated_at
                gate["evidence_paths"] = [benchmark_pack_relative]
        write_json(pack_root / "status/readiness.json", readiness)
        complete(
            "run_required_benchmarks",
            f"Executed benchmark command for {len(mandatory_gate_ids)} mandatory gates.",
        )

        release_state = "testing" if target_environment == "testing" else target_environment
        release_document = _package_release_document(
            pack_id=pack_id,
            release_id=release_id,
            lineage=lineage,
            built_at=generated_at,
            release_state=release_state,
        )
        candidate_path = pack_root / "dist/candidates" / release_id / "release.json"
        release_path = pack_root / "dist/releases" / release_id / "release.json"
        write_json(candidate_path, release_document)
        write_json(release_path, release_document)
        evidence_paths.extend(
            [
                f"build-packs/{pack_id}/dist/candidates/{release_id}/release.json",
                f"build-packs/{pack_id}/dist/releases/{release_id}/release.json",
            ]
        )
        complete("package_release", "Created candidate and release artifacts.")

        adapter_result = {
            "adapter_id": cloud_adapter_id,
            "provider": cloud_adapter_id,
            "deployment_handle": f"{pack_id}:{release_id}:{target_environment}",
            "deployment_url": f"https://example.invalid/{pack_id}/{target_environment}/{release_id}",
            "status": "completed",
            "artifacts": [f"dist/releases/{release_id}/release.json"],
            "logs": [f"Pipeline deployed {pack_id} to {target_environment}."],
        }
        complete("deploy_release", "Provider-neutral deployment adapter completed.")

        verification_failures = [
            command for command in verification_commands if _run_command(command, pack_root).returncode != 0
        ]
        if verification_failures:
            adapter_result["status"] = "failed"
            fail("verify_deployment", "One or more verification commands failed.")
            skip_remaining(6, "Skipped after deployment verification failure.")
            raise RuntimeError("pipeline_failed")
        verification_evidence = _write_stage_evidence(
            pipeline_dir / "verification-result.json",
            {
                "commands": verification_commands,
                "failures": verification_failures,
                "status": "passed",
            },
        )
        evidence_paths.append(relative_path(factory_root, Path(verification_evidence)))
        complete("verify_deployment", "Post-deploy verification commands passed.")

        if commit_promotion:
            promotion_request = {
                "schema_version": "build-pack-promotion-request/v1",
                "build_pack_id": pack_id,
                "target_environment": target_environment,
                "release_id": release_id,
                "promoted_by": invoked_by,
                "promotion_reason": f"Finalized by pipeline {pipeline_id}",
                "verification_timestamp": generated_at,
            }
            promotion_result = promote_build_pack(factory_root, promotion_request)
            evidence_paths.append(relative_path(factory_root, Path(promotion_result["promotion_report_path"])))
            canonical_assignment_status = "committed"
            if promotion_result["status"] == "reconciled":
                final_status = "reconciled"
                reconcile("finalize_promotion", "Promotion state was already current and was reconciled.")
            else:
                canonical_state_changed = True
                complete("finalize_promotion", "Committed promotion through the promotion workflow.")
        else:
            complete("finalize_promotion", "Promotion commit was intentionally deferred by request.")
    except RuntimeError:
        pass
    except Exception as exc:
        if not stage_results:
            fail("validate_factory_state", f"Unexpected pipeline failure: {exc}")
            skip_remaining(1, "Skipped after unexpected pipeline failure.")
        else:
            current_stage_ids = {stage["stage_id"] for stage in stage_results}
            next_index = next((index for index, stage_id in enumerate(STAGE_IDS) if stage_id not in current_stage_ids), len(STAGE_IDS))
            if next_index < len(STAGE_IDS):
                fail(STAGE_IDS[next_index], f"Unexpected pipeline failure: {exc}")
                skip_remaining(next_index + 1, "Skipped after unexpected pipeline failure.")
            else:
                final_status = "failed"

    report = {
        "schema_version": "deployment-pipeline-report/v1",
        "pipeline_id": pipeline_id,
        "generated_at": generated_at,
        "build_pack_id": pack_id,
        "build_pack_root": f"build-packs/{pack_id}",
        "target_environment": target_environment,
        "release_id": release_id,
        "cloud_adapter_id": cloud_adapter_id,
        "invoked_by": invoked_by,
        "commit_promotion_on_success": commit_promotion,
        "final_status": final_status,
        "canonical_state_changed": canonical_state_changed,
        "canonical_assignment_status": canonical_assignment_status,
        "operation_log_update": operation_log_update,
        "stage_results": stage_results,
        "adapter_result": adapter_result,
        "evidence_paths": evidence_paths,
    }
    try:
        promotion_log_path = factory_root / PROMOTION_LOG_PATH
        promotion_log = _load_object(promotion_log_path)
        events = promotion_log.setdefault("events", [])
        if not isinstance(events, list):
            raise ValueError(f"{promotion_log_path}: events must be an array")
        events.append(
            {
                "event_type": "pipeline_executed",
                "pipeline_id": pipeline_id,
                "build_pack_id": pack_id,
                "pipeline_report_path": report_relative,
                "status": final_status,
            }
        )
        promotion_log["updated_at"] = generated_at
        write_json(promotion_log_path, promotion_log)
    finally:
        write_json(report_path, report)

    return {
        "status": final_status,
        "pipeline_id": pipeline_id,
        "pipeline_report_path": str(report_path),
        "promotion_report_path": None if promotion_result is None else promotion_result.get("promotion_report_path"),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the PackFactory deployment pipeline.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        factory_root = resolve_factory_root(args.factory_root)
        request = _load_request(Path(args.request_file), factory_root)
        payload = run_deployment_pipeline(factory_root, request)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["status"] != "failed" else 1
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
