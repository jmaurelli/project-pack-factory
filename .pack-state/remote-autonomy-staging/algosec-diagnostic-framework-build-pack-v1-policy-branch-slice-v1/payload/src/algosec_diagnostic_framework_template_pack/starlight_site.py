from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .runtime_baseline import (
    DEFAULT_ARTIFACT_ROOT,
    SUPPORT_BASELINE_NAME,
    derive_command_linux_note,
    derive_known_working_example,
)

PRIMARY_PLAYBOOK_ID = "ui-and-proxy"
STARLIGHT_SITE_PNPM_LOCK = (
    Path(__file__).resolve().parent / "assets" / "starlight-site-pnpm-lock.yaml"
)
CANONICAL_PLAYBOOK_TEMPLATE = {
    "template_id": "field-manual",
    "label": "Field Manual",
    "summary": "ADF's canonical playbook shell: a chapter-style runbook with editorial pacing, wider reading flow, and calmer operator guidance.",
}
CANONICAL_PLAYBOOK_TEMPLATE_SLUG = "canonical-playbook-template"
FALLBACK_CANONICAL_PLAYBOOK = {
    "playbook_id": PRIMARY_PLAYBOOK_ID,
    "label": "ASMS UI is down",
    "symptom_focus": "The suite login shell or UI is not doing useful work.",
    "decision_rule": "Work from host to edge to auth to app. Stop at the first checkpoint that cannot do useful work.",
    "likely_failing_services": ["httpd", "keycloak", "ms-metro"],
    "dependency_path": [
        {
            "step_id": "ui-and-proxy-step-1",
            "step_label": "Step 1",
            "label": "Host can support useful work",
            "details": "Confirm the box itself is healthy before blaming higher services.",
        },
        {
            "step_id": "ui-and-proxy-step-2",
            "step_label": "Step 2",
            "label": "Apache/HTTPD serving the UI",
            "details": "Validate the edge and the first real HTTP surface.",
        },
        {
            "step_id": "ui-and-proxy-step-3",
            "step_label": "Step 3",
            "label": "Auth branch can do useful work",
            "details": "Check whether the login and identity hop can complete real work.",
        },
        {
            "step_id": "ui-and-proxy-step-4",
            "step_label": "Step 4",
            "label": "App branch can do useful work",
            "details": "Validate the first useful-work application hop behind the shell.",
        },
        {
            "step_id": "ui-and-proxy-step-5",
            "step_label": "Step 5",
            "label": "Useful work stops here",
            "details": "Use bounded evidence to name the first real stop point.",
        },
    ],
    "steps": [
        {
            "step_id": "ui-and-proxy-step-1",
            "step_label": "Step 1",
            "action": "Confirm the host is healthy before you chase Apache, auth, or app signals.",
            "why_this_matters": "If the host cannot support useful work, every higher branch is downstream noise.",
            "recommended_commands": [
                {
                    "label": "Check host pressure",
                    "command": "uptime && free -m && df -h /",
                    "expected_signal": "Load is reasonable, memory is available, and the root filesystem is not full.",
                    "healthy_markers": ["load average", "Mem:", "Filesystem"],
                    "interpretation": "If the host is clearly under pressure, stop here and stabilize the box first.",
                    "example_output": "load average: 0.32, 0.41, 0.55\nMem: 16000 6200 4200 120 5600 9300\n/dev/sda1 80G 31G 47G 40% /",
                }
            ],
            "if_pass": "Move to the HTTP edge and prove Apache can serve useful work.",
            "if_fail": "Treat host pressure as the first stop point.",
        },
        {
            "step_id": "ui-and-proxy-step-2",
            "step_label": "Step 2",
            "action": "Prove Apache is answering and routing the suite shell correctly.",
            "why_this_matters": "If the edge cannot serve the shell, deeper auth and app checks are premature.",
            "recommended_commands": [
                {
                    "label": "Check Apache service and shell response",
                    "command": "systemctl is-active httpd && curl -k -I https://127.0.0.1/algosec/suite/login",
                    "expected_signal": "Apache is active and the suite login returns an expected HTTP response.",
                    "healthy_markers": ["active", "HTTP/1.1 302", "Location:"],
                    "interpretation": "If Apache is down or the shell route is missing, stop at the edge.",
                    "example_output": "active\nHTTP/1.1 302 Found\nLocation: https://127.0.0.1/algosec-ui/login",
                }
            ],
            "if_pass": "Continue into the auth branch.",
            "if_fail": "Treat Apache or the edge route as the first stop point.",
        },
        {
            "step_id": "ui-and-proxy-step-3",
            "step_label": "Step 3",
            "action": "Check whether the auth branch can complete useful work instead of just redirecting.",
            "why_this_matters": "A healthy shell with a broken auth hop still leaves the operator blocked.",
            "recommended_commands": [
                {
                    "label": "Check Keycloak reachability",
                    "command": "systemctl is-active keycloak && curl -k -I https://127.0.0.1/auth/",
                    "expected_signal": "Keycloak is active and the auth route responds instead of timing out.",
                    "healthy_markers": ["active", "HTTP/1.1"],
                    "interpretation": "If auth cannot answer useful requests, stop on the auth branch.",
                    "example_output": "active\nHTTP/1.1 200 OK",
                }
            ],
            "if_pass": "Move to the first useful-work app hop.",
            "if_fail": "Treat auth as the first stop point.",
        },
        {
            "step_id": "ui-and-proxy-step-4",
            "step_label": "Step 4",
            "action": "Validate the first app-side dependency that should answer real UI work.",
            "why_this_matters": "This separates a generic shell problem from an app-branch failure.",
            "recommended_commands": [
                {
                    "label": "Check Metro health",
                    "command": "systemctl is-active ms-metro && curl -sS http://127.0.0.1:8080/afa/api/v1/config | head",
                    "expected_signal": "Metro is active and returns application config data instead of failing.",
                    "healthy_markers": ["active", "config"],
                    "interpretation": "If Metro cannot answer, the app branch is the first stop point.",
                    "example_output": "active\n{\"configVersion\":\"ok\"}",
                }
            ],
            "if_pass": "Use one bounded reproduction minute to name the actual stop point.",
            "if_fail": "Stop here and treat the local app path as the current failure point.",
        },
        {
            "step_id": "ui-and-proxy-step-5",
            "step_label": "Step 5",
            "action": "If useful work still stops here, use Apache, Keycloak, and Metro clues to find the first clear stop point.",
            "why_this_matters": "Only move into heavier log correlation after the host, edge, auth, and app branches have all been checked.",
            "recommended_commands": [
                {
                    "label": "Correlate one reproduced minute across the edge and app services",
                    "command": "journalctl -u httpd -u keycloak -u ms-metro --since '5 minutes ago' --no-pager | tail -n 120",
                    "expected_signal": "The same bounded minute shows the first branch that stops doing useful work.",
                    "healthy_markers": ["httpd", "keycloak", "ms-metro"],
                    "interpretation": "If only one branch degrades in the same minute, that branch owns the stop point.",
                    "example_output": "Mar 27 15:00:11 httpd[...]: GET /algosec/suite/login 302\nMar 27 15:00:12 keycloak[...]: login flow ok\nMar 27 15:00:13 ms-metro[...]: config fetch ok",
                }
            ],
            "if_pass": "Record the bounded proof and move to the next symptom slice.",
            "if_fail": "Name the first failing branch and stop the walk there.",
        },
    ],
}
FALLBACK_CANONICAL_SYMPTOMS = [
    {"symptom_label": "Suite login redirects but the operator still cannot do useful work."},
    {"symptom_label": "UI shell appears, but the first app action stalls immediately."},
    {"symptom_label": "Support needs one bounded route to prove where useful work stops."},
]


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
    template_lab_root = docs_root / "template-lab"
    canonical_template_path = docs_root / f"{CANONICAL_PLAYBOOK_TEMPLATE_SLUG}.md"
    for stale_path in (
        output_root / ".astro",
        output_root / "dist",
        output_root / "node_modules",
        output_root / "package-lock.json",
        output_root / "pnpm-lock.yaml",
    ):
        if stale_path.is_dir():
            shutil.rmtree(stale_path)
        elif stale_path.exists():
            stale_path.unlink()
    docs_root.mkdir(parents=True, exist_ok=True)
    stale_index_mdx = docs_root / "index.mdx"
    if stale_index_mdx.exists():
        stale_index_mdx.unlink()
    stale_not_found = docs_root / "404.md"
    if stale_not_found.exists():
        stale_not_found.unlink()
    if playbooks_root.exists():
        shutil.rmtree(playbooks_root)
    if template_lab_root.exists():
        shutil.rmtree(template_lab_root)
    for stale_doc in docs_root.glob("*.md"):
        if stale_doc.name not in {"index.md"}:
            stale_doc.unlink()

    symptom_lookup = _symptoms_by_playbook(support_baseline)
    primary_playbook: dict[str, Any] | None = None
    for playbook in support_baseline.get("decision_playbooks", []):
        if playbook.get("playbook_id") == PRIMARY_PLAYBOOK_ID:
            primary_playbook = playbook

    if primary_playbook is None:
        decision_playbooks = support_baseline.get("decision_playbooks", [])
        primary_playbook = decision_playbooks[0] if decision_playbooks else FALLBACK_CANONICAL_PLAYBOOK

    canonical_template_entry: dict[str, str | int] | None = None
    if primary_playbook is not None:
        canonical_template_path.write_text(
            _render_canonical_playbook_template_markdown(
                playbook=primary_playbook,
                symptom_entries=symptom_lookup.get(primary_playbook["playbook_id"], []) or FALLBACK_CANONICAL_SYMPTOMS,
            ),
            encoding="utf-8",
        )
        canonical_template_entry = {
            "label": str(CANONICAL_PLAYBOOK_TEMPLATE["label"]),
            "slug": CANONICAL_PLAYBOOK_TEMPLATE_SLUG,
            "relative_path": f"src/content/docs/{CANONICAL_PLAYBOOK_TEMPLATE_SLUG}.md",
            "order": 1,
        }

    (docs_root / "index.md").write_text(
        _render_index_markdown(support_baseline, canonical_template_entry),
        encoding="utf-8",
    )
    (output_root / "package.json").write_text(_render_package_json(), encoding="utf-8")
    (output_root / "pnpm-lock.yaml").write_text(STARLIGHT_SITE_PNPM_LOCK.read_text(encoding="utf-8"), encoding="utf-8")
    (output_root / "astro.config.mjs").write_text(
        _render_astro_config(canonical_template_entry),
        encoding="utf-8",
    )
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
        str((docs_root / "index.md").relative_to(project_root)),
        str((output_root / "pnpm-lock.yaml").relative_to(project_root)),
    ]
    if canonical_template_entry is not None:
        generated_files.append(str(canonical_template_path.relative_to(project_root)))

    return {
        "status": "pass",
        "artifact_root": str(output_root.relative_to(project_root)),
        "generated_files": generated_files,
        "summary": {
            "playbook_count": 0,
            "canonical_template": CANONICAL_PLAYBOOK_TEMPLATE["template_id"],
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
        "packageManager": "pnpm@10.33.0",
        "dependencies": {
            "astro": "5.12.8",
            "@astrojs/starlight": "0.36.0",
        },
    }
    return json.dumps(payload, indent=2) + "\n"


def _render_astro_config(canonical_template_entry: dict[str, str | int] | None) -> str:
    canonical_sidebar = (
        "{\n        label: 'Canonical Template',\n        items: [\n          { label: "
        + json.dumps(str(canonical_template_entry["label"]))
        + ", slug: "
        + json.dumps(str(canonical_template_entry["slug"]))
        + " }\n        ],\n      }"
        if canonical_template_entry
        else "{\n        label: 'Canonical Template',\n        items: [],\n      }"
    )
    return (
        "import { defineConfig } from 'astro/config';\n"
        "import starlight from '@astrojs/starlight';\n\n"
        "export default defineConfig({\n"
        "  integrations: [\n"
        "    starlight({\n"
        "      title: 'AlgoSec Diagnostic Framework',\n"
        "      description: 'Target-backed diagnostic playbooks for support engineers.',\n"
        "      disable404Route: true,\n"
        "      customCss: ['./src/custom.css'],\n"
        "      tableOfContents: false,\n"
        "      sidebar: [\n"
        "        {\n"
        "          label: 'Start Here',\n"
        "          items: [{ label: 'Overview', slug: 'index' }],\n"
        "        },\n"
        f"        {canonical_sidebar}\n"
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
        "import { docsSchema } from '@astrojs/starlight/schema';\n\n"
        "export const collections = {\n"
        "  docs: defineCollection({ schema: docsSchema() }),\n"
        "};\n"
    )


def _render_index_markdown(
    support_baseline: dict[str, Any],
    canonical_template_entry: dict[str, str | int] | None,
) -> str:
    observed = support_baseline.get("observed", {})
    service_summary = observed.get("service_summary", {})
    runtime_identity = observed.get("runtime_identity", {})
    os_release = runtime_identity.get("os_release", {})
    symptoms = support_baseline.get("symptom_lookup", [])
    first_response_steps = support_baseline.get("first_response_steps", [])
    canonical_target = f'/{canonical_template_entry["slug"]}/' if canonical_template_entry else "/"

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
        "Field Manual is now the canonical ADF playbook template. The old published playbooks have been intentionally cleared so we can rebuild the catalog from scratch on one consistent shell.",
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
            "      <li>ADF now has one canonical playbook shell instead of competing page grammars.</li>",
            "      <li>The old playbook set was cleared from publication on purpose so rebuild work starts from one template baseline.</li>",
            "      <li>The JSON baseline and pack state remain canonical. This site is still a render layer over that evidence.</li>",
            "    </ul>",
            "  </div>",
            "</div>",
            "",
            "## Canonical template",
            "",
            '<div class="adf-home-card-grid">',
            f'<a class="adf-home-card" href="{canonical_target}">',
            '  <p class="adf-panel-label">Field Manual</p>',
            '  <strong>Canonical ADF playbook shell</strong>',
            '  <span>This is now the only approved playbook template. Existing playbooks were intentionally dropped from publication and will be rebuilt on top of this shell.</span>',
            '  <span class="adf-home-card-list">Open the canonical template and use it as the rebuild reference.</span>',
            "</a>",
            "</div>",
            "",
            "## Rebuild status",
            "",
            '<div class="adf-home-grid">',
            '  <div class="adf-panel">',
            '    <p class="adf-panel-label">Published catalog</p>',
            "    <p>Zero playbooks are currently published on purpose. This prevents the older mixed shells from pretending to be canonical while we rebuild.</p>",
            "  </div>",
            '  <div class="adf-panel">',
            '    <p class="adf-panel-label">Next build rule</p>',
            "    <p>Every new playbook should be authored against the Field Manual shell first. We can add content families later, but not another competing page grammar.</p>",
            "  </div>",
            "</div>",
            "",
            "## Symptom lookup",
            "",
            '<div class="adf-symptom-grid">',
        ]
    )
    for symptom in symptoms:
        lines.extend(
            [
                '<div class="adf-symptom-card">',
                f'  <strong>{symptom["symptom_label"]}</strong>',
                f'  <p>{symptom["first_action"]}</p>',
                f'  <span>Rebuild later under {symptom["suggested_domain_label"]}.</span>',
                "</div>",
            ]
        )
    lines.extend(["</div>", "</div>", ""])
    return "\n".join(lines) + "\n"


def _render_canonical_playbook_template_markdown(
    *,
    playbook: dict[str, Any],
    symptom_entries: list[dict[str, str]],
) -> str:
    title_value = json.dumps(f"Canonical Playbook Template: {CANONICAL_PLAYBOOK_TEMPLATE['label']}")
    description_value = json.dumps(CANONICAL_PLAYBOOK_TEMPLATE["summary"])
    lines = [
        "---",
        f"title: {title_value}",
        f"description: {description_value}",
        "sidebar:",
        f"  label: {json.dumps(CANONICAL_PLAYBOOK_TEMPLATE['label'])}",
        "  order: 1",
        "---",
        "",
        CANONICAL_PLAYBOOK_TEMPLATE["summary"],
        "",
        '<div class="adf-template-intro adf-panel">',
        '  <p class="adf-panel-label">Canonical template</p>',
        f"  <h2>{CANONICAL_PLAYBOOK_TEMPLATE['label']}</h2>",
        "  <p>This is now the only approved ADF playbook shell. The older playbook set and the earlier template experiments were intentionally removed from publication.</p>",
        "  <p><strong>Rebuild rule:</strong> New ADF playbooks should be authored against this shell first and only then published.</p>",
        "</div>",
        "",
        _render_template_field_manual(playbook=playbook, symptom_entries=symptom_entries).rstrip(),
        "",
    ]
    return "\n".join(lines) + "\n"


def _render_template_lab_index_markdown(template_nav_entries: list[dict[str, str | int]]) -> str:
    lines = [
        "---",
        "title: Playbook Template Lab",
        "description: Review three new ADF-only playbook template candidates before choosing the next canonical shell.",
        "sidebar:",
        "  label: Template Lab",
        "  order: 1",
        "---",
        "",
        "# Playbook Template Lab",
        "",
        "These are new ADF-only template candidates. They all use the same ASMS UI sample content so the layout and navigation differences are easier to compare.",
        "",
        '<div class="adf-template-index-grid">',
    ]
    for template in TEMPLATE_PREVIEW_DEFS:
        lines.extend(
            [
                f'<a class="adf-template-card" href="/template-lab/{template["template_id"]}/">',
                f'  <p class="adf-panel-label">{template["label"]}</p>',
                f'  <strong>{template["summary"]}</strong>',
                f'  <span>{template["why_it_differs"]}</span>',
                "</a>",
            ]
        )
    lines.extend(["</div>", ""])
    return "\n".join(lines) + "\n"


def _render_template_preview_markdown(
    *,
    template: dict[str, str],
    playbook: dict[str, Any],
    symptom_entries: list[dict[str, str]],
    order: int,
) -> str:
    title_value = json.dumps(f"Template Preview: {template['label']}")
    description_value = json.dumps(template["summary"])
    sidebar_label_value = json.dumps(template["label"])
    rendered_body = _render_template_preview_body(
        template_id=template["template_id"],
        playbook=playbook,
        symptom_entries=symptom_entries,
    )
    lines = [
        "---",
        f"title: {title_value}",
        f"description: {description_value}",
        "sidebar:",
        f"  label: {sidebar_label_value}",
        f"  order: {order}",
        "---",
        "",
        f"{template['summary']}",
        "",
        '<div class="adf-template-intro adf-panel">',
        "  <p class=\"adf-panel-label\">Candidate template</p>",
        f"  <h2>{template['label']}</h2>",
        f"  <p>{template['why_it_differs']}</p>",
        "  <p><strong>Preview rule:</strong> This page keeps the current ASMS UI sample content and changes only the shell, navigation, and visual system.</p>",
        "</div>",
        "",
        rendered_body.rstrip(),
        "",
    ]
    return "\n".join(lines) + "\n"


def _render_template_preview_body(
    *,
    template_id: str,
    playbook: dict[str, Any],
    symptom_entries: list[dict[str, str]],
) -> str:
    if template_id == "atlas-map":
        return _render_template_atlas_map(playbook=playbook, symptom_entries=symptom_entries)
    if template_id == "incident-console":
        return _render_template_incident_console(playbook=playbook, symptom_entries=symptom_entries)
    return _render_template_field_manual(playbook=playbook, symptom_entries=symptom_entries)


def _render_template_atlas_map(
    *,
    playbook: dict[str, Any],
    symptom_entries: list[dict[str, str]],
) -> str:
    dependency_path = playbook.get("dependency_path", [])
    dependency_by_step = {item["step_id"]: item for item in dependency_path}
    command_total = sum(len(step.get("recommended_commands", [])) for step in playbook.get("steps", []))
    lines = [
        '<div class="adf-preview-shell adf-preview-atlas-map">',
        '  <section class="adf-preview-atlas-head adf-panel">',
        '    <div>',
        '      <p class="adf-panel-label">Atlas Map</p>',
        f"      <h2>{playbook['label']}</h2>",
        f"      <p>{playbook.get('decision_rule', playbook['symptom_focus'])}</p>",
        "    </div>",
        '    <div class="adf-preview-atlas-metrics">',
        f'      <span><strong>{len(dependency_path)}</strong> nodes</span>',
        f'      <span><strong>{max(len(symptom_entries), 1)}</strong> symptom fits</span>',
        f'      <span><strong>{command_total}</strong> proof commands</span>',
        "    </div>",
        "  </section>",
        '  <section class="adf-preview-atlas-canvas adf-panel">',
        '    <div class="adf-preview-atlas-kicker">',
        '      <p class="adf-panel-label">Dependency canvas</p>',
        '      <p>The route map is the main artifact here. Each node is a checkpoint in the useful-work path, and the step chapters live underneath as route drill-downs.</p>',
        "    </div>",
        '    <ol class="adf-preview-atlas-node-grid">',
    ]
    for index, item in enumerate(dependency_path):
        state = "is-entry" if index == 0 else "is-terminal" if index == len(dependency_path) - 1 else "is-branch"
        lines.extend(
            [
                f'      <li class="adf-preview-atlas-node {state}">',
                f'        <a class="adf-preview-atlas-node-link" href="#atlas-{item["step_id"]}">',
                f'          <span class="adf-route-step">{item["step_label"]}</span>',
                f'          <strong>{item["label"]}</strong>',
                f'          <span>{item["details"]}</span>',
                "        </a>",
                "      </li>",
            ]
        )
    lines.extend(
        [
            "    </ol>",
            "  </section>",
            '  <section class="adf-preview-atlas-legend">',
            '    <article class="adf-preview-atlas-legend-card">',
            '      <p class="adf-panel-label">Legend</p>',
            '      <strong>Entry, branch, supporting</strong>',
            '      <p>Each node is colored by role so the route reads like a transit map instead of a chapter stack.</p>',
            "    </article>",
            '    <article class="adf-preview-atlas-legend-card">',
            '      <p class="adf-panel-label">Symptom fit</p>',
            f'      <strong>{max(len(symptom_entries), 1)} entry prompts</strong>',
            f'      <p>{" / ".join(entry["symptom_label"] for entry in symptom_entries[:3]) if symptom_entries else playbook["symptom_focus"]}</p>',
            "    </article>",
            '    <article class="adf-preview-atlas-legend-card">',
            '      <p class="adf-panel-label">Stop rule</p>',
            '      <strong>First broken useful-work node wins</strong>',
            '      <p>Do not keep walking the graph after the first node that fails real work.</p>',
            "    </article>",
            "  </section>",
            '  <section class="adf-preview-atlas-chapters">',
        ]
    )
    for step in playbook.get("steps", []):
        lines.extend(
            _render_template_step_panel(
                step=step,
                dependency_item=dependency_by_step.get(step["step_id"]),
                panel_class="adf-preview-atlas-chapter",
                section_prefix="atlas",
                show_outcomes=True,
            )
        )
    lines.extend(["  </section>", "</div>", ""])
    return "\n".join(lines)


def _render_template_incident_console(
    *,
    playbook: dict[str, Any],
    symptom_entries: list[dict[str, str]],
) -> str:
    dependency_path = playbook.get("dependency_path", [])
    dependency_by_step = {item["step_id"]: item for item in dependency_path}
    likely_services = playbook.get("likely_failing_services", [])
    command_total = sum(len(step.get("recommended_commands", [])) for step in playbook.get("steps", []))
    prompt_items = [
        f"        <li>{entry['symptom_label']}</li>"
        for entry in symptom_entries[:4]
    ] or ["        <li>Bring the case symptom into the branch scan before running commands.</li>"]
    lines = [
        '<div class="adf-preview-shell adf-preview-incident-console">',
        '  <section class="adf-preview-console-topbar">',
        f'    <div class="adf-preview-console-stat"><span class="adf-panel-label">Symptom</span><strong>{playbook["symptom_focus"]}</strong></div>',
        f'    <div class="adf-preview-console-stat"><span class="adf-panel-label">Likely branch</span><strong>{dependency_path[0]["label"] if dependency_path else "Start at host"}</strong></div>',
        '    <div class="adf-preview-console-stat"><span class="adf-panel-label">Operator stance</span><strong>Stop at first useful-work break</strong></div>',
        f'    <div class="adf-preview-console-stat"><span class="adf-panel-label">Action tray</span><strong>{command_total} commands ready</strong></div>',
        "  </section>",
        '  <section class="adf-preview-console-grid">',
        '    <aside class="adf-preview-console-panel adf-preview-console-signals">',
        '      <p class="adf-panel-label">Signal stack</p>',
    ]
    for item in dependency_path:
        lines.extend(
            [
                f'<a class="adf-preview-console-signal" href="#console-{item["step_id"]}">',
                f'  <span class="adf-route-step">{item["step_label"]}</span>',
                f'  <strong>{item["label"]}</strong>',
                f'  <span>{item["details"]}</span>',
                "</a>",
            ]
        )
    if likely_services:
        lines.extend(
            [
                '      <div class="adf-preview-console-chipset">',
                *[f'        <span class="adf-service-chip">{service}</span>' for service in likely_services[:5]],
                "      </div>",
            ]
        )
    lines.extend(["    </aside>", '    <div class="adf-preview-console-panel adf-preview-console-feed">', '      <p class="adf-panel-label">Incident feed</p>'])
    for step in playbook.get("steps", []):
        dependency_item = dependency_by_step.get(step["step_id"])
        label = dependency_item["label"] if dependency_item else _step_summary_label(step)
        lines.extend(
            [
                f'<article id="console-{step["step_id"]}" class="adf-preview-console-step">',
                '  <div class="adf-preview-console-step-head">',
                f'    <span class="adf-step-badge">{step["step_label"]}</span>',
                f"    <strong>{label}</strong>",
                "  </div>",
                f'  <p class="adf-preview-console-action">{step["action"]}</p>',
            ]
        )
        if step.get("why_this_matters"):
            lines.append(f'  <p class="adf-preview-console-note">{step["why_this_matters"]}</p>')
        if step.get("if_fail"):
            lines.append(f'  <p class="adf-preview-console-fail"><strong>Failure branch:</strong> {step["if_fail"]}</p>')
        if step.get("if_pass"):
            lines.append(f'  <p class="adf-preview-console-pass"><strong>Healthy branch:</strong> {step["if_pass"]}</p>')
        lines.extend(["</article>"])
    lines.extend(
        [
            "    </div>",
            '    <aside class="adf-preview-console-panel adf-preview-console-actions">',
            '      <p class="adf-panel-label">Action tray</p>',
            '      <p class="adf-preview-console-tray-copy">Commands live here, separate from the incident feed, so the operator can scan the branch story and the actions independently.</p>',
        ]
    )
    for step in playbook.get("steps", []):
        commands = step.get("recommended_commands", [])
        if not commands:
            continue
        lines.extend(
            [
                '<section class="adf-preview-console-action-group">',
                f'  <p class="adf-panel-label">{step["step_label"]}</p>',
                f"  <strong>{_step_summary_label(step)}</strong>",
            ]
        )
        for command in commands:
            lines.extend(_render_command_markdown(command))
        lines.extend(["</section>"])
    lines.extend(
        [
            "    </aside>",
            "  </section>",
            '  <section class="adf-preview-console-evidence">',
            '    <div class="adf-preview-console-panel">',
            '      <p class="adf-panel-label">Evidence shelf</p>',
            f'      <p>{playbook.get("decision_rule", "Keep only the evidence that proves where useful work stops.")}</p>',
            "    </div>",
            '    <div class="adf-preview-console-panel">',
            '      <p class="adf-panel-label">Operator prompts</p>',
            "      <ul>",
            *prompt_items,
            "      </ul>",
            "    </div>",
            "  </section>",
            "</div>",
            "",
        ]
    )
    return "\n".join(lines)


def _render_template_field_manual(
    *,
    playbook: dict[str, Any],
    symptom_entries: list[dict[str, str]],
) -> str:
    dependency_path = playbook.get("dependency_path", [])
    dependency_by_step = {item["step_id"]: item for item in dependency_path}
    prompt_items = [
        f"        <li>{entry['symptom_label']}</li>"
        for entry in symptom_entries[:4]
    ] or ["        <li>Bring the exact operator wording into chapter one.</li>"]
    lines = [
        '<div class="adf-preview-shell adf-preview-field-manual">',
        '  <section class="adf-preview-manual-cover">',
        '    <p class="adf-panel-label">Field Manual</p>',
        f"    <h2>{playbook['label']}</h2>",
        f"    <p>{playbook['symptom_focus']}</p>",
        '    <p class="adf-preview-manual-when"><strong>When to use this:</strong> Reach for this version when the operator needs a calmer chapter-by-chapter guide instead of a board or console.</p>',
        "  </section>",
        '  <section class="adf-preview-manual-contents">',
        '    <p class="adf-panel-label">Contents</p>',
        '    <ol class="adf-preview-manual-list">',
    ]
    for step in playbook.get("steps", []):
        lines.extend(
            [
                f'<li><a href="#manual-{step["step_id"]}"><span>{step["step_label"]}</span><strong>{_step_summary_label(step)}</strong></a></li>'
            ]
        )
    lines.extend(
        [
            "    </ol>",
            "  </section>",
            '  <section class="adf-preview-manual-body">',
            '    <article class="adf-preview-manual-prologue">',
            '      <p class="adf-panel-label">Operator note</p>',
            '      <p>This version reads like a guided field manual. Each chapter is meant to be read, then executed, instead of skimmed like a dashboard card.</p>',
            "    </article>",
        ]
    )
    for step in playbook.get("steps", []):
        dependency_item = dependency_by_step.get(step["step_id"])
        chapter_label = dependency_item["label"] if dependency_item else _step_summary_label(step)
        command_count = len(step.get("recommended_commands", []))
        lines.extend(
            [
                f'<details id="manual-{step["step_id"]}" class="adf-preview-manual-step">',
                '  <summary class="adf-preview-manual-summary">',
                '    <span class="adf-preview-manual-summary-copy">',
                f'      <span class="adf-preview-manual-kicker">{step["step_label"]}</span>',
                f'      <span class="adf-preview-manual-summary-title">{chapter_label}</span>',
                f'      <span class="adf-preview-manual-action">{step["action"]}</span>',
                "    </span>",
                '    <span class="adf-preview-manual-summary-meta">',
                f'      <span class="adf-preview-manual-summary-count">{command_count} command{"s" if command_count != 1 else ""}</span>',
                "    </span>",
                "  </summary>",
                '  <div class="adf-preview-manual-step-body">',
            ]
        )
        if step.get("why_this_matters"):
            lines.append(f'  <p>{step["why_this_matters"]}</p>')
        if step.get("recommended_commands"):
            lines.extend(['  <div class="adf-preview-manual-callout">', '    <p class="adf-panel-label">Field note</p>'])
            for command in step.get("recommended_commands", []):
                lines.extend(_render_command_markdown(command))
            lines.extend(["  </div>"])
        if step.get("if_pass") or step.get("if_fail"):
            lines.extend(['  <div class="adf-preview-manual-branch">'])
            if step.get("if_pass"):
                lines.append(f'    <p><strong>If healthy:</strong> {step["if_pass"]}</p>')
            if step.get("if_fail"):
                lines.append(f'    <p><strong>If not healthy:</strong> {step["if_fail"]}</p>')
            lines.extend(["  </div>"])
        lines.extend(["  </div>", "</details>"])
    lines.extend(
        [
            "  </section>",
            '  <section class="adf-preview-manual-appendix">',
            '    <div class="adf-preview-manual-note">',
            '      <p class="adf-panel-label">Appendix</p>',
            "      <p>Use the dependency path as orientation only. The chapter order matters more than the map in this template.</p>",
            "    </div>",
            '    <div class="adf-preview-manual-note">',
            '      <p class="adf-panel-label">Matching symptom prompts</p>',
            "      <ul>",
            *prompt_items,
            "      </ul>",
            "    </div>",
            "  </section>",
            "</div>",
            "",
        ]
    )
    return "\n".join(lines)


def _render_template_step_panel(
    *,
    step: dict[str, Any],
    dependency_item: dict[str, str] | None,
    panel_class: str,
    section_prefix: str,
    show_outcomes: bool,
) -> list[str]:
    label = dependency_item["label"] if dependency_item else _step_summary_label(step)
    lines = [
        f'<article id="{section_prefix}-{step["step_id"]}" class="adf-preview-step-panel {panel_class}">',
        '  <div class="adf-preview-step-head">',
        f'    <span class="adf-step-badge">{step["step_label"]}</span>',
        '    <div class="adf-preview-step-copy">',
        f"      <strong>{label}</strong>",
        f'      <p>{step["action"]}</p>',
        "    </div>",
        "  </div>",
    ]
    if step.get("why_this_matters"):
        lines.extend(
            [
                '  <p class="adf-preview-step-why">',
                f"    {step['why_this_matters']}",
                "  </p>",
            ]
        )
    for command in step.get("recommended_commands", []):
        lines.extend(_render_command_markdown(command))
    if show_outcomes and (step.get("if_pass") or step.get("if_fail")):
        lines.extend(['  <div class="adf-preview-step-outcomes">'])
        if step.get("if_pass"):
            lines.append(f'    <p><strong>If healthy:</strong> {step["if_pass"]}</p>')
        if step.get("if_fail"):
            lines.append(f'    <p><strong>If this fails:</strong> {step["if_fail"]}</p>')
        lines.extend(["  </div>"])
    lines.extend(["</article>", ""])
    return lines


def _strip_frontmatter(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return markdown
    lines = markdown.splitlines()
    end_index = None
    for index in range(1, len(lines)):
        if lines[index] == "---":
            end_index = index
            break
    if end_index is None:
        return markdown
    return "\n".join(lines[end_index + 1 :]).lstrip()


def _render_playbook_markdown(
    *,
    playbook: dict[str, Any],
    order: int,
    symptom_entries: list[dict[str, str]],
) -> str:
    if playbook["playbook_id"] == PRIMARY_PLAYBOOK_ID:
        return _render_asms_ui_playbook_markdown(
            playbook=playbook,
            order=order,
            symptom_entries=symptom_entries,
        )

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
            "</div>",
            "</div>",
            "</div>",
            "",
        ]
    )

    return "\n".join(lines) + "\n"


def _render_asms_ui_playbook_markdown(
    *,
    playbook: dict[str, Any],
    order: int,
    symptom_entries: list[dict[str, str]],
) -> str:
    dependency_path = playbook.get("dependency_path", [])
    dependency_by_step = {item["step_id"]: item for item in dependency_path}

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
        "## ASMS UI Working Map",
        "",
        '<div class="adf-system-shell">',
        '  <div class="adf-system-topbar">',
        '    <div class="adf-panel">',
        '      <p class="adf-panel-label">Working rule</p>',
        "      <p>Start at the host, move into Apache/HTTPD serving the UI, then split into auth and app branches. Stop at the first place where useful work no longer happens.</p>",
        "    </div>",
        '    <div class="adf-panel">',
        '      <p class="adf-panel-label">What this page is proving</p>',
        "      <p>The goal is not to prove that services merely exist. The goal is to prove whether the ASMS UI path can do useful work for the current customer scenario.</p>",
        "    </div>",
        "  </div>",
        '  <div class="adf-system-map adf-panel">',
        '    <p class="adf-panel-label">Useful-work path</p>',
        '    <ol class="adf-system-map-list">',
    ]
    for item in dependency_path:
        lines.extend(
            [
                '      <li class="adf-system-map-item">',
                f'        <a class="adf-system-map-link" href="#{item["step_id"]}">',
                f'          <span class="adf-route-step">{item["step_label"]}</span>',
                f"          <strong>{item['label']}</strong>",
                f"          <span>{item['details']}</span>",
                "        </a>",
                "      </li>",
            ]
        )
    lines.extend(
        [
            "    </ol>",
            "  </div>",
            '  <div class="adf-system-grid">',
            '    <aside class="adf-system-nav adf-panel">',
            '      <p class="adf-panel-label">Quick jump</p>',
            '      <div class="adf-system-jumps">',
        ]
    )
    for item in dependency_path:
        lines.extend(
            [
                f'<a class="adf-system-jump" href="#{item["step_id"]}">',
                f'  <span class="adf-route-step">{item["step_label"]}</span>',
                f'  <strong>{item["label"]}</strong>',
                f'  <span>{item["details"]}</span>',
                "</a>",
            ]
        )
    lines.extend(["      </div>"])
    if symptom_entries:
        lines.extend(
            [
                '      <div class="adf-system-sideblock">',
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
            '    <div class="adf-system-main">',
        ]
    )
    for step in playbook.get("steps", []):
        lines.extend(_render_system_checkpoint_markdown(step, dependency_by_step.get(step["step_id"])))
    lines.extend(
        [
            "</div>",
            "</div>",
            "</div>",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_system_checkpoint_markdown(step: dict[str, Any], dependency_item: dict[str, str] | None) -> list[str]:
    checkpoint_label = dependency_item["label"] if dependency_item else _step_summary_label(step)
    lines = [
        f'<details id="{step["step_id"]}" class="adf-system-checkpoint">',
        '<summary class="adf-system-summary">',
        f'  <span class="adf-step-badge">{step["step_label"]}</span>',
        '  <span class="adf-system-heading">',
        f"    <strong>{checkpoint_label}</strong>",
        f'    <span>{step["action"]}</span>',
        "  </span>",
        '  <span class="adf-step-toggle" aria-hidden="true"></span>',
        "</summary>",
        "",
        '<div class="adf-system-body">',
    ]
    if step.get("why_this_matters"):
        lines.extend(
            [
                '<div class="adf-system-brief adf-panel">',
                '  <p class="adf-panel-label">Why this checkpoint exists</p>',
                f'  <p>{step["why_this_matters"]}</p>',
                "</div>",
                "",
            ]
        )
    for command in step.get("recommended_commands", []):
        lines.extend(_render_command_markdown(command))
    lines.extend(["</div>", "</details>", ""])
    return lines


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
    known_working_example = command.get("known_working_example") or derive_known_working_example(command)
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

    example = None
    example_title = "Known working example"
    if known_working_example:
        example = known_working_example.get("output")
        example_title = known_working_example.get("title") or example_title
    else:
        example = command.get("example_output")
    if example:
        lines.extend(
            [
                f'<p class="adf-inline-label">{example_title}</p>',
                "",
                "```text",
                example.rstrip(),
                "```",
            ]
        )
    lines.extend(["</div>", ""])
    return lines


def _command_knowledge(command: dict[str, Any]) -> tuple[str, list[str]] | None:
    linux_note = command.get("linux_note") or derive_command_linux_note(command)
    if not linux_note:
        return None
    return linux_note["title"], linux_note["items"]


def _render_custom_css() -> str:
    return "\n".join(
        [
            ":root {",
            "  --sl-color-accent-low: #d7ebe8;",
            "  --sl-color-accent: #155e63;",
            "  --sl-color-accent-high: #0d393e;",
            "  --sl-content-width: 124rem;",
            "  --adf-bg-soft: #eef3ef;",
            "  --adf-panel: rgba(255, 255, 255, 0.96);",
            "  --adf-panel-strong: #f8fbf8;",
            "  --adf-border: rgba(21, 94, 99, 0.14);",
            "  --adf-border-strong: rgba(21, 94, 99, 0.24);",
            "  --adf-muted: #52626c;",
            "  --adf-code-bg: #15262f;",
            "  --adf-shell-max-width: 112rem;",
            "  --adf-command-max-width: 92ch;",
            "}",
            "",
            ":root[data-theme='dark'] {",
            "  --adf-bg-soft: #0d1519;",
            "  --adf-panel: rgba(17, 24, 30, 0.96);",
            "  --adf-panel-strong: #132028;",
            "  --adf-border: rgba(130, 181, 187, 0.18);",
            "  --adf-border-strong: rgba(130, 181, 187, 0.34);",
            "  --adf-muted: #b7c4ca;",
            "}",
            "",
            "body {",
            "  background: radial-gradient(circle at top, rgba(21, 94, 99, 0.07), transparent 24%), var(--adf-bg-soft);",
            "}",
            "",
            ":root[data-theme='dark'] body {",
            "  background: radial-gradient(circle at top, rgba(70, 129, 139, 0.18), transparent 28%), var(--adf-bg-soft);",
            "}",
            "",
            ".content-panel {",
            "  border: 1px solid var(--adf-border);",
            "  border-radius: 0.9rem;",
            "  background: rgba(255, 255, 255, 0.94);",
            "}",
            "",
            ":root[data-theme='dark'] .content-panel {",
            "  background: rgba(17, 24, 30, 0.94);",
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
            ":root[data-theme='dark'] .sl-markdown-content {",
            "  color: #e7eef2;",
            "}",
            "",
            ":root[data-theme='dark'] .sl-markdown-content :is(h1, h2, h3, h4, strong) {",
            "  color: #f3f7fa;",
            "}",
            "",
            ".main-pane {",
            "  width: 100% !important;",
            "}",
            "",
            ".content-panel > .sl-container {",
            "  width: min(100%, 124rem) !important;",
            "  max-width: none !important;",
            "  margin-left: 0 !important;",
            "  margin-right: auto !important;",
            "}",
            "",
            ".adf-panel {",
            "  border-radius: 0.9rem;",
            "  border: 1px solid var(--adf-border);",
            "  background: linear-gradient(180deg, var(--adf-panel-strong) 0%, var(--adf-panel) 100%);",
            "  padding: 0.95rem 1rem;",
            "}",
            "",
            ":root[data-theme='dark'] .adf-panel {",
            "  box-shadow: 0 18px 36px rgba(0, 0, 0, 0.24);",
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
            ":root[data-theme='dark'] .adf-panel-label,",
            ":root[data-theme='dark'] .adf-inline-label,",
            ":root[data-theme='dark'] .adf-check-note-summary,",
            ":root[data-theme='dark'] .adf-route-step {",
            "  color: #b9f1f4;",
            "}",
            "",
            ".adf-home-shell,",
            ".adf-cockpit-shell,",
            ".adf-system-shell {",
            "  display: grid;",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-home-topbar,",
            ".adf-cockpit-topbar,",
            ".adf-system-topbar {",
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
            ".adf-template-index-grid,",
            ".adf-symptom-grid {",
            "  display: grid;",
            "  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));",
            "  gap: 0.85rem;",
            "}",
            "",
            ".adf-home-card,",
            ".adf-template-card,",
            ".adf-symptom-card,",
            ".adf-cockpit-jump,",
            ".adf-path-link,",
            ".adf-system-jump,",
            ".adf-system-map-link {",
            "  display: grid;",
            "  gap: 0.3rem;",
            "  border-radius: 0.9rem;",
            "  border: 1px solid var(--adf-border);",
            "  background: linear-gradient(180deg, rgba(245, 250, 248, 0.96) 0%, rgba(255, 255, 255, 0.98) 100%);",
            "  padding: 0.9rem;",
            "}",
            "",
            ".adf-home-card,",
            ".adf-template-card,",
            ".adf-cockpit-jump,",
            ".adf-symptom-link,",
            ".adf-path-link,",
            ".adf-system-jump,",
            ".adf-system-map-link {",
            "  text-decoration: none;",
            "  color: inherit;",
            "}",
            "",
            ".adf-home-card:hover,",
            ".adf-template-card:hover,",
            ".adf-cockpit-jump:hover,",
            ".adf-symptom-link:hover,",
            ".adf-path-link:hover,",
            ".adf-system-jump:hover,",
            ".adf-system-map-link:hover {",
            "  border-color: var(--adf-border-strong);",
            "  transform: translateY(-1px);",
            "}",
            "",
            ":root[data-theme='dark'] .adf-home-card,",
            ":root[data-theme='dark'] .adf-template-card,",
            ":root[data-theme='dark'] .adf-symptom-card,",
            ":root[data-theme='dark'] .adf-cockpit-jump,",
            ":root[data-theme='dark'] .adf-path-link,",
            ":root[data-theme='dark'] .adf-system-jump,",
            ":root[data-theme='dark'] .adf-system-map-link,",
            ":root[data-theme='dark'] .adf-template-intro,",
            ":root[data-theme='dark'] .adf-preview-step-panel,",
            ":root[data-theme='dark'] .adf-preview-manual-step,",
            ":root[data-theme='dark'] .adf-preview-manual-cover,",
            ":root[data-theme='dark'] .adf-preview-manual-cover-note,",
            ":root[data-theme='dark'] .adf-preview-manual-chip,",
            ":root[data-theme='dark'] .adf-preview-manual-callout,",
            ":root[data-theme='dark'] .adf-preview-manual-note,",
            ":root[data-theme='dark'] .adf-preview-atlas-head,",
            ":root[data-theme='dark'] .adf-preview-atlas-canvas,",
            ":root[data-theme='dark'] .adf-preview-atlas-node-link,",
            ":root[data-theme='dark'] .adf-preview-atlas-legend-card {",
            "  background: linear-gradient(180deg, rgba(19, 30, 37, 0.98) 0%, rgba(15, 23, 29, 0.98) 100%);",
            "  border-color: rgba(130, 181, 187, 0.18);",
            "  color: #e7eef2;",
            "}",
            "",
            ".adf-home-card span,",
            ".adf-template-card span,",
            ".adf-symptom-card span,",
            ".adf-cockpit-jump span:last-child,",
            ".adf-path-link span:last-child,",
            ".adf-system-jump span:last-child,",
            ".adf-system-map-link span:last-child {",
            "  color: var(--adf-muted);",
            "}",
            "",
            ".adf-home-card-list {",
            "  display: grid;",
            "  gap: 0.25rem;",
            "  font-size: 0.9rem;",
            "}",
            "",
            ".adf-template-intro {",
            "  display: grid;",
            "  gap: 0.55rem;",
            "  margin-bottom: 1rem;",
            "}",
            "",
            ".adf-template-intro h2 {",
            "  margin: 0;",
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
            "  grid-template-columns: 22rem minmax(0, 1fr) !important;",
            "  gap: 1rem;",
            "  align-items: start;",
            "}",
            "",
            ".adf-system-grid {",
            "  display: grid;",
            "  grid-template-columns: 22rem minmax(0, 1fr) !important;",
            "  gap: 1rem;",
            "  align-items: start;",
            "}",
            "",
            ".adf-cockpit-main {",
            "  display: grid;",
            "  gap: 1rem;",
            "  min-width: 0;",
            "  max-width: 100%;",
            "}",
            "",
            ".adf-system-main {",
            "  display: grid;",
            "  gap: 1rem;",
            "  min-width: 0;",
            "  max-width: 100%;",
            "}",
            "",
            ".adf-cockpit-nav {",
            "  align-self: start;",
            "  position: sticky;",
            "  top: 1.1rem;",
            "  width: 100%;",
            "}",
            "",
            ".adf-system-nav {",
            "  align-self: start;",
            "  position: sticky;",
            "  top: 1.1rem;",
            "  width: 100%;",
            "}",
            "",
            ".adf-cockpit-jumps,",
            ".adf-path-list,",
            ".adf-system-jumps {",
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
            ".adf-system-sideblock {",
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
            ".adf-system-sideblock ul {",
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
            ".adf-system-map {",
            "  display: grid;",
            "  gap: 0.7rem;",
            "  border-radius: 0.9rem;",
            "  border: 1px solid var(--adf-border);",
            "  background: linear-gradient(180deg, rgba(241, 247, 244, 0.95) 0%, rgba(255, 255, 255, 0.98) 100%);",
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
            ".adf-system-checkpoint {",
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
            ".adf-system-summary {",
            "  display: flex;",
            "  align-items: flex-start;",
            "  gap: 0.75rem;",
            "  cursor: pointer;",
            "  list-style: none;",
            "  padding: 0.8rem 0 0.4rem;",
            "}",
            "",
            ".adf-step-summary::-webkit-details-marker,",
            ".adf-step-summary::marker,",
            ".adf-system-summary::-webkit-details-marker,",
            ".adf-system-summary::marker {",
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
            ".adf-system-heading {",
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
            ".adf-system-heading span {",
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
            ".adf-system-body {",
            "  display: grid;",
            "  gap: 0.8rem;",
            "  padding-top: 0.2rem;",
            "}",
            "",
            ".adf-check {",
            "  display: grid;",
            "  gap: 0.7rem;",
            "  width: 100%;",
            "  min-width: 0;",
            "  border-top: 1px solid rgba(21, 94, 99, 0.08);",
            "  padding-top: 0.85rem;",
            "}",
            "",
            ".adf-system-body > .adf-check:first-of-type {",
            "  border-top: 0;",
            "  padding-top: 0;",
            "}",
            "",
            ".adf-step-body > .adf-check:first-of-type {",
            "  border-top: 0;",
            "  padding-top: 0;",
            "}",
            "",
            ".adf-system-brief {",
            "  padding: 0.9rem 1rem;",
            "}",
            "",
            ".adf-check-label {",
            "  margin: 0 0 0.55rem;",
            "  font-weight: 700;",
            "}",
            "",
            ":root[data-theme='dark'] .adf-check-label {",
            "  color: #f3f7fa;",
            "}",
            "",
            ":root[data-theme='dark'] .adf-check-note-summary span,",
            ":root[data-theme='dark'] .adf-preview-manual-callout .adf-panel-label,",
            ":root[data-theme='dark'] .adf-check p.adf-inline-label,",
            ":root[data-theme='dark'] .adf-check-signal .adf-inline-label,",
            ":root[data-theme='dark'] .adf-check-failure .adf-inline-label,",
            ":root[data-theme='dark'] .adf-check-reference .adf-inline-label,",
            ":root[data-theme='dark'] .adf-step-outcome .adf-inline-label {",
            "  color: #d9fbff;",
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
            ":root[data-theme='dark'] .adf-step-brief,",
            ":root[data-theme='dark'] .adf-check-signal,",
            ":root[data-theme='dark'] .adf-check-reference,",
            ":root[data-theme='dark'] .adf-check-failure,",
            ":root[data-theme='dark'] .adf-step-outcome,",
            ":root[data-theme='dark'] .adf-check-knowledge,",
            ":root[data-theme='dark'] .adf-step-evidence {",
            "  color: #e2ebf0;",
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
            ".adf-system-map-list {",
            "  list-style: none;",
            "  margin: 0;",
            "  padding: 0;",
            "  display: grid;",
            "  grid-template-columns: repeat(5, minmax(0, 1fr));",
            "  gap: 0.65rem;",
            "}",
            "",
            ".adf-system-map-item {",
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
            ".adf-check pre,",
            ".adf-check .expressive-code,",
            ".adf-check .frame,",
            ".adf-system-checkpoint pre,",
            ".adf-system-checkpoint .expressive-code,",
            ".adf-system-checkpoint .frame {",
            "  --ec-brdRad: 0.8rem !important;",
            "  width: 100% !important;",
            "  max-width: none !important;",
            "  margin-left: 0 !important;",
            "  margin-right: auto !important;",
            "}",
            "",
            ".adf-check .expressive-code .frame,",
            ".adf-system-checkpoint .expressive-code .frame {",
            "  border-radius: calc(var(--ec-brdRad) + var(--ec-brdWd)) !important;",
            "  overflow: hidden !important;",
            "}",
            "",
            ":root[data-theme='light'] .adf-check .expressive-code,",
            ":root[data-theme='light'] .adf-system-checkpoint .expressive-code {",
            "  --ec-brdCol: color-mix(in srgb, var(--sl-color-gray-5), transparent 25%) !important;",
            "  --ec-codeBg: #23262f !important;",
            "  --ec-codeFg: #d6deeb !important;",
            "  --ec-codeSelBg: #1d3b53 !important;",
            "  --ec-gtrFg: #63798b !important;",
            "  --ec-gtrBrdCol: #63798b33 !important;",
            "  --ec-gtrHlFg: #c5e4fd97 !important;",
            "  --ec-uiSelBg: #234d708c !important;",
            "  --ec-uiSelFg: #ffffff !important;",
            "  --ec-focusBrd: #122d42 !important;",
            "  --ec-sbThumbCol: #ffffff17 !important;",
            "  --ec-sbThumbHoverCol: #ffffff47 !important;",
            "  --ec-tm-markBg: #ffffff17 !important;",
            "  --ec-tm-markBrdCol: #ffffff40 !important;",
            "  --ec-tm-insBg: #1e571599 !important;",
            "  --ec-tm-insBrdCol: #487f3bd0 !important;",
            "  --ec-tm-insDiffIndCol: #79b169d0 !important;",
            "  --ec-tm-delBg: #862d2799 !important;",
            "  --ec-tm-delBrdCol: #d1584d !important;",
            "  --ec-tm-delDiffIndCol: #e26b5d !important;",
            "  --ec-frm-shdCol: #00000070 !important;",
            "  --ec-frm-edBg: #23262f !important;",
            "  --ec-frm-trmTtbBg: #1b1e26 !important;",
            "  --ec-frm-trmBg: #23262f !important;",
            "}",
            "",
            ":root[data-theme='dark'] .adf-check .expressive-code,",
            ":root[data-theme='dark'] .adf-system-checkpoint .expressive-code {",
            "  --ec-brdCol: rgba(99, 121, 139, 0.35) !important;",
            "  --ec-codeBg: #162833 !important;",
            "  --ec-codeFg: #eef7ff !important;",
            "  --ec-codeSelBg: #28526d !important;",
            "  --ec-gtrFg: #9bb4c7 !important;",
            "  --ec-gtrBrdCol: #63798b33 !important;",
            "  --ec-gtrHlFg: #c5e4fd97 !important;",
            "  --ec-uiSelBg: #234d708c !important;",
            "  --ec-uiSelFg: #ffffff !important;",
            "  --ec-focusBrd: #27465f !important;",
            "  --ec-sbThumbCol: #ffffff17 !important;",
            "  --ec-sbThumbHoverCol: #ffffff47 !important;",
            "  --ec-tm-markBg: #ffffff17 !important;",
            "  --ec-tm-markBrdCol: #ffffff40 !important;",
            "  --ec-tm-insBg: #1e571599 !important;",
            "  --ec-tm-insBrdCol: #487f3bd0 !important;",
            "  --ec-tm-insDiffIndCol: #79b169d0 !important;",
            "  --ec-tm-delBg: #862d2799 !important;",
            "  --ec-tm-delBrdCol: #d1584d !important;",
            "  --ec-tm-delDiffIndCol: #e26b5d !important;",
            "  --ec-frm-shdCol: #00000070 !important;",
            "  --ec-frm-edBg: #162833 !important;",
            "  --ec-frm-trmTtbBg: #13212c !important;",
            "  --ec-frm-trmBg: #162833 !important;",
            "}",
            "",
            ":root[data-theme='light'] .adf-check .expressive-code .ec-line :where(span[style^='--']:not([class])),",
            ":root[data-theme='light'] .adf-system-checkpoint .expressive-code .ec-line :where(span[style^='--']:not([class])) {",
            "  color: var(--0, inherit) !important;",
            "  background-color: var(--0bg, transparent) !important;",
            "  font-style: var(--0fs, inherit) !important;",
            "  font-weight: var(--0fw, inherit) !important;",
            "  text-decoration: var(--0td, inherit) !important;",
            "}",
            "",
            ":root[data-theme='dark'] .adf-check .expressive-code .ec-line :where(span[style^='--']:not([class])),",
            ":root[data-theme='dark'] .adf-system-checkpoint .expressive-code .ec-line :where(span[style^='--']:not([class])) {",
            "  color: var(--0, inherit) !important;",
            "  background-color: var(--0bg, transparent) !important;",
            "  font-style: var(--0fs, inherit) !important;",
            "  font-weight: var(--0fw, inherit) !important;",
            "  text-decoration: var(--0td, inherit) !important;",
            "}",
            "",
            ".adf-check .expressive-code .frame .header,",
            ".adf-system-checkpoint .expressive-code .frame .header {",
            "  display: none !important;",
            "}",
            "",
            ".adf-check .expressive-code .frame.has-title pre,",
            ".adf-check .expressive-code .frame.has-title code,",
            ".adf-check .expressive-code .frame.is-terminal pre,",
            ".adf-check .expressive-code .frame.is-terminal code,",
            ".adf-system-checkpoint .expressive-code .frame.has-title pre,",
            ".adf-system-checkpoint .expressive-code .frame.has-title code,",
            ".adf-system-checkpoint .expressive-code .frame.is-terminal pre,",
            ".adf-system-checkpoint .expressive-code .frame.is-terminal code {",
            "  border-top: var(--ec-brdWd) solid var(--ec-brdCol) !important;",
            "  border-top-left-radius: calc(var(--ec-brdRad) + var(--ec-brdWd)) !important;",
            "  border-top-right-radius: calc(var(--ec-brdRad) + var(--ec-brdWd)) !important;",
            "}",
            "",
            ".adf-check .expressive-code .frame.is-terminal pre,",
            ".adf-system-checkpoint .expressive-code .frame.is-terminal pre {",
            "  overflow-x: hidden !important;",
            "}",
            "",
            ".adf-check .expressive-code .frame.is-terminal .ec-line .code,",
            ".adf-system-checkpoint .expressive-code .frame.is-terminal .ec-line .code {",
            "  white-space: pre-wrap !important;",
            "  overflow-wrap: anywhere !important;",
            "  min-width: 0 !important;",
            "  padding-inline-end: calc(var(--ec-codePadInl) + 6.2rem) !important;",
            "}",
            "",
            ".adf-check .expressive-code .frame.is-terminal .copy,",
            ".adf-system-checkpoint .expressive-code .frame.is-terminal .copy {",
            "  inset-block-start: 0.9rem !important;",
            "  inset-inline-end: 6rem !important;",
            "  z-index: 3 !important;",
            "}",
            "",
            ".adf-check .expressive-code .frame.is-terminal .copy [aria-live],",
            ".adf-system-checkpoint .expressive-code .frame.is-terminal .copy [aria-live] {",
            "  position: absolute !important;",
            "  inset-inline-start: calc(100% + 0.45rem) !important;",
            "  inset-block-start: 50% !important;",
            "  transform: translateY(-50%) !important;",
            "  display: block !important;",
            "  pointer-events: none !important;",
            "}",
            "",
            ".adf-check .expressive-code .frame:not(.is-terminal) .copy,",
            ".adf-system-checkpoint .expressive-code .frame:not(.is-terminal) .copy {",
            "  display: none !important;",
            "}",
            "",
            ".adf-check .expressive-code .copy button,",
            ".adf-system-checkpoint .expressive-code .copy button {",
            "  background: rgba(27, 30, 38, 0.96) !important;",
            "  color: #d6deeb !important;",
            "  border-color: rgba(99, 121, 139, 0.35) !important;",
            "  border-radius: 0.75rem !important;",
            "  width: 2rem !important;",
            "  height: 2rem !important;",
            "  opacity: 0 !important;",
            "  pointer-events: none !important;",
            "  transition: opacity 160ms ease !important;",
            "}",
            "",
            ".adf-check .expressive-code .frame.is-terminal:hover .copy button,",
            ".adf-check .expressive-code .frame.is-terminal:focus-within .copy button,",
            ".adf-system-checkpoint .expressive-code .frame.is-terminal:hover .copy button,",
            ".adf-system-checkpoint .expressive-code .frame.is-terminal:focus-within .copy button {",
            "  opacity: 0.96 !important;",
            "  pointer-events: auto !important;",
            "}",
            "",
            ".adf-check .expressive-code .copy .feedback,",
            ".adf-system-checkpoint .expressive-code .copy .feedback {",
            "  margin-inline: 0 !important;",
            "  white-space: nowrap !important;",
            "}",
            "",
            ".adf-check .expressive-code .copy .feedback::after,",
            ".adf-system-checkpoint .expressive-code .copy .feedback::after {",
            "  inset-inline-end: auto !important;",
            "  inset-inline-start: calc(-2 * (var(--tooltip-arrow-size) - 0.5px)) !important;",
            "  border-inline-start-color: transparent !important;",
            "  border-inline-end-color: var(--tooltip-bg) !important;",
            "}",
            "",
            ".adf-preview-shell {",
            "  display: grid;",
            "  gap: 1.25rem;",
            "}",
            "",
            ".adf-preview-step-panel {",
            "  border-radius: 1.05rem;",
            "  border: 1px solid var(--adf-border);",
            "  background: rgba(255, 255, 255, 0.98);",
            "  padding: 1.05rem 1.1rem;",
            "  box-shadow: 0 16px 32px rgba(20, 34, 38, 0.06);",
            "}",
            "",
            ".adf-preview-step-head {",
            "  display: flex;",
            "  gap: 0.85rem;",
            "  align-items: flex-start;",
            "  margin-bottom: 0.7rem;",
            "}",
            "",
            ".adf-preview-step-copy {",
            "  display: grid;",
            "  gap: 0.22rem;",
            "}",
            "",
            ".adf-preview-step-copy p,",
            ".adf-preview-step-why,",
            ".adf-preview-step-outcomes p {",
            "  margin: 0;",
            "  color: var(--adf-muted);",
            "}",
            "",
            ".adf-preview-step-outcomes {",
            "  display: grid;",
            "  gap: 0.35rem;",
            "  margin-top: 0.7rem;",
            "  padding-top: 0.7rem;",
            "  border-top: 1px solid var(--adf-border);",
            "}",
            "",
            ".adf-preview-atlas-map {",
            "  gap: 1.35rem;",
            "}",
            "",
            ".adf-preview-atlas-head {",
            "  border-width: 2px;",
            "  background: linear-gradient(135deg, rgba(223, 241, 249, 0.98) 0%, rgba(255, 255, 255, 0.99) 100%);",
            "  box-shadow: 0 20px 44px rgba(30, 82, 110, 0.10);",
            "}",
            "",
            ".adf-preview-atlas-canvas {",
            "  display: grid;",
            "  gap: 1rem;",
            "  background: linear-gradient(180deg, rgba(244, 251, 253, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);",
            "}",
            "",
            ".adf-preview-atlas-kicker {",
            "  max-width: 60rem;",
            "}",
            "",
            ".adf-preview-atlas-kicker p:last-child {",
            "  margin-bottom: 0;",
            "}",
            "",
            ".adf-preview-atlas-node-grid {",
            "  list-style: none;",
            "  margin: 0;",
            "  padding: 0;",
            "  display: grid;",
            "  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));",
            "  gap: 0.8rem;",
            "}",
            "",
            ".adf-preview-atlas-node {",
            "  position: relative;",
            "}",
            "",
            ".adf-preview-atlas-node:not(:last-child)::after {",
            "  content: '->';",
            "  position: absolute;",
            "  right: -0.6rem;",
            "  top: 50%;",
            "  transform: translateY(-50%);",
            "  color: rgba(24, 98, 130, 0.46);",
            "  font-weight: 700;",
            "}",
            "",
            ".adf-preview-atlas-node-link {",
            "  display: grid;",
            "  gap: 0.32rem;",
            "  text-decoration: none;",
            "  color: inherit;",
            "  border-radius: 1rem;",
            "  min-height: 100%;",
            "  border: 1px solid rgba(24, 98, 130, 0.18);",
            "  background: linear-gradient(180deg, rgba(235, 247, 252, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);",
            "  padding: 1rem;",
            "}",
            "",
            ".adf-preview-atlas-legend {",
            "  display: grid;",
            "  grid-template-columns: repeat(3, minmax(0, 1fr));",
            "  gap: 0.85rem;",
            "}",
            "",
            ".adf-preview-atlas-legend-card {",
            "  border-radius: 1rem;",
            "  border: 1px solid rgba(24, 98, 130, 0.14);",
            "  background: rgba(255, 255, 255, 0.98);",
            "  padding: 1rem 1.05rem;",
            "}",
            "",
            ".adf-preview-atlas-legend-card p:last-child {",
            "  margin-bottom: 0;",
            "}",
            "",
            ".adf-preview-atlas-chapters {",
            "  display: grid;",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-preview-atlas-chapter {",
            "  border-left: 6px solid rgba(24, 98, 130, 0.35);",
            "  box-shadow: 0 18px 32px rgba(30, 82, 110, 0.08);",
            "}",
            "",
            ".adf-preview-incident-console {",
            "  color: #e8f1f7;",
            "}",
            "",
            ".adf-preview-console-top {",
            "  display: grid;",
            "  gap: 0.9rem;",
            "}",
            "",
            ".adf-preview-console-banner {",
            "  border-radius: 1.1rem;",
            "  padding: 1.15rem 1.2rem;",
            "  background: linear-gradient(180deg, #10202c 0%, #172d3f 100%);",
            "  color: #eef5fb;",
            "  border: 1px solid rgba(126, 170, 211, 0.22);",
            "  box-shadow: 0 24px 44px rgba(11, 19, 30, 0.28);",
            "}",
            "",
            ".adf-preview-console-banner p:last-child,",
            ".adf-preview-console-metric strong,",
            ".adf-preview-console-banner h2,",
            ".adf-preview-console-event strong,",
            ".adf-preview-console-tray strong,",
            ".adf-preview-console-rail strong {",
            "  color: inherit;",
            "}",
            "",
            ".adf-preview-console-metrics {",
            "  display: grid;",
            "  grid-template-columns: repeat(3, minmax(0, 1fr));",
            "  gap: 0.8rem;",
            "}",
            "",
            ".adf-preview-console-metric {",
            "  display: grid;",
            "  gap: 0.22rem;",
            "  border-radius: 0.95rem;",
            "  padding: 0.95rem 1rem;",
            "  background: linear-gradient(180deg, rgba(20, 36, 50, 0.98) 0%, rgba(29, 52, 72, 0.98) 100%);",
            "  border: 1px solid rgba(126, 170, 211, 0.2);",
            "}",
            "",
            ".adf-preview-console-grid {",
            "  display: grid;",
            "  grid-template-columns: 18rem minmax(0, 1fr) 16rem;",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-preview-console-rail,",
            ".adf-preview-console-tray {",
            "  display: grid;",
            "  gap: 0.7rem;",
            "  align-self: start;",
            "  position: sticky;",
            "  top: 1rem;",
            "  padding: 1rem;",
            "  border-radius: 1rem;",
            "  background: linear-gradient(180deg, rgba(17, 32, 44, 0.98) 0%, rgba(26, 46, 63, 0.98) 100%);",
            "  border: 1px solid rgba(126, 170, 211, 0.16);",
            "}",
            "",
            ".adf-preview-console-signal-card,",
            ".adf-preview-console-tray-card {",
            "  display: grid;",
            "  gap: 0.24rem;",
            "  color: #eef5fb;",
            "  border-radius: 0.95rem;",
            "  padding: 0.9rem;",
            "  background: linear-gradient(180deg, rgba(17, 32, 44, 0.98) 0%, rgba(26, 46, 63, 0.98) 100%);",
            "  border: 1px solid rgba(126, 170, 211, 0.16);",
            "}",
            "",
            ".adf-preview-console-service-stack {",
            "  display: flex;",
            "  flex-wrap: wrap;",
            "  gap: 0.45rem;",
            "}",
            "",
            ".adf-preview-console-feed {",
            "  display: grid;",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-preview-console-event {",
            "  background: linear-gradient(180deg, #13222e 0%, #1b3243 100%);",
            "  color: #e8f1f7;",
            "  border-color: rgba(126, 170, 211, 0.22);",
            "  box-shadow: 0 22px 36px rgba(11, 19, 30, 0.22);",
            "}",
            "",
            ".adf-preview-console-event .adf-check-label,",
            ".adf-preview-console-event .adf-inline-label {",
            "  color: #f3f7fb;",
            "}",
            "",
            ".adf-preview-console-event .adf-preview-step-copy p,",
            ".adf-preview-console-event .adf-preview-step-why,",
            ".adf-preview-console-event .adf-preview-step-outcomes p,",
            ".adf-preview-console-event .adf-check-signal,",
            ".adf-preview-console-event .adf-check-reference,",
            ".adf-preview-console-event .adf-check-failure,",
            ".adf-preview-console-tray-copy {",
            "  color: #bfd0dc;",
            "}",
            "",
            ".adf-preview-field-manual {",
            "  gap: 1.5rem;",
            "}",
            "",
            ".adf-preview-manual-cover {",
            "  display: grid;",
            "  grid-template-columns: minmax(0, 1.4fr) minmax(18rem, 0.8fr);",
            "  gap: 1rem;",
            "  padding: 1.3rem 1.4rem;",
            "  border-radius: 1.15rem;",
            "  background: linear-gradient(180deg, rgba(251, 247, 238, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);",
            "  border: 1px solid rgba(142, 102, 49, 0.20);",
            "  box-shadow: 0 18px 36px rgba(120, 90, 46, 0.08);",
            "}",
            "",
            ".adf-preview-manual-cover-copy h2,",
            ".adf-preview-manual-cover-copy p:last-child,",
            ".adf-preview-manual-cover-note p:last-child {",
            "  margin-bottom: 0;",
            "}",
            "",
            ".adf-preview-manual-cover-note {",
            "  align-self: start;",
            "  padding: 1rem 1.05rem;",
            "  border-radius: 0.95rem;",
            "  background: rgba(255, 252, 247, 0.95);",
            "  border: 1px solid rgba(142, 102, 49, 0.16);",
            "}",
            "",
            ".adf-preview-manual-nav {",
            "  display: flex;",
            "  flex-wrap: wrap;",
            "  gap: 0.7rem;",
            "}",
            "",
            ".adf-preview-manual-chip {",
            "  display: grid;",
            "  gap: 0.18rem;",
            "  text-decoration: none;",
            "  color: inherit;",
            "  padding: 0.75rem 0.95rem;",
            "  border-radius: 999px;",
            "  border: 1px solid rgba(142, 102, 49, 0.16);",
            "  background: rgba(255, 252, 247, 0.95);",
            "}",
            "",
            ".adf-preview-manual-body {",
            "  display: grid;",
            "  gap: 1.2rem;",
            "  max-width: 84rem;",
            "}",
            "",
            ".adf-preview-manual-prologue {",
            "  padding: 0.4rem 0 0.2rem;",
            "  border-top: 1px solid rgba(142, 102, 49, 0.16);",
            "  border-bottom: 1px solid rgba(142, 102, 49, 0.16);",
            "}",
            "",
            ".adf-preview-manual-prologue p:last-child {",
            "  margin-bottom: 0;",
            "}",
            "",
            ".adf-preview-manual-step {",
            "  border-left: 6px solid rgba(142, 102, 49, 0.34);",
            "  background: linear-gradient(180deg, rgba(255, 251, 245, 0.98) 0%, rgba(255, 255, 255, 0.98) 100%);",
            "  border-radius: 1.1rem;",
            "  box-shadow: 0 16px 32px rgba(120, 90, 46, 0.08);",
            "  overflow: clip;",
            "}",
            "",
            ".adf-preview-manual-step[open] {",
            "  border-left-color: rgba(121, 84, 35, 0.58);",
            "  box-shadow: 0 20px 36px rgba(120, 90, 46, 0.14);",
            "}",
            "",
            ".adf-preview-manual-summary {",
            "  list-style: none;",
            "  display: flex;",
            "  justify-content: space-between;",
            "  gap: 1rem;",
            "  align-items: flex-start;",
            "  text-align: left;",
            "  cursor: pointer;",
            "  padding: 1.15rem 1.3rem;",
            "}",
            "",
            ".adf-preview-manual-summary::-webkit-details-marker {",
            "  display: none;",
            "}",
            "",
            ".adf-preview-manual-summary-copy {",
            "  display: grid;",
            "  gap: 0.4rem;",
            "  flex: 1 1 auto;",
            "  min-width: 0;",
            "}",
            "",
            ".adf-preview-manual-summary-title {",
            "  font-size: 1.2rem;",
            "  font-weight: 700;",
            "  color: #203039;",
            "}",
            "",
            ":root[data-theme='dark'] .adf-preview-manual-summary-title {",
            "  color: #f3f7fa;",
            "}",
            "",
            ".adf-preview-manual-summary-meta {",
            "  display: grid;",
            "  gap: 0.55rem;",
            "  justify-items: end;",
            "  flex: 0 0 auto;",
            "  align-self: flex-start;",
            "}",
            "",
            ".adf-preview-manual-summary-count,",
            ".adf-preview-manual-summary-meta > span {",
            "  display: inline-flex;",
            "  align-items: center;",
            "  justify-content: center;",
            "  border-radius: 999px;",
            "  padding: 0.38rem 0.75rem;",
            "  font-size: 0.78rem;",
            "  line-height: 1;",
            "}",
            "",
            ".adf-preview-manual-summary-count {",
            "  background: rgba(142, 102, 49, 0.10);",
            "  color: #7c5d2d;",
            "  border: 1px solid rgba(142, 102, 49, 0.16);",
            "}",
            "",
            ":root[data-theme='dark'] .adf-preview-manual-summary-count {",
            "  background: rgba(210, 176, 107, 0.14);",
            "  color: #f3d9a4;",
            "  border-color: rgba(210, 176, 107, 0.22);",
            "}",
            "",
            ".adf-preview-manual-step-body {",
            "  display: grid;",
            "  gap: 1rem;",
            "  justify-items: stretch;",
            "  text-align: left;",
            "  padding: 0 1.3rem 1.3rem;",
            "  border-top: 1px solid rgba(142, 102, 49, 0.14);",
            "}",
            "",
            ".adf-preview-manual-step-body > p {",
            "  max-width: 78ch;",
            "}",
            "",
            ".adf-preview-atlas-head {",
            "  display: grid;",
            "  grid-template-columns: minmax(0, 1fr) auto;",
            "  gap: 1rem;",
            "  align-items: end;",
            "}",
            "",
            ".adf-preview-atlas-metrics {",
            "  display: flex;",
            "  flex-wrap: wrap;",
            "  gap: 0.7rem;",
            "  justify-content: flex-end;",
            "}",
            "",
            ".adf-preview-atlas-metrics span {",
            "  border-radius: 999px;",
            "  background: rgba(24, 98, 130, 0.10);",
            "  border: 1px solid rgba(24, 98, 130, 0.14);",
            "  padding: 0.55rem 0.8rem;",
            "}",
            "",
            ".adf-preview-atlas-node.is-entry .adf-preview-atlas-node-link {",
            "  border-width: 2px;",
            "  border-color: rgba(24, 98, 130, 0.48);",
            "}",
            "",
            ".adf-preview-atlas-node.is-branch .adf-preview-atlas-node-link {",
            "  border-width: 2px;",
            "  border-color: rgba(189, 136, 54, 0.46);",
            "}",
            "",
            ".adf-preview-atlas-node.is-terminal .adf-preview-atlas-node-link {",
            "  border-width: 2px;",
            "  border-color: rgba(116, 128, 144, 0.42);",
            "}",
            "",
            ".adf-preview-console-topbar {",
            "  display: grid;",
            "  grid-template-columns: repeat(4, minmax(0, 1fr));",
            "  gap: 0.8rem;",
            "}",
            "",
            ".adf-preview-console-stat,",
            ".adf-preview-console-panel {",
            "  border-radius: 1rem;",
            "  background: linear-gradient(180deg, #10202c 0%, #172d3f 100%);",
            "  color: #e8f1f7;",
            "  border: 1px solid rgba(126, 170, 211, 0.22);",
            "  box-shadow: 0 24px 44px rgba(11, 19, 30, 0.28);",
            "  padding: 1rem;",
            "}",
            "",
            ".adf-preview-console-topbar strong,",
            ".adf-preview-console-panel strong,",
            ".adf-preview-console-panel .adf-panel-label,",
            ".adf-preview-console-panel .adf-inline-label,",
            ".adf-preview-console-panel .adf-check-label {",
            "  color: #eef5fb;",
            "}",
            "",
            ".adf-preview-console-grid {",
            "  display: grid;",
            "  grid-template-columns: 18rem minmax(0, 1.35fr) minmax(22rem, 1fr);",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-preview-console-signals,",
            ".adf-preview-console-actions {",
            "  display: grid;",
            "  gap: 0.8rem;",
            "  align-self: start;",
            "}",
            "",
            ".adf-preview-console-signal {",
            "  display: grid;",
            "  gap: 0.24rem;",
            "  text-decoration: none;",
            "  color: #eef5fb;",
            "  border-radius: 0.95rem;",
            "  padding: 0.9rem;",
            "  background: linear-gradient(180deg, rgba(17, 32, 44, 0.98) 0%, rgba(26, 46, 63, 0.98) 100%);",
            "  border: 1px solid rgba(126, 170, 211, 0.16);",
            "}",
            "",
            ".adf-preview-console-chipset {",
            "  display: flex;",
            "  flex-wrap: wrap;",
            "  gap: 0.45rem;",
            "}",
            "",
            ".adf-preview-console-feed {",
            "  display: grid;",
            "  gap: 0.8rem;",
            "}",
            "",
            ".adf-preview-console-step {",
            "  display: grid;",
            "  gap: 0.55rem;",
            "  border-radius: 0.95rem;",
            "  background: linear-gradient(180deg, rgba(20, 36, 50, 0.98) 0%, rgba(29, 52, 72, 0.98) 100%);",
            "  border: 1px solid rgba(126, 170, 211, 0.2);",
            "  padding: 1rem;",
            "}",
            "",
            ".adf-preview-console-step-head {",
            "  display: flex;",
            "  gap: 0.75rem;",
            "  align-items: center;",
            "}",
            "",
            ".adf-preview-console-action,",
            ".adf-preview-console-note,",
            ".adf-preview-console-fail,",
            ".adf-preview-console-pass,",
            ".adf-preview-console-panel p,",
            ".adf-preview-console-panel li {",
            "  margin: 0;",
            "  color: #bfd0dc;",
            "}",
            "",
            ".adf-preview-console-action-group {",
            "  display: grid;",
            "  gap: 0.7rem;",
            "  border-top: 1px solid rgba(126, 170, 211, 0.16);",
            "  padding-top: 0.8rem;",
            "}",
            "",
            ".adf-preview-console-evidence {",
            "  display: grid;",
            "  grid-template-columns: repeat(2, minmax(0, 1fr));",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-preview-manual-cover {",
            "  display: grid;",
            "  gap: 0.8rem;",
            "  padding: 1.4rem 1.5rem;",
            "}",
            "",
            ".adf-preview-manual-when {",
            "  max-width: 78ch;",
            "}",
            "",
            ".adf-preview-manual-contents {",
            "  border-top: 1px solid rgba(142, 102, 49, 0.16);",
            "  border-bottom: 1px solid rgba(142, 102, 49, 0.16);",
            "  padding: 0.9rem 0;",
            "}",
            "",
            ".adf-preview-manual-list {",
            "  list-style: none;",
            "  margin: 0;",
            "  padding: 0;",
            "  display: grid;",
            "  gap: 0.6rem;",
            "}",
            "",
            ".adf-preview-manual-list a {",
            "  display: flex;",
            "  gap: 0.9rem;",
            "  align-items: baseline;",
            "  text-decoration: none;",
            "  color: inherit;",
            "  border-bottom: 1px dashed rgba(142, 102, 49, 0.18);",
            "  padding-bottom: 0.55rem;",
            "}",
            "",
            ".adf-preview-manual-list span {",
            "  min-width: 4rem;",
            "  color: #8c6d3a;",
            "}",
            "",
            ".adf-preview-manual-kicker {",
            "  margin: 0;",
            "  letter-spacing: 0.16em;",
            "  text-transform: uppercase;",
            "  font-size: 0.78rem;",
            "  color: #8c6d3a;",
            "}",
            "",
            ":root[data-theme='dark'] .adf-preview-manual-kicker,",
            ":root[data-theme='dark'] .adf-preview-manual-list span {",
            "  color: #d6b77a;",
            "}",
            "",
            ".adf-preview-manual-action {",
            "  margin: 0;",
            "  font-size: 1.05rem;",
            "  color: #32434a;",
            "}",
            "",
            ":root[data-theme='dark'] .adf-preview-manual-action {",
            "  color: #d6e0e6;",
            "}",
            "",
            ".adf-preview-manual-callout {",
            "  display: grid;",
            "  gap: 0.7rem;",
            "  width: 100%;",
            "  max-width: none;",
            "  justify-self: stretch;",
            "  border-radius: 1rem;",
            "  border: 1px solid rgba(142, 102, 49, 0.16);",
            "  background: rgba(255, 251, 245, 0.98);",
            "  padding: 1rem;",
            "}",
            "",
            ".adf-preview-manual-branch {",
            "  display: grid;",
            "  gap: 0.35rem;",
            "  padding-left: 1rem;",
            "  border-left: 3px solid rgba(142, 102, 49, 0.22);",
            "}",
            "",
            ".adf-preview-manual-appendix {",
            "  display: grid;",
            "  grid-template-columns: repeat(2, minmax(0, 1fr));",
            "  gap: 1rem;",
            "}",
            "",
            ".adf-preview-manual-note {",
            "  border-left: 4px solid rgba(142, 102, 49, 0.34);",
            "  padding-left: 1rem;",
            "}",
            "",
            "@media (max-width: 60rem) {",
            "  .adf-home-topbar,",
            "  .adf-home-grid,",
            "  .adf-cockpit-topbar,",
            "  .adf-system-topbar,",
            "  .adf-cockpit-grid,",
            "  .adf-system-grid,",
            "  .adf-preview-atlas-head,",
            "  .adf-preview-console-grid,",
            "  .adf-preview-console-topbar,",
            "  .adf-preview-console-evidence,",
            "  .adf-preview-atlas-legend,",
            "  .adf-preview-manual-cover,",
            "  .adf-preview-manual-appendix {",
            "    grid-template-columns: 1fr;",
            "  }",
            "  .adf-preview-manual-summary {",
            "    grid-template-columns: 1fr;",
            "  }",
            "  .adf-preview-manual-summary-meta {",
            "    justify-items: start;",
            "  }",
            "  .adf-cockpit-nav,",
            "  .adf-system-nav {",
            "    position: static;",
            "  }",
            "  .adf-system-map-list {",
            "    grid-template-columns: 1fr;",
            "  }",
            "  .adf-preview-atlas-node-grid {",
            "    grid-template-columns: 1fr;",
            "  }",
            "  .adf-preview-atlas-node::after {",
            "    display: none;",
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
