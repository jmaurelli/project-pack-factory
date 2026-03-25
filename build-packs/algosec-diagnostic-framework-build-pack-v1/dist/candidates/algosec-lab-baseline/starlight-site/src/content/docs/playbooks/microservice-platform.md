---
title: Microservice Platform
description: Use this when one product feature fails after login and the UI itself is still up.
sidebar:
  label: Microservice Platform
  order: 3
---

Use this when one product feature fails after login and the UI itself is still up.

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
        <span class="adf-service-chip">ms-batch-application.service</span>
        <span class="adf-service-chip">ms-bflow.service</span>
        <span class="adf-service-chip">ms-cloudlicensing.service</span>
        <span class="adf-service-chip">ms-configuration.service</span>
      </div>
    </div>
  </div>
  <div class="adf-cockpit-grid">
    <aside class="adf-cockpit-nav adf-panel">
      <p class="adf-panel-label">Quick jump</p>
      <div class="adf-cockpit-jumps">
<a class="adf-cockpit-jump" href="#microservice-platform-step-1">
  <span class="adf-route-step">Step 1</span>
  <strong>Identify the exact failing feature or ms-* path in the customer session so the diagnostic path stays anchored to one concrete product behavior</strong>
  <span>Identify the exact failing feature or ms-* path in the customer session so the diagnostic path stays anchored to one concrete product behavior.</span>
</a>
<a class="adf-cockpit-jump" href="#microservice-platform-step-2">
  <span class="adf-route-step">Step 2</span>
  <strong>Confirm algosec-ms</strong>
  <span>Confirm algosec-ms.service completed successfully and that the likely target service set is healthy: ms-batch-application.service, ms-bflow.service, ms-cloudlicensing.service.</span>
</a>
<a class="adf-cockpit-jump" href="#microservice-platform-step-3">
  <span class="adf-route-step">Step 3</span>
  <strong>Confirm the customer-facing failing path still maps to the expected local target port for that microservice</strong>
  <span>Confirm the customer-facing failing path still maps to the expected local target port for that microservice.</span>
</a>
<a class="adf-cockpit-jump" href="#microservice-platform-step-4">
  <span class="adf-route-step">Step 4</span>
  <strong>Confirm ms-configuration</strong>
  <span>Confirm ms-configuration.service is healthy before assuming the issue is isolated to the single feature path.</span>
</a>
<a class="adf-cockpit-jump" href="#microservice-platform-step-5">
  <span class="adf-route-step">Step 5</span>
  <strong>Collect the relevant ms-* service status or error snippet and decide whether the issue stays in the target service or moves to shared dependencies like httpd</strong>
  <span>Collect the relevant ms-* service status or error snippet and decide whether the issue stays in the target service or moves to shared dependencies like httpd.service.</span>
</a>
      </div>
      <div class="adf-cockpit-sideblock">
        <p class="adf-panel-label">Symptoms that fit here</p>
        <ul>
          <li>Feature failing behind UI</li>
          <li>Specific microservice path failing</li>
        </ul>
      </div>
    </aside>
    <div class="adf-cockpit-main">
      <div class="adf-panel adf-cockpit-strip">
        <p class="adf-panel-label">Command-first flow</p>
        <p>Open one checkpoint, run the listed read-only commands, compare the healthy signal, then stop at the first failure point.</p>
      </div>
<details id="microservice-platform-step-1" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 1</span>
  <span class="adf-step-heading">
    <strong>Identify the exact failing feature or ms-* path in the customer session so the diagnostic path stays anchored to one concrete product behavior</strong>
    <span>Identify the exact failing feature or ms-* path in the customer session so the diagnostic path stays anchored to one concrete product behavior.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to wrapper and target-service validation.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
If the failing feature cannot be isolated, collect the customer symptom and stay at the domain level before picking a narrower path.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Status of the routed path /ms-batch-application/local, /ms-batch-application and whether it still maps to 8159.</li>
      <li>Status of the routed path /BusinessFlow/local, /BusinessFlow and whether it still maps to 8081.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="microservice-platform-step-2" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 2</span>
  <span class="adf-step-heading">
    <strong>Confirm algosec-ms</strong>
    <span>Confirm algosec-ms.service completed successfully and that the likely target service set is healthy: ms-batch-application.service, ms-bflow.service, ms-cloudlicensing.service.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Check algosec-ms.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status algosec-ms.service --no-pager
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
If this wrapper is unhealthy, start at the shared microservice platform before chasing one feature path.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check ms-batch-application.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status ms-batch-application.service --no-pager
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
If the target ms-* service is unhealthy, treat that service as the current failure point.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to routed-path validation.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Treat algosec-ms.service or the first failing ms-* service as the current failure point.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Status of the routed path /BusinessFlow/local, /BusinessFlow and whether it still maps to 8081.</li>
      <li>Visible state of algosec-ms.service and ms-configuration.service.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="microservice-platform-step-3" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 3</span>
  <span class="adf-step-heading">
    <strong>Confirm the customer-facing failing path still maps to the expected local target port for that microservice</strong>
    <span>Confirm the customer-facing failing path still maps to the expected local target port for that microservice.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Check microservice listener</p>

<p class="adf-inline-label">Run</p>

```bash
ss -lntp | grep -E ':8159\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
A listening socket is present for 8159.
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
If the target port is missing, the feature path may be failing before the request reaches the service.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check config mapping</p>

<p class="adf-inline-label">Run</p>

```bash
grep -n 8159 /etc/httpd/conf.d/algosec-ms.ms-batch-application.conf
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The expected mapping token 8159 appears in /etc/httpd/conf.d/algosec-ms.ms-batch-application.conf.
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
If the proxy mapping is wrong, the customer path may point to the wrong backend or no backend at all.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to shared-configuration validation.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Treat the routed path or local target port mapping as the current failure point.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Status of the routed path /ms-batch-application/local, /ms-batch-application and whether it still maps to 8159.</li>
      <li>Status of the routed path /BusinessFlow/local, /BusinessFlow and whether it still maps to 8081.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="microservice-platform-step-4" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 4</span>
  <span class="adf-step-heading">
    <strong>Confirm ms-configuration</strong>
    <span>Confirm ms-configuration.service is healthy before assuming the issue is isolated to the single feature path.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Check ms-configuration.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status ms-configuration.service --no-pager
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
If configuration is unhealthy, many downstream ms-* services can fail together.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to dependency and error review.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Treat ms-configuration.service as the current failure point because other microservices depend on it.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Visible state of algosec-ms.service and ms-configuration.service.</li>
      <li>Any service status, console error, or log snippet for the failing ms-* feature path.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="microservice-platform-step-5" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 5</span>
  <span class="adf-step-heading">
    <strong>Collect the relevant ms-* service status or error snippet and decide whether the issue stays in the target service or moves to shared dependencies like httpd</strong>
    <span>Collect the relevant ms-* service status or error snippet and decide whether the issue stays in the target service or moves to shared dependencies like httpd.service.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Review ms-batch-application.service logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u ms-batch-application.service -n 50 --no-pager
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
Use recent log lines to separate local service failure, permission issues, and deeper shared dependency problems.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Inspect dependency services next: httpd.service, ms-configuration.service.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
If the error evidence cannot be collected, escalate with the routed-path and service-state checks already captured.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Visible state of algosec-ms.service and ms-configuration.service.</li>
      <li>Any service status, console error, or log snippet for the failing ms-* feature path.</li>
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

