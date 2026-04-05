---
title: Service State
description: Frontline triage path for the CLI `ms-*` service-status dashboard.
sidebar:
  label: Service State
  order: 2
---

## Steps

1. Open the CLI service-status dashboard.
2. Review the core `ms-*` services.
3. Put the result in one of these groups:
   - one core service down
   - multiple core services down
   - one or more core services not responding
   - core services up
4. If any service is down or not responding, open the first relevant logs for that service or service group.
5. If core services are up, leave this path and continue in `Logs`.

## Branch to

- `one core service down` -> [Logs: single core service down](/playbooks/logs/#single-core-service-down)
- `multiple core services down` -> if host pressure or broader appliance instability is already visible, [Host Health](/playbooks/host-health/); otherwise [Logs: multiple core services down](/playbooks/logs/#multiple-core-services-down)
- `one or more core services not responding` -> [Logs: service not responding](/playbooks/logs/#service-not-responding)
- `core services up` -> [Logs: core services up](/playbooks/logs/#core-services-up)

## Related cookbook foundations

- [Core Service Groups by Node Role](/cookbooks/core-service-groups-by-node-role/)
- [Log Entry Points](/cookbooks/log-entry-points/)
- [Distributed Role Foundations](/cookbooks/distributed-role-foundations/)
