# ASMS UI Login Bootstrap Control-Path Pass 2026-03-26

## Purpose

Identify whether the broader `GetConfigurationSettings()` seam should be
tested at `home.php`, at session bootstrap, or at another application hook.

## Key Evidence

### `home.php` mostly consumes an existing session object

From `/usr/share/fa/php/home.php`:

- `home.php` calls `utils::SetSession()`
- `utils::SetSession()` returns the existing `$_SESSION['AlgosecSession']`
  when the PHP session is already active and the session directory still
  exists

That means `home.php` is not the clean first control point for the broader
bundle. It mostly consumes an already-built session object.

### The broader config bundle is loaded during login bootstrap

From `/usr/share/fa/php/AlgosecSessionManager.php`:

- `executeLogin()` starts a PHP session
- `executeLogin()` constructs `new AlgosecSession(...)`
- `postLoginActions()` then stores the object in `$_SESSION`
- `postLoginActions()` immediately calls `utils::HandleConfigParams()`

From `/usr/share/fa/php/AlgosecSession.php`:

- `AlgosecSession::__construct()` calls `RestClient::reloadConfig()`
- `AlgosecSession::__construct()` calls `$this->GetConfigurationSettings()`

From `/usr/share/fa/php/utils.php`:

- `HandleConfigParams()` calls `$AlgosecSession->GetConfigurationSettings()`

So the broad bundle is loaded twice on the bootstrap path:

1. inside `AlgosecSession::__construct()`
2. again inside `postLoginActions()` via `HandleConfigParams()`

### `RestClient::getAllConfig()` is the direct PHP-to-Metro hook

From `/usr/share/fa/php/inc/rest-client.inc.php`:

- `RestClient::getAllConfig()` delegates to `RestClient::getConfig(NULL)`
- `RestClient::getConfig()` uses `PestJSON('http://127.0.0.1:8080/afa')`
- that path issues direct `/afa/config/...` requests to Metro

This confirms that an application-level hook can isolate the internal seam
without touching Apache proxy traffic.

## Interpretation

The broad config-bundle seam should be tested at login bootstrap, not at
`home.php`.

The lowest-risk first app-level mutation is not a global transport block.
It is a bounded bootstrap hook:

- first candidate: temporarily skip `utils::HandleConfigParams($AlgosecSession)`
  in `AlgosecSessionManager::postLoginActions()`
- second candidate only if needed: temporarily bypass the constructor-time
  `RestClient::reloadConfig()` / `GetConfigurationSettings()` path inside
  `AlgosecSession::__construct()`

## Why The First Candidate Is Better

Skipping `HandleConfigParams()` is narrower than breaking `getAllConfig()`
globally.

It lets us ask a useful first question:

- does the first usable shell depend on the post-login config recache path,
  or is the constructor-time bundle already enough?

It is also easy to roll back because it is a one-line application hook in one
file.

## Recommended Next Move

Use `AlgosecSessionManager::postLoginActions()` as the first broader-bundle
experiment seam.

If skipping `HandleConfigParams()` still leaves `/afa/php/home.php` usable,
demote the post-login recache path and then plan the deeper constructor-time
bundle experiment separately.
