from __future__ import annotations

import html
import json
import platform
import re
import shlex
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .target_connection import target_shell_capture


DEFAULT_ARTIFACT_ROOT = Path("dist/candidates/adf-baseline")
TARGET_PROFILE_ARTIFACT_ROOT = Path("dist/candidates/adf-target-profile-baseline")
RUNTIME_EVIDENCE_NAME = "runtime-evidence.json"
SERVICE_INVENTORY_NAME = "service-inventory.json"
SUPPORT_BASELINE_NAME = "support-baseline.json"
SUPPORT_BASELINE_HTML_NAME = "support-baseline.html"
SYSTEMD_UNIT_KEYS = ("load_state", "active_state", "sub_state", "description")
SYSTEMD_UNIT_ROOTS = (Path("/etc/systemd/system"), Path("/usr/lib/systemd/system"))
HTTPD_CONF_ROOT = Path("/etc/httpd/conf.d")
PRODUCT_SERVICE_PREFIXES = ("algosec-", "aff-", "ms-")
PRODUCT_SERVICE_NAMES = {
    "activemq.service",
    "postgresql.service",
    "httpd.service",
    "keycloak.service",
    "elasticsearch.service",
    "kibana.service",
    "logstash.service",
}
PRODUCT_PATH_HINTS = (
    "/usr/share/fa/",
    "/usr/share/aff/",
    "/usr/share/fireflow/",
    "/usr/share/algosec_toolbox/",
    "/home/afa/algosec",
    "/opt/activemq",
    "/opt/apache-activemq",
    "/opt/apache-tomcat",
)
PATH_TOKEN_RE = re.compile(r"(/[^\"';\s)]+)")
LISTENER_PROCESS_RE = re.compile(r'users:\(\("(?P<process>[^"]+)",pid=(?P<pid>\d+)')
UNIT_DEPENDENCY_RE = re.compile(r"^(?:After|Wants|Requires)=(.+)$", re.MULTILINE)
SERVICE_ROLE_HINTS = {
    "data service": ("postgres", "mysql", "mariadb", "oracle", "mongo", "redis"),
    "queue or messaging service": ("rabbitmq", "kafka", "activemq"),
    "edge or UI service": ("nginx", "httpd", "apache", "haproxy", "jetty", "tomcat", "keycloak"),
    "search or analytics service": ("elastic", "kibana", "logstash"),
    "microservice": ("ms-",),
    "core application service": ("algosec",),
}


def generate_support_baseline(
    *,
    project_root: Path,
    target_label: str,
    artifact_root: str | Path | None = None,
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    selected_root = (
        Path(artifact_root)
        if artifact_root
        else TARGET_PROFILE_ARTIFACT_ROOT
        if profile_path is not None
        else DEFAULT_ARTIFACT_ROOT
    )
    root = project_root / selected_root
    root.mkdir(parents=True, exist_ok=True)

    runtime_evidence = collect_runtime_evidence(
        target_label=target_label,
        project_root=project_root,
        profile_path=profile_path,
    )
    service_inventory = build_service_inventory(runtime_evidence=runtime_evidence, target_label=target_label)
    support_baseline = build_support_baseline(
        runtime_evidence=runtime_evidence,
        service_inventory=service_inventory,
        target_label=target_label,
    )
    html_document = render_support_baseline_html(support_baseline)

    _dump_json(root / RUNTIME_EVIDENCE_NAME, runtime_evidence)
    _dump_json(root / SERVICE_INVENTORY_NAME, service_inventory)
    _dump_json(root / SUPPORT_BASELINE_NAME, support_baseline)
    (root / SUPPORT_BASELINE_HTML_NAME).write_text(f"{html_document}\n", encoding="utf-8")

    return {
        "status": "pass",
        "artifact_root": str(root.relative_to(project_root)),
        "generated_files": [
            str((root / RUNTIME_EVIDENCE_NAME).relative_to(project_root)),
            str((root / SERVICE_INVENTORY_NAME).relative_to(project_root)),
            str((root / SUPPORT_BASELINE_NAME).relative_to(project_root)),
            str((root / SUPPORT_BASELINE_HTML_NAME).relative_to(project_root)),
        ],
        "summary": {
            "target_label": target_label,
            "service_count": service_inventory["summary"]["total_services"],
            "critical_service_count": service_inventory["summary"]["critical_services"],
            "comparison_checkpoint_count": len(support_baseline["comparison_checkpoints"]),
        },
    }


def collect_runtime_evidence(
    *,
    target_label: str,
    project_root: Path | None = None,
    profile_path: str | Path | None = None,
) -> dict[str, Any]:
    if profile_path is None:
        os_release = _load_os_release()
        hostname = socket.gethostname()
        command_results = [
            _run_command(
                command_id="systemd_units",
                argv=["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--plain", "--no-legend"],
                max_preview_lines=400,
            ),
            _run_command(
                command_id="systemd_unit_files",
                argv=["systemctl", "list-unit-files", "--type=service", "--no-pager", "--plain", "--no-legend"],
                max_preview_lines=400,
            ),
            _run_command(
                command_id="listening_tcp_ports",
                argv=["ss", "-lntHp"],
                max_preview_lines=400,
            ),
            _run_command(
                command_id="process_inventory",
                argv=["ps", "-eo", "pid=,ppid=,user=,comm=,args="],
                max_preview_lines=200,
            ),
        ]
        observed_note = "Runtime identity, service-manager output, TCP listeners, and process inventory were collected from local read-only sources."
        target_connection = {
            "collection_mode": "local_host",
            "profile_path": None,
        }
    else:
        if project_root is None:
            raise ValueError("project_root is required when profile_path is provided")
        os_release = _load_target_os_release(project_root=project_root, profile_path=profile_path)
        hostname = _load_target_hostname(project_root=project_root, profile_path=profile_path)
        kernel_release = _load_target_kernel_release(project_root=project_root, profile_path=profile_path)
        command_results = [
            _run_target_command(
                project_root=project_root,
                profile_path=profile_path,
                command_id="systemd_units",
                command="systemctl list-units --type=service --all --no-pager --plain --no-legend",
                max_preview_lines=400,
            ),
            _run_target_command(
                project_root=project_root,
                profile_path=profile_path,
                command_id="systemd_unit_files",
                command="systemctl list-unit-files --type=service --no-pager --plain --no-legend",
                max_preview_lines=400,
            ),
            _run_target_command(
                project_root=project_root,
                profile_path=profile_path,
                command_id="listening_tcp_ports",
                command="ss -lntHp",
                max_preview_lines=400,
            ),
            _run_target_command(
                project_root=project_root,
                profile_path=profile_path,
                command_id="process_inventory",
                command="ps -eo 'pid=,ppid=,user=,comm=,args='",
                max_preview_lines=200,
            ),
        ]
        observed_note = "Runtime identity, service-manager output, TCP listeners, and process inventory were collected from the target connection profile through bounded read-only SSH commands."
        target_connection = {
            "collection_mode": "target_profile",
            "profile_path": str(profile_path),
        }

    observed_facts = {
        "hostname": hostname,
        "os_release": os_release,
        "kernel_release": platform.release() if profile_path is None else kernel_release,
        "platform": platform.platform() if profile_path is None else "remote_target_via_target_connection",
    }
    unavailable_classes = []
    if command_results[0]["status"] != "completed":
        unavailable_classes.append("systemd service inventory is incomplete because systemctl was unavailable.")
    if command_results[2]["status"] != "completed":
        unavailable_classes.append("network listener discovery is incomplete because ss was unavailable.")

    return {
        "schema_version": "adf-runtime-evidence/v1",
        "generated_at": _isoformat_z(),
        "target": {
            "target_label": target_label,
            "execution_host": observed_facts["hostname"],
        },
        "target_connection": target_connection,
        "collection_policy": {
            "mode": "read_only",
            "canonical_source_of_truth": "machine_readable_json",
            "evidence_classes": [
                "runtime_identity",
                "service_inventory",
                "network_exposure",
                "process_inventory",
                "observation_boundaries",
            ],
        },
        "observed_facts": observed_facts,
        "command_results": command_results,
        "observation_boundaries": {
            "observed": [
                observed_note,
            ],
            "inferred": [
                "Support-priority hints and service roles are derived from command output heuristics in the build-pack.",
            ],
            "unknown": [
                "Only first-pass config and log checkpoints are collected in this slice.",
                "Dependency mapping between AlgoSec services is not yet collected directly.",
                *unavailable_classes,
            ],
        },
    }


def build_service_inventory(*, runtime_evidence: dict[str, Any], target_label: str) -> dict[str, Any]:
    results = {entry["command_id"]: entry for entry in runtime_evidence["command_results"]}
    collect_local_checkpoints = runtime_evidence.get("target_connection", {}).get("collection_mode") != "target_profile"
    services = _services_from_runtime_results(results, collect_local_checkpoints=collect_local_checkpoints)

    critical_services = sum(1 for service in services if service["inference"]["support_importance_tier"] == "critical")
    supporting_services = sum(1 for service in services if service["inference"]["support_importance_tier"] == "supporting")
    reference_services = sum(1 for service in services if service["inference"]["support_importance_tier"] == "reference")

    return {
        "schema_version": "adf-service-inventory/v1",
        "generated_at": _isoformat_z(),
        "target": {
            "target_label": target_label,
            "hostname": runtime_evidence["observed_facts"]["hostname"],
        },
        "artifact_refs": {
            "runtime_evidence": RUNTIME_EVIDENCE_NAME,
        },
        "summary": {
            "total_services": len(services),
            "critical_services": critical_services,
            "supporting_services": supporting_services,
            "reference_services": reference_services,
            "product_services": sum(1 for service in services if service["inference"]["product_scope"] == "algosec_product"),
            "product_dependencies": sum(
                1 for service in services if service["inference"]["product_scope"] == "product_dependency"
            ),
            "services_with_http_routes": sum(1 for service in services if service["observed"]["http_routes"]),
        },
        "services": services,
    }


def build_support_baseline(
    *,
    runtime_evidence: dict[str, Any],
    service_inventory: dict[str, Any],
    target_label: str,
) -> dict[str, Any]:
    service_paths = _build_service_paths(service_inventory)
    support_domains = _build_support_domains(service_inventory, service_paths)
    diagnostic_flows = _build_diagnostic_flows(service_inventory, service_paths, support_domains)
    page_records = _build_page_records(diagnostic_flows, support_domains)
    operator_rows = _build_operator_rows(page_records)
    page_routes = _build_page_routes(page_records)
    decision_playbooks = _build_decision_playbooks(diagnostic_flows)
    priority_candidates = [
        service for service in service_inventory["services"] if service["inference"]["product_scope"] != "platform"
    ] or service_inventory["services"]
    top_services = sorted(
        priority_candidates,
        key=lambda item: (
            -_product_scope_rank(item["inference"]["product_scope"]),
            -item["inference"]["support_importance_score"],
            item["service_name"],
        ),
    )[:5]
    listener_count = 0
    for entry in runtime_evidence["command_results"]:
        if entry["command_id"] == "listening_tcp_ports":
            listener_count = entry.get("stdout_line_count", 0)
            break
    comparison_checkpoints = [
        {
            "checkpoint_id": "compare-runtime-identity",
            "label": "Compare appliance identity first",
            "details": "Confirm the customer host, Rocky 8 baseline, and build markers line up with the trusted lab appliance before deeper diagnosis.",
        },
        {
            "checkpoint_id": "compare-critical-services",
            "label": "Compare critical service state",
            "details": "Verify that the critical services below appear active in the customer environment and match the expected enabled state.",
        },
        {
            "checkpoint_id": "compare-proxy-routes",
            "label": "Compare routed product endpoints",
            "details": "Use Apache proxy config and local port mappings to confirm the expected AlgoSec routes still point at the right local services.",
        },
        {
            "checkpoint_id": "compare-listening-ports",
            "label": "Compare visible listeners",
            "details": "Use the listening-port count and service listener hints as a quick baseline for what should be reachable or bound on the appliance.",
        },
    ]

    return {
        "schema_version": "adf-support-baseline/v1",
        "generated_at": _isoformat_z(),
        "target": {
            "target_label": target_label,
            "hostname": runtime_evidence["observed_facts"]["hostname"],
        },
        "artifact_refs": {
            "runtime_evidence": RUNTIME_EVIDENCE_NAME,
            "service_inventory": SERVICE_INVENTORY_NAME,
            "html_render": SUPPORT_BASELINE_HTML_NAME,
        },
        "observed": {
            "runtime_identity": runtime_evidence["observed_facts"],
            "service_summary": service_inventory["summary"],
            "listening_endpoint_count": listener_count,
            "config_checkpoint_count": sum(len(service["observed"]["config_refs"]) for service in service_inventory["services"]),
            "log_checkpoint_count": sum(len(service["observed"]["log_refs"]) for service in service_inventory["services"]),
        },
        "inferred": {
            "priority_services": [
                {
                    "service_name": service["service_name"],
                    "support_importance_tier": service["inference"]["support_importance_tier"],
                    "support_importance_score": service["inference"]["support_importance_score"],
                    "product_scope": service["inference"]["product_scope"],
                    "role_hint": service["inference"]["role_hint"],
                    "config_refs": service["observed"]["config_refs"][:3],
                    "log_refs": service["observed"]["log_refs"][:2],
                    "http_routes": service["observed"]["http_routes"][:2],
                }
                for service in top_services
            ],
            "support_focus": [
                "Start with AlgoSec product services and direct dependencies before generic Rocky platform services.",
                "Use service state, local port bindings, and proxy-config mismatches before deeper inference when guiding a remote support session.",
            ],
        },
        "service_paths": service_paths,
        "support_domains": support_domains,
        "diagnostic_flows": diagnostic_flows,
        "page_records": page_records,
        "operator_rows": operator_rows,
        "page_routes": page_routes,
        "decision_playbooks": decision_playbooks,
        "symptom_lookup": _build_symptom_lookup(diagnostic_flows),
        "unknowns": runtime_evidence["observation_boundaries"]["unknown"],
        "comparison_checkpoints": comparison_checkpoints,
        "first_response_steps": [
            "Confirm the customer appliance hostname, OS family, and any visible build markers against the lab baseline.",
            "Check whether the top AlgoSec services are active and enabled in the customer environment.",
            "Compare Apache-routed endpoints and local listener ports before moving into deeper service-specific diagnosis.",
            "Use the recorded config and log checkpoints for the top services before inferring broader platform issues.",
        ],
    }


def render_support_baseline_html(support_baseline: dict[str, Any]) -> str:
    observed = support_baseline["observed"]
    runtime_identity = observed["runtime_identity"]
    flow_lookup = {flow["flow_id"]: flow for flow in support_baseline["diagnostic_flows"]}
    symptoms_by_flow: dict[str, list[dict[str, str]]] = {}
    for item in support_baseline["symptom_lookup"]:
        symptoms_by_flow.setdefault(item["suggested_domain_id"], []).append(item)

    def nav_keywords(flow_id: str, symptom_label: str) -> list[str]:
        if flow_id == "ui-and-proxy":
            return ["UI down", "login", "httpd", "80/443", "keycloak", "metro"]
        if flow_id == "core-aff":
            return ["FireFlow", "/FireFlow/api", "1989", "aff-boot", "postgres"]
        if flow_id == "microservice-platform":
            return ["feature fails", "ms-*", "routes", "ms-configuration"]
        if flow_id == "messaging-and-data":
            return ["job stuck", "queue", "activemq", "61616", "postgres"]
        return [symptom_label]

    symptom_lookup_items = "".join(
        (
            f'<a class="symptom-chip" href="#playbook-{html.escape(item["suggested_domain_id"])}">'
            f'<strong class="symptom-title">{html.escape(item["symptom_label"])}</strong>'
            f'<span class="symptom-path">Open: {html.escape(item["suggested_domain_label"])}</span>'
            f'<span class="symptom-start">Start here: {html.escape(item["first_action"])}</span>'
            '<span class="symptom-tags">'
            + "".join(
                f'<span class="symptom-tag">{html.escape(keyword)}</span>'
                for keyword in nav_keywords(item["suggested_domain_id"], item["symptom_label"])
            )
            + "</span>"
            "</a>"
        )
        for item in support_baseline["symptom_lookup"]
    )

    def command_knowledge(command: dict[str, Any]) -> list[str]:
        raw = command["command"]
        label = command["label"]
        if raw.startswith("systemctl status "):
            return [
                "This command asks systemd whether the service is known and running right now.",
                "`Loaded` means the unit file exists on the server. `Active (running)` means the service is up now.",
                "`Main PID` means systemd still sees a live main process for the service.",
            ]
        if raw.startswith("ss -lntp"):
            return [
                "This command shows whether Linux is listening on the expected port.",
                "`LISTEN` means a process has opened the port and is waiting for connections.",
                "If the port is missing, the service may be down, starting slowly, or bound to the wrong place.",
            ]
        if raw == "df -h":
            return [
                "This checks human-readable disk usage for the main filesystems.",
                "Focus on `Use%` and `Avail`, especially for `/` and `/data`.",
                "If disk is full, services can fail to write logs, temp files, or runtime data.",
            ]
        if raw == "df -ih":
            return [
                "This checks inode usage, which is different from normal disk space.",
                "A filesystem can still have free space but fail because it has no free inodes left.",
                "Focus on `IUse%` and whether `IFree` is close to zero.",
            ]
        if raw == "free -h":
            return [
                "This is the quick memory check for the host.",
                "Focus on `available` memory and whether swap is starting to grow heavily.",
                "Low available memory can slow down or crash Java services before the whole server looks down.",
            ]
        if raw.startswith("journalctl -k --since"):
            return [
                "This checks the Linux kernel log for memory-pressure kills.",
                "OOM means Out Of Memory. Linux may kill a process to protect the server.",
                "If you see OOM or `Killed process` lines, memory pressure is likely part of the failure.",
            ]
        if raw.startswith("journalctl -u "):
            return [
                "Recent service logs are often the fastest way to find the real failure clue.",
                "Focus on startup errors, permission errors, heap errors, dependency failures, and repeated retries.",
                "Use this after the status check when the service looks up but still behaves badly.",
            ]
        if label.lower().startswith("check config mapping"):
            return [
                "This checks whether the expected mapping still exists in the service config.",
                "Use it to confirm the route, port, or target value is still what the application expects.",
            ]
        return [
            "This command gives a focused check for the current step.",
            "Use the healthy example below as the main output reference for what good looks like.",
        ]

    def render_command(command: dict[str, Any]) -> str:
        escaped_command = html.escape(command["command"], quote=True)
        knowledge_block = (
            '<div class="signal tip"><strong>Why this check matters</strong>'
            '<ul class="knowledge-list">'
            + "".join(f"<li>{html.escape(item)}</li>" for item in command_knowledge(command))
            + "</ul></div>"
        )
        example_block = (
            '<div class="signal example"><strong>Known-good example</strong>'
            f'<pre class="example-output"><code>{html.escape(command["example_output"])}</code></pre></div>'
            if command.get("example_output")
            else ""
        )
        return (
            '<div class="command-card">'
            + '<div class="command-header">'
            + f'<div class="command-label">{html.escape(command["label"])}</div>'
            + (
                '<button class="copy-button" type="button" '
                f'data-command="{escaped_command}" '
                'aria-label="Copy command">'
                'Copy'
                '</button>'
            )
            + "</div>"
            + f'<pre><code>{html.escape(command["command"])}</code></pre>'
            + f'<div class="signal ok"><strong>Healthy means:</strong> {html.escape(command["expected_signal"])}</div>'
            + knowledge_block
            + example_block
            + "</div>"
        )

    def render_step(step: dict[str, Any]) -> str:
        intro_block = (
            f'<div class="step-panel why"><strong>Step focus</strong><p>{html.escape(step["action"])}</p></div>'
        )
        commands_block = (
            '<div class="step-panel"><strong>Run</strong>'
            + "".join(render_command(command) for command in step["recommended_commands"])
            + "</div>"
            if step["recommended_commands"]
            else ""
        )
        return (
            f'<details class="step-card" id="{html.escape(step["step_id"])}">'
            '<summary class="step-summary">'
            f'<div class="step-number">{html.escape(step["step_label"])}</div>'
            + intro_block
            + "</summary>"
            + '<div class="step-body">'
            + commands_block
            + "</div>"
            + "</details>"
        )

    def render_playbook(playbook: dict[str, Any]) -> str:
        dependency_path = "".join(
            (
                f'<a class="dependency-node" href="#{html.escape(item["step_id"])}">'
                f'<span class="dependency-step">{html.escape(item["step_label"])}</span>'
                f'<strong>{html.escape(item["label"])}</strong>'
                f'<span>{html.escape(item["details"])}</span>'
                "</a>"
            )
            for item in playbook.get("dependency_path", [])
        )
        return (
            f'<section class="playbook" id="playbook-{html.escape(playbook["playbook_id"])}">'
            f'<div class="playbook-header"><div><h2>{html.escape(playbook["label"])}</h2>'
            f'<p class="playbook-focus">{html.escape(playbook["symptom_focus"])}</p></div>'
            f'<a class="top-link" href="#top">Back to top</a></div>'
            + (
                '<div class="dependency-map"><div class="dependency-title">Dependency path</div><div class="dependency-steps">'
                + dependency_path
                + "</div></div>"
                if dependency_path
                else ""
            )
            + "".join(render_step(step) for step in playbook["steps"])
            + "</section>"
        )

    playbook_sections = "".join(render_playbook(playbook) for playbook in support_baseline["decision_playbooks"])
    service_path_items = "".join(
        (
            '<article class="reference-card">'
            f"<h4>{html.escape(path['label'])}</h4>"
            f"<p>{html.escape(path['summary'])}</p>"
            "</article>"
        )
        for path in support_baseline["service_paths"]
    )
    unknown_items = "".join(f"<li>{html.escape(item)}</li>" for item in support_baseline["unknowns"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AlgoSec Support Playbooks</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f2eee5;
      --card: #fffdfa;
      --ink: #13212a;
      --accent: #0f6c7a;
      --accent-soft: #d8eef0;
      --rule: #d8ccbc;
      --ok: #edf8ef;
      --ok-ink: #1e6a33;
      --warn: #fff0db;
      --warn-ink: #8a4b00;
      --fail: #fff1ef;
      --fail-ink: #9d2d20;
      --muted: #5d6970;
      --code: #1f2933;
    }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      background:
        radial-gradient(circle at top right, #d8eef0 0, transparent 28%),
        linear-gradient(180deg, #f6f1e8 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px 20px 56px;
    }}
    section {{
      background: var(--card);
      border: 1px solid var(--rule);
      border-radius: 20px;
      padding: 22px;
      margin-top: 18px;
      box-shadow: 0 16px 40px rgba(19, 33, 42, 0.08);
    }}
    h1, h2, h3, h4 {{
      margin: 0 0 12px;
    }}
    h1 {{
      font-size: 2.2rem;
      line-height: 1.05;
    }}
    h2 {{
      font-size: 1.6rem;
    }}
    .meta {{
      color: var(--muted);
      margin-top: 8px;
    }}
    .hero {{
      display: grid;
      gap: 18px;
    }}
    .hero-grid,
    .playbook-meta,
    .step-grid,
    .jump-grid,
    .symptom-grid,
    .reference-grid {{
      display: grid;
      gap: 14px;
    }}
    .hero-grid,
    .playbook-meta {{
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .jump-grid {{
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }}
    .symptom-grid {{
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }}
    .reference-grid {{
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }}
    .meta-card,
    .jump-card,
    .symptom-chip,
    .reference-card,
    .step-panel,
    .command-card,
    .path-node {{
      border: 1px solid var(--rule);
      border-radius: 16px;
      background: #fff;
      padding: 14px 16px;
    }}
    .jump-card,
    .symptom-chip,
    .top-link {{
      text-decoration: none;
      color: inherit;
    }}
    .jump-card {{
      background: linear-gradient(180deg, #fffdfa 0%, #f4fbfb 100%);
      display: block;
      min-height: 84px;
    }}
    .jump-title {{
      display: block;
      font-weight: bold;
      color: var(--accent);
      margin-bottom: 6px;
    }}
    .jump-subtitle,
    .playbook-focus,
    .command-label,
    .path-node span,
    .symptom-chip span {{
      color: var(--muted);
    }}
    .symptom-chip {{
      display: block;
      background: linear-gradient(180deg, #fffdfa 0%, #f4fbfb 100%);
      min-height: 126px;
    }}
    .symptom-chip strong {{
      display: block;
      margin-bottom: 6px;
    }}
    .symptom-title {{
      color: var(--accent);
    }}
    .symptom-path,
    .symptom-start {{
      display: block;
      margin-bottom: 8px;
    }}
    .symptom-start {{
      color: var(--ink);
      font-weight: 600;
    }}
    .symptom-tags {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }}
    .symptom-tag {{
      display: inline-block;
      border: 1px solid var(--rule);
      border-radius: 999px;
      padding: 4px 8px;
      background: #fff;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    .playbook-header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      margin-bottom: 14px;
    }}
    .dependency-map {{
      display: grid;
      gap: 10px;
      margin: 10px 0 14px;
      padding: 14px;
      border-radius: 16px;
      background: linear-gradient(180deg, #f7fbfb 0%, #eef6f7 100%);
      border: 1px solid #cfe1e4;
    }}
    .dependency-title {{
      font-size: 0.92rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--accent);
    }}
    .dependency-steps {{
      display: grid;
      gap: 10px;
    }}
    .dependency-node {{
      display: grid;
      gap: 4px;
      padding: 12px 14px;
      border-radius: 12px;
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid #d7e6e8;
      position: relative;
      color: inherit;
      text-decoration: none;
    }}
    .dependency-node:not(:last-child)::after {{
      content: "↓";
      position: absolute;
      left: 50%;
      bottom: -18px;
      transform: translateX(-50%);
      color: var(--accent);
      font-size: 1rem;
      font-weight: 700;
    }}
    .dependency-step {{
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .dependency-node strong {{
      font-size: 1rem;
    }}
    .dependency-node span:last-child {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .top-link {{
      color: var(--accent);
      font-weight: bold;
      white-space: nowrap;
    }}
    .step-card {{
      border-top: 1px solid var(--rule);
      padding-top: 18px;
      margin-top: 18px;
    }}
    .step-summary {{
      display: flex;
      align-items: flex-start;
      gap: 12px;
      cursor: pointer;
      list-style: none;
    }}
    .step-summary::-webkit-details-marker {{
      display: none;
    }}
    .step-summary::marker {{
      display: none;
    }}
    .step-summary::after {{
      content: "Expand";
      margin-left: auto;
      color: var(--accent);
      font-weight: 700;
      white-space: nowrap;
      padding-top: 6px;
    }}
    .step-card[open] > .step-summary::after {{
      content: "Collapse";
    }}
    .step-number {{
      display: inline-block;
      background: var(--accent);
      color: white;
      font-weight: bold;
      border-radius: 999px;
      padding: 4px 10px;
      margin-top: 4px;
      flex: 0 0 auto;
    }}
    .step-grid {{
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      margin: 14px 0;
    }}
    .pass {{
      background: var(--ok);
      color: var(--ok-ink);
    }}
    .fail {{
      background: var(--fail);
      color: var(--fail-ink);
    }}
    .next,
    .evidence {{
      background: #f7f3ea;
    }}
    .why {{
      background: #eef6f1;
      color: #214a33;
      margin-bottom: 0;
      flex: 1 1 auto;
    }}
    .step-body {{
      margin-top: 12px;
    }}
    .command-card {{
      margin-top: 12px;
      background: #fbfcfe;
    }}
    .command-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }}
    .copy-button {{
      border: 1px solid var(--rule);
      background: #fffdfa;
      color: var(--accent);
      border-radius: 999px;
      padding: 6px 12px;
      font-weight: 700;
      cursor: pointer;
      transition: background 120ms ease, color 120ms ease, border-color 120ms ease;
    }}
    .copy-button:hover {{
      background: var(--accent-soft);
      border-color: #b7dadd;
    }}
    .copy-button.copied {{
      background: var(--ok);
      color: var(--ok-ink);
      border-color: #b9dfc2;
    }}
    .knowledge-list {{
      margin: 8px 0 0;
      padding-left: 18px;
    }}
    .knowledge-list li {{
      margin: 6px 0;
      line-height: 1.4;
    }}
    pre {{
      background: var(--code);
      color: #f4f7fb;
      padding: 12px 14px;
      border-radius: 12px;
      overflow-x: auto;
      margin: 10px 0;
    }}
    code {{
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 0.95rem;
    }}
    .signal {{
      border-radius: 12px;
      padding: 10px 12px;
      margin-top: 8px;
    }}
    .signal.ok {{
      background: var(--ok);
      color: var(--ok-ink);
    }}
    .signal.tip {{
      background: var(--accent-soft);
      color: #184c55;
    }}
    .signal.example {{
      background: #eef4fb;
      color: #1a3550;
    }}
    .signal.warn {{
      background: var(--warn);
      color: var(--warn-ink);
    }}
    .example-output {{
      margin-top: 10px;
      background: #101820;
    }}
    ul {{
      margin: 0;
      padding-left: 20px;
    }}
    p {{
      line-height: 1.45;
    }}
    details {{
      margin-top: 18px;
    }}
    summary {{
      cursor: pointer;
      font-weight: bold;
      color: var(--accent);
    }}
  </style>
</head>
<body>
  <main id="top">
    <section class="hero">
      <h1>AlgoSec Diagnostic Playbooks</h1>
      <p class="meta">Target: {html.escape(support_baseline['target']['target_label'])} | Host: {html.escape(support_baseline['target']['hostname'])} | Generated: {html.escape(support_baseline['generated_at'])}</p>
      <p>Use this page to get to the right playbook quickly, run the next command, validate the output, and isolate the likely failure point.</p>
      <div class="hero-grid">
        <div class="meta-card">
          <strong>System baseline</strong>
          <p>OS: {html.escape(runtime_identity.get('os_release', {}).get('PRETTY_NAME', 'unknown'))}</p>
          <p>Kernel: {html.escape(runtime_identity.get('kernel_release', 'unknown'))}</p>
        </div>
        <div class="meta-card">
          <strong>Runtime footprint</strong>
          <p>Services observed: {observed['service_summary']['total_services']}</p>
          <p>Product services: {observed['service_summary']['product_services']}</p>
        </div>
        <div class="meta-card">
          <strong>Support focus</strong>
          <p>Critical services: {observed['service_summary']['critical_services']}</p>
          <p>Listening endpoints: {observed['listening_endpoint_count']}</p>
        </div>
      </div>
    </section>
    <section>
      <h2>Jump To The Right Playbook</h2>
      <p class="step-order-note">Scan the symptom, read the start clue, and open the playbook that best matches what the customer is reporting.</p>
      <div class="symptom-grid">{symptom_lookup_items}</div>
    </section>
    {playbook_sections}
    <section>
      <h2>Reference</h2>
      <div class="reference-grid">{service_path_items}</div>
      <details>
        <summary>Known Unknowns</summary>
        <ul>{unknown_items}</ul>
      </details>
    </section>
  </main>
  <script>
    (function () {{
      async function copyCommand(text) {{
        if (navigator.clipboard && navigator.clipboard.writeText) {{
          await navigator.clipboard.writeText(text);
          return;
        }}
        const fallback = document.createElement('textarea');
        fallback.value = text;
        fallback.setAttribute('readonly', '');
        fallback.style.position = 'absolute';
        fallback.style.left = '-9999px';
        document.body.appendChild(fallback);
        fallback.select();
        document.execCommand('copy');
        document.body.removeChild(fallback);
      }}

      document.querySelectorAll('.copy-button').forEach((button) => {{
        const defaultLabel = button.textContent;
        button.addEventListener('click', async () => {{
          try {{
            await copyCommand(button.dataset.command || '');
            button.textContent = 'Copied';
            button.classList.add('copied');
            setTimeout(() => {{
              button.textContent = defaultLabel;
              button.classList.remove('copied');
            }}, 1400);
          }} catch (error) {{
            button.textContent = 'Copy failed';
            setTimeout(() => {{
              button.textContent = defaultLabel;
            }}, 1400);
          }}
        }});
      }});

      function openHashTarget() {{
        const rawHash = window.location.hash;
        if (!rawHash || rawHash.length < 2) {{
          return;
        }}
        const target = document.getElementById(decodeURIComponent(rawHash.slice(1)));
        if (!target) {{
          return;
        }}
        const step = target.matches('details.step-card') ? target : target.closest('details.step-card');
        if (step) {{
          step.open = true;
        }}
      }}

      window.addEventListener('hashchange', openHashTarget);
      openHashTarget();
    }})();
  </script>
</body>
</html>"""


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def _load_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    if not path.exists():
        return {}
    return _parse_os_release_lines(path.read_text(encoding="utf-8").splitlines())


def _parse_os_release_lines(lines: list[str]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for line in lines:
        if not line or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        payload[key] = raw_value.strip().strip('"')
    return payload


def _run_command(*, command_id: str, argv: list[str], max_preview_lines: int = 60) -> dict[str, Any]:
    binary = shutil.which(argv[0])
    observed_at = _isoformat_z()
    if binary is None:
        return {
            "command_id": command_id,
            "argv": argv,
            "status": "unavailable",
            "observed_at": observed_at,
            "reason": f"{argv[0]} is not installed",
            "stdout_preview": [],
            "stderr_preview": [],
        }

    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
    stdout_lines = completed.stdout.splitlines()
    stderr_lines = completed.stderr.splitlines()
    return {
        "command_id": command_id,
        "argv": argv,
        "status": "completed" if completed.returncode == 0 else "nonzero_exit",
        "observed_at": observed_at,
        "exit_code": completed.returncode,
        "stdout_line_count": len(stdout_lines),
        "stderr_line_count": len(stderr_lines),
        "stdout_preview": stdout_lines[:max_preview_lines],
        "stderr_preview": stderr_lines[:max_preview_lines],
    }


def _run_target_command(
    *,
    project_root: Path,
    profile_path: str | Path,
    command_id: str,
    command: str,
    max_preview_lines: int = 60,
) -> dict[str, Any]:
    observed_at = _isoformat_z()
    result = target_shell_capture(
        project_root=project_root,
        profile_path=profile_path,
        command=command,
        preview_line_limit=max_preview_lines,
    )
    command_result = result.get("command_result", {})
    attempts = command_result.get("attempts", [])
    last_attempt = attempts[-1] if attempts else {}
    stdout_lines = list(command_result.get("stdout_lines", []))[:max_preview_lines]
    stderr_lines = list(command_result.get("stderr_lines", []))[:max_preview_lines]
    attempt_status = str(last_attempt.get("status", ""))
    if result.get("status") == "pass":
        status = "completed"
    elif attempt_status in {"nonzero_exit", "timeout"}:
        status = attempt_status
    else:
        status = "unavailable"
    payload: dict[str, Any] = {
        "command_id": command_id,
        "argv": ["target-shell-command", command],
        "status": status,
        "observed_at": observed_at,
        "stdout_line_count": len(stdout_lines),
        "stderr_line_count": len(stderr_lines),
        "stdout_preview": stdout_lines,
        "stderr_preview": stderr_lines,
        "target_label": result.get("target_label"),
    }
    if "exit_code" in last_attempt:
        payload["exit_code"] = last_attempt.get("exit_code")
    reason = command_result.get("reason")
    if isinstance(reason, str) and reason:
        payload["reason"] = reason
    return payload


def _load_target_os_release(*, project_root: Path, profile_path: str | Path) -> dict[str, str]:
    result = _run_target_command(
        project_root=project_root,
        profile_path=profile_path,
        command_id="target_os_release",
        command="cat /etc/os-release",
        max_preview_lines=80,
    )
    if result["status"] != "completed":
        return {}
    return _parse_os_release_lines(result.get("stdout_preview", []))


def _load_target_hostname(*, project_root: Path, profile_path: str | Path) -> str:
    result = _run_target_command(
        project_root=project_root,
        profile_path=profile_path,
        command_id="target_hostname",
        command="hostname -f || hostname",
        max_preview_lines=10,
    )
    if result["status"] != "completed":
        return "target-host-unavailable"
    lines = result.get("stdout_preview", [])
    return lines[0].strip() if lines else "target-host-unavailable"


def _load_target_kernel_release(*, project_root: Path, profile_path: str | Path) -> str:
    result = _run_target_command(
        project_root=project_root,
        profile_path=profile_path,
        command_id="target_kernel_release",
        command="uname -r",
        max_preview_lines=10,
    )
    if result["status"] != "completed":
        return "unknown"
    lines = result.get("stdout_preview", [])
    return lines[0].strip() if lines else "unknown"


def _services_from_runtime_results(
    results: dict[str, dict[str, Any]],
    *,
    collect_local_checkpoints: bool = True,
) -> list[dict[str, Any]]:
    unit_rows = _parse_systemd_units(results.get("systemd_units", {}).get("stdout_preview", []))
    unit_file_rows = _parse_unit_files(results.get("systemd_unit_files", {}).get("stdout_preview", []))
    listeners = _parse_listeners(results.get("listening_tcp_ports", {}).get("stdout_preview", []))
    process_rows = _parse_processes(results.get("process_inventory", {}).get("stdout_preview", []))

    services: dict[str, dict[str, Any]] = {}
    for unit_name, details in unit_rows.items():
        services[unit_name] = {
            "service_name": unit_name,
            "observed": {
                **details,
                "unit_file_state": unit_file_rows.get(unit_name),
                "unit_file_path": None,
                "control_refs": [],
                "config_refs": [],
                "dependency_refs": [],
                "log_refs": [],
                "http_routes": [],
                "listeners": [],
                "process_matches": [],
                "evidence_refs": ["systemd_units"],
            },
        }

    for unit_name, state in unit_file_rows.items():
        service = services.setdefault(
            unit_name,
            {
                "service_name": unit_name,
                "observed": {
                    "load_state": "unknown",
                    "active_state": "unknown",
                    "sub_state": "unknown",
                    "description": unit_name,
                    "unit_file_state": None,
                    "unit_file_path": None,
                    "control_refs": [],
                    "config_refs": [],
                    "dependency_refs": [],
                    "log_refs": [],
                    "http_routes": [],
                    "listeners": [],
                    "process_matches": [],
                    "evidence_refs": [],
                },
            },
        )
        service["observed"]["unit_file_state"] = state
        service["observed"]["evidence_refs"].append("systemd_unit_files")

    base_name_index = {unit_name.removesuffix(".service"): unit_name for unit_name in services}
    pid_to_service: dict[str, str] = {}
    process_name_to_service: dict[str, str] = {}
    for process in process_rows:
        comm = process["comm"]
        service_name = base_name_index.get(comm)
        if service_name is None:
            for base_name, mapped_service in base_name_index.items():
                if base_name and base_name in process["args"]:
                    service_name = mapped_service
                    break
        if service_name is None:
            continue
        services[service_name]["observed"]["process_matches"].append(process)
        services[service_name]["observed"]["evidence_refs"].append("process_inventory")
        pid_to_service[process["pid"]] = service_name
        process_name_to_service[process["comm"]] = service_name

    assigned_listener_keys: set[tuple[str, str, str]] = set()
    for listener in listeners:
        service_name = None
        if listener.get("pid"):
            service_name = pid_to_service.get(listener["pid"])
        if service_name is None and listener.get("process_name"):
            service_name = process_name_to_service.get(listener["process_name"])
        if service_name is None and listener.get("process_name"):
            service_name = base_name_index.get(listener["process_name"])
        if service_name is None:
            service_name = base_name_index.get(listener["local_host"])
        if service_name is None:
            continue
        listener_key = (listener["local_address"], listener.get("pid", ""), listener.get("process_name", ""))
        if listener_key in assigned_listener_keys:
            continue
        services[service_name]["observed"]["listeners"].append(listener)
        services[service_name]["observed"]["evidence_refs"].append("listening_tcp_ports")
        assigned_listener_keys.add(listener_key)

    if not services:
        fallback_services = {}
        for process in process_rows:
            fallback_services.setdefault(
                process["comm"],
                {
                    "service_name": process["comm"],
                    "observed": {
                        "load_state": "unknown",
                        "active_state": "observed_process_only",
                        "sub_state": "unknown",
                        "description": process["comm"],
                        "unit_file_state": None,
                        "unit_file_path": None,
                        "control_refs": [],
                        "config_refs": [],
                        "dependency_refs": [],
                        "log_refs": [],
                        "http_routes": [],
                        "listeners": [],
                        "process_matches": [process],
                        "evidence_refs": ["process_inventory"],
                    },
                },
            )
        services = fallback_services

    final_services = []
    for service_name in sorted(services):
        service = services[service_name]
        if collect_local_checkpoints:
            service["observed"].update(_collect_service_checkpoints(service_name))
        service["observed"]["evidence_refs"] = sorted(set(service["observed"]["evidence_refs"]))
        service["inference"] = _score_service(service)
        service["unknowns"] = [
            "No direct dependency graph collection in this first slice.",
        ]
        if collect_local_checkpoints and service["observed"]["config_refs"]:
            service["unknowns"] = [
                "Config checkpoints are first-pass only and may not capture every product override or generated file.",
                "No direct dependency graph collection in this first slice.",
            ]
        if not collect_local_checkpoints:
            service["unknowns"] = [
                "This target-profile slice has runtime state, listeners, and processes, but it does not yet collect remote unit files, proxy configs, or log checkpoints directly.",
                "No direct dependency graph collection in this first slice.",
            ]
        final_services.append(service)
    return final_services


def _parse_systemd_units(lines: list[str]) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in lines:
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        unit_name = parts[0]
        if not unit_name.endswith(".service"):
            continue
        rows[unit_name] = dict(zip(SYSTEMD_UNIT_KEYS, parts[1:], strict=True))
    return rows


def _parse_unit_files(lines: list[str]) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in lines:
        parts = line.split(None, 2)
        if len(parts) < 2 or not parts[0].endswith(".service"):
            continue
        if parts[0].endswith("@.service") or parts[1] == "alias":
            continue
        rows[parts[0]] = parts[1]
    return rows


def _parse_listeners(lines: list[str]) -> list[dict[str, str]]:
    listeners = []
    for line in lines:
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[3]
        host, port = _split_host_port(local)
        pid = ""
        process_name = ""
        match = LISTENER_PROCESS_RE.search(line)
        if match:
            pid = match.group("pid")
            process_name = match.group("process")
        listeners.append(
            {
                "local_address": local,
                "local_host": host,
                "port": port,
                "pid": pid,
                "process_name": process_name,
            }
        )
    return listeners


def _split_host_port(value: str) -> tuple[str, str]:
    candidate = value.strip("[]")
    if ":" not in candidate:
        return candidate, ""
    host, port = candidate.rsplit(":", 1)
    return host, port


def _first_or(items: list[Any] | tuple[Any, ...], default: Any) -> Any:
    return items[0] if items else default


def _parse_processes(lines: list[str]) -> list[dict[str, str]]:
    rows = []
    for line in lines:
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        rows.append(
            {
                "pid": parts[0],
                "ppid": parts[1],
                "user": parts[2],
                "comm": parts[3],
                "args": parts[4],
            }
        )
    return rows


def _score_service(service: dict[str, Any]) -> dict[str, Any]:
    observed = service["observed"]
    score = 0
    reasons = []
    product_scope = _product_scope(service)
    if observed["active_state"] == "active":
        score += 3
        reasons.append("service is active")
    if observed["sub_state"] == "running":
        score += 2
        reasons.append("service is running")
    if observed.get("unit_file_state") in {"enabled", "enabled-runtime", "static"}:
        score += 1
        reasons.append("service is enabled or static")
    if observed["listeners"]:
        score += 2
        reasons.append("service has visible TCP listeners")
    if observed["process_matches"]:
        score += 1
        reasons.append("service has a matched running process")
    if product_scope == "algosec_product":
        score += 5
        reasons.append("service matches the AlgoSec product layer")
    elif product_scope == "product_dependency":
        score += 3
        reasons.append("service is a direct dependency used by the AlgoSec product layer")
    if observed["config_refs"] or observed["http_routes"]:
        score += 1
        reasons.append("service has product-specific config or route checkpoints")
    if observed["log_refs"]:
        score += 1
        reasons.append("service has log checkpoints")

    role_hint = "application or support service"
    service_name = service["service_name"].lower()
    for candidate_role, tokens in SERVICE_ROLE_HINTS.items():
        if any(token in service_name for token in tokens):
            role_hint = candidate_role
            break

    if score >= 8:
        tier = "critical"
    elif score >= 4:
        tier = "supporting"
    else:
        tier = "reference"

    return {
        "product_scope": product_scope,
        "support_importance_score": score,
        "support_importance_tier": tier,
        "role_hint": role_hint,
        "reasoning": reasons or ["service has limited directly observed support signals in this first slice"],
    }


def _collect_service_checkpoints(service_name: str) -> dict[str, Any]:
    unit_file_path = _unit_file_path_for_service(service_name)
    control_refs: list[str] = []
    config_refs: list[str] = []
    dependency_refs: list[str] = []
    log_refs: list[str] = []
    http_routes = _http_routes_for_service(service_name)

    if unit_file_path is not None:
        control_refs.append(str(unit_file_path))
        unit_text = unit_file_path.read_text(encoding="utf-8")
        dependency_refs.extend(_extract_unit_dependencies(unit_text))
        for path_text in _extract_path_tokens(unit_text):
            if path_text == str(unit_file_path):
                continue
            if _is_log_path(path_text):
                log_refs.append(path_text)
            elif _is_config_path(path_text):
                config_refs.append(path_text)
            else:
                control_refs.append(path_text)

    for route in http_routes:
        config_refs.append(route["config_path"])

    for candidate in _default_log_checkpoints(service_name):
        if Path(candidate).exists():
            log_refs.append(candidate)

    return {
        "unit_file_path": str(unit_file_path) if unit_file_path is not None else None,
        "control_refs": sorted(set(control_refs)),
        "config_refs": sorted(set(config_refs)),
        "dependency_refs": sorted(set(dependency_refs)),
        "log_refs": sorted(set(log_refs)),
        "http_routes": http_routes,
    }


def _unit_file_path_for_service(service_name: str) -> Path | None:
    for root in SYSTEMD_UNIT_ROOTS:
        candidate = root / service_name
        if candidate.exists():
            return candidate
    return None


def _http_routes_for_service(service_name: str) -> list[dict[str, str]]:
    base_name = service_name.removesuffix(".service")
    candidate_names = []
    if base_name.startswith("ms-"):
        candidate_names.append(f"algosec-ms.{base_name}.conf")
    elif base_name == "keycloak":
        candidate_names.append("keycloak.conf")
    elif base_name.startswith("aff-") or base_name == "aff-boot":
        candidate_names.append("aff.conf")
    elif base_name.startswith("algosec-"):
        candidate_names.append(f"{base_name}.conf")

    routes: list[dict[str, str]] = []
    for candidate_name in candidate_names:
        path = HTTPD_CONF_ROOT / candidate_name
        if not path.exists():
            continue
        config_text = path.read_text(encoding="utf-8")
        proxy_targets = sorted(
            set(re.findall(r"http://(?:127\.0\.0\.1|localhost):(\d+)", config_text))
        )
        locations = re.findall(r"<Location\s+([^>]+)>", config_text)
        routes.append(
            {
                "config_path": str(path),
                "locations": ", ".join(locations[:3]) if locations else "",
                "target_ports": ", ".join(proxy_targets),
            }
        )
    return routes


def _default_log_checkpoints(service_name: str) -> list[str]:
    base_name = service_name.removesuffix(".service")
    candidates = []
    if base_name.startswith("ms-") or base_name.startswith("algosec-") or base_name.startswith("aff-"):
        candidates.extend(
            [
                "/home/afa/algosec",
                "/data/log/algosec_hadr",
                "/var/log/httpd",
            ]
        )
    if base_name == "activemq":
        candidates.extend(["/opt/apache-activemq-6.1.7/data", "/opt/activemq/data"])
    if base_name == "postgresql":
        candidates.append("/var/lib/pgsql/15/data")
    if base_name in {"elasticsearch", "logstash", "kibana"}:
        candidates.append("/data/log/logstash")
    if base_name == "httpd":
        candidates.append("/var/log/httpd")
    return candidates


def _extract_unit_dependencies(text: str) -> list[str]:
    dependencies: list[str] = []
    for match in UNIT_DEPENDENCY_RE.finditer(text):
        for token in match.group(1).split():
            token = token.strip()
            if not token or not token.endswith(".service"):
                continue
            dependencies.append(token)
    return dependencies


def _extract_path_tokens(text: str) -> list[str]:
    return sorted(set(match.group(1).rstrip(")") for match in PATH_TOKEN_RE.finditer(text)))


def _is_config_path(path_text: str) -> bool:
    return (
        path_text.startswith("/etc/")
        or any(path_text.endswith(suffix) for suffix in (".conf", ".properties", ".yaml", ".yml", ".xml", ".cfg"))
        or "/conf/" in path_text
        or "/config/" in path_text
    )


def _is_log_path(path_text: str) -> bool:
    return "/log" in path_text or path_text.endswith(".log")


def _product_scope(service: dict[str, Any]) -> str:
    service_name = service["service_name"].lower()
    observed = service["observed"]
    if service_name.startswith(PRODUCT_SERVICE_PREFIXES) or service_name in PRODUCT_SERVICE_NAMES:
        if service_name.startswith(("ms-", "algosec-", "aff-")):
            return "algosec_product"
        if service_name in {"activemq.service", "postgresql.service", "httpd.service", "keycloak.service"}:
            return "product_dependency"
        return "platform"
    all_refs = [
        *observed.get("control_refs", []),
        *observed.get("config_refs", []),
        *observed.get("log_refs", []),
        *(process["args"] for process in observed.get("process_matches", [])),
    ]
    if any(hint in ref for ref in all_refs for hint in PRODUCT_PATH_HINTS):
        return "algosec_product"
    return "platform"


def _product_scope_rank(scope: str) -> int:
    return {
        "algosec_product": 3,
        "product_dependency": 2,
        "platform": 1,
    }.get(scope, 0)


def _build_service_paths(service_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    services = service_inventory["services"]
    service_index = {service["service_name"]: service for service in services}
    path_candidates = [
        service
        for service in services
        if service["inference"]["product_scope"] == "algosec_product"
        and service["inference"]["support_importance_tier"] == "critical"
    ]
    path_candidates.sort(
        key=lambda service: (
            -service["inference"]["support_importance_score"],
            service["service_name"],
        )
    )

    service_paths = []
    for service in path_candidates[:5]:
        dependencies = []
        for dependency_name in service["observed"].get("dependency_refs", []):
            dependency = service_index.get(dependency_name)
            if dependency is None:
                continue
            dependencies.append(
                {
                    "service_name": dependency_name,
                    "role_hint": dependency["inference"]["role_hint"],
                    "tier": dependency["inference"]["support_importance_tier"],
                }
            )

        route_bits = []
        for route in service["observed"]["http_routes"][:2]:
            location = route["locations"] or service["service_name"].removesuffix(".service")
            port = route["target_ports"] or "unknown local port"
            route_bits.append(f"{location} -> {port}")
        listener_ports = sorted({listener["port"] for listener in service["observed"]["listeners"] if listener["port"]})
        if not route_bits and listener_ports:
            route_bits.append(f"local listener ports {', '.join(listener_ports)}")

        dependency_names = [dependency["service_name"] for dependency in dependencies]
        summary_parts = []
        if route_bits:
            summary_parts.append(f"route {'; '.join(route_bits)}")
        if dependency_names:
            summary_parts.append(f"depends on {', '.join(dependency_names)}")
        if service["observed"]["config_refs"]:
            summary_parts.append(f"config checkpoints {', '.join(service['observed']['config_refs'][:2])}")
        summary = "; ".join(summary_parts) if summary_parts else "No direct path summary captured yet."

        service_paths.append(
            {
                "path_id": service["service_name"].removesuffix(".service"),
                "label": service["service_name"],
                "entry_service": service["service_name"],
                "entry_role_hint": service["inference"]["role_hint"],
                "dependency_services": dependencies,
                "route_checkpoints": service["observed"]["http_routes"][:2],
                "listener_ports": listener_ports[:4],
                "config_checkpoints": service["observed"]["config_refs"][:3],
                "log_checkpoints": service["observed"]["log_refs"][:2],
                "summary": summary,
            }
        )
    return service_paths


def _build_support_domains(service_inventory: dict[str, Any], service_paths: list[dict[str, Any]]) -> list[dict[str, Any]]:
    service_index = {service["service_name"]: service for service in service_inventory["services"]}
    domains = [
        {
            "domain_id": "ui-and-proxy",
            "label": "ASMS UI is down",
            "summary": "",
            "service_paths": [],
            "supporting_services": [],
        },
        {
            "domain_id": "core-aff",
            "label": "FireFlow Backend",
            "summary": "",
            "service_paths": [],
            "supporting_services": [],
        },
        {
            "domain_id": "microservice-platform",
            "label": "Microservice Platform",
            "summary": "",
            "service_paths": [],
            "supporting_services": [],
        },
        {
            "domain_id": "messaging-and-data",
            "label": "Messaging and Data",
            "summary": "",
            "service_paths": [],
            "supporting_services": [],
        },
    ]
    domain_index = {domain["domain_id"]: domain for domain in domains}

    for path in service_paths:
        domain_id = _domain_for_service(path["entry_service"])
        domain_index[domain_id]["service_paths"].append(path["path_id"])
        for dependency in path["dependency_services"]:
            domain_index[domain_id]["supporting_services"].append(dependency["service_name"])

    for service_name, service in service_index.items():
        if service["inference"]["product_scope"] == "platform":
            continue
        domain_id = _domain_for_service(service_name)
        domain_index[domain_id]["supporting_services"].append(service_name)

    # The appliance UI path is anchored in Apache and Keycloak, but it also
    # depends on the legacy Metro/API chain behind the login flow.
    if "ms-metro.service" in service_index:
        domain_index["ui-and-proxy"]["supporting_services"].append("ms-metro.service")

    finalized = []
    for domain in domains:
        path_ids = sorted(set(domain["service_paths"]))
        supporting_services = sorted(set(domain["supporting_services"]))
        if not path_ids and not supporting_services:
            continue
        summary_parts = []
        if path_ids:
            summary_parts.append(f"paths: {', '.join(path_ids[:4])}")
        if supporting_services:
            summary_parts.append(f"services: {', '.join(supporting_services[:6])}")
        finalized.append(
            {
                "domain_id": domain["domain_id"],
                "label": domain["label"],
                "path_ids": path_ids,
                "supporting_services": supporting_services,
                "first_checks": _domain_first_checks(
                    domain_id=domain["domain_id"],
                    path_ids=path_ids,
                    supporting_services=supporting_services,
                    service_index=service_index,
                ),
                "summary": "; ".join(summary_parts),
            }
        )
    return finalized


def _domain_for_service(service_name: str) -> str:
    base_name = service_name.removesuffix(".service")
    if base_name in {"httpd", "keycloak"}:
        return "ui-and-proxy"
    if base_name in {"activemq", "postgresql", "elasticsearch", "kibana", "logstash"}:
        return "messaging-and-data"
    if base_name.startswith("aff-") or base_name.startswith("algosec-dfs"):
        return "core-aff"
    if base_name.startswith("ms-") or base_name == "algosec-ms":
        return "microservice-platform"
    return "microservice-platform"


def _domain_first_checks(
    *,
    domain_id: str,
    path_ids: list[str],
    supporting_services: list[str],
    service_index: dict[str, dict[str, Any]],
) -> list[str]:
    checks: list[str] = []
    if domain_id == "ui-and-proxy":
        checks.append("Check whether the host is under storage, inode, memory, or CPU pressure before blaming the ASMS UI path.")
        checks.append("Confirm Apache/HTTPD can answer local UI traffic and still route toward the auth and app branches.")
        checks.append("If the login journey gets past the legacy setup hop, confirm BusinessFlow can still answer its local health and login handoff paths before treating the failure as Keycloak-only.")
        if "keycloak.service" in supporting_services:
            checks.append("Confirm Keycloak can still do useful auth work, not only that keycloak.service is active.")
        if "ms-metro.service" in supporting_services:
            checks.append("Confirm ms-metro can still do useful app work, not only that port 8080 is open.")
        checks.append("Use FireFlow auth checks as later customer-visible signals in the same journey, especially when the browser reaches `/afa/php/home.php` and then stalls.")
        checks.append("Use recent Apache, Keycloak, and Metro clues only after the host and edge checks narrow the first stop point.")
        return checks

    if domain_id == "core-aff":
        checks.append("Confirm aff-boot.service is active and /FireFlow/api or /aff/api still proxy to localhost:1989.")
        if "postgresql.service" in supporting_services:
            checks.append("Confirm postgresql.service is active before treating FireFlow symptoms as application-only.")
        return checks

    if domain_id == "microservice-platform":
        checks.append("Confirm algosec-ms.service completed successfully and the top ms-* services are active.")
        interesting_paths = ", ".join(path_ids[:3])
        if interesting_paths:
            checks.append(f"Compare the routed microservice paths first: {interesting_paths}.")
        if "ms-configuration.service" in supporting_services:
            checks.append("Check ms-configuration.service early because several other services depend on it.")
        return checks

    if domain_id == "messaging-and-data":
        if "activemq.service" in supporting_services:
            checks.append("Confirm activemq.service is active and listener 61616 is present.")
        if "postgresql.service" in supporting_services:
            checks.append("Confirm postgresql.service is active and local database access is healthy.")
        return checks

    return checks


def _build_diagnostic_flows(
    service_inventory: dict[str, Any],
    service_paths: list[dict[str, Any]],
    support_domains: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    service_index = {service["service_name"]: service for service in service_inventory["services"]}
    path_index = {path["path_id"]: path for path in service_paths}
    flows = []
    for domain in support_domains:
        domain_paths = [path_index[path_id] for path_id in domain["path_ids"] if path_id in path_index]
        likely_services = [path["entry_service"] for path in domain_paths]
        if not likely_services:
            likely_services = domain["supporting_services"][:3]

        check_sequence = list(domain["first_checks"])
        if domain_paths:
            for path in domain_paths[:2]:
                route_targets = [
                    route["target_ports"] or route["locations"] or path["label"]
                    for route in path["route_checkpoints"][:1]
                ]
                if route_targets:
                    check_sequence.append(f"Confirm route or local target {route_targets[0]} for {path['label']}.")

        next_dependency_focus = ""
        dependency_names = []
        for path in domain_paths:
            for dependency in path["dependency_services"]:
                dependency_names.append(dependency["service_name"])
        dependency_names = sorted(set(dependency_names))
        if dependency_names:
            next_dependency_focus = f"Inspect dependency services next: {', '.join(dependency_names[:4])}."

        page_metadata = _flow_page_metadata(domain["domain_id"])
        operator_row_id = f"{page_metadata['page_id']}-operator-row"

        flows.append(
            {
                "flow_id": domain["domain_id"],
                "label": domain["label"],
                "symptom_focus": _domain_symptom_focus(domain["domain_id"]),
                "page_metadata": page_metadata,
                "page_type": page_metadata["page_type"],
                "page_role": page_metadata["page_role"],
                "page_id": page_metadata["page_id"],
                "handoff_target": page_metadata["handoff_target"],
                "handoff_target_type": page_metadata["handoff_target_type"],
                "route_kind": page_metadata["route_kind"],
                "entry_question": page_metadata["entry_question"],
                "operator_row_id": operator_row_id,
                "routing": {
                    "from_page_id": page_metadata["page_id"],
                    "from_page_type": page_metadata["page_type"],
                    "to_page_id": page_metadata["handoff_target"],
                    "to_page_type": page_metadata["handoff_target_type"],
                    "route_kind": page_metadata["route_kind"],
                },
                "customer_symptom": domain["label"] if page_metadata["page_type"] == "symptom_entry" else "",
                "use_this_when": _domain_symptom_focus(domain["domain_id"])
                if page_metadata["page_type"] == "boundary_confirmation"
                else "",
                "service_name": _boundary_service_name_for_flow(
                    {
                        "flow_id": domain["domain_id"],
                        "label": domain["label"],
                        "likely_failing_services": likely_services,
                    }
                ),
                "likely_failing_services": likely_services,
                "path_checkpoints": [
                    {
                        "path_id": path["path_id"],
                        "label": path["label"],
                        "entry_service": path["entry_service"],
                        "route_checkpoints": path["route_checkpoints"],
                        "listener_ports": path["listener_ports"],
                        "config_checkpoints": path["config_checkpoints"],
                        "log_checkpoints": path["log_checkpoints"],
                    }
                    for path in domain_paths[:3]
                ],
                "supporting_service_details": _supporting_service_details(
                    supporting_services=domain["supporting_services"],
                    service_index=service_index,
                ),
                "check_sequence": check_sequence,
                "evidence_to_collect_next": _flow_evidence_to_collect_next(
                    domain_id=domain["domain_id"],
                    domain_paths=domain_paths,
                    domain=domain,
                ),
                "next_dependency_focus": next_dependency_focus,
                "supporting_evidence": _domain_supporting_evidence(
                    domain=domain,
                    domain_paths=domain_paths,
                    service_index=service_index,
                ),
            }
        )
    return flows


def _domain_symptom_focus(domain_id: str) -> str:
    return {
        "ui-and-proxy": "Use this when the ASMS UI is down and the engineer is checking the appliance from SSH.",
        "core-aff": "Use this when a FireFlow action fails or FireFlow returns an error.",
        "microservice-platform": "Use this when one product feature fails after login and the UI itself is still up.",
        "messaging-and-data": "Use this when jobs stop, queues back up, or data actions fail.",
    }.get(domain_id, "Use this when the problem matches this area.")


def _supporting_service_details(
    *,
    supporting_services: list[str],
    service_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    details: list[dict[str, Any]] = []
    for service_name in supporting_services[:8]:
        service = service_index.get(service_name)
        if service is None:
            continue
        details.append(
            {
                "service_name": service_name,
                "listener_ports": [
                    listener["port"]
                    for listener in service["observed"]["listeners"]
                    if listener.get("port")
                ][:4],
                "config_refs": service["observed"]["config_refs"][:3],
                "log_refs": service["observed"]["log_refs"][:2],
            }
        )
    return details


def _domain_supporting_evidence(
    *,
    domain: dict[str, Any],
    domain_paths: list[dict[str, Any]],
    service_index: dict[str, dict[str, Any]],
) -> list[str]:
    evidence = []
    for path in domain_paths[:3]:
        evidence.extend(path["config_checkpoints"][:1])
        evidence.extend(path["log_checkpoints"][:1])
    for service_name in domain["supporting_services"][:3]:
        service = service_index.get(service_name)
        if service is None:
            continue
        if service["observed"]["listeners"]:
            first_listener = service["observed"]["listeners"][0]["port"]
            evidence.append(f"{service_name} listener {first_listener}")
    return sorted(dict.fromkeys(evidence))


def _build_symptom_lookup(diagnostic_flows: list[dict[str, Any]]) -> list[dict[str, str]]:
    flow_index = {flow["flow_id"]: flow for flow in diagnostic_flows}
    symptom_map = [
        ("asms-ui-down", "ASMS UI is down", "ui-and-proxy"),
        ("asms-login-not-loading", "ASMS login page not loading", "ui-and-proxy"),
        ("fireflow-action-failing", "FireFlow action failing", "core-aff"),
        ("fireflow-api-error", "FireFlow API error", "core-aff"),
        ("feature-failing-behind-ui", "Feature failing behind UI", "microservice-platform"),
        ("specific-ms-path-failing", "Specific microservice path failing", "microservice-platform"),
        ("job-stuck", "Job stuck or not progressing", "messaging-and-data"),
        ("data-backed-action-failing", "Data-backed action failing", "messaging-and-data"),
    ]

    lookup = []
    for symptom_id, symptom_label, flow_id in symptom_map:
        flow = flow_index.get(flow_id)
        if flow is None:
            continue
        first_action = flow["check_sequence"][0] if flow["check_sequence"] else "Start with the first domain check."
        lookup.append(
            {
                "symptom_id": symptom_id,
                "symptom_label": symptom_label,
                "suggested_domain_id": flow["flow_id"],
                "suggested_domain_label": flow["label"],
                "suggested_flow_label": flow["label"],
                "suggested_page_id": flow["page_id"],
                "suggested_page_type": flow["page_type"],
                "page_type": flow["page_type"],
                "page_role": flow["page_role"],
                "page_id": flow["page_id"],
                "handoff_target": flow["handoff_target"],
                "handoff_target_type": flow["handoff_target_type"],
                "route_kind": flow["route_kind"],
                "operator_row_id": flow["operator_row_id"],
                "entry_question": flow["entry_question"],
                "next_page_id": flow["handoff_target"],
                "next_page_type": flow["handoff_target_type"],
                "first_action": first_action,
            }
        )
    return lookup


def _flow_evidence_to_collect_next(
    *,
    domain_id: str,
    domain_paths: list[dict[str, Any]],
    domain: dict[str, Any],
) -> list[str]:
    evidence: list[str] = []
    if domain_id == "ui-and-proxy":
        evidence.append("Host pressure signals from df -h, df -ih, free -h, uptime, journalctl -k, and top CPU output.")
        evidence.append("Apache edge evidence from systemctl status, ss -lntp, local curl -I, and proxy route snippets under /etc/httpd/conf.d.")
        evidence.append("Auth and app branch evidence from systemctl status, listener output, and local useful-work checks for Keycloak and Metro.")
        evidence.append("Recent Apache, Keycloak, and Metro clues only after the host and edge checks narrow the likely stop point.")
        return evidence

    if domain_id == "core-aff":
        evidence.append("Result of the failing FireFlow action, including the exact endpoint or screen.")
        evidence.append("Visible status for aff-boot.service and postgresql.service.")
        evidence.append("Any recent FireFlow-related lines from the customer-facing logs or service status output.")
        evidence.append("If the same minute rolls into `/FireFlow/api/swagger/v2/api-docs` or unified service-definition refresh, capture matching `ms-configuration` and Apache `ssl_error_log` lines before promoting ActiveMQ.")
        return evidence

    if domain_id == "microservice-platform":
        for path in domain_paths[:2]:
            if path["route_checkpoints"]:
                route = path["route_checkpoints"][0]
                target = route["locations"] or path["label"]
                port = route["target_ports"] or "local target"
                evidence.append(f"Status of the routed path {target} and whether it still maps to {port}.")
        evidence.append("Visible state of algosec-ms.service and ms-configuration.service.")
        evidence.append("Any service status, console error, or log snippet for the failing ms-* feature path.")
        return evidence

    if domain_id == "messaging-and-data":
        evidence.append("Visible status of activemq.service and whether listener 61616 is present.")
        evidence.append("Visible status of postgresql.service and any database connectivity error.")
        evidence.append("Any stuck job, queue, or backlog indicator shown during the customer session.")
        return evidence

    if domain["supporting_services"]:
        evidence.append(f"Visible status for {domain['supporting_services'][0]}.")
    return evidence


def _build_decision_playbooks(diagnostic_flows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    playbooks = []
    for flow in diagnostic_flows:
        steps = _decision_playbook_steps(flow)

        decision_rule = (
            "If a step fails, stop the happy-path sequence, record that step as the current failure point, "
            "and collect the matching evidence before moving on."
        )
        page_record = _page_record_for_flow(flow)
        playbooks.append(
            {
                "playbook_id": flow["flow_id"],
                "label": flow["label"],
                "symptom_focus": flow["symptom_focus"],
                "page_id": flow["page_id"],
                "page_type": flow["page_type"],
                "page_role": flow["page_role"],
                "entry_question": flow["entry_question"],
                "handoff_target": flow["handoff_target"],
                "handoff_target_type": flow["handoff_target_type"],
                "route_kind": flow["route_kind"],
                "operator_row_id": flow["operator_row_id"],
                "page_record": page_record,
                "operator_row": _operator_row_for_page_record(page_record),
                "routing": {
                    "from_page_id": flow["page_id"],
                    "from_page_type": flow["page_type"],
                    "to_page_id": flow["handoff_target"],
                    "to_page_type": flow["handoff_target_type"],
                    "route_kind": flow["route_kind"],
                },
                "decision_rule": decision_rule,
                "likely_failing_services": flow["likely_failing_services"],
                "dependency_path": _playbook_dependency_path(flow["flow_id"]),
                "steps": steps,
            }
        )
    return playbooks


def _flow_page_metadata(domain_id: str) -> dict[str, str]:
    if domain_id == "ui-and-proxy":
        return {
            "page_type": "symptom_entry",
            "page_role": "symptom_entry",
            "page_id": "ui-and-proxy",
            "handoff_target": "keycloak-auth",
            "handoff_target_type": "boundary_confirmation",
            "route_kind": "symptom_entry",
            "entry_question": "Where should I start from this customer symptom",
        }
    if domain_id == "core-aff":
        return {
            "page_type": "boundary_confirmation",
            "page_role": "boundary_confirmation",
            "page_id": "core-aff",
            "handoff_target": "asms-runtime-taxonomy",
            "handoff_target_type": "deep_guide",
            "route_kind": "boundary_confirmation",
            "entry_question": "Is this named service or module the reason for the symptom",
        }
    if domain_id == "microservice-platform":
        return {
            "page_type": "boundary_confirmation",
            "page_role": "boundary_confirmation",
            "page_id": "microservice-platform",
            "handoff_target": "asms-runtime-taxonomy",
            "handoff_target_type": "deep_guide",
            "route_kind": "boundary_confirmation",
            "entry_question": "Is this named service or module the reason for the symptom",
        }
    if domain_id == "messaging-and-data":
        return {
            "page_type": "boundary_confirmation",
            "page_role": "boundary_confirmation",
            "page_id": "messaging-and-data",
            "handoff_target": "asms-runtime-taxonomy",
            "handoff_target_type": "deep_guide",
            "route_kind": "boundary_confirmation",
            "entry_question": "Is this named service or module the reason for the symptom",
        }
    return {
        "page_type": "boundary_confirmation",
        "page_role": "boundary_confirmation",
        "page_id": domain_id,
        "handoff_target": "asms-runtime-taxonomy",
        "handoff_target_type": "deep_guide",
        "route_kind": "boundary_confirmation",
        "entry_question": "Is this named service or module the reason for the symptom",
    }


def _page_entry_question(page_type: str) -> str:
    return {
        "symptom_entry": "Where should I start from this customer symptom",
        "boundary_confirmation": "Is this named service or module the reason for the symptom",
        "deep_guide": "What should I understand before or after escalation",
    }.get(page_type, "What should I do next")


def _page_rendering_metadata(page_id: str) -> dict[str, Any]:
    if page_id == "keycloak-auth":
        return {
            "supplement_id": "keycloak-auth",
            "related_guides": [
                {
                    "guide_id": "keycloak-integration",
                    "label": "ASMS / Keycloak integration guide",
                    "slug": "guides/asms-keycloak-integration-guide",
                    "summary": "Technical map of where Keycloak sits in the ASMS path, backed by the current boundary contract.",
                    "detail": "Open this for architecture, handoff, and evidence context.",
                },
                {
                    "guide_id": "keycloak-tier-2-support",
                    "label": "ASMS / Keycloak Tier 2 support guide",
                    "slug": "guides/asms-keycloak-tier-2-support-guide",
                    "summary": "Support-first triage sheet derived from the current Keycloak boundary contract.",
                    "detail": "Open this during a live customer session.",
                },
            ],
        }
    if page_id == "core-aff":
        return {
            "supplement_id": "core-aff",
        }
    return {}


def _handoff_target_type(handoff_target: str) -> str:
    return {
        "keycloak-auth": "boundary_confirmation",
        "asms-runtime-taxonomy": "deep_guide",
        "escalate_or_review": "escalation_stop",
    }.get(handoff_target, "boundary_confirmation")


def _boundary_service_name_for_flow(flow: dict[str, Any]) -> str:
    likely_services = flow.get("likely_failing_services") or []
    if likely_services:
        return likely_services[0]
    if flow["flow_id"] == "ui-and-proxy":
        return "httpd.service"
    return flow["label"]


def _page_record_for_flow(flow: dict[str, Any]) -> dict[str, Any]:
    page_metadata = flow["page_metadata"]
    first_action = flow["check_sequence"][0] if flow["check_sequence"] else "Start with the first domain check."
    checks = flow["check_sequence"][:4]
    page_type = page_metadata["page_type"]
    steps = [
        {
            "step_id": f"{page_metadata['page_id']}-page-step-{index + 1}",
            "step_label": f"Step {index + 1}",
            "page_type": page_type,
            "action": action,
            "next_page": page_metadata["handoff_target"] if index == len(checks) - 1 else "",
            "next_page_type": page_metadata["handoff_target_type"] if index == len(checks) - 1 else page_type,
            "handoff_target": page_metadata["handoff_target"] if index == len(checks) - 1 else "",
            "handoff_target_type": page_metadata["handoff_target_type"] if index == len(checks) - 1 else page_type,
            "route_kind": page_metadata["route_kind"],
        }
        for index, action in enumerate(checks)
    ]
    if not steps:
        steps = [
            {
                "step_id": f"{page_metadata['page_id']}-page-step-1",
                "step_label": "Step 1",
                "page_type": page_type,
                "action": "Start with the first domain check.",
                "next_page": page_metadata["handoff_target"],
                "next_page_type": page_metadata["handoff_target_type"],
                "handoff_target": page_metadata["handoff_target"],
                "handoff_target_type": page_metadata["handoff_target_type"],
                "route_kind": page_metadata["route_kind"],
            }
        ]

    page_record = {
        "page_type": page_type,
        "page_role": page_metadata["page_role"],
        "page_id": page_metadata["page_id"],
        "label": flow["label"],
        "symptom_focus": flow["symptom_focus"],
        "entry_question": page_metadata["entry_question"],
        "first_action": first_action,
        "handoff_target": page_metadata["handoff_target"],
        "handoff_target_type": page_metadata["handoff_target_type"],
        "route_kind": page_metadata["route_kind"],
        "routing": {
            "from_page_id": page_metadata["page_id"],
            "from_page_type": page_type,
            "to_page_id": page_metadata["handoff_target"],
            "to_page_type": page_metadata["handoff_target_type"],
            "route_kind": page_metadata["route_kind"],
        },
        "operator_row_id": flow["operator_row_id"],
        "source_flow_id": flow["flow_id"],
        "decision_rule": (
            "If a step fails, stop the happy-path sequence, record that step as the current failure point, "
            "and collect the matching evidence before moving on."
        ),
        "checks": checks,
        "what_to_save": flow["evidence_to_collect_next"][:4] or flow["supporting_evidence"][:4],
        "steps": steps,
        "supporting_topics": [
            flow["label"],
            page_type,
            flow["handoff_target"],
        ],
    }
    if page_type == "symptom_entry":
        page_record.update(
            {
                "customer_symptom": flow["label"],
                "branch_if_pass": f"Move to {page_metadata['handoff_target']}.",
                "branch_if_fail": "Stay on the symptom-entry page and save the output before widening.",
            }
        )
    elif page_type == "boundary_confirmation":
        page_record.update(
            {
                "use_this_when": flow["symptom_focus"],
                "service_name": flow["service_name"],
                "branch_if_pass": f"Move to {page_metadata['handoff_target']}.",
                "branch_if_fail": "Stop on this boundary and escalate with the saved evidence.",
            }
        )
    else:
        page_record.update(
            {
                "title": flow["label"],
                "purpose": flow["symptom_focus"],
                "branch_if_pass": "Use the guide to prepare escalation or a later boundary check.",
                "branch_if_fail": "Stop and save the shared layer map before widening.",
            }
        )
    rendering = _page_rendering_metadata(page_record["page_id"])
    if rendering:
        page_record["rendering"] = rendering
    return page_record


def _operator_row_for_page_record(page_record: dict[str, Any]) -> dict[str, Any]:
    customer_symptom = (
        page_record.get("customer_symptom")
        or page_record.get("use_this_when")
        or page_record.get("symptom_focus")
        or page_record.get("label")
        or page_record["page_id"]
    )
    first_action = page_record.get("first_action", "Start with the first check.")
    what_to_save = page_record.get("what_to_save", [])
    return {
        "row_id": page_record["operator_row_id"],
        "page_id": page_record["page_id"],
        "page_type": page_record["page_type"],
        "page_role": page_record.get("page_role", page_record["page_type"]),
        "customer_symptom": customer_symptom,
        "entry_question": page_record.get("entry_question", _page_entry_question(page_record["page_type"])),
        "first_action": first_action,
        "next_page_or_next_service": page_record["handoff_target"],
        "next_page_type": page_record.get("handoff_target_type", ""),
        "what_to_save": what_to_save,
        "handoff_target": page_record["handoff_target"],
        "handoff_target_type": page_record.get("handoff_target_type", ""),
        "branch_if_pass": page_record.get("branch_if_pass", ""),
        "branch_if_fail": page_record.get("branch_if_fail", ""),
        "service_name": page_record.get("service_name", ""),
        "use_this_when": page_record.get("use_this_when", ""),
    }


def _build_page_records(
    diagnostic_flows: list[dict[str, Any]],
    support_domains: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    page_records = [_page_record_for_flow(flow) for flow in diagnostic_flows]
    flow_index = {flow["flow_id"]: flow for flow in diagnostic_flows}

    ui_flow = flow_index.get("ui-and-proxy")
    if ui_flow is not None:
        page_records.append(_build_keycloak_boundary_page_record(ui_flow))

    page_records.append(_build_taxonomy_deep_guide_page_record(support_domains))
    return page_records


def _build_keycloak_boundary_page_record(flow: dict[str, Any]) -> dict[str, Any]:
    page_metadata = {
        "page_type": "boundary_confirmation",
        "page_role": "boundary_confirmation",
        "page_id": "keycloak-auth",
        "handoff_target": "asms-runtime-taxonomy",
        "handoff_target_type": "deep_guide",
        "route_kind": "boundary_confirmation",
        "entry_question": "Is this named service or module the reason for the symptom",
    }
    return {
        "page_type": page_metadata["page_type"],
        "page_role": page_metadata["page_role"],
        "page_id": page_metadata["page_id"],
        "label": "ASMS Keycloak auth is down",
        "service_name": "keycloak",
        "use_this_when": "Login page opens but sign-in fails.",
        "entry_question": page_metadata["entry_question"],
        "branch_if_pass": f"Move to {page_metadata['handoff_target']}.",
        "branch_if_fail": "Stop on the Keycloak boundary and escalate with the saved evidence.",
        "checks": [
            "Confirm keycloak.service is active.",
            "Confirm listener 8443 is present.",
            "Confirm the OIDC probe responds.",
        ],
        "what_to_save": [
            "service status",
            "listener output",
            "OIDC probe output",
        ],
        "handoff_target": page_metadata["handoff_target"],
        "handoff_target_type": page_metadata["handoff_target_type"],
        "route_kind": page_metadata["route_kind"],
        "routing": {
            "from_page_id": page_metadata["page_id"],
            "from_page_type": page_metadata["page_type"],
            "to_page_id": page_metadata["handoff_target"],
            "to_page_type": page_metadata["handoff_target_type"],
            "route_kind": page_metadata["route_kind"],
        },
        "operator_row_id": f"{page_metadata['page_id']}-operator-row",
        "source_flow_id": flow["flow_id"],
        "decision_rule": (
            "If login still fails after the Keycloak checks, keep the case on the Keycloak boundary before widening into deeper ASMS layers."
        ),
        "steps": [
            {
                "step_id": "keycloak-auth-step-1",
                "step_label": "Step 1",
                "page_type": page_metadata["page_type"],
                "action": "Check the login page and the Keycloak OIDC path together.",
                "next_page": page_metadata["handoff_target"],
                "next_page_type": page_metadata["handoff_target_type"],
                "handoff_target": page_metadata["handoff_target"],
                "handoff_target_type": page_metadata["handoff_target_type"],
                "route_kind": page_metadata["route_kind"],
            },
            {
                "step_id": "keycloak-auth-step-2",
                "step_label": "Step 2",
                "page_type": page_metadata["page_type"],
                "action": "Check Keycloak service state and the local 8443 listener.",
                "next_page": page_metadata["handoff_target"],
                "next_page_type": page_metadata["handoff_target_type"],
                "handoff_target": page_metadata["handoff_target"],
                "handoff_target_type": page_metadata["handoff_target_type"],
                "route_kind": page_metadata["route_kind"],
            },
            {
                "step_id": "keycloak-auth-step-3",
                "step_label": "Step 3",
                "page_type": page_metadata["page_type"],
                "action": "Check the Apache proxy path for Keycloak.",
                "next_page": page_metadata["handoff_target"],
                "next_page_type": page_metadata["handoff_target_type"],
                "handoff_target": page_metadata["handoff_target"],
                "handoff_target_type": page_metadata["handoff_target_type"],
                "route_kind": page_metadata["route_kind"],
            },
        ],
        "supporting_topics": [
            "Keycloak auth boundary",
            "login page",
            "OIDC probe",
        ],
        "rendering": _page_rendering_metadata(page_metadata["page_id"]),
    }


def _build_taxonomy_deep_guide_page_record(support_domains: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "page_type": "deep_guide",
        "page_role": "deep_guide",
        "page_id": "asms-runtime-taxonomy",
        "label": "ASMS Runtime Taxonomy Guide",
        "purpose": "Explain the shared ASMS-runtime-first layers and how to move from symptom entry into deeper boundary checks.",
        "entry_question": _page_entry_question("deep_guide"),
        "branch_if_pass": "Use the guide to prepare escalation or a later boundary check.",
        "branch_if_fail": "Stop and save the shared layer map before widening.",
        "supporting_topics": [
            "ASMS entry and edge",
            "ASMS authentication and session",
            "ASMS application services",
            "Shared runtime and dependencies",
            "Host integration and operating evidence",
        ],
        "handoff_target": "escalate_or_review",
        "handoff_target_type": _handoff_target_type("escalate_or_review"),
        "route_kind": "deep_guide",
        "routing": {
            "from_page_id": "asms-runtime-taxonomy",
            "from_page_type": "deep_guide",
            "to_page_id": "escalate_or_review",
            "to_page_type": _handoff_target_type("escalate_or_review"),
            "route_kind": "deep_guide",
        },
        "operator_row_id": "asms-runtime-taxonomy-operator-row",
        "source_domain_ids": [domain["domain_id"] for domain in support_domains],
        "decision_rule": "Use this guide when you need the shared layer map before returning to a symptom-entry or boundary-confirmation page.",
        "steps": [
            {
                "step_id": "asms-runtime-taxonomy-step-1",
                "step_label": "Step 1",
                "page_type": "deep_guide",
                "action": "Review the ASMS entry, auth, application, shared runtime, and host evidence layers.",
                "next_page": "escalate_or_review",
                "next_page_type": _handoff_target_type("escalate_or_review"),
                "handoff_target": "escalate_or_review",
                "handoff_target_type": _handoff_target_type("escalate_or_review"),
                "route_kind": "deep_guide",
            }
        ],
        "what_to_save": [
            "layer map",
            "boundary notes",
            "escalation context",
        ],
    }


def _build_operator_rows(page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_operator_row_for_page_record(page_record) for page_record in page_records]


def _build_page_routes(page_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    routes = []
    for page_record in page_records:
        handoff_target = page_record.get("handoff_target")
        if not handoff_target:
            continue
        routes.append(
            {
                "from_page_id": page_record["page_id"],
                "from_page_type": page_record["page_type"],
                "to_page_id": handoff_target,
                "to_page_type": page_record.get("handoff_target_type", ""),
                "route_kind": page_record.get("route_kind", "boundary_confirmation"),
                "operator_row_id": page_record.get("operator_row_id"),
                "source_flow_id": page_record.get("source_flow_id"),
                "page_role": page_record.get("page_role", page_record["page_type"]),
                "handoff_target": handoff_target,
            }
        )
    return routes


def _playbook_dependency_path(flow_id: str) -> list[dict[str, Any]]:
    if flow_id == "ui-and-proxy":
        return [
            {
                "step_label": "Step 1",
                "step_id": "ui-and-proxy-step-1",
                "label": "Host sanity gate for ASMS runtime",
                "page_type": "symptom_entry",
                "page_role": "symptom_entry",
                "handoff_target": "ui-and-proxy",
                "handoff_target_type": "symptom_entry",
                "route_kind": "symptom_entry",
                "details": "Start here with a short sanity gate. Check storage, inode, memory, OOM, load, and CPU pressure to decide whether the Rocky host can still support the ASMS runtime and its supporting services before you deepen the ASMS path itself.",
            },
            {
                "step_label": "Step 2",
                "step_id": "ui-and-proxy-step-2",
                "label": "Apache/HTTPD serving the UI",
                "page_type": "symptom_entry",
                "page_role": "symptom_entry",
                "handoff_target": "ui-and-proxy",
                "handoff_target_type": "symptom_entry",
                "route_kind": "symptom_entry",
                "details": "If the host looks healthy, confirm Apache/HTTPD can answer local UI traffic and still route requests into the auth and app branches.",
            },
            {
                "step_label": "Step 3",
                "step_id": "ui-and-proxy-step-3",
                "label": "Core ASMS services and safe restart boundary",
                "page_type": "symptom_entry",
                "page_role": "symptom_entry",
                "handoff_target": "ui-and-proxy",
                "handoff_target_type": "symptom_entry",
                "route_kind": "symptom_entry",
                "details": "If the host and Apache edge look healthy, stay shallow first. Confirm the core ASMS services that support the UI are up, listening, and restartable: `httpd.service`, `keycloak.service`, and `ms-metro.service`. Use restart steps only for the service whose shallow check actually failed or hung.",
            },
            {
                "step_label": "Step 4",
                "step_id": "ui-and-proxy-step-4",
                "label": "First usable shell and case classification",
                "page_type": "symptom_entry",
                "page_role": "symptom_entry",
                "handoff_target": "keycloak-auth",
                "handoff_target_type": "boundary_confirmation",
                "route_kind": "symptom_to_boundary_handoff",
                "details": "Use the customer-visible shell boundary to decide whether the case is still `GUI down`. If the login page loads or the user reaches a usable home shell, stop treating it as a top-level UI outage and branch into the narrower failing workflow.",
            },
            {
                "step_label": "Step 5",
                "step_id": "ui-and-proxy-step-5",
                "label": "Escalation-only deeper auth and app correlation",
                "page_type": "symptom_entry",
                "page_role": "symptom_entry",
                "handoff_target": "escalate_or_review",
                "handoff_target_type": "escalation_stop",
                "route_kind": "escalation_stop",
                "details": "Only if the shallow host, Apache, service, and first-shell checks still do not explain the case should you replay the login bootstrap, auth chain, or deeper module seams. Those are escalation paths, not the frontline default.",
            },
        ]
    return []


def _playbook_step(
    *,
    step_id: str,
    step_number: int,
    action: str,
    why_this_matters: str | None = None,
    next_if_pass: str,
    failure_point: str,
    decision_if_fail: str,
    evidence_to_collect: list[str],
    recommended_commands: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "step_label": f"Step {step_number}",
        "action": action,
        "why_this_matters": why_this_matters or "",
        "next_if_pass": next_if_pass,
        "failure_point": failure_point,
        "decision_if_fail": decision_if_fail,
        "evidence_to_collect": evidence_to_collect,
        "recommended_commands": recommended_commands or [],
        # Backward-compatible render fields while the artifact model settles.
        "if_pass": next_if_pass,
        "if_fail": decision_if_fail,
    }


def _command_entry(
    *,
    label: str,
    command: str,
    expected_signal: str,
    interpretation: str,
    healthy_markers: list[str] | None = None,
    example_output: str | None = None,
) -> dict[str, Any]:
    entry = {
        "label": label,
        "command": command,
        "expected_signal": expected_signal,
        "interpretation": interpretation,
        "healthy_markers": healthy_markers or [],
        "example_output": example_output or "",
    }
    linux_note = derive_command_linux_note(entry)
    if linux_note:
        entry["linux_note"] = linux_note
    known_working_example = derive_known_working_example(entry)
    if known_working_example:
        entry["known_working_example"] = known_working_example
    return entry


def derive_known_working_example(command: dict[str, Any]) -> dict[str, str] | None:
    example = (command.get("example_output") or "").rstrip()
    if not example:
        return None
    return {
        "title": "Known working example",
        "output": example,
    }


def derive_command_linux_note(command: dict[str, Any]) -> dict[str, Any] | None:
    raw = command["command"]
    label = command["label"]
    if raw.startswith("systemctl status "):
        return {
            "title": "Linux note: service status",
            "items": [
                "This asks systemd whether the service is known and running now.",
                "`Loaded` means the service unit exists on the server.",
                "`Active (running)` means the service is up now. `Main PID` means systemd still sees the main process.",
            ],
        }
    if raw.startswith("ss -lntp"):
        return {
            "title": "Linux note: listening port",
            "items": [
                "This checks whether Linux is listening on the expected port.",
                "`LISTEN` means a process has opened the port and is waiting for connections.",
                "If the port is missing, the service may be down, slow to start, or bound to the wrong place.",
            ],
        }
    if raw == "df -h":
        return {
            "title": "Linux note: disk pressure",
            "items": [
                "This checks human-readable disk usage for the main filesystems.",
                "Focus on `Use%` and `Avail`, especially for `/` and `/data`.",
                "Disk pressure means the filesystem is close to full. When that happens, services can fail to write logs, temp files, or runtime data.",
            ],
        }
    if raw == "df -ih":
        return {
            "title": "Linux note: inode pressure",
            "items": [
                "This checks inode usage, which is different from normal disk space.",
                "A filesystem can still have free space but fail because it has no free inodes left.",
                "Inode pressure means the server has too many files or directory entries. Focus on `IUse%` and whether `IFree` is close to zero.",
            ],
        }
    if raw == "free -h":
        return {
            "title": "Linux note: memory pressure",
            "items": [
                "This is the quick memory check for the host.",
                "Focus on `available` memory and whether swap is starting to grow heavily.",
                "Memory pressure means the server is low on available memory. When that happens, the server slows down, swap grows, or Linux may kill a process to protect itself.",
            ],
        }
    if raw == "uptime":
        return {
            "title": "Linux note: system load",
            "items": [
                "This is the quick load check for the host.",
                "Focus on the `load average` values and whether they look unexpectedly high for the server.",
                "High load can mean CPU pressure, blocked work, or heavy I/O wait.",
            ],
        }
    if raw.startswith("journalctl -k --since"):
        return {
            "title": "Linux note: OOM pressure",
            "items": [
                "This checks the Linux kernel log for memory-pressure kills.",
                "OOM means Out Of Memory. Linux may kill a process to protect the server.",
                "If you see OOM or `Killed process` lines, memory pressure is likely part of the failure.",
            ],
        }
    if raw.startswith("ps -eo pid,comm,%cpu,%mem --sort=-%cpu"):
        return {
            "title": "Linux note: top CPU consumers",
            "items": [
                "This shows which processes are using the most CPU right now.",
                "Focus on whether one process is dominating CPU and whether that process matches the current symptom.",
                "A single runaway process can starve the rest of the server and make higher-level application failures look worse than they are.",
            ],
        }
    if "/health/ready" in raw:
        return {
            "title": "Linux note: service readiness",
            "items": [
                "This checks a local readiness endpoint instead of only checking whether the service process exists.",
                "A readiness endpoint helps prove the service is healthy enough to answer real traffic.",
                "Use the expected JSON value below as the main reference, not just the HTTP connection itself.",
            ],
        }
    if raw.startswith("for path in /algosec-ui/styles.css /algosec-ui/runtime.js /algosec-ui/main.js; do"):
        return {
            "title": "Linux note: browser-useful edge assets",
            "items": [
                "This checks whether Apache is serving real UI assets, not only the login HTML shell.",
                "Non-empty CSS and JavaScript bodies are a stronger edge proof because the browser needs them before the login page can work normally.",
                "If the HTML is up but these assets fail, stay on Apache and the static UI path before chasing Keycloak or Metro.",
            ],
        }
    if "/seikan/login/setup" in raw:
        return {
            "title": "Linux note: login setup mode",
            "items": [
                "This checks the login setup endpoint that the shipped UI uses before credentials are submitted.",
                "Use it to see whether this appliance is advertising SSO or a different login mode for the current journey.",
                "If `isSSOEnabled` is false here, do not assume Keycloak is the first observed auth hop without stronger request evidence.",
            ],
        }
    if "compare the first usable shell gate with metro bootstrap clues" in label.lower():
        return {
            "title": "Linux note: shell gate versus Metro bootstrap",
            "items": [
                "Use one same-minute comparison so the shell gate and the nearby Metro clues are judged on the same reproduced window, not as two unrelated tails.",
                "If `SuiteLoginSessionValidation.php` appears but `/afa/php/home.php` does not appear in that same shell-transition window, stop on the pre-shell gate before blaming Metro.",
                "If `/afa/php/home.php` appears but the same-minute Metro bootstrap clues such as `/afa/getStatus`, `config`, `session/extend`, or `config/all/noauth` are missing or unhealthy, stop on the Metro-backed home-shell path.",
                "If both the shell gate and the same-minute Metro bootstrap clues look healthy, stop calling the case `GUI down` and branch into the later failing workflow instead.",
            ],
        }
    if "check whether the case already crossed into a later content branch" in label.lower():
        return {
            "title": "Linux note: branch out of top-level GUI down",
            "items": [
                "This is a branch-out classifier, not another first-shell gate.",
                "Treat `DEVICES` tree refresh by itself as shell-context evidence only; do not promote it to a later workflow branch without a stronger marker.",
                "If the reproduced minute already shows later content markers such as `GET_REPORTS`, `GET_POLICY_TAB`, `GET_DEVICE_POLICY`, `GET_MONITORING_CHANGES`, or `GET_ANALYSIS_OPTIONS`, stop calling the case `GUI down` and switch to the narrower failing workflow.",
                "Keep the top-level playbook focused on the first usable shell. Once a later content branch is clearly present, the next support question is no longer whether the GUI is up.",
            ],
        }
    if "/afa/php/SuiteLoginSessionValidation.php" in raw:
        return {
            "title": "Linux note: legacy session validation",
            "items": [
                "This checks a legacy suite login endpoint with a cookie jar so one reproduced journey stays connected.",
                "A redirect back to `/algosec-ui/login` with a new PHP session cookie is a real auth-path clue, even without credentials.",
                "If this path lights up before `/BusinessFlow` or `/keycloak/`, treat it as the first observed auth-trigger hop for this journey and keep the later named modules behind it.",
            ],
        }
    if "businessflow checkpoint" in label.lower():
        return {
            "title": "Linux note: BusinessFlow checkpoint",
            "items": [
                "This checks a downstream module that may appear later in the customer-visible ASMS login path.",
                "Use the shallow check to prove BusinessFlow is answering through Apache, then the deep check to confirm its AFA, AFF, and database links still look healthy.",
                "Do not promote this as the first UI dependency unless the same reproduced journey already reached BusinessFlow.",
                "If these checks fail after the reproduced login path clearly crossed into BusinessFlow, stop on the BusinessFlow checkpoint before blaming Keycloak or Metro.",
                "The current staged dependency passes put Postgres, AFA, and AFF closer to this seam than Keycloak or ActiveMQ.",
                "Those AFA and AFF checks are now concrete local HTTPS session-liveness checks, so the immediate seam is closer to Apache and the local app routes than to raw 8080 or 1989 probes.",
                "On this lab the AFA side resolves to Apache-served local PHP SOAP at `/afa/php/ws.php`, while the AFF side resolves to Apache `443` -> aff-boot `1989` via `/FireFlow/api/session`.",
            ],
        }
    if label.lower().startswith("check the afa soap path behind businessflow afa connection"):
        return {
            "title": "Linux note: BusinessFlow AFA SOAP path",
            "items": [
                "This proves what owns the AFA side of the BusinessFlow AFA health check.",
                "On this lab the exact liveness path is the local SOAP endpoint `/afa/php/ws.php`.",
                "Apache receives that HTTPS request first, but it serves local PHP for `/afa/php` instead of proxying the whole family elsewhere.",
            ],
        }
    if label.lower().startswith("check the afa soap runtime seam behind ws.php"):
        return {
            "title": "Linux note: AFA SOAP runtime seam",
            "items": [
                "This is the first support-readable seam behind the AFA SOAP endpoint.",
                "Apache shows when `/afa/php/ws.php` was hit, but `.ht-fa-history` is the better seam because it carries the request hash, the `SESSION / TOKEN / COOKIE` triple, and the `is_session_alive` result.",
                "After that, pivot to the PHP session file and `.ht-LastActionTime` for the same session id before jumping outward into Metro or later GUI workflows.",
            ],
        }
    if label.lower().startswith("check the afa session backing files after ws.php"):
        return {
            "title": "Linux note: AFA session backing files",
            "items": [
                "This confirms that the same SOAP session id from `.ht-fa-history` still has local PHP session backing and a pulse-file update.",
                "Treat a missing `sess_<id>` file or a missing or stale `.ht-LastActionTime` file as a real `BusinessFlow -> AFA connection` stop point before jumping to Metro or broader GUI theories.",
                "Use the same session id from the latest `is_session_alive` request so the engineer stays on one reproduced AFA seam instead of mixing in unrelated background traffic.",
            ],
        }
    if label.lower().startswith("check the fireflow session path behind businessflow aff connection"):
        return {
            "title": "Linux note: BusinessFlow AFF route ownership",
            "items": [
                "This proves what owns the FireFlow side of the BusinessFlow AFF health check.",
                "On this lab the local HTTPS FireFlow session path hits Apache first and is immediately proxied to aff-boot on 1989.",
                "The Apache-fronted `/FireFlow/api/session` response and the direct `1989` `/aff/api/external/session` response should match on the same invalid-session JSON body.",
                "It does not go through Keycloak 8443 first, so the next support seam is Apache to aff-boot and then the FireFlow UserSession bridge behind `/FireFlow/api/session`.",
            ],
        }
    if label.lower().startswith("check the fireflow usersession bridge after the aff session path"):
        return {
            "title": "Linux note: FireFlow UserSession bridge after the AFF session path",
            "items": [
                "Use this after `/FireFlow/api/session` and direct `1989` already match, so the engineer stays on the next readable seam instead of widening into generic FireFlow workflow theory.",
                "On this lab the closest follow-on seam is the FireFlow `UserSession` bridge: the same minute can show `CommandsDispatcher`, `/FireFlow/api/session`, `UserSessionPersistenceEventHandler.java::requestUserDetails`, `LegacyRestRepository.java::sendRequest`, and then a reused FA session id.",
                "Keep this step at the service and auth boundary. The deeper localhost cookie-bootstrap and polling traces are archived engineering evidence only and are not part of the frontline support path.",
                "For a customer session, stop on actionable checks here: prove the AFF session path, confirm Apache to `aff-boot` route ownership, and only use the `UserSession` bridge when the higher-level auth and service checks still disagree.",
                "Treat a missing `UserSession` bridge for the reproduced window as a real `BusinessFlow -> AFF connection` stop before promoting later FireFlow workflow, config-broadcast, or ActiveMQ checks.",
                "Keep `aff-boot.service` as supporting route ownership, but do not stop there if the route already looks healthy and the sharper question is whether FireFlow still bridges into the FA session.",
            ],
        }
    if label.lower().startswith("check the fireflow auth-coupled signals"):
        return {
            "title": "Linux note: FireFlow auth bridge",
            "items": [
                "This checks the FireFlow signals that appear during sign-in and immediately after the PHP home page loads.",
                "Treat FireFlow here as an auth-coupled module, not as the first branch in the login journey.",
                "If these checks fail while BusinessFlow and Keycloak looked healthy, the stop point is later in the authenticated handoff, not at the static shell.",
                "For this seam, Apache proxying, aff-boot, and FireFlow's database-backed runtime still look closer than ActiveMQ for first-pass troubleshooting.",
                "ActiveMQ is now a proven later supporting dependency here because aff-boot holds live broker connections on 61616, but the reproduced login-handoff minute still showed auth, session, and REST work instead of broker-side signals.",
                "Keep ActiveMQ behind the closer FireFlow checks unless the reproduced failing minute points to JMS or queue activity.",
            ],
        }
    if "/BusinessFlow/rest/v1/login" in raw or "/FireFlow/SelfService/CheckAuthentication/" in raw:
        return {
            "title": "Linux note: authenticated auth handoff",
            "items": [
                "This checks the mid-login handoff after the legacy setup hop has already fired.",
                "On this lab the observed order was legacy setup, BusinessFlow as the first named operational module, then proxied Keycloak token paths and FireFlow auth checks before the final `/afa/php/home.php` redirect.",
                "Use this to show that Keycloak is in the observed auth chain, but not the first post-shell request and not the first named module the support engineer should check.",
            ],
        }
    if "openid-configuration" in raw:
        return {
            "title": "Linux note: OIDC path",
            "items": [
                "This checks a real Keycloak OpenID Connect path that the local login flow depends on.",
                "An HTTP 200 here is a stronger proof than a simple port check because it confirms the local path is answering correctly.",
                "If this path fails while the service still looks up, treat it as an application-path problem instead of a simple process problem.",
            ],
        }
    if "/tmp/asms-journey.cookies" in raw and "/algosec/suite/login" in raw:
        return {
            "title": "Linux note: browser-like replay",
            "items": [
                "This replays one login journey with browser-like headers and a cookie jar so the follow-up log check has one clear anchor.",
                "Use the headers, cookies, and HTML markers together instead of looking at only one response line.",
                "If this replay still stops at the static shell, say the first downstream auth or app hop is still unproven.",
            ],
        }
    if "/var/log/httpd/ssl_access_log" in raw and "/algosec-ui/" in raw and "/keycloak/" in raw:
        return {
            "title": "Linux note: request correlation",
            "items": [
                "This ties one reproduced Apache journey to concrete request paths instead of broad log greps.",
                "Use it to see whether the request stopped at static UI assets, moved through the legacy setup hop, reached BusinessFlow as the first named module, and only then hit Keycloak, FireFlow, and Metro later in the same login minute.",
                "If no later auth or app lines appear for the reproduced journey, say the next neighbor is still unproven instead of guessing.",
            ],
        }
    if "/afa/getStatus" in raw:
        return {
            "title": "Linux note: service heartbeat",
            "items": [
                "This checks a real ms-metro heartbeat path instead of only checking whether the Java process exists.",
                "A heartbeat response helps prove the service is alive enough to answer application traffic.",
                "Use this after the listener check when port 8080 is open but the UI still behaves badly.",
            ],
        }
    if "/data/ms-metro/logs/localhost_access_log.txt" in raw and "grep -E '/afa/getStatus|/afa/api/v1/config\\?|/afa/api/v1/license|/afa/api/v1/session/extend|/afa/api/v1/config/all/noauth'" in raw:
        return {
            "title": "Linux note: app traffic",
            "items": [
                "This checks whether ms-metro is serving useful application traffic after login, not only whether the port is open.",
                "Focus first on the immediate same-minute home-refresh clues such as `/afa/getStatus`, `/afa/api/v1/license`, `/afa/api/v1/config?...`, or `/afa/api/v1/session/extend`, not on every later subsystem route at once.",
                "On this lab `/afa/getStatus` is the strongest immediate Metro clue after the first usable shell appears. `config` and `session/extend` now have a stronger fresh-session tie because they matched the new `PHPSESSID`, but they still stay as supporting same-minute clues until a stronger isolation pass proves one of them is a true first-shell gate.",
                "A CDP `Network.setBlockedURLs(...)` pass matched only the early `config/PRINT_TABLE_IN_NORMAL_VIEW` probe and did not actually own the real fresh-session `license`, `config`, `config/all/noauth`, or `session/extend` requests.",
                "A later Apache seam mutation returned repeated `403` responses for `/afa/external` and still left a fully usable `/afa/php/home.php` shell, so `/afa/external` is demoted as a first-shell gate candidate.",
                "A second top-level Apache mutation on `/afa/api/v1` also left the home shell fully usable and still did not cleanly own the fresh-session `config` and `session/extend` routes, so the next seam must be narrower than a family-wide Apache deny.",
                "A service can look up from the outside and still fail here if the home-refresh path is returning errors or no longer serving requests.",
            ],
        }
    if label.lower().startswith("check post-home shell and dashboard hydration traffic"):
        return {
            "title": "Linux note: post-home follow-ups",
            "items": [
                "This checks the first traffic that appears after the browser lands on `/afa/php/home.php`.",
                "On this lab the first follow-ups were a summary dashboard and issue-center hydration path plus light Metro refresh traffic, not a broad subsystem fan-out.",
                "The early shell routes included `dynamic.js.php`, `DISPLAY_ISSUES_CENTER`, `/fa/tree/create`, `/afa/php/prod_stat.php`, and `/fa/tree/get_update` before the first deeper operator action was isolated.",
                "Use them as supporting clues, not as first-class gates by themselves. A bounded client-side check showed that blocking `FireFlowBridge.js` did not stop the initial home page from rendering with the normal menu and summary content.",
                "Treat `/afa/getStatus` as the strongest immediate Metro clue after home render. Keep `license`, `config`, `config/all/noauth`, and `session/extend` nearby but still unproven, even though `config` and `session/extend` now have a stronger tie to the fresh `PHPSESSID`. The later CDP browser-layer pass did not own those real fresh-session routes, so prefer proxy-side or server-side isolation before promoting any of them. A later Apache seam mutation denied `/afa/external` and still left a fully usable home shell, and a second top-level Apache mutation on `/afa/api/v1` also left the home shell fully usable and still did not cleanly own the fresh-session `config` and `session/extend` routes, so the next seam must be narrower than a family-wide Apache deny. The first clean deeper action isolated so far is `Analyze`, which mapped to `GET_ANALYSIS_OPTIONS` after the landing shell and device context were already visible. The real `Start Analysis` step then crosses into `cmd=ANALYZE` and `RunFaServer(...)`, so treat that as a later workflow branch rather than as part of the first usable-shell gate. The device-context tabs are also already later content branches: `POLICY` posts `GET_POLICY_TAB` and `GET_DEVICE_POLICY`, `CHANGES` uses `GET_MONITORING_CHANGES`, and `REPORTS` uses `GET_REPORTS`. For support classification, once the customer can navigate the devices tree and reach `REPORTS` or `Analyze`, stop calling the case `GUI down` and branch into the more specific failing workflow instead. Keep `bridge/refresh` demoted unless the reproduced fresh session actually owns that request.",
                "Treat routes like the Notification Center issue count as later subsystem candidates unless the reproduced browser minute proves they are the first stop point.",
            ],
        }
    if raw.startswith("ps -p $(cat /var/run/ms-metro/ms-metro.pid) -o "):
        return {
            "title": "Linux note: JVM activity",
            "items": [
                "This shows the live Metro JVM process with elapsed runtime, CPU, memory, and thread count.",
                "Focus on whether CPU, memory, or thread count looks unexpectedly high for the current case.",
                "This is a stronger answer to 'what is Metro busy doing' than reading random Java log lines first.",
            ],
        }
    if raw.startswith("journalctl -u "):
        return {
            "title": "Linux note: service logs",
            "items": [
                "Recent service logs are often the fastest way to find the real failure clue.",
                "Focus on startup errors, permission errors, heap errors, dependency failures, and repeated retries.",
                "Use this after the status check when the service looks up but still behaves badly.",
            ],
        }
    if raw.startswith("grep -n -i -E ") and "/data/ms-metro/logs/catalina.out" in raw:
        return {
            "title": "Linux note: Java log anomalies",
            "items": [
                "Large Java logs are often noisy when read from the bottom alone.",
                "This check pulls likely error signatures first so the engineer can find the useful anomaly faster.",
                "Use the line numbers and error keywords here as the first clue, then widen into the full log only if needed.",
            ],
        }
    if raw.startswith("tail -n ") and ("/var/log/keycloak/" in raw or "/data/ms-metro/logs/" in raw):
        return {
            "title": "Linux note: file-based service logs",
            "items": [
                "This appliance writes the useful service clues to log files, not only to systemd journal output.",
                "Focus on startup errors, dependency failures, auth errors, heap errors, and repeated retries.",
                "Use the most specific log for the service you are checking before widening the search.",
            ],
        }
    if label.lower().startswith("check config mapping"):
        return {
            "title": "Linux note: config check",
            "items": [
                "This checks whether the expected mapping still exists in the service config.",
                "Use it to confirm the route, port, or target value is still what the application expects.",
            ],
        }
    return {
        "title": "Linux note",
        "items": [
            "This command gives a focused check for the current step.",
            "Use the healthy example below as the main output reference for what good looks like.",
        ],
    }


def _flow_service_detail(flow: dict[str, Any], service_name: str) -> dict[str, Any]:
    for detail in flow.get("supporting_service_details", []):
        if detail["service_name"] == service_name:
            return detail
    for path in flow.get("path_checkpoints", []):
        if path["entry_service"] == service_name:
            return {
                "service_name": service_name,
                "listener_ports": path.get("listener_ports", []),
                "config_refs": path.get("config_checkpoints", []),
                "log_refs": path.get("log_checkpoints", []),
            }
    return {
        "service_name": service_name,
        "listener_ports": [],
        "config_refs": [],
        "log_refs": [],
    }


def _flow_path_checkpoint(flow: dict[str, Any], service_name: str) -> dict[str, Any] | None:
    for path in flow.get("path_checkpoints", []):
        if path["entry_service"] == service_name:
            return path
    return None


def _service_status_command(
    service_name: str,
    *,
    interpretation: str,
    healthy_markers: list[str] | None = None,
    example_output: str | None = None,
) -> dict[str, Any]:
    return _command_entry(
        label=f"Check {service_name} status",
        command=f"systemctl status {shlex.quote(service_name)} --no-pager",
        expected_signal="Unit is loaded and active (running).",
        interpretation=interpretation,
        healthy_markers=healthy_markers,
        example_output=example_output,
    )


def _listener_command(
    ports: list[str],
    *,
    interpretation: str,
    label: str = "Check listener state",
    healthy_markers: list[str] | None = None,
    example_output: str | None = None,
) -> dict[str, Any] | None:
    normalized = [port for port in ports if port]
    if not normalized:
        return None
    if len(normalized) == 1:
        pattern = f":{normalized[0]}\\b"
        port_label = normalized[0]
    else:
        joined = "|".join(re.escape(port) for port in normalized)
        pattern = f":({joined})\\b"
        port_label = ", ".join(normalized)
    return _command_entry(
        label=label,
        command=f"ss -lntp | grep -E '{pattern}'",
        expected_signal=f"A listening socket is present for {port_label}.",
        interpretation=interpretation,
        healthy_markers=healthy_markers,
        example_output=example_output,
    )


def _host_health_precheck_commands() -> list[dict[str, Any]]:
    return _command_bundle(
        _command_entry(
            label="Check storage pressure on runtime filesystems",
            command="df -h",
            expected_signal="Runtime filesystems still have enough free space for logs, temp files, and service work.",
            interpretation="If /, /boot, or /data is close to full, Apache, Keycloak, Metro, installers, and log writers can all fail or behave unpredictably.",
            healthy_markers=[
                "Use% below 100%",
                "Avail is not 0",
                "/ and /data still have free space",
            ],
            example_output=_example_output(
                "Filesystem           Size  Used Avail Use% Mounted on",
                "/dev/mapper/rl-root   60G   16G   45G  27% /",
                "/dev/mapper/rl-data  238G   21G  218G   9% /data",
            ),
        ),
        _command_entry(
            label="Check inode pressure on runtime filesystems",
            command="df -ih",
            expected_signal="Runtime filesystems still have free inodes for logs, temp files, sockets, and service output.",
            interpretation="If inode use is high, the host can look like it has free disk while Apache, Keycloak, Metro, or log rotation still fail to create files.",
            healthy_markers=[
                "IUse% below 100%",
                "IFree is not 0",
                "/ and /data still have free inodes",
            ],
            example_output=_example_output(
                "Filesystem          Inodes IUsed IFree IUse% Mounted on",
                "/dev/mapper/rl-root    30M  343K   30M    2% /",
                "/dev/mapper/rl-data   119M   21K  119M    1% /data",
            ),
        ),
        _command_entry(
            label="Check memory pressure on JVM-backed services",
            command="free -h",
            expected_signal="Available memory is still present and swap is not carrying active pressure for the host.",
            interpretation="If available memory is very low or swap is heavily used, Java services like Keycloak and Metro may slow down, hang, fail health checks, or get killed later.",
            healthy_markers=[
                "available memory is present",
                "swap is not exhausted",
                "Mem and Swap are shown in GiB",
            ],
            example_output=_example_output(
                "              total        used        free      shared  buff/cache   available",
                "Mem:           32Gi        13Gi       8.6Gi       2.4Gi         9Gi        15Gi",
                "Swap:          24Gi          0B        24Gi",
            ),
        ),
        _command_entry(
            label="Check current host load pressure",
            command="uptime",
            expected_signal="Load is not unexpectedly high for the host and does not already explain the UI symptom.",
            interpretation="If load is unusually high, the system may be under CPU pressure, blocked work, or heavy I/O wait before you even reach the UI-specific branches.",
            healthy_markers=[
                "load average:",
                "load values are not unexpectedly high",
            ],
            example_output=_example_output(
                "14:42:03 up 17 days,  1:52,  1 user,  load average: 0.25, 0.18, 0.11",
            ),
        ),
        _command_entry(
            label="Check recent memory-kill pressure",
            command="journalctl -k --since \"24 hours ago\" --no-pager | grep -i -E \"out of memory|oom|killed process\"",
            expected_signal="No recent Out Of Memory lines are returned.",
            interpretation="If OOM lines appear, the host has already been killing or starving processes under memory pressure, so downstream UI symptoms may only be the visible side effect.",
            healthy_markers=[
                "No output is normal",
                "No 'Out of memory' lines",
                "No 'Killed process' lines",
            ],
            example_output=_example_output(
                "No output",
            ),
        ),
        _command_entry(
            label="Check which process owns CPU pressure right now",
            command="ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 10",
            expected_signal="No unexpected process is consuming enough CPU to starve the rest of the ASMS path.",
            interpretation="If one process is consuming most of the CPU, treat that process as part of the current system pressure story before assuming the UI path itself is the root cause.",
            healthy_markers=[
                "PID",
                "COMMAND",
                "%CPU",
                "%MEM",
            ],
            example_output=_example_output(
                "  PID COMMAND         %CPU %MEM",
                " 6012 java             8.1  7.4",
                " 1018 httpd            1.2  0.4",
                " 3758 algosec_keycloa  0.8  1.6",
            ),
        ),
    )


def _config_command(
    config_path: str,
    *,
    needle: str | None,
    interpretation: str,
    label: str = "Check config mapping",
    healthy_markers: list[str] | None = None,
    example_output: str | None = None,
) -> dict[str, Any]:
    quoted_path = shlex.quote(config_path)
    if needle:
        command = f"grep -n {shlex.quote(needle)} {quoted_path}"
        expected_signal = f"The expected mapping token {needle} appears in {config_path}."
    else:
        command = f"sed -n '1,160p' {quoted_path}"
        expected_signal = f"The expected proxy or service mapping is visible in {config_path}."
    return _command_entry(
        label=label,
        command=command,
        expected_signal=expected_signal,
        interpretation=interpretation,
        healthy_markers=healthy_markers,
        example_output=example_output,
    )


def _journal_command(
    service_name: str,
    *,
    interpretation: str,
    healthy_markers: list[str] | None = None,
    example_output: str | None = None,
) -> dict[str, Any]:
    return _command_entry(
        label=f"Review {service_name} logs",
        command=f"journalctl -u {shlex.quote(service_name)} -n 50 --no-pager",
        expected_signal="Recent lines show healthy startup or a clear error signature to classify.",
        interpretation=interpretation,
        healthy_markers=healthy_markers,
        example_output=example_output,
    )


def _curl_head_command(
    *,
    label: str,
    url: str,
    expected_signal: str,
    interpretation: str,
    healthy_markers: list[str] | None = None,
    example_output: str | None = None,
) -> dict[str, Any]:
    return _command_entry(
        label=label,
        command=f"curl -k -I --max-time 5 {shlex.quote(url)}",
        expected_signal=expected_signal,
        interpretation=interpretation,
        healthy_markers=healthy_markers,
        example_output=example_output,
    )


def _command_bundle(*commands: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [command for command in commands if command]


def _example_output(*lines: str) -> str:
    return "\n".join(lines)


def _decision_playbook_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    if flow["flow_id"] == "ui-and-proxy":
        return _ui_and_proxy_playbook_steps(flow)
    if flow["flow_id"] == "core-aff":
        return _core_aff_playbook_steps(flow)
    if flow["flow_id"] == "microservice-platform":
        return _microservice_platform_playbook_steps(flow)
    if flow["flow_id"] == "messaging-and-data":
        return _messaging_and_data_playbook_steps(flow)

    steps = []
    for index, action in enumerate(flow["check_sequence"], start=1):
        if index == 1:
            if_pass = "Continue to the next check in this playbook."
            if_fail = f"Mark {', '.join(flow['likely_failing_services'][:2])} as the current failure point and escalate within {flow['label']}."
        elif index < len(flow["check_sequence"]):
            if_pass = "Continue to the next check in this playbook."
            if_fail = "Treat this step as the most likely failure point and collect the related evidence."
        else:
            if_pass = flow["next_dependency_focus"] or "Move to deeper product-specific checks if symptoms still persist."
            if_fail = "Treat this step as the most likely failure point and collect the related evidence."

        steps.append(
            _playbook_step(
                step_id=f"{flow['flow_id']}-step-{index}",
                step_number=index,
                action=action,
                next_if_pass=if_pass,
                failure_point=", ".join(flow["likely_failing_services"][:2]) or flow["label"],
                decision_if_fail=if_fail,
                evidence_to_collect=flow["evidence_to_collect_next"][:2],
                recommended_commands=[],
            )
        )
    return steps


def _ui_and_proxy_playbook_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = flow["evidence_to_collect_next"]
    return [
        _playbook_step(
            step_id="ui-and-proxy-step-1",
            step_number=1,
            action="Check host health before deeper ASMS UI checks. Confirm storage, inode, memory, load, OOM, and CPU pressure are not already blocking Apache, Keycloak, Metro, log writing, or temp-file work.",
            why_this_matters="A lot of GUI-down cases are still host-pressure problems. If the appliance is already out of space, out of inodes, under memory pressure, or killing processes, deeper UI checks will only blur the real stop point.",
            next_if_pass="If the host looks healthy, move to the Apache edge checks.",
            failure_point="Host health pre-check",
            decision_if_fail="Stop here and treat disk, inode, memory, load, OOM, or CPU pressure on the host as the current failure point.",
            evidence_to_collect=[
                "Host pressure signals from df -h, df -ih, free -h, and uptime.",
                "Any recent OOM lines and the process currently owning CPU pressure.",
            ],
            recommended_commands=_host_health_precheck_commands(),
        ),
        _playbook_step(
            step_id="ui-and-proxy-step-2",
            step_number=2,
            action="Check Apache/HTTPD and the ASMS login path. Confirm httpd.service is running, 80 and 443 are listening, the suite login route still lands on the Apache-served UI page, representative /algosec-ui/ assets still load through Apache, and the proxy mapping still points toward the auth and app branches.",
            why_this_matters="Once host health looks okay, the next question is simple: can Apache still serve the login path and hand requests to the right next services. If the login page or route fails here, there is no reason to start with auth or app theory.",
            next_if_pass="If Apache still serves the login entry page, the representative UI assets, and the edge still points toward the auth and app branches, move to the first auth-trigger checks.",
            failure_point="Apache/HTTPD edge or route mapping",
            decision_if_fail="Stop here and treat the Apache edge, local response path, or proxy mapping as the current failure point.",
            evidence_to_collect=[
                "Apache service and listener state from systemctl status and ss -lntp.",
                "The suite login redirect, the Apache-served UI login page, representative /algosec-ui/ assets, and a proxy route snippet that show where UI traffic goes next.",
            ],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "httpd.service",
                    interpretation="If this is not active, treat the edge service itself as the failure point before going deeper.",
                    healthy_markers=[
                        "Loaded: loaded",
                        "Active: active (running)",
                        "Main PID:",
                        "/usr/sbin/httpd",
                    ],
                    example_output=_example_output(
                        "● httpd.service - The Apache HTTP Server",
                        "   Loaded: loaded (/usr/lib/systemd/system/httpd.service; enabled; vendor preset: disabled)",
                        "   Active: active (running) since Sat 2026-03-07 13:37:12 EST; 2 weeks 2 days ago",
                        " Main PID: 1018 (/usr/sbin/httpd)",
                    ),
                ),
                _listener_command(
                    ["80", "443"],
                    label="Check edge listeners",
                    interpretation="If 80/443 are missing, the UI path is failing at the listener or bind layer.",
                    healthy_markers=["LISTEN", ":80", ":443", "httpd"],
                    example_output=_example_output(
                        'LISTEN 0 511 0.0.0.0:443 0.0.0.0:* users:(("/usr/sbin/httpd",pid=1018,fd=4),...)',
                        'LISTEN 0 511 0.0.0.0:80  0.0.0.0:* users:(("/usr/sbin/httpd",pid=1018,fd=3),...)',
                    ),
                ),
                _curl_head_command(
                    label="Check the legacy suite login route",
                    url="https://127.0.0.1/algosec/suite/login",
                    expected_signal="Apache returns a redirect from the legacy suite login path into the current UI login page.",
                    interpretation="If the suite login route stops redirecting here, the edge path is already broken before Keycloak or Metro have a chance to help.",
                    healthy_markers=["HTTP/1.1 302", "Server: Apache", "Location: https://127.0.0.1/algosec-ui/login"],
                    example_output=_example_output(
                        "HTTP/1.1 302 Found",
                        "Server: Apache",
                        "Location: https://127.0.0.1/algosec-ui/login",
                    ),
                ),
                _curl_head_command(
                    label="Check the Apache-served UI login page",
                    url="https://127.0.0.1/algosec-ui/login",
                    expected_signal="Apache returns the current UI login page with HTTP 200.",
                    interpretation="If Apache cannot serve the login page here, stop at the edge before chasing the auth or app neighbors.",
                    healthy_markers=["HTTP/1.1 200", "Server: Apache", "Content-Type: text/html"],
                    example_output=_example_output(
                        "HTTP/1.1 200 OK",
                        "Server: Apache",
                        "Content-Type: text/html; charset=UTF-8",
                    ),
                ),
                _command_entry(
                    label="Check representative /algosec-ui/ assets through Apache",
                    command="for path in /algosec-ui/styles.css /algosec-ui/runtime.js /algosec-ui/main.js; do echo \"=== $path ===\"; curl -k -sS -D - -o /tmp/asms-ui-asset.out \"https://127.0.0.1$path\" | sed -n '1,8p'; printf 'BODY_BYTES '; wc -c < /tmp/asms-ui-asset.out; done",
                    expected_signal="Apache returns HTTP 200 for representative CSS and JS assets and each body is non-empty.",
                    interpretation="If the login HTML works but these assets fail, return the wrong type, or come back empty, the login page is still not healthy before Keycloak or Metro are checked.",
                    healthy_markers=["HTTP/1.1 200", "Server: Apache", "Content-Type: text/css", "Content-Type: application/javascript", "BODY_BYTES"],
                    example_output=_example_output(
                        "=== /algosec-ui/styles.css ===",
                        "HTTP/1.1 200 OK",
                        "Server: Apache",
                        "Content-Type: text/css",
                        "BODY_BYTES 758180",
                        "=== /algosec-ui/runtime.js ===",
                        "HTTP/1.1 200 OK",
                        "Content-Type: application/javascript",
                        "BODY_BYTES 2737",
                    ),
                ),
                _command_entry(
                    label="Check Apache routes for login, auth, and app branches",
                    command="grep -R -n -E 'algosec-ui|algosec/suite|ProxyPass|ProxyPassReverse|keycloak|8443|afa/api/v1|8080' /etc/httpd/conf.d 2>/dev/null",
                    expected_signal="Apache config still shows the login redirect, the UI alias, and the auth and app route mapping needed by the ASMS UI path.",
                    interpretation="If the expected proxy targets are missing or wrong, the login path can look healthy while routing requests to the wrong place or nowhere useful.",
                    healthy_markers=["algosec/suite", "algosec-ui", "ProxyPass", "keycloak", "8443", "afa/api/v1", "8080"],
                    example_output=_example_output(
                        '78:RewriteRule "^/algosec/suite/login(.*)$" "/algosec-ui/login" [R]',
                        "299:AliasMatch (?i)^/algosec-ui/(.*)$ /usr/share/fa/suite/client/app/suite-new-ui/$1",
                        "1:<Location /keycloak/>",
                        "2:        ProxyPass https://localhost:8443/ timeout=300",
                        "139:<Location /afa/api/v1>",
                        "140:  ProxyPass http://localhost:8080/afa/api/v1 timeout=18000 retry=0",
                    ),
                ),
            ),
        ),
        _playbook_step(
            step_id="ui-and-proxy-step-3",
            step_number=3,
            action="Check the core ASMS services that a frontline support engineer can actually verify and restart during a live customer session. Stay shallow here: `httpd.service`, `keycloak.service`, `ms-metro.service`, their expected listeners, and one service-specific restart only when the matching shallow check fails.",
            why_this_matters="Most real `ASMS UI is down` cases do not need deep auth-chain forensics. They look more like disk pressure, a stopped service, a half-up service, or an edge path that works only partly. This step keeps the engineer on the shortest practical checks and safe restart boundaries before widening into login-bootstrap, BusinessFlow, FireFlow, or other deeper module theory. On this lab the delegated shallow-service pass showed localhost HTTPS and `/algosec/` healthy, `httpd`, `keycloak`, and related listeners up, and no fresh Apache crash clue. That makes this service-and-restart boundary the right frontline default.",
            next_if_pass="If the shallow service checks look healthy, move to the first usable shell boundary and decide whether the case is still truly `GUI down`.",
            failure_point="the first shallow ASMS service or listener that is down, hung, missing, or does not recover cleanly after a targeted restart",
            decision_if_fail="Stop here and name the failed shallow boundary directly: `httpd.service`, `keycloak.service`, `ms-metro.service`, or the matching listener and route. Do not widen into login-bootstrap or downstream modules until the failed shallow service has either recovered or clearly proven healthy.",
            evidence_to_collect=evidence[2:4],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "httpd.service",
                    interpretation="If Apache is not active, the UI outage already has a clear owner. Restart Apache first, then retest the login page before you widen scope.",
                    healthy_markers=[
                        "Loaded: loaded",
                        "Active: active (running)",
                        "Main PID:",
                        "/usr/sbin/httpd",
                    ],
                    example_output=_example_output(
                        "● httpd.service - The Apache HTTP Server",
                        "   Loaded: loaded (/usr/lib/systemd/system/httpd.service; enabled; vendor preset: disabled)",
                        "   Active: active (running) since Thu 2026-03-26 18:42:56 EDT; 17h ago",
                        " Main PID: 1018 (/usr/sbin/httpd)",
                    ),
                ),
                _service_status_command(
                    "keycloak.service",
                    interpretation="Use this as a shallow auth-service presence check only. If the login page loads but auth seems down and Keycloak is not active, stop here before deeper bootstrap tracing.",
                    healthy_markers=[
                        "Loaded: loaded",
                        "Active: active (running)",
                        "Main PID:",
                        "java",
                    ],
                    example_output=_example_output(
                        "● keycloak.service - Keycloak Service",
                        "   Loaded: loaded (/etc/systemd/system/keycloak.service; enabled; vendor preset: disabled)",
                        "   Active: active (running) since Thu 2026-03-26 18:43:11 EDT; 17h ago",
                        " Main PID: 2745 (java)",
                    ),
                ),
                _service_status_command(
                    "ms-metro.service",
                    interpretation="If the login page is up but the app shell is blank or only partly usable, Metro is the first app-side shallow check and restart boundary.",
                    healthy_markers=[
                        "Loaded: loaded",
                        "Active: active (running)",
                        "Main PID:",
                        "java",
                    ],
                    example_output=_example_output(
                        "● ms-metro.service - ms-metro Application Container",
                        "   Loaded: loaded (/etc/systemd/system/ms-metro.service; disabled; vendor preset: disabled)",
                        "   Active: active (running) since Sat 2026-03-07 13:39:32 EST; 2 weeks 2 days ago",
                        " Main PID: 6012 (java)",
                    ),
                ),
                _command_entry(
                    label="Check the wrapper and listener surfaces once",
                    command="systemctl status algosec-ms.service --no-pager; echo '--- listeners ---'; ss -lntp | grep -E ':(80|443|8080|8443)\\b'",
                    expected_signal="The wrapper unit is present, and the expected shallow listeners remain present on `80`, `443`, `8080`, and `8443`.",
                    interpretation="On this appliance `algosec-ms.service` can be `active (exited)` and still be healthy as a wrapper. The real value here is confirming the main shallow listeners are still present before you blame deeper auth or app logic.",
                    healthy_markers=["Active: active (exited)", "LISTEN", ":80", ":443", ":8080", ":8443"],
                    example_output=_example_output(
                        "● algosec-ms.service - AlgoSec Platform Wrapper",
                        "   Active: active (exited)",
                        "--- listeners ---",
                        'LISTEN 0 511 0.0.0.0:443 0.0.0.0:* users:(("/usr/sbin/httpd",pid=1018,fd=4),...)',
                        'LISTEN 0 100 0.0.0.0:8080 0.0.0.0:* users:(("java",pid=6012,fd=44))',
                        'LISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:(("java",pid=2745,fd=91))',
                    ),
                ),
                _command_entry(
                    label="Restart Apache only if the UI edge check failed",
                    command="sudo systemctl restart httpd.service && sleep 5 && systemctl is-active httpd.service && curl -k -sS -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'",
                    expected_signal="Apache returns to `active`, and the login page immediately answers again through localhost HTTPS.",
                    interpretation="Use this only when the earlier Apache route or status checks failed. Do not spray restarts across other services if Apache already looks healthy.",
                    healthy_markers=["active", "HTTP/1.1 200", "Server: Apache"],
                    example_output=_example_output(
                        "active",
                        "HTTP/1.1 200 OK",
                        "Server: Apache",
                    ),
                ),
                _command_entry(
                    label="Restart Keycloak only if the login page loads but auth service looks down",
                    command="sudo systemctl restart keycloak.service && sleep 10 && systemctl is-active keycloak.service && ss -lntp | grep -E ':8443\\b'",
                    expected_signal="Keycloak returns to `active`, and the auth listener on `8443` is present again.",
                    interpretation="Use this only when the customer can reach the login page but the auth service itself is down or hung. If the login page is not loading at all, Apache is still the earlier stop point.",
                    healthy_markers=["active", "LISTEN", ":8443"],
                    example_output=_example_output(
                        "active",
                        'LISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:(("java",pid=2745,fd=91))',
                    ),
                ),
                _command_entry(
                    label="Restart Metro only if the UI reaches the app shell but it is blank or partly loaded",
                    command="sudo systemctl restart ms-metro.service && sleep 10 && systemctl is-active ms-metro.service && curl -sS http://127.0.0.1:8080/afa/getStatus --max-time 10",
                    expected_signal='Metro returns to `active`, and the heartbeat shows `"isAlive" : true`.',
                    interpretation="Use this only after the case has clearly crossed beyond the login page and the app shell still looks broken. Do not restart Metro first for a pure edge outage.",
                    healthy_markers=["active", '"isAlive" : true'],
                    example_output=_example_output(
                        "active",
                        "{",
                        '  "isAlive" : true',
                        "}",
                    ),
                ),
            ),
        ),
        _playbook_step(
            step_id="ui-and-proxy-step-4",
            step_number=4,
            action="Check whether ASMS opens after login once the edge and core services look healthy. Use the rendered login or home shell to decide whether this is still `GUI down` or whether the user has already crossed into a narrower app workflow problem.",
            why_this_matters="The support question here is whether the case is still a top-level UI outage. If the customer can already reach `/afa/php/home.php` and navigate the devices tree or open `REPORTS`, the case needs a narrower label even if some later workflow still fails.",
            next_if_pass="If the customer reaches a usable shell, branch out of `GUI down` into the narrower failing workflow.",
            failure_point="the first customer-visible usable shell boundary or the nearest Metro-backed home-shell support surface",
            decision_if_fail="Stop here only when the login or home shell itself is not meaningfully usable. If the page renders and the user can navigate the basic shell, stop calling it `GUI down` and move to the narrower workflow playbook instead. If the shell is blank or partly loaded and Metro heartbeat or nearby app traffic is unhealthy, keep the stop point on the Metro-backed shell path before widening further.",
            evidence_to_collect=evidence[2:4],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "ms-metro.service",
                    interpretation="If Metro is not running, the UI may open only partly or fail after the first page.",
                    healthy_markers=[
                        "Loaded: loaded",
                        "Active: active (running)",
                        "Main PID:",
                        "java",
                    ],
                    example_output=_example_output(
                        "● ms-metro.service - ms-metro Application Container",
                        "   Loaded: loaded (/etc/systemd/system/ms-metro.service; disabled; vendor preset: disabled)",
                        "   Active: active (running) since Sat 2026-03-07 13:39:32 EST; 2 weeks 2 days ago",
                        " Main PID: 6012 (java)",
                    ),
                ),
                _command_entry(
                    label="Check Metro listener",
                    command="ss -lntp | grep -E ':8080\\b'",
                    expected_signal="Port 8080 is listening for ms-metro.",
                    interpretation="If port 8080 is missing, the UI backend route has no working target.",
                    healthy_markers=["LISTEN", ":8080", "java"],
                    example_output=_example_output(
                        'LISTEN 0 100 0.0.0.0:8080 0.0.0.0:* users:(("java",pid=6012,fd=44))',
                    ),
                ),
                _command_entry(
                    label="Compare the first usable shell gate with Metro bootstrap clues",
                    command="minute=$(grep -E '/afa/php/SuiteLoginSessionValidation.php|/afa/php/home.php|dynamic\\.js\\.php|/afa/php/home.js' /var/log/httpd/ssl_access_log | tail -n 1 | sed -E 's/.*\\[([^]]{17})[^]]*\\].*/\\1/'); printf 'WINDOW=%s\\n' \"$minute\"; printf '=== apache shell minute ===\\n'; grep \"$minute\" /var/log/httpd/ssl_access_log | grep -E '/afa/php/SuiteLoginSessionValidation.php|/afa/php/home.php|dynamic\\.js\\.php|/afa/php/home.js' | tail -n 20; printf '=== metro same minute ===\\n'; grep \"$minute\" /data/ms-metro/logs/localhost_access_log.txt | grep -E '/afa/getStatus|/afa/api/v1/config\\?|/afa/api/v1/session/extend|/afa/api/v1/config/all/noauth' | tail -n 20",
                    expected_signal="The same shell-transition minute shows `SuiteLoginSessionValidation.php -> /afa/php/home.php -> dynamic.js.php/home.js` on the Apache side and the nearest Metro bootstrap clues such as `GET /afa/getStatus`, `GET /afa/api/v1/config?...`, `POST /afa/api/v1/session/extend?...`, or `GET /afa/api/v1/config/all/noauth?...` on the Metro side.",
                    interpretation="Use this to keep the stop point narrow and same-window. If `SuiteLoginSessionValidation.php` appears but `/afa/php/home.php` does not appear in that same minute, stop on the pre-shell gate before blaming Metro. If `/afa/php/home.php` appears but the same-minute Metro bootstrap clues are missing or failing, stop on the Metro-backed home-shell path. If both sides look healthy in the same shell-transition minute, stop calling the case `GUI down` and branch into the later failing workflow instead. This is still a comparison check, not proof that every nearby Metro route is a hard first-shell dependency.",
                    healthy_markers=["WINDOW=", "/afa/php/SuiteLoginSessionValidation.php", "/afa/php/home.php", "dynamic.js.php", "GET /afa/getStatus", "/afa/api/v1/session/extend", "/afa/api/v1/config/all/noauth"],
                    example_output=_example_output(
                        "WINDOW=25/Mar/2026:17:29",
                        "=== apache shell minute ===",
                        '127.0.0.1 - - [25/Mar/2026:16:09:01 -0400] "POST /afa/php/SuiteLoginSessionValidation.php?clean=false HTTP/1.1" 200 65',
                        '127.0.0.1 - - [25/Mar/2026:16:09:09 -0400] "GET /afa/php/home.php HTTP/1.1" 200 35713',
                        '127.0.0.1 - - [25/Mar/2026:16:09:10 -0400] "GET /afa/php/JSlib1768164240/dynamic.js.php?sid=abc123fresh HTTP/1.1" 200 23846',
                        "=== metro same minute ===",
                        '127.0.0.1 [25/Mar/2026:17:29:35 -0400] [http-nio-0.0.0.0-8080-exec-7] "POST /afa/api/v1/session/extend?session=abc123fresh&domain=0 HTTP/1.1" 200 - 246 33410 -',
                        '127.0.0.1 [25/Mar/2026:17:29:35 -0400] [http-nio-0.0.0.0-8080-exec-8] "GET /afa/api/v1/config/all/noauth?domain=0 HTTP/1.1" 200 812 1543 33411 -',
                        '127.0.0.1 [25/Mar/2026:17:29:43 -0400] [http-nio-0.0.0.0-8080-exec-9] "GET /afa/getStatus HTTP/1.1" 200 33 506 33738 -',
                    ),
                ),
                _command_entry(
                    label="Check post-home shell and dashboard hydration traffic",
                    command="printf '=== apache ===\\n'; grep -E '/afa/php/home.php|dynamic\\.js\\.php|/afa/php/commands.php\\?cmd=DISPLAY_ISSUES_CENTER|/fa/tree/create|/afa/php/prod_stat.php|/fa/tree/get_update|FireFlowBridge.js|/afa/php/logo.php|/afa/api/v1/license|/ms-watchdog/v1/api/issues-center/issues/countAll' /var/log/httpd/ssl_access_log | tail -n 60; printf '=== metro ===\\n'; grep -E '/afa/getStatus|/afa/api/v1/bridge/refresh|/afa/api/v1/license|/afa/api/v1/config\\?|/afa/api/v1/session/extend|/afa/api/v1/config/all/noauth' /data/ms-metro/logs/localhost_access_log.txt | tail -n 30",
                    expected_signal="Recent lines show `/afa/php/home.php`, the first dashboard-hydration routes such as `dynamic.js.php`, `DISPLAY_ISSUES_CENTER`, `/fa/tree/create`, `/afa/php/prod_stat.php`, or `/fa/tree/get_update`, and the nearby Metro clues such as `GET /afa/getStatus`, `GET /afa/api/v1/license`, or the same-minute `config` and `session/extend` requests that surround the first usable shell.",
                    interpretation="Use this to keep the post-home model honest. On this lab the first post-home activity was a summary dashboard and issue-center hydration path before deeper operator actions. `DEVICES` mainly refreshed shell context and tree state in the bounded pass, while the first clean deeper action isolated so far was `Analyze`, which mapped to `GET_ANALYSIS_OPTIONS` after the landing shell and device context were already visible. Treat that `Analyze` handoff as the start of a later workflow branch, not as proof that the initial home shell is unhealthy. The real `Start Analysis` step crosses into `cmd=ANALYZE` and `RunFaServer(...)`, so it should not be used as a casual first-shell check. The device-context tabs are also already later content branches: `POLICY` posts `GET_POLICY_TAB` and `GET_DEVICE_POLICY`, `CHANGES` uses `GET_MONITORING_CHANGES`, and `REPORTS` uses `GET_REPORTS`. For support classification, once the customer can navigate the devices tree and reach those later content surfaces, stop calling the case `GUI down` and branch into the more specific failing workflow instead. Keep these shell and dashboard routes inside the ASMS playbook as supporting clues, not as first-class gates by themselves. `GET /afa/getStatus` is still the strongest immediate Metro clue after the home shell appears. `GET /afa/api/v1/config?...` and `POST /afa/api/v1/session/extend?...` are now more strongly tied to the fresh login session because the latest pass matched them to the new `PHPSESSID`, but they are still not proven first-shell requirements. `GET /afa/api/v1/license` and `GET /afa/api/v1/config/all/noauth?domain=0` also appeared in the same fresh-session minute and remain supporting clues rather than proven gates. `POST /afa/api/v1/bridge/refresh?...` stayed tied to a different long-lived session in this lab pass, so treat it as nearby background traffic unless a reproduced browser minute proves otherwise. In a later CDP browser-layer pass, the block rules matched only the early `config/PRINT_TABLE_IN_NORMAL_VIEW` probe and did not record real block events for the fresh-session `license`, `config`, `config/all/noauth`, or `session/extend` traffic, so do not treat browser-side blocking alone as proof that those routes gate the first usable shell. A later Apache seam mutation returned repeated `403` responses for `/afa/external` and still left a fully usable `/afa/php/home.php` shell, and a second top-level Apache mutation on `/afa/api/v1` also left the home shell fully usable and still did not cleanly own the fresh-session `config` and `session/extend` routes. If the landing shell is healthy but a deeper operator action fails, pivot to the first action-specific branch instead of blaming the landing shell. If `ms-watchdog` issue-count calls appear from another client address, treat them as a later subsystem candidate unless the reproduced browser minute proves they are your first stop point.",
                    healthy_markers=["/afa/php/home.php", "dynamic.js.php", "DISPLAY_ISSUES_CENTER", "/fa/tree/create", "/afa/php/prod_stat.php", "/fa/tree/get_update", "GET /afa/getStatus", "GET /afa/api/v1/license", "POST /afa/api/v1/session/extend", "GET /afa/api/v1/config/all/noauth"],
                    example_output=_example_output(
                        "=== apache ===",
                        '127.0.0.1 - - [25/Mar/2026:17:29:38 -0400] "GET /afa/php/home.php HTTP/1.1" 200 35714',
                        '127.0.0.1 - - [26/Mar/2026:05:13:14 -0400] "GET /afa/php/JSlib1768164240/dynamic.js.php?sid=nqo0c2b0dda9d9a4gas11vc6h6 HTTP/1.1" 200 23846',
                        '127.0.0.1 - - [26/Mar/2026:05:13:15 -0400] "GET /afa/php/commands.php?cmd=DISPLAY_ISSUES_CENTER HTTP/1.1" 200 741',
                        '127.0.0.1 - - [26/Mar/2026:05:13:15 -0400] "POST /fa/tree/create HTTP/1.1" 200 4211',
                        '127.0.0.1 - - [26/Mar/2026:05:13:19 -0400] "GET /afa/php/prod_stat.php HTTP/1.1" 200 169',
                        '127.0.0.1 - - [26/Mar/2026:05:13:19 -0400] "POST /fa/tree/get_update HTTP/1.1" 200 1642',
                        '127.0.0.1 - - [25/Mar/2026:17:29:39 -0400] "GET /afa/php/JSlib1768164240/FireFlowBridge.js HTTP/1.1" 200 484',
                        '127.0.0.1 - - [25/Mar/2026:17:29:39 -0400] "GET /afa/php/logo.php HTTP/1.1" 200 -',
                        '127.0.0.1 - - [25/Mar/2026:17:29:36 -0400] "GET /afa/api/v1/license HTTP/1.1" 200 311',
                        "=== metro ===",
                        '127.0.0.1 [25/Mar/2026:17:29:35 -0400] [http-nio-0.0.0.0-8080-exec-7] "POST /afa/api/v1/session/extend?session=abc123fresh&domain=0 HTTP/1.1" 200 - 246 33410 -',
                        '127.0.0.1 [25/Mar/2026:17:29:35 -0400] [http-nio-0.0.0.0-8080-exec-8] "GET /afa/api/v1/config/all/noauth?domain=0 HTTP/1.1" 200 812 1543 33411 -',
                        '127.0.0.1 [25/Mar/2026:17:29:43 -0400] [http-nio-0.0.0.0-8080-exec-9] "GET /afa/getStatus HTTP/1.1" 200 33 506 33738 -',
                        '127.0.0.1 [25/Mar/2026:17:29:44 -0400] [http-nio-0.0.0.0-8080-exec-8] "POST /afa/api/v1/bridge/refresh?session=kk4msqvndoc0c8lmjka8i93vj4&domain=0 HTTP/1.1" 200 - 1739954 33412 -',
                    ),
                ),
                _command_entry(
                    label="Check whether the case already crossed into a later content branch",
                    command="grep -E '/fa/tree/create|/afa/php/commands.php\\?cmd=(GET_REPORTS|GET_POLICY_TAB|GET_DEVICE_POLICY|GET_MONITORING_CHANGES|GET_ANALYSIS_OPTIONS|GET_ANALYZE_DATA|ANALYZE)' /var/log/httpd/ssl_access_log | tail -n 40",
                    expected_signal="Recent Apache lines show the device tree refresh plus any later content-branch markers such as `GET_REPORTS`, `GET_POLICY_TAB`, `GET_DEVICE_POLICY`, `GET_MONITORING_CHANGES`, or `GET_ANALYSIS_OPTIONS`.",
                    interpretation="Use this as the branch-out decision after the first usable shell is already visible. `tree/create` by itself is still only shell-context evidence, but once a later content marker like `GET_REPORTS`, `GET_POLICY_TAB`, `GET_MONITORING_CHANGES`, or `GET_ANALYSIS_OPTIONS` appears, stop treating the case as top-level `GUI down` and switch to the narrower failing workflow instead. Keep `cmd=ANALYZE` as a later branch than the dialog-opening `GET_ANALYSIS_OPTIONS` step.",
                    healthy_markers=["/fa/tree/create", "GET_REPORTS", "GET_POLICY_TAB", "GET_DEVICE_POLICY", "GET_MONITORING_CHANGES", "GET_ANALYSIS_OPTIONS"],
                    example_output=_example_output(
                        '127.0.0.1 - - [26/Mar/2026:05:13:15 -0400] "POST /fa/tree/create HTTP/1.1" 200 4211',
                        '127.0.0.1 - - [26/Mar/2026:05:16:42 -0400] "GET /afa/php/commands.php?cmd=GET_REPORTS HTTP/1.1" 200 812',
                        '127.0.0.1 - - [26/Mar/2026:05:18:09 -0400] "GET /afa/php/commands.php?cmd=GET_POLICY_TAB HTTP/1.1" 200 2213',
                        '127.0.0.1 - - [26/Mar/2026:05:18:09 -0400] "GET /afa/php/commands.php?cmd=GET_DEVICE_POLICY HTTP/1.1" 200 744',
                        '127.0.0.1 - - [26/Mar/2026:05:20:41 -0400] "GET /afa/php/commands.php?cmd=GET_ANALYSIS_OPTIONS HTTP/1.1" 200 1304',
                    ),
                ),
                _command_entry(
                    label="Check Metro heartbeat",
                    command="curl -sS http://127.0.0.1:8080/afa/getStatus --max-time 10",
                    expected_signal='The JSON response shows `"isAlive" : true`.',
                    interpretation="If the heartbeat hangs, errors, or returns a different value, Metro is not healthy enough for the ASMS UI path.",
                    healthy_markers=['"isAlive" : true'],
                    example_output=_example_output(
                        "{",
                        '  "isAlive" : true',
                        "}",
                    ),
                ),
                _command_entry(
                    label="Check Metro app traffic",
                    command="grep -E '/afa/getStatus|/afa/api/v1/config\\?|/afa/api/v1/license|/afa/api/v1/session/extend|/afa/api/v1/config/all/noauth' /data/ms-metro/logs/localhost_access_log.txt | tail -n 40",
                    expected_signal="Recent access lines show normal 200 responses for the Metro heartbeat and the light authenticated `/afa/api/v1/...` paths that appear immediately after the home page loads.",
                    interpretation="If heartbeat works but the same-minute `/afa/api/v1/...` lines stop, shift to 4xx or 5xx, or never appear around `/afa/php/home.php`, Metro may be up without serving real home-refresh work. Treat `GET /afa/getStatus` as the strongest immediate Metro clue after the first usable shell appears. Keep `license`, `config`, `config/all/noauth`, and `session/extend` as supporting same-minute clues until a fresh-session isolation pass proves one of them is a true first-shell gate. The strongest fresh-session tie now belongs to `config` and `session/extend`, because the latest pass matched them directly to the new `PHPSESSID`, but that still does not prove they gate the first usable shell. The later CDP browser-layer pass did not own the real fresh-session `license`, `config`, `config/all/noauth`, or `session/extend` traffic, so the next meaningful experiment is proxy-side or server-side isolation rather than another browser-side guess. A later Apache seam mutation denied `/afa/external` and still left a fully usable home shell, and a second top-level Apache mutation on `/afa/api/v1` still did not cleanly own the fresh-session `config` and `session/extend` routes. That means the next useful seam is narrower than a family-wide Apache deny, likely around the paired config surfaces themselves. Do not elevate `bridge/refresh` from this check alone because the current lab evidence tied it to a different long-lived session.",
                    healthy_markers=["GET /afa/getStatus", " 200 ", "/afa/api/v1/license", "/afa/api/v1/session/extend", "/afa/api/v1/config/all/noauth"],
                ),
                _command_entry(
                    label="Check what Metro is busy doing",
                    command="ps -p $(cat /var/run/ms-metro/ms-metro.pid) -o pid,etime,%cpu,%mem,nlwp,cmd --cols 160",
                    expected_signal="The Metro JVM is present, has a stable elapsed runtime, and its CPU, memory, and thread count look reasonable for the current case.",
                    interpretation="If CPU, memory, or thread count looks unexpectedly high or unstable, treat Metro resource pressure or a stuck JVM as part of the failure.",
                    healthy_markers=["PID", "ELAPSED", "%CPU", "%MEM", "NLWP", "java"],
                ),
                _command_entry(
                    label="Check Metro JVM error clues",
                    command="grep -n -i -E 'error|exception|failed|caused by|outofmemory|unable|refused|timed out' /data/ms-metro/logs/catalina.out | tail -n 40",
                    expected_signal="No fresh Metro error signatures appear, or the returned lines clearly point to the real Java, dependency, or application failure.",
                    interpretation="Use this inside the Metro command pack after the listener, heartbeat, app-traffic, and JVM-activity checks if the app branch still looks unhealthy. It keeps the Metro-specific clue inside the service pack instead of forcing the engineer to jump ahead to a generic final log sweep.",
                    healthy_markers=["No output is often normal", "Error", "Exception", "Caused by", "Failed"],
                ),
            ),
        ),
        _playbook_step(
            step_id="ui-and-proxy-step-5",
            step_number=5,
            action="If the shallow host, Apache, service, and first-shell checks still leave the stop point unclear, use one bounded reproduced journey plus logs to decide whether the deeper issue sits in login bootstrap, auth, or a later app path.",
            why_this_matters="This is escalation work, not the frontline default. Only move here after the simpler service-up, route-up, and shell-usable questions have failed to explain the case. The goal is to name the first deeper stop point without turning every normal support session into a code-path excavation.",
            next_if_pass="If the stop point is still unclear, move to the narrower escalation path that matches the reproduced journey.",
            failure_point="the first deeper auth, bootstrap, or app seam that the reproduced journey actually proves",
            decision_if_fail="Stop here and name the closest deeper seam you can defend from the reproduced journey. Keep BusinessFlow, FireFlow, AFA, and later auth hops conditional on what the reproduced path actually reached. If the customer has already crossed the devices-tree-plus-`REPORTS` boundary, branch out of `GUI down` instead of keeping the case at this top-level playbook.",
            evidence_to_collect=evidence[2:4],
            recommended_commands=_command_bundle(
                _command_entry(
                    label="Replay one browser-like login journey with cookies before chasing neighbors",
                    command="rm -f /tmp/asms-journey.cookies /tmp/asms-journey.headers /tmp/asms-journey.body; curl -k -sS -L -c /tmp/asms-journey.cookies -b /tmp/asms-journey.cookies -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.9' -H 'Upgrade-Insecure-Requests: 1' -D /tmp/asms-journey.headers -o /tmp/asms-journey.body https://127.0.0.1/algosec/suite/login; printf '=== headers ===\\n'; sed -n '1,30p' /tmp/asms-journey.headers; printf '=== cookies ===\\n'; cat /tmp/asms-journey.cookies 2>/dev/null; printf '=== html markers ===\\n'; grep -E 'base href=|runtime.js|main.js|styles.css' /tmp/asms-journey.body | head -n 10",
                    expected_signal="The replay proves the legacy suite redirect, the static shell markers, and whether the browser-like startup already picked up cookies before any deeper auth path is tested.",
                    interpretation="Use this as the bounded reproduction anchor for one minute of Apache logs. If it only proves the redirect and static shell, the first real downstream auth or app hop is still unproven.",
                    healthy_markers=["HTTP/1.1 302", "Location: https://127.0.0.1/algosec-ui/login", "<base href=\"/algosec-ui/\">", "runtime.js", "main.js"],
                    example_output=_example_output(
                        "HTTP/1.1 302 Found",
                        "Location: https://127.0.0.1/algosec-ui/login",
                        '<base href="/algosec-ui/">',
                        '<script src="runtime.js?v=1768164271" type="module"></script>',
                        '<script src="main.js?v=1768164271" type="module"></script>',
                    ),
                ),
                _command_entry(
                    label="Correlate the reproduced minute in Apache access logs",
                    command="grep -E '/algosec/suite/login|/algosec-ui/login|/algosec-ui/(styles.css|runtime.js|main.js)|/afa/php/commands.php\\?cmd=IS_SESSION_ACTIVE|/afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW|/seikan/login/setup|/aff/api/internal/noauth/getStatus|/BusinessFlow|/afa/php/SuiteLoginSessionValidation.php|/keycloak/|/FireFlow/SelfService/CheckAuthentication/|/afa/php/home.php|/afa/api/v1' /var/log/httpd/ssl_access_log | tail -n 120",
                    expected_signal="Recent Apache access lines show the same reproduced journey and make it clear whether the request stopped at the shell, moved through the legacy setup and session-validation paths, and only later reached downstream modules such as BusinessFlow, Keycloak, FireFlow, the PHP home page, and Metro-backed app paths.",
                    interpretation="If the reproduced journey only shows /algosec/suite/login and /algosec-ui/ lines, the first real downstream hop is still unproven. If `/seikan/login/setup` appears first, treat it as the first observed JS-triggered post-shell request. If `/afa/php/SuiteLoginSessionValidation.php` is the first auth-triggering line, keep the failure point there unless later module lines actually appear in the same journey. If `/BusinessFlow` lights up but `/afa/api/v1` only appears after `/afa/php/home.php`, treat Metro as a later post-login app branch, not the first auth hop.",
                    healthy_markers=["/algosec/suite/login", "/algosec-ui/login", " 200 ", " 302 "],
                    example_output=_example_output(
                        '127.0.0.1 - - [25/Mar/2026:16:09:01 -0400] "GET /algosec-ui/login HTTP/1.1" 200 13345',
                        '127.0.0.1 - - [25/Mar/2026:16:09:00 -0400] "GET /seikan/login/setup HTTP/1.1" 200 217',
                        '127.0.0.1 - - [25/Mar/2026:16:09:01 -0400] "GET /BusinessFlow/login HTTP/1.1" 302 30',
                        '127.0.0.1 - - [25/Mar/2026:16:09:01 -0400] "POST /afa/php/SuiteLoginSessionValidation.php?clean=false HTTP/1.1" 200 65',
                        '127.0.0.1 - - [25/Mar/2026:16:09:02 -0400] "POST //keycloak/realms/master/protocol/openid-connect/token? HTTP/1.1" 200 1562',
                        '127.0.0.1 - - [25/Mar/2026:16:09:06 -0400] "POST /BusinessFlow/rest/v1/login HTTP/1.1" 200 49',
                        '127.0.0.1 - - [25/Mar/2026:16:09:09 -0400] "GET /afa/php/home.php HTTP/1.1" 200 35713',
                    ),
                ),
                _command_entry(
                    label="Review recent Apache/HTTPD logs",
                    command="journalctl -u httpd.service -n 50 --no-pager",
                    expected_signal="No obvious disk, permission, startup, or crash errors appear in recent lines.",
                    interpretation="If recent Apache/HTTPD lines show errors, stay on that clue first.",
                ),
                _command_entry(
                    label="Review recent Keycloak logs",
                    command="tail -n 80 /var/log/keycloak/keycloak.log",
                    expected_signal="Recent lines show healthy startup or a clear auth, database, TLS, or startup clue.",
                    interpretation="If recent Keycloak lines show errors, stay on that clue first.",
                    healthy_markers=["started", "Listening on", "https://0.0.0.0:8443", "hostname:"],
                ),
                _command_entry(
                    label="Review Metro error clues",
                    command="grep -n -i -E 'error|exception|failed|caused by|outofmemory|unable|refused|timed out' /data/ms-metro/logs/catalina.out | tail -n 40",
                    expected_signal="No fresh Metro error signatures appear, or the returned lines clearly point to the real Java, dependency, or application failure.",
                    interpretation="Use this only after the traffic and JVM checks if you still need a narrower Java clue.",
                    healthy_markers=["No output is often normal", "Error", "Exception", "Caused by", "Failed"],
                ),
            ),
        ),
    ]


def _core_aff_playbook_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = flow["evidence_to_collect_next"]
    aff_path = _flow_path_checkpoint(flow, "aff-boot.service")
    aff_config = _first_or((aff_path or {}).get("config_checkpoints") or [], "/etc/httpd/conf.d/aff.conf")
    aff_ports = (aff_path or {}).get("listener_ports", ["1989"])
    postgres_detail = _flow_service_detail(flow, "postgresql.service")
    return [
        _playbook_step(
            step_id="core-aff-step-1",
            step_number=1,
            action="Identify the failing FireFlow action and confirm that the symptom is tied to /FireFlow/api or /aff/api.",
            next_if_pass="Continue to aff-boot and route validation.",
            failure_point="Domain mismatch",
            decision_if_fail="If the symptom is not tied to FireFlow, switch to a different domain playbook instead of staying here.",
            evidence_to_collect=evidence[:1],
            recommended_commands=_command_bundle(
                _config_command(
                    aff_config,
                    needle="1989",
                    interpretation="Use the known proxy mapping to confirm the FireFlow path really terminates at the expected backend.",
                ),
            ),
        ),
        _playbook_step(
            step_id="core-aff-step-2",
            step_number=2,
            action="Confirm aff-boot.service is active and that the failing FireFlow route still proxies to localhost:1989.",
            next_if_pass="Continue to database validation.",
            failure_point="aff-boot.service or 1989 route",
            decision_if_fail="Treat aff-boot.service or the 1989 route as the current failure point.",
            evidence_to_collect=evidence[:2],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "aff-boot.service",
                    interpretation="If aff-boot is not active, stop here and treat the FireFlow service itself as the failure point. For this seam, aff-boot is a closer readable dependency than ActiveMQ, even though the latest staged pass proved that the live FireFlow runtime also talks to the broker on 61616.",
                ),
                _listener_command(
                    aff_ports or ["1989"],
                    label="Check FireFlow listener",
                    interpretation="If the FireFlow listener is missing, the backend route has nothing healthy to terminate to.",
                ),
                _config_command(
                    aff_config,
                    needle="1989",
                    interpretation="If the proxy config no longer points to 1989, the FireFlow request path may be broken even when the service is up.",
                ),
                _command_entry(
                    label="Check the FireFlow session path behind BusinessFlow AFF connection",
                    command="curl -sk -D - https://localhost/FireFlow/api/session | sed -n '1,12p'; echo '--- direct aff-boot ---'; curl -sk -D - https://localhost:1989/aff/api/external/session | sed -n '1,12p'",
                    expected_signal="The Apache-fronted FireFlow session route and the direct aff-boot session route should return the same invalid-session shape.",
                    interpretation="Use this to confirm that Apache still owns the session hop into aff-boot before moving deeper. If the two responses diverge, stay on Apache proxying, route ownership, or aff-boot listener issues rather than jumping ahead to later FireFlow workflow checks.",
                    healthy_markers=["/FireFlow/api/session", "/aff/api/external/session", "invalid session", "HTTP/"],
                ),
                _command_entry(
                    label="Check aff-boot database and broker sockets",
                    command="pid=$(systemctl show -p MainPID --value aff-boot.service); echo PID=$pid; lsof -Pan -p \"$pid\" -i 2>/dev/null | egrep '(:1989|:5432|:61616)' || true",
                    expected_signal="The aff-boot Java PID still owns the 1989 listener and usually shows local PostgreSQL and broker connections for its live runtime.",
                    interpretation="Use this to separate a healthy FireFlow runtime from a partial one. Current lab evidence shows that aff-boot can hold live database and ActiveMQ sockets at the same time, so a missing 61616 connection is a later supporting clue, not a first-pass route failure by itself.",
                    healthy_markers=["PID=", ":1989", ":5432", ":61616"],
                    example_output=_example_output(
                        "PID=1687",
                        "java 1687 root   24u  IPv6 ... TCP *:1989 (LISTEN)",
                        "java 1687 root  146u  IPv6 ... TCP 127.0.0.1:20770->127.0.0.1:5432 (ESTABLISHED)",
                        "java 1687 root  165u  IPv6 ... TCP 127.0.0.1:21910->127.0.0.1:61616 (ESTABLISHED)",
                    ),
                ),
            ),
        ),
        _playbook_step(
            step_id="core-aff-step-3",
            step_number=3,
            action="Confirm postgresql.service is active and local database access is healthy before assuming a FireFlow-only fault.",
            next_if_pass="Continue to FireFlow log review.",
            failure_point="postgresql.service",
            decision_if_fail="Treat postgresql.service as the current failure point for this customer issue.",
            evidence_to_collect=evidence[1:3],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "postgresql.service",
                    interpretation="If the database is not active, FireFlow symptoms are likely downstream of data availability.",
                ),
                _listener_command(
                    postgres_detail.get("listener_ports", ["5432"]),
                    label="Check database listener",
                    interpretation="If the database listener is missing, focus on database startup, permissions, or bind issues.",
                ),
            ),
        ),
        _playbook_step(
            step_id="core-aff-step-4",
            step_number=4,
            action="Collect the latest FireFlow-related error lines or status output and decide whether the failure stays in FireFlow logic or must move deeper into dependencies.",
            next_if_pass=flow["next_dependency_focus"] or "Use the collected FireFlow evidence to choose the next app-specific check.",
            failure_point="FireFlow runtime evidence incomplete",
            decision_if_fail="If you cannot collect the logs, escalate with the route, service, and database checks already captured.",
            evidence_to_collect=evidence[1:3],
            recommended_commands=_command_bundle(
                _journal_command(
                    "aff-boot.service",
                    interpretation="Look for permission errors, startup failures, database errors, or Metro-adjacent dependency errors first. Broker theory is now real for this seam because aff-boot holds live 61616 sockets, but the reproduced login-handoff minute still centered on auth, session, and REST activity rather than broker-side signals. A later FireFlow workflow minute now sharpened the same rule further: `CommandsDispatcher` plus nearby AFF reads rolled into `ms-configuration` unified-swagger refresh and an `AutoDiscovery` 502 without same-minute broker evidence. A second `CommandsDispatcher` pass on the `2026-03-21 04:30 EDT` cadence also stayed synchronous, matching journal refresh and `UserSession` fetches rather than queue-backed progression. The next non-`UserSession` branch still did not prove ticket progression either: it clustered around config broadcast plus `Authentication:authenticateUser` and `User:GetUserInfo`. A later targeted hunt on the same lab then showed a different boundary: FireFlow was enabled and polling AFF or AFA surfaces successfully, but `syslog_ticket_changes.pl` reported `Total tickets in DB: 0`, so there was no live request branch to correlate. Keep JMS and queue suspicion after the closer FireFlow route, service, and database checks unless the same failing minute points directly at broker activity, and if the lab appears empty from a ticket-workflow perspective, seed or replay a real request before another progression slice.",
                ),
                _command_entry(
                    label="Check same-minute configuration refresh clues",
                    command="grep -E 'AlgoSec_FireFlow|AlgoSec_ApplicationDiscovery|swagger|BAD_GATEWAY' /data/algosec-ms/logs/ms-configuration.log | tail -n 40; echo '--- apache ---'; grep -E 'AutoDiscovery|swagger/v2/api-docs' /var/log/httpd/ssl_error_log | tail -n 20",
                    expected_signal="Recent lines either stay quiet or show whether the failing FireFlow minute rolled into unified swagger refresh, downstream service-definition fetches, or a concrete Apache-side 502.",
                    interpretation="Use this when the FireFlow action minute includes `CommandsDispatcher`, `/FireFlow/api/session`, or nearby AFF config reads and then drifts into swagger or service-definition work. If `ms-configuration` and Apache show same-minute refresh or downstream 502 clues, pivot next to configuration-service troubleshooting before promoting ActiveMQ.",
                    healthy_markers=["AlgoSec_FireFlow", "swagger", "AutoDiscovery", "BAD_GATEWAY"],
                ),
                _command_entry(
                    label="Check whether CommandsDispatcher stayed on journal or session maintenance",
                    command="grep -E 'CommandsDispatcher|/journal/getChangesInOrigRulesByDate|/FireFlow/api/session|/session/extend' /var/log/httpd/ssl_access_log | tail -n 60",
                    expected_signal="The returned window shows whether the FireFlow branch stayed on journal refresh and session maintenance or moved into a different workflow shape.",
                    interpretation="Use this before escalating to ActiveMQ for a `CommandsDispatcher` minute. If the same window keeps resolving to journal refresh, `/FireFlow/api/session`, or `/session/extend`, treat it as synchronous maintenance-style traffic and keep broker inspection later.",
                    healthy_markers=["CommandsDispatcher", "/journal/getChangesInOrigRulesByDate", "/FireFlow/api/session", "/session/extend"],
                ),
                _command_entry(
                    label="Check whether the branch is config broadcast plus FireFlow auth bootstrap",
                    command="grep -E 'application-afaConfig.properties|notify ActiveMq broadcast|MicroserviceConfigurationBroadcast|Refreshing application context' /data/algosec-ms/logs/ms-configuration.log /data/algosec-ms/logs/ms-initial-plan.log | tail -n 60; echo '--- fireflow ---'; grep -E 'authenticateUser|GetUserInfo' /usr/share/fireflow/var/log/fireflow.log /usr/share/fireflow/var/log/fireflow.log.1 /usr/share/fireflow/var/log/fireflow.log.2 2>/dev/null | tail -n 40",
                    expected_signal="The returned window shows whether the same FireFlow minute is really a config-broadcast ripple with nearby authentication and user bootstrap rather than a ticket-progression branch.",
                    interpretation="Use this when a non-`UserSession` dispatcher destination appears, but the nearby minute still looks like setup work. If config broadcast, `MicroserviceConfigurationBroadcast`, `Authentication:authenticateUser`, and `User:GetUserInfo` cluster together, classify the branch as config-propagation plus auth bootstrap and keep approval, worker, or broker escalation later.",
                    healthy_markers=["application-afaConfig.properties", "MicroserviceConfigurationBroadcast", "authenticateUser", "GetUserInfo"],
                ),
                _command_entry(
                    label="Check whether FireFlow is active but the lab has zero tickets",
                    command="grep -E 'Total tickets in DB|tickets updated in the last 10 minutes|setup/fireflow/is_enabled|allowedDevices|brandConfig' /usr/share/fireflow/var/log/fireflow.log /usr/share/fireflow/var/log/fireflow.log.1 /usr/share/fireflow/var/log/fireflow.log.2 2>/dev/null | tail -n 80; echo '--- apache ---'; grep -E '/setup/fireflow/is_enabled|/allowedDevices|/bridge/refresh|/config/all/noauth' /var/log/httpd/ssl_access_log | tail -n 40",
                    expected_signal="The returned window shows whether FireFlow is enabled and polling neighboring dependencies successfully while still reporting zero tickets in DB.",
                    interpretation="Use this when FireFlow looks enabled but every progression hunt collapses back into setup, config, AFF bridge, and session-maintenance traffic. If the same windows show `Total tickets in DB: 0` or no recent ticket updates, stop treating the lab as a populated workflow environment. Seed or replay one real FireFlow request before another approval, implementation, review, or ActiveMQ-oriented slice.",
                    healthy_markers=["Total tickets in DB: 0", "setup/fireflow/is_enabled", "allowedDevices", "brandConfig"],
                ),
            ),
        ),
    ]


def _microservice_platform_playbook_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = flow["evidence_to_collect_next"]
    likely_services = ", ".join(flow["likely_failing_services"][:3])
    first_service = flow["likely_failing_services"][0] if flow["likely_failing_services"] else "ms-batch-application.service"
    first_path = _flow_path_checkpoint(flow, first_service)
    first_route = _first_or((first_path or {}).get("route_checkpoints") or [], {})
    first_port = first_route.get("target_ports") or _first_or((first_path or {}).get("listener_ports") or [], "unknown")
    first_config = _first_or((first_path or {}).get("config_checkpoints") or [], None)
    return [
        _playbook_step(
            step_id="microservice-platform-step-1",
            step_number=1,
            action="Identify the exact failing feature or ms-* path in the customer session so the diagnostic path stays anchored to one concrete product behavior.",
            next_if_pass="Continue to wrapper and target-service validation.",
            failure_point="Feature path not isolated",
            decision_if_fail="If the failing feature cannot be isolated, collect the customer symptom and stay at the domain level before picking a narrower path.",
            evidence_to_collect=evidence[:2],
            recommended_commands=[],
        ),
        _playbook_step(
            step_id="microservice-platform-step-2",
            step_number=2,
            action=f"Confirm algosec-ms.service completed successfully and that the likely target service set is healthy: {likely_services}.",
            next_if_pass="Continue to routed-path validation.",
            failure_point="algosec-ms.service or first failing ms-* service",
            decision_if_fail="Treat algosec-ms.service or the first failing ms-* service as the current failure point.",
            evidence_to_collect=evidence[1:3],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "algosec-ms.service",
                    interpretation="If this wrapper is unhealthy, start at the shared microservice platform before chasing one feature path.",
                ),
                _service_status_command(
                    first_service,
                    interpretation="If the target ms-* service is unhealthy, treat that service as the current failure point.",
                ),
            ),
        ),
        _playbook_step(
            step_id="microservice-platform-step-3",
            step_number=3,
            action="Confirm the customer-facing failing path still maps to the expected local target port for that microservice.",
            next_if_pass="Continue to shared-configuration validation.",
            failure_point="Routed path or local target port mapping",
            decision_if_fail="Treat the routed path or local target port mapping as the current failure point.",
            evidence_to_collect=evidence[:2],
            recommended_commands=_command_bundle(
                _listener_command(
                    [first_port] if first_port and first_port != "unknown" else [],
                    label="Check microservice listener",
                    interpretation="If the target port is missing, the feature path may be failing before the request reaches the service.",
                ),
                _config_command(
                    first_config or "/etc/httpd/conf.d/algosec-ms.conf",
                    needle=str(first_port) if first_port and first_port != "unknown" else None,
                    interpretation="If the proxy mapping is wrong, the customer path may point to the wrong backend or no backend at all.",
                ),
            ),
        ),
        _playbook_step(
            step_id="microservice-platform-step-4",
            step_number=4,
            action="Confirm ms-configuration.service is healthy before assuming the issue is isolated to the single feature path.",
            next_if_pass="Continue to dependency and error review.",
            failure_point="ms-configuration.service",
            decision_if_fail="Treat ms-configuration.service as the current failure point because other microservices depend on it.",
            evidence_to_collect=evidence[2:4],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "ms-configuration.service",
                    interpretation="If configuration is unhealthy, many downstream ms-* services can fail together.",
                ),
            ),
        ),
        _playbook_step(
            step_id="microservice-platform-step-5",
            step_number=5,
            action="Collect the relevant ms-* service status or error snippet and decide whether the issue stays in the target service or moves to shared dependencies like httpd.service.",
            next_if_pass=flow["next_dependency_focus"] or "Use the collected microservice evidence to choose the next dependency check.",
            failure_point="Microservice runtime evidence incomplete",
            decision_if_fail="If the error evidence cannot be collected, escalate with the routed-path and service-state checks already captured.",
            evidence_to_collect=evidence[2:4],
            recommended_commands=_command_bundle(
                _journal_command(
                    first_service,
                    interpretation="Use recent log lines to separate local service failure, permission issues, and deeper shared dependency problems.",
                ),
            ),
        ),
    ]


def _messaging_and_data_playbook_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = flow["evidence_to_collect_next"]
    activemq_detail = _flow_service_detail(flow, "activemq.service")
    postgres_detail = _flow_service_detail(flow, "postgresql.service")
    return [
        _playbook_step(
            step_id="messaging-and-data-step-1",
            step_number=1,
            action="Confirm the customer symptom is really a stuck job, stalled event, or data-backed action failure instead of a pure UI-path issue.",
            next_if_pass="Continue to broker validation.",
            failure_point="Domain mismatch",
            decision_if_fail="If the symptom is UI-only, switch to UI and Proxy or Microservice Platform instead of staying here.",
            evidence_to_collect=evidence[:1],
            recommended_commands=[],
        ),
        _playbook_step(
            step_id="messaging-and-data-step-2",
            step_number=2,
            action="Confirm activemq.service is active and listener 61616 is present before assuming the issue is only downstream data state.",
            next_if_pass="Continue to database validation.",
            failure_point="activemq.service or 61616 listener",
            decision_if_fail="Treat activemq.service or the 61616 listener as the current failure point.",
            evidence_to_collect=evidence[:2],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "activemq.service",
                    interpretation="If the broker is not active, stop here and treat messaging infrastructure as the likely failure point.",
                ),
                _listener_command(
                    activemq_detail.get("listener_ports", ["61616"]),
                    label="Check broker listener",
                    interpretation="If 61616 is missing, queued work may fail before any feature-specific processing begins.",
                ),
            ),
        ),
        _playbook_step(
            step_id="messaging-and-data-step-3",
            step_number=3,
            action="Confirm postgresql.service is active and that the customer environment shows no obvious database connectivity or state error.",
            next_if_pass="Continue to backlog or queue-state review.",
            failure_point="postgresql.service",
            decision_if_fail="Treat postgresql.service as the current failure point for this issue.",
            evidence_to_collect=evidence[1:3],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "postgresql.service",
                    interpretation="If the database is not active, treat data availability as the underlying failure point.",
                ),
                _listener_command(
                    postgres_detail.get("listener_ports", ["5432"]),
                    label="Check database listener",
                    interpretation="If the database listener is missing, look for deeper startup or permission issues on the host.",
                ),
            ),
        ),
        _playbook_step(
            step_id="messaging-and-data-step-4",
            step_number=4,
            action="Review the visible queue, backlog, or stuck-job signal and decide whether the problem stays in broker/data infrastructure or should move back to a feature-specific domain.",
            next_if_pass="If infrastructure checks passed, move to the feature-specific domain that owns the stalled job or action.",
            failure_point="Queue or backlog evidence incomplete",
            decision_if_fail="If queue or backlog evidence cannot be gathered, escalate with the broker and database checks already captured.",
            evidence_to_collect=evidence[:3],
            recommended_commands=_command_bundle(
                _journal_command(
                    "activemq.service",
                    interpretation="Use broker log lines to decide whether the queue layer is blocked, degraded, or forwarding the issue downstream.",
                ),
                _journal_command(
                    "postgresql.service",
                    interpretation="Use database log lines to spot deeper availability or permission problems affecting queued work.",
                ),
            ),
        ),
    ]


def _isoformat_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
