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

### Remote Codex Auth Recovery

If a remote assistant-UAT run fails at the prompt layer with Codex auth errors
such as `refresh_token_reused` or `token_expired`, treat that as a remote-host
credential issue first, not as PackFactory control-plane breakage.

Operational rule:

- if the remote execution manifest still shows a healthy runner and successful
  export, inspect the imported assistant-UAT stderr before changing PackFactory
  code
- repair Codex auth on the remote target account outside the PackFactory run
  itself
- verify the repair with one direct remote `codex exec` smoke
- then rerun the same generated PackFactory request unchanged so the prompt
  failure and the recovery remain comparable

Evidence:

- `v21` prompt-level auth failure:
  `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260331t164306z/external-runtime-evidence/artifacts/assistant-uat/preference_calibration_caution-stderr.txt`
- `v22` clean recovery after remote auth repair:
  `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260331t165720z/import-report.json`
- `v22` clean prompt-level completion:
  `build-packs/codex-personal-assistant-daily-driver-build-pack-v1/eval/history/import-external-runtime-evidence-20260331t165720z/external-runtime-evidence/artifacts/assistant-uat/uat-report.json`

Plain-language consequence:

- do not widen assistant-UAT writable surfaces or rewrite the request builder
  just because a remote prompt hit stale Codex auth
- fix auth first, rerun the same PackFactory request, and only treat the issue
  as a builder/control-plane defect if the failure survives a healthy remote
  Codex smoke

## Transient Local Scratch

PackFactory's remote-autonomy staging trees and roundtrip `incoming/` trees are
transient scratch. They should be treated as disposable workspace, not as the
canonical preserved evidence line.

- the scratch-root contract is defined in
  `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TRANSIENT-LOCAL-SCRATCH-ROOT-AND-STAGING-LIFECYCLE-TECH-SPEC.md`
- the local scratch root is selected and persisted by PackFactory host-local
  runtime state, not by a remote request payload or wrapper request
- agent sessions should inherit that persisted selection automatically; manual
  env configuration is an override path, not the normal control plane
- durable artifacts that operators still need after a run, such as generated
  import requests or roundtrip manifests, must be written or copied outside
  scratch before cleanup runs
- if a host must stay on the repo-local fallback scratch root, disk-pressure
  guardrails should still prevent a repeat of the 2026-03-29 fill-up pattern

## Default Factory Autonomy Workflows

Use the workflows below as the standard PackFactory path for remote-memory and
remote-session work rather than assembling your own control flow from shell
prompts plus terminal logs.

## Fresh-Pack Certification Rule

When a newly materialized build-pack is expected to become the operator's real
working or daily-driver instance and may later need promotion-ready remote
evidence, do not skip the fresh-pack certification step.

Current rule:

- run the official fresh-pack autonomy workflow before that pack diverges into
  long-lived daily-driver use
- treat `run_multi_hop_autonomy_rehearsal.py` and
  `run_autonomy_to_promotion_workflow.py` as certification surfaces for a
  fresh proving-ground build-pack
- do not describe those workflows as if they retroactively certify an
  already-evolving build-pack in place

Plain-language consequence:

- if the operator builds directly in the first long-lived pack and only later
  asks for official promotion-compatible remote evidence on that same pack,
  the missed step is the fresh-pack rehearsal, not template creation
- in that situation, use a fresh proving-ground build-pack for official remote
  proof or say plainly that PackFactory still lacks an official
  "rehearse this existing build-pack in place" workflow

- `python3 tools/run_multi_hop_autonomy_rehearsal.py ...`
  Use this to prove the full default autonomy loop on a fresh build-pack:
  materialize, checkpoint mid-backlog memory, run remote active-task
  continuity, reconcile, and verify ready-boundary continuity. This is a
  fresh-pack certification workflow, not a retrofit certifier for an
  already-evolving build-pack.

- `python3 tools/run_autonomy_to_promotion_workflow.py ...`
  Use this when you want the full factory-default path in one motion:
  materialize, run the multi-hop rehearsal, prepare a release, and promote the
  result to the target environment. This is also a fresh-pack certification
  workflow.

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
  a score report under `.pack-state/autonomy-quality-scores/`. When a matching
  score report exists for the rehearsal selected during promotion,
  `tools/promote_build_pack.py` now records that quality evidence as an
  advisory signal in the promotion report. Packs can also opt into a bounded
  hard gate through `contracts/project-objective.json.autonomy_quality_requirement`
  when promotion should require explicit minimum quality thresholds.

- `python3 tools/record_autonomy_run.py finalize-run ...`
  Use this when you want the bounded operator-intervention learning handoff.
  When an autonomy run records an applied operator hint in
  `.pack-state/autonomy-runs/<run-id>/branch-selection.json`, finalization now
  carries that guidance forward into
  `autonomy-feedback-memory.operator_intervention_summary` so the next agent
  can see which hint ids changed branch selection, which task was chosen, and
  which branch-selection artifact explains the decision.
  The same finalize step now also carries bounded blocker-resolution learning:
  when the previously active feedback memory ended in a structured block and
  the current run clears that boundary, the new feedback memory records
  `resolved_block_summary` so the next agent can see the prior stop reason,
  the old recovery instruction, and the new run evidence that resolved it.
  The same feedback memory now also carries `memory_validity` with bounded
  confidence, restart scope, and expiry semantics so the next agent can tell
  whether a note is a fresh active-pack restart hint, a ready-boundary handoff,
  or a low-confidence short-lived note that should be treated cautiously.
  When a previously active feedback memory exists, finalization now also writes
  `delta_summary` so the next agent can see which canonical fields changed,
  which tasks were newly completed, and how the current run differs from the
  last active restart note without diffing the artifacts by hand.
  Finalization now also writes `negative_memory_summary` when the run shows a
  concrete anti-pattern the next agent should avoid repeating, such as trusting
  a run without canonical integrity, reusing stale memory, or replaying a
  fail-closed blocked path without first resolving it.
  Finalization now also writes `autonomy_budget` with explicit bounded run
  limits, observed usage, and `within_budget` versus `budget_exceeded`
  status, and autonomy quality scoring now uses those budgets to derive a
  `budget_efficiency_quality` dimension.
  Pack-local feedback memory now also declares `memory_tier.tier=restart_memory`
  so the next agent can distinguish live restart context from other memory
  kinds without inference.

- `python3 tools/refresh_local_feedback_memory_pointer.py ...`
  Use this when you want the pack-local `latest-memory.json` pointer to pick
  the best compatible live feedback memory. The selector now ignores
  otherwise-compatible memory notes whose `memory_validity.expires_at` is
  already in the past, so expired restart context does not silently become the
  active default. The pointer now also exposes `selected_memory_tier` so the
  active tier is visible from the pointer alone.

- `python3 tools/refresh_factory_autonomy_memory.py ...`
  Use this when you want a fresh root-level PackFactory handoff after major
  autonomy changes. Root memory now declares
  `memory_tier.tier=promoted_factory_memory`, and the root
  `.pack-state/agent-memory/latest-memory.json` pointer now exposes
  `selected_memory_tier=promoted_factory_memory`.

- `python3 tools/distill_autonomy_memory_across_build_packs.py ...`
  Use this when you want to promote repeated autonomy lessons from multiple
  build-packs into one factory-level memory artifact. It reads the latest
  cross-template transfer matrix, the available autonomy-quality scores, and
  the existing operator-guided branch-choice proofs, then writes a bounded
  distillation report under `.pack-state/autonomy-memory-distillations/`.

- `python3 tools/refresh_template_lineage_memory.py ...`
  Use this when you want a compact template-family memory surface for one
  active template. It reads derived build-pack lineage plus the latest
  factory-level distillation report and writes template-local advisory memory
  under `templates/<template-id>/.pack-state/template-lineage-memory/`.

- `python3 tools/run_adversarial_restart_drills.py ...`
  Use this when you want one bounded proof that the restart loop recovers from
  adversarial conditions. It creates a fresh proving-ground build-pack, proves
  local lost-pointer recovery, forces expired-memory fail-closed behavior,
  restores the local pointer, and then reuses the degraded-connectivity path
  to prove conflicting imported-memory preservation.

- `python3 tools/run_post_autonomy_change_maintenance.py ...`
  Use this after major autonomy tooling, promotion, or startup-surface
  changes. It runs the bounded baseline-preservation path in one command:
  refresh factory-level lesson distillation, refresh active-template lineage
  memory, refresh root factory memory, and then fail closed until the
  filtered validation slice for instruction surfaces, root memory,
  template-lineage memory, and autonomy-memory distillation passes.

- `python3 tools/run_factory_root_startup_benchmark.py ...`
  Use this when you want a deterministic benchmark of the root `load AGENTS.md`
  startup experience. It records the source trace, generates a benchmark
  startup brief from canonical startup surfaces, checks environment consistency,
  and writes a bounded benchmark report under `.pack-state/startup-benchmarks/`.

- `python3 tools/generate_factory_dashboard.py ...`
  Use this when you want a local-first operator dashboard that turns the
  current factory state, deployment assignments, recent motion, and advisory
  root memory into a single static briefing page under
  `.pack-state/factory-dashboard/latest/`.

- `python3 tools/run_cross_template_transfer_matrix.py ...`
  Use this when you want one report that summarizes autonomy transfer proofs
  across multiple template lines. It reads existing multi-hop rehearsal
  reports, scores each transfer row, and writes a matrix report under
  `.pack-state/cross-template-transfer-matrices/`.

- `python3 tools/distill_autonomy_memory_lessons.py ...`
  Use this when you want one factory-level lesson report synthesized from
  repeated proof artifacts instead of keeping the same autonomy pattern
  scattered across individual build-packs. The first bounded use case is to
  distill repeated lessons from cross-template transfer reports, autonomy
  quality score reports, fail-closed import reports, and branch-choice
  exercise reports into one report under
  `.pack-state/autonomy-memory-distillations/`.

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
  Use this when a proving-ground autonomy improvement has been promoted into
  factory defaults and you want that inheritance state recorded explicitly.

- `python3 tools/record_runtime_template_parity.py ...`
  Use this when a reusable behavior was first proved in a runtime build-pack
  and then backported into its source template, and you want the runtime to
  template parity state recorded explicitly at the factory root.

Active source templates now participate in bounded startup-compliance drift
checking too. `tools/validate_factory.py` verifies a small marker set in each
active template's `AGENTS.md`, `project-context.md`, and `pack.json` so the
template inheritance layer stays aligned with the root startup baseline
without forcing full text equality.

Template creation now carries a bounded reusability gate as well.
`tools/create_template_pack.py` requires the request planning summary to
declare a reusable `capability_family`, at least two expected build-pack
variants, and the `first_materialization_purpose` for the first proving-ground
derivative. That keeps template creation aligned with the factory model of
reusable source templates plus concrete build-pack proofs.

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

Current direction: the bounded memory and feedback frontier wave is closed.
Keep PackFactory startup surfaces, template lineage memory, root memory, and
distilled factory lessons synchronized through the fail-closed maintenance
workflow so agents continue to use the local evidence and memory flows
instead of drifting back toward ad hoc remote control.
