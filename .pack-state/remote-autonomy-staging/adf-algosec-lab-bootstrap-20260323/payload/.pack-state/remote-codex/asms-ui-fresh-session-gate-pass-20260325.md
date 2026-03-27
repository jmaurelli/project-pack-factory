# ASMS UI Fresh-Session Gate Pass

Date: 2026-03-25
Path constraint: stay on `ASMS UI is down`
Method: read-only pack review, two fresh Chromium incognito-context logins to `https://127.0.0.1/algosec-ui/login`, bounded waits only, visible-shell checks, exact fresh-session Apache and Metro correlation

## Observed facts

- I read `status/work-state.json`, `status/readiness.json`, `.pack-state/remote-codex/asms-ui-metro-home-shell-essentiality-pass-20260325.md`, and `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py` first.
- Fresh login 1 started at `25/Mar/2026:18:44:32 -0400` and reached `https://127.0.0.1/afa/php/home.php` with title `AlgoSec - Home`.
- Fresh login 1 showed the expected first usable shell markers: `HOME`, `DEVICES`, `DASHBOARDS`, `GROUPS`, `MATRICES`, `Firewall Analyzer`, `FireFlow`, `AlgoSec Cloud`, `ObjectFlow`, and `AppViz`.
- Fresh login 1 created a new `PHPSESSID` cookie: `9eufggf8sif6n3o59nrfeo9fhl`.
- In browser-captured requests for fresh login 1, the only relevant post-login requests that surfaced directly were:
  - `GET /afa/php/home.php`
  - `GET /afa/php/JSlib1768164240/FireFlowBridge.js`
  - `GET /afa/php/logo.php`
- Same-minute Apache and Metro lines for that exact fresh session showed:
  - `GET /afa/api/v1/config/all/noauth?domain=0` at `18:44:36`
  - `GET /afa/api/v1/config?session=9eufggf8sif6n3o59nrfeo9fhl&domain=0` at `18:44:40`
  - `POST /afa/api/v1/session/extend?...session=9eufggf8sif6n3o59nrfeo9fhl...` at `18:44:41` and `18:44:43`
  - `GET /afa/api/v1/license` at `18:44:42`
  - `GET /afa/php/home.php` at `18:44:44`
  - `GET /afa/getStatus` at `18:44:43` and `18:44:44`
- Fresh login 2 started at `25/Mar/2026:18:45:29 -0400` and also reached a normal `AlgoSec - Home` shell with the same visible markers.
- Fresh login 2 created a new `PHPSESSID` cookie: `rdu8ohak643q4ps6398214nf0s`.
- In fresh login 2, Playwright `context.route('**/*')` was set to abort:
  - `GET /afa/api/v1/license`
  - `GET /afa/api/v1/config?...`
  - `GET /afa/api/v1/config/all/noauth?...`
  - `POST /afa/api/v1/session/extend?...`
- That abort probe recorded `route_abort_count: 0` and still reached `GET /afa/php/home.php` with a usable shell.
- Same-minute Metro lines for fresh login 2 still showed the new session owning:
  - `GET /afa/api/v1/config?session=rdu8ohak643q4ps6398214nf0s...` at `18:45:37`, `18:45:38`, and `18:45:41`
  - `POST /afa/api/v1/session/extend?...session=rdu8ohak643q4ps6398214nf0s...` at `18:45:38` and `18:45:40`
  - `GET /afa/api/v1/license` at `18:45:39`
  - `GET /afa/getStatus` at `18:45:43` and `18:45:44`
  - `GET /afa/php/home.php` at `18:45:41`
- `POST /afa/api/v1/bridge/refresh?...` still stayed tied to the long-lived session `kk4msqvndoc0c8lmjka8i93vj4`, not either reproduced fresh login session.

## What is proven required vs not yet proven

- Proven required: a successful `GET /afa/php/home.php` render remains the strongest first-class post-login checkpoint for the first usable ASMS home shell.
- Not yet proven required: `GET /afa/api/v1/license`, `GET /afa/api/v1/config?...`, `GET /afa/api/v1/config/all/noauth?domain=0`, and `POST /afa/api/v1/session/extend?...`.
- Reason: those routes were present in the exact fresh-session minute, and `config` plus `session/extend` were clearly tied to the new `PHPSESSID`, but this pass still could not make the browser own or suppress them at the Playwright route layer. Their presence is proven; their first-shell gate status is still unproven.

## Status change for the named routes

- `GET /afa/api/v1/license`: no status change; remains a same-minute supporting clue, not a proven first-shell gate.
- `GET /afa/api/v1/config?...`: no status change; stronger fresh-session tie is now observed, but first-shell essentiality is still unproven.
- `GET /afa/api/v1/config/all/noauth?domain=0`: no status change; remains a pre-home supporting clue, not a proven gate.
- `POST /afa/api/v1/session/extend?...`: no status change; stronger fresh-session tie is now observed, but first-shell essentiality is still unproven.

## Immediate supporting clue status

- `GET /afa/getStatus` remains the strongest immediate Metro supporting clue after the first usable shell appears. In both exact fresh-session minutes it appeared after `home.php` was already rendered or in the same immediate second after the shell became usable.

## Single best next investigation step

- Isolate the exact fresh login session one layer lower than Playwright, then selectively suppress `license` and `config` family traffic for that one fresh session at the proxy or server-observation layer. This pass proved those routes belong to the fresh-session minute, but it did not yet prove that removing them changes the first usable `home.php` shell.
