# Frontline trial validation

Classification: external path or browser-side issue.

Shallow validation on the appliance shows the local UI edge is up and serving expected entry points:
- Host is up and stable (`uptime` 20 days) on Rocky Linux 8.10.
- `httpd` is `active` and `enabled`.
- `algosec-ms` is `active` and `enabled`.
- Listeners are present on `80`, `443`, `8080`, and `8443`.
- `http://localhost/` returns `302` to `https://localhost/`.
- `https://localhost/` returns `200` and redirects via HTML refresh to `/algosec/`.
- `https://localhost/algosec/` returns `200` and redirects via HTML refresh to `data/index.php`.
- `https://localhost/algosec-ui/login` returns `200` and serves the Angular login shell.
- `apachectl -t` ends with `Syntax OK`; warnings are configuration hygiene warnings, not startup blockers.
- Recent `/var/log/httpd/error_log` lines do not show Apache crash/503/proxy-failure symptoms at this shallow layer.

Notes:
- The baseline summary path from the request (`.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/run-summary.json`) was not present locally, so this validation relied on direct shallow checks only.
- A login transaction was not executed; this stayed within the request's shallow symptom-classification scope.

Operator takeaway: if the customer still reports “GUI down” while localhost serves the login shell cleanly, the next frontline classification should point away from local Apache/app startup failure and toward external reachability, client/browser behavior, TLS/intermediate device handling, or user-specific pathing before deeper server-side login internals are investigated.
