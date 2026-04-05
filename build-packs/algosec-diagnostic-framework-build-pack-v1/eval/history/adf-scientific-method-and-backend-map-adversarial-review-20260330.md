# ADF Scientific Method And Backend Map Adversarial Review 2026-03-30

## Purpose

Record the adversarial review outcome for:

- `docs/specs/adf-support-safe-scientific-method-contract-v1.md`
- `docs/specs/adf-backend-map-and-render-contract-v1.md`

## Accepted Findings

1. The scientific-method note was still too conceptual.
   Fix: require an explicit six-part cycle record and keep the current
   hypothesis tied to a support-visible candidate stop point.

2. The scientific-method note needed a clearer boundary around lab mutation
   experiments.
   Fix: require the observer result and rollback outcome to stay distinct from
   the mutation step itself.

3. The backend map-and-render note did not yet describe a safe migration path
   from the current `support-baseline` shape.
   Fix: add a staged compatibility rule with optional new fields first, then
   stricter fail-closed handling for migrated records.

4. The backend map-and-render note needed stronger linkage and minimum-field
   rules.
   Fix: define stable IDs across symptom, mapping row, page record, and handoff
   target, plus minimum required fields by page type.

## Hardened Files

- `docs/specs/adf-support-safe-scientific-method-contract-v1.md`
- `docs/specs/adf-backend-map-and-render-contract-v1.md`

## Pack-State Follow-Up

The active content task should continue, but the next generator change should
keep these review outcomes in force:

- scientific-method cycles must be explicit enough to audit
- schema migration must be staged
- new page records should fail closed when required fields are missing
