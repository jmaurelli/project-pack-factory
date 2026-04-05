# ADF Backend Map And Render Contract v1

## Purpose

Define how the Codex agent should build the internal ADF map on the backend so
it can later be rendered into clear frontline playbooks for support engineers.

This is the contract between:

- runtime evidence and mapping work
- structured ADF artifacts
- the Starlight generator and rendered pages

## Why This Matters

ADF should not build support pages directly from free-form reasoning.

It should build:

1. an internal structured map
2. an operator-facing structured row
3. a rendered page from those structures

That keeps systems thinking in the model while keeping support language in the
output.

## Current Code Surfaces

The current ADF backend already uses this basic path:

- `runtime_baseline.py` builds `diagnostic_flows`
- `runtime_baseline.py` derives `decision_playbooks`
- `runtime_baseline.py` derives `symptom_lookup`
- `starlight_site.py` reads `support-baseline.json`
- `starlight_site.py` renders the Starlight playbook markdown

This note hardens that path into an explicit contract.

## Required Backend Layers

The Codex agent should keep these layers distinct:

1. runtime evidence
2. internal mapping model
3. operator-facing mapping row
4. page record
5. rendered page

## Ownership Rule

For the current ADF phase, keep ownership split like this:

- runtime evidence and preserved lab observations feed the map
- Codex or pack-local mapping logic may create internal mapping rows
- the support-baseline schema carries the accepted page records
- `starlight_site.py` renders accepted page records only

The renderer should not invent missing map structure on its own.

## Layer 1: Runtime Evidence

This is the observed input.

Examples:

- service state
- listener state
- local route behavior
- Apache logs
- Keycloak logs
- Metro clues
- bounded lab experiment results

This layer should stay fact-oriented.

## Layer 2: Internal Mapping Model

This is the systems-thinking layer used by ADF authors and Codex.

It may include:

- symptom family
- internal hypothesis
- candidate support boundary
- rejected branches
- dependency notes
- confidence
- supporting evidence references

This layer may use internal mapping language.

## Layer 3: Operator-Facing Mapping Row

This is the translated row that support content should use.

It should include fields like:

- customer symptom
- first check
- first branch result
- next page or next service
- what to save
- when to escalate

This layer must use support-visible language.

Each operator-facing row should retain a stable link back to the internal map
row and the eventual page record.

This row should be required whenever a new page record is promoted for
frontline use.

## Layer 4: Page Record

This is the structured page object the generator consumes.

Future page records should explicitly include:

- `page_type`
- `label`
- `symptom_focus`
- `first_action`
- `handoff_target`
- `what_to_save`
- `steps`
- `decision_rule`

Allowed `page_type` values for the current ADF phase:

- `symptom_entry`
- `boundary_confirmation`
- `deep_guide`

Minimum required fields by page type:

- `symptom_entry`:
  `page_type`, `page_id`, `customer_symptom`, `first_action`,
  `branch_if_pass`, `branch_if_fail`, `what_to_save`, `handoff_target`
- `boundary_confirmation`:
  `page_type`, `page_id`, `use_this_when`, `service_name`, `checks`,
  `what_to_save`, `handoff_target`
- `deep_guide`:
  `page_type`, `page_id`, `title`, `purpose`, `supporting_topics`

## Layer 5: Rendered Page

The rendered page is the Starlight output.

It should be built from the page record, not from free-form reconstruction.

That means the generator should:

- render symptom-entry pages differently from boundary-confirmation pages
- use operator-facing wording from the page record
- fail closed when page metadata is missing or contradictory

Do not let the renderer guess `page_type`, `handoff_target`, or frontline
headings from free-form prose when those fields are missing.

## Separation Rule

Do not let internal mapping labels flow directly into the rendered page.

Examples of internal-only fields:

- internal hypothesis
- internal boundary label
- rejected branches
- taxonomy layer

Examples of operator-facing fields:

- `Use this when the page does not open`
- `Check if login works`
- `Check the Keycloak service`
- `Save this output`
- `When to escalate`

## Linkage Rule

The backend contract should keep these identifiers stable when possible:

- `symptom_id`
- `mapping_row_id`
- `page_id`
- `handoff_target`

That makes it easier to trace:

- which symptom produced the mapping row
- which mapping row produced the page record
- which page should be opened next

## Routing Rule

The routing layer should behave like this:

- `symptom_lookup` should route into `symptom_entry` or
  `boundary_confirmation` records
- `deep_guide` records should be linked as optional follow-up, not as the first
  page for a vague symptom
- every frontline page record should name a handoff target or explicit
  escalation stop point

## Minimum Structured Shape

The backend map should eventually be able to produce records shaped like:

```json
{
  "page_type": "symptom_entry",
  "page_id": "ui-and-proxy",
  "customer_symptom": "The ASMS page is not loading",
  "first_action": "Check httpd and local HTTPS",
  "branch_if_pass": "Continue to login checks",
  "branch_if_fail": "Diagnose Apache/HTTPD",
  "what_to_save": [
    "httpd status output",
    "local curl output"
  ],
  "handoff_target": "keycloak-auth"
}
```

And for a boundary page:

```json
{
  "page_type": "boundary_confirmation",
  "page_id": "keycloak-auth",
  "use_this_when": "Login page opens but sign-in fails",
  "service_name": "keycloak",
  "checks": [
    "service state",
    "listener 8443",
    "OIDC probe"
  ],
  "what_to_save": [
    "service status",
    "recent logs",
    "probe output"
  ],
  "handoff_target": "escalate_or_deeper_guide"
}
```

## Current Gap

The current backend already has `decision_playbooks` and `symptom_lookup`, but
it does not yet carry the full explicit split needed by the new refinement
contracts.

The main gaps are:

- `page_type` is not yet explicit in the main baseline schema
- internal mapping rows and operator-facing rows are not yet separated clearly
- handoff targets are not yet first-class fields
- the generator still contains wording and layout assumptions tied to the older
  generic playbook shape

## Compatibility And Migration Rule

Do not switch the whole pack to the new schema in one jump.

Use this staged adoption rule:

1. add the new fields to the support-baseline schema as optional
2. teach the generator to prefer the new fields when present
3. keep current fallback behavior only for legacy records that have not been
   migrated yet
4. fail closed for new or migrated pages that claim the new contract but omit
   required fields

This keeps current content renderable while making new content stricter.

## Generator Rule

Future generator work should:

1. extend the support-baseline schema first
2. carry explicit page metadata into `starlight_site.py`
3. render by `page_type`
4. reject operator-facing headings that use internal mapping language
5. reject frontline page promotion when no operator-facing row exists

The generator should not invent page type, handoff target, or operator wording
when those fields are missing from a migrated record. It should fail closed for
that record and report the missing fields instead.

## Current ADF Application

For the current ADF phase:

- `ui-and-proxy` should become the primary `symptom_entry` page record
- Keycloak should become a `boundary_confirmation` page record
- deep architecture and upstream explanation should move into `deep_guide`
  records instead of staying blended into frontline pages

Until that migration lands, current guide pages may remain outside the main
`decision_playbooks` list, but the contract should still be treated as the
target render shape.

## Current Code Anchors

This backend contract is explicitly anchored to the current code below.

Backend shape producers:

- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `build_support_baseline()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_diagnostic_flows()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_symptom_lookup()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_build_decision_playbooks()`
- `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`
  `_playbook_dependency_path()`

Current render entry points and hardcoded record shapes:

- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
  `PRIMARY_PLAYBOOK_ID`
- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
  `FALLBACK_CANONICAL_PLAYBOOK`
- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
  `KEYCLOAK_PLAYBOOK`
- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
  `_render_playbook_markdown()`
- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
  `_render_operator_playbook_markdown()`
- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
  `_render_imported_module_drilldown_markdown()`

These are the exact current code anchors expected to change first.

## First Expected Change Surfaces

The first implementation-grade changes expected by this contract should happen
in this order:

1. `build_support_baseline()`
   Extend the emitted support-baseline schema with optional new fields for
   `page_type`, operator-facing rows, and handoff metadata.

2. `_build_symptom_lookup()`
   Preserve routing fields that can explicitly hand a symptom to a page record
   instead of only a generic domain suggestion.

3. `_build_decision_playbooks()`
   Start emitting page-record metadata for new or migrated records without
   breaking current legacy records.

4. `_render_playbook_markdown()` and `_render_operator_playbook_markdown()`
   Prefer explicit `page_type` and handoff fields when present.

5. `_render_imported_module_drilldown_markdown()`
   Stop acting as a one-off implicit schema for boundary-confirmation pages once
   the new page-record fields exist.
