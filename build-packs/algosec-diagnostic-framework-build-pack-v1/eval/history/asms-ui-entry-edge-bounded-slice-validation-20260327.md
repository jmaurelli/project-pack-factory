# ASMS UI Entry Edge Bounded Slice Validation 2026-03-27

## Purpose

Record the first small framework trial for `ASMS UI is down` using the new
diagnostic mapping method.

This slice stayed intentionally narrow:

- short host sanity gate
- ASMS entry and edge
- one extra downstream BusinessFlow check for comparison only, not as the
  assumed next UI dependency

The goal was not to diagnose every possible UI failure. The goal was to test
whether this bounded method reduces ambiguity quickly and gives the next slice a
clearer starting point.

## Control Path

This pass used a local multi-agent swarm plus the official split-host remote
control path:

- a small local swarm proposed the tightest framework-aligned slice and the
  least-broad sanctioned remote path
- PackFactory root prepared and staged the build pack to `adf-dev`
- the staged build pack on `adf-dev` used the pack-local target helper commands
- the downstream target stayed the active profile `algosec-lab` at
  `10.167.2.150`

Relevant surfaces:

- `docs/specs/adf-diagnostic-mapping-framework-v1.md`
- `docs/remote-targets/adf-dev/remote-autonomy-run-request.json`
- `docs/remote-targets/algosec-lab/target-connection-profile.json`
- `.pack-state/remote-autonomy-staging/algosec-diagnostic-framework-build-pack-v1-split-host-smoke-run-v1/target-manifest.json`

## Hypothesis

For a small first pass, the first broken or ambiguous boundary would most likely
be early:

- host pressure or host sanity
- Apache or HTTPD entry and edge
- auth-adjacent handoff before the first named ASMS service seam

The slice was considered successful if it either named one early failure
boundary or proved those early surfaces healthy enough to justify moving on.

## Bounded Checks

1. `target-preflight`
   Result: pass
   Meaning: the non-login shell launcher on `adf-dev -> 10.167.2.150` still
   works and the staged helper path is usable.

2. `target-heartbeat`
   Result: pass
   Meaning: the active downstream target remained reachable through the bounded
   helper path.

3. `target-shell-command`
   Command shape:
   `df -h / /tmp && free -h && uptime && systemctl is-active httpd.service`
   Result:
   root remained `32%` used, memory remained healthy, load average stayed under
   `1`, and `httpd.service` returned `active`

4. `target-shell-command`
   Command shape:
   `ss -lntp | grep -E ':80|:443'`
   Result:
   Apache listeners remained present on `0.0.0.0:80` and `0.0.0.0:443`

5. `target-shell-command`
   Command shape:
   `curl -k -sS -I https://127.0.0.1/algosec-ui/login && curl -k -sS -I https://127.0.0.1/algosec-ui/main.js`
   Result:
   both returned `HTTP/1.1 200 OK`

6. `target-shell-command`
   Command shape:
   `curl -k -sS https://127.0.0.1/BusinessFlow/shallow_health_check && curl -k -sS https://127.0.0.1/BusinessFlow/deep_health_check`
   Result:
   shallow health returned overall `status:true` for `ABF connection`, and deep
   health returned overall `status:true` with `Postgres connection`,
   `AFA connection`, and `AFF connection` all true

## Important Refinement

After this first trial, the canonical UI-down path was tightened further.

The BusinessFlow check above remains useful recorded context, but it should not
be treated as the default next checkpoint for a pure `ASMS UI is down` case.
The better fail-closed reading is:

- host sanity gate
- ASMS entry and edge
- login-bootstrap surfaces such as `/seikan/login/setup` and
  `/afa/php/SuiteLoginSessionValidation.php`
- only then name downstream modules when the same reproduced journey actually
  reaches them

## What Became Clear

- The small remote control path itself is healthy and repeatable enough for
  bounded framework trials.
- The target host did not show early pressure signals during this pass.
- Apache or HTTPD was healthy enough to serve the login shell and UI asset path.
- BusinessFlow health was also healthy in the same observed window, but that
  is supporting downstream context rather than proof that BusinessFlow is a
  primary UI dependency.

## Productivity Reading

This trial was productive under the framework rule because it:

- proved the staged remote helper seam healthy
- eliminated host pressure as the first likely stop point in the observed test
  window
- eliminated ASMS entry and edge as the first likely stop point in the observed
  test window
- replaced a vague `UI is down` symptom with a narrower next question

## Current Reading

This slice does **not** prove a user-specific login or session path. It proves
that the earliest coarse boundaries were healthy on this pass.

That means the next bounded slice should move to the login-bootstrap part of
`ASMS authentication and session` during an actual reproduced login attempt,
rather than spending more time on host sanity, generic Apache reachability, or
downstream modules that the same reproduced journey has not yet proven.
