# ADF Autonomous Iteration Loop Completion Boundary V1

## Purpose

This note defines what must exist before
`build_adf_autonomous_iteration_loop` can be treated as complete.

The goal is to stop ADF from treating remote continuity bookkeeping as if it
were the same thing as a real, repeatable iteration loop.

## Current Decision

For the current ADF phase, the iteration-loop boundary stays inside the ADF
build pack.

PackFactory root remains the owner of:

- managed continuity workflows
- runtime-evidence import and pull flows
- multi-hop rehearsal and promotion gating

ADF remains the owner of:

- what counts as completion for the ADF-local iteration-loop task
- what pack-local artifact the next bounded iteration must produce
- what ADF-specific logic is still too local to promote into PackFactory

Factory inheritance decision: defer any PackFactory-root promotion until ADF
records one pilot iteration evidence artifact that uses this boundary and shows
either a reusable shared pattern or a real PackFactory control-plane gap.

## Named Outputs Required For Completion

`build_adf_autonomous_iteration_loop` is only complete when all of the
following exist:

1. Loop contract artifact:
   `docs/specs/adf-autonomous-iteration-loop-completion-boundary-v1.md`
2. Pack-local versus factory split decision record:
   the decision table in this note
3. Pilot iteration evidence artifact:
   `docs/specs/adf-autonomous-iteration-loop-pilot-evidence-v1.md`

The pilot iteration evidence artifact must record one bounded iteration that
produced a real ADF-local outcome beyond bookkeeping.

Required fields for the future pilot evidence artifact:

- `Attempted task:`
- `Evidence reviewed:`
- `Outcome class: changed_artifact | no_change | blocked_boundary`
- `Why not only bookkeeping:`

Required outcome marker for the future pilot evidence artifact:

- `Changed pack-local artifact:`
- `No-change decision:`
- `Blocked boundary:`

The outcome marker must point to one of these concrete result types:

- a source or docs artifact that changed for a real ADF task
- an explicit no-change decision with a bounded reason tied to the attempted
  task and reviewed evidence
- an explicit blocked boundary with the concrete reason the loop stopped and
  what prevented further ADF-local progress

## Decision Table

| Concern | Current home | Why now | Promotion trigger |
| --- | --- | --- | --- |
| Continuity, rehearsal, import, and promotion semantics | PackFactory root | These are already factory-owned workflows and should not be redefined by ADF | Only change at root when a shared control-plane gap is proven |
| ADF loop completion boundary | ADF build pack | This is first a question about what ADF itself must produce before moving on | Promote only if the same boundary pattern is needed across multiple packs |
| AlgoSec appliance launcher hygiene | ADF build pack | The menu, shell, and browser constraints are ADF-specific right now | Promote only if the same launcher pattern becomes a repeated factory need |
| Distinguishing continuity success from real task completion | ADF build pack now, PackFactory candidate later | ADF is the proving ground for this distinction today | Promote later if ADF records a reusable rule that should govern multiple build packs |

## Not Sufficient For Completion

The following do not complete `build_adf_autonomous_iteration_loop` on their
own:

- `validate-project-pack` passing by itself
- imported runtime-evidence reconciliation by itself
- `promoted_only` memory intake by itself
- a successful managed continuity pass by itself
- launcher result files, moved timestamps, rebuilt review artifacts, or live
  page checks by themselves
- restaging the pack to the remote target by itself
- work-state advancement or recorded next steps by themselves

Those signals are useful, but they only prove orchestration health unless they
are paired with the named loop contract, split decision, and pilot iteration
evidence artifact.

## Consequence For The Active Task

`build_adf_autonomous_iteration_loop` stays open after this clarification task.

The next bounded ADF slice should produce
`docs/specs/adf-autonomous-iteration-loop-pilot-evidence-v1.md` and use it to
record one real iteration outcome tied to a pack-local ADF artifact or an
explicit no-change decision.
