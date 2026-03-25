# Project Pack Factory Autonomy Operations Note

Purpose: give a fresh agent one clear factory-level place to discover the
current autonomy tooling, the root memory surface, the required remote-session
control plane, and the normal rehearsal flows that now exist in PackFactory.

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

## Remote Session Compliance

For remote Codex session management, the PackFactory-local workflows in this
note and the root operator-tool lists are the required control plane.

- do not improvise ad hoc `ssh` prompts or handcrafted remote-session runners
  when a PackFactory workflow already exists for the same job
- treat raw stdout/stderr from remote sessions as supplementary debugging only
- export runtime evidence from the pack when needed, but return to the
  factory root for import through `tools/import_external_runtime_evidence.py`
  or a higher-level PackFactory workflow that wraps that import
- when a build-pack instruction surface and the root workflow guidance appear
  to diverge, prefer the root PackFactory workflow rather than inventing a
  pack-local remote-session path

## Default Factory Autonomy Workflows

Use the workflows below as the standard PackFactory path for remote-memory and
remote-session work rather than assembling your own control flow from shell
prompts plus terminal logs.

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

- `python3 tools/run_operator_hint_conflict_exercise.py ...`
  Use this when you want to prove the full operator-hint precedence ladder on
  a conflict-heavy branch choice. It materializes a fresh proving-ground pack,
  creates three tied post-validation branches, applies a preferred-task hint
  plus a later avoid-task hint, and verifies that the chooser applies the
  current ladder of priority -> avoid -> prefer -> semantic alignment ->
  fail-closed review before continuing through the normal remote continuity
  loop.

- `python3 tools/run_ordered_hint_lifecycle_exercise.py ...`
  Use this when you want to prove ordered preferred-task guidance plus bounded
  hint lifetime. It materializes a fresh proving-ground pack, applies a
  one-shot ordered preference hint with `remaining_applications=1`, verifies
  the first branch follows that ordered hint, and then verifies that a later
  tied branch falls back to semantic alignment after the hint deactivates.

- `python3 tools/audit_branch_selection_hints.py ...`
  Use this when you want one operator-facing view of current hint state. It
  audits canonical `branch_selection_hints`, reports which hints are active,
  exhausted, or cleanup candidates, summarizes recent consumed and deactivated
  hint evidence from recent `branch-selection.json` artifacts, and can
  optionally prune exhausted inactive hints from canonical work-state.

- `python3 tools/run_operator_hint_audit_cleanup_exercise.py ...`
  Use this when you want to prove the full hint audit and cleanup loop on a
  fresh proving-ground pack. It creates a one-shot ordered hint, consumes it,
  audits it as a cleanup candidate, prunes it, and verifies that canonical
  work-state is left clean afterward.

- `python3 tools/score_autonomy_quality.py ...`
  Use this when you want a bounded autonomy-quality score from an existing
  rehearsal artifact. It reads a multi-hop or startup-compliance rehearsal
  report, derives handoff, replay-avoidance, recovery, outcome, branch-choice,
  block-reporting, and startup-compliance quality where applicable, and writes
  a score report under `.pack-state/autonomy-quality-scores/`.

- `python3 tools/run_factory_root_startup_benchmark.py ...`
  Use this when you want a deterministic benchmark of the root `load AGENTS.md`
  startup experience. It records the source trace, generates a benchmark
  startup brief from canonical startup surfaces, checks environment consistency,
  and writes a bounded benchmark report under `.pack-state/startup-benchmarks/`.

- `python3 tools/run_cross_template_transfer_matrix.py ...`
  Use this when you want one report that summarizes autonomy transfer proofs
  across multiple template lines. It reads existing multi-hop rehearsal
  reports, scores each transfer row, and writes a matrix report under
  `.pack-state/cross-template-transfer-matrices/`.

- `python3 tools/run_operator_hint_status_surfacing_exercise.py ...`
  Use this when you want to prove that normal readiness state now carries
  hint-status context. It runs the full audit-and-cleanup path on a fresh
  proving-ground pack, refreshes readiness, and verifies that
  `status/readiness.json.operator_hint_status` shows current hint counts,
  recent consumed/deactivated hint ids, and the latest audit report path.

- `python3 tools/run_startup_compliance_rehearsal.py ...`
  Use this when you want to prove the startup-compliance baseline end to end.
  It verifies the root and template compliance markers, materializes a fresh
  proving-ground build-pack, verifies inherited build-pack startup guidance,
  and then runs the managed PackFactory multi-hop remote-session path.

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
  including preferred-task and avoid-task guidance plus optional
  `remaining_applications` for bounded lifetime
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

Current direction: pack-local operator-hint briefing is now proven. Keep the
bounded semantic chooser and fail-closed ambiguity handling in place, and
keep PackFactory startup and remote-session compliance synchronized as the
tooling evolves so agents continue to use the local evidence and memory flows
instead of drifting back toward ad hoc remote control.
