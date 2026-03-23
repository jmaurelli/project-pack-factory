from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Mapping, cast


PORTABLE_RUNTIME_CONTRACT_KEYS: Final[dict[str, str]] = {
    "portable_runtime_tools_dir": ".packfactory-runtime/tools",
    "portable_runtime_schemas_dir": ".packfactory-runtime/schemas",
    "portable_runtime_helper_manifest": ".packfactory-runtime/manifest.json",
}
SUPPORTED_SCHEMA_NAMES: Final[frozenset[str]] = frozenset(
    {
        "readiness.schema.json",
        "eval-latest-index.schema.json",
        "autonomy-loop-event.schema.json",
        "autonomy-run-summary.schema.json",
        "portable-runtime-helper-manifest.schema.json",
    }
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(dump_json(data))
        temp_path = Path(handle.name)
    temp_path.replace(path)


def read_now() -> datetime:
    fixed_now = os.environ.get("PROJECT_PACK_FACTORY_FIXED_NOW") or os.environ.get("PACK_FACTORY_FIXED_NOW")
    if fixed_now:
        value = fixed_now.strip()
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0)
    return datetime.now(timezone.utc).replace(microsecond=0)


def isoformat_z(moment: datetime | None = None) -> str:
    current = read_now() if moment is None else moment.astimezone(timezone.utc).replace(microsecond=0)
    return current.isoformat().replace("+00:00", "Z")


def timestamp_token(moment: datetime | None = None) -> str:
    current = read_now() if moment is None else moment.astimezone(timezone.utc).replace(microsecond=0)
    return current.strftime("%Y%m%d") + "t" + current.strftime("%H%M%S") + "z"


def relative_path(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_pack_root(pack_root: str | Path) -> Path:
    root = Path(pack_root).expanduser().resolve()
    if not root.is_absolute():
        raise ValueError("pack_root must resolve to an absolute path")
    return root


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def load_pack_manifest(pack_root: Path) -> dict[str, Any]:
    manifest = _load_object(pack_root / "pack.json")
    if manifest.get("pack_kind") != "build_pack":
        raise ValueError("portable runtime helpers only support build_pack manifests")
    return manifest


def pack_directory_contract(pack_root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    contract = manifest.get("directory_contract")
    if not isinstance(contract, dict):
        raise ValueError(f"{pack_root / 'pack.json'}: directory_contract must be an object")
    return cast(dict[str, Any], contract)


def _resolve_within_pack(pack_root: Path, relative_value: str, *, label: str) -> Path:
    if not relative_value or Path(relative_value).is_absolute():
        raise ValueError(f"{label} must be a non-empty relative path")
    resolved = (pack_root / relative_value).resolve()
    try:
        resolved.relative_to(pack_root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay within pack_root") from exc
    return resolved


def runtime_contract_path(pack_root: Path, manifest: dict[str, Any], key: str) -> Path:
    contract = pack_directory_contract(pack_root, manifest)
    relative_value = contract.get(key)
    if not isinstance(relative_value, str):
        raise ValueError(f"{pack_root / 'pack.json'}: directory_contract.{key} must be a string")
    resolved = _resolve_within_pack(pack_root, relative_value, label=f"directory_contract.{key}")
    if key != "portable_runtime_helper_manifest" and not resolved.is_dir():
        raise ValueError(f"{resolved}: expected a directory for {key}")
    if key == "portable_runtime_helper_manifest" and not resolved.is_file():
        raise ValueError(f"{resolved}: expected a file for {key}")
    return resolved


def runtime_schema_path(pack_root: Path, manifest: dict[str, Any], schema_name: str) -> Path:
    if schema_name not in SUPPORTED_SCHEMA_NAMES:
        raise ValueError(f"unsupported portable runtime schema: {schema_name}")
    schema_root = runtime_contract_path(pack_root, manifest, "portable_runtime_schemas_dir")
    schema_path = _resolve_within_pack(
        pack_root,
        f"{relative_path(pack_root, schema_root)}/{schema_name}",
        label=f"portable runtime schema `{schema_name}`",
    )
    if not schema_path.is_file():
        raise ValueError(f"{schema_path}: required portable runtime schema is missing")
    return schema_path


def _require_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _require_bool(payload: Mapping[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _require_int(payload: Mapping[str, Any], key: str, *, minimum: int = 0) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value < minimum:
        raise ValueError(f"{key} must be an integer >= {minimum}")
    return value


def _require_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be an array")
    return value


def _validate_readiness(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != "pack-readiness/v2":
        raise ValueError("readiness payload must set schema_version=pack-readiness/v2")
    _require_string(payload, "pack_id")
    if payload.get("pack_kind") != "build_pack":
        raise ValueError("readiness payload must set pack_kind=build_pack")
    if payload.get("readiness_state") not in {
        "blocked",
        "in_progress",
        "ready_for_review",
        "ready_for_deploy",
        "deployed",
        "retired",
    }:
        raise ValueError("readiness_state must be a supported readiness value")
    _require_bool(payload, "ready_for_deployment")
    _require_string(payload, "last_evaluated_at")
    for key in ("blocking_issues", "recommended_next_actions"):
        if not all(isinstance(item, str) and item for item in _require_list(payload, key)):
            raise ValueError(f"{key} entries must be non-empty strings")
    gates = _require_list(payload, "required_gates")
    if not gates:
        raise ValueError("required_gates must include at least one gate")
    for gate in gates:
        if not isinstance(gate, dict):
            raise ValueError("required_gates entries must be objects")
        _require_string(gate, "gate_id")
        _require_bool(gate, "mandatory")
        if gate.get("status") not in {"not_run", "in_progress", "pass", "fail", "waived"}:
            raise ValueError("required_gates[*].status must be a supported readiness gate status")
        _require_string(gate, "summary")
        last_run_at = gate.get("last_run_at")
        if last_run_at is not None and (not isinstance(last_run_at, str) or not last_run_at):
            raise ValueError("required_gates[*].last_run_at must be null or a non-empty string")
        evidence_paths = _require_list(gate, "evidence_paths")
        if not all(isinstance(item, str) and item for item in evidence_paths):
            raise ValueError("required_gates[*].evidence_paths must contain only non-empty strings")


def _validate_eval_latest_index(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != "pack-eval-index/v1":
        raise ValueError("eval/latest payload must set schema_version=pack-eval-index/v1")
    _require_string(payload, "pack_id")
    if payload.get("pack_kind") != "build_pack":
        raise ValueError("eval/latest payload must set pack_kind=build_pack")
    _require_string(payload, "updated_at")
    benchmark_results = _require_list(payload, "benchmark_results")
    if not benchmark_results:
        raise ValueError("benchmark_results must include at least one result")
    for result in benchmark_results:
        if not isinstance(result, dict):
            raise ValueError("benchmark_results entries must be objects")
        _require_string(result, "benchmark_id")
        if result.get("status") not in {"pass", "fail", "in_progress", "not_run"}:
            raise ValueError("benchmark_results[*].status must be a supported eval status")
        _require_string(result, "latest_run_id")
        run_artifact_path = _require_string(result, "run_artifact_path")
        summary_artifact_path = _require_string(result, "summary_artifact_path")
        if not run_artifact_path.startswith("eval/history/") or not run_artifact_path.endswith(".json"):
            raise ValueError("benchmark_results[*].run_artifact_path must point into eval/history/*.json")
        if not summary_artifact_path.endswith(".json") or not (
            summary_artifact_path.startswith("eval/history/") or summary_artifact_path.startswith("eval/latest/")
        ):
            raise ValueError("benchmark_results[*].summary_artifact_path must point into eval/history/ or eval/latest/")


def _validate_canonical_snapshot(snapshot: Any, *, label: str) -> None:
    if not isinstance(snapshot, dict):
        raise ValueError(f"{label} must be an object")
    for key in ("active_task_id", "next_recommended_task_id"):
        value = snapshot.get(key)
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"{label}.{key} must be null or a non-empty string")
    _require_string(snapshot, "readiness_state")
    _require_bool(snapshot, "ready_for_deployment")
    for key in ("gate_statuses", "eval_result_statuses"):
        mapping = snapshot.get(key)
        if not isinstance(mapping, dict):
            raise ValueError(f"{label}.{key} must be an object")
        for entry_key, entry_value in mapping.items():
            if not isinstance(entry_key, str) or not entry_key or not isinstance(entry_value, str) or not entry_value:
                raise ValueError(f"{label}.{key} must map non-empty strings to non-empty strings")


def _validate_autonomy_loop_event(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != "autonomy-loop-event/v1":
        raise ValueError("autonomy event payload must set schema_version=autonomy-loop-event/v1")
    _require_string(payload, "run_id")
    _require_string(payload, "recorded_at")
    _require_int(payload, "step_index", minimum=1)
    if payload.get("event_type") not in {
        "run_started",
        "task_selected",
        "command_completed",
        "state_updated",
        "escalation_raised",
        "run_stopped",
        "run_completed",
    }:
        raise ValueError("event_type must be a supported autonomy loop event")
    for key in ("active_task_id", "next_recommended_task_id"):
        value = payload.get(key)
        if value is not None and (not isinstance(value, str) or not value):
            raise ValueError(f"{key} must be null or a non-empty string")
    if payload.get("decision_source") not in {"canonical_only", "canonical_plus_memory", "memory_only"}:
        raise ValueError("decision_source must be a supported decision source")
    if payload.get("memory_state") not in {"not_used", "used_and_consistent", "used_and_stale", "used_and_incomplete"}:
        raise ValueError("memory_state must be a supported memory state")
    for key in ("commands_attempted", "notes"):
        if not all(isinstance(item, str) and item for item in _require_list(payload, key)):
            raise ValueError(f"{key} entries must be non-empty strings")
    _require_string(payload, "outcome")
    _require_string(payload, "readiness_state_before")
    _require_string(payload, "readiness_state_after")
    stop_reason = payload.get("stop_reason")
    if stop_reason is not None and (not isinstance(stop_reason, str) or not stop_reason):
        raise ValueError("stop_reason must be null or a non-empty string")
    evidence_paths = payload.get("evidence_paths", [])
    if not isinstance(evidence_paths, list) or not all(isinstance(item, str) and item for item in evidence_paths):
        raise ValueError("evidence_paths must contain only non-empty strings")
    if "baseline_snapshot" in payload:
        _validate_canonical_snapshot(payload.get("baseline_snapshot"), label="baseline_snapshot")
    _validate_canonical_snapshot(payload.get("canonical_snapshot_after"), label="canonical_snapshot_after")


def _validate_autonomy_run_summary(payload: Mapping[str, Any]) -> None:
    if payload.get("schema_version") != "autonomy-run-summary/v1":
        raise ValueError("autonomy run summary must set schema_version=autonomy-run-summary/v1")
    _require_string(payload, "run_id")
    _require_string(payload, "pack_id")
    _require_string(payload, "started_at")
    _require_string(payload, "ended_at")
    _validate_canonical_snapshot(payload.get("baseline_snapshot"), label="baseline_snapshot")
    _validate_canonical_snapshot(payload.get("final_snapshot"), label="final_snapshot")
    for key in ("step_count", "resume_count", "failed_command_count", "escalation_count"):
        _require_int(payload, key, minimum=0 if key != "step_count" else 1)
    completed_task_ids = _require_list(payload, "completed_task_ids")
    if not all(isinstance(item, str) and item for item in completed_task_ids):
        raise ValueError("completed_task_ids entries must be non-empty strings")
    _require_string(payload, "stop_reason")
    metrics = payload.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be an object")
    _require_string(payload, "operator_summary")
    _require_string(payload, "highest_risk_observation")
    _require_string(payload, "recommended_next_action")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("artifacts must be an object")
    _require_string(artifacts, "loop_events_path")
    _require_string(artifacts, "run_summary_path")
    factory_validation_command = artifacts.get("factory_validation_command")
    if factory_validation_command is not None and (
        not isinstance(factory_validation_command, str) or not factory_validation_command
    ):
        raise ValueError("artifacts.factory_validation_command must be null or a non-empty string")


def validate_named_payload(pack_root: Path, manifest: dict[str, Any], schema_name: str, payload: dict[str, Any]) -> None:
    runtime_schema_path(pack_root, manifest, schema_name)
    if schema_name == "readiness.schema.json":
        _validate_readiness(payload)
        return
    if schema_name == "eval-latest-index.schema.json":
        _validate_eval_latest_index(payload)
        return
    if schema_name == "autonomy-loop-event.schema.json":
        _validate_autonomy_loop_event(payload)
        return
    if schema_name == "autonomy-run-summary.schema.json":
        _validate_autonomy_run_summary(payload)
        return
    if schema_name == "portable-runtime-helper-manifest.schema.json":
        return
    raise ValueError(f"unsupported portable runtime schema: {schema_name}")
