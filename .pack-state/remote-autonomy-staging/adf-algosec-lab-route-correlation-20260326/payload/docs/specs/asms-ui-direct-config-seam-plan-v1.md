# ASMS UI Direct Config Seam Plan V1

## Purpose

This plan defines the next internal ASMS seam after the browser-facing
owner-split question was reduced by the fresh-session correlation pass.

The remaining question is:

- which direct PHP-to-Metro `/afa/config/...` reads actually matter to the
  first usable ASMS path?

## Why This Is The Next Seam

The fresh-session correlation pass already proved:

- Apache `/afa/external/...` lines map cleanly to Metro `/afa/api/v1/...`
- direct Metro `/afa/config/...` lines can appear with no Apache parent
- same-minute `/afa/getStatus` also behaves like an internal supporting clue

So the next unresolved control surface is not the browser proxy family.
It is the direct PHP-to-Metro config family.

## Highest-Value Known PHP Callers

### Auth-side caller

`/usr/share/fa/php/SuiteLoginSessionValidation.php:227`

- `RestClient::getConfig('Case_Sensitive_Username')`

Why it matters:

- this is already in the login-validation path
- it is a small, named config read
- it is a better first auth-side candidate than a broad config-bundle mutation

Current result:

- this path is already effectively reduced by observation
- the lab logs show `GET /afa/config/Case_Sensitive_Username?...` returning
  `404`
- `SuiteLoginSessionValidation.php` already falls back when that happens
- login still succeeds on the same fresh session

Use `.pack-state/remote-codex/asms-ui-case-sensitive-username-read-pass-20260326.md`
as the canonical note for that demotion.

### Home-shell config-bundle caller

`/usr/share/fa/php/AlgosecSession.php:1257-1275`

- `GetConfigurationSettings()`
- calls `RestClient::getAllConfig()`
- loads `m_configurationSettings`

Why it matters:

- `home.php` consumes `m_configurationSettings` immediately for
  monitoring, routing, training, AppViz, and related shell behavior
- this is the strongest broad home-shell internal config candidate
- it is also much riskier because it is wider than one named config read

### Supporting module callers

`/usr/share/fa/php/AlgosecSession.php:1041-1063`

- `isFireFlowConfigured()`
- calls `RestClient::getAllConfig()`

`/usr/share/fa/php/BusinessFlowAPI.php:156-166`

- `isAppVizCloudEnabled()`
- calls `RestClient::reloadConfig()` and `RestClient::getAllConfig()`

Why they matter:

- these are likely later or supporting module checks, not the first internal
  seam to mutate
- they still matter for branch expansion after the main home-shell path is
  stronger

## Preferred Next Sequence

### Step 1: Caller Mapping

Before any mutation, map the direct `/afa/config/...` lines to the most likely
PHP caller path.

Goal:

- separate auth-side config reads from broad home-shell config-bundle reads

Preferred evidence:

- existing code call sites
- same-minute request timing
- any PHP or application logs that can tie the request to login validation or
  home-shell initialization

### Step 2: Choose The Smallest Useful Internal Seam

Prefer the smallest useful internal seam first.

Candidate order:

1. broad home-shell config bundle:
   `GetConfigurationSettings()` / `getAllConfig()`
2. later supporting module bundle reads:
   `isFireFlowConfigured()` / `BusinessFlowAPI::isAppVizCloudEnabled()`

Why this order:

- the auth-side named read is already demoted by observed `404` plus successful
  login fallback on this lab
- the broad config bundle is now the first unresolved internal config surface
- later supporting module bundle reads can stay behind the main home-shell path

### Step 3: Write A Separate Mutation Plan

Do not mutate this internal seam without a separate bounded plan that states:

- exact control point
- exact rollback
- exact expected degradation
- exact same-minute evidence to capture
- exact stop condition

## What Not To Do

Do not:

- reuse the Apache family deny pattern
- treat browser-route interception as proof of the internal seam
- mutate both the auth-side named read and the broad home-shell config bundle
  in the same run

## Deliverable

The next internal-seam planning pass should leave behind:

- one named candidate control point
- one rollback shape
- one explicit statement about whether the first target is the auth-side named
  config read or the broader home-shell config bundle

Current preferred first target:

- the broader home-shell config bundle in
  `AlgosecSession::__construct()` / `GetConfigurationSettings()`
