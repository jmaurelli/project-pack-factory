---
title: "Canonical Playbook Template: Field Manual"
description: "ADF's canonical playbook shell: a chapter-style runbook with editorial pacing, wider reading flow, and calmer operator guidance."
sidebar:
  label: "Field Manual"
  order: 1
---

ADF's canonical playbook shell: a chapter-style runbook with editorial pacing, wider reading flow, and calmer operator guidance.

<div class="adf-template-intro adf-panel">
  <p class="adf-panel-label">Canonical template</p>
  <h2>Field Manual</h2>
  <p>This is now the only approved ADF playbook shell. The older playbook set and the earlier template experiments were intentionally removed from publication.</p>
  <p><strong>Rebuild rule:</strong> New ADF playbooks should be authored against this shell first and only then published.</p>
</div>

<div class="adf-preview-shell adf-preview-field-manual">
  <section class="adf-preview-manual-cover">
    <p class="adf-panel-label">Field Manual</p>
    <h2>ASMS UI is down</h2>
    <p>The suite login shell or UI is not doing useful work.</p>
    <p class="adf-preview-manual-when"><strong>When to use this:</strong> Reach for this version when the operator needs a calmer chapter-by-chapter guide instead of a board or console.</p>
  </section>
  <section class="adf-preview-manual-contents">
    <p class="adf-panel-label">Contents</p>
    <ol class="adf-preview-manual-list">
<li><a href="#manual-ui-and-proxy-step-1"><span>Step 1</span><strong>Confirm the host is healthy before you chase Apache, auth, or app signals</strong></a></li>
<li><a href="#manual-ui-and-proxy-step-2"><span>Step 2</span><strong>Prove Apache is answering and routing the suite shell correctly</strong></a></li>
<li><a href="#manual-ui-and-proxy-step-3"><span>Step 3</span><strong>Check whether the auth branch can complete useful work instead of just redirecting</strong></a></li>
<li><a href="#manual-ui-and-proxy-step-4"><span>Step 4</span><strong>Validate the first app-side dependency that should answer real UI work</strong></a></li>
<li><a href="#manual-ui-and-proxy-step-5"><span>Step 5</span><strong>If useful work still stops here, use Apache, Keycloak, and Metro clues to find the first clear stop point</strong></a></li>
    </ol>
  </section>
  <section class="adf-preview-manual-body">
    <article class="adf-preview-manual-prologue">
      <p class="adf-panel-label">Operator note</p>
      <p>This version reads like a guided field manual. Each chapter is meant to be read, then executed, instead of skimmed like a dashboard card.</p>
    </article>
<details id="manual-ui-and-proxy-step-1" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 1</span>
      <span class="adf-preview-manual-summary-title">Host can support useful work</span>
      <span class="adf-preview-manual-action">Confirm the host is healthy before you chase Apache, auth, or app signals.</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <p>If the host cannot support useful work, every higher branch is downstream noise.</p>
  <div class="adf-preview-manual-callout">
    <p class="adf-panel-label">Field note</p>
<div class="adf-check">
<p class="adf-check-label">Check host pressure</p>

<p class="adf-inline-label">Run</p>

```bash
uptime && free -m && df -h /
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Load is reasonable, memory is available, and the root filesystem is not full.
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
Look for: load average, Mem:, Filesystem
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If the host is clearly under pressure, stop here and stabilize the box first.
</p>

<p class="adf-inline-label">Known working example</p>

```text
load average: 0.32, 0.41, 0.55
Mem: 16000 6200 4200 120 5600 9300
/dev/sda1 80G 31G 47G 40% /
```
</div>

  </div>
  <div class="adf-preview-manual-branch">
    <p><strong>If healthy:</strong> Move to the HTTP edge and prove Apache can serve useful work.</p>
    <p><strong>If not healthy:</strong> Treat host pressure as the first stop point.</p>
  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-2" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 2</span>
      <span class="adf-preview-manual-summary-title">Apache/HTTPD serving the UI</span>
      <span class="adf-preview-manual-action">Prove Apache is answering and routing the suite shell correctly.</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <p>If the edge cannot serve the shell, deeper auth and app checks are premature.</p>
  <div class="adf-preview-manual-callout">
    <p class="adf-panel-label">Field note</p>
<div class="adf-check">
<p class="adf-check-label">Check Apache service and shell response</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl is-active httpd && curl -k -I https://127.0.0.1/algosec/suite/login
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Apache is active and the suite login returns an expected HTTP response.
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
Look for: active, HTTP/1.1 302, Location:
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If Apache is down or the shell route is missing, stop at the edge.
</p>

<p class="adf-inline-label">Known working example</p>

```text
active
HTTP/1.1 302 Found
Location: https://127.0.0.1/algosec-ui/login
```
</div>

  </div>
  <div class="adf-preview-manual-branch">
    <p><strong>If healthy:</strong> Continue into the auth branch.</p>
    <p><strong>If not healthy:</strong> Treat Apache or the edge route as the first stop point.</p>
  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-3" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 3</span>
      <span class="adf-preview-manual-summary-title">Auth branch can do useful work</span>
      <span class="adf-preview-manual-action">Check whether the auth branch can complete useful work instead of just redirecting.</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <p>A healthy shell with a broken auth hop still leaves the operator blocked.</p>
  <div class="adf-preview-manual-callout">
    <p class="adf-panel-label">Field note</p>
<div class="adf-check">
<p class="adf-check-label">Check Keycloak reachability</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl is-active keycloak && curl -k -I https://127.0.0.1/auth/
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Keycloak is active and the auth route responds instead of timing out.
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
Look for: active, HTTP/1.1
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If auth cannot answer useful requests, stop on the auth branch.
</p>

<p class="adf-inline-label">Known working example</p>

```text
active
HTTP/1.1 200 OK
```
</div>

  </div>
  <div class="adf-preview-manual-branch">
    <p><strong>If healthy:</strong> Move to the first useful-work app hop.</p>
    <p><strong>If not healthy:</strong> Treat auth as the first stop point.</p>
  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-4" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 4</span>
      <span class="adf-preview-manual-summary-title">App branch can do useful work</span>
      <span class="adf-preview-manual-action">Validate the first app-side dependency that should answer real UI work.</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <p>This separates a generic shell problem from an app-branch failure.</p>
  <div class="adf-preview-manual-callout">
    <p class="adf-panel-label">Field note</p>
<div class="adf-check">
<p class="adf-check-label">Check Metro health</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl is-active ms-metro && curl -sS http://127.0.0.1:8080/afa/api/v1/config | head
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
Metro is active and returns application config data instead of failing.
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
Look for: active, config
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If Metro cannot answer, the app branch is the first stop point.
</p>

<p class="adf-inline-label">Known working example</p>

```text
active
{"configVersion":"ok"}
```
</div>

  </div>
  <div class="adf-preview-manual-branch">
    <p><strong>If healthy:</strong> Use one bounded reproduction minute to name the actual stop point.</p>
    <p><strong>If not healthy:</strong> Stop here and treat the local app path as the current failure point.</p>
  </div>
  </div>
</details>
<details id="manual-ui-and-proxy-step-5" class="adf-preview-manual-step">
  <summary class="adf-preview-manual-summary">
    <span class="adf-preview-manual-summary-copy">
      <span class="adf-preview-manual-kicker">Step 5</span>
      <span class="adf-preview-manual-summary-title">Useful work stops here</span>
      <span class="adf-preview-manual-action">If useful work still stops here, use Apache, Keycloak, and Metro clues to find the first clear stop point.</span>
    </span>
    <span class="adf-preview-manual-summary-meta">
      <span class="adf-preview-manual-summary-count">1 command</span>
    </span>
  </summary>
  <div class="adf-preview-manual-step-body">
  <p>Only move into heavier log correlation after the host, edge, auth, and app branches have all been checked.</p>
  <div class="adf-preview-manual-callout">
    <p class="adf-panel-label">Field note</p>
<div class="adf-check">
<p class="adf-check-label">Correlate one reproduced minute across the edge and app services</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u httpd -u keycloak -u ms-metro --since '5 minutes ago' --no-pager | tail -n 120
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Verification:</span> 
The same bounded minute shows the first branch that stops doing useful work.
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

<p class="adf-check-reference">
Look for: httpd, keycloak, ms-metro
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If not healthy:</span> 
If only one branch degrades in the same minute, that branch owns the stop point.
</p>

<p class="adf-inline-label">Known working example</p>

```text
Mar 27 15:00:11 httpd[...]: GET /algosec/suite/login 302
Mar 27 15:00:12 keycloak[...]: login flow ok
Mar 27 15:00:13 ms-metro[...]: config fetch ok
```
</div>

  </div>
  <div class="adf-preview-manual-branch">
    <p><strong>If healthy:</strong> Record the bounded proof and move to the next symptom slice.</p>
    <p><strong>If not healthy:</strong> Name the first failing branch and stop the walk there.</p>
  </div>
  </div>
</details>
  </section>
  <section class="adf-preview-manual-appendix">
    <div class="adf-preview-manual-note">
      <p class="adf-panel-label">Appendix</p>
      <p>Use the dependency path as orientation only. The chapter order matters more than the map in this template.</p>
    </div>
    <div class="adf-preview-manual-note">
      <p class="adf-panel-label">Matching symptom prompts</p>
      <ul>
        <li>Suite login redirects but the operator still cannot do useful work.</li>
        <li>UI shell appears, but the first app action stalls immediately.</li>
        <li>Support needs one bounded route to prove where useful work stops.</li>
      </ul>
    </div>
  </section>
</div>

