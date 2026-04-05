---
title: Microservice Platform
description: ""
sidebar:
  label: Microservice Platform
  order: 3
---

## Use this page when

- one product feature fails after login and the UI itself is still up.

## Check ms-batch-application.service

Use the checks below to confirm whether this service or module is the current failure point.

## Command flow

<div class="adf-preview-shell adf-preview-field-manual">
  <section class="adf-preview-manual-cover">
    <h2>Microservice Platform</h2>
  </section>
  <section class="adf-preview-manual-contents">
    <p class="adf-panel-label">Steps</p>
    <ol class="adf-preview-manual-list">
<li><a class="adf-preview-manual-link" href="#manual-microservice-platform-step-1" data-adf-manual-target="manual-microservice-platform-step-1"><span>Step 1</span><strong>Identify the exact failing feature or ms-* path in the customer session so the diagnostic path stays anchored to one concrete product behavior</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-microservice-platform-step-2" data-adf-manual-target="manual-microservice-platform-step-2"><span>Step 2</span><strong>Confirm algosec-ms</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-microservice-platform-step-3" data-adf-manual-target="manual-microservice-platform-step-3"><span>Step 3</span><strong>Confirm the customer-facing failing path still maps to the expected local target port for that microservice</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-microservice-platform-step-4" data-adf-manual-target="manual-microservice-platform-step-4"><span>Step 4</span><strong>Confirm ms-configuration</strong></a></li>
<li><a class="adf-preview-manual-link" href="#manual-microservice-platform-step-5" data-adf-manual-target="manual-microservice-platform-step-5"><span>Step 5</span><strong>Collect the relevant ms-* service status or error snippet and decide whether the issue stays in the target service or moves to shared dependencies like httpd</strong></a></li>
    </ol>
  </section>
  <section class="adf-preview-manual-body">
<details id="manual-microservice-platform-step-1" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 1</span>
      <span class="adf-preview-manual-summary-title">Identify the exact failing feature or ms-* path in the customer session so the diagnostic path stays anchored to one concrete product behavior</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">0 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  </div>
</details>
<details id="manual-microservice-platform-step-2" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 2</span>
      <span class="adf-preview-manual-summary-title">Confirm algosec-ms</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">2 commands</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check algosec-ms.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status algosec-ms.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
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
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the target ms-* service is unhealthy, treat that service as the current failure point.
</p>

</div>

  </div>
  </div>
</details>
<details id="manual-microservice-platform-step-3" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 3</span>
      <span class="adf-preview-manual-summary-title">Confirm the customer-facing failing path still maps to the expected local target port for that microservice</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check config mapping</p>

<p class="adf-inline-label">Run</p>

```bash
sed -n '1,160p' /etc/httpd/conf.d/algosec-ms.conf
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The expected proxy or service mapping is visible in /etc/httpd/conf.d/algosec-ms.conf.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the proxy mapping is wrong, the customer path may point to the wrong backend or no backend at all.
</p>

</div>

  </div>
  </div>
</details>
<details id="manual-microservice-platform-step-4" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 4</span>
      <span class="adf-preview-manual-summary-title">Confirm ms-configuration</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Check ms-configuration.service status</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status ms-configuration.service --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Unit is loaded and active (running).
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If configuration is unhealthy, many downstream ms-* services can fail together.
</p>

</div>

  </div>
  </div>
</details>
<details id="manual-microservice-platform-step-5" class="adf-preview-manual-step" data-adf-manual-step="true">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 5</span>
      <span class="adf-preview-manual-summary-title">Collect the relevant ms-* service status or error snippet and decide whether the issue stays in the target service or moves to shared dependencies like httpd</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count" title="Commands to run in this step">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <div class="adf-preview-manual-callout">
<div class="adf-check">
<p class="adf-check-label">Review ms-batch-application.service logs</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u ms-batch-application.service -n 50 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent lines show healthy startup or a clear error signature to classify.
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
Use recent log lines to separate local service failure, permission issues, and deeper shared dependency problems.
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

- If Ms-Batch-Application.Service looks healthy, move to the deeper ASMS guide for the next layer.

## What to save

- Visible state of algosec-ms.service and ms-configuration.service.
- Any service status, console error, or log snippet for the failing ms-* feature path.

## When to escalate

- Keep the case on this service and escalate with the saved evidence.
- Escalate after the bounded checks and any approved safe restart step if the saved evidence still points to this boundary.

