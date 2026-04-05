---
title: AlgoSec Diagnostic Framework
description: Runtime-backed framework for diagnostic playbooks, evidence, and support workflows.
sidebar:
  label: Overview
  order: 1
---

# AlgoSec Diagnostic Framework

Open the live playbook first. Use the canonical template only as a reusable shell.

<div class="adf-home-shell">
  <div class="adf-home-topbar">
    <div class="adf-panel">
      <p class="adf-panel-label">Live baseline</p>
      <p>algosec-lab on algosec running Rocky Linux 8.10 (Green Obsidian).</p>
    </div>
    <div class="adf-panel">
      <p class="adf-panel-label">Observed scope</p>
      <p>261 services, 51 listeners, 0 config checkpoints, 0 log checkpoints.</p>
    </div>
  </div>

## Start here

<div class="adf-home-grid">
  <div class="adf-panel">
    <p class="adf-panel-label">Operator route</p>
    <ul>
      <li>Confirm the customer appliance hostname, OS family, and any visible build markers against the lab baseline.</li>
      <li>Check whether the top AlgoSec services are active and enabled in the customer environment.</li>
      <li>Compare Apache-routed endpoints and local listener ports before moving into deeper service-specific diagnosis.</li>
      <li>Use the recorded config and log checkpoints for the top services before inferring broader platform issues.</li>
    </ul>
  </div>
  <div class="adf-panel">
    <p class="adf-panel-label">Build rule</p>
    <ul>
      <li>Keep the real troubleshooting steps in the playbook routes.</li>
      <li>Keep placeholders in the canonical template only.</li>
      <li>Use one page grammar across future playbooks.</li>
    </ul>
  </div>
</div>

## Published pages

<div class="adf-home-card-grid">
<a class="adf-home-card" href="/canonical-playbook-template/">
  <p class="adf-panel-label">Template</p>
  <strong>Canonical ADF playbook shell</strong>
  <span>Reference shell only. Keep placeholders here.</span>
  <span class="adf-home-card-list">Open the template for page structure.</span>
</a>
<a class="adf-home-card" href="/playbooks/asms-ui-is-down/">
  <p class="adf-panel-label">Live playbook</p>
  <strong>ASMS UI is down</strong>
  <span>Lab-validated operator playbook.</span>
  <span class="adf-home-card-list">Open the live playbook for support use.</span>
</a>
<a class="adf-home-card" href="/playbooks/asms-keycloak-auth-is-down/">
  <p class="adf-panel-label">Live playbook</p>
  <strong>ASMS Keycloak auth is down</strong>
  <span>Dedicated auth-service diagnostic route.</span>
  <span class="adf-home-card-list">Use this when the login page still loads but auth fails.</span>
</a>
<a class="adf-home-card" href="/guides/asms-keycloak-integration-guide/">
  <p class="adf-panel-label">Guide</p>
  <strong>ASMS / Keycloak integration guide</strong>
  <span>Technical map of where Keycloak sits in the ASMS path.</span>
  <span class="adf-home-card-list">Open this for architecture and evidence.</span>
</a>
<a class="adf-home-card" href="/guides/asms-keycloak-junior-operator-guide/">
  <p class="adf-panel-label">Guide</p>
  <strong>ASMS / Keycloak junior operator guide</strong>
  <span>Short triage sheet for frontline support use.</span>
  <span class="adf-home-card-list">Open this during a customer session.</span>
</a>
</div>

## Catalog status

<div class="adf-home-grid">
  <div class="adf-panel">
    <p class="adf-panel-label">Published catalog</p>
    <p>5 playbooks are and 2 guides are currently published from the new shell.</p>
  </div>
  <div class="adf-panel">
    <p class="adf-panel-label">Next build rule</p>
    <p>Build new playbooks from the canonical template. Keep the operator routes separate.</p>
  </div>
</div>

## Symptom lookup

<div class="adf-symptom-grid">
<div class="adf-symptom-card">
  <strong>ASMS UI is down</strong>
  <p>Check whether the host is under storage, inode, memory, or CPU pressure before blaming the ASMS UI path.</p>
  <span>Rebuild later under ASMS UI is down.</span>
</div>
<div class="adf-symptom-card">
  <strong>ASMS login page not loading</strong>
  <p>Check whether the host is under storage, inode, memory, or CPU pressure before blaming the ASMS UI path.</p>
  <span>Rebuild later under ASMS UI is down.</span>
</div>
<div class="adf-symptom-card">
  <strong>FireFlow action failing</strong>
  <p>Confirm aff-boot.service is active and /FireFlow/api or /aff/api still proxy to localhost:1989.</p>
  <span>Rebuild later under FireFlow Backend.</span>
</div>
<div class="adf-symptom-card">
  <strong>FireFlow API error</strong>
  <p>Confirm aff-boot.service is active and /FireFlow/api or /aff/api still proxy to localhost:1989.</p>
  <span>Rebuild later under FireFlow Backend.</span>
</div>
<div class="adf-symptom-card">
  <strong>Feature failing behind UI</strong>
  <p>Confirm algosec-ms.service completed successfully and the top ms-* services are active.</p>
  <span>Rebuild later under Microservice Platform.</span>
</div>
<div class="adf-symptom-card">
  <strong>Specific microservice path failing</strong>
  <p>Confirm algosec-ms.service completed successfully and the top ms-* services are active.</p>
  <span>Rebuild later under Microservice Platform.</span>
</div>
<div class="adf-symptom-card">
  <strong>Job stuck or not progressing</strong>
  <p>Confirm activemq.service is active and listener 61616 is present.</p>
  <span>Rebuild later under Messaging and Data.</span>
</div>
<div class="adf-symptom-card">
  <strong>Data-backed action failing</strong>
  <p>Confirm activemq.service is active and listener 61616 is present.</p>
  <span>Rebuild later under Messaging and Data.</span>
</div>
</div>
</div>

