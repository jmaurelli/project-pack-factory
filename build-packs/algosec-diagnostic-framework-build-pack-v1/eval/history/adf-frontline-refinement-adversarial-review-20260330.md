# ADF Frontline Refinement Adversarial Review 2026-03-30

## Purpose

Record the adversarial review outcome for the new ADF refinement contracts:

- page types and entry rules
- support-language translation
- symptom-to-boundary mapping workflow

## Review Goal

Pressure-test whether the new contracts were strong enough to prevent the same
failure modes that already slowed ADF before:

- hybrid pages that try to do too many jobs
- internal systems-thinking language leaking into frontline content
- mapping drift into open-ended reverse engineering

## Accepted Findings

1. The page-type contract still left room for hybrid pages.
   Fix: require one main job per page, an explicit page declaration, a handoff
   rule, and an admission rule for new symptom-entry pages.

2. The language translation contract still allowed abstract labels to return in
   headings and quick-jump surfaces.
   Fix: extend the contract to titles, headings, quick-jump labels, and add a
   heading test plus enforcement checklist.

3. The mapping workflow still needed a stronger fail-closed stop rule.
   Fix: stop when the next step would require unsafe mutation, R&D-level
   knowledge, broad architecture digging, or more than two fast safe checks
   without narrowing the case.

4. The imported-module pilot still needed a clearer statement that Keycloak-like
   drilldowns are second-stage pages by default.
   Fix: treat imported-module drilldowns as boundary-confirmation content unless
   the customer symptom already names that module directly.

## Files Hardened

- `docs/specs/adf-frontline-page-types-and-entry-contract-v1.md`
- `docs/specs/adf-frontline-support-language-translation-contract-v1.md`
- `docs/specs/adf-symptom-to-boundary-mapping-workflow-v1.md`
- `docs/specs/adf-language-standard-v1.md`
- `docs/specs/adf-diagnostic-mapping-framework-v1.md`
- `docs/specs/adf-imported-module-drilldown-pilot-v1.md`

## Planner And State Follow-Up

The review outcome should be visible in:

- `tasks/active-backlog.json`
- `status/work-state.json`
- `status/readiness.json`

The next content pass should treat these hardened contracts as the gate for
generator and Starlight updates.
