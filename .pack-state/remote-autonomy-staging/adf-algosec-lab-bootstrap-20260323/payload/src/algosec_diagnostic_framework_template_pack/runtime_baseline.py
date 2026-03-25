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


DEFAULT_ARTIFACT_ROOT = Path("dist/candidates/adf-baseline")
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
) -> dict[str, Any]:
    root = project_root / (Path(artifact_root) if artifact_root else DEFAULT_ARTIFACT_ROOT)
    root.mkdir(parents=True, exist_ok=True)

    runtime_evidence = collect_runtime_evidence(target_label=target_label)
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


def collect_runtime_evidence(*, target_label: str) -> dict[str, Any]:
    os_release = _load_os_release()
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

    observed_facts = {
        "hostname": socket.gethostname(),
        "os_release": os_release,
        "kernel_release": platform.release(),
        "platform": platform.platform(),
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
                "Runtime identity, service-manager output, TCP listeners, and process inventory were collected from local read-only sources.",
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
    services = _services_from_runtime_results(results)

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

    quick_jump_items = "".join(
        (
            f'<a class="jump-card" href="#playbook-{html.escape(playbook["playbook_id"])}">'
            f'<span class="jump-title">{html.escape(playbook["label"])}</span>'
            f'<span class="jump-subtitle">{html.escape(playbook["steps"][0]["action"])}</span>'
            "</a>"
        )
        for playbook in support_baseline["decision_playbooks"]
    )

    symptom_lookup_items = "".join(
        (
            f'<a class="symptom-chip" href="#playbook-{html.escape(item["suggested_domain_id"])}">'
            f'<strong>{html.escape(item["symptom_label"])}</strong>'
            f'<span>{html.escape(item["suggested_domain_label"])}</span>'
            "</a>"
        )
        for item in support_baseline["symptom_lookup"]
    )

    def render_command(command: dict[str, str]) -> str:
        return (
            '<div class="command-card">'
            f'<div class="command-label">{html.escape(command["label"])}</div>'
            f'<pre><code>{html.escape(command["command"])}</code></pre>'
            f'<div class="signal ok"><strong>Healthy means:</strong> {html.escape(command["expected_signal"])}</div>'
            f'<div class="signal warn"><strong>If not healthy:</strong> {html.escape(command["interpretation"])}</div>'
            "</div>"
        )

    def render_step(step: dict[str, Any]) -> str:
        evidence_block = (
            '<div class="step-panel evidence"><strong>Collect if this step fails</strong><ul>'
            + "".join(f"<li>{html.escape(item)}</li>" for item in step["evidence_to_collect"])
            + "</ul></div>"
            if step["evidence_to_collect"]
            else ""
        )
        commands_block = (
            '<div class="step-panel"><strong>Run these commands</strong>'
            + "".join(render_command(command) for command in step["recommended_commands"])
            + "</div>"
            if step["recommended_commands"]
            else ""
        )
        return (
            '<article class="step-card">'
            f'<div class="step-number">{html.escape(step["step_label"])}</div>'
            f'<h4>{html.escape(step["action"])}</h4>'
            '<div class="step-grid">'
            f'<div class="step-panel pass"><strong>If healthy</strong><p>{html.escape(step["next_if_pass"])}</p></div>'
            f'<div class="step-panel fail"><strong>Likely failure point</strong><p>{html.escape(step["failure_point"])}</p></div>'
            f'<div class="step-panel next"><strong>Decision if this fails</strong><p>{html.escape(step["decision_if_fail"])}</p></div>'
            "</div>"
            + commands_block
            + evidence_block
            + "</article>"
        )

    def render_playbook(playbook: dict[str, Any]) -> str:
        flow = flow_lookup.get(playbook["playbook_id"], {})
        symptom_items = symptoms_by_flow.get(playbook["playbook_id"], [])
        symptom_list = "".join(f"<li>{html.escape(item['symptom_label'])}</li>" for item in symptom_items)
        first_command_preview = ""
        for step in playbook["steps"]:
            if step["recommended_commands"]:
                first_command_preview = step["recommended_commands"][0]["command"]
                break
        quick_path = "".join(
            f'<div class="path-node">{html.escape(step["step_label"])}<span>{html.escape(step["failure_point"])}</span></div>'
            for step in playbook["steps"]
        )
        return (
            f'<section class="playbook" id="playbook-{html.escape(playbook["playbook_id"])}">'
            f'<div class="playbook-header"><div><h2>{html.escape(playbook["label"])}</h2>'
            f'<p class="playbook-focus">{html.escape(playbook["symptom_focus"])}</p></div>'
            f'<a class="top-link" href="#top">Back to top</a></div>'
            + (
                '<div class="playbook-meta"><div class="meta-card"><strong>Use this when</strong><ul>'
                + symptom_list
                + "</ul></div>"
                if symptom_items
                else '<div class="playbook-meta">'
            )
            + (
                f'<div class="meta-card"><strong>Start with</strong><p>{html.escape(first_command_preview)}</p></div>'
                if first_command_preview
                else '<div class="meta-card"><strong>Start with</strong><p>Use the first explicit step below.</p></div>'
            )
            + (
                f'<div class="meta-card"><strong>Next dependency path</strong><p>{html.escape(flow.get("next_dependency_focus", "Stay inside this playbook until a step fails or passes cleanly."))}</p></div>'
                "</div>"
            )
            + '<div class="quick-path">'
            + quick_path
            + "</div>"
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
    .symptom-chip strong {{
      display: block;
      margin-bottom: 4px;
    }}
    .playbook-header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      margin-bottom: 14px;
    }}
    .top-link {{
      color: var(--accent);
      font-weight: bold;
      white-space: nowrap;
    }}
    .quick-path {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 10px;
      margin: 18px 0;
    }}
    .path-node {{
      border-left: 5px solid var(--accent);
      background: #f8fcfc;
      font-weight: bold;
    }}
    .path-node span {{
      display: block;
      font-weight: normal;
      margin-top: 6px;
    }}
    .step-card {{
      border-top: 1px solid var(--rule);
      padding-top: 18px;
      margin-top: 18px;
    }}
    .step-number {{
      display: inline-block;
      background: var(--accent);
      color: white;
      font-weight: bold;
      border-radius: 999px;
      padding: 4px 10px;
      margin-bottom: 10px;
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
    .command-card {{
      margin-top: 12px;
      background: #fbfcfe;
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
    .signal.warn {{
      background: var(--warn);
      color: var(--warn-ink);
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
      <div class="symptom-grid">{symptom_lookup_items}</div>
    </section>
    <section>
      <h2>Playbook Paths</h2>
      <div class="jump-grid">{quick_jump_items}</div>
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
</body>
</html>"""


def _dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")


def _load_os_release() -> dict[str, str]:
    path = Path("/etc/os-release")
    payload: dict[str, str] = {}
    if not path.exists():
        return payload
    for line in path.read_text(encoding="utf-8").splitlines():
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


def _services_from_runtime_results(results: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
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
        service["observed"].update(_collect_service_checkpoints(service_name))
        service["observed"]["evidence_refs"] = sorted(set(service["observed"]["evidence_refs"]))
        service["inference"] = _score_service(service)
        service["unknowns"] = [
            "No direct dependency graph collection in this first slice.",
        ]
        if service["observed"]["config_refs"]:
            service["unknowns"] = [
                "Config checkpoints are first-pass only and may not capture every product override or generated file.",
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
            "label": "Appliance UI is down",
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
        checks.append("Confirm httpd.service is active and ports 80 and 443 are listening.")
        checks.append("Confirm the Apache login rewrite still sends /algosec/suite/login to /algosec-ui/login.")
        if "keycloak.service" in supporting_services:
            checks.append("Confirm keycloak.service is active and the /keycloak/ proxy path still points to localhost:8443.")
        if "ms-metro.service" in supporting_services:
            checks.append("Confirm ms-metro.service is active and the /afa/api/v1 route still maps to localhost:8080.")
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

        flows.append(
            {
                "flow_id": domain["domain_id"],
                "label": domain["label"],
                "symptom_focus": _domain_symptom_focus(domain["domain_id"]),
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
        "ui-and-proxy": "Use this when the appliance UI does not load, the login page does not resolve, or the web shell is down before feature-specific troubleshooting can begin.",
        "core-aff": "Use this when FireFlow actions fail, stall, or return backend-facing errors.",
        "microservice-platform": "Use this when product features fail behind the UI, especially path-specific ms-* behavior.",
        "messaging-and-data": "Use this when jobs back up, events do not move, or data-backed actions fail unexpectedly.",
    }.get(domain_id, "Use this when symptoms cluster around this domain.")


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
        ("appliance-ui-down", "Appliance UI is down", "ui-and-proxy"),
        ("appliance-login-not-loading", "Appliance login page not loading", "ui-and-proxy"),
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
        evidence.append("Customer browser error or screenshot for the failing UI or login path.")
        evidence.append("Visible status of httpd.service and the current 80/443 listener state.")
        evidence.append("Result of a local login-path probe to /algosec/suite/login and whether it redirects to /algosec-ui/login.")
        evidence.append("Visible status of keycloak.service and whether localhost:8443 is listening.")
        evidence.append("Visible status of ms-metro.service and whether localhost:8080 is listening.")
        return evidence

    if domain_id == "core-aff":
        evidence.append("Result of the failing FireFlow action, including the exact endpoint or screen.")
        evidence.append("Visible status for aff-boot.service and postgresql.service.")
        evidence.append("Any recent FireFlow-related lines from the customer-facing logs or service status output.")
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
        playbooks.append(
            {
                "playbook_id": flow["flow_id"],
                "label": flow["label"],
                "symptom_focus": flow["symptom_focus"],
                "decision_rule": decision_rule,
                "likely_failing_services": flow["likely_failing_services"],
                "steps": steps,
            }
        )
    return playbooks


def _playbook_step(
    *,
    step_id: str,
    step_number: int,
    action: str,
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
) -> dict[str, str]:
    return {
        "label": label,
        "command": command,
        "expected_signal": expected_signal,
        "interpretation": interpretation,
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


def _service_status_command(service_name: str, *, interpretation: str) -> dict[str, str]:
    return _command_entry(
        label=f"Check {service_name} status",
        command=f"systemctl status {shlex.quote(service_name)} --no-pager",
        expected_signal="Unit is loaded and active (running).",
        interpretation=interpretation,
    )


def _listener_command(
    ports: list[str],
    *,
    interpretation: str,
    label: str = "Check listener state",
) -> dict[str, str] | None:
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
    )


def _config_command(
    config_path: str,
    *,
    needle: str | None,
    interpretation: str,
    label: str = "Check config mapping",
) -> dict[str, str]:
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
    )


def _journal_command(service_name: str, *, interpretation: str) -> dict[str, str]:
    return _command_entry(
        label=f"Review {service_name} logs",
        command=f"journalctl -u {shlex.quote(service_name)} -n 50 --no-pager",
        expected_signal="Recent lines show healthy startup or a clear error signature to classify.",
        interpretation=interpretation,
    )


def _curl_head_command(
    *,
    label: str,
    url: str,
    expected_signal: str,
    interpretation: str,
) -> dict[str, str]:
    return _command_entry(
        label=label,
        command=f"curl -k -I --max-time 5 {shlex.quote(url)}",
        expected_signal=expected_signal,
        interpretation=interpretation,
    )


def _command_bundle(*commands: dict[str, str] | None) -> list[dict[str, str]]:
    return [command for command in commands if command]


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
    keycloak_detail = _flow_service_detail(flow, "keycloak.service")
    metro_detail = _flow_service_detail(flow, "ms-metro.service")
    return [
        _playbook_step(
            step_id="ui-and-proxy-step-1",
            step_number=1,
            action="Confirm the appliance UI itself is down or the login page is not loading, rather than a single feature failing behind an otherwise healthy UI.",
            next_if_pass="Continue to Apache edge validation.",
            failure_point="Domain mismatch",
            decision_if_fail="If the UI shell loads and only one workflow fails after login, switch to the feature-specific playbook instead of staying here.",
            evidence_to_collect=evidence[:2],
            recommended_commands=[],
        ),
        _playbook_step(
            step_id="ui-and-proxy-step-2",
            step_number=2,
            action="Confirm Apache is up first: httpd.service must be active and ports 80 and 443 must be listening before any appliance UI path can work.",
            next_if_pass="Continue to login rewrite validation.",
            failure_point="httpd.service or edge listener state",
            decision_if_fail="Treat httpd.service or the edge listener state as the current failure point.",
            evidence_to_collect=evidence[:2],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "httpd.service",
                    interpretation="If this is not active, treat the edge service itself as the failure point before going deeper.",
                ),
                _listener_command(
                    ["80", "443"],
                    label="Check edge listeners",
                    interpretation="If 80/443 are missing, the UI path is failing at the listener or bind layer.",
                ),
            ),
        ),
        _playbook_step(
            step_id="ui-and-proxy-step-3",
            step_number=3,
            action="Validate the appliance login route itself: Apache should redirect /algosec/suite/login to /algosec-ui/login and serve the UI shell path cleanly.",
            next_if_pass="Continue to Keycloak authentication validation.",
            failure_point="Apache login rewrite or UI shell path",
            decision_if_fail="Treat the Apache login rewrite or appliance UI shell path as the current failure point.",
            evidence_to_collect=evidence[1:3],
            recommended_commands=_command_bundle(
                _command_entry(
                    label="Check login rewrite config",
                    command="grep -n -E 'algosec/suite/login|algosec-ui/login|FallbackResource' /etc/httpd/conf.d/zzz_fa.conf",
                    expected_signal="The login rewrite and UI fallback lines are present in zzz_fa.conf.",
                    interpretation="If the rewrite or UI fallback is missing, Apache may be up while the appliance UI entry path is broken.",
                ),
                _curl_head_command(
                    label="Probe the login path locally",
                    url="https://127.0.0.1/algosec/suite/login",
                    expected_signal="The local login path responds with an HTTP redirect to /algosec-ui/login, not a timeout or 5xx error.",
                    interpretation="If the login path does not redirect cleanly, focus on Apache rewrite or local UI-path handling before moving deeper.",
                ),
            ),
        ),
        _playbook_step(
            step_id="ui-and-proxy-step-4",
            step_number=4,
            action="Validate the authentication path next: keycloak.service must be active, localhost:8443 must be listening, and the /keycloak/ proxy path must answer locally.",
            next_if_pass="Continue to Metro/API backend validation.",
            failure_point="keycloak.service or /keycloak/ proxy path",
            decision_if_fail="Treat keycloak.service or the /keycloak/ proxy path as the current failure point.",
            evidence_to_collect=evidence[2:4],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "keycloak.service",
                    interpretation="If Keycloak is not active, the appliance login/auth path is failing before the UI can complete.",
                ),
                _listener_command(
                    keycloak_detail.get("listener_ports", ["8443"]),
                    label="Check Keycloak listener",
                    interpretation="If the auth listener is missing, focus on Keycloak startup or bind issues.",
                ),
                _command_entry(
                    label="Check keycloak proxy mapping",
                    command="grep -R -n '/keycloak\\|8443' /etc/httpd/conf.d",
                    expected_signal="A /keycloak proxy rule points at the expected local auth target.",
                    interpretation="If the proxy mapping is missing or wrong, the login path may be routed incorrectly.",
                ),
                _curl_head_command(
                    label="Probe the Keycloak path locally",
                    url="https://127.0.0.1/keycloak/",
                    expected_signal="The local Keycloak path returns an HTTP auth response such as 302 or 401, not a timeout or 5xx error.",
                    interpretation="If the local Keycloak probe fails, the appliance auth path is broken even if Apache is healthy.",
                ),
            ),
        ),
        _playbook_step(
            step_id="ui-and-proxy-step-5",
            step_number=5,
            action="Validate the first backend path behind the appliance UI: ms-metro.service should be active, localhost:8080 should be listening, and /afa/api/v1 should answer locally.",
            next_if_pass="If these checks pass, the appliance UI shell is likely healthy and the issue should move to a narrower backend or feature-specific playbook.",
            failure_point="ms-metro.service, localhost:8080, or the /afa/api/v1 route",
            decision_if_fail="Treat Metro or the local API route as the current failure point for the appliance UI path.",
            evidence_to_collect=evidence[3:5],
            recommended_commands=_command_bundle(
                _service_status_command(
                    "ms-metro.service",
                    interpretation="If Metro is not active, the appliance UI may load partially while its main backend path remains unavailable.",
                ),
                _listener_command(
                    metro_detail.get("listener_ports", ["8080"]),
                    label="Check Metro listener",
                    interpretation="If localhost:8080 is missing, the UI-facing backend route has no healthy target.",
                ),
                _command_entry(
                    label="Check Metro/API route mapping",
                    command="grep -n -E '/afa/api/v1|localhost:8080|afa/external' /etc/httpd/conf.d/zzz_fa.conf",
                    expected_signal="Apache routes the AFA/API path to localhost:8080 in zzz_fa.conf.",
                    interpretation="If the route mapping is missing or wrong, the UI may be up while the application backend path is broken.",
                ),
                _curl_head_command(
                    label="Probe the API path locally",
                    url="https://127.0.0.1/afa/api/v1",
                    expected_signal="The API path returns a local HTTP response such as 200, 302, or 401, not a timeout or 5xx error.",
                    interpretation="If the API path does not answer locally, focus on Metro or the Apache route chain rather than the browser first.",
                ),
            ),
        ),
    ]


def _core_aff_playbook_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = flow["evidence_to_collect_next"]
    aff_path = _flow_path_checkpoint(flow, "aff-boot.service")
    aff_config = (aff_path or {}).get("config_checkpoints", ["/etc/httpd/conf.d/aff.conf"])[0]
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
                    interpretation="If aff-boot is not active, stop here and treat the FireFlow service itself as the failure point.",
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
                    interpretation="Look for permission errors, startup failures, or dependency errors that explain why FireFlow is unhealthy.",
                ),
            ),
        ),
    ]


def _microservice_platform_playbook_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = flow["evidence_to_collect_next"]
    likely_services = ", ".join(flow["likely_failing_services"][:3])
    first_service = flow["likely_failing_services"][0] if flow["likely_failing_services"] else "ms-batch-application.service"
    first_path = _flow_path_checkpoint(flow, first_service)
    first_route = (first_path or {}).get("route_checkpoints", [{}])[0]
    first_port = first_route.get("target_ports") or ((first_path or {}).get("listener_ports") or ["unknown"])[0]
    first_config = ((first_path or {}).get("config_checkpoints") or [None])[0]
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
