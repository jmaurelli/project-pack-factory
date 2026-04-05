# ASMS UI Frontline Healthy-Path Trial 2026-03-27

## Purpose

Run the first explicit healthy-path trial for the frontline `ASMS UI is down`
playbook and score whether the playbook stays shallow in practice.

This trial was meant to answer one simple question:

- when the appliance is healthy, does the playbook stop quickly at the host,
  edge, service, and shell boundary without drifting into deeper auth or
  subsystem theory?

## Control Path

This pass used both a local swarm and the official split-host delegated path:

- PackFactory root used a small local swarm to keep the trial scoped to the
  shallow frontline path
- PackFactory root used the staged `adf-dev` build-pack copy
- the staged pack on `adf-dev` launched one target-local Codex worker on
  `algosec-lab`
- delegation tier: `observe_only`
- remote run root on `adf-dev`:
  `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/`
- delegation run id:
  `adf-autonomy-baseline-catch-up-checkpoint-v1-validate_frontline_playbook_with_small_trial_series-20260327t205317z`

## Trial Guardrails

The delegated request kept the trial intentionally shallow:

- host sanity
- `HTTPD/Apache` edge
- core service status
- listeners
- login page reachability
- first usable shell classification

The delegated worker was told not to inspect:

- `/seikan/login/setup`
- `SuiteLoginSessionValidation`
- BusinessFlow
- FireFlow
- AFA SOAP
- Keycloak OIDC
- Metro post-home traffic
- ActiveMQ
- database
- broad log sweeps

unless an earlier shallow check clearly failed and needed one matching local
clue.

## Shallow Scorecard

The trial counts as "stayed shallow" when all of these are true:

- it stops on host, edge, service, listener, or shell classification
- it names whether this is still a top-level UI outage
- it does not widen into bootstrap or downstream module theory
- it produces a clear next support action

The trial counts as drift if it starts using deeper auth, session, or module
surfaces before the shallow path fails.

## Accepted Result

The accepted delegated bundle showed:

- host `algosec` up and stable
- `httpd.service` active
- `php74-php-fpm.service` active
- `httpd` listening on `80` and `443`
- `https://127.0.0.1/` returning `200 OK` with redirect behavior into
  `/algosec/`
- `https://127.0.0.1/algosec/` returning `200 OK`
- `https://127.0.0.1/algosec-ui/login` returning `200 OK` with a substantial
  HTML payload
- no need to widen into the blocked deeper surfaces

The delegated result summary was:

- the appliance is not currently in a top-level `ASMS UI is down` state
- if the issue is still user-reported, the next useful branch is user path,
  load balancer path, or a narrower login or shell problem

## Scoring Outcome

This trial passed the shallow-path test.

Why:

- it stopped at the frontline host, Apache, service, and login-page boundary
- it answered the top-level classification question quickly
- it did not inspect the forbidden deeper auth or downstream surfaces
- it produced a practical next move instead of a deeper dependency hunt

## What This Means

The healthy-path phase of the frontline validation sequence is now proven
useful enough to keep.

The next phase should be a symptom-classification trial:

- reproduce a case where the user still reports "GUI down"
- prove the playbook can reclassify it into login, shell, or later workflow
  trouble without falling back into deeper auth/bootstrap theory too early

Controlled shallow-fault work should stay later and only use safe reversible
faults after the healthy and symptom-classification phases keep paying off.
