ASMS UI is down at the front-end HTTP boundary because `httpd` is stopped.

Observed facts:
- `systemctl status httpd --no-pager --full` shows `httpd.service` `inactive (dead)` since `Sat 2026-03-28 12:11:14 EDT`.
- `ss -ltnp | grep -E ':(80|443)\s'` returned no listeners on ports `80` or `443`.
- `curl -k -I -sS --max-time 10 https://localhost/algosec-ui/login` failed with `curl: (7) Failed to connect to localhost port 443: Connection refused`.
- `curl -k -I -sS --max-time 10 https://localhost/algosec/` failed with the same `connection refused` result.
- A short `journalctl -u httpd -n 12 --no-pager` slice shows an intentional stop sequence at `2026-03-28 12:11:13-12:11:14 EDT` ending with `Stopped The Apache HTTP Server.`

Support classification:
- First failing boundary: web entrypoint unavailable because Apache `httpd` is not running.
- This is not a deeper application-layer symptom in the evidence collected here; the HTTPS listener is absent.

Immediate recovery recommendation:
- Restore `httpd` in the lab stop window recovery flow, then rerun the same shallow checks: `systemctl status httpd`, listener check on `80/443`, and the two localhost HTTPS curls.
