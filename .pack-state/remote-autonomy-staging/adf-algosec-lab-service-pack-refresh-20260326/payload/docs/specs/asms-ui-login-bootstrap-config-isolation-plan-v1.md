# ASMS UI Login Bootstrap Config Isolation Plan V1

## Purpose

Run the first bounded application-level experiment against the broader
`GetConfigurationSettings()` seam during ASMS login bootstrap.

## Why This Is The Next Experiment

The browser-facing Apache seam is already reduced.

The owner split is already explained:

- Apache owns browser-facing `/afa/external/...` and `/afa/api/v1/...`
- PHP `RestClient` also issues direct `/afa/config/...` requests to Metro

The remaining unresolved question is now:

- which broader login-bootstrap config loads actually matter to the first
  usable ASMS shell?

The login-bootstrap control-path pass showed that the safest first
application-level hook is:

- `AlgosecSessionManager::postLoginActions()`
- specifically the call to `utils::HandleConfigParams($AlgosecSession)`

## Variant C1: Skip Post-Login Config Recache

### Goal

Test whether the first usable ASMS shell depends on the post-login config
recache path, or whether the earlier constructor-time config bundle is already
enough.

### Exact Control Point

Remote file:

- `/usr/share/fa/php/AlgosecSessionManager.php`

Target line:

- `utils::HandleConfigParams($AlgosecSession);`

Temporary mutation:

- replace that call with a temporary ADF marker log line or guarded no-op

### Expected Degradation

Possible outcomes:

- login still succeeds and `/afa/php/home.php` is still usable
- login succeeds but the home shell is partially degraded
- login or redirect flow fails before a usable shell appears

### Evidence To Capture

- fresh incognito login result
- final URL
- page title
- visible home-shell markers
- same-minute Apache access lines
- same-minute Metro access lines around `/afa/config/...`, `/afa/api/v1/...`,
  and `/afa/getStatus`
- any application log line showing the temporary ADF marker

### Rollback

- restore the original `/usr/share/fa/php/AlgosecSessionManager.php`
- run `php -l /usr/share/fa/php/AlgosecSessionManager.php`
- rerun one fresh login to confirm recovery if the mutation changed behavior

### Stop Condition

Stop immediately and roll back if:

- PHP syntax check fails
- login loop becomes unstable
- the shell degrades in a way that is not cleanly attributable to the bounded
  change

## Variant C2: Constructor-Time Bundle Bypass

Run after Variant C1, which now left the first usable shell intact.

### Goal

Test whether the constructor-time config bundle in
`AlgosecSession::__construct()` is the first broader-bundle gate.

### Candidate Control Points

Remote file:

- `/usr/share/fa/php/AlgosecSession.php`

Candidate lines:

- `RestClient::reloadConfig();`
- `$this->GetConfigurationSettings();`

### Why This Is Second

This is wider and riskier than Variant C1 because it changes the first bundle
load in the login bootstrap path itself.

Use it only after the safer post-login recache variant is reduced.

## What Not To Do

Do not:

- reuse a family-wide Apache deny
- use a host-level owner-based `iptables` block on user `apache`
- mutate both Variant C1 and Variant C2 in the same run

## Current Preferred Next Move

Variant C1 is now complete and reduced:

- skipping `utils::HandleConfigParams($AlgosecSession)` still left
  `/afa/php/home.php` usable
- use `.pack-state/remote-codex/asms-ui-postlogin-handleconfigparams-variant-c1-pass-20260326.md`
  as the canonical result

Current preferred next move:

- Variant C2 is now also complete and reduced:
  - bypassing the constructor-time bundle still left `/afa/php/home.php`
    usable
  - use `.pack-state/remote-codex/asms-ui-constructor-config-bypass-variant-c2-pass-20260326.md`
    as the canonical result

Current preferred next move:

- Variant C3 is now also complete and reduced:
  - suppressing both bootstrap bundle loads still left `/afa/php/home.php`
    usable
  - use `.pack-state/remote-codex/asms-ui-combined-bootstrap-variant-c3-pass-20260326.md`
    as the canonical result

Current preferred next move:

- stop treating the bootstrap bundle as the main first-shell gate candidate
- move the next seam work to later demand-loaded home-shell behavior
