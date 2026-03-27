# ASMS UI Post-Login HandleConfigParams Variant C1 Pass 2026-03-26

## Purpose

Run the first bounded application-level bootstrap experiment by skipping
`utils::HandleConfigParams($AlgosecSession)` inside
`AlgosecSessionManager::postLoginActions()`.

## Mutation

Remote file:

- `/usr/share/fa/php/AlgosecSessionManager.php`

Temporary change:

- replaced `utils::HandleConfigParams($AlgosecSession);`
- with a temporary no-op log marker for the bounded experiment

Safety checks:

- `php -l /usr/share/fa/php/AlgosecSessionManager.php` passed after mutation
- the original file was restored automatically on exit
- `php -l /usr/share/fa/php/AlgosecSessionManager.php` passed again after
  rollback

## Browser Result

Fresh headless Chromium login result:

- completed at `2026-03-26T01:01:46Z`
- final URL: `https://127.0.0.1/afa/php/home.php`
- title: `AlgoSec - Home`
- `PHPSESSID`: `cj2kbi2g8kfqcj0i7an1pheor2`

Observed browser-visible events:

- `GET /algosec-ui/login` `200`
- `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` `401`
- `GET /algosec-ui/login` `200`
- `GET /afa/php/home.php` `200`

Body markers still showed the shell as meaningfully present:

- `Firewall Analyzer`: present

## Same-Minute Apache Evidence

From `/tmp/adf_variant_c1_apache_20260326T010107Z.log`:

- `GET /algosec-ui/login` `200`
- repeated `/afa/external//config?...session=cj2kbi2g8kfqcj0i7an1pheor2` `200`
- repeated `/afa/external//session/extend?...session=cj2kbi2g8kfqcj0i7an1pheor2` `200`
- `GET /afa/php/home.php` `200`
- `GET /afa/php/JSlib.../dynamic.js.php?sid=cj2kbi2g8kfqcj0i7an1pheor2` `200`

## Same-Minute Metro Evidence

From `/tmp/adf_variant_c1_metro_20260326T010107Z.log`:

- `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` `401`
- `GET /afa/api/v1/config/all/noauth?domain=0` `200`
- `DELETE /afa/config/?` `204`
- `GET /afa/config/?` `200`
- `GET /afa/getStatus` `200`

Important absence:

- no direct Metro lines in the captured tail matched the fresh session
  `cj2kbi2g8kfqcj0i7an1pheor2`

## Interpretation

Skipping the post-login `HandleConfigParams()` recache path did **not** stop the
first usable ASMS shell.

This demotes `postLoginActions()` / `HandleConfigParams()` as a first-shell
gate candidate.

The broader bootstrap seam is still real, but the stronger remaining candidate
is now the constructor-time bundle in `AlgosecSession::__construct()`:

- `RestClient::reloadConfig()`
- `$this->GetConfigurationSettings()`

## Recommended Next Move

Treat Variant C1 as reduced and plan Variant C2 next:

- temporarily bypass the constructor-time bundle
- reproduce one fresh login
- capture the exact same-minute Apache and Metro evidence
- roll back immediately
