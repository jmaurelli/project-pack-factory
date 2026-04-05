# ADF Field-Manual Overview Summary Contract v1

## Purpose

The field-manual playbook shell has two different operator jobs:

1. Let the support engineer scan the top step list quickly and decide where to
   jump.
2. Let the support engineer open a step card and follow the actual diagnostic
   flow.

Those jobs should not reuse the same sentence automatically.

`ASMS UI is down` is the proving-ground example for this contract.

## Problem

The current field-manual overview list reuses the first sentence of the
detailed step action text. That makes the top step list sound analytical,
machine-derived, and longer than it should be.

An overview item is not a mini paragraph. It is a short scan surface that tells
the engineer what the step is about and what the step helps confirm.

## Contract

Each newly generated field-manual step must carry two different operator-facing
text fields:

- `overview_summary`
- `action`

`overview_summary` is the quick-look summary for the top step list.

`action` is the fuller sentence that introduces the detailed step card.

The source of truth for operator-facing overview labels is
`steps[].overview_summary`.

The renderer must use `overview_summary` for the operator-facing overview list
and any matching field-manual quick-jump labels derived from the same step.

Legacy generated artifacts that predate this contract may still lack
`overview_summary`.

For those legacy artifacts only, the renderer may use a strict fallback
translation of `action` into overview-summary shape.

Newly generated field-manual content must not rely on automatic sentence
splitting as its published overview-summary path.

## Overview Summary Rules

`overview_summary` must be:

- one short line
- concise enough to scan quickly
- written in plain support language
- directly tied to what the detailed step card actually checks
- useful as a quick expectation-setting summary
- short enough to work as a quick-jump label as well as a top-list summary

`overview_summary` should usually:

- describe the main thing the step confirms
- mention the surface or service the engineer is about to check
- stay short enough that the engineer can skim the whole list quickly

`overview_summary` must also pass these hard checks:

- hard cap: 10 words
- one clause only
- no semicolons
- no backtick-delimited service lists
- no internal architecture nouns unless the adjacent language contract already
  treats them as normal daily support terms
- would sound natural if a support engineer said it aloud on a live case

## Overview Summary Language Rules

Prefer forms like:

- `Check host health first`
- `Check Apache and the login page`
- `Check core ASMS services`
- `Check the home page after sign-in`
- `Reproduce once and follow the failing branch`

Avoid forms like:

- `Check whether the host can support useful work for the ASMS UI path`
- `Check the first usable ASMS shell`
- `If the shallow host, Apache, service, and first-shell checks still leave the stop point unclear`
- `Check auth/session boundary ownership`
- `Confirm runtime seam health`

Those may be acceptable as internal mapping language or as part of the fuller
step card, but not as the top overview summary.

## Relationship To The Detailed Step Card

The overview summary should preview the step, not replace it.

That means:

- the overview summary should match the detailed card's real intent
- the detailed card can carry more context than the overview summary
- the overview summary should not promise a different branch than the step body
- the overview summary must not be a trivial copy of `action`

If the detailed card checks Apache and the login page, the overview summary
should say that plainly instead of summarizing the diagnostic theory around it.

If a producer cannot write a distinct overview summary that passes this
contract, that step is not ready for new frontline publication.

## Publication Rule

The top step list in the field-manual shell is a navigation aid for human
operators.

It should not expose backend-analysis phrasing just because the backend record
contains richer diagnostic text.

Affected operator-facing surfaces:

- the top field-manual step list
- field-manual quick-jump labels that point to the same step cards
- any shared step-navigation panel derived from the same `steps[]` records
- the collapsed step-card summary row
- the collapsed step-card command-count cue

The fuller `action` text remains the card-intro surface inside the detailed
step body.

## Step Interaction Rule

If a support engineer clicks an overview-step link and the page navigates to the
matching collapsed step card, that target step card must open automatically.

The shared field-manual shell should stay collapsed by default, but hash-based
navigation into a specific step is expected to reveal that step's content
without requiring a second click.

## Command Count Cue Rule

Each collapsed step-card summary should show a short literal cue for how many
commands are inside that step.

Preferred form:

- `6 commands`
- `1 command`

That cue is an expectation-setting aid, not a second sentence. Keep it short,
literal, and tied to the actual number of commands inside the step.

## Reject Conditions

Reject a field-manual overview summary when it:

- sounds like internal analytical notes instead of operator guidance
- is materially longer than the other overview items on the page
- does not clearly match the detailed step card it links to
- requires the reader to decode ADF-specific theory before they know what the
  step actually checks
- copies or lightly trims the `action` sentence without becoming a distinct
  quick-look summary

If a newly generated step fails those checks, publication should be treated as
not yet ready instead of silently falling back to the older machine-like
summary behavior.

## Implementation Notes

The backend record may keep richer step text for rendering, AI analysis, or
future branching logic. This contract requires that newly generated
field-manual artifacts publish a dedicated quick-look summary surface and treat
`steps[].overview_summary` as the human-facing source of truth for overview
navigation.

This is a backward-compatible additive artifact change for field-manual step
records inside the support-baseline output. Existing consumers may ignore
`overview_summary`, but field-manual operator publication should not.
