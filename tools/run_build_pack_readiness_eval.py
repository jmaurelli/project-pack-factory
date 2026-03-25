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
    read_now,
    relative_path,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


VALIDATION_GATE_ID: Final[str] = "validate_build_pack_contract"
EVAL_LATEST_INDEX_PATH: Final[Path] = Path("eval/latest/index.json")
READINESS_PATH: Final[Path] = Path("status/readiness.json")
PACK_MANIFEST_PATH: Final[Path] = Path("pack.json")
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


def _resolve_pack_root(pack_root: str | Path) -> Path:
    root = Path(pack_root).expanduser().resolve()
    if not root.is_absolute():
        raise ValueError("pack_root must resolve to an absolute path")
    return root


def _discover_factory_root(pack_root: Path) -> Path:
    for candidate in (pack_root, *pack_root.parents):
        if (candidate / "registry").is_dir() and (candidate / "docs/specs/project-pack-factory/schemas").is_dir():
            return candidate
    raise ValueError("could not discover factory_root from pack_root")


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


def _stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _pack_relative_path(pack_root: Path, path: Path) -> str:
    return str(path.relative_to(pack_root))


def _gate_id(benchmark_id: str) -> str:
    return benchmark_id.replace("-", "_")


def _write_stage_evidence(path: Path, payload: dict[str, Any]) -> str:
    write_json(path, payload)
    return str(path)


def _validate_payload(factory_root: Path, schema_name: str, payload: dict[str, Any], *, label: str) -> None:
    temp_root = factory_root / ".pack-state" / "readiness-eval-schema-validation"
    temp_path = temp_root / f"{label}.json"
    write_json(temp_path, payload)
    errors = validate_json_document(temp_path, schema_path(factory_root, schema_name))
    temp_path.unlink(missing_ok=True)
    if temp_path.parent.exists() and not any(temp_path.parent.iterdir()):
        temp_path.parent.rmdir()
    if errors:
        raise ValueError("; ".join(errors))


def _read_manifest(pack_root: Path) -> dict[str, Any]:
    manifest = _load_object(pack_root / PACK_MANIFEST_PATH)
    if manifest.get("pack_kind") != "build_pack":
        raise ValueError("run_build_pack_readiness_eval only supports build_pack manifests")
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


def _hint_is_active(hint: dict[str, Any]) -> bool:
    if hint.get("active") is False:
        return False
    remaining_applications = hint.get("remaining_applications")
    return not (isinstance(remaining_applications, int) and remaining_applications <= 0)


def _latest_hint_audit_report(pack_root: Path) -> str | None:
    history_root = pack_root / "eval" / "history"
    if not history_root.exists():
        return None
    candidates: list[tuple[str, Path]] = []
    for report_path in history_root.glob("branch-selection-hint-audit-*/branch-selection-hint-audit-report.json"):
        try:
            payload = _load_object(report_path)
        except Exception:
            continue
        generated_at = payload.get("generated_at")
        if isinstance(generated_at, str):
            candidates.append((generated_at, report_path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return _pack_relative_path(pack_root, candidates[-1][1])


def _recent_branch_hint_activity(pack_root: Path) -> tuple[list[str], list[str]]:
    autonomy_root = pack_root / ".pack-state" / "autonomy-runs"
    if not autonomy_root.exists():
        return [], []
    candidates: list[tuple[str, dict[str, Any]]] = []
    for branch_path in autonomy_root.glob("*/branch-selection.json"):
        try:
            payload = _load_object(branch_path)
        except Exception:
            continue
        recorded_at = payload.get("recorded_at")
        if not isinstance(recorded_at, str):
            continue
        candidates.append((recorded_at, payload))
    candidates.sort(key=lambda item: item[0], reverse=True)
    consumed: list[str] = []
    deactivated: list[str] = []
    for _, payload in candidates[:5]:
        for hint_id in payload.get("consumed_hint_ids", []):
            if isinstance(hint_id, str):
                consumed.append(hint_id)
        for hint_id in payload.get("deactivated_hint_ids", []):
            if isinstance(hint_id, str):
                deactivated.append(hint_id)
    return _stable_unique(consumed), _stable_unique(deactivated)


def _operator_hint_status(pack_root: Path) -> dict[str, Any]:
    work_state = _load_object(pack_root / "status/work-state.json")
    raw_hints = work_state.get("branch_selection_hints", [])
    hints = [cast(dict[str, Any], hint) for hint in raw_hints if isinstance(hint, dict)]

    active_hint_ids: list[str] = []
    inactive_hint_ids: list[str] = []
    exhausted_hint_ids: list[str] = []
    cleanup_candidate_hint_ids: list[str] = []
    for hint in hints:
        hint_id = hint.get("hint_id")
        if not isinstance(hint_id, str):
            continue
        remaining_applications = hint.get("remaining_applications")
        if isinstance(remaining_applications, int) and remaining_applications <= 0:
            exhausted_hint_ids.append(hint_id)
        if _hint_is_active(hint):
            active_hint_ids.append(hint_id)
        else:
            inactive_hint_ids.append(hint_id)
        if hint.get("active") is False and isinstance(remaining_applications, int) and remaining_applications <= 0:
            cleanup_candidate_hint_ids.append(hint_id)

    recent_consumed_hint_ids, recent_deactivated_hint_ids = _recent_branch_hint_activity(pack_root)
    return {
        "hint_count": len(hints),
        "active_hint_ids": _stable_unique(active_hint_ids),
        "inactive_hint_ids": _stable_unique(inactive_hint_ids),
        "exhausted_hint_ids": _stable_unique(exhausted_hint_ids),
        "cleanup_candidate_hint_ids": _stable_unique(cleanup_candidate_hint_ids),
        "recent_consumed_hint_ids": recent_consumed_hint_ids,
        "recent_deactivated_hint_ids": recent_deactivated_hint_ids,
        "latest_audit_report_path": _latest_hint_audit_report(pack_root),
    }


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
    return f"readiness-eval-{pack_id}-{token}-{timestamp_token()}"


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
    factory_root: Path,
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
    updated_readiness["ready_for_deployment"] = False
    if updated_readiness.get("readiness_state") == "ready_for_deploy":
        updated_readiness["readiness_state"] = "in_progress"
    updated_readiness["operator_hint_status"] = _operator_hint_status(pack_root)

    _validate_payload(factory_root, "readiness.schema.json", updated_readiness, label="readiness")
    write_json(pack_root / READINESS_PATH, updated_readiness)

    return {
        "status": "completed",
        "mode": "validation-only",
        "pack_id": pack_id,
        "eval_run_id": eval_run_id,
        "evidence_paths": [relative_path(factory_root, Path(validation_evidence))],
        "readiness_path": relative_path(factory_root, pack_root / READINESS_PATH),
        "eval_latest_index_path": relative_path(factory_root, pack_root / EVAL_LATEST_INDEX_PATH),
        "ready_for_deployment": False,
    }


def _run_benchmark_only(
    *,
    factory_root: Path,
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
    for gate_id in mandatory_gate_ids:
        gate = _gate_by_id(readiness, gate_id)
        if gate.get("status") == "waived":
            continue
        if gate_id not in {_gate_id(benchmark_id) for benchmark_id in expected_benchmark_ids}:
            raise ValueError(f"mandatory benchmark gate `{gate_id}` is not represented in eval/latest/index.json")

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
    # eval/latest v1 cannot encode `waived`, so waived benchmark evidence is represented
    # there as terminal artifact-backed `pass` while readiness preserves the waived gate.
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
        if gate_id == VALIDATION_GATE_ID:
            continue
        if gate.get("mandatory") is not True:
            continue
        if not isinstance(gate_id, str):
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
    updated_readiness["operator_hint_status"] = _operator_hint_status(pack_root)

    _validate_payload(factory_root, "eval-latest-index.schema.json", updated_eval_latest, label="eval-latest-index")
    _validate_payload(factory_root, "readiness.schema.json", updated_readiness, label="readiness")
    write_json(pack_root / EVAL_LATEST_INDEX_PATH, updated_eval_latest)
    write_json(pack_root / READINESS_PATH, updated_readiness)

    return {
        "status": "completed",
        "mode": "benchmark-only",
        "pack_id": pack_id,
        "eval_run_id": eval_run_id,
        "evidence_paths": [relative_path(factory_root, Path(benchmark_evidence))],
        "readiness_path": relative_path(factory_root, pack_root / READINESS_PATH),
        "eval_latest_index_path": relative_path(factory_root, pack_root / EVAL_LATEST_INDEX_PATH),
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

    factory_root = _discover_factory_root(pack_root)
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
            factory_root=factory_root,
            pack_root=pack_root,
            manifest=manifest,
            readiness=readiness,
            eval_run_id=resolved_eval_run_id,
        )
    else:
        payload = _run_benchmark_only(
            factory_root=factory_root,
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
            pack_root=_resolve_pack_root(args.pack_root),
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
