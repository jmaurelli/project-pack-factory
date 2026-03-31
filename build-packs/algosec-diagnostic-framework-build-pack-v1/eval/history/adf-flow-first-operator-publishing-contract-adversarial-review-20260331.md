# ADF Flow-First Operator Publishing Contract Adversarial Review

Date: 2026-03-31

## Scope

Adversarially review:

- `docs/specs/adf-flow-first-operator-publishing-contract-v1.md`

against:

- `docs/specs/adf-symptom-to-boundary-mapping-workflow-v1.md`
- `docs/specs/adf-support-safe-scientific-method-contract-v1.md`
- `docs/specs/adf-backend-map-and-render-contract-v1.md`

## Review Prompt

Pressure-test the new flow-first publication spec for ambiguity, fail-open
renderer behavior, and any wording that could accidentally hide operator-facing
branch, stop-point, or evidence cues while trimming wrapper sections.

## Swarm Findings

1. The first draft was too fail-open about removing wrapper sections.
It did not require an equally visible replacement for fit, stop-point, and
evidence-capture cues when those headings disappeared.

2. The phrase "the renderer should choose the leanest operator-facing shell"
was too subjective.
Without tighter language, it could let the renderer hide important handoff or
stop-point structure inconsistently across pages.

3. The spec said backend fields like `what_to_save` and `handoff_target` could
stay behind the scenes, but it did not yet say when equivalent visible cues
must still appear in the published flow.

4. The first draft leaned too heavily on what the operator could infer.
That risked conflicting with the explicit-recording discipline required by the
mapping, scientific-method, and backend map contracts.

## Tightening Applied

The spec was tightened to require that a leaner page shell still keeps these
operator-facing cues visible:

- why the page fits
- what the next branch is
- where to stop
- what evidence matters when it changes the next action

The spec now also says:

- hidden backend metadata must be replaced by equivalent visible branch cues
  whenever that metadata changes operator action
- this publication contract does not weaken explicit backend recording,
  operator-facing structured rows, branch semantics, or scientific-method cycle
  records

## Result

The reviewed contract is now acceptable for bounded implementation.

It still relaxes unnecessary wrapper headings for the current support workflow,
but it no longer gives the renderer permission to hide branch, stop-point, or
evidence semantics behind backend-only metadata.
