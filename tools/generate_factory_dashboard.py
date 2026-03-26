#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, cast

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from factory_ops import (
    DEPLOYMENT_ENVIRONMENTS,
    discover_environment_assignment,
    isoformat_z,
    load_json,
    read_now,
    relative_path,
    resolve_factory_root,
    schema_path,
    timestamp_token,
    validate_json_document,
    write_json,
)


DASHBOARD_PREFIX = "factory-dashboard-build"
SNAPSHOT_SCHEMA_NAME = "factory-dashboard-snapshot.schema.json"
SNAPSHOT_SCHEMA_VERSION = "factory-dashboard-snapshot/v1"
REPORT_SCHEMA_NAME = "factory-dashboard-report.schema.json"
REPORT_SCHEMA_VERSION = "factory-dashboard-report/v1"
FRESH_HOURS = 24
STALE_HOURS = 72
RECENT_MOTION_HOURS = 96
RECENT_MOTION_LIMIT = 8
CHECKLIST_PATTERN = re.compile(r"^- \[(?P<done>[ xX])\] (?P<text>.+)$")
TIMESTAMP_TOKEN_PATTERN = re.compile(r"(20[0-9]{6}t[0-9]{6}z)")

CSS_ASSET = """
:root {
  --bg: #f5f0e8;
  --panel: #fffaf2;
  --panel-strong: #f1e5d1;
  --ink: #1f1c18;
  --muted: #5d5446;
  --accent: #0f6b5b;
  --accent-soft: #d7efe8;
  --warn: #a65a1b;
  --warn-soft: #f7e3d1;
  --danger: #922b21;
  --danger-soft: #f8d9d4;
  --line: #d7cbb6;
  --canonical: #0f6b5b;
  --advisory: #8a5a11;
  --derived: #375c8a;
  --shadow: 0 18px 40px rgba(38, 26, 9, 0.08);
  --radius: 18px;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(15, 107, 91, 0.09), transparent 32%),
    radial-gradient(circle at top right, rgba(166, 90, 27, 0.1), transparent 28%),
    var(--bg);
  line-height: 1.5;
}

a {
  color: var(--accent);
}

.shell {
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 18px 72px;
}

.masthead {
  background: linear-gradient(135deg, rgba(255, 250, 242, 0.96), rgba(241, 229, 209, 0.92));
  border: 1px solid var(--line);
  border-radius: calc(var(--radius) + 8px);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.masthead-inner {
  padding: 28px 28px 22px;
}

.eyebrow {
  display: inline-block;
  font-size: 0.82rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 10px;
}

h1, h2, h3 {
  font-family: "IBM Plex Serif", Georgia, serif;
  line-height: 1.15;
  margin: 0;
}

h1 {
  font-size: clamp(2rem, 4vw, 3.3rem);
}

.lede {
  color: var(--muted);
  font-size: 1rem;
  margin: 14px 0 0;
  max-width: 72ch;
}

.build-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 18px;
}

.meta-pill,
.truth-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  padding: 7px 12px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.72);
  font-size: 0.92rem;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 0 28px 24px;
}

.filter-button {
  appearance: none;
  border: 1px solid var(--line);
  background: var(--panel);
  color: var(--ink);
  border-radius: 999px;
  padding: 9px 14px;
  cursor: pointer;
  font: inherit;
}

.filter-button.is-active {
  background: var(--accent-soft);
  border-color: var(--accent);
}

.layout {
  display: grid;
  gap: 18px;
  margin-top: 22px;
}

.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 22px;
}

.panel h2 {
  font-size: 1.55rem;
  margin-bottom: 12px;
}

.panel p.section-note {
  margin: 0 0 14px;
  color: var(--muted);
}

.card-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.card {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  padding: 16px;
}

.card[data-truth-layer="advisory"] {
  border-color: rgba(138, 90, 17, 0.35);
  background: #fff8ef;
}

.card[data-truth-layer="derived"] {
  border-color: rgba(55, 92, 138, 0.32);
  background: #f6f8fc;
}

.card[data-status="mismatch"],
.card[data-status="fail"],
.card[data-status="stale"] {
  background: var(--danger-soft);
  border-color: rgba(146, 43, 33, 0.35);
}

.card[data-status="warning"],
.card[data-status="aging"] {
  background: var(--warn-soft);
  border-color: rgba(166, 90, 27, 0.35);
}

.card-title {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.card-title h3 {
  font-size: 1.02rem;
  flex: 1 1 auto;
}

.card p {
  margin: 0;
}

.status-chip {
  display: inline-block;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 0.8rem;
  border: 1px solid var(--line);
  color: var(--muted);
}

.source-line {
  margin-top: 10px;
  font-size: 0.84rem;
  color: var(--muted);
}

.detail-list,
.bullet-list {
  margin: 12px 0 0;
  padding-left: 18px;
}

.detail-list li,
.bullet-list li {
  margin: 4px 0;
}

.portfolio-bands {
  display: grid;
  gap: 14px;
}

.band {
  border-top: 1px solid var(--line);
  padding-top: 14px;
}

.band:first-child {
  border-top: 0;
  padding-top: 0;
}

.band h3 {
  font-size: 1rem;
  margin-bottom: 10px;
}

.motion-list {
  display: grid;
  gap: 10px;
}

.motion-item {
  border-left: 4px solid var(--accent);
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.72);
  border-radius: 0 12px 12px 0;
}

.hidden-by-filter {
  display: none !important;
}

@media (max-width: 720px) {
  .shell {
    padding: 18px 12px 48px;
  }

  .masthead-inner,
  .toolbar,
  .panel {
    padding-left: 16px;
    padding-right: 16px;
  }
}
""".strip()

JS_ASSET = """
(() => {
  const buttons = Array.from(document.querySelectorAll("[data-filter]"));
  const cards = Array.from(document.querySelectorAll("[data-truth-layer]"));
  if (!buttons.length || !cards.length) {
    return;
  }

  const applyFilter = (value) => {
    buttons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.filter === value);
    });
    cards.forEach((card) => {
      const truthLayer = card.dataset.truthLayer || "";
      const hidden = value !== "all" && truthLayer !== value;
      card.classList.toggle("hidden-by-filter", hidden);
    });
  };

  buttons.forEach((button) => {
    button.addEventListener("click", () => applyFilter(button.dataset.filter || "all"));
  });

  applyFilter("all");
})();
""".strip()


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: JSON document must contain an object")
    return cast(dict[str, Any], payload)


def _track_source(source_trace: list[dict[str, str]], path: Path, source_kind: str, status: str) -> None:
    source_trace.append(
        {
            "path": str(path.resolve()),
            "kind": source_kind,
            "status": status,
        }
    )


def _load_required_object(path: Path, source_trace: list[dict[str, str]], source_kind: str) -> dict[str, Any]:
    if not path.exists():
        _track_source(source_trace, path, source_kind, "missing")
        raise FileNotFoundError(path)
    try:
        payload = _load_object(path)
    except Exception:
        _track_source(source_trace, path, source_kind, "error")
        raise
    _track_source(source_trace, path, source_kind, "loaded")
    return payload


def _load_optional_object(path: Path, source_trace: list[dict[str, str]], source_kind: str) -> dict[str, Any] | None:
    if not path.exists():
        _track_source(source_trace, path, source_kind, "missing")
        return None
    try:
        payload = _load_object(path)
    except Exception:
        _track_source(source_trace, path, source_kind, "error")
        raise
    _track_source(source_trace, path, source_kind, "loaded")
    return payload


def _dashboard_build_id() -> str:
    return f"{DASHBOARD_PREFIX}-{timestamp_token(read_now())}"


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _extract_timestamp_token(value: str | None) -> datetime | None:
    if not value:
        return None
    match = TIMESTAMP_TOKEN_PATTERN.search(value)
    if match is None:
        return None
    token = match.group(1)
    try:
        return datetime.strptime(token, "%Y%m%dt%H%M%Sz").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _event_time(event: dict[str, Any]) -> datetime | None:
    for key in ("retired_at", "generated_at", "updated_at"):
        parsed = _parse_iso_datetime(cast(str | None, event.get(key)))
        if parsed is not None:
            return parsed
    for key in ("materialization_id", "promotion_id", "pipeline_id", "deployment_transaction_id"):
        parsed = _extract_timestamp_token(cast(str | None, event.get(key)))
        if parsed is not None:
            return parsed
    return None


def _hours_since(value: datetime | None) -> float | None:
    if value is None:
        return None
    return max((read_now() - value).total_seconds() / 3600.0, 0.0)


def _freshness_status(value: datetime | None) -> str:
    hours = _hours_since(value)
    if hours is None:
        return "unknown"
    if hours <= FRESH_HOURS:
        return "fresh"
    if hours <= STALE_HOURS:
        return "aging"
    return "stale"


def _band_name(entry: dict[str, Any]) -> str:
    if entry.get("active") is not True:
        return "historical_baseline"
    deployment_state = str(entry.get("deployment_state", "not_deployed"))
    ready = entry.get("ready_for_deployment") is True
    lifecycle_stage = str(entry.get("lifecycle_stage", "unknown"))
    if deployment_state in {"production", "staging"}:
        return "high_priority"
    if deployment_state == "testing" or ready:
        return "medium_priority"
    if lifecycle_stage == "testing":
        return "worth_watching"
    return "medium_priority"


def _summary_item(
    *,
    item_id: str,
    title: str,
    summary: str,
    source_kind: str,
    source_path: Iterable[str],
    truth_layer: str,
    details: Iterable[str] | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": item_id,
        "title": title,
        "summary": summary,
        "source_kind": source_kind,
        "source_path": sorted(set(source_path)),
        "truth_layer": truth_layer,
    }
    detail_list = [detail for detail in details or [] if detail]
    if detail_list:
        payload["details"] = detail_list
    if status:
        payload["status"] = status
    return payload


def _load_root_memory(factory_root: Path, source_trace: list[dict[str, str]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None, Path | None]:
    pointer_path = factory_root / ".pack-state" / "agent-memory" / "latest-memory.json"
    pointer = _load_optional_object(pointer_path, source_trace, "root_memory_pointer")
    if pointer is None:
        return None, None, None
    selected_memory_path = pointer.get("selected_memory_path")
    if not isinstance(selected_memory_path, str) or not selected_memory_path:
        return pointer, None, None
    memory_path = Path(selected_memory_path)
    if not memory_path.is_absolute():
        memory_path = factory_root / memory_path
    memory = _load_optional_object(memory_path, source_trace, "root_memory")
    return pointer, memory, memory_path if memory is not None else None


def _parse_planning_list(factory_root: Path, source_trace: list[dict[str, str]]) -> list[dict[str, Any]]:
    planning_path = factory_root / "docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md"
    if not planning_path.exists():
        _track_source(source_trace, planning_path, "planning_list", "missing")
        return []
    _track_source(source_trace, planning_path, "planning_list", "loaded")
    items: list[dict[str, Any]] = []
    current_section: str | None = None
    active_item: dict[str, Any] | None = None

    def flush_active_item() -> None:
        nonlocal active_item
        if active_item is None:
            return
        text = " ".join(active_item["parts"]).strip()
        if text:
            items.append(
                {
                    "section": active_item["section"],
                    "done": active_item["done"],
                    "text": text,
                    "source_path": str(planning_path.resolve()),
                }
            )
        active_item = None

    for raw_line in planning_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            flush_active_item()
            current_section = line[3:].strip()
            continue
        if current_section is None:
            continue
        stripped = line.strip()
        if not stripped:
            flush_active_item()
            continue
        match = CHECKLIST_PATTERN.match(stripped)
        if match is not None:
            flush_active_item()
            active_item = {
                "section": current_section,
                "done": match.group("done").lower() == "x",
                "parts": [match.group("text").strip()],
            }
            continue
        if active_item is not None:
            active_item["parts"].append(stripped)
    flush_active_item()
    return items


def _latest_startup_benchmark(factory_root: Path, source_trace: list[dict[str, str]]) -> dict[str, Any] | None:
    benchmark_root = factory_root / ".pack-state" / "startup-benchmarks"
    if not benchmark_root.exists():
        _track_source(source_trace, benchmark_root, "startup_benchmark_root", "missing")
        return None
    _track_source(source_trace, benchmark_root, "startup_benchmark_root", "loaded")
    candidates: list[tuple[str, Path, dict[str, Any]]] = []
    for report_path in benchmark_root.glob("*/benchmark-report.json"):
        try:
            report = _load_required_object(report_path, source_trace, "startup_benchmark_report")
        except Exception:
            continue
        generated_at = report.get("generated_at")
        if isinstance(generated_at, str):
            candidates.append((generated_at, report_path, report))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    _, report_path, report = candidates[-1]
    report["_report_path"] = str(report_path.resolve())
    return report


def _load_registry(factory_root: Path, relative: str, source_trace: list[dict[str, str]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _load_required_object(factory_root / relative, source_trace, "registry")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"{relative}: entries must be an array")
    return payload, cast(list[dict[str, Any]], entries)


def _pack_root(factory_root: Path, entry: dict[str, Any]) -> Path:
    pack_root = entry.get("pack_root")
    if isinstance(pack_root, str) and pack_root:
        return factory_root / pack_root
    pack_kind = str(entry.get("pack_kind", "build_pack"))
    pack_id = str(entry.get("pack_id", "unknown-pack"))
    directory = "templates" if pack_kind == "template_pack" else "build-packs"
    return factory_root / directory / pack_id


def _validation_status(readiness: dict[str, Any] | None) -> str:
    if readiness is None:
        return "missing"
    gates = readiness.get("required_gates", [])
    statuses = [
        str(gate.get("status"))
        for gate in gates
        if isinstance(gate, dict) and gate.get("gate_id") == "validate_build_pack_contract"
    ]
    if not statuses:
        return "unknown"
    if any(status in {"fail", "error"} for status in statuses):
        return "fail"
    if all(status == "pass" for status in statuses):
        return "pass"
    return "mixed"


def _benchmark_status(eval_index: dict[str, Any] | None) -> str:
    if eval_index is None:
        return "missing"
    results = eval_index.get("benchmark_results", [])
    statuses = [str(result.get("status")) for result in results if isinstance(result, dict) and isinstance(result.get("status"), str)]
    if not statuses:
        return "unknown"
    if any(status in {"fail", "error"} for status in statuses):
        return "fail"
    if all(status in {"pass", "completed"} for status in statuses):
        return "pass"
    return "mixed"


def _quality_summary_for_entry(factory_root: Path, entry: dict[str, Any], source_trace: list[dict[str, str]]) -> dict[str, Any]:
    pack_id = str(entry.get("pack_id", "unknown-pack"))
    pack_root = _pack_root(factory_root, entry)
    readiness_path = pack_root / "status/readiness.json"
    eval_path = pack_root / "eval/latest/index.json"
    readiness = _load_optional_object(readiness_path, source_trace, "pack_readiness")
    eval_index = _load_optional_object(eval_path, source_trace, "pack_eval_latest")
    source_paths = [
        str((factory_root / "registry/build-packs.json").resolve()),
    ]
    if readiness is not None:
        source_paths.append(str(readiness_path.resolve()))
    if eval_index is not None:
        source_paths.append(str(eval_path.resolve()))
    validation_status = _validation_status(readiness)
    benchmark_status = _benchmark_status(eval_index)
    blocking_issues = []
    if readiness is not None:
        blocking_issues = [
            str(issue)
            for issue in readiness.get("blocking_issues", [])
            if isinstance(issue, str) and issue.strip()
        ]
    readiness_state = str(readiness.get("readiness_state", "unknown")) if readiness is not None else "missing"
    ready_for_deployment = bool(readiness.get("ready_for_deployment")) if readiness is not None else False
    evidence_points = [
        _parse_iso_datetime(cast(str | None, readiness.get("last_evaluated_at"))) if readiness is not None else None,
        _parse_iso_datetime(cast(str | None, eval_index.get("updated_at"))) if eval_index is not None else None,
    ]
    evidence_points = [point for point in evidence_points if point is not None]
    latest_evidence_at = max(evidence_points) if evidence_points else None
    freshness_status = _freshness_status(latest_evidence_at)
    warnings: list[str] = []
    if readiness is None:
        warnings.append("Readiness state is missing.")
    if eval_index is None:
        warnings.append("Latest evaluation index is missing.")
    if blocking_issues:
        warnings.extend(blocking_issues)
    if validation_status == "fail":
        warnings.append("Validation evidence is failing.")
    if benchmark_status == "fail":
        warnings.append("Benchmark or workflow evidence is failing.")
    if freshness_status == "stale":
        warnings.append("Quality evidence is stale.")
    risk_status = "healthy"
    if validation_status == "fail" or benchmark_status == "fail":
        risk_status = "fail"
    elif freshness_status == "stale":
        risk_status = "stale"
    elif warnings:
        risk_status = "warning"
    evidence_label = latest_evidence_at.isoformat().replace("+00:00", "Z") if latest_evidence_at is not None else "unknown"
    summary = (
        f"Validation {validation_status}, benchmark/workflow {benchmark_status}, "
        f"readiness `{readiness_state}`, evidence {freshness_status} ({evidence_label})."
    )
    details = [
        f"ready_for_deployment={str(ready_for_deployment).lower()}",
        f"validation_status={validation_status}",
        f"benchmark_status={benchmark_status}",
        f"freshness_status={freshness_status}",
    ]
    return {
        "pack_id": pack_id,
        "summary_item": _summary_item(
            item_id=f"quality-{pack_id}",
            title=pack_id,
            summary=summary,
            source_kind="canonical",
            source_path=source_paths,
            truth_layer="canonical",
            details=details + warnings,
            status=risk_status,
        ),
        "warnings": warnings,
        "freshness_status": freshness_status,
        "risk_status": risk_status,
    }


def _recent_motion_items(factory_root: Path, promotion_log: dict[str, Any], source_trace: list[dict[str, str]]) -> list[dict[str, Any]]:
    events = promotion_log.get("events", [])
    if not isinstance(events, list):
        return []
    cutoff = read_now().timestamp() - RECENT_MOTION_HOURS * 3600
    candidates: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            continue
        event_time = _event_time(event)
        timestamp = event_time.timestamp() if event_time is not None else float(index)
        if event_time is not None and timestamp < cutoff:
            continue
        candidates.append((timestamp, event, event))
    candidates.sort(key=lambda item: item[0], reverse=True)
    recent = candidates[:RECENT_MOTION_LIMIT]
    results: list[dict[str, Any]] = []
    promotion_log_path = str((factory_root / "registry/promotion-log.json").resolve())
    for _, event, _raw in recent:
        event_type = str(event.get("event_type", "updated"))
        pack_id = (
            cast(str | None, event.get("target_build_pack_id"))
            or cast(str | None, event.get("retired_pack_id"))
            or cast(str | None, event.get("build_pack_id"))
            or "factory-state"
        )
        event_time = _event_time(event)
        if event_time is not None:
            stamp = event_time.isoformat().replace("+00:00", "Z")
        else:
            stamp = "timestamp unavailable"
        summary = f"{stamp}: `{event_type}` `{pack_id}`."
        source_paths = [promotion_log_path]
        for key in ("promotion_report_path", "materialization_report_path", "retirement_report_path"):
            value = event.get(key)
            if isinstance(value, str):
                source_paths.append(str((factory_root / value).resolve()))
        results.append(
            _summary_item(
                item_id=f"motion-{event_type}-{pack_id}-{len(results) + 1}",
                title=event_type.replace("_", " ").title(),
                summary=summary,
                source_kind="canonical",
                source_path=source_paths,
                truth_layer="canonical",
                status=event_type,
            )
        )
    return results


def _portfolio_item(factory_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    pack_id = str(entry.get("pack_id", "unknown-pack"))
    lifecycle_stage = str(entry.get("lifecycle_stage", "unknown"))
    deployment_state = str(entry.get("deployment_state", "not_deployed"))
    ready = entry.get("ready_for_deployment") is True
    if deployment_state == "production":
        summary = "Assigned to production now."
    elif deployment_state == "staging":
        summary = "Assigned to staging now."
    elif deployment_state == "testing":
        summary = "Assigned to testing now."
    elif ready:
        summary = "Ready for the next step but not assigned."
    elif lifecycle_stage == "testing":
        summary = "Still proving itself in testing."
    else:
        summary = f"Current lifecycle stage is `{lifecycle_stage}`."
    payload = _summary_item(
        item_id=f"portfolio-{pack_id}",
        title=pack_id,
        summary=summary,
        source_kind="canonical",
        source_path=[str((factory_root / "registry/build-packs.json").resolve())],
        truth_layer="canonical",
        details=[
            f"lifecycle_stage={lifecycle_stage}",
            f"deployment_state={deployment_state}",
            f"ready_for_deployment={str(ready).lower()}",
        ],
        status=deployment_state,
    )
    payload["lifecycle_stage"] = lifecycle_stage
    payload["deployment_state"] = deployment_state
    payload["ready_for_deployment"] = ready
    return payload


def _root_memory_items(memory: dict[str, Any] | None, memory_path: Path | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if memory is None or memory_path is None:
        return [], [], []
    source_path = [str(memory_path.resolve())]
    agent_items: list[dict[str, Any]] = []
    learning_items: list[dict[str, Any]] = []
    automation_items: list[dict[str, Any]] = []
    for field in (
        "current_focus",
        "next_action_items",
        "pending_items",
        "overdue_items",
        "blockers",
        "known_limits",
        "latest_autonomy_proof",
        "recommended_next_step",
    ):
        value = memory.get(field)
        if isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, str) and item.strip():
                    agent_items.append(
                        _summary_item(
                            item_id=f"agent-memory-{field}-{index + 1}",
                            title=field.replace("_", " ").title(),
                            summary=item,
                            source_kind="root_memory",
                            source_path=source_path,
                            truth_layer="advisory",
                            status="advisory",
                        )
                    )
        elif isinstance(value, str) and value.strip():
            agent_items.append(
                _summary_item(
                    item_id=f"agent-memory-{field}",
                    title=field.replace("_", " ").title(),
                    summary=value,
                    source_kind="root_memory",
                    source_path=source_path,
                    truth_layer="advisory",
                    status="advisory",
                )
            )
    for index, item in enumerate(memory.get("current_capabilities", [])):
        if isinstance(item, str) and item.strip():
            automation_items.append(
                _summary_item(
                    item_id=f"automation-capability-{index + 1}",
                    title="Current Capability",
                    summary=item,
                    source_kind="root_memory",
                    source_path=source_path,
                    truth_layer="advisory",
                    status="advisory",
                )
            )
    for field in ("current_focus", "recommended_next_step"):
        value = memory.get(field)
        if isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, str) and item.strip():
                    learning_items.append(
                        _summary_item(
                            item_id=f"factory-learning-{field}-{index + 1}",
                            title=field.replace("_", " ").title(),
                            summary=item,
                            source_kind="root_memory",
                            source_path=source_path,
                            truth_layer="advisory",
                            status="advisory",
                        )
                    )
        elif isinstance(value, str) and value.strip():
            learning_items.append(
                _summary_item(
                    item_id=f"factory-learning-{field}",
                    title=field.replace("_", " ").title(),
                    summary=value,
                    source_kind="root_memory",
                    source_path=source_path,
                    truth_layer="advisory",
                    status="advisory",
                )
            )
    return agent_items, learning_items, automation_items


def _ideas_items(planning_items: list[dict[str, Any]], memory: dict[str, Any] | None, memory_path: Path | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_actions = set()
    if isinstance(memory, dict):
        raw_next_actions = memory.get("next_action_items", [])
        if isinstance(raw_next_actions, list):
            next_actions = {item for item in raw_next_actions if isinstance(item, str)}
    for item in planning_items:
        if item["done"]:
            continue
        bucket = "candidate"
        if item["text"] in next_actions:
            bucket = "active_experiment"
        items.append(
            _summary_item(
                item_id=f"idea-{len(items) + 1}",
                title=item["section"],
                summary=f"[{bucket}] {item['text']}",
                source_kind="planning_list",
                source_path=[item["source_path"]],
                truth_layer="advisory",
                details=[f"bucket={bucket}"],
                status=bucket,
            )
        )
        if len(items) >= 6:
            break
    if not items and memory is not None and memory_path is not None:
        recommended = memory.get("recommended_next_step")
        if isinstance(recommended, str) and recommended.strip():
            items.append(
                _summary_item(
                    item_id="idea-memory-recommended-next-step",
                    title="Recommended Next Step",
                    summary=f"[active_experiment] {recommended}",
                    source_kind="root_memory",
                    source_path=[str(memory_path.resolve())],
                    truth_layer="advisory",
                    details=["bucket=active_experiment"],
                    status="active_experiment",
                )
            )
    return items


def _environment_board(factory_root: Path, build_entries: list[dict[str, Any]], source_trace: list[dict[str, str]]) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[str]]:
    registry_path = str((factory_root / "registry/build-packs.json").resolve())
    promotion_log_path = str((factory_root / "registry/promotion-log.json").resolve())
    cards: list[dict[str, Any]] = []
    assignment_by_environment: dict[str, dict[str, Any]] = {}
    mismatch_warnings: list[str] = []
    assigned_pack_ids: set[str] = set()
    for environment in ("production", "staging", "testing"):
        pointer_dir = factory_root / "deployments" / environment
        if pointer_dir.exists():
            _track_source(source_trace, pointer_dir, "deployment_pointer_dir", "loaded")
        else:
            _track_source(source_trace, pointer_dir, "deployment_pointer_dir", "missing")
        try:
            assignment = _discover_environment_assignment_for_dashboard(factory_root, environment)
        except Exception as exc:
            mismatch_warnings.append(str(exc))
            cards.append(
                {
                    "id": f"environment-{environment}",
                    "environment": "mismatch",
                    "label": environment.title(),
                    "title": environment.title(),
                    "summary": f"{environment.title()} assignment has a mismatch.",
                    "source_kind": "canonical",
                    "source_path": [str(pointer_dir.resolve()), registry_path, promotion_log_path],
                    "truth_layer": "canonical",
                    "details": [str(exc)],
                    "status": "mismatch",
                }
            )
            continue
        if assignment is None:
            cards.append(
                {
                    "id": f"environment-{environment}",
                    "environment": "not_assigned",
                    "label": environment.title(),
                    "title": environment.title(),
                    "summary": f"No pack is currently assigned to {environment}.",
                    "source_kind": "canonical",
                    "source_path": [str(pointer_dir.resolve()), registry_path],
                    "truth_layer": "canonical",
                    "details": ["The environment board has no current deployment pointer."],
                    "status": "not_assigned",
                }
            )
            continue
        assigned_pack_ids.add(assignment.pack_id)
        source_paths = [
            str(assignment.pointer_path.resolve()),
            str(assignment.deployment_path.resolve()),
            registry_path,
            str(assignment.promotion_report_path.resolve()),
        ]
        details = [
            f"pack_id={assignment.pack_id}",
            f"active_release_id={assignment.pointer_payload.get('active_release_id')}",
        ]
        cards.append(
            {
                "id": f"environment-{environment}",
                "environment": environment,
                "label": environment.title(),
                "title": environment.title(),
                "summary": f"{assignment.pack_id} is currently assigned to {environment}.",
                "source_kind": "canonical",
                "source_path": source_paths,
                "truth_layer": "canonical",
                "details": details,
                "status": environment,
            }
        )
        assignment_by_environment[environment] = cards[-1]
    ready_unassigned = sorted(
        str(entry.get("pack_id"))
        for entry in build_entries
        if entry.get("active") is True
        and entry.get("ready_for_deployment") is True
        and str(entry.get("pack_id")) not in assigned_pack_ids
        and str(entry.get("deployment_state", "not_deployed")) == "not_deployed"
    )
    not_assigned = sorted(
        str(entry.get("pack_id"))
        for entry in build_entries
        if entry.get("active") is True
        and str(entry.get("pack_id")) not in assigned_pack_ids
        and str(entry.get("pack_id")) not in ready_unassigned
        and str(entry.get("deployment_state", "not_deployed")) == "not_deployed"
    )
    board = {
        "title": "Environment Board",
        "source_kind": "canonical",
        "source_path": sorted(
            {
                registry_path,
                promotion_log_path,
                str((factory_root / "deployments").resolve()),
            }
        ),
        "truth_layer": "canonical",
        "cards": cards,
        "ready_unassigned_pack_ids": ready_unassigned,
        "not_assigned_pack_ids": not_assigned,
    }
    return board, assignment_by_environment, mismatch_warnings


def _discover_environment_assignment_for_dashboard(factory_root: Path, environment: str) -> Any | None:
    try:
        return discover_environment_assignment(factory_root, environment)
    except Exception as exc:
        if "promotion report is missing" not in str(exc):
            raise
        original_exc = exc

    pointer_dir = factory_root / "deployments" / environment
    pointer_paths = sorted(pointer_dir.glob("*.json")) if pointer_dir.exists() else []
    if len(pointer_paths) != 1:
        raise original_exc
    pointer_path = pointer_paths[0]
    pointer_payload = _load_object(pointer_path)
    pack_id = cast(str | None, pointer_payload.get("pack_id"))
    if not isinstance(pack_id, str) or not pack_id:
        raise ValueError(f"{relative_path(factory_root, pointer_path)}: pack_id is required")
    if pointer_payload.get("environment") != environment:
        raise ValueError(
            f"{relative_path(factory_root, pointer_path)}: pointer environment does not match target environment {environment}"
        )

    deployment_path = factory_root / "build-packs" / pack_id / "status" / "deployment.json"
    deployment_payload = _load_object(deployment_path)
    expected_pointer_relative_path = f"deployments/{environment}/{pack_id}.json"
    if deployment_payload.get("deployment_state") != environment:
        raise ValueError(
            f"{relative_path(factory_root, deployment_path)}: deployment_state does not match {environment}"
        )
    if deployment_payload.get("active_environment") != environment:
        raise ValueError(
            f"{relative_path(factory_root, deployment_path)}: active_environment does not match {environment}"
        )
    if deployment_payload.get("deployment_pointer_path") != expected_pointer_relative_path:
        raise ValueError(
            f"{relative_path(factory_root, deployment_path)}: deployment_pointer_path does not match {expected_pointer_relative_path}"
        )
    if deployment_payload.get("active_release_id") != pointer_payload.get("active_release_id"):
        raise ValueError(
            f"{relative_path(factory_root, deployment_path)}: active_release_id does not match deployment pointer"
        )

    build_registry = _load_object(factory_root / "registry/build-packs.json")
    entries = build_registry.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("registry/build-packs.json: entries must be an array")
    matching_entries = [entry for entry in entries if isinstance(entry, dict) and entry.get("pack_id") == pack_id]
    if len(matching_entries) != 1:
        raise ValueError(f"registry/build-packs.json: expected exactly one registry entry for {pack_id}")
    registry_entry = cast(dict[str, Any], matching_entries[0])
    if registry_entry.get("deployment_state") != environment:
        raise ValueError(f"registry/build-packs.json: {pack_id} deployment_state does not match {environment}")
    if registry_entry.get("deployment_pointer") != expected_pointer_relative_path:
        raise ValueError(
            f"registry/build-packs.json: {pack_id} deployment_pointer does not match {expected_pointer_relative_path}"
        )
    if registry_entry.get("active_release_id") != pointer_payload.get("active_release_id"):
        raise ValueError(f"registry/build-packs.json: {pack_id} active_release_id does not match deployment pointer")

    promotion_id = pointer_payload.get("deployment_transaction_id")
    promotion_report_relative_path = pointer_payload.get("promotion_evidence_ref")
    if not isinstance(promotion_id, str) or not promotion_id:
        raise ValueError(f"{relative_path(factory_root, pointer_path)}: deployment_transaction_id is required")
    if not isinstance(promotion_report_relative_path, str) or not promotion_report_relative_path:
        raise ValueError(f"{relative_path(factory_root, pointer_path)}: promotion_evidence_ref is required")
    promotion_log = _load_object(factory_root / "registry/promotion-log.json")
    events = promotion_log.get("events", [])
    if not isinstance(events, list):
        raise ValueError("registry/promotion-log.json: events must be an array")
    matching_events = [
        event
        for event in events
        if isinstance(event, dict)
        and event.get("event_type") == "promoted"
        and event.get("promotion_id") == promotion_id
        and event.get("build_pack_id") == pack_id
        and event.get("target_environment") == environment
        and event.get("promotion_report_path") == promotion_report_relative_path
    ]
    if len(matching_events) != 1:
        raise ValueError(
            f"canonical promotion evidence is inconsistent for {environment}: expected exactly one matching promoted event for {pack_id}"
        )

    promotion_report_path = factory_root / "build-packs" / pack_id / promotion_report_relative_path
    return SimpleNamespace(
        environment=environment,
        pack_id=pack_id,
        pointer_path=pointer_path,
        pointer_payload=pointer_payload,
        deployment_path=deployment_path,
        deployment_payload=deployment_payload,
        registry_entry=registry_entry,
        promotion_event=matching_events[0],
        promotion_report_path=promotion_report_path,
    )


def _what_matters_most(
    assignment_by_environment: dict[str, dict[str, Any]],
    quality_by_pack: dict[str, dict[str, Any]],
    ready_unassigned: list[str],
    recent_motion_items: list[dict[str, Any]],
) -> dict[str, Any]:
    def assigned_pack_id(card: dict[str, Any]) -> str | None:
        for detail in cast(list[str], card.get("details", [])):
            if detail.startswith("pack_id="):
                return detail.split("=", 1)[1]
        return None

    for environment in ("production", "staging", "testing"):
        card = assignment_by_environment.get(environment)
        if card is None:
            continue
        pack_id = assigned_pack_id(card)
        if card.get("environment") == "mismatch":
            return _summary_item(
                item_id=pack_id or f"what-matters-{environment}-mismatch",
                title=f"{environment.title()} Needs Attention",
                summary=card["summary"],
                source_kind=card["source_kind"],
                source_path=card["source_path"],
                truth_layer="canonical",
                details=card.get("details", []),
                status="mismatch",
            )
        if environment in {"production", "staging"}:
            return _summary_item(
                item_id=pack_id or f"what-matters-{environment}",
                title=f"{environment.title()} Is The Main Active Path",
                summary=card["summary"],
                source_kind=card["source_kind"],
                source_path=card["source_path"],
                truth_layer="canonical",
                details=card.get("details", []),
                status=environment,
            )
        testing_pack_id = pack_id
        if testing_pack_id and testing_pack_id in quality_by_pack:
            quality = quality_by_pack[testing_pack_id]
            if quality["risk_status"] in {"fail", "stale", "warning"}:
                return _summary_item(
                    item_id=testing_pack_id,
                    title="Testing Needs Attention",
                    summary=f"{testing_pack_id} is the current testing path and its quality evidence needs review.",
                    source_kind="derived",
                    source_path=quality["summary_item"]["source_path"] + card["source_path"],
                    truth_layer="derived",
                    details=quality["warnings"],
                    status=quality["risk_status"],
                )
            return _summary_item(
                item_id=testing_pack_id,
                title="Testing Is The Best Near-Term Bet",
                summary=card["summary"],
                source_kind="canonical",
                source_path=card["source_path"],
                truth_layer="canonical",
                details=card.get("details", []),
                status="testing",
            )
    for pack_id in ready_unassigned:
        quality = quality_by_pack.get(pack_id)
        if quality and quality["risk_status"] in {"fail", "stale", "warning"}:
            return _summary_item(
                item_id=pack_id,
                title="A Ready Pack Needs Evidence Attention",
                summary=f"{pack_id} is ready for the next step, but its quality evidence is not clean enough yet.",
                source_kind="derived",
                source_path=quality["summary_item"]["source_path"],
                truth_layer="derived",
                details=quality["warnings"],
                status=quality["risk_status"],
            )
    if recent_motion_items:
        motion = recent_motion_items[0]
        return _summary_item(
            item_id=str(motion.get("id", "what-matters-recent-motion")),
            title="Recent Motion Is The Main Fresh Signal",
            summary=motion["summary"],
            source_kind=motion["source_kind"],
            source_path=motion["source_path"],
            truth_layer=motion["truth_layer"],
            details=motion.get("details", []),
            status=motion.get("status", "recent"),
        )
    return _summary_item(
        item_id="what-matters-none",
        title="No Single Path Is Dominating",
        summary="The current factory state does not surface one dominant active path from canonical inputs alone.",
        source_kind="derived",
        source_path=[],
        truth_layer="derived",
        status="unknown",
    )


def _render_detail_list(items: Iterable[str]) -> str:
    values = [item for item in items if item]
    if not values:
        return ""
    rendered = "".join(f"<li>{html.escape(item)}</li>" for item in values)
    return f"<ul class=\"detail-list\">{rendered}</ul>"


def _render_cards(items: Iterable[dict[str, Any]]) -> str:
    cards: list[str] = []
    for item in items:
        truth_layer = str(item.get("truth_layer", "derived"))
        status = str(item.get("status", ""))
        source_paths = cast(list[str], item.get("source_path", []))
        source_line = ""
        if source_paths:
            source_line = f"<div class=\"source-line\">Source: {html.escape(relative_path(Path('/'), Path(source_paths[0])))}</div>"
        cards.append(
            (
                f"<article class=\"card\" data-truth-layer=\"{html.escape(truth_layer)}\" data-status=\"{html.escape(status)}\">"
                f"<div class=\"card-title\"><h3>{html.escape(str(item.get('title', 'Untitled')))}</h3>"
                f"<span class=\"status-chip\">{html.escape(truth_layer)}</span></div>"
                f"<p>{html.escape(str(item.get('summary', '')))}</p>"
                f"{_render_detail_list(cast(list[str], item.get('details', [])))}"
                f"{source_line}"
                "</article>"
            )
        )
    return "".join(cards)


def _render_section(section: dict[str, Any]) -> str:
    items = cast(list[dict[str, Any]], section.get("items", []))
    warnings = cast(list[str], section.get("warnings", []))
    warnings_block = ""
    if warnings:
        warnings_block = (
            "<div class=\"card-grid\">"
            + _render_cards(
                [
                    _summary_item(
                        item_id=f"warning-{index + 1}",
                        title="Warning",
                        summary=warning,
                        source_kind=section.get("source_kind", "derived"),
                        source_path=cast(list[str], section.get("source_path", [])),
                        truth_layer=section.get("truth_layer", "derived"),
                        status="warning",
                    )
                    for index, warning in enumerate(warnings)
                ]
            )
            + "</div>"
        )
    return (
        f"<section class=\"panel\"><h2>{html.escape(str(section.get('title', 'Section')))}</h2>"
        f"<div class=\"card-grid\">{_render_cards(items)}</div>{warnings_block}</section>"
    )


def _render_environment_board(board: dict[str, Any]) -> str:
    items = cast(list[dict[str, Any]], board.get("cards", []))
    extras = [
        _summary_item(
            item_id="environment-ready-unassigned",
            title="Ready For The Next Step",
            summary=", ".join(cast(list[str], board.get("ready_unassigned_pack_ids", []))) or "none",
            source_kind="canonical",
            source_path=cast(list[str], board.get("source_path", [])),
            truth_layer="canonical",
            status="ready_unassigned",
        ),
        _summary_item(
            item_id="environment-not-assigned",
            title="Not Currently Assigned",
            summary=", ".join(cast(list[str], board.get("not_assigned_pack_ids", []))) or "none",
            source_kind="canonical",
            source_path=cast(list[str], board.get("source_path", [])),
            truth_layer="canonical",
            status="not_assigned",
        ),
    ]
    return (
        f"<section class=\"panel\"><h2>{html.escape(str(board.get('title', 'Environment Board')))}</h2>"
        f"<div class=\"card-grid\">{_render_cards(items + extras)}</div></section>"
    )


def _render_recent_motion(section: dict[str, Any]) -> str:
    items = cast(list[dict[str, Any]], section.get("items", []))
    rendered = "".join(
        (
            f"<article class=\"motion-item\" data-truth-layer=\"{html.escape(str(item.get('truth_layer', 'derived')))}\">"
            f"<strong>{html.escape(str(item.get('title', 'Motion')))}</strong>"
            f"<p>{html.escape(str(item.get('summary', '')))}</p>"
            "</article>"
        )
        for item in items
    )
    return f"<section class=\"panel\"><h2>{html.escape(str(section.get('title', 'Recent Motion')))}</h2><div class=\"motion-list\">{rendered}</div></section>"


def _render_portfolio(section: dict[str, Any]) -> str:
    parts = []
    for band_name, label in (
        ("high_priority", "High Priority"),
        ("medium_priority", "Medium Priority"),
        ("worth_watching", "Worth Watching"),
        ("historical_baseline", "Historical Baseline"),
    ):
        items = cast(list[dict[str, Any]], section.get(band_name, []))
        parts.append(
            f"<div class=\"band\"><h3>{html.escape(label)}</h3><div class=\"card-grid\">{_render_cards(items)}</div></div>"
        )
    return f"<section class=\"panel\"><h2>{html.escape(str(section.get('title', 'Focused Portfolio')))}</h2><div class=\"portfolio-bands\">{''.join(parts)}</div></section>"


def _render_dashboard_html(snapshot: dict[str, Any]) -> str:
    generated_at = html.escape(str(snapshot["generated_at"]))
    build_id = html.escape(str(snapshot["dashboard_build_id"]))
    what_matters = cast(dict[str, Any], snapshot["what_matters_most"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PackFactory Dashboard</title>
  <link rel="stylesheet" href="assets/dashboard.css">
</head>
<body>
  <div class="shell">
    <header class="masthead">
      <div class="masthead-inner">
        <div class="eyebrow">What matters most now</div>
        <h1>{html.escape(str(what_matters.get("title", "What Matters Most Now")))}</h1>
        <p class="lede">{html.escape(str(what_matters.get("summary", "")))}</p>
        <div class="build-meta">
          <span class="meta-pill">Build {build_id}</span>
          <span class="meta-pill">Generated {generated_at}</span>
          <span class="truth-pill">Truth layer: canonical / advisory / derived</span>
        </div>
      </div>
      <div class="toolbar">
        <button class="filter-button is-active" data-filter="all" type="button">All layers</button>
        <button class="filter-button" data-filter="canonical" type="button">Canonical</button>
        <button class="filter-button" data-filter="advisory" type="button">Advisory</button>
        <button class="filter-button" data-filter="derived" type="button">Derived</button>
      </div>
    </header>
    <main class="layout">
      {_render_environment_board(cast(dict[str, Any], snapshot["environment_board"]))}
      {_render_section(cast(dict[str, Any], snapshot["quality_now"]))}
      {_render_section(cast(dict[str, Any], snapshot["automation_now"]))}
      {_render_section(cast(dict[str, Any], snapshot["factory_learning"]))}
      {_render_section(cast(dict[str, Any], snapshot["agent_memory"]))}
      {_render_section(cast(dict[str, Any], snapshot["ideas_lab"]))}
      {_render_recent_motion(cast(dict[str, Any], snapshot["recent_motion"]))}
      {_render_portfolio(cast(dict[str, Any], snapshot["focused_portfolio"]))}
    </main>
  </div>
  <script src="assets/dashboard.js"></script>
</body>
</html>
"""


def generate_factory_dashboard(*, factory_root: Path, output_dir: Path, publish_latest: bool = True) -> dict[str, Any]:
    source_trace: list[dict[str, str]] = []
    templates_registry, _template_entries = _load_registry(factory_root, "registry/templates.json", source_trace)
    build_registry, build_entries = _load_registry(factory_root, "registry/build-packs.json", source_trace)
    promotion_log = _load_required_object(factory_root / "registry/promotion-log.json", source_trace, "promotion_log")
    memory_pointer, root_memory, memory_path = _load_root_memory(factory_root, source_trace)
    planning_items = _parse_planning_list(factory_root, source_trace)
    startup_benchmark = _latest_startup_benchmark(factory_root, source_trace)

    dashboard_build_id = _dashboard_build_id()
    generated_at = isoformat_z(read_now())
    output_dir = output_dir.resolve()
    base_root = output_dir.parent if output_dir.name == "latest" else output_dir.parent
    history_root = base_root / "history"
    build_root = history_root / dashboard_build_id
    latest_root = output_dir
    if build_root.exists():
        shutil.rmtree(build_root)
    (build_root / "assets").mkdir(parents=True, exist_ok=True)

    env_board, assignment_by_environment, mismatch_warnings = _environment_board(factory_root, build_entries, source_trace)
    ready_unassigned = cast(list[str], env_board["ready_unassigned_pack_ids"])
    quality_pack_ids: list[str] = []
    for environment in ("production", "staging", "testing"):
        assignment = assignment_by_environment.get(environment)
        if assignment is None:
            continue
        for detail in cast(list[str], assignment.get("details", [])):
            if detail.startswith("pack_id="):
                quality_pack_ids.append(detail.split("=", 1)[1])
                break
    quality_pack_ids.extend(ready_unassigned)
    quality_pack_ids = sorted(set(pack_id for pack_id in quality_pack_ids if pack_id))

    build_entries_by_id = {
        str(entry.get("pack_id")): entry
        for entry in build_entries
        if isinstance(entry, dict) and isinstance(entry.get("pack_id"), str)
    }
    quality_items: list[dict[str, Any]] = []
    quality_warnings: list[str] = []
    quality_by_pack: dict[str, dict[str, Any]] = {}
    for pack_id in quality_pack_ids:
        entry = build_entries_by_id.get(pack_id)
        if entry is None:
            continue
        summary = _quality_summary_for_entry(factory_root, entry, source_trace)
        quality_items.append(summary["summary_item"])
        quality_warnings.extend(summary["warnings"])
        quality_by_pack[pack_id] = summary

    recent_motion_items = _recent_motion_items(factory_root, promotion_log, source_trace)
    agent_items, learning_items, automation_memory_items = _root_memory_items(root_memory, memory_path)
    idea_items = _ideas_items(planning_items, root_memory, memory_path)

    automation_items = automation_memory_items[:4]
    testing_assignment = assignment_by_environment.get("testing")
    if testing_assignment is not None and testing_assignment.get("environment") == "testing":
        automation_items.insert(
            0,
            _summary_item(
                item_id="automation-current-testing-path",
                title="Current Testing Path",
                summary=testing_assignment["summary"],
                source_kind="canonical",
                source_path=testing_assignment["source_path"],
                truth_layer="canonical",
                details=testing_assignment.get("details", []),
                status="testing",
            ),
        )

    focused_portfolio = {
        "title": "Focused Portfolio",
        "source_kind": "canonical",
        "source_path": [
            str((factory_root / "registry/build-packs.json").resolve()),
            str((factory_root / "registry/templates.json").resolve()),
        ],
        "truth_layer": "canonical",
        "high_priority": [],
        "medium_priority": [],
        "worth_watching": [],
        "historical_baseline": [],
    }
    for entry in build_entries:
        band = _band_name(entry)
        focused_portfolio[band].append(_portfolio_item(factory_root, entry))

    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "dashboard_build_id": dashboard_build_id,
        "generated_at": generated_at,
        "source_trace": source_trace,
        "what_matters_most": _what_matters_most(assignment_by_environment, quality_by_pack, ready_unassigned, recent_motion_items),
        "environment_board": env_board,
        "quality_now": {
            "title": "Quality Now",
            "source_kind": "canonical",
            "source_path": sorted(
                {
                    str((factory_root / "registry/build-packs.json").resolve()),
                    *[path for item in quality_items for path in cast(list[str], item.get("source_path", []))],
                }
            ),
            "truth_layer": "canonical",
            "items": quality_items,
            "warnings": sorted(set(quality_warnings)),
        },
        "automation_now": {
            "title": "Automation Now",
            "source_kind": "derived",
            "source_path": sorted(
                {
                    *([str(memory_path.resolve())] if memory_path is not None else []),
                    *(path for item in automation_items for path in cast(list[str], item.get("source_path", []))),
                }
            ),
            "truth_layer": "derived",
            "items": automation_items,
            "warnings": [],
        },
        "factory_learning": {
            "title": "Factory Learning",
            "source_kind": "derived",
            "source_path": sorted(
                {
                    *([str(memory_path.resolve())] if memory_path is not None else []),
                    *(path for item in learning_items for path in cast(list[str], item.get("source_path", []))),
                }
            ),
            "truth_layer": "derived",
            "items": learning_items[:6],
            "warnings": [],
        },
        "agent_memory": {
            "title": "Agent Memory",
            "source_kind": "root_memory",
            "source_path": [str(memory_path.resolve())] if memory_path is not None else [],
            "truth_layer": "advisory",
            "items": agent_items[:10],
            "warnings": [] if memory_pointer is not None else ["Root memory pointer is not available."],
        },
        "ideas_lab": {
            "title": "Ideas Lab",
            "source_kind": "derived",
            "source_path": sorted(
                {
                    *([str(memory_path.resolve())] if memory_path is not None else []),
                    *(path for item in idea_items for path in cast(list[str], item.get("source_path", []))),
                }
            ),
            "truth_layer": "advisory",
            "items": idea_items,
            "warnings": [] if idea_items else ["No deterministic idea items were surfaced from current advisory inputs."],
        },
        "recent_motion": {
            "title": "Recent Motion",
            "source_kind": "canonical",
            "source_path": [str((factory_root / "registry/promotion-log.json").resolve())],
            "truth_layer": "canonical",
            "items": recent_motion_items,
        },
        "focused_portfolio": focused_portfolio,
        "mismatch_warnings": mismatch_warnings,
    }

    snapshot_path = build_root / "dashboard-snapshot.json"
    write_json(snapshot_path, snapshot)
    snapshot_validation_errors = validate_json_document(snapshot_path, schema_path(factory_root, SNAPSHOT_SCHEMA_NAME))

    (build_root / "assets" / "dashboard.css").write_text(CSS_ASSET + "\n", encoding="utf-8")
    (build_root / "assets" / "dashboard.js").write_text(JS_ASSET + "\n", encoding="utf-8")
    (build_root / "index.html").write_text(_render_dashboard_html(snapshot), encoding="utf-8")

    startup_benchmark_comparison: dict[str, Any] | None = None
    if startup_benchmark is not None:
        startup_benchmark_comparison = {
            "available": True,
            "benchmark_report_path": startup_benchmark["_report_path"],
            "benchmark_id": startup_benchmark.get("benchmark_id"),
            "summary": (
                "The latest startup benchmark is available and the dashboard consolidates the same operator-summary "
                "inputs into one pre-rendered page."
            ),
        }

    report_path = build_root / "dashboard-report.json"
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "dashboard_build_id": dashboard_build_id,
        "generated_at": generated_at,
        "output_root": str(output_dir),
        "latest_output_root": str(latest_root),
        "latest_published": publish_latest,
        "publication_mode": "published_latest" if publish_latest else "history_only",
        "renderer": "python",
        "renderer_output_root": str(build_root),
        "history_build_root": str(build_root),
        "snapshot_path": str(snapshot_path),
        "index_path": str((build_root / "index.html")),
        "report_path": str(report_path),
        "asset_paths": [
            str(build_root / "assets" / "dashboard.css"),
            str(build_root / "assets" / "dashboard.js"),
        ],
        "renderer_artifact_paths": [
            str(build_root / "index.html"),
            str(build_root / "assets" / "dashboard.css"),
            str(build_root / "assets" / "dashboard.js"),
        ],
        "source_trace": source_trace,
        "source_count": len(source_trace),
        "mismatch_warning_count": len(mismatch_warnings),
        "mismatch_warnings": mismatch_warnings,
        "freshness_thresholds": {
            "fresh_hours": FRESH_HOURS,
            "stale_hours": STALE_HOURS,
            "recent_motion_hours": RECENT_MOTION_HOURS,
        },
        "ranking_rules": [
            "production mismatch or production assignment first",
            "staging mismatch or staging assignment second",
            "testing assignment with active blocker or stale evidence third",
            "ready-but-unassigned pack with missing or stale quality evidence fourth",
            "strongest recent proven improvement fifth",
        ],
        "summary_counts": {
            "high_priority": len(cast(list[dict[str, Any]], focused_portfolio["high_priority"])),
            "medium_priority": len(cast(list[dict[str, Any]], focused_portfolio["medium_priority"])),
            "worth_watching": len(cast(list[dict[str, Any]], focused_portfolio["worth_watching"])),
            "historical_baseline": len(cast(list[dict[str, Any]], focused_portfolio["historical_baseline"])),
            "ideas_lab": len(cast(list[dict[str, Any]], snapshot["ideas_lab"]["items"])),
        },
        "startup_benchmark_comparison": startup_benchmark_comparison,
        "validations": {
            "snapshot_schema": "pass" if not snapshot_validation_errors else "fail",
            "report_schema": "pass",
            "errors": snapshot_validation_errors[:],
        },
    }
    write_json(report_path, report)
    report_validation_errors = validate_json_document(report_path, schema_path(factory_root, REPORT_SCHEMA_NAME))
    if report_validation_errors:
        report["validations"]["report_schema"] = "fail"
        report["validations"]["errors"] = report["validations"]["errors"] + report_validation_errors
        write_json(report_path, report)

    if publish_latest:
        latest_tmp = latest_root.with_name(f"{latest_root.name}-tmp-{dashboard_build_id}")
        if latest_tmp.exists():
            shutil.rmtree(latest_tmp)
        shutil.copytree(build_root, latest_tmp)
        if latest_root.exists():
            shutil.rmtree(latest_root)
        latest_tmp.rename(latest_root)

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Python-native static PackFactory operator dashboard.")
    parser.add_argument("--factory-root", required=True, help="Absolute path to the PackFactory root.")
    parser.add_argument(
        "--output-dir",
        default="/home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest",
        help=(
            "Absolute path to the latest dashboard output directory. The generator always writes a versioned "
            "history build alongside it; use --skip-latest-publish to leave latest untouched."
        ),
    )
    parser.add_argument(
        "--skip-latest-publish",
        action="store_true",
        help="Write the immutable history build only and do not publish it into latest.",
    )
    parser.add_argument("--report-format", choices=("json", "text"), default="text")
    args = parser.parse_args()

    result = generate_factory_dashboard(
        factory_root=resolve_factory_root(args.factory_root),
        output_dir=Path(args.output_dir).expanduser().resolve(),
        publish_latest=not args.skip_latest_publish,
    )
    if args.report_format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Generated dashboard {result['dashboard_build_id']}")
        if args.skip_latest_publish:
            print(f"- latest output: not updated ({result['latest_output_root']})")
        else:
            print(f"- latest output: {result['latest_output_root']}")
        print(f"- snapshot: {result['snapshot_path']}")
        print(f"- report: {result['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
