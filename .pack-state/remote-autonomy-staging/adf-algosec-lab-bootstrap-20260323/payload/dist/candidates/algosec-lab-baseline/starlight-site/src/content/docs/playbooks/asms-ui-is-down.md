---
title: ASMS UI is down
description: Use this when the ASMS UI is down and the engineer is checking the appliance from SSH.
sidebar:
  label: ASMS UI is down
  order: 1
---

Use this when the ASMS UI is down and the engineer is checking the appliance from SSH.

## ASMS UI Working Map

<div class="adf-system-shell">
  <div class="adf-system-topbar">
    <div class="adf-panel">
      <p class="adf-panel-label">Working rule</p>
      <p>Start at the host, move into Apache/HTTPD serving the UI, then split into auth and app branches. Stop at the first place where useful work no longer happens.</p>
    </div>
    <div class="adf-panel">
      <p class="adf-panel-label">What this page is proving</p>
      <p>The goal is not to prove that services merely exist. The goal is to prove whether the ASMS UI path can do useful work for the current customer scenario.</p>
    </div>
  </div>
  <div class="adf-system-map adf-panel">
    <p class="adf-panel-label">Useful-work path</p>
    <ol class="adf-system-map-list">
      <li class="adf-system-map-item">
        <a class="adf-system-map-link" href="#ui-and-proxy-step-1">
          <span class="adf-route-step">Step 1</span>
          <strong>Host can support useful work</strong>
          <span>Start here. Check storage, inode, memory, OOM, load, and CPU pressure to decide whether the Linux host can still support Apache, Keycloak, Metro, logging, and temp-file writes.</span>
        </a>
      </li>
      <li class="adf-system-map-item">
        <a class="adf-system-map-link" href="#ui-and-proxy-step-2">
          <span class="adf-route-step">Step 2</span>
          <strong>Apache/HTTPD serving the UI</strong>
          <span>If the host looks healthy, confirm Apache/HTTPD can answer local UI traffic and still route requests into the auth and app branches.</span>
        </a>
      </li>
      <li class="adf-system-map-item">
        <a class="adf-system-map-link" href="#ui-and-proxy-step-3">
          <span class="adf-route-step">Step 3</span>
          <strong>Auth branch can do useful work</strong>
          <span>Check whether Keycloak is healthy enough to answer local auth and login traffic, not only whether the service process exists.</span>
        </a>
      </li>
      <li class="adf-system-map-item">
        <a class="adf-system-map-link" href="#ui-and-proxy-step-4">
          <span class="adf-route-step">Step 4</span>
          <strong>App branch can do useful work</strong>
          <span>Check whether ms-metro is serving useful app traffic and showing healthy JVM behavior, not only whether port 8080 is open.</span>
        </a>
      </li>
      <li class="adf-system-map-item">
        <a class="adf-system-map-link" href="#ui-and-proxy-step-5">
          <span class="adf-route-step">Step 5</span>
          <strong>Useful work stops here</strong>
          <span>If the host and both branches still look up, use Apache/HTTPD, Keycloak, and Metro clues to find the first clear stop point.</span>
        </a>
      </li>
    </ol>
  </div>
  <div class="adf-system-grid">
    <aside class="adf-system-nav adf-panel">
      <p class="adf-panel-label">Quick jump</p>
      <div class="adf-system-jumps">
<a class="adf-system-jump" href="#ui-and-proxy-step-1">
  <span class="adf-route-step">Step 1</span>
  <strong>Host can support useful work</strong>
  <span>Start here. Check storage, inode, memory, OOM, load, and CPU pressure to decide whether the Linux host can still support Apache, Keycloak, Metro, logging, and temp-file writes.</span>
</a>
<a class="adf-system-jump" href="#ui-and-proxy-step-2">
  <span class="adf-route-step">Step 2</span>
  <strong>Apache/HTTPD serving the UI</strong>
  <span>If the host looks healthy, confirm Apache/HTTPD can answer local UI traffic and still route requests into the auth and app branches.</span>
</a>
<a class="adf-system-jump" href="#ui-and-proxy-step-3">
  <span class="adf-route-step">Step 3</span>
  <strong>Auth branch can do useful work</strong>
  <span>Check whether Keycloak is healthy enough to answer local auth and login traffic, not only whether the service process exists.</span>
</a>
<a class="adf-system-jump" href="#ui-and-proxy-step-4">
  <span class="adf-route-step">Step 4</span>
  <strong>App branch can do useful work</strong>
  <span>Check whether ms-metro is serving useful app traffic and showing healthy JVM behavior, not only whether port 8080 is open.</span>
</a>
<a class="adf-system-jump" href="#ui-and-proxy-step-5">
  <span class="adf-route-step">Step 5</span>
  <strong>Useful work stops here</strong>
  <span>If the host and both branches still look up, use Apache/HTTPD, Keycloak, and Metro clues to find the first clear stop point.</span>
</a>
      </div>
      <div class="adf-system-sideblock">
        <p class="adf-panel-label">Symptoms that fit here</p>
        <ul>
          <li>ASMS UI is down</li>
          <li>ASMS login page not loading</li>
        </ul>
      </div>
    </aside>
    <div class="adf-system-main">
<details id="ui-and-proxy-step-1" class="adf-system-checkpoint">
<summary class="adf-system-summary">
  <span class="adf-step-badge">Step 1</span>
  <span class="adf-system-heading">
    <strong>Host can support useful work</strong>
    <span>Check whether the host can support useful work for the ASMS UI path. Confirm storage, inode, memory, load, OOM, and CPU pressure are not already blocking Apache, Keycloak, Metro, log writing, or temp-file work.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-system-body">
<div class="adf-system-brief adf-panel">
  <p class="adf-panel-label">Why this checkpoint exists</p>
  <p>Every major playbook starts with the Linux host. The first question is not whether a number looks high. It is whether current host pressure is already enough to break useful work in the UI system.</p>
</div>

<div class="adf-check">
<p class="adf-check-label">Check storage pressure on runtime filesystems</p>

<p class="adf-inline-label">Run</p>

```bash
df -h
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Runtime filesystems still have enough free space for logs, temp files, and service work.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: disk pressure</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks human-readable disk usage for the main filesystems.
- Focus on `Use%` and `Avail`, especially for `/` and `/data`.
- Disk pressure means the filesystem is close to full. When that happens, services can fail to write logs, temp files, or runtime data.
  </div>
</details>

<p class="adf-check-reference">
Look for: Use% below 100%, Avail is not 0, / and /data still have free space
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If /, /boot, or /data is close to full, Apache, Keycloak, Metro, installers, and log writers can all fail or behave unpredictably.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Runtime filesystems still have free inodes for logs, temp files, sockets, and service output.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: inode pressure</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks inode usage, which is different from normal disk space.
- A filesystem can still have free space but fail because it has no free inodes left.
- Inode pressure means the server has too many files or directory entries. Focus on `IUse%` and whether `IFree` is close to zero.
  </div>
</details>

<p class="adf-check-reference">
Look for: IUse% below 100%, IFree is not 0, / and /data still have free inodes
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If inode use is high, the host can look like it has free disk while Apache, Keycloak, Metro, or log rotation still fail to create files.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Available memory is still present and swap is not carrying active pressure for the host.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: memory pressure</span>
  </summary>
  <div class="adf-check-knowledge">

- This is the quick memory check for the host.
- Focus on `available` memory and whether swap is starting to grow heavily.
- Memory pressure means the server is low on available memory. When that happens, the server slows down, swap grows, or Linux may kill a process to protect itself.
  </div>
</details>

<p class="adf-check-reference">
Look for: available memory is present, swap is not exhausted, Mem and Swap are shown in GiB
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If available memory is very low or swap is heavily used, Java services like Keycloak and Metro may slow down, hang, fail health checks, or get killed later.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Load is not unexpectedly high for the host and does not already explain the UI symptom.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: system load</span>
  </summary>
  <div class="adf-check-knowledge">

- This is the quick load check for the host.
- Focus on the `load average` values and whether they look unexpectedly high for the server.
- High load can mean CPU pressure, blocked work, or heavy I/O wait.
  </div>
</details>

<p class="adf-check-reference">
Look for: load average:, load values are not unexpectedly high
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If load is unusually high, the system may be under CPU pressure, blocked work, or heavy I/O wait before you even reach the UI-specific branches.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
No recent Out Of Memory lines are returned.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: OOM pressure</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks the Linux kernel log for memory-pressure kills.
- OOM means Out Of Memory. Linux may kill a process to protect the server.
- If you see OOM or `Killed process` lines, memory pressure is likely part of the failure.
  </div>
</details>

<p class="adf-check-reference">
Look for: No output is normal, No 'Out of memory' lines, No 'Killed process' lines
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If OOM lines appear, the host has already been killing or starving processes under memory pressure, so downstream UI symptoms may only be the visible side effect.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
No unexpected process is consuming enough CPU to starve the rest of the ASMS path.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: top CPU consumers</span>
  </summary>
  <div class="adf-check-knowledge">

- This shows which processes are using the most CPU right now.
- Focus on whether one process is dominating CPU and whether that process matches the current symptom.
- A single runaway process can starve the rest of the server and make higher-level application failures look worse than they are.
  </div>
</details>

<p class="adf-check-reference">
Look for: PID, COMMAND, %CPU, %MEM
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If one process is consuming most of the CPU, treat that process as part of the current system pressure story before assuming the UI path itself is the root cause.
</p>

<p class="adf-inline-label">Known working example</p>

```text
  PID COMMAND         %CPU %MEM
 6012 java             8.1  7.4
 1018 httpd            1.2  0.4
 3758 algosec_keycloa  0.8  1.6
```
</div>

</div>
</details>

<details id="ui-and-proxy-step-2" class="adf-system-checkpoint">
<summary class="adf-system-summary">
  <span class="adf-step-badge">Step 2</span>
  <span class="adf-system-heading">
    <strong>Apache/HTTPD serving the UI</strong>
    <span>Check whether Apache/HTTPD can do useful edge work for the ASMS UI path. Confirm httpd.service is running, 80 and 443 are listening, the suite login route still lands on the Apache-served UI page, representative /algosec-ui/ assets still load through Apache, and the proxy mapping still points toward the auth and app branches.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-system-body">
<div class="adf-system-brief adf-panel">
  <p class="adf-panel-label">Why this checkpoint exists</p>
  <p>After host health, Apache/HTTPD is the system edge for the UI path. The real question is whether the edge can still serve browser-useful login content and hand auth and app requests to the right neighbors, not only whether a process exists.</p>
</div>

<div class="adf-check">
<p class="adf-check-label">Check httpd.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status httpd.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Unit is loaded and active (running).
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: service status</span>
  </summary>
  <div class="adf-check-knowledge">

- This asks systemd whether the service is known and running now.
- `Loaded` means the service unit exists on the server.
- `Active (running)` means the service is up now. `Main PID` means systemd still sees the main process.
  </div>
</details>

<p class="adf-check-reference">
Look for: Loaded: loaded, Active: active (running), Main PID:, /usr/sbin/httpd
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If this is not active, treat the edge service itself as the failure point before going deeper.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
A listening socket is present for 80, 443.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: listening port</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks whether Linux is listening on the expected port.
- `LISTEN` means a process has opened the port and is waiting for connections.
- If the port is missing, the service may be down, slow to start, or bound to the wrong place.
  </div>
</details>

<p class="adf-check-reference">
Look for: LISTEN, :80, :443, httpd
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If 80/443 are missing, the UI path is failing at the listener or bind layer.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Apache returns a redirect from the legacy suite login path into the current UI login page.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note</span>
  </summary>
  <div class="adf-check-knowledge">

- This command gives a focused check for the current step.
- Use the healthy example below as the main output reference for what good looks like.
  </div>
</details>

<p class="adf-check-reference">
Look for: HTTP/1.1 302, Server: Apache, Location: https://127.0.0.1/algosec-ui/login
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the suite login route stops redirecting here, the edge path is already broken before Keycloak or Metro have a chance to help.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Apache returns the current UI login page with HTTP 200.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note</span>
  </summary>
  <div class="adf-check-knowledge">

- This command gives a focused check for the current step.
- Use the healthy example below as the main output reference for what good looks like.
  </div>
</details>

<p class="adf-check-reference">
Look for: HTTP/1.1 200, Server: Apache, Content-Type: text/html
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If Apache cannot serve the login page here, stop at the edge before chasing the auth or app neighbors.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Apache returns HTTP 200 for representative CSS and JS assets and each body is non-empty.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: browser-useful edge assets</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks whether Apache is serving real UI assets, not only the login HTML shell.
- Non-empty CSS and JavaScript bodies are a stronger edge proof because a browser needs them before sign-in can do useful work.
- If the HTML is up but these assets fail, stay on Apache and the static UI path before chasing Keycloak or Metro.
  </div>
</details>

<p class="adf-check-reference">
Look for: HTTP/1.1 200, Server: Apache, Content-Type: text/css, Content-Type: application/javascript, BODY_BYTES
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the login HTML works but these assets fail, return the wrong type, or come back empty, the edge is not yet browser-useful even before Keycloak or Metro are checked.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Apache config still shows the login redirect, the UI alias, and the auth and app route mapping needed by the ASMS UI path.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note</span>
  </summary>
  <div class="adf-check-knowledge">

- This command gives a focused check for the current step.
- Use the healthy example below as the main output reference for what good looks like.
  </div>
</details>

<p class="adf-check-reference">
Look for: algosec/suite, algosec-ui, ProxyPass, keycloak, 8443, afa/api/v1, 8080
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the expected proxy targets are missing or wrong, the edge can look healthy while routing useful work to the wrong place or nowhere useful.
</p>

<p class="adf-inline-label">Known working example</p>

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
</details>

<details id="ui-and-proxy-step-3" class="adf-system-checkpoint">
<summary class="adf-system-summary">
  <span class="adf-step-badge">Step 3</span>
  <span class="adf-system-heading">
    <strong>Auth branch can do useful work</strong>
    <span>Check the first auth-triggering chain after the static shell. On this lab, the browser first touches legacy suite setup and session-validation paths, then reaches BusinessFlow, Keycloak, and FireFlow-backed auth checks before the final handoff into `/afa/php/home.php`.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-system-body">
<div class="adf-system-brief adf-panel">
  <p class="adf-panel-label">Why this checkpoint exists</p>
  <p>The static shell alone does not prove the real auth order. On this lab the first JS-triggered request after the shell was `/seikan/login/setup`, the first session-validation hop was `POST /afa/php/SuiteLoginSessionValidation.php?clean=false`, and the authenticated path then lit up BusinessFlow, proxied Keycloak token paths, and FireFlow auth checks before the PHP home page loaded.</p>
</div>

<div class="adf-check">
<p class="adf-check-label">Check the shipped login setup endpoint first</p>

<p class="adf-inline-label">Run</p>

```bash
curl -k -sS -D - https://127.0.0.1/seikan/login/setup -o /tmp/asms-login-setup.json && sed -n '1,40p' /tmp/asms-login-setup.json
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The setup endpoint returns JSON that shows the current login mode and whether SSO is enabled on this appliance.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: login setup mode</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks the login setup endpoint that the shipped UI uses before credentials are submitted.
- Use it to see whether this appliance is advertising SSO or a different login mode for the current journey.
- If `isSSOEnabled` is false here, do not assume Keycloak is the first observed auth hop without stronger request evidence.
  </div>
</details>

<p class="adf-check-reference">
Look for: HTTP/1.1 200, Server: Apache-Coyote, "isSSOEnabled" : false, "needsFirstTimeSetup" : false
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If this endpoint fails, the first auth-trigger path is already broken before credentials are submitted. If it shows `"isSSOEnabled" : false`, do not assume Keycloak is the first real auth hop for this journey.
</p>

<p class="adf-inline-label">Known working example</p>

```text
HTTP/1.1 200
Server: Apache-Coyote
{  "isSSOEnabled" : false,
  "needsFirstTimeSetup" : false,
  "isAffEnabled" : true,
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check the legacy suite session-validation hop with cookies</p>

<p class="adf-inline-label">Run</p>

```bash
rm -f /tmp/asms-auth-hop.cookies /tmp/asms-auth-hop.headers /tmp/asms-auth-hop.body; curl -k -sS -L -c /tmp/asms-auth-hop.cookies -b /tmp/asms-auth-hop.cookies -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.9' -H 'Upgrade-Insecure-Requests: 1' -D /tmp/asms-auth-hop.headers -o /tmp/asms-auth-hop.body https://127.0.0.1/afa/php/SuiteLoginSessionValidation.php; sed -n '1,20p' /tmp/asms-auth-hop.headers; echo '--- cookies ---'; cat /tmp/asms-auth-hop.cookies 2>/dev/null
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The legacy session-validation path either redirects back to `/algosec-ui/login` and sets a PHP session cookie, or returns a different concrete auth clue for the same reproduced journey.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: legacy session validation</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks a legacy suite login endpoint with a cookie jar so one reproduced journey stays connected.
- A redirect back to `/algosec-ui/login` with a new PHP session cookie is a real auth-path clue, even without credentials.
- If this path lights up before `/keycloak/`, treat it as the first observed auth-trigger hop for this journey and keep BusinessFlow or Keycloak as later auth neighbors.
  </div>
</details>

<p class="adf-check-reference">
Look for: HTTP/1.1 302, Set-Cookie: PHPSESSID=, Location: /algosec-ui/login?last_url=%2Fafa%2Fphp%2FSuiteLoginSessionValidation.php
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If this path is the first auth-triggering hop you can actually reproduce, treat it as stronger evidence than a guessed Keycloak-first model. On this lab the browser hit `POST /afa/php/SuiteLoginSessionValidation.php?clean=false` before the later Keycloak and BusinessFlow login activity. If it never appears in the reproduced journey, keep it inferred only.
</p>

<p class="adf-inline-label">Known working example</p>

```text
HTTP/1.1 302 Found
Set-Cookie: PHPSESSID=pp3eujujutk0t1mrmvfd6jflrm; path=/; secure; HttpOnly; SameSite=Lax
Location: /algosec-ui/login?last_url=%2Fafa%2Fphp%2FSuiteLoginSessionValidation.php
```
</div>

<div class="adf-check">
<p class="adf-check-label">Correlate the authenticated auth handoff in Apache</p>

<p class="adf-inline-label">Run</p>

```bash
grep -E '/seikan/login/setup|/afa/php/SuiteLoginSessionValidation.php|/BusinessFlow/rest/v1/login|/FireFlow/SelfService/CheckAuthentication/|/keycloak/' /var/log/httpd/ssl_access_log | tail -n 80
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Recent Apache lines show whether the reproduced login moved from the legacy setup and session-validation paths into BusinessFlow, Keycloak, FireFlow auth checks, and the final PHP handoff.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: login setup mode</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks the login setup endpoint that the shipped UI uses before credentials are submitted.
- Use it to see whether this appliance is advertising SSO or a different login mode for the current journey.
- If `isSSOEnabled` is false here, do not assume Keycloak is the first observed auth hop without stronger request evidence.
  </div>
</details>

<p class="adf-check-reference">
Look for: /seikan/login/setup, /afa/php/SuiteLoginSessionValidation.php, /BusinessFlow/rest/v1/login, /keycloak/, /FireFlow/SelfService/CheckAuthentication/
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
Use this to keep the auth model honest. On this lab the Keycloak lines appeared after the legacy setup and session-validation requests, not before them. If BusinessFlow and Keycloak never light up for the reproduced minute, keep the failure point earlier in the auth chain.
</p>

<p class="adf-inline-label">Known working example</p>

```text
127.0.0.1 - - [25/Mar/2026:15:52:35 -0400] "GET /seikan/login/setup HTTP/1.1" 200 217
127.0.0.1 - - [25/Mar/2026:15:52:35 -0400] "POST /afa/php/SuiteLoginSessionValidation.php?clean=false HTTP/1.1" 200 65
127.0.0.1 - - [25/Mar/2026:15:52:43 -0400] "POST //keycloak/realms/master/protocol/openid-connect/token? HTTP/1.1" 200 1562
127.0.0.1 - - [25/Mar/2026:15:52:46 -0400] "POST /BusinessFlow/rest/v1/login HTTP/1.1" 200 49
127.0.0.1 - - [25/Mar/2026:15:52:50 -0400] "GET /FireFlow/SelfService/CheckAuthentication/?login=1 HTTP/1.1" 200 309
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check keycloak.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status keycloak.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Unit is loaded and active (running).
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: service status</span>
  </summary>
  <div class="adf-check-knowledge">

- This asks systemd whether the service is known and running now.
- `Loaded` means the service unit exists on the server.
- `Active (running)` means the service is up now. `Main PID` means systemd still sees the main process.
  </div>
</details>

<p class="adf-check-reference">
Look for: Loaded: loaded, Active: active (running), Main PID:, algosec_keycloak_start.sh
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the reproduced journey lights up `/keycloak/` and this service is not running, the auth branch is failing at Keycloak. On this lab `/keycloak/` appeared inside the authenticated BusinessFlow handoff, not as the first post-shell request. If the journey has not reached `/keycloak/` yet, keep Keycloak as a reachable auth neighbor, not the first proven hop.
</p>

<p class="adf-inline-label">Known working example</p>

```text
● keycloak.service - The authentication and authorization server
   Loaded: loaded (/usr/lib/systemd/system/keycloak.service; enabled; vendor preset: disabled)
   Active: active (running) since Sat 2026-03-07 13:38:32 EST; 2 weeks 2 days ago
 Main PID: 3758 (algosec_keycloa)
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check Keycloak ports</p>

<p class="adf-inline-label">Run</p>

```bash
ss -lntp | grep -E ':(8443|9000)\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Ports 8443 and 9000 are listening for Keycloak.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: listening port</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks whether Linux is listening on the expected port.
- `LISTEN` means a process has opened the port and is waiting for connections.
- If the port is missing, the service may be down, slow to start, or bound to the wrong place.
  </div>
</details>

<p class="adf-check-reference">
Look for: LISTEN, :8443, :9000, java
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If 8443 or 9000 is missing, focus on Keycloak startup, bind, or health-endpoint problems.
</p>

<p class="adf-inline-label">Known working example</p>

```text
LISTEN 0 16384 0.0.0.0:8443 0.0.0.0:* users:(("java",pid=5129,fd=363))
LISTEN 0 16384 127.0.0.1:9000 0.0.0.0:* users:(("java",pid=5129,fd=412))
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check Keycloak readiness</p>

<p class="adf-inline-label">Run</p>

```bash
curl -k https://127.0.0.1:9000/health/ready --max-time 10
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The JSON response shows `"status": "UP"`.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: service readiness</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks a local readiness endpoint instead of only checking whether the service process exists.
- A readiness endpoint helps prove the service is healthy enough to answer real traffic.
- Use the expected JSON value below as the main reference, not just the HTTP connection itself.
  </div>
</details>

<p class="adf-check-reference">
Look for: "status": "UP", Keycloak database connections async health check, "status": "UP"
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the readiness endpoint is not UP, Keycloak may be running but not healthy enough to serve login traffic.
</p>

<p class="adf-inline-label">Known working example</p>

```text
{
    "status": "UP",
    "checks": [
        {
            "name": "Keycloak database connections async health check",
            "status": "UP"
        }
    ]
}
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check Keycloak OIDC path</p>

<p class="adf-inline-label">Run</p>

```bash
curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration --max-time 10
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The local Keycloak OIDC path returns HTTP 200.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: OIDC path</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks a real Keycloak OpenID Connect path that the local login flow depends on.
- An HTTP 200 here is a stronger proof than a simple port check because it confirms the local path is answering correctly.
- If this path fails while the service still looks up, treat it as an application-path problem instead of a simple process problem.
  </div>
</details>

<p class="adf-check-reference">
Look for: HTTP/1.1 200, Server: Apache, application/json
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the OIDC path fails, Keycloak may be up but not reachable through the expected local path. If it works but your reproduced journey never hits `/keycloak/`, keep Keycloak as reachable and inferred, not observed as the first post-shell hop.
</p>

<p class="adf-inline-label">Known working example</p>

```text
HTTP/1.1 200 OK
Server: Apache
Content-Type: application/json;charset=UTF-8
```
</div>

</div>
</details>

<details id="ui-and-proxy-step-4" class="adf-system-checkpoint">
<summary class="adf-system-summary">
  <span class="adf-step-badge">Step 4</span>
  <span class="adf-system-heading">
    <strong>App branch can do useful work</strong>
    <span>Check whether the app branch can do useful work after the authenticated handoff. Confirm ms-metro is running, listening on 8080, answering the heartbeat, and serving recent authenticated app traffic after login reaches `/afa/php/home.php`.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-system-body">
<div class="adf-system-brief adf-panel">
  <p class="adf-panel-label">Why this checkpoint exists</p>
  <p>The app branch can fail even when Apache/HTTPD and the auth chain look healthy. On this lab Metro first appeared as an unauthenticated config probe that returned `401`, then lit up with authenticated `/afa/api/v1/...` traffic only after the BusinessFlow, Keycloak, FireFlow, and final PHP handoff.</p>
</div>

<div class="adf-check">
<p class="adf-check-label">Check ms-metro.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status ms-metro.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Unit is loaded and active (running).
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: service status</span>
  </summary>
  <div class="adf-check-knowledge">

- This asks systemd whether the service is known and running now.
- `Loaded` means the service unit exists on the server.
- `Active (running)` means the service is up now. `Main PID` means systemd still sees the main process.
  </div>
</details>

<p class="adf-check-reference">
Look for: Loaded: loaded, Active: active (running), Main PID:, java
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If Metro is not running, the UI may open only partly or fail after the first page.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Port 8080 is listening for ms-metro.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: listening port</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks whether Linux is listening on the expected port.
- `LISTEN` means a process has opened the port and is waiting for connections.
- If the port is missing, the service may be down, slow to start, or bound to the wrong place.
  </div>
</details>

<p class="adf-check-reference">
Look for: LISTEN, :8080, java
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If port 8080 is missing, the UI backend route has no working target.
</p>

<p class="adf-inline-label">Known working example</p>

```text
LISTEN 0 100 0.0.0.0:8080 0.0.0.0:* users:(("java",pid=6012,fd=44))
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check Metro heartbeat</p>

<p class="adf-inline-label">Run</p>

```bash
curl -sS http://127.0.0.1:8080/afa/getStatus --max-time 10
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The JSON response shows `"isAlive" : true`.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: service heartbeat</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks a real ms-metro heartbeat path instead of only checking whether the Java process exists.
- A heartbeat response helps prove the service is alive enough to answer application traffic.
- Use this after the listener check when port 8080 is open but the UI still behaves badly.
  </div>
</details>

<p class="adf-check-reference">
Look for: "isAlive" : true
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the heartbeat hangs, errors, or returns a different value, Metro is not healthy enough for the ASMS UI path.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Recent access lines show normal 200 responses for the Metro heartbeat and the authenticated `/afa/api/v1/...` paths that appear after login succeeds.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: service heartbeat</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks a real ms-metro heartbeat path instead of only checking whether the Java process exists.
- A heartbeat response helps prove the service is alive enough to answer application traffic.
- Use this after the listener check when port 8080 is open but the UI still behaves badly.
  </div>
</details>

<p class="adf-check-reference">
Look for: GET /afa/getStatus,  200 , /afa/api/v1/config, /afa/api/v1/license, /afa/api/v1/session/extend
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If heartbeat works but the authenticated `/afa/api/v1/...` lines stop, shift to 4xx or 5xx, or never appear after `/afa/php/home.php`, Metro may be up without serving real post-login app work.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check what Metro is busy doing</p>

<p class="adf-inline-label">Run</p>

```bash
ps -p $(cat /var/run/ms-metro/ms-metro.pid) -o pid,etime,%cpu,%mem,nlwp,cmd --cols 160
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The Metro JVM is present, has a stable elapsed runtime, and its CPU, memory, and thread count look reasonable for the current case.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: JVM activity</span>
  </summary>
  <div class="adf-check-knowledge">

- This shows the live Metro JVM process with elapsed runtime, CPU, memory, and thread count.
- Focus on whether CPU, memory, or thread count looks unexpectedly high for the current case.
- This is a stronger answer to 'what is Metro busy doing' than reading random Java log lines first.
  </div>
</details>

<p class="adf-check-reference">
Look for: PID, ELAPSED, %CPU, %MEM, NLWP, java
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If CPU, memory, or thread count looks unexpectedly high or unstable, treat Metro resource pressure or a stuck JVM as part of the failure.
</p>

</div>

</div>
</details>

<details id="ui-and-proxy-step-5" class="adf-system-checkpoint">
<summary class="adf-system-summary">
  <span class="adf-step-badge">Step 5</span>
  <span class="adf-system-heading">
    <strong>Useful work stops here</strong>
    <span>If useful work still stops here, use Apache/HTTPD, Keycloak, and Metro clues to find the first clear stop point.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-system-body">
<div class="adf-system-brief adf-panel">
  <p class="adf-panel-label">Why this checkpoint exists</p>
  <p>Only move to logs after the host, edge, auth branch, and app branch checks. At this point the goal is to find where useful work stops, not to read every log from the bottom.</p>
</div>

<div class="adf-check">
<p class="adf-check-label">Replay one browser-like login journey with cookies before chasing neighbors</p>

<p class="adf-inline-label">Run</p>

```bash
rm -f /tmp/asms-journey.cookies /tmp/asms-journey.headers /tmp/asms-journey.body; curl -k -sS -L -c /tmp/asms-journey.cookies -b /tmp/asms-journey.cookies -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.9' -H 'Upgrade-Insecure-Requests: 1' -D /tmp/asms-journey.headers -o /tmp/asms-journey.body https://127.0.0.1/algosec/suite/login; printf '=== headers ===\n'; sed -n '1,30p' /tmp/asms-journey.headers; printf '=== cookies ===\n'; cat /tmp/asms-journey.cookies 2>/dev/null; printf '=== html markers ===\n'; grep -E 'base href=|runtime.js|main.js|styles.css' /tmp/asms-journey.body | head -n 10
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The replay proves the legacy suite redirect, the static shell markers, and whether the browser-like startup already picked up cookies before any deeper auth path is tested.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: browser-like replay</span>
  </summary>
  <div class="adf-check-knowledge">

- This replays one login journey with browser-like headers and a cookie jar so the follow-up log check has one clear anchor.
- Use the headers, cookies, and HTML markers together instead of looking at only one response line.
- If this replay still stops at the static shell, say the first downstream auth or app hop is still unproven.
  </div>
</details>

<p class="adf-check-reference">
Look for: HTTP/1.1 302, Location: https://127.0.0.1/algosec-ui/login, <base href="/algosec-ui/">, runtime.js, main.js
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
Use this as the bounded reproduction anchor for one minute of Apache logs. If it only proves the redirect and static shell, the first real downstream auth or app hop is still unproven.
</p>

<p class="adf-inline-label">Known working example</p>

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
  <span class="adf-inline-label">Verification:</span> 
Recent Apache access lines show the same reproduced journey and make it clear whether the request stopped at the shell, moved through the legacy setup and session-validation paths, reached BusinessFlow and Keycloak, and only then handed off into the PHP home page and Metro-backed app paths.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: login setup mode</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks the login setup endpoint that the shipped UI uses before credentials are submitted.
- Use it to see whether this appliance is advertising SSO or a different login mode for the current journey.
- If `isSSOEnabled` is false here, do not assume Keycloak is the first observed auth hop without stronger request evidence.
  </div>
</details>

<p class="adf-check-reference">
Look for: /algosec/suite/login, /algosec-ui/login,  200 ,  302 
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the reproduced journey only shows /algosec/suite/login and /algosec-ui/ lines, the first real downstream hop is still unproven. If `/seikan/login/setup` appears first, treat it as the first observed JS-triggered post-shell request. If `/afa/php/SuiteLoginSessionValidation.php` is the first auth-triggering line, keep the failure point there unless later BusinessFlow, Keycloak, or FireFlow lines appear. If `/afa/api/v1` only appears after `/afa/php/home.php`, treat Metro as a later post-login app branch, not the first auth hop.
</p>

<p class="adf-inline-label">Known working example</p>

```text
127.0.0.1 - - [25/Mar/2026:15:52:34 -0400] "GET /algosec-ui/login HTTP/1.1" 200 13345
127.0.0.1 - - [25/Mar/2026:15:52:35 -0400] "GET /seikan/login/setup HTTP/1.1" 200 217
127.0.0.1 - - [25/Mar/2026:15:52:35 -0400] "POST /afa/php/SuiteLoginSessionValidation.php?clean=false HTTP/1.1" 200 65
127.0.0.1 - - [25/Mar/2026:15:52:43 -0400] "POST //keycloak/realms/master/protocol/openid-connect/token? HTTP/1.1" 200 1562
127.0.0.1 - - [25/Mar/2026:15:52:46 -0400] "POST /BusinessFlow/rest/v1/login HTTP/1.1" 200 49
127.0.0.1 - - [25/Mar/2026:15:52:49 -0400] "GET /afa/php/SuiteLoginSessionValidation.php HTTP/1.1" 302 -
127.0.0.1 - - [25/Mar/2026:15:52:50 -0400] "GET /afa/php/home.php HTTP/1.1" 200 35707
```
</div>

<div class="adf-check">
<p class="adf-check-label">Review recent Apache/HTTPD logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u httpd.service -n 50 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
No obvious disk, permission, startup, or crash errors appear in recent lines.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: service logs</span>
  </summary>
  <div class="adf-check-knowledge">

- Recent service logs are often the fastest way to find the real failure clue.
- Focus on startup errors, permission errors, heap errors, dependency failures, and repeated retries.
- Use this after the status check when the service looks up but still behaves badly.
  </div>
</details>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
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
  <span class="adf-inline-label">Verification:</span> 
Recent lines show healthy startup or a clear auth, database, TLS, or startup clue.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: file-based service logs</span>
  </summary>
  <div class="adf-check-knowledge">

- This appliance writes the useful service clues to log files, not only to systemd journal output.
- Focus on startup errors, dependency failures, auth errors, heap errors, and repeated retries.
- Use the most specific log for the service you are checking before widening the search.
  </div>
</details>

<p class="adf-check-reference">
Look for: started, Listening on, https://0.0.0.0:8443, hostname:
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
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
  <span class="adf-inline-label">Verification:</span> 
No fresh Metro error signatures appear, or the returned lines clearly point to the real Java, dependency, or application failure.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: Java log anomalies</span>
  </summary>
  <div class="adf-check-knowledge">

- Large Java logs are often noisy when read from the bottom alone.
- This check pulls likely error signatures first so the engineer can find the useful anomaly faster.
- Use the line numbers and error keywords here as the first clue, then widen into the full log only if needed.
  </div>
</details>

<p class="adf-check-reference">
Look for: No output is often normal, Error, Exception, Caused by, Failed
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
Use this only after the traffic and JVM checks if you still need a narrower Java clue.
</p>

</div>

</div>
</details>

    </div>
  </div>
</div>

<script>
(() => {
  const openHashTarget = () => {
    const rawHash = window.location.hash;
    if (!rawHash || rawHash.length < 2) return;
    const target = document.getElementById(decodeURIComponent(rawHash.slice(1)));
    if (!target) return;
    const details = target.matches('details') ? target : target.closest('details');
    if (details) details.open = true;
  };
  window.addEventListener('hashchange', openHashTarget);
  openHashTarget();
})();
</script>

