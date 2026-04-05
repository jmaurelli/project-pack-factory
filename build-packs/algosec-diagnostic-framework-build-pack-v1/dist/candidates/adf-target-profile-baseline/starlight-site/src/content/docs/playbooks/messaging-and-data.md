---
title: Messaging and Data
description: ""
sidebar:
  label: Messaging and Data
  order: 4
---

## Use this page when

- jobs stop, queues back up, or data actions fail.

## Check activemq.service

Use the checks below to confirm whether this service or module is the current failure point.

## Command flow

<div class="adf-preview-shell adf-preview-field-manual">
  <section class="adf-preview-manual-cover">
    <h2>Messaging and Data</h2>
  </section>
  <section class="adf-preview-manual-contents">
    <p class="adf-panel-label">Steps</p>
    <ol class="adf-preview-manual-list">
<li><a class="adf-preview-manual-link" href="#manual-messaging-and-data-step-1" data-adf-manual-target="manual-messaging-and-data-step-1"><span>Step 1</span><strong>Confirm the customer symptom is really a stuck job, stalled event, or data-backed action failure instead of a pure UI-path issue</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-messaging-and-data-step-2" data-adf-manual-target="manual-messaging-and-data-step-2"><span>Step 2</span><strong>Confirm activemq</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-messaging-and-data-step-3" data-adf-manual-target="manual-messaging-and-data-step-3"><span>Step 3</span><strong>Confirm postgresql</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-messaging-and-data-step-4" data-adf-manual-target="manual-messaging-and-data-step-4"><span>Step 4</span><strong>Review the visible queue, backlog, or stuck-job signal and decide whether the problem stays in broker/data infrastructure or should move back to a feature-specific domain</strong></a></li>
    </ol>
  </section>
  <section class="adf-preview-manual-body">
<details id="manual-messaging-and-data-step-1" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 1</span>
      <span class="adf-preview-manual-summary-title">Confirm the customer symptom is really a stuck job, stalled event, or data-backed action failure instead of a pure UI-path issue</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">0 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  </div>
</details>
<details id="manual-messaging-and-data-step-2" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 2</span>
      <span class="adf-preview-manual-summary-title">Confirm activemq</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">2 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check activemq.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status activemq.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
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
  <span class="adf-inline-label">Expected result:</span> 
A listening socket is present for 61616.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If 61616 is missing, queued work may fail before any feature-specific processing begins.
</p>

</div>

  </div>
  </div>
</details>
<details id="manual-messaging-and-data-step-3" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 3</span>
      <span class="adf-preview-manual-summary-title">Confirm postgresql</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check postgresql.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status postgresql.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the database is not active, treat data availability as the underlying failure point.
</p>

</div>

  </div>
  </div>
</details>
<details id="manual-messaging-and-data-step-4" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 4</span>
      <span class="adf-preview-manual-summary-title">Review the visible queue, backlog, or stuck-job signal and decide whether the problem stays in broker/data infrastructure or should move back to a feature-specific domain</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">2 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Review activemq.service logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u activemq.service -n 50 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent lines show healthy startup or a clear error signature to classify.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
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
  <span class="adf-inline-label">Expected result:</span> 
Recent lines show healthy startup or a clear error signature to classify.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use database log lines to spot deeper availability or permission problems affecting queued work.
</p>

</div>

  </div>
  </div>
</details>
  </section>
</div>

## If this boundary still looks unhealthy

- Keep the case on this service and escalate with the saved evidence.

## If this boundary looks healthy

- If Activemq.Service looks healthy, move to the deeper ASMS guide for the next layer.

## What to save

- Visible status of activemq.service and whether listener 61616 is present.
- Visible status of postgresql.service and any database connectivity error.
- Any stuck job, queue, or backlog indicator shown during the customer session.

## When to escalate

- Keep the case on this service and escalate with the saved evidence.
- Escalate after the bounded checks and any approved safe restart step if the saved evidence still points to this boundary.

