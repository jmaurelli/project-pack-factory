from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, cast

try:
    import yaml
except ImportError:  # pragma: no cover - handled at runtime with deterministic output
    yaml = cast(Any, None)

try:
    from jsonschema.validators import validator_for
    import referencing
except ImportError:  # pragma: no cover - handled at runtime with deterministic output
    validator_for = cast(Any, None)
    referencing = cast(Any, None)

if __package__ in (None, ""):
    package_src_root = Path(__file__).resolve().parents[2]
    if str(package_src_root) not in sys.path:
        sys.path.insert(0, str(package_src_root))
    from ai_native_package.validators.validate_task_brief import validate_task_brief
    from ai_native_package.validators.validate_task_order_and_approval import (
        validate_task_order_and_approval,
    )
else:
    from ..validators.validate_task_brief import validate_task_brief
    from ..validators.validate_task_order_and_approval import (
        validate_task_order_and_approval,
    )


LIST_FIELDS = (
    "project_context_reference",
    "source_spec_reference",
    "files_in_scope",
    "required_changes",
    "acceptance_criteria",
    "validation_commands",
    "out_of_scope",
    "local_evidence",
    "task_boundary_rules",
    "required_return_format",
)
BRIEF_FIELD_ORDER = (
    "task_name",
    "operating_root",
    "project_context_reference",
    "source_spec_reference",
    "objective",
    "files_in_scope",
    "required_changes",
    "acceptance_criteria",
    "validation_commands",
    "out_of_scope",
    "local_evidence",
    "task_boundary_rules",
    "required_return_format",
)
EXIT_CODES = {
    "dispatch": 0,
    "blocked": 3,
    "runtime_error": 2,
}


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _contracts_dir() -> Path:
    return _package_root() / "contracts"


def _policy_paths() -> tuple[Path, Path]:
    policies_dir = _package_root() / "policies"
    return (
        policies_dir / "approval-policy.json",
        policies_dir / "minimum-rollout-order.json",
    )


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_task_record(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return json.loads(text)


def _coerce_single_task_record(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and "task_id" in payload:
        return payload
    if isinstance(payload, list) and len(payload) == 1 and isinstance(payload[0], dict):
        return payload[0]
    if isinstance(payload, dict):
        for key in ("task_records", "tasks"):
            candidate = payload.get(key)
            if isinstance(candidate, list) and len(candidate) == 1 and isinstance(candidate[0], dict):
                return candidate[0]
    raise ValueError(
        "The predispatch runtime requires exactly one task record object or a single-entry task-record collection."
    )


def _require_string_field(task_record: dict[str, Any], field_name: str) -> str:
    value = task_record.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"The task record must declare a non-empty string `{field_name}`.")
    return value.strip()


def _render_delegation_brief(task_record: dict[str, Any]) -> str:
    lines = [
        "# Delegation Brief",
        "",
        "This rendered handoff artifact is derived only from the authoritative `task_record` input. If this brief and the task record differ, the task record is the source of truth.",
    ]
    for field_name in BRIEF_FIELD_ORDER:
        lines.extend(("", f"## {field_name}", ""))
        value = task_record.get(field_name)
        if field_name in LIST_FIELDS:
            if isinstance(value, list):
                lines.extend(f"- {item}" for item in value)
        elif value is not None:
            lines.append(str(value))
    lines.append("")
    return "\n".join(lines)


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


def _resolve_artifacts_dir(
    *,
    task_record_path: Path,
    task_id: str,
    dispatch_attempt: int,
    artifacts_dir: Path | None,
) -> Path:
    if artifacts_dir is not None:
        return artifacts_dir.resolve()
    return task_record_path.resolve().parent / ".predispatch" / task_id / f"attempt-{dispatch_attempt}"


def _validator_result_reference(result_path: Path, digest: str) -> dict[str, str]:
    return _artifact_reference(
        artifact_role="validator_result",
        reference=result_path,
        content_digest=digest,
    )


def _summary_for_brief_result(result: dict[str, Any]) -> str:
    return (
        f"result={result['result']}; "
        f"errors={len(result.get('errors', []))}; "
        f"warnings={len(result.get('warnings', []))}"
    )


def _summary_for_order_result(result: dict[str, Any], task_result: dict[str, Any] | None) -> str:
    summary = (
        f"result={result['result']}; "
        f"errors={len(result.get('errors', []))}; "
        f"warnings={len(result.get('warnings', []))}"
    )
    if task_result is not None:
        summary = (
            f"{summary}; "
            f"approval_state={task_result['approval_state']}; "
            f"dispatchable={task_result['dispatchable']}"
        )
    return summary


def _find_task_result(order_result: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    for item in order_result.get("task_results", []):
        if item.get("task_id") == task_id:
            return item
    return None


def _dedupe_reasons(reasons: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            ordered.append(reason)
    return ordered


def _blocking_reasons(
    *,
    brief_result: dict[str, Any],
    order_result: dict[str, Any],
    task_result: dict[str, Any] | None,
    task_id: str,
) -> list[str]:
    reasons: list[str] = []
    if brief_result["result"] == "fail":
        reasons.extend(
            f"validate-task-brief:{issue['check']}:{issue['message']}"
            for issue in brief_result.get("errors", [])
        )
    if order_result["result"] == "fail":
        reasons.extend(
            f"validate-task-order-and-approval:{issue['check']}:{issue['message']}"
            for issue in order_result.get("errors", [])
        )
    elif task_result is None:
        reasons.append(
            f"validate-task-order-and-approval:task_result_missing:No approval decision support was emitted for task `{task_id}`."
        )
    elif not bool(task_result.get("dispatchable")):
        reasons.append(
            "validate-task-order-and-approval:"
            f"approval_state_not_dispatchable:Task approval_state `{task_result['approval_state']}` is non-dispatchable."
        )
    return _dedupe_reasons(reasons)


def _decision_identity_digest(task_id: str, dispatch_attempt: int, decision_path: Path) -> str:
    # The decision artifact cannot embed a digest of its own final bytes without recursion,
    # so this is a deterministic identity digest for the persisted decision artifact.
    seed = f"{task_id}\n{dispatch_attempt}\n{decision_path.resolve()}".encode("utf-8")
    return _sha256_bytes(seed)


def _validate_with_schema(instance: Any, schema_path: Path) -> list[str]:
    if validator_for is None or referencing is None:
        return []

    approval_state_schema_path = _contracts_dir() / "approval-state.schema.json"
    schema_uri = schema_path.resolve().as_uri()
    approval_state_schema_uri = approval_state_schema_path.resolve().as_uri()
    schema = dict(_load_json_file(schema_path))
    approval_state_schema = dict(_load_json_file(approval_state_schema_path))
    schema.setdefault("$id", schema_uri)
    approval_state_schema.setdefault("$id", approval_state_schema_uri)

    registry = referencing.Registry().with_resources(
        [
            (schema_uri, referencing.Resource.from_contents(schema)),
            (approval_state_schema_uri, referencing.Resource.from_contents(approval_state_schema)),
        ]
    )
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema, registry=registry)
    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (".".join(str(part) for part in error.path), error.message),
    )
    return [error.message for error in errors]


def run_predispatch(
    *,
    task_record_path: Path,
    delegation_brief_path: Path | None = None,
    artifacts_dir: Path | None = None,
    dispatch_attempt: int = 1,
) -> dict[str, Any]:
    if dispatch_attempt < 1:
        raise ValueError("`dispatch_attempt` must be >= 1.")

    task_record_payload = _load_task_record(task_record_path)
    task_record = _coerce_single_task_record(task_record_payload)
    task_id = _require_string_field(task_record, "task_id")
    approval_state = _require_string_field(task_record, "approval_state")

    effective_artifacts_dir = _resolve_artifacts_dir(
        task_record_path=task_record_path,
        task_id=task_id,
        dispatch_attempt=dispatch_attempt,
        artifacts_dir=artifacts_dir,
    )
    effective_artifacts_dir.mkdir(parents=True, exist_ok=True)

    if delegation_brief_path is None:
        delegation_brief_text = _render_delegation_brief(task_record)
    else:
        delegation_brief_text = delegation_brief_path.read_text(encoding="utf-8")

    effective_brief_path = effective_artifacts_dir / "delegation-brief.md"
    brief_digest = _write_text(effective_brief_path, delegation_brief_text)

    brief_result = validate_task_brief(
        brief_path=effective_brief_path,
        task_record_path=task_record_path,
    )
    order_result = validate_task_order_and_approval(task_record_path=task_record_path)
    task_result = _find_task_result(order_result, task_id)

    brief_result_path = effective_artifacts_dir / "validate-task-brief.result.json"
    order_result_path = effective_artifacts_dir / "validate-task-order-and-approval.result.json"
    brief_result_digest = _write_json(brief_result_path, brief_result)
    order_result_digest = _write_json(order_result_path, order_result)

    approval_policy_path, _ = _policy_paths()
    decision_schema_path = _contracts_dir() / "predispatch-decision.schema.json"
    task_record_reference = _artifact_reference(
        artifact_role="task_record",
        reference=task_record_path,
        content_digest=_file_digest(task_record_path),
    )
    delegation_brief_reference = _artifact_reference(
        artifact_role="delegation_brief",
        reference=effective_brief_path,
        content_digest=brief_digest,
    )
    validator_results = [
        {
            "validator_name": "validate-task-brief",
            "outcome": brief_result["result"],
            "result_reference": _validator_result_reference(brief_result_path, brief_result_digest),
            "summary": _summary_for_brief_result(brief_result),
        },
        {
            "validator_name": "validate-task-order-and-approval",
            "outcome": order_result["result"],
            "result_reference": _validator_result_reference(order_result_path, order_result_digest),
            "summary": _summary_for_order_result(order_result, task_result),
        },
    ]

    blocking_reasons = _blocking_reasons(
        brief_result=brief_result,
        order_result=order_result,
        task_result=task_result,
        task_id=task_id,
    )
    decision = "dispatch" if not blocking_reasons else "blocked"
    resulting_task_state = "ready_to_dispatch" if decision == "dispatch" else "blocked"
    decision_path = effective_artifacts_dir / "predispatch-decision.json"
    decision_payload: dict[str, Any] = {
        "task_id": task_id,
        "decision": decision,
        "resulting_task_state": resulting_task_state,
        "task_record_reference": task_record_reference,
        "delegation_brief_reference": delegation_brief_reference,
        "approval_state": approval_state,
        "validator_results": validator_results,
        "persisted_artifacts": {
            "decision_artifact_reference": _artifact_reference(
                artifact_role="predispatch_decision",
                reference=decision_path,
                content_digest=_decision_identity_digest(task_id, dispatch_attempt, decision_path),
            ),
            "approval_policy_reference": _artifact_reference(
                artifact_role="approval_policy",
                reference=approval_policy_path,
                content_digest=_file_digest(approval_policy_path),
            ),
            "validator_result_references": [
                _validator_result_reference(brief_result_path, brief_result_digest),
                _validator_result_reference(order_result_path, order_result_digest),
            ],
            "input_artifacts": [
                task_record_reference,
                delegation_brief_reference,
            ],
        },
        "dispatch_attempt": dispatch_attempt,
    }
    if blocking_reasons:
        decision_payload["blocking_reasons"] = blocking_reasons

    decision_schema_errors = _validate_with_schema(decision_payload, decision_schema_path)
    if decision_schema_errors:
        schema_blocking_reasons = [
            f"predispatch-decision-schema:{message}" for message in decision_schema_errors
        ]
        decision_payload["decision"] = "blocked"
        decision_payload["resulting_task_state"] = "blocked"
        decision_payload["blocking_reasons"] = _dedupe_reasons(
            blocking_reasons + schema_blocking_reasons
        )

    _write_json(decision_path, decision_payload)
    return decision_payload


def _runtime_error_payload(
    *,
    task_record_path: Path,
    delegation_brief_path: Path | None,
    artifacts_dir: Path | None,
    dispatch_attempt: int,
    error: Exception,
) -> dict[str, Any]:
    return {
        "result": "runtime_error",
        "errors": [{"message": str(error)}],
        "warnings": [],
        "inputs": {
            "task_record": str(task_record_path.resolve()),
            "delegation_brief": str(delegation_brief_path.resolve()) if delegation_brief_path else None,
            "artifacts_dir": str(artifacts_dir.resolve()) if artifacts_dir else None,
            "predispatch_decision_schema": str((_contracts_dir() / "predispatch-decision.schema.json").resolve()),
            "dispatch_attempt": dispatch_attempt,
        },
    }


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the machine-readable predispatch validation gate.")
    parser.add_argument(
        "--task-record",
        required=True,
        type=Path,
        help="Path to the canonical task-record YAML or JSON file.",
    )
    parser.add_argument(
        "--delegation-brief",
        type=Path,
        default=None,
        help="Optional path to a rendered delegation brief Markdown file. If omitted, the brief is rendered from the task record.",
    )
    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        default=None,
        help="Optional directory for persisted validator-result and predispatch-decision artifacts.",
    )
    parser.add_argument(
        "--dispatch-attempt",
        type=int,
        default=1,
        help="1-based dispatch-attempt counter for the emitted predispatch-decision artifact.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        decision = run_predispatch(
            task_record_path=args.task_record,
            delegation_brief_path=args.delegation_brief,
            artifacts_dir=args.artifacts_dir,
            dispatch_attempt=args.dispatch_attempt,
        )
    except (OSError, ValueError, json.JSONDecodeError, TypeError, AttributeError) as exc:
        print(
            _json_text(
                _runtime_error_payload(
                    task_record_path=args.task_record,
                    delegation_brief_path=args.delegation_brief,
                    artifacts_dir=args.artifacts_dir,
                    dispatch_attempt=args.dispatch_attempt,
                    error=exc,
                )
            )
        )
        return EXIT_CODES["runtime_error"]

    print(_json_text(decision))
    return EXIT_CODES[decision["decision"]]


if __name__ == "__main__":
    raise SystemExit(main())
