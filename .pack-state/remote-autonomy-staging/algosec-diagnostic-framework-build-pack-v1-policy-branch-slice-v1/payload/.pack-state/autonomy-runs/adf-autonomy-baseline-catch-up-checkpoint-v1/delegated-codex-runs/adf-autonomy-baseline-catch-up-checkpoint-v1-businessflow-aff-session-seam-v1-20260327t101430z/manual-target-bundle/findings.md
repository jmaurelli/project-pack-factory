BusinessFlow -> AFF session seam observation completed in observe-only mode.

Summary:
- Apache config proves `/FireFlow/api` proxies to `http://localhost:1989/aff/api/external` in [`artifacts/aff.conf.snippet.txt`](artifacts/aff.conf.snippet.txt).
- Live checks show response parity for `GET https://localhost/FireFlow/api/session` and `GET http://localhost:1989/aff/api/external/session`: both returned HTTP 200 and the same JSON body, `{"valid":false,"message":{"code":"INVALID_SESSION_KEY","message":"The session key provided is invalid"}}`.
- Apache adds the expected frontend headers on the 443 path; the direct `aff-boot` path does not. Body parity is intact.
- Service ownership is `aff-boot.service` running as user `afa`, with `ExecStart=/usr/share/aff/lib/aff-boot.jar`, captured in [`artifacts/aff-boot.systemctl-status.txt`](artifacts/aff-boot.systemctl-status.txt) and [`artifacts/aff-boot.systemctl-cat.txt`](artifacts/aff-boot.systemctl-cat.txt).

Evidence:
- Apache path headers/body: [`artifacts/apache_session.headers.txt`](artifacts/apache_session.headers.txt), [`artifacts/apache_session.body.json`](artifacts/apache_session.body.json)
- Direct AFF path headers/body: [`artifacts/direct_aff_session.headers.txt`](artifacts/direct_aff_session.headers.txt), [`artifacts/direct_aff_session.body.json`](artifacts/direct_aff_session.body.json)
- Apache access tail shows `GET /FireFlow/api/session` at `27/Mar/2026:06:15:38 -0400` and again at `06:15:43` and `06:15:44`: [`artifacts/httpd.ssl_access.tail.txt`](artifacts/httpd.ssl_access.tail.txt)
- AFF access tail shows matching `GET /aff/api/external/session` at `27/Mar/2026:06:15:38 -0400`, `06:15:43`, and `06:15:44`: [`artifacts/aff-boot.access.tail.txt`](artifacts/aff-boot.access.tail.txt)

Close backend clue for the next seam:
- Recent FireFlow log lines show the AFF side handling session-linked work on `1989-exec-*` threads and calling into legacy Perl session lookup code:
  - `UserSessionPersistenceEventHandler.java::requestUserDetails` with `ff-session: e0974e9f0e`
  - `LegacyRestRepository.java::sendRequest` calling `UserSession::getUserSession`
  Captured in [`artifacts/fireflow.tail.filtered.txt`](artifacts/fireflow.tail.filtered.txt).

Operator readout:
- The 443 Apache -> `aff-boot` 1989 -> `/aff/api/external/session` seam is behaving consistently for the unauthenticated invalid-session case.
- If a later parity break appears, the next clean stop is inside AFF session handling around `UserSessionPersistenceEventHandler` / `LegacyRestRepository` / `UserSession::getUserSession`, using the matching Apache and `aff-boot` access timestamps to correlate requests.
