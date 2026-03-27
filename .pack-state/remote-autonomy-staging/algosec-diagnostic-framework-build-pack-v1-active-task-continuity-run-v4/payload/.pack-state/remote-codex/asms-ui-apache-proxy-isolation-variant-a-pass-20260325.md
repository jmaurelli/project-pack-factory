# ASMS UI Apache Proxy Isolation Variant A

Date: 2026-03-25
Target: `ASMS UI is down`
Variant: deny `/afa/external` only
Mutation surface: temporary Apache override file `/etc/httpd/conf.d/zzzz_adf_proxy_isolation.conf`

## Method

- Baseline check: one fresh bounded Chromium login before mutation
- Mutation:
  - temporary Apache override:
    ```apache
    <Location /afa/external>
      Require all denied
    </Location>
    ```
  - `apachectl -t`
  - `systemctl reload httpd`
- Mutation reproduction: one fresh bounded Chromium login
- Evidence: same-minute Apache and Metro log correlation
- Rollback:
  - remove override file
  - `apachectl -t`
  - `systemctl reload httpd`
- Recovery check: one fresh bounded Chromium login after rollback

## Baseline

- Fresh session: `PHPSESSID=o1pknjhf1ikr0ul965alvnv94f`
- Window: `19:40:31` to `19:40:52 -0400`
- Result:
  - final URL `https://127.0.0.1/afa/php/home.php`
  - title `AlgoSec - Home`
  - all normal home-shell markers present

## Mutation Window

- Override applied at `2026-03-25T23:41:03Z`
- Fresh mutated session: `PHPSESSID=tv42f5qv45d3vugtfh1ba6a7pv`
- Mutation reproduction window: `19:41:17` to `19:41:37 -0400`

## Mutation Result

- The browser still reached `https://127.0.0.1/afa/php/home.php`.
- The title remained `AlgoSec - Home`.
- All normal home-shell markers were still present.
- Apache showed repeated `403` responses for the denied `/afa/external` family, including:
  - `GET /afa/external//config/all/noauth?domain=0`
  - `GET /afa/external//config?...`
  - `POST /afa/external//session/extend?...`
  - `POST /afa/external//bridge/storeFireflowCookie?...`
- Apache still served `GET /afa/php/home.php` with `200`.
- Metro still served same-minute config-family and shell-follow-up traffic, including:
  - `GET /afa/config/?domain=0&session=tv42f5qv45d3vugtfh1ba6a7pv` `200`
  - `GET /afa/config/FIREFLOW_ADDRESS?...` `200`
  - `GET /afa/getStatus` `200`
  - multiple later authenticated `/afa/...` requests `200`

## Interpretation

- Denying `/afa/external` alone does not break the first usable ASMS home shell on this lab.
- That demotes `/afa/external` as a first-shell gate candidate.
- The stronger remaining seam is `/afa/api/v1` or a deeper Metro-side surface behind it.

## Rollback And Recovery

- Rollback completed at `2026-03-25T23:41:55Z`
- Recovery session: `PHPSESSID=84p9hd3jlhgra4v72pnvp2dovq`
- Recovery window: `19:42:09` to `19:42:30 -0400`
- Result:
  - final URL `https://127.0.0.1/afa/php/home.php`
  - title `AlgoSec - Home`
  - all normal home-shell markers present

## Best Next Step

Run Variant B against `/afa/api/v1` with the same temporary Apache override pattern, one bounded fresh login, same-minute log correlation, and immediate rollback.
