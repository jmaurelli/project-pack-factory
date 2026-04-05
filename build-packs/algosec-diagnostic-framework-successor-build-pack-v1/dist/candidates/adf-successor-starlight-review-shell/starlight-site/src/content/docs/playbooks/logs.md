---
title: Logs
description: Frontline triage path for the first relevant logs behind the current service group or node role.
sidebar:
  label: Logs
  order: 3
---

## Steps

1. Open the first relevant log for the current service, service group, or node role.
2. Stay on the recent failure window first.
3. Match the current case to one of the reviewed sections below.
4. If none of the sections fit cleanly, move back one level and choose a different playbook path.

## Branch to

- `host pressure or broader appliance instability is already visible` -> [Host Health](/playbooks/host-health/)
- `data collection, stale results, or delayed processing is the stronger read` -> [Data Collection and Processing](/playbooks/data-collection-and-processing/)
- `node-role context is the stronger read` -> [Distributed Node Role](/playbooks/distributed-node-role/)

## Related cookbook foundations

- [Log Entry Points](/cookbooks/log-entry-points/)
- [Core Service Groups by Node Role](/cookbooks/core-service-groups-by-node-role/)
- [Distributed Role Foundations](/cookbooks/distributed-role-foundations/)

## Single core service down

### Steps

1. Open the first log for the failed service.
2. Stay on the most recent failure window first.
3. Separate startup failure, repeated runtime failure, and dependency-looking failure.

### Branch to

- `host pressure or filesystem trouble is visible` -> [Host Health](/playbooks/host-health/)
- `the log pattern stays local and bounded` -> remain on `Logs`
- `node-role context is stronger` -> [Distributed Node Role](/playbooks/distributed-node-role/)

## Multiple core services down

### Steps

1. Check whether host pressure, disk pressure, inode pressure, or broader appliance instability is already visible.
2. If yes, move to `Host Health`.
3. If no, open the first common or high-signal logs across the affected service group.

### Branch to

- `host pressure or broader appliance instability is visible` -> [Host Health](/playbooks/host-health/)
- `shared log clues are stronger than host clues` -> remain on `Logs`

## Service not responding

### Steps

1. Open the first log for the not-responding service or service group.
2. Check whether the state looks stalled, timing out, or flapping.
3. Keep the first pass local before widening into deeper ownership theory.

### Branch to

- `host pressure is visible` -> [Host Health](/playbooks/host-health/)
- `node-role context is stronger` -> [Distributed Node Role](/playbooks/distributed-node-role/)
- `the log pattern stays local and bounded` -> remain on `Logs`

## Core services up

### Steps

1. Open the first logs for the path that still matches the observed issue.
2. Do not force a service-state explanation when the dashboard is healthy.
3. Use the first log clues to decide whether this is still local runtime behavior, data collection and processing, or a node-role issue.

### Branch to

- `data collection, stale results, or delayed processing is stronger` -> [Data Collection and Processing](/playbooks/data-collection-and-processing/)
- `node-role context is stronger` -> [Distributed Node Role](/playbooks/distributed-node-role/)
- `the issue stays local and log-visible` -> remain on `Logs`
