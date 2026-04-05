---
title: Core Service Groups by Node Role
description: Runtime foundation for CM, RA, LDU, and DR role differences.
---

Use this page to confirm which node role you are on before you interpret service state or first logs. CM, RA, LDU, and DR do not expose the same first-response surface.

## Role matrix

| Role | Service State surface | Open these logs first | First read | Common mistake |
| --- | --- | --- | --- | --- |
| CM | broadest local `ms-*` surface and web edge | `httpd`, primary `ms-*` journals | best first stop for broad local issues | assuming CM health proves peer health |
| RA | narrower role-local `ms-*` surface | role-local `ms-*` journals | read the local runtime first, then widen | reading CM expectations into RA |
| LDU | processing-heavy and utility-heavy surface | ingestion, processing, and role-local journals | expect a different service mix than CM | treating CM-only services as missing on purpose |
| DR | standby-oriented or colder posture | role-local journals around DR services | quiet or reduced activity may be normal | treating standby quietness as failure by default |

## Validated behavior

- CM and non-CM nodes do not expose the same first-response service surface.
- First-log priorities change by node role.
- Role differences should be treated as runtime facts, not as drift by default.

## Observed practice

- Service State plus node role is usually enough to narrow the first log choice quickly.
- Engineers get faster traction when they decide the node role first instead of comparing every node to CM.

## Operator theory

- Some peer or cross-node failures may first appear as local ambiguity on a healthy-looking node.

## Not proven

- Full DR service expectations across every standby posture are still incomplete.
- Some role-specific caveats still need more lab-backed repetition before they should move into `Validated behavior`.

## Related playbooks

- [Service State](/playbooks/service-state/)
- [Logs](/playbooks/logs/)
