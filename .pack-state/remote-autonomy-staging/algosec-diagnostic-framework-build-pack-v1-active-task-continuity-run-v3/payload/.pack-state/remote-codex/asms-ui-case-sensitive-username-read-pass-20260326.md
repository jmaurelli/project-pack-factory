# ASMS UI Case Sensitive Username Read Pass 2026-03-26

## Purpose

Decide whether the auth-side `Case_Sensitive_Username` config read is still the
smallest meaningful internal seam for `ASMS UI is down`.

## Key Evidence

### The login path does issue the direct config read

From `/usr/share/fa/php/SuiteLoginSessionValidation.php:225-234`:

- `checkUsernamesMatch()` calls
  `RestClient::getConfig('Case_Sensitive_Username')`
- if Metro returns `Pest_NotFound`, the code logs a warning and falls back to
  case-insensitive comparison

### The fresh-session read is already missing on this lab

From `/data/ms-metro/logs/localhost_access_log.txt`:

- fresh session `jkp0cnnf971ksgifu3k25jopiq` logged:
  `GET /afa/config/Case_Sensitive_Username?domain=0&session=jkp0cnnf971ksgifu3k25jopiq`
  -> `404`

The same direct `404` pattern appears across many earlier fresh sessions too.

### There is no Apache parent for that request

The Apache access log had no matching `Case_Sensitive_Username` line for the
same fresh session minute.

### Login still succeeded

In the same session window:

- `/afa/php/home.php` rendered successfully
- the authenticated ASMS path proceeded to a usable home shell

## Interpretation

This auth-side named config read is already effectively demoted by observation:

- it is direct PHP-to-Metro traffic
- it already returns `404` on the lab
- the login path already has a fallback for that missing value
- the customer-visible ASMS path still succeeds

So this is not the next best mutation target.

## What This Changes

The smallest auth-side direct config read is no longer the main unresolved seam.

The next more meaningful internal seam is the broader config bundle loaded by:

- `AlgosecSession::__construct()`
- `AlgosecSession::GetConfigurationSettings()`
- related `RestClient::reloadConfig()` / `RestClient::getAllConfig()` calls

## Recommended Next Move

Do not spend the next mutation on `Case_Sensitive_Username`.

Use it as proof that one auth-side direct config read is already non-blocking on
this lab, then shift the internal seam plan to the broader
`GetConfigurationSettings()` bundle.
