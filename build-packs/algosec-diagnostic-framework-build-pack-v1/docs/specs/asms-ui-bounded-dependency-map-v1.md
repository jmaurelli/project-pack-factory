# ASMS UI Bounded Dependency Map v1

Date: 2026-03-26

## Purpose

Capture the current evidence-backed dependency map for the top-level `ASMS UI is
down` path without overstating a strict serial chain that the lab evidence does
not yet prove.

This note is intentionally bounded:

- keep the top-level map focused on the first usable shell and the earliest
  named stop points
- separate first-pass checks from later supporting dependencies
- record the strongest remaining question for the next lab-backed cycle

## Current Working Rule

Start at the host, move into Apache as the UI edge, then split into auth and
app branches. Stop at the first place where useful work no longer happens.

The current evidence does **not** support a strict serial chain of:

`host -> httpd -> keycloak -> ms-metro`

The stronger current model is:

1. host can support useful work
2. Apache serves the practical UI edge
3. the path splits into an auth branch and an app branch
4. the first usable shell boundary is `/afa/php/home.php`
5. later module and workflow failures should branch out of top-level `GUI down`

## What Is Currently Proven

### Host and Apache edge

- `httpd.service` is active and serving the practical UI edge.
- `/algosec/suite/login` redirects into `/algosec-ui/login`.
- Apache serves `/algosec-ui/login` directly before the later auth and app
  paths are tested.

That means Apache can already prove useful work before Keycloak or Metro are
tested.

### Earliest observed auth chain

- The first observed JS-triggered post-shell hop is `/seikan/login/setup`.
- The first proven legacy auth-triggering request is
  `/afa/php/SuiteLoginSessionValidation.php`.
- Keycloak is a real observed auth-chain member, but not the first post-shell
  auth trigger.
- A successful authenticated flow reached BusinessFlow before later FireFlow
  auth checks and before the final home-shell transition.

So the auth side currently looks like:

`Apache UI edge -> legacy setup/session-validation hop -> BusinessFlow -> later Keycloak/FireFlow handoff`

### First usable shell boundary

- The strongest current GUI-up boundary is the first usable
  `/afa/php/home.php` shell.
- The current live seam pass now narrows the first-shell Metro dependency:
  login/session bootstrap calls `utils::HandleConfigParams()`, which reaches
  `AlgosecSession::GetConfigurationSettings()` and then
  `RestClient::getAllConfig()` against `http://127.0.0.1:8080/afa` before the
  shell is usable.
- Same-minute external config, license, and session-extension traffic still
  exists, but it now looks more like adjacent or supporting traffic than the
  hard first-shell dependency itself.

### App branch ownership

- Apache owns browser-facing proxy families like `/afa/external` and
  `/afa/api/v1`.
- PHP also talks directly to Metro through `RestClient` against
  `http://127.0.0.1:8080/afa`.
- That means the remaining `config` question is split across two owners:
  browser-owned Apache proxy traffic and PHP-owned direct Metro calls.

## What Is Demoted

### A strict `httpd -> keycloak -> ms-metro` chain

This is too strong for the current evidence. Apache proves useful work before a
Keycloak or Metro dependency has to be claimed.

### Family-wide Apache deny as the main next tool

Broad Apache denial of `/afa/external` and `/afa/api/v1` did not cleanly break
the first usable home shell. Those broad route families are no longer the best
next control point for this question.

### ActiveMQ as a first-pass GUI-down dependency

ActiveMQ is a real supporting dependency for later FireFlow behavior, but the
current reproduced login and handoff minutes still center on auth, session, and
REST work instead of broker-side signals.

## Bounded Dependency Map

Keep this as the current top-level map unless stronger lab evidence disproves
it:

- Host health
- Apache UI edge
- Legacy setup and session-validation hop
- BusinessFlow as the first named operational checkpoint
- Later Keycloak and FireFlow auth-coupled handoff
- First usable `/afa/php/home.php` shell
- Immediate shell hydration
- Later module and workflow branches

Within that map:

- `BusinessFlow` is the earliest named operational checkpoint.
- `Keycloak` is a strong auth-branch dependency, but not the first observed
  trigger.
- `ms-metro` is clearly in the subsystem, and the best current evidence says
  the first-shell Metro dependency is the backend config fetch during
  login/session bootstrap rather than every same-minute Metro request.
- `ActiveMQ` stays behind closer FireFlow checks unless a failing minute shows
  broker or JMS involvement directly.

## Core Scenarios To Validate Next

These are the smallest next scenarios that should sharpen the map without
widening scope:

1. `Apache edge up, legacy auth hop fails`
   Goal: confirm the closest named stop point stays on the early auth path
   before later Keycloak or FireFlow clues are promoted.

2. `Successful SuiteLoginSessionValidation -> home.php transition`
   Status: validated from a successful `2026-03-26 05:29:53-05:29:56 EDT`
   session window.
   Result: the hard first-shell dependency set is the redirect into
   `home.php` plus `dynamic.js`, `home.js`, dashboard bootstrap
   `commands.php`, tree bootstrap, `TopbarMenu.php`, and `prod_stat.php`.
   Nearby FireFlow auth checks, BusinessFlow shallow health, AFF shallow
   health, and suite static assets are adjacent traffic rather than the
   redirect gate itself.

3. `Apache edge and auth hop up, first home shell fails`
   Goal: compare a failed shell-transition window against the successful
   baseline above and identify which immediate first-shell requests are truly
   missing or degraded.

4. `First home shell is up, later module path fails`
   Goal: branch out of top-level `GUI down` and keep later module or workflow
   failures outside the first-pass map.

## Strongest Remaining Question

The best next bounded question is:

How tightly can we correlate the successful
`SuiteLoginSessionValidation.php -> home.php` transition to the exact Metro
request set, so we can separate the hard first-shell config fetch from nearby
suite-frame and external-shell traffic?

Current evidence says this is now a better next seam than:

- another family-wide Apache deny
- a generic “is Metro up” pass
- promoting ActiveMQ into the first-pass path
- re-deriving the successful shell-transition sequence from scratch

## Latest Live Follow-Up

The latest accepted delegated target-local Codex slice confirmed this exact
direct PHP-to-Metro seam:

- `home.php` mainly consumes already-cached configuration state
- login/session bootstrap populates that state before the shell via
  `HandleConfigParams() -> GetConfigurationSettings() -> RestClient::getAllConfig()`
- the backend PHP path talks directly to Metro at `http://127.0.0.1:8080/afa`
- Apache externally exposes the equivalent backend through `/afa/api/v1/config`
- externally visible `/afa/config` is not mapped on this appliance and showed
  `404` in observed logs

That means the next refinement should focus on tighter request correlation, not
on reopening the broad question of whether Metro is involved at all.

The next accepted delegated slice then correlated one successful
`SuiteLoginSessionValidation.php -> home.php` transition to AFA session
`i88p8vb1s79p6nb0f4o2jkpb07` and sharpened the first-shell dependency set:

- redirect gate: `SuiteLoginSessionValidation.php -> home.php`
- immediate shell bootstrap: `dynamic.js.php`, `home.js`, dashboard bootstrap
  `commands.php`, `POST /fa/tree/create`, `TopbarMenu.php`, and `prod_stat.php`
- backend data plane after entry: Metro session traffic such as config, user,
  device, report, and monitor reads that populate the shell after it is already
  entered

That makes the next high-value comparison a failed shell-transition window
against this successful baseline, rather than another generic route-ownership
pass.
