# Project Pack Factory Testing Policy

## Purpose

Keep testing intentionally small, high-signal, and aligned with the actual size
and risk profile of Project Pack Factory.

This factory is:

- small
- single-operator
- text-oriented
- low-security
- not a multi-user platform

The test suite should reflect that reality.

## Policy

Testing must prioritize core workflow confidence over broad coverage.

The default rule is:

- test the few behaviors that would materially break factory operation
- do not test everything that can be tested

## Hard Test Cap

For the three factory workflow areas below, the total combined test budget is:

- `12` tests maximum

Covered areas:

- build-pack materialization
- build-pack promotion
- CI and deployment orchestration

This `12`-test cap applies only to those three workflow areas.

## Template Creation Budget

The template planning and creation workflow has a separate small budget:

- `4` tests maximum

If that budget needs to grow, replace a weaker creation test rather than
adding a fifth.

Recommended allocation:

- materialization: `4`
- promotion: `4`
- CI and deployment orchestration: `4`

If a new test is needed after the cap is reached:

- replace a weaker test rather than increasing the total

## What Deserves A Test

Tests in the capped workflow areas should protect:

- the primary happy path
- one or two fail-closed preconditions
- one reconcile or idempotent path where repeated execution matters
- one evidence-writing or state-mutation check where later agents depend on it

## What Does Not Deserve A Test

Do not spend test budget on:

- metrics formatting
- incidental helper functions
- low-risk internal plumbing
- broad edge-case matrices
- multi-user behavior
- security hardening scenarios outside the actual use case
- image or media behavior

## Preferred Test Style

Tests should be:

- small
- deterministic
- text-only
- local
- high-signal

Prefer:

- smoke tests
- contract-level assertions
- minimal fixture setup
- assertions on the few state files that actually matter

Avoid:

- large fixture forests
- deep mocks for low-risk helpers
- tests that mostly restate implementation details

## Decision Rule For New Tests

A new test is justified only if it protects:

- a core user-visible behavior
- a critical fail-closed invariant
- a state mutation that later agents rely on

If it does not clearly protect one of those, it should not be added.

## Relationship To Other Specs

This policy constrains implementation of:

- `PROJECT-PACK-FACTORY-TEMPLATE-PLANNING-AND-CREATION-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-BUILD-PACK-MATERIALIZATION-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-BUILD-PACK-PROMOTION-WORKFLOW-TECH-SPEC.md`
- `PROJECT-PACK-FACTORY-CI-CLOUD-DEPLOYMENT-ORCHESTRATION-TECH-SPEC.md`

This policy does not require broad new testing for unrelated historical fixture
packs.
