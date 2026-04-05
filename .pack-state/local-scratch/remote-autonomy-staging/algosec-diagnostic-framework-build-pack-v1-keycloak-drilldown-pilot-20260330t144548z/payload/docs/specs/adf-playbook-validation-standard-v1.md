# ADF Playbook Validation Standard v1

## Purpose

Define the minimum validation rule for treating an ADF diagnostic playbook as
trusted support content.

## Standard

ADF should not treat a diagnostic playbook as trusted support content until two
things are true:

1. the playbook logic has been validated in operational practice
2. the important service and workflow dependency claims have been validated
   against runtime evidence

This rule exists to prevent ADF from publishing technically plausible but
operationally unproven guidance.

## What Must Be Validated

### 1. Playbook logic

ADF must validate that the playbook helps a support engineer:

- start in the right place
- gather useful evidence quickly
- stop at the first useful support boundary
- classify the issue into a narrower branch when the top-level label is wrong

This is about operational usefulness, not just architectural correctness.

### 2. Dependency logic

ADF must validate the important dependency claims behind the playbook, such as:

- which service is actually the first useful stop point
- which service is only a later branch dependency
- whether two services are peers or a strict serial chain
- whether a visible symptom belongs to Apache, auth, shell bootstrap, or a
  later workflow branch

ADF should only make dependency claims that are backed by bounded runtime
evidence.

## Minimum Evidence Types

At least one trusted playbook should have evidence from these surfaces when
they apply:

- healthy-path validation
- symptom-classification validation
- one or more bounded shallow-fault validations
- runtime dependency-order or dependency-ownership validation

Useful evidence may include:

- service state and listener checks
- login-page or shell reachability checks
- same-window Apache request evidence
- bounded proxy-path checks
- bounded service-fault simulations
- preserved restart and rollback outcomes

## Claim Levels

Use these practical claim levels when writing support content:

### Proposed

The idea is plausible, but not yet validated against runtime evidence.

ADF should not present this as trusted support content.

### Validated playbook logic

The support workflow has been tested and shown to guide the engineer to the
right shallow boundary or narrower branch.

ADF may publish this as support guidance, but only within the bounds of the
validated behavior.

### Validated dependency logic

The dependency claim itself has been tested against runtime evidence.

ADF may describe the dependency ordering or service ownership as a trusted
runtime-backed claim.

## Required Writing Discipline

When a playbook is validated only partly:

- say exactly what is proven
- say exactly what is still inferred
- do not merge incomplete sibling branches into one conclusion

Example:

- Keycloak-down behavior may be proven
- Metro-down behavior may still be unproven
- the playbook should say that plainly instead of pretending both branches are
  equally proven

## Current ADF Evidence Pattern

The current ADF proving-ground pattern is:

1. validate the frontline decision model
2. validate healthy-path behavior
3. validate symptom classification
4. validate one or more shallow-fault behaviors
5. validate dependency order or dependency ownership where the playbook makes a
   stronger service claim

## Current Grounding Evidence

This standard is grounded in the current ADF pack evidence:

- [adf-frontline-testing-decision-model-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/adf-frontline-testing-decision-model-v1.md)
- [asms-ui-dependency-order-validation-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/asms-ui-dependency-order-validation-v1.md)
- [asms-ui-httpd-shallow-fault-validation-20260328.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/eval/history/asms-ui-httpd-shallow-fault-validation-20260328.md)
- [asms-ui-keycloak-simulation-and-metro-blocked-20260330.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/eval/history/asms-ui-keycloak-simulation-and-metro-blocked-20260330.md)
- [asms-keycloak-integration-map-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/asms-keycloak-integration-map-v1.md)

## Rule For Publication

ADF may publish a playbook route or operator guide before every branch is fully
proven, but only if:

- the published guidance stays inside the validated behavior
- the page does not overclaim the unproven branches
- the evidence note clearly marks the remaining gaps

That gives ADF a safe way to grow useful support content while still staying
fail-closed about what is actually proven.
