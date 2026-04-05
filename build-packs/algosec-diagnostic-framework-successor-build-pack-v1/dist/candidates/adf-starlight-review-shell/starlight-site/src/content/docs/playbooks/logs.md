---
title: Logs
description: First-log triage after service state stops being enough.
---

## Steps

1. Open the first relevant log for the current service, service group, or node role.
2. Stay on the recent failure window first.
3. Match the current case to one of the reviewed sections below.
4. If none of the sections fit cleanly, move back one level and choose a different playbook path.

## Branch to

- `host pressure or broader appliance instability is already visible` -> `Host Health`
- `data collection, stale results, or delayed processing is the stronger read` -> `Data Collection and Processing`
- `node-role context is the stronger read` -> `Distributed Node Role`

## Single core service down

### Steps

1. Open the first log for the failed service.
2. Stay on the most recent failure window first.
3. Separate startup failure, repeated runtime failure, and dependency-looking failure.

```bash
journalctl -u ms-reporting -n 80 --no-pager
```

```text
2026-04-05 09:11:42 ERROR startup failed
2026-04-05 09:11:42 ERROR could not open expected runtime file
```

### Branch to

- `host pressure or filesystem trouble is visible` -> `Host Health`
- `the log pattern stays local and bounded` -> remain on `Logs`
- `node-role context is stronger` -> `Distributed Node Role`

## Multiple core services down

### Steps

1. Check whether host pressure, disk pressure, inode pressure, or broader appliance instability is already visible.
2. If yes, move to `Host Health`.
3. If no, open the first common or high-signal logs across the affected service group.

```bash
journalctl -u ms-metro -u ms-reporting -n 120 --no-pager
```

### Branch to

- `host pressure or broader appliance instability is visible` -> `Host Health`
- `shared log clues are stronger than host clues` -> remain on `Logs`

## Service not responding

### Steps

1. Open the first log for the not-responding service or service group.
2. Check whether the state looks stalled, timing out, or flapping.
3. Keep the first pass local before widening into deeper ownership theory.

```bash
journalctl -u ms-metro -n 120 --no-pager | tail -n 40
```

```text
2026-04-05 09:24:19 WARN request timed out after 30000ms
2026-04-05 09:24:49 WARN request timed out after 30000ms
```

### Branch to

- `host pressure is visible` -> `Host Health`
- `node-role context is stronger` -> `Distributed Node Role`
- `the log pattern stays local and bounded` -> remain on `Logs`

## Core services up

### Steps

1. Open the first logs for the path that still matches the observed issue.
2. Do not force a service-state explanation when the dashboard is healthy.
3. Use the first log clues to decide whether this is still local runtime behavior, data collection and processing, or a node-role issue.

```bash
tail -n 80 /var/log/httpd/error_log
```

```text
[error] proxy timeout contacting local upstream
[error] request returned 503 for /afa/php/home.php
```

### Branch to

- `data collection, stale results, or delayed processing is stronger` -> `Data Collection and Processing`
- `node-role context is stronger` -> `Distributed Node Role`
- `the issue stays local and log-visible` -> remain on `Logs`

## Related cookbook foundations

- `Log Entry Points` (next reviewed page)
- [Core Service Groups by Node Role](/cookbooks/core-service-groups-by-node-role/)
- `Distributed Role Foundations` (next reviewed page)
