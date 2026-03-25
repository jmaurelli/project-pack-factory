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
4. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md`
5. `.pack-state/agent-memory/latest-memory.json`

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
2. canonical operator `branch_selection_hints`
3. bounded semantic alignment from objective, resume context, and task
   `selection_signals`
4. fail-closed escalation when the choice is still not explainable

This means the factory can now:

- choose deterministically when explicit priority metadata exists
- honor explicit operator intent when an operator wants to steer the branch
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

The next meaningful autonomy improvement is to expand broader operator support
around the current bounded branch-choice ladder.

That follow-up is already tracked in:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md`

The near-term direction is now chosen:

- prefer broader operator support before broadening toward more open-ended
  semantic choice
- keep the current fail-closed and explainable branch-choice ladder intact
- expand the canonical operator-hint surface, conflict handling, and proving
  exercises first

In plain language: the factory is not trying to become a free-form chooser by
default right now. The next gain is to let operators steer autonomy more
cleanly, more often, and with better recorded evidence.
