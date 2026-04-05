# ASMS UI Metro Home-Shell Essentiality Pass

Date: 2026-03-25
Path constraint: stay on `ASMS UI is down`
Method: read-only pack review, authenticated Playwright reproduction against `https://127.0.0.1/algosec-ui/login`, bounded one-at-a-time route-family comparisons, same-minute Apache and Metro log correlation

## Observed facts

- I read `status/work-state.json`, `status/readiness.json`, and the ASMS Step 4 section in `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py` before the live pass.
- Playwright used the installed Chromium at `/usr/bin/chromium-browser` with the provided `ADF_GUI_USER` and `ADF_GUI_PASS` environment variables.
- In repeated authenticated runs, the browser reached `https://127.0.0.1/afa/php/home.php` with title `AlgoSec - Home`.
- The first clearly usable shell showed normal top-level text such as `HOME`, `DEVICES`, `DASHBOARDS`, `GROUPS`, `MATRICES`, `Firewall Analyzer`, `FireFlow`, `AlgoSec Cloud`, `ObjectFlow`, and `AppViz`.
- No obvious error banners or blocking overlays were visible on the initial usable shell in the baseline or comparison runs.
- Console/page noise did exist during successful runs:
  - console: `Failed to load resource: the server responded with a status of 401 ()`
  - page error: `Cannot set properties of undefined (setting 'fnAFAreloadTable')`
  These did not stop the first usable home shell.
- Browser-observed immediate post-home requests were only:
  - `GET /afa/php/home.php`
  - `GET /afa/php/JSlib1768164240/FireFlowBridge.js`
  - `GET /afa/php/logo.php`
- In the repeated same-minute Apache pattern for fresh logins, the observed order was:
  - `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` -> `401`
  - `GET /afa/api/v1/license` -> `200`
  - `GET /afa/php/home.php` -> `200`
  - `GET /afa/php/JSlib1768164240/FireFlowBridge.js` -> `200`
  - `GET /afa/php/logo.php` -> `200`
- In the repeated same-minute Metro pattern around those fresh logins, fresh session ids changed per login and showed:
  - `POST /afa/api/v1/session/extend?...` before `home.php`
  - `GET /afa/api/v1/config?...` before and just after `home.php`
  - `GET /afa/api/v1/config/all/noauth?domain=0` before `home.php`
  - `GET /afa/api/v1/license` about 1 second before `home.php`
  - `GET /afa/getStatus` after `home.php`, then repeating roughly every 10 seconds
- `POST /afa/api/v1/bridge/refresh?...` did appear in Metro logs in the same minutes, but it kept using the long-lived session `kk4msqvndoc0c8lmjka8i93vj4` instead of the fresh post-login session ids from the current reproduced logins. That makes it look like nearby background traffic, not the fresh home-shell gate.
- `ms-watchdog` issue-count traffic was present elsewhere in the minute, but this pass did not produce evidence that it blocks the first customer-visible ASMS home shell.

## What is proven required for initial home-shell usability

- A successful `GET /afa/php/home.php` render remains the strongest proven first-class post-login signal for the first usable ASMS home shell.
- `FireFlowBridge.js` and `logo.php` are immediate same-shell follow-ups, but the usable shell already exists when they arrive.
- `GET /afa/getStatus` is not proven required for the first usable shell because the shell was already visible before any browser-observed Metro heartbeat request, and Metro log timing placed `getStatus` after `home.php`.
- `POST /afa/api/v1/bridge/refresh` is not proven required for the first usable shell because the same-minute Metro hits were tied to a different long-lived session than the fresh login session.

## What is not yet proven required

- `GET /afa/api/v1/license`
- `GET /afa/api/v1/config?...`
- `GET /afa/api/v1/config/all/noauth?domain=0`
- `POST /afa/api/v1/session/extend?...`
- `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` should especially stay unproven; it was a repeated `401` and did not stop successful login-to-home runs.

Reason: those routes were visible in Apache and Metro logs around the fresh login minute, but in this Playwright pass they did not surface as interceptable page-level requests, so this pass could not prove that blocking them changes the first usable shell.

## What should remain a supporting clue vs a first-class gate

- Keep `/afa/getStatus` as the strongest Metro/home-refresh supporting clue for the first minute after home render.
- Keep `/afa/api/v1/bridge/refresh` as a nearby Metro clue only. Do not promote it to a first-class gate from this pass.
- Keep `/afa/api/v1/license`, `/afa/api/v1/config?...`, `/afa/api/v1/config/all/noauth`, and `/afa/api/v1/session/extend` as supporting same-minute clues until a reproduction can truly block or isolate them per fresh session.
- Keep Notification Center and watchdog-linked issue counts as supporting clues, not first-class gates, because this pass did not show that they block the initial customer-visible home shell.

## Single best next investigation step

- Run one more authenticated reproduction with fresh-session isolation at the proxy/log level so each Metro request can be tied to the exact new login session id, then selectively suppress `license` and `config` for that same fresh session only. That is the cleanest next step to prove whether either route is a real first-shell gate or only a nearby supporting request.
