---
title: Service State
description: First-pass CLI triage for core ms-* service state.
---

## Steps

1. Open the CLI service-status dashboard.
2. Review only the core `ms-*` services first.
3. Put the current state in one of these buckets:
   - one core service down
   - multiple core services down
   - one or more core services not responding
   - core services up
4. If any service is down or not responding, open the first log for that named service or service group.
5. If core services are up, leave this path and continue in [Logs](/playbooks/logs/).
6. Do not stay on this page after the bucket is clear. This path is only the front-door filter.

```text
Example dashboard
ms-auth             up
ms-collector        up
ms-metro            up
ms-reporting        down
```

## Branch to

- `one core service down` -> [Logs / Single core service down](/playbooks/logs/#single-core-service-down)
- `multiple core services down` -> if host pressure is already visible, `Host Health`; otherwise [Logs / Multiple core services down](/playbooks/logs/#multiple-core-services-down)
- `one or more core services not responding` -> [Logs / Service not responding](/playbooks/logs/#service-not-responding)
- `core services up` -> [Logs / Core services up](/playbooks/logs/#core-services-up)

## Related cookbook foundations

- [Core Service Groups by Node Role](/cookbooks/core-service-groups-by-node-role/)
- `Log Entry Points` (next reviewed page)
- `Distributed Role Foundations` (next reviewed page)
