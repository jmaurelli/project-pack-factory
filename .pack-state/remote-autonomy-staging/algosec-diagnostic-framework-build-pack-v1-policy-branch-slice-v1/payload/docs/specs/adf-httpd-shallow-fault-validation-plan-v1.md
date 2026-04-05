# ADF HTTPD Shallow-Fault Validation Plan v1

## Purpose

Define the first controlled shallow-fault validation for the frontline
`ASMS UI is down` playbook.

This plan is intentionally narrow. The goal is not to create a generic chaos
workflow. The goal is to test one clear top-level UI boundary in the lab with
safe rollback and plain support-facing success criteria.

Use `docs/specs/adf-controlled-lab-mutation-experiment-pattern-v1.md` as the
broader lab mutation safety contract alongside this note.

## Chosen Fault Candidate

Use `httpd` as the first controlled shallow-fault candidate.

Why this service:

- it is the clearest top-level UI edge boundary
- it is already a named frontline checkpoint in the canonical playbook
- failure is easy to verify with shallow commands
- rollback is straightforward compared with deeper app or auth services

## Preconditions

Only run this trial when all of these are true:

- the healthy-path frontline trial is already recorded and passed
- the symptom-classification trial is already recorded and passed
- the target is the lab appliance, not a shared customer environment
- `target-preflight` and `target-heartbeat` pass immediately before mutation
- the mutation owner and observer are both using the current recorded testing
  decision model
- the operator has approved the `httpd` fault as the next validation move

## Trial Roles

Use a small two-agent shape:

1. Mutation owner
   Responsible for the stop, the start, and rollback verification only.

2. Observer
   Responsible for following the frontline `ASMS UI is down` playbook during
   the active fault window and stopping at the first failing shallow boundary.

Keep those roles separate so the observer is not biased by the mutation steps.

## Baseline Before Fault

Record one short healthy baseline immediately before the fault:

- `systemctl is-active httpd`
- `systemctl is-enabled httpd`
- `apachectl -t`
- `ss -ltn '( sport = :80 or sport = :443 )'`
- `curl -k -I https://localhost/algosec-ui/login`
- `curl -k -I https://localhost/algosec/`

The baseline should prove:

- `httpd` is active
- Apache config is valid
- listeners on `80` and `443` exist
- the login shell and local entry path answer normally

## Controlled Fault Step

Use the smallest reversible mutation:

```bash
systemctl stop httpd
systemctl is-active httpd
ss -ltn '( sport = :80 or sport = :443 )'
```

Do not disable `httpd`.
Do not edit Apache config.
Do not combine this with any other service mutation.

## Observer Scope During Fault

The observer must stay shallow:

- host sanity
- `httpd` state
- listeners
- local UI reachability
- first clear failing boundary

The observer should use commands like:

```bash
systemctl is-active httpd
ss -ltn '( sport = :80 or sport = :443 )'
curl -k -I https://localhost/algosec-ui/login
curl -k -I https://localhost/algosec/
```

The observer should not widen into:

- login bootstrap
- Keycloak internals
- BusinessFlow
- FireFlow
- Metro internals
- broker or database
- broad log hunts

unless the shallow fault somehow does not reproduce at the expected boundary.

## Expected Observer Outcome

The observer should classify the failure at the `Apache/HTTPD serving the UI`
boundary.

Success means the observer can say, in plain support language:

- this is a top-level UI edge outage
- the failing shallow boundary is `httpd`
- the next action is to restore or restart `httpd`

The observer should not need deeper theory to reach that conclusion.

## Rollback

Rollback should happen immediately after the observer captures the failing
boundary:

```bash
systemctl start httpd
systemctl is-active httpd
apachectl -t
ss -ltn '( sport = :80 or sport = :443 )'
curl -k -I https://localhost/algosec-ui/login
curl -k -I https://localhost/algosec/
```

Rollback is complete only when:

- `httpd` is active again
- Apache config still validates
- listeners return on `80` and `443`
- local entry and login paths answer again

## Stop Conditions

Abort the trial and restore immediately if:

- `systemctl stop httpd` hangs or behaves unexpectedly
- `systemctl start httpd` fails
- `apachectl -t` fails after rollback
- another unrelated core service degrades during the trial
- the observer needs deep subsystem tracing to classify the failure

## Evidence To Preserve

Capture:

- baseline command outputs
- active-fault command outputs
- rollback command outputs
- the observer’s classification statement
- the exact point where the playbook stopped

The result should answer one question:

`Did the frontline playbook stop quickly at the `httpd` boundary and recommend
the right shallow recovery action?`
