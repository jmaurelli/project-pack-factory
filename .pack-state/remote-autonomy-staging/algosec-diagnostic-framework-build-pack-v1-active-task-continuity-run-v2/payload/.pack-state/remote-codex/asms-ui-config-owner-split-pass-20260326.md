# ASMS UI Config Owner Split Pass 2026-03-26

## Purpose

Clarify who actually owns the remaining `config` and `session` surfaces after
the family-wide Apache seam experiments closed without breaking the first
usable ASMS home shell.

## Key Evidence

### Apache owns two browser-facing proxy families

From `/etc/httpd/conf.d/zzz_fa.conf`:

- `<Location /afa/external>` proxies to
  `http://localhost:8080/afa/api/v1`
- `<Location /afa/api/v1>` also proxies to
  `http://localhost:8080/afa/api/v1`

This confirms that Apache is the browser-facing owner of both proxy families,
but only at that browser edge.

### PHP also talks directly to Metro

From `/usr/share/fa/php/inc/rest-client.inc.php`:

- `RestClient::getPest()` builds `new PestJSON('http://127.0.0.1:8080/afa')`
- `RestClient::getConfig($param)` calls `GET /config/<param>...` through that
  direct Metro client

This means PHP can generate direct `http://127.0.0.1:8080/afa/config/...`
traffic without Apache owning the request path.

### The login path already uses that direct PHP config helper

From `/usr/share/fa/php/SuiteLoginSessionValidation.php`:

- `checkUsernamesMatch()` calls
  `RestClient::getConfig('Case_Sensitive_Username')`

That is direct evidence that the ASMS login path already depends on a
server-side PHP-to-Metro config read that bypasses the browser proxy seam.

### The browser UI also owns a separate config family

From `/usr/share/fa/suite/client/app/suite-new-ui/main.js`:

- the bundle contains `const Wp="/afa/api/v1/config"`

From `/usr/share/fa/suite/client/report-export.json`:

- `GET /afa/api/v1/config/uiParameters` is mapped to
  `/afa/external/config/uiParameters`

This confirms a separate browser-owned config family alongside the PHP direct
Metro path.

## Interpretation

The remaining ASMS `config` family is split across at least two owners:

1. browser-owned requests through Apache proxy families such as
   `/afa/external/...` and `/afa/api/v1/...`
2. PHP-owned direct Metro requests through `RestClient` to
   `http://127.0.0.1:8080/afa/config/...`

That explains why family-wide Apache denies were still able to leave fresh
`config` evidence inside Metro logs: Apache is no longer the only owner of the
path.

## What Changed In The Model

- The unresolved seam is no longer just an Apache proxy-family question.
- It is now a route-owner split question.
- Future isolation should treat browser-owned config requests and PHP-owned
  direct Metro config reads as different control surfaces.

## Preferred Next Experiment Shape

Prefer this order:

1. a read-only correlation pass that proves which Metro `config` requests have
   no matching Apache access-log parent
2. an exact browser-route isolation pass only for the browser-owned requests
   that can be cleanly intercepted and counted
3. only then a deeper internal seam plan if the remaining uncertainty is
   entirely inside the PHP-to-Metro path

Do not repeat another family-wide Apache deny as the default next move for
this question.
