# ASMS UI Dashboard Demand-Load Pass 2026-03-26

## Purpose

Reduce the next post-bootstrap seam for `ASMS UI is down` by proving what the
first usable home shell actually loads after `/afa/php/home.php`, and by
finding the first clearly isolated deeper operator action after that shell is
already visible.

## Method

- used one fresh headless Chromium login against
  `https://127.0.0.1/algosec-ui/login`
- used bounded waits plus visible-shell checks instead of `networkidle`
- captured only a narrow request family:
  - `commands.php`
  - `dynamic.js.php`
  - `/fa/tree/create`
  - `/fa/tree/get_update`
  - `prod_stat.php`
  - `inFrm=1`
  - `/afa/getStatus`
- then drove one bounded path:
  - login
  - `DEVICES`
  - device `200132`
  - `Analyze`

## What The Visible Shell Showed

After login, the first usable shell was not a blank landing page.

It already showed:

- the normal `AlgoSec - Home` title
- the top shell navigation: `HOME`, `DEVICES`, `DASHBOARDS`, `GROUPS`,
  `MATRICES`
- the main module labels: `Firewall Analyzer`, `FireFlow`, `AlgoSec Cloud`,
  `ObjectFlow`, `AppViz`
- a populated summary dashboard view rather than an empty shell

After `DEVICES`, the browser still remained on `/afa/php/home.php` and the
summary dashboard content was still visible alongside the left tree.

After selecting device `200132`, the shell stayed on `/afa/php/home.php` and
showed device-context content such as:

- `Host: 10.86.1.249`
- `Device Version: 11.1.6-h3`
- `OVERVIEW`, `POLICY`, `CHANGES`, `REPORTS`, `MAP`
- `Analyze`, `Traffic Simulation`, `Query`, `Topology`, `Trusted Traffic`,
  `Locate Object`

## Narrow Event Result

The first bounded request family after login was:

- `GET /afa/php/commands.php?cmd=IS_SESSION_ACTIVE&extended=true`
- `GET /afa/php/JSlib1768164240/dynamic.js.php?sid=...`
- `GET /afa/php/commands.php?cmd=DISPLAY_ISSUES_CENTER`
- `POST /fa/tree/create`
- `POST /afa/php/commands.php` with:
  - `cmd=GET_DASHBOARDS_DATA&dashboard=ALL`
  - `cmd=GET_DASHBOARDS_DATA&dashboard=DEFAULT`
  - `cmd=GET_CHART_FOR_DASHBOARD_MULTIPLE`
  - `cmd=GET_RISK_PROFILES_OPTIONS`

When `DEVICES` was clicked, the clean additional bounded requests were:

- `GET /afa/php/prod_stat.php`
- `POST /fa/tree/get_update`

Selecting device `200132` changed the visible shell into a device-context view
but did not produce a new clearly isolated bounded backend command in this
capture.

The first clearly isolated deeper action happened at `Analyze`, which produced:

- `POST /afa/php/commands.php`
  - `cmd=GET_ANALYSIS_OPTIONS`
  - `SelectedFirewalls=200132`
  - `SelectedType=firewall`

## Analyze Code Handoff Follow-Up

A direct code trace on the appliance reduced that `Analyze` seam further:

- `/usr/share/fa/php/JSlib1768164240/home.js:242-274`
- function: `SubmitAnalysisHTMLOptionsRequest(...)`

That function:

- opens the Analyze dialog first with `openAnalysisDialog(...)`
- then posts `cmd=GET_ANALYSIS_OPTIONS` to `commands.php`
- expects HTML back and feeds it into `modifyAnalysisDialog(...)`

This means the first isolated `Analyze` handoff is still an options/dialog
fetch, not yet a full backend analysis run.

## Start Analysis Server-Side Boundary

The next step after that dialog is materially different:

- dialog population goes through
  `/usr/share/fa/php/commands/get_analysis_options.cmd.php`
- that path already calls:
  - `utils::RunFaServer("GET_ANALYZE_DATA", null, $sParams, true)`
- the dialog submit path in
  `/usr/share/fa/php/JSlib1768164240/home.js:447-512`
  posts:
  - `cmd=ANALYZE`
- `/usr/share/fa/php/commands/analyze.cmd.php`
  then calls:
  - `StartAnalysis(...)`
  - `utils::RunFaServer("ANALYZE", "", "")`

So there is now a clear support-useful boundary:

- `GET_ANALYSIS_OPTIONS` is still lightweight UI workflow plumbing
- `ANALYZE` is a real backend job launch with session work-dir state,
  progress files, and fa_server execution

## Interpretation

This reduces the post-home path in a support-useful way:

- the first usable shell is a dashboard-and-issues-center hydration path, not
  only `home.php` plus light Metro clues
- `DEVICES` mainly refreshes shell context and tree state in the bounded pass
- device selection changes the operator-visible context before a clearly named
  deeper backend command appears
- the first clean deeper operator action isolated so far is
  `Analyze -> GET_ANALYSIS_OPTIONS`
- that `Analyze` handoff is still only the analysis-options dialog fetch, not
  yet the heavier run-analysis workflow
- the real `Start Analysis` step is already beyond simple GUI-usable-state
  checking because it crosses into `ANALYZE` and `RunFaServer(...)`

So the next ASMS seam should not go back to bootstrap config theory.

The next best narrowing move is:

- keep the landing-shell model centered on dashboard hydration
- treat `Analyze` as the first clean deeper action path worth its own bounded
  follow-up, starting with the dialog/options fetch rather than assuming a full
  analysis run
- do not press `Start Analysis` as part of the core `ASMS UI is down` path
  without explicit intent, because that step launches real backend work on the
  appliance
- only split later subsystem paths when a reproduced browser minute proves that
  they are the real first stop point
