#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import isoformat_z, load_json, read_now, resolve_factory_root, schema_path, timestamp_token, validate_json_document, write_json


REPORT_SCHEMA_NAME = "startup-benchmark-report.schema.json"
REPORT_SCHEMA_VERSION = "startup-benchmark-report/v1"
SOURCE_TRACE_SCHEMA_VERSION = "startup-benchmark-source-trace/v1"
BENCHMARK_PREFIX = "factory-root-startup-benchmark"
STARTUP_DATE_FORMAT = "%B %-d, %Y"

SOURCE_TRACE_ORDER: tuple[tuple[str, str], ...] = (
    ("AGENTS.md", "root startup instructions"),
    ("README.md", "root operator tooling and startup guidance"),
    (
        "docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md",
        "factory autonomy workflow baseline",
    ),
    (
        "docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md",
        "factory autonomy state baseline",
    ),
    ("registry/templates.json", "canonical template portfolio state"),
    ("registry/build-packs.json", "canonical build-pack portfolio state"),
    ("registry/promotion-log.json", "recent factory workflow motion"),
    (".pack-state/agent-memory/latest-memory.json", "factory restart memory pointer"),
)


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _benchmark_id() -> str:
    return f"{BENCHMARK_PREFIX}-{timestamp_token(read_now())}"


def _benchmark_root(factory_root: Path, benchmark_id: str) -> Path:
    return factory_root / ".pack-state" / "startup-benchmarks" / benchmark_id


def _format_startup_date() -> str:
    try:
        return read_now().strftime(STARTUP_DATE_FORMAT)
    except ValueError:
        return read_now().strftime("%B %d, %Y").replace(" 0", " ")


def _score_dimension(*, score: float | None, status: str, summary: str, evidence_paths: list[str], details: list[str]) -> dict[str, Any]:
    return {
        "status": status,
        "score": score,
        "summary": summary,
        "evidence_paths": evidence_paths,
        "details": details,
    }


def _extract_timestamp_token(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(20[0-9]{6}t[0-9]{6}z)", value)
    if match:
        token = match.group(1)
        return f"{token[:4]}-{token[4:6]}-{token[6:8]} {token[9:11]}:{token[11:13]}:{token[13:15]}Z"
    return None


def _load_root_memory(factory_root: Path) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    pointer_path = factory_root / ".pack-state" / "agent-memory" / "latest-memory.json"
    if not pointer_path.exists():
        return None, None
    pointer = _load_object(pointer_path)
    selected_memory_path = pointer.get("selected_memory_path")
    if not isinstance(selected_memory_path, str) or not selected_memory_path:
        return pointer, None
    memory_path = Path(selected_memory_path)
    if not memory_path.is_absolute():
        memory_path = factory_root / selected_memory_path
    if not memory_path.exists():
        return pointer, None
    return pointer, _load_object(memory_path)


def _load_source_trace(factory_root: Path) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for order, (relative_path, purpose) in enumerate(SOURCE_TRACE_ORDER, start=1):
        path = factory_root / relative_path
        status = "loaded" if path.exists() else "missing"
        trace.append(
            {
                "order": order,
                "path": str(path),
                "relative_path": relative_path,
                "purpose": purpose,
                "status": status,
            }
        )
    return trace


def _load_deployment_pointers(factory_root: Path) -> list[dict[str, Any]]:
    pointers: list[dict[str, Any]] = []
    for environment_dir in sorted((factory_root / "deployments").iterdir()):
        if not environment_dir.is_dir():
            continue
        environment = environment_dir.name
        for pointer_path in sorted(environment_dir.glob("*.json")):
            pointers.append(
                {
                    "environment": environment,
                    "path": str(pointer_path),
                    "payload": _load_object(pointer_path),
                }
            )
    return pointers


def _priority_bands(build_pack_entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    bands: dict[str, list[dict[str, Any]]] = {
        "high_priority": [],
        "medium_priority": [],
        "worth_watching": [],
        "historical_baseline": [],
    }
    for entry in build_pack_entries:
        if entry.get("active") is not True:
            bands["historical_baseline"].append(entry)
            continue
        deployment_state = entry.get("deployment_state")
        ready_for_deployment = entry.get("ready_for_deployment") is True
        lifecycle_stage = entry.get("lifecycle_stage")
        if deployment_state in {"production", "staging"}:
            bands["high_priority"].append(entry)
        elif deployment_state == "testing" or ready_for_deployment:
            bands["medium_priority"].append(entry)
        elif lifecycle_stage == "testing":
            bands["worth_watching"].append(entry)
        else:
            bands["medium_priority"].append(entry)
    return bands


def _pack_phrase(entry: dict[str, Any]) -> str:
    pack_id = cast(str, entry.get("pack_id", "unknown-pack"))
    deployment_state = cast(str, entry.get("deployment_state", "not_deployed"))
    ready = bool(entry.get("ready_for_deployment"))
    if deployment_state == "production":
        return f"{pack_id} is the live path in production."
    if deployment_state == "staging":
        return f"{pack_id} is the main staging path."
    if deployment_state == "testing":
        return f"{pack_id} is the main testing path."
    if ready:
        return f"{pack_id} is ready for the next deployment step."
    return f"{pack_id} is still proving itself."


def _recent_motion(events: list[dict[str, Any]], limit: int = 5) -> list[str]:
    lines: list[str] = []
    for event in events[-limit:]:
        event_type = cast(str, event.get("event_type", "updated"))
        pack_id = cast(str, event.get("target_build_pack_id", event.get("pack_id", "factory-state")))
        timestamp = (
            _extract_timestamp_token(cast(str | None, event.get("materialization_id")))
            or _extract_timestamp_token(cast(str | None, event.get("promotion_id")))
            or _extract_timestamp_token(cast(str | None, event.get("deployment_transaction_id")))
        )
        if timestamp:
            lines.append(f"{timestamp}: `{event_type}` `{pack_id}`.")
        else:
            lines.append(f"`{event_type}` `{pack_id}`.")
    return lines


def _build_startup_brief(
    *,
    build_pack_entries: list[dict[str, Any]],
    bands: dict[str, list[dict[str, Any]]],
    deployment_pointers: list[dict[str, Any]],
    memory: dict[str, Any] | None,
    recent_motion_lines: list[str],
) -> str:
    date_label = _format_startup_date()
    high = bands["high_priority"]
    medium = bands["medium_priority"]
    watching = bands["worth_watching"]
    historical = bands["historical_baseline"]
    what_matters_entry = high[0] if high else (medium[0] if medium else (watching[0] if watching else None))
    what_matters = _pack_phrase(what_matters_entry) if what_matters_entry else "No active build-pack path is currently standing out from the registry."
    live_now = [pointer["payload"].get("pack_id") for pointer in deployment_pointers if pointer["environment"] == "production"]
    testing_now = [pointer["payload"].get("pack_id") for pointer in deployment_pointers if pointer["environment"] == "testing"]
    ready_idle = [entry["pack_id"] for entry in medium if entry.get("deployment_state") == "not_deployed" and entry.get("ready_for_deployment") is True]

    lines = [
        f"# Factory-Root Startup Benchmark Brief",
        "",
        f"Generated from canonical startup surfaces on {date_label}.",
        "",
        "## What Matters Most Now",
        what_matters,
        "",
        "## Canonical Factory State",
        f"- High priority: {', '.join(entry['pack_id'] for entry in high) if high else 'none'}",
        f"- Medium priority: {', '.join(entry['pack_id'] for entry in medium) if medium else 'none'}",
        f"- Worth watching: {', '.join(entry['pack_id'] for entry in watching) if watching else 'none'}",
        f"- Historical baseline: {', '.join(entry['pack_id'] for entry in historical[:6]) if historical else 'none'}",
        f"- Live now: {', '.join(pack_id for pack_id in live_now if isinstance(pack_id, str)) if live_now else 'none'}",
        f"- Testing now: {', '.join(pack_id for pack_id in testing_now if isinstance(pack_id, str)) if testing_now else 'none'}",
        f"- Ready but unassigned: {', '.join(ready_idle) if ready_idle else 'none'}",
    ]
    if memory is not None:
        current_focus = memory.get("current_focus")
        if isinstance(current_focus, list):
            current_focus_text = ", ".join(item for item in current_focus if isinstance(item, str)) or "none recorded"
        elif isinstance(current_focus, str):
            current_focus_text = current_focus
        else:
            current_focus_text = "none recorded"
        lines.extend(
            [
                "",
                "## Agent Memory",
                f"- Current focus: {current_focus_text}",
                f"- Next action items: {', '.join(memory.get('next_action_items', [])) if isinstance(memory.get('next_action_items'), list) and memory.get('next_action_items') else 'none recorded'}",
                f"- Pending items: {', '.join(memory.get('pending_items', [])) if isinstance(memory.get('pending_items'), list) and memory.get('pending_items') else 'none recorded'}",
                f"- Overdue items: {', '.join(memory.get('overdue_items', [])) if isinstance(memory.get('overdue_items'), list) and memory.get('overdue_items') else 'none recorded'}",
                f"- Blockers: {', '.join(memory.get('blockers', [])) if isinstance(memory.get('blockers'), list) and memory.get('blockers') else 'none recorded'}",
                f"- Latest autonomy proof: {memory.get('latest_autonomy_proof') or 'none recorded'}",
                f"- Recommended next step: {memory.get('recommended_next_step') or 'none recorded'}",
            ]
        )
    lines.extend(
        [
            "",
            "## Recent Motion",
            *(f"- {line}" for line in recent_motion_lines),
            "",
            "## Practical Next Steps",
            "- Review the current startup benchmark score and close any weak dimension before changing the startup contract again.",
            "- Expand the cross-template transfer proof beyond config drift so the autonomy baseline is not treated as JSON-health-only.",
            "- Use the latest root memory as restart context, but keep registry, deployment, readiness, and promotion state as the truth layer.",
        ]
    )
    return "\n".join(lines) + "\n"


def _deployment_checks(factory_root: Path, build_pack_by_id: dict[str, dict[str, Any]], deployment_pointers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float]:
    checks: list[dict[str, Any]] = []
    passed = 0
    total = 0
    for pointer_entry in deployment_pointers:
        total += 1
        environment = cast(str, pointer_entry["environment"])
        payload = cast(dict[str, Any], pointer_entry["payload"])
        pack_id = cast(str, payload.get("pack_id", ""))
        registry_entry = build_pack_by_id.get(pack_id)
        pack_root_relative = payload.get("pack_root")
        deployment_file = None
        deployment_status = "pass"
        details: list[str] = []
        if payload.get("environment") != environment:
            deployment_status = "fail"
            details.append(f"pointer environment={payload.get('environment')!r} folder environment={environment!r}")
        if registry_entry is None:
            deployment_status = "fail"
            details.append("pack not present in registry/build-packs.json")
        elif registry_entry.get("deployment_state") != environment:
            deployment_status = "fail"
            details.append(
                f"registry deployment_state={registry_entry.get('deployment_state')!r} pointer environment={environment!r}"
            )
        if isinstance(pack_root_relative, str) and pack_root_relative:
            pack_root = factory_root / pack_root_relative
            deployment_file = pack_root / "status" / "deployment.json"
            if not deployment_file.exists():
                deployment_status = "fail"
                details.append("pack-local status/deployment.json missing")
            else:
                deployment_payload = _load_object(deployment_file)
                if deployment_payload.get("pack_id") != pack_id or deployment_payload.get("active_environment") != environment:
                    deployment_status = "fail"
                    details.append("pack-local deployment state did not match deployment pointer")
        if deployment_status == "pass":
            passed += 1
        checks.append(
            {
                "status": deployment_status,
                "environment": environment,
                "pack_id": pack_id,
                "pointer_path": pointer_entry["path"],
                "pack_local_deployment_path": str(deployment_file) if deployment_file is not None else None,
                "details": details,
            }
        )
    score = round((passed / total) * 100.0, 2) if total else 100.0
    return checks, score


def run_factory_root_startup_benchmark(*, factory_root: Path) -> dict[str, Any]:
    benchmark_id = _benchmark_id()
    benchmark_root = _benchmark_root(factory_root, benchmark_id)
    benchmark_root.mkdir(parents=True, exist_ok=False)

    source_trace = _load_source_trace(factory_root)
    templates_registry = _load_object(factory_root / "registry/templates.json")
    build_packs_registry = _load_object(factory_root / "registry/build-packs.json")
    promotion_log = _load_object(factory_root / "registry/promotion-log.json")
    deployment_pointers = _load_deployment_pointers(factory_root)
    memory_pointer, memory = _load_root_memory(factory_root)

    build_pack_entries = cast(list[dict[str, Any]], build_packs_registry.get("entries", []))
    build_pack_by_id = {
        cast(str, entry.get("pack_id")): entry
        for entry in build_pack_entries
        if isinstance(entry, dict) and isinstance(entry.get("pack_id"), str)
    }
    bands = _priority_bands(build_pack_entries)
    recent_motion_lines = _recent_motion(cast(list[dict[str, Any]], promotion_log.get("events", [])))

    source_trace_path = benchmark_root / "source-trace.json"
    write_json(
        source_trace_path,
        {
            "schema_version": SOURCE_TRACE_SCHEMA_VERSION,
            "benchmark_id": benchmark_id,
            "generated_at": isoformat_z(read_now()),
            "sources": source_trace,
        },
    )

    startup_brief = _build_startup_brief(
        build_pack_entries=build_pack_entries,
        bands=bands,
        deployment_pointers=deployment_pointers,
        memory=memory,
        recent_motion_lines=recent_motion_lines,
    )
    startup_brief_path = benchmark_root / "startup-brief.md"
    startup_brief_path.write_text(startup_brief, encoding="utf-8")

    dimensions: dict[str, dict[str, Any]] = {}
    scored_values: list[float] = []

    loaded_count = sum(1 for source in source_trace if source["status"] == "loaded")
    source_score = round((loaded_count / len(source_trace)) * 100.0, 2) if source_trace else 0.0
    scored_values.append(source_score)
    dimensions["source_discipline_quality"] = _score_dimension(
        score=source_score,
        status="scored",
        summary="Scores whether the canonical root startup surfaces were loaded in the expected order.",
        evidence_paths=[str(source_trace_path)],
        details=[f"loaded_sources={loaded_count}", f"total_sources={len(source_trace)}"],
    )

    memory_required_fields = [
        "current_focus",
        "next_action_items",
        "pending_items",
        "overdue_items",
        "blockers",
        "latest_autonomy_proof",
        "recommended_next_step",
    ]
    if memory_pointer is not None and memory is not None:
        present_count = sum(1 for field in memory_required_fields if field in memory)
        memory_score = round((present_count / len(memory_required_fields)) * 100.0, 2)
        scored_values.append(memory_score)
        dimensions["memory_usage_quality"] = _score_dimension(
            score=memory_score,
            status="scored",
            summary="Scores whether root startup memory is present and structured enough to support an Agent Memory section.",
            evidence_paths=[
                str(factory_root / ".pack-state/agent-memory/latest-memory.json"),
                str((factory_root / cast(str, memory_pointer["selected_memory_path"])) if not Path(cast(str, memory_pointer["selected_memory_path"])).is_absolute() else Path(cast(str, memory_pointer["selected_memory_path"]))),
            ],
            details=[f"present_fields={present_count}", f"required_fields={len(memory_required_fields)}"],
        )
    else:
        dimensions["memory_usage_quality"] = _score_dimension(
            score=None,
            status="not_applicable",
            summary="Root memory pointer was missing, so startup memory usage was not scored.",
            evidence_paths=[],
            details=[],
        )

    high_priority_ids = [cast(str, entry["pack_id"]) for entry in bands["high_priority"]]
    medium_priority_ids = [cast(str, entry["pack_id"]) for entry in bands["medium_priority"]]
    watching_ids = [cast(str, entry["pack_id"]) for entry in bands["worth_watching"]]
    priority_score = 100.0
    priority_details: list[str] = []
    if high_priority_ids and high_priority_ids[0] not in startup_brief:
        priority_score -= 30.0
        priority_details.append("highest-priority pack was missing from generated startup brief")
    if not high_priority_ids:
        priority_score -= 10.0
        priority_details.append("no high-priority production or staging path was present in the registry")
    if not medium_priority_ids:
        priority_score -= 10.0
        priority_details.append("no medium-priority testing or ready path was present in the registry")
    if not watching_ids:
        priority_details.append("no worth-watching testing-only path was present in the registry")
    priority_score = max(priority_score, 0.0)
    scored_values.append(priority_score)
    dimensions["priority_ordering_quality"] = _score_dimension(
        score=priority_score,
        status="scored",
        summary="Scores whether the generated startup brief reflects a registry-first priority order instead of a flat pack listing.",
        evidence_paths=[str(startup_brief_path), str(factory_root / "registry/build-packs.json")],
        details=priority_details,
    )

    deployment_checks, environment_score = _deployment_checks(factory_root, build_pack_by_id, deployment_pointers)
    scored_values.append(environment_score)
    dimensions["environment_fail_closed_quality"] = _score_dimension(
        score=environment_score,
        status="scored",
        summary="Scores whether deployment pointers, registry state, and pack-local deployment state agree across current environments.",
        evidence_paths=[item["path"] for item in deployment_pointers],
        details=[
            f"{check['pack_id']}@{check['environment']} status={check['status']}"
            for check in deployment_checks
        ],
    )

    operator_checks = [
        "## What Matters Most Now",
        "## Canonical Factory State",
        "## Recent Motion",
        "## Practical Next Steps",
    ]
    if memory is not None:
        operator_checks.append("## Agent Memory")
    present_sections = sum(1 for marker in operator_checks if marker in startup_brief)
    operator_score = round((present_sections / len(operator_checks)) * 100.0, 2)
    scored_values.append(operator_score)
    dimensions["operator_usefulness_quality"] = _score_dimension(
        score=operator_score,
        status="scored",
        summary="Scores whether the generated startup brief contains the expected operator-facing sections and next-step guidance.",
        evidence_paths=[str(startup_brief_path)],
        details=[f"present_sections={present_sections}", f"expected_sections={len(operator_checks)}"],
    )

    overall_score = round(sum(scored_values) / len(scored_values), 2) if scored_values else 0.0
    if overall_score >= 90.0:
        overall_rating = "strong"
    elif overall_score >= 75.0:
        overall_rating = "good"
    elif overall_score >= 60.0:
        overall_rating = "mixed"
    else:
        overall_rating = "weak"

    findings: list[str] = []
    for name, dimension in dimensions.items():
        score = dimension.get("score")
        if isinstance(score, (int, float)) and float(score) < 80.0:
            findings.append(f"{name} scored below 80")

    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "benchmark_id": benchmark_id,
        "generated_at": isoformat_z(read_now()),
        "startup_brief_path": str(startup_brief_path),
        "source_trace_path": str(source_trace_path),
        "overall_score": overall_score,
        "overall_rating": overall_rating,
        "dimensions": dimensions,
        "findings": findings,
        "high_priority_pack_ids": high_priority_ids,
        "medium_priority_pack_ids": medium_priority_ids,
        "worth_watching_pack_ids": watching_ids,
        "historical_baseline_pack_ids": [cast(str, entry["pack_id"]) for entry in bands["historical_baseline"]],
        "deployment_checks": deployment_checks,
        "what_matters_most": startup_brief.splitlines()[5] if len(startup_brief.splitlines()) > 5 else "",
    }
    report_path = benchmark_root / "benchmark-report.json"
    write_json(report_path, report)
    errors = validate_json_document(report_path, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if errors:
        raise ValueError("; ".join(errors))
    return {
        "status": "completed",
        "benchmark_id": benchmark_id,
        "report_path": str(report_path),
        "startup_brief_path": str(startup_brief_path),
        "source_trace_path": str(source_trace_path),
        "overall_score": overall_score,
        "overall_rating": overall_rating,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a deterministic PackFactory root startup benchmark.")
    parser.add_argument("--factory-root", required=True)
    parser.add_argument("--output", choices=("json",), default="json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = run_factory_root_startup_benchmark(factory_root=resolve_factory_root(args.factory_root))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
