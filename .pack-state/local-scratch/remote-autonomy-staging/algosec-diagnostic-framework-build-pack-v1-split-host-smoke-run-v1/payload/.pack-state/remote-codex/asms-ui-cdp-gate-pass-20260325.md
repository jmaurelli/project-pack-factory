# ASMS UI CDP Gate Pass

Date: 2026-03-25
Path constraint: stay on `ASMS UI is down`
Method: fresh Chromium incognito context with Playwright Python sync API, page-scoped CDP session via `context.new_cdp_session(page)`, `Network.enable`, `Network.setBlockedURLs(...)`, bounded waits only, same-minute Apache and Metro correlation by fresh `PHPSESSID`

## Observed facts

- The browser still reached `https://127.0.0.1/afa/php/home.php` with title `AlgoSec - Home`.
- The normal home-shell markers were still present: `HOME`, `DEVICES`, `DASHBOARDS`, `GROUPS`, `MATRICES`, `Firewall Analyzer`, `FireFlow`, `AlgoSec Cloud`, `ObjectFlow`, and `AppViz`.
- The fresh session cookie was `PHPSESSID=cviqe976klg8krkb5lfdjtkugd`.
- The CDP block rules matched only one early request: `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW`.
- The CDP pass recorded `blocked_count: 0`, so it did not actually own the real fresh-session `license`, `config`, `config/all/noauth`, or `session/extend` traffic.
- Same-minute Metro lines for the fresh session still showed:
  - `GET /afa/api/v1/config/all/noauth?domain=0`
  - `GET /afa/api/v1/config?session=cviqe976klg8krkb5lfdjtkugd&domain=0`
  - `POST /afa/api/v1/session/extend?domain=0&session=cviqe976klg8krkb5lfdjtkugd`
  - `GET /afa/api/v1/license`
  - `GET /afa/getStatus`

## What changed in the model

- `/afa/php/home.php` stays the strongest first-class usable-shell checkpoint.
- `GET /afa/getStatus` stays the strongest immediate Metro supporting clue after the first usable shell appears.
- `config`, `session/extend`, `license`, and `config/all/noauth` remain supporting same-minute clues rather than proven first-shell gates.
- The lower browser-network layer is not yet a reliable control point for those fresh-session routes on this lab, so another browser-side blocking pass is unlikely to reduce ambiguity much by itself.

## Best next step

Use proxy-side or server-side isolation for the fresh-session Metro routes, or another server-observation method that can prove whether suppressing `config` or `session/extend` changes initial ASMS home-shell usability.
