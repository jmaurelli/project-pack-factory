from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

try:
    import yaml
except ImportError:  # pragma: no cover - handled at runtime with deterministic output
    yaml = cast(Any, None)

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled at runtime with deterministic output
    validator_for = cast(Any, None)

if __package__ in (None, ""):
    package_src_root = Path(__file__).resolve().parents[2]
    if str(package_src_root) not in sys.path:
        sys.path.insert(0, str(package_src_root))
    from ai_native_package.validators.validate_task_scope import validate_task_scope
else:
    from ..validators.validate_task_scope import validate_task_scope


EXIT_CODES = {
    "complete": 0,
    "blocked": 3,
    "retry": 4,
    "escalate": 5,
    "runtime_error": 2,
}
RESULT_PASS = "pass"
RESULT_FAIL = "fail"
WORKER_RESULT_VALIDATOR = "worker-result-contract"
TASK_SCOPE_VALIDATOR = "validate-task-scope"


def _issue(check: str, message: str, **details: Any) -> dict[str, Any]:
    issue = {"check": check, "message": message}
    for key, value in details.items():
        if value is not None:
            issue[key] = value
    return issue


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _contracts_dir() -> Path:
    return _package_root() / "contracts"


def _schema_paths() -> tuple[Path, Path, Path]:
    contracts_dir = _contracts_dir()
    return (
        contracts_dir / "worker-result.schema.json",
        contracts_dir / "task-record.schema.json",
        contracts_dir / "posttask-decision.schema.json",
    )


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_task_record(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return json.loads(text)


def _json_text(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return _sha256_bytes(text.encode("utf-8"))


def _write_json(path: Path, payload: Any) -> str:
    return _write_text(path, _json_text(payload))


def _file_digest(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _artifact_reference(*, artifact_role: str, reference: Path, content_digest: str) -> dict[str, str]:
    return {
        "artifact_role": artifact_role,
        "reference": str(reference.resolve()),
        "content_digest": content_digest,
    }


def _validator_result_reference(result_path: Path, digest: str) -> dict[str, str]:
    return _artifact_reference(
        artifact_role="validator_result",
        reference=result_path,
        content_digest=digest,
    )


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _decision_identity_digest(task_id: str, worker_attempt: int, decision_path: Path) -> str:
    seed = f"{task_id}\n{worker_attempt}\n{decision_path.resolve()}".encode("utf-8")
    return _sha256_bytes(seed)


def _resolve_artifacts_dir(
    *,
    task_record_path: Path,
    task_id: str,
    worker_attempt: int,
    artifacts_dir: Path | None,
) -> Path:
    if artifacts_dir is not None:
        return artifacts_dir.resolve()
    return task_record_path.resolve().parent / ".posttask" / task_id / f"attempt-{worker_attempt}"


def _format_schema_path(path_segments: Any) -> str:
    parts = [str(segment) for segment in path_segments]
    return ".".join(parts) if parts else "$"


def _schema_errors(
    *,
    instance: Any,
    schema: dict[str, Any],
    check: str,
    label: str,
) -> list[dict[str, Any]]:
    if validator_for is None:
        return [
            _issue(
                check,
                "The `jsonschema` dependency is required to validate machine-readable contracts.",
                source=label,
            )
        ]

    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (_format_schema_path(error.path), error.message),
    )
    return [
        _issue(
            check,
            error.message,
            source=label,
            path=_format_schema_path(error.path),
        )
        for error in errors
    ]


def _load_valid_task_record(task_record_path: Path) -> dict[str, Any]:
    _, task_record_schema_path, _ = _schema_paths()
    task_record_schema = _load_json_file(task_record_schema_path)
    payload = _load_task_record(task_record_path)
    schema_errors = _schema_errors(
        instance=payload,
        schema=task_record_schema,
        check="task_record_schema",
        label="task-record.schema.json",
    )
    if schema_errors:
        raise ValueError(
            "The authoritative task record failed schema validation: "
            + "; ".join(issue["message"] for issue in schema_errors)
        )
    if not isinstance(payload, dict):
        raise ValueError("The authoritative task record must deserialize to a JSON object.")

    task_id = payload.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise ValueError("The authoritative task record must declare a non-empty string `task_id`.")
    return payload


def _load_worker_result_validation(
    *,
    worker_result_path: Path,
    worker_result_schema_path: Path,
) -> tuple[Any, dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "validator": WORKER_RESULT_VALIDATOR,
        "result": RESULT_PASS,
        "errors": errors,
        "warnings": warnings,
        "inputs": {
            "worker_result": str(worker_result_path.resolve()),
            "worker_result_schema": str(worker_result_schema_path.resolve()),
        },
    }

    try:
        worker_result_schema = _load_json_file(worker_result_schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        result["errors"].append(
            _issue(
                "schema_load",
                f"Unable to load the worker-result schema: {exc}",
                source=str(worker_result_schema_path),
            )
        )
        result["result"] = RESULT_FAIL
        return None, result

    try:
        payload = _load_json_file(worker_result_path)
    except OSError as exc:
        result["errors"].append(
            _issue(
                "worker_result_load",
                f"Unable to load the worker-result payload: {exc}",
                source=str(worker_result_path),
            )
        )
        result["result"] = RESULT_FAIL
        return None, result
    except json.JSONDecodeError as exc:
        result["errors"].append(
            _issue(
                "worker_result_load",
                f"Unable to parse the worker-result payload as canonical JSON: {exc}",
                source=str(worker_result_path),
            )
        )
        result["result"] = RESULT_FAIL
        return None, result

    result["errors"].extend(
        _schema_errors(
            instance=payload,
            schema=worker_result_schema,
            check="worker_result_schema",
            label="worker-result.schema.json",
        )
    )
    if result["errors"]:
        result["result"] = RESULT_FAIL
    return payload, result


def _summary(result: dict[str, Any]) -> str:
    return (
        f"result={result['result']}; "
        f"errors={len(result.get('errors', []))}; "
        f"warnings={len(result.get('warnings', []))}"
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _blocking_reasons(
    *,
    worker_result: dict[str, Any] | None,
    worker_contract_result: dict[str, Any],
    scope_result: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    if worker_contract_result["result"] == RESULT_FAIL:
        reasons.extend(
            f"{WORKER_RESULT_VALIDATOR}:{issue['check']}:{issue['message']}"
            for issue in worker_contract_result.get("errors", [])
        )
    if scope_result["result"] == RESULT_FAIL:
        reasons.extend(
            f"{TASK_SCOPE_VALIDATOR}:{issue['check']}:{issue['message']}"
            for issue in scope_result.get("errors", [])
        )
    if isinstance(worker_result, dict) and worker_result.get("status") == "blocked":
        blocked_reason = worker_result.get("blocked_reason")
        if isinstance(blocked_reason, str) and blocked_reason.strip():
            reasons.append(f"worker_result:blocked_reason:{blocked_reason.strip()}")
    return _dedupe(reasons)


def _retry_reason(worker_result: dict[str, Any]) -> str:
    status = str(worker_result["status"])
    return f"worker_result_status_{status}"


def _escalation_reason(worker_result: dict[str, Any]) -> str:
    scope_mismatch = worker_result.get("scope_mismatch")
    if isinstance(scope_mismatch, dict):
        required_file = scope_mismatch.get("required_file")
        smallest_scope_expansion = scope_mismatch.get("smallest_scope_expansion")
        if isinstance(required_file, str) and isinstance(smallest_scope_expansion, str):
            return (
                "worker_scope_mismatch:"
                f"required_file={required_file};"
                f"smallest_scope_expansion={smallest_scope_expansion}"
            )
    return "worker_scope_mismatch"


def _decision_from_results(
    *,
    worker_result: dict[str, Any] | None,
    worker_contract_result: dict[str, Any],
    scope_result: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    extras: dict[str, Any] = {}
    blocking_reasons = _blocking_reasons(
        worker_result=worker_result,
        worker_contract_result=worker_contract_result,
        scope_result=scope_result,
    )
    if blocking_reasons:
        extras["blocking_reasons"] = blocking_reasons
        return "blocked", "blocked", extras

    if not isinstance(worker_result, dict):
        extras["blocking_reasons"] = ["worker_result:missing:Worker result payload was not available."]
        return "blocked", "blocked", extras

    worker_status = worker_result["status"]
    if worker_status == "success":
        return "complete", "completed", extras
    if worker_status == "blocked":
        extras["blocking_reasons"] = ["worker_result:blocked_status:Worker reported blocked status."]
        return "blocked", "blocked", extras
    if worker_status == "scope_mismatch":
        extras["escalation_reason"] = _escalation_reason(worker_result)
        return "escalate", "escalated", extras
    if worker_status in {"failed", "partial"}:
        extras["retry_reason"] = _retry_reason(worker_result)
        return "retry", "retry_pending", extras

    extras["blocking_reasons"] = [f"worker_result:unsupported_status:{worker_status}"]
    return "blocked", "blocked", extras


def _validate_decision_schema(decision_payload: dict[str, Any], decision_schema_path: Path) -> list[str]:
    schema = _load_json_file(decision_schema_path)
    return [issue["message"] for issue in _schema_errors(
        instance=decision_payload,
        schema=schema,
        check="posttask_decision_schema",
        label="posttask-decision.schema.json",
    )]


def run_posttask(
    *,
    task_record_path: Path,
    worker_result_path: Path,
    artifacts_dir: Path | None = None,
    worker_attempt: int = 1,
) -> dict[str, Any]:
    if worker_attempt < 1:
        raise ValueError("`worker_attempt` must be >= 1.")

    task_record = _load_valid_task_record(task_record_path)
    task_id = str(task_record["task_id"]).strip()
    worker_result_schema_path, _, decision_schema_path = _schema_paths()

    effective_artifacts_dir = _resolve_artifacts_dir(
        task_record_path=task_record_path,
        task_id=task_id,
        worker_attempt=worker_attempt,
        artifacts_dir=artifacts_dir,
    )
    effective_artifacts_dir.mkdir(parents=True, exist_ok=True)

    worker_result_payload, worker_contract_result = _load_worker_result_validation(
        worker_result_path=worker_result_path,
        worker_result_schema_path=worker_result_schema_path,
    )
    worker_contract_result_path = effective_artifacts_dir / "worker-result-contract.result.json"
    worker_contract_result_digest = _write_json(worker_contract_result_path, worker_contract_result)

    changed_files_payload = []
    if isinstance(worker_result_payload, dict):
        changed_files_value = worker_result_payload.get("files_changed")
        if isinstance(changed_files_value, list):
            changed_files_payload = changed_files_value

    changed_files_path = effective_artifacts_dir / "changed-files.json"
    changed_files_digest = _write_json(changed_files_path, changed_files_payload)

    scope_result = validate_task_scope(
        changed_files_path=changed_files_path,
        task_record_path=task_record_path,
    )
    scope_result_path = effective_artifacts_dir / "validate-task-scope.result.json"
    scope_result_digest = _write_json(scope_result_path, scope_result)

    worker_result_reference = _artifact_reference(
        artifact_role="worker_result",
        reference=worker_result_path,
        content_digest=_file_digest(worker_result_path),
    )
    task_record_reference = _artifact_reference(
        artifact_role="task_record",
        reference=task_record_path,
        content_digest=_file_digest(task_record_path),
    )
    changed_files_reference = _artifact_reference(
        artifact_role="changed_files",
        reference=changed_files_path,
        content_digest=changed_files_digest,
    )

    validator_results = [
        {
            "validation_stage": "worker_result_contract",
            "validator_name": WORKER_RESULT_VALIDATOR,
            "outcome": worker_contract_result["result"],
            "result_reference": _validator_result_reference(
                worker_contract_result_path,
                worker_contract_result_digest,
            ),
            "summary": _summary(worker_contract_result),
        },
        {
            "validation_stage": "task_scope",
            "validator_name": TASK_SCOPE_VALIDATOR,
            "outcome": scope_result["result"],
            "result_reference": _validator_result_reference(scope_result_path, scope_result_digest),
            "summary": _summary(scope_result),
        },
    ]

    decision, resulting_task_state, decision_extras = _decision_from_results(
        worker_result=worker_result_payload if isinstance(worker_result_payload, dict) else None,
        worker_contract_result=worker_contract_result,
        scope_result=scope_result,
    )

    decision_path = effective_artifacts_dir / "posttask-decision.json"
    decision_payload: dict[str, Any] = {
        "task_id": task_id,
        "decision": decision,
        "resulting_task_state": resulting_task_state,
        "worker_result_reference": worker_result_reference,
        "worker_result_status": (
            str(worker_result_payload["status"])
            if isinstance(worker_result_payload, dict) and "status" in worker_result_payload
            else "blocked"
        ),
        "validator_results": validator_results,
        "persisted_artifacts": {
            "decision_artifact_reference": _artifact_reference(
                artifact_role="posttask_decision",
                reference=decision_path,
                content_digest=_decision_identity_digest(task_id, worker_attempt, decision_path),
            ),
            "validator_result_references": [
                _validator_result_reference(worker_contract_result_path, worker_contract_result_digest),
                _validator_result_reference(scope_result_path, scope_result_digest),
            ],
            "evaluated_inputs": [
                worker_result_reference,
                task_record_reference,
                changed_files_reference,
            ],
        },
        "emitted_at": _utc_timestamp(),
    }
    decision_payload.update(decision_extras)

    decision_schema_errors = _validate_decision_schema(decision_payload, decision_schema_path)
    if decision_schema_errors:
        decision_payload["decision"] = "blocked"
        decision_payload["resulting_task_state"] = "blocked"
        decision_payload.pop("retry_reason", None)
        decision_payload.pop("escalation_reason", None)
        existing_blocking = list(decision_payload.get("blocking_reasons", []))
        decision_payload["blocking_reasons"] = _dedupe(
            existing_blocking
            + [f"posttask-decision-schema:{message}" for message in decision_schema_errors]
        )
        final_schema_errors = _validate_decision_schema(decision_payload, decision_schema_path)
        if final_schema_errors:
            raise ValueError(
                "The posttask decision artifact failed schema validation: "
                + "; ".join(final_schema_errors)
            )

    _write_json(decision_path, decision_payload)
    return decision_payload


def _runtime_error_payload(
    *,
    task_record_path: Path,
    worker_result_path: Path,
    artifacts_dir: Path | None,
    worker_attempt: int,
    error: Exception,
) -> dict[str, Any]:
    return {
        "result": "runtime_error",
        "errors": [{"message": str(error)}],
        "warnings": [],
        "inputs": {
            "task_record": str(task_record_path.resolve()),
            "worker_result": str(worker_result_path.resolve()),
            "artifacts_dir": str(artifacts_dir.resolve()) if artifacts_dir is not None else None,
            "worker_result_schema": str((_contracts_dir() / "worker-result.schema.json").resolve()),
            "posttask_decision_schema": str((_contracts_dir() / "posttask-decision.schema.json").resolve()),
            "worker_attempt": worker_attempt,
        },
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the machine-readable posttask validation gate.")
    parser.add_argument(
        "--task-record",
        required=True,
        type=Path,
        help="Path to the canonical task-record YAML or JSON file.",
    )
    parser.add_argument(
        "--worker-result",
        required=True,
        type=Path,
        help="Path to the canonical worker-result JSON file.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Optional directory for persisted validator-result and posttask-decision artifacts.",
    )
    parser.add_argument(
        "--worker-attempt",
        type=int,
        default=1,
        help="1-based worker-attempt counter for the emitted posttask-decision artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        decision = run_posttask(
            task_record_path=args.task_record,
            worker_result_path=args.worker_result,
            artifacts_dir=args.artifacts_dir,
            worker_attempt=args.worker_attempt,
        )
    except (OSError, ValueError, json.JSONDecodeError, TypeError, AttributeError) as exc:
        print(
            _json_text(
                _runtime_error_payload(
                    task_record_path=args.task_record,
                    worker_result_path=args.worker_result,
                    artifacts_dir=args.artifacts_dir,
                    worker_attempt=args.worker_attempt,
                    error=exc,
                )
            )
        )
        return EXIT_CODES["runtime_error"]

    print(_json_text(decision))
    return EXIT_CODES[decision["decision"]]


if __name__ == "__main__":
    raise SystemExit(main())
