# ASMS UI Apache Proxy Isolation Variant B

Date: 2026-03-25
Target: `ASMS UI is down`
Variant: deny `/afa/api/v1` only
Mutation surface: temporary Apache override file `/etc/httpd/conf.d/zzzz_adf_proxy_isolation.conf`

## Method

- Baseline check: one fresh bounded Chromium login before mutation
- Mutation:
  - temporary Apache override:
    ```apache
    <Location /afa/api/v1>
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

- Fresh session: `PHPSESSID=it0a4q3pqm2mnm09ipngbkmcek`
- Window: `19:49:29` to `19:49:50 -0400`
- Result:
  - final URL `https://127.0.0.1/afa/php/home.php`
  - title `AlgoSec - Home`
  - all normal home-shell markers present

## Mutation Window

- Override applied at `2026-03-25T23:49:56Z`
- Fresh mutated session: `PHPSESSID=jmv796rsrd5gql2586f03l90i6`
- Mutation reproduction window: `19:50:12` to `19:50:32 -0400`

## Mutation Result

- The browser still reached `https://127.0.0.1/afa/php/home.php`.
- The title remained `AlgoSec - Home`.
- All normal home-shell markers were still present.
- Apache showed `403` for some `/afa/api/v1` requests, including:
  - `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW`
  - `GET /afa/api/v1/license`
- But Apache still showed the `/afa/external` family returning `200`, including:
  - `GET /afa/external//config?...`
  - `POST /afa/external//session/extend?...`
  - `POST /afa/external//bridge/storeFireflowCookie?...`
- In the same fresh-session minute, Metro still served:
  - `GET /afa/config/?domain=0&session=jmv796rsrd5gql2586f03l90i6` `200`
  - `GET /afa/api/v1/config?...` `200`
  - `POST /afa/api/v1/session/extend?...` `200`
  - `GET /afa/getStatus` `200`

## Interpretation

- Denying the top-level Apache `<Location /afa/api/v1>` block did not break the first usable ASMS home shell on this lab.
- More importantly, it did not cleanly own the fresh-session `config` and `session/extend` routes we were trying to isolate.
- That means the top-level Apache proxy-family deny is not a precise enough control lever for the real fresh-session config/session path.
- The narrowest remaining unknown is why fresh-session `/afa/api/v1/config?...` and `/afa/api/v1/session/extend?...` still reached Metro as `200` during the deny window.

## Rollback And Recovery

- Rollback completed at `2026-03-25T23:50:56Z`
- Recovery session: `PHPSESSID=v6ep7bpe0mv0rrs26ukmgac76s`
- Recovery window: `19:51:07` to `19:51:27 -0400`
- Result:
  - final URL `https://127.0.0.1/afa/php/home.php`
  - title `AlgoSec - Home`
  - all normal home-shell markers present

## Best Next Step

Move one seam deeper than the top-level Apache proxy-family deny. The best next experiment is a narrower path-specific control around the paired config surfaces, especially `/afa/config/...` and the fresh-session `/afa/api/v1/config?...` and `/afa/api/v1/session/extend?...` routes, instead of another family-wide deny.
