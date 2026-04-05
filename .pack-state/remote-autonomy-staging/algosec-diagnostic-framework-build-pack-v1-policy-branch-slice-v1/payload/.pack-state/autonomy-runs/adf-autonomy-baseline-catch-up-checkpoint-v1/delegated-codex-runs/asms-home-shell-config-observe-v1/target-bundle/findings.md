Observed the direct PHP-to-Metro config seam behind the first usable ASMS home shell.

Key findings:
- PHP login bootstrap makes Metro config a hard prerequisite before `home.php`: `AlgosecSessionManager::postLoginActions()` calls `utils::HandleConfigParams()`, which calls `GetConfigurationSettings()`, which calls `RestClient::getAllConfig()`.
- `RestClient` talks straight to Metro at `http://127.0.0.1:8080/afa`, so the PHP stack does not need Apache's external `/afa/api/v1/config` route for its own config hydration.
- `home.php` primarily consumes already-cached `m_configurationSettings`; its same-request live reads are mostly non-config data such as `/noauth/device/`, `UsersInfo/<user>`, and local analyzed-list/session artifacts.
- Apache exposes `/afa/api/v1` to the same Metro backend, but externally visible `/afa/config` is not mapped in Apache. A captured access-log pair on 2026-03-25 19:20:54 shows `/afa/api/v1/config?...` returning `200` while `/afa/config/?...` returns `404`.
- Same-minute supporting traffic around successful shell entry includes unauthenticated or external-shell config probes such as `/afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW` (`401`) and `/afa/external//config/all/noauth` (`200`). Those appear adjacent to shell validation and suite framing, not as blockers for `home.php` itself.

Assessment:
- First-shell requirement: Metro config fetch via backend `GET /afa/api/v1/config?session=...&domain=...` during login/session bootstrap.
- Supporting traffic in the same minute: `/afa/external//config/all/noauth`, `/afa/external//config?...`, `/afa/api/v1/config/PRINT_TABLE_IN_NORMAL_VIEW`, session-extend/license checks, and static asset loads.

Artifacts:
- `artifacts/seam-evidence.txt`
