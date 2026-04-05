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
<li><a class="adf-preview-manual-link" href="/playbooks/asms-ui-is-down/#manual-ui-and-proxy-step-1" data-adf-manual-target="manual-ui-and-proxy-step-1"><span>Step 1</span><strong>Check host pressure first</strong></a></li>
<li><a class="adf-preview-manual-link" href="/playbooks/asms-ui-is-down/#manual-ui-and-proxy-step-2" data-adf-manual-target="manual-ui-and-proxy-step-2"><span>Step 2</span><strong>Check Apache login route</strong></a></li>
<li><a class="adf-preview-manual-link" href="/playbooks/asms-ui-is-down/#manual-ui-and-proxy-step-3" data-adf-manual-target="manual-ui-and-proxy-step-3"><span>Step 3</span><strong>Check shallow core services</strong></a></li>
<li><a class="adf-preview-manual-link" href="/playbooks/asms-ui-is-down/#manual-ui-and-proxy-step-4" data-adf-manual-target="manual-ui-and-proxy-step-4"><span>Step 4</span><strong>Check first usable shell</strong></a></li>
<li><a class="adf-preview-manual-link" href="/playbooks/asms-ui-is-down/#manual-ui-and-proxy-step-5" data-adf-manual-target="manual-ui-and-proxy-step-5"><span>Step 5</span><strong>Check later branch markers</strong></a></li>
    </ol>
  </section>
  <section class="adf-preview-manual-body">
<details id="manual-ui-and-proxy-step-1" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 1</span>
      <span class="adf-preview-manual-summary-title">Check host pressure first</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">6 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check storage pressure on runtime filesystems</p>

<p class="adf-inline-label">Run</p>

```bash
df -h
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Runtime filesystems still have enough free space for logs, temp files, and service work.
</p>

<p class="adf-check-reference">
Check output for: Use% below 100%, Avail is not 0, / and /data still have free space
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If /, /boot, or /data is close to full, Apache, Keycloak, Metro, installers, and log writers can all fail or behave unpredictably.
</p>

<p class="adf-inline-label">Example</p>

```text
Filesystem           Size  Used Avail Use% Mounted on
/dev/mapper/rl-root   60G   16G   45G  27% /
/dev/mapper/rl-data  238G   21G  218G   9% /data
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check inode pressure on runtime filesystems</p>

<p class="adf-inline-label">Run</p>

```bash
df -ih
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Runtime filesystems still have free inodes for logs, temp files, sockets, and service output.
</p>

<p class="adf-check-reference">
Check output for: IUse% below 100%, IFree is not 0, / and /data still have free inodes
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If inode use is high, the host can look like it has free disk while Apache, Keycloak, Metro, or log rotation still fail to create files.
</p>

<p class="adf-inline-label">Example</p>

```text
Filesystem          Inodes IUsed IFree IUse% Mounted on
/dev/mapper/rl-root    30M  343K   30M    2% /
/dev/mapper/rl-data   119M   21K  119M    1% /data
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check memory pressure on JVM-backed services</p>

<p class="adf-inline-label">Run</p>

```bash
free -h
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Available memory is still present and swap is not carrying active pressure for the host.
</p>

<p class="adf-check-reference">
Check output for: available memory is present, swap is not exhausted, Mem and Swap are shown in GiB
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If available memory is very low or swap is heavily used, Java services like Keycloak and Metro may slow down, hang, fail health checks, or get killed later.
</p>

<p class="adf-inline-label">Example</p>

```text
              total        used        free      shared  buff/cache   available
Mem:           32Gi        13Gi       8.6Gi       2.4Gi         9Gi        15Gi
Swap:          24Gi          0B        24Gi
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check current host load pressure</p>

<p class="adf-inline-label">Run</p>

```bash
uptime
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Load is not unexpectedly high for the host and does not already explain the UI symptom.
</p>

<p class="adf-check-reference">
Check output for: load average:, load values are not unexpectedly high
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If load is unusually high, the system may be under CPU pressure, blocked work, or heavy I/O wait before you even reach the UI-specific branches.
</p>

<p class="adf-inline-label">Example</p>

```text
14:42:03 up 17 days,  1:52,  1 user,  load average: 0.25, 0.18, 0.11
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check recent memory-kill pressure</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -k --since "24 hours ago" --no-pager | grep -i -E "out of memory|oom|killed process"
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
No recent Out Of Memory lines are returned.
</p>

<p class="adf-check-reference">
Check output for: No output is normal, No 'Out of memory' lines, No 'Killed process' lines
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If OOM lines appear, the host has already been killing or starving processes under memory pressure, so downstream UI symptoms may only be the visible side effect.
</p>

<p class="adf-inline-label">Example</p>

```text
No output
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check which process owns CPU pressure right now</p>

<p class="adf-inline-label">Run</p>

```bash
ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -n 10
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
No unexpected process is consuming enough CPU to starve the rest of the ASMS path.
</p>

<p class="adf-check-reference">
Check output for: PID, COMMAND, %CPU, %MEM
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If one process is consuming most of the CPU, treat that process as part of the current system pressure story before assuming the UI path itself is the root cause.
</p>

<p class="adf-inline-label">Example</p>

```text
  PID COMMAND         %CPU %MEM
 6012 java             8.1  7.4
 1018 httpd            1.2  0.4
 3758 algosec_keycloa  0.8  1.6
```
</div>

  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-2" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 2</span>
      <span class="adf-preview-manual-summary-title">Check Apache login route</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">6 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check httpd.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status httpd.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-reference">
Check output for: Loaded: loaded, Active: active (running), Main PID:, /usr/sbin/httpd
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If this is not active, treat the edge service itself as the failure point before going deeper.
</p>

<p class="adf-inline-label">Example</p>

```text
● httpd.service - The Apache HTTP Server
   Loaded: loaded (/usr/lib/systemd/system/httpd.service; enabled; vendor preset: disabled)
   Active: active (running) since Sat 2026-03-07 13:37:12 EST; 2 weeks 2 days ago
 Main PID: 1018 (/usr/sbin/httpd)
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check edge listeners</p>

<p class="adf-inline-label">Run</p>

```bash
ss -lntp | grep -E ':(80|443)\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
A listening socket is present for 80, 443.
</p>

<p class="adf-check-reference">
Check output for: LISTEN, :80, :443, httpd
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If 80/443 are missing, the UI path is failing at the listener or bind layer.
</p>

<p class="adf-inline-label">Example</p>

```text
LISTEN 0 511 0.0.0.0:443 0.0.0.0:* users:(("/usr/sbin/httpd",pid=1018,fd=4),...)
LISTEN 0 511 0.0.0.0:80  0.0.0.0:* users:(("/usr/sbin/httpd",pid=1018,fd=3),...)
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check the legacy suite login route</p>

<p class="adf-inline-label">Run</p>

```bash
curl -k -I --max-time 5 https://127.0.0.1/algosec/suite/login
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Apache returns a redirect from the legacy suite login path into the current UI login page.
</p>

<p class="adf-check-reference">
Check output for: HTTP/1.1 302, Server: Apache, Location: https://127.0.0.1/algosec-ui/login
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the suite login route stops redirecting here, the edge path is already broken before Keycloak or Metro have a chance to help.
</p>

<p class="adf-inline-label">Example</p>

```text
HTTP/1.1 302 Found
Server: Apache
Location: https://127.0.0.1/algosec-ui/login
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check the Apache-served UI login page</p>

<p class="adf-inline-label">Run</p>

```bash
curl -k -I --max-time 5 https://127.0.0.1/algosec-ui/login
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Apache returns the current UI login page with HTTP 200.
</p>

<p class="adf-check-reference">
Check output for: HTTP/1.1 200, Server: Apache, Content-Type: text/html
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If Apache cannot serve the login page here, stop at the edge before chasing the auth or app neighbors.
</p>

<p class="adf-inline-label">Example</p>

```text
HTTP/1.1 200 OK
Server: Apache
Content-Type: text/html; charset=UTF-8
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check representative /algosec-ui/ assets through Apache</p>

<p class="adf-inline-label">Run</p>

```bash
for path in /algosec-ui/styles.css /algosec-ui/runtime.js /algosec-ui/main.js; do echo "=== $path ==="; curl -k -sS -D - -o /tmp/asms-ui-asset.out "https://127.0.0.1$path" | sed -n '1,8p'; printf 'BODY_BYTES '; wc -c < /tmp/asms-ui-asset.out; done
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Apache returns HTTP 200 for representative CSS and JS assets and each body is non-empty.
</p>

<p class="adf-check-reference">
Check output for: HTTP/1.1 200, Server: Apache, Content-Type: text/css, Content-Type: application/javascript, BODY_BYTES
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the login HTML works but these assets fail, return the wrong type, or come back empty, the login page is still not healthy before Keycloak or Metro are checked.
</p>

<p class="adf-inline-label">Example</p>

```text
=== /algosec-ui/styles.css ===
HTTP/1.1 200 OK
Server: Apache
Content-Type: text/css
BODY_BYTES 758180
=== /algosec-ui/runtime.js ===
HTTP/1.1 200 OK
Content-Type: application/javascript
BODY_BYTES 2737
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check Apache routes for login, auth, and app branches</p>

<p class="adf-inline-label">Run</p>

```bash
grep -R -n -E 'algosec-ui|algosec/suite|ProxyPass|ProxyPassReverse|keycloak|8443|afa/api/v1|8080' /etc/httpd/conf.d 2>/dev/null
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Apache config still shows the login redirect, the UI alias, and the auth and app route mapping needed by the ASMS UI path.
</p>

<p class="adf-check-reference">
Check output for: algosec/suite, algosec-ui, ProxyPass, keycloak, 8443, afa/api/v1, 8080
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the expected proxy targets are missing or wrong, the login path can look healthy while routing requests to the wrong place or nowhere useful.
</p>

<p class="adf-inline-label">Example</p>

```text
78:RewriteRule "^/algosec/suite/login(.*)$" "/algosec-ui/login" [R]
299:AliasMatch (?i)^/algosec-ui/(.*)$ /usr/share/fa/suite/client/app/suite-new-ui/$1
1:<Location /keycloak/>
2:        ProxyPass https://localhost:8443/ timeout=300
139:<Location /afa/api/v1>
140:  ProxyPass http://localhost:8080/afa/api/v1 timeout=18000 retry=0
```
</div>

  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-3" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 3</span>
      <span class="adf-preview-manual-summary-title">Check shallow core services</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">7 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check httpd.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status httpd.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-reference">
Check output for: Loaded: loaded, Active: active (running), Main PID:, /usr/sbin/httpd
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If Apache is not active, the UI outage already has a clear owner. Restart Apache first, then retest the login page before you widen scope.
</p>

<p class="adf-inline-label">Example</p>

```text
● httpd.service - The Apache HTTP Server
   Loaded: loaded (/usr/lib/systemd/system/httpd.service; enabled; vendor preset: disabled)
   Active: active (running) since Thu 2026-03-26 18:42:56 EDT; 17h ago
 Main PID: 1018 (/usr/sbin/httpd)
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check keycloak.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status keycloak.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-reference">
Check output for: Loaded: loaded, Active: active (running), Main PID:, java
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this as a shallow auth-service presence check only. If the login page loads but auth seems down and Keycloak is not active, stop here before deeper bootstrap tracing.
</p>

<p class="adf-inline-label">Example</p>

```text
● keycloak.service - Keycloak Service
   Loaded: loaded (/etc/systemd/system/keycloak.service; enabled; vendor preset: disabled)
   Active: active (running) since Thu 2026-03-26 18:43:11 EDT; 17h ago
 Main PID: 2745 (java)
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check ms-metro.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status ms-metro.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-reference">
Check output for: Loaded: loaded, Active: active (running), Main PID:, java
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the login page is up but the app shell is blank or only partly usable, Metro is the first app-side shallow check and restart boundary.
</p>

<p class="adf-inline-label">Example</p>

```text
● ms-metro.service - ms-metro Application Container
   Loaded: loaded (/etc/systemd/system/ms-metro.service; disabled; vendor preset: disabled)
   Active: active (running) since Sat 2026-03-07 13:39:32 EST; 2 weeks 2 days ago
 Main PID: 6012 (java)
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check the wrapper and listener surfaces once</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status algosec-ms.service --no-pager; echo '--- listeners ---'; ss -lntp | grep -E ':(80|443|8080|8443)\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The wrapper unit is present, and the expected shallow listeners remain present on `80`, `443`, `8080`, and `8443`.
</p>

<p class="adf-check-reference">
Check output for: Active: active (exited), LISTEN, :80, :443, :8080, :8443
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
On this appliance `algosec-ms.service` can be `active (exited)` and still be healthy as a wrapper. The real value here is confirming the main shallow listeners are still present before you blame deeper auth or app logic.
</p>

<p class="adf-inline-label">Example</p>

```text
● algosec-ms.service - AlgoSec Platform Wrapper
   Active: active (exited)
--- listeners ---
LISTEN 0 511 0.0.0.0:443 0.0.0.0:* users:(("/usr/sbin/httpd",pid=1018,fd=4),...)
LISTEN 0 100 0.0.0.0:8080 0.0.0.0:* users:(("java",pid=6012,fd=44))
LISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:(("java",pid=2745,fd=91))
```
</div>

<div class="adf-check">
<p class="adf-check-label">Restart Apache only if the UI edge check failed</p>

<p class="adf-inline-label">Run</p>

```bash
sudo systemctl restart httpd.service && sleep 5 && systemctl is-active httpd.service && curl -k -sS -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Apache returns to `active`, and the login page immediately answers again through localhost HTTPS.
</p>

<p class="adf-check-reference">
Check output for: active, HTTP/1.1 200, Server: Apache
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this only when the earlier Apache route or status checks failed. Do not spray restarts across other services if Apache already looks healthy.
</p>

<p class="adf-inline-label">Example</p>

```text
active
HTTP/1.1 200 OK
Server: Apache
```
</div>

<div class="adf-check">
<p class="adf-check-label">Restart Keycloak only if the login page loads but auth service looks down</p>

<p class="adf-inline-label">Run</p>

```bash
sudo systemctl restart keycloak.service && sleep 10 && systemctl is-active keycloak.service && ss -lntp | grep -E ':8443\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Keycloak returns to `active`, and the auth listener on `8443` is present again.
</p>

<p class="adf-check-reference">
Check output for: active, LISTEN, :8443
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this only when the customer can reach the login page but the auth service itself is down or hung. If the login page is not loading at all, Apache is still the earlier stop point.
</p>

<p class="adf-inline-label">Example</p>

```text
active
LISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:(("java",pid=2745,fd=91))
```
</div>

<div class="adf-check">
<p class="adf-check-label">Restart Metro only if the UI reaches the app shell but it is blank or partly loaded</p>

<p class="adf-inline-label">Run</p>

```bash
sudo systemctl restart ms-metro.service && sleep 10 && systemctl is-active ms-metro.service && curl -sS http://127.0.0.1:8080/afa/getStatus --max-time 10
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Metro returns to `active`, and the heartbeat shows `"isAlive" : true`.
</p>

<p class="adf-check-reference">
Check output for: active, "isAlive" : true
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this only after the case has clearly crossed beyond the login page and the app shell still looks broken. Do not restart Metro first for a pure edge outage.
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
<details id="manual-ui-and-proxy-step-4" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 4</span>
      <span class="adf-preview-manual-summary-title">Check first usable shell</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">9 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check ms-metro.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status ms-metro.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-reference">
Check output for: Loaded: loaded, Active: active (running), Main PID:, java
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If Metro is not running, the UI may open only partly or fail after the first page.
</p>

<p class="adf-inline-label">Example</p>

```text
● ms-metro.service - ms-metro Application Container
   Loaded: loaded (/etc/systemd/system/ms-metro.service; disabled; vendor preset: disabled)
   Active: active (running) since Sat 2026-03-07 13:39:32 EST; 2 weeks 2 days ago
 Main PID: 6012 (java)
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check Metro listener</p>

<p class="adf-inline-label">Run</p>

```bash
ss -lntp | grep -E ':8080\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Port 8080 is listening for ms-metro.
</p>

<p class="adf-check-reference">
Check output for: LISTEN, :8080, java
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If port 8080 is missing, the UI backend route has no working target.
</p>

<p class="adf-inline-label">Example</p>

```text
LISTEN 0 100 0.0.0.0:8080 0.0.0.0:* users:(("java",pid=6012,fd=44))
```
</div>

<div class="adf-check">
<p class="adf-check-label">Compare the first usable shell gate with Metro bootstrap clues</p>

<p class="adf-inline-label">Run</p>

```bash
minute=$(grep -E '/afa/php/SuiteLoginSessionValidation.php|/afa/php/home.php|dynamic\.js\.php|/afa/php/home.js' /var/log/httpd/ssl_access_log | tail -n 1 | sed -E 's/.*\[([^]]{17})[^]]*\].*/\1/'); printf 'WINDOW=%s\n' "$minute"; printf '=== apache shell minute ===\n'; grep "$minute" /var/log/httpd/ssl_access_log | grep -E '/afa/php/SuiteLoginSessionValidation.php|/afa/php/home.php|dynamic\.js\.php|/afa/php/home.js' | tail -n 20; printf '=== metro same minute ===\n'; grep "$minute" /data/ms-metro/logs/localhost_access_log.txt | grep -E '/afa/getStatus|/afa/api/v1/config\?|/afa/api/v1/session/extend|/afa/api/v1/config/all/noauth' | tail -n 20
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The same shell-transition minute shows `SuiteLoginSessionValidation.php -> /afa/php/home.php -> dynamic.js.php/home.js` on the Apache side and the nearest Metro bootstrap clues such as `GET /afa/getStatus`, `GET /afa/api/v1/config?...`, `POST /afa/api/v1/session/extend?...`, or `GET /afa/api/v1/config/all/noauth?...` on the Metro side.
</p>

<p class="adf-check-reference">
Check output for: WINDOW=, /afa/php/SuiteLoginSessionValidation.php, /afa/php/home.php, dynamic.js.php, GET /afa/getStatus, /afa/api/v1/session/extend, /afa/api/v1/config/all/noauth
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this to keep the stop point narrow and same-window. If `SuiteLoginSessionValidation.php` appears but `/afa/php/home.php` does not appear in that same minute, stop on the pre-shell gate before blaming Metro. If `/afa/php/home.php` appears but the same-minute Metro bootstrap clues are missing or failing, stop on the Metro-backed home-shell path. If both sides look healthy in the same shell-transition minute, stop calling the case `GUI down` and branch into the later failing workflow instead. This is still a comparison check, not proof that every nearby Metro route is a hard first-shell dependency.
</p>

<p class="adf-inline-label">Example</p>

```text
WINDOW=25/Mar/2026:17:29
=== apache shell minute ===
127.0.0.1 - - [25/Mar/2026:16:09:01 -0400] "POST /afa/php/SuiteLoginSessionValidation.php?clean=false HTTP/1.1" 200 65
127.0.0.1 - - [25/Mar/2026:16:09:09 -0400] "GET /afa/php/home.php HTTP/1.1" 200 35713
127.0.0.1 - - [25/Mar/2026:16:09:10 -0400] "GET /afa/php/JSlib1768164240/dynamic.js.php?sid=abc123fresh HTTP/1.1" 200 23846
=== metro same minute ===
127.0.0.1 [25/Mar/2026:17:29:35 -0400] [http-nio-0.0.0.0-8080-exec-7] "POST /afa/api/v1/session/extend?session=abc123fresh&domain=0 HTTP/1.1" 200 - 246 33410 -
127.0.0.1 [25/Mar/2026:17:29:35 -0400] [http-nio-0.0.0.0-8080-exec-8] "GET /afa/api/v1/config/all/noauth?domain=0 HTTP/1.1" 200 812 1543 33411 -
127.0.0.1 [25/Mar/2026:17:29:43 -0400] [http-nio-0.0.0.0-8080-exec-9] "GET /afa/getStatus HTTP/1.1" 200 33 506 33738 -
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check post-home shell and dashboard hydration traffic</p>

<p class="adf-inline-label">Run</p>

```bash
printf '=== apache ===\n'; grep -E '/afa/php/home.php|dynamic\.js\.php|/afa/php/commands.php\?cmd=DISPLAY_ISSUES_CENTER|/fa/tree/create|/afa/php/prod_stat.php|/fa/tree/get_update|FireFlowBridge.js|/afa/php/logo.php|/afa/api/v1/license|/ms-watchdog/v1/api/issues-center/issues/countAll' /var/log/httpd/ssl_access_log | tail -n 60; printf '=== metro ===\n'; grep -E '/afa/getStatus|/afa/api/v1/bridge/refresh|/afa/api/v1/license|/afa/api/v1/config\?|/afa/api/v1/session/extend|/afa/api/v1/config/all/noauth' /data/ms-metro/logs/localhost_access_log.txt | tail -n 30
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent lines show `/afa/php/home.php`, the first dashboard-hydration routes such as `dynamic.js.php`, `DISPLAY_ISSUES_CENTER`, `/fa/tree/create`, `/afa/php/prod_stat.php`, or `/fa/tree/get_update`, and the nearby Metro clues such as `GET /afa/getStatus`, `GET /afa/api/v1/license`, or the same-minute `config` and `session/extend` requests that surround the first usable shell.
</p>

<p class="adf-check-reference">
Check output for: /afa/php/home.php, dynamic.js.php, DISPLAY_ISSUES_CENTER, /fa/tree/create, /afa/php/prod_stat.php, /fa/tree/get_update, GET /afa/getStatus, GET /afa/api/v1/license, POST /afa/api/v1/session/extend, GET /afa/api/v1/config/all/noauth
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this to keep the post-home model honest. On this lab the first post-home activity was a summary dashboard and issue-center hydration path before deeper operator actions. `DEVICES` mainly refreshed shell context and tree state in the bounded pass, while the first clean deeper action isolated so far was `Analyze`, which mapped to `GET_ANALYSIS_OPTIONS` after the landing shell and device context were already visible. Treat that `Analyze` handoff as the start of a later workflow branch, not as proof that the initial home shell is unhealthy. The real `Start Analysis` step crosses into `cmd=ANALYZE` and `RunFaServer(...)`, so it should not be used as a casual first-shell check. The device-context tabs are also already later content branches: `POLICY` posts `GET_POLICY_TAB` and `GET_DEVICE_POLICY`, `CHANGES` uses `GET_MONITORING_CHANGES`, and `REPORTS` uses `GET_REPORTS`. For support classification, once the customer can navigate the devices tree and reach those later content surfaces, stop calling the case `GUI down` and branch into the more specific failing workflow instead. Keep these shell and dashboard routes inside the ASMS playbook as supporting clues, not as first-class gates by themselves. `GET /afa/getStatus` is still the strongest immediate Metro clue after the home shell appears. `GET /afa/api/v1/config?...` and `POST /afa/api/v1/session/extend?...` are now more strongly tied to the fresh login session because the latest pass matched them to the new `PHPSESSID`, but they are still not proven first-shell requirements. `GET /afa/api/v1/license` and `GET /afa/api/v1/config/all/noauth?domain=0` also appeared in the same fresh-session minute and remain supporting clues rather than proven gates. `POST /afa/api/v1/bridge/refresh?...` stayed tied to a different long-lived session in this lab pass, so treat it as nearby background traffic unless a reproduced browser minute proves otherwise. In a later CDP browser-layer pass, the block rules matched only the early `config/PRINT_TABLE_IN_NORMAL_VIEW` probe and did not record real block events for the fresh-session `license`, `config`, `config/all/noauth`, or `session/extend` traffic, so do not treat browser-side blocking alone as proof that those routes gate the first usable shell. A later Apache seam mutation returned repeated `403` responses for `/afa/external` and still left a fully usable `/afa/php/home.php` shell, and a second top-level Apache mutation on `/afa/api/v1` also left the home shell fully usable and still did not cleanly own the fresh-session `config` and `session/extend` routes. If the landing shell is healthy but a deeper operator action fails, pivot to the first action-specific branch instead of blaming the landing shell. If `ms-watchdog` issue-count calls appear from another client address, treat them as a later subsystem candidate unless the reproduced browser minute proves they are your first stop point.
</p>

<p class="adf-inline-label">Example</p>

```text
=== apache ===
127.0.0.1 - - [25/Mar/2026:17:29:38 -0400] "GET /afa/php/home.php HTTP/1.1" 200 35714
127.0.0.1 - - [26/Mar/2026:05:13:14 -0400] "GET /afa/php/JSlib1768164240/dynamic.js.php?sid=nqo0c2b0dda9d9a4gas11vc6h6 HTTP/1.1" 200 23846
127.0.0.1 - - [26/Mar/2026:05:13:15 -0400] "GET /afa/php/commands.php?cmd=DISPLAY_ISSUES_CENTER HTTP/1.1" 200 741
127.0.0.1 - - [26/Mar/2026:05:13:15 -0400] "POST /fa/tree/create HTTP/1.1" 200 4211
127.0.0.1 - - [26/Mar/2026:05:13:19 -0400] "GET /afa/php/prod_stat.php HTTP/1.1" 200 169
127.0.0.1 - - [26/Mar/2026:05:13:19 -0400] "POST /fa/tree/get_update HTTP/1.1" 200 1642
127.0.0.1 - - [25/Mar/2026:17:29:39 -0400] "GET /afa/php/JSlib1768164240/FireFlowBridge.js HTTP/1.1" 200 484
127.0.0.1 - - [25/Mar/2026:17:29:39 -0400] "GET /afa/php/logo.php HTTP/1.1" 200 -
127.0.0.1 - - [25/Mar/2026:17:29:36 -0400] "GET /afa/api/v1/license HTTP/1.1" 200 311
=== metro ===
127.0.0.1 [25/Mar/2026:17:29:35 -0400] [http-nio-0.0.0.0-8080-exec-7] "POST /afa/api/v1/session/extend?session=abc123fresh&domain=0 HTTP/1.1" 200 - 246 33410 -
127.0.0.1 [25/Mar/2026:17:29:35 -0400] [http-nio-0.0.0.0-8080-exec-8] "GET /afa/api/v1/config/all/noauth?domain=0 HTTP/1.1" 200 812 1543 33411 -
127.0.0.1 [25/Mar/2026:17:29:43 -0400] [http-nio-0.0.0.0-8080-exec-9] "GET /afa/getStatus HTTP/1.1" 200 33 506 33738 -
127.0.0.1 [25/Mar/2026:17:29:44 -0400] [http-nio-0.0.0.0-8080-exec-8] "POST /afa/api/v1/bridge/refresh?session=kk4msqvndoc0c8lmjka8i93vj4&domain=0 HTTP/1.1" 200 - 1739954 33412 -
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check whether the case already crossed into a later content branch</p>

<p class="adf-inline-label">Run</p>

```bash
grep -E '/fa/tree/create|/afa/php/commands.php\?cmd=(GET_REPORTS|GET_POLICY_TAB|GET_DEVICE_POLICY|GET_MONITORING_CHANGES|GET_ANALYSIS_OPTIONS|GET_ANALYZE_DATA|ANALYZE)' /var/log/httpd/ssl_access_log | tail -n 40
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent Apache lines show the device tree refresh plus any later content-branch markers such as `GET_REPORTS`, `GET_POLICY_TAB`, `GET_DEVICE_POLICY`, `GET_MONITORING_CHANGES`, or `GET_ANALYSIS_OPTIONS`.
</p>

<p class="adf-check-reference">
Check output for: /fa/tree/create, GET_REPORTS, GET_POLICY_TAB, GET_DEVICE_POLICY, GET_MONITORING_CHANGES, GET_ANALYSIS_OPTIONS
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this as the branch-out decision after the first usable shell is already visible. `tree/create` by itself is still only shell-context evidence, but once a later content marker like `GET_REPORTS`, `GET_POLICY_TAB`, `GET_MONITORING_CHANGES`, or `GET_ANALYSIS_OPTIONS` appears, stop treating the case as top-level `GUI down` and switch to the narrower failing workflow instead. Keep `cmd=ANALYZE` as a later branch than the dialog-opening `GET_ANALYSIS_OPTIONS` step.
</p>

<p class="adf-inline-label">Example</p>

```text
127.0.0.1 - - [26/Mar/2026:05:13:15 -0400] "POST /fa/tree/create HTTP/1.1" 200 4211
127.0.0.1 - - [26/Mar/2026:05:16:42 -0400] "GET /afa/php/commands.php?cmd=GET_REPORTS HTTP/1.1" 200 812
127.0.0.1 - - [26/Mar/2026:05:18:09 -0400] "GET /afa/php/commands.php?cmd=GET_POLICY_TAB HTTP/1.1" 200 2213
127.0.0.1 - - [26/Mar/2026:05:18:09 -0400] "GET /afa/php/commands.php?cmd=GET_DEVICE_POLICY HTTP/1.1" 200 744
127.0.0.1 - - [26/Mar/2026:05:20:41 -0400] "GET /afa/php/commands.php?cmd=GET_ANALYSIS_OPTIONS HTTP/1.1" 200 1304
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check Metro heartbeat</p>

<p class="adf-inline-label">Run</p>

```bash
curl -sS http://127.0.0.1:8080/afa/getStatus --max-time 10
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The JSON response shows `"isAlive" : true`.
</p>

<p class="adf-check-reference">
Check output for: "isAlive" : true
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the heartbeat hangs, errors, or returns a different value, Metro is not healthy enough for the ASMS UI path.
</p>

<p class="adf-inline-label">Example</p>

```text
{
  "isAlive" : true
}
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check Metro app traffic</p>

<p class="adf-inline-label">Run</p>

```bash
grep -E '/afa/getStatus|/afa/api/v1/config\?|/afa/api/v1/license|/afa/api/v1/session/extend|/afa/api/v1/config/all/noauth' /data/ms-metro/logs/localhost_access_log.txt | tail -n 40
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent access lines show normal 200 responses for the Metro heartbeat and the light authenticated `/afa/api/v1/...` paths that appear immediately after the home page loads.
</p>

<p class="adf-check-reference">
Check output for: GET /afa/getStatus,  200 , /afa/api/v1/license, /afa/api/v1/session/extend, /afa/api/v1/config/all/noauth
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If heartbeat works but the same-minute `/afa/api/v1/...` lines stop, shift to 4xx or 5xx, or never appear around `/afa/php/home.php`, Metro may be up without serving real home-refresh work. Treat `GET /afa/getStatus` as the strongest immediate Metro clue after the first usable shell appears. Keep `license`, `config`, `config/all/noauth`, and `session/extend` as supporting same-minute clues until a fresh-session isolation pass proves one of them is a true first-shell gate. The strongest fresh-session tie now belongs to `config` and `session/extend`, because the latest pass matched them directly to the new `PHPSESSID`, but that still does not prove they gate the first usable shell. The later CDP browser-layer pass did not own the real fresh-session `license`, `config`, `config/all/noauth`, or `session/extend` traffic, so the next meaningful experiment is proxy-side or server-side isolation rather than another browser-side guess. A later Apache seam mutation denied `/afa/external` and still left a fully usable home shell, and a second top-level Apache mutation on `/afa/api/v1` still did not cleanly own the fresh-session `config` and `session/extend` routes. That means the next useful seam is narrower than a family-wide Apache deny, likely around the paired config surfaces themselves. Do not elevate `bridge/refresh` from this check alone because the current lab evidence tied it to a different long-lived session.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check what Metro is busy doing</p>

<p class="adf-inline-label">Run</p>

```bash
ps -p $(cat /var/run/ms-metro/ms-metro.pid) -o pid,etime,%cpu,%mem,nlwp,cmd --cols 160
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The Metro JVM is present, has a stable elapsed runtime, and its CPU, memory, and thread count look reasonable for the current case.
</p>

<p class="adf-check-reference">
Check output for: PID, ELAPSED, %CPU, %MEM, NLWP, java
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If CPU, memory, or thread count looks unexpectedly high or unstable, treat Metro resource pressure or a stuck JVM as part of the failure.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check Metro JVM error clues</p>

<p class="adf-inline-label">Run</p>

```bash
grep -n -i -E 'error|exception|failed|caused by|outofmemory|unable|refused|timed out' /data/ms-metro/logs/catalina.out | tail -n 40
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
No fresh Metro error signatures appear, or the returned lines clearly point to the real Java, dependency, or application failure.
</p>

<p class="adf-check-reference">
Check output for: No output is often normal, Error, Exception, Caused by, Failed
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this inside the Metro command pack after the listener, heartbeat, app-traffic, and JVM-activity checks if the app branch still looks unhealthy. It keeps the Metro-specific clue inside the service pack instead of forcing the engineer to jump ahead to a generic final log sweep.
</p>

</div>

  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-5" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 5</span>
      <span class="adf-preview-manual-summary-title">Check later branch markers</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">5 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Replay one browser-like login journey with cookies before chasing neighbors</p>

<p class="adf-inline-label">Run</p>

```bash
rm -f /tmp/asms-journey.cookies /tmp/asms-journey.headers /tmp/asms-journey.body; curl -k -sS -L -c /tmp/asms-journey.cookies -b /tmp/asms-journey.cookies -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.9' -H 'Upgrade-Insecure-Requests: 1' -D /tmp/asms-journey.headers -o /tmp/asms-journey.body https://127.0.0.1/algosec/suite/login; printf '=== headers ===\n'; sed -n '1,30p' /tmp/asms-journey.headers; printf '=== cookies ===\n'; cat /tmp/asms-journey.cookies 2>/dev/null; printf '=== html markers ===\n'; grep -E 'base href=|runtime.js|main.js|styles.css' /tmp/asms-journey.body | head -n 10
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The replay proves the legacy suite redirect, the static shell markers, and whether the browser-like startup already picked up cookies before any deeper auth path is tested.
</p>

<p class="adf-check-reference">
Check output for: HTTP/1.1 302, Location: https://127.0.0.1/algosec-ui/login, <base href="/algosec-ui/">, runtime.js, main.js
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this as the bounded reproduction anchor for one minute of Apache logs. If it only proves the redirect and static shell, the first real downstream auth or app hop is still unproven.
</p>

<p class="adf-inline-label">Example</p>

```text
HTTP/1.1 302 Found
Location: https://127.0.0.1/algosec-ui/login
<base href="/algosec-ui/">
<script src="runtime.js?v=1768164271" type="module"></script>
<script src="main.js?v=1768164271" type="module"></script>
```
</div>

<div class="adf-check">
<p class="adf-check-label">Correlate the reproduced minute in Apache access logs</p>

<p class="adf-inline-label">Run</p>

```bash
grep -E '/algosec/suite/login|/algosec-ui/login|/algosec-ui/(styles.css|runtime.js|main.js)|/afa/php/commands.php\?cmd=IS_SESSION_ACTIVE|/afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW|/seikan/login/setup|/aff/api/internal/noauth/getStatus|/BusinessFlow|/afa/php/SuiteLoginSessionValidation.php|/keycloak/|/FireFlow/SelfService/CheckAuthentication/|/afa/php/home.php|/afa/api/v1' /var/log/httpd/ssl_access_log | tail -n 120
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent Apache access lines show the same reproduced journey and make it clear whether the request stopped at the shell, moved through the legacy setup and session-validation paths, and only later reached downstream modules such as BusinessFlow, Keycloak, FireFlow, the PHP home page, and Metro-backed app paths.
</p>

<p class="adf-check-reference">
Check output for: /algosec/suite/login, /algosec-ui/login,  200 ,  302 
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the reproduced journey only shows /algosec/suite/login and /algosec-ui/ lines, the first real downstream hop is still unproven. If `/seikan/login/setup` appears first, treat it as the first observed JS-triggered post-shell request. If `/afa/php/SuiteLoginSessionValidation.php` is the first auth-triggering line, keep the failure point there unless later module lines actually appear in the same journey. If `/BusinessFlow` lights up but `/afa/api/v1` only appears after `/afa/php/home.php`, treat Metro as a later post-login app branch, not the first auth hop.
</p>

<p class="adf-inline-label">Example</p>

```text
127.0.0.1 - - [25/Mar/2026:16:09:01 -0400] "GET /algosec-ui/login HTTP/1.1" 200 13345
127.0.0.1 - - [25/Mar/2026:16:09:00 -0400] "GET /seikan/login/setup HTTP/1.1" 200 217
127.0.0.1 - - [25/Mar/2026:16:09:01 -0400] "GET /BusinessFlow/login HTTP/1.1" 302 30
127.0.0.1 - - [25/Mar/2026:16:09:01 -0400] "POST /afa/php/SuiteLoginSessionValidation.php?clean=false HTTP/1.1" 200 65
127.0.0.1 - - [25/Mar/2026:16:09:02 -0400] "POST //keycloak/realms/master/protocol/openid-connect/token? HTTP/1.1" 200 1562
127.0.0.1 - - [25/Mar/2026:16:09:06 -0400] "POST /BusinessFlow/rest/v1/login HTTP/1.1" 200 49
127.0.0.1 - - [25/Mar/2026:16:09:09 -0400] "GET /afa/php/home.php HTTP/1.1" 200 35713
```
</div>

<div class="adf-check">
<p class="adf-check-label">Review recent Apache/HTTPD logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u httpd.service -n 50 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
No obvious disk, permission, startup, or crash errors appear in recent lines.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If recent Apache/HTTPD lines show errors, stay on that clue first.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Review recent Keycloak logs</p>

<p class="adf-inline-label">Run</p>

```bash
tail -n 80 /var/log/keycloak/keycloak.log
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent lines show healthy startup or a clear auth, database, TLS, or startup clue.
</p>

<p class="adf-check-reference">
Check output for: started, Listening on, https://0.0.0.0:8443, hostname:
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If recent Keycloak lines show errors, stay on that clue first.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Review Metro error clues</p>

<p class="adf-inline-label">Run</p>

```bash
grep -n -i -E 'error|exception|failed|caused by|outofmemory|unable|refused|timed out' /data/ms-metro/logs/catalina.out | tail -n 40
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
No fresh Metro error signatures appear, or the returned lines clearly point to the real Java, dependency, or application failure.
</p>

<p class="adf-check-reference">
Check output for: No output is often normal, Error, Exception, Caused by, Failed
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use this only after the traffic and JVM checks if you still need a narrower Java clue.
</p>

</div>

  </div>
  </div>
</details>
  </section>
</div>

