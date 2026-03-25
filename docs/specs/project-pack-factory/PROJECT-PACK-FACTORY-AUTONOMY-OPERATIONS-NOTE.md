# Project Pack Factory Autonomy Operations Note

Purpose: give a fresh agent one clear factory-level place to discover the
current autonomy tooling, the root memory surface, and the normal rehearsal
flows that now exist in PackFactory.

## Read This When

- the task is factory-level autonomy work rather than pack-local feature work
- you are continuing recent PackFactory autonomy improvements
- you need to know which autonomy workflows are now standard
- you want the shortest path to the current root-level restart memory

## Root Restart Memory

PackFactory now has a factory-level restart memory surface in:

- `.pack-state/agent-memory/latest-memory.json`

When present, read the pointer first, then read the selected memory artifact it
references under:

- `.pack-state/agent-memory/factory-autonomy-memory-*.json`

This root memory is advisory restart context for the factory repo itself. It
does not replace canonical registry, deployment, readiness, or promotion
surfaces.

When giving a factory-root executive summary, keep that memory in a distinct
`Agent Memory` section after the canonical factory-state summary. Prefer the
memory artifact's structured fields such as `current_focus`,
`next_action_items`, `pending_items`, `overdue_items`, `blockers`,
`latest_autonomy_proof`, and `recommended_next_step`.

## Default Factory Autonomy Workflows

- `python3 tools/run_multi_hop_autonomy_rehearsal.py ...`
  Use this to prove the full default autonomy loop on a fresh build-pack:
  materialize, checkpoint mid-backlog memory, run remote active-task
  continuity, reconcile, and verify ready-boundary continuity.

- `python3 tools/run_autonomy_to_promotion_workflow.py ...`
  Use this when you want the full factory-default path in one motion:
  materialize, run the multi-hop rehearsal, prepare a release, and promote the
  result to the target environment.

- `python3 tools/run_local_mid_backlog_checkpoint.py ...`
  Use this when you want a local checkpoint after the current active task plus
  a refreshed `latest-memory.json` pointer.

- `python3 tools/run_remote_active_task_continuity_test.py ...`
  Use this when the pack is at a compatible mid-backlog boundary and you want
  to prove the next task resumes remotely from memory.

- `python3 tools/run_remote_memory_continuity_test.py ...`
  Use this after the pack reaches `ready_for_deploy` and the pack-local
  `latest-memory.json` pointer is active.

- `python3 tools/refresh_factory_autonomy_memory.py ...`
  Use this after meaningful factory-level autonomy work so the next agent gets
  an updated root memory handoff.

## Current Factory Default

Newly materialized autonomy-capable build-packs now inherit:

- pack-local feedback-memory writing
- pack-local `latest-memory.json` activation
- remote memory export/import support
- multi-hop autonomy rehearsal guidance
- promotion gating through compatible autonomy rehearsal evidence

The strongest current proof path is the JSON health checker proving-ground
line, especially:

- `json-health-checker-promotion-gate-build-pack-v1`

## Important Current Limits

- PackFactory autonomy is strongest in bounded workflows, not broad unscripted
  project work.
- A rehearsal can leave a pack logically ready while canonical readiness
  evidence still needs a local refresh before promotion succeeds cleanly.
- The factory root itself is only now gaining first-class restart memory; older
  work assumed memory mainly at the build-pack layer.

## Canonical Factory Anchors

For actual factory truth, prefer:

- `registry/templates.json`
- `registry/build-packs.json`
- `registry/promotion-log.json`
- `deployments/`

Treat root-level memory as a restart accelerator, not as the source of truth.

## Active Follow-Up List

The current autonomy follow-up list is:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md`
