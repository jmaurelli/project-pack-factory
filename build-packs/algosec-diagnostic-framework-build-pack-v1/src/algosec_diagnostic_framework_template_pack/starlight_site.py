from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .runtime_baseline import DEFAULT_ARTIFACT_ROOT, SUPPORT_BASELINE_NAME

PRIMARY_PLAYBOOK_ID = "ui-and-proxy"


def generate_starlight_site(
    *,
    project_root: Path,
    artifact_root: str | Path | None = None,
    site_root: str | Path | None = None,
) -> dict[str, Any]:
    baseline_root = project_root / (Path(artifact_root) if artifact_root else DEFAULT_ARTIFACT_ROOT)
    support_baseline_path = baseline_root / SUPPORT_BASELINE_NAME
    support_baseline = json.loads(support_baseline_path.read_text(encoding="utf-8"))

    output_root = project_root / Path(site_root) if site_root else baseline_root / "starlight-site"
    docs_root = output_root / "src" / "content" / "docs"
    playbooks_root = docs_root / "playbooks"
    docs_root.mkdir(parents=True, exist_ok=True)
    playbooks_root.mkdir(parents=True, exist_ok=True)
    for stale_playbook in playbooks_root.glob("*.md"):
        stale_playbook.unlink()

    playbook_nav_entries: list[dict[str, str | int]] = []
    symptom_lookup = _symptoms_by_playbook(support_baseline)
    for order, playbook in enumerate(support_baseline.get("decision_playbooks", []), start=1):
        slug = _slugify(playbook["label"])
        filename = f"{slug}.md"
        relative_path = f"src/content/docs/playbooks/{filename}"
        (playbooks_root / filename).write_text(
            _render_playbook_markdown(
                playbook=playbook,
                order=order,
                symptom_entries=symptom_lookup.get(playbook["playbook_id"], []),
            ),
            encoding="utf-8",
        )
        playbook_nav_entries.append(
            {
                "label": playbook["label"],
                "slug": f"playbooks/{slug}",
                "relative_path": relative_path,
                "order": order,
                "playbook_id": playbook["playbook_id"],
            }
        )

    (docs_root / "index.mdx").write_text(_render_index_markdown(support_baseline, playbook_nav_entries), encoding="utf-8")
    (output_root / "package.json").write_text(_render_package_json(), encoding="utf-8")
    (output_root / "astro.config.mjs").write_text(_render_astro_config(playbook_nav_entries), encoding="utf-8")
    (output_root / "tsconfig.json").write_text(_render_tsconfig(), encoding="utf-8")
    (output_root / "src" / "content.config.ts").parent.mkdir(parents=True, exist_ok=True)
    (output_root / "src" / "content.config.ts").write_text(_render_content_config(), encoding="utf-8")
    (output_root / "src" / "custom.css").write_text(_render_custom_css(), encoding="utf-8")

    generated_files = [
        str((output_root / "package.json").relative_to(project_root)),
        str((output_root / "astro.config.mjs").relative_to(project_root)),
        str((output_root / "tsconfig.json").relative_to(project_root)),
        str((output_root / "src" / "content.config.ts").relative_to(project_root)),
        str((output_root / "src" / "custom.css").relative_to(project_root)),
        str((docs_root / "index.mdx").relative_to(project_root)),
    ] + [
        str((playbooks_root / Path(entry["relative_path"]).name).relative_to(project_root))
        for entry in playbook_nav_entries
    ]

    return {
        "status": "pass",
        "artifact_root": str(output_root.relative_to(project_root)),
        "generated_files": generated_files,
        "summary": {
            "playbook_count": len(playbook_nav_entries),
            "symptom_count": len(support_baseline.get("symptom_lookup", [])),
            "source_artifact": str(support_baseline_path.relative_to(project_root)),
        },
    }


def _render_package_json() -> str:
    payload = {
        "name": "algosec-diagnostic-framework-site",
        "private": True,
        "type": "module",
        "scripts": {
            "dev": "astro dev",
            "build": "astro build",
            "preview": "astro preview --host 0.0.0.0 --port 18082",
        },
        "dependencies": {
            "astro": "5.12.8",
            "@astrojs/starlight": "0.36.0",
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def _render_astro_config(playbook_nav_entries: list[dict[str, str | int]]) -> str:
    primary = _primary_nav_entry(playbook_nav_entries)
    current_focus_items = (
        "{ label: "
        + json.dumps(str(primary["label"]))
        + ", slug: "
        + json.dumps(str(primary["slug"]))
        + " }"
        if primary
        else ""
    )
    focus_sidebar = (
        "{\n        label: 'Current Focus',\n        items: [\n          "
        + current_focus_items
        + "\n        ],\n      }"
        if current_focus_items
        else "{\n        label: 'Current Focus',\n        items: [],\n      }"
    )
    playbook_items = ",\n          ".join(
        "{ label: "
        + json.dumps(str(entry["label"]))
        + ", slug: "
        + json.dumps(str(entry["slug"]))
        + " }"
        for entry in playbook_nav_entries
    )
    playbook_sidebar = (
        "{\n        label: 'Playbooks',\n        items: [\n          "
        + playbook_items
        + "\n        ],\n      }"
        if playbook_items
        else "{\n        label: 'Playbooks',\n        items: [],\n      }"
    )
    return (
        "import { defineConfig } from 'astro/config';\n"
        "import starlight from '@astrojs/starlight';\n\n"
        "export default defineConfig({\n"
        "  integrations: [\n"
        "    starlight({\n"
        "      title: 'AlgoSec Diagnostic Framework',\n"
        "      description: 'Target-backed diagnostic playbooks for support engineers.',\n"
        "      customCss: ['./src/custom.css'],\n"
        "      tableOfContents: false,\n"
        "      sidebar: [\n"
        "        {\n"
        "          label: 'Start Here',\n"
        "          items: [{ label: 'Overview', slug: 'index' }],\n"
        "        },\n"
        f"        {focus_sidebar},\n"
        f"        {playbook_sidebar}\n"
        "      ],\n"
        "    }),\n"
        "  ],\n"
        "});\n"
    )


def _render_tsconfig() -> str:
    return '{\n  "extends": "astro/tsconfigs/strict"\n}\n'


def _render_content_config() -> str:
    return (
        "import { defineCollection } from 'astro:content';\n"
        "import { docsLoader } from '@astrojs/starlight/loaders';\n"
        "import { docsSchema } from '@astrojs/starlight/schema';\n\n"
        "export const collections = {\n"
        "  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),\n"
        "};\n"
    )


def _render_index_markdown(
    support_baseline: dict[str, Any],
    playbook_nav_entries: list[dict[str, str | int]],
) -> str:
    observed = support_baseline.get("observed", {})
    service_summary = observed.get("service_summary", {})
    runtime_identity = observed.get("runtime_identity", {})
    os_release = runtime_identity.get("os_release", {})
    domains = support_baseline.get("support_domains", [])
    symptoms = support_baseline.get("symptom_lookup", [])
    first_response_steps = support_baseline.get("first_response_steps", [])

    lines = [
        "---",
        "title: AlgoSec Diagnostic Framework",
        "description: Runtime-backed framework for diagnostic playbooks, evidence, and support workflows.",
        "sidebar:",
        "  label: Overview",
        "  order: 1",
        "---",
        "",
        "# AlgoSec Diagnostic Framework",
        "",
        "Support Cockpit is the current interaction model for the Starlight publisher.",
        "",
        '<div class="adf-home-shell">',
        '  <div class="adf-home-topbar">',
        '    <div class="adf-panel">',
        '      <p class="adf-panel-label">Live baseline</p>',
        f"      <p>{support_baseline['target']['target_label']} on {support_baseline['target']['hostname']} running {os_release.get('PRETTY_NAME', 'the recorded OS baseline')}.</p>",
        "    </div>",
        '    <div class="adf-panel">',
        '      <p class="adf-panel-label">Observed scope</p>',
        f"      <p>{service_summary.get('total_services', 0)} services, {observed.get('listening_endpoint_count', 0)} listeners, {observed.get('config_checkpoint_count', 0)} config checkpoints, {observed.get('log_checkpoint_count', 0)} log checkpoints.</p>",
        "    </div>",
        "  </div>",
        "",
        "## First response",
        "",
        '<div class="adf-home-grid">',
        '  <div class="adf-panel">',
        '    <p class="adf-panel-label">How to use this site</p>',
        "    <ul>",
    ]
    lines.extend([f"      <li>{step}</li>" for step in first_response_steps])
    lines.extend(
        [
            "    </ul>",
            "  </div>",
            '  <div class="adf-panel">',
            '    <p class="adf-panel-label">Why this shape</p>',
            "    <ul>",
            "      <li>Quick jump stays visible while you read lower command content.</li>",
            "      <li>Each checkpoint stays collapsed until you need it.</li>",
            "      <li>The JSON baseline stays canonical. This page is only a render.</li>",
            "    </ul>",
            "  </div>",
            "</div>",
            "",
            "## Playbooks",
            "",
            '<div class="adf-home-card-grid">',
        ]
    )
    for domain in domains:
        target = _starlight_target_for_playbook_id(playbook_nav_entries, domain["domain_id"])
        lines.extend(
            [
                f'<a class="adf-home-card" href="{target}">',
                f'  <p class="adf-panel-label">{domain["domain_id"]}</p>',
                f"  <strong>{domain['label']}</strong>",
                f"  <span>{domain.get('summary', '')}</span>",
            ]
        )
        first_checks = domain.get("first_checks", [])[:2]
        if first_checks:
            lines.append('  <span class="adf-home-card-list">')
            for item in first_checks:
                lines.append(f"    {item}")
            lines.append("  </span>")
        lines.append("</a>")
    lines.extend(
        [
            "</div>",
            "",
            "## Symptom lookup",
            "",
            '<div class="adf-symptom-grid">',
        ]
    )
    for symptom in symptoms:
        target = _starlight_target_for_playbook_id(playbook_nav_entries, symptom["suggested_domain_id"])
        lines.extend(
            [
                '<div class="adf-symptom-card">',
                f'  <a class="adf-symptom-link" href="{target}"><strong>{symptom["symptom_label"]}</strong></a>',
                f'  <p>{symptom["first_action"]}</p>',
                f'  <span>Use {symptom["suggested_domain_label"]}.</span>',
                "</div>",
            ]
        )
    lines.extend(["</div>", "</div>", ""])
    return "\n".join(lines) + "\n"


def _render_playbook_markdown(
    *,
    playbook: dict[str, Any],
    order: int,
    symptom_entries: list[dict[str, str]],
) -> str:
    dependency_path = playbook.get("dependency_path", [])
    dependency_by_step = {item["step_id"]: item for item in dependency_path}
    likely_services = playbook.get("likely_failing_services", [])
    jump_items = dependency_path or [
        {
            "step_id": step["step_id"],
            "step_label": step["step_label"],
            "label": _step_summary_label(step),
            "details": step["action"],
        }
        for step in playbook.get("steps", [])
    ]

    lines = [
        "---",
        f"title: {playbook['label']}",
        f"description: {playbook['symptom_focus']}",
        "sidebar:",
        f"  label: {playbook['label']}",
        f"  order: {order}",
        "---",
        "",
        playbook["symptom_focus"],
        "",
        "## Support Cockpit",
        "",
        '<div class="adf-cockpit-shell">',
        '  <div class="adf-cockpit-topbar">',
        '    <div class="adf-panel">',
        '      <p class="adf-panel-label">Decision rule</p>',
        f"      <p>{playbook.get('decision_rule', 'Work top to bottom. Stop at the first unhealthy checkpoint.')}</p>",
        "    </div>",
        '    <div class="adf-panel">',
        '      <p class="adf-panel-label">Likely services</p>',
    ]
    if likely_services:
        lines.extend(
            [
                '      <div class="adf-service-chip-row">',
                *[f'        <span class="adf-service-chip">{service}</span>' for service in likely_services],
                "      </div>",
            ]
        )
    else:
        lines.append("      <p>Use the quick jump and step actions to isolate the first unhealthy checkpoint.</p>")
    lines.extend(
        [
            "    </div>",
            "  </div>",
            '  <div class="adf-panel adf-cockpit-strip">',
            '    <p class="adf-panel-label">Command-first flow</p>',
            "    <p>Open one checkpoint, run the listed read-only commands, compare the healthy signal, then stop at the first failure point.</p>",
            "  </div>",
        ]
    )
    if dependency_path:
        lines.extend(
            [
                '  <div class="adf-cockpit-path">',
                '    <p class="adf-panel-label">Dependency path</p>',
                '    <ol class="adf-path-list">',
            ]
        )
        for item in dependency_path:
            lines.extend(
                [
                    '      <li class="adf-path-item">',
                    f'        <a class="adf-path-link" href="#{item["step_id"]}">',
                    f'          <span class="adf-route-step">{item["step_label"]}</span>',
                    f"          <strong>{item['label']}</strong>",
                    f"          <span>{item['details']}</span>",
                    "        </a>",
                    "      </li>",
                ]
            )
        lines.extend(["    </ol>", "  </div>"])
    lines.extend(
        [
            '  <div class="adf-cockpit-grid">',
            '    <aside class="adf-cockpit-nav adf-panel">',
            '      <p class="adf-panel-label">Quick jump</p>',
            '      <div class="adf-cockpit-jumps">',
        ]
    )
    for item in jump_items:
        lines.extend(
            [
                f'<a class="adf-cockpit-jump" href="#{item["step_id"]}">',
                f'  <span class="adf-route-step">{item["step_label"]}</span>',
                f'  <strong>{item["label"]}</strong>',
                f'  <span>{item["details"]}</span>',
                "</a>",
            ]
        )
    lines.extend(
        [
            "      </div>",
        ]
    )
    if symptom_entries:
        lines.extend(
            [
                '      <div class="adf-cockpit-sideblock">',
                '        <p class="adf-panel-label">Symptoms that fit here</p>',
                "        <ul>",
                *[f"          <li>{entry['symptom_label']}</li>" for entry in symptom_entries],
                "        </ul>",
                "      </div>",
            ]
        )
    lines.extend(
        [
            "    </aside>",
            '    <div class="adf-cockpit-main">',
        ]
    )
    for step in playbook.get("steps", []):
        lines.extend(_render_step_markdown(step, dependency_by_step.get(step["step_id"])))

    lines.extend(
        [
            "    </div>",
            "  </div>",
            "</div>",
            "",
            '<script>',
            "(() => {",
            "  const openHashTarget = () => {",
            "    const rawHash = window.location.hash;",
            "    if (!rawHash || rawHash.length < 2) return;",
            "    const target = document.getElementById(decodeURIComponent(rawHash.slice(1)));",
            "    if (!target) return;",
            "    const details = target.matches('details') ? target : target.closest('details');",
            "    if (details) details.open = true;",
            "  };",
            "  window.addEventListener('hashchange', openHashTarget);",
            "  openHashTarget();",
            "})();",
            "</script>",
            "",
        ]
    )

    return "\n".join(lines) + "\n"


def _render_step_markdown(step: dict[str, Any], dependency_item: dict[str, str] | None) -> list[str]:
    summary_label = dependency_item["label"] if dependency_item else _step_summary_label(step)
    lines = [
        f'<details id="{step["step_id"]}" class="adf-checkpoint">',
        '<summary class="adf-step-summary">',
        f'  <span class="adf-step-badge">{step["step_label"]}</span>',
        '  <span class="adf-step-heading">',
        f"    <strong>{summary_label}</strong>",
        f'    <span>{step["action"]}</span>',
        "  </span>",
        '  <span class="adf-step-toggle" aria-hidden="true"></span>',
        "</summary>",
        "",
        '<div class="adf-step-body">',
    ]
    if step.get("why_this_matters"):
        lines.extend(
            [
                '<p class="adf-step-brief">',
                '  <span class="adf-inline-label">Why this step matters:</span> ',
                f"{step['why_this_matters']}",
                "</p>",
                "",
            ]
        )

    for command in step.get("recommended_commands", []):
        lines.extend(_render_command_markdown(command))

    if step.get("if_pass") or step.get("if_fail") or step.get("evidence_to_collect"):
        lines.extend(
            [
                '<div class="adf-step-outcomes">',
            ]
        )
        if step.get("if_pass"):
            lines.extend(
                [
                    '  <p class="adf-step-outcome">',
                    '    <span class="adf-inline-label">If healthy:</span> ',
                    f"{step['if_pass']}",
                    "  </p>",
                ]
            )
        if step.get("if_fail"):
            lines.extend(
                [
                    '  <p class="adf-step-outcome">',
                    '    <span class="adf-inline-label">If this fails:</span> ',
                    f"{step['if_fail']}",
                    "  </p>",
                ]
            )
        if step.get("evidence_to_collect"):
            lines.extend(
                [
                    '  <div class="adf-step-evidence">',
                    '    <p class="adf-inline-label">Collect before moving on:</p>',
                    "    <ul>",
                    *[f"      <li>{item}</li>" for item in step["evidence_to_collect"]],
                    "    </ul>",
                    "  </div>",
                ]
            )
        lines.extend(["</div>", ""])

    lines.extend(["</div>", "</details>", ""])
    return lines


def _render_command_markdown(command: dict[str, Any]) -> list[str]:
    knowledge = _command_knowledge(command)
    healthy_markers = command.get("healthy_markers", [])
    lines = [
        '<div class="adf-check">',
        f'<p class="adf-check-label">{command["label"]}</p>',
        "",
        '<p class="adf-inline-label">Run</p>',
        "",
        "```bash",
        command["command"],
        "```",
        "",
        '<p class="adf-check-signal">',
        '  <span class="adf-inline-label">Verification:</span> ',
        f"{command['expected_signal']}",
        "</p>",
        "",
    ]
    if knowledge:
        title, knowledge_items = knowledge
        lines.extend(
            [
                '<details class="adf-check-note">',
                '  <summary class="adf-check-note-summary">',
                f"    <span>{title}</span>",
                "  </summary>",
                '  <div class="adf-check-knowledge">',
                "",
            ]
        )
        for item in knowledge_items:
            lines.append(f"- {item}")
        lines.extend(["  </div>", "</details>", ""])
    if healthy_markers:
        lines.extend(
            [
                '<p class="adf-check-reference">',
                f"Look for: {', '.join(healthy_markers)}",
                "</p>",
                "",
            ]
        )
    if command.get("interpretation"):
        lines.extend(
            [
                '<p class="adf-check-failure">',
                '  <span class="adf-inline-label">If not healthy:</span> ',
                f"{command['interpretation']}",
                "</p>",
                "",
            ]
        )

    example = command.get("example_output")
    if example:
        lines.extend(
            [
                '<p class="adf-inline-label">Known working example</p>',
                "",
                "```text",
                example.rstrip(),
                "```",
            ]
        )
    lines.extend(["</div>", ""])
    return lines


def _command_knowledge(command: dict[str, Any]) -> tuple[str, list[str]] | None:
    raw = command["command"]
    label = command["label"]
    if raw.startswith("systemctl status "):
        return ("Linux note: service status", [
            "This asks systemd whether the service is known and running now.",
            "`Loaded` means the service unit exists on the server.",
            "`Active (running)` means the service is up now. `Main PID` means systemd still sees the main process.",
        ])
    if raw.startswith("ss -lntp"):
        return ("Linux note: listening port", [
            "This checks whether Linux is listening on the expected port.",
            "`LISTEN` means a process has opened the port and is waiting for connections.",
            "If the port is missing, the service may be down, slow to start, or bound to the wrong place.",
        ])
    if raw == "df -h":
        return ("Linux note: disk pressure", [
            "This checks human-readable disk usage for the main filesystems.",
            "Focus on `Use%` and `Avail`, especially for `/` and `/data`.",
            "Disk pressure means the filesystem is close to full. When that happens, services can fail to write logs, temp files, or runtime data.",
        ])
    if raw == "df -ih":
        return ("Linux note: inode pressure", [
            "This checks inode usage, which is different from normal disk space.",
            "A filesystem can still have free space but fail because it has no free inodes left.",
            "Inode pressure means the server has too many files or directory entries. Focus on `IUse%` and whether `IFree` is close to zero.",
        ])
    if raw == "free -h":
        return ("Linux note: memory pressure", [
            "This is the quick memory check for the host.",
            "Focus on `available` memory and whether swap is starting to grow heavily.",
            "Memory pressure means the server is low on available memory. When that happens, the server slows down, swap grows, or Linux may kill a process to protect itself.",
        ])
    if raw == "uptime":
        return ("Linux note: system load", [
            "This is the quick load check for the host.",
            "Focus on the `load average` values and whether they look unexpectedly high for the server.",
            "High load can mean CPU pressure, blocked work, or heavy I/O wait.",
        ])
    if raw.startswith("journalctl -k --since"):
        return ("Linux note: OOM pressure", [
            "This checks the Linux kernel log for memory-pressure kills.",
            "OOM means Out Of Memory. Linux may kill a process to protect the server.",
            "If you see OOM or `Killed process` lines, memory pressure is likely part of the failure.",
        ])
    if raw.startswith("ps -eo pid,comm,%cpu,%mem --sort=-%cpu"):
        return ("Linux note: top CPU consumers", [
            "This shows which processes are using the most CPU right now.",
            "Focus on whether one process is dominating CPU and whether that process matches the current symptom.",
            "A single runaway process can starve the rest of the server and make higher-level application failures look worse than they are.",
        ])
    if "/health/ready" in raw:
        return ("Linux note: service readiness", [
            "This checks a local readiness endpoint instead of only checking whether the service process exists.",
            "A readiness endpoint helps prove the service is healthy enough to answer real traffic.",
            "Use the expected JSON value below as the main reference, not just the HTTP connection itself.",
        ])
    if "openid-configuration" in raw:
        return ("Linux note: OIDC path", [
            "This checks a real Keycloak OpenID Connect path that the local login flow depends on.",
            "An HTTP 200 here is a stronger proof than a simple port check because it confirms the local path is answering correctly.",
            "If this path fails while the service still looks up, treat it as an application-path problem instead of a simple process problem.",
        ])
    if "/afa/getStatus" in raw:
        return ("Linux note: service heartbeat", [
            "This checks a real ms-metro heartbeat path instead of only checking whether the Java process exists.",
            "A heartbeat response helps prove the service is alive enough to answer application traffic.",
            "Use this after the listener check when port 8080 is open but the UI still behaves badly.",
        ])
    if "/data/ms-metro/logs/localhost_access_log.txt" in raw and "grep -E '/afa/getStatus|/afa/api/v1/config/all/noauth'" in raw:
        return ("Linux note: app traffic", [
            "This checks whether ms-metro is serving useful application traffic, not only whether the port is open.",
            "Focus on whether the expected Metro paths are returning 200 responses in recent access lines.",
            "A service can look up from the outside and still fail here if the app path is returning errors or no longer serving requests.",
        ])
    if raw.startswith("ps -p $(cat /var/run/ms-metro/ms-metro.pid) -o "):
        return ("Linux note: JVM activity", [
            "This shows the live Metro JVM process with elapsed runtime, CPU, memory, and thread count.",
            "Focus on whether CPU, memory, or thread count looks unexpectedly high for the current case.",
            "This is a stronger answer to 'what is Metro busy doing' than reading random Java log lines first.",
        ])
    if raw.startswith("journalctl -u "):
        return ("Linux note: service logs", [
            "Recent service logs are often the fastest way to find the real failure clue.",
            "Focus on startup errors, permission errors, heap errors, dependency failures, and repeated retries.",
            "Use this after the status check when the service looks up but still behaves badly.",
        ])
    if raw.startswith("grep -n -i -E ") and "/data/ms-metro/logs/catalina.out" in raw:
        return ("Linux note: Java log anomalies", [
            "Large Java logs are often noisy when read from the bottom alone.",
            "This check pulls likely error signatures first so the engineer can find the useful anomaly faster.",
            "Use the line numbers and error keywords here as the first clue, then widen into the full log only if needed.",
        ])
    if raw.startswith("tail -n ") and ("/var/log/keycloak/" in raw or "/data/ms-metro/logs/" in raw):
        return ("Linux note: file-based service logs", [
            "This appliance writes the useful service clues to log files, not only to systemd journal output.",
            "Focus on startup errors, dependency failures, auth errors, heap errors, and repeated retries.",
            "Use the most specific log for the service you are checking before widening the search.",
        ])
    if label.lower().startswith("check config mapping"):
        return ("Linux note: config check", [
            "This checks whether the expected mapping still exists in the service config.",
            "Use it to confirm the route, port, or target value is still what the application expects.",
        ])
    return ("Linux note", [
        "This command gives a focused check for the current step.",
        "Use the healthy example below as the main output reference for what good looks like.",
    ])


def _render_custom_css() -> str:
    return "\n".join(
        [
            ":root {",
            "  --sl-color-accent-low: #d7ebe8;",
            "  --sl-color-accent: #155e63;",
            "  --sl-color-accent-high: #0d393e;",
            "  --adf-bg-soft: #eef3ef;",
            "  --adf-panel: rgba(255, 255, 255, 0.96);",
            "  --adf-panel-strong: #f8fbf8;",
            "  --adf-border: rgba(21, 94, 99, 0.14);",
            "  --adf-border-strong: rgba(21, 94, 99, 0.24);",
            "  --adf-muted: #52626c;",
            "  --adf-code-bg: #15262f;",
            "}",
            "",
            "body {",
            "  background: radial-gradient(circle at top, rgba(21, 94, 99, 0.07), transparent 24%), var(--adf-bg-soft);",
            "}",
            "",
            ".content-panel {",
            "  border: 1px solid var(--adf-border);",
            "  border-radius: 0.9rem;",
            "  background: rgba(255, 255, 255, 0.94);",
            "}",
            "",
            ".sl-markdown-content > :first-child {",
            "  margin-top: 0;",
            "}",
            "",
            ".sl-markdown-content {",
            "  color: #142126;",
            "}",
            "",
            ".adf-panel {",
            "  border-radius: 0.9rem;",
            "  border: 1px solid var(--adf-border);",
            "  background: linear-gradient(180deg, var(--adf-panel-strong) 0%, var(--adf-panel) 100%);",
            "  padding: 0.95rem 1rem;",
            "}",
            "",
            ".adf-panel p:last-child,",
            ".adf-panel ul:last-child {",
            "  margin-bottom: 0;",
            "}",
            "",
            ".adf-panel-label {",
            "  margin: 0 0 0.4rem;",
            "  font-size: 0.77rem;",
            "  text-transform: uppercase;",
            "  letter-spacing: 0.04em;",
            "  font-weight: 700;",
            "  color: var(--sl-color-text-accent);",
            "}",
            "",
            ".adf-home-shell,",
            ".adf-cockpit-shell {",
            "  display: grid;",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-home-topbar,",
            ".adf-cockpit-topbar {",
            "  display: grid;",
            "  grid-template-columns: repeat(2, minmax(0, 1fr));",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-home-grid {",
            "  display: grid;",
            "  grid-template-columns: repeat(2, minmax(0, 1fr));",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-home-card-grid,",
            ".adf-symptom-grid {",
            "  display: grid;",
            "  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));",
            "  gap: 0.85rem;",
            "}",
            "",
            ".adf-home-card,",
            ".adf-symptom-card,",
            ".adf-cockpit-jump,",
            ".adf-path-link {",
            "  display: grid;",
            "  gap: 0.3rem;",
            "  border-radius: 0.9rem;",
            "  border: 1px solid var(--adf-border);",
            "  background: linear-gradient(180deg, rgba(245, 250, 248, 0.96) 0%, rgba(255, 255, 255, 0.98) 100%);",
            "  padding: 0.9rem;",
            "}",
            "",
            ".adf-home-card,",
            ".adf-cockpit-jump,",
            ".adf-symptom-link,",
            ".adf-path-link {",
            "  text-decoration: none;",
            "  color: inherit;",
            "}",
            "",
            ".adf-home-card:hover,",
            ".adf-cockpit-jump:hover,",
            ".adf-symptom-link:hover,",
            ".adf-path-link:hover {",
            "  border-color: var(--adf-border-strong);",
            "  transform: translateY(-1px);",
            "}",
            "",
            ".adf-home-card span,",
            ".adf-symptom-card span,",
            ".adf-cockpit-jump span:last-child,",
            ".adf-path-link span:last-child {",
            "  color: var(--adf-muted);",
            "}",
            "",
            ".adf-home-card-list {",
            "  display: grid;",
            "  gap: 0.25rem;",
            "  font-size: 0.9rem;",
            "}",
            "",
            ".adf-service-chip-row {",
            "  display: flex;",
            "  flex-wrap: wrap;",
            "  gap: 0.5rem;",
            "  margin-top: 0.35rem;",
            "}",
            "",
            ".adf-service-chip {",
            "  display: inline-flex;",
            "  align-items: center;",
            "  padding: 0.3rem 0.72rem;",
            "  border-radius: 999px;",
            "  background: rgba(255, 255, 255, 0.95);",
            "  border: 1px solid var(--adf-border);",
            "  color: var(--adf-muted);",
            "  font-size: 0.9rem;",
            "}",
            "",
            ".adf-cockpit-grid {",
            "  display: grid;",
            "  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-cockpit-main {",
            "  display: grid;",
            "  gap: 1rem;",
            "  min-width: 0;",
            "}",
            "",
            ".adf-cockpit-nav {",
            "  align-self: start;",
            "  position: sticky;",
            "  top: 1.1rem;",
            "}",
            "",
            ".adf-cockpit-jumps,",
            ".adf-path-list {",
            "  display: grid;",
            "  gap: 0.65rem;",
            "}",
            "",
            ".adf-cockpit-sideblock {",
            "  margin-top: 0.9rem;",
            "  border-top: 1px solid var(--adf-border);",
            "  padding-top: 0.9rem;",
            "}",
            "",
            ".adf-cockpit-sideblock ul {",
            "  margin: 0;",
            "  padding-left: 1.1rem;",
            "}",
            "",
            ".adf-route-step {",
            "  font-size: 0.76rem;",
            "  text-transform: uppercase;",
            "  letter-spacing: 0.04em;",
            "  font-weight: 700;",
            "  color: var(--sl-color-text-accent);",
            "}",
            "",
            ".adf-cockpit-strip,",
            ".adf-cockpit-path {",
            "  border-radius: 0.9rem;",
            "  border: 1px solid var(--adf-border);",
            "  background: linear-gradient(180deg, rgba(242, 248, 245, 0.95) 0%, rgba(255, 255, 255, 0.98) 100%);",
            "  padding: 0.9rem 1rem;",
            "}",
            "",
            ".adf-checkpoint {",
            "  margin: 0.9rem 0;",
            "  border: 1px solid var(--adf-border);",
            "  border-radius: 0.95rem;",
            "  background: rgba(255, 255, 255, 0.98);",
            "  padding: 0.15rem 0.95rem 0.9rem;",
            "  scroll-margin-top: 1rem;",
            "}",
            "",
            ".adf-step-summary {",
            "  display: flex;",
            "  align-items: flex-start;",
            "  gap: 0.75rem;",
            "  cursor: pointer;",
            "  list-style: none;",
            "  padding: 0.8rem 0 0.4rem;",
            "}",
            "",
            ".adf-step-summary::-webkit-details-marker,",
            ".adf-step-summary::marker {",
            "  display: none;",
            "}",
            "",
            ".adf-step-badge {",
            "  display: inline-flex;",
            "  align-items: center;",
            "  justify-content: center;",
            "  min-width: 4.4rem;",
            "  border-radius: 999px;",
            "  background: var(--sl-color-text-accent);",
            "  color: white;",
            "  font-size: 0.82rem;",
            "  font-weight: 700;",
            "  padding: 0.28rem 0.76rem;",
            "}",
            "",
            ".adf-step-heading {",
            "  display: grid;",
            "  gap: 0.18rem;",
            "  flex: 1 1 auto;",
            "}",
            "",
            ".adf-step-heading span {",
            "  color: var(--adf-muted);",
            "  line-height: 1.4;",
            "}",
            "",
            ".adf-step-toggle {",
            "  margin-left: auto;",
            "  align-self: center;",
            "  color: var(--sl-color-text-accent);",
            "  font-weight: 700;",
            "  white-space: nowrap;",
            "  padding-left: 0.75rem;",
            "}",
            "",
            ".adf-step-toggle::before {",
            "  content: 'Open';",
            "}",
            "",
            ".adf-checkpoint[open] .adf-step-toggle::before {",
            "  content: 'Close';",
            "}",
            "",
            ".adf-step-body {",
            "  display: grid;",
            "  gap: 0.8rem;",
            "  padding-top: 0.2rem;",
            "}",
            "",
            ".adf-check {",
            "  border-top: 1px solid rgba(21, 94, 99, 0.08);",
            "  padding-top: 0.85rem;",
            "}",
            "",
            ".adf-step-body > .adf-check:first-of-type {",
            "  border-top: 0;",
            "  padding-top: 0;",
            "}",
            "",
            ".adf-check-label {",
            "  margin: 0 0 0.55rem;",
            "  font-weight: 700;",
            "}",
            "",
            ".adf-inline-label {",
            "  font-size: 0.78rem;",
            "  text-transform: uppercase;",
            "  letter-spacing: 0.04em;",
            "  font-weight: 700;",
            "  color: var(--sl-color-text-accent);",
            "}",
            "",
            ".adf-step-brief,",
            ".adf-check-signal,",
            ".adf-check-reference,",
            ".adf-check-failure,",
            ".adf-step-outcome {",
            "  margin: 0;",
            "  color: #142126;",
            "}",
            "",
            ".adf-check-knowledge,",
            ".adf-step-evidence {",
            "  border-left: 3px solid rgba(21, 94, 99, 0.16);",
            "  padding-left: 0.85rem;",
            "}",
            "",
            ".adf-check-note {",
            "  border-left: 3px solid rgba(21, 94, 99, 0.16);",
            "  padding-left: 0.85rem;",
            "}",
            "",
            ".adf-check-note-summary {",
            "  cursor: pointer;",
            "  list-style: none;",
            "  font-size: 0.78rem;",
            "  text-transform: uppercase;",
            "  letter-spacing: 0.04em;",
            "  font-weight: 700;",
            "  color: var(--sl-color-text-accent);",
            "}",
            "",
            ".adf-check-note-summary::-webkit-details-marker,",
            ".adf-check-note-summary::marker {",
            "  display: none;",
            "}",
            "",
            ".adf-check-note-summary span::after {",
            "  content: '  +';",
            "}",
            "",
            ".adf-check-note[open] .adf-check-note-summary span::after {",
            "  content: '  -';",
            "}",
            "",
            ".adf-check-knowledge ul,",
            ".adf-step-evidence ul {",
            "  margin: 0.35rem 0 0;",
            "  padding-left: 1.05rem;",
            "}",
            "",
            ".adf-step-outcomes {",
            "  display: grid;",
            "  gap: 0.55rem;",
            "  padding-top: 0.2rem;",
            "}",
            "",
            ".adf-cockpit-path {",
            "  display: grid;",
            "  gap: 0.6rem;",
            "  min-width: 0;",
            "}",
            "",
            ".adf-path-list {",
            "  list-style: none;",
            "  margin: 0;",
            "  padding: 0;",
            "  grid-auto-flow: column;",
            "  grid-auto-columns: minmax(15rem, 1fr);",
            "  align-items: stretch;",
            "  overflow-x: auto;",
            "  padding-bottom: 0.2rem;",
            "  scroll-snap-type: x proximity;",
            "}",
            "",
            ".adf-path-item {",
            "  position: relative;",
            "  min-width: 0;",
            "}",
            "",
            ".adf-path-item + .adf-path-item::before {",
            "  content: '->';",
            "  position: absolute;",
            "  left: -0.7rem;",
            "  top: 50%;",
            "  transform: translateY(-50%);",
            "  color: var(--sl-color-text-accent);",
            "  font-weight: 700;",
            "}",
            "",
            ".adf-path-link {",
            "  height: 100%;",
            "  min-height: 100%;",
            "  scroll-snap-align: start;",
            "}",
            "",
            ".sl-markdown-content details > summary + * {",
            "  margin-top: 0.25rem;",
            "}",
            "",
            ".sl-markdown-content pre {",
            "  border-radius: 0.8rem;",
            "  background: var(--adf-code-bg);",
            "}",
            "",
            "@media (max-width: 60rem) {",
            "  .adf-home-topbar,",
            "  .adf-home-grid,",
            "  .adf-cockpit-topbar,",
            "  .adf-cockpit-grid {",
            "    grid-template-columns: 1fr;",
            "  }",
            "  .adf-cockpit-nav {",
            "    position: static;",
            "  }",
            "  .adf-path-list {",
            "    grid-auto-flow: row;",
            "    grid-auto-columns: minmax(0, 1fr);",
            "    overflow-x: visible;",
            "    padding-bottom: 0;",
            "    scroll-snap-type: none;",
            "  }",
            "  .adf-path-item + .adf-path-item::before {",
            "    content: '';",
            "  }",
            "}",
            "",
            "@media (max-width: 50rem) {",
            "  .adf-step-summary {",
            "    flex-wrap: wrap;",
            "  }",
            "  .adf-step-toggle {",
            "    margin-left: 5.1rem;",
            "    padding-left: 0;",
            "  }",
            "}",
            "",
        ]
    ) + "\n"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "playbook"


def _starlight_target_for_playbook_id(playbook_nav_entries: list[dict[str, str | int]], playbook_id: str) -> str:
    for entry in playbook_nav_entries:
        if entry.get("playbook_id") == playbook_id:
            return f"/{entry['slug']}/"
    return "/"


def _primary_nav_entry(playbook_nav_entries: list[dict[str, str | int]]) -> dict[str, str | int] | None:
    for entry in playbook_nav_entries:
        if entry.get("playbook_id") == PRIMARY_PLAYBOOK_ID:
            return entry
    return playbook_nav_entries[0] if playbook_nav_entries else None


def _step_summary_label(step: dict[str, Any]) -> str:
    action = step["action"]
    if "." in action:
        return action.split(".", 1)[0].strip()
    return action


def _symptoms_by_playbook(support_baseline: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    symptom_map: dict[str, list[dict[str, str]]] = {}
    for item in support_baseline.get("symptom_lookup", []):
        playbook_id = item.get("playbook_id") or item.get("suggested_domain_id")
        if not playbook_id:
            continue
        symptom_map.setdefault(playbook_id, []).append(item)
    return symptom_map
