---
title: ASMS UI is down
description: ""
sidebar:
  label: ASMS UI is down
  order: 1
---

## Command flow

<div class="adf-preview-shell adf-preview-field-manual">
  <section class="adf-preview-manual-cover">
    <h2>ASMS UI is down</h2>
  </section>
  <section class="adf-preview-manual-contents">
    <p class="adf-panel-label">Steps</p>
    <ol class="adf-preview-manual-list">
<li><a href="#manual-ui-and-proxy-step-1"><span>Step 1</span><strong>Check host pressure</strong></a></li>
<li><a href="#manual-ui-and-proxy-step-2"><span>Step 2</span><strong>Check Apache and login page</strong></a></li>
<li><a href="#manual-ui-and-proxy-step-3"><span>Step 3</span><strong>Check core services</strong></a></li>
<li><a href="#manual-ui-and-proxy-step-4"><span>Step 4</span><strong>Check shell access</strong></a></li>
<li><a href="#manual-ui-and-proxy-step-5"><span>Step 5</span><strong>Check later workflow markers</strong></a></li>
    </ol>
  </section>
  <section class="adf-preview-manual-body">
<details id="manual-ui-and-proxy-step-1" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 1</span>
      <span class="adf-preview-manual-summary-title">Check host pressure</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check host pressure</p>

<p class="adf-inline-label">Run</p>

```bash
uptime && free -h && df -h /
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Load is reasonable, memory is available, and the root filesystem is not full.
</p>

<p class="adf-check-reference">
Check output for: load average, Mem:, Filesystem
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If load is high, memory is low, or disk is full, save the output and troubleshoot server pressure before checking the application.
</p>

<p class="adf-inline-label">Example</p>

```text
load average: 0.32, 0.41, 0.55
Mem: 16Gi 6.1Gi 4.1Gi 120Mi 5.5Gi 9.1Gi
/dev/sda1 80G 31G 47G 40% /
```
</div>

  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-2" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 2</span>
      <span class="adf-preview-manual-summary-title">Check Apache and login page</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check Apache service, listeners, and login page</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl is-active httpd && ss -lnt | grep -E ':(80|443)\b' && curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Apache is active, ports 80 and 443 are listening, and the login page returns an expected HTTP response.
</p>

<p class="adf-check-reference">
Check output for: active, :80, :443, HTTP/1.1 200
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If httpd is not active, ports 80 or 443 are missing, or the login page does not return HTTP 200, save the output and diagnose Apache/HTTPD.
</p>

<p class="adf-inline-label">Example</p>

```text
active
LISTEN 0 511 0.0.0.0:443 0.0.0.0:*
LISTEN 0 511 0.0.0.0:80 0.0.0.0:*
HTTP/1.1 200 OK
```
</div>

  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-3" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 3</span>
      <span class="adf-preview-manual-summary-title">Check core services</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check the shallow core services once</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl is-active httpd; systemctl is-active ms-metro; systemctl is-active keycloak
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The shallow services are active. If one is inactive, that is the current stop point.
</p>

<p class="adf-check-reference">
Check output for: active
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If one service is not active, save the service name and status. Diagnose or restart only that service.
</p>

<p class="adf-inline-label">Example</p>

```text
active
active
active
```
</div>

<div class="adf-check">
<p class="adf-check-label">Restart Apache only if Apache failed</p>

<p class="adf-inline-label">Run</p>

```bash
sudo systemctl restart httpd.service && sleep 5 && systemctl is-active httpd.service && curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Apache returns to active and the login page answers again.
</p>

<p class="adf-check-reference">
Check output for: active, HTTP/1.1 200
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Run this only if Apache failed in the previous check.
</p>

<p class="adf-inline-label">Example</p>

```text
active
HTTP/1.1 200 OK
```
</div>

<div class="adf-check">
<p class="adf-check-label">Restart Metro only if the shell is blank or partly loaded</p>

<p class="adf-inline-label">Run</p>

```bash
sudo systemctl restart ms-metro.service && sleep 10 && systemctl is-active ms-metro.service && curl -sS http://127.0.0.1:8080/afa/getStatus --max-time 10
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Metro returns to active and the heartbeat answers.
</p>

<p class="adf-check-reference">
Check output for: active, "isAlive" : true
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Run this only if the login page works but the shell is blank, partial, or not loading correctly.
</p>

<p class="adf-inline-label">Example</p>

```text
active
{
  "isAlive" : true
}
```
</div>

  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-4" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 4</span>
      <span class="adf-preview-manual-summary-title">Check shell access</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check the login page and home-shell clues</p>

<p class="adf-inline-label">Run</p>

```bash
curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'; echo '---'; grep -E '/afa/php/SuiteLoginSessionValidation.php|/afa/php/home.php' /var/log/httpd/ssl_access_log | tail -n 20
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The login page answers, and recent log lines show whether the session ever reached SuiteLoginSessionValidation or /afa/php/home.php.
</p>

<p class="adf-check-reference">
Check output for: HTTP/1.1 200, SuiteLoginSessionValidation.php, /afa/php/home.php
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the login page answers or /afa/php/home.php appears, save that evidence and continue with shell or workflow diagnosis.
</p>

<p class="adf-inline-label">Example</p>

```text
HTTP/1.1 200 OK
---
127.0.0.1 - - [28/Mar/2026:19:27:29 -0400] "GET /afa/php/home.php?segment=DEVICES HTTP/1.1" 200 328934
```
</div>

  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-5" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 5</span>
      <span class="adf-preview-manual-summary-title">Check later workflow markers</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Look for later content markers</p>

<p class="adf-inline-label">Run</p>

```bash
grep -E '/fa/tree/create|/afa/php/commands.php\?cmd=(GET_REPORTS|GET_POLICY_TAB|GET_DEVICE_POLICY|GET_MONITORING_CHANGES|GET_ANALYSIS_OPTIONS)' /var/log/httpd/ssl_access_log | tail -n 40
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent Apache lines show device-tree activity plus a later content marker like GET_REPORTS, GET_POLICY_TAB, or GET_MONITORING_CHANGES.
</p>

<p class="adf-check-reference">
Check output for: /fa/tree/create, GET_REPORTS, GET_POLICY_TAB, GET_DEVICE_POLICY, GET_MONITORING_CHANGES, GET_ANALYSIS_OPTIONS
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If one of these markers appears, save the marker and continue with the matching workflow diagnosis.
</p>

<p class="adf-inline-label">Example</p>

```text
127.0.0.1 - - [28/Mar/2026:19:27:30 -0400] "GET /afa/php/commands.php?cmd=GET_REPORTS HTTP/1.1" 200 99
```
</div>

  </div>
  </div>
</details>
  </section>
</div>

