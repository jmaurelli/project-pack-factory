# ADF Successor Site Map And Wireframe Review v1

## Purpose

Capture the first concrete successor site map and wireframe-level page
skeletal review before implementation starts.

This note turns the approved playbook-versus-cookbook split into a small,
reviewable site shape.

## First Release Site Map

```text
/
|-- /playbooks/                    (index page)
|   |-- /playbooks/service-state/
|   |-- /playbooks/host-health/
|   |-- /playbooks/logs/
|   |   |-- #single-core-service-down
|   |   |-- #multiple-core-services-down
|   |   |-- #service-not-responding
|   |   `-- #core-services-up
|   |-- /playbooks/data-collection-and-processing/
|   `-- /playbooks/distributed-node-role/
`-- /cookbooks/                   (index page)
    |-- /cookbooks/core-service-groups-by-node-role/
    |-- /cookbooks/log-entry-points/
    |-- /cookbooks/data-flow-foundations/
    `-- /cookbooks/distributed-role-foundations/
```

Top navigation labels:

- `Overview`
- `Playbooks`
- `Cookbooks`

Navigation rule:

- `Overview` resolves to `/`
- `Playbooks` resolves to `/playbooks/`
- `Cookbooks` resolves to `/cookbooks/`

## Overview Page Skeleton

```text
+---------------------------------------------------------------+
| AlgoSec Diagnostic Framework                                  |
| Diagnostic playbooks and cookbooks for ASMS support work      |
+---------------------------------------------------------------+
| Playbook paths                                                |
| [Service State] [Host Health] [Logs]                          |
| [Data Collection and Processing] [Distributed Node Role]      |
+---------------------------------------------------------------+
| Cookbook foundations                                          |
| [Core Service Groups by Node Role] [Log Entry Points]         |
| [Data Flow Foundations] [Distributed Role Foundations]        |
+---------------------------------------------------------------+
```

The overview page should stay short and operational. It should route the
engineer into a path fast.

## Playbooks Index Skeleton

```text
+---------------------------------------------------------------+
| Playbooks                                                     |
| Five frontline triage paths                                   |
+---------------------------------------------------------------+
| [Service State] [Host Health] [Logs]                          |
| [Data Collection and Processing] [Distributed Node Role]      |
+---------------------------------------------------------------+
```

## Cookbooks Index Skeleton

```text
+---------------------------------------------------------------+
| Cookbooks                                                     |
| Runtime foundations behind the playbook paths                 |
+---------------------------------------------------------------+
| [Core Service Groups by Node Role] [Log Entry Points]         |
| [Data Flow Foundations] [Distributed Role Foundations]        |
+---------------------------------------------------------------+
```

## Playbook Template Skeleton

This is the reviewed generic playbook page frame:

```text
+---------------------------------------------------------------+
| Service State                                                 |
|                                                               |
| Steps                                                         |
| 1. ...                                                        |
| 2. ...                                                        |
| 3. ...                                                        |
|                                                               |
| Branch to                                                     |
| - ...                                                         |
| - ...                                                         |
|                                                               |
| Related cookbook foundations                                  |
| - ...                                                         |
+---------------------------------------------------------------+
```

## Cookbook Template Skeleton

This is the reviewed generic cookbook page frame:

```text
+---------------------------------------------------------------+
| Core Service Groups by Node Role                              |
| short summary                                                 |
|                                                               |
| Role matrix                                                   |
| Service group sections                                        |
| Validated behavior                                            |
| Observed practice                                             |
| Operator theory                                               |
| Not proven                                                    |
| Related playbooks                                             |
+---------------------------------------------------------------+
```

## Concrete Page Skeleton: Service State

Route:

- `/playbooks/service-state/`

Page shape:

```text
Title
Service State

Steps
1. Open the CLI service-status dashboard.
2. Review the core `ms-*` services.
3. Put the result in one of these groups:
   - one core service down
   - multiple core services down
   - one or more core services not responding
   - core services up
4. If any service is down or not responding, open the first relevant logs for
   that service or service group.
5. If core services are up, leave this path and continue in `Logs`.

Branch to
- `one core service down` -> `/playbooks/logs/#single-core-service-down`
- `multiple core services down` -> if host pressure or broader appliance instability is already visible, `/playbooks/host-health/`; otherwise `/playbooks/logs/#multiple-core-services-down`
- `one or more core services not responding` -> `/playbooks/logs/#service-not-responding`
- `core services up` -> `/playbooks/logs/#core-services-up`

Related cookbook foundations
- `Core Service Groups by Node Role`
- `Log Entry Points`
- `Distributed Role Foundations`
```

This page should not contain:

- explanation of when an engineer is allowed to restart
- explanation of what evidence to report
- customer-story framing
- listener or route-owner depth

## Concrete Page Skeleton: Logs

Route:

- `/playbooks/logs/`

Page shape:

```text
Title
Logs

Steps
1. Open the first relevant log for the current service, service group, or node role.
2. Stay on the recent failure window first.
3. Match the current case to one of the reviewed sections below.
4. If none of the sections fit cleanly, move back one level and choose a different playbook path.

Branch to
- `host pressure or broader appliance instability is already visible` -> `/playbooks/host-health/`
- `data collection, stale results, or delayed processing is the stronger read` -> `/playbooks/data-collection-and-processing/`
- `node-role context is the stronger read` -> `/playbooks/distributed-node-role/`

Related cookbook foundations
- `Log Entry Points`
- `Core Service Groups by Node Role`
- `Distributed Role Foundations`

Anchor section
`#single-core-service-down`
- Steps
  1. Open the first log for the failed service.
  2. Stay on the most recent failure window first.
  3. Separate startup failure, repeated runtime failure, and dependency-looking failure.
- Branch to
  - `host pressure or filesystem trouble is visible` -> `/playbooks/host-health/`
  - `the log pattern stays local and bounded` -> remain on `Logs`
  - `node-role context is stronger` -> `/playbooks/distributed-node-role/`

Anchor section
`#multiple-core-services-down`
- Steps
  1. Check whether host pressure, disk pressure, inode pressure, or broader appliance instability is already visible.
  2. If yes, move to `Host Health`.
  3. If no, open the first common or high-signal logs across the affected service group.
- Branch to
  - `host pressure or broader appliance instability is visible` -> `/playbooks/host-health/`
  - `shared log clues are stronger than host clues` -> remain on `Logs`

Anchor section
`#service-not-responding`
- Steps
  1. Open the first log for the not-responding service or service group.
  2. Check whether the state looks stalled, timing out, or flapping.
  3. Keep the first pass local before widening into deeper ownership theory.
- Branch to
  - `host pressure is visible` -> `/playbooks/host-health/`
  - `node-role context is stronger` -> `/playbooks/distributed-node-role/`
  - `the log pattern stays local and bounded` -> remain on `Logs`

Anchor section
`#core-services-up`
- Steps
  1. Open the first logs for the path that still matches the observed issue.
  2. Do not force a service-state explanation when the dashboard is healthy.
  3. Use the first log clues to decide whether this is still local runtime behavior, data collection and processing, or a node-role issue.
- Branch to
  - `data collection, stale results, or delayed processing is stronger` -> `/playbooks/data-collection-and-processing/`
  - `node-role context is stronger` -> `/playbooks/distributed-node-role/`
  - `the issue stays local and log-visible` -> remain on `Logs`
```

## Concrete Page Skeleton: Core Service Groups by Node Role

Route:

- `/cookbooks/core-service-groups-by-node-role/`

Page shape:

```text
Title
Core Service Groups by Node Role

Compact summary
Reference page for how core service families, first logs, role-local
expectations, and known caveats differ across CM, RA, LDU, and DR nodes.

Section
Role matrix
- columns:
  - role
  - core service families
  - first logs
  - role-local expectations
  - known role-specific caveats
- rows:
  - CM
  - RA
  - LDU
  - DR

Section
Service groups
- web edge and first access surfaces
- core `ms-*` application families
- data-processing families
- node-role-specific families

Section
Validated behavior
- role differences that are lab-proven
- service-group expectations that are packet-backed or runtime-backed

Section
Observed practice
- repeated support-useful patterns seen in real work but not yet fully proven

Section
Operator theory
- plausible role-specific expectations still under review

Section
Not proven
- still-thin role expectations
- gaps where the current successor evidence is not yet enough

Section
Related playbooks
- `Service State`
- `Logs`
- `Distributed Node Role`
```

## Wireframe Notes

For `Service State`:

- `Steps` should dominate the page
- `Branch to` should be easy to scan without scrolling far
- no subtitle or coaching block should appear above `Steps`
- no `On this page` division should take width from the main reading lane

For `Logs`:

- each anchor section should stay short and procedural
- the page should not drift into runtime-owner theory or architecture prose
- the four anchor sections should still be obvious without relying on a
  persistent table of contents

For `Core Service Groups by Node Role`:

- a role matrix or compact comparison table should appear near the top
- `Observed practice`, `Operator theory`, and `Not proven` should be visually quieter than `Validated behavior`
- the page should still feel support-facing, not architecture-heavy

## Review Gates Before Implementation

Do not start shell implementation until these points still feel right in review:

- five-path playbook entry set
- one overview page only
- strict playbook page shape
- reviewed `Logs` page with anchor sections behind `Service State`
- compact cookbook page shape
- light field-manual presentation
- `Service State`, `Logs`, and `Core Service Groups by Node Role` as the first
  reviewed set

## Why This Matters

The site map and wireframes matter now because they convert the reviewed
content model into something we can judge visually and structurally before we
spend time porting Starlight machinery into the successor line.
