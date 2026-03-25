---
title: Appliance UI is down
description: Use this when the customer UI is down and the engineer is checking the appliance from SSH.
sidebar:
  label: Appliance UI is down
  order: 1
---

Use this when the customer UI is down and the engineer is checking the appliance from SSH.

## Support Cockpit

<div class="adf-cockpit-shell">
  <div class="adf-cockpit-topbar">
    <div class="adf-panel">
      <p class="adf-panel-label">Decision rule</p>
      <p>If a step fails, stop the happy-path sequence, record that step as the current failure point, and collect the matching evidence before moving on.</p>
    </div>
    <div class="adf-panel">
      <p class="adf-panel-label">Likely services</p>
      <div class="adf-service-chip-row">
        <span class="adf-service-chip">httpd.service</span>
        <span class="adf-service-chip">keycloak.service</span>
        <span class="adf-service-chip">ms-metro.service</span>
      </div>
    </div>
  </div>
  <div class="adf-panel adf-cockpit-strip">
    <p class="adf-panel-label">Command-first flow</p>
    <p>Open one checkpoint, run the listed read-only commands, compare the healthy signal, then stop at the first failure point.</p>
  </div>
  <div class="adf-cockpit-path">
    <p class="adf-panel-label">Dependency path</p>
    <ol class="adf-path-list">
      <li class="adf-path-item">
        <a class="adf-path-link" href="#ui-and-proxy-step-1">
          <span class="adf-route-step">Step 1</span>
          <strong>Apache edge</strong>
          <span>Start here. Confirm httpd.service is active and ports 80 and 443 are listening before checking anything deeper.</span>
        </a>
      </li>
      <li class="adf-path-item">
        <a class="adf-path-link" href="#ui-and-proxy-step-2">
          <span class="adf-route-step">Step 2</span>
          <strong>Host health</strong>
          <span>If Apache is up, check disk space, inode usage, available memory, and recent OOM pressure on the host.</span>
        </a>
      </li>
      <li class="adf-path-item">
        <a class="adf-path-link" href="#ui-and-proxy-step-3">
          <span class="adf-route-step">Step 3</span>
          <strong>UI services</strong>
          <span>Then check the main UI services: keycloak.service on 8443 and ms-metro.service on 8080.</span>
        </a>
      </li>
      <li class="adf-path-item">
        <a class="adf-path-link" href="#ui-and-proxy-step-4">
          <span class="adf-route-step">Step 4</span>
          <strong>Logs</strong>
          <span>If the services are up, check httpd, keycloak, and ms-metro logs to find the real clue.</span>
        </a>
      </li>
    </ol>
  </div>
  <div class="adf-cockpit-grid">
    <aside class="adf-cockpit-nav adf-panel">
      <p class="adf-panel-label">Quick jump</p>
      <div class="adf-cockpit-jumps">
<a class="adf-cockpit-jump" href="#ui-and-proxy-step-1">
  <span class="adf-route-step">Step 1</span>
  <strong>Apache edge</strong>
  <span>Start here. Confirm httpd.service is active and ports 80 and 443 are listening before checking anything deeper.</span>
</a>
<a class="adf-cockpit-jump" href="#ui-and-proxy-step-2">
  <span class="adf-route-step">Step 2</span>
  <strong>Host health</strong>
  <span>If Apache is up, check disk space, inode usage, available memory, and recent OOM pressure on the host.</span>
</a>
<a class="adf-cockpit-jump" href="#ui-and-proxy-step-3">
  <span class="adf-route-step">Step 3</span>
  <strong>UI services</strong>
  <span>Then check the main UI services: keycloak.service on 8443 and ms-metro.service on 8080.</span>
</a>
<a class="adf-cockpit-jump" href="#ui-and-proxy-step-4">
  <span class="adf-route-step">Step 4</span>
  <strong>Logs</strong>
  <span>If the services are up, check httpd, keycloak, and ms-metro logs to find the real clue.</span>
</a>
      </div>
      <div class="adf-cockpit-sideblock">
        <p class="adf-panel-label">Symptoms that fit here</p>
        <ul>
          <li>Appliance UI is down</li>
          <li>Appliance login page not loading</li>
        </ul>
      </div>
    </aside>
    <div class="adf-cockpit-main">
<details id="ui-and-proxy-step-1" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 1</span>
  <span class="adf-step-heading">
    <strong>Apache edge</strong>
    <span>Check Apache first. Confirm httpd.service is running and ports 80 and 443 are open.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<p class="adf-step-brief">
  <span class="adf-inline-label">Why this step matters:</span> 
Apache is the front door for the UI. If Apache is down, the UI cannot load.
</p>

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

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
If httpd is running and both ports are open, go to the next step.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Stop here and treat httpd.service or the 80/443 listener layer as the current failure point.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Output of systemctl status for httpd.service, keycloak.service, and ms-metro.service.</li>
      <li>Listener output for ports 80, 443, 8443, and 8080 from ss -lntp.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="ui-and-proxy-step-2" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 2</span>
  <span class="adf-step-heading">
    <strong>Host health</strong>
    <span>Check system pressure. Confirm the server still has free disk, free inodes, and available memory.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<p class="adf-step-brief">
  <span class="adf-inline-label">Why this step matters:</span> 
Disk full, inode full, or OOM pressure are common Linux failure points and are more common than Apache rewrite problems.
</p>

<div class="adf-check">
<p class="adf-check-label">Check disk usage</p>

<p class="adf-inline-label">Run</p>

```bash
df -h
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Main filesystems still have free space and are not close to 100% use.
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
If /, /boot, or /data is full or nearly full, services may stop writing logs, temp files, or data.
</p>

<p class="adf-inline-label">Known working example</p>

```text
Filesystem           Size  Used Avail Use% Mounted on
/dev/mapper/rl-root   60G   16G   45G  27% /
/dev/mapper/rl-data  238G   21G  218G   9% /data
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check inode usage</p>

<p class="adf-inline-label">Run</p>

```bash
df -ih
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Main filesystems still have free inodes and are not close to 100% inode use.
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
If inode use is high, services can fail even when normal disk space still looks free.
</p>

<p class="adf-inline-label">Known working example</p>

```text
Filesystem          Inodes IUsed IFree IUse% Mounted on
/dev/mapper/rl-root    30M  343K   30M    2% /
/dev/mapper/rl-data   119M   21K  119M    1% /data
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check memory pressure</p>

<p class="adf-inline-label">Run</p>

```bash
free -h
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The host still has available memory and is not fully relying on swap.
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
If available memory is very low or swap is heavily used, Java services may slow down, hang, or crash.
</p>

<p class="adf-inline-label">Known working example</p>

```text
              total        used        free      shared  buff/cache   available
Mem:           32Gi        13Gi       8.6Gi       2.4Gi         9Gi        15Gi
Swap:          24Gi          0B        24Gi
```
</div>

<div class="adf-check">
<p class="adf-check-label">Check for recent OOM pressure</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -k --since '-7 days' --no-pager | grep -i -E 'out of memory|oom|killed process' | tail -n 20
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
No recent OOM lines are returned.
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
If OOM lines appear, the host has been killing or starving processes under memory pressure.
</p>

<p class="adf-inline-label">Known working example</p>

```text
No output
```
</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
If disk, inode, and memory checks look healthy, go to the service checks.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Stop here and treat host pressure as the current failure point.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Output of systemctl status for httpd.service, keycloak.service, and ms-metro.service.</li>
      <li>Listener output for ports 80, 443, 8443, and 8080 from ss -lntp.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="ui-and-proxy-step-3" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 3</span>
  <span class="adf-step-heading">
    <strong>UI services</strong>
    <span>Check the main UI services. Confirm keycloak.service and ms-metro.service are running and ports 8443 and 8080 are open.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<p class="adf-step-brief">
  <span class="adf-inline-label">Why this step matters:</span> 
After Apache and host health, the next common failure is that a key Java service is down or not listening.
</p>

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
If Keycloak is not running, the login path is failing before the UI can finish loading.
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

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
If the services and listeners look healthy, go to the log checks.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Stop here and treat the missing service or listener as the current failure point.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Disk, inode, memory, and OOM checks from df -h, df -ih, free -h, and journalctl -k.</li>
      <li>Recent journalctl output for httpd.service, keycloak.service, and ms-metro.service.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="ui-and-proxy-step-4" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 4</span>
  <span class="adf-step-heading">
    <strong>Logs</strong>
    <span>Check the logs. Look for disk, memory, startup, or Java errors in httpd, keycloak, and ms-metro.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<p class="adf-step-brief">
  <span class="adf-inline-label">Why this step matters:</span> 
Logs often show disk problems, heap problems, startup failures, and Java stack clues faster than config review.
</p>

<div class="adf-check">
<p class="adf-check-label">Review recent httpd logs</p>

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
If recent httpd lines show errors, stay on Apache and follow that clue first.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Review recent Keycloak logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u keycloak.service -n 50 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
No obvious startup, auth, memory, or crash errors appear in recent lines.
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
If recent Keycloak lines show errors, stay on Keycloak and follow that clue first.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Review recent Metro logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u ms-metro.service -n 50 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
No obvious Java heap, startup, disk, or application crash errors appear in recent lines.
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
If recent Metro lines show errors, stay on Metro and follow that clue first.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
If the logs do not show the issue clearly, move to a narrower service or escalation workflow.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Stop here and treat the service with the clear error as the current failure point.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Disk, inode, memory, and OOM checks from df -h, df -ih, free -h, and journalctl -k.</li>
      <li>Recent journalctl output for httpd.service, keycloak.service, and ms-metro.service.</li>
    </ul>
  </div>
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

