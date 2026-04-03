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
PLAYBOOK_NAME = "diagnostic-playbook.md"
COOKBOOK_NAME = "runtime-cookbook-guide.md"
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
KNOWN_EXTERNAL_VENDOR_TERMS = (
    ("aws", "AWS"),
    ("azure", "Azure"),
    ("check point", "Check Point"),
    ("fortinet", "Fortinet"),
    ("juniper", "Juniper"),
    ("palo alto", "Palo Alto Networks"),
    ("panorama", "Panorama"),
    ("zscaler", "Zscaler"),
    ("vmware nsx", "VMware NSX"),
    ("f5", "F5 BIG-IP"),
    ("arista", "Arista"),
    ("cisco", "Cisco"),
)
KNOWN_DISTRIBUTED_ADJACENT_FAMILIES = {
    "ms-aad-azure-sensor",
    "ms-aad-log-sensor",
    "ms-autodiscovery",
}
KNOWN_CLOUD_ADJACENT_FAMILIES = {
    "ms-cloudflow-broker",
    "ms-cloudlicensing",
}
KNOWN_PROVIDER_CONFIG_FAMILIES = {
    "ms-devicedriver-aws",
    "ms-devicedriver-azure",
}
EXTERNAL_SURFACE_ROUTE_PREFIXES = {
    "/afa/external": "afa_external_surface",
    "/afa/api": "afa_api_surface",
    "/BusinessFlow": "businessflow_surface",
    "/FireFlow": "fireflow_surface",
    "/aff/api": "aff_surface",
    "/keycloak/": "identity_surface",
    "/ms-mapDiagnostics": "map_diagnostics_surface",
}
PROVIDER_DRIVER_VENDOR_LABELS = {
    "ms-devicedriver-aws": "AWS",
    "ms-devicedriver-azure": "Azure",
}
PROVIDER_ADJACENT_FAMILY_LABELS = {
    "ms-aad-azure-sensor": "Azure",
    "ms-aad-log-sensor": "Azure",
    "ms-cloudflow-broker": "AWS",
    "ms-cloudlicensing": "AWS",
}
CONFIG_PATH_RE = re.compile(r"(/[^\s\"']+\.(?:conf|cfg|ini|xml|yaml|yml|properties|json))")
LOG_PATH_RE = re.compile(r"(/[^\s\"']+(?:/logs?/[^\"'\s]+|/log/[^\"'\s]+|\.log(?:\.\d+)?))")
GENERIC_PATH_RE = re.compile(r"(?<![A-Za-z0-9_])(/[^ \t\n\r\"';,|)}]+)")
LISTENER_PROCESS_RE = re.compile(r'users:\(\("(?P<process>[^"]+)",pid=(?P<pid>\d+)')
HTTPD_ROUTE_LINE_RE = re.compile(r"^(?P<config_path>/[^:]+):(?P<line_number>\d+):(?P<content>.*)$")
HTTPD_LOCATION_RE = re.compile(r"<Location(?:Match)?\s+\"?(?P<route>[^\"> ]+)\"?", re.IGNORECASE)
HTTPD_URL_RE = re.compile(r"https?://[^/\s:]+(?::(?P<port>\d+))?[^ \t]*", re.IGNORECASE)
HTTPD_MS_FAMILY_RE = re.compile(r"^algosec-ms\.(?P<family>[^/]+)\.conf$")
SYSTEMD_SHOW_SPLIT_MARKER = "__ADF_UNIT_SHOW_SPLIT__"
SYSTEMD_UNIT_DETAILS_COMMAND = (
    "while read -r unit _; do "
    "[ -n \"$unit\" ] || continue; "
    "systemctl show \"$unit\" "
    "--property=Id,FragmentPath,DropInPaths,EnvironmentFiles,ExecStart,ExecStartPre,ExecStartPost,ExecReload,"
    "WorkingDirectory,LogsDirectory,ConfigurationDirectory,StateDirectory "
    "2>/dev/null || true; "
    f"echo '{SYSTEMD_SHOW_SPLIT_MARKER}'; "
    "done < <(systemctl list-units --type=service --all --no-pager --plain --no-legend)"
)
HTTPD_ROUTE_HINT_COMMAND = (
    "if [ -d /etc/httpd ]; then "
    "grep -R -n -E '^[[:space:]]*(ProxyPass|ProxyPassReverse|ProxyPassMatch|RewriteRule|JkMount|Listen)[[:space:]]|<Location[^>]*>' "
    "/etc/httpd/conf /etc/httpd/conf.d 2>/dev/null || true; "
    "fi"
)
ESTABLISHED_TCP_CONNECTIONS_COMMAND = "ss -ntpH state established || true"
TCP_PROBE_SUCCESS_MARKER = "__ADF_TCP_OK__"
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
BUSINESSFLOW_SESSION_ORIGIN_HTTPD_MARKERS_COMMAND = (
    "grep -E '/fa/server/connection/login|/fa/environment/getAFASessionInfo|/afa/external//bridge/storeFireflowCookie|"
    "/afa/external//bridge/refresh|/afa/external//session/extend|"
    "/FireFlow/FireFlowAffApi/NoAuth/CommandsDispatcher|/afa/php/ws.php|"
    "/BusinessFlow/shallow_health_check|/BusinessFlow/deep_health_check|"
    "/aff/api/internal/noauth/health/shallow|/aff/api/internal/noauth/health/deep' "
    "/var/log/httpd/ssl_access_log* 2>/dev/null | tail -n 120 || true"
)
BUSINESSFLOW_SESSION_ORIGIN_SOURCE_MARKERS_COMMAND = (
    "grep -R -n -E 'AFF_COOKIE|BFCookie|getAFASessionInfo|Could not find AlgosecSession|"
    "VerifyGetFASessionIdValid|getFireflowCookie|checkFireFlowAuth|storeFireflowCookie' "
    "/usr/share/fa/php /usr/share/fireflow 2>/dev/null | tail -n 120 || true"
)
HTTP_STATUS_MARKER = "__ADF_HTTP_STATUS__:"
AFF_SESSION_SERVICE_UNITS = ("httpd.service", "ms-bflow.service", "aff-boot.service")
CONFIG_OPTION_PREFIXES = (
    "-Dlogback.configurationFile=",
    "-Dlogging.config=",
    "-Dspring.config.location=",
    "-Dspring.config.additional-location=",
    "-Dactivemq.conf=",
    "-Dcatalina.base=",
    "-Dcatalina.home=",
    "-Djboss.server.config.dir=",
    "-Dkc.config-file=",
)
LOG_OPTION_PREFIXES = (
    "-XX:HeapDumpPath=",
    "-Dlogging.file.name=",
    "-Dlogging.file.path=",
    "-Djboss.server.log.dir=",
)
PROVIDER_JOURNAL_FAILURE_PATTERNS = (
    ("auth_failure", re.compile(r"(?i)(authentication failed|authorization failed|unauthorized|forbidden|invalid credentials|access denied)")),
    ("network_failure", re.compile(r"(?i)(connection refused|timed out|timeout|no route to host|network is unreachable|name or service not known|temporary failure in name resolution|connection reset)")),
    ("tls_failure", re.compile(r"(?i)(certificate|ssl|tls|handshake)")),
    ("runtime_failure", re.compile(r"(?i)(fatal|exception|failed to| failure\\b)")),
)
DIRECTIONALITY_COORDINATION_FAMILIES = (
    "algosec-ms",
    "ms-configuration",
    "ms-devicemanager",
    "ms-genericdevice",
    "ms-devicedriver-aws",
    "ms-devicedriver-azure",
)
DIRECTIONALITY_SIGNAL_PATTERNS = (
    ("dispatch", re.compile(r"(?i)\b(dispatch|dispatcher|enqueue|publish|forward)\b")),
    ("receive", re.compile(r"(?i)\b(receive|received|receiving|consume|consumed)\b")),
    ("polling", re.compile(r"(?i)\b(poll|polling|heartbeat|keepalive|refresh)\b")),
    ("agent", re.compile(r"(?i)\b(remote[- ]agent|agent)\b")),
    ("manager", re.compile(r"(?i)\b(manager|management)\b")),
    ("registration", re.compile(r"(?i)\b(register|registered|registration)\b")),
)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


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
    provider_health_command_results = _collect_provider_health_command_results(
        target_connection=target_connection,
        component_records=component_records,
        edge_route_hints=edge_route_hints,
    )
    if provider_health_command_results:
        command_results.extend(provider_health_command_results)
    directionality_command_results = _collect_directionality_command_results(
        target_connection=target_connection,
        component_records=component_records,
    )
    if directionality_command_results:
        command_results.extend(directionality_command_results)
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
    businessflow_session_origin_packets = _build_businessflow_session_origin_packets(
        command_results,
        usersession_reuse_packets=usersession_reuse_packets,
    )
    bootstrap_polling_packets = _build_bootstrap_polling_packets(
        command_results,
        businessflow_session_origin_packets=businessflow_session_origin_packets,
    )
    aff_cookie_handoff_packets = _build_aff_cookie_handoff_packets(
        command_results,
        edge_route_hints=edge_route_hints,
        usersession_reuse_packets=usersession_reuse_packets,
        bootstrap_polling_packets=bootstrap_polling_packets,
    )
    java_runtime_cluster_packets = _build_java_runtime_cluster_packets(
        component_records,
        edge_route_hints=edge_route_hints,
        boundary_packets=boundary_packets,
        aff_cookie_handoff_packets=aff_cookie_handoff_packets,
    )
    provider_integration_packets = _build_provider_integration_packets(
        component_records,
        edge_route_hints=edge_route_hints,
        target_label=target_label,
        command_results=command_results,
    )
    knowledge_layer_packets = _build_knowledge_layer_packets(
        component_records,
        edge_route_hints=edge_route_hints,
        java_runtime_cluster_packets=java_runtime_cluster_packets,
        provider_integration_packets=provider_integration_packets,
        docpack_hints=docpack_hints,
        target_label=target_label,
    )
    next_candidate_seams = _build_next_candidate_seams(
        component_records,
        edge_route_hints=edge_route_hints,
        boundary_packets=boundary_packets,
        session_parity_packets=session_parity_packets,
        usersession_bridge_packets=usersession_bridge_packets,
        usersession_reuse_packets=usersession_reuse_packets,
        businessflow_session_origin_packets=businessflow_session_origin_packets,
        bootstrap_polling_packets=bootstrap_polling_packets,
        aff_cookie_handoff_packets=aff_cookie_handoff_packets,
        java_runtime_cluster_packets=java_runtime_cluster_packets,
        provider_integration_packets=provider_integration_packets,
        knowledge_layer_packets=knowledge_layer_packets,
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
            "engineer_consumable_artifacts": [
                PLAYBOOK_NAME,
                COOKBOOK_NAME,
            ],
        },
        "collection_policy": {
            "mode": "read_only",
            "fact_inference_boundary": "observed facts, tentative inference, and unknowns are kept separate",
            "command_scope": [
                "runtime_identity",
                "systemd_units",
                "systemd_unit_files",
                "systemd_unit_details",
                "listening_tcp_ports",
                "established_tcp_connections",
                "process_inventory",
                "httpd_route_hints",
                "aff_session_parity_checks",
                "fireflow_usersession_bridge_hints",
                "businessflow_session_origin_hints",
                "provider_health_local_probes",
                "directionality_coordination_journals",
            ],
            "out_of_scope": [
                "deep dependency mapping",
                "deep config file parsing",
                "log content interpretation beyond bounded marker checks",
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
        "businessflow_session_origin_packets": businessflow_session_origin_packets,
        "bootstrap_polling_packets": bootstrap_polling_packets,
        "aff_cookie_handoff_packets": aff_cookie_handoff_packets,
        "java_runtime_cluster_packets": java_runtime_cluster_packets,
        "provider_integration_packets": provider_integration_packets,
        "knowledge_layer_packets": knowledge_layer_packets,
        "unknowns": _build_global_unknowns(command_results, component_records, edge_route_hints=edge_route_hints),
        "next_candidate_seams": next_candidate_seams,
    }
    summary = _render_summary(surface_map)
    playbook = _render_diagnostic_playbook(surface_map)
    cookbook = _render_runtime_cookbook(surface_map)

    _dump_json(root / SURFACE_MAP_NAME, surface_map)
    (root / SUMMARY_NAME).write_text(summary, encoding="utf-8")
    (root / PLAYBOOK_NAME).write_text(playbook, encoding="utf-8")
    (root / COOKBOOK_NAME).write_text(cookbook, encoding="utf-8")

    mirrored_files: list[str] = []
    if mirror_into_run_id:
        mirrored_files = _mirror_generated_files_into_run(
            project_root=project_root,
            artifact_root=root,
            run_id=mirror_into_run_id,
            generated_files=[
                root / SURFACE_MAP_NAME,
                root / SUMMARY_NAME,
                root / PLAYBOOK_NAME,
                root / COOKBOOK_NAME,
            ],
        )

    result: dict[str, Any] = {
        "status": "pass",
        "artifact_root": str(root.relative_to(project_root)),
        "generated_files": [
            str((root / SURFACE_MAP_NAME).relative_to(project_root)),
            str((root / SUMMARY_NAME).relative_to(project_root)),
            str((root / PLAYBOOK_NAME).relative_to(project_root)),
            str((root / COOKBOOK_NAME).relative_to(project_root)),
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
            "businessflow_session_origin_packet_count": len(businessflow_session_origin_packets),
            "bootstrap_polling_packet_count": len(bootstrap_polling_packets),
            "aff_cookie_handoff_packet_count": len(aff_cookie_handoff_packets),
            "java_runtime_cluster_packet_count": len(java_runtime_cluster_packets),
            "provider_integration_packet_count": len(provider_integration_packets),
            "knowledge_layer_packet_count": len(knowledge_layer_packets),
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
    run_root.mkdir(parents=True, exist_ok=True)
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
                command_id="systemd_unit_details",
                argv=["bash", "-lc", SYSTEMD_UNIT_DETAILS_COMMAND],
                max_preview_lines=250,
            ),
            _run_command(
                command_id="listening_tcp_ports",
                argv=["ss", "-lntpH"],
                max_preview_lines=250,
            ),
            _run_command(
                command_id="established_tcp_connections",
                argv=["bash", "-lc", ESTABLISHED_TCP_CONNECTIONS_COMMAND],
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
            _run_command(
                command_id="businessflow_session_origin_httpd_markers",
                argv=["bash", "-lc", BUSINESSFLOW_SESSION_ORIGIN_HTTPD_MARKERS_COMMAND],
                max_preview_lines=250,
            ),
            _run_command(
                command_id="businessflow_session_origin_source_markers",
                argv=["bash", "-lc", BUSINESSFLOW_SESSION_ORIGIN_SOURCE_MARKERS_COMMAND],
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
            command_id="systemd_unit_details",
            command=SYSTEMD_UNIT_DETAILS_COMMAND,
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
            command_id="established_tcp_connections",
            command=ESTABLISHED_TCP_CONNECTIONS_COMMAND,
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
            command_id="businessflow_session_origin_httpd_markers",
            command=BUSINESSFLOW_SESSION_ORIGIN_HTTPD_MARKERS_COMMAND,
            timeout_seconds=timeout_seconds,
        ),
        _run_target_command(
            target_connection=target_connection,
            command_id="businessflow_session_origin_source_markers",
            command=BUSINESSFLOW_SESSION_ORIGIN_SOURCE_MARKERS_COMMAND,
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


def _collect_provider_health_command_results(
    *,
    target_connection: dict[str, Any] | None,
    component_records: list[dict[str, Any]],
    edge_route_hints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    plan = _build_provider_health_probe_plan(
        component_records=component_records,
        edge_route_hints=edge_route_hints,
    )
    if not plan:
        return []

    if target_connection is None:
        results: list[dict[str, Any]] = []
        for item in plan:
            if item.get("service_unit"):
                results.append(
                    _run_command(
                        command_id=f"provider_journal_{item['family_id']}",
                        argv=["bash", "-lc", _provider_journal_command(str(item["service_unit"]))],
                        max_preview_lines=250,
                    )
                )
            if item.get("probe_port") is not None:
                results.append(
                    _run_command(
                        command_id=f"provider_local_port_probe_{item['family_id']}",
                        argv=["bash", "-lc", _provider_local_port_probe_command(int(item["probe_port"]))],
                        max_preview_lines=40,
                    )
                )
        return results

    timeout_seconds = int(target_connection.get("timeouts", {}).get("command_seconds", 120))
    results = []
    for item in plan:
        if item.get("service_unit"):
            results.append(
                _run_target_command(
                    target_connection=target_connection,
                    command_id=f"provider_journal_{item['family_id']}",
                    command=_provider_journal_command(str(item["service_unit"])),
                    timeout_seconds=timeout_seconds,
                )
            )
        if item.get("probe_port") is not None:
            results.append(
                _run_target_command(
                    target_connection=target_connection,
                    command_id=f"provider_local_port_probe_{item['family_id']}",
                    command=_provider_local_port_probe_command(int(item["probe_port"])),
                    timeout_seconds=timeout_seconds,
                )
            )
    return results


def _collect_directionality_command_results(
    *,
    target_connection: dict[str, Any] | None,
    component_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    plan = _build_directionality_probe_plan(component_records=component_records)
    if not plan:
        return []

    if target_connection is None:
        return [
            _run_command(
                command_id=f"directionality_journal_{item['family_id']}",
                argv=["bash", "-lc", _directionality_journal_command(str(item["service_unit"]))],
                max_preview_lines=250,
            )
            for item in plan
            if item.get("service_unit")
        ]

    timeout_seconds = int(target_connection.get("timeouts", {}).get("command_seconds", 120))
    return [
        _run_target_command(
            target_connection=target_connection,
            command_id=f"directionality_journal_{item['family_id']}",
            command=_directionality_journal_command(str(item["service_unit"])),
            timeout_seconds=timeout_seconds,
        )
        for item in plan
        if item.get("service_unit")
    ]


def _build_provider_health_probe_plan(
    *,
    component_records: list[dict[str, Any]],
    edge_route_hints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    route_families = _extract_httpd_route_families(edge_route_hints)
    route_family_by_id = {
        str(family.get("family_id")): family
        for family in route_families
        if family.get("family_id")
    }
    records_by_id = {
        str(record.get("component_id")): record
        for record in component_records
        if record.get("component_id")
    }
    plan: list[dict[str, Any]] = []
    for family_id, vendor_label in PROVIDER_DRIVER_VENDOR_LABELS.items():
        route_family = route_family_by_id.get(family_id)
        record = records_by_id.get(family_id)
        if route_family is None and record is None:
            continue
        observed = (record or {}).get("observed", {})
        listener_ports = observed.get("listening_ports", []) if observed else []
        backend_port = (route_family or {}).get("backend_ports", [None])[0]
        probe_port = backend_port if backend_port is not None else (listener_ports[0] if listener_ports else None)
        plan.append(
            {
                "family_id": family_id,
                "vendor_label": vendor_label,
                "service_unit": observed.get("service_unit"),
                "probe_port": probe_port,
            }
        )
    return plan


def _build_directionality_probe_plan(
    *,
    component_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records_by_id = {
        str(record.get("component_id")): record
        for record in component_records
        if record.get("component_id")
    }
    plan: list[dict[str, Any]] = []
    for family_id in DIRECTIONALITY_COORDINATION_FAMILIES:
        record = records_by_id.get(family_id)
        if record is None:
            continue
        service_unit = record.get("observed", {}).get("service_unit")
        if not service_unit:
            continue
        plan.append(
            {
                "family_id": family_id,
                "service_unit": service_unit,
            }
        )
    return plan


def _provider_journal_command(service_unit: str) -> str:
    return f"journalctl -u {shlex.quote(service_unit)} --no-pager -n 120 || true"


def _directionality_journal_command(service_unit: str) -> str:
    return f"journalctl -u {shlex.quote(service_unit)} --no-pager -n 120 || true"


def _provider_local_port_probe_command(port: int) -> str:
    return (
        f"timeout 5 bash -lc 'exec 3<>/dev/tcp/127.0.0.1/{port}; "
        f"printf \"{TCP_PROBE_SUCCESS_MARKER}\\\\n\"; exec 3<&-; exec 3>&-' || true"
    )


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
    unit_details = _parse_systemd_unit_details(results_by_id.get("systemd_unit_details", {}))
    listeners = _parse_listeners(results_by_id.get("listening_tcp_ports", {}))
    established_connections = _parse_established_tcp_connections(results_by_id.get("established_tcp_connections", {}))
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
                "established_connection_bindings": [],
                "peer_connection_targets": [],
                "config_path_details": [],
                "config_path_candidates": [],
                "log_path_details": [],
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
        detail = unit_details.get(unit_name)
        if detail is not None:
            observed = records[unit_name]["observed"]
            observed["main_command"] = observed["main_command"] or _extract_execstart_command(detail)
            observed["config_path_details"] = _merge_path_details(
                observed["config_path_details"],
                _build_unit_detail_config_paths(detail),
            )
            observed["log_path_details"] = _merge_path_details(
                observed["log_path_details"],
                _build_unit_detail_log_paths(detail),
            )
            if "systemd_unit_details" not in observed["source_command_ids"]:
                observed["source_command_ids"].append("systemd_unit_details")

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
                    "established_connection_bindings": [],
                    "peer_connection_targets": [],
                    "config_path_details": [],
                    "config_path_candidates": [],
                    "log_path_details": [],
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
        command_config_details, command_log_details = _extract_command_path_details(process["command"])
        if "process_inventory" not in observed["record_sources"]:
            observed["record_sources"].append("process_inventory")
        observed["process_name"] = observed["process_name"] or process["comm"]
        observed["process_id"] = observed["process_id"] or process["pid"]
        if observed["main_command"] is None or _should_replace_main_command(observed["main_command"], process["command"]):
            observed["process_name"] = process["comm"]
            observed["process_id"] = process["pid"]
            observed["main_command"] = process["command"]
        observed["config_path_details"] = _merge_path_details(
            observed["config_path_details"],
            command_config_details,
        )
        observed["log_path_details"] = _merge_path_details(
            observed["log_path_details"],
            command_log_details,
        )
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
        observed["established_connection_bindings"] = _connection_bindings_for_record(
            established_connections,
            record,
            process_index=process_index,
            children_by_ppid=children_by_ppid,
        )
        observed["peer_connection_targets"] = _merge_unique(
            observed["peer_connection_targets"],
            [
                binding["remote_ip"]
                for binding in observed["established_connection_bindings"]
                if _is_non_loopback_ip(str(binding.get("remote_ip") or ""))
            ],
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

    component_records = sorted(
        records.values(),
        key=lambda item: (
            -item["inference"]["support_priority_score"],
            item["display_name"].lower(),
        ),
    )
    edge_route_hints = _build_edge_route_hints(httpd_route_rows, component_records)
    _enrich_component_path_surfaces(component_records, edge_route_hints=edge_route_hints)
    for record in component_records:
        observed = record["observed"]
        observed["config_path_candidates"] = _merge_unique(
            observed["config_path_candidates"],
            _detail_paths_only(observed.get("config_path_details", [])),
        )
        observed["log_path_candidates"] = _merge_unique(
            observed["log_path_candidates"],
            _detail_paths_only(observed.get("log_path_details", [])),
        )
        record["unknowns"] = _build_record_unknowns(record)
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


def _parse_systemd_unit_details(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    if result.get("status") != "completed":
        return details
    for block in result.get("stdout", "").split(SYSTEMD_SHOW_SPLIT_MARKER):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        parsed: dict[str, str] = {}
        for line in lines:
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            parsed[key] = value.strip()
        unit_id = parsed.get("Id")
        if unit_id:
            details[unit_id] = parsed
    return details


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


def _parse_established_tcp_connections(result: dict[str, Any]) -> list[dict[str, Any]]:
    connections: list[dict[str, Any]] = []
    if result.get("status") != "completed":
        return connections
    for line in result.get("stdout", "").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        local_endpoint = parts[2]
        remote_endpoint = parts[3]
        local_ip, local_port = _parse_tcp_endpoint(local_endpoint)
        remote_ip, remote_port = _parse_tcp_endpoint(remote_endpoint)
        if local_ip is None or remote_ip is None:
            continue
        process_name = parts[-1] if parts else "unknown"
        process_id = None
        match = LISTENER_PROCESS_RE.search(line)
        if match:
            process_name = match.group("process")
            process_id = int(match.group("pid"))
        connections.append(
            {
                "local_ip": local_ip,
                "local_port": local_port,
                "remote_ip": remote_ip,
                "remote_port": remote_port,
                "process_name": process_name,
                "process_id": process_id,
            }
        )
    return connections


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


def _extract_any_paths(text: str) -> list[str]:
    return _dedupe_preserve_order(
        [
            _normalize_path_candidate(match.group(1))
            for match in GENERIC_PATH_RE.finditer(text)
            if not match.group(1).startswith("//")
        ]
    )


def _normalize_path_candidate(path: str) -> str:
    normalized = path.strip().rstrip(")]},;")
    if not normalized:
        return normalized
    if normalized.startswith("file:/"):
        normalized = normalized.removeprefix("file:")
    return normalized


def _build_path_detail(
    *,
    path: str,
    status: str,
    source: str,
    source_command_id: str,
    surface_kind: str = "path",
    note: str | None = None,
) -> dict[str, str]:
    detail = {
        "path": _normalize_path_candidate(path),
        "status": status,
        "source": source,
        "source_command_id": source_command_id,
        "surface_kind": surface_kind,
    }
    if note:
        detail["note"] = note
    return detail


def _merge_path_details(existing: list[dict[str, Any]], new_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = list(existing)
    seen = {
        (
            str(item.get("path") or ""),
            str(item.get("status") or ""),
            str(item.get("source") or ""),
            str(item.get("surface_kind") or ""),
        )
        for item in merged
    }
    for item in new_items:
        path = str(item.get("path") or "")
        if not path:
            continue
        key = (
            path,
            str(item.get("status") or ""),
            str(item.get("source") or ""),
            str(item.get("surface_kind") or ""),
        )
        if key in seen:
            continue
        merged.append(item)
        seen.add(key)
    return merged


def _detail_paths_only(details: list[dict[str, Any]]) -> list[str]:
    return _dedupe_preserve_order(
        [
            str(detail["path"])
            for detail in details
            if str(detail.get("surface_kind") or "path") == "path" and str(detail.get("path") or "").startswith("/")
        ]
    )


def _extract_command_path_details(command: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    config_details = [
        _build_path_detail(
            path=path,
            status="observed",
            source="process_command_path",
            source_command_id="process_inventory",
        )
        for path in _extract_paths(command, CONFIG_PATH_RE)
    ]
    log_details = [
        _build_path_detail(
            path=path,
            status="observed",
            source="process_command_path",
            source_command_id="process_inventory",
        )
        for path in _extract_paths(command, LOG_PATH_RE)
    ]
    for option_prefix in CONFIG_OPTION_PREFIXES:
        value = _extract_command_option_value(command, option_prefix)
        if value:
            config_details.append(
                _build_path_detail(
                    path=value,
                    status="observed",
                    source="process_command_option",
                    source_command_id="process_inventory",
                    note=f"Observed in runtime option `{option_prefix}`.",
                )
            )
    for option_prefix in LOG_OPTION_PREFIXES:
        value = _extract_command_option_value(command, option_prefix)
        if value:
            log_details.append(
                _build_path_detail(
                    path=value,
                    status="observed",
                    source="process_command_option",
                    source_command_id="process_inventory",
                    note=f"Observed in runtime option `{option_prefix}`.",
                )
            )

    catalina_base = _extract_command_option_value(command, "-Dcatalina.base=")
    if catalina_base:
        config_details.append(
            _build_path_detail(
                path=f"{catalina_base.rstrip('/')}/conf",
                status="candidate",
                source="derived_runtime_root",
                source_command_id="process_inventory",
                note="Derived from observed `-Dcatalina.base`.",
            )
        )
        log_details.append(
            _build_path_detail(
                path=f"{catalina_base.rstrip('/')}/logs",
                status="candidate",
                source="derived_runtime_root",
                source_command_id="process_inventory",
                note="Derived from observed `-Dcatalina.base`.",
            )
        )
    catalina_home = _extract_command_option_value(command, "-Dcatalina.home=")
    if catalina_home:
        config_details.append(
            _build_path_detail(
                path=f"{catalina_home.rstrip('/')}/conf",
                status="candidate",
                source="derived_runtime_root",
                source_command_id="process_inventory",
                note="Derived from observed `-Dcatalina.home`.",
            )
        )
    return (
        _merge_path_details([], config_details),
        _merge_path_details([], log_details),
    )


def _build_unit_detail_config_paths(detail: dict[str, Any]) -> list[dict[str, str]]:
    config_details: list[dict[str, str]] = []
    fragment_path = str(detail.get("FragmentPath") or "")
    if fragment_path:
        config_details.append(
            _build_path_detail(
                path=fragment_path,
                status="observed",
                source="systemd_fragment",
                source_command_id="systemd_unit_details",
            )
        )
    for path in _extract_any_paths(str(detail.get("DropInPaths") or "")):
        config_details.append(
            _build_path_detail(
                path=path,
                status="observed",
                source="systemd_dropin",
                source_command_id="systemd_unit_details",
            )
        )
    for path in _extract_any_paths(str(detail.get("EnvironmentFiles") or "")):
        config_details.append(
            _build_path_detail(
                path=path,
                status="observed",
                source="systemd_environment_file",
                source_command_id="systemd_unit_details",
            )
        )
    for path in _extract_any_paths(str(detail.get("ConfigurationDirectory") or "")):
        config_details.append(
            _build_path_detail(
                path=path,
                status="observed",
                source="systemd_configuration_directory",
                source_command_id="systemd_unit_details",
            )
        )
    for path in _extract_any_paths(str(detail.get("WorkingDirectory") or "")):
        config_details.append(
            _build_path_detail(
                path=path,
                status="candidate",
                source="systemd_working_directory",
                source_command_id="systemd_unit_details",
                note="Working directory can be a useful config-adjacent inspection root.",
            )
        )
    for path in _extract_any_paths(str(detail.get("StateDirectory") or "")):
        config_details.append(
            _build_path_detail(
                path=path,
                status="candidate",
                source="systemd_state_directory",
                source_command_id="systemd_unit_details",
            )
        )
    for key in ("ExecStart", "ExecStartPre", "ExecStartPost", "ExecReload"):
        exec_config_details, _ = _extract_command_path_details(str(detail.get(key) or ""))
        config_details = _merge_path_details(config_details, exec_config_details)
    return config_details


def _build_unit_detail_log_paths(detail: dict[str, Any]) -> list[dict[str, str]]:
    log_details: list[dict[str, str]] = []
    unit_id = str(detail.get("Id") or "").strip()
    if unit_id:
        log_details.append(
            _build_path_detail(
                path=f"journalctl -u {unit_id} --no-pager -n 80",
                status="candidate",
                source="systemd_journal_locator",
                source_command_id="systemd_unit_details",
                surface_kind="locator",
                note="Bounded journal entrypoint for this service unit.",
            )
        )
    for path in _extract_any_paths(str(detail.get("LogsDirectory") or "")):
        log_details.append(
            _build_path_detail(
                path=path,
                status="observed",
                source="systemd_logs_directory",
                source_command_id="systemd_unit_details",
            )
        )
    for path in _extract_any_paths(str(detail.get("StateDirectory") or "")):
        log_details.append(
            _build_path_detail(
                path=path,
                status="candidate",
                source="systemd_state_directory",
                source_command_id="systemd_unit_details",
            )
        )
    for path in _extract_any_paths(str(detail.get("WorkingDirectory") or "")):
        if path.endswith("/logs") or path.endswith("/log"):
            log_details.append(
                _build_path_detail(
                    path=path,
                    status="candidate",
                    source="systemd_working_directory",
                    source_command_id="systemd_unit_details",
                )
            )
    for key in ("ExecStart", "ExecStartPre", "ExecStartPost", "ExecReload"):
        _, exec_log_details = _extract_command_path_details(str(detail.get(key) or ""))
        log_details = _merge_path_details(log_details, exec_log_details)
    return log_details


def _enrich_component_path_surfaces(
    component_records: list[dict[str, Any]],
    *,
    edge_route_hints: list[dict[str, Any]],
) -> None:
    httpd_record = next((record for record in component_records if record.get("component_id") == "httpd"), None)
    if httpd_record is not None:
        httpd_record["observed"]["config_path_details"] = _merge_path_details(
            httpd_record["observed"].get("config_path_details", []),
            [
                _build_path_detail(
                    path=str(hint["config_path"]),
                    status="observed",
                    source="httpd_route_hint",
                    source_command_id="httpd_route_hints",
                    note="Observed in bounded Apache route-hint collection.",
                )
                for hint in edge_route_hints
                if hint.get("config_path")
            ],
        )


def _extract_execstart_command(detail: dict[str, Any]) -> str | None:
    for key in ("ExecStart", "ExecStartPre", "ExecStartPost", "ExecReload"):
        value = str(detail.get(key) or "").strip()
        if not value:
            continue
        argv_match = re.search(r"argv\[]=(.+?)(?: ;|$)", value)
        if argv_match:
            return argv_match.group(1).strip()
        path_match = re.search(r"path=(/[^ ;]+)", value)
        if path_match:
            return path_match.group(1).strip()
        if value.startswith("/"):
            return value
    return None


def _should_replace_main_command(existing: str, candidate: str) -> bool:
    existing_lower = existing.lower()
    candidate_lower = candidate.lower()
    if existing_lower.startswith("/bin/sh -c") or existing_lower.startswith("/bin/bash "):
        return True
    if "source ~/.bashrc" in existing_lower:
        return True
    if "bootstrap start" in existing_lower and "bootstrap start" not in candidate_lower:
        return False
    if "java" not in existing_lower and "java" in candidate_lower:
        return True
    if "bootstrap start" not in existing_lower and "bootstrap start" in candidate_lower:
        return True
    return False

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


def _connection_bindings_for_record(
    connections: list[dict[str, Any]],
    record: dict[str, Any],
    *,
    process_index: dict[int, dict[str, Any]],
    children_by_ppid: dict[int, list[int]],
) -> list[dict[str, Any]]:
    observed = record["observed"]
    process_id = observed.get("process_id")
    if not isinstance(process_id, int):
        return []
    related_pids = _descendant_pids(process_id, children_by_ppid)
    related_pids.add(process_id)
    bindings: list[dict[str, Any]] = []
    for connection in connections:
        connection_pid = connection.get("process_id")
        if connection_pid not in related_pids:
            continue
        ownership_basis = "exact_pid" if connection_pid == process_id else "descendant_pid"
        owner_process = process_index.get(connection_pid, {})
        bindings.append(
            {
                "local_ip": connection.get("local_ip"),
                "local_port": connection.get("local_port"),
                "remote_ip": connection.get("remote_ip"),
                "remote_port": connection.get("remote_port"),
                "owner_pid": connection_pid,
                "owner_name": str(owner_process.get("comm") or connection.get("process_name") or "unknown"),
                "ownership_basis": ownership_basis,
            }
        )
    return sorted(
        bindings,
        key=lambda item: (
            str(item.get("remote_ip") or ""),
            int(item.get("remote_port") or 0),
            int(item.get("local_port") or 0),
        ),
    )


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


def _parse_tcp_endpoint(endpoint: str) -> tuple[str | None, int | None]:
    candidate = endpoint.strip()
    if not candidate:
        return None, None
    if candidate.startswith("[") and "]:" in candidate:
        host, port_text = candidate[1:].split("]:", 1)
    elif ":" in candidate:
        host, port_text = candidate.rsplit(":", 1)
    else:
        return candidate, None
    port = int(port_text) if port_text.isdigit() else None
    return host, port


def _is_non_loopback_ip(value: str) -> bool:
    candidate = value.strip().strip("[]")
    if not candidate:
        return False
    return candidate not in {"127.0.0.1", "::1", "*", "localhost"}


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
    config_details = observed.get("config_path_details", [])
    log_details = observed.get("log_path_details", [])
    has_config_surface = bool(config_details or observed["config_path_candidates"])
    has_log_surface = bool(log_details or observed["log_path_candidates"])
    has_observed_config = any(detail.get("status") == "observed" for detail in config_details)
    has_observed_log = any(detail.get("status") == "observed" for detail in log_details)
    if not has_config_surface:
        unknowns.append("No config path candidate was visible from the bounded command-line, unit-metadata, or Apache-route evidence.")
    elif not has_observed_config:
        unknowns.append("Only candidate config surfaces are visible so far; no target-local config path is confirmed yet.")
    if not has_log_surface:
        unknowns.append("No log path candidate was visible from the bounded command-line or unit-metadata evidence.")
    elif not has_observed_log:
        unknowns.append("Only candidate log surfaces are visible so far; no target-local log path is confirmed yet.")
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
        "The first pass still does not deeply parse config files, unit fragments, or logs; it only records bounded path surfaces and route clues.",
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


def _parse_tcp_probe_result(result: dict[str, Any], *, port: int | None) -> dict[str, Any]:
    stdout = str(result.get("stdout", ""))
    reachable = TCP_PROBE_SUCCESS_MARKER in stdout
    return {
        "probe_port": port,
        "probe_attempted": port is not None,
        "reachable": reachable,
        "command_status": result.get("status"),
        "exit_code": result.get("exit_code"),
        "stderr_preview": result.get("stderr_preview", []),
    }


def _parse_provider_journal_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") not in {"completed", "nonzero_exit"}:
        return {
            "failure_signal_count": 0,
            "signal_categories": [],
            "signal_lines": [],
        }

    categories: list[str] = []
    signal_lines: list[dict[str, str]] = []
    for raw_line in str(result.get("stdout", "")).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for category, pattern in PROVIDER_JOURNAL_FAILURE_PATTERNS:
            if not pattern.search(line):
                continue
            if category not in categories:
                categories.append(category)
            signal_lines.append(
                {
                    "category": category,
                    "line_excerpt": line[:220],
                }
            )
            break

    return {
        "failure_signal_count": len(signal_lines),
        "signal_categories": categories,
        "signal_lines": signal_lines[:5],
    }


def _parse_directionality_journal_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") not in {"completed", "nonzero_exit"}:
        return {
            "signal_count": 0,
            "matched_terms": [],
            "peer_ips": [],
            "signal_lines": [],
        }

    matched_terms: list[str] = []
    peer_ips: list[str] = []
    signal_lines: list[dict[str, Any]] = []
    for raw_line in str(result.get("stdout", "")).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line_terms = [
            term_id
            for term_id, pattern in DIRECTIONALITY_SIGNAL_PATTERNS
            if pattern.search(line)
        ]
        line_ips = [
            ip
            for ip in IPV4_RE.findall(line)
            if _is_non_loopback_ip(ip)
        ]
        if not line_terms and not line_ips:
            continue
        for term_id in line_terms:
            if term_id not in matched_terms:
                matched_terms.append(term_id)
        for ip in line_ips:
            if ip not in peer_ips:
                peer_ips.append(ip)
        signal_lines.append(
            {
                "matched_terms": line_terms,
                "peer_ips": line_ips,
                "line_excerpt": line[:220],
            }
        )

    return {
        "signal_count": len(signal_lines),
        "matched_terms": matched_terms,
        "peer_ips": peer_ips[:6],
        "signal_lines": signal_lines[:5],
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


def _build_businessflow_session_origin_packets(
    command_results: list[dict[str, Any]],
    *,
    usersession_reuse_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reuse_packet = next(
        (packet for packet in usersession_reuse_packets if packet.get("packet_id") == "usersession_fa_session_reuse"),
        None,
    )
    if reuse_packet is None or reuse_packet.get("status") != "reuse_chain_visible":
        return []

    results_by_id = {entry["command_id"]: entry for entry in command_results}
    httpd_markers = _parse_marker_lines(
        results_by_id.get("businessflow_session_origin_httpd_markers", {}),
        expected_terms=(
            "/fa/server/connection/login",
            "storeFireflowCookie",
            "getAFASessionInfo",
            "bridge/refresh",
            "CommandsDispatcher",
            "/afa/php/ws.php",
            "BusinessFlow/shallow_health_check",
            "BusinessFlow/deep_health_check",
        ),
    )
    source_markers = _parse_marker_lines(
        results_by_id.get("businessflow_session_origin_source_markers", {}),
        expected_terms=(
            "AFF_COOKIE",
            "BFCookie",
            "getAFASessionInfo",
            "getFireflowCookie",
            "checkFireFlowAuth",
            "VerifyGetFASessionIdValid",
            "Could not find AlgosecSession",
            "storeFireflowCookie",
        ),
    )

    httpd_terms = set(httpd_markers.get("matched_terms", []))
    source_terms = set(source_markers.get("matched_terms", []))
    bootstrap_httpd_terms = (
        "/fa/server/connection/login",
        "storeFireflowCookie",
    )
    polling_httpd_terms = (
        "getAFASessionInfo",
        "CommandsDispatcher",
        "bridge/refresh",
        "/afa/php/ws.php",
        "BusinessFlow/shallow_health_check",
        "BusinessFlow/deep_health_check",
    )
    source_cookie_terms = (
        "AFF_COOKIE",
        "BFCookie",
        "getFireflowCookie",
        "storeFireflowCookie",
    )
    source_fallback_terms = (
        "getAFASessionInfo",
        "checkFireFlowAuth",
        "VerifyGetFASessionIdValid",
        "Could not find AlgosecSession",
    )
    bootstrap_visible = all(term in httpd_terms for term in bootstrap_httpd_terms)
    polling_visible = "getAFASessionInfo" in httpd_terms and "CommandsDispatcher" in httpd_terms and any(
        term in httpd_terms
        for term in ("bridge/refresh", "/afa/php/ws.php", "BusinessFlow/shallow_health_check", "BusinessFlow/deep_health_check")
    )
    source_cookie_visible = any(term in source_terms for term in source_cookie_terms)
    source_fallback_visible = any(term in source_terms for term in source_fallback_terms)
    httpd_bootstrap_terms_present = [term for term in bootstrap_httpd_terms if term in httpd_terms]
    httpd_polling_terms_present = [term for term in polling_httpd_terms if term in httpd_terms]
    source_cookie_terms_present = [term for term in source_cookie_terms if term in source_terms]
    source_fallback_terms_present = [term for term in source_fallback_terms if term in source_terms]

    if bootstrap_visible and not polling_visible:
        packet_status = "bootstrap_origin_clues_visible"
        distinction_status = "bootstrap_pair_visible_without_refresh_dominance"
        next_stop = "inspect_aff_cookie_handoff"
    elif polling_visible and not bootstrap_visible:
        packet_status = "shared_polling_origin_clues_visible"
        distinction_status = "polling_dominant_without_httpd_bootstrap_pair"
        next_stop = "distinguish_bootstrap_from_shared_polling"
    elif bootstrap_visible and polling_visible:
        packet_status = "shared_polling_origin_clues_visible"
        distinction_status = "mixed_origin_window"
        next_stop = "distinguish_bootstrap_from_shared_polling"
    elif source_cookie_visible or source_fallback_visible:
        packet_status = "source_side_origin_clues_visible"
        distinction_status = "source_only_origin_vocabulary"
        next_stop = "inspect_aff_cookie_handoff"
    else:
        packet_status = "origin_clues_thin"
        distinction_status = "thin"
        next_stop = "keep_session_origin_bounded"

    confidence = (
        "high"
        if (bootstrap_visible and source_cookie_visible)
        or (polling_visible and not bootstrap_visible and source_cookie_visible)
        else "medium"
    )
    origin_reading = (
        "original_cookie_handoff"
        if distinction_status == "bootstrap_pair_visible_without_refresh_dominance"
        else "later_shared_polling"
        if distinction_status == "polling_dominant_without_httpd_bootstrap_pair"
        else "source_side_clue_only"
        if packet_status == "source_side_origin_clues_visible"
        else "mixed_bootstrap_and_polling_window"
        if distinction_status == "mixed_origin_window"
        else "still_ambiguous"
    )

    confirmed_elements: list[str] = []
    remaining_questions: list[str] = []
    if bootstrap_visible:
        confirmed_elements.append(
            "Retained Apache-side markers show the stronger bootstrap pattern: FireFlow session traffic sits alongside AFA login and `storeFireflowCookie`, which is a better origin clue than later refresh-only upkeep."
        )
    if polling_visible:
        confirmed_elements.append(
            "Retained Apache-side markers also show the shared polling family: `getAFASessionInfo`, `CommandsDispatcher`, and nearby BusinessFlow or AFF health checks can recur after the session already exists."
        )
    if polling_visible and not bootstrap_visible:
        confirmed_elements.append(
            "The retained Apache-side window does not keep the stronger bootstrap pair (`/fa/server/connection/login` plus `storeFireflowCookie`), so this specific window is better read as later shared polling than as first cookie handoff."
        )
    if bootstrap_visible and polling_visible:
        remaining_questions.append(
            "The retained Apache-side window mixes both bootstrap and upkeep vocabulary, so the current packet still needs a bounded bootstrap-versus-polling separation step before claiming a cleaner first handoff."
        )
    if source_cookie_visible:
        confirmed_elements.append(
            "Local source-side hints still name the BusinessFlow cookie handoff directly through `AFF_COOKIE`, `BFCookie`, or `getFireflowCookie`."
        )
        if polling_visible and not bootstrap_visible:
            confirmed_elements.append(
                "That means the bootstrap vocabulary still exists in the product code even though the retained Apache-side evidence currently shows the later refresh and health family instead."
            )
    if source_fallback_visible:
        confirmed_elements.append(
            "Local source-side hints also preserve the fallback or validation side through `getAFASessionInfo`, `checkFireFlowAuth`, or `VerifyGetFASessionIdValid`."
        )
    if packet_status == "origin_clues_thin":
        remaining_questions.append(
            "The retained origin-side markers were too thin to classify this as original cookie handoff versus later shared polling."
        )
    remaining_questions.append(
        "The packet still does not prove the exact external browser action that triggered the localhost-side session-origin branch."
    )

    return [
        {
            "packet_id": "businessflow_session_origin_clue",
            "packet_kind": "retained_origin_side_hint",
            "display_name": "BusinessFlow Session Origin Packet",
            "status": packet_status,
            "confidence": confidence,
            "distinction_status": distinction_status,
            "origin_reading": origin_reading,
            "why_it_matters": "This packet stays just upstream of the reused FireFlow FA-session chain and distinguishes the original BusinessFlow cookie handoff from later shared session upkeep when the retained evidence supports that read.",
            "usersession_reuse_ref": reuse_packet["packet_id"],
            "httpd_origin_markers": httpd_markers,
            "source_origin_markers": source_markers,
            "distinction_basis": {
                "httpd_bootstrap_terms_present": httpd_bootstrap_terms_present,
                "httpd_bootstrap_terms_missing": [
                    term for term in bootstrap_httpd_terms if term not in httpd_terms
                ],
                "httpd_polling_terms_present": httpd_polling_terms_present,
                "source_cookie_terms_present": source_cookie_terms_present,
                "source_fallback_terms_present": source_fallback_terms_present,
            },
            "next_stop": next_stop,
            "stop_rule": "If upstream origin clues are thin, stop here instead of widening into full login or cookie-bootstrap reconstruction.",
            "confirmed_elements": confirmed_elements,
            "remaining_questions": remaining_questions,
        }
    ]


def _build_bootstrap_polling_packets(
    command_results: list[dict[str, Any]],
    *,
    businessflow_session_origin_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    origin_packet = next(
        (packet for packet in businessflow_session_origin_packets if packet.get("packet_id") == "businessflow_session_origin_clue"),
        None,
    )
    if origin_packet is None or origin_packet.get("status") == "origin_clues_thin":
        return []

    results_by_id = {entry["command_id"]: entry for entry in command_results}
    analysis = _parse_bootstrap_polling_analysis(
        results_by_id.get("businessflow_session_origin_httpd_markers", {}),
        results_by_id.get("businessflow_session_origin_source_markers", {}),
    )
    status = analysis["status"]

    confirmed_elements: list[str] = []
    remaining_questions: list[str] = []
    if status in {
        "polling_dominant",
        "polling_dominant_with_bootstrap_residue",
        "polling_dominant_with_bootstrap_anchor",
    }:
        confirmed_elements.append(
            "Retained runtime-side evidence is dominated by repeated `getAFASessionInfo`-family polling rather than a fresh login-side burst."
        )
        if analysis["repeated_polling_sessions"]:
            session_samples = ", ".join(
                f"{item['session_id']} x{item['occurrence_count']}"
                for item in analysis["repeated_polling_sessions"][:3]
            )
            confirmed_elements.append(
                f"The same FireFlow session ids recur in the retained polling window, for example {session_samples}."
            )
        if status == "polling_dominant_with_bootstrap_anchor":
            anchor_samples = ", ".join(
                (
                    f"{item['session_id']} store->{item['first_poll_after_bootstrap_seconds']}s"
                    f" then ~{item['representative_polling_gap_seconds']}s cadence"
                )
                if item.get("representative_polling_gap_seconds") is not None
                else f"{item['session_id']} store->{item['first_poll_after_bootstrap_seconds']}s"
                for item in analysis["bootstrap_anchor_sessions"][:2]
            )
            confirmed_elements.append(
                f"A bounded bootstrap anchor is still visible before the polling tail, for example {anchor_samples}."
            )
            remaining_questions.append(
                "The retained window now separates bootstrap anchor from later upkeep strongly enough to move upstream to the cookie-handoff seam, but it still does not reconstruct the original external browser request."
            )
        elif status == "polling_dominant_with_bootstrap_residue":
            confirmed_elements.append(
                "Bootstrap vocabulary such as `storeFireflowCookie`, `AFF_COOKIE`, or `BFCookie` is still present, but it now reads like residue around a polling-dominant window rather than the dominant live action."
            )
            remaining_questions.append(
                "This packet does not prove the original browser-side bootstrap request anymore; it only shows that the current retained window is dominated by later upkeep."
            )
        elif status == "polling_dominant":
            remaining_questions.append(
                "This packet does not prove the original browser-side bootstrap request anymore; it only shows that the current retained window is dominated by later upkeep."
            )
    elif status == "bootstrap_dominant":
        confirmed_elements.append(
            "The retained runtime-side evidence still centers on login and `storeFireflowCookie`, which is stronger than the later polling family in this bounded window."
        )
        remaining_questions.append(
            "The packet still does not reconstruct the full browser-side bootstrap sequence beyond the visible cookie-handoff markers."
        )
    elif status == "mixed_window_still_ambiguous":
        confirmed_elements.append(
            "Both bootstrap-style and polling-style runtime markers are visible in the same bounded window."
        )
        remaining_questions.append(
            "The retained evidence still mixes original handoff and later upkeep too closely to classify the window cleanly without over-claiming."
        )
    else:
        remaining_questions.append(
            "The retained runtime-side evidence stayed too thin to separate bootstrap from later shared polling."
        )

    return [
        {
            "packet_id": "bootstrap_polling_distinction",
            "packet_kind": "retained_origin_window_distinction",
            "display_name": "Bootstrap Versus Polling Packet",
            "status": status,
            "confidence": analysis["confidence"],
            "window_reading": analysis["window_reading"],
            "why_it_matters": "This packet closes the current upstream ambiguity by deciding whether the retained session-origin window is better read as original cookie bootstrap or later shared polling, without widening into full browser replay.",
            "origin_packet_ref": origin_packet["packet_id"],
            "distinction_basis": analysis["distinction_basis"],
            "repeated_polling_sessions": analysis["repeated_polling_sessions"],
            "polling_only_sessions": analysis["polling_only_sessions"],
            "bootstrap_anchor_sessions": analysis["bootstrap_anchor_sessions"],
            "bootstrap_runtime_samples": analysis["bootstrap_runtime_samples"],
            "polling_runtime_samples": analysis["polling_runtime_samples"],
            "bootstrap_residue_samples": analysis["bootstrap_residue_samples"],
            "next_stop": analysis["next_stop"],
            "stop_rule": "If bootstrap-versus-polling evidence stays mixed, stop here instead of widening into full login or cookie-bootstrap reconstruction.",
            "confirmed_elements": confirmed_elements,
            "remaining_questions": remaining_questions,
        }
    ]


def _build_aff_cookie_handoff_packets(
    command_results: list[dict[str, Any]],
    *,
    edge_route_hints: list[dict[str, Any]],
    usersession_reuse_packets: list[dict[str, Any]],
    bootstrap_polling_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bootstrap_packet = next(
        (packet for packet in bootstrap_polling_packets if packet.get("packet_id") == "bootstrap_polling_distinction"),
        None,
    )
    if bootstrap_packet is None or bootstrap_packet.get("status") not in {
        "bootstrap_dominant",
        "polling_dominant_with_bootstrap_anchor",
    }:
        return []

    reuse_packet = next(
        (packet for packet in usersession_reuse_packets if packet.get("packet_id") == "usersession_fa_session_reuse"),
        None,
    )
    if reuse_packet is None:
        return []

    results_by_id = {entry["command_id"]: entry for entry in command_results}
    source_lines = _result_lines(results_by_id.get("businessflow_session_origin_source_markers", {}))
    httpd_lines = _result_lines(results_by_id.get("businessflow_session_origin_httpd_markers", {}))

    route_hints = [
        hint
        for hint in edge_route_hints
        if hint.get("route_path") in {"/afa/external", "/afa/api/v1"}
    ]
    store_events = _parse_store_fireflow_cookie_events(source_lines)
    extend_events = _parse_aff_session_extend_events(httpd_lines)

    handoff_links: list[dict[str, Any]] = []
    for anchor in bootstrap_packet.get("bootstrap_anchor_sessions", []):
        session_id = anchor.get("session_id")
        matching_store_events = [
            event for event in store_events if event.get("fireflow_session_id") == session_id
        ]
        if not matching_store_events:
            continue
        matching_reuse_pair = next(
            (pair for pair in reuse_packet.get("reuse_pairs", []) if pair.get("ff_session_id") == session_id),
            None,
        )
        for store_event in matching_store_events[:2]:
            carried_tokens = store_event.get("carried_session_tokens", [])
            matched_reuse_token = None
            if matching_reuse_pair is not None:
                matched_reuse_token = next(
                    (
                        token
                        for token in carried_tokens
                        if token == matching_reuse_pair.get("fa_session_id")
                        or token.startswith(str(matching_reuse_pair.get("fa_session_id") or ""))
                    ),
                    None,
                )
            matching_extend_event = next(
                (
                    event
                    for event in extend_events
                    if any(
                        extend_token == token or extend_token.startswith(token) or token.startswith(extend_token)
                        for token in carried_tokens
                        for extend_token in event.get("carried_session_tokens", [])
                    )
                ),
                None,
            )
            route_hint = next(
                (hint for hint in route_hints if hint.get("route_path") == "/afa/external"),
                route_hints[0] if route_hints else None,
            )
            handoff_links.append(
                {
                    "fireflow_session_id": session_id,
                    "bootstrap_anchor_ref": session_id,
                    "store_bridge_path": store_event.get("bridge_path"),
                    "store_bridge_url": store_event.get("bridge_url"),
                    "store_called_at": store_event.get("called_at"),
                    "carried_session_tokens": carried_tokens,
                    "matched_reuse_fa_session_id": None if matching_reuse_pair is None else matching_reuse_pair.get("fa_session_id"),
                    "matched_store_bridge_token": matched_reuse_token,
                    "httpd_extend_path": None if matching_extend_event is None else matching_extend_event.get("path"),
                    "httpd_extend_called_at": None if matching_extend_event is None else matching_extend_event.get("called_at"),
                    "httpd_extend_session_tokens": [] if matching_extend_event is None else matching_extend_event.get("carried_session_tokens", []),
                    "edge_route_hint": route_hint,
                }
            )

    if not handoff_links:
        return []

    confident_links = [
        link
        for link in handoff_links
        if link.get("matched_store_bridge_token") and link.get("httpd_extend_session_tokens")
    ]
    packet_status = "cookie_handoff_visible" if confident_links else "cookie_handoff_partially_visible"
    next_stop = "inspect_java_runtime_clusters" if confident_links else "trace_edge_to_local_service_routes"
    confidence = "high" if confident_links else "medium"

    confirmed_elements: list[str] = []
    remaining_questions: list[str] = []
    if confident_links:
        best_link = confident_links[0]
        route_hint = best_link.get("edge_route_hint") or {}
        owner = route_hint.get("likely_owner_component") or "unknown"
        backend_port = route_hint.get("backend_port")
        confirmed_elements.append(
            "The retained bootstrap anchor now crosses a concrete AFF bridge surface instead of staying only as abstract cookie vocabulary."
        )
        confirmed_elements.append(
            f"FireFlow session `{best_link['fireflow_session_id']}` calls `{best_link['store_bridge_path']}` while carrying FA-session token `{best_link['matched_store_bridge_token']}`."
        )
        if best_link.get("httpd_extend_path"):
            confirmed_elements.append(
                f"The same carried token family later appears on Apache path `{best_link['httpd_extend_path']}`, which makes the bridge-to-extend handoff visible in one bounded packet."
            )
        if owner != "unknown" and backend_port is not None:
            confirmed_elements.append(
                f"The `/afa/external` bridge surface is already route-hinted to `{owner}` on local port `{backend_port}`, so the cookie handoff lands on a named local owner."
            )
    else:
        remaining_questions.append(
            "The retained cookie-handoff evidence showed a bootstrap bridge call but did not correlate the carried token strongly enough to a later visible extend-side path."
        )
    remaining_questions.append(
        "The packet still does not reconstruct the external browser request that first created the FireFlow session; it only follows the bounded carry-forward into the AFF bridge surface."
    )

    return [
        {
            "packet_id": "aff_cookie_handoff",
            "packet_kind": "retained_cookie_bridge_handoff",
            "display_name": "AFF Cookie Handoff Packet",
            "status": packet_status,
            "confidence": confidence,
            "why_it_matters": "This packet follows the bounded bootstrap anchor into the AFF bridge surface and shows whether the carried session token becomes visible on the AFA side without widening into full login reconstruction.",
            "bootstrap_polling_ref": bootstrap_packet["packet_id"],
            "usersession_reuse_ref": reuse_packet["packet_id"],
            "route_hints": route_hints[:4],
            "handoff_links": handoff_links[:4],
            "next_stop": next_stop,
            "stop_rule": "If the carried token cannot be tied to the visible bridge and extend surfaces, stop here instead of inventing a broader cookie-replay story.",
            "confirmed_elements": confirmed_elements,
            "remaining_questions": remaining_questions,
        }
    ]


def _build_java_runtime_cluster_packets(
    component_records: list[dict[str, Any]],
    *,
    edge_route_hints: list[dict[str, Any]],
    boundary_packets: list[dict[str, Any]],
    aff_cookie_handoff_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    aff_cookie_packet = next(
        (packet for packet in aff_cookie_handoff_packets if packet.get("packet_id") == "aff_cookie_handoff"),
        None,
    )
    if aff_cookie_packet is None or aff_cookie_packet.get("status") not in {
        "cookie_handoff_visible",
        "cookie_handoff_partially_visible",
    }:
        return []

    records_by_id = {record.get("component_id"): record for record in component_records}
    target_component_ids = ["ms-metro", "ms-bflow", "algosec-ms", "aff-boot"]
    route_hints_by_owner: dict[str, list[dict[str, Any]]] = {}
    for hint in edge_route_hints:
        owner = hint.get("likely_owner_component")
        if owner:
            route_hints_by_owner.setdefault(owner, []).append(hint)
    aff_boundary_packet = next(
        (packet for packet in boundary_packets if packet.get("boundary_id") == "aff_fireflow_1989_route_owner"),
        None,
    )

    cluster_families: list[dict[str, Any]] = []
    distinct_signature_count = 0
    for component_id in target_component_ids:
        record = records_by_id.get(component_id)
        if record is None:
            continue
        cluster = _build_java_runtime_cluster_family(
            record=record,
            owner_route_hints=route_hints_by_owner.get(component_id, []),
            aff_boundary_packet=aff_boundary_packet if component_id == "aff-boot" else None,
        )
        if cluster is None:
            continue
        cluster_families.append(cluster)
        if cluster.get("cluster_signature"):
            distinct_signature_count += 1

    if not cluster_families:
        return []

    shared_substrates: list[dict[str, Any]] = []
    activemq_record = records_by_id.get("activemq")
    if activemq_record is not None:
        activemq_observed = activemq_record.get("observed", {})
        shared_substrates.append(
            {
                "component_id": "activemq",
                "role": "messaging_adjacency",
                "listener_ports": activemq_observed.get("listening_ports", []),
                "notes": [
                    "ActiveMQ remains a separate messaging-visible Java service rather than evidence that the AFA, BusinessFlow, or AFF owners share one runtime cluster."
                ],
            }
        )

    distinct_tomcat_bases = {
        cluster.get("catalina_base")
        for cluster in cluster_families
        if cluster.get("cluster_type") == "tomcat_service_family" and cluster.get("catalina_base")
    }
    status = (
        "cluster_boundaries_visible"
        if len(cluster_families) >= 4 and len(distinct_tomcat_bases) >= 2 and distinct_signature_count >= 4
        else "cluster_boundaries_partially_visible"
    )
    confidence = "high" if status == "cluster_boundaries_visible" else "medium"
    next_stop = "review_asms_runtime_architecture" if status == "cluster_boundaries_visible" else "inspect_java_runtime_clusters"

    confirmed_elements: list[str] = []
    if {"ms-metro", "ms-bflow"} <= {cluster["component_id"] for cluster in cluster_families}:
        metro_cluster = next(cluster for cluster in cluster_families if cluster["component_id"] == "ms-metro")
        bflow_cluster = next(cluster for cluster in cluster_families if cluster["component_id"] == "ms-bflow")
        confirmed_elements.append(
            f"`ms-metro` and `ms-bflow` now separate cleanly as different Tomcat families because their visible `catalina.base` values differ (`{metro_cluster.get('catalina_base')}` versus `{bflow_cluster.get('catalina_base')}`) and their listener sets do not overlap."
        )
    algosec_ms_cluster = next(
        (cluster for cluster in cluster_families if cluster.get("component_id") == "algosec-ms"),
        None,
    )
    if algosec_ms_cluster is not None:
        confirmed_elements.append(
            f"`algosec-ms` stays separate from the Tomcat families as a smaller standalone jar-backed service on local port(s) `{', '.join(str(port) for port in algosec_ms_cluster.get('listener_ports', [])) or 'none'}`."
        )
    aff_cluster = next(
        (cluster for cluster in cluster_families if cluster.get("component_id") == "aff-boot"),
        None,
    )
    if aff_cluster is not None:
        confirmed_elements.append(
            f"`aff-boot` remains its own wrapper-owned Java family behind the confirmed AFF boundary on local port(s) `{', '.join(str(port) for port in aff_cluster.get('listener_ports', [])) or 'none'}`."
        )
    if shared_substrates:
        confirmed_elements.append(
            "ActiveMQ is still visible as messaging adjacency, which matters to the runtime shape, but it is not the same cluster as the AFA, BusinessFlow, or AFF owners in this bounded packet."
        )

    remaining_questions = [
        "This packet does not claim full request-path ownership or full dependency order between the separated Java families; it only makes the family boundaries more support-useful.",
    ]
    if status != "cluster_boundaries_visible":
        remaining_questions.append(
            "Some Java-heavy services still need stronger config-path or route-adjacency evidence before every cluster boundary can be treated as cleanly separated."
        )

    return [
        {
            "packet_id": "java_runtime_clusters",
            "packet_kind": "bounded_java_runtime_cluster_map",
            "display_name": "Java Runtime Cluster Packet",
            "status": status,
            "confidence": confidence,
            "why_it_matters": "This packet separates the visible Java-heavy owners into bounded runtime families so the next support-facing architecture review can build on observed boundaries instead of one undifferentiated JVM blur.",
            "aff_cookie_handoff_ref": aff_cookie_packet["packet_id"],
            "cluster_families": cluster_families,
            "shared_substrates": shared_substrates,
            "next_stop": next_stop,
            "stop_rule": "If the visible JVM families still collapse into one mixed boundary, stop here instead of widening into attach tooling, deep dependency crawling, or config-tree parsing.",
            "confirmed_elements": confirmed_elements,
            "remaining_questions": remaining_questions,
        }
    ]


def _build_java_runtime_cluster_family(
    *,
    record: dict[str, Any],
    owner_route_hints: list[dict[str, Any]],
    aff_boundary_packet: dict[str, Any] | None,
) -> dict[str, Any] | None:
    observed = record.get("observed", {})
    if not observed.get("jvm_visibility", {}).get("detected"):
        return None

    main_command = str(observed.get("main_command") or "")
    runtime_option_haystack = " ".join(
        part
        for part in [
            main_command,
            " ".join(str(note) for note in observed.get("jvm_visibility", {}).get("notes", [])),
        ]
        if part
    )
    catalina_base = _extract_command_option_value(runtime_option_haystack, "-Dcatalina.base=")
    catalina_home = _extract_command_option_value(runtime_option_haystack, "-Dcatalina.home=")
    tmp_dir = _extract_command_option_value(runtime_option_haystack, "-Djava.io.tmpdir=")
    heap_settings = [
        note
        for note in observed.get("jvm_visibility", {}).get("notes", [])
        if note.startswith("-Xmx") or note.startswith("-Xms")
    ]
    jar_paths = _extract_jar_paths(main_command)
    route_paths = _dedupe_preserve_order(
        [
            hint.get("route_path")
            for hint in owner_route_hints
            if hint.get("route_path")
        ]
    )[:4]
    boundary_routes = []
    if aff_boundary_packet is not None:
        boundary_routes = aff_boundary_packet.get("route_family", [])[:4]
    cluster_type = "generic_java_family"
    cluster_signature = None
    if catalina_base:
        cluster_type = "tomcat_service_family"
        cluster_signature = catalina_base
    elif jar_paths:
        cluster_type = "standalone_jar_service"
        cluster_signature = jar_paths[0]
    elif observed.get("service_unit"):
        cluster_signature = observed.get("service_unit")
    elif observed.get("process_name"):
        cluster_signature = observed.get("process_name")

    return {
        "component_id": record.get("component_id"),
        "cluster_type": cluster_type,
        "cluster_signature": cluster_signature,
        "service_unit": observed.get("service_unit"),
        "listener_ports": observed.get("listening_ports", []),
        "route_paths": route_paths,
        "boundary_routes": boundary_routes,
        "catalina_base": catalina_base,
        "catalina_home": catalina_home,
        "heap_settings": heap_settings[:3],
        "jar_paths": jar_paths[:3],
        "tmp_dir": tmp_dir,
        "config_path_candidates": observed.get("config_path_candidates", [])[:4],
    }


def _extract_command_option_value(command: str, option_prefix: str) -> str | None:
    for token in _command_tokens(command):
        if token.startswith(option_prefix):
            return token.removeprefix(option_prefix)
    return None


def _extract_jar_paths(command: str) -> list[str]:
    jar_re = re.compile(r"(/[^\s]+\.jar)")
    return _dedupe_preserve_order(jar_re.findall(command))


def _command_tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _extract_httpd_route_families(edge_route_hints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family_index: dict[str, dict[str, Any]] = {}
    for hint in edge_route_hints:
        config_path = str(hint.get("config_path") or "")
        match = HTTPD_MS_FAMILY_RE.match(Path(config_path).name)
        if match is None:
            continue
        family_id = match.group("family")
        existing = family_index.setdefault(
            family_id,
            {
                "family_id": family_id,
                "config_path": config_path,
                "backend_ports": [],
                "route_paths": [],
                "owner_components": [],
            },
        )
        backend_port = hint.get("backend_port")
        if backend_port is not None:
            existing["backend_ports"] = _dedupe_preserve_order(existing["backend_ports"] + [backend_port])
        route_path = hint.get("route_path")
        if route_path:
            existing["route_paths"] = _dedupe_preserve_order(existing["route_paths"] + [route_path])
        owner = hint.get("likely_owner_component")
        if owner:
            existing["owner_components"] = _dedupe_preserve_order(existing["owner_components"] + [owner])
    return list(family_index.values())


def _build_component_guidance_candidates(
    component_records: list[dict[str, Any]],
    *,
    java_runtime_cluster_packets: list[dict[str, Any]],
    edge_route_hints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records_by_id = {record.get("component_id"): record for record in component_records}
    route_family_ids = {family["family_id"] for family in _extract_httpd_route_families(edge_route_hints)}
    candidates: list[dict[str, Any]] = []

    for packet in java_runtime_cluster_packets:
        for cluster in packet.get("cluster_families", []):
            evidence = []
            if cluster.get("catalina_base"):
                evidence.append(f"visible catalina.base `{cluster['catalina_base']}`")
            if cluster.get("jar_paths"):
                evidence.append(f"visible jar `{cluster['jar_paths'][0]}`")
            if cluster.get("route_paths"):
                evidence.append("Apache route adjacency")
            candidates.append(
                {
                    "component_id": cluster.get("component_id"),
                    "guidance_family": cluster.get("cluster_type"),
                    "confidence": "high" if evidence else "medium",
                    "evidence_basis": evidence or ["bounded JVM lineage visibility"],
                }
            )

    if records_by_id.get("httpd") is not None:
        candidates.append(
            {
                "component_id": "httpd",
                "guidance_family": "apache_httpd_edge",
                "confidence": "high",
                "evidence_basis": [
                    "observed systemd fragment",
                    "observed Apache conf.d route families",
                ],
            }
        )

    activemq_record = records_by_id.get("activemq")
    if activemq_record is not None:
        activemq_paths = activemq_record.get("observed", {}).get("config_path_details", [])
        versioned_paths = [
            detail["path"]
            for detail in activemq_paths
            if "apache-activemq-" in str(detail.get("path") or "")
        ]
        candidates.append(
            {
                "component_id": "activemq",
                "guidance_family": "activemq_broker",
                "confidence": "high" if versioned_paths else "medium",
                "evidence_basis": (
                    [f"visible config root `{versioned_paths[0]}`"]
                    if versioned_paths
                    else ["observed messaging-side config surfaces"]
                ),
            }
        )

    keycloak_record = records_by_id.get("keycloak")
    if keycloak_record is not None and any(
        "keycloak" in str(detail.get("path") or "")
        for detail in keycloak_record.get("observed", {}).get("config_path_details", [])
    ):
        candidates.append(
            {
                "component_id": "keycloak",
                "guidance_family": "keycloak_identity_service",
                "confidence": "medium",
                "evidence_basis": [
                    "observed keycloak service fragment",
                    "observed keycloak environment-file surface",
                ],
            }
        )

    if "ms-devicedriver-aws" in route_family_ids or "ms-devicedriver-azure" in route_family_ids:
        candidates.append(
            {
                "component_id": "algosec-ms",
                "guidance_family": "suite_service_gateway",
                "confidence": "medium",
                "evidence_basis": [
                    "observed `algosec-ms` local owner role",
                    "provider-specific Apache family surfaces under algosec-ms",
                ],
            }
        )

    deduped: list[dict[str, Any]] = []
    seen_component_ids: set[str] = set()
    for candidate in candidates:
        component_id = str(candidate.get("component_id") or "")
        if not component_id or component_id in seen_component_ids:
            continue
        seen_component_ids.add(component_id)
        deduped.append(candidate)
    return deduped


def _extract_docpack_vendor_hints(docpack_hints: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not docpack_hints:
        return []
    term_hints = docpack_hints.get("term_hints", [])
    matches: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for normalized, label in KNOWN_EXTERNAL_VENDOR_TERMS:
        hit = next(
            (
                item
                for item in term_hints
                if normalized in str(item.get("normalized_term") or "")
            ),
            None,
        )
        if hit is None or label in seen_labels:
            continue
        seen_labels.add(label)
        matches.append(
            {
                "vendor_label": label,
                "matched_term": hit.get("term") or hit.get("normalized_term"),
                "product_areas": hit.get("product_areas", []),
                "source_titles": hit.get("source_titles", [])[:2],
            }
        )
    return matches


def _build_knowledge_layer_packets(
    component_records: list[dict[str, Any]],
    *,
    edge_route_hints: list[dict[str, Any]],
    java_runtime_cluster_packets: list[dict[str, Any]],
    provider_integration_packets: list[dict[str, Any]],
    docpack_hints: dict[str, Any] | None,
    target_label: str,
) -> list[dict[str, Any]]:
    records_by_id = {
        str(record.get("component_id")): record
        for record in component_records
        if record.get("component_id")
    }
    java_runtime_packet = next(
        (packet for packet in java_runtime_cluster_packets if packet.get("packet_id") == "java_runtime_clusters"),
        None,
    )
    cluster_by_id = {
        str(cluster.get("component_id")): cluster
        for cluster in (java_runtime_packet or {}).get("cluster_families", [])
        if cluster.get("component_id")
    }
    component_guidance = _build_component_guidance_activations(records_by_id, cluster_by_id)
    external_activation = _build_external_integration_activation(
        component_records=component_records,
        edge_route_hints=edge_route_hints,
        docpack_hints=docpack_hints,
    )
    provider_packet = next(
        (
            packet
            for packet in provider_integration_packets
            if packet.get("packet_id") == "provider_specific_integration_evidence_current_node"
        ),
        None,
    )
    node_scope = {
        "status": "single_node_only",
        "observed_node_count": 1,
        "current_node": {
            "target_label": target_label,
        },
        "cross_node_envelope_status": "not_activated",
        "why_not_activated": "No second imported node-local proof bundle exists yet, so the successor should preserve this as one honest node map instead of inventing a suite graph.",
    }

    confirmed_elements = [
        f"The current proof is still a single-node readout for `{target_label}`, so cross-node claims remain intentionally inactive.",
    ]
    if component_guidance:
        confirmed_elements.append(
            "Observed runtime lineage is now strong enough to layer bounded component guidance for "
            + ", ".join(f"`{activation['component_id']}`" for activation in component_guidance[:6])
            + " without treating that guidance as node-local fact."
        )
    if external_activation.get("vendor_activation_status") == "dormant":
        confirmed_elements.append(
            "Vendor-side terms "
            + ", ".join(f"`{vendor}`" for vendor in external_activation.get("dormant_vendor_inventory", [])[:5])
            + " are present in the doc-pack hint inventory, but they remain dormant until provider-specific local evidence appears on the node."
        )
    elif external_activation.get("activated_vendor_terms"):
        confirmed_elements.append(
            "Provider-specific local evidence is visible for "
            + ", ".join(f"`{vendor}`" for vendor in external_activation.get("activated_vendor_terms", [])[:4])
            + "."
        )
    if provider_packet is not None and provider_packet.get("observed_providers"):
        confirmed_elements.append(
            "Those activated provider hints are now grounded in one bounded current-node readout covering "
            + ", ".join(
                f"`{provider.get('vendor_label', 'unknown')}`"
                for provider in provider_packet.get("observed_providers", [])[:4]
            )
            + "."
        )

    remaining_questions = [
        "This packet does not claim multi-node topology or live external provider integrations; it only says which outside knowledge layers are currently activated by this node.",
        "A thin cross-node envelope should activate only after a second node-local proof bundle exists.",
    ]
    if provider_packet is not None and provider_packet.get("status") == "local_provider_health_partially_classified":
        next_stop = "strengthen_cross_node_directionality_proof"
    elif provider_packet is not None and provider_packet.get("status") == "local_surfaces_visible_not_health_validated":
        next_stop = "capture_second_node_node_local_proof"
    elif external_activation.get("vendor_activation_status") == "provider_specific_local_evidence_visible":
        next_stop = "capture_provider_specific_integration_evidence"
    else:
        next_stop = "define_second_node_request_shape"

    return [
        {
            "packet_id": "distributed_and_external_knowledge_layers",
            "packet_kind": "bounded_knowledge_layer_activation",
            "display_name": "Distributed And External Knowledge Layer Packet",
            "status": "single_node_layering_ready",
            "confidence": "medium",
            "why_it_matters": "This packet marks which outside knowledge layers the current node can honestly activate now, so the successor can stay evidence-first while preparing for later cross-node and provider-side expansion.",
            "node_scope": node_scope,
            "component_guidance_activations": component_guidance,
            "external_integration_activation": external_activation,
            "next_stop": next_stop,
            "stop_rule": "If no second node bundle or provider-specific local evidence exists, stop at activation boundaries instead of inventing a distributed suite map or vendor behavior story.",
            "confirmed_elements": confirmed_elements,
            "remaining_questions": remaining_questions,
        }
    ]


def _extract_httpd_route_families(edge_route_hints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family_index: dict[str, dict[str, Any]] = {}
    for hint in edge_route_hints:
        config_path = str(hint.get("config_path") or "")
        match = HTTPD_MS_FAMILY_RE.match(Path(config_path).name)
        if match is None:
            continue
        family_id = match.group("family")
        existing = family_index.setdefault(
            family_id,
            {
                "family_id": family_id,
                "config_path": config_path,
                "backend_ports": [],
                "route_paths": [],
                "owner_components": [],
            },
        )
        backend_port = hint.get("backend_port")
        if backend_port is not None:
            existing["backend_ports"] = _dedupe_preserve_order(existing["backend_ports"] + [backend_port])
        route_path = hint.get("route_path")
        if route_path:
            existing["route_paths"] = _dedupe_preserve_order(existing["route_paths"] + [route_path])
        owner = hint.get("likely_owner_component")
        if owner:
            existing["owner_components"] = _dedupe_preserve_order(existing["owner_components"] + [owner])
    return list(family_index.values())


def _build_component_guidance_candidates(
    component_records: list[dict[str, Any]],
    *,
    java_runtime_cluster_packets: list[dict[str, Any]],
    edge_route_hints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records_by_id = {record.get("component_id"): record for record in component_records}
    route_family_ids = {family["family_id"] for family in _extract_httpd_route_families(edge_route_hints)}
    candidates: list[dict[str, Any]] = []

    for packet in java_runtime_cluster_packets:
        for cluster in packet.get("cluster_families", []):
            evidence = []
            if cluster.get("catalina_base"):
                evidence.append(f"visible catalina.base `{cluster['catalina_base']}`")
            if cluster.get("jar_paths"):
                evidence.append(f"visible jar `{cluster['jar_paths'][0]}`")
            if cluster.get("route_paths"):
                evidence.append("Apache route adjacency")
            candidates.append(
                {
                    "component_id": cluster.get("component_id"),
                    "guidance_family": cluster.get("cluster_type"),
                    "confidence": "high" if evidence else "medium",
                    "evidence_basis": evidence or ["bounded JVM lineage visibility"],
                }
            )

    if records_by_id.get("httpd") is not None:
        candidates.append(
            {
                "component_id": "httpd",
                "guidance_family": "apache_httpd_edge",
                "confidence": "high",
                "evidence_basis": [
                    "observed systemd fragment",
                    "observed Apache conf.d route families",
                ],
            }
        )

    activemq_record = records_by_id.get("activemq")
    if activemq_record is not None:
        activemq_paths = activemq_record.get("observed", {}).get("config_path_details", [])
        versioned_paths = [
            detail["path"]
            for detail in activemq_paths
            if "apache-activemq-" in str(detail.get("path") or "")
        ]
        candidates.append(
            {
                "component_id": "activemq",
                "guidance_family": "activemq_broker",
                "confidence": "high" if versioned_paths else "medium",
                "evidence_basis": (
                    [f"visible config root `{versioned_paths[0]}`"]
                    if versioned_paths
                    else ["observed messaging-side config surfaces"]
                ),
            }
        )

    keycloak_record = records_by_id.get("keycloak")
    if keycloak_record is not None and any(
        "keycloak" in str(detail.get("path") or "")
        for detail in keycloak_record.get("observed", {}).get("config_path_details", [])
    ):
        candidates.append(
            {
                "component_id": "keycloak",
                "guidance_family": "keycloak_identity_service",
                "confidence": "medium",
                "evidence_basis": [
                    "observed keycloak service fragment",
                    "observed keycloak environment-file surface",
                ],
            }
        )

    if "ms-devicedriver-aws" in route_family_ids or "ms-devicedriver-azure" in route_family_ids:
        candidates.append(
            {
                "component_id": "algosec-ms",
                "guidance_family": "suite_service_gateway",
                "confidence": "medium",
                "evidence_basis": [
                    "observed `algosec-ms` local owner role",
                    "provider-specific Apache family surfaces under algosec-ms",
                ],
            }
        )

    deduped: list[dict[str, Any]] = []
    seen_component_ids: set[str] = set()
    for candidate in candidates:
        component_id = str(candidate.get("component_id") or "")
        if not component_id or component_id in seen_component_ids:
            continue
        seen_component_ids.add(component_id)
        deduped.append(candidate)
    return deduped


def _extract_docpack_vendor_hints(docpack_hints: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not docpack_hints:
        return []
    term_hints = docpack_hints.get("term_hints", [])
    matches: list[dict[str, Any]] = []
    seen_labels: set[str] = set()
    for normalized, label in KNOWN_EXTERNAL_VENDOR_TERMS:
        hit = next(
            (
                item
                for item in term_hints
                if normalized in str(item.get("normalized_term") or "")
            ),
            None,
        )
        if hit is None or label in seen_labels:
            continue
        seen_labels.add(label)
        matches.append(
            {
                "vendor_label": label,
                "matched_term": hit.get("term") or hit.get("normalized_term"),
                "product_areas": hit.get("product_areas", []),
                "source_titles": hit.get("source_titles", [])[:2],
            }
        )
    return matches


def _build_component_guidance_activations(
    records_by_id: dict[str, dict[str, Any]],
    cluster_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    activations: list[dict[str, Any]] = []
    target_ids = [
        "httpd",
        "ms-metro",
        "ms-bflow",
        "activemq",
        "keycloak",
        "kibana",
        "elasticsearch",
        "logstash",
    ]
    for component_id in target_ids:
        record = records_by_id.get(component_id)
        if record is None:
            continue
        activation = _build_component_guidance_activation(
            component_id=component_id,
            record=record,
            cluster=cluster_by_id.get(component_id),
        )
        if activation is not None:
            activations.append(activation)
    return activations


def _build_component_guidance_activation(
    *,
    component_id: str,
    record: dict[str, Any],
    cluster: dict[str, Any] | None,
) -> dict[str, Any] | None:
    observed = record.get("observed", {})
    main_command = str(observed.get("main_command") or "")
    config_paths = [
        detail.get("path")
        for detail in observed.get("config_path_details", [])
        if detail.get("path")
    ]
    log_paths = [
        detail.get("path")
        for detail in observed.get("log_path_details", [])
        if detail.get("path")
    ]
    family = None
    observed_version = None
    lineage_evidence: list[str] = []
    if component_id == "httpd":
        family = "apache_httpd"
        lineage_evidence = [
            path
            for path in config_paths
            if "/etc/httpd/" in path or path.endswith("httpd.service")
        ][:4]
    elif component_id in {"ms-metro", "ms-bflow"} and cluster is not None:
        family = "apache_tomcat_family"
        lineage_evidence = [
            item
            for item in [
                cluster.get("catalina_base"),
                cluster.get("catalina_home"),
                *cluster.get("route_paths", []),
            ]
            if item
        ][:4]
    elif component_id == "activemq":
        family = "apache_activemq"
        observed_version = _extract_version_from_text(main_command, r"apache-activemq-([0-9][A-Za-z0-9.\-]+)")
        lineage_evidence = [
            item
            for item in [
                observed_version and f"apache-activemq-{observed_version}",
                *[path for path in config_paths if "activemq" in path.lower()],
            ]
            if item
        ][:4]
    elif component_id == "keycloak":
        family = "keycloak"
        lineage_evidence = [
            item
            for item in [*config_paths, main_command]
            if "keycloak" in str(item).lower()
        ][:4]
    elif component_id == "kibana":
        family = "kibana"
        lineage_evidence = [
            item
            for item in [main_command, *config_paths]
            if "kibana" in str(item).lower()
        ][:4]
    elif component_id == "elasticsearch":
        family = "elasticsearch"
        lineage_evidence = [
            item
            for item in [main_command, *config_paths]
            if "elasticsearch" in str(item).lower()
        ][:4]
    elif component_id == "logstash":
        family = "logstash"
        lineage_evidence = [
            item
            for item in [main_command, *config_paths]
            if "logstash" in str(item).lower()
        ][:4]

    if family is None or not lineage_evidence:
        return None

    guidance_status = (
        "version_matched_guidance_allowed"
        if observed_version
        else "runtime_lineage_visible"
    )
    allowed_guidance = ["component_vocabulary", "config_surface_expectations"]
    if log_paths:
        allowed_guidance.append("log_entrypoint_expectations")
    if observed_version:
        allowed_guidance.append("version_matched_component_guidance")
    caution = (
        None
        if observed_version
        else "Version is not pinned from current node evidence, so layered guidance should stay generic and should not import defaults as local truth."
    )
    return {
        "component_id": component_id,
        "component_family": family,
        "guidance_status": guidance_status,
        "observed_version": observed_version,
        "lineage_evidence": lineage_evidence,
        "allowed_guidance": allowed_guidance,
        "caution": caution,
    }


def _build_external_integration_activation(
    *,
    component_records: list[dict[str, Any]],
    edge_route_hints: list[dict[str, Any]],
    docpack_hints: dict[str, Any] | None,
) -> dict[str, Any]:
    route_families = _extract_httpd_route_families(edge_route_hints)
    observed_local_surfaces = _build_observed_external_surfaces(edge_route_hints, route_families=route_families)
    activated_vendor_terms = _find_activated_vendor_terms(
        route_families=route_families,
    )
    dormant_vendor_inventory = [
        vendor
        for vendor in _extract_docpack_vendor_inventory(docpack_hints)
        if vendor not in activated_vendor_terms
    ]
    if activated_vendor_terms:
        vendor_activation_status = "provider_specific_local_evidence_visible"
    elif dormant_vendor_inventory:
        vendor_activation_status = "dormant"
    else:
        vendor_activation_status = "no_vendor_inventory_visible"
    return {
        "vendor_activation_status": vendor_activation_status,
        "observed_local_external_surfaces": observed_local_surfaces,
        "activated_vendor_terms": activated_vendor_terms,
        "dormant_vendor_inventory": dormant_vendor_inventory,
        "activation_triggers": [
            "provider-specific config families under Apache, AFA, or service-local config roots",
            "provider-specific runtime log or journal markers",
            "observed integration-side API paths or route families",
            "a second imported node-local proof bundle",
        ],
    }


def _build_observed_external_surfaces(
    edge_route_hints: list[dict[str, Any]],
    *,
    route_families: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    generic_surfaces: list[dict[str, Any]] = []
    provider_surfaces: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for hint in edge_route_hints:
        route_path = str(hint.get("route_path") or "")
        if not route_path:
            continue
        surface_family = next(
            (
                family
                for prefix, family in EXTERNAL_SURFACE_ROUTE_PREFIXES.items()
                if route_path.startswith(prefix)
            ),
            None,
        )
        if surface_family is None:
            continue
        key = (route_path, str(hint.get("likely_owner_component") or ""))
        if key in seen:
            continue
        generic_surfaces.append(
            {
                "route_path": route_path,
                "surface_family": surface_family,
                "likely_owner_component": hint.get("likely_owner_component"),
                "backend_port": hint.get("backend_port"),
                "config_path": hint.get("config_path"),
                "confidence": hint.get("confidence"),
            }
        )
        seen.add(key)
    for family in route_families:
        family_id = str(family.get("family_id") or "")
        if not family_id:
            continue
        if not any(token in family_id for token in ("aws", "azure", "cloud", "aad")):
            continue
        key = (family_id, ",".join(family.get("owner_components", [])))
        if key in seen:
            continue
        provider_surfaces.append(
            {
                "route_path": (family.get("route_paths") or [None])[0],
                "surface_family": "provider_config_family",
                "family_id": family_id,
                "likely_owner_component": (family.get("owner_components") or [None])[0],
                "backend_port": (family.get("backend_ports") or [None])[0],
                "config_path": family.get("config_path"),
                "confidence": "medium",
            }
        )
        seen.add(key)
    return (provider_surfaces + generic_surfaces)[:10]


def _build_provider_integration_packets(
    component_records: list[dict[str, Any]],
    *,
    edge_route_hints: list[dict[str, Any]],
    target_label: str,
    command_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    route_families = _extract_httpd_route_families(edge_route_hints)
    route_family_by_id = {
        str(family.get("family_id")): family
        for family in route_families
        if family.get("family_id")
    }
    records_by_id = {
        str(record.get("component_id")): record
        for record in component_records
        if record.get("component_id")
    }
    results_by_id = {
        str(result.get("command_id")): result
        for result in command_results
        if result.get("command_id")
    }

    observed_providers = [
        entry
        for family_id, vendor_label in PROVIDER_DRIVER_VENDOR_LABELS.items()
        if (entry := _build_provider_integration_entry(
            vendor_label=vendor_label,
            family_id=family_id,
            route_family=route_family_by_id.get(family_id),
            record=records_by_id.get(family_id),
            journal_result=results_by_id.get(f"provider_journal_{family_id}"),
            probe_result=results_by_id.get(f"provider_local_port_probe_{family_id}"),
            directionality_journal_result=results_by_id.get(f"directionality_journal_{family_id}"),
        )) is not None
    ]
    adjacent_surfaces = _build_provider_adjacent_surfaces(route_families)
    coordination_surfaces = _build_provider_coordination_surfaces(
        records_by_id=records_by_id,
        results_by_id=results_by_id,
    )

    if not observed_providers and not adjacent_surfaces and not coordination_surfaces:
        return []

    provider_labels = [entry["vendor_label"] for entry in observed_providers]
    health_states = [str(entry.get("health_state") or "configured") for entry in observed_providers]
    if any(state in {"reachable", "degraded"} for state in health_states):
        status = "local_provider_health_partially_classified"
    elif observed_providers:
        status = "local_surfaces_visible_not_health_validated"
    else:
        status = "provider_activation_still_thin"
    confidence = (
        "high"
        if any(entry.get("confidence") == "high" for entry in observed_providers)
        else "medium"
    )
    confirmed_elements = []
    if observed_providers:
        confirmed_elements.append(
            "The current node exposes bounded provider-driver surfaces for "
            + ", ".join(f"`{label}`" for label in provider_labels)
            + " through matching Apache family names, local service units, and listener ownership."
        )
    reachable_labels = [entry["vendor_label"] for entry in observed_providers if entry.get("health_state") == "reachable"]
    degraded_labels = [entry["vendor_label"] for entry in observed_providers if entry.get("health_state") == "degraded"]
    if reachable_labels:
        confirmed_elements.append(
            "Local loopback reachability is now visible for "
            + ", ".join(f"`{label}`" for label in reachable_labels)
            + " on the currently observed provider-driver listener ports."
        )
    if degraded_labels:
        confirmed_elements.append(
            "Recent local failure signals are now visible for "
            + ", ".join(f"`{label}`" for label in degraded_labels)
            + ", so those provider-driver surfaces should be treated as degraded rather than merely present."
        )
    if adjacent_surfaces:
        confirmed_elements.append(
            "Adjacent provider-facing families such as "
            + ", ".join(
                f"`{surface.get('family_id', 'unknown')}`"
                for surface in adjacent_surfaces[:3]
            )
            + " are also visible, but they are kept separate from the core provider-driver packet."
        )
    coordination_with_peers = [
        surface
        for surface in coordination_surfaces
        if surface.get("peer_connection_clues") or surface.get("journal_directionality_clues", {}).get("signal_count", 0) > 0
    ]
    if coordination_with_peers:
        confirmed_elements.append(
            "Additional local coordination clues are visible for "
            + ", ".join(
                f"`{surface.get('component_id', 'unknown')}`"
                for surface in coordination_with_peers[:4]
            )
            + ", which gives the next cross-node directionality pass more than placement-only evidence to compare."
        )

    return [
        {
            "packet_id": "provider_specific_integration_evidence_current_node",
            "packet_kind": "bounded_provider_integration_evidence",
            "display_name": "Provider-Specific Integration Evidence Current Node",
            "status": status,
            "confidence": confidence,
            "target_label": target_label,
            "node_scope": "single_node_only",
            "provider_status": status,
            "observed_providers": observed_providers,
            "adjacent_surfaces": adjacent_surfaces,
            "coordination_surfaces": coordination_surfaces,
            "not_proven": [
                "No external API success or provider credential correctness is proven in this packet.",
                "No provider-side sync state, inventory freshness, or cloud-side health is claimed from current node evidence.",
                "No cross-node role or suite-topology claim is made from this current-node packet.",
            ],
            "why_it_matters": "This packet keeps AWS and Azure provider evidence fail-closed while sharpening local classification from merely configured toward bounded reachable or degraded states where the current node evidence actually supports that.",
            "next_stop": "strengthen_cross_node_directionality_proof" if status == "local_provider_health_partially_classified" else "capture_second_node_node_local_proof",
            "confirmed_elements": confirmed_elements,
        }
    ]


def _build_provider_integration_entry(
    *,
    vendor_label: str,
    family_id: str,
    route_family: dict[str, Any] | None,
    record: dict[str, Any] | None,
    journal_result: dict[str, Any] | None,
    probe_result: dict[str, Any] | None,
    directionality_journal_result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if route_family is None and record is None:
        return None
    observed = (record or {}).get("observed", {})
    listener_ports = observed.get("listening_ports", []) if observed else []
    listener_bindings = observed.get("listener_bindings", []) if observed else []
    journal_entrypoint = next(
        (
            detail.get("path")
            for detail in observed.get("log_path_details", [])
            if detail.get("surface_kind") == "locator" and detail.get("path")
        ),
        None,
    )
    service_unit = observed.get("service_unit")
    apache_backend_port = (route_family or {}).get("backend_ports", [None])[0]
    matched_port = (
        apache_backend_port is not None
        and apache_backend_port in listener_ports
    )
    confidence = "high" if route_family is not None and record is not None and matched_port else "medium"
    activation_basis = []
    if route_family is not None:
        activation_basis.append(
            f"Observed Apache family `{family_id}` in `{route_family.get('config_path', 'unknown config')}`"
            + (
                f" routing to local port `{apache_backend_port}`."
                if apache_backend_port is not None
                else "."
            )
        )
    if service_unit:
        activation_basis.append(f"Observed active local service unit `{service_unit}`.")
    if observed.get("main_command"):
        activation_basis.append(f"Observed local runtime command `{observed['main_command']}`.")
    if journal_entrypoint:
        activation_basis.append(f"Observed bounded journal entrypoint `{journal_entrypoint}`.")
    owner_basis = ", ".join(
        sorted({binding.get("ownership_basis") for binding in listener_bindings if binding.get("ownership_basis")})
    ) or None
    probe_port = apache_backend_port if apache_backend_port is not None else (listener_ports[0] if listener_ports else None)
    tcp_probe = _parse_tcp_probe_result(probe_result or {}, port=probe_port)
    journal_signals = _parse_provider_journal_result(journal_result or {})
    directionality_journal_clues = _parse_directionality_journal_result(directionality_journal_result or {})
    peer_connection_clues = _build_peer_connection_clues(observed.get("established_connection_bindings", []))
    health_state = "configured"
    health_basis: list[str] = []
    if observed.get("active_state") == "failed":
        health_state = "degraded"
        health_basis.append(f"Service unit `{service_unit}` is currently in active state `failed`.")
    if tcp_probe.get("probe_attempted"):
        if tcp_probe.get("reachable"):
            health_basis.append(f"Local loopback TCP connect succeeded on port `{probe_port}`.")
            if health_state != "degraded":
                health_state = "reachable"
        else:
            health_state = "degraded"
            health_basis.append(f"Local loopback TCP connect did not succeed on port `{probe_port}`.")
    if journal_signals.get("failure_signal_count", 0) > 0:
        health_state = "degraded"
        categories = ", ".join(journal_signals.get("signal_categories", [])[:3]) or "runtime failure"
        health_basis.append(
            f"Recent bounded journal markers show `{categories}` signals for `{service_unit or family_id}`."
        )
    return {
        "vendor_label": vendor_label,
        "provider_family_id": family_id,
        "confidence": confidence,
        "health_state": health_state,
        "apache_config_family": {
            "config_path": None if route_family is None else route_family.get("config_path"),
            "backend_port": apache_backend_port,
            "route_paths": [] if route_family is None else route_family.get("route_paths", []),
            "owner_components": [] if route_family is None else route_family.get("owner_components", []),
        },
        "local_runtime_service": {
            "component_id": None if record is None else record.get("component_id"),
            "service_unit": service_unit,
            "main_command": observed.get("main_command") if observed else None,
            "listener_ports": listener_ports,
            "listener_ownership_basis": owner_basis,
            "journal_entrypoint": journal_entrypoint,
            "config_surfaces": [
                detail.get("path")
                for detail in observed.get("config_path_details", [])
                if detail.get("path")
            ][:3],
        },
        "local_health_probe": tcp_probe,
        "recent_journal_signals": journal_signals,
        "peer_connection_clues": peer_connection_clues,
        "directionality_journal_clues": directionality_journal_clues,
        "health_basis": health_basis,
        "activation_basis": activation_basis,
    }


def _build_provider_coordination_surfaces(
    *,
    records_by_id: dict[str, dict[str, Any]],
    results_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    for component_id in DIRECTIONALITY_COORDINATION_FAMILIES:
        record = records_by_id.get(component_id)
        if record is None:
            continue
        observed = record.get("observed", {})
        surfaces.append(
            {
                "component_id": component_id,
                "service_unit": observed.get("service_unit"),
                "listener_ports": observed.get("listening_ports", [])[:6],
                "peer_connection_clues": _build_peer_connection_clues(observed.get("established_connection_bindings", [])),
                "journal_directionality_clues": _parse_directionality_journal_result(
                    results_by_id.get(f"directionality_journal_{component_id}", {})
                ),
            }
        )
    return surfaces[:6]


def _build_peer_connection_clues(bindings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clues: list[dict[str, Any]] = []
    seen: set[tuple[str, int | None, int | None, str]] = set()
    for binding in bindings:
        remote_ip = str(binding.get("remote_ip") or "")
        if not _is_non_loopback_ip(remote_ip):
            continue
        key = (
            remote_ip,
            binding.get("remote_port"),
            binding.get("local_port"),
            str(binding.get("ownership_basis") or ""),
        )
        if key in seen:
            continue
        clues.append(
            {
                "remote_ip": remote_ip,
                "remote_port": binding.get("remote_port"),
                "local_port": binding.get("local_port"),
                "owner_name": binding.get("owner_name"),
                "ownership_basis": binding.get("ownership_basis"),
            }
        )
        seen.add(key)
    return clues[:6]


def _build_provider_adjacent_surfaces(route_families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    adjacent: list[dict[str, Any]] = []
    for family in route_families:
        family_id = str(family.get("family_id") or "")
        if family_id not in PROVIDER_ADJACENT_FAMILY_LABELS:
            continue
        adjacent.append(
            {
                "vendor_label": PROVIDER_ADJACENT_FAMILY_LABELS[family_id],
                "family_id": family_id,
                "config_path": family.get("config_path"),
                "backend_port": (family.get("backend_ports") or [None])[0],
                "owner_components": family.get("owner_components", []),
                "route_paths": family.get("route_paths", []),
            }
        )
    return adjacent[:4]


def _extract_docpack_vendor_inventory(docpack_hints: dict[str, Any] | None) -> list[str]:
    if docpack_hints is None:
        return []
    discovered: list[str] = []
    for hint in docpack_hints.get("term_hints", []):
        term = _normalize_hint_text(str(hint.get("normalized_term") or ""))
        if not term:
            continue
        for alias, display_name in KNOWN_EXTERNAL_VENDOR_TERMS:
            if alias in term and display_name not in discovered:
                discovered.append(display_name)
    return discovered


def _find_activated_vendor_terms(
    *,
    route_families: list[dict[str, Any]],
) -> list[str]:
    haystack = _normalize_hint_text(
        " ".join(
            " ".join(
                filter(
                    None,
                    [
                        str(family.get("family_id") or ""),
                        str(family.get("config_path") or ""),
                        " ".join(str(port) for port in family.get("backend_ports", [])),
                    ],
                )
            )
            for family in route_families
        )
    )
    activated: list[str] = []
    for alias, display_name in KNOWN_EXTERNAL_VENDOR_TERMS:
        if alias in haystack and display_name not in activated:
            activated.append(display_name)
    return activated


def _extract_version_from_text(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    if match is None:
        return None
    return match.group(1)


def _parse_bootstrap_polling_analysis(
    httpd_result: dict[str, Any],
    source_result: dict[str, Any],
) -> dict[str, Any]:
    httpd_lines = _result_lines(httpd_result)
    source_lines = _result_lines(source_result)

    bootstrap_httpd_terms = ("/fa/server/connection/login", "storeFireflowCookie")
    polling_httpd_terms = (
        "getAFASessionInfo",
        "CommandsDispatcher",
        "bridge/refresh",
        "/afa/php/ws.php",
        "BusinessFlow/shallow_health_check",
        "BusinessFlow/deep_health_check",
        "/aff/api/internal/noauth/health/shallow",
        "/aff/api/internal/noauth/health/deep",
    )
    bootstrap_source_terms = ("storeFireflowCookie", "getFireflowCookie", "AFF_COOKIE", "BFCookie")
    polling_source_terms = ("getAFASessionInfo", "VerifyGetFASessionIdValid", "Could not find AlgosecSession", "checkFireFlowAuth")

    httpd_bootstrap_lines = [line for line in httpd_lines if _line_contains_any(line, bootstrap_httpd_terms)]
    httpd_polling_lines = [line for line in httpd_lines if _line_contains_any(line, polling_httpd_terms)]
    source_runtime_bootstrap_lines = [
        line for line in source_lines if _is_log_line(line) and _line_contains_any(line, ("storeFireflowCookie", "getFireflowCookie"))
    ]
    source_runtime_polling_lines = [
        line for line in source_lines if _is_log_line(line) and _line_contains_any(line, ("getAFASessionInfo",))
    ]
    source_static_bootstrap_lines = [
        line
        for line in source_lines
        if not _is_log_line(line) and _line_contains_any(line, bootstrap_source_terms)
    ]
    source_static_polling_lines = [
        line
        for line in source_lines
        if not _is_log_line(line) and _line_contains_any(line, polling_source_terms)
    ]

    session_occurrences: dict[str, int] = {}
    runtime_events_by_session: dict[str, list[dict[str, Any]]] = {}
    seen_event_keys: set[tuple[str, str, str]] = set()
    for line in source_lines:
        if not _is_log_line(line):
            continue
        event_kind: str | None = None
        if _line_contains_any(line, ("storeFireflowCookie", "getFireflowCookie")):
            event_kind = "bootstrap"
        elif "getAFASessionInfo" in line:
            event_kind = "polling"
        if event_kind is None:
            continue
        session_id = _extract_session_token(line)
        timestamp = _extract_log_timestamp(line)
        if session_id is None or timestamp is None:
            continue
        event_key = (session_id, event_kind, timestamp.isoformat())
        if event_key in seen_event_keys:
            continue
        seen_event_keys.add(event_key)
        runtime_events_by_session.setdefault(session_id, []).append(
            {
                "event_kind": event_kind,
                "timestamp": timestamp,
                "line": line,
            }
        )
        if event_kind == "polling":
            session_occurrences[session_id] = session_occurrences.get(session_id, 0) + 1

    repeated_polling_sessions = [
        {"session_id": session_id, "occurrence_count": count}
        for session_id, count in sorted(session_occurrences.items(), key=lambda item: (-item[1], item[0]))
        if count >= 3
    ]

    bootstrap_anchor_sessions: list[dict[str, Any]] = []
    polling_only_sessions: list[dict[str, Any]] = []
    for session_id, events in runtime_events_by_session.items():
        ordered_events = sorted(events, key=lambda item: item["timestamp"])
        bootstrap_events = [item for item in ordered_events if item["event_kind"] == "bootstrap"]
        polling_events = [item for item in ordered_events if item["event_kind"] == "polling"]
        if not polling_events:
            continue
        polling_deltas = [
            int((polling_events[index]["timestamp"] - polling_events[index - 1]["timestamp"]).total_seconds())
            for index in range(1, len(polling_events))
        ]
        cadence_like_deltas = [delta for delta in polling_deltas if 240 <= delta <= 360]
        representative_gap = None
        if cadence_like_deltas:
            cadence_sorted = sorted(cadence_like_deltas)
            representative_gap = cadence_sorted[len(cadence_sorted) // 2]
        if bootstrap_events:
            first_bootstrap = bootstrap_events[0]["timestamp"]
            first_poll_after_bootstrap = next(
                (
                    polling_event["timestamp"]
                    for polling_event in polling_events
                    if polling_event["timestamp"] >= first_bootstrap
                ),
                None,
            )
            if first_poll_after_bootstrap is not None:
                bootstrap_anchor_sessions.append(
                    {
                        "session_id": session_id,
                        "bootstrap_event_count": len(bootstrap_events),
                        "polling_event_count": len(polling_events),
                        "first_bootstrap_at": _format_datetime_z(first_bootstrap),
                        "first_poll_after_bootstrap_at": _format_datetime_z(first_poll_after_bootstrap),
                        "first_poll_after_bootstrap_seconds": int(
                            (first_poll_after_bootstrap - first_bootstrap).total_seconds()
                        ),
                        "cadence_like_gap_count": len(cadence_like_deltas),
                        "representative_polling_gap_seconds": representative_gap,
                    }
                )
        elif len(polling_events) >= 3:
            polling_only_sessions.append(
                {
                    "session_id": session_id,
                    "occurrence_count": len(polling_events),
                    "first_poll_at": _format_datetime_z(polling_events[0]["timestamp"]),
                    "last_poll_at": _format_datetime_z(polling_events[-1]["timestamp"]),
                    "cadence_like_gap_count": len(cadence_like_deltas),
                    "representative_polling_gap_seconds": representative_gap,
                }
            )

    bootstrap_anchor_sessions.sort(
        key=lambda item: (
            -item["polling_event_count"],
            item["first_poll_after_bootstrap_seconds"],
            item["session_id"],
        )
    )
    polling_only_sessions.sort(
        key=lambda item: (
            -item["occurrence_count"],
            item["session_id"],
        )
    )

    bootstrap_score = (
        (len(httpd_bootstrap_lines) * 4)
        + (len(source_runtime_bootstrap_lines) * 4)
        + min(len(source_static_bootstrap_lines), 3)
    )
    polling_score = (
        (len(httpd_polling_lines) * 2)
        + (len(source_runtime_polling_lines) * 3)
        + min(len(source_static_polling_lines), 2)
        + (len(repeated_polling_sessions) * 4)
    )

    runtime_bootstrap_count = len(httpd_bootstrap_lines) + len(source_runtime_bootstrap_lines)
    runtime_polling_count = len(httpd_polling_lines) + len(source_runtime_polling_lines)
    if bootstrap_anchor_sessions and (
        polling_only_sessions
        or any(item.get("cadence_like_gap_count", 0) >= 2 for item in bootstrap_anchor_sessions)
    ):
        status = "polling_dominant_with_bootstrap_anchor"
        window_reading = "bootstrap_anchor_then_shared_polling"
        next_stop = "inspect_aff_cookie_handoff"
        confidence = (
            "high"
            if any(item.get("first_poll_after_bootstrap_seconds", 9999) <= 10 for item in bootstrap_anchor_sessions)
            else "medium"
        )
    elif runtime_polling_count >= max(5, runtime_bootstrap_count + 4) and repeated_polling_sessions:
        status = (
            "polling_dominant_with_bootstrap_residue"
            if bootstrap_score > 0
            else "polling_dominant"
        )
        window_reading = "later_shared_polling"
        next_stop = "inspect_java_runtime_clusters"
        confidence = "high" if len(source_runtime_polling_lines) >= 8 else "medium"
    elif runtime_bootstrap_count >= 2 and bootstrap_score >= polling_score + 3:
        status = "bootstrap_dominant"
        window_reading = "original_cookie_handoff"
        next_stop = "inspect_aff_cookie_handoff"
        confidence = "high" if len(httpd_bootstrap_lines) >= 1 and len(source_runtime_bootstrap_lines) >= 1 else "medium"
    elif runtime_bootstrap_count > 0 and runtime_polling_count > 0:
        status = "mixed_window_still_ambiguous"
        window_reading = "mixed_bootstrap_and_polling"
        next_stop = "keep_bootstrap_polling_bounded"
        confidence = "medium"
    else:
        status = "distinction_thin"
        window_reading = "still_ambiguous"
        next_stop = "keep_bootstrap_polling_bounded"
        confidence = "low"

    return {
        "status": status,
        "confidence": confidence,
        "window_reading": window_reading,
        "next_stop": next_stop,
        "distinction_basis": {
            "bootstrap_score": bootstrap_score,
            "polling_score": polling_score,
            "runtime_bootstrap_line_count": runtime_bootstrap_count,
            "runtime_polling_line_count": runtime_polling_count,
            "static_bootstrap_residue_count": len(source_static_bootstrap_lines),
            "static_polling_hint_count": len(source_static_polling_lines),
            "repeated_polling_session_count": len(repeated_polling_sessions),
            "bootstrap_anchor_session_count": len(bootstrap_anchor_sessions),
            "polling_only_session_count": len(polling_only_sessions),
        },
        "repeated_polling_sessions": repeated_polling_sessions[:5],
        "polling_only_sessions": polling_only_sessions[:5],
        "bootstrap_anchor_sessions": bootstrap_anchor_sessions[:5],
        "bootstrap_runtime_samples": _dedupe_preserve_order((httpd_bootstrap_lines + source_runtime_bootstrap_lines))[:5],
        "polling_runtime_samples": _dedupe_preserve_order((httpd_polling_lines + source_runtime_polling_lines))[:5],
        "bootstrap_residue_samples": _dedupe_preserve_order(source_static_bootstrap_lines)[:5],
    }


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


def _result_lines(result: dict[str, Any]) -> list[str]:
    return [line.strip() for line in str(result.get("stdout", "")).splitlines() if line.strip()]


def _line_contains_any(line: str, terms: tuple[str, ...]) -> bool:
    return any(term in line for term in terms)


def _is_log_line(line: str) -> bool:
    return ".log" in line or "ssl_access_log" in line


def _extract_session_token(line: str) -> str | None:
    matches = re.findall(r"\[([A-Za-z0-9]{8,})\]", line)
    return matches[-1] if matches else None


def _extract_log_timestamp(line: str) -> datetime | None:
    match = re.search(r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+\]", line)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _extract_query_session_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[?&]session=([A-Za-z0-9]+)", text)
    return _dedupe_preserve_order(tokens)


def _parse_store_fireflow_cookie_events(lines: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    current_anchor: dict[str, Any] | None = None
    for line in lines:
        if "storeFireflowCookie" not in line:
            continue
        session_id = _extract_session_token(line)
        if session_id is None:
            continue
        timestamp = _extract_log_timestamp(line)
        if "_issuePostToAfa will call /storeFireflowCookie" in line:
            current_anchor = {
                "fireflow_session_id": session_id,
                "called_at": None if timestamp is None else _format_datetime_z(timestamp),
                "sample_lines": [line],
            }
            continue
        if current_anchor is None or current_anchor.get("fireflow_session_id") != session_id:
            current_anchor = {
                "fireflow_session_id": session_id,
                "called_at": None if timestamp is None else _format_datetime_z(timestamp),
                "sample_lines": [],
            }
        current_anchor["sample_lines"] = _dedupe_preserve_order(current_anchor["sample_lines"] + [line])[-4:]
        if "https://localhost:443/afa/external" in line:
            bridge_url = _extract_bracket_url(line)
            bridge_path = None if bridge_url is None else _extract_url_path(bridge_url)
            current_anchor["bridge_url"] = bridge_url
            current_anchor["bridge_path"] = bridge_path
            current_anchor["carried_session_tokens"] = _extract_query_session_tokens(line)
            if current_anchor["carried_session_tokens"] or "RestClient post:" in line:
                events.append(current_anchor.copy())
    return events


def _parse_aff_session_extend_events(lines: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in lines:
        if "/afa/external//session/extend" not in line:
            continue
        timestamp = _extract_httpd_timestamp(line)
        path_match = re.search(r'"[A-Z]+\s+([^ ]+)\s+HTTP/', line)
        path = None if path_match is None else path_match.group(1).split("?")[0]
        events.append(
            {
                "called_at": None if timestamp is None else _format_datetime_z(timestamp),
                "path": path,
                "carried_session_tokens": _extract_query_session_tokens(line),
                "sample_line": line,
            }
        )
    return events


def _extract_bracket_url(line: str) -> str | None:
    match = re.search(r"\[(https://[^\]]+)\]", line)
    if match is None:
        return None
    return match.group(1)


def _extract_url_path(url: str) -> str | None:
    match = re.search(r"https?://[^/]+(?P<path>/[^?]+)", url)
    if match is None:
        return None
    return match.group("path")


def _extract_httpd_timestamp(line: str) -> datetime | None:
    match = re.search(r"\[(\d{2})/([A-Za-z]{3})/(\d{4}):(\d{2}:\d{2}:\d{2}) [+-]\d{4}\]", line)
    if match is None:
        return None
    months = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }
    month = months.get(match.group(2))
    if month is None:
        return None
    try:
        return datetime.strptime(
            f"{match.group(3)}-{month:02d}-{match.group(1)} {match.group(4)}",
            "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


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
    businessflow_session_origin_packets: list[dict[str, Any]],
    bootstrap_polling_packets: list[dict[str, Any]],
    aff_cookie_handoff_packets: list[dict[str, Any]],
    java_runtime_cluster_packets: list[dict[str, Any]],
    provider_integration_packets: list[dict[str, Any]],
    knowledge_layer_packets: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    seams: list[dict[str, Any]] = []
    path_surface_records = _select_path_surface_records(component_records, [], [])
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
    origin_packet = next(
        (packet for packet in businessflow_session_origin_packets if packet.get("packet_id") == "businessflow_session_origin_clue"),
        None,
    )
    bootstrap_polling_packet = next(
        (packet for packet in bootstrap_polling_packets if packet.get("packet_id") == "bootstrap_polling_distinction"),
        None,
    )
    aff_cookie_packet = next(
        (packet for packet in aff_cookie_handoff_packets if packet.get("packet_id") == "aff_cookie_handoff"),
        None,
    )
    java_runtime_packet = next(
        (packet for packet in java_runtime_cluster_packets if packet.get("packet_id") == "java_runtime_clusters"),
        None,
    )
    provider_packet = next(
        (
            packet
            for packet in provider_integration_packets
            if packet.get("packet_id") == "provider_specific_integration_evidence_current_node"
        ),
        None,
    )
    knowledge_layer_packet = next(
        (packet for packet in knowledge_layer_packets if packet.get("packet_id") == "distributed_and_external_knowledge_layers"),
        None,
    )
    if provider_packet is not None and provider_packet.get("status") == "local_provider_health_partially_classified":
        seams.append(
            {
                "seam_id": provider_packet.get("next_stop", "strengthen_cross_node_directionality_proof"),
                "why_it_matters": "The current node now says more than provider presence alone: some AWS and Azure driver families are locally reachable while others may already show degraded signals. The next meaningful ambiguity is how those provider-facing families divide across nodes and whether directionality is stable in the distributed pair.",
                "starting_components": [
                    entry["provider_family_id"]
                    for entry in provider_packet.get("observed_providers", [])[:4]
                    if entry.get("provider_family_id")
                ] or ["ms-devicedriver-aws", "ms-devicedriver-azure"],
            }
        )
        return seams[:2]
    if provider_packet is not None and provider_packet.get("status") == "local_surfaces_visible_not_health_validated":
        seams.append(
            {
                "seam_id": provider_packet.get("next_stop", "capture_second_node_node_local_proof"),
                "why_it_matters": "The current node now has a bounded provider-evidence packet for AWS and Azure, so the next meaningful ambiguity is no longer what this node exposes but what changes on a second imported node-local proof.",
                "starting_components": [
                    entry["provider_family_id"]
                    for entry in provider_packet.get("observed_providers", [])[:4]
                    if entry.get("provider_family_id")
                ] or ["ms-devicedriver-aws", "ms-devicedriver-azure"],
            }
        )
        return seams[:2]
    if knowledge_layer_packet is not None and knowledge_layer_packet.get("status") == "single_node_layering_ready":
        guidance_components = [
            activation["component_id"]
            for activation in knowledge_layer_packet.get("component_guidance_activations", [])[:4]
            if activation.get("component_id")
        ]
        seams.append(
            {
                "seam_id": knowledge_layer_packet.get("next_stop", "define_second_node_request_shape"),
                "why_it_matters": "The current node now has explicit activation boundaries for component guidance and external-system hints, so the next bounded move should stay at the control-plane edge instead of widening this one node into a suite graph or vendor-health story.",
                "starting_components": guidance_components or ["ms-metro", "ms-bflow", "activemq"],
            }
        )
        external_activation = knowledge_layer_packet.get("external_integration_activation", {})
        if external_activation.get("vendor_activation_status") == "provider_specific_local_evidence_visible":
            seams.append(
                {
                    "seam_id": "capture_provider_specific_integration_evidence",
                    "why_it_matters": "AWS and Azure are already activated at the knowledge-layer level, but the next useful stop is packaging the exact node-local Apache, service-unit, listener, and journal evidence into one bounded provider packet before moving to a second node.",
                    "starting_components": ["ms-devicedriver-aws", "ms-devicedriver-azure", "httpd"],
                }
            )
        elif external_activation.get("vendor_activation_status") == "dormant":
            seams.append(
                {
                    "seam_id": "capture_provider_specific_integration_evidence",
                    "why_it_matters": "Vendor-side terms are already present in the ASMS doc-pack hint inventory, but this node still lacks provider-specific local evidence. The next useful trigger is a bounded pass that captures config, route, or log markers strong enough to activate a real vendor packet later.",
                    "starting_components": [
                        surface["likely_owner_component"]
                        for surface in external_activation.get("observed_local_external_surfaces", [])[:3]
                        if surface.get("likely_owner_component")
                    ] or ["httpd", "ms-metro", "keycloak"],
                }
            )
        return seams[:2]
    if _config_log_surface_seam_ready(path_surface_records):
        seams.append(
            {
                "seam_id": "infer_configuration_patterns_and_tunable_behaviors",
                "why_it_matters": "The successor now has bounded config and log entrypoints for the central service families, so the next useful step is separating real observed knobs and repeated runtime patterns from still-unproven folklore.",
                "starting_components": [
                    record["component_id"]
                    for record in path_surface_records
                ] or ["ms-metro", "ms-bflow", "algosec-ms"],
            }
        )
    if java_runtime_packet is not None and java_runtime_packet.get("status") == "cluster_boundaries_visible":
        seams.append(
            {
                "seam_id": java_runtime_packet.get("next_stop", "review_asms_runtime_architecture"),
                "why_it_matters": "The visible Java-heavy owners now separate into bounded runtime families, so the next useful step is an operator-facing architecture review built on observed seams instead of one generic JVM story.",
                "starting_components": [
                    cluster["component_id"]
                    for cluster in java_runtime_packet.get("cluster_families", [])[:4]
                ] or ["ms-metro", "ms-bflow", "algosec-ms"],
            }
        )
    elif java_runtime_packet is not None and java_runtime_packet.get("status") == "cluster_boundaries_partially_visible":
        seams.append(
            {
                "seam_id": "inspect_java_runtime_clusters",
                "why_it_matters": "Some Java-heavy families now separate, but the remaining runtime boundary still needs one more bounded pass before a wider architecture review would be honest.",
                "starting_components": [
                    cluster["component_id"]
                    for cluster in java_runtime_packet.get("cluster_families", [])[:4]
                ] or ["ms-metro", "ms-bflow", "algosec-ms"],
            }
        )
    elif aff_cookie_packet is not None and aff_cookie_packet.get("status") in {
        "cookie_handoff_visible",
        "cookie_handoff_partially_visible",
    }:
        seams.append(
            {
                "seam_id": aff_cookie_packet.get("next_stop", "inspect_java_runtime_clusters"),
                "why_it_matters": "The bounded bootstrap anchor now crosses a visible AFF bridge handoff, so the next ambiguity shifts from session-origin classification to the local owners and runtime boundaries behind that bridge.",
                "starting_components": ["ms-metro", "ms-bflow", "aff-boot"],
            }
        )
    elif bootstrap_polling_packet is not None and bootstrap_polling_packet.get("status") in {
        "bootstrap_dominant",
        "polling_dominant_with_bootstrap_anchor",
    }:
        seams.append(
            {
                "seam_id": "inspect_aff_cookie_handoff",
                "why_it_matters": "The retained upstream evidence now separates a bounded bootstrap anchor from the later upkeep tail, so the next bounded stop is the AFF cookie handoff instead of looping on the same origin-window ambiguity.",
                "starting_components": ["ms-bflow", "httpd", "aff-boot"],
            }
        )
    elif bootstrap_polling_packet is not None and bootstrap_polling_packet.get("status") in {
        "polling_dominant",
        "polling_dominant_with_bootstrap_residue",
    }:
        seams.append(
            {
                "seam_id": "inspect_java_runtime_clusters",
                "why_it_matters": "The retained upstream window is now polling-dominant, so the session-origin chain is bounded for now and the strongest remaining ambiguity shifts to the Java runtime boundaries behind the visible service families.",
                "starting_components": ["algosec-ms", "ms-metro", "ms-bflow"],
            }
        )
    elif bootstrap_polling_packet is not None and bootstrap_polling_packet.get("status") in {
        "mixed_window_still_ambiguous",
        "distinction_thin",
    }:
        seams.append(
            {
                "seam_id": "distinguish_bootstrap_from_shared_polling",
                "why_it_matters": "The retained origin-side window still mixes bootstrap and upkeep too closely, so the next bounded stop stays on separating those two readings without widening into full login reconstruction.",
                "starting_components": ["ms-bflow", "httpd", "aff-boot"],
            }
        )
    elif origin_packet is not None and origin_packet.get("status") in {
        "bootstrap_origin_clues_visible",
        "source_side_origin_clues_visible",
    }:
        seams.append(
            {
                "seam_id": "inspect_aff_cookie_handoff",
                "why_it_matters": "The reused FA-session chain now has an upstream BusinessFlow or AFA-side origin clue, so the next bounded stop is the AFF cookie handoff rather than broad login reconstruction.",
                "starting_components": ["ms-bflow", "httpd", "aff-boot"],
            }
        )
    elif origin_packet is not None and origin_packet.get("distinction_status") == "polling_dominant_without_httpd_bootstrap_pair":
        seams.append(
            {
                "seam_id": "inspect_aff_cookie_handoff",
                "why_it_matters": "The retained upstream window is now classified as later shared polling, while the cookie-handoff vocabulary survives only in source-side hints. The next bounded stop is the AFF cookie handoff itself rather than looping on the same bootstrap-versus-polling ambiguity.",
                "starting_components": ["ms-bflow", "httpd", "aff-boot"],
            }
        )
    elif origin_packet is not None and origin_packet.get("status") == "shared_polling_origin_clues_visible":
        seams.append(
            {
                "seam_id": "distinguish_bootstrap_from_shared_polling",
                "why_it_matters": "The retained origin-side window now looks more like later shared polling, so the next bounded stop is separating bootstrap from upkeep instead of inventing a cleaner first caller.",
                "starting_components": ["ms-bflow", "httpd", "aff-boot"],
            }
        )
    elif reuse_packet is not None and reuse_packet.get("status") == "reuse_chain_visible":
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


def _config_log_surface_seam_ready(records: list[dict[str, Any]]) -> bool:
    ready_count = 0
    for record in records:
        observed = record.get("observed", {})
        config_details = observed.get("config_path_details", [])
        log_details = observed.get("log_path_details", [])
        if any(detail.get("status") == "observed" for detail in config_details) and log_details:
            ready_count += 1
    return ready_count >= 3


def _render_summary(surface_map: dict[str, Any]) -> str:
    records = surface_map["component_records"]
    central = [record for record in records if record["inference"]["appears_central"]][:5]
    top_candidates = [record for record in records if record["inference"]["support_priority_score"] > 0][:5]
    failed_records = _select_failed_records(records)
    edge_route_hints = surface_map.get("edge_route_hints", [])[:5]
    boundary_packets = surface_map.get("boundary_packets", [])[:3]
    session_parity_packets = surface_map.get("session_parity_packets", [])[:2]
    usersession_bridge_packets = surface_map.get("usersession_bridge_packets", [])[:2]
    usersession_reuse_packets = surface_map.get("usersession_reuse_packets", [])[:2]
    businessflow_session_origin_packets = surface_map.get("businessflow_session_origin_packets", [])[:2]
    bootstrap_polling_packets = surface_map.get("bootstrap_polling_packets", [])[:2]
    aff_cookie_handoff_packets = surface_map.get("aff_cookie_handoff_packets", [])[:2]
    java_runtime_cluster_packets = surface_map.get("java_runtime_cluster_packets", [])[:2]
    provider_integration_packets = surface_map.get("provider_integration_packets", [])[:2]
    knowledge_layer_packets = surface_map.get("knowledge_layer_packets", [])[:2]
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
    lines.extend(["", "## Fast Read", ""])
    strongest_owner_line = _build_strongest_owner_line(boundary_packets, edge_route_hints)
    if strongest_owner_line:
        lines.append(f"- {strongest_owner_line}")
    else:
        lines.append("- No bounded route-owner chain is strong enough to headline yet.")
    if failed_records:
        failed_summary = ", ".join(
            f"`{record['display_name']}` ({record['observed'].get('active_state', 'unknown')})"
            for record in failed_records[:4]
        )
        lines.append(f"- Immediate pressure points: {failed_summary}.")
    else:
        lines.append("- No failed high-signal services were highlighted in this bounded pass.")
    if session_parity_packets:
        packet = session_parity_packets[0]
        agreement = packet.get("agreement", {})
        lines.append(
            f"- Session seam: `{packet['packet_id']}` is `{packet['status']}` with status-code match `{agreement.get('status_code_match')}` and body match `{agreement.get('body_match')}`."
        )
    if seams:
        seam = seams[0]
        starts = ", ".join(seam["starting_components"]) or "none"
        lines.append(f"- Next best seam: `{seam['seam_id']}` from {starts}.")
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
    lines.extend(["", "## Config And Log Surfaces", ""])
    surfaced_records = _select_path_surface_records(records, central, top_candidates)
    surfaced_any_paths = False
    for record in surfaced_records:
        config_summary = _render_path_surface_summary(record, detail_key="config_path_details", candidate_key="config_path_candidates")
        log_summary = _render_path_surface_summary(record, detail_key="log_path_details", candidate_key="log_path_candidates")
        if not config_summary and not log_summary:
            continue
        surfaced_any_paths = True
        lines.append(
            f"- `{record['display_name']}`: configs {config_summary or 'none visible'}; logs {log_summary or 'none visible'}."
        )
    if not surfaced_any_paths:
        lines.append("- No stronger config or log path surfaces were visible in this bounded pass.")
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
    lines.extend(["", "## Session Origin Clues", ""])
    if businessflow_session_origin_packets:
        for packet in businessflow_session_origin_packets:
            httpd_terms = ", ".join(packet["httpd_origin_markers"].get("matched_terms", [])[:5]) or "none"
            source_terms = ", ".join(packet["source_origin_markers"].get("matched_terms", [])[:5]) or "none"
            distinction_status = packet.get("distinction_status", "not_set")
            missing_bootstrap = ", ".join(packet.get("distinction_basis", {}).get("httpd_bootstrap_terms_missing", [])[:2]) or "none"
            lines.append(
                f"- `{packet['packet_id']}`: status `{packet['status']}` with distinction `{distinction_status}` and reading `{packet['origin_reading']}`; Apache-side markers `{httpd_terms}` and source-side markers `{source_terms}` are visible, while missing Apache bootstrap terms are `{missing_bootstrap}`. Next stop: `{packet['next_stop']}`."
            )
    else:
        lines.append("- No bounded upstream session-origin packet was strong enough to summarize in this pass.")
    lines.extend(["", "## Bootstrap Vs Polling", ""])
    if bootstrap_polling_packets:
        for packet in bootstrap_polling_packets:
            anchor_samples = ", ".join(
                (
                    f"{item['session_id']} store->{item['first_poll_after_bootstrap_seconds']}s"
                    f" then ~{item['representative_polling_gap_seconds']}s cadence"
                )
                if item.get("representative_polling_gap_seconds") is not None
                else f"{item['session_id']} store->{item['first_poll_after_bootstrap_seconds']}s"
                for item in packet.get("bootstrap_anchor_sessions", [])[:2]
            ) or "none"
            polling_only = ", ".join(
                (
                    f"{item['session_id']} x{item['occurrence_count']}"
                    if item.get("occurrence_count") is not None
                    else item["session_id"]
                )
                for item in packet.get("polling_only_sessions", [])[:2]
            ) or "none"
            lines.append(
                f"- `{packet['packet_id']}`: status `{packet['status']}` with reading `{packet['window_reading']}`; bootstrap anchors `{anchor_samples}` and polling-only sessions `{polling_only}` are visible. Next stop: `{packet['next_stop']}`."
            )
    else:
        lines.append("- No bounded bootstrap-versus-polling packet was strong enough to summarize in this pass.")
    lines.extend(["", "## AFF Cookie Handoff", ""])
    if aff_cookie_handoff_packets:
        for packet in aff_cookie_handoff_packets:
            handoff = next(
                (
                    link
                    for link in packet.get("handoff_links", [])
                    if link.get("matched_store_bridge_token") and link.get("httpd_extend_path")
                ),
                (packet.get("handoff_links") or [{}])[0],
            )
            route_hint = handoff.get("edge_route_hint") or {}
            owner = route_hint.get("likely_owner_component", "unknown")
            bridge_path = handoff.get("store_bridge_path") or "none"
            carried = handoff.get("matched_store_bridge_token") or ", ".join(handoff.get("carried_session_tokens", [])[:2]) or "none"
            extend_path = handoff.get("httpd_extend_path") or "none"
            lines.append(
                f"- `{packet['packet_id']}`: status `{packet['status']}`; bootstrap anchor `{handoff.get('fireflow_session_id', 'unknown')}` carries token `{carried}` through `{bridge_path}` toward owner `{owner}`, with later extend path `{extend_path}`. Next stop: `{packet['next_stop']}`."
            )
    else:
        lines.append("- No bounded AFF cookie-handoff packet was strong enough to summarize in this pass.")
    lines.extend(["", "## Java Runtime Clusters", ""])
    if java_runtime_cluster_packets:
        for packet in java_runtime_cluster_packets:
            cluster_summaries = []
            for cluster in packet.get("cluster_families", [])[:4]:
                identity = cluster.get("catalina_base") or ", ".join(cluster.get("jar_paths", [])[:1]) or cluster.get("service_unit") or "generic java family"
                ports = ", ".join(str(port) for port in cluster.get("listener_ports", [])) or "none"
                routes = ", ".join(cluster.get("route_paths", [])[:2] or cluster.get("boundary_routes", [])[:2]) or "no explicit route family"
                cluster_summaries.append(
                    f"{cluster['component_id']} as `{cluster.get('cluster_type', 'generic_java_family')}` via `{identity}` on ports `{ports}` with routes `{routes}`"
                )
            shared_substrates = ", ".join(
                substrate["component_id"] for substrate in packet.get("shared_substrates", [])[:3]
            ) or "none"
            lines.append(
                f"- `{packet['packet_id']}`: status `{packet['status']}`; visible families {', '.join(cluster_summaries) if cluster_summaries else 'none'}. Shared substrates: `{shared_substrates}`. Next stop: `{packet['next_stop']}`."
            )
    else:
        lines.append("- No bounded Java runtime cluster packet was strong enough to summarize in this pass.")
    lines.extend(["", "## Provider-Specific Integration Evidence", ""])
    if provider_integration_packets:
        for packet in provider_integration_packets:
            provider_summaries = []
            for entry in packet.get("observed_providers", [])[:3]:
                apache = entry.get("apache_config_family", {})
                runtime = entry.get("local_runtime_service", {})
                health_probe = entry.get("local_health_probe", {})
                journal = entry.get("recent_journal_signals", {})
                health_notes = [f"health `{entry.get('health_state', 'configured')}`"]
                if health_probe.get("probe_attempted"):
                    reachability = "reachable" if health_probe.get("reachable") else "not reachable"
                    health_notes.append(
                        f"local port `{health_probe.get('probe_port', 'unknown')}` {reachability}"
                    )
                if journal.get("failure_signal_count", 0) > 0:
                    categories = ", ".join(journal.get("signal_categories", [])[:2]) or "failure signals"
                    health_notes.append(
                        f"journal signals `{categories}` x{journal.get('failure_signal_count', 0)}"
                    )
                provider_summaries.append(
                    f"{entry.get('vendor_label', 'unknown')} via `{entry.get('provider_family_id', 'unknown')}` "
                    f"from `{apache.get('config_path', 'unknown config')}` to port `{apache.get('backend_port', 'unknown')}` "
                    f"with service `{runtime.get('service_unit', 'unknown service')}` "
                    f"({' ; '.join(health_notes)})"
                )
            adjacent = ", ".join(
                (
                    f"{item.get('family_id', 'unknown')}->{item.get('backend_port', 'unknown')}"
                )
                for item in packet.get("adjacent_surfaces", [])[:3]
            ) or "none"
            coordination = ", ".join(
                (
                    f"{item.get('component_id', 'unknown')}"
                    + (
                        f" peers {','.join(clue.get('remote_ip', '?') for clue in item.get('peer_connection_clues', [])[:2])}"
                        if item.get("peer_connection_clues")
                        else ""
                    )
                    + (
                        f" journal {','.join(item.get('journal_directionality_clues', {}).get('matched_terms', [])[:2])}"
                        if item.get("journal_directionality_clues", {}).get("signal_count", 0) > 0
                        else ""
                    )
                )
                for item in packet.get("coordination_surfaces", [])[:4]
                if item.get("peer_connection_clues") or item.get("journal_directionality_clues", {}).get("signal_count", 0) > 0
            ) or "none"
            not_proven = "; ".join(packet.get("not_proven", [])[:2]) or "none"
            lines.append(
                f"- `{packet['packet_id']}`: status `{packet['status']}`; observed providers {', '.join(provider_summaries) if provider_summaries else 'none'}; adjacent surfaces `{adjacent}`; coordination clues `{coordination}`; not proven: {not_proven}. Next stop: `{packet['next_stop']}`."
            )
    else:
        lines.append("- No bounded provider-specific integration packet was strong enough to summarize in this pass.")
    lines.extend(["", "## Distributed And External Knowledge Layers", ""])
    if knowledge_layer_packets:
        for packet in knowledge_layer_packets:
            node_scope = packet.get("node_scope", {})
            external = packet.get("external_integration_activation", {})
            guidance_components = ", ".join(
                (
                    f"{activation.get('component_id', 'unknown')} as `{activation.get('component_family', 'unknown_family')}`"
                    + (
                        f" v{activation.get('observed_version')}"
                        if activation.get("observed_version")
                        else ""
                    )
                )
                for activation in packet.get("component_guidance_activations", [])[:5]
            ) or "none"
            observed_surfaces = ", ".join(
                (
                    f"{surface.get('route_path')} -> {surface.get('likely_owner_component', 'unknown owner')}"
                    if surface.get("route_path")
                    else f"{surface.get('family_id', surface.get('surface_family', 'unknown surface'))} -> {surface.get('likely_owner_component', 'unknown owner')}"
                )
                for surface in external.get("observed_local_external_surfaces", [])[:4]
            ) or "none"
            vendor_hints = ", ".join(external.get("dormant_vendor_inventory", [])[:5]) or "none"
            lines.append(
                f"- `{packet['packet_id']}`: node scope `{node_scope.get('status', 'unknown')}` with cross-node envelope `{node_scope.get('cross_node_envelope_status', 'unknown')}`; component guidance `{guidance_components}`; observed local external surfaces `{observed_surfaces}`; vendor activation `{external.get('vendor_activation_status', 'unknown')}` with dormant inventory `{vendor_hints}`. Next stop: `{packet['next_stop']}`."
            )
    else:
        lines.append("- No bounded distributed or external knowledge-layer packet was strong enough to summarize in this pass.")
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


def _render_diagnostic_playbook(surface_map: dict[str, Any]) -> str:
    records = surface_map["component_records"]
    central = [record for record in records if record["inference"]["appears_central"]][:5]
    top_candidates = [record for record in records if record["inference"]["support_priority_score"] > 0][:5]
    failed_records = _select_failed_records(records)
    surfaced_records = _select_path_surface_records(records, central, top_candidates)
    boundary_packets = surface_map.get("boundary_packets", [])[:2]
    session_parity_packets = surface_map.get("session_parity_packets", [])[:2]
    provider_integration_packets = surface_map.get("provider_integration_packets", [])[:2]
    seams = surface_map.get("next_candidate_seams", [])[:2]
    unknowns = surface_map.get("unknowns", [])[:5]

    lines = [
        "# ADF Successor Diagnostic Playbook",
        "",
        "## Use This For",
        "",
        f"- Live triage on `{surface_map['target']['target_label']}` when the engineer needs the fastest bounded owner, evidence, and escalation path.",
        "- Decision support under pressure, not full product study.",
        "- A fast route from symptom to local owner, first checks, and explicit stop rules.",
        "",
        "## Fast Start",
        "",
    ]
    strongest_owner_line = _build_strongest_owner_line(boundary_packets, surface_map.get("edge_route_hints", []))
    if strongest_owner_line:
        lines.append(f"- Strongest current owner chain: {strongest_owner_line}")
    if session_parity_packets:
        packet = session_parity_packets[0]
        lines.append(
            f"- Session check: `{packet['display_name']}` is `{packet['status']}`. The fronted `/FireFlow/api/session` path and the direct aff-boot session path currently agree at the bounded edge."
        )
    if provider_integration_packets:
        packet = provider_integration_packets[0]
        degraded = [
            entry.get("provider_family_id", "unknown")
            for entry in packet.get("observed_providers", [])
            if entry.get("health_state") == "degraded"
        ]
        if degraded:
            lines.append(
                f"- Provider warning: local degradation is visible for {', '.join(f'`{item}`' for item in degraded[:4])}, but provider-side success is still not proven."
            )
    if failed_records:
        failed_summary = ", ".join(
            f"`{record['display_name']}`" for record in failed_records[:4]
        )
        lines.append(f"- Failed or degraded-looking services worth checking early: {failed_summary}.")
    if not strongest_owner_line and not session_parity_packets and not provider_integration_packets and not failed_records:
        lines.append("- This bounded pass has not yet produced a strong pressure-path headline.")

    lines.extend(["", "## Route To Owner Shortlist", ""])
    route_lines = _build_route_owner_lines(boundary_packets, surface_map.get("edge_route_hints", []))
    if route_lines:
        lines.extend(f"- {line}" for line in route_lines)
    else:
        lines.append("- No bounded route-owner shortlist is ready yet.")

    lines.extend(["", "## First Checks By Family", ""])
    check_records = []
    for record in failed_records + central + top_candidates:
        if record not in check_records:
            check_records.append(record)
        if len(check_records) >= 5:
            break
    if not check_records:
        check_records = surfaced_records[:5]
    if check_records:
        for record in check_records:
            ports = ", ".join(str(port) for port in record["observed"].get("listening_ports", [])[:4]) or "none linked yet"
            config_summary = _render_path_surface_summary(record, detail_key="config_path_details", candidate_key="config_path_candidates") or "none visible"
            log_summary = _render_path_surface_summary(record, detail_key="log_path_details", candidate_key="log_path_candidates") or "none visible"
            active_state = record["observed"].get("active_state", "unknown")
            lines.append(
                f"- `{record['display_name']}`: state `{active_state}`, listener ports `{ports}`, configs {config_summary}, logs {log_summary}."
            )
    else:
        lines.append("- No stronger family-level check surface is ready yet.")

    lines.extend(["", "## Escalate Or Stop When", ""])
    stop_lines = _build_stop_rule_lines(surface_map)
    if stop_lines:
        lines.extend(f"- {line}" for line in stop_lines)
    else:
        lines.append("- Stop when the current packet chain stops proving ownership and would require broad product guessing.")

    lines.extend(["", "## Known Boundaries", ""])
    if unknowns:
        lines.extend(f"- {item}" for item in unknowns)
    else:
        lines.append("- No additional unknowns were recorded in this bounded pass.")

    lines.extend(["", "## Best Next Deepening Step", ""])
    if seams:
        for seam in seams:
            starts = ", ".join(seam["starting_components"]) or "none"
            lines.append(
                f"- `{seam['seam_id']}`: {seam['why_it_matters']} Starting points: {starts}."
            )
    else:
        lines.append("- No deeper seam is named yet.")
    lines.append("")
    return "\n".join(lines) + "\n"


def _render_runtime_cookbook(surface_map: dict[str, Any]) -> str:
    records = surface_map["component_records"]
    central = [record for record in records if record["inference"]["appears_central"]][:6]
    top_candidates = [record for record in records if record["inference"]["support_priority_score"] > 0][:6]
    surfaced_records = _select_path_surface_records(records, central, top_candidates)
    packet_groups = [
        ("Boundary packets", surface_map.get("boundary_packets", [])[:2]),
        ("Session parity packets", surface_map.get("session_parity_packets", [])[:2]),
        ("UserSession bridge packets", surface_map.get("usersession_bridge_packets", [])[:2]),
        ("Provider packets", surface_map.get("provider_integration_packets", [])[:2]),
        ("Knowledge-layer packets", surface_map.get("knowledge_layer_packets", [])[:2]),
    ]
    seams = surface_map.get("next_candidate_seams", [])[:2]
    unknowns = surface_map.get("unknowns", [])[:6]

    lines = [
        "# ADF Successor Runtime Cookbook Guide",
        "",
        "## Purpose",
        "",
        "- Preserve the richer product-learning view that sits behind the fast diagnostic playbook.",
        "- Keep the explanation grounded in observed runtime packets instead of broad suite folklore.",
        "- Help engineers translate product-facing paths into runtime-facing owners, seams, and evidence surfaces.",
        "",
        "## Current Runtime Shape",
        "",
    ]
    if central:
        for record in central:
            ports = ", ".join(str(port) for port in record["observed"].get("listening_ports", [])[:4]) or "none linked yet"
            category = record["inference"].get("first_observed_category", "unknown")
            lines.append(
                f"- `{record['display_name']}` currently reads as `{category}` on ports `{ports}`."
            )
    else:
        for record in top_candidates[:5]:
            category = record["inference"].get("first_observed_category", "unknown")
            lines.append(
                f"- `{record['display_name']}` is a top visible candidate for `{category}` in this bounded pass."
            )

    lines.extend(["", "## Product Language To Runtime Owners", ""])
    route_lines = _build_route_owner_lines(surface_map.get("boundary_packets", []), surface_map.get("edge_route_hints", []))
    if route_lines:
        lines.extend(f"- {line}" for line in route_lines[:6])
    else:
        lines.append("- Product-facing route ownership is still too thin to summarize cleanly.")

    lines.extend(["", "## Proven Packets And Why They Matter", ""])
    packet_rendered = False
    for label, packets in packet_groups:
        if not packets:
            continue
        packet_rendered = True
        lines.append(f"### {label}")
        lines.append("")
        for packet in packets:
            headline = packet.get("display_name") or packet.get("packet_id") or packet.get("boundary_id") or "bounded packet"
            status = packet.get("status", "unknown")
            why = packet.get("why_it_matters") or "Why it matters is not set."
            confirmed = "; ".join(packet.get("confirmed_elements", [])[:2]) or "No confirmed elements recorded."
            lines.append(
                f"- {headline} is `{status}`. {why} Confirmed elements: {confirmed}"
            )
        lines.append("")
    if not packet_rendered:
        lines.append("- No richer packet layer is ready yet beyond the base component inventory.")

    lines.extend(["", "## Config And Log Entry Points", ""])
    if surfaced_records:
        for record in surfaced_records[:6]:
            config_summary = _render_path_surface_summary(record, detail_key="config_path_details", candidate_key="config_path_candidates") or "none visible"
            log_summary = _render_path_surface_summary(record, detail_key="log_path_details", candidate_key="log_path_candidates") or "none visible"
            lines.append(
                f"- `{record['display_name']}`: configs {config_summary}; logs {log_summary}."
            )
    else:
        lines.append("- No strong config or log entry points were surfaced in this bounded pass.")

    lines.extend(["", "## What Is Still Not Proven", ""])
    if unknowns:
        lines.extend(f"- {item}" for item in unknowns)
    else:
        lines.append("- No explicit unknowns were recorded.")
    provider_packets = surface_map.get("provider_integration_packets", [])[:1]
    if provider_packets:
        for note in provider_packets[0].get("not_proven", [])[:3]:
            lines.append(f"- {note}")

    lines.extend(["", "## Best Follow-On Study Paths", ""])
    if seams:
        for seam in seams:
            starts = ", ".join(seam["starting_components"]) or "none"
            lines.append(
                f"- `{seam['seam_id']}`: {seam['why_it_matters']} Starting points: {starts}."
            )
    else:
        lines.append("- No follow-on study path is named yet.")
    lines.append("")
    return "\n".join(lines) + "\n"


def _build_strongest_owner_line(
    boundary_packets: list[dict[str, Any]],
    edge_route_hints: list[dict[str, Any]],
) -> str | None:
    if boundary_packets:
        packet = boundary_packets[0]
        routes = ", ".join(packet.get("route_family", [])[:3]) or "the visible edge"
        owner = packet.get("local_owner", {}).get("component_id", "unknown owner")
        ports = ", ".join(
            str(port) for port in packet.get("local_owner", {}).get("listening_ports", [])[:4]
        ) or "none"
        return f"routes {routes} currently land on `{owner}` over local ports `{ports}`."
    if edge_route_hints:
        hint = edge_route_hints[0]
        route_path = hint.get("route_path") or "(route path not explicit)"
        owner = hint.get("likely_owner_component") or "owner still unclear"
        backend = hint.get("backend_url") or (
            f"port {hint['backend_port']}" if hint.get("backend_port") else "no backend target"
        )
        return f"`{route_path}` currently points toward `{backend}` with likely owner `{owner}`."
    return None


def _build_route_owner_lines(
    boundary_packets: list[dict[str, Any]],
    edge_route_hints: list[dict[str, Any]],
) -> list[str]:
    rendered: list[str] = []
    seen_routes: set[str] = set()
    for packet in boundary_packets[:3]:
        owner = packet.get("local_owner", {}).get("component_id", "unknown owner")
        ports = ", ".join(
            str(port) for port in packet.get("local_owner", {}).get("listening_ports", [])[:4]
        ) or "none"
        for route in packet.get("route_family", [])[:4]:
            key = f"{route}:{owner}"
            if key in seen_routes:
                continue
            rendered.append(f"`{route}` -> `{owner}` on local ports `{ports}`.")
            seen_routes.add(key)
    for hint in edge_route_hints[:6]:
        route_path = hint.get("route_path") or "(route path not explicit)"
        owner = hint.get("likely_owner_component") or "owner still unclear"
        key = f"{route_path}:{owner}"
        if key in seen_routes:
            continue
        backend = hint.get("backend_url") or (
            f"port {hint['backend_port']}" if hint.get("backend_port") else "no backend target"
        )
        rendered.append(
            f"`{route_path}` -> `{owner}` via `{backend}` from `{hint['config_path']}:{hint['line_number']}`."
        )
        seen_routes.add(key)
    return rendered


def _select_failed_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed = [
        record
        for record in records
        if record.get("observed", {}).get("active_state") == "failed"
    ]
    failed.sort(
        key=lambda record: (
            -int(record.get("inference", {}).get("support_priority_score", 0)),
            str(record.get("display_name", "")),
        )
    )
    return failed[:5]


def _build_stop_rule_lines(surface_map: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    boundary_packets = surface_map.get("boundary_packets", [])[:1]
    session_parity_packets = surface_map.get("session_parity_packets", [])[:1]
    provider_packets = surface_map.get("provider_integration_packets", [])[:1]
    if boundary_packets:
        packet = boundary_packets[0]
        for question in packet.get("remaining_questions", [])[:2]:
            lines.append(question)
    if session_parity_packets:
        packet = session_parity_packets[0]
        for question in packet.get("remaining_questions", [])[:2]:
            lines.append(question)
    if provider_packets:
        packet = provider_packets[0]
        for note in packet.get("not_proven", [])[:2]:
            lines.append(note)
    deduped: list[str] = []
    seen: set[str] = set()
    for line in lines:
        if line in seen:
            continue
        deduped.append(line)
        seen.add(line)
    return deduped[:5]


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


def _render_path_surface_summary(
    record: dict[str, Any],
    *,
    detail_key: str,
    candidate_key: str,
) -> str:
    observed = record.get("observed", {})
    details = observed.get(detail_key, [])[:3]
    rendered: list[str] = []
    if details:
        for detail in details:
            path = detail.get("path")
            if not path:
                continue
            label = detail.get("status") or "candidate"
            source = detail.get("source") or "bounded evidence"
            rendered.append(f"`{path}` ({label}, {source})")
    else:
        for path in observed.get(candidate_key, [])[:3]:
            rendered.append(f"`{path}` (candidate)")
    return ", ".join(rendered)


def _select_path_surface_records(
    records: list[dict[str, Any]],
    central: list[dict[str, Any]],
    top_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    preferred_ids = {"aff-boot", "activemq", "keycloak", "httpd"}
    for record in records:
        if record in central or record in top_candidates:
            selected.append(record)
            continue
        observed = record.get("observed", {})
        if observed.get("active_state") == "failed" or record.get("component_id") in preferred_ids:
            selected.append(record)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in selected:
        component_id = str(record.get("component_id") or "")
        if component_id in seen:
            continue
        deduped.append(record)
        seen.add(component_id)
        if len(deduped) >= 7:
            break
    return deduped


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


def _format_datetime_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _isoformat_z() -> str:
    return _format_datetime_z(datetime.now(timezone.utc))
