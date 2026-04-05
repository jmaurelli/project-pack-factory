# ADF Diagnostic Mapping Framework v1

## Purpose

Define the small, adjustable operating contract for how ADF should map ASMS
runtime surfaces without drifting into open-ended exploration.

This framework is intentionally subject to change. The goal is to start small,
stay grounded, read the evidence, and only keep methods that help support
engineers reach clearer stop points faster.

## Scope

The framework maps `ASMS runtime on Rocky 8`, not Rocky 8 as a generic Linux
architecture exercise.

Linux utilities remain critical, but they are the evidence surface around ASMS
runtime rather than the primary architecture map.

## Core Method

Use `ASMS-first, hypothesis-driven, bounded traversal`.

Each mapping cycle should:

1. Pick one symptom or support scenario.
2. Reproduce one bounded runtime journey.
3. Correlate that journey across ASMS runtime layers and host evidence.
4. Name the first broken or ambiguous boundary.
5. Record the result as a confirmed seam, eliminated branch, or narrowed but
   unresolved branch.
6. Stop and update the map instead of widening into open-ended hunting.

## Shared Taxonomy

Use the current shared ASMS-runtime-first taxonomy:

1. ASMS entry and edge
2. ASMS authentication and session
3. ASMS application services
4. Shared runtime and dependencies
5. Host integration and operating evidence

`Useful work` remains the stop rule, not a named layer.

This taxonomy is an internal mapping scaffold.

Do not surface these taxonomy labels as the main headings in frontline
playbooks unless support already uses the same term in daily work.

This shared taxonomy is internal ADF mapping language.
Translate it before it appears in frontline operator-facing pages.

## Surface-Mapping Passes

Use three bounded passes:

1. Static surface inventory

- relevant `systemd` units
- listeners and ports
- Apache routes and proxy rules
- app-owned entry points
- log locations
- config files
- JVM, Perl, and PHP runtime footprints
- database and broker dependencies

2. Runtime surface correlation

- what actually participates in the reproduced symptom journey
- which ASMS seams are customer-visible or support-visible
- which host surfaces explain those runtime seams

3. Support-value reduction

- keep only surfaces that are customer-relevant, safe to probe, readable from
  SSH, repeatable, and useful for naming the next stop point
- archive deep or rare surfaces as engineering evidence instead of promoting
  them into the frontline path

## First-Step Rule

Do not invent first steps case by case.

Start with:

1. short host sanity gate
2. ASMS entry and edge
3. ASMS authentication and session
4. first named ASMS service seam
5. shared runtime or host evidence only when earlier ASMS seams stay ambiguous

Use this as internal discovery order, not as required operator-facing page
labels.

Within that order, prefer the lowest-cost, highest-signal, safe check first.

## Productivity Rule

A mapping step is productive only if it does at least one of these:

- proves a seam is healthy
- proves a seam is broken
- eliminates a false branch
- narrows the next stop point
- upgrades a vague symptom into a named support boundary

If a step only produces more logs without reducing ambiguity, it was not
productive enough to keep.

Do not follow more than one new branch in the same pass unless the earlier
branch was clearly eliminated.

## Repeatability Rule

Every mapping run should record:

- target and run id
- symptom or scenario
- hypothesis under test
- exact commands used
- bounded time window
- observed surfaces
- first stop point or ambiguity point
- next recommended branch
- confidence level
- one operator-facing row that translates the result into support language

Repeatability matters more than exhaustiveness.

## Trajectory Rule

Every slice should name:

- entry symptom
- current hypothesis
- next seam to test
- success condition
- stop condition
- escalation condition

No open-ended hunts.

## Fail-Closed Stop Rule

Stop the current mapping pass when the next step would require:

- unsafe mutation for the current trial
- R&D-level subsystem reasoning instead of frontline support reasoning
- broad architecture exploration that does not change the next support action
- more than two fast safe checks without narrowing the case

When that happens, record the stop point and handoff instead of widening the
slice.

## Evaluation Rule

Compare mapping methods by outcome quality, not by volume.

A method is better if it:

- finds the first stop point faster
- uses fewer commands
- avoids deeper irrelevant branches
- produces a clearer support action
- is easier for a Tier 2 support engineer to follow
- repeats cleanly on another run

## Current Direction

The current direction is to use `ASMS UI is down` as the canonical proving
ground for this framework.

For that proving ground, keep the default path shallow and support-first:

- host sanity gate
- Apache or HTTPD edge and local UI reachability
- core ASMS service status and safe restart boundary
- first usable shell and case classification

Use login-bootstrap, auth-chain, or downstream module tracing only as
escalation when those shallow checks do not explain the case. Do not promote
BusinessFlow, Keycloak, or FireFlow as assumed first dependencies for a pure
frontline `ASMS UI is down` case unless the same reproduced journey actually
reaches them.

The current four playbooks are still useful, but they should be treated as seed
examples and comparison points rather than as the final architecture.

## Frontline Trial Sequence

Use a small phased validation sequence for the frontline `ASMS UI is down`
playbook:

1. Healthy-path trial
   Goal: prove the shallow path stops quickly on a healthy lab minute without
   drifting into deeper auth or subsystem theory.

2. Symptom-classification trial
   Goal: prove the playbook can reclassify a vague `GUI down` report into a
   narrower login, shell, or workflow problem once the shallow path shows the
   top-level UI is still up.

3. Controlled shallow-fault trial
   Goal: only after the first two passes are useful, test one safe reversible
   lab fault such as `httpd.service` or `ms-metro.service` so the playbook has
   to land on a real shallow failure boundary.

Keep the sequence intentionally small:

- start with the healthy path
- prefer service or shell classification before fault injection
- only use safe reversible shallow faults
- stop quickly if a phase is not reducing ambiguity or support effort

Use `docs/specs/adf-frontline-testing-decision-model-v1.md` as the explicit
logic note for why the frontline sequence is judged by support usefulness
rather than by deeper technical reach.
