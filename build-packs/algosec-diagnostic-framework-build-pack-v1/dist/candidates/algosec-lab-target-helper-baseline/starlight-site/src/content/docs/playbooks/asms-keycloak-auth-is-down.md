---
title: ASMS Keycloak auth is down
description: ""
sidebar:
  label: ASMS Keycloak auth is down
  order: 5
---

Use this when the login page still opens but ASMS auth looks down, loops, or returns an auth error.

## Imported-module drilldown

Use this page to prove the Keycloak boundary first, classify the failure, and gather a support-ready evidence packet before you widen the case.

### Observed boundary on this appliance

- Apache can still serve `https://127.0.0.1/algosec-ui/login` while the proxied Keycloak OIDC path is unhealthy.
- Keycloak service state, listener `8443`, and the OIDC well-known probe together define whether the auth module can still do useful work.
- Use current appliance evidence first. In the validated March 30, 2026 slice on `10.167.2.150`, the login page stayed `200`, the Keycloak OIDC path returned `503`, `keycloak.service` was failed, `8443` was absent, and Metro still reported `isAlive: true`.

### What that boundary means in ASMS

- The browser-facing UI edge is still alive enough to serve the login page, so this is not yet a top-level Apache outage.
- Keycloak sits behind Apache as the imported auth module boundary for this path. If the login page works but the OIDC path does not, keep the case on Keycloak before widening into unrelated services.
- Metro can help separate auth failure from deeper app failure, but a healthy Metro heartbeat does not make Keycloak healthy again.

### Generic failure classes

- `startup_failure`: Use this when `keycloak.service` exits, flaps, or never reaches `active`. Journal and service-status clues belong here.
- `listener_absent`: Use this when the expected local Keycloak listener on `8443` is missing even though Apache still points there.
- `useful_work_path_failed`: Use this when the service may look present but the OIDC path still fails, loops, or returns unhealthy HTTP while the login page still loads.
- `apache_proxy_mismatch`: Use this when `/keycloak/` is no longer mapped to `https://localhost:8443/` or the proxy path itself drifted.
- `dependency_or_resource_unknown`: Use this when the Keycloak boundary is proven but the current slice still cannot tell whether the real cause is config, filesystem, secret, database, or host pressure.

### Bounded next checks

- Classify the module first: service state, listener state, OIDC useful-work check, and proxy path.
- Keep the next support step on the smallest failing Keycloak boundary instead of widening back into Apache or later ASMS modules too early.
- If the boundary is still unresolved after the shallow checks, gather the escalation packet and only then branch into deeper module-specific interpretation.

### Escalation-ready evidence

- `systemctl status keycloak.service --no-pager` and `systemctl show keycloak.service ...` output
- Listener output for `8443`
- The paired login-page and OIDC probe outputs from the same troubleshooting minute
- Apache proxy evidence showing whether `/keycloak/` still maps to `https://localhost:8443/`
- Recent Keycloak journal lines that show the startup or runtime clue
- Any supporting separation clue such as Metro heartbeat when the customer reports a broader UI symptom

### Upstream references

- [Keycloak documentation](https://www.keycloak.org/documentation): Use this after the appliance evidence proves the Keycloak boundary and you need bounded interpretation of Keycloak server behavior.
- [Keycloak server configuration guide](https://www.keycloak.org/server/configuration): Use this for deeper configuration or startup interpretation only after the local service and listener checks narrow the failure class.

## Command flow

<div class="adf-preview-shell adf-preview-field-manual">
  <section class="adf-preview-manual-cover">
    <h2>ASMS Keycloak auth is down</h2>
  </section>
  <section class="adf-preview-manual-contents">
    <p class="adf-panel-label">Steps</p>
    <ol class="adf-preview-manual-list">
<li><a href="#manual-keycloak-step-1"><span>Step 1</span><strong>Check the login page and the Keycloak OIDC path together</strong></a></li>
<li><a href="#manual-keycloak-step-2"><span>Step 2</span><strong>Check Keycloak service state and the local 8443 listener</strong></a></li>
<li><a href="#manual-keycloak-step-3"><span>Step 3</span><strong>Check the Apache proxy path for Keycloak</strong></a></li>
<li><a href="#manual-keycloak-step-4"><span>Step 4</span><strong>Check recent failure clues from the service journal</strong></a></li>
<li><a href="#manual-keycloak-step-5"><span>Step 5</span><strong>Restart Keycloak only when the service is down or failed</strong></a></li>
    </ol>
  </section>
  <section class="adf-preview-manual-body">
<details id="manual-keycloak-step-1" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 1</span>
      <span class="adf-preview-manual-summary-title">Check login page and OIDC path</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Compare login page and Keycloak OIDC</p>

<p class="adf-inline-label">Run</p>

```bash
curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'; echo '---'; curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration | sed -n '1,12p'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The login page returns HTTP 200 and the Keycloak OIDC path also returns HTTP 200.
</p>

<p class="adf-check-reference">
Check output for: HTTP/1.1 200
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the login page is still HTTP 200 but the Keycloak OIDC path returns 503 or another failure, save both outputs and diagnose Keycloak instead of Apache.
</p>

<p class="adf-inline-label">Example</p>

```text
HTTP/1.1 200 OK
---
HTTP/1.1 200 OK
```
</div>

  </div>
  </div>
</details>
<details id="manual-keycloak-step-2" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 2</span>
      <span class="adf-preview-manual-summary-title">Check Keycloak service</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check Keycloak service and 8443 listener</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status keycloak.service --no-pager; echo '--- listeners ---'; ss -lntp | grep -E ':(8443)\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Keycloak is active and a Java process is listening on port 8443.
</p>

<p class="adf-check-reference">
Check output for: Active: active (running), LISTEN, :8443
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If keycloak.service is failed or 8443 is missing, keep the stop point on Keycloak.
</p>

<p class="adf-inline-label">Example</p>

```text
● keycloak.service - Keycloak Service
   Active: active (running)
--- listeners ---
LISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:(("java",pid=2745,fd=91))
```
</div>

  </div>
  </div>
</details>
<details id="manual-keycloak-step-3" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 3</span>
      <span class="adf-preview-manual-summary-title">Check Apache proxy</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check Apache Keycloak proxy config</p>

<p class="adf-inline-label">Run</p>

```bash
grep -R -n -E '<Location /keycloak/|ProxyPass https://localhost:8443/|ProxyPassReverse https://localhost:8443/' /etc/httpd/conf.d 2>/dev/null
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Apache still exposes /keycloak/ and proxies it to https://localhost:8443/.
</p>

<p class="adf-check-reference">
Check output for: <Location /keycloak/>, ProxyPass https://localhost:8443/, ProxyPassReverse https://localhost:8443/
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If these proxy lines are missing, save the output and diagnose Apache Keycloak proxy configuration before going deeper into the service.
</p>

<p class="adf-inline-label">Example</p>

```text
/etc/httpd/conf.d/keycloak.conf:1:<Location /keycloak/>
/etc/httpd/conf.d/keycloak.conf:2:        ProxyPass https://localhost:8443/ timeout=300
/etc/httpd/conf.d/keycloak.conf:3:        ProxyPassReverse https://localhost:8443/
```
</div>

  </div>
  </div>
</details>
<details id="manual-keycloak-step-4" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 4</span>
      <span class="adf-preview-manual-summary-title">Check failure clues</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check recent Keycloak journal clues</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u keycloak.service -n 80 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent lines show Keycloak starting normally or show the failure clue that explains why it did not come up.
</p>

<p class="adf-check-reference">
Check output for: started, Listening on, 8443
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If you see repeated startup failures such as java.io.EOFException or exit-code failure, save the output and keep the case on the Keycloak service boundary.
</p>

<p class="adf-inline-label">Example</p>

```text
Exception in thread "main" java.lang.reflect.UndeclaredThrowableException
Caused by: java.io.EOFException
... SerializedApplication.read(...)
... QuarkusEntryPoint.doRun(...)
keycloak.service: Main process exited, status=1/FAILURE
```
</div>

  </div>
  </div>
</details>
<details id="manual-keycloak-step-5" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 5</span>
      <span class="adf-preview-manual-summary-title">Restart Keycloak</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Restart Keycloak and recheck auth</p>

<p class="adf-inline-label">Run</p>

```bash
sudo systemctl restart keycloak.service && sleep 30 && systemctl is-active keycloak.service && ss -lntp | grep -E ':(8443)\b' && curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration | sed -n '1,12p'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Keycloak returns to active, 8443 is listening again, and the OIDC path returns HTTP 200.
</p>

<p class="adf-check-reference">
Check output for: active, LISTEN, :8443, HTTP/1.1 200
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the service still fails, 8443 does not return, or the OIDC path stays unhealthy, save all output and keep the case on Keycloak.
</p>

<p class="adf-inline-label">Example</p>

```text
active
LISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:(("java",pid=2745,fd=91))
HTTP/1.1 200 OK
```
</div>

  </div>
  </div>
</details>
  </section>
</div>

