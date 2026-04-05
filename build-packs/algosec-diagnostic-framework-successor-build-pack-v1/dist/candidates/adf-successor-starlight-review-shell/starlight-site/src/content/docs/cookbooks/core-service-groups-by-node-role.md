---
title: Core Service Groups by Node Role
description: Role-local expectations, first logs, and caveats across CM, RA, LDU, and DR nodes.
sidebar:
  label: Core Service Groups by Node Role
  order: 2
---

Reference page for how core service families, first logs, role-local expectations, and known caveats differ across CM, RA, LDU, and DR nodes.

## Role matrix

| Role | Core service families | First logs | Role-local expectations | Known role-specific caveats |
| ---- | --------------------- | ---------- | ----------------------- | --------------------------- |
| CM | web edge, core `ms-*`, data-processing, coordination | `httpd`, role-local `ms-*` logs | broadest local surface | can look healthy while a peer role is degraded |
| RA | provider-facing and role-local `ms-*` families | role-local `ms-*` logs | thinner than CM | local symptoms can still reflect CM-led state |
| LDU | log and data utility families | ingestion and processing logs | edge-heavy and processing-heavy | service mix differs from CM by design |
| DR | standby-oriented and failover-adjacent families | role-local service logs | colder posture can be normal | some absences may be expected, not failures |

## Service groups

- web edge and first access surfaces
- core `ms-*` application families
- data-processing families
- node-role-specific families

## Validated behavior

- CM and non-CM nodes do not expose the same first-response service surface.
- First-log priorities change by node role.
- Service-family expectations differ by role even when the product line is the same.

## Observed practice

- Engineers often get better first traction by checking role-local logs before widening into cross-node theory.
- Role context helps narrow which `ms-*` service states matter first during frontline triage.

## Operator theory

- Some degraded peer patterns may present as local ambiguity before role separation becomes obvious.
- Some role-local `not responding` patterns may resolve into shared-dependency trouble later in the case.

## Not proven

- Full service expectations for every DR posture are still incomplete.
- Some role-specific caveats are still thin outside the current lab set.

## Related playbooks

- [Service State](/playbooks/service-state/)
- [Logs](/playbooks/logs/)
- [Distributed Node Role](/playbooks/distributed-node-role/)
