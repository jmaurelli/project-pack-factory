Observed the March 27, 2026 reproduction window directly from Apache and FireFlow logs and packaged the correlated slices under `artifacts/`.

Findings:
- Apache `ssl_request_log` shows a repeatable sequence at `06:20` and again at `06:25` EDT: `BusinessFlow` health checks continue while `FireFlow` performs `GET /FireFlow/api/session/validate`, `POST /FireFlow/api/session/extendSession`, `POST /fa/environment/getAFASessionInfo`, and `POST /afa/external//bridge/refresh`.
- FireFlow logs match that seam. Around `2026-03-27 06:20:33` and `06:25:35`, `UserSessionPersistenceEventHandler` emits `ff-session`, `LegacyRestRepository` calls `UserSession::getUserSession`, and Perl resolves `Using existing FASessionId: uimmr6u9e8`.
- A second FireFlow session path around `06:20:43` and `06:25:43` calls `POST /fa/environment/getAFASessionInfo` before resolving `Using existing FASessionId: n575jpek15`, then extends the AFA session. This suggests the bridge can derive or refresh AFA session context when the direct mapping is not already attached to the FF session.
- BusinessFlow-side PHP context supports that handoff model:
  - `SSOLogin.php` sends `AFF_COOKIE=<utils::getFireflowCookie()>` into FireFlow SSO bootstrap and can set a returned BusinessFlow cookie on `/BusinessFlow`.
  - `SuiteLoginSessionValidation.php` explicitly states BusinessFlow cannot read its own cookie in this suite-login context because the cookie path is `/BusinessFlow`, and it validates against AFA plus FireFlow instead.
  - `AlgosecSessionManager.php` notes AFF separation changed suite login to use AFA REST login semantics.
  - `ExtUtils.php` preserves the `Could not find AlgosecSession` string because FireFlow searches for it in `VerifyGetFASessionIdValid`.

Interpretation:
- The reproduced seam is consistent with a healthy BusinessFlow -> FireFlow `UserSession` bridge rather than a dead handoff. FireFlow keeps validating FF session `533c342cd4...`, then later authenticates `ff-session` values such as `ecad8a323f` and resolves them to AFA session `uimmr6u9e8`.
- The more interesting branch is the `getAFASessionInfo` fallback that resolves to `n575jpek15`, because that is where FireFlow appears to reconstruct or refresh AFA context before serving `/FireFlow/api/session`.

Artifacts:
- `artifacts/apache-aff-usersession-window.txt`
- `artifacts/fireflow-usersession-window.txt`
- `artifacts/businessflow-php-aff-context.txt`

Minor blocker:
- The request referenced `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/run-summary.json`, but that file was absent on disk.
