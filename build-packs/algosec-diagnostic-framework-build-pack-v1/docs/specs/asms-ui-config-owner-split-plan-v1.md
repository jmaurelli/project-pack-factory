# ASMS UI Config Owner Split Plan V1

## Purpose

This plan defines the next narrower ASMS investigation after the
family-wide Apache proxy experiments.

The new question is no longer:

- which top-level Apache proxy family matters to the first usable shell?

That question is now closed.

The new question is:

- which remaining `config` and `session` surfaces are browser-owned, and which
  are PHP-owned direct Metro calls?

## Why The Seam Changed

The family-wide Apache experiments already proved:

- denying `/afa/external` did not break the first usable ASMS home shell
- denying the top-level `/afa/api/v1` Location also did not break the first
  usable ASMS home shell

The deeper route-owner pass added the missing explanation:

- Apache proxies `/afa/external` and `/afa/api/v1` to
  `http://localhost:8080/afa/api/v1`
- PHP `RestClient` also talks directly to
  `http://127.0.0.1:8080/afa`
- `RestClient::getConfig($param)` issues direct `/config/...` requests
- the login path already uses that direct helper through
  `SuiteLoginSessionValidation.php`
- the browser UI bundle separately owns `/afa/api/v1/config`

That means the remaining `config` family is split across different owners.

## Current Interpretation

Use this model until stronger evidence replaces it:

- browser-owned config/session paths:
  - `/afa/external/...`
  - `/afa/api/v1/...`
- PHP-owned direct Metro config path:
  - `/afa/config/...` through `RestClient`

This is why a browser-edge Apache deny is no longer enough to explain all
same-minute Metro `config` evidence.

## Preferred Next Experiment Order

### Step 1: Read-Only Correlation Pass

Run one bounded fresh login and prove which Metro `config` requests have no
matching Apache access-log parent in the same session minute.

Goal:

- separate browser-owned requests from PHP-owned direct Metro requests without
  mutating the appliance

Success condition:

- at least one meaningful `config` request family can be classified as
  browser-owned or PHP-owned with stronger evidence than inference alone

Current result:

- completed in `.pack-state/remote-codex/asms-ui-config-correlation-pass-20260326.md`
- browser-facing `/afa/external/...` requests lined up with Metro
  `/afa/api/v1/...`
- direct Metro `/afa/config/...` and same-minute `/afa/getStatus` lines had no
  matching Apache access-log parent
- the remaining unresolved seam is now mostly the internal direct
  `/afa/config/...` family, not the browser proxy family

### Step 2: Internal Seam Planning

Now that the read-only correlation pass is complete, prefer internal seam
planning before another browser-route experiment.

Target:

- the direct PHP-to-Metro `/afa/config/...` family

Reason:

- the browser-facing `/afa/external` -> `/afa/api/v1` mapping is now already
  explained well enough for this path
- the remaining unanswered ownership question sits behind PHP `RestClient`

This internal plan needs its own:

- control point
- rollback shape
- evidence plan
- risk review

Do not execute that deeper internal mutation by default.

### Step 3: Exact Browser-Route Isolation

Only use exact browser-route isolation now if a later question still requires
browser-only confirmation after the internal seam is planned.

Isolate browser-owned requests that can be intercepted
cleanly and counted.

Preferred targets:

- exact `/afa/api/v1/config/...` requests seen in the browser flow
- exact `/afa/external/...` config or session requests seen in the browser flow

Rules:

- use bounded waits and visible-shell checks
- record actual matched block or abort events, not only intended patterns
- treat this as optional follow-up, not the default next move

## What Not To Repeat

Do not default back to:

- a family-wide Apache deny on `/afa/external`
- a family-wide Apache deny on `/afa/api/v1`
- broad CDP blocked-URL patterns without confirmed matched block events

Those surfaces are now useful historical evidence, not the next best default.

## Deliverables

The next pass should leave behind:

- one note that records the correlation result
- the updated next-seam interpretation in pack state
- one explicit statement about whether the unresolved path is still browser-side
  or now mostly internal PHP-to-Metro
- one separate internal seam plan if the unresolved path is now mostly direct
  `/afa/config/...`
