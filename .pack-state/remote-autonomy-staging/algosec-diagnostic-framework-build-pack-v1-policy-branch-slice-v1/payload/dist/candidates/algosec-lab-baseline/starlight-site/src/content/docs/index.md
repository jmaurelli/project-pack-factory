---
title: AlgoSec Diagnostic Framework
description: Runtime-backed framework for diagnostic playbooks, evidence, and support workflows.
sidebar:
  label: Overview
  order: 1
---

# AlgoSec Diagnostic Framework

Field Manual is now the canonical ADF playbook template. The old published playbooks have been intentionally cleared so we can rebuild the catalog from scratch on one consistent shell.

<div class="adf-home-shell">
  <div class="adf-home-topbar">
    <div class="adf-panel">
      <p class="adf-panel-label">Live baseline</p>
      <p>algosec-lab on orch-lab-01 running Ubuntu 24.04.4 LTS.</p>
    </div>
    <div class="adf-panel">
      <p class="adf-panel-label">Observed scope</p>
      <p>223 services, 6 listeners, 69 config checkpoints, 10 log checkpoints.</p>
    </div>
  </div>

## First response

<div class="adf-home-grid">
  <div class="adf-panel">
    <p class="adf-panel-label">How to use this site</p>
    <ul>
      <li>Confirm the customer appliance hostname, OS family, and any visible build markers against the lab baseline.</li>
      <li>Check whether the top AlgoSec services are active and enabled in the customer environment.</li>
      <li>Compare Apache-routed endpoints and local listener ports before moving into deeper service-specific diagnosis.</li>
      <li>Use the recorded config and log checkpoints for the top services before inferring broader platform issues.</li>
    </ul>
  </div>
  <div class="adf-panel">
    <p class="adf-panel-label">Why this shape</p>
    <ul>
      <li>ADF now has one canonical playbook shell instead of competing page grammars.</li>
      <li>The old playbook set was cleared from publication on purpose so rebuild work starts from one template baseline.</li>
      <li>The JSON baseline and pack state remain canonical. This site is still a render layer over that evidence.</li>
    </ul>
  </div>
</div>

## Canonical template

<div class="adf-home-card-grid">
<a class="adf-home-card" href="/canonical-playbook-template/">
  <p class="adf-panel-label">Field Manual</p>
  <strong>Canonical ADF playbook shell</strong>
  <span>This is now the only approved playbook template. Existing playbooks were intentionally dropped from publication and will be rebuilt on top of this shell.</span>
  <span class="adf-home-card-list">Open the canonical template and use it as the rebuild reference.</span>
</a>
</div>

## Rebuild status

<div class="adf-home-grid">
  <div class="adf-panel">
    <p class="adf-panel-label">Published catalog</p>
    <p>Zero playbooks are currently published on purpose. This prevents the older mixed shells from pretending to be canonical while we rebuild.</p>
  </div>
  <div class="adf-panel">
    <p class="adf-panel-label">Next build rule</p>
    <p>Every new playbook should be authored against the Field Manual shell first. We can add content families later, but not another competing page grammar.</p>
  </div>
</div>

## Symptom lookup

<div class="adf-symptom-grid">
</div>
</div>

