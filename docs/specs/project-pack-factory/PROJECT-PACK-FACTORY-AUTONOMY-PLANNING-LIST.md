# Project Pack Factory Autonomy Planning List

Purpose: track the current PackFactory autonomy follow-up work at the factory
level so future build-packs inherit the improvements by default instead of
repeating the same optimization per pack.

Last updated: 2026-03-25

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

Recent proof points:

- `json-health-checker-multi-hop-autonomy-build-pack-v1`
- `json-health-checker-promotion-gate-build-pack-v1`
- `json-health-checker-one-pass-promotion-proof-build-pack-v1`
- `json-health-checker-autonomy-to-promotion-build-pack-v1`

## Current Limits

- Autonomy is strongest in bounded PackFactory workflows, not broad unscripted
  project work.
- Imported memory is fail-closed by design, so progress can pause until
  reconcile happens.
- The strongest current proof covers short starter backlogs more than longer
  branching work.
- Testing-time remote connectivity is proven; permanent factory-to-pack
  connectivity is not assumed.

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

- [ ] Drift exercise.
  Scope: intentionally change canonical `status/work-state.json` after a remote
  run, then import returned memory and confirm it is preserved but not
  activated.
  Why it matters: this verifies fail-closed memory intake under real mismatch.

- [ ] Longer-backlog exercise.
  Scope: prove continuity across a starter backlog with 4-6 tasks instead of 2.
  Why it matters: this tests whether task selection stays stable as autonomy
  depth increases.

- [ ] Branching exercise.
  Scope: create a proving-ground pack where two next tasks are both valid and
  inspect how autonomy chooses and explains the choice.
  Why it matters: this is the first meaningful step beyond single-path starter
  backlogs.

- [ ] Degraded-connectivity exercise.
  Scope: continue local build-pack progress without factory access, then
  reconnect and test import plus compatibility gating.
  Why it matters: this reflects the expected real-world deployment case more
  closely than always-on connectivity.

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

## Working Notes

- Keep these changes factory-level unless there is a strong reason to scope
  them to one build-pack.
- Prefer proving-ground JSON health checker packs first because they are the
  cleanest current autonomy test surface.
- Treat promotion-grade evidence as the standard for autonomy improvements,
  not just local success.
- When possible, turn executive-summary memory items into structured fields and
  planning-backed evidence instead of relying on prose-only handoff notes.

## Progress Notes

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
