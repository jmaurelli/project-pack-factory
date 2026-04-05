# ASMS UI Combined Bootstrap Variant C3 Pass 2026-03-26

## Purpose

Run the first combined bootstrap experiment by suppressing both:

- the constructor-time config bundle in `AlgosecSession::__construct()`
- the post-login `HandleConfigParams()` recache in
  `AlgosecSessionManager::postLoginActions()`

## Mutation

Remote files:

- `/usr/share/fa/php/AlgosecSession.php`
- `/usr/share/fa/php/AlgosecSessionManager.php`

Temporary changes:

- in `AlgosecSession.php`, replaced:
  - `RestClient::reloadConfig();`
  - `$this->GetConfigurationSettings();`
- with:
  - a temporary ADF marker log line
  - a minimal seed:
    `array('System_Users' => $userName)`

- in `AlgosecSessionManager.php`, replaced:
  - `utils::HandleConfigParams($AlgosecSession);`
- with:
  - a temporary ADF marker log line

Safety checks:

- `php -l` passed for both files after mutation
- both original files were restored automatically on exit
- `php -l` passed for both files again after rollback

## Browser Result

Fresh headless Chromium login result:

- completed at `2026-03-26T08:59:20Z`
- final URL: `https://127.0.0.1/afa/php/home.php`
- title: `AlgoSec - Home`
- `PHPSESSID`: `vq6d70hh7m9u6a4ssk0ad9sojp`

Observed browser-visible events:

- `GET /algosec-ui/login` `200`
- `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` `401`
- `GET /algosec-ui/login` `200`
- `GET /afa/php/home.php` `200`

Body markers still showed the shell as meaningfully present:

- `Firewall Analyzer`: present

## Same-Minute Apache Evidence

From `/tmp/adf_variant_c3_apache_20260326T085836Z.log`:

- `GET /algosec-ui/login` `200`
- repeated `/afa/external//config?...session=vq6d70hh7m9u6a4ssk0ad9sojp` `200`
- repeated `/afa/external//session/extend?...session=vq6d70hh7m9u6a4ssk0ad9sojp`
  `200`
- `GET /afa/php/home.php` `200`
- `GET /afa/php/JSlib.../dynamic.js.php?sid=vq6d70hh7m9u6a4ssk0ad9sojp`
  `200`

## Same-Minute Metro Evidence

From `/tmp/adf_variant_c3_metro_20260326T085836Z.log`:

- `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` `401`
- `GET /afa/api/v1/config/all/noauth?domain=0` `200`

Important absence in the captured grep surface:

- no direct Metro lines in the captured tail matched the fresh session
  `vq6d70hh7m9u6a4ssk0ad9sojp`
- no matched fresh-session lines appeared for:
  - `/afa/config?...session=vq6d...`
  - `/afa/api/v1/config?...session=vq6d...`
  - `/afa/api/v1/session/extend?...session=vq6d...`

## Interpretation

Even with both bootstrap bundle loads suppressed, the first usable ASMS shell
still rendered.

This strongly demotes the bootstrap-bundle hypothesis as the first-shell gate.

The better current inference is:

- the first customer-visible shell is more resilient than the bootstrap model
  suggested
- the real first-shell gate is more likely in later demand-loaded behavior,
  post-home shell use, or another route family that still survives these
  bootstrap suppressions

## Recommended Next Move

Stop treating the bootstrap config bundle as the primary first-shell gate
candidate.

Shift the next seam work toward later demand-loaded behavior, especially:

- what `dynamic.js.php?sid=...` and immediate home-shell JS need next
- whether `/afa/external//config...` is still owned by a later surviving path
- which first interactive home-shell action is the earliest one that truly
  fails when config-family traffic is reduced
