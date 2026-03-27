from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROTOTYPES = [
    {
        "slug": "triage-console",
        "title": "ADF Prototype 1",
        "subtitle": "Triage Console",
        "description": "A second-screen triage console for engineers who need one clear lane, one clear route, and one clear next command.",
        "home_heading": "Triage Console",
        "home_copy": "This concept treats a playbook like a live operator console instead of a documentation page.",
    },
    {
        "slug": "mission-board",
        "title": "ADF Prototype 2",
        "subtitle": "Mission Board",
        "description": "A visual mission board that turns deterministic troubleshooting into a sequence of bold checkpoints and stop points.",
        "home_heading": "Mission Board",
        "home_copy": "This concept leans into a guided mission metaphor: start here, move forward, stop at the first broken checkpoint.",
    },
    {
        "slug": "support-cockpit",
        "title": "ADF Prototype 3",
        "subtitle": "Support Cockpit",
        "description": "A compact support cockpit for fast scanning under pressure, with commands and healthy output kept close together.",
        "home_heading": "Support Cockpit",
        "home_copy": "This concept treats the playbook like a compact control panel for an engineer who is juggling a customer screen and a shell.",
    },
]

PLAYBOOKS = [
    {
        "slug": "application-ui-wont-load",
        "title": "Application UI won't load",
        "summary": "Use this when the customer says the application UI is down and the engineer is already on SSH.",
        "services": ["httpd.service", "app-ui.service", "postgresql.service"],
        "route": [
            {
                "step": "Step 1",
                "label": "Web edge",
                "details": "Confirm the web service is active and ports 80 and 443 are listening before going deeper.",
            },
            {
                "step": "Step 2",
                "label": "Host pressure",
                "details": "Check disk, inodes, memory, and recent OOM pressure because Linux resource failures often break the UI first.",
            },
            {
                "step": "Step 3",
                "label": "App service",
                "details": "Confirm the application service is active, listening, and not blocked by a dependency issue.",
            },
            {
                "step": "Step 4",
                "label": "Logs",
                "details": "If the services look up, use logs to find the real clue before escalating.",
            },
        ],
        "steps": [
            {
                "id": "ui-step-1",
                "step": "Step 1",
                "label": "Web edge",
                "focus": "Check the web edge first. Confirm httpd.service is running and ports 80 and 443 are open.",
                "why": "When the UI is down, the fastest first question is whether the front door is still open.",
                "checks": [
                    {
                        "label": "Check httpd.service status",
                        "command": "systemctl status httpd.service --no-pager",
                        "healthy": "Loaded and active (running).",
                        "why": [
                            "This tells you whether systemd still sees the service as up.",
                            "Focus on Loaded, Active, and the Main PID line.",
                        ],
                        "example": "\n".join(
                            [
                                "● httpd.service - The Apache HTTP Server",
                                "   Loaded: loaded (/usr/lib/systemd/system/httpd.service; enabled)",
                                "   Active: active (running) since Tue 2026-03-24 09:13:05 UTC; 34min ago",
                                " Main PID: 1243 (/usr/sbin/httpd)",
                            ]
                        ),
                    },
                    {
                        "label": "Check web listeners",
                        "command": "ss -lntp | grep -E ':(80|443)\\b'",
                        "healthy": "Both ports are listening.",
                        "why": [
                            "A service can look up in systemd and still fail to bind the expected port.",
                            "Focus on LISTEN, :80, :443, and the process name.",
                        ],
                        "example": "\n".join(
                            [
                                'LISTEN 0 511 0.0.0.0:443 0.0.0.0:* users:(("httpd",pid=1243,fd=4),...)',
                                'LISTEN 0 511 0.0.0.0:80  0.0.0.0:* users:(("httpd",pid=1243,fd=3),...)',
                            ]
                        ),
                    },
                ],
            },
            {
                "id": "ui-step-2",
                "step": "Step 2",
                "label": "Host pressure",
                "focus": "Check Linux host pressure next. Confirm the server still has free disk, free inodes, and available memory.",
                "why": "Application failures often come from normal Linux pressure before they come from rare application config problems.",
                "checks": [
                    {
                        "label": "Check disk usage",
                        "command": "df -h",
                        "healthy": "Main filesystems still have free space and are not near 100% use.",
                        "why": [
                            "Disk full is one of the most common triage findings on Linux hosts.",
                            "Focus on Use% and Avail, especially for / and /data.",
                        ],
                        "example": "\n".join(
                            [
                                "Filesystem           Size  Used Avail Use% Mounted on",
                                "/dev/mapper/rl-root   60G   17G   44G  28% /",
                                "/dev/mapper/rl-data  240G   22G  219G   9% /data",
                            ]
                        ),
                    },
                    {
                        "label": "Check inode usage",
                        "command": "df -ih",
                        "healthy": "Main filesystems still have free inodes.",
                        "why": [
                            "A filesystem can fail even when disk space looks fine if inode use is exhausted.",
                            "Focus on IUse% and IFree.",
                        ],
                        "example": "\n".join(
                            [
                                "Filesystem          Inodes IUsed IFree IUse% Mounted on",
                                "/dev/mapper/rl-root    30M  351K   30M    2% /",
                                "/dev/mapper/rl-data   119M   24K  119M    1% /data",
                            ]
                        ),
                    },
                    {
                        "label": "Check memory pressure",
                        "command": "free -h",
                        "healthy": "Available memory is present and swap is not heavily used.",
                        "why": [
                            "Java applications often slow down or crash before the whole host appears dead.",
                            "Focus on available memory and swap growth.",
                        ],
                        "example": "\n".join(
                            [
                                "              total        used        free      shared  buff/cache   available",
                                "Mem:           32Gi        14Gi       7.8Gi       2.1Gi        10Gi        14Gi",
                                "Swap:          24Gi          0B        24Gi",
                            ]
                        ),
                    },
                    {
                        "label": "Check for recent OOM pressure",
                        "command": "journalctl -k --since '-24 hours' --no-pager | grep -i -E 'out of memory|oom|killed process' | tail -n 20",
                        "healthy": "No recent OOM lines are returned.",
                        "why": [
                            "OOM means Linux killed or starved a process because the host ran out of memory.",
                            "If you see OOM lines, host pressure is part of the failure story.",
                        ],
                        "example": "No output",
                    },
                ],
            },
            {
                "id": "ui-step-3",
                "step": "Step 3",
                "label": "App service",
                "focus": "Check the main application service. Confirm app-ui.service is running and the app listener is open.",
                "why": "If Linux looks healthy, the next common failure is that the app process is down, hung, or unable to bind.",
                "checks": [
                    {
                        "label": "Check app-ui.service status",
                        "command": "systemctl status app-ui.service --no-pager",
                        "healthy": "Loaded and active (running).",
                        "why": [
                            "This confirms the application service itself is still under systemd control.",
                            "Focus on Active and recent restart history.",
                        ],
                        "example": "\n".join(
                            [
                                "● app-ui.service - Example Application UI",
                                "   Loaded: loaded (/etc/systemd/system/app-ui.service; enabled)",
                                "   Active: active (running) since Tue 2026-03-24 09:16:42 UTC; 31min ago",
                                " Main PID: 2418 (java)",
                            ]
                        ),
                    },
                    {
                        "label": "Check application listener",
                        "command": "ss -lntp | grep ':8080\\b'",
                        "healthy": "The application listener is present on 8080.",
                        "why": [
                            "A Java process can exist but still fail to open its expected port.",
                            "Focus on LISTEN, :8080, and the owning process.",
                        ],
                        "example": 'LISTEN 0 200 0.0.0.0:8080 0.0.0.0:* users:(("java",pid=2418,fd=202))',
                    },
                ],
            },
            {
                "id": "ui-step-4",
                "step": "Step 4",
                "label": "Logs",
                "focus": "Check recent logs. Look for disk, permission, startup, heap, or dependency errors before escalating.",
                "why": "When services still look healthy, logs usually reveal the real clue faster than deeper config review.",
                "checks": [
                    {
                        "label": "Review web service logs",
                        "command": "journalctl -u httpd.service -n 50 --no-pager",
                        "healthy": "No obvious startup, permission, or crash errors appear.",
                        "why": [
                            "This is the fastest way to confirm whether the web tier is complaining about the application or the host.",
                        ],
                        "example": "",
                    },
                    {
                        "label": "Review application logs",
                        "command": "journalctl -u app-ui.service -n 50 --no-pager",
                        "healthy": "No obvious startup, heap, dependency, or crash errors appear.",
                        "why": [
                            "This is where Java stack traces, dependency failures, and startup loops usually appear first.",
                        ],
                        "example": "",
                    },
                ],
            },
        ],
    },
    {
        "slug": "service-wont-start",
        "title": "Application service will not start",
        "summary": "Use this when a service is stopped, flapping, or exits immediately after restart.",
        "services": ["app-worker.service", "port 9090", "lock files"],
        "route": [
            {"step": "Step 1", "label": "Service state", "details": "Check the service state and recent exit reason."},
            {"step": "Step 2", "label": "Port or lock conflict", "details": "Check whether a stale lock or occupied port is blocking startup."},
            {"step": "Step 3", "label": "Permissions and files", "details": "Check runtime paths, ownership, and writable directories."},
            {"step": "Step 4", "label": "Logs", "details": "Use logs to isolate config, dependency, or Java startup failure clues."},
        ],
        "steps": [
            {
                "id": "svc-step-1",
                "step": "Step 1",
                "label": "Service state",
                "focus": "Check the service state first. Confirm whether the service is stopped, failed, or restarting.",
                "why": "The quickest way to start triage is to see exactly how systemd understands the failure.",
                "checks": [
                    {
                        "label": "Check app-worker.service status",
                        "command": "systemctl status app-worker.service --no-pager",
                        "healthy": "Loaded and active (running).",
                        "why": [
                            "Focus on Active, Result, exit code lines, and restart messages.",
                        ],
                        "example": "\n".join(
                            [
                                "● app-worker.service - Example Background Worker",
                                "   Loaded: loaded (/etc/systemd/system/app-worker.service; enabled)",
                                "   Active: failed (Result: exit-code) since Tue 2026-03-24 10:18:11 UTC; 2min ago",
                                "  Process: 7821 ExecStart=/opt/example/bin/worker start (code=exited, status=1/FAILURE)",
                            ]
                        ),
                    }
                ],
            },
            {
                "id": "svc-step-2",
                "step": "Step 2",
                "label": "Port or lock conflict",
                "focus": "Check for stale lock files or a port that is already occupied by another process.",
                "why": "Startup failures are often simple Linux conflicts rather than application bugs.",
                "checks": [
                    {
                        "label": "Check for port conflicts",
                        "command": "ss -lntp | grep ':9090\\b'",
                        "healthy": "Only the expected service owns the port, or no stale listener is present before startup.",
                        "why": [
                            "If another process already owns the port, the service cannot bind and will fail to start.",
                        ],
                        "example": 'LISTEN 0 128 0.0.0.0:9090 0.0.0.0:* users:(("java",pid=8121,fd=122))',
                    },
                    {
                        "label": "Check for stale lock files",
                        "command": "find /var/run /tmp -maxdepth 2 -type f | grep app-worker",
                        "healthy": "No stale lock or pid file is left behind after a failed run.",
                        "why": [
                            "Applications sometimes refuse to start because they think an old instance is still running.",
                        ],
                        "example": "No output",
                    },
                ],
            },
            {
                "id": "svc-step-3",
                "step": "Step 3",
                "label": "Permissions and files",
                "focus": "Check runtime paths and permissions. Confirm the service can read configs and write temp or log files.",
                "why": "Permissions, ownership, and missing files are classic Linux startup failures.",
                "checks": [
                    {
                        "label": "Check service user and runtime directories",
                        "command": "namei -l /opt/example /opt/example/logs /opt/example/tmp",
                        "healthy": "The service user can traverse and write the required directories.",
                        "why": [
                            "This exposes ownership and mode bits across the whole path, not just the final directory.",
                        ],
                        "example": "\n".join(
                            [
                                "f: /opt/example/logs",
                                "drwxr-xr-x root     root     /",
                                "drwxr-xr-x root     root     opt",
                                "drwxr-x--- example  example  example",
                                "drwxrwx--- example  example  logs",
                            ]
                        ),
                    }
                ],
            },
            {
                "id": "svc-step-4",
                "step": "Step 4",
                "label": "Logs",
                "focus": "Check recent logs. Look for permission, bind, config, file lock, or dependency errors.",
                "why": "Once simple Linux conflicts are ruled out, the logs usually show the direct startup blocker.",
                "checks": [
                    {
                        "label": "Review service logs",
                        "command": "journalctl -u app-worker.service -n 80 --no-pager",
                        "healthy": "No recurring bind, permission, dependency, or stack trace errors appear.",
                        "why": [
                            "This is where you will usually find the first clear reason the process exited.",
                        ],
                        "example": "",
                    }
                ],
            },
        ],
    },
    {
        "slug": "linux-host-under-pressure",
        "title": "Linux host under pressure",
        "summary": "Use this when multiple services are acting strangely and the host itself may be the real problem.",
        "services": ["disk", "memory", "inodes", "locks"],
        "route": [
            {"step": "Step 1", "label": "Disk", "details": "Check whether normal disk space is exhausted on critical filesystems."},
            {"step": "Step 2", "label": "Memory", "details": "Check whether memory pressure or OOM events are starving processes."},
            {"step": "Step 3", "label": "File pressure", "details": "Check inode usage, open file pressure, and stale locks."},
            {"step": "Step 4", "label": "Logs", "details": "Use kernel and service logs to confirm which pressure signal is real."},
        ],
        "steps": [
            {
                "id": "host-step-1",
                "step": "Step 1",
                "label": "Disk",
                "focus": "Check disk first. Confirm /, /var, and /data still have free space.",
                "why": "Disk pressure is one of the fastest ways to make many unrelated services fail at once.",
                "checks": [
                    {
                        "label": "Check disk usage",
                        "command": "df -h",
                        "healthy": "Critical filesystems still have free space.",
                        "why": [
                            "A service cannot write logs, temp files, or state when the host is full.",
                        ],
                        "example": "\n".join(
                            [
                                "Filesystem           Size  Used Avail Use% Mounted on",
                                "/dev/mapper/rl-root   60G   18G   43G  30% /",
                                "/dev/mapper/rl-var    20G   11G    9G  56% /var",
                                "/dev/mapper/rl-data  240G   22G  219G   9% /data",
                            ]
                        ),
                    }
                ],
            },
            {
                "id": "host-step-2",
                "step": "Step 2",
                "label": "Memory",
                "focus": "Check memory pressure next. Confirm the host still has available memory and no recent OOM events.",
                "why": "When memory is low, Linux may kill processes and create scattered symptoms across the application stack.",
                "checks": [
                    {
                        "label": "Check memory usage",
                        "command": "free -h",
                        "healthy": "Available memory is present and swap is not heavily used.",
                        "why": [
                            "This is the fastest memory snapshot for triage.",
                        ],
                        "example": "\n".join(
                            [
                                "              total        used        free      shared  buff/cache   available",
                                "Mem:           64Gi        32Gi       6.4Gi       3.0Gi        25Gi        28Gi",
                                "Swap:          24Gi          0B        24Gi",
                            ]
                        ),
                    },
                    {
                        "label": "Check recent OOM events",
                        "command": "journalctl -k --since '-24 hours' --no-pager | grep -i -E 'out of memory|oom|killed process' | tail -n 20",
                        "healthy": "No recent OOM lines are returned.",
                        "why": [
                            "This confirms whether Linux has already started killing processes.",
                        ],
                        "example": "No output",
                    },
                ],
            },
            {
                "id": "host-step-3",
                "step": "Step 3",
                "label": "File pressure",
                "focus": "Check inode and file pressure. Confirm the host is not out of inodes and not trapped by stale file locks.",
                "why": "Disk space alone does not explain many Linux failures. Inodes and locks matter too.",
                "checks": [
                    {
                        "label": "Check inode usage",
                        "command": "df -ih",
                        "healthy": "Critical filesystems still have free inodes.",
                        "why": [
                            "Inode exhaustion looks like a file error even when normal disk space appears free.",
                        ],
                        "example": "\n".join(
                            [
                                "Filesystem          Inodes IUsed IFree IUse% Mounted on",
                                "/dev/mapper/rl-root    30M  360K   30M    2% /",
                                "/dev/mapper/rl-var     12M  210K   12M    2% /var",
                            ]
                        ),
                    },
                    {
                        "label": "Check for common stale lock files",
                        "command": "find /var/lock /var/run /tmp -maxdepth 2 -type f | head -n 20",
                        "healthy": "No suspicious stale application lock files are blocking normal service behavior.",
                        "why": [
                            "A stale lock can stop one service, a batch job, or an application restart even when the host looks healthy.",
                        ],
                        "example": "",
                    },
                ],
            },
            {
                "id": "host-step-4",
                "step": "Step 4",
                "label": "Logs",
                "focus": "Check kernel and service logs. Look for pressure signals that repeat across more than one service.",
                "why": "Shared host pressure usually leaves clues in more than one place.",
                "checks": [
                    {
                        "label": "Review kernel warnings",
                        "command": "journalctl -k -n 80 --no-pager",
                        "healthy": "No recurring OOM, IO, mount, or filesystem warnings appear.",
                        "why": [
                            "Kernel warnings often reveal the host-level issue before application logs explain it clearly.",
                        ],
                        "example": "",
                    }
                ],
            },
        ],
    },
]


def generate_starlight_prototypes(*, project_root: Path, output_root: str | Path | None = None) -> dict[str, Any]:
    base_root = project_root / (Path(output_root) if output_root else Path("dist/prototypes/starlight"))
    generated_files: list[str] = []
    sites: list[dict[str, str]] = []

    for prototype in PROTOTYPES:
        site_root = base_root / prototype["slug"]
        docs_root = site_root / "src" / "content" / "docs"
        playbooks_root = docs_root / "playbooks"
        playbooks_root.mkdir(parents=True, exist_ok=True)

        (site_root / "package.json").write_text(_render_package_json(prototype), encoding="utf-8")
        (site_root / "astro.config.mjs").write_text(_render_astro_config(prototype), encoding="utf-8")
        (site_root / "tsconfig.json").write_text('{\n  "extends": "astro/tsconfigs/strict"\n}\n', encoding="utf-8")
        (site_root / "src" / "content.config.ts").parent.mkdir(parents=True, exist_ok=True)
        (site_root / "src" / "content.config.ts").write_text(_render_content_config(), encoding="utf-8")
        (site_root / "src" / "custom.css").write_text(_render_custom_css(prototype), encoding="utf-8")
        (docs_root / "index.mdx").write_text(_render_homepage(prototype), encoding="utf-8")

        for order, playbook in enumerate(PLAYBOOKS, start=1):
            filename = f"{playbook['slug']}.md"
            (playbooks_root / filename).write_text(_render_playbook(prototype, playbook, order), encoding="utf-8")
            generated_files.append(str((playbooks_root / filename).relative_to(project_root)))

        generated_files.extend(
            [
                str((site_root / "package.json").relative_to(project_root)),
                str((site_root / "astro.config.mjs").relative_to(project_root)),
                str((site_root / "tsconfig.json").relative_to(project_root)),
                str((site_root / "src" / "content.config.ts").relative_to(project_root)),
                str((site_root / "src" / "custom.css").relative_to(project_root)),
                str((docs_root / "index.mdx").relative_to(project_root)),
            ]
        )
        sites.append({"slug": prototype["slug"], "artifact_root": str(site_root.relative_to(project_root))})

    return {
        "status": "pass",
        "artifact_root": str(base_root.relative_to(project_root)),
        "generated_files": generated_files,
        "summary": {
            "site_count": len(PROTOTYPES),
            "playbook_count_per_site": len(PLAYBOOKS),
            "sites": sites,
        },
    }


def _render_package_json(prototype: dict[str, str]) -> str:
    payload = {
        "name": f"adf-prototype-{prototype['slug']}",
        "private": True,
        "type": "module",
        "scripts": {
            "dev": "astro dev",
            "build": "astro build",
        },
        "dependencies": {
            "astro": "latest",
            "@astrojs/starlight": "latest",
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def _render_astro_config(prototype: dict[str, str]) -> str:
    sidebar_items = json.dumps(
        [{"label": playbook["title"], "slug": f"playbooks/{playbook['slug']}"} for playbook in PLAYBOOKS],
        indent=12,
    )
    return (
        "import { defineConfig } from 'astro/config';\n"
        "import starlight from '@astrojs/starlight';\n\n"
        "export default defineConfig({\n"
        "  integrations: [\n"
        "    starlight({\n"
        f"      title: {json.dumps(prototype['title'] + ' · ' + prototype['subtitle'])},\n"
        f"      description: {json.dumps(prototype['description'])},\n"
        "      customCss: ['./src/custom.css'],\n"
        "      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 2 },\n"
        "      sidebar: [\n"
        "        {\n"
        "          label: 'Start',\n"
        "          items: [{ label: 'Overview', slug: 'index' }],\n"
        "        },\n"
        "        {\n"
        "          label: 'Sample Playbooks',\n"
        f"          items: {sidebar_items},\n"
        "        },\n"
        "      ],\n"
        "    }),\n"
        "  ],\n"
        "});\n"
    )


def _render_content_config() -> str:
    return (
        "import { defineCollection } from 'astro:content';\n"
        "import { docsLoader } from '@astrojs/starlight/loaders';\n"
        "import { docsSchema } from '@astrojs/starlight/schema';\n\n"
        "export const collections = {\n"
        "  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),\n"
        "};\n"
    )


def _render_homepage(prototype: dict[str, str]) -> str:
    home_cards = "\n".join(
        [
            f'<a class="proto-home-card" href="/playbooks/{playbook["slug"]}/"><strong>{playbook["title"]}</strong><span>{playbook["summary"]}</span></a>'
            for playbook in PLAYBOOKS
        ]
    )
    lines = [
        "---",
        f"title: {prototype['title']} · {prototype['subtitle']}",
        f"description: {prototype['description']}",
        "sidebar:",
        "  label: Overview",
        "  order: 1",
        "---",
        "",
        f"# {prototype['home_heading']}",
        "",
        prototype["home_copy"],
        "",
        "These prototype sites use fake triage data only. The goal is to compare interface styles, not content accuracy.",
        "",
        "## Triage context",
        "",
        "- Engineers are on SSH during a live case.",
        "- They troubleshoot both Linux and the application running on Linux.",
        "- Common Linux failures like disk pressure, OOM, file locks, inode exhaustion, and port conflicts can break the application.",
        "- The job is triage: find the first broken checkpoint fast and move the case forward with confidence.",
        "",
        "## Sample playbooks",
        "",
        '<div class="proto-home-grid">',
        home_cards,
        "</div>",
        "",
    ]
    return "\n".join(lines) + "\n"


def _render_playbook(prototype: dict[str, str], playbook: dict[str, Any], order: int) -> str:
    lines = [
        "---",
        f"title: {playbook['title']}",
        f"description: {playbook['summary']}",
        "sidebar:",
        f"  label: {playbook['title']}",
        f"  order: {order}",
        "---",
        "",
    ]
    if prototype["slug"] == "triage-console":
        lines.extend(_render_triage_console(playbook))
    elif prototype["slug"] == "mission-board":
        lines.extend(_render_mission_board(playbook))
    else:
        lines.extend(_render_support_cockpit(playbook))
    lines.extend(
        [
            "<script>",
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
    return "\n".join(lines)


def _render_triage_console(playbook: dict[str, Any]) -> list[str]:
    service_chips = "\n".join([f'    <span class="proto-chip">{service}</span>' for service in playbook["services"]])
    route_nodes = "\n".join(
        [
            "\n".join(
                [
                    f'<a class="proto-route-node proto-console-node" href="#{step["id"]}">',
                    f'  <span class="proto-route-step">{step["step"]}</span>',
                    f'  <strong>{step["label"]}</strong>',
                    f'  <span>{step["focus"]}</span>',
                    "</a>",
                ]
            )
            for step in playbook["steps"]
        ]
    )
    lines = [
        playbook["summary"],
        "",
        "## Console view",
        "",
        '<div class="proto-console-shell">',
        '  <aside class="proto-console-rail">',
        '    <div class="proto-panel proto-console-panel">',
        "      <p class=\"proto-kicker\">Working rule</p>",
        "      <p>Move top to bottom. Stop at the first checkpoint that does not look healthy.</p>",
        "    </div>",
        '    <div class="proto-panel proto-console-panel">',
        "      <p class=\"proto-kicker\">Likely surfaces</p>",
        '      <div class="proto-chip-row">',
        service_chips,
        "      </div>",
        "    </div>",
        '    <div class="proto-panel proto-console-panel">',
        "      <p class=\"proto-kicker\">Route map</p>",
        f"      <div class=\"proto-route proto-console-route\">{route_nodes}</div>",
        "    </div>",
        "  </aside>",
        '  <div class="proto-console-main">',
        '    <div class="proto-panel proto-console-panel">',
        '      <p class="proto-kicker">Active lane</p>',
        '      <p>Open one checkpoint at a time. Run the command. Compare the output. Stop at the first broken checkpoint.</p>',
        "    </div>",
    ]
    for step in playbook["steps"]:
        lines.extend(_render_step_details(step, variant="console"))
    lines.extend(["  </div>", "</div>", ""])
    return lines


def _render_mission_board(playbook: dict[str, Any]) -> list[str]:
    route_tiles = "\n".join(
        [
            "\n".join(
                [
                    f'<a class="proto-board-tile" href="#{step["id"]}">',
                    f'  <span class="proto-route-step">{step["step"]}</span>',
                    f'  <strong>{step["label"]}</strong>',
                    f'  <span>{step["focus"]}</span>',
                    "</a>",
                ]
            )
            for step in playbook["steps"]
        ]
    )
    lines = [
        playbook["summary"],
        "",
        "## Mission board",
        "",
        '<div class="proto-board-hero">',
        '  <div class="proto-panel proto-board-brief">',
        "    <p class=\"proto-kicker\">Mission</p>",
        f"    <h2>{playbook['title']}</h2>",
        "    <p>Start at the top of the route. Each checkpoint is a stop point. The first broken checkpoint becomes the working failure point.</p>",
        '    <div class="proto-chip-row">',
        *[f'      <span class="proto-chip">{service}</span>' for service in playbook["services"]],
        "    </div>",
        "  </div>",
        '  <div class="proto-board-map">',
        route_tiles,
        "  </div>",
        "</div>",
        "",
        "## Checkpoint board",
        "",
    ]
    for step in playbook["steps"]:
        lines.extend(_render_step_details(step, variant="board"))
    return lines


def _render_support_cockpit(playbook: dict[str, Any]) -> list[str]:
    route_list = "\n".join(
        [
            "\n".join(
                [
                    f'<a class="proto-cockpit-jump" href="#{step["id"]}">',
                    f'  <span class="proto-route-step">{step["step"]}</span>',
                    f'  <strong>{step["label"]}</strong>',
                    "</a>",
                ]
            )
            for step in playbook["steps"]
        ]
    )
    lines = [
        playbook["summary"],
        "",
        "## Cockpit layout",
        "",
        '<div class="proto-cockpit-shell">',
        '  <div class="proto-cockpit-topbar">',
        '    <div class="proto-panel proto-cockpit-strip">',
        "      <p class=\"proto-kicker\">Case mode</p>",
        "      <p>Live triage over SSH. Reduce guesswork. Keep the next command visible.</p>",
        "    </div>",
        '    <div class="proto-panel proto-cockpit-strip">',
        "      <p class=\"proto-kicker\">Core surfaces</p>",
        '      <div class="proto-chip-row">',
        *[f'        <span class="proto-chip">{service}</span>' for service in playbook["services"]],
        "      </div>",
        "    </div>",
        "  </div>",
        '  <div class="proto-cockpit-grid">',
        '    <aside class="proto-cockpit-nav proto-panel">',
        "      <p class=\"proto-kicker\">Quick jump</p>",
        f"      <div class=\"proto-cockpit-jumps\">{route_list}</div>",
        "    </aside>",
        '    <div class="proto-cockpit-main">',
        '      <div class="proto-panel proto-cockpit-strip">',
        '        <p class="proto-kicker">Command deck</p>',
        '        <p>Keep the next command and the healthy reference close together so the engineer can glance left and run right.</p>',
        "      </div>",
    ]
    for step in playbook["steps"]:
        lines.extend(_render_step_details(step, variant="cockpit"))
    lines.extend(["    </div>", "  </div>", "</div>", ""])
    return lines


def _render_step_details(step: dict[str, Any], *, variant: str) -> list[str]:
    classes = {
        "console": "proto-step proto-step-console",
        "board": "proto-step proto-step-board",
        "cockpit": "proto-step proto-step-cockpit",
    }[variant]
    lines = [
        f'<details id="{step["id"]}" class="{classes}">',
        '<summary class="proto-step-summary">',
        f'  <span class="proto-step-badge">{step["step"]}</span>',
        '  <span class="proto-step-heading">',
        f"    <strong>{step['label']}</strong>",
        f"    <span>{step['focus']}</span>",
        "  </span>",
        '  <span class="proto-step-toggle" aria-hidden="true"></span>',
        "</summary>",
        '<div class="proto-panel proto-focus">',
        "  <p class=\"proto-kicker\">Checkpoint focus</p>",
        f"  <p>{step['focus']}</p>",
        "</div>",
        '<div class="proto-panel proto-why">',
        "  <p class=\"proto-kicker\">Why this matters</p>",
        f"  <p>{step['why']}</p>",
        "</div>",
    ]
    for check in step["checks"]:
        lines.extend(
            [
                '<div class="proto-command-card">',
                f'<p class="proto-command-label">{check["label"]}</p>',
                "",
                "```bash",
                check["command"],
                "```",
                "",
                f"**Healthy output:** {check['healthy']}",
                "",
                '<div class="proto-panel proto-mini-why">',
                "  <p class=\"proto-kicker\">Why this matters</p>",
                "",
            ]
        )
        for bullet in check["why"]:
            lines.append(f"- {bullet}")
        lines.extend(["</div>", ""])
        if check["example"]:
            lines.extend(
                [
                    "**Known-good output:**",
                    "",
                    "```text",
                    check["example"].rstrip(),
                    "```",
                    "",
                ]
            )
        lines.extend(["</div>", ""])
    lines.extend(["</details>", ""])
    return lines


def _render_custom_css(prototype: dict[str, str]) -> str:
    palettes = {
        "triage-console": {
            "bg": "#eef4f5",
            "panel": "#ffffff",
            "accent": "#175f6a",
            "accent_soft": "#dfeff1",
            "muted": "#587176",
            "ink": "#162125",
        },
        "mission-board": {
            "bg": "#f3eee4",
            "panel": "#fffaf2",
            "accent": "#8a4f1d",
            "accent_soft": "#f1dec4",
            "muted": "#685540",
            "ink": "#2e2418",
        },
        "support-cockpit": {
            "bg": "#0f1722",
            "panel": "#162230",
            "accent": "#65d8df",
            "accent_soft": "#163646",
            "muted": "#9ab3c7",
            "ink": "#edf5ff",
        },
    }
    palette = palettes[prototype["slug"]]
    return "\n".join(
        [
            ":root {",
            f"  --proto-bg: {palette['bg']};",
            f"  --proto-panel: {palette['panel']};",
            f"  --proto-accent: {palette['accent']};",
            f"  --proto-accent-soft: {palette['accent_soft']};",
            f"  --proto-muted: {palette['muted']};",
            f"  --proto-ink: {palette['ink']};",
            "}",
            "",
            "body {",
            "  background: radial-gradient(circle at top, rgba(255,255,255,0.12), transparent 28%), var(--proto-bg);",
            "}",
            "",
            ".content-panel {",
            "  border-radius: 1rem;",
            "  border: 1px solid color-mix(in srgb, var(--proto-accent) 16%, transparent);",
            "  background: color-mix(in srgb, var(--proto-panel) 95%, white 5%);",
            "}",
            "",
            ".sl-markdown-content {",
            "  color: var(--proto-ink);",
            "}",
            "",
            ".sl-markdown-content > :first-child {",
            "  margin-top: 0;",
            "}",
            "",
            ".proto-home-grid {",
            "  display: grid;",
            "  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));",
            "  gap: 1rem;",
            "  margin-top: 1rem;",
            "}",
            "",
            ".proto-home-card {",
            "  display: grid;",
            "  gap: 0.45rem;",
            "  padding: 1rem;",
            "  border-radius: 1rem;",
            "  text-decoration: none;",
            "  color: inherit;",
            "  background: linear-gradient(180deg, color-mix(in srgb, var(--proto-panel) 92%, white 8%) 0%, color-mix(in srgb, var(--proto-accent-soft) 32%, var(--proto-panel) 68%) 100%);",
            "  border: 1px solid color-mix(in srgb, var(--proto-accent) 18%, transparent);",
            "}",
            "",
            ".proto-home-card span, .proto-step-heading span, .proto-route-node span:last-child, .proto-board-tile span:last-child {",
            "  color: var(--proto-muted);",
            "}",
            "",
            ".proto-panel {",
            "  border-radius: 1rem;",
            "  border: 1px solid color-mix(in srgb, var(--proto-accent) 16%, transparent);",
            "  background: linear-gradient(180deg, color-mix(in srgb, var(--proto-accent-soft) 32%, var(--proto-panel) 68%) 0%, var(--proto-panel) 100%);",
            "  padding: 1rem 1.1rem;",
            "}",
            "",
            ".proto-kicker, .proto-route-step {",
            "  font-size: 0.76rem;",
            "  text-transform: uppercase;",
            "  letter-spacing: 0.04em;",
            "  font-weight: 700;",
            "  color: var(--proto-accent);",
            "}",
            "",
            ".proto-chip-row {",
            "  display: flex;",
            "  flex-wrap: wrap;",
            "  gap: 0.55rem;",
            "  margin-top: 0.75rem;",
            "}",
            "",
            ".proto-chip {",
            "  display: inline-flex;",
            "  align-items: center;",
            "  padding: 0.35rem 0.75rem;",
            "  border-radius: 999px;",
            "  background: color-mix(in srgb, var(--proto-panel) 90%, white 10%);",
            "  border: 1px solid color-mix(in srgb, var(--proto-accent) 18%, transparent);",
            "  color: var(--proto-muted);",
            "}",
            "",
            ".proto-route {",
            "  display: grid;",
            "  gap: 0.9rem;",
            "}",
            "",
            ".proto-route-node, .proto-board-tile, .proto-cockpit-jump {",
            "  display: grid;",
            "  gap: 0.25rem;",
            "  text-decoration: none;",
            "  color: inherit;",
            "  padding: 0.95rem 1rem;",
            "  border-radius: 1rem;",
            "  background: var(--proto-panel);",
            "  border: 1px solid color-mix(in srgb, var(--proto-accent) 18%, transparent);",
            "}",
            "",
            ".proto-step {",
            "  margin: 1rem 0;",
            "  border-radius: 1rem;",
            "  border: 1px solid color-mix(in srgb, var(--proto-accent) 18%, transparent);",
            "  background: var(--proto-panel);",
            "  padding: 0.2rem 1rem 1rem;",
            "}",
            "",
            ".proto-step-summary {",
            "  display: flex;",
            "  align-items: flex-start;",
            "  gap: 0.85rem;",
            "  list-style: none;",
            "  cursor: pointer;",
            "  padding: 0.85rem 0 0.55rem;",
            "}",
            "",
            ".proto-step-summary::-webkit-details-marker, .proto-step-summary::marker {",
            "  display: none;",
            "}",
            "",
            ".proto-step-badge {",
            "  display: inline-flex;",
            "  align-items: center;",
            "  justify-content: center;",
            "  min-width: 4.7rem;",
            "  padding: 0.32rem 0.8rem;",
            "  border-radius: 999px;",
            "  background: var(--proto-accent);",
            "  color: white;",
            "  font-size: 0.84rem;",
            "  font-weight: 700;",
            "}",
            "",
            ".proto-step-heading {",
            "  display: grid;",
            "  gap: 0.2rem;",
            "  flex: 1 1 auto;",
            "}",
            "",
            ".proto-step-toggle {",
            "  margin-left: auto;",
            "  color: var(--proto-accent);",
            "  font-weight: 700;",
            "  white-space: nowrap;",
            "}",
            "",
            ".proto-step-toggle::before {",
            "  content: 'Open';",
            "}",
            "",
            ".proto-step[open] .proto-step-toggle::before {",
            "  content: 'Close';",
            "}",
            "",
            ".proto-focus, .proto-why, .proto-mini-why {",
            "  margin: 0.8rem 0 1rem;",
            "}",
            "",
            ".proto-command-card {",
            "  margin: 1rem 0 1.25rem;",
            "}",
            "",
            ".proto-command-label {",
            "  margin: 0 0 0.55rem;",
            "  font-weight: 700;",
            "}",
            "",
            ".proto-panel p:last-child {",
            "  margin-bottom: 0;",
            "}",
            "",
            ".proto-mini-why ul {",
            "  margin: 0.45rem 0 0;",
            "}",
            "",
            ".proto-console-shell {",
            "  display: grid;",
            "  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);",
            "  gap: 1.1rem;",
            "}",
            "",
            ".proto-console-rail {",
            "  display: grid;",
            "  gap: 1rem;",
            "  align-content: start;",
            "  position: sticky;",
            "  top: 1rem;",
            "}",
            "",
            ".proto-console-main h2, .proto-cockpit-main h2 {",
            "  margin-top: 0;",
            "}",
            "",
            ".proto-board-hero {",
            "  display: grid;",
            "  gap: 1rem;",
            "}",
            "",
            ".proto-board-map {",
            "  display: grid;",
            "  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));",
            "  gap: 0.9rem;",
            "}",
            "",
            ".proto-board-brief h2 {",
            "  margin: 0.2rem 0 0.8rem;",
            "}",
            "",
            ".proto-cockpit-shell {",
            "  display: grid;",
            "  gap: 1rem;",
            "}",
            "",
            ".proto-cockpit-topbar {",
            "  display: grid;",
            "  grid-template-columns: repeat(2, minmax(0, 1fr));",
            "  gap: 1rem;",
            "}",
            "",
            ".proto-cockpit-grid {",
            "  display: grid;",
            "  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);",
            "  gap: 1rem;",
            "}",
            "",
            ".proto-cockpit-nav {",
            "  align-self: start;",
            "  position: sticky;",
            "  top: 1rem;",
            "}",
            "",
            ".proto-cockpit-jumps {",
            "  display: grid;",
            "  gap: 0.7rem;",
            "  margin-top: 0.8rem;",
            "}",
            "",
            ".proto-route.proto-console-route {",
            "  margin-top: 0.8rem;",
            "}",
            "",
            ".proto-step-console {",
            "  box-shadow: 0 18px 32px color-mix(in srgb, var(--proto-accent) 10%, transparent);",
            "}",
            "",
            ".proto-step-board {",
            "  border-width: 2px;",
            "}",
            "",
            ".proto-step-cockpit {",
            "  background: linear-gradient(180deg, color-mix(in srgb, var(--proto-accent-soft) 22%, var(--proto-panel) 78%) 0%, var(--proto-panel) 100%);",
            "}",
            "",
            "@media (max-width: 60rem) {",
            "  .proto-console-shell, .proto-cockpit-grid, .proto-cockpit-topbar {",
            "    grid-template-columns: 1fr;",
            "  }",
            "  .proto-console-rail, .proto-cockpit-nav {",
            "    position: static;",
            "  }",
            "}",
            "",
            "@media (max-width: 50rem) {",
            "  .proto-step-summary {",
            "    flex-wrap: wrap;",
            "  }",
            "  .proto-step-toggle {",
            "    margin-left: 5.4rem;",
            "  }",
            "}",
            "",
        ]
    ) + "\n"
