#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Final, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    isoformat_z,
    load_json,
    load_pack_manifest,
    read_now,
    relative_path,
    resolve_pack_root,
    validate_named_payload,
    write_json,
)


VALIDATION_GATE_ID: Final[str] = "validate_build_pack_contract"
EVAL_LATEST_INDEX_PATH: Final[Path] = Path("eval/latest/index.json")
READINESS_PATH: Final[Path] = Path("status/readiness.json")
HANDOFF_DIRECTORY_KEYS: Final[tuple[str, ...]] = (
    "project_objective_file",
    "task_backlog_file",
    "work_state_file",
)
ALLOWED_MODES: Final[tuple[str, ...]] = ("validation-only", "benchmark-only")
ALLOWED_BENCHMARK_STATUSES: Final[frozenset[str]] = frozenset({"pass", "waived"})


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


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


def _parse_json_text(value: str) -> dict[str, Any]:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("benchmark command must emit a JSON object")
    return payload


def _benchmark_results_from_stdout(stdout: str) -> list[dict[str, Any]]:
    payload = _parse_json_text(stdout)
    benchmark_results = payload.get("benchmark_results")
    if isinstance(benchmark_results, list):
        return [result for result in benchmark_results if isinstance(result, dict)]
    if isinstance(payload.get("benchmark_id"), str):
        return [payload]
    raise ValueError("benchmark command JSON output must include benchmark_id or benchmark_results")


def _pack_relative_path(pack_root: Path, path: Path) -> str:
    return str(path.relative_to(pack_root))


def _gate_id(benchmark_id: str) -> str:
    return benchmark_id.replace("-", "_")


def _write_stage_evidence(path: Path, payload: dict[str, Any]) -> str:
    write_json(path, payload)
    return str(path)


def _validate_payload(pack_root: Path, manifest: dict[str, Any], schema_name: str, payload: dict[str, Any]) -> None:
    validate_named_payload(pack_root, manifest, schema_name, payload)


def _read_manifest(pack_root: Path) -> dict[str, Any]:
    manifest = load_pack_manifest(pack_root)
    directory_contract = manifest.get("directory_contract")
    if not isinstance(directory_contract, dict):
        raise ValueError("pack.json.directory_contract must be an object")
    for key in HANDOFF_DIRECTORY_KEYS:
        relative = directory_contract.get(key)
        if not isinstance(relative, str) or not relative:
            raise ValueError(f"pack.json.directory_contract must declare `{key}` for handoff-carrying build-packs")
        if not (pack_root / relative).exists():
            raise ValueError(f"handoff-carrying pack is missing `{key}` at {relative}")
    return manifest


def _assert_canonical_identity(
    *,
    manifest: dict[str, Any],
    readiness: dict[str, Any],
    eval_latest: dict[str, Any],
) -> None:
    pack_id = manifest.get("pack_id")
    if readiness.get("pack_id") != pack_id:
        raise ValueError("status/readiness.json pack_id does not match pack.json")
    if eval_latest.get("pack_id") != pack_id:
        raise ValueError("eval/latest/index.json pack_id does not match pack.json")
    if readiness.get("pack_kind") != "build_pack":
        raise ValueError("status/readiness.json pack_kind must be build_pack")
    if eval_latest.get("pack_kind") != "build_pack":
        raise ValueError("eval/latest/index.json pack_kind must be build_pack")


def _gate_by_id(readiness: dict[str, Any], gate_id: str) -> dict[str, Any]:
    gates = readiness.get("required_gates", [])
    if not isinstance(gates, list):
        raise ValueError("status/readiness.json required_gates must be an array")
    for gate in gates:
        if isinstance(gate, dict) and gate.get("gate_id") == gate_id:
            return gate
    raise ValueError(f"status/readiness.json is missing required gate `{gate_id}`")


def _mandatory_benchmark_gates(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    gates = readiness.get("required_gates", [])
    if not isinstance(gates, list):
        raise ValueError("status/readiness.json required_gates must be an array")
    return [
        gate
        for gate in gates
        if isinstance(gate, dict)
        and gate.get("gate_id") != VALIDATION_GATE_ID
        and gate.get("mandatory") is True
    ]


def _canonical_validation_evidence_path(pack_root: Path, gate: dict[str, Any]) -> Path:
    evidence_paths = gate.get("evidence_paths", [])
    if not isinstance(evidence_paths, list):
        raise ValueError("validation gate evidence_paths must be an array")
    for candidate in evidence_paths:
        if not isinstance(candidate, str) or not candidate.endswith("validation-result.json"):
            continue
        resolved = (pack_root / candidate).resolve()
        try:
            resolved.relative_to(pack_root)
        except ValueError as exc:
            raise ValueError("validation gate evidence path must stay within pack_root") from exc
        if resolved.exists():
            return resolved
    raise ValueError(
        "benchmark-only mode requires validate_build_pack_contract to point at a real validation-result.json artifact"
    )


def _all_mandatory_benchmark_gates_satisfied(readiness: dict[str, Any]) -> bool:
    for gate in _mandatory_benchmark_gates(readiness):
        status = gate.get("status")
        if status not in ("pass", "waived"):
            return False
    return True


def _default_eval_run_id(pack_id: str, mode: str) -> str:
    token = "validation" if mode == "validation-only" else "benchmark"
    return f"readiness-eval-{pack_id}-{token}-{read_now().strftime('%Y%m%d')}t{read_now().strftime('%H%M%S')}z"


def _validation_result_payload(
    *,
    pack_id: str,
    command: str,
    result: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    return {
        "build_pack_id": pack_id,
        "gate_id": VALIDATION_GATE_ID,
        "status": "pass",
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _benchmark_result_payload(
    *,
    pack_id: str,
    command: str,
    benchmark_entries: list[dict[str, Any]],
    mandatory_gate_ids: list[str],
    result: subprocess.CompletedProcess[str],
) -> dict[str, Any]:
    return {
        "build_pack_id": pack_id,
        "status": "pass",
        "benchmark_results": benchmark_entries,
        "command": command,
        "mandatory_gate_ids": mandatory_gate_ids,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _run_validation_only(
    *,
    pack_root: Path,
    manifest: dict[str, Any],
    readiness: dict[str, Any],
    eval_run_id: str,
) -> dict[str, Any]:
    pack_id = str(manifest["pack_id"])
    generated_at = isoformat_z()
    validation_command = str(cast(dict[str, Any], manifest["entrypoints"])["validation_command"])
    validation_result = _run_command(validation_command, pack_root)
    if validation_result.returncode != 0:
        raise ValueError("build-pack validation command failed")

    eval_dir = pack_root / "eval/history" / eval_run_id
    if (eval_dir / "validation-result.json").exists():
        raise ValueError(f"validation evidence already exists for eval_run_id `{eval_run_id}`")
    validation_evidence = _write_stage_evidence(
        eval_dir / "validation-result.json",
        _validation_result_payload(
            pack_id=pack_id,
            command=validation_command,
            result=validation_result,
        ),
    )

    updated_readiness = json.loads(json.dumps(readiness))
    validation_gate = _gate_by_id(updated_readiness, VALIDATION_GATE_ID)
    validation_gate["status"] = "pass"
    validation_gate["last_run_at"] = generated_at
    validation_gate["evidence_paths"] = [_pack_relative_path(pack_root, Path(validation_evidence))]
    updated_readiness["last_evaluated_at"] = generated_at
    updated_readiness["ready_for_deployment"] = False
    if updated_readiness.get("readiness_state") == "ready_for_deploy":
        updated_readiness["readiness_state"] = "in_progress"

    _validate_payload(pack_root, manifest, "readiness.schema.json", updated_readiness)
    write_json(pack_root / READINESS_PATH, updated_readiness)

    return {
        "status": "completed",
        "mode": "validation-only",
        "pack_id": pack_id,
        "eval_run_id": eval_run_id,
        "evidence_paths": [relative_path(pack_root, Path(validation_evidence))],
        "readiness_path": relative_path(pack_root, pack_root / READINESS_PATH),
        "eval_latest_index_path": relative_path(pack_root, pack_root / EVAL_LATEST_INDEX_PATH),
        "ready_for_deployment": False,
    }


def _run_benchmark_only(
    *,
    pack_root: Path,
    manifest: dict[str, Any],
    readiness: dict[str, Any],
    eval_latest: dict[str, Any],
    eval_run_id: str,
) -> dict[str, Any]:
    pack_id = str(manifest["pack_id"])
    generated_at = isoformat_z()
    validation_gate = _gate_by_id(readiness, VALIDATION_GATE_ID)
    if validation_gate.get("status") != "pass":
        raise ValueError("benchmark-only mode requires validate_build_pack_contract.status = pass")
    _canonical_validation_evidence_path(pack_root, validation_gate)

    mandatory_benchmark_gates = _mandatory_benchmark_gates(readiness)
    mandatory_gate_ids = [str(gate["gate_id"]) for gate in mandatory_benchmark_gates]

    expected_benchmark_ids = {
        str(result.get("benchmark_id"))
        for result in cast(list[dict[str, Any]], eval_latest.get("benchmark_results", []))
        if isinstance(result, dict) and isinstance(result.get("benchmark_id"), str)
    }
    if not expected_benchmark_ids:
        raise ValueError("eval/latest/index.json must declare at least one benchmark result")

    benchmark_command = str(cast(dict[str, Any], manifest["entrypoints"])["benchmark_command"])
    benchmark_result = _run_command(benchmark_command, pack_root)
    if benchmark_result.returncode != 0:
        raise ValueError("required benchmark command failed")

    benchmark_entries = _benchmark_results_from_stdout(benchmark_result.stdout)
    observed_benchmark_ids = {
        str(result.get("benchmark_id"))
        for result in benchmark_entries
        if isinstance(result.get("benchmark_id"), str)
    }
    if observed_benchmark_ids != expected_benchmark_ids:
        raise ValueError("benchmark command reported benchmark ids that do not match eval/latest")
    if any(result.get("status") not in ALLOWED_BENCHMARK_STATUSES for result in benchmark_entries):
        raise ValueError("required benchmark command did not report only pass or waived benchmark results")

    eval_dir = pack_root / "eval/history" / eval_run_id
    if (eval_dir / "benchmark-result.json").exists():
        raise ValueError(f"benchmark evidence already exists for eval_run_id `{eval_run_id}`")
    benchmark_evidence = _write_stage_evidence(
        eval_dir / "benchmark-result.json",
        _benchmark_result_payload(
            pack_id=pack_id,
            command=benchmark_command,
            benchmark_entries=benchmark_entries,
            mandatory_gate_ids=mandatory_gate_ids,
            result=benchmark_result,
        ),
    )

    updated_eval_latest = json.loads(json.dumps(eval_latest))
    benchmark_pack_relative = _pack_relative_path(pack_root, Path(benchmark_evidence))
    benchmark_status_by_benchmark_id = {
        str(result["benchmark_id"]): str(result["status"])
        for result in benchmark_entries
        if isinstance(result.get("benchmark_id"), str) and isinstance(result.get("status"), str)
    }
    benchmark_status_by_id = {
        _gate_id(str(result["benchmark_id"])): str(result["status"])
        for result in benchmark_entries
        if isinstance(result.get("benchmark_id"), str) and isinstance(result.get("status"), str)
    }
    for result in cast(list[dict[str, Any]], updated_eval_latest.get("benchmark_results", [])):
        benchmark_id = str(result.get("benchmark_id"))
        if benchmark_id not in benchmark_status_by_benchmark_id:
            continue
        result["status"] = "pass"
        result["latest_run_id"] = eval_run_id
        result["run_artifact_path"] = benchmark_pack_relative
        result["summary_artifact_path"] = benchmark_pack_relative
    updated_eval_latest["updated_at"] = generated_at

    updated_readiness = json.loads(json.dumps(readiness))
    updated_readiness["last_evaluated_at"] = generated_at
    for gate in cast(list[dict[str, Any]], updated_readiness.get("required_gates", [])):
        if not isinstance(gate, dict):
            continue
        gate_id = gate.get("gate_id")
        if gate_id == VALIDATION_GATE_ID or gate.get("mandatory") is not True or not isinstance(gate_id, str):
            continue
        if gate_id not in benchmark_status_by_id:
            continue
        reported_status = benchmark_status_by_id[gate_id]
        gate["status"] = "waived" if reported_status == "waived" else "pass"
        gate["last_run_at"] = generated_at
        gate["evidence_paths"] = [str(EVAL_LATEST_INDEX_PATH)]

    ready_for_deployment = (
        _gate_by_id(updated_readiness, VALIDATION_GATE_ID).get("status") == "pass"
        and _all_mandatory_benchmark_gates_satisfied(updated_readiness)
    )
    updated_readiness["ready_for_deployment"] = ready_for_deployment
    if ready_for_deployment:
        updated_readiness["readiness_state"] = "ready_for_deploy"
        updated_readiness["blocking_issues"] = []
    elif updated_readiness.get("readiness_state") == "ready_for_deploy":
        updated_readiness["readiness_state"] = "in_progress"

    _validate_payload(pack_root, manifest, "eval-latest-index.schema.json", updated_eval_latest)
    _validate_payload(pack_root, manifest, "readiness.schema.json", updated_readiness)
    write_json(pack_root / EVAL_LATEST_INDEX_PATH, updated_eval_latest)
    write_json(pack_root / READINESS_PATH, updated_readiness)

    return {
        "status": "completed",
        "mode": "benchmark-only",
        "pack_id": pack_id,
        "eval_run_id": eval_run_id,
        "evidence_paths": [relative_path(pack_root, Path(benchmark_evidence))],
        "readiness_path": relative_path(pack_root, pack_root / READINESS_PATH),
        "eval_latest_index_path": relative_path(pack_root, pack_root / EVAL_LATEST_INDEX_PATH),
        "ready_for_deployment": ready_for_deployment,
    }


def run_build_pack_readiness_eval(
    *,
    pack_root: Path,
    mode: str,
    invoked_by: str,
    eval_run_id: str | None,
) -> dict[str, Any]:
    if mode not in ALLOWED_MODES:
        raise ValueError(f"mode must be one of: {', '.join(ALLOWED_MODES)}")
    if not invoked_by.strip():
        raise ValueError("invoked_by must be non-empty")

    manifest = _read_manifest(pack_root)
    readiness = _load_object(pack_root / READINESS_PATH)
    eval_latest = _load_object(pack_root / EVAL_LATEST_INDEX_PATH)
    _assert_canonical_identity(
        manifest=manifest,
        readiness=readiness,
        eval_latest=eval_latest,
    )
    pack_id = str(manifest["pack_id"])
    resolved_eval_run_id = eval_run_id.strip() if eval_run_id and eval_run_id.strip() else _default_eval_run_id(pack_id, mode)

    if mode == "validation-only":
        payload = _run_validation_only(
            pack_root=pack_root,
            manifest=manifest,
            readiness=readiness,
            eval_run_id=resolved_eval_run_id,
        )
    else:
        payload = _run_benchmark_only(
            pack_root=pack_root,
            manifest=manifest,
            readiness=readiness,
            eval_latest=eval_latest,
            eval_run_id=resolved_eval_run_id,
        )
    payload["invoked_by"] = invoked_by
    payload["generated_at"] = isoformat_z(read_now())
    return payload


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded build-pack readiness evaluation step.")
    parser.add_argument("--pack-root", required=True)
    parser.add_argument("--mode", required=True, choices=ALLOWED_MODES)
    parser.add_argument("--invoked-by", required=True)
    parser.add_argument("--eval-run-id")
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        payload = run_build_pack_readiness_eval(
            pack_root=resolve_pack_root(args.pack_root),
            mode=args.mode,
            invoked_by=args.invoked_by,
            eval_run_id=args.eval_run_id,
        )
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
