Successful correlation window: `2026-03-26 05:29:53-05:29:56 EDT`.

Observed successful shell transition:
- Apache shows `GET /afa/php/SuiteLoginSessionValidation.php` returning `302` at `05:29:53`, followed by `GET /afa/php/home.php` `200` at `05:29:54`.
- The resulting AFA session is visible immediately after in Apache as `dynamic.js.php?sid=i88p8vb1s79p6nb0f4o2jkpb07` and in Metro as repeated `session=i88p8vb1s79p6nb0f4o2jkpb07`.

Code-path correlation:
- `SuiteLoginSessionValidation.php` validates AFA and FireFlow auth, then redirects default AFA landing traffic to `/afa/php/home.php`.
- `home.php` creates the shell page, sets the session, emits `dynamic.js.php?sid=<session>`, and loads `home.js`.
- `home.js` immediately issues dashboard bootstrap requests and `POST /fa/tree/create`.
- `utils::PrintTopbar()` points the shell to `/AFA/php/TopbarMenu.php`.
- `prod_stat.php` returns product usability state and is shell-adjacent, not the redirect gate itself.

Hard first-shell dependency set from this window:
- `GET /afa/php/SuiteLoginSessionValidation.php` -> `302`
- `GET /afa/php/home.php` -> `200`
- `GET /afa/php/JSlib1768164240/dynamic.js.php?sid=i88p8vb1s79p6nb0f4o2jkpb07`
- `GET /afa/php/JSlib1768164240/home.js`
- `POST /afa/php/commands.php` x2 at `05:29:55`
  These align with `home.js` startup calls for dashboard data (`GET_DASHBOARDS_DATA` for default and all dashboards).
- `POST /fa/tree/create`
  This is the tree bootstrap call issued by `LazyLoadTrees_initialize()`.
- `GET /AFA/php/TopbarMenu.php`
- `GET /afa/php/prod_stat.php`

Correlated Metro requests for the same session window:
- Pre-redirect auth/session-support traffic already exists for the same session and continues through the redirect:
  `storeFireflowCookie`, `config`, `session/extend`, landing-page lookup, `allowedFirewalls`, user lookup.
- Immediately after `home.php`, Metro receives shell data requests carrying the same session:
  `getAllFirewalls`, `device`, `findLatestReportPerDevice`, `monitor/folders`, `deviceInfo/getDeviceSummarizedInfo`, `nameToDevicesCount`, `brandConfig/getByDeviceName`, and repeated `allowedFirewalls`.

Classification of nearby but non-core traffic:
- `GET /FireFlow/SelfService/CheckAuthentication/?login=1` is adjacent suite traffic, not required to enter AFA `home.php`.
- `GET /aff/api/internal/noauth/health/shallow` and `GET /BusinessFlow/shallow_health_check` are periodic health probes and should not be treated as first-shell dependencies.
- Additional static assets under `/algosec-ui/` and `/algosec/suite/` are suite-frame branding and shared shell assets, not the AFA shell gate.

Bottom line:
- The hard transition into the AFA first shell is the `SuiteLoginSessionValidation.php -> home.php` redirect plus the immediate `dynamic.js`, `home.js`, dashboard bootstrap, tree bootstrap, topbar, and product-status requests.
- The Metro calls with `session=i88p8vb1s79p6nb0f4o2jkpb07` are the backend data plane that populates the shell after entry, not the redirect decision itself.
