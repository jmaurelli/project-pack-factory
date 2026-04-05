# ASMS UI httpd shallow-fault validation - 2026-03-28

## Purpose

Run the first controlled shallow-fault validation for the canonical `ASMS UI is down` playbook and confirm that the observer stops at the Apache or HTTPD edge boundary instead of drifting into deeper auth or downstream module theory.

## Control path

- Local PackFactory orchestrator -> staged `adf-dev` build-pack copy -> helper path on `algosec-lab`
- Delegated observer tier: `observe_only`
- Delegation run id: `adf-autonomy-baseline-catch-up-checkpoint-v1-execute_httpd_shallow_fault_validation_trial-20260328t161133z`

## Baseline before mutation

- `target-preflight` passed.
- `target-heartbeat` passed.
- `systemctl is-active httpd` returned `active`.
- `systemctl is-enabled httpd` returned `enabled`.
- `apachectl -t` returned `Syntax OK`.
- `ss -ltn | grep -E ':(80|443)\b'` showed listeners on `80` and `443`.
- `curl -k -I https://localhost/algosec-ui/login` returned `HTTP/1.1 200 OK`.
- `curl -k -I https://localhost/algosec/` returned `HTTP/1.1 200 OK`.

## Mutation window

- Mutation window opened at `2026-03-28T16:11:12Z`.
- The mutation owner stopped `httpd` through the official helper path.

## Fault observations

- `systemctl status httpd --no-pager --full` showed `httpd.service` as `inactive (dead)` since `Sat 2026-03-28 12:11:14 EDT`.
- `ss -ltnp | grep -E ':(80|443)\s'` returned no listeners on `80` or `443`.
- `curl -k -I -sS --max-time 10 https://localhost/algosec-ui/login` failed with `curl: (7) Failed to connect to localhost port 443: Connection refused`.
- `curl -k -I -sS --max-time 10 https://localhost/algosec/` failed with the same `connection refused` result.
- `journalctl -u httpd -n 12 --no-pager` showed the intentional stop sequence at `2026-03-28 12:11:13-12:11:14 EDT`, ending with `Stopped The Apache HTTP Server.`

## Observer result

The accepted delegated observer stopped at the first shallow failing boundary and did not widen into deeper auth or module tracing. The preserved delegated bundle is:

- `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/delegated-codex-runs/adf-autonomy-baseline-catch-up-checkpoint-v1-execute_httpd_shallow_fault_validation_trial-20260328t161133z/target-bundle/delegated-task-result.json`
- `.pack-state/autonomy-runs/adf-autonomy-baseline-catch-up-checkpoint-v1/delegated-codex-runs/adf-autonomy-baseline-catch-up-checkpoint-v1-execute_httpd_shallow_fault_validation_trial-20260328t161133z/target-bundle/findings.md`

Plain-language classification:

- First failing boundary: web entrypoint unavailable because Apache `httpd` is not running.
- This observed case does not require deeper application-layer explanation because the HTTPS listener is absent.

## Rollback and recovery

- `systemctl start httpd` succeeded through the official helper path.
- `apachectl -t` again returned `Syntax OK`.
- `ss -ltn | grep -E ':(80|443)\b'` again showed listeners on `80` and `443`.
- `curl -k -I https://localhost/algosec-ui/login` returned `HTTP/1.1 200 OK`.
- `curl -k -I https://localhost/algosec/` returned `HTTP/1.1 200 OK`.
- Final `systemctl is-active httpd` returned `active`.

## Outcome

- Trial status: pass
- The mutation-backed validation proved that a real lab-only `httpd` outage stops cleanly at the Apache or HTTPD edge boundary.
- The frontline playbook reached the correct shallow recovery action without deep drift.
