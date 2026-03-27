BusinessFlow AFF seam validation completed in observe-only mode.

Summary:
- Apache `/etc/httpd/conf.d/aff.conf` maps `Location /FireFlow/api` to `http://localhost:1989/aff/api/external`.
- Live probe of `https://localhost/FireFlow/api/session` returned `HTTP/1.1 200` with JSON body `{"valid":false,"message":{"code":"INVALID_SESSION_KEY","message":"The session key provided is invalid"}}`.
- Live probe of `http://localhost:1989/aff/api/external/session` returned the same `HTTP/1.1 200` JSON body.
- The two response bodies were byte-identical (`cmp` exit code `0`; identical SHA-256 hashes).
- `aff-boot.service` is active and running, with `systemctl status` showing `Active: active (running) since Sat 2026-03-07 13:36:11 EST`.

Operator note:
- `systemctl status` shows the loaded unit path as `/etc/systemd/system/aff-boot.service`. That path is outside this task's declared `allowed_targets`, so I did not read or snapshot the unit file itself. I captured bounded status output only.

Captured artifacts:
- `artifacts/aff.conf.snapshot`
- `artifacts/apache-fireflow-session.txt`
- `artifacts/direct-aff-session.txt`
- `artifacts/aff-boot.service.txt`
