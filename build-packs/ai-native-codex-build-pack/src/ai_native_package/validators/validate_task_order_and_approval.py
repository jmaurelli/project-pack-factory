from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, cast

try:
    import yaml
except ImportError:  # pragma: no cover - handled at runtime with a deterministic error
    yaml = cast(Any, None)

try:
    from jsonschema.validators import validator_for
except ImportError:  # pragma: no cover - handled at runtime with a deterministic error
    validator_for = cast(Any, None)


VALIDATOR_NAME = "validate-task-order-and-approval"
RESULT_PASS = "pass"
RESULT_WARN = "warn"
RESULT_FAIL = "fail"
RESULT_BLOCKED = "blocked"
TASK_SET_KEYS = ("task_records", "tasks")
EXIT_CODES = {
    RESULT_PASS: 0,
    RESULT_WARN: 1,
    RESULT_FAIL: 2,
    RESULT_BLOCKED: 3,
}


def _issue(check: str, message: str, **details: Any) -> dict[str, Any]:
    issue = {"check": check, "message": message}
    for key, value in details.items():
        if value is not None:
            issue[key] = value
    return issue


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _artifact_paths() -> tuple[Path, Path, Path, Path]:
    package_root = _package_root()
    return (
        package_root / "contracts" / "task-record.schema.json",
        package_root / "contracts" / "approval-state.schema.json",
        package_root / "policies" / "approval-policy.json",
        package_root / "policies" / "minimum-rollout-order.json",
    )


def _load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_task_record(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text)
    return json.loads(text)


def _format_schema_path(path_segments: Any) -> str:
    parts = [str(segment) for segment in path_segments]
    return ".".join(parts) if parts else "$"


def _sort_issues(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        issues,
        key=lambda issue: (
            str(issue.get("check", "")),
            str(issue.get("task_id", "")),
            str(issue.get("record_index", "")),
            str(issue.get("path", "")),
            str(issue.get("message", "")),
        ),
    )


def _validate_with_schema(
    *,
    instance: Any,
    schema: dict[str, Any],
    check: str,
    label: str,
    task_id: str | None = None,
    record_index: int | None = None,
) -> list[dict[str, Any]]:
    if validator_for is None:
        return [
            _issue(
                check,
                "The `jsonschema` dependency is required to validate machine-readable contracts.",
                source=label,
                task_id=task_id,
                record_index=record_index,
            )
        ]

    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema)
    errors: list[dict[str, Any]] = []
    sorted_errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: (_format_schema_path(error.path), error.message),
    )
    for error in sorted_errors:
        errors.append(
            _issue(
                check,
                error.message,
                source=label,
                path=_format_schema_path(error.path),
                task_id=task_id,
                record_index=record_index,
            )
        )
    return errors


def _build_result_payload(
    *,
    task_record_path: Path,
    task_record_schema_path: Path,
    approval_state_schema_path: Path,
    approval_policy_path: Path,
    minimum_rollout_order_path: Path,
) -> dict[str, Any]:
    return {
        "validator": VALIDATOR_NAME,
        "result": RESULT_PASS,
        "errors": [],
        "warnings": [],
        "inputs": {
            "task_record": str(task_record_path.resolve()),
            "task_record_schema": str(task_record_schema_path.resolve()),
            "approval_state_schema": str(approval_state_schema_path.resolve()),
            "approval_policy": str(approval_policy_path.resolve()),
            "minimum_rollout_order": str(minimum_rollout_order_path.resolve()),
        },
        "task_results": [],
        "deterministic_order": [],
    }


def _extract_task_records(payload: Any) -> tuple[list[dict[str, Any]], str | None, list[dict[str, Any]]]:
    if isinstance(payload, dict) and "task_id" in payload:
        return [payload], "single_task_record", []

    if isinstance(payload, list):
        return _coerce_task_record_list(payload, container_kind="task_record_list")

    if isinstance(payload, dict):
        for key in TASK_SET_KEYS:
            candidate = payload.get(key)
            if candidate is not None:
                return _coerce_task_record_list(candidate, container_kind=f"task_record_set.{key}")

    return [], None, [
        _issue(
            "task_record_shape",
            "The task-record input must deserialize to a task record object, a list of task records, or a mapping with `task_records` or `tasks`.",
        )
    ]


def _coerce_task_record_list(payload: Any, *, container_kind: str) -> tuple[list[dict[str, Any]], str, list[dict[str, Any]]]:
    if not isinstance(payload, list):
        return [], container_kind, [
            _issue(
                "task_record_shape",
                "The task-record collection must deserialize to a JSON array.",
                source=container_kind,
            )
        ]

    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for index, item in enumerate(payload):
        if isinstance(item, dict):
            records.append(item)
            continue
        errors.append(
            _issue(
                "task_record_shape",
                "Each task-record entry must deserialize to a JSON object.",
                source=container_kind,
                record_index=index,
            )
        )
    return records, container_kind, errors


def _canonical_sort_key(record: dict[str, Any]) -> tuple[int, str]:
    declared_order = record.get("declared_order")
    task_id = record.get("task_id")
    if isinstance(declared_order, int) and isinstance(task_id, str):
        return declared_order, task_id
    if isinstance(declared_order, int):
        return declared_order, ""
    if isinstance(task_id, str):
        return 0, task_id
    return 0, ""


def _validate_rollout_policy(rollout_policy: Any) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    ordered_steps = rollout_policy.get("ordered_steps") if isinstance(rollout_policy, dict) else None
    if not isinstance(ordered_steps, list):
        return [
            _issue(
                "rollout_policy",
                "The minimum rollout order policy should expose an `ordered_steps` array for validator sequencing context.",
                source="minimum-rollout-order.json",
            )
        ]

    step = None
    for candidate in ordered_steps:
        if isinstance(candidate, dict) and candidate.get("step_id") == VALIDATOR_NAME:
            step = candidate
            break

    if step is None:
        warnings.append(
            _issue(
                "rollout_policy",
                "The minimum rollout order policy does not declare `validate-task-order-and-approval`.",
                source="minimum-rollout-order.json",
            )
        )
        return warnings

    if step.get("step_type") != "validator":
        warnings.append(
            _issue(
                "rollout_policy",
                "The rollout-policy entry for this validator should declare `step_type` as `validator`.",
                source="minimum-rollout-order.json",
            )
        )
    if step.get("enforcement_point") != "pre_dispatch":
        warnings.append(
            _issue(
                "rollout_policy",
                "The rollout-policy entry for this validator should remain scoped to `pre_dispatch`.",
                source="minimum-rollout-order.json",
            )
        )
    return warnings


def _index_approval_policy(
    approval_policy: Any,
) -> tuple[dict[str, str], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    initial_state_by_requirement: dict[str, str] = {}
    state_policy_by_state: dict[str, dict[str, Any]] = {}

    if not isinstance(approval_policy, dict):
        return initial_state_by_requirement, state_policy_by_state, [
            _issue(
                "approval_policy",
                "The approval policy must deserialize to a JSON object.",
                source="approval-policy.json",
            )
        ]

    initial_state_entries = approval_policy.get("initial_state_by_approval_requirement")
    if not isinstance(initial_state_entries, list):
        errors.append(
            _issue(
                "approval_policy",
                "The approval policy must declare `initial_state_by_approval_requirement` as an array.",
                source="approval-policy.json",
            )
        )
    else:
        for index, entry in enumerate(initial_state_entries):
            if not isinstance(entry, dict):
                errors.append(
                    _issue(
                        "approval_policy",
                        "Each approval-requirement initial-state entry must be an object.",
                        source="approval-policy.json",
                        record_index=index,
                    )
                )
                continue
            requirement = entry.get("approval_requirement")
            initial_state = entry.get("initial_approval_state")
            if not isinstance(requirement, str) or not isinstance(initial_state, str):
                errors.append(
                    _issue(
                        "approval_policy",
                        "Each approval-requirement initial-state entry must declare string values for `approval_requirement` and `initial_approval_state`.",
                        source="approval-policy.json",
                        record_index=index,
                    )
                )
                continue
            if requirement in initial_state_by_requirement:
                errors.append(
                    _issue(
                        "approval_policy",
                        f"Duplicate approval requirement `{requirement}` found in the approval policy.",
                        source="approval-policy.json",
                    )
                )
                continue
            initial_state_by_requirement[requirement] = initial_state

    state_entries = approval_policy.get("state_policies")
    if not isinstance(state_entries, list):
        errors.append(
            _issue(
                "approval_policy",
                "The approval policy must declare `state_policies` as an array.",
                source="approval-policy.json",
            )
        )
    else:
        for index, entry in enumerate(state_entries):
            if not isinstance(entry, dict):
                errors.append(
                    _issue(
                        "approval_policy",
                        "Each state-policy entry must be an object.",
                        source="approval-policy.json",
                        record_index=index,
                    )
                )
                continue
            approval_state = entry.get("approval_state")
            if not isinstance(approval_state, str):
                errors.append(
                    _issue(
                        "approval_policy",
                        "Each state-policy entry must declare a string `approval_state`.",
                        source="approval-policy.json",
                        record_index=index,
                    )
                )
                continue
            if approval_state in state_policy_by_state:
                errors.append(
                    _issue(
                        "approval_policy",
                        f"Duplicate approval state `{approval_state}` found in the approval policy.",
                        source="approval-policy.json",
                    )
                )
                continue
            state_policy_by_state[approval_state] = entry

    return initial_state_by_requirement, state_policy_by_state, errors


def _reachable_states(initial_state: str, state_policy_by_state: dict[str, dict[str, Any]]) -> set[str]:
    visited: set[str] = set()
    stack = [initial_state]
    while stack:
        state = stack.pop()
        if state in visited:
            continue
        visited.add(state)
        entry = state_policy_by_state.get(state, {})
        next_states = entry.get("allowed_next_states", [])
        if isinstance(next_states, list):
            for candidate in reversed(next_states):
                if isinstance(candidate, str):
                    stack.append(candidate)
    return visited


def _validate_task_records(
    records: list[dict[str, Any]],
    task_record_schema: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    valid_records: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        task_id = record.get("task_id") if isinstance(record.get("task_id"), str) else None
        schema_errors = _validate_with_schema(
            instance=record,
            schema=task_record_schema,
            check="task_record_schema",
            label="task-record.schema.json",
            task_id=task_id,
            record_index=index,
        )
        errors.extend(schema_errors)
        if not schema_errors:
            valid_records.append(record)
    return valid_records, errors


def _validate_order_metadata(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    records_by_id: dict[str, dict[str, Any]] = {}
    encounter_order: list[str] = []

    for index, record in enumerate(records):
        task_id = record.get("task_id")
        if not isinstance(task_id, str):
            continue
        encounter_order.append(task_id)
        if task_id in records_by_id:
            errors.append(
                _issue(
                    "task_order",
                    f"Duplicate task_id `{task_id}` found in the task-record set.",
                    task_id=task_id,
                    record_index=index,
                )
            )
            continue
        records_by_id[task_id] = record

    for task_id, record in sorted(records_by_id.items(), key=lambda item: _canonical_sort_key(item[1])):
        dependencies = record.get("dependencies")
        if not isinstance(dependencies, list):
            continue
        for dependency in dependencies:
            if dependency == task_id:
                errors.append(
                    _issue(
                        "task_order",
                        "A task cannot depend on itself.",
                        task_id=task_id,
                        dependency=dependency,
                    )
                )
            elif dependency not in records_by_id:
                errors.append(
                    _issue(
                        "task_order",
                        f"Dependency reference `{dependency}` does not resolve to a task_id in the provided task-record input.",
                        task_id=task_id,
                        dependency=dependency,
                    )
                )

    cycle_errors = _detect_dependency_cycles(records_by_id)
    errors.extend(cycle_errors)

    deterministic_order = [
        task_id for task_id, _ in sorted(records_by_id.items(), key=lambda item: _canonical_sort_key(item[1]))
    ]
    if len(encounter_order) > 1 and encounter_order != deterministic_order:
        warnings.append(
            _issue(
                "task_order",
                "The input task-record order does not match the canonical deterministic order `declared_order` then `task_id`.",
            )
        )

    return errors, warnings, deterministic_order


def _detect_dependency_cycles(records_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            cycle_start = path.index(task_id)
            cycle_path = path[cycle_start:] + [task_id]
            errors.append(
                _issue(
                    "task_order",
                    f"Dependency cycle detected: {' -> '.join(cycle_path)}",
                    task_id=task_id,
                )
            )
            return

        visiting.add(task_id)
        path.append(task_id)
        dependencies = records_by_id[task_id].get("dependencies", [])
        if isinstance(dependencies, list):
            for dependency in dependencies:
                if dependency in records_by_id:
                    visit(dependency)
        path.pop()
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in sorted(records_by_id):
        visit(task_id)

    return errors


def _evaluate_approval_state(
    *,
    record: dict[str, Any],
    approval_state_schema: dict[str, Any],
    approval_policy: dict[str, Any],
    initial_state_by_requirement: dict[str, str],
    state_policy_by_state: dict[str, dict[str, Any]],
    record_index: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    task_id = record.get("task_id") if isinstance(record.get("task_id"), str) else None
    approval_requirement = record.get("approval_requirement")
    approval_state = record.get("approval_state")

    errors.extend(
        _validate_with_schema(
            instance=approval_state,
            schema=approval_state_schema,
            check="approval_state_schema",
            label="approval-state.schema.json",
            task_id=task_id,
            record_index=record_index,
        )
    )

    if not isinstance(approval_requirement, str):
        errors.append(
            _issue(
                "approval_requirement",
                "The task record must declare a string `approval_requirement` before dispatchability can be computed.",
                task_id=task_id,
                record_index=record_index,
            )
        )
        return None, errors

    if not isinstance(approval_state, str):
        return None, errors

    initial_state = initial_state_by_requirement.get(approval_requirement)
    if initial_state is None:
        errors.append(
            _issue(
                "approval_policy",
                f"No initial approval state is defined in approval-policy.json for requirement `{approval_requirement}`.",
                task_id=task_id,
            )
        )
        return None, errors

    state_policy = state_policy_by_state.get(approval_state)
    if state_policy is None:
        errors.append(
            _issue(
                "approval_policy",
                f"No state policy is defined in approval-policy.json for state `{approval_state}`.",
                task_id=task_id,
            )
        )
        return None, errors

    reachable_states = _reachable_states(initial_state, state_policy_by_state)
    if approval_state not in reachable_states:
        errors.append(
            _issue(
                "approval_policy",
                f"Approval state `{approval_state}` is not reachable from requirement `{approval_requirement}` under approval-policy.json.",
                task_id=task_id,
                approval_requirement=approval_requirement,
                approval_state=approval_state,
            )
        )
        return None, errors

    dispatchable = state_policy.get("dispatchable")
    if not isinstance(dispatchable, bool):
        errors.append(
            _issue(
                "approval_policy",
                f"State `{approval_state}` must declare boolean `dispatchable` in approval-policy.json.",
                task_id=task_id,
            )
        )
        return None, errors

    predispatch_outcome = state_policy.get("predispatch_outcome")
    autonomous_continuation = state_policy.get("autonomous_continuation")
    non_dispatchable_outcome = approval_policy.get("non_dispatchable_outcome")

    if not dispatchable and predispatch_outcome != non_dispatchable_outcome:
        errors.append(
            _issue(
                "approval_policy",
                f"Non-dispatchable state `{approval_state}` must resolve to the configured non-dispatchable outcome.",
                task_id=task_id,
                approval_state=approval_state,
            )
        )
        return None, errors

    return {
        "task_id": task_id,
        "declared_order": record.get("declared_order"),
        "dependencies": record.get("dependencies", []),
        "approval_requirement": approval_requirement,
        "approval_state": approval_state,
        "initial_approval_state": initial_state,
        "dispatchable": dispatchable,
        "predispatch_outcome": predispatch_outcome,
        "autonomous_continuation": autonomous_continuation,
        "non_dispatchable_outcome": non_dispatchable_outcome,
        "policy_version": approval_policy.get("policy_version"),
        "effective_result": RESULT_PASS if dispatchable else RESULT_BLOCKED,
    }, errors


def validate_task_order_and_approval(task_record_path: Path) -> dict[str, Any]:
    (
        task_record_schema_path,
        approval_state_schema_path,
        approval_policy_path,
        minimum_rollout_order_path,
    ) = _artifact_paths()
    result = _build_result_payload(
        task_record_path=task_record_path,
        task_record_schema_path=task_record_schema_path,
        approval_state_schema_path=approval_state_schema_path,
        approval_policy_path=approval_policy_path,
        minimum_rollout_order_path=minimum_rollout_order_path,
    )

    try:
        task_record_schema = _load_json_file(task_record_schema_path)
        approval_state_schema = _load_json_file(approval_state_schema_path)
        approval_policy = _load_json_file(approval_policy_path)
        minimum_rollout_order = _load_json_file(minimum_rollout_order_path)
    except (OSError, json.JSONDecodeError) as exc:
        result["errors"].append(
            _issue(
                "artifact_load",
                f"Unable to load the required validator contract or policy artifact: {exc}",
            )
        )
        result["result"] = RESULT_FAIL
        result["errors"] = _sort_issues(result["errors"])
        return result

    result["warnings"].extend(_validate_rollout_policy(minimum_rollout_order))

    initial_state_by_requirement, state_policy_by_state, approval_policy_errors = _index_approval_policy(approval_policy)
    result["errors"].extend(approval_policy_errors)

    try:
        payload = _load_task_record(task_record_path)
    except OSError as exc:
        result["errors"].append(
            _issue(
                "task_record_load",
                f"Unable to load the task record: {exc}",
                source=str(task_record_path),
            )
        )
        result["result"] = RESULT_FAIL
        result["errors"] = _sort_issues(result["errors"])
        result["warnings"] = _sort_issues(result["warnings"])
        return result
    except (json.JSONDecodeError, AttributeError, TypeError, ValueError) as exc:
        result["errors"].append(
            _issue(
                "task_record_load",
                f"Unable to parse the task record as canonical YAML or JSON: {exc}",
                source=str(task_record_path),
            )
        )
        result["result"] = RESULT_FAIL
        result["errors"] = _sort_issues(result["errors"])
        result["warnings"] = _sort_issues(result["warnings"])
        return result

    records, input_kind, shape_errors = _extract_task_records(payload)
    result["errors"].extend(shape_errors)
    result["inputs"]["task_record_input_kind"] = input_kind

    if not records:
        result["result"] = RESULT_FAIL
        result["errors"] = _sort_issues(result["errors"])
        result["warnings"] = _sort_issues(result["warnings"])
        return result

    valid_records, schema_errors = _validate_task_records(records, task_record_schema)
    result["errors"].extend(schema_errors)

    order_errors, order_warnings, deterministic_order = _validate_order_metadata(valid_records)
    result["errors"].extend(order_errors)
    result["warnings"].extend(order_warnings)
    result["deterministic_order"] = deterministic_order

    task_results: list[dict[str, Any]] = []
    valid_record_indexes = {id(record): index for index, record in enumerate(records)}
    for record in valid_records:
        evaluation, evaluation_errors = _evaluate_approval_state(
            record=record,
            approval_state_schema=approval_state_schema,
            approval_policy=approval_policy,
            initial_state_by_requirement=initial_state_by_requirement,
            state_policy_by_state=state_policy_by_state,
            record_index=valid_record_indexes[id(record)],
        )
        result["errors"].extend(evaluation_errors)
        if evaluation is not None:
            task_results.append(evaluation)

    result["task_results"] = sorted(task_results, key=lambda item: (item["declared_order"], item["task_id"]))

    if result["errors"]:
        result["result"] = RESULT_FAIL
    elif any(not task_result["dispatchable"] for task_result in result["task_results"]):
        result["result"] = RESULT_BLOCKED
    elif result["warnings"]:
        result["result"] = RESULT_WARN

    result["errors"] = _sort_issues(result["errors"])
    result["warnings"] = _sort_issues(result["warnings"])
    return result


def _format_text_output(result: dict[str, Any]) -> str:
    lines = [
        f"validator: {result['validator']}",
        f"result: {result['result']}",
        "inputs:",
    ]
    for key in (
        "task_record",
        "task_record_input_kind",
        "task_record_schema",
        "approval_state_schema",
        "approval_policy",
        "minimum_rollout_order",
    ):
        lines.append(f"  {key}: {result['inputs'].get(key)}")

    lines.append("deterministic_order:")
    if result["deterministic_order"]:
        for index, task_id in enumerate(result["deterministic_order"], start=1):
            lines.append(f"  {index}. {task_id}")
    else:
        lines.append("  none")

    lines.append("task_results:")
    if result["task_results"]:
        for index, task_result in enumerate(result["task_results"], start=1):
            lines.append(
                "  "
                f"{index}. {task_result['task_id']} "
                f"(declared_order={task_result['declared_order']}, "
                f"approval_state={task_result['approval_state']}, "
                f"dispatchable={task_result['dispatchable']}, "
                f"predispatch_outcome={task_result['predispatch_outcome']})"
            )
    else:
        lines.append("  none")

    lines.append("errors:")
    if result["errors"]:
        for index, issue in enumerate(result["errors"], start=1):
            lines.append(f"  {index}. [{issue['check']}] {issue['message']}")
    else:
        lines.append("  none")

    lines.append("warnings:")
    if result["warnings"]:
        for index, issue in enumerate(result["warnings"], start=1):
            lines.append(f"  {index}. [{issue['check']}] {issue['message']}")
    else:
        lines.append("  none")

    return "\n".join(lines)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate task-record order metadata and approval dispatchability.")
    parser.add_argument(
        "--task-record",
        required=True,
        type=Path,
        help="Path to the canonical task-record YAML or JSON file.",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Deterministic output mode.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = validate_task_order_and_approval(task_record_path=args.task_record)
    if args.output == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_format_text_output(result))
    return EXIT_CODES[result["result"]]


if __name__ == "__main__":
    raise SystemExit(main())
