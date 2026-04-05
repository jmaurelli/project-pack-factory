from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

DEFAULT_REVIEW_SHELL_ARTIFACT_ROOT = Path("dist/candidates/adf-starlight-review-shell")


def generate_starlight_site(
    *,
    project_root: Path,
    artifact_root: str | Path | None = None,
    site_root: str | Path | None = None,
) -> dict[str, Any]:
    output_root = _resolve_output_root(
        project_root=project_root,
        artifact_root=artifact_root,
        site_root=site_root,
    )
    if output_root.exists():
        shutil.rmtree(output_root)

    docs_root = output_root / "src" / "content" / "docs"
    docs_root.mkdir(parents=True, exist_ok=True)

    files_to_write = {
        output_root / "package.json": _render_package_json(),
        output_root / "astro.config.mjs": _render_astro_config(),
        output_root / "tsconfig.json": _render_tsconfig(),
        output_root / "src" / "content.config.ts": _render_content_config(),
        output_root / "src" / "custom.css": _render_custom_css(),
        docs_root / "index.md": _render_overview_page(),
        docs_root / "playbooks" / "index.md": _render_playbooks_index_page(),
        docs_root / "playbooks" / "service-state.md": _render_service_state_page(),
        docs_root / "playbooks" / "logs.md": _render_logs_page(),
        docs_root / "cookbooks" / "index.md": _render_cookbooks_index_page(),
        docs_root / "cookbooks" / "core-service-groups-by-node-role.md": _render_core_service_groups_page(),
    }
    for path, content in files_to_write.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    generated_files = [str(path.relative_to(project_root)) for path in sorted(files_to_write)]
    return {
        "status": "pass",
        "artifact_root": str(output_root.relative_to(project_root)),
        "generated_files": generated_files,
        "summary": {
            "page_count": 6,
            "playbook_count": 2,
            "cookbook_count": 1,
            "top_level_routes": [
                "/",
                "/playbooks/",
                "/playbooks/service-state/",
                "/playbooks/logs/",
                "/cookbooks/",
                "/cookbooks/core-service-groups-by-node-role/",
            ],
        },
    }


def _resolve_output_root(
    *,
    project_root: Path,
    artifact_root: str | Path | None,
    site_root: str | Path | None,
) -> Path:
    if site_root is not None:
        return (project_root / Path(site_root)).resolve()
    root = Path(artifact_root) if artifact_root is not None else DEFAULT_REVIEW_SHELL_ARTIFACT_ROOT
    return (project_root / root / "starlight-site").resolve()


def _render_package_json() -> str:
    payload = {
        "name": "adf-successor-starlight-review-shell",
        "private": True,
        "type": "module",
        "scripts": {
            "dev": "astro dev --host 0.0.0.0 --port 18083",
            "build": "astro build",
            "preview": "astro preview --host 0.0.0.0 --port 18083",
        },
        "dependencies": {
            "@astrojs/starlight": "0.38.2",
            "astro": "6.1.3",
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def _render_astro_config() -> str:
    sidebar = [
        {
            "label": "Overview",
            "items": [{"label": "AlgoSec Diagnostic Framework", "slug": "index"}],
        },
        {
            "label": "Playbooks",
            "items": [
                {"label": "Index", "slug": "playbooks"},
                {"label": "Service State", "slug": "playbooks/service-state"},
                {"label": "Logs", "slug": "playbooks/logs"},
            ],
        },
        {
            "label": "Cookbooks",
            "items": [
                {"label": "Index", "slug": "cookbooks"},
                {
                    "label": "Core Service Groups by Node Role",
                    "slug": "cookbooks/core-service-groups-by-node-role",
                },
            ],
        },
    ]
    return (
        "import { defineConfig } from 'astro/config';\n"
        "import starlight from '@astrojs/starlight';\n\n"
        "export default defineConfig({\n"
        "  integrations: [\n"
        "    starlight({\n"
        "      title: 'AlgoSec Diagnostic Framework',\n"
        "      description: 'Diagnostic playbooks and cookbooks for ASMS support work.',\n"
        "      disable404Route: true,\n"
        "      tableOfContents: false,\n"
        "      customCss: ['./src/custom.css'],\n"
        f"      sidebar: {json.dumps(sidebar, indent=8)},\n"
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


def _render_custom_css() -> str:
    return """
:root {
  --sl-color-accent-low: #d8ece8;
  --sl-color-accent: #0f6c69;
  --sl-color-accent-high: #073d3b;
  --sl-color-text: #162326;
  --sl-color-text-accent: #0b5f5c;
  --sl-color-bg: #f7f8f6;
  --sl-color-bg-nav: #ffffff;
  --sl-color-bg-sidebar: #f2f4f2;
  --sl-color-hairline-light: #d8dfdc;
  --sl-color-hairline: #c7d0cc;
  --sl-color-black: #10191c;
}

html {
  scroll-behavior: smooth;
}

body {
  letter-spacing: 0.01em;
}

h1,
h2,
h3 {
  letter-spacing: -0.01em;
}

h2 {
  margin-top: 2rem;
  padding-top: 0.25rem;
  border-top: 1px solid rgba(199, 208, 204, 0.8);
}

pre {
  border-radius: 0.9rem;
}

table {
  font-size: 0.96rem;
}
""".strip() + "\n"


def _render_overview_page() -> str:
    return """---
title: AlgoSec Diagnostic Framework
description: Diagnostic playbooks and cookbooks for ASMS support work.
---

# AlgoSec Diagnostic Framework

Diagnostic playbooks and cookbooks for ASMS support work.

## Playbooks

- [Service State](/playbooks/service-state/)
- [Logs](/playbooks/logs/)

## Cookbooks

- [Core Service Groups by Node Role](/cookbooks/core-service-groups-by-node-role/)

## Current implementation slice

- This first shell intentionally publishes only the reviewed routes.
- Additional playbook and cookbook pages stay out until their copy and structure are reviewed.
"""


def _render_playbooks_index_page() -> str:
    return """---
title: Playbooks
description: Frontline triage paths for ASMS support work.
---

- [Service State](/playbooks/service-state/)
- [Logs](/playbooks/logs/)

## Next reviewed paths

- `Host Health`
- `Data Collection and Processing`
- `Distributed Node Role`
"""


def _render_service_state_page() -> str:
    return """---
title: Service State
description: First-pass CLI triage for core ms-* service state.
---

## Steps

1. Open the CLI service-status dashboard.
2. Review only the core `ms-*` services first.
3. Put the current state in one of these buckets:
   - one core service down
   - multiple core services down
   - one or more core services not responding
   - core services up
4. If any service is down or not responding, open the first log for that named service or service group.
5. If core services are up, leave this path and continue in [Logs](/playbooks/logs/).
6. Do not stay on this page after the bucket is clear. This path is only the front-door filter.

```text
Example dashboard
ms-auth             up
ms-collector        up
ms-metro            up
ms-reporting        down
```

## Branch to

- `one core service down` -> [Logs / Single core service down](/playbooks/logs/#single-core-service-down)
- `multiple core services down` -> if host pressure is already visible, `Host Health`; otherwise [Logs / Multiple core services down](/playbooks/logs/#multiple-core-services-down)
- `one or more core services not responding` -> [Logs / Service not responding](/playbooks/logs/#service-not-responding)
- `core services up` -> [Logs / Core services up](/playbooks/logs/#core-services-up)

## Related cookbook foundations

- [Core Service Groups by Node Role](/cookbooks/core-service-groups-by-node-role/)
- `Log Entry Points` (next reviewed page)
- `Distributed Role Foundations` (next reviewed page)
"""


def _render_logs_page() -> str:
    return """---
title: Logs
description: First-log triage after service state stops being enough.
---

## Steps

1. Open the first relevant log for the current service, service group, or node role.
2. Stay on the recent failure window first.
3. Match the current case to one of the reviewed sections below.
4. If none of the sections fit cleanly, move back one level and choose a different playbook path.

## Branch to

- `host pressure or broader appliance instability is already visible` -> `Host Health`
- `data collection, stale results, or delayed processing is the stronger read` -> `Data Collection and Processing`
- `node-role context is the stronger read` -> `Distributed Node Role`

## Single core service down

### Steps

1. Open the first log for the failed service.
2. Stay on the most recent failure window first.
3. Separate startup failure, repeated runtime failure, and dependency-looking failure.

```bash
journalctl -u ms-reporting -n 80 --no-pager
```

```text
2026-04-05 09:11:42 ERROR startup failed
2026-04-05 09:11:42 ERROR could not open expected runtime file
```

### Branch to

- `host pressure or filesystem trouble is visible` -> `Host Health`
- `the log pattern stays local and bounded` -> remain on `Logs`
- `node-role context is stronger` -> `Distributed Node Role`

## Multiple core services down

### Steps

1. Check whether host pressure, disk pressure, inode pressure, or broader appliance instability is already visible.
2. If yes, move to `Host Health`.
3. If no, open the first common or high-signal logs across the affected service group.

```bash
journalctl -u ms-metro -u ms-reporting -n 120 --no-pager
```

### Branch to

- `host pressure or broader appliance instability is visible` -> `Host Health`
- `shared log clues are stronger than host clues` -> remain on `Logs`

## Service not responding

### Steps

1. Open the first log for the not-responding service or service group.
2. Check whether the state looks stalled, timing out, or flapping.
3. Keep the first pass local before widening into deeper ownership theory.

```bash
journalctl -u ms-metro -n 120 --no-pager | tail -n 40
```

```text
2026-04-05 09:24:19 WARN request timed out after 30000ms
2026-04-05 09:24:49 WARN request timed out after 30000ms
```

### Branch to

- `host pressure is visible` -> `Host Health`
- `node-role context is stronger` -> `Distributed Node Role`
- `the log pattern stays local and bounded` -> remain on `Logs`

## Core services up

### Steps

1. Open the first logs for the path that still matches the observed issue.
2. Do not force a service-state explanation when the dashboard is healthy.
3. Use the first log clues to decide whether this is still local runtime behavior, data collection and processing, or a node-role issue.

```bash
tail -n 80 /var/log/httpd/error_log
```

```text
[error] proxy timeout contacting local upstream
[error] request returned 503 for /afa/php/home.php
```

### Branch to

- `data collection, stale results, or delayed processing is stronger` -> `Data Collection and Processing`
- `node-role context is stronger` -> `Distributed Node Role`
- `the issue stays local and log-visible` -> remain on `Logs`

## Related cookbook foundations

- `Log Entry Points` (next reviewed page)
- [Core Service Groups by Node Role](/cookbooks/core-service-groups-by-node-role/)
- `Distributed Role Foundations` (next reviewed page)
"""


def _render_cookbooks_index_page() -> str:
    return """---
title: Cookbooks
description: Runtime foundations behind the playbook paths.
---

- [Core Service Groups by Node Role](/cookbooks/core-service-groups-by-node-role/)

## Next reviewed foundations

- `Log Entry Points`
- `Data Flow Foundations`
- `Distributed Role Foundations`
"""


def _render_core_service_groups_page() -> str:
    return """---
title: Core Service Groups by Node Role
description: Runtime foundation for CM, RA, LDU, and DR role differences.
---

Use this page to confirm which node role you are on before you interpret service state or first logs. CM, RA, LDU, and DR do not expose the same first-response surface.

## Role matrix

| Role | Service State surface | Open these logs first | First read | Common mistake |
| --- | --- | --- | --- | --- |
| CM | broadest local `ms-*` surface and web edge | `httpd`, primary `ms-*` journals | best first stop for broad local issues | assuming CM health proves peer health |
| RA | narrower role-local `ms-*` surface | role-local `ms-*` journals | read the local runtime first, then widen | reading CM expectations into RA |
| LDU | processing-heavy and utility-heavy surface | ingestion, processing, and role-local journals | expect a different service mix than CM | treating CM-only services as missing on purpose |
| DR | standby-oriented or colder posture | role-local journals around DR services | quiet or reduced activity may be normal | treating standby quietness as failure by default |

## Validated behavior

- CM and non-CM nodes do not expose the same first-response service surface.
- First-log priorities change by node role.
- Role differences should be treated as runtime facts, not as drift by default.

## Observed practice

- Service State plus node role is usually enough to narrow the first log choice quickly.
- Engineers get faster traction when they decide the node role first instead of comparing every node to CM.

## Operator theory

- Some peer or cross-node failures may first appear as local ambiguity on a healthy-looking node.

## Not proven

- Full DR service expectations across every standby posture are still incomplete.
- Some role-specific caveats still need more lab-backed repetition before they should move into `Validated behavior`.

## Related playbooks

- [Service State](/playbooks/service-state/)
- [Logs](/playbooks/logs/)
"""
