from __future__ import annotations

import json
import os
import platform
import re
import shlex
import socket
import subprocess
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .docpack_hints import load_docpack_hints
from .target_connection import load_target_connection_profile, target_shell_capture


DEFAULT_ARTIFACT_ROOT = Path("dist/candidates/adf-shallow-surface-map-first-pass")
SURFACE_MAP_NAME = "shallow-surface-map.json"
SUMMARY_NAME = "shallow-surface-summary.md"
AUTONOMY_RUN_ROOT = Path(".pack-state") / "autonomy-runs"
RETURNED_ARTIFACTS_DIR = "artifacts"
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
LISTENER_PROCESS_RE = re.compile(r'users:\(\("(?P<process>[^"]+)",pid=(?P<pid>\d+)')
HTTPD_ROUTE_LINE_RE = re.compile(r"^(?P<config_path>/[^:]+):(?P<line_number>\d+):(?P<content>.*)$")
HTTPD_LOCATION_RE = re.compile(r"<Location(?:Match)?\s+\"?(?P<route>[^\"> ]+)\"?", re.IGNORECASE)
HTTPD_URL_RE = re.compile(r"https?://[^/\s:]+(?::(?P<port>\d+))?[^ \t]*", re.IGNORECASE)
HTTPD_ROUTE_HINT_COMMAND = (
    "if [ -d /etc/httpd ]; then "
    "grep -R -n -E '^[[:space:]]*(ProxyPass|ProxyPassReverse|ProxyPassMatch|RewriteRule|JkMount|Listen)[[:space:]]|<Location[^>]*>' "
    "/etc/httpd/conf /etc/httpd/conf.d 2>/dev/null || true; "
    "fi"
)
AFF_SESSION_SERVICE_CHECK_COMMAND = "systemctl is-active httpd.service ms-bflow.service aff-boot.service || true"
AFF_SESSION_FRONTED_PROBE_COMMAND = (
    "curl -k -sS --max-time 15 -D - -o - -w '\\n__ADF_HTTP_STATUS__:%{http_code}\\n' "
    "https://localhost/FireFlow/api/session"
)
AFF_SESSION_DIRECT_PROBE_COMMAND = (
    "curl -sS --max-time 15 -D - -o - -w '\\n__ADF_HTTP_STATUS__:%{http_code}\\n' "
    "http://localhost:1989/aff/api/external/session"
)
BUSINESSFLOW_DEEP_HEALTH_COMMAND = (
    "curl -k -sS --max-time 15 https://127.0.0.1/BusinessFlow/deep_health_check || true"
)
FIREFLOW_USERSESSION_HTTPD_MARKERS_COMMAND = (
    "grep -E '/FireFlow/api/session|/FireFlow/api/session/validate|extendSession' "
    "/var/log/httpd/ssl_access_log 2>/dev/null | tail -n 80 || true"
)
FIREFLOW_USERSESSION_LOG_MARKERS_COMMAND = (
    "grep -E 'UserSession::getUserSession|isUserSessionValid|Using existing FASessionId|ff-session:' "
    "/usr/share/fireflow/var/log/fireflow.log* 2>/dev/null | tail -n 80 || true"
)
HTTP_STATUS_MARKER = "__ADF_HTTP_STATUS__:"
AFF_SESSION_SERVICE_UNITS = ("httpd.service", "ms-bflow.service", "aff-boot.service")


def generate_shallow_surface_map(
    *,
    project_root: Path,
    target_label: str,
    target_connection_profile: str | Path | None = None,
    artifact_root: str | Path | None = None,
    docpack_hints_path: str | Path | None = None,
    mirror_into_run_id: str | None = None,
) -> dict[str, Any]:
    root = project_root / (Path(artifact_root) if artifact_root else DEFAULT_ARTIFACT_ROOT)
    root.mkdir(parents=True, exist_ok=True)

    target_connection = (
        load_target_connection_profile(project_root=project_root, profile_path=target_connection_profile)
        if target_connection_profile
        else None
    )
    runtime_identity = _collect_runtime_identity(target_connection=target_connection)
    command_results = _collect_command_results(target_connection=target_connection)
    docpack_hints = load_docpack_hints(project_root, docpack_hints_path)
    component_records, edge_route_hints = _build_component_records(command_results, docpack_hints=docpack_hints)
    boundary_packets = _build_boundary_packets(component_records, edge_route_hints=edge_route_hints)
    session_parity_packets = _build_session_parity_packets(
        command_results,
        boundary_packets=boundary_packets,
    )
    usersession_bridge_packets = _build_usersession_bridge_packets(
        command_results,
        session_parity_packets=session_parity_packets,
    )
    usersession_reuse_packets = _build_usersession_fa_session_reuse_packets(
        command_results,
        usersession_bridge_packets=usersession_bridge_packets,
    )
    next_candidate_seams = _build_next_candidate_seams(
        component_records,
        edge_route_hints=edge_route_hints,
        boundary_packets=boundary_packets,
        session_parity_packets=session_parity_packets,
        usersession_bridge_packets=usersession_bridge_packets,
        usersession_reuse_packets=usersession_reuse_packets,
    )
    surface_map = {
        "schema_version": "adf-shallow-surface-map/v1",
        "generated_at": _isoformat_z(),
        "target": {
            "target_label": target_label,
            "hostname": runtime_identity["hostname"],
        },
        "target_connection": None
        if target_connection is None
        else {
            "loaded_from": target_connection.get("_loaded_from"),
            "target_label": target_connection.get("target_label"),
            "ssh_host": target_connection.get("ssh_host"),
            "ssh_user": target_connection.get("ssh_user"),
            "auth_mode": target_connection.get("auth_mode"),
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
                "httpd_route_hints",
                "aff_session_parity_checks",
                "fireflow_usersession_bridge_hints",
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
        "edge_route_hints": edge_route_hints,
        "boundary_packets": boundary_packets,
        "session_parity_packets": session_parity_packets,
        "usersession_bridge_packets": usersession_bridge_packets,
        "usersession_reuse_packets": usersession_reuse_packets,
        "unknowns": _build_global_unknowns(command_results, component_records, edge_route_hints=edge_route_hints),
        "next_candidate_seams": next_candidate_seams,
    }
    summary = _render_summary(surface_map)

    _dump_json(root / SURFACE_MAP_NAME, surface_map)
    (root / SUMMARY_NAME).write_text(summary, encoding="utf-8")

    mirrored_files: list[str] = []
    if mirror_into_run_id:
        mirrored_files = _mirror_generated_files_into_run(
            project_root=project_root,
            artifact_root=root,
            run_id=mirror_into_run_id,
            generated_files=[root / SURFACE_MAP_NAME, root / SUMMARY_NAME],
        )

    result: dict[str, Any] = {
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
            "edge_route_hint_count": len(edge_route_hints),
            "boundary_packet_count": len(boundary_packets),
            "session_parity_packet_count": len(session_parity_packets),
            "usersession_bridge_packet_count": len(usersession_bridge_packets),
            "usersession_reuse_packet_count": len(usersession_reuse_packets),
            "candidate_seam_count": len(next_candidate_seams),
        },
    }
    if mirrored_files:
        result["mirrored_run_artifact_paths"] = mirrored_files
    return result


def _mirror_generated_files_into_run(
    *,
    project_root: Path,
    artifact_root: Path,
    run_id: str,
    generated_files: list[Path],
) -> list[str]:
    run_root = (project_root / AUTONOMY_RUN_ROOT / run_id).resolve()
    allowed_run_root = (project_root / AUTONOMY_RUN_ROOT).resolve()
    if not run_root.exists():
        raise ValueError(f"{run_root}: run directory does not exist")
    try:
        run_root.relative_to(allowed_run_root)
    except ValueError as exc:
        raise ValueError(f"{run_root}: run directory escapes .pack-state/autonomy-runs") from exc

    resolved_artifact_root = artifact_root.resolve()
    relative_artifact_root = resolved_artifact_root.relative_to(project_root.resolve())
    destination_root = run_root / RETURNED_ARTIFACTS_DIR / relative_artifact_root
    mirrored_paths: list[str] = []
    for source_path in generated_files:
        resolved_source = source_path.resolve()
        relative_source = resolved_source.relative_to(resolved_artifact_root)
        target_path = destination_root / relative_source
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(resolved_source, target_path)
        mirrored_paths.append(str(target_path.relative_to(project_root)))
    return mirrored_paths


def _collect_runtime_identity(*, target_connection: dict[str, Any] | None) -> dict[str, Any]:
    if target_connection is None:
        return {
            "hostname": socket.gethostname(),
            "kernel_release": platform.release(),
            "platform": platform.platform(),
            "os_release": _load_os_release(),
        }
    return _collect_target_runtime_identity(target_connection)


def _collect_command_results(*, target_connection: dict[str, Any] | None) -> list[dict[str, Any]]:
    if target_connection is None:
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
            _run_command(
                command_id="httpd_route_hints",
                argv=["bash", "-lc", HTTPD_ROUTE_HINT_COMMAND],
                max_preview_lines=250,
            ),
            _run_command(
                command_id="aff_session_service_checks",
                argv=["bash", "-lc", AFF_SESSION_SERVICE_CHECK_COMMAND],
                max_preview_lines=250,
            ),
            _run_command(
                command_id="aff_session_fronted_probe",
                argv=["bash", "-lc", AFF_SESSION_FRONTED_PROBE_COMMAND],
                max_preview_lines=250,
            ),
            _run_command(
                command_id="aff_session_direct_probe",
                argv=["bash", "-lc", AFF_SESSION_DIRECT_PROBE_COMMAND],
                max_preview_lines=250,
            ),
            _run_command(
                command_id="businessflow_deep_health",
                argv=["bash", "-lc", BUSINESSFLOW_DEEP_HEALTH_COMMAND],
                max_preview_lines=250,
            ),
        ]
    return _collect_target_command_results(target_connection)


def _collect_target_runtime_identity(target_connection: dict[str, Any]) -> dict[str, Any]:
    timeout_seconds = int(target_connection.get("timeouts", {}).get("command_seconds", 120))
    hostname_result = target_shell_capture(
        profile=target_connection,
        command_id="runtime_hostname",
        command="hostname",
        timeout_seconds=timeout_seconds,
    )
    kernel_result = target_shell_capture(
        profile=target_connection,
        command_id="runtime_kernel_release",
        command="uname -r",
        timeout_seconds=timeout_seconds,
    )
    platform_result = target_shell_capture(
        profile=target_connection,
        command_id="runtime_platform",
        command="uname -srm",
        timeout_seconds=timeout_seconds,
    )
    os_release_result = target_shell_capture(
        profile=target_connection,
        command_id="runtime_os_release",
        command="cat /etc/os-release",
        timeout_seconds=timeout_seconds,
    )
    hostname = _first_output_line(hostname_result) or str(target_connection.get("ssh_host") or "unknown")
    return {
        "hostname": hostname,
        "kernel_release": _first_output_line(kernel_result),
        "platform": _first_output_line(platform_result),
        "os_release": _parse_os_release_text(os_release_result.get("stdout", "")),
        "collection_mode": "ssh_read_only",
        "target_connection": {
            "loaded_from": target_connection.get("_loaded_from"),
            "target_label": target_connection.get("target_label"),
            "ssh_host": target_connection.get("ssh_host"),
            "ssh_user": target_connection.get("ssh_user"),
            "auth_mode": target_connection.get("auth_mode"),
        },
    }


def _collect_target_command_results(target_connection: dict[str, Any]) -> list[dict[str, Any]]:
    timeout_seconds = int(target_connection.get("timeouts", {}).get("command_seconds", 120))
    return [
        _run_target_command(
            target_connection=target_connection,
            command_id="systemd_units",
            command="systemctl list-units --type=service --all --no-pager --plain --no-legend",
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="systemd_unit_files",
            command="systemctl list-unit-files --type=service --no-pager --plain --no-legend",
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="listening_tcp_ports",
            command="ss -lntpH",
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="process_inventory",
            command="ps -eo pid=,ppid=,user=,comm=,args=",
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="httpd_route_hints",
            command=HTTPD_ROUTE_HINT_COMMAND,
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="aff_session_service_checks",
            command=AFF_SESSION_SERVICE_CHECK_COMMAND,
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="aff_session_fronted_probe",
            command=AFF_SESSION_FRONTED_PROBE_COMMAND,
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="aff_session_direct_probe",
            command=AFF_SESSION_DIRECT_PROBE_COMMAND,
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="businessflow_deep_health",
            command=BUSINESSFLOW_DEEP_HEALTH_COMMAND,
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="fireflow_usersession_httpd_markers",
            command=FIREFLOW_USERSESSION_HTTPD_MARKERS_COMMAND,
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="fireflow_usersession_log_markers",
            command=FIREFLOW_USERSESSION_LOG_MARKERS_COMMAND,
            timeout_seconds=timeout_seconds,
        ),
    ]


def _run_target_command(
    *,
    target_connection: dict[str, Any],
    command_id: str,
    command: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    result = target_shell_capture(
        profile=target_connection,
        command_id=command_id,
        command=command,
        timeout_seconds=timeout_seconds,
        preview_line_limit=250,
    )
    result["command"] = command
    return result


def _build_component_records(
    command_results: list[dict[str, Any]],
    *,
    docpack_hints: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    results_by_id = {entry["command_id"]: entry for entry in command_results}
    unit_states = _parse_systemd_units(results_by_id.get("systemd_units", {}))
    unit_file_states = _parse_unit_files(results_by_id.get("systemd_unit_files", {}))
    listeners = _parse_listeners(results_by_id.get("listening_tcp_ports", {}))
    processes = _parse_processes(results_by_id.get("process_inventory", {}))
    process_index, children_by_ppid = _index_processes(processes)
    httpd_route_rows = _parse_httpd_route_hints(results_by_id.get("httpd_route_hints", {}))

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
                "listener_bindings": [],
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
                    "listener_bindings": [],
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
        observed["listener_bindings"] = _listener_bindings_for_record(
            listeners,
            record,
            process_index=process_index,
            children_by_ppid=children_by_ppid,
        )
        observed["listening_ports"] = _merge_unique(
            observed["listening_ports"],
            [binding["bind_port"] for binding in observed["listener_bindings"]],
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

    component_records = sorted(
        records.values(),
        key=lambda item: (
            -item["inference"]["support_priority_score"],
            item["display_name"].lower(),
        ),
    )
    edge_route_hints = _build_edge_route_hints(httpd_route_rows, component_records)
    return component_records, edge_route_hints


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


def _parse_listeners(result: dict[str, Any]) -> list[dict[str, Any]]:
    listeners: list[dict[str, Any]] = []
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
        process_name = parts[-1] if parts else "unknown"
        process_id = None
        match = LISTENER_PROCESS_RE.search(line)
        if match:
            process_name = match.group("process")
            process_id = int(match.group("pid"))
        listeners.append(
            {
                "port": port,
                "process_name": process_name,
                "process_id": process_id,
            }
        )
    return listeners


def _parse_httpd_route_hints(result: dict[str, Any]) -> list[dict[str, Any]]:
    route_hints: list[dict[str, Any]] = []
    if result.get("status") != "completed":
        return route_hints

    current_location_by_file: dict[str, str] = {}
    for raw_line in result.get("stdout", "").splitlines():
        line_match = HTTPD_ROUTE_LINE_RE.match(raw_line)
        if line_match is None:
            continue
        config_path = line_match.group("config_path")
        line_number = int(line_match.group("line_number"))
        content = line_match.group("content").strip()
        if not content:
            continue

        location_match = HTTPD_LOCATION_RE.search(content)
        if location_match:
            current_location_by_file[config_path] = location_match.group("route")
            continue

        tokens = content.split()
        if not tokens:
            continue
        directive = tokens[0]
        route_path = _extract_httpd_route_path(tokens, current_location_by_file.get(config_path))
        backend_url = _extract_httpd_backend_url(tokens)
        backend_port = _extract_httpd_backend_port(content)
        if directive == "Listen":
            listen_port = _extract_httpd_listen_port(tokens)
            if listen_port is None:
                continue
            route_hints.append(
                {
                    "directive": directive,
                    "config_path": config_path,
                    "line_number": line_number,
                    "route_path": route_path,
                    "backend_url": None,
                    "backend_port": listen_port,
                    "raw_line": content,
                }
            )
            continue
        if directive not in {"ProxyPass", "ProxyPassReverse", "ProxyPassMatch", "RewriteRule", "JkMount"}:
            continue
        if route_path is None and backend_port is None and backend_url is None:
            continue
        route_hints.append(
            {
                "directive": directive,
                "config_path": config_path,
                "line_number": line_number,
                "route_path": route_path,
                "backend_url": backend_url,
                "backend_port": backend_port,
                "raw_line": content,
            }
        )
    return route_hints


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
        try:
            comm = shlex.split(parts[3])[0] if parts[3] else parts[2]
        except ValueError:
            comm = parts[2]
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


def _index_processes(
    processes: list[dict[str, Any]],
) -> tuple[dict[int, dict[str, Any]], dict[int, list[int]]]:
    process_index: dict[int, dict[str, Any]] = {}
    children_by_ppid: dict[int, list[int]] = {}
    for process in processes:
        pid = int(process["pid"])
        process_index[pid] = process
        ppid = process.get("ppid")
        if isinstance(ppid, int):
            children_by_ppid.setdefault(ppid, []).append(pid)
    return process_index, children_by_ppid


def _first_output_line(result: dict[str, Any]) -> str | None:
    preview = result.get("stdout_preview", [])
    if preview:
        return str(preview[0]).strip() or None
    stdout = str(result.get("stdout", "")).splitlines()
    if stdout:
        return stdout[0].strip() or None
    return None


def _parse_os_release_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


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
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    for token in tokens:
        if token.startswith("-Xmx") or token.startswith("-Xms"):
            notes.append(token)
        if token.startswith("-D") and ("java" in token.lower() or "catalina" in token.lower()):
            notes.append(token)
    return notes[:8]


def _ports_for_candidates(listeners: list[dict[str, Any]], candidates: list[str]) -> list[int]:
    ports: list[int] = []
    for candidate in candidates:
        candidate_lower = candidate.lower()
        if not candidate_lower:
            continue
        for listener in listeners:
            process_lower = str(listener["process_name"]).lower()
            if candidate_lower in process_lower or process_lower in candidate_lower:
                port = int(listener["port"])
                if port not in ports:
                    ports.append(port)
    return sorted(ports)


def _ports_for_record(listeners: list[dict[str, Any]], record: dict[str, Any]) -> list[int]:
    observed = record["observed"]
    listener_key_candidates = [
        observed["service_unit"] or "",
        record["display_name"],
    ]
    process_name = str(observed.get("process_name") or "")
    if process_name and not _is_generic_process_name(process_name):
        listener_key_candidates.append(process_name)
    return _ports_for_candidates(listeners, listener_key_candidates)


def _listener_bindings_for_record(
    listeners: list[dict[str, Any]],
    record: dict[str, Any],
    *,
    process_index: dict[int, dict[str, Any]],
    children_by_ppid: dict[int, list[int]],
) -> list[dict[str, Any]]:
    observed = record["observed"]
    process_id = observed.get("process_id")
    bindings: list[dict[str, Any]] = []
    if isinstance(process_id, int):
        related_pids = _descendant_pids(process_id, children_by_ppid)
        related_pids.add(process_id)
        for listener in listeners:
            listener_pid = listener.get("process_id")
            if listener_pid in related_pids:
                ownership_basis = "exact_pid" if listener_pid == process_id else "descendant_pid"
                owner_process = process_index.get(listener_pid, {})
                bindings.append(
                    {
                        "bind_port": int(listener["port"]),
                        "owner_pid": listener_pid,
                        "owner_name": str(owner_process.get("comm") or listener["process_name"]),
                        "ownership_basis": ownership_basis,
                    }
                )
    if bindings:
        return sorted(bindings, key=lambda item: item["bind_port"])

    fallback_ports = _ports_for_record(listeners, record)
    return [
        {
            "bind_port": int(port),
            "owner_pid": None,
            "owner_name": observed.get("process_name"),
            "ownership_basis": "name_fallback",
        }
        for port in fallback_ports
    ]


def _descendant_pids(root_pid: int, children_by_ppid: dict[int, list[int]]) -> set[int]:
    descendants: set[int] = set()
    queue = list(children_by_ppid.get(root_pid, []))
    while queue:
        pid = queue.pop(0)
        if pid in descendants:
            continue
        descendants.add(pid)
        queue.extend(children_by_ppid.get(pid, []))
    return descendants


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
    if "httpd" in haystack or "/usr/sbin/httpd" in haystack or "apache http server" in haystack:
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


def _build_global_unknowns(
    command_results: list[dict[str, Any]],
    component_records: list[dict[str, Any]],
    *,
    edge_route_hints: list[dict[str, Any]],
) -> list[str]:
    unknowns = [
        "The first pass does not yet parse config files, unit fragments, or logs.",
        "The first pass does not claim complete dependency order or request-path ownership.",
        "The first pass keeps product labeling bounded; some components may still be generic or misclassified.",
    ]
    for result in command_results:
        if result["status"] != "completed":
            unknowns.append(f"{result['command_id']} could not be collected in this pass.")
    if not component_records:
        unknowns.append("No component records were produced from the bounded first-pass commands.")
    if not edge_route_hints:
        unknowns.append("No bounded Apache route hints were linked to local services in this pass.")
    return unknowns


def _build_boundary_packets(
    component_records: list[dict[str, Any]],
    *,
    edge_route_hints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    aff_hints = [hint for hint in edge_route_hints if "aff.conf" in hint.get("config_path", "")]
    aff_record = next((record for record in component_records if record["component_id"] == "aff-boot"), None)
    if aff_hints and aff_record is not None:
        route_paths = _dedupe_preserve_order(
            [str(hint["route_path"]) for hint in aff_hints if hint.get("route_path")]
        )
        config_paths = _dedupe_preserve_order(
            [str(hint["config_path"]) for hint in aff_hints if hint.get("config_path")]
        )
        backend_ports = sorted(
            {
                int(hint["backend_port"])
                for hint in aff_hints
                if isinstance(hint.get("backend_port"), int)
            }
        )
        listener_bindings = aff_record["observed"].get("listener_bindings", [])
        packets.append(
            {
                "boundary_id": "aff_fireflow_1989_route_owner",
                "boundary_kind": "route_owner_confirmation",
                "display_name": "AFF or FireFlow 1989 Route Owner Packet",
                "status": "bounded_owner_confirmed",
                "confidence": "high" if backend_ports == [1989] and listener_bindings else "medium",
                "why_it_matters": "This packet keeps Apache route ownership, the local 1989 listener, and the owning service family in one bounded proof surface.",
                "route_family": route_paths,
                "config_paths": config_paths,
                "local_owner": {
                    "component_id": aff_record["component_id"],
                    "category": aff_record["inference"]["first_observed_category"],
                    "service_unit": aff_record["observed"].get("service_unit"),
                    "wrapper_process_id": aff_record["observed"].get("process_id"),
                    "listener_bindings": listener_bindings,
                    "listening_ports": aff_record["observed"].get("listening_ports", []),
                },
                "route_evidence": [
                    {
                        "directive": hint["directive"],
                        "route_path": hint.get("route_path"),
                        "backend_url": hint.get("backend_url"),
                        "backend_port": hint.get("backend_port"),
                        "config_path": hint["config_path"],
                        "line_number": hint["line_number"],
                        "match_reason": hint["match_reason"],
                    }
                    for hint in aff_hints[:8]
                ],
                "confirmed_elements": [
                    "Apache aff.conf points `/FireFlow/api` and `/aff/api` at local port 1989.",
                    "The local 1989 listener is attached to the aff-boot service family through descendant PID ownership.",
                    "This is enough to treat aff-boot as the current bounded local route owner for the AFF or FireFlow API edge."
                ],
                "remaining_questions": [
                    "The packet does not yet prove the full downstream FireFlow workflow behind aff-boot.",
                    "The packet does not yet replay requests or prove post-handoff business logic behavior."
                ],
            }
        )
    return packets


def _build_session_parity_packets(
    command_results: list[dict[str, Any]],
    *,
    boundary_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    aff_packet = next(
        (packet for packet in boundary_packets if packet.get("boundary_id") == "aff_fireflow_1989_route_owner"),
        None,
    )
    if aff_packet is None:
        return []

    results_by_id = {entry["command_id"]: entry for entry in command_results}
    service_checks = _parse_service_activity_checks(results_by_id.get("aff_session_service_checks", {}))
    fronted_probe = _parse_http_probe_result(
        results_by_id.get("aff_session_fronted_probe", {}),
        probe_url="https://localhost/FireFlow/api/session",
    )
    direct_probe = _parse_http_probe_result(
        results_by_id.get("aff_session_direct_probe", {}),
        probe_url="http://localhost:1989/aff/api/external/session",
    )
    deep_health = _parse_deep_health_result(results_by_id.get("businessflow_deep_health", {}))

    probes_completed = fronted_probe["probe_status"] == "completed" and direct_probe["probe_status"] == "completed"
    status_code_match = (
        probes_completed
        and fronted_probe.get("http_status_code") is not None
        and fronted_probe.get("http_status_code") == direct_probe.get("http_status_code")
    )
    body_match = (
        probes_completed
        and fronted_probe.get("normalized_body") is not None
        and fronted_probe.get("normalized_body") == direct_probe.get("normalized_body")
    )
    invalid_session_match = (
        probes_completed
        and fronted_probe.get("message_code") == "INVALID_SESSION_KEY"
        and direct_probe.get("message_code") == "INVALID_SESSION_KEY"
    )
    all_services_active = all(
        service_checks.get(unit_name) == "active"
        for unit_name in AFF_SESSION_SERVICE_UNITS
    )

    if probes_completed and status_code_match and body_match:
        packet_status = "parity_confirmed"
    elif probes_completed:
        packet_status = "parity_mismatch"
    else:
        packet_status = "probe_incomplete"

    confidence = "high" if packet_status == "parity_confirmed" and all_services_active else "medium"
    confirmed_elements = []
    remaining_questions = []
    if all_services_active:
        confirmed_elements.append("httpd.service, ms-bflow.service, and aff-boot.service all report active.")
    else:
        remaining_questions.append("One or more services in the Apache to BusinessFlow to AFF seam did not report active.")
    if packet_status == "parity_confirmed":
        confirmed_elements.extend(
            [
                "The Apache-fronted `/FireFlow/api/session` probe and the direct aff-boot `/aff/api/external/session` probe returned the same observable response.",
                "The current session response stays bounded at invalid-session semantics instead of claiming a full logged-in workflow.",
            ]
        )
    elif packet_status == "parity_mismatch":
        remaining_questions.append(
            "The fronted `/FireFlow/api/session` probe and the direct aff-boot session probe diverged, so the seam should stay bounded at the Apache-to-aff-boot boundary."
        )
    else:
        remaining_questions.append(
            "At least one AFF session probe did not complete, so parity is not proven yet."
        )
    if invalid_session_match:
        confirmed_elements.append("Both probes report the same invalid-session message code: `INVALID_SESSION_KEY`.")
    if deep_health.get("aff_connection") is True:
        confirmed_elements.append("BusinessFlow deep health still reports `AFF connection` as true.")
    elif deep_health.get("overall_status") is not None:
        remaining_questions.append("BusinessFlow deep health did not show a clean AFF connection signal in this bounded pass.")

    next_stop = (
        "fireflow_usersession_bridge"
        if packet_status == "parity_confirmed"
        else "apache_to_aff_boot_boundary"
    )
    operator_takeaways = (
        "Apache owns `/FireFlow/api/session`, proxies it to aff-boot on `1989`, and the next bounded stop is the FireFlow UserSession bridge."
        if packet_status == "parity_confirmed"
        else "Apache still owns `/FireFlow/api/session` to aff-boot on `1989`, but the fronted and direct session responses do not align cleanly yet, so the seam stays bounded at Apache to aff-boot."
    )

    return [
        {
            "packet_id": "aff_session_route_parity",
            "packet_kind": "route_parity_validation",
            "display_name": "AFF Session Route Parity Packet",
            "status": packet_status,
            "confidence": confidence,
            "why_it_matters": "This packet checks whether the fronted Apache AFF session path and the direct aff-boot local session path still behave the same before widening into later FireFlow behavior.",
            "operator_title": "BusinessFlow AFF route ownership",
            "operator_takeaways": operator_takeaways,
            "route_owner_boundary_id": aff_packet["boundary_id"],
            "service_checks": service_checks,
            "fronted_probe": fronted_probe,
            "direct_probe": direct_probe,
            "agreement": {
                "probes_completed": probes_completed,
                "status_code_match": status_code_match,
                "body_match": body_match,
                "invalid_session_code_match": invalid_session_match,
            },
            "businessflow_deep_health": deep_health,
            "next_stop": next_stop,
            "stop_rule": "If the fronted and direct probes disagree, stop at the Apache-to-aff-boot boundary.",
            "confirmed_elements": confirmed_elements,
            "remaining_questions": remaining_questions,
        }
    ]


def _parse_service_activity_checks(result: dict[str, Any]) -> dict[str, str]:
    checks = {unit_name: "unknown" for unit_name in AFF_SESSION_SERVICE_UNITS}
    if result.get("status") not in {"completed", "nonzero_exit"}:
        return checks
    lines = [line.strip() for line in str(result.get("stdout", "")).splitlines() if line.strip()]
    for unit_name, line in zip(AFF_SESSION_SERVICE_UNITS, lines):
        checks[unit_name] = line
    return checks


def _parse_http_probe_result(result: dict[str, Any], *, probe_url: str) -> dict[str, Any]:
    stdout = str(result.get("stdout", ""))
    marker_value = None
    payload = stdout
    if HTTP_STATUS_MARKER in stdout:
        payload, _, tail = stdout.rpartition(HTTP_STATUS_MARKER)
        marker_line = tail.splitlines()[0].strip() if tail else ""
        marker_value = marker_line

    header_text, body_text = _split_http_headers_and_body(payload)
    status_code = None
    status_lines = [line.strip() for line in header_text.splitlines() if line.strip().startswith("HTTP/")]
    if marker_value and marker_value.isdigit():
        status_code = int(marker_value)
    elif status_lines:
        match = re.search(r"\s(\d{3})(?:\s|$)", status_lines[-1])
        if match:
            status_code = int(match.group(1))

    normalized_body, parsed_json = _normalize_response_body(body_text)
    message_code = None
    if isinstance(parsed_json, dict):
        message = parsed_json.get("message")
        if isinstance(message, dict) and isinstance(message.get("code"), str):
            message_code = message["code"]

    return {
        "probe_url": probe_url,
        "probe_status": "completed" if result.get("status") == "completed" else result.get("status"),
        "command_status": result.get("status"),
        "exit_code": result.get("exit_code"),
        "http_status_code": status_code,
        "http_status_line": status_lines[-1] if status_lines else None,
        "body_excerpt": body_text.strip()[:300] or None,
        "normalized_body": normalized_body,
        "message_code": message_code,
        "stderr_preview": result.get("stderr_preview", []),
    }


def _split_http_headers_and_body(payload: str) -> tuple[str, str]:
    normalized = payload.replace("\r\n", "\n")
    if "\n\n" not in normalized:
        return normalized, ""
    header_text, body_text = normalized.split("\n\n", 1)
    return header_text, body_text


def _normalize_response_body(body_text: str) -> tuple[str | None, dict[str, Any] | None]:
    stripped = body_text.strip()
    if not stripped:
        return None, None
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped, None
    if isinstance(parsed, dict):
        return json.dumps(parsed, sort_keys=True, separators=(",", ":")), parsed
    return stripped, None


def _parse_deep_health_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") not in {"completed", "nonzero_exit"}:
        return {
            "probe_status": result.get("status"),
            "overall_status": None,
            "aff_connection": None,
            "body_excerpt": None,
        }
    stdout = str(result.get("stdout", "")).strip()
    overall_status = None
    aff_connection = None
    try:
        payload = json.loads(stdout) if stdout else None
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        status_value = payload.get("status")
        if isinstance(status_value, bool):
            overall_status = status_value
        aff_connection = _find_named_boolean(payload, "AFF connection")
    return {
        "probe_status": result.get("status"),
        "overall_status": overall_status,
        "aff_connection": aff_connection,
        "body_excerpt": stdout[:300] or None,
    }


def _build_usersession_bridge_packets(
    command_results: list[dict[str, Any]],
    *,
    session_parity_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parity_packet = next(
        (packet for packet in session_parity_packets if packet.get("packet_id") == "aff_session_route_parity"),
        None,
    )
    if parity_packet is None or parity_packet.get("status") != "parity_confirmed":
        return []

    results_by_id = {entry["command_id"]: entry for entry in command_results}
    httpd_markers = _parse_marker_lines(
        results_by_id.get("fireflow_usersession_httpd_markers", {}),
        expected_terms=("/FireFlow/api/session", "/FireFlow/api/session/validate", "extendSession"),
    )
    fireflow_markers = _parse_marker_lines(
        results_by_id.get("fireflow_usersession_log_markers", {}),
        expected_terms=("UserSession::getUserSession", "isUserSessionValid", "Using existing FASessionId", "ff-session:"),
    )

    httpd_visible = bool(httpd_markers["matched_terms"])
    fireflow_visible = bool(fireflow_markers["matched_terms"])
    bridge_confirmed = httpd_visible and fireflow_visible
    packet_status = "bridge_signals_visible" if bridge_confirmed else "bridge_signals_thin"
    confidence = "high" if bridge_confirmed and "Using existing FASessionId" in fireflow_markers["matched_terms"] else "medium"

    confirmed_elements: list[str] = []
    remaining_questions: list[str] = []
    if httpd_visible:
        confirmed_elements.append("Apache retained markers still show `/FireFlow/api/session`-family activity.")
    else:
        remaining_questions.append("Retained Apache session-path markers were too thin to prove a concrete UserSession-side window.")
    if fireflow_visible:
        confirmed_elements.append(
            "Retained FireFlow logs show UserSession-style markers such as `UserSession::getUserSession`, `isUserSessionValid`, `ff-session`, or reused FA session hints."
        )
    else:
        remaining_questions.append("Retained FireFlow logs did not show a strong UserSession-style bridge in this bounded pass.")

    next_stop = (
        "trace_usersession_fa_session_reuse"
        if bridge_confirmed and "Using existing FASessionId" in fireflow_markers["matched_terms"]
        else "keep_usersession_bridge_bounded"
    )

    return [
        {
            "packet_id": "fireflow_usersession_bridge",
            "packet_kind": "retained_log_bridge_hint",
            "display_name": "FireFlow UserSession Bridge Packet",
            "status": packet_status,
            "confidence": confidence,
            "why_it_matters": "This packet uses bounded retained evidence to show whether the next support-useful stop behind the confirmed AFF session route is the FireFlow UserSession bridge.",
            "session_parity_ref": parity_packet["packet_id"],
            "httpd_markers": httpd_markers,
            "fireflow_markers": fireflow_markers,
            "next_stop": next_stop,
            "stop_rule": "If retained UserSession markers are weak, stop here instead of widening into generic FireFlow theory.",
            "confirmed_elements": confirmed_elements,
            "remaining_questions": remaining_questions,
        }
    ]


def _build_usersession_fa_session_reuse_packets(
    command_results: list[dict[str, Any]],
    *,
    usersession_bridge_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bridge_packet = next(
        (packet for packet in usersession_bridge_packets if packet.get("packet_id") == "fireflow_usersession_bridge"),
        None,
    )
    if bridge_packet is None or bridge_packet.get("status") != "bridge_signals_visible":
        return []

    results_by_id = {entry["command_id"]: entry for entry in command_results}
    reuse_analysis = _parse_usersession_reuse_analysis(
        results_by_id.get("fireflow_usersession_log_markers", {}),
    )
    reuse_pairs = reuse_analysis["reuse_pairs"]
    packet_status = "reuse_chain_visible" if reuse_pairs else "reuse_chain_thin"
    confidence = "high" if reuse_analysis["repeated_pair_count"] >= 1 and len(reuse_pairs) >= 2 else "medium"

    confirmed_elements: list[str] = []
    remaining_questions: list[str] = []
    if reuse_pairs:
        confirmed_elements.append(
            "Retained FireFlow markers now correlate concrete `ff-session` values with reused FA-session ids in the same UserSession window."
        )
        if reuse_analysis["repeated_pair_count"] >= 1:
            confirmed_elements.append(
                "At least one `ff-session -> FA-session` pair repeats across multiple retained request windows, which makes this look like real reuse rather than a one-off adjacent hint."
            )
        if reuse_analysis["distinct_ff_session_count"] >= 2:
            confirmed_elements.append(
                "More than one distinct FireFlow session id participates in the retained reuse chain, so the pattern is not limited to a single isolated session."
            )
    else:
        remaining_questions.append(
            "The retained FireFlow marker window did not correlate a concrete `ff-session` value to a reused FA-session id strongly enough to treat the chain as visible."
        )

    if reuse_analysis["validation_only_marker_count"] >= 1:
        confirmed_elements.append(
            "The same retained window also contains `UserSession::isUserSessionValid` dispatcher markers, which supports the reading that this is still a bounded UserSession validation and reuse seam."
        )
    else:
        remaining_questions.append(
            "Dispatcher-style `isUserSessionValid` markers were thin in the retained window, so the packet stays focused on the concrete reuse pairs that were visible."
        )

    next_stop = "trace_businessflow_session_origin" if reuse_pairs else "keep_usersession_reuse_bounded"
    remaining_questions.append(
        "The packet does not yet prove which upstream BusinessFlow or AFA-side caller created or refreshed the session context before FireFlow reused the FA session."
    )

    return [
        {
            "packet_id": "usersession_fa_session_reuse",
            "packet_kind": "retained_log_reuse_chain",
            "display_name": "UserSession Reused FA Session Packet",
            "status": packet_status,
            "confidence": confidence,
            "why_it_matters": "This packet keeps the post-UserSession seam narrow and shows whether retained FireFlow evidence supports a real reused FA-session chain behind the confirmed AFF session route.",
            "usersession_bridge_ref": bridge_packet["packet_id"],
            "correlation_summary": {
                "reuse_pair_count": len(reuse_pairs),
                "distinct_ff_session_count": reuse_analysis["distinct_ff_session_count"],
                "distinct_fa_session_count": reuse_analysis["distinct_fa_session_count"],
                "repeated_pair_count": reuse_analysis["repeated_pair_count"],
                "validation_only_marker_count": reuse_analysis["validation_only_marker_count"],
            },
            "reuse_pairs": reuse_pairs,
            "validation_only_markers": reuse_analysis["validation_only_markers"],
            "next_stop": next_stop,
            "stop_rule": "If concrete `ff-session -> reused FA-session` pairs are not visible, stop here instead of widening into broad FireFlow workflow theory.",
            "confirmed_elements": confirmed_elements,
            "remaining_questions": remaining_questions,
        }
    ]


def _parse_marker_lines(result: dict[str, Any], *, expected_terms: tuple[str, ...]) -> dict[str, Any]:
    lines = [line.strip() for line in str(result.get("stdout", "")).splitlines() if line.strip()]
    matched_terms = [
        term
        for term in expected_terms
        if any(term in line for line in lines)
    ]
    return {
        "probe_status": result.get("status"),
        "line_count": len(lines),
        "matched_terms": matched_terms,
        "sample_lines": lines[-5:],
    }


def _parse_usersession_reuse_analysis(result: dict[str, Any]) -> dict[str, Any]:
    lines = [line.strip() for line in str(result.get("stdout", "")).splitlines() if line.strip()]
    ff_session_re = re.compile(r"ff-session:\s*(?P<ff_session>[A-Za-z0-9]+)")
    fa_session_re = re.compile(r"Using existing FASessionId:\s*(?P<fa_session>[A-Za-z0-9]+)")
    bracket_id_re = re.compile(r"\[(?P<token>[A-Za-z0-9]{8,})\]")

    pair_index: dict[tuple[str, str], dict[str, Any]] = {}
    validation_only_markers: list[str] = []
    last_ff_line_index: int | None = None
    last_ff_session_id: str | None = None

    for index, line in enumerate(lines):
        ff_match = ff_session_re.search(line)
        if ff_match:
            last_ff_line_index = index
            last_ff_session_id = ff_match.group("ff_session")
            continue

        if (
            "UserSession::isUserSessionValid" in line
            or "Destination module: [UserSession], Command: [isUserSessionValid]" in line
            or "Command Dispatcher [UserSession:isUserSessionValid]" in line
        ):
            if line not in validation_only_markers:
                validation_only_markers.append(line)

        fa_match = fa_session_re.search(line)
        if not fa_match or last_ff_line_index is None or last_ff_session_id is None:
            continue

        if index - last_ff_line_index > 4:
            continue

        bracket_tokens = bracket_id_re.findall(line)
        if last_ff_session_id not in bracket_tokens:
            continue

        pair_key = (last_ff_session_id, fa_match.group("fa_session"))
        existing = pair_index.get(pair_key)
        if existing is None:
            existing = {
                "ff_session_id": last_ff_session_id,
                "fa_session_id": fa_match.group("fa_session"),
                "occurrence_count": 0,
                "observed_methods": [],
                "correlation_basis": "same_session_id_and_tight_adjacency",
                "sample_lines": [],
            }
            pair_index[pair_key] = existing

        existing["occurrence_count"] += 1
        window_lines = lines[last_ff_line_index : min(len(lines), index + 1)]
        methods = []
        if any("UserSession::getUserSession" in candidate for candidate in window_lines):
            methods.append("UserSession::getUserSession")
        if any("UserSession::isUserSessionValid" in candidate for candidate in window_lines):
            methods.append("UserSession::isUserSessionValid")
        existing["observed_methods"] = _dedupe_preserve_order(existing["observed_methods"] + methods)
        existing["sample_lines"] = _dedupe_preserve_order(existing["sample_lines"] + window_lines)[-6:]

    reuse_pairs = sorted(
        pair_index.values(),
        key=lambda item: (-item["occurrence_count"], item["ff_session_id"], item["fa_session_id"]),
    )
    repeated_pair_count = sum(1 for pair in reuse_pairs if pair["occurrence_count"] > 1)
    distinct_ff_session_count = len({pair["ff_session_id"] for pair in reuse_pairs})
    distinct_fa_session_count = len({pair["fa_session_id"] for pair in reuse_pairs})

    return {
        "reuse_pairs": reuse_pairs[:5],
        "repeated_pair_count": repeated_pair_count,
        "distinct_ff_session_count": distinct_ff_session_count,
        "distinct_fa_session_count": distinct_fa_session_count,
        "validation_only_marker_count": len(validation_only_markers),
        "validation_only_markers": validation_only_markers[-5:],
    }


def _find_named_boolean(payload: Any, target_key: str) -> bool | None:
    if isinstance(payload, dict):
        name_value = payload.get("name")
        status_value = payload.get("status")
        if name_value == target_key and isinstance(status_value, bool):
            return status_value
        for key, value in payload.items():
            if key == target_key and isinstance(value, bool):
                return value
            nested = _find_named_boolean(value, target_key)
            if nested is not None:
                return nested
    if isinstance(payload, list):
        for item in payload:
            nested = _find_named_boolean(item, target_key)
            if nested is not None:
                return nested
    return None


def _build_next_candidate_seams(
    component_records: list[dict[str, Any]],
    *,
    edge_route_hints: list[dict[str, Any]],
    boundary_packets: list[dict[str, Any]],
    session_parity_packets: list[dict[str, Any]],
    usersession_bridge_packets: list[dict[str, Any]],
    usersession_reuse_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seams: list[dict[str, Any]] = []
    aff_packet = next(
        (packet for packet in boundary_packets if packet.get("boundary_id") == "aff_fireflow_1989_route_owner"),
        None,
    )
    session_packet = next(
        (packet for packet in session_parity_packets if packet.get("packet_id") == "aff_session_route_parity"),
        None,
    )
    usersession_packet = next(
        (packet for packet in usersession_bridge_packets if packet.get("packet_id") == "fireflow_usersession_bridge"),
        None,
    )
    reuse_packet = next(
        (packet for packet in usersession_reuse_packets if packet.get("packet_id") == "usersession_fa_session_reuse"),
        None,
    )
    if reuse_packet is not None and reuse_packet.get("status") == "reuse_chain_visible":
        seams.append(
            {
                "seam_id": "trace_businessflow_session_origin",
                "why_it_matters": "The retained FireFlow window now shows concrete `ff-session -> reused FA-session` pairs, so the next bounded question is which upstream BusinessFlow or AFA-side caller fed that session context into the confirmed FireFlow bridge.",
                "starting_components": ["ms-bflow", "aff-boot", "httpd"],
            }
        )
    elif usersession_packet is not None and usersession_packet.get("status") == "bridge_signals_visible":
        seams.append(
            {
                "seam_id": "trace_usersession_fa_session_reuse",
                "why_it_matters": "The retained UserSession bridge is now visible behind the confirmed AFF session hop, so the next bounded stop is the reused FA-session chain rather than reopening general FireFlow internals.",
                "starting_components": ["httpd", "ms-bflow", "aff-boot"],
            }
        )
    elif session_packet is not None and session_packet.get("status") == "parity_confirmed":
        seams.append(
            {
                "seam_id": "inspect_fireflow_usersession_bridge",
                "why_it_matters": "The fronted and direct AFF session probes now agree, so the next bounded seam should stay narrow and inspect the FireFlow UserSession-style bridge behind aff-boot instead of reopening route ownership.",
                "starting_components": ["httpd", "ms-bflow", aff_packet["local_owner"]["component_id"]] if aff_packet is not None else ["httpd", "ms-bflow", "aff-boot"],
            }
        )
    elif aff_packet is not None:
        seams.append(
            {
                "seam_id": "validate_aff_session_route_parity",
                "why_it_matters": "The AFF route-owner packet is now stable enough to compare the fronted `/FireFlow/api/session` path with the direct local aff-boot session path on port 1989 without widening into deeper FireFlow workflow theory yet.",
                "starting_components": ["httpd", aff_packet["local_owner"]["component_id"]],
            }
        )
    edge_owned_components = [
        hint["likely_owner_component"]
        for hint in edge_route_hints
        if hint.get("likely_owner_component")
    ]
    if edge_owned_components:
        seams.append(
            {
                "seam_id": "trace_edge_to_local_service_routes",
                "why_it_matters": "Apache route hints now expose candidate local handoffs, so the next bounded pass can confirm which service owns each browser-facing route.",
                "starting_components": _dedupe_preserve_order(edge_owned_components)[:3],
            }
        )
    else:
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
    edge_route_hints = surface_map.get("edge_route_hints", [])[:5]
    boundary_packets = surface_map.get("boundary_packets", [])[:3]
    session_parity_packets = surface_map.get("session_parity_packets", [])[:2]
    usersession_bridge_packets = surface_map.get("usersession_bridge_packets", [])[:2]
    usersession_reuse_packets = surface_map.get("usersession_reuse_packets", [])[:2]
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
    lines.extend(["", "## Edge-To-Local Route Hints", ""])
    if edge_route_hints:
        for hint in edge_route_hints:
            route_path = hint.get("route_path") or "(route path not explicit)"
            backend = hint.get("backend_url") or (f"port {hint['backend_port']}" if hint.get("backend_port") else "no backend target")
            owner = hint.get("likely_owner_component") or "owner still unclear"
            match_reason = hint.get("match_reason") or "bounded config clue only"
            lines.append(
                f"- `{route_path}` via `{hint['directive']}` in `{hint['config_path']}:{hint['line_number']}` "
                f"points toward `{backend}`; likely owner `{owner}` ({match_reason})."
            )
    else:
        lines.append("- No Apache route hints were strong enough to summarize in this pass.")
    lines.extend(["", "## Boundary Packets", ""])
    if boundary_packets:
        for packet in boundary_packets:
            owner = packet["local_owner"]["component_id"]
            ports = ", ".join(str(port) for port in packet["local_owner"].get("listening_ports", [])) or "none"
            routes = ", ".join(packet.get("route_family", [])) or "no named routes"
            lines.append(
                f"- `{packet['boundary_id']}`: {packet['display_name']} confirms routes {routes} through owner `{owner}` on local ports {ports}."
            )
    else:
        lines.append("- No bounded boundary packet was strong enough to summarize in this pass.")
    lines.extend(["", "## Session Parity Packets", ""])
    if session_parity_packets:
        for packet in session_parity_packets:
            fronted_status = packet["fronted_probe"].get("http_status_code")
            direct_status = packet["direct_probe"].get("http_status_code")
            body_match = packet["agreement"].get("body_match")
            invalid_code = packet["agreement"].get("invalid_session_code_match")
            next_stop = packet.get("next_stop")
            lines.append(
                f"- `{packet['packet_id']}`: status `{packet['status']}`; fronted `/FireFlow/api/session` returned `{fronted_status}`, direct aff-boot session returned `{direct_status}`, body match `{body_match}`, invalid-session code match `{invalid_code}`. Next stop: `{next_stop}`."
            )
    else:
        lines.append("- No bounded AFF session parity packet was strong enough to summarize in this pass.")
    lines.extend(["", "## UserSession Bridge", ""])
    if usersession_bridge_packets:
        for packet in usersession_bridge_packets:
            httpd_terms = ", ".join(packet["httpd_markers"].get("matched_terms", [])) or "none"
            fireflow_terms = ", ".join(packet["fireflow_markers"].get("matched_terms", [])) or "none"
            lines.append(
                f"- `{packet['packet_id']}`: status `{packet['status']}`; Apache markers `{httpd_terms}` and FireFlow markers `{fireflow_terms}` are visible. Next stop: `{packet['next_stop']}`."
            )
    else:
        lines.append("- No bounded UserSession bridge packet was strong enough to summarize in this pass.")
    lines.extend(["", "## Reused FA Session Chain", ""])
    if usersession_reuse_packets:
        for packet in usersession_reuse_packets:
            pair_summaries = []
            for pair in packet.get("reuse_pairs", [])[:3]:
                pair_summaries.append(
                    f"{pair['ff_session_id']} -> {pair['fa_session_id']} x{pair['occurrence_count']}"
                )
            pair_summary = ", ".join(pair_summaries) or "no concrete pairs"
            lines.append(
                f"- `{packet['packet_id']}`: status `{packet['status']}`; retained pairs `{pair_summary}`. Next stop: `{packet['next_stop']}`."
            )
    else:
        lines.append("- No bounded reused FA-session packet was strong enough to summarize in this pass.")
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


def _extract_httpd_route_path(tokens: list[str], current_location: str | None) -> str | None:
    if len(tokens) >= 2 and tokens[1].startswith("/"):
        return tokens[1]
    if tokens and tokens[0] == "JkMount" and len(tokens) >= 2 and tokens[1].startswith("/"):
        return tokens[1]
    return current_location


def _extract_httpd_backend_url(tokens: list[str]) -> str | None:
    for token in tokens[1:]:
        if token.startswith("http://") or token.startswith("https://"):
            return token
    return None


def _extract_httpd_backend_port(content: str) -> int | None:
    match = HTTPD_URL_RE.search(content)
    if match and match.group("port") and match.group("port").isdigit():
        return int(match.group("port"))
    return None


def _extract_httpd_listen_port(tokens: list[str]) -> int | None:
    if len(tokens) < 2:
        return None
    listen_target = tokens[1]
    if ":" in listen_target:
        listen_target = listen_target.rsplit(":", 1)[-1]
    if listen_target.isdigit():
        return int(listen_target)
    return None


def _build_edge_route_hints(
    route_rows: list[dict[str, Any]],
    component_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not route_rows:
        return []

    records_by_component = {record["component_id"]: record for record in component_records}
    hints: list[dict[str, Any]] = []
    for route_row in route_rows:
        if route_row["directive"] == "Listen":
            continue
        owner_component, owner_match_reason, confidence = _match_route_owner(route_row, component_records)
        hints.append(
            {
                "directive": route_row["directive"],
                "config_path": route_row["config_path"],
                "line_number": route_row["line_number"],
                "route_path": route_row.get("route_path"),
                "backend_url": route_row.get("backend_url"),
                "backend_port": route_row.get("backend_port"),
                "likely_owner_component": owner_component,
                "match_reason": owner_match_reason,
                "confidence": confidence,
                "owner_category": None
                if owner_component is None
                else records_by_component.get(owner_component, {}).get("inference", {}).get("first_observed_category"),
            }
        )
    return sorted(
        hints,
        key=lambda hint: (
            0 if hint.get("likely_owner_component") else 1,
            {"high": 0, "medium": 1, "low": 2}.get(str(hint.get("confidence")), 3),
            hint.get("config_path", ""),
            hint.get("line_number", 0),
        ),
    )


def _match_route_owner(
    route_row: dict[str, Any],
    component_records: list[dict[str, Any]],
) -> tuple[str | None, str, str]:
    route_haystack = " ".join(
        filter(
            None,
            [
                str(route_row.get("route_path") or ""),
                str(route_row.get("config_path") or ""),
                str(route_row.get("raw_line") or ""),
            ],
        )
    ).lower()
    config_basename = Path(str(route_row.get("config_path") or "")).name.lower()
    backend_port = route_row.get("backend_port")
    if isinstance(backend_port, int):
        exact_port_matches = [
            record
            for record in component_records
            if any(
                binding.get("bind_port") == backend_port and binding.get("ownership_basis") == "exact_pid"
                for binding in record["observed"].get("listener_bindings", [])
            )
        ]
        if len(exact_port_matches) == 1:
            return exact_port_matches[0]["component_id"], f"listener port {backend_port} matches exact PID ownership", "high"
        if len(exact_port_matches) > 1:
            ranked = sorted(
                exact_port_matches,
                key=lambda record: (
                    -record["inference"]["support_priority_score"],
                    record["display_name"],
                ),
            )
            return ranked[0]["component_id"], f"listener port {backend_port} matches multiple exact-PID components", "medium"

    config_name_matches = _route_config_name_matches(config_basename, component_records)
    if config_name_matches:
        return config_name_matches[0]["component_id"], f"Apache config file family `{config_basename}` matches component naming", "medium"

    for record in component_records:
        component_token = record["component_id"].lower()
        if component_token and component_token in route_haystack:
            return record["component_id"], f"name hint `{record['component_id']}` is visible in Apache route config", "medium"

    if isinstance(backend_port, int):
        port_matches = [
            record
            for record in component_records
            if backend_port in record["observed"]["listening_ports"]
        ]
        if len(port_matches) == 1:
            return port_matches[0]["component_id"], f"listener port {backend_port} matches by bounded fallback only", "low"
        if len(port_matches) > 1:
            ranked = sorted(
                port_matches,
                key=lambda record: (
                    -record["inference"]["support_priority_score"],
                    record["display_name"],
                ),
            )
            return ranked[0]["component_id"], f"listener port {backend_port} matches multiple fallback candidates", "low"

    if "keycloak" in route_haystack:
        return "keycloak", "Apache route config names Keycloak directly", "medium"
    return None, "bounded config clue only", "low"


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    deduped: list[str] = []
    for value in values:
        if value not in deduped:
            deduped.append(value)
    return deduped


def _is_generic_process_name(process_name: str) -> bool:
    lowered = process_name.lower().strip()
    return lowered in {
        "java",
        "sh",
        "bash",
        "dash",
        "perl",
        "python",
        "python3",
    }


def _route_config_name_matches(
    config_basename: str,
    component_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    normalized_name = config_basename.removesuffix(".conf")
    for record in component_records:
        component_id = record["component_id"].lower()
        if normalized_name.startswith(component_id):
            matches.append(record)
            continue
        component_prefix = component_id.split("-", 1)[0]
        if component_prefix and (normalized_name == component_prefix or normalized_name.startswith(f"{component_prefix}.")):
            matches.append(record)
    return sorted(
        matches,
        key=lambda record: (
            -record["inference"]["support_priority_score"],
            record["display_name"],
        ),
    )


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
