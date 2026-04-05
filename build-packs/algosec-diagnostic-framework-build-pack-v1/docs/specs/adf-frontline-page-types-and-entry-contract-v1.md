# ADF Frontline Page Types And Entry Contract v1

## Purpose

Define the operator-facing page shapes for ADF without forcing every published
page into the same visible section scaffold.

This contract keeps the page-type split and the broad-to-narrow diagnostic
logic. It relaxes the older assumption that every page must render headings
like `Use this when`, `Start here`, `What to save`, or `When to escalate`.
It also treats the field-manual top step list as a separate quick-look
publication surface, with `steps[].overview_summary` carrying the scan-first
label for that list and any matching quick-jump labels.

## Why This Matters

ADF needs stable page types so the generator, the renderer, and the operator do
not drift into mixed page jobs.

But the live AlgoSec support workflow does not need teaching-style wrappers on
every page. Support engineers can already search titles, scan commands, collect
evidence, and follow internal escalation workflow.

The published page should therefore optimize first for:

- a searchable fit
- a clear first check
- clear branch movement
- a clear stop point

## Page Types

ADF keeps three page types:

1. symptom-entry playbook
2. boundary-confirmation page
3. deep guide

Do not collapse those page types into one generic document shape.

## One Job Per Page

Every page must answer one operator question.

Examples:

- symptom-entry playbook: `The ASMS UI is down. What should I check first?`
- boundary-confirmation page: `Is Keycloak the current stop point?`
- deep guide: `How does this boundary behave and what usually breaks it?`

If a page needs to answer more than one main question, split it.

## Page Declaration Rule

The page type must stay explicit in the backend model and page record.

The renderer may publish different visible shells for different page types, but
it must not guess the page type from prose alone.

## One-Question Rule

Reject a draft if the first screenful asks the operator to do more than one of
these at once:

- classify the broad symptom
- prove a suspected boundary
- learn deeper explanatory context

That mixing creates slow pages and weak stop points.

## Symptom-Entry Playbooks

Use a symptom-entry playbook when the operator starts from vague customer
language or a broad failure such as `ASMS UI is down`.

The page should:

- begin with the first useful check path, not with architecture framing
- move from low-cost, high-signal checks toward narrower branches
- stop once the case has narrowed to a clear subsystem, service, or next page

Visible cues must still make these things clear:

- why this page fits
- what the next branch is when a result changes
- where the current page stops being the right page

Those cues do not need fixed headings if the title, the step labels, and the
`If result is different` lines already carry them clearly.

## Boundary-Confirmation Pages

Use a boundary-confirmation page when the broad symptom has already narrowed to
a likely service, module, or route and the next job is to prove that boundary.

The page should:

- lead with the suspected service or route
- keep the checks shallow and support-practical
- surface the next branch when the boundary is healthy
- surface the failure point when the boundary is not healthy

It is acceptable for a boundary page to include an authored supplement or deep
notes, but the diagnostic path must remain the first-class content.

## Deep Guides

Use a deep guide when the page exists mainly to explain:

- how a boundary works
- what common failure classes mean
- what longer-form reference material or upstream notes matter

Deep guides must not replace the faster frontline playbook route.

## Entry Rule

The first screenful of a frontline page should spend its space on the
diagnostic flow itself.

The operator should be able to decide quickly:

- this page fits
- this does not fit
- this is the next check

Do not spend the first screenful on backend metadata, architecture notes, or
authoring commentary.
The top step list may use `overview_summary` as a separate quick-look surface,
but it should still stay distinct from the detailed step-card text.
If that top step list links to collapsed step cards farther down the same page,
the targeted card should open automatically after navigation lands there.

## Wrapper Heading Rule

The older visible wrapper sections are now optional, not mandatory.

Examples:

- `Use this when`
- `Start here`
- `What to save`
- `When to escalate`

Use them only when they make the live page clearer.

Do not add them by default just because the backend carries those fields.

## Visible Cue Rule

Removing wrapper headings is not permission to hide important operator cues.

The published page must still make these things visible in some form:

- why the page fits
- what the next branch is
- where the page stops
- what evidence matters when it changes the next action

If those cues are not obvious from the title, check labels, branch text, and
flow shape, the page fails this contract.
For field-manual pages, collapsed step cards should also surface the command
count cue before the operator opens the card.

## Check Grammar Rule

Frontline playbooks still use the standard check grammar:

- `Run`
- `Expected result`
- `Check output for`
- `If result is different`
- `Example`

That grammar is the stable field-manual unit even when the larger page shell is
leaner than older contracts required.

## Searchability Rule

Because the operator can already search and scan quickly, the title and step
labels matter more than wrapper sections.

Titles and visible step labels should therefore be:

- literal
- short enough to scan
- symptom or service oriented
- easy to search

## Reject Conditions

Reject a frontline draft if any of these are true:

- the page mixes symptom-entry, boundary proof, and deep explanation into one
  undifferentiated shell
- the first screenful explains architecture before the first useful check
- the next branch is only recoverable from hidden metadata
- the stop point is unclear after following the visible flow
- the page depends on wrapper headings to carry logic that should already be
  clear in the diagnostic path

## Current Proving Ground

For the current ADF phase:

- `ASMS UI is down` is the proving ground for the symptom-entry shell
- `ASMS Keycloak auth is down` is the proving ground for the boundary shell

Use those pages to judge whether the contracts produce searchable,
branch-friendly field manuals instead of wrapper-heavy training sheets.
