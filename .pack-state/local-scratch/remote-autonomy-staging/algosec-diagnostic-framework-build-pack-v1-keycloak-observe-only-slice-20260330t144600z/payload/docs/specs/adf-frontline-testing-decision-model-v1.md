# ADF Frontline Testing Decision Model v1

## Purpose

Record the reasoning that drives the current frontline playbook testing order
for `ASMS UI is down`.

This note is intentionally subject to change. The goal is to keep the testing
logic explicit enough that later swarm runs and autonomy loops can reuse it,
question it, and replace it quickly if the evidence says it is not useful.

## Main Question

The testing loop is not trying to prove the deepest technical truth first.

The current main question is:

`Does the playbook help a normal support engineer stop at the first useful,
supportable boundary quickly?`

That question drives the rest of the testing order.

## What The Frontline Engineer Usually Needs

For `ASMS UI is down`, the frontline engineer usually needs to answer:

- is the host under obvious pressure
- is `httpd` up
- are the core services up
- is the login page or first shell reachable
- is this really a UI outage, or is it actually a narrower login or later app
  problem

That means shallow operational checks are the main path.

Deeper auth/bootstrap/module tracing is background escalation context, not the
default frontline route.

## Why The Healthy Path Comes First

The healthy-path trial tests the shape of the playbook before fault injection.

It asks:

- does the playbook stay shallow when nothing obvious is broken
- does it stop quickly
- does it avoid drifting into deeper subsystem theory
- does it let the engineer say `this is not a top-level UI outage`

If the playbook fails on the healthy path, it is already too deep or too wide
before any lab fault is introduced.

## What `Stayed Shallow` Means

A trial stays shallow when it reaches a useful conclusion using only:

- host sanity
- `HTTPD/Apache`
- core service state
- safe restart boundaries
- listeners and basic reachability
- first usable shell classification

A trial does not stay shallow when it reaches for escalation-only surfaces
before the simple path has actually failed, such as:

- `/seikan/login/setup`
- `SuiteLoginSessionValidation`
- BusinessFlow
- FireFlow
- deeper AFA or AFF seams
- database or broker checks
- broad log hunts

## Why That Logic Matters

The current target user is a support engineer, not a Linux architect and not a
subsystem specialist.

So the frontline playbook is only good if it works at that support level.
Technically correct deep tracing is still useful, but only after the shallow
path fails to explain the case.

## Current Trial Order

Use this order for the frontline `ASMS UI is down` proving ground:

1. Healthy-path trial
2. Symptom-classification trial
3. Controlled shallow-fault trial

The order matters because it proves:

- the playbook can stay shallow
- the playbook can classify vague customer language into a narrower problem
- the playbook can later land on a real shallow failure boundary

## Decision Rule For Productivity

Keep a test slice only when it improves support usefulness.

A slice is productive when it does at least one of these:

- proves the playbook stopped at the right shallow boundary
- rules out a top-level UI outage quickly
- reclassifies a vague `GUI down` report into a narrower support branch
- identifies a safe restart boundary
- leaves the engineer with a clearer next action

If the slice mostly produces deeper logs or more internals without reducing
support ambiguity, the method is not productive enough to keep as the default.

## Current Reading

The first healthy-path trial passed this decision model:

- it stayed on host, edge, service, listener, and login-shell reachability
- it concluded the observed window was not a top-level UI outage
- it did not drift into deeper auth/bootstrap/module tracing

That means the next best phase is symptom classification, not another
healthy-path pass and not deeper module tracing.
