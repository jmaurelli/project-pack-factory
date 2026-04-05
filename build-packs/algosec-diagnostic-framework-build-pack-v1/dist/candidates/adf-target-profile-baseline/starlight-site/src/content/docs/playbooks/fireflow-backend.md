---
title: FireFlow Backend
description: ""
sidebar:
  label: FireFlow Backend
  order: 2
---

## Use this page when

- a FireFlow action fails or FireFlow returns an error.

## Check aff-boot.service

Use the checks below to confirm whether this service or module is the current failure point.

## Command flow

<div class="adf-preview-shell adf-preview-field-manual">
  <section class="adf-preview-manual-cover">
    <h2>FireFlow Backend</h2>
  </section>
  <section class="adf-preview-manual-contents">
    <p class="adf-panel-label">Steps</p>
    <ol class="adf-preview-manual-list">
<li><a class="adf-preview-manual-link" href="#manual-core-aff-step-1" data-adf-manual-target="manual-core-aff-step-1"><span>Step 1</span><strong>Identify the failing FireFlow action and confirm that the symptom is tied to /FireFlow/api or /aff/api</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-core-aff-step-2" data-adf-manual-target="manual-core-aff-step-2"><span>Step 2</span><strong>Confirm aff-boot</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-core-aff-step-3" data-adf-manual-target="manual-core-aff-step-3"><span>Step 3</span><strong>Confirm postgresql</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-core-aff-step-4" data-adf-manual-target="manual-core-aff-step-4"><span>Step 4</span><strong>Collect the latest FireFlow-related error lines or status output and decide whether the failure stays in FireFlow logic or must move deeper into dependencies</strong></a></li>
    </ol>
  </section>
  <section class="adf-preview-manual-body">
<details id="manual-core-aff-step-1" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 1</span>
      <span class="adf-preview-manual-summary-title">Identify the failing FireFlow action and confirm that the symptom is tied to /FireFlow/api or /aff/api</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check config mapping</p>

<p class="adf-inline-label">Run</p>

```bash
grep -n 1989 /etc/httpd/conf.d/aff.conf
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The expected mapping token 1989 appears in /etc/httpd/conf.d/aff.conf.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use the known proxy mapping to confirm the FireFlow path really terminates at the expected backend.
</p>

</div>

  </div>
  </div>
</details>
<details id="manual-core-aff-step-2" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 2</span>
      <span class="adf-preview-manual-summary-title">Confirm aff-boot</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">5 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check aff-boot.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status aff-boot.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If aff-boot is not active, stop here and treat the FireFlow service itself as the failure point. For this seam, aff-boot is a closer readable dependency than ActiveMQ, even though the latest staged pass proved that the live FireFlow runtime also talks to the broker on 61616.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check FireFlow listener</p>

<p class="adf-inline-label">Run</p>

```bash
ss -lntp | grep -E ':1989\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
A listening socket is present for 1989.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the FireFlow listener is missing, the backend route has nothing healthy to terminate to.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check config mapping</p>

<p class="adf-inline-label">Run</p>

```bash
grep -n 1989 /etc/httpd/conf.d/aff.conf
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The expected mapping token 1989 appears in /etc/httpd/conf.d/aff.conf.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the proxy config no longer points to 1989, the FireFlow request path may be broken even when the service is up.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check the FireFlow session path behind BusinessFlow AFF connection</p>

<p class="adf-inline-label">Run</p>

```bash
curl -sk -D - https://localhost/FireFlow/api/session | sed -n '1,12p'; echo '--- direct aff-boot ---'; curl -sk -D - https://localhost:1989/aff/api/external/session | sed -n '1,12p'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The Apache-fronted FireFlow session route and the direct aff-boot session route should return the same invalid-session shape.
</p>

<p class="adf-check-reference">
Check output for: /FireFlow/api/session, /aff/api/external/session, invalid session, HTTP/
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this to confirm that Apache still owns the session hop into aff-boot before moving deeper. If the two responses diverge, stay on Apache proxying, route ownership, or aff-boot listener issues rather than jumping ahead to later FireFlow workflow checks.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check aff-boot database and broker sockets</p>

<p class="adf-inline-label">Run</p>

```bash
pid=$(systemctl show -p MainPID --value aff-boot.service); echo PID=$pid; lsof -Pan -p "$pid" -i 2>/dev/null | egrep '(:1989|:5432|:61616)' || true
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The aff-boot Java PID still owns the 1989 listener and usually shows local PostgreSQL and broker connections for its live runtime.
</p>

<p class="adf-check-reference">
Check output for: PID=, :1989, :5432, :61616
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this to separate a healthy FireFlow runtime from a partial one. Current lab evidence shows that aff-boot can hold live database and ActiveMQ sockets at the same time, so a missing 61616 connection is a later supporting clue, not a first-pass route failure by itself.
</p>

<p class="adf-inline-label">Example</p>

```text
PID=1687
java 1687 root   24u  IPv6 ... TCP *:1989 (LISTEN)
java 1687 root  146u  IPv6 ... TCP 127.0.0.1:20770->127.0.0.1:5432 (ESTABLISHED)
java 1687 root  165u  IPv6 ... TCP 127.0.0.1:21910->127.0.0.1:61616 (ESTABLISHED)
```
</div>

  </div>
  </div>
</details>
<details id="manual-core-aff-step-3" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 3</span>
      <span class="adf-preview-manual-summary-title">Confirm postgresql</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check postgresql.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status postgresql.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the database is not active, FireFlow symptoms are likely downstream of data availability.
</p>

</div>

  </div>
  </div>
</details>
<details id="manual-core-aff-step-4" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 4</span>
      <span class="adf-preview-manual-summary-title">Collect the latest FireFlow-related error lines or status output and decide whether the failure stays in FireFlow logic or must move deeper into dependencies</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">5 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Review aff-boot.service logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u aff-boot.service -n 50 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent lines show healthy startup or a clear error signature to classify.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Look for permission errors, startup failures, database errors, or Metro-adjacent dependency errors first. Broker theory is now real for this seam because aff-boot holds live 61616 sockets, but the reproduced login-handoff minute still centered on auth, session, and REST activity rather than broker-side signals. A later FireFlow workflow minute now sharpened the same rule further: `CommandsDispatcher` plus nearby AFF reads rolled into `ms-configuration` unified-swagger refresh and an `AutoDiscovery` 502 without same-minute broker evidence. A second `CommandsDispatcher` pass on the `2026-03-21 04:30 EDT` cadence also stayed synchronous, matching journal refresh and `UserSession` fetches rather than queue-backed progression. The next non-`UserSession` branch still did not prove ticket progression either: it clustered around config broadcast plus `Authentication:authenticateUser` and `User:GetUserInfo`. A later targeted hunt on the same lab then showed a different boundary: FireFlow was enabled and polling AFF or AFA surfaces successfully, but `syslog_ticket_changes.pl` reported `Total tickets in DB: 0`, so there was no live request branch to correlate. Keep JMS and queue suspicion after the closer FireFlow route, service, and database checks unless the same failing minute points directly at broker activity, and if the lab appears empty from a ticket-workflow perspective, seed or replay a real request before another progression slice.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check same-minute configuration refresh clues</p>

<p class="adf-inline-label">Run</p>

```bash
grep -E 'AlgoSec_FireFlow|AlgoSec_ApplicationDiscovery|swagger|BAD_GATEWAY' /data/algosec-ms/logs/ms-configuration.log | tail -n 40; echo '--- apache ---'; grep -E 'AutoDiscovery|swagger/v2/api-docs' /var/log/httpd/ssl_error_log | tail -n 20
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent lines either stay quiet or show whether the failing FireFlow minute rolled into unified swagger refresh, downstream service-definition fetches, or a concrete Apache-side 502.
</p>

<p class="adf-check-reference">
Check output for: AlgoSec_FireFlow, swagger, AutoDiscovery, BAD_GATEWAY
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this when the FireFlow action minute includes `CommandsDispatcher`, `/FireFlow/api/session`, or nearby AFF config reads and then drifts into swagger or service-definition work. If `ms-configuration` and Apache show same-minute refresh or downstream 502 clues, pivot next to configuration-service troubleshooting before promoting ActiveMQ.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check whether CommandsDispatcher stayed on journal or session maintenance</p>

<p class="adf-inline-label">Run</p>

```bash
grep -E 'CommandsDispatcher|/journal/getChangesInOrigRulesByDate|/FireFlow/api/session|/session/extend' /var/log/httpd/ssl_access_log | tail -n 60
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The returned window shows whether the FireFlow branch stayed on journal refresh and session maintenance or moved into a different workflow shape.
</p>

<p class="adf-check-reference">
Check output for: CommandsDispatcher, /journal/getChangesInOrigRulesByDate, /FireFlow/api/session, /session/extend
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this before escalating to ActiveMQ for a `CommandsDispatcher` minute. If the same window keeps resolving to journal refresh, `/FireFlow/api/session`, or `/session/extend`, treat it as synchronous maintenance-style traffic and keep broker inspection later.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check whether the branch is config broadcast plus FireFlow auth bootstrap</p>

<p class="adf-inline-label">Run</p>

```bash
grep -E 'application-afaConfig.properties|notify ActiveMq broadcast|MicroserviceConfigurationBroadcast|Refreshing application context' /data/algosec-ms/logs/ms-configuration.log /data/algosec-ms/logs/ms-initial-plan.log | tail -n 60; echo '--- fireflow ---'; grep -E 'authenticateUser|GetUserInfo' /usr/share/fireflow/var/log/fireflow.log /usr/share/fireflow/var/log/fireflow.log.1 /usr/share/fireflow/var/log/fireflow.log.2 2>/dev/null | tail -n 40
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The returned window shows whether the same FireFlow minute is really a config-broadcast ripple with nearby authentication and user bootstrap rather than a ticket-progression branch.
</p>

<p class="adf-check-reference">
Check output for: application-afaConfig.properties, MicroserviceConfigurationBroadcast, authenticateUser, GetUserInfo
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this when a non-`UserSession` dispatcher destination appears, but the nearby minute still looks like setup work. If config broadcast, `MicroserviceConfigurationBroadcast`, `Authentication:authenticateUser`, and `User:GetUserInfo` cluster together, classify the branch as config-propagation plus auth bootstrap and keep approval, worker, or broker escalation later.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check whether FireFlow is active but the lab has zero tickets</p>

<p class="adf-inline-label">Run</p>

```bash
grep -E 'Total tickets in DB|tickets updated in the last 10 minutes|setup/fireflow/is_enabled|allowedDevices|brandConfig' /usr/share/fireflow/var/log/fireflow.log /usr/share/fireflow/var/log/fireflow.log.1 /usr/share/fireflow/var/log/fireflow.log.2 2>/dev/null | tail -n 80; echo '--- apache ---'; grep -E '/setup/fireflow/is_enabled|/allowedDevices|/bridge/refresh|/config/all/noauth' /var/log/httpd/ssl_access_log | tail -n 40
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The returned window shows whether FireFlow is enabled and polling neighboring dependencies successfully while still reporting zero tickets in DB.
</p>

<p class="adf-check-reference">
Check output for: Total tickets in DB: 0, setup/fireflow/is_enabled, allowedDevices, brandConfig
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this when FireFlow looks enabled but every progression hunt collapses back into setup, config, AFF bridge, and session-maintenance traffic. If the same windows show `Total tickets in DB: 0` or no recent ticket updates, stop treating the lab as a populated workflow environment. Seed or replay one real FireFlow request before another approval, implementation, review, or ActiveMQ-oriented slice.
</p>

</div>

  </div>
  </div>
</details>
  </section>
</div>

## If this boundary still looks unhealthy

- Keep the case on this service and escalate with the saved evidence.

## If this boundary looks healthy

- If Aff-Boot.Service looks healthy, move to the deeper ASMS guide for the next layer.

## What to save

- Result of the failing FireFlow action, including the exact endpoint or screen.
- Visible status for aff-boot.service and postgresql.service.
- Any recent FireFlow-related lines from the customer-facing logs or service status output.
- If the same minute rolls into `/FireFlow/api/swagger/v2/api-docs` or unified service-definition refresh, capture matching `ms-configuration` and Apache `ssl_error_log` lines before promoting ActiveMQ.

## When to escalate

- Keep the case on this service and escalate with the saved evidence.
- Escalate after the bounded checks and any approved safe restart step if the saved evidence still points to this boundary.

## Optional deeper notes

Use this page to prove the FireFlow backend boundary first, separate Apache route ownership from aff-boot runtime health, and gather a support-ready evidence packet before widening into later workflow or broker theory.

### Observed boundary on this appliance

- Apache owns the newer FireFlow session edge and proxies `/FireFlow/api` and `/aff/api` into aff-boot on `1989`.
- The closest readable backend seam for this path is aff-boot plus its direct route ownership, not generic FireFlow workflow theory.
- Current lab evidence keeps PostgreSQL closer than ActiveMQ for first-pass troubleshooting even though aff-boot can also hold live broker sockets on `61616`.

### What that boundary means in ASMS

- If the Apache-fronted FireFlow session path and the direct `1989` AFF session path disagree, stop on Apache proxying or aff-boot route ownership before widening.
- If the routes match but the action still fails, the next support seam is the FireFlow session or config boundary, not a generic broker-first guess.
- Treat ActiveMQ as later supporting evidence unless the same failing minute points directly at broker-side behavior.

### Generic failure classes

- `route_proxy_mismatch`: Use this when `/FireFlow/api` no longer matches the direct `1989` AFF session path or Apache route ownership drifted.
- `aff_boot_unhealthy`: Use this when `aff-boot.service` is down, flapping, or not holding the expected `1989` listener.
- `session_parity_drift`: Use this when the Apache-fronted session path and the direct AFF session path stop returning the same invalid-session or session-shape response.
- `downstream_config_refresh`: Use this when the same failing minute rolls into `ms-configuration`, swagger refresh, or downstream `502` clues after the FireFlow route itself still looks healthy.
- `later_broker_or_database_supporting`: Use this when route ownership and aff-boot look healthy but the current evidence starts pointing at PostgreSQL or broker-side supporting dependencies.

### Bounded next checks

- Prove Apache-fronted `/FireFlow/api/session` parity against the direct `1989` AFF session path first.
- Check `aff-boot.service`, the `1989` listener, and PostgreSQL state before widening into later FireFlow workflow theory.
- Only promote ActiveMQ when the same failing minute points directly at broker-side evidence instead of route or service ownership.

### Escalation-ready evidence

- The exact failing FireFlow action, route, or screen
- Visible status for `aff-boot.service` and `postgresql.service`
- Apache-fronted and direct `1989` session probe outputs from the same troubleshooting minute
- Same-minute Apache, FireFlow, or `ms-configuration` lines that show where the route stops doing useful work

