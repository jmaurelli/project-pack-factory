# ASMS UI Config Correlation Pass 2026-03-26

## Purpose

Run one bounded fresh-session correlation pass to prove which same-minute Metro
`config` and `session` requests still have Apache parents and which do not.

## Method

- staged ADF pack on the lab appliance
- guided remote Codex run
- Playwright Python with system Chromium at `/usr/bin/chromium-browser`
- bounded waits only, no `networkidle`
- authenticated login with `admin`
- same-minute Apache and Metro log correlation by fresh `PHPSESSID`

## Fresh Session Result

- `PHPSESSID = jkp0cnnf971ksgifu3k25jopiq`
- browser result file was written to `/tmp/adf_route_correlation_result.txt`
- browser-visible result was mixed:
  - final browser URL stayed `https://127.0.0.1/algosec-ui/login`
  - page title was `AlgoSec - Home`
  - visible marker capture was empty
- browser-side event capture still undercounted the real same-minute traffic
  and recorded only:
  - `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` -> `401`
  - `GET /afa/php/home.php` -> `200`

That undercount matches the earlier warning that browser-only capture is not
enough to explain the real same-minute Metro path.

## Apache Parent Lines

For the fresh session minute, Apache recorded:

- `GET /afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` -> `401`
- `GET /afa/external//config/all/noauth?domain=0` -> `200`
- repeated `GET /afa/external//config?session=jkp0cnnf971ksgifu3k25jopiq...`
- repeated `POST /afa/external//session/extend?...session=jkp0cnnf971ksgifu3k25jopiq...`
- `GET /afa/php/home.php` -> `200`

## Metro Lines With And Without Apache Parents

Metro recorded these browser-backed routes with matching Apache parents:

- `GET /afa/api/v1/config/all/noauth?domain=0`
  parent: Apache `/afa/external//config/all/noauth`
- repeated `GET /afa/api/v1/config?session=jkp0cnnf971ksgifu3k25jopiq...`
  parent: Apache `/afa/external//config?...`
- `POST /afa/api/v1/session/extend?domain=0&session=jkp0cnnf971ksgifu3k25jopiq`
  parent: Apache `/afa/external//session/extend?...`

Metro also recorded these same-minute routes without matching Apache parents:

- `DELETE /afa/config/?`
- `GET /afa/config/?`
- repeated `GET /afa/config/?domain=0&session=jkp0cnnf971ksgifu3k25jopiq`
- repeated `GET /afa/getStatus`

## Classification

The ownership split is now explicit:

- browser-facing proxy path:
  - Apache `/afa/external/...`
  - Metro `/afa/api/v1/...`
- internal direct Metro path with no Apache parent:
  - `/afa/config/...`
  - `/afa/getStatus`

So the remaining unresolved `config` seam is no longer mainly browser-owned.
It is now mostly the internal PHP-to-Metro direct `/afa/config/...` family,
with `/afa/getStatus` staying as a separate same-minute internal supporting
clue.

## Operational Meaning

- another family-wide Apache mutation would mostly repeat solved ground
- another browser-only capture pass would still undercount the internal path
- the next truly new seam is the direct `/afa/config/...` family behind PHP
  `RestClient`

## Recommended Next Move

Plan a separate bounded internal seam experiment for the direct
PHP-to-Metro `/afa/config/...` path, with its own control point, rollback, and
risk review, instead of repeating a browser-proxy mutation.

One launcher note also became explicit during this pass:

- remote Codex can use Playwright Python plus the system Chromium binary even
  when Playwright's bundled browser cache is missing
