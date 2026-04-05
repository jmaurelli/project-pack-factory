# ADF Playbook Publication Note

Date: 2026-03-29

This note records the current ADF operator-playbook publication milestone so
PackFactory root memory can carry it forward without reconstructing it from
chat history.

## What changed

- The ADF canonical template is now a separate placeholder-only route.
- The real `ASMS UI is down` operator playbook now publishes as its own live
  review route.
- The ADF site overview now sends reviewers to the live playbook first and
  keeps the template secondary.

## Current live review routes

- Real operator playbook:
  `http://10.167.2.151:18082/playbooks/asms-ui-is-down/`
- Placeholder-only canonical template:
  `http://10.167.2.151:18082/canonical-playbook-template/`

## Canonical pack evidence

- Build-pack evidence note:
  `build-packs/algosec-diagnostic-framework-build-pack-v1/eval/history/asms-ui-canonical-template-and-live-playbook-split-20260329.md`
- Build-pack restart memory:
  `build-packs/algosec-diagnostic-framework-build-pack-v1/.pack-state/agent-memory/autonomy-feedback-canonical-template-real-playbook-split-20260329.json`
- Build-pack state:
  `build-packs/algosec-diagnostic-framework-build-pack-v1/status/work-state.json`
  `build-packs/algosec-diagnostic-framework-build-pack-v1/status/readiness.json`

## Why this matters

- Support engineers now have one clean operator page to use during live
  customer triage.
- Future ADF playbooks can reuse the same page shell without mixing placeholder
  content into live diagnostics.
- PackFactory root can now remember this as a real ADF milestone instead of a
  temporary review state.
