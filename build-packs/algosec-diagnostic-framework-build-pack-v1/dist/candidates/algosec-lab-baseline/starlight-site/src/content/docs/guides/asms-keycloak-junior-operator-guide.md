---
title: "ASMS / Keycloak junior operator guide"
description: ""
sidebar:
  label: "ASMS / Keycloak junior operator guide"
  order: 2
---

# ASMS / Keycloak junior operator guide

## Use this guide for this kind of case

- The login page opens, but login or auth does not finish.
- The customer reports auth failure, redirect loop, or login not working.
- Apache still looks healthy and you need to decide whether the problem is Keycloak.

## Fast rule

- If `/algosec-ui/login` is still `HTTP 200` but the Keycloak OIDC path is failing, diagnose Keycloak.
- Do not move back to Apache unless the login page itself stops loading.

## Failure classes

- `startup_failure`: the service fails or exits during startup.
- `listener_absent`: the Keycloak service is supposed to listen on `8443`, but that listener is missing.
- `useful_work_path_failed`: the service may look partly alive, but the OIDC path still fails while the login page loads.
- `dependency_or_resource_unknown`: the Keycloak boundary is proven, but the current clues do not yet show whether the deeper cause is config, storage, secrets, or host pressure.

## Check 1

<div class="adf-check">
<p class="adf-check-label">Compare login page and Keycloak OIDC</p>

<p class="adf-inline-label">Run</p>

```bash
curl -k -I https://127.0.0.1/algosec-ui/login | sed -n '1,8p'; echo '---'; curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration | sed -n '1,12p'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
The login page and the Keycloak OIDC path both return HTTP 200.
</p>

<p class="adf-check-reference">
Check output for: HTTP/1.1 200
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the login page is still HTTP 200 but the OIDC path is not, keep the case on Keycloak.
</p>

<p class="adf-inline-label">Example</p>

```text
HTTP/1.1 200 OK
---
HTTP/1.1 200 OK
```
</div>

## Check 2

<div class="adf-check">
<p class="adf-check-label">Check Keycloak service and 8443 listener</p>

<p class="adf-inline-label">Run</p>

```bash
systemctl status keycloak.service --no-pager; echo '--- listeners ---'; ss -lntp | grep -E ':(8443)\b'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Keycloak is active and 8443 is listening.
</p>

<p class="adf-check-reference">
Check output for: Active: active (running), LISTEN, :8443
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If keycloak.service is failed or 8443 is missing, save the output and keep the case on Keycloak.
</p>

<p class="adf-inline-label">Example</p>

```text
● keycloak.service - Keycloak Service
   Active: active (running)
--- listeners ---
LISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:(("java",pid=2745,fd=91))
```
</div>

## Check 3

<div class="adf-check">
<p class="adf-check-label">Check the recent Keycloak journal</p>

<p class="adf-inline-label">Run</p>

```bash
journalctl -u keycloak.service -n 80 --no-pager
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Recent lines show either a normal start or the failure clue that stopped startup.
</p>

<p class="adf-check-reference">
Check output for: started, Listening on, 8443
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the service failed to start, save the clue. One proven example in this lab was `java.io.EOFException`.
</p>

<p class="adf-inline-label">Example</p>

```text
Exception in thread "main" java.lang.reflect.UndeclaredThrowableException
Caused by: java.io.EOFException
... SerializedApplication.read(...)
... QuarkusEntryPoint.doRun(...)
keycloak.service: Main process exited, status=1/FAILURE
```
</div>

## Check 4

<div class="adf-check">
<p class="adf-check-label">Optional: run one bounded restart if recovery validation is needed</p>

<p class="adf-inline-label">Run</p>

```bash
sudo systemctl restart keycloak.service && sleep 30 && systemctl is-active keycloak.service && ss -lntp | grep -E ':(8443)\b' && curl -k -I https://127.0.0.1/keycloak/realms/master/.well-known/openid-configuration | sed -n '1,12p'
```

<p class="adf-check-signal">
  <span class="adf-inline-label">Expected result:</span> 
Keycloak comes back active, 8443 listens again, and the OIDC path returns HTTP 200.
</p>

<p class="adf-check-reference">
Check output for: active, LISTEN, :8443, HTTP/1.1 200
</p>

<p class="adf-check-failure">
  <span class="adf-inline-label">If result is different:</span> 
If the service still fails after one bounded restart, stop there. Save the output and escalate with the Keycloak failure clue instead of inventing many extra branches.
</p>

<p class="adf-inline-label">Example</p>

```text
active
LISTEN 0 100 0.0.0.0:8443 0.0.0.0:* users:(("java",pid=2745,fd=91))
HTTP/1.1 200 OK
```
</div>

## When to escalate

- Escalate when the login page still loads but the OIDC path is failing and you already captured the service, listener, proxy, and journal clues.
- Escalate when one bounded restart does not restore useful auth work.
- Escalate with the failure class you proved, not with a vague `login broken` summary.

## What to save before the next session

- output from the login-page and OIDC comparison
- output from `systemctl status keycloak.service`
- the recent Keycloak journal clue
- the result of the restart attempt if you ran it

## Upstream references

- [Keycloak documentation](https://www.keycloak.org/documentation)
- [Configuring Keycloak](https://www.keycloak.org/server/configuration)
- [Keycloak GitHub repository](https://github.com/keycloak/keycloak)

