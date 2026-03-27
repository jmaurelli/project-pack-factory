---
title: Application UI won't load
description: Use this when the customer says the application UI is down and the engineer is already on SSH.
sidebar:
  label: Application UI won't load
  order: 1
---

Use this when the customer says the application UI is down and the engineer is already on SSH.

## Console view

<div class="proto-console-shell">
  <aside class="proto-console-rail">
    <div class="proto-panel proto-console-panel">
      <p class="proto-kicker">Working rule</p>
      <p>Move top to bottom. Stop at the first checkpoint that does not look healthy.</p>
    </div>
    <div class="proto-panel proto-console-panel">
      <p class="proto-kicker">Likely surfaces</p>
      <div class="proto-chip-row">
    <span class="proto-chip">httpd.service</span>
    <span class="proto-chip">app-ui.service</span>
    <span class="proto-chip">postgresql.service</span>
      </div>
    </div>
    <div class="proto-panel proto-console-panel">
      <p class="proto-kicker">Route map</p>
      <div class="proto-route proto-console-route"><a class="proto-route-node proto-console-node" href="#ui-step-1">
  <span class="proto-route-step">Step 1</span>
  <strong>Web edge</strong>
  <span>Check the web edge first. Confirm httpd.service is running and ports 80 and 443 are open.</span>
</a>
<a class="proto-route-node proto-console-node" href="#ui-step-2">
  <span class="proto-route-step">Step 2</span>
  <strong>Host pressure</strong>
  <span>Check Linux host pressure next. Confirm the server still has free disk, free inodes, and available memory.</span>
</a>
<a class="proto-route-node proto-console-node" href="#ui-step-3">
  <span class="proto-route-step">Step 3</span>
  <strong>App service</strong>
  <span>Check the main application service. Confirm app-ui.service is running and the app listener is open.</span>
</a>
<a class="proto-route-node proto-console-node" href="#ui-step-4">
  <span class="proto-route-step">Step 4</span>
  <strong>Logs</strong>
  <span>Check recent logs. Look for disk, permission, startup, heap, or dependency errors before escalating.</span>
</a></div>
    </div>
  </aside>
  <div class="proto-console-main">
    <div class="proto-panel proto-console-panel">
      <p class="proto-kicker">Active lane</p>
      <p>Open one checkpoint at a time. Run the command. Compare the output. Stop at the first broken checkpoint.</p>
    </div>
<details id="ui-step-1" class="proto-step proto-step-console">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 1</span>
  <span class="proto-step-heading">
    <strong>Web edge</strong>
    <span>Check the web edge first. Confirm httpd.service is running and ports 80 and 443 are open.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check the web edge first. Confirm httpd.service is running and ports 80 and 443 are open.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>When the UI is down, the fastest first question is whether the front door is still open.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Check httpd.service status</p>

```bash
systemctl status httpd.service --no-pager
```

**Healthy output:** Loaded and active (running).

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- This tells you whether systemd still sees the service as up.
- Focus on Loaded, Active, and the Main PID line.
</div>

**Known-good output:**

```text
● httpd.service - The Apache HTTP Server
   Loaded: loaded (/usr/lib/systemd/system/httpd.service; enabled)
   Active: active (running) since Tue 2026-03-24 09:13:05 UTC; 34min ago
 Main PID: 1243 (/usr/sbin/httpd)
```

</div>

<div class="proto-command-card">
<p class="proto-command-label">Check web listeners</p>

```bash
ss -lntp | grep -E ':(80|443)\b'
```

**Healthy output:** Both ports are listening.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- A service can look up in systemd and still fail to bind the expected port.
- Focus on LISTEN, :80, :443, and the process name.
</div>

**Known-good output:**

```text
LISTEN 0 511 0.0.0.0:443 0.0.0.0:* users:(("httpd",pid=1243,fd=4),...)
LISTEN 0 511 0.0.0.0:80  0.0.0.0:* users:(("httpd",pid=1243,fd=3),...)
```

</div>

</details>

<details id="ui-step-2" class="proto-step proto-step-console">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 2</span>
  <span class="proto-step-heading">
    <strong>Host pressure</strong>
    <span>Check Linux host pressure next. Confirm the server still has free disk, free inodes, and available memory.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check Linux host pressure next. Confirm the server still has free disk, free inodes, and available memory.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>Application failures often come from normal Linux pressure before they come from rare application config problems.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Check disk usage</p>

```bash
df -h
```

**Healthy output:** Main filesystems still have free space and are not near 100% use.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- Disk full is one of the most common triage findings on Linux hosts.
- Focus on Use% and Avail, especially for / and /data.
</div>

**Known-good output:**

```text
Filesystem           Size  Used Avail Use% Mounted on
/dev/mapper/rl-root   60G   17G   44G  28% /
/dev/mapper/rl-data  240G   22G  219G   9% /data
```

</div>

<div class="proto-command-card">
<p class="proto-command-label">Check inode usage</p>

```bash
df -ih
```

**Healthy output:** Main filesystems still have free inodes.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- A filesystem can fail even when disk space looks fine if inode use is exhausted.
- Focus on IUse% and IFree.
</div>

**Known-good output:**

```text
Filesystem          Inodes IUsed IFree IUse% Mounted on
/dev/mapper/rl-root    30M  351K   30M    2% /
/dev/mapper/rl-data   119M   24K  119M    1% /data
```

</div>

<div class="proto-command-card">
<p class="proto-command-label">Check memory pressure</p>

```bash
free -h
```

**Healthy output:** Available memory is present and swap is not heavily used.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- Java applications often slow down or crash before the whole host appears dead.
- Focus on available memory and swap growth.
</div>

**Known-good output:**

```text
              total        used        free      shared  buff/cache   available
Mem:           32Gi        14Gi       7.8Gi       2.1Gi        10Gi        14Gi
Swap:          24Gi          0B        24Gi
```

</div>

<div class="proto-command-card">
<p class="proto-command-label">Check for recent OOM pressure</p>

```bash
journalctl -k --since '-24 hours' --no-pager | grep -i -E 'out of memory|oom|killed process' | tail -n 20
```

**Healthy output:** No recent OOM lines are returned.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- OOM means Linux killed or starved a process because the host ran out of memory.
- If you see OOM lines, host pressure is part of the failure story.
</div>

**Known-good output:**

```text
No output
```

</div>

</details>

<details id="ui-step-3" class="proto-step proto-step-console">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 3</span>
  <span class="proto-step-heading">
    <strong>App service</strong>
    <span>Check the main application service. Confirm app-ui.service is running and the app listener is open.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check the main application service. Confirm app-ui.service is running and the app listener is open.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>If Linux looks healthy, the next common failure is that the app process is down, hung, or unable to bind.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Check app-ui.service status</p>

```bash
systemctl status app-ui.service --no-pager
```

**Healthy output:** Loaded and active (running).

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- This confirms the application service itself is still under systemd control.
- Focus on Active and recent restart history.
</div>

**Known-good output:**

```text
● app-ui.service - Example Application UI
   Loaded: loaded (/etc/systemd/system/app-ui.service; enabled)
   Active: active (running) since Tue 2026-03-24 09:16:42 UTC; 31min ago
 Main PID: 2418 (java)
```

</div>

<div class="proto-command-card">
<p class="proto-command-label">Check application listener</p>

```bash
ss -lntp | grep ':8080\b'
```

**Healthy output:** The application listener is present on 8080.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- A Java process can exist but still fail to open its expected port.
- Focus on LISTEN, :8080, and the owning process.
</div>

**Known-good output:**

```text
LISTEN 0 200 0.0.0.0:8080 0.0.0.0:* users:(("java",pid=2418,fd=202))
```

</div>

</details>

<details id="ui-step-4" class="proto-step proto-step-console">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 4</span>
  <span class="proto-step-heading">
    <strong>Logs</strong>
    <span>Check recent logs. Look for disk, permission, startup, heap, or dependency errors before escalating.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check recent logs. Look for disk, permission, startup, heap, or dependency errors before escalating.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>When services still look healthy, logs usually reveal the real clue faster than deeper config review.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Review web service logs</p>

```bash
journalctl -u httpd.service -n 50 --no-pager
```

**Healthy output:** No obvious startup, permission, or crash errors appear.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- This is the fastest way to confirm whether the web tier is complaining about the application or the host.
</div>

</div>

<div class="proto-command-card">
<p class="proto-command-label">Review application logs</p>

```bash
journalctl -u app-ui.service -n 50 --no-pager
```

**Healthy output:** No obvious startup, heap, dependency, or crash errors appear.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- This is where Java stack traces, dependency failures, and startup loops usually appear first.
</div>

</div>

</details>

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
