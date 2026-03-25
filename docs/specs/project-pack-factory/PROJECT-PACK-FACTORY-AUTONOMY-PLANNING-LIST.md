# Project Pack Factory Autonomy Planning List

Purpose: track the current PackFactory autonomy follow-up work at the factory
level so future build-packs inherit the improvements by default instead of
repeating the same optimization per pack.

Factory learning loop: use proving-ground build-packs to improve agentic
memory and feedback loops, then carry those improvements back into PackFactory
itself so the factory becomes a better default starting point for every future
build-pack.

Last updated: 2026-03-25

## Current State Snapshot

Use this stable state brief when you need one concise factory-level snapshot of
the autonomy baseline, proof points, restart surfaces, and current limits:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`

Why it matters: this keeps the current autonomy baseline in the repo itself so
future agents do not need to reconstruct it from chat history or scattered
workflow artifacts.

## Current Baseline

PackFactory autonomy can now:

- carry feedback memory across runs and reuse it by default
- resume from a mid-backlog checkpoint on a remote target
- stop cleanly at the deployment boundary without replaying starter tasks
- import returned memory, compatibility-gate it, and activate it when valid
- run a multi-hop autonomy rehearsal and use that rehearsal as promotion
  evidence
- run a single autonomy-to-promotion workflow that materializes, rehearses,
  prepares a release, and promotes in one motion
- stop fail-closed at an ambiguous branch boundary instead of silently
  choosing by backlog order when multiple next tasks share the same highest
  precedence
- honor explicit operator branch-selection hints before semantic inference
  when multiple next tasks remain tied after priority comparison
- use bounded semantic alignment to break a next-task tie when the objective,
  resume context, and task `selection_signals` make one candidate clearly
  stronger and the justification can be recorded
- use broader operator support through canonical hint guidance that can both
  prefer and avoid tasks before semantic tie-breaking runs
- apply a proven operator-hint conflict ladder of priority, avoid, prefer,
  semantic alignment, then fail-closed review
- support bounded hint lifetime through `remaining_applications`
- audit and prune exhausted operator hints cleanly
- surface operator-hint status directly in `status/readiness.json`
- inherit pack-local startup guidance that surfaces hint status early
- require PackFactory-local remote-session tooling and evidence flows at the
  factory root and in newly materialized build-pack startup guidance

Recent proof points:

- `json-health-checker-multi-hop-autonomy-build-pack-v1`
- `json-health-checker-promotion-gate-build-pack-v1`
- `json-health-checker-one-pass-promotion-proof-build-pack-v1`
- `json-health-checker-autonomy-to-promotion-build-pack-v1`
- `json-health-checker-operator-avoid-branch-build-pack-v2`
- `json-health-checker-operator-hint-conflict-build-pack-v1`
- `json-health-checker-ordered-hint-lifecycle-build-pack-v1`
- `json-health-checker-hint-audit-cleanup-build-pack-v3`
- `json-health-checker-hint-status-surfacing-build-pack-v2`
- `json-health-checker-hint-briefing-build-pack-v1`
- `json-health-checker-startup-compliance-build-pack-v1`
- `json-health-checker-startup-compliance-rehearsal-build-pack-v1`
- `config-drift-autonomy-transfer-build-pack-v1`

## Current Limits

- Autonomy is strongest in bounded PackFactory workflows, not broad unscripted
  project work.
- Imported memory is fail-closed by design, so progress can pause until
  reconcile happens.
- The strongest current proof now covers a four-task linear starter backlog,
  deterministic branching with explicit `selection_priority`, and temporary
  degraded-connectivity recovery during testing. Ambiguous no-priority branch
  choice is now fail-closed, explicit operator hint overrides are proven, and
  bounded semantic tie-breaking is proven, but open-ended branch choice is
  still not proven.
- Testing-time remote connectivity and delayed-import recovery are proven;
  permanent factory-to-pack connectivity is not assumed.

## Next Frontier

- [x] Startup-compliance rehearsal workflow.
  Scope: add and prove a reusable factory workflow that materializes a fresh
  build-pack, verifies inherited startup-compliance markers, and runs the
  managed PackFactory remote-session path end to end.
  Why it matters: this turns the startup-compliance baseline into a repeatable
  proof surface instead of relying on static doc inspection alone.

- [x] Capability-surface proving-ground expansion.
  Scope: choose a new proving-ground build-pack or template beyond the current
  JSON health checker line and use the autonomy baseline to improve a fresh
  capability surface.
  Why it matters: this checks whether the factory-default memory, feedback,
  and startup baseline transfers cleanly outside the current proving ground.

- [x] Root startup-experience re-brief.
  Scope: run a fresh factory-root `load AGENTS.md` style briefing against the
  updated memory and compliance baseline, then capture any remaining operator
  or agent friction that shows up during real startup.
  Why it matters: the startup experience is the main entry point for the next
  agent, so it should be re-tested after the recent autonomy and compliance
  changes.

## Frontier Wave 2

- [x] Autonomy quality scoring.
  Scope: define and implement a reusable factory scoring surface for autonomy
  quality, including handoff quality, replay avoided, branch-choice quality,
  block quality, and recovery quality across existing autonomy artifacts.
  Why it matters: the factory can now prove that autonomy loops complete, but
  it still needs a bounded way to measure how well they complete.
  Success signal: `tools/score_autonomy_quality.py` produces schema-valid
  score reports from rehearsal artifacts, and at least one startup-compliance
  proof plus one cross-template proof have recorded scores.

- [x] Factory-root startup benchmark.
  Scope: define and implement a repeatable benchmark for the `load AGENTS.md`
  style startup experience so PackFactory can score source selection, priority
  ordering, memory usage, and startup compliance behavior.
  Why it matters: startup is the main entry point for the next agent, and it
  should be benchmarked as a first-class autonomy surface instead of judged
  informally.
  Success signal: `tools/run_factory_root_startup_benchmark.py` produces a
  schema-valid benchmark report, source trace, and startup brief under
  `.pack-state/startup-benchmarks/`.

- [x] Cross-template transfer matrix.
  Scope: run a small matrix of autonomy transfer proofs across multiple active
  template lines beyond JSON health checking and capture where the baseline
  transfers cleanly versus where template-specific gaps remain.
  Why it matters: one successful transfer is encouraging, but a small matrix is
  the stronger proof that the PackFactory default autonomy baseline is truly
  general.
  Success signal: `tools/run_cross_template_transfer_matrix.py` records at
  least a three-row matrix with successful proofs beyond JSON health checking.

- [ ] Promotion-time autonomy quality gating.
  Scope: decide whether promotion should stay compatible-evidence-based only
  or begin consuming bounded autonomy-quality scores as an additional gate or
  advisory signal.
  Why it matters: the factory can now score autonomy quality, so the next
  question is how much of that score should affect real promotion decisions.

## Quick Wins

- [x] Add a canonical readiness refresh step at the end of
  `tools/run_multi_hop_autonomy_rehearsal.py`.
  Why it matters: the first real promotion attempt after rehearsal failed until
  the bounded readiness surfaces were rerun locally.
  Success signal: a fresh rehearsal result is immediately promotion-ready
  without a manual validation/benchmark retry.

- [x] Add a single autonomy-to-promotion factory workflow.
  Scope: materialize pack, run multi-hop autonomy rehearsal, refresh canonical
  readiness evidence, package release, and optionally promote to testing.
  Why it matters: this turns the new autonomy loop into one repeatable factory
  motion instead of several operator steps.

- [x] Improve autonomy block reporting.
  Scope: produce one operator-facing summary when autonomy stops fail-closed,
  including the exact reason, the blocking artifact, and the next bounded
  recovery action.
  Why it matters: it reduces ambiguity and shortens recovery time.

- [x] Add factory-root autonomy tooling discoverability.
  Scope: update the factory root instruction surfaces so a fresh agent can
  discover the new autonomy tools and workflows without relying on pack-local
  materialization guidance alone.
  Suggested surfaces: `AGENTS.md`, `README.md`, or a short factory-level
  autonomy operations note.
  Why it matters: the tooling is currently documented well for new build-packs,
  but not yet clearly advertised at the factory root.

- [x] Add factory-level agent memory for the PackFactory repo itself.
  Scope: create a root-level `.pack-state/agent-memory/` memory path plus a
  small factory handoff artifact that records the current autonomy toolset,
  latest rehearsal/promotion outcomes, known gaps, and recommended next steps.
  Why it matters: the build-packs now use distilled restart memory by default,
  but the factory root does not yet consume the same pattern.

- [x] Add agent memory to the root executive summary.
  Scope: upgrade the factory startup/executive summary so it includes a short
  `Agent Memory` section after the canonical factory state section.
  Required content:
  - current focus
  - next action items
  - pending items
  - overdue items
  - blockers
  - known limits
  - latest autonomy proof
  - recommended next step
  Guardrails:
  - canonical registry, deployment, readiness, and promotion state remain the
    truth layer
  - agent memory stays explicitly labeled as advisory restart context
  - if memory and canonical state disagree, the summary must say so plainly
  Why it matters: the summary should tell the next agent not just what is true
  now, but also what deserves attention next.

- [x] Add a template/factory improvement promotion loop.
  Scope: after a proving-ground build-pack validates a new autonomy pattern,
  record whether that pattern has been promoted into materializer defaults,
  source-template tracking, factory-root discoverability, or factory-root
  memory.
  Why it matters: it makes learning transfer explicit, so we know what is
  already automatic for future build-packs and what still needs a deliberate
  factory change.

## Executive Summary Memory Plan

- [x] Extend the root factory memory artifact.
  Scope: add explicit fields for `next_action_items`, `pending_items`,
  `overdue_items`, and `blockers` to the root memory schema and refresh tool.
  Why it matters: the executive summary should read from structured memory, not
  infer these items from free-form notes.

- [x] Define overdue items from a real planning surface.
  Scope: derive overdue or lagging work from the autonomy planning list or
  another explicit factory-level planning surface, not from free-form memory
  alone.
  Why it matters: overdue items should be evidence-backed rather than guessed.

- [x] Add an `Agent Memory` section to startup/executive summary behavior.
  Scope: update the root startup instructions so factory-level orientation work
  includes a short memory section after the canonical `what matters most now`
  and portfolio state summary.
  Why it matters: this makes root memory visible in the normal operator-facing
  briefing path.

- [x] Add contradiction handling between canonical state and memory.
  Scope: when root memory and canonical state diverge, have the summary report
  the mismatch and prefer canonical state.
  Why it matters: this keeps the summary fail-closed while still benefiting
  from memory.

## Autonomy Exercises

- [x] Promotion-readiness exercise.
  Scope: rerun the proving-ground path after the readiness-refresh improvement
  and confirm promotion succeeds in one pass.
  Why it matters: this closes the exact gap found in the live promotion-gate
  test.

- [x] Drift exercise.
  Scope: intentionally change canonical `status/work-state.json` after a remote
  run, then import returned memory and confirm it is preserved but not
  activated.
  Why it matters: this verifies fail-closed memory intake under real mismatch.

- [x] Longer-backlog exercise.
  Scope: prove continuity across a starter backlog with 4-6 tasks instead of 2.
  Why it matters: this tests whether task selection stays stable as autonomy
  depth increases.

- [x] Branching exercise.
  Scope: create a proving-ground pack where two next tasks are both valid and
  inspect how autonomy chooses and explains the choice.
  Why it matters: this is the first meaningful step beyond single-path starter
  backlogs.

- [x] Degraded-connectivity exercise.
  Scope: continue local build-pack progress without factory access, then
  reconnect and test import plus compatibility gating.
  Why it matters: this reflects the expected real-world deployment case more
  closely than always-on connectivity.

- [x] Ambiguous-branch exercise.
  Scope: create a proving-ground pack where two next tasks are equally
  eligible with no disambiguating `selection_priority`, and confirm autonomy
  stops fail-closed with a clear escalation boundary instead of choosing by
  backlog order.
  Why it matters: this keeps the memory loop honest when the factory lacks
  enough structured information to make a justified next-task decision.

- [x] Bounded semantic branch-choice exercise.
  Scope: create a proving-ground pack where two next tasks are equally
  eligible with no disambiguating `selection_priority`, but one candidate has
  clearly stronger alignment to the objective, resume context, and task
  `selection_signals`, then confirm autonomy chooses it with recorded
  justification.
  Why it matters: this proves PackFactory can make a more intelligent next
  choice without dropping explainability or fail-closed behavior.

- [x] Operator-hint branch-choice exercise.
  Scope: create a proving-ground pack where bounded semantic alignment would
  normally choose one branch, then apply an explicit operator branch-selection
  hint and confirm autonomy honors that hint with recorded evidence.
  Why it matters: this proves the factory can accept clear human intent
  without abandoning explainability or continuity.

- [x] Open-ended branch-choice follow-up.
  Scope: decide whether PackFactory should require richer structured priority
  metadata, expand the operator-hint surface, or broaden the bounded semantic
  chooser beyond explicit task `selection_signals`, objective alignment, and
  operator hints.
  Decision: prefer broader operator support for now.
  Why it matters: the safe bounded branch-choice ladder is now proven, so the
  next autonomy gain is extending operator steering without sacrificing
  explainability or fail-closed behavior.

- [x] Broader operator-support expansion.
  Scope: extend the canonical operator-hint surface beyond a single preferred
  task so operators can express stronger bounded steering such as ordered
  preferences, avoid-task guidance, or short-lived branch preferences while
  keeping the result machine-readable.
  Why it matters: this is the chosen next autonomy gain, and it should improve
  agent effectiveness without jumping prematurely to open-ended semantic
  judgment.

- [x] Operator-hint conflict and precedence policy.
  Scope: define how PackFactory should behave when explicit priority metadata,
  multiple operator hints, avoid-task hints, and bounded semantic signals point
  in different directions.
  Why it matters: richer operator support only helps if the chooser stays
  deterministic, explainable, and easy to recover when guidance conflicts.

### Operator-Hint Conflict Policy Plan

Use this precedence ladder for the current implementation pass:

1. explicit `selection_priority`
2. active operator `avoid_task_ids` within the tied top-priority set
3. active operator `preferred_task_ids` within the remaining tied set
4. bounded semantic alignment
5. fail-closed operator review

Safety rules for this pass:

- `avoid_task_ids` must never eliminate all remaining top candidates; if they
  would, ignore that narrowing and record that the avoid guidance could not be
  applied safely
- operator hints are processed in stable canonical list order from
  `status/work-state.json.branch_selection_hints`
- inactive hints are ignored entirely
- applied and ignored hint effects should be visible in `branch-selection.json`

Proof plan for this pass:

- create a proving-ground pack with three tied post-validation branches
- add one hint that prefers branch alpha
- add one later hint that avoids branch alpha
- make branch beta the stronger semantic fit than branch gamma
- confirm the chooser filters alpha, cannot apply the alpha preference after
  that filter, then selects beta through bounded semantic alignment

- [x] Richer operator-support proving-ground exercise.
  Scope: create a fresh proving-ground pack that uses more than one operator
  hint shape or a conflict case, then confirm autonomy follows the policy and
  records a clean branch-decision artifact.
  Why it matters: this turns the chosen direction into promotion-grade evidence
  instead of leaving it as a design preference.

- [x] Ordered-preference and hint-lifecycle follow-up.
  Scope: extend the operator-hint surface with stronger ordered preferences or
  bounded lifetimes so operators can steer a short stretch of autonomy work
  without leaving old guidance behind indefinitely.
  Why it matters: broader operator support is now proven for prefer, avoid,
  and conflict resolution, so the next gain is making that guidance more
  expressive while keeping the chooser explainable.

- [x] Operator-hint audit and cleanup follow-up.
  Scope: surface active, consumed, and exhausted operator hints more clearly in
  operator-facing status and branch-decision artifacts so stale guidance is
  easy to spot and clear.
  Why it matters: hint lifecycles are now proven, so the next win is making
  those lifecycle changes easier to see and trust during long-running autonomy.

- [x] Operator-hint status surfacing follow-up.
  Scope: carry hint-audit status forward into operator-facing summaries or
  readiness-style status so active, exhausted, and recently consumed hints are
  visible without rerunning a forensic read of work-state plus run artifacts.
  Why it matters: audit and cleanup are now proven, so the next gain is making
  hint state easier to notice during normal PackFactory operation.

- [x] Pack-local operator-hint briefing follow-up.
  Scope: teach pack-level startup and continuation briefings to surface
  readiness `operator_hint_status` when it exists so the next agent sees hint
  state during normal pack entry, not only by opening JSON directly.
  Why it matters: hint status is now present in readiness, so the next win is
  making that status show up naturally in agent briefings and operator-facing
  pack summaries.

- [x] PackFactory instruction and startup compliance review.
  Scope: review the factory instruction set, startup surfaces, and initial
  `load AGENTS.md` behavior so agents reliably recognize that PackFactory local
  tooling must be used for remote Codex session management instead of ad hoc
  SSH prompts or plain stdout/stderr logging patterns.
  Why it matters: if that rule is not obvious at startup, an agent can drift
  into unmanaged remote-session behavior and bypass the PackFactory evidence,
  memory, and audit loops we are explicitly building.

- [x] Instruction-surface drift follow-up.
  Scope: keep the root tool inventories, state brief, operations note, and
  inherited build-pack startup guidance synchronized as autonomy tooling
  changes so the next agent does not see stale commands or an older autonomy
  baseline.
  Why it matters: the startup compliance review found real drift between the
  operations note, tool lists, and autonomy state summaries, which can hide
  supported workflows and weaken the PackFactory-default path.

- [x] Source-template tracking for startup compliance guidance.
  Scope: mirror the PackFactory remote-session compliance baseline into the
  JSON health checker source template so template-local startup context points
  at the same managed remote-session and evidence-flow expectations as the
  root and generated build-pack guidance.
  Why it matters: the startup-compliance improvement promotion is still marked
  pending at the source-template surface.

## Suggested Order

1. Readiness refresh quick win
2. Promotion-readiness exercise
3. Factory-root autonomy tooling discoverability
4. Factory-level agent memory for the PackFactory repo itself
5. Add agent memory to the root executive summary
6. Executive summary memory plan implementation
7. Autonomy-to-promotion workflow
8. Block reporting quick win
9. Drift exercise
10. Longer-backlog exercise
11. Branching exercise
12. Degraded-connectivity exercise
13. Ambiguous-branch exercise
14. Bounded semantic branch-choice exercise
15. Operator-hint branch-choice exercise
16. Open-ended branch-choice follow-up
17. Broader operator-support expansion
18. Operator-hint conflict and precedence policy
19. Richer operator-support proving-ground exercise
20. Ordered-preference and hint-lifecycle follow-up
21. Operator-hint audit and cleanup follow-up
22. Operator-hint status surfacing follow-up
23. Pack-local operator-hint briefing follow-up
24. PackFactory instruction and startup compliance review
25. Instruction-surface drift follow-up
26. Source-template tracking for startup compliance guidance
27. Startup-compliance rehearsal workflow
28. Capability-surface proving-ground expansion
29. Root startup-experience re-brief
30. Autonomy quality scoring
31. Factory-root startup benchmark
32. Cross-template transfer matrix

## Working Notes

- Keep these changes factory-level unless there is a strong reason to scope
  them to one build-pack.
- Use build-packs as autonomy proving grounds: improvements validated in a
  build-pack should be assessed for promotion into PackFactory's own default
  agent memory, feedback loop, rehearsal, and startup surfaces.
- Prefer proving-ground JSON health checker packs first because they are the
  cleanest current autonomy test surface.
- Treat promotion-grade evidence as the standard for autonomy improvements,
  not just local success.
- When possible, turn executive-summary memory items into structured fields and
  planning-backed evidence instead of relying on prose-only handoff notes.
- When instruction drift shows up in real use, add the fix to startup-facing
  surfaces first so `load AGENTS.md` catches it early instead of depending on
  later correction.

## Progress Notes

- Completed on 2026-03-25: captured the current autonomy baseline in
  `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`
  so the current memory, restart, branch-choice, and proof state has a stable
  factory-level snapshot outside chat history.
- Completed on 2026-03-25: JSON health checker source-template tracking now
  points fresh agents at the factory autonomy baseline through
  `templates/json-health-checker-template-pack/AGENTS.md`,
  `templates/json-health-checker-template-pack/project-context.md`, and
  `templates/json-health-checker-template-pack/pack.json`.
- Completed on 2026-03-25: the open-ended branch-choice follow-up was resolved
  in favor of broader operator support first, keeping the bounded semantic
  chooser in place and making richer operator guidance the next planned
  autonomy expansion.
- Completed on 2026-03-25: broader operator support now includes canonical
  avoid-task guidance in `status/work-state.json.branch_selection_hints`, and
  the chooser can apply that guidance to narrow tied candidates before semantic
  tie-breaking.
- Completed on 2026-03-25: the richer operator-support proving-ground exercise
  succeeded with `json-health-checker-operator-avoid-branch-build-pack-v2`,
  proving an avoid-style operator hint can filter out one tied branch, record
  the filtered task in `branch-selection.json`, and still complete the remote
  continuity loop to `ready_for_deploy`.
- Completed on 2026-03-25: the operator-hint conflict and precedence policy is
  now proven with
  `json-health-checker-operator-hint-conflict-build-pack-v1`, confirming the
  current ladder of `selection_priority` -> active `avoid_task_ids` in
  canonical hint order -> active `preferred_task_ids` in canonical hint order
  -> bounded semantic alignment -> fail-closed operator review. In that proof,
  an avoid hint filtered out the preferred reporting branch, semantic
  alignment selected the stronger schema-validation branch, and the pack still
  completed the remote continuity loop to `ready_for_deploy`.
- Completed on 2026-03-25: ordered preferences and bounded hint lifecycles are
  now proven with
  `json-health-checker-ordered-hint-lifecycle-build-pack-v1`, confirming that
  a one-shot operator hint can rank preferred tasks in order, select the first
  surviving candidate, deactivate itself after first use with
  `remaining_applications=0`, and leave a later tied branch to bounded
  semantic alignment without stale operator steering.
- Completed on 2026-03-25: operator-hint audit and cleanup are now proven with
  `json-health-checker-hint-audit-cleanup-build-pack-v3`, confirming that an
  exhausted one-shot hint can be surfaced as a cleanup candidate through
  `tools/audit_branch_selection_hints.py`, then pruned cleanly from canonical
  `status/work-state.json.branch_selection_hints` without disturbing the
  completed pack state.
- Completed on 2026-03-25: operator-hint status surfacing is now proven with
  `json-health-checker-hint-status-surfacing-build-pack-v2`, confirming that
  `status/readiness.json.operator_hint_status` can carry current hint counts,
  recent consumed and deactivated hint ids, and the latest hint-audit report
  path after cleanup without requiring a separate forensic pass through
  work-state plus autonomy-run artifacts.
- Completed on 2026-03-25: pack-local operator-hint briefing is now inherited
  by fresh build-packs through `tools/materialize_build_pack.py`, and the
  generated `build-packs/json-health-checker-hint-briefing-build-pack-v1/AGENTS.md`
  now explicitly tells the next agent to surface
  `status/readiness.json.operator_hint_status` during pack startup and
  continuation briefings before going deeper.
- Completed on 2026-03-25: the PackFactory instruction and startup compliance
  review tightened `AGENTS.md`, `README.md`,
  `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`,
  and generated build-pack `AGENTS.md` inheritance so remote Codex session
  work now points clearly to PackFactory-local tooling and treats raw
  stdout/stderr as supplementary debugging rather than canonical evidence.
  The fresh proof pack
  `json-health-checker-startup-compliance-build-pack-v1` confirmed those
  inherited rules show up in newly materialized build-pack startup guidance.
- Completed on 2026-03-25: instruction-surface drift is now checked by
  `tools/validate_factory.py`, which validates root tool-inventory sync,
  startup-compliance markers, the autonomy state brief, the planning list, and
  inherited build-pack guidance markers in `tools/materialize_build_pack.py`.
- Completed on 2026-03-25: the JSON health checker source template now tracks
  the startup-compliance baseline through
  `templates/json-health-checker-template-pack/AGENTS.md`,
  `templates/json-health-checker-template-pack/project-context.md`, and
  `templates/json-health-checker-template-pack/pack.json`, so template-local
  entry now points agents back to the same managed remote-session and
  factory-only runtime-evidence import rules used at the root and in
  generated build-packs.
- Completed on 2026-03-25: the new
  `tools/run_startup_compliance_rehearsal.py` workflow proved the startup and
  remote-session compliance baseline end to end with
  `json-health-checker-startup-compliance-rehearsal-build-pack-v1`, verifying
  root markers, template markers, inherited build-pack startup guidance, and
  the managed PackFactory remote-session path on `adf-dev`.
- Completed on 2026-03-25: autonomy baseline transfer beyond the JSON health
  checker line is now proven with
  `config-drift-autonomy-transfer-build-pack-v1`, which completed the full
  PackFactory multi-hop autonomy rehearsal and reached
  `ready_for_deploy` on `adf-dev`.
- Completed on 2026-03-25: a fresh root startup re-brief now has clearer
  priority structure because it can rely on the autonomy state brief, root
  memory, startup-compliance guidance, and the instruction-surface drift
  validator together instead of reconstructing those pieces ad hoc.
- Completed on 2026-03-25: factory-root autonomy tooling discoverability via
  `AGENTS.md`, `README.md`, and
  `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`.
- Completed on 2026-03-25: factory-level root memory via
  `.pack-state/agent-memory/latest-memory.json`,
  `tools/refresh_factory_autonomy_memory.py`, and root memory schemas.
- Completed on 2026-03-25: structured root-memory fields for
  `next_action_items`, `pending_items`, `overdue_items`, and `blockers`.
- Completed on 2026-03-25: root startup/executive-summary guidance now calls
  for a distinct `Agent Memory` section, uses structured memory fields, and
  prefers canonical state when memory and control-plane state disagree.
- Completed on 2026-03-25: multi-hop autonomy rehearsal now performs a
  canonical validation-plus-benchmark readiness refresh before finishing, so a
  fresh rehearsal leaves the pack in promotion-ready canonical shape.
- Completed on 2026-03-25: the promotion-readiness exercise succeeded in one
  pass with `json-health-checker-one-pass-promotion-proof-build-pack-v1`,
  proving promotion could proceed immediately after rehearsal without a manual
  readiness retry.
- Completed on 2026-03-25: the single autonomy-to-promotion workflow landed in
  `tools/run_autonomy_to_promotion_workflow.py` and succeeded end to end with
  `json-health-checker-autonomy-to-promotion-build-pack-v1`.
- Completed on 2026-03-25: fail-closed autonomy now writes a structured block
  summary into autonomy run summaries and feedback memory, and promoted-only
  remote memory imports now record a matching operator-facing block summary in
  the import report.
- Completed on 2026-03-25: the drift exercise succeeded with
  `json-health-checker-drift-exercise-build-pack-v1`, proving that intentionally
  drifted local canonical state causes imported memory to be preserved as
  `promoted_only` with a concrete mismatch block summary instead of being
  auto-activated.
- Completed on 2026-03-25: PackFactory now has an explicit autonomy
  improvement promotion loop through
  `tools/record_autonomy_improvement_promotion.py` and
  `autonomy-improvement-promotion-report.schema.json`, so proven build-pack
  autonomy patterns can be recorded as adopted or pending across materializer,
  template, factory-root discoverability, and factory-root memory surfaces.
- Completed on 2026-03-25: the longer-backlog exercise succeeded with
  `json-health-checker-longer-backlog-build-pack-v4`, proving stable
  continuity across a four-task linear starter backlog and hardening two
  factory issues found by the exercise: imported memory reports now retain
  `block_summary` during activation, and imported-state reconcile now preserves
  canonical `validation-result.json` evidence for later benchmark execution.
- Completed on 2026-03-25: the branching exercise succeeded with
  `json-health-checker-branching-build-pack-v1`, proving that when two
  post-validation tasks are both valid, autonomy now makes a deterministic
  choice using explicit `selection_priority` before backlog order and records
  that decision in `branch-selection.json` for later review.
- Completed on 2026-03-25: the degraded-connectivity exercise succeeded with
  `json-health-checker-degraded-connectivity-build-pack-v1`, proving the
  factory can delay remote import, continue local progress while disconnected,
  preserve the returned remote memory as `promoted_only` when local canonical
  state has already advanced, and then finish the ready-boundary continuity
  pass cleanly after reconnection.
- Completed on 2026-03-25: the ambiguous-branch exercise succeeded with
  `json-health-checker-ambiguous-branch-build-pack-v2`, proving that when two
  next tasks are equally eligible without disambiguating `selection_priority`
  metadata, autonomy now stops fail-closed at `declared_escalation_boundary`,
  records both blocked candidates, and writes compatible feedback memory for
  the next agent instead of silently choosing by backlog order.
- Completed on 2026-03-25: the bounded semantic branch-choice exercise
  succeeded with `json-health-checker-semantic-branch-build-pack-v1`, proving
  that when two next tasks are equally eligible without disambiguating
  `selection_priority`, autonomy can still choose the stronger candidate by
  bounded semantic alignment to the objective, resume context, and task
  `selection_signals`, record the selection rationale, and carry that choice
  through the normal remote continuity loop to `ready_for_deploy`.
- Completed on 2026-03-25: the operator-hint branch-choice exercise succeeded
  with `json-health-checker-operator-hint-branch-build-pack-v1`, proving that
  an explicit operator branch-selection hint can override the semantic default,
  is recorded in `branch-selection.json`, and still carries cleanly through the
  normal remote continuity loop to `ready_for_deploy`.
- Completed on 2026-03-25: pack-local local-run summaries now stop passing the
  whole-factory validator into `finalize_run`, so unrelated dirty-state noise
  elsewhere in the repo no longer overrides pack-local ambiguity or escalation
  summaries with `canonical_state_integrity_failed`.
