# Project Pack Factory Autonomy Operations Note

Purpose: give a fresh agent one clear factory-level place to discover the
current autonomy tooling, the root memory surface, and the normal rehearsal
flows that now exist in PackFactory.

## Read This When

- the task is factory-level autonomy work rather than pack-local feature work
- you are continuing recent PackFactory autonomy improvements
- you need to know which autonomy workflows are now standard
- you want the shortest path to the current root-level restart memory
- you want one stable snapshot of the current autonomy baseline without
  rebuilding it from chat history

## Current State Snapshot

The current autonomy baseline is summarized in:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`

Use that note when you want one concise factory-level snapshot of:

- inherited memory and knowledge-loading defaults
- the proven stop and restart loop
- the current branch-choice ladder
- the strongest proof points
- the main current limits

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

- `python3 tools/run_longer_backlog_autonomy_exercise.py ...`
  Use this when you want to stress the current memory loop on a deeper linear
  starter backlog. It materializes a fresh proving-ground pack, adds bounded
  checkpoint tasks before the inherited benchmark task, loops remote
  active-task continuity until the pack reaches `ready_for_deploy`, and then
  runs the ready-boundary continuity pass.

- `python3 tools/run_branching_autonomy_exercise.py ...`
  Use this when you want to stress the current memory loop on a starter
  backlog with two valid post-validation choices. It materializes a fresh
  proving-ground pack, adds two branch tasks plus explicit `selection_priority`
  metadata, proves the chosen branch is recorded in `branch-selection.json`,
  and then continues the remote continuity hops through the remaining branch
  and final benchmark task.

- `python3 tools/run_degraded_connectivity_autonomy_exercise.py ...`
  Use this when you want to prove the factory can tolerate a temporary loss of
  connectivity during testing. It materializes a fresh proving-ground pack,
  checkpoints memory locally, runs a remote active-task hop with delayed
  import, continues local progress while disconnected, then reconnects,
  imports the preserved remote evidence, and verifies that incompatible
  returned memory is kept fail-closed instead of overriding newer canonical
  local state.

- `python3 tools/run_ambiguous_branch_autonomy_exercise.py ...`
  Use this when you want to prove the factory stays honest at an ambiguous
  branch boundary. It materializes a fresh proving-ground pack, creates two
  equally eligible post-validation tasks with no disambiguating
  `selection_priority`, and verifies that autonomy stops fail-closed with a
  clear escalation boundary and blocked-task record instead of choosing by
  backlog order.

- `python3 tools/run_semantic_branch_choice_exercise.py ...`
  Use this when you want to prove the factory can make a bounded semantic
  branch choice without explicit `selection_priority`. It materializes a fresh
  proving-ground pack, creates two equally eligible post-validation tasks,
  biases one candidate through objective/resume alignment plus task
  `selection_signals`, and verifies that autonomy records the semantic scores
  and chooses the stronger candidate before continuing through the normal
  remote continuity loop.

- `python3 tools/apply_branch_selection_hint.py ...`
  Use this when you want to record explicit operator guidance in
  `status/work-state.json.branch_selection_hints` before the chooser falls
  back to semantic alignment. It now supports both preferred-task and
  avoid-task guidance.

- `python3 tools/run_operator_hint_branch_choice_exercise.py ...`
  Use this when you want to prove the factory honors explicit operator
  branch-selection hints before semantic inference. It materializes a fresh
  proving-ground pack, applies a canonical operator hint, and verifies that
  autonomy follows that hint with recorded evidence before continuing through
  the normal remote continuity loop.

- `python3 tools/run_operator_avoid_branch_choice_exercise.py ...`
  Use this when you want to prove the factory can apply avoid-style operator
  guidance before semantic inference. It materializes a fresh proving-ground
  pack, applies a canonical avoid-task hint, verifies that the avoided branch
  is filtered out in `branch-selection.json`, and then continues through the
  normal remote continuity loop.

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

- `python3 tools/record_autonomy_improvement_promotion.py ...`
  Use this after a proving-ground build-pack demonstrates a new autonomy
  pattern and you want a factory-level record of where that improvement has
  actually been promoted: materializer defaults, source template tracking,
  factory-root discoverability, or factory-root memory.

## Current Factory Default

Newly materialized autonomy-capable build-packs now inherit:

- pack-local feedback-memory writing
- pack-local `latest-memory.json` activation
- remote memory export/import support
- optional canonical `branch_selection_hints` in `status/work-state.json`,
  including preferred-task and avoid-task guidance
- multi-hop autonomy rehearsal guidance
- promotion gating through compatible autonomy rehearsal evidence

The strongest current proof path is the JSON health checker proving-ground
line, especially:

- `json-health-checker-promotion-gate-build-pack-v1`

## Important Current Limits

- PackFactory autonomy is strongest in bounded workflows, not broad unscripted
  project work.
- The current proof now includes deeper starter backlogs, deterministic
  branching, delayed-import recovery under temporary degraded connectivity,
  fail-closed handling for ambiguous no-priority branches, explicit operator
  hint overrides, and bounded semantic tie-breaking through task
  `selection_signals`, but it still does not prove open-ended branch choice.
- Permanent factory-to-pack connectivity is not assumed after deployment.

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

Current direction: operator-hint conflict and precedence policy is the next
planned expansion. Keep the bounded semantic chooser and fail-closed ambiguity
handling in place, and prefer richer canonical operator guidance before
expanding toward more open-ended semantic branch choice.
