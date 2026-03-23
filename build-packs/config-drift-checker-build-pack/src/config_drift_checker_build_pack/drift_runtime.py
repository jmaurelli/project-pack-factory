from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yaml


SEVERITIES = ("informational", "warning", "blocking")
CHANGE_TYPES = ("added", "removed", "changed", "type_changed")


class DriftRuntimeError(ValueError):
    pass


@dataclass(frozen=True)
class Rules:
    ignore_paths: tuple[str, ...] = ()
    severity_overrides: tuple[tuple[tuple[str, ...], str], ...] = ()
    allowed_exceptions: tuple[tuple[str, ...], ...] = ()


def check_drift(
    baseline_path: Path,
    candidate_path: Path,
    *,
    rules_path: Path | None = None,
    fail_on: str = "blocking",
) -> dict[str, Any]:
    try:
        baseline_value, baseline_format = _load_structured_document(baseline_path)
        candidate_value, candidate_format = _load_structured_document(candidate_path)
        rules = _load_rules(rules_path) if rules_path is not None else Rules()
        findings = _compare_documents(baseline_value, candidate_value, rules)
        counts = _count_findings(findings)
        status = _classify_status(counts, fail_on=fail_on)
        input_format = _combine_input_formats(baseline_format, candidate_format)
        summary = _build_summary(status, counts)
        return {
            "status": status,
            "baseline_path": str(baseline_path.resolve()),
            "candidate_path": str(candidate_path.resolve()),
            "input_format": input_format,
            "summary": summary,
            "findings": findings,
            "counts": counts,
        }
    except DriftRuntimeError as exc:
        return {
            "status": "fail",
            "baseline_path": str(baseline_path.resolve()),
            "candidate_path": str(candidate_path.resolve()),
            "input_format": "mixed",
            "summary": f"Input could not be trusted: {exc}",
            "findings": [],
            "counts": _count_findings([]),
            "errors": [str(exc)],
        }


def _load_structured_document(path: Path) -> tuple[Any, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DriftRuntimeError(f"Unable to read {path}: {exc.strerror or exc}") from exc

    if not text.strip():
        raise DriftRuntimeError(f"{path} is empty")

    suffix = path.suffix.lower()
    parse_order: Sequence[tuple[str, Any]]
    if suffix == ".json":
        parse_order = (("json", json.loads),)
    elif suffix in {".yaml", ".yml"}:
        parse_order = (("yaml", yaml.safe_load),)
    else:
        parse_order = (("json", json.loads), ("yaml", yaml.safe_load))

    last_error: Exception | None = None
    for format_name, parser in parse_order:
        try:
            value = parser(text)
        except Exception as exc:  # pragma: no cover - parser-specific failures are data dependent
            last_error = exc
            continue
        if value is None:
            last_error = DriftRuntimeError(f"{path} parsed as {format_name} but produced an empty document")
            continue
        normalized = _normalize_value(value)
        return normalized, format_name

    raise DriftRuntimeError(
        f"Unable to parse {path} as structured JSON or YAML: {last_error}"
    )


def _load_rules(path: Path) -> Rules:
    data, _ = _load_structured_document(path)
    if not isinstance(data, Mapping):
        raise DriftRuntimeError(f"Rules file {path} must contain a mapping at the top level")

    ignore_paths = _read_path_list(
        data.get("ignore_paths", data.get("ignored_paths", ())),
        field_name="ignore_paths",
    )
    allowed_exceptions = _read_path_list(
        data.get("allowed_exceptions", ()),
        field_name="allowed_exceptions",
    )
    severity_overrides_raw = data.get("severity_overrides", {})
    if severity_overrides_raw is None:
        severity_overrides_raw = {}
    if not isinstance(severity_overrides_raw, Mapping):
        raise DriftRuntimeError("severity_overrides must be a mapping from path to severity")

    severity_overrides: list[tuple[tuple[str, ...], str]] = []
    for raw_path, raw_severity in severity_overrides_raw.items():
        rule_path = _parse_path_spec(str(raw_path))
        severity = str(raw_severity).lower()
        if severity not in SEVERITIES:
            raise DriftRuntimeError(
                f"Unsupported severity override {raw_severity!r} for path {raw_path!r}"
            )
        severity_overrides.append((rule_path, severity))

    severity_overrides.sort(key=lambda item: (-len(item[0]), _format_path(item[0])))
    return Rules(
        ignore_paths=tuple(ignore_paths),
        severity_overrides=tuple(severity_overrides),
        allowed_exceptions=tuple(allowed_exceptions),
    )


def _read_path_list(raw_value: Any, *, field_name: str) -> list[tuple[str, ...]]:
    if raw_value in (None, ""):
        return []
    if not isinstance(raw_value, Sequence) or isinstance(raw_value, (str, bytes, bytearray)):
        raise DriftRuntimeError(f"{field_name} must be a list of path strings")
    parsed_paths: list[tuple[str, ...]] = []
    for entry in raw_value:
        if isinstance(entry, Mapping):
            if "path" not in entry:
                raise DriftRuntimeError(f"{field_name} entries must include a path field")
            parsed_paths.append(_parse_path_spec(str(entry["path"])))
            continue
        parsed_paths.append(_parse_path_spec(str(entry)))
    parsed_paths.sort(key=lambda item: (-len(item), _format_path(item)))
    return parsed_paths


def _normalize_value(value: Any, *, _seen: set[int] | None = None) -> Any:
    if _seen is None:
        _seen = set()

    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DriftRuntimeError("Non-finite numeric values are not supported")
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    object_id = id(value)
    if object_id in _seen:
        raise DriftRuntimeError("Cyclic data structures are not supported")

    if isinstance(value, Mapping):
        _seen.add(object_id)
        normalized_items: list[tuple[str, Any]] = []
        for key in sorted(value.keys(), key=lambda item: str(item)):
            if not isinstance(key, str):
                raise DriftRuntimeError("Only string mapping keys are supported")
            normalized_items.append((key, _normalize_value(value[key], _seen=_seen)))
        _seen.remove(object_id)
        return {key: item for key, item in normalized_items}

    if isinstance(value, list):
        _seen.add(object_id)
        normalized_list = [_normalize_value(item, _seen=_seen) for item in value]
        _seen.remove(object_id)
        return normalized_list

    if isinstance(value, tuple):
        _seen.add(object_id)
        normalized_tuple = [_normalize_value(item, _seen=_seen) for item in value]
        _seen.remove(object_id)
        return normalized_tuple

    raise DriftRuntimeError(f"Unsupported value type {type(value).__name__}")


def _compare_documents(baseline: Any, candidate: Any, rules: Rules) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    _compare_values((), baseline, candidate, findings, rules)
    findings.sort(key=lambda item: (item["path"], item["change_type"]))
    return findings


def _compare_values(
    path_parts: tuple[Any, ...],
    baseline: Any,
    candidate: Any,
    findings: list[dict[str, Any]],
    rules: Rules,
) -> None:
    if isinstance(baseline, dict) and isinstance(candidate, dict):
        keys = sorted(set(baseline) | set(candidate))
        for key in keys:
            next_path = path_parts + (key,)
            baseline_has = key in baseline
            candidate_has = key in candidate
            if baseline_has and candidate_has:
                _compare_values(next_path, baseline[key], candidate[key], findings, rules)
            elif baseline_has:
                _record_finding(
                    findings,
                    next_path,
                    "removed",
                    baseline[key],
                    None,
                    rules,
                )
            else:
                _record_finding(
                    findings,
                    next_path,
                    "added",
                    None,
                    candidate[key],
                    rules,
                )
        return

    if isinstance(baseline, list) and isinstance(candidate, list):
        max_length = max(len(baseline), len(candidate))
        for index in range(max_length):
            next_path = path_parts + (index,)
            if index < len(baseline) and index < len(candidate):
                _compare_values(next_path, baseline[index], candidate[index], findings, rules)
            elif index < len(baseline):
                _record_finding(
                    findings,
                    next_path,
                    "removed",
                    baseline[index],
                    None,
                    rules,
                )
            else:
                _record_finding(
                    findings,
                    next_path,
                    "added",
                    None,
                    candidate[index],
                    rules,
                )
        return

    if type(baseline) is not type(candidate):
        _record_finding(findings, path_parts, "type_changed", baseline, candidate, rules)
        return

    if baseline != candidate:
        _record_finding(findings, path_parts, "changed", baseline, candidate, rules)


def _record_finding(
    findings: list[dict[str, Any]],
    path_parts: tuple[Any, ...],
    change_type: str,
    baseline_value: Any,
    candidate_value: Any,
    rules: Rules,
) -> None:
    path = _format_path(path_parts)
    if _matches_any(path_parts, rules.ignore_paths):
        return
    severity = "warning" if change_type in {"added", "removed", "changed"} else "blocking"
    overridden = _lookup_severity_override(path_parts, rules.severity_overrides)
    if overridden is not None:
        severity = overridden
    if severity == "blocking" and _matches_any(path_parts, rules.allowed_exceptions):
        severity = "warning"

    reason = _build_reason(path, change_type)
    if _matches_any(path_parts, rules.allowed_exceptions):
        reason = f"{reason} An allowed exception applies."

    findings.append(
        {
            "path": path,
            "change_type": change_type,
            "baseline_value": baseline_value,
            "candidate_value": candidate_value,
            "severity": severity,
            "reason": reason,
        }
    )


def _lookup_severity_override(
    path_parts: tuple[Any, ...],
    severity_overrides: tuple[tuple[tuple[str, ...], str], ...],
) -> str | None:
    for rule_path, severity in severity_overrides:
        if _path_is_prefix(rule_path, path_parts):
            return severity
    return None


def _matches_any(path_parts: tuple[Any, ...], rule_paths: tuple[tuple[str, ...], ...]) -> bool:
    return any(_path_is_prefix(rule_path, path_parts) for rule_path in rule_paths)


def _path_is_prefix(rule_path: tuple[str, ...], path_parts: tuple[Any, ...]) -> bool:
    if len(rule_path) > len(path_parts):
        return False
    for index, part in enumerate(rule_path):
        if part != str(path_parts[index]):
            return False
    return True


def _count_findings(findings: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    counts = {"informational": 0, "warning": 0, "blocking": 0, "total_findings": 0}
    for finding in findings:
        severity = str(finding.get("severity", "warning"))
        if severity not in counts:
            severity = "warning"
        counts[severity] += 1
        counts["total_findings"] += 1
    return counts


def _classify_status(counts: Mapping[str, int], *, fail_on: str) -> str:
    normalized_fail_on = fail_on.lower()
    if normalized_fail_on not in {"warning", "blocking"}:
        raise DriftRuntimeError("--fail-on must be warning or blocking")
    if counts.get("blocking", 0):
        return "fail"
    if normalized_fail_on == "warning" and counts.get("warning", 0):
        return "fail"
    if counts.get("warning", 0):
        return "review_required"
    return "pass"


def _combine_input_formats(baseline_format: str, candidate_format: str) -> str:
    if baseline_format == candidate_format:
        return baseline_format
    return "mixed"


def _build_summary(status: str, counts: Mapping[str, int]) -> str:
    blocking = counts.get("blocking", 0)
    warning = counts.get("warning", 0)
    if status == "pass":
        return "No meaningful config drift was found."
    if status == "review_required":
        return f"Found {warning} review-worthy change(s) and no blocking drift."
    if blocking:
        return f"Found {blocking} blocking change(s), so promotion should stop."
    return "The input could not be trusted well enough to make a safe promotion decision."


def _build_reason(path: str, change_type: str) -> str:
    if change_type == "added":
        return f"{path} was added in the candidate configuration."
    if change_type == "removed":
        return f"{path} was removed from the candidate configuration."
    if change_type == "type_changed":
        return f"{path} changed type between baseline and candidate."
    return f"{path} changed value between baseline and candidate."


def _parse_path_spec(path: str) -> tuple[str, ...]:
    if path == "$":
        return ()
    if not path:
        raise DriftRuntimeError("Path rules cannot be empty")

    parts: list[str] = []
    token = []
    index = 0
    while index < len(path):
        char = path[index]
        if char == ".":
            if not token:
                raise DriftRuntimeError(f"Invalid path {path!r}")
            parts.append("".join(token))
            token = []
            index += 1
            continue
        if char == "[":
            if token:
                parts.append("".join(token))
                token = []
            end_index = path.find("]", index)
            if end_index == -1:
                raise DriftRuntimeError(f"Invalid path {path!r}")
            index_text = path[index + 1 : end_index]
            if not index_text.isdigit():
                raise DriftRuntimeError(f"Invalid list index in path {path!r}")
            parts.append(index_text)
            index = end_index + 1
            if index < len(path) and path[index] == ".":
                index += 1
            continue
        token.append(char)
        index += 1

    if token:
        parts.append("".join(token))
    if not parts:
        raise DriftRuntimeError(f"Invalid path {path!r}")
    return tuple(parts)


def _format_path(path_parts: tuple[Any, ...]) -> str:
    if not path_parts:
        return "$"
    rendered = ""
    for part in path_parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered = part if not rendered else f"{rendered}.{part}"
    return rendered
