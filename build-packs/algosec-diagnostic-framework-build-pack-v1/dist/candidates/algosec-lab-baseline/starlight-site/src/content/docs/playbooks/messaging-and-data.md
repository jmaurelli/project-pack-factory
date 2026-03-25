---
title: Messaging and Data
description: Use this when jobs stop, queues back up, or data actions fail.
sidebar:
  label: Messaging and Data
  order: 4
---

Use this when jobs stop, queues back up, or data actions fail.

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
        <span class="adf-service-chip">activemq.service</span>
        <span class="adf-service-chip">postgresql.service</span>
      </div>
    </div>
  </div>
  <div class="adf-cockpit-grid">
    <aside class="adf-cockpit-nav adf-panel">
      <p class="adf-panel-label">Quick jump</p>
      <div class="adf-cockpit-jumps">
<a class="adf-cockpit-jump" href="#messaging-and-data-step-1">
  <span class="adf-route-step">Step 1</span>
  <strong>Confirm the customer symptom is really a stuck job, stalled event, or data-backed action failure instead of a pure UI-path issue</strong>
  <span>Confirm the customer symptom is really a stuck job, stalled event, or data-backed action failure instead of a pure UI-path issue.</span>
</a>
<a class="adf-cockpit-jump" href="#messaging-and-data-step-2">
  <span class="adf-route-step">Step 2</span>
  <strong>Confirm activemq</strong>
  <span>Confirm activemq.service is active and listener 61616 is present before assuming the issue is only downstream data state.</span>
</a>
<a class="adf-cockpit-jump" href="#messaging-and-data-step-3">
  <span class="adf-route-step">Step 3</span>
  <strong>Confirm postgresql</strong>
  <span>Confirm postgresql.service is active and that the customer environment shows no obvious database connectivity or state error.</span>
</a>
<a class="adf-cockpit-jump" href="#messaging-and-data-step-4">
  <span class="adf-route-step">Step 4</span>
  <strong>Review the visible queue, backlog, or stuck-job signal and decide whether the problem stays in broker/data infrastructure or should move back to a feature-specific domain</strong>
  <span>Review the visible queue, backlog, or stuck-job signal and decide whether the problem stays in broker/data infrastructure or should move back to a feature-specific domain.</span>
</a>
      </div>
      <div class="adf-cockpit-sideblock">
        <p class="adf-panel-label">Symptoms that fit here</p>
        <ul>
          <li>Job stuck or not progressing</li>
          <li>Data-backed action failing</li>
        </ul>
      </div>
    </aside>
    <div class="adf-cockpit-main">
      <div class="adf-panel adf-cockpit-strip">
        <p class="adf-panel-label">Command-first flow</p>
        <p>Open one checkpoint, run the listed read-only commands, compare the healthy signal, then stop at the first failure point.</p>
      </div>
<details id="messaging-and-data-step-1" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 1</span>
  <span class="adf-step-heading">
    <strong>Confirm the customer symptom is really a stuck job, stalled event, or data-backed action failure instead of a pure UI-path issue</strong>
    <span>Confirm the customer symptom is really a stuck job, stalled event, or data-backed action failure instead of a pure UI-path issue.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to broker validation.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
If the symptom is UI-only, switch to UI and Proxy or Microservice Platform instead of staying here.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Visible status of activemq.service and whether listener 61616 is present.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="messaging-and-data-step-2" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 2</span>
  <span class="adf-step-heading">
    <strong>Confirm activemq</strong>
    <span>Confirm activemq.service is active and listener 61616 is present before assuming the issue is only downstream data state.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Check activemq.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status activemq.service --no-pager
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
If the broker is not active, stop here and treat messaging infrastructure as the likely failure point.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Check broker listener</p>

<p class="adf-inline-label">Run</p>

```bash
ss -lntp | grep -E ':61616\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
A listening socket is present for 61616.
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
If 61616 is missing, queued work may fail before any feature-specific processing begins.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to database validation.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Treat activemq.service or the 61616 listener as the current failure point.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Visible status of activemq.service and whether listener 61616 is present.</li>
      <li>Visible status of postgresql.service and any database connectivity error.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="messaging-and-data-step-3" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 3</span>
  <span class="adf-step-heading">
    <strong>Confirm postgresql</strong>
    <span>Confirm postgresql.service is active and that the customer environment shows no obvious database connectivity or state error.</span>
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
If the database is not active, treat data availability as the underlying failure point.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
Continue to backlog or queue-state review.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
Treat postgresql.service as the current failure point for this issue.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Visible status of postgresql.service and any database connectivity error.</li>
      <li>Any stuck job, queue, or backlog indicator shown during the customer session.</li>
    </ul>
  </div>
</div>

</div>
</details>

<details id="messaging-and-data-step-4" class="adf-checkpoint">
<summary class="adf-step-summary">
  <span class="adf-step-badge">Step 4</span>
  <span class="adf-step-heading">
    <strong>Review the visible queue, backlog, or stuck-job signal and decide whether the problem stays in broker/data infrastructure or should move back to a feature-specific domain</strong>
    <span>Review the visible queue, backlog, or stuck-job signal and decide whether the problem stays in broker/data infrastructure or should move back to a feature-specific domain.</span>
  </span>
  <span class="adf-step-toggle" aria-hidden="true"></span>
</summary>

<div class="adf-step-body">
<div class="adf-check">
<p class="adf-check-label">Review activemq.service logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u activemq.service -n 50 --no-pager
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
Use broker log lines to decide whether the queue layer is blocked, degraded, or forwarding the issue downstream.
</p>

</div>

<div class="adf-check">
<p class="adf-check-label">Review postgresql.service logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u postgresql.service -n 50 --no-pager
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
Use database log lines to spot deeper availability or permission problems affecting queued work.
</p>

</div>

<div class="adf-step-outcomes">
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If healthy:</span> 
If infrastructure checks passed, move to the feature-specific domain that owns the stalled job or action.
  </p>
  <p class="adf-step-outcome">
    <span class="adf-inline-label">If this fails:</span> 
If queue or backlog evidence cannot be gathered, escalate with the broker and database checks already captured.
  </p>
  <div class="adf-step-evidence">
    <p class="adf-inline-label">Collect before moving on:</p>
    <ul>
      <li>Visible status of activemq.service and whether listener 61616 is present.</li>
      <li>Visible status of postgresql.service and any database connectivity error.</li>
      <li>Any stuck job, queue, or backlog indicator shown during the customer session.</li>
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

