# ADF Flow-First Operator Publishing Contract v1

## Purpose

Define how ADF should publish operator-facing playbooks for AlgoSec support
engineers who already know how to collect evidence, when to escalate, and how
to read log-heavy text quickly.

This note does not weaken the existing systems-thinking model.
It changes how that model should be presented in frontline pages.

## Problem

Recent ADF contracts improved page-type separation, support-language safety,
and backend structure.

They also drifted into a stronger publication assumption than the real support
workflow needs:

- explicit scaffolding like `Use this when`
- explicit scaffolding like `Start here`
- explicit scaffolding like `What to save`
- explicit scaffolding like `When to escalate`

Those sections are useful in some support organizations.
They are not required in the current AlgoSec support workflow.

For the current operator audience, too much scaffolding can waste screen space
and human attention that should stay on the diagnostic path itself.

## Operator Model

Assume the operator:

- can search by playbook title or by terms inside the page
- can read command output and surrounding prose quickly
- already knows internal workflow for evidence capture and escalation
- needs the playbook to narrow the problem to the next component, branch, or
  stop point

That means the frontline page should optimize for:

- diagnostic narrowing
- branch clarity
- searchable wording
- direct check-result-next-step flow

Do not optimize first for onboarding-style instruction wrappers.

## Core Rule

The published frontline page should spend its first screenful on the diagnostic
flow itself.

If an instruction wrapper does not help the engineer choose, run, read, or
narrow the next branch, do not force it into the published page.

## Keep These Things

Keep these current ADF strengths:

- start from a broad customer symptom when the page is a symptom-entry playbook
- move from low-cost high-signal checks to narrower branches
- stop when the next action is clear
- keep deeper explanation separate from the fastest live path
- keep the standard check-block labels:
  - `Run`
  - `Expected result`
  - `Check output for`
  - `If result is different`
  - `Example`

## Change These Things

Change these publication assumptions:

1. Do not require explicit section scaffolding like `Use this when`,
   `Start here`, `What to save`, or `When to escalate` on every published page.
2. Treat those concepts as backend or authoring fields first, not mandatory
   rendered headings.
3. Let the diagnostic flow carry those meanings implicitly when the operator can
   already infer them from the check path.
4. Prefer a strong title, strong check labels, and clear branch language over
   extra explanatory headers.

This relaxation is not permission to hide:

- whether the page fits the case
- the current branch or stop point
- the next action when a result changes the path
- the evidence the engineer must preserve when that evidence changes the next
  operator action

## Page-Type Rule

Keep the three page types:

1. symptom-entry playbook
2. boundary-confirmation page
3. deep guide

Do not collapse those page types.

But do relax the assumption that each type needs one rigid visible heading set.

The contract should require:

- one clear support question per page
- one clear diagnostic flow
- one clear stop-point or handoff shape

It should not require:

- one fixed visible section list for every page of that type

## Publication Rule

The page should be judged by these operator-facing questions:

1. Can the engineer quickly tell whether this page fits the case?
2. Can the engineer follow the checks from broad symptom to narrower stop point?
3. Does each result change the next action clearly?
4. Does the page avoid making the engineer translate ADF-internal reasoning?

If the answer is yes, the page may be acceptable even without explicit wrapper
sections like `What to save`.

But the page still fails this contract if the operator has to infer the next
branch, stop point, or required evidence from hidden metadata or weak prose.

## Diagnostic Flow Rule

The main flow should still express:

- starting symptom or branch context
- the next check
- the expected result
- the branch if the result differs
- the point where the problem is narrowed enough to stop or hand off

Those things may be expressed in the check sequence itself instead of in
separate wrapper headings.

If a page removes wrapper headings, it must still surface equivalent cues in the
visible flow.

Examples of acceptable inline cues:

- a title and first check that make the fit obvious
- a step label or `If result is different` line that names the next branch
- a final check block or short inline note that makes the stop point obvious
- a short save or escalation cue attached to the branch where it matters

## Backend And Renderer Split

Keep rich backend records.

The backend may still preserve:

- `what_to_save`
- `handoff_target`
- `handoff_target_type`
- branch outcomes
- rejected branches
- stop-point notes
- page-type metadata

But the renderer should not be forced to publish every one of those fields as a
top-level operator-facing section.

The renderer should choose the leanest operator-facing shell that still keeps
these cues visible in the published flow:

- why this page fits
- what the next branch is
- where to stop
- what evidence matters when it changes the next action

The renderer must not hide those cues behind collapsed backend notes or leave
them to inference from internal route metadata alone.

## Generated Metadata Rule

Do not publish backend-facing generated metadata to support engineers by
default.

Examples of backend-facing metadata that should remain hidden from the normal
support page:

- `page_id`
- `route_kind`
- `handoff_target_type`
- internal page-record summaries

Those fields may stay in backend artifacts such as `support-baseline.json`.

If any hidden metadata field changes the operator-visible next action, the
renderer must publish an equivalent visible branch cue in support language.

Examples:

- `handoff_target` may stay internal as an identifier, but the page must still
  show the next branch or next playbook in visible language
- `what_to_save` may stay structured in the backend, but the page must still
  surface the evidence to preserve when that evidence changes escalation or the
  next session outcome

## Searchability Rule

Because the operator already knows the internal workflow, the page title and
check labels carry more weight than wrapper sections.

That means titles and visible check names should be:

- literal
- searchable
- symptom or service oriented
- short enough to scan

## Contract Impact

This note should tighten or reinterpret:

- `adf-frontline-page-types-and-entry-contract-v1.md`
- `adf-frontline-support-language-translation-contract-v1.md`

It should not weaken:

- `adf-symptom-to-boundary-mapping-workflow-v1.md`
- `adf-support-safe-scientific-method-contract-v1.md`
- `adf-backend-map-and-render-contract-v1.md`

Those three notes already carry the broad-to-narrow diagnostic logic ADF needs.

## Expected Renderer Outcome

For the current ADF phase:

- `ASMS UI is down` should remain the primary proving ground
- the page should read like a searchable field manual
- the page should keep the strong check-block grammar
- the page should reduce meta-guidance that the support workflow already covers
- internal metadata should stay behind the scenes

## Fail-Closed Rule

Do not use this contract as permission to:

- remove branching clarity
- remove stop-point logic
- remove escalation-ready backend data
- collapse page-type distinctions
- publish architecture-heavy prose just because wrapper headings were removed

If a leaner page shell makes the next action less clear, restore the smallest
necessary visible guidance and stop there.

Do not use this contract as permission to weaken:

- explicit backend recording
- structured operator-facing rows
- branch or handoff semantics in the backend map
- scientific-method cycle recording

## Current Code Anchors

This contract is expected to affect the publication path in:

- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`

It should also drive bounded changes in:

- `docs/specs/adf-frontline-page-types-and-entry-contract-v1.md`
- `docs/specs/adf-frontline-support-language-translation-contract-v1.md`
