from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from .runtime_baseline import (
    DEFAULT_ARTIFACT_ROOT,
    SUPPORT_BASELINE_NAME,
    TARGET_PROFILE_ARTIFACT_ROOT,
    derive_command_linux_note,
    derive_known_working_example,
)

PRIMARY_PLAYBOOK_ID = "ui-and-proxy"
STARLIGHT_SITE_PNPM_LOCK = (
    Path(__file__).resolve().parent / "assets" / "starlight-site-pnpm-lock.yaml"
)
CANONICAL_PLAYBOOK_TEMPLATE = {
    "template_id": "field-manual",
    "label": "Canonical Template",
    "summary": "Lab-validated ASMS frontline diagnostic steps.",
}
CANONICAL_PLAYBOOK_TEMPLATE_SLUG = "canonical-playbook-template"
FALLBACK_CANONICAL_PLAYBOOK = {
    "playbook_id": PRIMARY_PLAYBOOK_ID,
    "label": "ASMS UI is down",
    "symptom_focus": "Use this when the customer says the ASMS GUI is down, blank, or not usable.",
    "decision_rule": "Stay shallow first: host sanity, Apache/HTTPD, core services, first usable shell, then branch into the narrower workflow.",
    "likely_failing_services": ["httpd", "ms-metro", "keycloak"],
    "dependency_path": [
        {
            "step_id": "ui-and-proxy-step-1",
            "step_label": "Step 1",
            "label": "Check host pressure",
            "details": "Capture load, memory, and disk evidence first.",
        },
        {
            "step_id": "ui-and-proxy-step-2",
            "step_label": "Step 2",
            "label": "Check Apache and login page",
            "details": "Capture httpd, listeners, and login-page evidence.",
        },
        {
            "step_id": "ui-and-proxy-step-3",
            "step_label": "Step 3",
            "label": "Check core services",
            "details": "Check core services and restart only the failed one.",
        },
        {
            "step_id": "ui-and-proxy-step-4",
            "step_label": "Step 4",
            "label": "Check shell access",
            "details": "Check whether the session already reaches the first usable shell.",
        },
        {
            "step_id": "ui-and-proxy-step-5",
            "step_label": "Step 5",
            "label": "Check later workflow markers",
            "details": "Check whether the case already moved into reports, policy, or changes.",
        },
    ],
    "steps": [
        {
            "step_id": "ui-and-proxy-step-1",
            "step_label": "Step 1",
            "overview_summary": "Check host pressure first",
            "action": "Check host pressure.",
            "why_this_matters": "A lot of real GUI-down cases are still basic appliance health problems. If disk or memory is exhausted, deeper app checks are noise.",
            "recommended_commands": [
                {
                    "label": "Check host pressure",
                    "command": "uptime && free -h && df -h /",
                    "expected_signal": "Load is reasonable, memory is available, and the root filesystem is not full.",
                    "healthy_markers": ["load average", "Mem:", "Filesystem"],
                    "interpretation": "If load is high, memory is low, or disk is full, save the output and troubleshoot server pressure before checking the application.",
                    "example_output": "load average: 0.32, 0.41, 0.55\nMem: 16Gi 6.1Gi 4.1Gi 120Mi 5.5Gi 9.1Gi\n/dev/sda1 80G 31G 47G 40% /",
                }
            ],
            "if_pass": "Move to Apache/HTTPD and the login page.",
            "if_fail": "Treat host pressure as the first stop point and stabilize the appliance first.",
        },
        {
            "step_id": "ui-and-proxy-step-2",
            "step_label": "Step 2",
            "overview_summary": "Check Apache login route",
            "action": "Check Apache and login page.",
            "why_this_matters": "If Apache cannot answer the login route, there is no reason to start with auth or backend theory.",
            "recommended_commands": [
                {
                    "label": "Check Apache service, listeners, and login page",
                    "command": "systemctl is-active httpd && ss -lnt | grep -E ':(80|443)\\b' && curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'",
                    "expected_signal": "Apache is active, ports 80 and 443 are listening, and the login page returns an expected HTTP response.",
                    "healthy_markers": ["active", ":80", ":443", "HTTP/1.1 200"],
                    "interpretation": "If httpd is not active, ports 80 or 443 are missing, or the login page does not return HTTP 200, save the output and diagnose Apache/HTTPD.",
                    "example_output": "active\nLISTEN 0 511 0.0.0.0:443 0.0.0.0:*\nLISTEN 0 511 0.0.0.0:80 0.0.0.0:*\nHTTP/1.1 200 OK",
                }
            ],
            "if_pass": "Move to the shallow core services only if the login page still does not explain the case.",
            "if_fail": "Treat Apache/HTTPD or the UI edge route as the first stop point.",
        },
        {
            "step_id": "ui-and-proxy-step-3",
            "step_label": "Step 3",
            "overview_summary": "Check shallow core services",
            "action": "Check core services.",
            "why_this_matters": "This keeps the engineer on practical service checks instead of deep architecture. Restart only the service that actually failed.",
            "recommended_commands": [
                {
                    "label": "Check the shallow core services once",
                    "command": "systemctl is-active httpd; systemctl is-active ms-metro; systemctl is-active keycloak",
                    "expected_signal": "The shallow services are active. If one is inactive, that is the current stop point.",
                    "healthy_markers": ["active"],
                    "interpretation": "If one service is not active, save the service name and status. Diagnose or restart only that service.",
                    "example_output": "active\nactive\nactive",
                },
                {
                    "label": "Restart Apache only if Apache failed",
                    "command": "sudo systemctl restart httpd.service && sleep 5 && systemctl is-active httpd.service && curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'",
                    "expected_signal": "Apache returns to active and the login page answers again.",
                    "healthy_markers": ["active", "HTTP/1.1 200"],
                    "interpretation": "Run this only if Apache failed in the previous check.",
                    "example_output": "active\nHTTP/1.1 200 OK",
                },
                {
                    "label": "Restart Metro only if the shell is blank or partly loaded",
                    "command": "sudo systemctl restart ms-metro.service && sleep 10 && systemctl is-active ms-metro.service && curl -sS http://127.0.0.1:8080/afa/getStatus --max-time 10",
                    "expected_signal": "Metro returns to active and the heartbeat answers.",
                    "healthy_markers": ["active", "\"isAlive\" : true"],
                    "interpretation": "Run this only if the login page works but the shell is blank, partial, or not loading correctly.",
                    "example_output": "active\n{\n  \"isAlive\" : true\n}",
                }
            ],
            "if_pass": "Move to the first usable shell check.",
            "if_fail": "Name the failed shallow service directly and stop there until it recovers or clearly proves healthy.",
        },
        {
            "step_id": "ui-and-proxy-step-4",
            "step_label": "Step 4",
            "overview_summary": "Check first usable shell",
            "action": "Check shell access.",
            "why_this_matters": "If the customer can already reach the login page or home shell, the top-level UI path is doing useful work and the case needs a narrower label.",
            "recommended_commands": [
                {
                    "label": "Check the login page and home-shell clues",
                    "command": "curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'; echo '---'; grep -E '/afa/php/SuiteLoginSessionValidation.php|/afa/php/home.php' /var/log/httpd/ssl_access_log | tail -n 20",
                    "expected_signal": "The login page answers, and recent log lines show whether the session ever reached SuiteLoginSessionValidation or /afa/php/home.php.",
                    "healthy_markers": ["HTTP/1.1 200", "SuiteLoginSessionValidation.php", "/afa/php/home.php"],
                    "interpretation": "If the login page answers or /afa/php/home.php appears, save that evidence and continue with shell or workflow diagnosis.",
                    "example_output": "HTTP/1.1 200 OK\n---\n127.0.0.1 - - [28/Mar/2026:19:27:29 -0400] \"GET /afa/php/home.php?segment=DEVICES HTTP/1.1\" 200 328934",
                }
            ],
            "if_pass": "Branch out of GUI down into the narrower workflow the customer is actually in.",
            "if_fail": "If the shell is still not usable, keep the stop point on the first shell boundary before widening further.",
        },
        {
            "step_id": "ui-and-proxy-step-5",
            "step_label": "Step 5",
            "overview_summary": "Check later branch markers",
            "action": "Check later workflow markers.",
            "why_this_matters": "This is the clean branch-out rule. If later content is already visible, support should stop treating the case as GUI down.",
            "recommended_commands": [
                {
                    "label": "Look for later content markers",
                    "command": "grep -E '/fa/tree/create|/afa/php/commands.php\\?cmd=(GET_REPORTS|GET_POLICY_TAB|GET_DEVICE_POLICY|GET_MONITORING_CHANGES|GET_ANALYSIS_OPTIONS)' /var/log/httpd/ssl_access_log | tail -n 40",
                    "expected_signal": "Recent Apache lines show device-tree activity plus a later content marker like GET_REPORTS, GET_POLICY_TAB, or GET_MONITORING_CHANGES.",
                    "healthy_markers": ["/fa/tree/create", "GET_REPORTS", "GET_POLICY_TAB", "GET_DEVICE_POLICY", "GET_MONITORING_CHANGES", "GET_ANALYSIS_OPTIONS"],
                    "interpretation": "If one of these markers appears, save the marker and continue with the matching workflow diagnosis.",
                    "example_output": "127.0.0.1 - - [28/Mar/2026:19:27:30 -0400] \"GET /afa/php/commands.php?cmd=GET_REPORTS HTTP/1.1\" 200 99",
                }
            ],
            "if_pass": "Move to the matching workflow playbook or targeted service diagnosis for that later branch.",
            "if_fail": "If no later marker appears and the shell is still not usable, keep the stop point on the first usable shell boundary.",
        },
    ],
}
FALLBACK_CANONICAL_SYMPTOMS = [
    {"symptom_label": "Suite login redirects but the operator still cannot do useful work."},
    {"symptom_label": "UI shell appears, but the first app action stalls immediately."},
    {"symptom_label": "Support needs one bounded route to prove where useful work stops."},
]
KEYCLOAK_PLAYBOOK = {
    "playbook_id": "keycloak-auth",
    "label": "ASMS Keycloak auth is down",
    "symptom_focus": "Use this when the login page still opens but ASMS auth looks down, loops, or returns an auth error.",
    "decision_rule": "If Apache still serves the login page, keep the stop point on Keycloak until the service, listener, and OIDC path prove healthy again.",
    "imported_module_drilldown": {
        "observed_boundary_on_appliance": [
            "Apache can still serve `https://127.0.0.1/algosec-ui/login` while the proxied Keycloak OIDC path is unhealthy.",
            "Keycloak service state, listener `8443`, and the OIDC well-known probe together define whether the auth module can still do useful work.",
            "Use current appliance evidence first. In the validated March 30, 2026 slice on `10.167.2.150`, the login page stayed `200`, the Keycloak OIDC path returned `503`, `keycloak.service` was failed, `8443` was absent, and Metro still reported `isAlive: true`.",
        ],
        "what_that_boundary_means_in_asms": [
            "The browser-facing UI edge is still alive enough to serve the login page, so this is not yet a top-level Apache outage.",
            "Keycloak sits behind Apache as the imported auth module boundary for this path. If the login page works but the OIDC path does not, keep the case on Keycloak before widening into unrelated services.",
            "Metro can help separate auth failure from deeper app failure, but a healthy Metro heartbeat does not make Keycloak healthy again.",
        ],
        "generic_failure_classes": [
            {
                "label": "startup_failure",
                "details": "Use this when `keycloak.service` exits, flaps, or never reaches `active`. Journal and service-status clues belong here."
            },
            {
                "label": "listener_absent",
                "details": "Use this when the expected local Keycloak listener on `8443` is missing even though Apache still points there."
            },
            {
                "label": "useful_work_path_failed",
                "details": "Use this when the service may look present but the OIDC path still fails, loops, or returns unhealthy HTTP while the login page still loads."
            },
            {
                "label": "apache_proxy_mismatch",
                "details": "Use this when `/keycloak/` is no longer mapped to `https://localhost:8443/` or the proxy path itself drifted."
            },
            {
                "label": "dependency_or_resource_unknown",
                "details": "Use this when the Keycloak boundary is proven but the current slice still cannot tell whether the real cause is config, filesystem, secret, database, or host pressure."
            },
        ],
        "bounded_next_checks": [
            "Classify the module first: service state, listener state, OIDC useful-work check, and proxy path.",
            "Keep the next support step on the smallest failing Keycloak boundary instead of widening back into Apache or later ASMS modules too early.",
            "If the boundary is still unresolved after the shallow checks, gather the escalation packet and only then branch into deeper module-specific interpretation.",
        ],
        "escalation_ready_evidence": [
            "`systemctl status keycloak.service --no-pager` and `systemctl show keycloak.service ...` output",
            "Listener output for `8443`",
            "The paired login-page and OIDC probe outputs from the same troubleshooting minute",
            "Apache proxy evidence showing whether `/keycloak/` still maps to `https://localhost:8443/`",
            "Recent Keycloak journal lines that show the startup or runtime clue",
            "Any supporting separation clue such as Metro heartbeat when the customer reports a broader UI symptom",
        ],
        "upstream_references": [
            {
                "label": "Keycloak documentation",
                "url": "https://www.keycloak.org/documentation",
                "details": "Use this after the appliance evidence proves the Keycloak boundary and you need bounded interpretation of Keycloak server behavior."
            },
            {
                "label": "Keycloak server configuration guide",
                "url": "https://www.keycloak.org/server/configuration",
                "details": "Use this for deeper configuration or startup interpretation only after the local service and listener checks narrow the failure class."
            },
        ],
    },
    "dependency_path": [
        {
            "step_id": "keycloak-step-1",
            "step_label": "Step 1",
            "label": "Check login page and OIDC path",
            "details": "Compare the UI shell with the Keycloak OIDC well-known path.",
        },
        {
            "step_id": "keycloak-step-2",
            "step_label": "Step 2",
            "label": "Check Keycloak service",
            "details": "Check service state and the local 8443 listener.",
        },
        {
            "step_id": "keycloak-step-3",
            "step_label": "Step 3",
            "label": "Check Apache proxy",
            "details": "Confirm Apache still proxies /keycloak/ to localhost:8443.",
        },
        {
            "step_id": "keycloak-step-4",
            "step_label": "Step 4",
            "label": "Check failure clues",
            "details": "Read the recent Keycloak startup and service clues.",
        },
        {
            "step_id": "keycloak-step-5",
            "step_label": "Step 5",
            "label": "Restart Keycloak",
            "details": "Restart only if the service is actually down or failed.",
        },
    ],
    "steps": [
        {
            "step_id": "keycloak-step-1",
            "step_label": "Step 1",
            "overview_summary": "Check login and OIDC",
            "action": "Check the login page and the Keycloak OIDC path together.",
            "recommended_commands": [
                {
                    "label": "Compare login page and Keycloak OIDC",
                    "command": "curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'; echo '---'; curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration | sed -n '1,12p'",
                    "expected_signal": "The login page returns HTTP 200 and the Keycloak OIDC path also returns HTTP 200.",
                    "healthy_markers": ["HTTP/1.1 200"],
                    "interpretation": "If the login page is still HTTP 200 but the Keycloak OIDC path returns 503 or another failure, save both outputs and diagnose Keycloak instead of Apache.",
                    "example_output": "HTTP/1.1 200 OK\n---\nHTTP/1.1 200 OK",
                }
            ],
        },
        {
            "step_id": "keycloak-step-2",
            "step_label": "Step 2",
            "overview_summary": "Check service and listener",
            "action": "Check Keycloak service state and the local 8443 listener.",
            "recommended_commands": [
                {
                    "label": "Check Keycloak service and 8443 listener",
                    "command": "systemctl status keycloak.service --no-pager; echo '--- listeners ---'; ss -lntp | grep -E ':(8443)\\b'",
                    "expected_signal": "Keycloak is active and a Java process is listening on port 8443.",
                    "healthy_markers": ["Active: active (running)", "LISTEN", ":8443"],
                    "interpretation": "If keycloak.service is failed or 8443 is missing, keep the stop point on Keycloak.",
                    "example_output": "● keycloak.service - Keycloak Service\n   Active: active (running)\n--- listeners ---\nLISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:((\"java\",pid=2745,fd=91))",
                }
            ],
        },
        {
            "step_id": "keycloak-step-3",
            "step_label": "Step 3",
            "overview_summary": "Check Apache proxy",
            "action": "Check the Apache proxy path for Keycloak.",
            "recommended_commands": [
                {
                    "label": "Check Apache Keycloak proxy config",
                    "command": "grep -R -n -E '<Location /keycloak/|ProxyPass https://localhost:8443/|ProxyPassReverse https://localhost:8443/' /etc/httpd/conf.d 2>/dev/null",
                    "expected_signal": "Apache still exposes /keycloak/ and proxies it to https://localhost:8443/.",
                    "healthy_markers": ["<Location /keycloak/>", "ProxyPass https://localhost:8443/", "ProxyPassReverse https://localhost:8443/"],
                    "interpretation": "If these proxy lines are missing, save the output and diagnose Apache Keycloak proxy configuration before going deeper into the service.",
                    "example_output": "/etc/httpd/conf.d/keycloak.conf:1:<Location /keycloak/>\n/etc/httpd/conf.d/keycloak.conf:2:        ProxyPass https://localhost:8443/ timeout=300\n/etc/httpd/conf.d/keycloak.conf:3:        ProxyPassReverse https://localhost:8443/",
                }
            ],
        },
        {
            "step_id": "keycloak-step-4",
            "step_label": "Step 4",
            "overview_summary": "Check failure clues",
            "action": "Check recent failure clues from the service journal.",
            "recommended_commands": [
                {
                    "label": "Check recent Keycloak journal clues",
                    "command": "journalctl -u keycloak.service -n 80 --no-pager",
                    "expected_signal": "Recent lines show Keycloak starting normally or show the failure clue that explains why it did not come up.",
                    "healthy_markers": ["started", "Listening on", "8443"],
                    "interpretation": "If you see repeated startup failures such as java.io.EOFException or exit-code failure, save the output and keep the case on the Keycloak service boundary.",
                    "example_output": "Exception in thread \"main\" java.lang.reflect.UndeclaredThrowableException\nCaused by: java.io.EOFException\n... SerializedApplication.read(...)\n... QuarkusEntryPoint.doRun(...)\nkeycloak.service: Main process exited, status=1/FAILURE",
                }
            ],
        },
        {
            "step_id": "keycloak-step-5",
            "step_label": "Step 5",
            "overview_summary": "Restart Keycloak only if down",
            "action": "Restart Keycloak only when the service is down or failed.",
            "recommended_commands": [
                {
                    "label": "Restart Keycloak and recheck auth",
                    "command": "sudo systemctl restart keycloak.service && sleep 30 && systemctl is-active keycloak.service && ss -lntp | grep -E ':(8443)\\b' && curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration | sed -n '1,12p'",
                    "expected_signal": "Keycloak returns to active, 8443 is listening again, and the OIDC path returns HTTP 200.",
                    "healthy_markers": ["active", "LISTEN", ":8443", "HTTP/1.1 200"],
                    "interpretation": "If the service still fails, 8443 does not return, or the OIDC path stays unhealthy, save all output and keep the case on Keycloak.",
                    "example_output": "active\nLISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:((\"java\",pid=2745,fd=91))\nHTTP/1.1 200 OK",
                }
            ],
        },
    ],
}
KEYCLOAK_PLAYBOOK_SLUG = "asms-keycloak-auth-is-down"
CORE_AFF_PLAYBOOK_SUPPLEMENT = {
    "imported_module_drilldown": {
        "intro": "Use this page to prove the FireFlow backend boundary first, separate Apache route ownership from aff-boot runtime health, and gather a support-ready evidence packet before widening into later workflow or broker theory.",
        "observed_boundary_on_appliance": [
            "Apache owns the newer FireFlow session edge and proxies `/FireFlow/api` and `/aff/api` into aff-boot on `1989`.",
            "The closest readable backend seam for this path is aff-boot plus its direct route ownership, not generic FireFlow workflow theory.",
            "Current lab evidence keeps PostgreSQL closer than ActiveMQ for first-pass troubleshooting even though aff-boot can also hold live broker sockets on `61616`.",
        ],
        "what_that_boundary_means_in_asms": [
            "If the Apache-fronted FireFlow session path and the direct `1989` AFF session path disagree, stop on Apache proxying or aff-boot route ownership before widening.",
            "If the routes match but the action still fails, the next support seam is the FireFlow session or config boundary, not a generic broker-first guess.",
            "Treat ActiveMQ as later supporting evidence unless the same failing minute points directly at broker-side behavior.",
        ],
        "generic_failure_classes": [
            {
                "label": "route_proxy_mismatch",
                "details": "Use this when `/FireFlow/api` no longer matches the direct `1989` AFF session path or Apache route ownership drifted."
            },
            {
                "label": "aff_boot_unhealthy",
                "details": "Use this when `aff-boot.service` is down, flapping, or not holding the expected `1989` listener."
            },
            {
                "label": "session_parity_drift",
                "details": "Use this when the Apache-fronted session path and the direct AFF session path stop returning the same invalid-session or session-shape response."
            },
            {
                "label": "downstream_config_refresh",
                "details": "Use this when the same failing minute rolls into `ms-configuration`, swagger refresh, or downstream `502` clues after the FireFlow route itself still looks healthy."
            },
            {
                "label": "later_broker_or_database_supporting",
                "details": "Use this when route ownership and aff-boot look healthy but the current evidence starts pointing at PostgreSQL or broker-side supporting dependencies."
            },
        ],
        "bounded_next_checks": [
            "Prove Apache-fronted `/FireFlow/api/session` parity against the direct `1989` AFF session path first.",
            "Check `aff-boot.service`, the `1989` listener, and PostgreSQL state before widening into later FireFlow workflow theory.",
            "Only promote ActiveMQ when the same failing minute points directly at broker-side evidence instead of route or service ownership.",
        ],
        "escalation_ready_evidence": [
            "The exact failing FireFlow action, route, or screen",
            "Visible status for `aff-boot.service` and `postgresql.service`",
            "Apache-fronted and direct `1989` session probe outputs from the same troubleshooting minute",
            "Same-minute Apache, FireFlow, or `ms-configuration` lines that show where the route stops doing useful work",
        ],
    }
}
PLAYBOOK_SUPPLEMENTS = {
    "keycloak-auth": KEYCLOAK_PLAYBOOK,
    "core-aff": CORE_AFF_PLAYBOOK_SUPPLEMENT,
}


def generate_starlight_site(
    *,
    project_root: Path,
    artifact_root: str | Path | None = None,
    site_root: str | Path | None = None,
) -> dict[str, Any]:
    baseline_root = project_root / _default_starlight_artifact_root(project_root, artifact_root)
    support_baseline_path = baseline_root / SUPPORT_BASELINE_NAME
    support_baseline = json.loads(support_baseline_path.read_text(encoding="utf-8"))

    output_root = project_root / Path(site_root) if site_root else baseline_root / "starlight-site"
    docs_root = output_root / "src" / "content" / "docs"
    playbooks_root = docs_root / "playbooks"
    guides_root = docs_root / "guides"
    template_lab_root = docs_root / "template-lab"
    canonical_template_path = docs_root / f"{CANONICAL_PLAYBOOK_TEMPLATE_SLUG}.md"
    for stale_path in (
        output_root / ".astro",
        output_root / "dist",
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
    if guides_root.exists():
        shutil.rmtree(guides_root)
    if template_lab_root.exists():
        shutil.rmtree(template_lab_root)
    for stale_doc in docs_root.glob("*.md"):
        if stale_doc.name not in {"index.md"}:
            stale_doc.unlink()

    symptom_lookup = _symptoms_by_playbook(support_baseline)
    page_records_by_id = _page_records_by_id(support_baseline)
    primary_playbook: dict[str, Any] | None = None
    for playbook in support_baseline.get("decision_playbooks", []):
        if playbook.get("playbook_id") == PRIMARY_PLAYBOOK_ID:
            primary_playbook = playbook

    if primary_playbook is None:
        decision_playbooks = support_baseline.get("decision_playbooks", [])
        primary_playbook = decision_playbooks[0] if decision_playbooks else FALLBACK_CANONICAL_PLAYBOOK

    canonical_template_entry: dict[str, str | int] | None = {
        "label": str(CANONICAL_PLAYBOOK_TEMPLATE["label"]),
        "slug": CANONICAL_PLAYBOOK_TEMPLATE_SLUG,
        "relative_path": f"src/content/docs/{CANONICAL_PLAYBOOK_TEMPLATE_SLUG}.md",
        "order": 1,
    }
    canonical_template_path.write_text(
        _render_canonical_playbook_template_markdown(),
        encoding="utf-8",
    )
    supplemental_boundary_playbooks = _supplemental_boundary_playbooks(page_records_by_id)
    keycloak_page_record = page_records_by_id.get("keycloak-auth")
    keycloak_playbook = supplemental_boundary_playbooks.get(
        "keycloak-auth",
        _merge_page_record_into_playbook(
            KEYCLOAK_PLAYBOOK,
            keycloak_page_record,
        ),
    )

    playbook_nav_entries: list[dict[str, str | int]] = []
    rendered_playbooks = support_baseline.get("decision_playbooks", []) or (
        [primary_playbook] if primary_playbook is not None else []
    )
    for order, playbook in enumerate(rendered_playbooks, start=1):
        page_record = _page_record_for_playbook(playbook, page_records_by_id)
        rendered_playbook = _apply_playbook_supplement(playbook, _supplement_for_page_record(page_record))
        playbook_slug = _playbook_slug(rendered_playbook)
        playbook_path = playbooks_root / f"{playbook_slug}.md"
        playbook_path.parent.mkdir(parents=True, exist_ok=True)
        playbook_path.write_text(
            _render_playbook_markdown(
                playbook=rendered_playbook,
                order=order,
                symptom_entries=symptom_lookup.get(playbook["playbook_id"], []) or FALLBACK_CANONICAL_SYMPTOMS,
                page_record=page_record,
            ),
            encoding="utf-8",
        )
        playbook_nav_entries.append(
            {
                "label": str(rendered_playbook["label"]),
                "slug": f"playbooks/{playbook_slug}",
                "relative_path": str(playbook_path.relative_to(project_root)),
                "order": order,
                "playbook_id": str(playbook["playbook_id"]),
            }
        )

    rendered_page_ids = {str(entry["playbook_id"]) for entry in playbook_nav_entries}
    generated_boundary_records = [
        page_record
        for page_record in page_records_by_id.values()
        if page_record.get("page_type") == "boundary_confirmation"
        and str(page_record.get("page_id") or "") not in rendered_page_ids
    ]
    for page_record in generated_boundary_records:
        order = len(playbook_nav_entries) + 1
        playbook_slug = _page_record_slug(page_record)
        playbook_path = playbooks_root / f"{playbook_slug}.md"
        playbook_path.parent.mkdir(parents=True, exist_ok=True)
        supplemental_playbook = supplemental_boundary_playbooks.get(str(page_record.get("page_id") or ""))
        playbook_path.write_text(
            _render_boundary_page_markdown(
                page_record=page_record,
                order=order,
                supplemental_playbook=supplemental_playbook,
            ),
            encoding="utf-8",
        )
        playbook_nav_entries.append(
            {
                "label": str(page_record.get("label") or page_record.get("page_id") or "Generated page"),
                "slug": f"playbooks/{playbook_slug}",
                "relative_path": str(playbook_path.relative_to(project_root)),
                "order": order,
                "playbook_id": str(page_record.get("page_id") or playbook_slug),
            }
        )
        rendered_page_ids.add(str(page_record.get("page_id") or ""))

    guide_nav_entries: list[dict[str, str | int]] = []
    generated_guide_records = [
        page_record
        for page_record in page_records_by_id.values()
        if page_record.get("page_type") == "deep_guide"
    ]
    for page_record in generated_guide_records:
        guide_slug = f"guides/{_page_record_slug(page_record)}"
        guide_path = guides_root / f"{_page_record_slug(page_record)}.md"
        guide_path.parent.mkdir(parents=True, exist_ok=True)
        guide_path.write_text(
            _render_generated_page_record_markdown(page_record=page_record, order=len(guide_nav_entries) + 1),
            encoding="utf-8",
        )
        guide_nav_entries.append(
            {
                "label": str(page_record.get("label") or page_record.get("page_id") or "Generated guide"),
                "slug": guide_slug,
                "relative_path": str(guide_path.relative_to(project_root)),
                "order": len(guide_nav_entries) + 1,
            }
        )

    for guide_entry in _related_guides_for_page_record(keycloak_page_record):
        order = len(guide_nav_entries) + 1
        rendered_guide = _render_authored_guide_markdown(
            guide_entry=guide_entry,
            order=order,
            page_record=keycloak_page_record,
            playbook=keycloak_playbook,
        )
        if rendered_guide is None:
            continue
        guide_slug = str(guide_entry.get("slug") or "")
        guide_name = Path(guide_slug).name if guide_slug else f"guide-{order}"
        guide_path = guides_root / f"{guide_name}.md"
        guide_path.parent.mkdir(parents=True, exist_ok=True)
        guide_path.write_text(rendered_guide, encoding="utf-8")
        guide_nav_entries.append(
            {
                "label": str(guide_entry.get("label") or guide_name),
                "slug": guide_slug or f"guides/{guide_name}",
                "relative_path": str(guide_path.relative_to(project_root)),
                "order": order,
                "summary": str(guide_entry.get("summary") or ""),
                "detail": str(guide_entry.get("detail") or ""),
            }
        )

    (docs_root / "index.md").write_text(
        _render_index_markdown(
            support_baseline,
            canonical_template_entry,
            playbook_nav_entries,
            guide_nav_entries,
        ),
        encoding="utf-8",
    )
    (output_root / "package.json").write_text(_render_package_json(), encoding="utf-8")
    (output_root / "pnpm-lock.yaml").write_text(STARLIGHT_SITE_PNPM_LOCK.read_text(encoding="utf-8"), encoding="utf-8")
    (output_root / "astro.config.mjs").write_text(
        _render_astro_config(canonical_template_entry, playbook_nav_entries, guide_nav_entries),
        encoding="utf-8",
    )
    (output_root / "tsconfig.json").write_text(_render_tsconfig(), encoding="utf-8")
    (output_root / "src" / "content.config.ts").parent.mkdir(parents=True, exist_ok=True)
    (output_root / "src" / "content.config.ts").write_text(_render_content_config(), encoding="utf-8")
    (output_root / "src" / "custom.css").write_text(_render_custom_css(), encoding="utf-8")
    (output_root / "public").mkdir(parents=True, exist_ok=True)
    (output_root / "public" / "adf-field-manual.js").write_text(_render_field_manual_script(), encoding="utf-8")

    generated_files = [
        str((output_root / "package.json").relative_to(project_root)),
        str((output_root / "astro.config.mjs").relative_to(project_root)),
        str((output_root / "tsconfig.json").relative_to(project_root)),
        str((output_root / "src" / "content.config.ts").relative_to(project_root)),
        str((output_root / "src" / "custom.css").relative_to(project_root)),
        str((output_root / "public" / "adf-field-manual.js").relative_to(project_root)),
        str((docs_root / "index.md").relative_to(project_root)),
        str((output_root / "pnpm-lock.yaml").relative_to(project_root)),
    ]
    generated_files.append(str(canonical_template_path.relative_to(project_root)))
    for entry in playbook_nav_entries:
        generated_files.append(str(entry["relative_path"]))
    for entry in guide_nav_entries:
        generated_files.append(str(entry["relative_path"]))

    return {
        "status": "pass",
        "artifact_root": str(output_root.relative_to(project_root)),
        "generated_files": generated_files,
        "summary": {
            "playbook_count": len(playbook_nav_entries),
            "guide_count": len(guide_nav_entries),
            "canonical_template": CANONICAL_PLAYBOOK_TEMPLATE["template_id"],
            "symptom_count": len(support_baseline.get("symptom_lookup", [])),
            "source_artifact": str(support_baseline_path.relative_to(project_root)),
        },
    }


def _default_starlight_artifact_root(project_root: Path, artifact_root: str | Path | None) -> Path:
    if artifact_root is not None:
        return Path(artifact_root)

    target_profile_candidate = project_root / TARGET_PROFILE_ARTIFACT_ROOT / SUPPORT_BASELINE_NAME
    if target_profile_candidate.exists():
        return TARGET_PROFILE_ARTIFACT_ROOT
    return DEFAULT_ARTIFACT_ROOT


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


def _render_astro_config(
    canonical_template_entry: dict[str, str | int] | None,
    playbook_nav_entries: list[dict[str, str | int]],
    guide_nav_entries: list[dict[str, str | int]],
) -> str:
    canonical_sidebar = (
        "{\n        label: 'Canonical Template',\n        items: [\n          { label: "
        + json.dumps(str(canonical_template_entry["label"]))
        + ", slug: "
        + json.dumps(str(canonical_template_entry["slug"]))
        + " }\n        ],\n      }"
        if canonical_template_entry
        else "{\n        label: 'Canonical Template',\n        items: [],\n      }"
    )
    if playbook_nav_entries:
        playbook_items = ",\n".join(
            [
                "          { label: "
                + json.dumps(str(entry["label"]))
                + ", slug: "
                + json.dumps(str(entry["slug"]))
                + " }"
                for entry in playbook_nav_entries
            ]
        )
        playbook_sidebar = "{\n        label: 'Playbooks',\n        items: [\n" + playbook_items + "\n        ],\n      }"
    else:
        playbook_sidebar = "{\n        label: 'Playbooks',\n        items: [],\n      }"
    if guide_nav_entries:
        guide_items = ",\n".join(
            [
                "          { label: "
                + json.dumps(str(entry["label"]))
                + ", slug: "
                + json.dumps(str(entry["slug"]))
                + " }"
                for entry in guide_nav_entries
            ]
        )
        guide_sidebar = "{\n        label: 'Guides',\n        items: [\n" + guide_items + "\n        ],\n      }"
    else:
        guide_sidebar = "{\n        label: 'Guides',\n        items: [],\n      }"
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
        "      head: [\n"
        "        {\n"
        "          tag: 'script',\n"
        "          attrs: { type: 'module', src: '/adf-field-manual.js' },\n"
        "        },\n"
        "      ],\n"
        "      tableOfContents: false,\n"
        "      sidebar: [\n"
        "        {\n"
        "          label: 'Start Here',\n"
        "          items: [{ label: 'Overview', slug: 'index' }],\n"
        "        },\n"
        f"        {playbook_sidebar},\n"
        f"        {guide_sidebar},\n"
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
    playbook_nav_entries: list[dict[str, str | int]],
    guide_nav_entries: list[dict[str, str | int]],
) -> str:
    observed = support_baseline.get("observed", {})
    service_summary = observed.get("service_summary", {})
    runtime_identity = observed.get("runtime_identity", {})
    os_release = runtime_identity.get("os_release", {})
    page_records = support_baseline.get("page_records", [])
    symptoms = support_baseline.get("symptom_lookup", [])
    first_response_steps = support_baseline.get("first_response_steps", [])
    canonical_target = f'/{canonical_template_entry["slug"]}/' if canonical_template_entry else "/"
    primary_nav_entry = _primary_nav_entry(playbook_nav_entries)
    primary_target = f'/{primary_nav_entry["slug"]}/' if primary_nav_entry else "/"
    published_playbook_count = len(playbook_nav_entries)
    published_guide_count = len(guide_nav_entries)
    playbook_cards = "".join(_home_card_for_playbook_entry(entry, primary_nav_entry) for entry in playbook_nav_entries)
    guide_cards = "".join(_home_card_for_guide_entry(entry) for entry in guide_nav_entries)

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
        "Open the live playbook first. Use the canonical template only as a reusable shell.",
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
        "## Start here",
        "",
        '<div class="adf-home-grid">',
        '  <div class="adf-panel">',
        '    <p class="adf-panel-label">Operator route</p>',
        "    <ul>",
    ]
    lines.extend([f"      <li>{step}</li>" for step in first_response_steps])
    lines.extend(
        [
            "    </ul>",
            "  </div>",
            '  <div class="adf-panel">',
            '    <p class="adf-panel-label">Build rule</p>',
            "    <ul>",
            "      <li>Keep the real troubleshooting steps in the playbook routes.</li>",
            "      <li>Keep placeholders in the canonical template only.</li>",
            "      <li>Use one page grammar across future playbooks.</li>",
            "    </ul>",
            "  </div>",
            "</div>",
        "",
        "## Published pages",
        "",
        '<div class="adf-home-card-grid">',
        f'<a class="adf-home-card" href="{canonical_target}">',
        '  <p class="adf-panel-label">Template</p>',
        '  <strong>Canonical ADF playbook shell</strong>',
        '  <span>Reference shell only. Keep placeholders here.</span>',
        '  <span class="adf-home-card-list">Open the template for page structure.</span>',
        "</a>",
        playbook_cards,
        guide_cards,
        "</div>",
        "",
        "## Catalog status",
            "",
            '<div class="adf-home-grid">',
            '  <div class="adf-panel">',
            '    <p class="adf-panel-label">Published catalog</p>',
        f"    <p>{published_playbook_count} playbook{'s are' if published_playbook_count != 1 else ' is'} and {published_guide_count} guide{'s are' if published_guide_count != 1 else ' is'} currently published from the new shell.</p>",
            "  </div>",
            '  <div class="adf-panel">',
            '    <p class="adf-panel-label">Next build rule</p>',
            "    <p>Build new playbooks from the canonical template and keep the generated page-record layer behind the scenes so the operator catalog stays cleaner.</p>",
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


def _render_canonical_playbook_template_markdown() -> str:
    title_value = json.dumps("Canonical Playbook Template")
    description_value = json.dumps("Placeholder shell for future ADF diagnostic playbooks.")
    lines = [
        "---",
        f"title: {title_value}",
        f"description: {description_value}",
        "sidebar:",
        f"  label: {json.dumps(str(CANONICAL_PLAYBOOK_TEMPLATE['label']))}",
        "  order: 1",
        "---",
        "",
        "# Canonical Playbook Template",
        "",
        "Placeholder page only.",
        "",
        "Do not put real ASMS troubleshooting content here.",
        "",
        "## Placeholders",
        "",
        "- `<Playbook title>`",
        "- `Check <surface>`",
        "- `Run`",
        "- `Expected result`",
        "- `Check output for`",
        "- `If result is different`",
        "- `Example`",
        "",
        "## Writing rules",
        "",
        "- use short verb-based check names",
        "- use direct support language",
        "- keep placeholders obvious",
        "- move real troubleshooting content into a playbook route",
        "",
        "## Live example",
        "",
        "Use the real `ASMS UI is down` playbook under `/playbooks/asms-ui-is-down/` as the working example built from this shell.",
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
    return _render_template_field_manual(
        playbook=playbook,
        symptom_entries=symptom_entries,
        anchor_prefix="",
    )


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
        label = _step_navigation_label(step, dependency_item)
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
                f"  <strong>{_step_navigation_label(step)}</strong>",
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
    anchor_prefix: str = "",
) -> str:
    dependency_path = playbook.get("dependency_path", [])
    dependency_by_step = {item["step_id"]: item for item in dependency_path}
    del symptom_entries
    lines = [
        '<div class="adf-preview-shell adf-preview-field-manual">',
        '  <section class="adf-preview-manual-cover">',
        f"    <h2>{playbook['label']}</h2>",
        "  </section>",
        '  <section class="adf-preview-manual-contents">',
        '    <p class="adf-panel-label">Steps</p>',
        '    <ol class="adf-preview-manual-list">',
    ]
    for step in playbook.get("steps", []):
        lines.extend(
            [
                f'<li><a class="adf-preview-manual-link" href="{anchor_prefix}#manual-{step["step_id"]}" data-adf-manual-target="manual-{step["step_id"]}"><span>{step["step_label"]}</span><strong>{_step_navigation_label(step)}</strong></a></li>'
            ]
        )
    lines.extend(
        [
            "    </ol>",
            "  </section>",
            '  <section class="adf-preview-manual-body">',
        ]
    )
    for step in playbook.get("steps", []):
        dependency_item = dependency_by_step.get(step["step_id"])
        chapter_label = _step_navigation_label(step, dependency_item)
        command_count_label = _step_command_count_label(step)
        lines.extend(
            [
                f'<details id="manual-{step["step_id"]}" class="adf-preview-manual-step" data-adf-manual-step="true">',
                '  <summary class="adf-preview-manual-summary">',
                '    <span class="adf-preview-manual-summary-copy">',
                f'      <span class="adf-preview-manual-kicker">{step["step_label"]}</span>',
                f'      <span class="adf-preview-manual-summary-title">{chapter_label}</span>',
                "    </span>",
                '    <span class="adf-preview-manual-summary-meta">',
                f'      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">{command_count_label}</span>',
                "    </span>",
                "  </summary>",
                '  <div class="adf-preview-manual-step-body">',
            ]
        )
        if step.get("recommended_commands"):
            lines.extend(['  <div class="adf-preview-manual-callout">'])
            for command in step.get("recommended_commands", []):
                lines.extend(_render_operator_command_markdown(command))
            lines.extend(["  </div>"])
        lines.extend(["  </div>", "</details>"])
    lines.extend(
        [
            "  </section>",
            "</div>",
            "",
        ]
    )
    return "\n".join(lines)


def _render_keycloak_integration_guide_markdown(
    *,
    order: int,
    page_record: dict[str, Any] | None = None,
    playbook: dict[str, Any] | None = None,
    guide_entry: dict[str, Any] | None = None,
) -> str:
    drilldown = playbook.get("imported_module_drilldown", {}) if isinstance(playbook, dict) else {}
    route_summary = (
        str(page_record.get("use_this_when") or page_record.get("symptom_focus") or "").strip()
        if isinstance(page_record, dict)
        else ""
    )
    handoff_target = (
        str(page_record.get("handoff_target") or "").strip()
        if isinstance(page_record, dict)
        else ""
    )
    next_checks = drilldown.get("bounded_next_checks")
    observed_boundary = drilldown.get("observed_boundary_on_appliance")
    upstream_references = drilldown.get("upstream_references")
    what_to_save = page_record.get("what_to_save") if isinstance(page_record, dict) else None

    lines = [
        "---",
        f"title: {json.dumps(str((guide_entry or {}).get('label') or 'ASMS / Keycloak integration guide'))}",
        'description: ""',
        "sidebar:",
        f"  label: {json.dumps(str((guide_entry or {}).get('label') or 'ASMS / Keycloak integration guide'))}",
        f"  order: {order}",
        "---",
        "",
        "# ASMS / Keycloak integration guide",
        "",
    ]
    if route_summary:
        lines.extend(
            [
                "## Current route contract",
                "",
                f"- Use this route when: {route_summary}",
                f"- Current handoff target: `{handoff_target}`" if handoff_target else "- Current handoff target: not declared",
                "",
            ]
        )
    lines.extend(
        [
            "## What Keycloak does in ASMS",
            "",
            "- Keycloak is the auth service used in the ASMS login chain.",
            "- Apache exposes Keycloak through `/keycloak/` and proxies that path to `https://localhost:8443/`.",
            "- The UI login page can still load even when Keycloak is down. That means Keycloak failure is not always a top-level Apache failure.",
            "",
            "## Proven integration points",
            "",
            "1. Apache rewrites `/algosec/suite/login...` to `/algosec-ui/login` before the operator reaches the browser-facing login shell.",
            "2. Apache proxies `/keycloak/` to local Keycloak on `8443` through `/etc/httpd/conf.d/keycloak.conf`.",
            "3. The preserved login-bootstrap window on this lab was `/seikan/login/setup` -> `SuiteLoginSessionValidation.php` -> same-window Keycloak OIDC request.",
            "4. In the clean Keycloak-down simulation, Apache still returned `HTTP 200` for `/algosec-ui/login` while the Keycloak OIDC well-known path returned `503`.",
            "",
            "## What this means for support",
            "",
            "- If the login page itself is down, stay on Apache or the UI edge.",
            "- If the login page still loads but auth is failing, move to Keycloak.",
            "- Do not treat Keycloak as the first browser-facing edge. Treat it as the auth branch behind Apache.",
            "",
            "## Imported-module drilldown summary",
            "",
        ]
    )
    if isinstance(next_checks, list) and next_checks:
        lines.extend([f"- {item}" for item in next_checks])
    else:
        lines.extend(
            [
                "- Prove the module boundary first: login page versus OIDC path.",
                "- Classify the failure next: service state, listener state, proxy mapping, and journal clue.",
                "- Stop with a support-ready evidence packet before expanding into many Keycloak-specific branches.",
            ]
        )
    lines.extend(["", "## Proven runtime clues", ""])
    if isinstance(observed_boundary, list) and observed_boundary:
        lines.extend([f"- {item}" for item in observed_boundary])
    else:
        lines.extend(
            [
                "- Healthy baseline from March 29, 2026 around `19:59:50 EDT`: `httpd`, `keycloak`, and `ms-metro` were active, the login page returned `HTTP 200`, Keycloak OIDC returned `200`, and Metro heartbeat returned `isAlive: true`.",
                "- Keycloak-down simulation from March 29, 2026: login page stayed `HTTP 200`, OIDC returned `503`, and Metro stayed healthy.",
                "- Live observe-only validation from March 30, 2026 around `10:10:55 EDT` on `10.167.2.150`: login page stayed `HTTP 200`, OIDC returned `503`, `keycloak.service` was failed, `8443` was absent, Metro stayed healthy, and the journal showed a repeated `java.io.EOFException` startup clue.",
                "- Current failure clue from the same troubleshooting line: repeated `java.io.EOFException` in the Keycloak startup path can leave `keycloak.service` failed while Apache still serves the login page.",
            ]
        )
    lines.extend(
        [
            "",
            "## Useful files and endpoints",
            "",
            "- Apache Keycloak proxy config: `/etc/httpd/conf.d/keycloak.conf`",
            "- Apache login rewrite config: `/etc/httpd/conf.d/zzz_fa.conf`",
            "- Browser-facing login page: `https://127.0.0.1/algosec-ui/login`",
            "- Browser-facing OIDC well-known probe: `https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration`",
            "- Local Keycloak listener: `8443`",
            "",
        ]
    )
    if isinstance(what_to_save, list) and what_to_save:
        lines.extend(
            [
                "## Save these items",
                "",
                *[f"- {item}" for item in what_to_save],
                "",
            ]
        )
    lines.extend(["## Upstream references", ""])
    if isinstance(upstream_references, list) and upstream_references:
        for entry in upstream_references:
            if not isinstance(entry, dict):
                continue
            label = entry.get("label")
            url = entry.get("url")
            details = entry.get("details")
            if isinstance(label, str) and isinstance(url, str):
                if isinstance(details, str) and details.strip():
                    lines.append(f"- [{label}]({url}): {details}")
                else:
                    lines.append(f"- [{label}]({url})")
    else:
        lines.extend(
            [
                "- [Keycloak documentation](https://www.keycloak.org/documentation)",
                "- [Configuring Keycloak](https://www.keycloak.org/server/configuration)",
                "- [Keycloak GitHub repository](https://github.com/keycloak/keycloak)",
            ]
        )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            "- `eval/history/asms-ui-login-bootstrap-observe-only-delegation-20260327.md`",
            "- `eval/history/asms-ui-keycloak-simulation-and-metro-blocked-20260330.md`",
            "- `eval/history/asms-ui-keycloak-and-metro-service-fault-simulation-attempt-20260330.md`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_keycloak_tier_2_support_guide_markdown(
    *,
    order: int,
    page_record: dict[str, Any] | None = None,
    playbook: dict[str, Any] | None = None,
    guide_entry: dict[str, Any] | None = None,
) -> str:
    drilldown = playbook.get("imported_module_drilldown", {}) if isinstance(playbook, dict) else {}
    route_summary = (
        str(page_record.get("use_this_when") or page_record.get("symptom_focus") or "").strip()
        if isinstance(page_record, dict)
        else ""
    )
    handoff_target = (
        str(page_record.get("handoff_target") or "").strip()
        if isinstance(page_record, dict)
        else ""
    )
    login_vs_oidc_command = {
        "label": "Compare login page and Keycloak OIDC",
        "command": "curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'; echo '---'; curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration | sed -n '1,12p'",
        "expected_signal": "The login page and the Keycloak OIDC path both return HTTP 200.",
        "healthy_markers": ["HTTP/1.1 200"],
        "interpretation": "If the login page is still HTTP 200 but the OIDC path is not, keep the case on Keycloak.",
        "example_output": "HTTP/1.1 200 OK\n---\nHTTP/1.1 200 OK",
    }
    service_command = {
        "label": "Check Keycloak service and 8443 listener",
        "command": "systemctl status keycloak.service --no-pager; echo '--- listeners ---'; ss -lntp | grep -E ':(8443)\\b'",
        "expected_signal": "Keycloak is active and 8443 is listening.",
        "healthy_markers": ["Active: active (running)", "LISTEN", ":8443"],
        "interpretation": "If keycloak.service is failed or 8443 is missing, save the output and keep the case on Keycloak.",
        "example_output": "● keycloak.service - Keycloak Service\n   Active: active (running)\n--- listeners ---\nLISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:((\"java\",pid=2745,fd=91))",
    }
    journal_command = {
        "label": "Check the recent Keycloak journal",
        "command": "journalctl -u keycloak.service -n 80 --no-pager",
        "expected_signal": "Recent lines show either a normal start or the failure clue that stopped startup.",
        "healthy_markers": ["started", "Listening on", "8443"],
        "interpretation": "If the service failed to start, save the clue. One proven example in this lab was `java.io.EOFException`.",
        "example_output": "Exception in thread \"main\" java.lang.reflect.UndeclaredThrowableException\nCaused by: java.io.EOFException\n... SerializedApplication.read(...)\n... QuarkusEntryPoint.doRun(...)\nkeycloak.service: Main process exited, status=1/FAILURE",
    }
    restart_command = {
        "label": "Optional: run one bounded restart if recovery validation is needed",
        "command": "sudo systemctl restart keycloak.service && sleep 30 && systemctl is-active keycloak.service && ss -lntp | grep -E ':(8443)\\b' && curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration | sed -n '1,12p'",
        "expected_signal": "Keycloak comes back active, 8443 listens again, and the OIDC path returns HTTP 200.",
        "healthy_markers": ["active", "LISTEN", ":8443", "HTTP/1.1 200"],
        "interpretation": "If the service still fails after one bounded restart, stop there. Save the output and escalate with the Keycloak failure clue instead of inventing many extra branches.",
        "example_output": "active\nLISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:((\"java\",pid=2745,fd=91))\nHTTP/1.1 200 OK",
    }
    lines = [
        "---",
        f"title: {json.dumps(str((guide_entry or {}).get('label') or 'ASMS / Keycloak Tier 2 support guide'))}",
        'description: ""',
        "sidebar:",
        f"  label: {json.dumps(str((guide_entry or {}).get('label') or 'ASMS / Keycloak Tier 2 support guide'))}",
        f"  order: {order}",
        "---",
        "",
        "# ASMS / Keycloak Tier 2 support guide",
        "",
        "## Use this guide for this kind of case",
        "",
        f"- {route_summary}" if route_summary else "- The login page opens, but login or auth does not finish.",
        "- The customer reports auth failure, redirect loop, or login not working.",
        "- Apache still looks healthy and you need to decide whether the problem is Keycloak.",
        "",
        "## Fast rule",
        "",
        "- If `/algosec-ui/login` is still `HTTP 200` but the Keycloak OIDC path is failing, diagnose Keycloak.",
        "- Do not move back to Apache unless the login page itself stops loading.",
        f"- If the Keycloak boundary proves healthy again, hand off to `{handoff_target}`." if handoff_target else "- If the Keycloak boundary proves healthy again, hand off to the next deeper ASMS layer.",
        "",
        "## Failure classes",
        "",
        "",
        "## Check 1",
        "",
    ]
    failure_classes = drilldown.get("generic_failure_classes")
    if isinstance(failure_classes, list) and failure_classes:
        for entry in failure_classes:
            if not isinstance(entry, dict):
                continue
            label = entry.get("label")
            details = entry.get("details")
            if isinstance(label, str) and isinstance(details, str):
                lines.insert(-3, f"- `{label}`: {details}")
    else:
        lines[-3:-3] = [
            "- `startup_failure`: the service fails or exits during startup.",
            "- `listener_absent`: the Keycloak service is supposed to listen on `8443`, but that listener is missing.",
            "- `useful_work_path_failed`: the service may look partly alive, but the OIDC path still fails while the login page loads.",
            "- `dependency_or_resource_unknown`: the Keycloak boundary is proven, but the current clues do not yet show whether the deeper cause is config, storage, secrets, or host pressure.",
        ]
    lines.extend(_render_operator_command_markdown(login_vs_oidc_command))
    lines.extend(
        [
            "## Check 2",
            "",
        ]
    )
    lines.extend(_render_operator_command_markdown(service_command))
    lines.extend(
        [
            "## Check 3",
            "",
        ]
    )
    lines.extend(_render_operator_command_markdown(journal_command))
    lines.extend(
        [
            "## Check 4",
            "",
        ]
    )
    lines.extend(_render_operator_command_markdown(restart_command))
    lines.extend(
        [
            "## When to escalate",
            "",
            "- Escalate when the login page still loads but the OIDC path is failing and you already captured the service, listener, proxy, and journal clues.",
            "- Escalate when one bounded restart does not restore useful auth work.",
            "- Escalate with the failure class you proved, not with a vague `login broken` summary.",
            "",
            "## What to save before the next session",
            "",
            "",
            "## Upstream references",
            "",
            "- [Keycloak documentation](https://www.keycloak.org/documentation)",
            "- [Configuring Keycloak](https://www.keycloak.org/server/configuration)",
            "- [Keycloak GitHub repository](https://github.com/keycloak/keycloak)",
            "",
        ]
    )
    save_index = lines.index("## Upstream references") - 1
    what_to_save = page_record.get("what_to_save") if isinstance(page_record, dict) else None
    if isinstance(what_to_save, list) and what_to_save:
        lines[save_index:save_index] = [f"- {item}" for item in what_to_save]
    else:
        lines[save_index:save_index] = [
            "- output from the login-page and OIDC comparison",
            "- output from `systemctl status keycloak.service`",
            "- the recent Keycloak journal clue",
            "- the result of the restart attempt if you ran it",
        ]
    return "\n".join(lines) + "\n"


def _render_template_step_panel(
    *,
    step: dict[str, Any],
    dependency_item: dict[str, str] | None,
    panel_class: str,
    section_prefix: str,
    show_outcomes: bool,
) -> list[str]:
    label = _step_navigation_label(step, dependency_item)
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
    page_record: dict[str, Any] | None = None,
) -> str:
    if playbook["playbook_id"] == PRIMARY_PLAYBOOK_ID:
        return _render_operator_playbook_markdown(
            playbook=playbook,
            order=order,
            symptom_entries=symptom_entries,
            page_record=page_record,
        )
    if page_record and page_record.get("page_type") == "boundary_confirmation":
        return _render_canonical_boundary_playbook_markdown(
            playbook=playbook,
            order=order,
            page_record=page_record,
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
    drilldown_lines = _render_imported_module_drilldown_markdown(
        playbook,
        include_symptom_focus=False,
    )
    if drilldown_lines:
        lines.extend(drilldown_lines)
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


def _render_operator_playbook_markdown(
    *,
    playbook: dict[str, Any],
    order: int,
    symptom_entries: list[dict[str, str]],
    page_record: dict[str, Any] | None = None,
) -> str:
    if page_record and page_record.get("page_type") == "boundary_confirmation":
        return _render_boundary_confirmation_playbook_markdown(
            playbook=playbook,
            order=order,
            page_record=page_record,
        )

    lines = [
        "---",
        f"title: {playbook['label']}",
        'description: ""',
        "sidebar:",
        f"  label: {playbook['label']}",
        f"  order: {order}",
        "---",
        "",
    ]
    lines.extend(_render_imported_module_drilldown_markdown(playbook))
    if lines[-1] != "":
        lines.append("")
    lines.extend(
        [
        "## Command flow",
        "",
        _render_template_field_manual(
            playbook=playbook,
            symptom_entries=symptom_entries,
            anchor_prefix=f"/playbooks/{_playbook_slug(playbook)}/",
        ).rstrip(),
        "",
    ])
    return "\n".join(lines) + "\n"


def _render_boundary_confirmation_playbook_markdown(
    *,
    playbook: dict[str, Any],
    order: int,
    page_record: dict[str, Any],
) -> str:
    lines = [
        "---",
        f"title: {playbook['label']}",
        'description: ""',
        "sidebar:",
        f"  label: {playbook['label']}",
        f"  order: {order}",
        "---",
        "",
    ]

    lines.extend(_render_boundary_use_this_when_markdown(playbook, page_record))
    lines.extend(_render_boundary_check_this_service_markdown(playbook, page_record))

    if lines[-1] != "":
        lines.append("")
    lines.extend(
        [
            "## Command flow",
            "",
            _render_template_field_manual(
                playbook=playbook,
                symptom_entries=[],
                anchor_prefix=f"/playbooks/{_playbook_slug(playbook)}/",
            ).rstrip(),
            "",
        ]
    )
    lines.extend(_render_boundary_what_to_save_markdown(playbook, page_record))
    lines.extend(_render_boundary_when_to_escalate_markdown(page_record))
    lines.extend(_render_boundary_reference_notes_markdown(playbook))
    lines.extend(_render_route_notes_markdown(page_record))
    return "\n".join(lines) + "\n"


def _render_imported_module_drilldown_markdown(
    playbook: dict[str, Any],
    *,
    include_symptom_focus: bool = True,
    section_title: str = "Imported-module drilldown",
) -> list[str]:
    drilldown = playbook.get("imported_module_drilldown")
    if not isinstance(drilldown, dict):
        return []

    lines: list[str] = []
    if include_symptom_focus:
        lines.extend([playbook["symptom_focus"], ""])
    lines.extend(
        [
            f"## {section_title}",
            "",
            str(
                drilldown.get("intro")
                or "Use this page to prove the current boundary first, classify the failure, and gather a support-ready evidence packet before you widen the case."
            ),
            "",
        ]
    )

    observed_boundary = drilldown.get("observed_boundary_on_appliance")
    if isinstance(observed_boundary, list) and observed_boundary:
        lines.extend(
            [
                "### Observed boundary on this appliance",
                "",
                *[f"- {item}" for item in observed_boundary],
                "",
            ]
        )

    asms_meaning = drilldown.get("what_that_boundary_means_in_asms")
    if isinstance(asms_meaning, list) and asms_meaning:
        lines.extend(
            [
                "### What that boundary means in ASMS",
                "",
                *[f"- {item}" for item in asms_meaning],
                "",
            ]
        )

    failure_classes = drilldown.get("generic_failure_classes")
    if isinstance(failure_classes, list) and failure_classes:
        lines.extend(
            [
                "### Generic failure classes",
                "",
            ]
        )
        for entry in failure_classes:
            if not isinstance(entry, dict):
                continue
            label = entry.get("label")
            details = entry.get("details")
            if isinstance(label, str) and isinstance(details, str):
                lines.append(f"- `{label}`: {details}")
        lines.append("")

    next_checks = drilldown.get("bounded_next_checks")
    if isinstance(next_checks, list) and next_checks:
        lines.extend(
            [
                "### Bounded next checks",
                "",
                *[f"- {item}" for item in next_checks],
                "",
            ]
        )

    escalation_evidence = drilldown.get("escalation_ready_evidence")
    if isinstance(escalation_evidence, list) and escalation_evidence:
        lines.extend(
            [
                "### Escalation-ready evidence",
                "",
                *[f"- {item}" for item in escalation_evidence],
                "",
            ]
        )

    upstream_references = drilldown.get("upstream_references")
    if isinstance(upstream_references, list) and upstream_references:
        lines.extend(
            [
                "### Upstream references",
                "",
            ]
        )
        for entry in upstream_references:
            if not isinstance(entry, dict):
                continue
            label = entry.get("label")
            url = entry.get("url")
            details = entry.get("details")
            if isinstance(label, str) and isinstance(url, str) and url:
                if isinstance(details, str) and details:
                    lines.append(f"- [{label}]({url}): {details}")
                else:
                    lines.append(f"- [{label}]({url})")
        lines.append("")

    return lines


def _render_page_record_panel_markdown(page_record: dict[str, Any]) -> list[str]:
    lines = [
        "## Generated page record",
        "",
        f"- `Page type`: {page_record.get('page_type', '')}",
        f"- `Page id`: {page_record.get('page_id', '')}",
    ]
    if page_record.get("label"):
        lines.append(f"- `Label`: {page_record['label']}")
    if page_record.get("symptom_focus"):
        lines.append(f"- `Symptom focus`: {page_record['symptom_focus']}")
    if page_record.get("entry_question"):
        lines.append(f"- `Entry question`: {page_record['entry_question']}")
    if page_record.get("first_action"):
        lines.append(f"- `First action`: {page_record['first_action']}")
    if page_record.get("handoff_target"):
        lines.append(f"- `Handoff target`: {page_record['handoff_target']}")
    if page_record.get("handoff_target_type"):
        lines.append(f"- `Handoff target type`: {page_record['handoff_target_type']}")
    if page_record.get("route_kind"):
        lines.append(f"- `Route kind`: {page_record['route_kind']}")
    if page_record.get("branch_if_pass"):
        lines.append(f"- `Branch if pass`: {page_record['branch_if_pass']}")
    if page_record.get("branch_if_fail"):
        lines.append(f"- `Branch if fail`: {page_record['branch_if_fail']}")
    what_to_save = page_record.get("what_to_save")
    if isinstance(what_to_save, list) and what_to_save:
        lines.append(f"- `What to save`: {', '.join(str(item) for item in what_to_save)}")
    lines.append("")
    return lines


def _render_boundary_use_this_when_markdown(
    playbook: dict[str, Any],
    page_record: dict[str, Any],
) -> list[str]:
    use_this_when = _normalized_use_this_when(
        page_record.get("use_this_when") or playbook.get("symptom_focus"),
    )
    if not use_this_when:
        return []
    return [
        "## Use this when",
        "",
        f"- {use_this_when}",
        "",
    ]


def _render_boundary_check_this_service_markdown(
    playbook: dict[str, Any],
    page_record: dict[str, Any],
) -> list[str]:
    lines = ["## Check this service", ""]
    service_name = page_record.get("service_name")
    if isinstance(service_name, str) and service_name:
        lines.append(f"- Service to check first: `{service_name}.service`.")
    first_action = page_record.get("first_action")
    if isinstance(first_action, str) and first_action:
        lines.append(f"- Start here: {first_action}")
    decision_rule = playbook.get("decision_rule")
    if isinstance(decision_rule, str) and decision_rule:
        lines.append(f"- Decision rule: {decision_rule}")

    drilldown = playbook.get("imported_module_drilldown")
    observed_boundary = drilldown.get("observed_boundary_on_appliance") if isinstance(drilldown, dict) else None
    if isinstance(observed_boundary, list) and observed_boundary:
        lines.extend(["", "### What to look for", ""])
        lines.extend([f"- {item}" for item in observed_boundary if isinstance(item, str) and item])

    failure_classes = drilldown.get("generic_failure_classes") if isinstance(drilldown, dict) else None
    if isinstance(failure_classes, list) and failure_classes:
        lines.extend(["", "### If the service is still unhealthy", ""])
        for entry in failure_classes:
            if not isinstance(entry, dict):
                continue
            label = entry.get("label")
            details = entry.get("details")
            if isinstance(label, str) and isinstance(details, str) and label and details:
                lines.append(f"- `{label}`: {details}")

    next_checks = drilldown.get("bounded_next_checks") if isinstance(drilldown, dict) else None
    if isinstance(next_checks, list) and next_checks:
        lines.extend(["", "### If the cause is still not clear", ""])
        lines.extend([f"- {item}" for item in next_checks if isinstance(item, str) and item])

    lines.append("")
    return lines


def _render_boundary_what_to_save_markdown(
    playbook: dict[str, Any],
    page_record: dict[str, Any],
) -> list[str]:
    evidence_items: list[str] = []
    what_to_save = page_record.get("what_to_save")
    if isinstance(what_to_save, list):
        evidence_items.extend(str(item) for item in what_to_save if isinstance(item, str) and item)

    drilldown = playbook.get("imported_module_drilldown")
    escalation_evidence = drilldown.get("escalation_ready_evidence") if isinstance(drilldown, dict) else None
    if isinstance(escalation_evidence, list):
        evidence_items.extend(str(item) for item in escalation_evidence if isinstance(item, str) and item)

    deduped_items: list[str] = []
    seen: set[str] = set()
    for item in evidence_items:
        if item not in seen:
            deduped_items.append(item)
            seen.add(item)

    if not deduped_items:
        return []
    return [
        "## What to save",
        "",
        *[f"- {item}" for item in deduped_items],
        "",
    ]


def _render_boundary_when_to_escalate_markdown(page_record: dict[str, Any]) -> list[str]:
    lines = ["## When to escalate", ""]
    branch_if_fail = page_record.get("branch_if_fail")
    if isinstance(branch_if_fail, str) and branch_if_fail:
        lines.append(f"- {branch_if_fail}")
    branch_if_pass = page_record.get("branch_if_pass")
    if isinstance(branch_if_pass, str) and branch_if_pass:
        lines.append(f"- If the service looks healthy again, {branch_if_pass[0].lower() + branch_if_pass[1:]}")
    lines.append("")
    return lines


def _render_boundary_reference_notes_markdown(playbook: dict[str, Any]) -> list[str]:
    drilldown = playbook.get("imported_module_drilldown")
    if not isinstance(drilldown, dict):
        return []

    lines: list[str] = []
    asms_meaning = drilldown.get("what_that_boundary_means_in_asms")
    if isinstance(asms_meaning, list) and asms_meaning:
        lines.extend(["## Deeper notes", ""])
        lines.extend([f"- {item}" for item in asms_meaning if isinstance(item, str) and item])
        lines.append("")

    upstream_references = drilldown.get("upstream_references")
    if isinstance(upstream_references, list) and upstream_references:
        lines.extend(["## Reference links", ""])
        for entry in upstream_references:
            if not isinstance(entry, dict):
                continue
            label = entry.get("label")
            url = entry.get("url")
            details = entry.get("details")
            if isinstance(label, str) and isinstance(url, str) and url:
                if isinstance(details, str) and details:
                    lines.append(f"- [{label}]({url}): {details}")
                else:
                    lines.append(f"- [{label}]({url})")
        lines.append("")

    return lines


def _render_route_notes_markdown(page_record: dict[str, Any]) -> list[str]:
    lines = [
        "<details class=\"adf-route-notes\">",
        "<summary>Route notes</summary>",
        "",
        f"- Page type: `{page_record.get('page_type', '')}`",
        f"- Page id: `{page_record.get('page_id', '')}`",
    ]
    if page_record.get("handoff_target"):
        lines.append(f"- Next page: `{page_record['handoff_target']}`")
    if page_record.get("handoff_target_type"):
        lines.append(f"- Next page type: `{page_record['handoff_target_type']}`")
    if page_record.get("route_kind"):
        lines.append(f"- Route kind: `{page_record['route_kind']}`")
    lines.extend(["", "</details>", ""])
    return lines


def _render_generated_page_record_markdown(*, page_record: dict[str, Any], order: int) -> str:
    title = str(page_record.get("label") or page_record.get("page_id") or "Generated page")
    intro = (
        page_record.get("use_this_when")
        or page_record.get("symptom_focus")
        or page_record.get("purpose")
        or page_record.get("customer_symptom")
        or ""
    )
    lines = [
        "---",
        f"title: {json.dumps(title)}",
        'description: ""',
        "sidebar:",
        f"  label: {json.dumps(title)}",
        f"  order: {order}",
        "---",
        "",
    ]
    if isinstance(intro, str) and intro:
        lines.extend([intro, ""])
    steps = page_record.get("steps")
    if isinstance(steps, list) and steps:
        lines.extend(["## Steps", ""])
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_label = step.get("step_label") or "Step"
            action = step.get("action")
            if isinstance(action, str) and action:
                lines.append(f"- **{step_label}**: {action}")
        lines.append("")
    what_to_save = page_record.get("what_to_save")
    if isinstance(what_to_save, list) and what_to_save:
        lines.extend(["## What to save", ""])
        lines.extend([f"- {item}" for item in what_to_save if isinstance(item, str) and item])
        lines.append("")
    if page_record.get("branch_if_fail"):
        lines.extend(["## When to escalate", "", f"- {page_record['branch_if_fail']}", ""])
    return "\n".join(lines) + "\n"


def _page_rendering(page_record: dict[str, Any] | None) -> dict[str, Any]:
    rendering = page_record.get("rendering") if isinstance(page_record, dict) else None
    return rendering if isinstance(rendering, dict) else {}


def _supplement_id_for_page_record(page_record: dict[str, Any] | None) -> str | None:
    supplement_id = _page_rendering(page_record).get("supplement_id")
    return supplement_id if isinstance(supplement_id, str) and supplement_id else None


def _supplement_for_page_record(page_record: dict[str, Any] | None) -> dict[str, Any] | None:
    supplement_id = _supplement_id_for_page_record(page_record)
    if supplement_id is None:
        return None
    supplement = PLAYBOOK_SUPPLEMENTS.get(supplement_id)
    return supplement if isinstance(supplement, dict) else None


def _apply_playbook_supplement(
    playbook: dict[str, Any],
    supplement: dict[str, Any] | None,
) -> dict[str, Any]:
    if supplement is None:
        return dict(playbook)

    merged = dict(playbook)
    imported_module_drilldown = supplement.get("imported_module_drilldown")
    if isinstance(imported_module_drilldown, dict):
        merged["imported_module_drilldown"] = imported_module_drilldown
    return merged


def _related_guides_for_page_record(page_record: dict[str, Any] | None) -> list[dict[str, Any]]:
    related_guides = _page_rendering(page_record).get("related_guides")
    if not isinstance(related_guides, list):
        return []
    return [entry for entry in related_guides if isinstance(entry, dict)]


def _render_authored_guide_markdown(
    *,
    guide_entry: dict[str, Any],
    order: int,
    page_record: dict[str, Any] | None = None,
    playbook: dict[str, Any] | None = None,
) -> str | None:
    guide_id = guide_entry.get("guide_id")
    if guide_id == "keycloak-integration":
        return _render_keycloak_integration_guide_markdown(
            order=order,
            page_record=page_record,
            playbook=playbook,
            guide_entry=guide_entry,
        )
    if guide_id == "keycloak-tier-2-support":
        return _render_keycloak_tier_2_support_guide_markdown(
            order=order,
            page_record=page_record,
            playbook=playbook,
            guide_entry=guide_entry,
        )
    return None


def _canonical_boundary_service_heading(
    *,
    playbook: dict[str, Any],
    page_record: dict[str, Any],
) -> str:
    service_name = str(page_record.get("service_name") or "").strip()
    if service_name:
        if service_name.endswith(".service"):
            return f"Check {service_name}"
        return f"Check the {service_name.title()} service"
    return f"Check {playbook['label']}"


def _normalized_use_this_when(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    prefix = "use this when "
    if text.lower().startswith(prefix):
        return text[len(prefix):].strip()
    return text


def _canonical_boundary_if_healthy(
    *,
    playbook: dict[str, Any],
    page_record: dict[str, Any],
) -> str:
    service_name = str(page_record.get("service_name") or "this service").strip()
    service_phrase = service_name.title() if service_name and service_name != "this service" else service_name
    handoff_type = str(page_record.get("handoff_target_type") or "").strip()
    if handoff_type == "deep_guide":
        return (
            f"If {service_phrase} looks healthy, move to the deeper ASMS guide for the next layer."
        )
    if handoff_type == "boundary_confirmation":
        return (
            f"If {service_phrase} looks healthy, move to the next named service check."
        )
    return (
        f"If {service_phrase} looks healthy, move to the next page in the diagnosis."
    )


def _canonical_boundary_if_unhealthy(
    *,
    playbook: dict[str, Any],
    page_record: dict[str, Any],
) -> str:
    branch_if_fail = str(page_record.get("branch_if_fail") or "").strip()
    if branch_if_fail:
        branch_if_fail = branch_if_fail.replace(
            "Stop on the Keycloak boundary and escalate with the saved evidence.",
            "Keep the case on Keycloak and escalate with the saved evidence.",
        )
        branch_if_fail = branch_if_fail.replace(
            "Stop on this boundary and escalate with the saved evidence.",
            "Keep the case on this service and escalate with the saved evidence.",
        )
        return branch_if_fail
    service_name = str(page_record.get("service_name") or "this service").strip()
    service_phrase = service_name.title() if service_name and service_name != "this service" else service_name
    return f"If {service_phrase} still looks unhealthy, keep the case on this service and escalate with the saved evidence."


def _render_canonical_boundary_playbook_markdown(
    *,
    playbook: dict[str, Any],
    order: int,
    page_record: dict[str, Any],
) -> str:
    lines = [
        "---",
        f"title: {playbook['label']}",
        'description: ""',
        "sidebar:",
        f"  label: {playbook['label']}",
        f"  order: {order}",
        "---",
        "",
        "## Use this page when",
        "",
    ]

    use_this_when = _normalized_use_this_when(
        page_record.get("use_this_when")
        or playbook.get("symptom_focus")
        or "",
    )
    if use_this_when:
        lines.append(f"- {use_this_when}")
    symptom_focus = _normalized_use_this_when(playbook.get("symptom_focus") or "")
    if symptom_focus and symptom_focus != use_this_when:
        lines.append(f"- {symptom_focus}")
    lines.extend(
        [
            "",
            f"## {_canonical_boundary_service_heading(playbook=playbook, page_record=page_record)}",
            "",
            "Use the checks below to confirm whether this service or module is the current failure point.",
            "",
            "## Command flow",
            "",
            _render_template_field_manual(playbook=playbook, symptom_entries=[]).rstrip(),
            "",
            "## If this boundary still looks unhealthy",
            "",
            f"- {_canonical_boundary_if_unhealthy(playbook=playbook, page_record=page_record)}",
            "",
            "## If this boundary looks healthy",
            "",
            f"- {_canonical_boundary_if_healthy(playbook=playbook, page_record=page_record)}",
            "",
            "## What to save",
            "",
        ]
    )

    what_to_save = page_record.get("what_to_save")
    if isinstance(what_to_save, list) and what_to_save:
        lines.extend([f"- {item}" for item in what_to_save if isinstance(item, str) and item])
    else:
        lines.append("- Save the command output that shows where this boundary first stops looking healthy.")
    lines.extend(
        [
            "",
            "## When to escalate",
            "",
            f"- {_canonical_boundary_if_unhealthy(playbook=playbook, page_record=page_record)}",
            "- Escalate after the bounded checks and any approved safe restart step if the saved evidence still points to this boundary.",
            "",
        ]
    )

    drilldown_lines = _render_imported_module_drilldown_markdown(
        playbook,
        include_symptom_focus=False,
        section_title="Optional deeper notes",
    )
    if drilldown_lines:
        lines.extend(drilldown_lines)

    return "\n".join(lines) + "\n"


def _render_boundary_page_markdown(
    *,
    page_record: dict[str, Any],
    order: int,
    supplemental_playbook: dict[str, Any] | None = None,
) -> str:
    canonical_playbook = supplemental_playbook or _minimal_boundary_playbook(page_record)
    return _render_canonical_boundary_playbook_markdown(
        playbook=canonical_playbook,
        order=order,
        page_record=page_record,
    )


def _minimal_boundary_playbook(page_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": str(page_record.get("label") or page_record.get("page_id") or "Boundary page"),
        "symptom_focus": str(page_record.get("use_this_when") or page_record.get("symptom_focus") or ""),
        "decision_rule": str(page_record.get("decision_rule") or "Run the checks in order and stop at the first unhealthy boundary."),
        "steps": list(page_record.get("steps") or []),
        "playbook_id": str(page_record.get("page_id") or "boundary-page"),
    }


def _supplemental_boundary_playbooks(
    page_records_by_id: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    supplemental_playbooks: dict[str, dict[str, Any]] = {}
    for page_id, page_record in page_records_by_id.items():
        supplement = _supplement_for_page_record(page_record)
        if supplement is None or "steps" not in supplement:
            continue
        supplemental_playbooks[page_id] = _merge_page_record_into_playbook(
            supplement,
            page_record,
        )
    return supplemental_playbooks


def _page_records_by_id(support_baseline: dict[str, Any]) -> dict[str, dict[str, Any]]:
    page_records: dict[str, dict[str, Any]] = {}
    for item in support_baseline.get("page_records", []):
        if not isinstance(item, dict):
            continue
        page_id = item.get("page_id")
        if not isinstance(page_id, str) or not page_id:
            continue
        if page_id in page_records:
            raise ValueError(f"duplicate page_records entry for page_id {page_id!r}")
        page_records[page_id] = item
    return page_records


def _page_record_for_playbook(
    playbook: dict[str, Any],
    page_records_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    page_key = playbook.get("page_id") or playbook.get("playbook_id")
    embedded_page_record = playbook.get("page_record") if isinstance(playbook.get("page_record"), dict) else None

    if not isinstance(page_key, str) or not page_key:
        return embedded_page_record

    page_record = page_records_by_id.get(page_key) or embedded_page_record
    if page_record is not None:
        _assert_page_record_alignment(playbook, page_record, source="page record")
    if embedded_page_record is not None and page_records_by_id.get(page_key) is not None:
        _assert_page_record_alignment(playbook, embedded_page_record, source="embedded page record")
    return page_record


def _merge_page_record_into_playbook(
    playbook: dict[str, Any],
    page_record: dict[str, Any] | None,
) -> dict[str, Any]:
    if page_record is None:
        return dict(playbook)

    merged_playbook = dict(playbook)
    route_overrides = {
        "label": page_record.get("label"),
        "symptom_focus": page_record.get("use_this_when") or page_record.get("symptom_focus"),
        "decision_rule": page_record.get("decision_rule"),
        "page_id": page_record.get("page_id"),
        "page_type": page_record.get("page_type"),
        "route_kind": page_record.get("route_kind"),
        "handoff_target": page_record.get("handoff_target"),
        "handoff_target_type": page_record.get("handoff_target_type"),
    }
    for field, value in route_overrides.items():
        if value:
            merged_playbook[field] = value
    merged_playbook["page_record"] = page_record
    return merged_playbook


def _assert_page_record_alignment(
    playbook: dict[str, Any],
    page_record: dict[str, Any],
    *,
    source: str,
) -> None:
    expected_page_id = playbook.get("page_id") or playbook.get("playbook_id")
    if isinstance(expected_page_id, str) and page_record.get("page_id") and page_record["page_id"] != expected_page_id:
        raise ValueError(
            f"{source} page_id {page_record['page_id']!r} does not match playbook {expected_page_id!r}"
        )
    for field in ("page_type", "handoff_target", "handoff_target_type", "route_kind"):
        expected_value = playbook.get(field)
        actual_value = page_record.get(field)
        if expected_value and actual_value and actual_value != expected_value:
            raise ValueError(
                f"{source} {field} {actual_value!r} does not match playbook {field} {expected_value!r}"
            )


def _playbook_slug(playbook: dict[str, Any]) -> str:
    if playbook.get("playbook_id") == PRIMARY_PLAYBOOK_ID:
        return "asms-ui-is-down"
    return _slugify(str(playbook.get("label", playbook.get("playbook_id", "playbook"))))


def _page_record_slug(page_record: dict[str, Any]) -> str:
    if page_record.get("page_id") == "keycloak-auth":
        return KEYCLOAK_PLAYBOOK_SLUG
    return _slugify(str(page_record.get("label") or page_record.get("page_id") or "generated-page"))


def _render_system_checkpoint_markdown(step: dict[str, Any], dependency_item: dict[str, str] | None) -> list[str]:
    checkpoint_label = _step_navigation_label(step, dependency_item)
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
    summary_label = _step_navigation_label(step, dependency_item)
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


def _render_operator_command_markdown(command: dict[str, Any]) -> list[str]:
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
        '  <span class="adf-inline-label">Expected result:</span> ',
        f"{command['expected_signal']}",
        "</p>",
        "",
    ]
    if healthy_markers:
        lines.extend(
            [
                '<p class="adf-check-reference">',
                f"Check output for: {', '.join(healthy_markers)}",
                "</p>",
                "",
            ]
        )
    if command.get("interpretation"):
        lines.extend(
            [
                '<p class="adf-check-failure">',
                '  <span class="adf-inline-label">If result is different:</span> ',
                f"{command['interpretation']}",
                "</p>",
                "",
            ]
        )
    example = None
    example_title = "Example"
    if known_working_example:
        example = known_working_example.get("output")
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
            ".adf-preview-manual-step:target {",
            "  border-color: rgba(145, 114, 61, 0.42);",
            "  box-shadow: 0 18px 36px rgba(137, 104, 53, 0.18);",
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
            ".adf-preview-manual-list a:hover,",
            ".adf-preview-manual-list a:focus-visible {",
            "  border-bottom-color: rgba(145, 114, 61, 0.34);",
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


def _home_card_for_playbook_entry(
    entry: dict[str, str | int],
    primary_nav_entry: dict[str, str | int] | None,
) -> str:
    label = str(entry.get("label", "Playbook"))
    slug = str(entry.get("slug", ""))
    playbook_id = str(entry.get("playbook_id", ""))
    is_primary = primary_nav_entry is not None and entry.get("slug") == primary_nav_entry.get("slug")

    summary = "Target-backed generated playbook."
    detail = "Open the live playbook for support use."
    if is_primary:
        summary = "Lab-validated operator playbook."
    elif playbook_id == "keycloak-auth":
        summary = "Dedicated auth-service diagnostic route."
        detail = "Use this when the login page still loads but auth fails."

    return (
        f'<a class="adf-home-card" href="/{slug}/">\n'
        '  <p class="adf-panel-label">Live playbook</p>\n'
        f"  <strong>{label}</strong>\n"
        f"  <span>{summary}</span>\n"
        f'  <span class="adf-home-card-list">{detail}</span>\n'
        "</a>"
    )


def _home_card_for_guide_entry(entry: dict[str, str | int]) -> str:
    label = str(entry.get("label", "Guide"))
    slug = str(entry.get("slug", ""))
    summary = str(entry.get("summary") or "Generated support guide.")
    detail = str(entry.get("detail") or "Open this for supporting context.")

    return (
        f'<a class="adf-home-card" href="/{slug}/">\n'
        '  <p class="adf-panel-label">Guide</p>\n'
        f"  <strong>{label}</strong>\n"
        f"  <span>{summary}</span>\n"
        f'  <span class="adf-home-card-list">{detail}</span>\n'
        "</a>"
    )


def _home_card_for_page_record(page_record: dict[str, Any]) -> str:
    label = str(page_record.get("label") or page_record.get("page_id") or "Generated page")
    page_id = str(page_record.get("page_id") or "")
    page_type = str(page_record.get("page_type") or "page")
    handoff_target = str(page_record.get("handoff_target") or "n/a")
    summary = str(page_record.get("symptom_focus") or page_record.get("use_this_when") or "Generated from the page-record layer.")
    return (
        '<div class="adf-home-card adf-home-card-generated">\n'
        '  <p class="adf-panel-label">Generated page record</p>\n'
        f"  <strong>{label}</strong>\n"
        f"  <span>{page_type.replace('_', ' ')}</span>\n"
        f'  <span class="adf-home-card-list">Handoff: {handoff_target}</span>\n'
        f"  <span>{summary}</span>\n"
        f'  <span class="adf-home-card-list">Page id: {page_id}</span>\n'
        "</div>"
    )


def _primary_nav_entry(playbook_nav_entries: list[dict[str, str | int]]) -> dict[str, str | int] | None:
    for entry in playbook_nav_entries:
        if entry.get("playbook_id") == PRIMARY_PLAYBOOK_ID:
            return entry
    return playbook_nav_entries[0] if playbook_nav_entries else None


def _step_summary_label(step: dict[str, Any]) -> str:
    overview_summary = str(step.get("overview_summary") or "").strip()
    if overview_summary:
        return overview_summary
    action = str(step.get("action") or "").strip()
    if "." in action:
        return action.split(".", 1)[0].strip()
    if action:
        return action
    return str(step.get("label") or "").strip()


def _step_command_count_label(step: dict[str, Any]) -> str:
    count = len(step.get("recommended_commands", []))
    noun = "command" if count == 1 else "commands"
    return f"{count} {noun}"


def _step_navigation_label(step: dict[str, Any], dependency_item: dict[str, str] | None = None) -> str:
    overview_summary = str(step.get("overview_summary") or "").strip()
    if overview_summary:
        return overview_summary
    if dependency_item and dependency_item.get("label"):
        return str(dependency_item["label"]).strip()
    return _step_summary_label(step)


def _render_field_manual_script() -> str:
    return """const FIELD_MANUAL_SELECTOR = 'details.adf-preview-manual-step[data-adf-manual-step=\"true\"]';

function resolveFieldManualTarget(hash = window.location.hash) {
  if (!hash || !hash.startsWith('#manual-')) return null;
  const id = decodeURIComponent(hash.slice(1));
  const target = document.getElementById(id);
  if (!target) return null;
  if (target.matches(FIELD_MANUAL_SELECTOR)) return target;
  return target.closest(FIELD_MANUAL_SELECTOR);
}

function openFieldManualTarget(hash = window.location.hash) {
  const details = resolveFieldManualTarget(hash);
  if (details) details.open = true;
}

document.addEventListener('click', (event) => {
  const link = event.target.closest('a[href*=\"#manual-\"]');
  if (!link) return;
  const hash = new URL(link.href, window.location.href).hash;
  window.requestAnimationFrame(() => openFieldManualTarget(hash));
});

window.addEventListener('hashchange', () => {
  window.requestAnimationFrame(() => openFieldManualTarget(window.location.hash));
});

window.addEventListener('DOMContentLoaded', () => {
  window.requestAnimationFrame(() => openFieldManualTarget(window.location.hash));
});
"""


def _symptoms_by_playbook(support_baseline: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    symptom_map: dict[str, list[dict[str, str]]] = {}
    for item in support_baseline.get("symptom_lookup", []):
        playbook_id = item.get("playbook_id") or item.get("suggested_domain_id")
        if not playbook_id:
            continue
        symptom_map.setdefault(playbook_id, []).append(item)
    return symptom_map
