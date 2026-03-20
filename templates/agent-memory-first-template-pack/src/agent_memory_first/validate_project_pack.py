from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any, Final, cast

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled deterministically at runtime
    validator_for = None

REQUIRED_RELATIVE_PATHS: Final[tuple[str, ...]] = (
    "AGENTS.md",
    "README.md",
    "project-context.md",
    "pack.json",
    "pyproject.toml",
    "status/lifecycle.json",
    "status/readiness.json",
    "status/deployment.json",
    "benchmarks/active-set.json",
    "eval/latest/index.json",
    "contracts/agent-memory.schema.json",
    "contracts/agent-memory-reader.schema.json",
    "src/agent_memory_first/__about__.py",
    "src/agent_memory_first/__init__.py",
    "src/agent_memory_first/__main__.py",
    "src/agent_memory_first/constants.py",
    "src/agent_memory_first/cli.py",
    "src/agent_memory_first/agent_memory.py",
    "src/agent_memory_first/agent_memory_benchmark.py",
    "src/agent_memory_first/validate_project_pack.py",
    "tests/test_agent_memory.py",
    "tests/test_agent_memory_cli.py",
    "tests/test_agent_memory_benchmark.py",
    "tests/test_agent_memory_benchmark_cli.py",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _check_schema_file(path: Path) -> list[str]:
    if validator_for is None:
        return ["The `jsonschema` dependency is required to validate schema contracts."]
    schema = _load_json(path)
    if not isinstance(schema, dict):
        return [f"{path}: schema file must contain a JSON object"]
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    return []


def _compare_file_text(left: Path, right: Path) -> bool:
    return left.read_text(encoding="utf-8") == right.read_text(encoding="utf-8")


def _factory_root_for(root: Path) -> Path | None:
    for candidate in (root, *root.parents):
        schema_dir = candidate / "docs" / "specs" / "project-pack-factory" / "schemas"
        if schema_dir.is_dir():
            return candidate
    return None


def _validate_json_document(path: Path, schema_path: Path) -> list[str]:
    if validator_for is None:
        return ["The `jsonschema` dependency is required to validate schema contracts."]
    payload = _load_json(path)
    schema = _load_json(schema_path)
    if not isinstance(payload, dict):
        return [f"{path}: JSON document must contain an object"]
    if not isinstance(schema, dict):
        return [f"{schema_path}: schema file must contain a JSON object"]
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    return [f"{path.relative_to(path.parent.parent.parent)} failed schema validation: {error.message}" for error in validator.iter_errors(payload)]


def _existing_relative_path(root: Path, relative_path: str) -> bool:
    return (root / relative_path).exists()


def _validate_entrypoint_command(command: str, subcommand: str, allowed_options: set[str]) -> str | None:
    tokens = shlex.split(command)
    if subcommand not in tokens:
        return f"entrypoint command does not invoke `{subcommand}`: {command}"
    seen_subcommand = False
    for token in tokens:
        if token == subcommand:
            seen_subcommand = True
            continue
        if not seen_subcommand or not token.startswith("--"):
            continue
        option_name = token.split("=", 1)[0]
        if option_name not in allowed_options:
            return f"entrypoint command uses unsupported option `{option_name}` for `{subcommand}`"
    return None


def validate_project_pack(project_root: str | Path) -> dict[str, object]:
    root = Path(project_root).expanduser().resolve()
    errors: list[str] = []
    validated_paths: list[str] = []
    factory_root = _factory_root_for(root)

    if not root.is_absolute():
        raise ValueError("project_root must resolve to an absolute path")

    for relative_path in REQUIRED_RELATIVE_PATHS:
        candidate = root / relative_path
        if candidate.exists():
            validated_paths.append(relative_path)
        else:
            errors.append(f"missing required path: {relative_path}")

    pack_path = root / "pack.json"
    pack_payload: dict[str, Any] = {}
    if pack_path.exists():
        payload = _load_json(pack_path)
        if isinstance(payload, dict):
            pack_payload = cast(dict[str, Any], payload)
        else:
            errors.append("pack.json must contain a JSON object")

    pack_id = cast(str, pack_payload.get("pack_id", "unknown"))
    pack_kind = cast(str, pack_payload.get("pack_kind", "unknown"))
    if pack_payload:
        entrypoints = cast(dict[str, str], pack_payload.get("entrypoints", {}))
        benchmark_error = _validate_entrypoint_command(
            entrypoints.get("benchmark_command", ""),
            "benchmark-agent-memory",
            {"--fixture-root", "--output-path", "--snapshot-output-path", "--output"},
        )
        if benchmark_error is not None:
            errors.append(benchmark_error)
        validation_error = _validate_entrypoint_command(
            entrypoints.get("validation_command", ""),
            "validate-project-pack",
            {"--project-root", "--output"},
        )
        if validation_error is not None:
            errors.append(validation_error)

    for relative_path in ("status/lifecycle.json", "status/readiness.json", "status/deployment.json"):
        candidate = root / relative_path
        if not candidate.exists():
            continue
        payload = _load_json(candidate)
        if not isinstance(payload, dict):
            errors.append(f"{relative_path} must contain a JSON object")
            continue
        status_payload = cast(dict[str, Any], payload)
        if pack_id != "unknown" and status_payload.get("pack_id") != pack_id:
            errors.append(f"{relative_path} pack_id does not match pack.json")
        if pack_kind != "unknown" and status_payload.get("pack_kind") != pack_kind:
            errors.append(f"{relative_path} pack_kind does not match pack.json")

    schema_dir = None if factory_root is None else factory_root / "docs" / "specs" / "project-pack-factory" / "schemas"
    schema_map = {
        "status/lifecycle.json": "lifecycle.schema.json",
        "status/readiness.json": "readiness.schema.json",
        "status/deployment.json": "deployment.schema.json",
        "benchmarks/active-set.json": "benchmark-active-set.schema.json",
        "eval/latest/index.json": "eval-latest-index.schema.json",
        "lineage/source-template.json": "source-template.schema.json",
    }
    if schema_dir is not None:
        for relative_path, schema_name in schema_map.items():
            candidate = root / relative_path
            schema_path = schema_dir / schema_name
            if not candidate.exists() or not schema_path.exists():
                continue
            try:
                document_errors = _validate_json_document(candidate, schema_path)
            except Exception as exc:  # pragma: no cover - fail closed for runtime validation
                errors.append(f"{relative_path} schema validation failed: {exc}")
            else:
                if document_errors:
                    errors.extend(document_errors)
                else:
                    validated_paths.append(f"schema:{relative_path}")

    root_contract_dir = root / "contracts"
    package_contract_dir = root / "src" / "agent_memory_first" / "contracts"
    for contract_name in ("agent-memory.schema.json", "agent-memory-reader.schema.json"):
        root_contract = root_contract_dir / contract_name
        package_contract = package_contract_dir / contract_name
        if root_contract.exists() and package_contract.exists():
            if not _compare_file_text(root_contract, package_contract):
                errors.append(f"root/package contract mismatch: {contract_name}")
            else:
                validated_paths.append(f"contracts-sync:{contract_name}")
            for candidate in (root_contract, package_contract):
                try:
                    schema_errors = _check_schema_file(candidate)
                except Exception as exc:  # pragma: no cover - fail closed for runtime validation
                    errors.append(f"{candidate.relative_to(root)} schema validation failed: {exc}")
                else:
                    errors.extend(schema_errors)

    active_set_path = root / "benchmarks" / "active-set.json"
    latest_index_path = root / "eval" / "latest" / "index.json"
    if active_set_path.exists() and latest_index_path.exists():
        active_set = _load_json(active_set_path)
        latest_index = _load_json(latest_index_path)
        if isinstance(active_set, dict) and isinstance(latest_index, dict):
            active_benchmarks = cast(list[dict[str, Any]], active_set.get("active_benchmarks", []))
            benchmark_results = cast(list[dict[str, Any]], latest_index.get("benchmark_results", []))
            active_ids = {cast(str, item["benchmark_id"]) for item in active_benchmarks if "benchmark_id" in item}
            result_ids = {cast(str, item["benchmark_id"]) for item in benchmark_results if "benchmark_id" in item}
            missing_result_ids = sorted(active_ids - result_ids)
            if missing_result_ids:
                errors.append(
                    f"eval/latest/index.json is missing active benchmark ids: {', '.join(missing_result_ids)}"
                )
            for benchmark in active_benchmarks:
                declaration_path = cast(str | None, benchmark.get("declaration_path"))
                if declaration_path is not None and not _existing_relative_path(root, declaration_path):
                    errors.append(f"missing benchmark declaration path: {declaration_path}")
            for result in benchmark_results:
                run_artifact_path = cast(str | None, result.get("run_artifact_path"))
                summary_artifact_path = cast(str | None, result.get("summary_artifact_path"))
                if run_artifact_path is not None and not _existing_relative_path(root, run_artifact_path):
                    errors.append(f"missing eval run artifact: {run_artifact_path}")
                if summary_artifact_path is not None and not _existing_relative_path(root, summary_artifact_path):
                    errors.append(f"missing eval summary artifact: {summary_artifact_path}")

    readiness_path = root / "status" / "readiness.json"
    if readiness_path.exists():
        readiness_payload = _load_json(readiness_path)
        if isinstance(readiness_payload, dict):
            required_gates = cast(list[dict[str, Any]], readiness_payload.get("required_gates", []))
            for gate in required_gates:
                for evidence_path in cast(list[str], gate.get("evidence_paths", [])):
                    if not _existing_relative_path(root, evidence_path):
                        errors.append(f"missing readiness evidence path: {evidence_path}")

    return {
        "command": "validate-project-pack",
        "result": "pass" if not errors else "fail",
        "project_root": str(root),
        "pack_id": pack_id,
        "pack_kind": pack_kind,
        "errors": errors,
        "validated_path_count": len(validated_paths),
        "validated_paths": validated_paths,
    }
