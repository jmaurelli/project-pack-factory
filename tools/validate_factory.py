#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    load_json,
    path_is_relative_to,
    resolve_factory_root,
    validate_json_document,
    validate_schema_file,
)


SCHEMA_BY_RELATIVE_PATH = {
    "pack.json": "pack.schema.json",
    "status/lifecycle.json": "lifecycle.schema.json",
    "status/readiness.json": "readiness.schema.json",
    "status/deployment.json": "deployment.schema.json",
    "status/retirement.json": "retirement.schema.json",
    "lineage/source-template.json": "source-template.schema.json",
    "benchmarks/active-set.json": "benchmark-active-set.schema.json",
    "eval/latest/index.json": "eval-latest-index.schema.json",
}
AUTONOMY_SCHEMA_BY_CONTRACT_KEY = {
    "project_objective_file": "project-objective.schema.json",
    "task_backlog_file": "task-backlog.schema.json",
    "work_state_file": "work-state.schema.json",
}
AUTONOMY_CONTRACT_KEYS = tuple(AUTONOMY_SCHEMA_BY_CONTRACT_KEY.keys()) + ("tasks_dir",)
PORTABLE_RUNTIME_HELPER_CONTRACT_KEYS = (
    "portable_runtime_tools_dir",
    "portable_runtime_schemas_dir",
    "portable_runtime_helper_manifest",
)
PORTABLE_RUNTIME_HELPER_MANIFEST_SCHEMA = "portable-runtime-helper-manifest.schema.json"
REQUIRED_PORTABLE_RUNTIME_TOOL_PATHS = {
    ".packfactory-runtime/tools/factory_ops.py",
    ".packfactory-runtime/tools/run_build_pack_readiness_eval.py",
    ".packfactory-runtime/tools/record_autonomy_run.py",
}
REQUIRED_PORTABLE_RUNTIME_SCHEMA_PATHS = {
    ".packfactory-runtime/schemas/portable-runtime-helper-manifest.schema.json",
    ".packfactory-runtime/schemas/readiness.schema.json",
    ".packfactory-runtime/schemas/eval-latest-index.schema.json",
    ".packfactory-runtime/schemas/autonomy-loop-event.schema.json",
    ".packfactory-runtime/schemas/autonomy-run-summary.schema.json",
}
EXPECTED_PORTABLE_STARTER_COMMANDS = {
    "run_build_pack_validation": "python3 .packfactory-runtime/tools/run_build_pack_readiness_eval.py --pack-root . --mode validation-only --invoked-by autonomous-loop",
    "run_inherited_benchmarks": "python3 .packfactory-runtime/tools/run_build_pack_readiness_eval.py --pack-root . --mode benchmark-only --invoked-by autonomous-loop",
}
FINAL_TASK_STATUSES = {"completed", "escalated", "cancelled"}
ACTIVE_TASK_REQUIRED_AUTONOMY_STATES = {
    "actively_building",
    "blocked",
}

PACK_ROOTS = ("templates", "build-packs")
DEPLOYMENT_ENVIRONMENTS = ("testing", "staging", "production")
VALIDATION_GATE_ID = "validate_build_pack_contract"
EVAL_LATEST_INDEX_PATH = "eval/latest/index.json"
FACTORY_MEMORY_POINTER_PATH = Path(".pack-state/agent-memory/latest-memory.json")
AGENTS_PATH = Path("AGENTS.md")
README_PATH = Path("README.md")
AUTONOMY_OPS_NOTE_PATH = Path("docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md")
AUTONOMY_STATE_BRIEF_PATH = Path("docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md")
AUTONOMY_PLANNING_LIST_PATH = Path("docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md")
MATERIALIZE_BUILD_PACK_TOOL_PATH = Path("tools/materialize_build_pack.py")
TOOL_COMMAND_PATTERN = re.compile(r"`python3 tools/([^`\s]+\.py)\b")


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return payload


def _load_registry_map(path: Path) -> dict[str, dict[str, Any]]:
    payload = _load_object(path)
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError(f"{path}: entries must be an array")
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: registry entries must be objects")
        pack_id = entry.get("pack_id")
        if not isinstance(pack_id, str):
            raise ValueError(f"{path}: registry entry missing string pack_id")
        result[pack_id] = entry
    return result


def _iter_pack_roots(factory_root: Path) -> list[Path]:
    results: list[Path] = []
    for root_name in PACK_ROOTS:
        root = factory_root / root_name
        if not root.exists():
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "pack.json").exists():
                results.append(child)
    return results


def _validate_contract_paths(pack_root: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    contract = manifest.get("directory_contract")
    if not isinstance(contract, dict):
        errors.append(f"{pack_root / 'pack.json'}: directory_contract must be an object")
        return
    for key, value in contract.items():
        if value is None or not isinstance(value, str):
            continue
        target = pack_root / value
        if key == "local_state_dir" and not target.exists():
            continue
        if not target.exists():
            errors.append(f"{pack_root}: directory_contract.{key} points to missing path `{value}`")


def _gate_id(benchmark_id: str) -> str:
    return benchmark_id.replace("-", "_")


def _parse_json_text(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str):
        return None
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _benchmark_results_from_artifact(payload: dict[str, Any]) -> list[dict[str, Any]]:
    stdout_payload = _parse_json_text(payload.get("stdout"))
    results: list[dict[str, Any]] = []
    if stdout_payload is not None:
        stdout_results = stdout_payload.get("benchmark_results")
        if isinstance(stdout_results, list):
            results.extend(result for result in stdout_results if isinstance(result, dict))
        elif isinstance(stdout_payload.get("benchmark_id"), str):
            results.append(stdout_payload)
        return results

    benchmark_results = payload.get("benchmark_results")
    if isinstance(benchmark_results, list):
        results.extend(result for result in benchmark_results if isinstance(result, dict))
    elif isinstance(payload.get("benchmark_id"), str):
        results.append(payload)
    return results


def _load_object_if_present(path: Path, errors: list[str], *, label: str) -> dict[str, Any] | None:
    if not path.exists():
        errors.append(f"{path}: {label} is missing")
        return None
    try:
        return _load_object(path)
    except ValueError as exc:
        errors.append(str(exc))
        return None


def _load_text_if_present(path: Path, errors: list[str], *, label: str) -> str | None:
    if not path.exists():
        errors.append(f"{path}: {label} is missing")
        return None
    return path.read_text(encoding="utf-8")


def _extract_tool_script_names(text: str) -> set[str]:
    return {match.group(1) for match in TOOL_COMMAND_PATTERN.finditer(text)}


def _validate_instruction_surface_sync(factory_root: Path, errors: list[str]) -> None:
    agents_text = _load_text_if_present(factory_root / AGENTS_PATH, errors, label="root instruction surface")
    readme_text = _load_text_if_present(factory_root / README_PATH, errors, label="root overview surface")
    ops_note_text = _load_text_if_present(factory_root / AUTONOMY_OPS_NOTE_PATH, errors, label="autonomy operations note")
    state_brief_text = _load_text_if_present(factory_root / AUTONOMY_STATE_BRIEF_PATH, errors, label="autonomy state brief")
    planning_list_text = _load_text_if_present(factory_root / AUTONOMY_PLANNING_LIST_PATH, errors, label="autonomy planning list")
    materializer_text = _load_text_if_present(factory_root / MATERIALIZE_BUILD_PACK_TOOL_PATH, errors, label="build-pack materializer")
    if any(text is None for text in (agents_text, readme_text, ops_note_text, state_brief_text, planning_list_text, materializer_text)):
        return

    assert agents_text is not None
    assert readme_text is not None
    assert ops_note_text is not None
    assert state_brief_text is not None
    assert planning_list_text is not None
    assert materializer_text is not None

    ops_tool_scripts = _extract_tool_script_names(ops_note_text)
    for relative_path, text in ((AGENTS_PATH, agents_text), (README_PATH, readme_text)):
        root_scripts = _extract_tool_script_names(text)
        missing_scripts = sorted(ops_tool_scripts - root_scripts)
        if missing_scripts:
            errors.append(
                f"{factory_root / relative_path}: operator tool inventory is missing autonomy workflow commands present in the operations note: {', '.join(missing_scripts)}"
            )

    required_markers_by_path: dict[Path, tuple[str, ...]] = {
        AGENTS_PATH: (
            "PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md",
            "remote Codex session management",
            "raw stdout/stderr",
        ),
        README_PATH: (
            "PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md",
            "Remote Session Compliance",
            "raw stdout/stderr",
        ),
        AUTONOMY_OPS_NOTE_PATH: (
            "Remote Session Compliance",
            "tools/import_external_runtime_evidence.py",
            "raw stdout/stderr",
        ),
        AUTONOMY_STATE_BRIEF_PATH: (
            "json-health-checker-startup-compliance-rehearsal-build-pack-v1",
            "config-drift-autonomy-transfer-build-pack-v1",
            "managed PackFactory remote-session path",
        ),
        AUTONOMY_PLANNING_LIST_PATH: (
            "Instruction-surface drift follow-up",
            "json-health-checker-startup-compliance-build-pack-v1",
            "[x] PackFactory instruction and startup compliance review.",
        ),
        MATERIALIZE_BUILD_PACK_TOOL_PATH: (
            "status/readiness.json.operator_hint_status",
            "status/work-state.json.branch_selection_hints",
            "remote Codex session management",
            "tools/import_external_runtime_evidence.py",
            "raw remote stdout/stderr",
        ),
    }
    loaded_text_by_path = {
        AGENTS_PATH: agents_text,
        README_PATH: readme_text,
        AUTONOMY_OPS_NOTE_PATH: ops_note_text,
        AUTONOMY_STATE_BRIEF_PATH: state_brief_text,
        AUTONOMY_PLANNING_LIST_PATH: planning_list_text,
        MATERIALIZE_BUILD_PACK_TOOL_PATH: materializer_text,
    }
    for relative_path, markers in required_markers_by_path.items():
        text = loaded_text_by_path[relative_path]
        for marker in markers:
            if marker not in text:
                errors.append(f"{factory_root / relative_path}: instruction-surface drift detected; missing marker `{marker}`")


def _extract_benchmark_artifact_result(payload: dict[str, Any], benchmark_id: str) -> dict[str, Any] | None:
    for result in _benchmark_results_from_artifact(payload):
        if result.get("benchmark_id") == benchmark_id:
            return result
    return None


def collect_build_pack_evidence_integrity_errors(pack_root: Path) -> list[str]:
    readiness = _load_object(pack_root / "status/readiness.json")
    errors: list[str] = []
    _validate_build_pack_evidence_integrity(pack_root, readiness, errors)
    return errors


def _validate_build_pack_evidence_integrity(
    pack_root: Path,
    readiness: dict[str, Any],
    errors: list[str],
) -> None:
    active_set = _load_object_if_present(
        pack_root / "benchmarks/active-set.json",
        errors,
        label="benchmark active set required for evidence integrity validation",
    )
    eval_latest = _load_object_if_present(
        pack_root / EVAL_LATEST_INDEX_PATH,
        errors,
        label="latest eval index required for evidence integrity validation",
    )
    if active_set is None or eval_latest is None:
        return

    active_benchmarks = active_set.get("active_benchmarks", [])
    benchmark_id_by_gate_id = {
        _gate_id(str(benchmark.get("benchmark_id"))): str(benchmark.get("benchmark_id"))
        for benchmark in active_benchmarks
        if isinstance(benchmark, dict) and isinstance(benchmark.get("benchmark_id"), str)
    }

    benchmark_results = eval_latest.get("benchmark_results", [])
    result_by_benchmark_id = {
        str(result.get("benchmark_id")): result
        for result in benchmark_results
        if isinstance(result, dict) and isinstance(result.get("benchmark_id"), str)
    }

    for result in benchmark_results:
        if not isinstance(result, dict):
            continue
        benchmark_id = result.get("benchmark_id")
        status = result.get("status")
        latest_run_id = result.get("latest_run_id")
        run_artifact_path = result.get("run_artifact_path")
        summary_artifact_path = result.get("summary_artifact_path")
        if not all(isinstance(value, str) for value in (benchmark_id, status, latest_run_id, run_artifact_path, summary_artifact_path)):
            continue

        run_path = pack_root / run_artifact_path
        if not run_path.exists():
            errors.append(f"{run_path}: benchmark run artifact referenced by eval/latest/index.json is missing")
            continue

        summary_path = pack_root / summary_artifact_path
        if not summary_path.exists():
            errors.append(f"{summary_path}: benchmark summary artifact referenced by eval/latest/index.json is missing")

        if status == "not_run":
            continue

        expected_prefix = f"eval/history/{latest_run_id}/"
        if not run_artifact_path.startswith(expected_prefix):
            errors.append(
                f"{pack_root / EVAL_LATEST_INDEX_PATH}: benchmark `{benchmark_id}` run_artifact_path must begin with `{expected_prefix}`"
            )
        if not (
            summary_artifact_path.startswith(expected_prefix)
            or summary_artifact_path.startswith("eval/latest/")
        ):
            errors.append(
                f"{pack_root / EVAL_LATEST_INDEX_PATH}: benchmark `{benchmark_id}` summary_artifact_path must point at the same run or an eval/latest summary"
            )

        artifact = _load_object_if_present(
            run_path,
            errors,
            label=f"benchmark run artifact for `{benchmark_id}`",
        )
        if artifact is None:
            continue
        artifact_result = _extract_benchmark_artifact_result(artifact, benchmark_id)
        if artifact_result is None:
            errors.append(
                f"{run_path}: benchmark run artifact does not report benchmark_id `{benchmark_id}`"
            )
            continue
        if artifact_result.get("status") != status:
            errors.append(
                f"{run_path}: benchmark `{benchmark_id}` status must match eval/latest/index.json"
            )

    for gate in readiness.get("required_gates", []):
        if not isinstance(gate, dict):
            continue
        gate_id = gate.get("gate_id")
        status = gate.get("status")
        evidence_paths = gate.get("evidence_paths", [])
        if not isinstance(gate_id, str) or not isinstance(status, str) or not isinstance(evidence_paths, list):
            continue
        if status == "not_run":
            continue

        if gate_id == VALIDATION_GATE_ID:
            for evidence_path in evidence_paths:
                if not isinstance(evidence_path, str):
                    continue
                if not evidence_path.endswith("validation-result.json"):
                    errors.append(
                        f"{pack_root / 'status/readiness.json'}: validation gate `{gate_id}` must point to validation-result.json evidence"
                    )
                    continue
                evidence_file = pack_root / evidence_path
                artifact = _load_object_if_present(
                    evidence_file,
                    errors,
                    label=f"validation artifact for `{gate_id}`",
                )
                if artifact is None:
                    continue
                if artifact.get("build_pack_id") != pack_root.name:
                    errors.append(f"{evidence_file}: build_pack_id must equal `{pack_root.name}`")
                if artifact.get("gate_id") != gate_id:
                    errors.append(f"{evidence_file}: gate_id must match `{gate_id}`")
                if artifact.get("status") != status:
                    errors.append(f"{evidence_file}: status must match readiness gate `{gate_id}`")
            continue

        benchmark_id = benchmark_id_by_gate_id.get(gate_id)
        if benchmark_id is None:
            continue
        if evidence_paths != [EVAL_LATEST_INDEX_PATH]:
            errors.append(
                f"{pack_root / 'status/readiness.json'}: benchmark gate `{gate_id}` must point to `{EVAL_LATEST_INDEX_PATH}`"
            )
        result = result_by_benchmark_id.get(benchmark_id)
        if result is None:
            errors.append(
                f"{pack_root / 'status/readiness.json'}: benchmark gate `{gate_id}` is missing matching eval/latest benchmark result `{benchmark_id}`"
            )
            continue
        if status != "waived" and result.get("status") != status:
            errors.append(
                f"{pack_root / 'status/readiness.json'}: benchmark gate `{gate_id}` status must match eval/latest benchmark `{benchmark_id}`"
            )


def _validate_pack_documents(pack_root: Path, manifest: dict[str, Any], errors: list[str]) -> None:
    schema_root = pack_root.parents[1] / "docs/specs/project-pack-factory/schemas"
    for relative_path, schema_name in SCHEMA_BY_RELATIVE_PATH.items():
        document_path = pack_root / relative_path
        if not document_path.exists():
            if relative_path == "lineage/source-template.json" and manifest.get("pack_kind") != "build_pack":
                continue
            errors.append(f"{document_path}: required pack document is missing")
            continue
        errors.extend(validate_json_document(document_path, schema_root / schema_name))

    _validate_autonomy_documents(pack_root, manifest, schema_root, errors)
    _validate_portable_runtime_helpers(pack_root, manifest, schema_root, errors)

    retirement_state = _load_object(pack_root / "status/retirement.json")
    report_path = retirement_state.get("retirement_report_path")
    if isinstance(report_path, str):
        errors.extend(
            validate_json_document(
                pack_root / report_path,
                schema_root / "retirement-report.schema.json",
            )
        )


def _autonomy_contract(contract: dict[str, Any]) -> dict[str, str] | None:
    present_values = {
        key: value
        for key, value in ((key, contract.get(key)) for key in AUTONOMY_CONTRACT_KEYS)
        if value is not None
    }
    if not present_values:
        return None
    return {
        key: value
        for key, value in present_values.items()
        if isinstance(value, str)
    }


def _validate_autonomy_documents(
    pack_root: Path,
    manifest: dict[str, Any],
    schema_root: Path,
    errors: list[str],
) -> None:
    contract = manifest.get("directory_contract")
    if not isinstance(contract, dict):
        return

    autonomy_contract = _autonomy_contract(contract)
    if autonomy_contract is None:
        return

    for key in AUTONOMY_CONTRACT_KEYS:
        value = contract.get(key)
        if not isinstance(value, str):
            errors.append(
                f"{pack_root / 'pack.json'}: directory_contract.{key} must be a string when autonomy handoff files are declared"
            )

    task_backlog: dict[str, Any] | None = None
    work_state: dict[str, Any] | None = None
    for key, schema_name in AUTONOMY_SCHEMA_BY_CONTRACT_KEY.items():
        relative_path = contract.get(key)
        if not isinstance(relative_path, str):
            continue
        document_path = pack_root / relative_path
        if not document_path.exists():
            continue
        errors.extend(validate_json_document(document_path, schema_root / schema_name))
        document = _load_object(document_path)
        if key == "task_backlog_file":
            task_backlog = document
        elif key == "work_state_file":
            work_state = document

    if task_backlog is None or work_state is None:
        return

    tasks = task_backlog.get("tasks", [])
    if not isinstance(tasks, list):
        return
    task_by_id = {
        str(task.get("task_id")): task
        for task in tasks
        if isinstance(task, dict) and isinstance(task.get("task_id"), str)
    }

    active_task_id = work_state.get("active_task_id")
    autonomy_state = work_state.get("autonomy_state")
    if autonomy_state in ACTIVE_TASK_REQUIRED_AUTONOMY_STATES:
        if not isinstance(active_task_id, str) or active_task_id not in task_by_id:
            errors.append(
                f"{pack_root / contract['work_state_file']}: active_task_id must reference a real task when autonomy_state is active"
            )

    next_task_id = work_state.get("next_recommended_task_id")
    if isinstance(next_task_id, str):
        next_task = task_by_id.get(next_task_id)
        if next_task is None:
            errors.append(
                f"{pack_root / contract['work_state_file']}: next_recommended_task_id must reference a real task"
            )
        else:
            next_status = next_task.get("status")
            if next_status in FINAL_TASK_STATUSES:
                errors.append(
                    f"{pack_root / contract['work_state_file']}: next_recommended_task_id must reference a non-final task"
                )
            if next_status == "blocked" or next_task_id in set(work_state.get("blocked_task_ids", [])):
                errors.append(
                    f"{pack_root / contract['work_state_file']}: next_recommended_task_id must not reference a blocked task"
                )

    blocked_task_ids = work_state.get("blocked_task_ids", [])
    if not isinstance(blocked_task_ids, list):
        return
    if isinstance(active_task_id, str):
        active_task = task_by_id.get(active_task_id)
        if active_task is not None and active_task.get("status") == "blocked":
            errors.append(
                f"{pack_root / contract['work_state_file']}: blocked tasks must not also be marked as active"
            )
        if active_task_id in blocked_task_ids:
            errors.append(
                f"{pack_root / contract['work_state_file']}: blocked_task_ids must not include the active task"
            )


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_paths(pack_root: Path, root: Path) -> list[str]:
    return sorted(path.relative_to(pack_root).as_posix() for path in _iter_files(root))


def _resolve_contract_path(pack_root: Path, relative_value: str) -> Path:
    if Path(relative_value).is_absolute():
        raise ValueError("directory_contract paths must be relative")
    return (pack_root / relative_value).resolve()


def _validate_portable_runtime_helpers(
    pack_root: Path,
    manifest: dict[str, Any],
    schema_root: Path,
    errors: list[str],
) -> None:
    contract = manifest.get("directory_contract")
    if not isinstance(contract, dict):
        return

    portable_contract = {
        key: contract.get(key)
        for key in PORTABLE_RUNTIME_HELPER_CONTRACT_KEYS
        if contract.get(key) is not None
    }
    if not portable_contract:
        return

    for key in PORTABLE_RUNTIME_HELPER_CONTRACT_KEYS:
        value = contract.get(key)
        if not isinstance(value, str):
            errors.append(
                f"{pack_root / 'pack.json'}: directory_contract.{key} must be a string when portable runtime helpers are declared"
            )

    tools_relative = contract.get("portable_runtime_tools_dir")
    schemas_relative = contract.get("portable_runtime_schemas_dir")
    manifest_relative = contract.get("portable_runtime_helper_manifest")
    if not all(isinstance(value, str) for value in (tools_relative, schemas_relative, manifest_relative)):
        return

    try:
        tools_dir = _resolve_contract_path(pack_root, tools_relative)
        schemas_dir = _resolve_contract_path(pack_root, schemas_relative)
        helper_manifest_path = _resolve_contract_path(pack_root, manifest_relative)
    except ValueError as exc:
        errors.append(f"{pack_root / 'pack.json'}: {exc}")
        return
    for resolved_path, key in (
        (tools_dir, "portable_runtime_tools_dir"),
        (schemas_dir, "portable_runtime_schemas_dir"),
        (helper_manifest_path, "portable_runtime_helper_manifest"),
    ):
        if not path_is_relative_to(resolved_path, pack_root):
            errors.append(f"{pack_root / 'pack.json'}: directory_contract.{key} must stay under the pack root")
            return
    if not (tools_dir.exists() and schemas_dir.exists() and helper_manifest_path.exists()):
        return

    errors.extend(
        validate_json_document(
            helper_manifest_path,
            schema_root / PORTABLE_RUNTIME_HELPER_MANIFEST_SCHEMA,
        )
    )

    helper_manifest = _load_object_if_present(
        helper_manifest_path,
        errors,
        label="portable runtime helper manifest",
    )
    if helper_manifest is None:
        return

    declared_tools = helper_manifest.get("tools", [])
    declared_schemas = helper_manifest.get("schemas", [])
    helper_entries = helper_manifest.get("helper_entries", [])

    actual_tools = _relative_paths(pack_root, tools_dir)
    actual_schemas = _relative_paths(pack_root, schemas_dir)
    actual_helper_files = sorted({*actual_tools, *actual_schemas})

    if not isinstance(declared_tools, list) or not all(isinstance(path, str) for path in declared_tools):
        errors.append(f"{helper_manifest_path}: tools must be an array of strings")
        declared_tools = []
    elif len(set(declared_tools)) != len(declared_tools):
        errors.append(f"{helper_manifest_path}: tools must not contain duplicate paths")
    if not isinstance(declared_schemas, list) or not all(isinstance(path, str) for path in declared_schemas):
        errors.append(f"{helper_manifest_path}: schemas must be an array of strings")
        declared_schemas = []
    elif len(set(declared_schemas)) != len(declared_schemas):
        errors.append(f"{helper_manifest_path}: schemas must not contain duplicate paths")
    if not isinstance(helper_entries, list):
        errors.append(f"{helper_manifest_path}: helper_entries must be an array")
        helper_entries = []
    elif len({entry.get('relative_path') for entry in helper_entries if isinstance(entry, dict)}) != len(helper_entries):
        errors.append(f"{helper_manifest_path}: helper_entries must not contain duplicate relative_path values")

    declared_tool_set = set(declared_tools)
    actual_tool_set = set(actual_tools)
    missing_tool_declarations = sorted(actual_tool_set - declared_tool_set)
    stale_tool_declarations = sorted(declared_tool_set - actual_tool_set)
    if missing_tool_declarations:
        errors.append(
            f"{helper_manifest_path}: tools must enumerate the actual helper files present in `{tools_relative}`; missing `{', '.join(missing_tool_declarations)}`"
        )
    if stale_tool_declarations:
        errors.append(
            f"{helper_manifest_path}: tools references missing helper files: {', '.join(stale_tool_declarations)}"
        )

    declared_schema_set = set(declared_schemas)
    actual_schema_set = set(actual_schemas)
    missing_schema_declarations = sorted(actual_schema_set - declared_schema_set)
    stale_schema_declarations = sorted(declared_schema_set - actual_schema_set)
    if missing_schema_declarations:
        errors.append(
            f"{helper_manifest_path}: schemas must enumerate the actual helper files present in `{schemas_relative}`; missing `{', '.join(missing_schema_declarations)}`"
        )
    if stale_schema_declarations:
        errors.append(
            f"{helper_manifest_path}: schemas references missing helper files: {', '.join(stale_schema_declarations)}"
        )
    missing_required_tools = sorted(REQUIRED_PORTABLE_RUNTIME_TOOL_PATHS - actual_tool_set)
    if missing_required_tools:
        errors.append(
            f"{helper_manifest_path}: portable runtime helper tools are missing required files: {', '.join(missing_required_tools)}"
        )
    missing_required_schemas = sorted(REQUIRED_PORTABLE_RUNTIME_SCHEMA_PATHS - actual_schema_set)
    if missing_required_schemas:
        errors.append(
            f"{helper_manifest_path}: portable runtime helper schemas are missing required files: {', '.join(missing_required_schemas)}"
        )
    for schema_relative in sorted(actual_schema_set):
        errors.extend(validate_schema_file(pack_root / schema_relative))

    declared_helper_entries: dict[str, dict[str, Any]] = {}
    for entry in helper_entries:
        if not isinstance(entry, dict):
            errors.append(f"{helper_manifest_path}: helper_entries must contain objects")
            continue
        relative_path = entry.get("relative_path")
        if not isinstance(relative_path, str):
            errors.append(f"{helper_manifest_path}: helper_entries[].relative_path must be a string")
            continue
        entry_path = pack_root / relative_path
        resolved_entry_path = entry_path.resolve()
        if not path_is_relative_to(resolved_entry_path, pack_root):
            errors.append(f"{helper_manifest_path}: helper_entries[].relative_path must stay under the pack root")
            continue
        if not entry_path.exists():
            errors.append(f"{entry_path}: helper entry referenced by manifest is missing")
            continue
        if not (
            path_is_relative_to(resolved_entry_path, tools_dir)
            or path_is_relative_to(resolved_entry_path, schemas_dir)
        ):
            errors.append(
                f"{helper_manifest_path}: helper_entries[].relative_path must reference the declared portable helper tool or schema directories"
            )
            continue
        declared_helper_entries[relative_path] = entry

    declared_helper_entry_paths = set(declared_helper_entries)
    actual_helper_path_set = set(actual_helper_files)
    missing_helper_entries = sorted(actual_helper_path_set - declared_helper_entry_paths)
    stale_helper_entries = sorted(declared_helper_entry_paths - actual_helper_path_set)
    if missing_helper_entries:
        errors.append(
            f"{helper_manifest_path}: helper_entries must enumerate the actual helper files present; missing `{', '.join(missing_helper_entries)}`"
        )
    if stale_helper_entries:
        errors.append(
            f"{helper_manifest_path}: helper_entries references missing helper files: {', '.join(stale_helper_entries)}"
        )

    for relative_path, entry in sorted(declared_helper_entries.items()):
        entry_path = pack_root / relative_path
        sha256 = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if not isinstance(sha256, str) or not isinstance(size_bytes, int):
            continue
        actual_sha256 = _sha256_file(entry_path)
        actual_size = entry_path.stat().st_size
        if sha256 != actual_sha256:
            errors.append(f"{entry_path}: helper entry sha256 must match the file contents")
        if size_bytes != actual_size:
            errors.append(f"{entry_path}: helper entry size_bytes must match the file size")

    for helper_path in _iter_files(tools_dir):
        try:
            contents = helper_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"{helper_path}: portable helper files must be UTF-8 text")
            continue
        if "../../tools/" in contents:
            errors.append(
                f"{helper_path}: portable helper files must not contain factory-relative fallback references like `../../tools/`"
            )

    task_backlog_path = contract.get("task_backlog_file")
    if not isinstance(task_backlog_path, str):
        return
    task_backlog = _load_object_if_present(
        pack_root / task_backlog_path,
        errors,
        label="task backlog required for portable helper validation",
    )
    if task_backlog is None:
        return
    tasks = task_backlog.get("tasks", [])
    if not isinstance(tasks, list):
        return
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = task.get("task_id")
        validation_commands = task.get("validation_commands", [])
        if not isinstance(validation_commands, list):
            errors.append(f"{pack_root / task_backlog_path}: validation_commands must be an array when portable helpers are declared")
            continue
        for command in validation_commands:
            if isinstance(command, str) and "../../tools/" in command:
                errors.append(
                    f"{pack_root / task_backlog_path}: validation_commands must not retain factory-relative helper references like `../../tools/` when portable helpers are declared"
                )
                break
        expected_command = EXPECTED_PORTABLE_STARTER_COMMANDS.get(task_id)
        if expected_command is not None and validation_commands[:1] != [expected_command]:
            errors.append(
                f"{pack_root / task_backlog_path}: `{task_id}` must start with the canonical portable helper command"
            )


def _state_snapshot(pack_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    lifecycle = _load_object(pack_root / "status/lifecycle.json")
    readiness = _load_object(pack_root / "status/readiness.json")
    deployment = _load_object(pack_root / "status/deployment.json")
    retirement = _load_object(pack_root / "status/retirement.json")
    return lifecycle, readiness, deployment, retirement


def _relative_path(factory_root: Path, path: Path) -> str:
    return path.relative_to(factory_root).as_posix()


def _iter_build_pack_roots(factory_root: Path) -> list[Path]:
    return [pack_root for pack_root in _iter_pack_roots(factory_root) if pack_root.parent.name == "build-packs"]


def _build_registry_environment_claims(build_registry: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    claims = {environment: set() for environment in DEPLOYMENT_ENVIRONMENTS}
    for pack_id, entry in build_registry.items():
        for environment in DEPLOYMENT_ENVIRONMENTS:
            expected_pointer = f"deployments/{environment}/{pack_id}.json"
            if entry.get("deployment_state") == environment or entry.get("deployment_pointer") == expected_pointer:
                claims[environment].add(pack_id)
    return claims


def _build_pack_environment_claims(build_pack_roots: dict[str, Path]) -> dict[str, set[str]]:
    claims = {environment: set() for environment in DEPLOYMENT_ENVIRONMENTS}
    for pack_id, pack_root in build_pack_roots.items():
        deployment = _load_object(pack_root / "status/deployment.json")
        for environment in DEPLOYMENT_ENVIRONMENTS:
            expected_pointer = f"deployments/{environment}/{pack_id}.json"
            if (
                deployment.get("deployment_state") == environment
                or deployment.get("active_environment") == environment
                or deployment.get("deployment_pointer_path") == expected_pointer
            ):
                claims[environment].add(pack_id)
    return claims


def _validate_environment_assignments(
    factory_root: Path,
    build_registry: dict[str, dict[str, Any]],
    promotion_log: dict[str, Any],
    errors: list[str],
) -> None:
    schema_root = factory_root / "docs/specs/project-pack-factory/schemas"
    pointer_schema = schema_root / "deployment-pointer.schema.json"
    promotion_report_schema = schema_root / "promotion-report.schema.json"
    rehearsal_report_schema = schema_root / "multi-hop-autonomy-rehearsal-report.schema.json"
    build_pack_roots = {pack_root.name: pack_root for pack_root in _iter_build_pack_roots(factory_root)}
    registry_claims = _build_registry_environment_claims(build_registry)
    pack_claims = _build_pack_environment_claims(build_pack_roots)
    promotion_events = promotion_log.get("events", [])
    if not isinstance(promotion_events, list):
        promotion_events = []

    for environment in DEPLOYMENT_ENVIRONMENTS:
        deployment_dir = factory_root / "deployments" / environment
        pointers = sorted(deployment_dir.glob("*.json")) if deployment_dir.exists() else []
        pointer_names = ", ".join(pointer.name for pointer in pointers)

        if len(pointers) > 1:
            errors.append(
                f"{deployment_dir}: environment `{environment}` has multiple active deployment pointers: {pointer_names}"
            )

        if not pointers:
            if registry_claims[environment]:
                claimed_pack_ids = ", ".join(sorted(registry_claims[environment]))
                errors.append(
                    f"{factory_root / 'registry/build-packs.json'}: environment `{environment}` has no deployment pointer but registry claims `{claimed_pack_ids}`"
                )
            if pack_claims[environment]:
                claimed_pack_ids = ", ".join(sorted(pack_claims[environment]))
                errors.append(
                    f"{deployment_dir}: environment `{environment}` has no deployment pointer but pack-local deployment files claim `{claimed_pack_ids}`"
                )
            continue

        for pointer in pointers:
            errors.extend(validate_json_document(pointer, pointer_schema))

        pointer_path = pointers[0]
        pointer = _load_object(pointer_path)
        pointer_relative = _relative_path(factory_root, pointer_path)
        pack_id = pointer.get("pack_id")
        if not isinstance(pack_id, str):
            errors.append(f"{pointer_path}: pack_id must be a string")
            continue

        expected_claims = {pack_id}
        if registry_claims[environment] != expected_claims:
            claimed_pack_ids = ", ".join(sorted(registry_claims[environment])) or "none"
            errors.append(
                f"{factory_root / 'registry/build-packs.json'}: environment `{environment}` registry claims must resolve to `{pack_id}`, found `{claimed_pack_ids}`"
            )
        if pack_claims[environment] != expected_claims:
            claimed_pack_ids = ", ".join(sorted(pack_claims[environment])) or "none"
            errors.append(
                f"{factory_root / 'build-packs'}: environment `{environment}` pack-local claims must resolve to `{pack_id}`, found `{claimed_pack_ids}`"
            )

        registry_entry = build_registry.get(pack_id)
        if registry_entry is None:
            errors.append(f"{factory_root / 'registry/build-packs.json'}: active pointer references unknown build pack `{pack_id}`")
            continue
        if registry_entry.get("active") is not True:
            errors.append(f"{factory_root / 'registry/build-packs.json'}: active pointer pack `{pack_id}` must set active=true")
        if registry_entry.get("retirement_state") != "active":
            errors.append(f"{factory_root / 'registry/build-packs.json'}: active pointer pack `{pack_id}` must set retirement_state=active")

        pack_root = build_pack_roots.get(pack_id)
        if pack_root is None:
            errors.append(f"{factory_root / 'build-packs'}: active pointer references missing pack directory for `{pack_id}`")
            continue

        expected_pack_root = f"build-packs/{pack_id}"
        if pointer.get("environment") != environment:
            errors.append(f"{pointer_path}: environment must equal `{environment}`")
        if pointer.get("pack_root") != expected_pack_root:
            errors.append(f"{pointer_path}: pack_root must equal `{expected_pack_root}`")

        source_deployment_file = pointer.get("source_deployment_file")
        expected_source_deployment_file = f"{expected_pack_root}/status/deployment.json"
        if source_deployment_file != expected_source_deployment_file:
            errors.append(f"{pointer_path}: source_deployment_file must equal `{expected_source_deployment_file}`")
        elif not (factory_root / expected_source_deployment_file).exists():
            errors.append(f"{factory_root / expected_source_deployment_file}: source_deployment_file referenced by pointer is missing")

        deployment = _load_object(pack_root / "status/deployment.json")
        if deployment.get("deployment_state") != environment:
            errors.append(f"{pack_root / 'status/deployment.json'}: active pointer pack must set deployment_state={environment}")
        if deployment.get("active_environment") != environment:
            errors.append(f"{pack_root / 'status/deployment.json'}: active pointer pack must set active_environment={environment}")
        if deployment.get("deployment_pointer_path") != pointer_relative:
            errors.append(f"{pack_root / 'status/deployment.json'}: deployment_pointer_path must equal `{pointer_relative}`")
        if deployment.get("active_release_id") != pointer.get("active_release_id"):
            errors.append(f"{pack_root / 'status/deployment.json'}: active_release_id must match `{pointer_relative}`")
        if deployment.get("active_release_path") != pointer.get("active_release_path"):
            errors.append(f"{pack_root / 'status/deployment.json'}: active_release_path must match `{pointer_relative}`")

        if registry_entry.get("deployment_state") != environment:
            errors.append(f"{factory_root / 'registry/build-packs.json'}: `{pack_id}` deployment_state must equal `{environment}`")
        if registry_entry.get("deployment_pointer") != pointer_relative:
            errors.append(f"{factory_root / 'registry/build-packs.json'}: `{pack_id}` deployment_pointer must equal `{pointer_relative}`")
        if registry_entry.get("active_release_id") != pointer.get("active_release_id"):
            errors.append(f"{factory_root / 'registry/build-packs.json'}: `{pack_id}` active_release_id must match `{pointer_relative}`")

        report_relative = pointer.get("promotion_evidence_ref")
        if not isinstance(report_relative, str):
            errors.append(f"{pointer_path}: promotion_evidence_ref must be a string")
            continue

        report_path = pack_root / report_relative
        if not report_path.exists():
            errors.append(f"{report_path}: promotion report referenced by active pointer is missing")
        else:
            errors.extend(validate_json_document(report_path, promotion_report_schema))
            report = _load_object(report_path)
            if report.get("build_pack_id") != pack_id:
                errors.append(f"{report_path}: build_pack_id must match `{pack_id}`")
            if report.get("target_environment") != environment:
                errors.append(f"{report_path}: target_environment must equal `{environment}`")
            if report.get("release_id") != pointer.get("active_release_id"):
                errors.append(f"{report_path}: release_id must match `{pointer_relative}`")
            if report.get("promotion_id") != pointer.get("deployment_transaction_id"):
                errors.append(f"{report_path}: promotion_id must match `{pointer_relative}`")
            post_state = report.get("post_promotion_state", {})
            if post_state.get("active_environment") != environment:
                errors.append(f"{report_path}: post_promotion_state.active_environment must equal `{environment}`")
            if post_state.get("active_release_path") != pointer.get("active_release_path"):
                errors.append(f"{report_path}: post_promotion_state.active_release_path must match `{pointer_relative}`")
            if post_state.get("deployment_pointer_path") != pointer_relative:
                errors.append(f"{report_path}: post_promotion_state.deployment_pointer_path must equal `{pointer_relative}`")
            rehearsal_evidence = report.get("autonomy_rehearsal_evidence")
            if isinstance(rehearsal_evidence, dict):
                rehearsal_relative = rehearsal_evidence.get("report_path")
                if not isinstance(rehearsal_relative, str):
                    errors.append(f"{report_path}: autonomy_rehearsal_evidence.report_path must be a string")
                else:
                    rehearsal_path = factory_root / rehearsal_relative
                    if not rehearsal_path.exists():
                        errors.append(f"{rehearsal_path}: autonomy rehearsal report referenced by promotion report is missing")
                    else:
                        errors.extend(validate_json_document(rehearsal_path, rehearsal_report_schema))
                        rehearsal_report = _load_object(rehearsal_path)
                        if rehearsal_report.get("target_build_pack_id") != pack_id:
                            errors.append(f"{rehearsal_path}: target_build_pack_id must match `{pack_id}`")

        matching_events = [
            event
            for event in promotion_events
            if isinstance(event, dict)
            and event.get("event_type") == "promoted"
            and event.get("build_pack_id") == pack_id
            and event.get("target_environment") == environment
            and event.get("promotion_report_path") == report_relative
        ]
        if not matching_events:
            errors.append(
                f"{factory_root / 'registry/promotion-log.json'}: active pointer `{pointer_relative}` is missing a matching promoted event"
            )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_factory_root_autonomy_memory(factory_root: Path, errors: list[str]) -> None:
    pointer_path = factory_root / FACTORY_MEMORY_POINTER_PATH
    if not pointer_path.exists():
        return

    schema_root = factory_root / "docs/specs/project-pack-factory/schemas"
    pointer_schema = schema_root / "factory-autonomy-memory-pointer.schema.json"
    memory_schema = schema_root / "factory-autonomy-memory.schema.json"

    errors.extend(validate_json_document(pointer_path, pointer_schema))
    pointer = _load_object(pointer_path)

    selected_memory_path = pointer.get("selected_memory_path")
    if not isinstance(selected_memory_path, str):
        errors.append(f"{pointer_path}: selected_memory_path must be a string")
        return

    resolved_memory_path = (factory_root / selected_memory_path).resolve()
    if not path_is_relative_to(resolved_memory_path, factory_root.resolve()):
        errors.append(f"{pointer_path}: selected_memory_path must stay within the factory root")
        return
    if not resolved_memory_path.exists():
        errors.append(f"{resolved_memory_path}: selected factory autonomy memory is missing")
        return

    errors.extend(validate_json_document(resolved_memory_path, memory_schema))
    memory = _load_object(resolved_memory_path)

    if memory.get("memory_id") != pointer.get("selected_memory_id"):
        errors.append(f"{pointer_path}: selected_memory_id must match the selected factory autonomy memory")
    if memory.get("generated_at") != pointer.get("selected_generated_at"):
        errors.append(f"{pointer_path}: selected_generated_at must match the selected factory autonomy memory")
    if _sha256(resolved_memory_path) != pointer.get("selected_memory_sha256"):
        errors.append(f"{pointer_path}: selected_memory_sha256 must match the selected factory autonomy memory")
    if memory.get("factory_root") != str(factory_root):
        errors.append(f"{resolved_memory_path}: factory_root must equal the validated factory root")


def _check_active_registry(entry: dict[str, Any], registry_path: Path, errors: list[str]) -> None:
    if entry.get("active") is not True:
        errors.append(f"{registry_path}: active pack `{entry.get('pack_id')}` must set active=true")
    if entry.get("retirement_state") != "active":
        errors.append(f"{registry_path}: active pack `{entry.get('pack_id')}` must set retirement_state=active")
    if entry.get("retired_at") is not None:
        errors.append(f"{registry_path}: active pack `{entry.get('pack_id')}` must set retired_at=null")
    if entry.get("retirement_file") != "status/retirement.json":
        errors.append(
            f"{registry_path}: active pack `{entry.get('pack_id')}` must set retirement_file=status/retirement.json"
        )


def _check_retired_registry(entry: dict[str, Any], retired_at: str, registry_path: Path, errors: list[str]) -> None:
    if entry.get("active") is not False:
        errors.append(f"{registry_path}: retired pack `{entry.get('pack_id')}` must set active=false")
    if entry.get("retirement_state") != "retired":
        errors.append(f"{registry_path}: retired pack `{entry.get('pack_id')}` must set retirement_state=retired")
    if entry.get("retired_at") != retired_at:
        errors.append(f"{registry_path}: retired pack `{entry.get('pack_id')}` retired_at does not match status/retirement.json")
    if entry.get("retirement_file") != "status/retirement.json":
        errors.append(
            f"{registry_path}: retired pack `{entry.get('pack_id')}` must set retirement_file=status/retirement.json"
        )


def _validate_pack_state(
    factory_root: Path,
    pack_root: Path,
    templates_registry: dict[str, dict[str, Any]],
    build_registry: dict[str, dict[str, Any]],
    promotion_log: dict[str, Any],
    errors: list[str],
) -> None:
    manifest = _load_object(pack_root / "pack.json")
    pack_id = manifest.get("pack_id")
    pack_kind = manifest.get("pack_kind")
    lifecycle, readiness, deployment, retirement = _state_snapshot(pack_root)
    _validate_contract_paths(pack_root, manifest, errors)
    _validate_pack_documents(pack_root, manifest, errors)

    registry_path = factory_root / ("registry/templates.json" if pack_kind == "template_pack" else "registry/build-packs.json")
    registry_map = templates_registry if pack_kind == "template_pack" else build_registry
    entry = registry_map.get(str(pack_id))
    if entry is None:
        errors.append(f"{registry_path}: missing registry entry for `{pack_id}`")
        return

    pack_root_relative = f"{pack_root.parent.name}/{pack_root.name}"
    if entry.get("pack_root") != pack_root_relative:
        errors.append(f"{registry_path}: `{pack_id}` pack_root must equal `{pack_root_relative}`")
    latest_eval_index = entry.get("latest_eval_index")
    if isinstance(latest_eval_index, str) and not (factory_root / latest_eval_index).exists():
        errors.append(f"{registry_path}: `{pack_id}` latest_eval_index points to missing path `{latest_eval_index}`")

    retirement_state = retirement.get("retirement_state")
    if retirement.get("pack_id") != pack_id:
        errors.append(f"{pack_root / 'status/retirement.json'}: pack_id does not match pack.json")
    if retirement.get("pack_kind") != pack_kind:
        errors.append(f"{pack_root / 'status/retirement.json'}: pack_kind does not match pack.json")

    superseded_by = retirement.get("superseded_by_pack_id")
    if isinstance(superseded_by, str):
        if superseded_by == pack_id:
            errors.append(f"{pack_root / 'status/retirement.json'}: superseded_by_pack_id must not equal pack_id")
        if superseded_by not in templates_registry and superseded_by not in build_registry:
            errors.append(f"{pack_root / 'status/retirement.json'}: superseded_by_pack_id `{superseded_by}` is not registered")

    if retirement_state == "active":
        if retirement.get("retired_at") is not None:
            errors.append(f"{pack_root / 'status/retirement.json'}: active pack must set retired_at=null")
        if retirement.get("retirement_report_path") is not None:
            errors.append(f"{pack_root / 'status/retirement.json'}: active pack must set retirement_report_path=null")
        if retirement.get("removed_deployment_pointer_paths") != []:
            errors.append(f"{pack_root / 'status/retirement.json'}: active pack must not list removed deployment pointers")
        if pack_kind == "build_pack":
            _validate_build_pack_evidence_integrity(pack_root, readiness, errors)
        _check_active_registry(entry, registry_path, errors)
        return

    retired_at = retirement.get("retired_at")
    if lifecycle.get("lifecycle_stage") != "retired":
        errors.append(f"{pack_root / 'status/lifecycle.json'}: retired pack must set lifecycle_stage=retired")
    if lifecycle.get("promotion_target") != "none":
        errors.append(f"{pack_root / 'status/lifecycle.json'}: retired pack must set promotion_target=none")
    if readiness.get("readiness_state") != "retired":
        errors.append(f"{pack_root / 'status/readiness.json'}: retired pack must set readiness_state=retired")
    if readiness.get("ready_for_deployment") is not False:
        errors.append(f"{pack_root / 'status/readiness.json'}: retired pack must set ready_for_deployment=false")
    _check_retired_registry(entry, str(retired_at), registry_path, errors)

    report_relative = retirement.get("retirement_report_path")
    if not isinstance(report_relative, str):
        errors.append(f"{pack_root / 'status/retirement.json'}: retired pack must set retirement_report_path")
        return
    report_path = pack_root / report_relative
    if not report_path.exists():
        errors.append(f"{report_path}: retirement report is missing")
        return
    report = _load_object(report_path)

    if report.get("generated_at") != retired_at:
        errors.append(f"{report_path}: generated_at must match status/retirement.json retired_at")
    if report.get("pack_id") != pack_id:
        errors.append(f"{report_path}: pack_id does not match pack.json")
    if report.get("pack_kind") != pack_kind:
        errors.append(f"{report_path}: pack_kind does not match pack.json")
    if report.get("pack_root") != pack_root_relative:
        errors.append(f"{report_path}: pack_root must equal `{pack_root_relative}`")

    post_state = report.get("post_retirement_state", {})
    if post_state.get("lifecycle_stage") != "retired":
        errors.append(f"{report_path}: post_retirement_state.lifecycle_stage must be retired")
    if post_state.get("readiness_state") != "retired":
        errors.append(f"{report_path}: post_retirement_state.readiness_state must be retired")
    if post_state.get("deployment_state") != "not_deployed":
        errors.append(f"{report_path}: post_retirement_state.deployment_state must be not_deployed")
    if post_state.get("active_environment") != "none":
        errors.append(f"{report_path}: post_retirement_state.active_environment must be none")
    if post_state.get("deployment_pointer_path") is not None:
        errors.append(f"{report_path}: post_retirement_state.deployment_pointer_path must be null")
    if post_state.get("retirement_state") != "retired":
        errors.append(f"{report_path}: post_retirement_state.retirement_state must be retired")

    actions = report.get("actions", [])
    if not actions or actions[-1].get("action_id") != "write_retirement_report":
        errors.append(f"{report_path}: write_retirement_report must be the last recorded action")
    for evidence_path in report.get("evidence_paths", []):
        if not isinstance(evidence_path, str) or not (factory_root / evidence_path).exists():
            errors.append(f"{report_path}: evidence path `{evidence_path}` does not exist")

    matching_events = [
        event
        for event in promotion_log.get("events", [])
        if isinstance(event, dict)
        and event.get("event_type") == "retired"
        and event.get("retired_pack_id") == pack_id
        and event.get("retirement_report_path") == report_relative
    ]
    if not matching_events:
        errors.append(f"{factory_root / 'registry/promotion-log.json'}: missing retired event for `{pack_id}` with report `{report_relative}`")

    if pack_kind == "build_pack":
        if deployment.get("deployment_state") != "not_deployed":
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must set deployment_state=not_deployed")
        if deployment.get("active_environment") != "none":
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must set active_environment=none")
        if deployment.get("active_release_id") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear active_release_id")
        if deployment.get("active_release_path") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear active_release_path")
        if deployment.get("deployment_pointer_path") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear deployment_pointer_path")
        if deployment.get("deployment_transaction_id") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear deployment_transaction_id")
        if deployment.get("projection_state") != "not_required":
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must set projection_state=not_required")
        if deployment.get("last_promoted_at") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear last_promoted_at")
        if deployment.get("last_verified_at") is not None:
            errors.append(f"{pack_root / 'status/deployment.json'}: retired build pack must clear last_verified_at")
        for environment in DEPLOYMENT_ENVIRONMENTS:
            pointer_path = factory_root / "deployments" / environment / f"{pack_id}.json"
            if pointer_path.exists():
                errors.append(f"{pointer_path}: retired build pack must not keep active deployment pointers")


def _validate_template_creation_events(
    factory_root: Path,
    templates_registry: dict[str, dict[str, Any]],
    promotion_log: dict[str, Any],
    errors: list[str],
) -> None:
    schema_root = factory_root / "docs/specs/project-pack-factory/schemas"
    events = promotion_log.get("events", [])
    if not isinstance(events, list):
        errors.append(f"{factory_root / 'registry/promotion-log.json'}: events must be an array")
        return

    for event in events:
        if not isinstance(event, dict) or event.get("event_type") != "template_created":
            continue
        template_pack_id = event.get("template_pack_id")
        creation_id = event.get("creation_id")
        report_relative = event.get("template_creation_report_path")
        if not isinstance(template_pack_id, str):
            errors.append(f"{factory_root / 'registry/promotion-log.json'}: template_created event must include template_pack_id")
            continue
        if not isinstance(creation_id, str):
            errors.append(f"{factory_root / 'registry/promotion-log.json'}: template_created event for `{template_pack_id}` must include creation_id")
            continue
        if not isinstance(report_relative, str):
            errors.append(f"{factory_root / 'registry/promotion-log.json'}: template_created event for `{template_pack_id}` must include template_creation_report_path")
            continue

        entry = templates_registry.get(template_pack_id)
        if entry is None:
            errors.append(f"{factory_root / 'registry/promotion-log.json'}: template_created event references unknown template `{template_pack_id}`")
            continue
        pack_root_relative = entry.get("pack_root")
        if not isinstance(pack_root_relative, str):
            errors.append(f"{factory_root / 'registry/templates.json'}: template `{template_pack_id}` is missing pack_root")
            continue
        report_path = factory_root / pack_root_relative / report_relative
        if not report_path.exists():
            errors.append(f"{report_path}: template creation report referenced by promotion log is missing")
            continue

        errors.extend(
            validate_json_document(
                report_path,
                schema_root / "template-creation-report.schema.json",
            )
        )
        report = _load_object(report_path)
        if report.get("creation_id") != creation_id:
            errors.append(f"{report_path}: creation_id does not match registry/promotion-log.json")
        if report.get("template_pack_id") != template_pack_id:
            errors.append(f"{report_path}: template_pack_id does not match registry/promotion-log.json")
        artifact_paths = report.get("artifact_paths", {})
        if artifact_paths.get("template_root") != pack_root_relative:
            errors.append(f"{report_path}: artifact_paths.template_root must equal `{pack_root_relative}`")
        expected_report_artifact = f"{pack_root_relative}/{report_relative}"
        if artifact_paths.get("creation_report") != expected_report_artifact:
            errors.append(f"{report_path}: artifact_paths.creation_report must equal `{expected_report_artifact}`")
        if entry.get("lifecycle_stage") != "maintained":
            errors.append(f"{factory_root / 'registry/templates.json'}: created template `{template_pack_id}` must set lifecycle_stage=maintained")
        if entry.get("ready_for_deployment") is not False:
            errors.append(f"{factory_root / 'registry/templates.json'}: created template `{template_pack_id}` must set ready_for_deployment=false")
        active_set = _load_object(factory_root / pack_root_relative / "benchmarks/active-set.json")
        active_benchmark_ids = [
            benchmark.get("benchmark_id")
            for benchmark in active_set.get("active_benchmarks", [])
            if isinstance(benchmark, dict)
        ]
        if entry.get("active_benchmark_ids") != active_benchmark_ids:
            errors.append(f"{factory_root / 'registry/templates.json'}: created template `{template_pack_id}` active_benchmark_ids must match benchmarks/active-set.json")
        notes = entry.get("notes")
        if not isinstance(notes, list) or not any(isinstance(note, str) and creation_id in note for note in notes):
            errors.append(f"{factory_root / 'registry/templates.json'}: created template `{template_pack_id}` notes must include the creation_id")
        factory_mutations = report.get("factory_mutations", {})
        if factory_mutations.get("registry_updated") is not True:
            errors.append(f"{report_path}: factory_mutations.registry_updated must be true")
        if factory_mutations.get("operation_log_updated") is not True:
            errors.append(f"{report_path}: factory_mutations.operation_log_updated must be true")
        if event.get("status") == "completed" and factory_mutations.get("post_write_factory_validation") != "pass":
            errors.append(f"{report_path}: factory_mutations.post_write_factory_validation must be pass for completed template_created events")


def validate_factory(factory_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    schema_root = factory_root / "docs/specs/project-pack-factory/schemas"
    schema_files = sorted(schema_root.glob("*.schema.json"))
    for schema_file in schema_files:
        errors.extend(validate_schema_file(schema_file))

    registry_templates = _load_registry_map(factory_root / "registry/templates.json")
    registry_builds = _load_registry_map(factory_root / "registry/build-packs.json")
    promotion_log = _load_object(factory_root / "registry/promotion-log.json")

    for pack_root in _iter_pack_roots(factory_root):
        _validate_pack_state(factory_root, pack_root, registry_templates, registry_builds, promotion_log, errors)

    _validate_template_creation_events(factory_root, registry_templates, promotion_log, errors)
    _validate_environment_assignments(factory_root, registry_builds, promotion_log, errors)
    _validate_factory_root_autonomy_memory(factory_root, errors)
    _validate_instruction_surface_sync(factory_root, errors)

    known_pack_ids = {pack_root.name for pack_root in _iter_pack_roots(factory_root)}
    for registry_path, registry_map in (
        (factory_root / "registry/templates.json", registry_templates),
        (factory_root / "registry/build-packs.json", registry_builds),
    ):
        for pack_id in registry_map:
            if pack_id not in known_pack_ids:
                errors.append(f"{registry_path}: registry entry `{pack_id}` does not have a matching pack directory")

    for environment in DEPLOYMENT_ENVIRONMENTS:
        deployment_dir = factory_root / "deployments" / environment
        if not deployment_dir.exists():
            errors.append(f"{deployment_dir}: deployment directory is missing")

    return {
        "factory_root": str(factory_root),
        "schema_files_checked": len(schema_files),
        "pack_count": len(_iter_pack_roots(factory_root)),
        "error_count": len(errors),
        "errors": errors,
        "valid": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate PackFactory state against PackFactory contracts.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory root.")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    args = parser.parse_args()

    result = validate_factory(resolve_factory_root(args.factory_root))
    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if result["valid"]:
            print(f"VALID: {result['pack_count']} packs and {result['schema_files_checked']} schemas passed")
        else:
            print(f"INVALID: {result['error_count']} errors")
            for error in result["errors"]:
                print(f"- {error}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
