# ASMS UI GetConfiguration Control Surface Pass 2026-03-26

## Purpose

Check whether the broader `AlgosecSession::__construct()` /
`GetConfigurationSettings()` config-bundle seam has a clean first mutation
surface.

## Key Evidence

### The broad config bundle is on the hot login/session path

From `/usr/share/fa/php/AlgosecSession.php:304-335`:

- `AlgosecSession::__construct()` does:
  - `RestClient::reloadConfig()`
  - `$this->GetConfigurationSettings()`
  - then applies `Case_Sensitive_Username`

That places the broad config-bundle load directly in the login/session
bootstrap path before later shell behavior.

### The config bundle is reused again after login

From `/usr/share/fa/php/utils.php:2482-2491`:

- `HandleConfigParams(&$AlgosecSession)` calls
  `GetConfigurationSettings()` again

From `/usr/share/fa/php/AlgosecSessionManager.php:58-69`:

- `postLoginActions()` calls `utils::HandleConfigParams($AlgosecSession)`

So the broad bundle is not just a one-time constructor detail. It is also
reloaded during post-login session setup.

### The obvious network-level block is too coarse

Observed runtime users:

- `httpd` master runs as `root`
- worker processes run as `apache`
- `ms-metro` runs as `afa`
- Metro listens on `0.0.0.0:8080`

This means a host-level owner-based rule such as an `iptables` OUTPUT block for
user `apache` to `127.0.0.1:8080` would not isolate only the direct PHP config
bundle.

It would also risk blocking browser-facing Apache proxy traffic because that
proxy traffic is also emitted from `httpd` worker processes under the same
`apache` user.

## Interpretation

The broader `GetConfigurationSettings()` bundle is now the right unresolved
internal seam, but the first obvious control point is not clean enough.

The seam is real.
The current mutation surface is not yet precise enough.

## What This Changes

Do not execute an owner-based `iptables` block as the first broader-config
experiment.

That would mix:

- browser-facing proxy traffic
- direct PHP-to-Metro config-bundle traffic

and would make the result harder to interpret.

## Recommended Next Move

Plan a more precise app-level or Metro-side control point for the broad
config-bundle seam before mutating anything.

Good next questions:

- is there a narrower application-level hook around `GetConfigurationSettings()`
  or `RestClient::getAllConfig()`?
- is there a Metro-side config endpoint behavior that can be changed temporarily
  without breaking every Apache-mediated route at once?
- can the broad bundle be reduced into one or two higher-value config-family
  reads inside the constructor or post-login setup instead of mutating the
  whole bundle at once?
