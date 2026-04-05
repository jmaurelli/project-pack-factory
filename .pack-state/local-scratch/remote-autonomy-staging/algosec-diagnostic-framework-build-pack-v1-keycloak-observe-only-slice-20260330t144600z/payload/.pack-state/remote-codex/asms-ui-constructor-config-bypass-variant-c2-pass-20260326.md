# ASMS UI Constructor Config Bypass Variant C2 Pass 2026-03-26

## Purpose

Run the second bounded bootstrap experiment by bypassing the constructor-time
config bundle in `AlgosecSession::__construct()` while leaving the later
post-login recache path intact.

## Mutation

Remote file:

- `/usr/share/fa/php/AlgosecSession.php`

Temporary change:

- replaced:
  - `RestClient::reloadConfig();`
  - `$this->GetConfigurationSettings();`
- with:
  - a temporary ADF marker log line
  - a minimal seed:
    `array('System_Users' => $userName)`

Why the seed was needed:

- it avoids turning the experiment into a pure undefined-variable failure at
  the `System_Users` check
- it keeps the question focused on the broader constructor-time bundle rather
  than on a trivial local variable hazard

Safety checks:

- `php -l /usr/share/fa/php/AlgosecSession.php` passed after mutation
- the original file was restored automatically on exit
- `php -l /usr/share/fa/php/AlgosecSession.php` passed again after rollback

## Browser Result

Fresh headless Chromium login result:

- completed at `2026-03-26T01:05:52Z`
- final URL: `https://127.0.0.1/afa/php/home.php`
- title: `AlgoSec - Home`
- `PHPSESSID`: `2njhgubafhl5stdv54fb19vsn4`

Observed browser-visible events:

- `GET /algosec-ui/login` `200`
- `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` `401`
- `GET /algosec-ui/login` `200`
- `GET /afa/php/home.php` `200`

Body markers still showed the shell as meaningfully present:

- `Firewall Analyzer`: present

## Same-Minute Apache Evidence

From `/tmp/adf_variant_c2_apache_20260326T010458Z.log`:

- `GET /algosec-ui/login` `200`
- repeated `/afa/external//config?...session=2njhgubafhl5stdv54fb19vsn4` `200`
- repeated `/afa/external//session/extend?...session=2njhgubafhl5stdv54fb19vsn4` `200`
- `GET /afa/php/home.php` `200`
- `GET /afa/php/JSlib.../dynamic.js.php?sid=2njhgubafhl5stdv54fb19vsn4` `200`

## Same-Minute Metro Evidence

From `/tmp/adf_variant_c2_metro_20260326T010458Z.log`:

- `GET /afa/config/?domain=0&session=2njhgubafhl5stdv54fb19vsn4` `200`
- `POST /afa/password/decrypt?domain=0&session=2njhgubafhl5stdv54fb19vsn4`
  `200`
- `POST /afa/api/v1/bridge/storeFireflowCookie?...session=2njhg...` `200`
- repeated `GET /afa/api/v1/config?...session=2njhg...` `200`
- repeated `POST /afa/api/v1/session/extend?...session=2njhg...` `200`
- `GET /afa/config/FIREFLOW_ADDRESS?...session=2njhg...` `200`
- `GET /afa/config/Case_Sensitive_Username?...session=2njhg...` `404`
- `GET /afa/UsersInfo/landing_page/admin?...session=2njhg...` `200`
- `GET /afa/UsersInfo/allowedFirewalls/admin?...session=2njhg...` `200`

## Interpretation

Bypassing the constructor-time bundle did **not** stop the first usable ASMS
shell.

This means the constructor-time bundle is also not the sole first-shell gate,
at least while the later post-login recache path is still intact.

The strongest new inference is:

- neither bootstrap half by itself appears to be the sole gate
- the shell may depend on the combined effect of:
  - constructor-time bundle load
  - post-login `HandleConfigParams()` recache
- or on later config reads that still happen after either single bypass

## Recommended Next Move

Plan Variant C3 as the next bounded bootstrap experiment:

- suppress the constructor-time bundle
- suppress the post-login `HandleConfigParams()` recache
- reproduce one fresh login
- roll back immediately

That is now the cleanest next way to test whether the first usable shell only
breaks when both bootstrap bundle loads are removed together.
