---
title: ASMS Keycloak auth is down
description: ""
sidebar:
  label: ASMS Keycloak auth is down
  order: 2
---

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

