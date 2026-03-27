---
title: FireFlow Backend
description: Use this when a FireFlow action fails or FireFlow returns an error.
sidebar:
  label: FireFlow Backend
  order: 2
---

Use this when a FireFlow action fails or FireFlow returns an error.

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
        <span class="adf-service-chip">aff-boot.service</span>
      </div>
    </div>
  </div>
  <div class="adf-panel adf-cockpit-strip">
    <p class="adf-panel-label">Command-first flow</p>
    <p>Open one checkpoint, run the listed read-only commands, compare the healthy signal, then stop at the first failure point.</p>
  </div>
  <div class="adf-cockpit-grid">
    <aside class="adf-cockpit-nav adf-panel">
      <p class="adf-panel-label">Quick jump</p>
      <div class="adf-cockpit-jumps">
<a class="adf-cockpit-jump" href="#core-aff-step-1">
  <span class="adf-route-step">Step 1</span>
  <strong>Identify the failing FireFlow action and confirm that the symptom is tied to /FireFlow/api or /aff/api</strong>
  <span>Identify the failing FireFlow action and confirm that the symptom is tied to /FireFlow/api or /aff/api.</span>
</a>
<a class="adf-cockpit-jump" href="#core-aff-step-2">
  <span class="adf-route-step">Step 2</span>
  <strong>Confirm aff-boot</strong>
  <span>Confirm aff-boot.service is active and that the failing FireFlow route still proxies to localhost:1989.</span>
</a>
<a class="adf-cockpit-jump" href="#core-aff-step-3">
  <span class="adf-route-step">Step 3</span>
  <strong>Confirm postgresql</strong>
  <span>Confirm postgresql.service is active and local database access is healthy before assuming a FireFlow-only fault.</span>
</a>
<a class="adf-cockpit-jump" href="#core-aff-step-4">
  <span class="adf-route-step">Step 4</span>
  <strong>Collect the latest FireFlow-related error lines or status output and decide whether the failure stays in FireFlow logic or must move deeper into dependencies</strong>
  <span>Collect the latest FireFlow-related error lines or status output and decide whether the failure stays in FireFlow logic or must move deeper into dependencies.</span>
</a>
      </div>
      <div class="adf-cockpit-sideblock">
        <p class="adf-panel-label">Symptoms that fit here</p>
        <ul>
          <li>FireFlow action failing</li>
          <li>FireFlow API error</li>
        </ul>
      </div>
    </aside>
    <div class="adf-cockpit-main">
<details id="core-aff-step-1" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 1</span>
  <span class="adf-step-heading">
    <strong>Identify the failing FireFlow action and confirm that the symptom is tied to /FireFlow/api or /aff/api</strong>
    <span>Identify the failing FireFlow action and confirm that the symptom is tied to /FireFlow/api or /aff/api.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Check config mapping</p>

<p class="adf-inline-label">Run</p>

```bash
grep -n 1989 /etc/httpd/conf.d/aff.conf
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The expected mapping token 1989 appears in /etc/httpd/conf.d/aff.conf.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: config check</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks whether the expected mapping still exists in the service config.
- Use it to confirm the route, port, or target value is still what the application expects.
  </div>
</details>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
Use the known proxy mapping to confirm the FireFlow path really terminates at the expected backend.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to aff-boot and route validation.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
If the symptom is not tied to FireFlow, switch to a different domain playbook instead of staying here.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Result of the failing FireFlow action, including the exact endpoint or screen.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="core-aff-step-2" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 2</span>
  <span class="adf-step-heading">
    <strong>Confirm aff-boot</strong>
    <span>Confirm aff-boot.service is active and that the failing FireFlow route still proxies to localhost:1989.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Check aff-boot.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status aff-boot.service --no-pager
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

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If aff-boot is not active, stop here and treat the FireFlow service itself as the failure point.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check FireFlow listener</p>

<p class="adf-inline-label">Run</p>

```bash
ss -lntp | grep -E ':1989\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
A listening socket is present for 1989.
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

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
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
  <span class="adf-inline-label">Verification:</span> 
The expected mapping token 1989 appears in /etc/httpd/conf.d/aff.conf.
</p>

<details class="adf-check-note">
  <summary class="adf-check-note-summary">
    <span>Linux note: config check</span>
  </summary>
  <div class="adf-check-knowledge">

- This checks whether the expected mapping still exists in the service config.
- Use it to confirm the route, port, or target value is still what the application expects.
  </div>
</details>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the proxy config no longer points to 1989, the FireFlow request path may be broken even when the service is up.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to database validation.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Treat aff-boot.service or the 1989 route as the current failure point.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Result of the failing FireFlow action, including the exact endpoint or screen.</li>
      <li>Visible status for aff-boot.service and postgresql.service.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="core-aff-step-3" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 3</span>
  <span class="adf-step-heading">
    <strong>Confirm postgresql</strong>
    <span>Confirm postgresql.service is active and local database access is healthy before assuming a FireFlow-only fault.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Check postgresql.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status postgresql.service --no-pager
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

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the database is not active, FireFlow symptoms are likely downstream of data availability.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to FireFlow log review.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Treat postgresql.service as the current failure point for this customer issue.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Visible status for aff-boot.service and postgresql.service.</li>
      <li>Any recent FireFlow-related lines from the customer-facing logs or service status output.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="core-aff-step-4" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 4</span>
  <span class="adf-step-heading">
    <strong>Collect the latest FireFlow-related error lines or status output and decide whether the failure stays in FireFlow logic or must move deeper into dependencies</strong>
    <span>Collect the latest FireFlow-related error lines or status output and decide whether the failure stays in FireFlow logic or must move deeper into dependencies.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Review aff-boot.service logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u aff-boot.service -n 50 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Recent lines show healthy startup or a clear error signature to classify.
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
Look for permission errors, startup failures, or dependency errors that explain why FireFlow is unhealthy.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Inspect dependency services next: postgresql.service.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
If you cannot collect the logs, escalate with the route, service, and database checks already captured.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Visible status for aff-boot.service and postgresql.service.</li>
      <li>Any recent FireFlow-related lines from the customer-facing logs or service status output.</li>
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

