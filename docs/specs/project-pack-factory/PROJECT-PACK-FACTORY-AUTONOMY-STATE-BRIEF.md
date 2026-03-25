# Project Pack Factory Autonomy State Brief

Purpose: preserve the current PackFactory autonomy baseline in one stable
factory-level note so future agents can recover the current memory, restart,
and branch-choice capabilities without reconstructing them from chat history.

Snapshot date: 2026-03-25

## What Exists Now

PackFactory now has a real factory-default autonomy loop rather than a
collection of one-off proving-ground experiments.

At a high level, the factory can now:

- materialize new build-packs with autonomy guidance and pack-local memory
  support by default
- write distilled restart memory after autonomy runs and activate a stable
  `latest-memory.json` pointer
- export that memory from a remote testing target, import it back into the
  factory, compatibility-gate it, and reactivate it when canonical state still
  matches
- checkpoint a pack mid-backlog, stop, restart later, and continue from the
  next task instead of replaying the whole starter path
- rehearse the full autonomy loop and use that rehearsal as real promotion
  evidence
- run a one-command autonomy-to-promotion workflow for fresh proving-ground
  packs

## Knowledge Loading And Memory Surfaces

The current default knowledge-loading path for a new autonomy-capable
build-pack is:

1. `AGENTS.md`
2. `pack.json`
3. `contracts/project-objective.json`
4. `tasks/active-backlog.json`
5. `status/work-state.json`
6. `.pack-state/agent-memory/latest-memory.json`

At the factory root, the main restart-memory path is:

1. `AGENTS.md`
2. `README.md`
3. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`
4. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`
5. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md`
6. `.pack-state/agent-memory/latest-memory.json`

The root memory is advisory restart context. Canonical truth still lives in
the factory control-plane surfaces such as `registry/`, `deployments/`,
readiness state, and promotion evidence.

## Proven Stop And Restart Loop

The current autonomy loop can now handle long-running bounded work across more
than one hop.

The proven loop is:

1. create a local checkpoint after the current active task
2. write pack-local feedback memory and activate `latest-memory.json`
3. resume the next task on a remote testing target from that memory
4. export runtime evidence and returned memory from the remote target
5. import the returned evidence into factory history
6. compatibility-gate the returned memory against canonical local state
7. activate the returned memory when compatible, or preserve it fail-closed
8. continue the next hop or stop cleanly at `ready_for_deploy`

This is proven through the factory workflows in:

- `tools/run_local_mid_backlog_checkpoint.py`
- `tools/run_remote_active_task_continuity_test.py`
- `tools/run_remote_memory_continuity_test.py`
- `tools/run_multi_hop_autonomy_rehearsal.py`
- `tools/run_autonomy_to_promotion_workflow.py`

## Proven Branch-Choice Ladder

PackFactory now has an explicit next-task decision ladder instead of relying on
backlog order as fake judgment.

The current ladder is:

1. explicit `selection_priority`
2. canonical operator `branch_selection_hints`, including preferred-task and
   avoid-task guidance
3. bounded semantic alignment from objective, resume context, and task
   `selection_signals`
4. fail-closed escalation when the choice is still not explainable

This means the factory can now:

- choose deterministically when explicit priority metadata exists
- honor explicit operator intent when an operator wants to steer the branch
- honor explicit operator avoid guidance when an operator wants to rule out a
  branch before semantic tie-breaking
- make a bounded semantic choice when one task is clearly better aligned and
  the justification can be recorded
- stop honestly when the choice is still too ambiguous to defend

## Strongest Current Proof

The strongest current proof line is the JSON health checker proving-ground
family.

Important proof surfaces include:

- multi-hop rehearsal and promotion-gated continuity
- one-pass rehearsal-to-promotion proof
- longer linear backlog continuity
- degraded-connectivity recovery during testing
- ambiguous branch fail-closed stopping
- bounded semantic branch choice
- operator-hint branch choice
- operator-avoid branch choice
- operator-hint conflict precedence
- ordered hint lifetime
- hint audit and cleanup
- readiness hint-status surfacing
- inherited pack-local hint-status briefing
- startup-compliance rehearsal
- cross-template autonomy transfer on the config-drift line

In plain language: the factory has now proven memory handoff, stop/restart,
promotion-linked rehearsal, and bounded branch choice. It is no longer just a
theory or a pack-local workaround.

## Current Limits

PackFactory autonomy is still strongest in bounded factory-shaped workflows,
not broad unscripted project work.

The main current limits are:

- imported memory is fail-closed by design, so progress can pause until
  reconcile happens
- the system assumes testing-time remote connectivity only; permanent
  factory-to-pack connectivity is not required after deployment
- open-ended branch choice beyond explicit metadata, operator hints, and
  bounded semantic signals is still not proven
- this is not yet a perpetual always-on autonomous worker that invents and
  reprioritizes work indefinitely without stronger structure

## Why This Matters

This is now a real PackFactory default for future build-packs, not a repeated
per-pack optimization exercise.

The build-packs remain the proving grounds, but validated improvements are now
being carried back into factory tooling, root memory, startup surfaces, and
promotion gates so the next pack starts from a stronger baseline.

## Current Best Next Frontier

The next meaningful frontier is no longer basic loop survivability. It is the
quality and generality of the autonomy baseline we already have.

That follow-up is already tracked in:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md`

The current proven operator-hint ladder is:

1. explicit `selection_priority`
2. active operator `avoid_task_ids` within the tied top-priority set, in
   canonical hint order
3. active operator `preferred_task_ids` within the remaining tied set, in
   canonical hint order
4. bounded semantic alignment
5. fail-closed operator review

Hints can now also carry bounded lifetime state through
`remaining_applications`, so one-shot steering can expire automatically after
it has been used, exhausted hints can be audited and pruned cleanly, the
current hint summary can be surfaced directly in readiness state, and fresh
build-packs now inherit guidance to mention that status during pack entry.

The latest proof line is now anchored by
`json-health-checker-startup-compliance-rehearsal-build-pack-v1` plus
`config-drift-autonomy-transfer-build-pack-v1`. The first proved the startup
and remote-session compliance baseline end to end through the managed PackFactory remote-session path,
and the second proved that the autonomy baseline transfers
cleanly beyond the JSON health checker proving ground into the config-drift
line. That instruction-surface baseline is also guarded by
`tools/validate_factory.py`, so the root docs, state brief, planning list, and
generated build-pack guidance do not have to stay in sync by memory alone.

In plain language: the factory is still not trying to become a free-form
chooser by default. It now has a proven, explainable policy for conflicting
operator guidance, a proven way to expire one-shot operator steering, a proven
way to audit and clean up exhausted hints, a proven way to surface hint status
both in readiness state and in fresh pack entry guidance, and a proven
startup-compliance rehearsal that uses the managed PackFactory remote-session
path. It has also now shown that this autonomy baseline transfers cleanly to
the config-drift line instead of staying trapped inside the JSON health
checker proving ground.

The three strong lanes from the last frontier wave are now in place:

1. autonomy quality scoring
2. a factory-root startup benchmark
3. a cross-template transfer matrix

The first quality-scoring surface is now live in
`tools/score_autonomy_quality.py`. It writes schema-valid score reports under
`.pack-state/autonomy-quality-scores/` from existing rehearsal artifacts
instead of requiring a new autonomy loop. The first two proofs are:

- the startup-compliance rehearsal for
  `json-health-checker-startup-compliance-rehearsal-build-pack-v1`
- the first cross-template transfer for
  `config-drift-autonomy-transfer-build-pack-v1`

Both currently score `strong`, which is useful as a baseline but also a sign
that the next frontier is not raw survivability anymore. The next quality
question is whether startup itself can be benchmarked directly and whether the
same baseline holds across a broader template matrix.

Those two follow-ups are now also proven:

- `tools/run_factory_root_startup_benchmark.py` produced a `strong` root
  startup benchmark with a source trace and generated startup brief.
- `tools/run_cross_template_transfer_matrix.py` produced a three-row matrix
  across config drift, release evidence, and API contract transfer proofs, all
  of which reached `ready_for_deploy`.

The next meaningful frontier is now narrower: decide how autonomy-quality
scores should influence real promotion behavior, if at all.
