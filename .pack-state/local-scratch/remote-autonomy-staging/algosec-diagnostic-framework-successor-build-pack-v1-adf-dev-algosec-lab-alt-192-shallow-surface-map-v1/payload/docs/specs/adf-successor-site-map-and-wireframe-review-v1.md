# ADF Successor Site Map And Wireframe Review v1

## Purpose

Capture the first concrete successor site map and wireframe-level page
skeletal review before implementation starts.

This note turns the approved playbook-versus-cookbook split into a small,
reviewable site shape.

## First Release Site Map

```text
/
|-- /playbooks/
|   |-- /playbooks/service-state/
|   |-- /playbooks/host-health/
|   |-- /playbooks/logs/
|   |-- /playbooks/data-collection-and-processing/
|   `-- /playbooks/distributed-node-role/
`-- /cookbooks/
    |-- /cookbooks/core-service-groups-by-node-role/
    |-- /cookbooks/log-entry-points/
    |-- /cookbooks/data-flow-foundations/
    `-- /cookbooks/distributed-role-foundations/
```

Top navigation labels:

- `Overview`
- `Playbooks`
- `Cookbooks`

## Overview Page Skeleton

```text
+---------------------------------------------------------------+
| ADF Successor                                                 |
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

## Playbook Template Skeleton

This is the reviewed generic playbook page frame:

```text
+-------------------------+-------------------------------------+
| sticky rail             | main lane                           |
|-------------------------|-------------------------------------|
| path jump links         | Service State                       |
| step 1                  | one-line path description           |
| step 2                  |                                     |
| step 3                  | Steps                               |
| branch links            | 1. ...                              |
| cookbook links          | 2. ...                              |
|                         | 3. ...                              |
|                         |                                     |
|                         | Branch to                           |
|                         | - ...                               |
|                         | - ...                               |
|                         |                                     |
|                         | Related cookbook foundations        |
|                         | - ...                               |
+-------------------------+-------------------------------------+
```

## Cookbook Template Skeleton

This is the reviewed generic cookbook page frame:

```text
+-------------------------+-------------------------------------+
| sticky rail             | main lane                           |
|-------------------------|-------------------------------------|
| section jump links      | Core Service Groups by Node Role    |
| related playbooks       | short summary                       |
|                         |                                     |
|                         | Role matrix                         |
|                         | Service group sections              |
|                         | Behavior notes                      |
|                         | Proven vs not proven                |
|                         | Related playbooks                   |
+-------------------------+-------------------------------------+
```

## Concrete Page Skeleton: Service State

Route:

- `/playbooks/service-state/`

Page shape:

```text
Title
Service State

Short description
Use the CLI service-status view to sort the case quickly, then move to logs.

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
- `one core service down` -> `service-focused logs`
- `multiple core services down` -> `host health` or `broader logs`
- `one or more core services not responding` -> `logs`
- `core services up` -> `logs`

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

## Concrete Page Skeleton: Core Service Groups by Node Role

Route:

- `/cookbooks/core-service-groups-by-node-role/`

Page shape:

```text
Title
Core Service Groups by Node Role

Short summary
Use this page to understand which core service families matter most on CM, RA,
LDU, and DR nodes before going deeper into logs or node-specific behavior.

Section
Role matrix
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
What support should expect to vary by role
- service presence
- service importance
- first-log focus

Section
Behavior notes
- notes that are useful in practice but not yet universally proven

Section
Proven vs not proven
- proven role differences
- still-thin role expectations

Section
Related playbooks
- `Service State`
- `Logs`
- `Distributed Node Role`
```

## Wireframe Notes

For `Service State`:

- the sticky rail should be narrow and mostly functional
- `Steps` should dominate the page
- `Branch to` should be easy to scan without scrolling far

For `Core Service Groups by Node Role`:

- a role matrix or compact comparison table should appear near the top
- behavior notes should be visually quieter than proven content
- the page should still feel support-facing, not architecture-heavy

## Review Gates Before Implementation

Do not start shell implementation until these points still feel right in review:

- five-path playbook entry set
- one overview page only
- strict playbook page shape
- compact cookbook page shape
- light field-manual presentation
- `Service State` and `Core Service Groups by Node Role` as the first paired
  review pages

## Why This Matters

The site map and wireframes matter now because they convert the reviewed
content model into something we can judge visually and structurally before we
spend time porting Starlight machinery into the successor line.
