# ASMS UI Apache-To-Metro Proxy Isolation Plan V1

## Purpose

This plan defines the next tight lab experiment for `ASMS UI is down`.

The question is no longer whether browser-side blocking can own the fresh
`config` and `session/extend` traffic. That was already answered in the
negative.

The new question is:

- which Apache-to-Metro proxy family actually matters to the first usable ASMS
  home shell?

## Current Evidence

Known Apache seam:

- `/etc/httpd/conf.d/zzz_fa.conf:130`
  `<Location /afa/external>`
- `/etc/httpd/conf.d/zzz_fa.conf:139`
  `<Location /afa/api/v1>`

Both currently proxy to:

- `http://localhost:8080/afa/api/v1`

Known fresh-session evidence:

- Apache saw fresh-session requests such as:
  - `/afa/external//config?...`
  - `/afa/external//session/extend?...`
- Metro saw fresh-session requests such as:
  - `/afa/getStatus`
  - `/afa/api/v1/license`
  - `/afa/api/v1/config?...`
  - `/afa/api/v1/session/extend?...`
  - `/afa/config/...`

Current interpretation:

- `/afa/config/...` and `/afa/api/v1/config?...` behave like paired
  server-side surfaces around the same config family.
- That makes the Apache proxy seam the right next isolation point.

## Tight Experiment Sequence

Run only one variant at a time.

Always roll back fully before attempting a second variant.

### Variant A

Temporarily block `/afa/external` only.

Hypothesis:

- if `/afa/external` is required for the first usable home shell, the fresh
  login should fail earlier or the post-login shell should lose expected
  usability clues
- if `/afa/external` is not required for the first usable home shell, the
  shell may still render and the route should be demoted

### Variant B

Temporarily block `/afa/api/v1` only.

Hypothesis:

- if `/afa/api/v1` is the stronger first-shell gate, the fresh login should
  degrade earlier or the first usable home shell should fail to stabilize

Variant A should run first because the fresh Apache evidence already showed
`/afa/external//config?...` and `/afa/external//session/extend?...` tied to
the fresh session.

## Latest Result

Variant A and Variant B are now complete.

Variant A observed result:

- Apache returned repeated `403` responses for `/afa/external//config...`,
  `/afa/external//session/extend...`, and related `/afa/external` requests
- `/afa/php/home.php` still rendered a fully usable `AlgoSec - Home` shell
- Metro still served `/afa/config/...`, `/afa/getStatus`, and later
  authenticated home-shell follow-up traffic

Variant B observed result:

- Apache returned `403` for some `/afa/api/v1` requests such as
  `config/PRINT_TABLE_IN_NORMAL_VIEW` and `license`
- `/afa/php/home.php` still rendered a fully usable `AlgoSec - Home` shell
- Metro still served fresh-session `/afa/api/v1/config?...` and
  `/afa/api/v1/session/extend?...` as `200`

Current interpretation:

- `/afa/external` is demoted as a first-shell gate candidate
- the top-level Apache `/afa/api/v1` deny is also not a clean control lever for
  the fresh-session config/session path
- the next seam must move one level deeper than the family-wide Apache deny
- the newer route-owner split is now captured separately in
  `docs/specs/asms-ui-config-owner-split-plan-v1.md`

## Preferred Mutation Surface

Use a temporary override include file:

- `/etc/httpd/conf.d/zzzz_adf_proxy_isolation.conf`

Do not edit `/etc/httpd/conf.d/zzz_fa.conf` inline unless the temporary
override approach fails for a proven Apache reason.

## Candidate Override Shapes

The experiment should prefer the simplest override that Apache accepts cleanly
on this appliance.

Candidate A:

```apache
<Location /afa/external>
  Require all denied
</Location>
```

Candidate B:

```apache
<Location /afa/api/v1>
  Require all denied
</Location>
```

If a deny-based override does not control the seam cleanly, close out the
family-wide Apache experiment and shift to the owner-split plan in
`docs/specs/asms-ui-config-owner-split-plan-v1.md` instead of repeating
broader Apache-family mutations.

## Preflight

Before Variant A or Variant B:

1. Confirm current syntax:
   `apachectl -t`
2. Confirm current UI baseline:
   one fresh bounded login to `https://127.0.0.1/algosec-ui/login`
3. Record the fresh `PHPSESSID` and same-minute logs
4. Confirm rollback command is ready:
   - `rm -f /etc/httpd/conf.d/zzzz_adf_proxy_isolation.conf`
   - `apachectl -t`
   - `systemctl reload httpd`

## Mutation Steps

For one variant only:

1. Write the temporary override file
2. Run:
   `apachectl -t`
3. If syntax passes, run:
   `systemctl reload httpd`
4. Record the mutation start time in UTC and local appliance time

## Reproduction Steps

After reload:

1. Launch one fresh incognito login to:
   `https://127.0.0.1/algosec-ui/login`
2. Use bounded waits only
3. Record:
   - final URL
   - page title
   - visible markers:
     `HOME`, `DEVICES`, `DASHBOARDS`, `GROUPS`, `MATRICES`,
     `Firewall Analyzer`, `FireFlow`, `AlgoSec Cloud`, `ObjectFlow`,
     `AppViz`
   - fresh `PHPSESSID`

## Evidence To Capture

Capture the exact mutation minute from:

- `/var/log/httpd/ssl_access_log`
- `/data/ms-metro/logs/localhost_access_log.txt`

Focus on:

- `/afa/getStatus`
- `/afa/api/v1/license`
- `/afa/api/v1/config?...`
- `/afa/api/v1/config/all/noauth?...`
- `/afa/api/v1/session/extend?...`
- `/afa/external//config?...`
- `/afa/external//session/extend?...`
- `/afa/config/...`
- `/afa/php/home.php`

## Rollback

Immediately after the single reproduction:

1. Remove the temporary override file:
   `rm -f /etc/httpd/conf.d/zzzz_adf_proxy_isolation.conf`
2. Run:
   `apachectl -t`
3. If syntax passes, run:
   `systemctl reload httpd`
4. Confirm the normal login path works again

## Interpretation Rules

Treat the result this way:

- if blocking `/afa/external` breaks the first usable home shell, promote that
  proxy family as a first-shell-relevant seam
- if blocking `/afa/external` does not break the first usable home shell,
  demote it and move to Variant B only after rollback
- if blocking `/afa/api/v1` breaks the first usable home shell, promote that
  proxy family as the stronger first-shell seam
- if neither variant changes first-shell usability, keep both as supporting
  surfaces and narrow the next seam deeper inside Metro or into a more
  path-specific Apache control point

## Deliverable Note Shape

The mutation note should include:

- exact variant name
- exact override file contents
- exact mutation window
- fresh `PHPSESSID`
- final URL and title
- whether the first usable shell survived
- same-minute Apache and Metro evidence
- whether the seam is promoted, demoted, or still ambiguous
