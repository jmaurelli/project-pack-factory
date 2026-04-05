# ASMS UI Frontline Symptom-Classification Trial 2026-03-27

## Purpose

Run the second explicit frontline trial for `ASMS UI is down` and test whether
the playbook can reclassify a vague customer-reported `GUI down` symptom
without drifting into deeper auth or subsystem theory.

This trial asked:

- if the shallow appliance surfaces are healthy, does the playbook correctly
  stop calling this a top-level UI outage and point the engineer toward a
  narrower support branch?

## Control Path

This pass used both a local swarm and the official split-host delegated path:

- PackFactory root used a small local swarm to keep the trial tied to the
  recorded testing decision model
- PackFactory root used the staged `adf-dev` build-pack copy
- the staged pack on `adf-dev` launched one target-local Codex worker on
  `algosec-lab`
- delegation tier: `observe_only`
- remote run root on `adf-dev`:
  `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/`
- delegation run id:
  `adf-autonomy-baseline-catch-up-checkpoint-v1-validate_frontline_playbook_with_small_trial_series-20260327t211257z`

## Trial Guardrails

The delegated request kept the trial intentionally shallow:

- host sanity
- `HTTPD/Apache` edge
- core service state
- listeners
- local UI and login reachability
- first usable shell classification

The delegated worker was told not to inspect:

- `/seikan/login/setup`
- `SuiteLoginSessionValidation`
- BusinessFlow
- FireFlow
- AFA
- AFF
- Metro internals
- Keycloak OIDC
- ActiveMQ
- database
- broad log sweeps

unless a shallow check clearly failed first.

## Accepted Result

The accepted delegated bundle showed:

- host up and stable on Rocky Linux `8.10`
- `httpd` active and enabled
- `algosec-ms` active and enabled
- listeners present on `80`, `443`, `8080`, and `8443`
- `http://localhost/` redirecting to `https://localhost/`
- `https://localhost/` serving the local entry point and redirecting into
  `/algosec/`
- `https://localhost/algosec/` returning `200`
- `https://localhost/algosec-ui/login` returning `200` and serving the Angular
  login shell
- `apachectl -t` ending with `Syntax OK`
- recent Apache error-log lines not showing shallow crash or proxy-failure
  symptoms

The delegated result summary was:

- the local ASMS UI edge is healthy
- the frontline classification should move away from local UI startup failure
- the best next support branch is external path or browser-side issue

## Scoring Outcome

This trial passed the symptom-classification test.

Why:

- it stayed on the shallow host, edge, service, listener, and login-shell
  surfaces
- it converted a vague `GUI down` complaint into a narrower classification
- it did not widen into deeper auth/bootstrap or downstream module theory
- it produced a clearer next support action for a real engineer

## What This Means

The frontline testing logic is now proving useful in two ways:

- the healthy-path pass can stop quickly and say `not a top-level UI outage`
- the symptom-classification pass can say `treat this as external path or
  browser-side trouble first`

The next testing move should be planned carefully, not rushed:

- define one safe reversible shallow fault
- keep the fault at the same support level, such as `httpd` or one core ASMS
  service
- only then test whether the playbook lands on that failure boundary quickly
