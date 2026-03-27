---
title: Application service will not start
description: Use this when a service is stopped, flapping, or exits immediately after restart.
sidebar:
  label: Application service will not start
  order: 2
---

Use this when a service is stopped, flapping, or exits immediately after restart.

## Cockpit layout

<div class="proto-cockpit-shell">
  <div class="proto-cockpit-topbar">
    <div class="proto-panel proto-cockpit-strip">
      <p class="proto-kicker">Case mode</p>
      <p>Live triage over SSH. Reduce guesswork. Keep the next command visible.</p>
    </div>
    <div class="proto-panel proto-cockpit-strip">
      <p class="proto-kicker">Core surfaces</p>
      <div class="proto-chip-row">
        <span class="proto-chip">app-worker.service</span>
        <span class="proto-chip">port 9090</span>
        <span class="proto-chip">lock files</span>
      </div>
    </div>
  </div>
  <div class="proto-cockpit-grid">
    <aside class="proto-cockpit-nav proto-panel">
      <p class="proto-kicker">Quick jump</p>
      <div class="proto-cockpit-jumps"><a class="proto-cockpit-jump" href="#svc-step-1">
  <span class="proto-route-step">Step 1</span>
  <strong>Service state</strong>
</a>
<a class="proto-cockpit-jump" href="#svc-step-2">
  <span class="proto-route-step">Step 2</span>
  <strong>Port or lock conflict</strong>
</a>
<a class="proto-cockpit-jump" href="#svc-step-3">
  <span class="proto-route-step">Step 3</span>
  <strong>Permissions and files</strong>
</a>
<a class="proto-cockpit-jump" href="#svc-step-4">
  <span class="proto-route-step">Step 4</span>
  <strong>Logs</strong>
</a></div>
    </aside>
    <div class="proto-cockpit-main">
      <div class="proto-panel proto-cockpit-strip">
        <p class="proto-kicker">Command deck</p>
        <p>Keep the next command and the healthy reference close together so the engineer can glance left and run right.</p>
      </div>
<details id="svc-step-1" class="proto-step proto-step-cockpit">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 1</span>
  <span class="proto-step-heading">
    <strong>Service state</strong>
    <span>Check the service state first. Confirm whether the service is stopped, failed, or restarting.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check the service state first. Confirm whether the service is stopped, failed, or restarting.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>The quickest way to start triage is to see exactly how systemd understands the failure.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Check app-worker.service status</p>

```bash
systemctl status app-worker.service --no-pager
```

**Healthy output:** Loaded and active (running).

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- Focus on Active, Result, exit code lines, and restart messages.
</div>

**Known-good output:**

```text
● app-worker.service - Example Background Worker
   Loaded: loaded (/etc/systemd/system/app-worker.service; enabled)
   Active: failed (Result: exit-code) since Tue 2026-03-24 10:18:11 UTC; 2min ago
  Process: 7821 ExecStart=/opt/example/bin/worker start (code=exited, status=1/FAILURE)
```

</div>

</details>

<details id="svc-step-2" class="proto-step proto-step-cockpit">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 2</span>
  <span class="proto-step-heading">
    <strong>Port or lock conflict</strong>
    <span>Check for stale lock files or a port that is already occupied by another process.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check for stale lock files or a port that is already occupied by another process.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>Startup failures are often simple Linux conflicts rather than application bugs.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Check for port conflicts</p>

```bash
ss -lntp | grep ':9090\b'
```

**Healthy output:** Only the expected service owns the port, or no stale listener is present before startup.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- If another process already owns the port, the service cannot bind and will fail to start.
</div>

**Known-good output:**

```text
LISTEN 0 128 0.0.0.0:9090 0.0.0.0:* users:(("java",pid=8121,fd=122))
```

</div>

<div class="proto-command-card">
<p class="proto-command-label">Check for stale lock files</p>

```bash
find /var/run /tmp -maxdepth 2 -type f | grep app-worker
```

**Healthy output:** No stale lock or pid file is left behind after a failed run.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- Applications sometimes refuse to start because they think an old instance is still running.
</div>

**Known-good output:**

```text
No output
```

</div>

</details>

<details id="svc-step-3" class="proto-step proto-step-cockpit">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 3</span>
  <span class="proto-step-heading">
    <strong>Permissions and files</strong>
    <span>Check runtime paths and permissions. Confirm the service can read configs and write temp or log files.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check runtime paths and permissions. Confirm the service can read configs and write temp or log files.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>Permissions, ownership, and missing files are classic Linux startup failures.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Check service user and runtime directories</p>

```bash
namei -l /opt/example /opt/example/logs /opt/example/tmp
```

**Healthy output:** The service user can traverse and write the required directories.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- This exposes ownership and mode bits across the whole path, not just the final directory.
</div>

**Known-good output:**

```text
f: /opt/example/logs
drwxr-xr-x root     root     /
drwxr-xr-x root     root     opt
drwxr-x--- example  example  example
drwxrwx--- example  example  logs
```

</div>

</details>

<details id="svc-step-4" class="proto-step proto-step-cockpit">
<summary class="proto-step-summary">
  <span class="proto-step-badge">Step 4</span>
  <span class="proto-step-heading">
    <strong>Logs</strong>
    <span>Check recent logs. Look for permission, bind, config, file lock, or dependency errors.</span>
  </span>
  <span class="proto-step-toggle" aria-hidden="true"></span>
</summary>
<div class="proto-panel proto-focus">
  <p class="proto-kicker">Checkpoint focus</p>
  <p>Check recent logs. Look for permission, bind, config, file lock, or dependency errors.</p>
</div>
<div class="proto-panel proto-why">
  <p class="proto-kicker">Why this matters</p>
  <p>Once simple Linux conflicts are ruled out, the logs usually show the direct startup blocker.</p>
</div>
<div class="proto-command-card">
<p class="proto-command-label">Review service logs</p>

```bash
journalctl -u app-worker.service -n 80 --no-pager
```

**Healthy output:** No recurring bind, permission, dependency, or stack trace errors appear.

<div class="proto-panel proto-mini-why">
  <p class="proto-kicker">Why this matters</p>

- This is where you will usually find the first clear reason the process exited.
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
