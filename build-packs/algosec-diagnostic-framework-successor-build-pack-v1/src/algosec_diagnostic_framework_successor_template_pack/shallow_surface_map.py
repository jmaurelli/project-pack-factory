from __future__ import annotations

import json
import os
import platform
import re
import shlex
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .docpack_hints import load_docpack_hints


DEFAULT_ARTIFACT_ROOT = Path("dist/candidates/adf-shallow-surface-map-first-pass")
SURFACE_MAP_NAME = "shallow-surface-map.json"
SUMMARY_NAME = "shallow-surface-summary.md"
PRODUCT_HINTS = (
    "algosec",
    "asms",
    "afa",
    "appviz",
    "fireflow",
    "objectflow",
    "horizon",
    "ms-",
    "keycloak",
    "postgres",
    "activemq",
)
CONCRETE_DOCPACK_CATEGORIES = {
    "api_surface",
    "data_store",
    "edge_proxy",
    "identity_or_access",
    "integration_surface",
    "queue_or_messaging",
}
NOISY_DOCPACK_TERMS = {
    "about",
    "access",
    "accounts",
    "action",
    "activities",
    "add",
    "address",
    "after",
    "all",
    "auto",
    "automatic",
    "availability",
    "backup",
    "based",
    "check",
    "cloud",
    "configure",
    "connect",
    "data",
    "define",
    "device",
    "devices",
    "display",
    "download",
    "enable",
    "event",
    "example",
    "file",
    "files",
    "get",
    "home",
    "initial",
    "interfaces",
    "json",
    "key",
    "known",
    "list",
    "load",
    "manage",
    "messages",
    "network",
    "pen",
    "pre",
    "processing",
    "profiles",
    "project",
    "report",
    "retrieve",
    "search",
    "secure",
    "service",
    "specified",
    "upgrade",
}
GENERIC_DOCPACK_PORTS = {16, 25, 41, 42, 80, 423, 443, 8000, 8080}
CONFIG_PATH_RE = re.compile(r"(/[^\s\"']+\.(?:conf|cfg|ini|xml|yaml|yml|properties|json))")
LOG_PATH_RE = re.compile(r"(/[^\s\"']+(?:/logs?/[^\"'\s]+|/log/[^\"'\s]+|\.log(?:\.\d+)?))")


def generate_shallow_surface_map(
    *,
    project_root: Path,
    target_label: str,
    artifact_root: str | Path | None = None,
    docpack_hints_path: str | Path | None = None,
) -> dict[str, Any]:
    root = project_root / (Path(artifact_root) if artifact_root else DEFAULT_ARTIFACT_ROOT)
    root.mkdir(parents=True, exist_ok=True)

    runtime_identity = _collect_runtime_identity()
    command_results = _collect_command_results()
    docpack_hints = load_docpack_hints(project_root, docpack_hints_path)
    component_records = _build_component_records(command_results, docpack_hints=docpack_hints)
    next_candidate_seams = _build_next_candidate_seams(component_records)
    surface_map = {
        "schema_version": "adf-shallow-surface-map/v1",
        "generated_at": _isoformat_z(),
        "target": {
            "target_label": target_label,
            "hostname": runtime_identity["hostname"],
        },
        "artifact_contract": {
            "machine_readable_artifact": SURFACE_MAP_NAME,
            "operator_reviewable_artifact": SUMMARY_NAME,
        },
        "collection_policy": {
            "mode": "read_only",
            "fact_inference_boundary": "observed facts, tentative inference, and unknowns are kept separate",
            "command_scope": [
                "runtime_identity",
                "systemd_units",
                "systemd_unit_files",
                "listening_tcp_ports",
                "process_inventory",
            ],
            "out_of_scope": [
                "deep dependency mapping",
                "config file parsing",
                "log content interpretation",
                "predictive analysis",
                "write or mutation operations",
            ],
        },
        "runtime_identity": runtime_identity,
        "docpack_hint_ref": None
        if docpack_hints is None
        else {
            "loaded_from": docpack_hints.get("_loaded_from"),
            "docpack_id": docpack_hints.get("source", {}).get("docpack_id"),
            "version": docpack_hints.get("source", {}).get("version"),
        },
        "command_results": command_results,
        "component_records": component_records,
        "unknowns": _build_global_unknowns(command_results, component_records),
        "next_candidate_seams": next_candidate_seams,
    }
    summary = _render_summary(surface_map)

    _dump_json(root / SURFACE_MAP_NAME, surface_map)
    (root / SUMMARY_NAME).write_text(summary, encoding="utf-8")

    return {
        "status": "pass",
        "artifact_root": str(root.relative_to(project_root)),
        "generated_files": [
            str((root / SURFACE_MAP_NAME).relative_to(project_root)),
            str((root / SUMMARY_NAME).relative_to(project_root)),
        ],
        "summary": {
            "target_label": target_label,
            "component_count": len(component_records),
            "central_component_count": sum(1 for record in component_records if record["inference"]["appears_central"]),
            "candidate_seam_count": len(next_candidate_seams),
        },
    }


def _collect_runtime_identity() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "kernel_release": platform.release(),
        "platform": platform.platform(),
        "os_release": _load_os_release(),
    }


def _collect_command_results() -> list[dict[str, Any]]:
    return [
        _run_command(
            command_id="systemd_units",
            argv=["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"],
            max_preview_lines=250,
        ),
        _run_command(
            command_id="systemd_unit_files",
            argv=["systemctl", "list-unit-files", "--type=service", "--no-pager", "--plain", "--no-legend"],
            max_preview_lines=250,
        ),
        _run_command(
            command_id="listening_tcp_ports",
            argv=["ss", "-lntpH"],
            max_preview_lines=250,
        ),
        _run_command(
            command_id="process_inventory",
            argv=["ps", "-eo", "pid=,ppid=,user=,comm=,args="],
            max_preview_lines=250,
        ),
    ]


def _build_component_records(
    command_results: list[dict[str, Any]],
    *,
    docpack_hints: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    results_by_id = {entry["command_id"]: entry for entry in command_results}
    unit_states = _parse_systemd_units(results_by_id.get("systemd_units", {}))
    unit_file_states = _parse_unit_files(results_by_id.get("systemd_unit_files", {}))
    listeners = _parse_listeners(results_by_id.get("listening_tcp_ports", {}))
    processes = _parse_processes(results_by_id.get("process_inventory", {}))

    records: dict[str, dict[str, Any]] = {}
    for unit_name, unit_state in unit_states.items():
        records[unit_name] = {
            "component_id": unit_name.removesuffix(".service"),
            "display_name": unit_name.removesuffix(".service"),
            "observed": {
                "record_sources": ["systemd_unit"],
                "service_unit": unit_name,
                "active_state": unit_state["active_state"],
                "sub_state": unit_state["sub_state"],
                "unit_file_state": unit_file_states.get(unit_name),
                "description": unit_state["description"],
                "main_command": None,
                "process_name": None,
                "process_id": None,
                "listening_ports": [],
                "config_path_candidates": [],
                "log_path_candidates": [],
                "jvm_visibility": {
                    "detected": False,
                    "notes": [],
                },
                "source_command_ids": ["systemd_units", "systemd_unit_files"],
            },
            "inference": {},
            "unknowns": [],
        }

    for process in processes:
        record_key = _match_record_key(process["command"], process["comm"], records)
        if record_key is None:
            record_key = f"process-{process['pid']}"
            records[record_key] = {
                "component_id": record_key,
                "display_name": process["comm"],
                "observed": {
                    "record_sources": ["process_inventory"],
                    "service_unit": None,
                    "active_state": "unknown",
                    "sub_state": None,
                    "unit_file_state": None,
                    "description": None,
                    "main_command": process["command"],
                    "process_name": process["comm"],
                    "process_id": process["pid"],
                    "listening_ports": [],
                    "config_path_candidates": [],
                    "log_path_candidates": [],
                    "jvm_visibility": {
                        "detected": False,
                        "notes": [],
                    },
                    "source_command_ids": ["process_inventory"],
                },
                "inference": {},
                "unknowns": [],
            }

        observed = records[record_key]["observed"]
        if "process_inventory" not in observed["record_sources"]:
            observed["record_sources"].append("process_inventory")
        observed["process_name"] = observed["process_name"] or process["comm"]
        observed["process_id"] = observed["process_id"] or process["pid"]
        observed["main_command"] = observed["main_command"] or process["command"]
        observed["config_path_candidates"] = _merge_unique(
            observed["config_path_candidates"],
            _extract_paths(process["command"], CONFIG_PATH_RE),
        )
        observed["log_path_candidates"] = _merge_unique(
            observed["log_path_candidates"],
            _extract_paths(process["command"], LOG_PATH_RE),
        )
        if _looks_like_java_process(process["comm"], process["command"]):
            observed["jvm_visibility"] = {
                "detected": True,
                "notes": _build_jvm_notes(process["command"]),
            }

    for record in records.values():
        observed = record["observed"]
        listener_key_candidates = [
            observed["service_unit"] or "",
            record["display_name"],
            observed["process_name"] or "",
        ]
        observed["listening_ports"] = _merge_unique(
            observed["listening_ports"],
            _ports_for_candidates(listeners, listener_key_candidates),
        )

        docpack_matches = _match_docpack_hints(record=record, docpack_hints=docpack_hints)
        category, confidence, notes = _classify_record(record, docpack_matches=docpack_matches)
        priority_score = _priority_score(category, observed, docpack_matches=docpack_matches)
        record["inference"] = {
            "first_observed_category": category,
            "confidence": confidence,
            "appears_central": priority_score >= 5,
            "support_priority_score": priority_score,
            "docpack_matches": docpack_matches,
            "notes": notes,
        }
        record["unknowns"] = _build_record_unknowns(record)

    return sorted(
        records.values(),
        key=lambda item: (
            -item["inference"]["support_priority_score"],
            item["display_name"].lower(),
        ),
    )


def _parse_systemd_units(result: dict[str, Any]) -> dict[str, dict[str, str | None]]:
    units: dict[str, dict[str, str | None]] = {}
    if result.get("status") != "completed":
        return units
    for line in result.get("stdout", "").splitlines():
        parts = line.split(None, 4)
        if len(parts) < 4 or not parts[0].endswith(".service"):
            continue
        description = parts[4] if len(parts) > 4 else None
        units[parts[0]] = {
            "load_state": parts[1],
            "active_state": parts[2],
            "sub_state": parts[3],
            "description": description,
        }
    return units


def _parse_unit_files(result: dict[str, Any]) -> dict[str, str]:
    unit_files: dict[str, str] = {}
    if result.get("status") != "completed":
        return unit_files
    for line in result.get("stdout", "").splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].endswith(".service"):
            unit_files[parts[0]] = parts[1]
    return unit_files


def _parse_listeners(result: dict[str, Any]) -> dict[str, list[int]]:
    listeners: dict[str, list[int]] = {}
    if result.get("status") != "completed":
        return listeners
    for line in result.get("stdout", "").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        local_address = parts[3]
        port_text = local_address.rsplit(":", 1)[-1]
        if not port_text.isdigit():
            continue
        port = int(port_text)
        process_name = ""
        if 'users:((' in line:
            try:
                process_name = line.split('users:(("', 1)[1].split('"', 1)[0]
            except IndexError:
                process_name = ""
        if not process_name:
            process_name = parts[-1] if parts else "unknown"
        listeners.setdefault(process_name, [])
        if port not in listeners[process_name]:
            listeners[process_name].append(port)
    return listeners


def _parse_processes(result: dict[str, Any]) -> list[dict[str, Any]]:
    processes: list[dict[str, Any]] = []
    current_pid = os.getpid()
    if result.get("status") != "completed":
        return processes
    for line in result.get("stdout", "").splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) < 4 or not parts[0].isdigit():
            continue
        pid = int(parts[0])
        ppid = int(parts[1]) if parts[1].isdigit() else None
        comm = shlex.split(parts[3])[0] if parts[3] else parts[2]
        if pid == current_pid or comm == "ps":
            continue
        processes.append(
            {
                "pid": pid,
                "ppid": ppid,
                "user": parts[2],
                "comm": comm,
                "command": parts[3],
            }
        )
    return processes


def _match_record_key(command: str, comm: str, records: dict[str, dict[str, Any]]) -> str | None:
    lowered_command = command.lower()
    lowered_comm = comm.lower()
    for key, record in records.items():
        unit_name = (record["observed"]["service_unit"] or "").lower()
        display_name = record["display_name"].lower()
        if unit_name and unit_name.removesuffix(".service") in lowered_command:
            return key
        if display_name in lowered_command or display_name in lowered_comm:
            return key
    return None


def _extract_paths(command: str, pattern: re.Pattern[str]) -> list[str]:
    return sorted(set(match.group(1) for match in pattern.finditer(command)))


def _merge_unique(existing: list[Any], new_items: list[Any]) -> list[Any]:
    merged = list(existing)
    for item in new_items:
        if item not in merged:
            merged.append(item)
    return merged


def _looks_like_java_process(comm: str, command: str) -> bool:
    lowered = f"{comm} {command}".lower()
    return "java" in lowered or "-xmx" in lowered or "-djava" in lowered


def _build_jvm_notes(command: str) -> list[str]:
    notes = []
    for token in shlex.split(command):
        if token.startswith("-Xmx") or token.startswith("-Xms"):
            notes.append(token)
        if token.startswith("-D") and ("java" in token.lower() or "catalina" in token.lower()):
            notes.append(token)
    return notes[:8]


def _ports_for_candidates(listeners: dict[str, list[int]], candidates: list[str]) -> list[int]:
    ports: list[int] = []
    for candidate in candidates:
        candidate_lower = candidate.lower()
        if not candidate_lower:
            continue
        for process_name, process_ports in listeners.items():
            process_lower = process_name.lower()
            if candidate_lower in process_lower or process_lower in candidate_lower:
                for port in process_ports:
                    if port not in ports:
                        ports.append(port)
    return sorted(ports)


def _classify_record(
    record: dict[str, Any],
    *,
    docpack_matches: dict[str, Any],
) -> tuple[str, str, list[str]]:
    observed = record["observed"]
    haystack = " ".join(
        filter(
            None,
            [
                record["display_name"],
                observed["service_unit"],
                observed["description"],
                observed["process_name"],
                observed["main_command"],
            ],
        )
    ).lower()
    notes: list[str] = []
    docpack_categories = set(docpack_matches.get("categories", []))
    if "httpd" in haystack or "apache" in haystack:
        return "edge_proxy", "high", ["Edge-facing Apache/httpd service is visible."]
    if "postgres" in haystack:
        return "data_store", "high", ["PostgreSQL-like service or process name is visible."]
    if "activemq" in haystack or "rabbitmq" in haystack or "kafka" in haystack:
        return "queue_or_messaging", "high", ["Messaging-layer naming is visible."]
    if "keycloak" in haystack or "auth" in haystack:
        return "identity_or_access", "medium", ["Identity or auth-adjacent naming is visible."]
    if "edge_proxy" in docpack_categories:
        notes.extend(_docpack_match_notes(docpack_matches))
        return "edge_proxy", "medium", notes
    if "data_store" in docpack_categories:
        notes.extend(_docpack_match_notes(docpack_matches))
        return "data_store", "medium", notes
    if "queue_or_messaging" in docpack_categories:
        notes.extend(_docpack_match_notes(docpack_matches))
        return "queue_or_messaging", "medium", notes
    if "identity_or_access" in docpack_categories:
        notes.extend(_docpack_match_notes(docpack_matches))
        return "identity_or_access", "medium", notes
    if any(hint in haystack for hint in PRODUCT_HINTS):
        notes.append("AlgoSec product-family naming is visible in service or process metadata.")
        if observed["jvm_visibility"]["detected"]:
            notes.append("Java runtime hints are visible for this component.")
        return "application_service", "medium", notes
    if "application_service" in docpack_categories:
        notes.extend(_docpack_match_notes(docpack_matches))
        return "application_service", "low", notes
    if observed["jvm_visibility"]["detected"]:
        return "java_process", "low", ["Only Java runtime hints are visible so far."]
    if observed["service_unit"]:
        return "system_service", "low", ["Only generic systemd service evidence is visible so far."]
    return "standalone_process", "low", ["No stronger category evidence is visible yet."]


def _priority_score(category: str, observed: dict[str, Any], *, docpack_matches: dict[str, Any]) -> int:
    score = 0
    if observed["listening_ports"]:
        score += 3
    if observed["jvm_visibility"]["detected"]:
        score += 1
    if docpack_matches.get("matched_terms"):
        score += min(2, len(docpack_matches["matched_terms"]))
    if docpack_matches.get("matched_ports"):
        score += 1
    if category == "edge_proxy":
        score += 4
    elif category in {"application_service", "data_store", "queue_or_messaging", "identity_or_access"}:
        score += 2
    elif category == "java_process":
        score += 1
    return score


def _match_docpack_hints(record: dict[str, Any], docpack_hints: dict[str, Any] | None) -> dict[str, Any]:
    if docpack_hints is None:
        return {"matched_terms": [], "matched_ports": [], "categories": []}

    observed = record["observed"]
    haystack = _normalize_hint_text(
        " ".join(
            filter(
                None,
                [
                    record["display_name"],
                    observed["service_unit"],
                    observed["description"],
                    observed["process_name"],
                    observed["main_command"],
                ],
            )
        )
    )
    matched_terms = []
    categories: set[str] = set()
    for hint in docpack_hints.get("term_hints", []):
        if not isinstance(hint, dict) or not _is_signal_bearing_docpack_hint(hint):
            continue
        term = _normalize_hint_text(str(hint.get("normalized_term") or ""))
        if not term or len(term) < 3:
            continue
        if _term_matches_haystack(term, haystack):
            hint_categories = {
                str(category)
                for category in hint.get("categories", [])
                if str(category) != "surface_term"
            }
            matched_terms.append(
                {
                    "term": term,
                    "categories": sorted(hint_categories),
                    "product_areas": list(hint.get("product_areas", [])),
                }
            )
            categories.update(hint_categories)
        if len(matched_terms) >= 6:
            break

    matched_ports = []
    observed_ports = set(observed["listening_ports"])
    for hint in docpack_hints.get("port_hints", []):
        if not isinstance(hint, dict) or not _is_signal_bearing_docpack_hint(hint):
            continue
        port = hint.get("port")
        if isinstance(port, int) and port in observed_ports:
            hint_categories = {
                str(category)
                for category in hint.get("categories", [])
                if str(category) != "surface_term"
            }
            matched_ports.append(
                {
                    "port": port,
                    "categories": sorted(hint_categories),
                    "context_terms": list(hint.get("context_terms", []))[:6],
                }
            )
            categories.update(hint_categories)

    return {
        "matched_terms": matched_terms,
        "matched_ports": matched_ports,
        "categories": sorted(categories),
    }


def _is_signal_bearing_docpack_hint(hint: dict[str, Any]) -> bool:
    categories = {
        str(category)
        for category in hint.get("categories", [])
        if str(category)
    }
    normalized_parts = []
    term = hint.get("normalized_term")
    if term:
        normalized_parts.append(_normalize_hint_text(str(term)))
    for context_term in hint.get("context_terms", []):
        normalized_parts.append(_normalize_hint_text(str(context_term)))
    combined = " ".join(part for part in normalized_parts if part)
    term_text = normalized_parts[0] if normalized_parts else ""

    concrete_categories = categories & CONCRETE_DOCPACK_CATEGORIES
    if concrete_categories:
        return True
    if term_text in NOISY_DOCPACK_TERMS:
        return False
    if any(product_hint in combined for product_hint in PRODUCT_HINTS if len(product_hint) >= 3):
        return True
    if term_text and " " in term_text:
        if any(signal in combined for signal in ("application discovery", "risk", "workflow", "sensor", "collector")):
            return True
    port = hint.get("port")
    if isinstance(port, int) and port not in GENERIC_DOCPACK_PORTS:
        return True
    return False


def _term_matches_haystack(term: str, haystack: str) -> bool:
    if " " in term:
        return term in haystack
    return re.search(rf"\b{re.escape(term)}\b", haystack) is not None


def _normalize_hint_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _docpack_match_notes(docpack_matches: dict[str, Any]) -> list[str]:
    notes = []
    matched_terms = docpack_matches.get("matched_terms", [])
    matched_ports = docpack_matches.get("matched_ports", [])
    if matched_terms:
        terms = ", ".join(match["term"] for match in matched_terms[:3])
        notes.append(f"ASMS doc-pack terminology matches this component: {terms}.")
    if matched_ports:
        port_notes = []
        for match in matched_ports[:2]:
            context = ", ".join(match.get("context_terms", [])[:3]) or "no context terms"
            port_notes.append(f"{match['port']} ({context})")
        notes.append("ASMS doc-pack port hints intersect with this component: " + "; ".join(port_notes) + ".")
    return notes


def _build_record_unknowns(record: dict[str, Any]) -> list[str]:
    observed = record["observed"]
    unknowns: list[str] = []
    if not observed["config_path_candidates"]:
        unknowns.append("No config path candidate was visible from the first-pass command line or unit evidence.")
    if not observed["log_path_candidates"]:
        unknowns.append("No log path candidate was visible from the first-pass command line evidence.")
    if not observed["listening_ports"]:
        unknowns.append("No listening TCP port was linked to this component in the first-pass port scan.")
    if observed["service_unit"] and observed["main_command"] is None:
        unknowns.append("The unit is visible, but the main runtime command line was not linked in this first pass.")
    return unknowns


def _build_global_unknowns(command_results: list[dict[str, Any]], component_records: list[dict[str, Any]]) -> list[str]:
    unknowns = [
        "The first pass does not yet parse config files, unit fragments, or logs.",
        "The first pass does not claim complete dependency order or request-path ownership.",
        "The first pass keeps product labeling bounded; some components may still be generic or misclassified.",
    ]
    for result in command_results:
        if result["status"] != "completed":
            unknowns.append(f"{result['command_id']} could not be collected on this host.")
    if not component_records:
        unknowns.append("No component records were produced from the bounded first-pass commands.")
    return unknowns


def _build_next_candidate_seams(component_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seams: list[dict[str, Any]] = []
    listener_heavy = [record for record in component_records if record["observed"]["listening_ports"]]
    if listener_heavy:
        seams.append(
            {
                "seam_id": "trace_edge_to_local_service_routes",
                "why_it_matters": "Several visible listeners suggest a bounded next pass through proxy-to-local-service ownership.",
                "starting_components": [record["display_name"] for record in listener_heavy[:3]],
            }
        )
    java_heavy = [record for record in component_records if record["observed"]["jvm_visibility"]["detected"]]
    if java_heavy:
        seams.append(
            {
                "seam_id": "inspect_java_runtime_clusters",
                "why_it_matters": "Java-adjacent components are visible but their role boundaries are still tentative.",
                "starting_components": [record["display_name"] for record in java_heavy[:3]],
            }
        )
    return seams[:2]


def _render_summary(surface_map: dict[str, Any]) -> str:
    records = surface_map["component_records"]
    central = [record for record in records if record["inference"]["appears_central"]][:5]
    top_candidates = [record for record in records if record["inference"]["support_priority_score"] > 0][:5]
    unknowns = surface_map["unknowns"][:5]
    seams = surface_map["next_candidate_seams"][:2]
    docpack_ref = surface_map.get("docpack_hint_ref")
    lines = [
        "# ADF Successor Shallow Surface Summary",
        "",
        "## Scope",
        "",
        f"- Target: {surface_map['target']['target_label']}",
        f"- Hostname: {surface_map['runtime_identity']['hostname']}",
        f"- Components recorded: {len(records)}",
    ]
    if docpack_ref:
        lines.extend(
            [
                f"- ASMS doc-pack hints: loaded from `{docpack_ref.get('loaded_from')}`",
                f"- ASMS doc-pack version: {docpack_ref.get('docpack_id') or 'unknown'} {docpack_ref.get('version') or 'unknown'}",
                "",
                "The doc-pack hint layer only informs naming, port-based hints, and prioritization. Live runtime evidence remains the source of truth for what is running here.",
            ]
        )
    lines.extend(
        [
            "",
            "## What Appears To Be Running",
            "",
        ]
    )
    for record in central:
        ports = ", ".join(str(port) for port in record["observed"]["listening_ports"]) or "none linked yet"
        docpack_summary = _render_docpack_match_summary(record["inference"].get("docpack_matches", {}))
        line = (
            f"- `{record['display_name']}`: {record['inference']['first_observed_category']} "
            f"(confidence {record['inference']['confidence']}, ports {ports})"
        )
        if docpack_summary:
            line += f" Doc-pack hints: {docpack_summary}"
        lines.append(line)
    if not central:
        lines.append("- No clearly central components were identified in this first pass.")
        lines.append("Top visible candidates from the bounded run:")
        for record in top_candidates:
            ports = ", ".join(str(port) for port in record["observed"]["listening_ports"]) or "none linked yet"
            docpack_summary = _render_docpack_match_summary(record["inference"].get("docpack_matches", {}))
            line = (
                f"- `{record['display_name']}`: {record['inference']['first_observed_category']} "
                f"(confidence {record['inference']['confidence']}, score {record['inference']['support_priority_score']}, ports {ports})"
            )
            if docpack_summary:
                line += f" Doc-pack hints: {docpack_summary}"
            lines.append(line)
    lines.extend(["", "## Visible Unknowns", ""])
    for item in unknowns:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Candidate Seams", ""])
    for seam in seams:
        starts = ", ".join(seam["starting_components"]) or "none"
        lines.append(f"- `{seam['seam_id']}`: {seam['why_it_matters']} Starting points: {starts}.")
    if not seams:
        lines.append("- No deeper seam was strong enough to name yet from the bounded first pass.")
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_docpack_match_summary(docpack_matches: dict[str, Any]) -> str:
    if not docpack_matches:
        return ""
    notes = []
    matched_terms = docpack_matches.get("matched_terms", [])
    matched_ports = docpack_matches.get("matched_ports", [])
    if matched_terms:
        terms = ", ".join(match["term"] for match in matched_terms[:3])
        notes.append(f"matched terms {terms}")
    if matched_ports:
        ports = ", ".join(str(match["port"]) for match in matched_ports[:3])
        notes.append(f"matched ports {ports}")
    return "; ".join(notes)


def _run_command(*, command_id: str, argv: list[str], max_preview_lines: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        return {
            "command_id": command_id,
            "argv": argv,
            "status": "not_available",
            "exit_code": None,
            "stdout": "",
            "stdout_preview": [],
            "stdout_line_count": 0,
            "stderr_preview": [],
        }

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return {
        "command_id": command_id,
        "argv": argv,
        "status": "completed" if completed.returncode == 0 else "nonzero_exit",
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stdout_preview": stdout.splitlines()[:max_preview_lines],
        "stdout_line_count": len(stdout.splitlines()),
        "stderr_preview": stderr.splitlines()[:40],
    }


def _load_os_release() -> dict[str, str]:
    os_release_path = Path("/etc/os-release")
    values: dict[str, str] = {}
    if not os_release_path.exists():
        return values
    for line in os_release_path.read_text(encoding="utf-8").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
