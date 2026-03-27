Recent failed shell-transition candidate: `25/Mar/2026 12:56:01 EDT` in `/var/log/httpd/ssl_access_log`.

Baseline used for comparison:
- Successful sequence on `26/Mar/2026 05:29:53-05:29:56 EDT` for session `i88p8vb1s79p6nb0f4o2jkpb07`.
- Apache shows `GET /afa/php/SuiteLoginSessionValidation.php` at line 72874 returning `302`, then `GET /afa/php/home.php` at line 72922 returning `200`, followed by shell bootstrap requests:
  `dynamic.js.php`, `home.js`, `TopbarMenu.php`, `prod_stat.php`.
- Metro confirms the same session is active and serving AFA APIs during `05:29:50-05:29:56 EDT`.

Failed candidate:
- Apache line 16738 on `25/Mar/2026 12:56:01 EDT` shows `GET /AFA/php/SuiteLoginSessionValidation.php` returning `302`.
- Relative to the successful baseline, the first missing request is `GET /afa/php/home.php`.
- Instead of `home.php`, Apache later serves `GET /algosec-ui/login` at `12:56:12 EDT` and `GET /algosec-ui/login?last_url=%2FAFA%2Fphp%2FSuiteLoginSessionValidation.php` at `12:56:19 EDT` (lines 16747-16750).
- No `home.php`, `dynamic.js.php`, `home.js`, `TopbarMenu.php`, or `prod_stat.php` requests follow this failed SuiteLoginSessionValidation transition.

Relevant code path:
- `/usr/share/fa/php/SuiteLoginSessionValidation.php` redirects to `/algosec-ui/login` when `redirectOrRespond()` is invoked without a target.
- That happens when no usable authenticated context is found, including:
  empty AFA and FireFlow cookies,
  empty username after auth checks,
  failed AFA auth when the user is not a valid FireFlow-only requestor.

Interpretation:
- The failure is earlier than shell bootstrap; it is not a degraded `home.php` load.
- The first divergence from the good baseline is that SuiteLoginSessionValidation does not produce the redirect chain that results in `home.php`.
- The observed outcome is consistent with authentication context being absent or rejected before landing-page resolution.

Artifacts:
- `artifacts/baseline-apache-window.txt`
- `artifacts/baseline-metro-window.txt`
- `artifacts/failure-apache-window.txt`
- `artifacts/SuiteLoginSessionValidation-head.php.txt`
