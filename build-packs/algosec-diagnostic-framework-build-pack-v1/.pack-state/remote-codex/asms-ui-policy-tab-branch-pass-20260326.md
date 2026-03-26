# ASMS UI Policy Tab Branch Pass 2026-03-26

## Purpose

Decide whether the device-context `POLICY` tab still belongs inside the core
`ASMS UI is down` path or whether it is already a later workflow branch.

## Front-End Path

The device-context policy logic is not a trivial shell toggle.

From `/usr/share/fa/php/JSlib1768164240/rule_documentation.js`:

- `getPolicyTabData(...)` posts `cmd=GET_POLICY_TAB`
- group drill-down later posts `cmd=GET_DEVICE_POLICY`

That means the tab already crosses into its own rule-documentation workflow.

## Server-Side Path

From `/usr/share/fa/php/commands/rule_documentation.cmd.php`:

- `GET_POLICY_TAB` calls `getPolicyTab(...)`
- `GET_DEVICE_POLICY` calls `GetSingleDevicePolicy(...)`
- `getPolicyTab(...)` selects report or monitor rule files
- it prepares `PolicyTabIframe.php`
- it builds paging and HTML around parsed rules data

Important fallback from the same handler:

- if the needed rules/report surface is not available, it returns:
  - `The policy of this device will be displayed once a report is created for it. To create a report, please go to the Overview tab and click on Analyze.`

## Interpretation

This is enough to place `POLICY` correctly in the ASMS map:

- `POLICY` is not part of the first usable-shell gate
- it is a later device-content branch that depends on rule/report surfaces
- it can even depend on having an analyzed report already available
- so it should not be used as the first proof that the GUI is healthy enough

For the current `ASMS UI is down` trajectory:

- keep the landing-shell model centered on dashboard and issue-center hydration
- keep device selection as a later shell-context step
- keep `POLICY` outside the first usable-shell checkpoint
- only branch into `POLICY` deliberately when the case has already moved from
  "GUI is down" into "device content or policy content inside the GUI is not
  loading"

## Sibling Device-Content Branches

The nearby sibling tabs follow the same general pattern:

- `CHANGES` in `home.js` uses `cmd=GET_MONITORING_CHANGES`
- `REPORTS` in `home.js` uses `cmd=GET_REPORTS`

This is enough to keep the higher-level rule clear:

- device-context tabs are already later content branches
- they should not be used as the first proof of basic ASMS home-shell
  availability
