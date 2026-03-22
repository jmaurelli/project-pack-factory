# Project Pack Factory Test Intent And Test Authorization Clarification Spec

## Status

Proposed specification for instruction-document updates only.

Core root-level behavior from this spec is now reflected in `AGENTS.md`,
`README.md`, and `PROJECT-PACK-FACTORY-TESTING-POLICY.md`.

This document remains useful as rationale and as a regression guardrail for
future root-doc edits.

Some evidence and gap statements below describe the state of the docs at the
time this spec was proposed.

This spec does not authorize implementation changes outside documentation.

## Problem Statement

Project Pack Factory currently says testing should stay small, deterministic,
and high-signal, but the operator-facing and agent-facing instructions do not
clearly separate:

- running existing test, validation, benchmark, or pipeline surfaces
- authoring new tests or expanding test coverage

That ambiguity can cause an agent to interpret requests such as:

- `continue testing`
- `test this build pack`
- `refresh testing evidence`

as permission to create new tests, even when the operator only intended the
agent to execute existing bounded checks.

## Desired Outcome

The documentation must make the default interpretation explicit:

- requests to `test`, `continue testing`, `run tests`, `refresh evidence`, or
  similar phrases mean: run existing test and benchmark surfaces that already
  exist for the relevant factory workflow, template pack, or build pack
- those requests do not authorize creating, modifying, or expanding tests
- adding or changing tests requires explicit operator authorization

Agents may still recommend new tests, but recommendation and implementation
must be treated as separate actions.

This clarification is intended only for Project Pack Factory root-level and
factory-spec documentation.

It is not intended to modify internal documentation that lives inside a
specific template pack or build pack.

## Definitions

### Existing Test Surfaces

For this repo, `existing test surfaces` means already-present commands or
artifacts such as:

- existing unit or workflow tests already checked into the repo
- declared pack validation commands such as `validate-project-pack`
- declared pack benchmarks such as `benchmark-smoke`
- existing factory validation commands such as `tools/validate_factory.py`
- existing deployment pipeline or promotion flows when the operator asks for
  deployment-linked evidence

### New Test Authoring

For this repo, `new test authoring` means any of the following:

- creating a new test file
- adding a new test case to an existing file
- strengthening an existing test or benchmark by adding assertions, cases,
  branches, fixtures, or expanded runtime checks
- adding a new benchmark scenario beyond the currently declared benchmark
  contract
- adding a new benchmark declaration
- expanding a test matrix beyond the currently implemented scope
- changing a placeholder document such as `tests/README.md` into executable test
  coverage

### Explicit Operator Authorization

`Explicit operator authorization` means the operator clearly requests one of:

- add a test
- create a benchmark
- expand coverage
- strengthen this test by adding a case
- modify the tests for this pack or workflow

General testing requests are not explicit authorization.

## Required Policy

### Default Interpretation Rule

When an operator asks to test a factory workflow, template pack, or build pack,
the agent must default to executing the smallest relevant existing bounded
checks before considering any test authoring.

Default execution order should be:

1. existing validation commands
2. existing pack benchmarks or workflow smoke tests
3. existing workflow or deployment pipeline commands only when the operator
   asked for deployment-linked evidence or promotion readiness

### No-Implied-Test-Authoring Rule

The following operator requests must not be treated as permission to add tests:

- `continue testing`
- `test this`
- `run the tests`
- `refresh testing evidence`
- `make sure this is working`
- `evaluate this pack`

If the agent believes current test surfaces are insufficient, it must:

1. run the existing executable surfaces that already exist
2. report the gap clearly
3. recommend concrete test additions separately
4. wait for explicit authorization before creating or modifying tests

Weak, placeholder-only, minimal, or missing current coverage is not implicit
authorization to create or strengthen tests.

### Recommendation Rule

Agents may recommend new tests when:

- a core runtime path has no direct executable protection
- a fail-closed invariant is only implied and not checked
- a workflow mutation lacks meaningful regression coverage

Recommendations must be framed as recommendations, not as already-approved
work.

### Minimal-Change Rule

When explicit authorization to add tests is given, the agent should still
prefer:

- strengthening or replacing the weakest existing test
- extending an existing benchmark if it is the correct protection surface
- avoiding broad new matrices or speculative edge-case coverage

Strengthening or extending an existing test or benchmark still counts as test
authoring and still requires explicit operator authorization.

This clarification does not expand any existing test budget.

## Required Documentation Updates

The following documents must be updated.

### 1. Root `AGENTS.md`

Add a new working-rule block that states:

- `testing` requests default to running existing validation, benchmark, and
  workflow commands
- agents must not create or expand tests without explicit operator approval
- agents may recommend test additions after reporting results from existing
  surfaces
- pack-level benchmarks are preferred before broader workflow or deployment
  actions unless deployment evidence was requested

Update any already-live ambiguous phrases so they are no longer standalone
authorization cues.

Required replacement or annotation targets include:

- `continuing active testing work`
- any similar startup or next-step wording that could be read as permission to
  expand test coverage

Add one short example pair:

- `continue testing this build pack` means rerun the
  existing build-pack validation and benchmark surfaces
- it does not mean add new unit tests unless explicitly asked

### 2. Root `README.md`

Add a short `Testing Intent` section for operators that explains:

- asking to test a pack or workflow reruns existing checks by default
- asking to add or change tests must be explicit
- deployment evidence may require pipeline execution, but pipeline execution is
  different from authoring new tests

Also replace or annotate any already-live ambiguous phrases such as
`continuing active testing work` so the nearby text explicitly says that this
means rerunning existing checks unless the operator separately authorizes test
changes.

### 3. `PROJECT-PACK-FACTORY-TESTING-POLICY.md`

Add a dedicated section named `Interpretation Of Testing Requests`.

That section must state:

- default testing work means execute existing surfaces
- new tests require explicit operator authorization
- recommendations for new tests are allowed without implementation
- the policy's test caps constrain authorized test additions but do not make
  those additions implicit

Add a dedicated section named `What Counts As A New Test`.

That section must list:

- new files
- added test cases
- strengthening existing tests or benchmarks with added cases or assertions
- new benchmark scenarios
- new benchmark declarations
- expanded matrices
- converting placeholders into executable coverage

### 4. Template And Build-Pack Guidance Surfaces

Update only the factory-level guidance that shapes future template and
build-pack docs, so that root instructions do not accidentally imply
permission to author tests.

This update should apply to:

- `PROJECT-PACK-FACTORY-TEMPLATE-PLANNING-AND-CREATION-TECH-SPEC.md`
- any pack scaffold guidance that currently creates `tests/README.md`

Required clarification:

- the presence of `tests/README.md` or a `tests/` directory is documentation of
  a testing area in future scaffolds, not standing authorization to add tests
  during ordinary testing work
- factory-level guidance that mentions pack-local benchmarks or tests must make
  clear that those references describe existing surfaces to run, not permission
  to create or strengthen tests
- if a pack has only placeholder testing guidance or thin executable coverage,
  root/factory-level instructions should still direct the agent to recommend
  changes rather than author tests without approval

### 5. Explicit Scope Exclusion

This spec must explicitly state that it does not require edits to internal
documentation inside existing packs, including:

- `build-packs/*/AGENTS.md`
- `build-packs/*/project-context.md`
- `build-packs/*/tests/README.md`
- `templates/*/AGENTS.md`
- `templates/*/project-context.md`
- other pack-local documentation files inside a specific template or build pack

If later work is desired to align those internal docs, that should happen under
a separate spec with separate approval.

## Suggested Wording Constraints

Updated instruction documents should consistently use the following phrasing:

- `run existing tests and benchmarks`
- `refresh existing evidence`
- `add or modify tests only with explicit operator approval`

Updated instruction documents should avoid using bare phrases such as:

- `continue testing work`
- `test the pack`

without a nearby sentence defining that those phrases mean executing existing
surfaces by default.

Existing uses of those phrases in live instruction documents should be replaced
or directly annotated, not merely offset by new sections elsewhere.

## Acceptance Criteria

This documentation update is complete when all of the following are true:

- a fresh agent reading root instructions would interpret `continue testing` as
  rerunning existing test surfaces only
- a fresh agent would understand that adding a new test file requires explicit
  operator approval
- a fresh agent would also understand that strengthening an existing test or
  benchmark requires explicit operator approval
- the testing policy defines what counts as a new test
- root and factory-spec instruction documents no longer contain unannotated
  phrases that imply broad testing work
- factory-level template/build-pack guidance no longer implies that the
  existence of `tests/` invites test authoring during ordinary testing tasks
- the spec explicitly excludes editing internal documentation within existing
  template-pack and build-pack directories
- the clarified language does not expand current test budgets or broaden the
  testing scope

## Non-Goals

This spec does not:

- change current test budgets
- require deleting existing tests
- change deployment packaging behavior
- require agents to ask permission before running existing tests
- prohibit agents from recommending better tests
- require edits to internal documentation inside a specific existing template
  pack or build pack
