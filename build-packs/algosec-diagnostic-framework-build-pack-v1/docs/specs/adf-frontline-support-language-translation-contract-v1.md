# ADF Frontline Support Language Translation Contract v1

## Purpose

Define how ADF should translate its internal systems-thinking model into the
plain support language used in frontline playbooks.

The internal model may still reason about layers, seams, dependencies, and
branching. The operator-facing page should not force a support engineer to
translate those ideas during a live customer session.

## Reader Baseline

Write for a support engineer who:

- handles many cases per day
- often joins the first session with little context
- works quickly from SSH and browser checks
- may be reading English as a second language
- already knows normal evidence collection and escalation workflow
- knows product basics, Linux basics, and service or log basics, but is not an
  R&D subsystem owner

## Core Rule

Do not expose internal architecture labels in the main diagnostic flow unless
support already uses that exact term in daily work.

The main flow should use:

- symptom language
- service status language
- log and output language
- result-and-next-action language

## Allowed Noun Sources

In the frontline path, prefer nouns that come from:

- the customer complaint
- visible page or button labels
- command output
- literal service, process, unit, file, route, port, or log names

Do not build frontline wording from internal architecture nouns unless support
already uses that exact term in daily work.

This rule also applies to:

- page titles
- section headings
- navigation labels
- quick-jump labels
- step titles

The main flow should also keep the standard frontline labels from
`docs/specs/adf-language-standard-v1.md`:

- `Run`
- `Expected result`
- `Check output for`
- `If result is different`
- `Example`

Treat `steps[].overview_summary` as a separate field-manual quick-look
publication surface for the top step list and matching quick-jump labels.
It should stay in plain support language, but it should not be written as a
trimmed copy of the detailed `action` text.
When the collapsed step summary shows a command-count cue, keep that cue short
and literal, for example `6 commands` or `1 command`.

## Good Main-Flow Language

Prefer forms like:

- `Check if the login page opens`
- `Check if the service is running`
- `Check the recent service logs`
- `Check the ASMS home page after login`
- `If result is different, check Keycloak next`
- `If the page opens, move to the failing workflow next`

These are easier to scan and easier to act on.

## Language To Avoid In Frontline Flow

Avoid internal or analytical phrases such as:

- `boundary confirmation`
- `auth/session seam`
- `first usable shell`
- `later Metro-backed workflow`
- `useful work`
- `branch out`
- `stop at this boundary`
- `paired login-page and OIDC probe outputs from the same troubleshooting minute`

Those phrases may be acceptable in internal notes, mapping artifacts, or guide
material, but they should not lead the main operator path.

## Titles, Headings, And Nav Labels

This contract applies not only to step prose, but also to:

- page titles
- section headings
- `steps[].overview_summary`
- quick-jump labels
- navigation labels

Avoid analytical labels such as:

- `Boundary confirmation`
- `Imported-module drilldown`
- `System layer`
- `What that boundary means in ASMS`

Prefer labels such as:

- `Check the Keycloak service`
- `Check the ASMS home page`
- `Check Apache and the login route`
- `Review the recent Keycloak logs`

## Translation Rule

When ADF uses an internal systems-thinking label, translate it before it
appears in the playbook.

Examples:

- `entry and edge` -> `Check if the page opens`
- `auth/session` -> `Check if login works`
- `first usable shell` -> `Check if ASMS opens after login`
- `later workflow branch` -> `If ASMS opens, check the failing area next`
- `support boundary` -> `Check this service next` or `Move to the next playbook`

## Service Names

Literal service names are allowed when the engineer needs them for the next
check.

Examples:

- `Check if keycloak.service is running`
- `Check if httpd is active`
- `Check the recent Keycloak logs`

But do not lead with the module name unless the page is already a
boundary-confirmation page.

## Section Title Rule

Before the first command, use only titles a frontline support engineer would
already recognize from daily work.

Prefer:

- `ASMS UI is down`
- `Check Apache and the login route`
- `Check if login works`
- `Check if the service is running`
- `Check the next failing area`

Avoid:

- `Boundary confirmation`
- `What that boundary means in ASMS`
- `Generic failure classes`
- `Imported-module drilldown`

## Title Test

Before a title or heading is published, ask:

- would a support engineer naturally say this phrase on a live customer call

If the answer is no, rewrite it in support language even if the internal model
keeps the deeper label.

## Main-Flow Rule

Every bullet or step in the frontline path should help the engineer do one of
these:

- run a check
- read a result
- decide the next service to inspect
- decide whether the case has narrowed enough to stop
- preserve the evidence that changes the next action when it matters

If a sentence does not help with one of those actions, move it to a guide,
note, or supporting explanation.

## Heading Test

Use this quick test before keeping a title or heading in a frontline page:

- would a support engineer naturally say this on a live call
- does it describe the next action or result directly
- does it avoid internal analysis language

If the answer is no, rewrite it or move it out of the frontline path.

If a title or heading does not help the engineer choose, run, read, or branch
cleanly, rewrite it or move it out of the frontline page.

## Example Translation

Instead of:

- `The paired login-page and OIDC probe outputs from the same troubleshooting minute`

Use:

- `Save the output from the login-page check and the Keycloak check`

Instead of:

- `What that boundary means in ASMS`

Use:

- `If result is different: check the next service`

or move the explanation into a guide if it is not needed for the next action.

## Fail-Closed Rule

If a sentence still sounds like internal analysis, AI summarization, or design
commentary, do not keep rewriting it in place inside the main flow.

Move it out of the frontline path and keep only:

- the check
- the result to look for
- the next action
- the evidence to save when that evidence changes the next action

## Generator Rule

Future generator and template work should treat this translation step as part
of page generation, not as optional copyediting at the very end.

The internal model may stay technical.
The generated frontline wording must stay operational.

## Enforcement Checklist

Reject a frontline draft if any of these are true:

- a heading uses internal mapping language instead of support-visible language
- the first screenful explains architecture before the first action
- the page asks the engineer to translate internal terms mentally
- the next action is not obvious after reading the step title and the `If result is different` line
- the page only makes sense because wrapper headings explain fit, stop-point,
  or evidence cues that should already be clear in the visible flow

## Current Code Anchors

This contract is expected to anchor to the current operator-facing wording
emitted by:

- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_playbook_dependency_path()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_decision_playbooks()`
- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
  `_render_playbook_markdown()`
- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
  `_render_operator_playbook_markdown()`
