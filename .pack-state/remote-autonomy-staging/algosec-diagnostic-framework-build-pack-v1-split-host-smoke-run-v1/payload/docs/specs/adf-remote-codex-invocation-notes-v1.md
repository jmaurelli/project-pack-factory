# ADF Remote Codex Invocation Notes V1

## Context

These notes capture what happened while invoking the remote Codex runtime on
the AlgoSec lab appliance during the first `Support Cockpit` implementation
cycle.

These notes now apply to the remote Codex host side of the ADF split-host
model.

Use `docs/specs/adf-remote-runtime-decoupling-plan-v1.md` as the current
runtime-topology note when the ADF build-pack runtime host and the target
application host are different systems. This note is narrower: it records how
to launch and manage remote Codex on the host that runs the staged ADF build
pack.

For the current split-host model, prefer the existing PackFactory remote
autonomy control plane rather than building a new ADF-specific launcher path.

Use these PackFactory-root tools first:

- `tools/prepare_remote_autonomy_target.py`
- `tools/push_build_pack_to_remote.py`
- `tools/run_remote_autonomy_loop.py`
- `tools/pull_remote_runtime_evidence.py`
- `tools/import_external_runtime_evidence.py`
- `tools/reconcile_imported_runtime_state.py`

Treat the ADF-specific `adf-remote-checkpoint-bundle.json` as supplementary
review metadata that rides alongside the existing PackFactory request,
staging, execution, export, pull, import, and reconcile workflow.

The appliance-shell observations later in this note remain useful as
historical debugging guidance, but they are not the primary control path for
the current `adf-dev` split-host model.

Current remote Codex host assignment:

- use `adf-dev` as the remote Codex host
- use the existing PackFactory-to-`adf-dev` SSH key authentication path as the
  default launcher transport
- treat the remote staged build-pack copy on `adf-dev` as the live execution
  workspace, while the local PackFactory build-pack copy remains the current
  precedence source of truth

In that split-host model, long-running ADF loops should stay on the remote
Codex host. When a bounded checkpoint, pause, or completed run is reached, use
the existing build-pack runtime-evidence export surface to hand back
`run-summary.json`, `loop-events.jsonl`, feedback memory, and accepted
artifacts to PackFactory root instead of depending on one continuously open
root-to-target session.

Use `docs/specs/adf-remote-runtime-decoupling-plan-v1.md` for the exact
current local-to-`adf-dev` checkpoint contract:

- local PackFactory pushes accepted source and instructions to `adf-dev`
- `adf-dev` returns bounded run artifacts and candidate changes at named
  checkpoints
- local PackFactory keeps precedence unless the checkpoint bundle explicitly
  accepts the pulled remote state

Use the named checkpoint manifest shape in that same note when a remote run is
ready to hand back candidate state:

- `adf-remote-checkpoint-bundle.json`

That manifest should point to the exported runtime-evidence bundle, raw run
artifacts, candidate source/docs changes, and the exact work-state or backlog
fields proposed for local acceptance.

Current emit rule:

- write it first under `.pack-state/autonomy-runs/<run-id>/`
- copy it into the export bundle under `artifacts/` when a runtime-evidence
  bundle is emitted
- refresh it on `paused_for_review`, `task_slice_complete`, `evidence_ready`,
  `blocked_boundary`, and `recovery_snapshot`

Target appliance:

- `10.167.2.150`

Staged build-pack root:

- `/root/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1`

## What Worked

- The remote appliance has a working Codex CLI and valid auth state.
- A small control test succeeded when the launcher used a non-login shell and a
  bounded timeout.
- The control test confirmed that remote Codex can:
  - read pack-local JSON state files
  - summarize the current build-pack state
  - write a result file under `/tmp`

## Observed Challenges

### 1. Appliance menu interferes with login-shell execution

The appliance drops into its interactive configuration menu when commands are
launched through a login shell. This leaked into the remote Codex session and
interrupted early file reads.

Observed mitigation:

- use `env -i ... /bin/bash --noprofile --norc` for the outer SSH launcher
- let remote Codex switch its internal file reads to `/bin/bash -c`

### 2. Early retries created duplicate sleeping Codex processes

The first real Support Cockpit launches were retried before the previous remote
processes were cleared. This left multiple `codex exec` processes sleeping on
the appliance and made progress harder to read.

Observed mitigation:

- `pkill -f "codex exec ... /tmp/adf_remote_codex_last.txt"` before relaunch
- use a single launcher script instead of long inline SSH quoting

### 3. Long implementation runs did not emit a final output file during the observation window

The small control test wrote `/tmp/adf_remote_codex_test_out.txt` successfully.
The longer real implementation run for `Support Cockpit` made visible progress
but did not produce `/tmp/adf_remote_codex_last.txt` during the observed
window.

This means:

- remote Codex was not fully blocked
- but final completion could not be confirmed from the expected output file

### 4. Inline SSH quoting was fragile

Long one-line SSH launches were error-prone and made retries harder to reason
about.

Observed mitigation:

- write the remote launcher as a small shell script under `/tmp`
- copy it to the appliance
- run that script with a clean non-login shell

## Confirmed Progress During The Real Support Cockpit Run

During the longer `Support Cockpit` run, remote Codex did all of the following
against the real staged build-pack:

- read the control-plane state files
- read the `Support Cockpit` direction note
- inspected the real `support-baseline.json` schema from
  `dist/candidates/algosec-lab-baseline/support-baseline.json`
- inspected the existing generated Starlight review artifact under
  `dist/candidates/algosec-lab-baseline/starlight-site`
- switched from `jq` to Python when `jq` was unavailable

Remote file timestamps also showed progress during the run:

- `src/algosec_diagnostic_framework_template_pack/starlight_site.py`
- `dist/candidates/algosec-lab-baseline/starlight-site/src/content/docs/playbooks/appliance-ui-is-down.md`
- `dist/candidates/algosec-lab-baseline/starlight-site/src/custom.css`

Those timestamps moved forward during the remote implementation attempt, which
is evidence that the remote Codex run did begin changing the real Support
Cockpit publishing path.

## Recommended Remote Invocation Pattern

Use this pattern for the next remote implementation cycle:

1. sync the intended local state and pack-local source files to the staged
   build-pack root
2. kill any prior matching `codex exec` processes for the same result path
3. launch from a small remote shell script instead of a long inline SSH command
4. use:
   - `env -i`
   - `HOME=/root`
   - `PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin`
   - `/bin/bash --noprofile --norc`
5. wrap the remote run in a bounded `timeout`
6. verify success with all of:
   - result file written under `/tmp`
   - changed pack-local file timestamps
   - rebuilt review artifact under `dist/candidates/algosec-lab-baseline/starlight-site`
   - live page check on `http://10.167.2.150:18082/`

## Launcher Update For The Appliance Bash Menu

During the horizontal dependency-path implementation cycle, the remote launcher
was tightened again to reduce interaction with the appliance shell/menu
behavior.

Working pattern:

- write the Codex task into a prompt file under `/tmp`
- write a small shell launcher under `/tmp`
- launch that script with:
  - `env -i`
  - `HOME=/root`
  - an explicit minimal `PATH`
  - `nohup`
  - `/bin/bash --noprofile --norc`
- redirect launcher output to a dedicated log file under `/tmp`
- let the script itself write the Codex result to a separate dedicated result
  file under `/tmp`

Observed result:

- the remote Codex process tree started cleanly under the staged build-pack
- the result file appeared immediately, which is a strong sign that the launch
  bypassed the interactive appliance menu successfully

Current preference:

- prefer a small `/tmp` launcher script over inline SSH command strings
- prefer `/bin/bash --noprofile --norc` over login-shell execution for remote
  Codex on the appliance
- keep the prompt file, launcher log, and result file separated so retries are
  easier to reason about

## Not Sufficient For Task Completion

These signals are orchestration evidence, not iteration-loop completion proof:

- launcher success
- result-file creation
- moved file timestamps
- rebuilt review artifacts
- live page checks
- clean restaging and relaunch

Those signals only prove that the remote path is usable.

For `build_adf_autonomous_iteration_loop`, they are not sufficient on their
own unless they are paired with:

- the loop contract note at
  `docs/specs/adf-autonomous-iteration-loop-completion-boundary-v1.md`
- the recorded pack-local versus future factory split
- a pilot iteration evidence artifact that records a real ADF-local outcome
  beyond bookkeeping

## Revised Workflow For ASMS Investigative Authoring

During the March 25, 2026 ASMS UI system-thinking cycle, ADF also tried the
factory-level bounded remote autonomy wrapper:

- `python3 tools/run_remote_autonomy_loop.py ...`

That structured path worked as designed, but it stopped with:

- `terminal_outcome = boundary_violation`
- `terminal_reason = unauthorized_writable_surface`

The recorded boundary violations included generated candidate artifacts and
`src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`.

This matters because the current ASMS trajectory is not a starter-backlog-only
autonomy proof. It is a guided investigative authoring loop that needs all of
the following:

- live browser and log investigation on the real appliance
- pack-local source edits
- regeneration of appliance-backed artifacts
- operator-guided systems-thinking refinement

So the revised workflow for the current ADF phase is:

1. use the PackFactory-root remote request, staging, execution, export, pull,
   import, and reconcile workflows rather than inventing pack-local substitutes
2. use the staged remote workspace for a guided remote Codex investigation run
   against the named ADF task when the current slice needs appliance-backed
   investigation and pack-local authoring
3. keep ADF notes focused on launcher, browser, and artifact-shape constraints,
   while PackFactory root remains the owner of control-plane workflow semantics
4. update local pack state and validate locally after the PackFactory-root
   workflow returns evidence

Do not treat this note as authority for remote-session control-plane policy.
If it ever diverges from PackFactory-root request/export/pull/import/reconcile
workflows, PackFactory root wins and this note should be updated.

Do not use `run_remote_autonomy_loop.py` as the primary execution path for the
current ASMS investigative authoring cycles unless the goal is explicitly a
bounded starter-backlog autonomy proof rather than guided subsystem
investigation and source-authoring work.

## Browser Wait Correction For ASMS UI Investigation

During the March 25, 2026 fresh-session isolation pass, a more specific remote
browser-method lesson became clear for the `ASMS UI is down` path:

- do not wait for Playwright `networkidle` on the ASMS home shell

On this appliance, the post-login home shell keeps enough background activity
alive that `networkidle` can hang or stall an otherwise healthy investigation.
That creates a false blocker: the browser session may already have reached a
usable `AlgoSec - Home` shell while the automation is still waiting for a page
state that never arrives.

Use this corrected pattern instead:

- launch a fresh browser context or incognito session
- authenticate normally
- use bounded waits plus visible-shell checks rather than `networkidle`
- treat these as the main success markers:
  - final URL reaches `/afa/php/home.php`
  - page title is `AlgoSec - Home`
  - visible body markers such as `HOME`, `DEVICES`, `DASHBOARDS`, `GROUPS`,
    `MATRICES`, `Firewall Analyzer`, `FireFlow`, `AlgoSec Cloud`, `ObjectFlow`,
    and `AppViz`
- capture request and response timing, cookies, and visible-shell markers
  without waiting for the page to go fully idle

Why this matters:

- it keeps the remote Codex investigation aligned with the real support
  question, which is first usable home-shell availability, not complete browser
  quiet

## Route-Owner Split For The Remaining Config Family

During the later March 26, 2026 narrowing pass, one more systems-thinking
lesson became explicit for the `ASMS UI is down` path:

- the remaining `config` family is not owned by one seam

Carry forward these facts:

- Apache owns browser-facing `/afa/external` and `/afa/api/v1` proxy families
- PHP `RestClient` also talks directly to `http://127.0.0.1:8080/afa`
- `RestClient::getConfig($param)` issues direct `/config/...` requests
- the login path already uses that direct helper in
  `SuiteLoginSessionValidation.php`
- the browser UI bundle separately owns `/afa/api/v1/config`

What this changes:

- do not treat the remaining `config` question as only an Apache proxy-family
  problem
- do not repeat family-wide Apache denies as the default next move
- separate browser-owned config requests from PHP-owned direct Metro config
  reads before planning the next deeper mutation

Use these pack-local notes next:

- `.pack-state/remote-codex/asms-ui-config-owner-split-pass-20260326.md`
- `docs/specs/asms-ui-config-owner-split-plan-v1.md`

## Browser Tooling Note From The Correlation Pass

During the March 26, 2026 read-only correlation run, one more remote-launch
detail became explicit:

- Playwright Python was available inside the remote Codex environment
- Playwright's bundled browser cache was missing
- system Chromium still worked through
  `executable_path='/usr/bin/chromium-browser'`

Why this matters:

- remote Codex can still run bounded browser-backed investigation on this
  appliance without installing browser bundles during the session
- future read-only investigation prompts should prefer the system Chromium
  binary first when the bundled Playwright browsers are absent
  quiet
- it prevents the fresh-session isolation loop from stalling on the page's
  normal background chatter
- it should be treated as the default browser method for the current ASMS
  post-login and Metro-clue investigations unless a later path proves it needs
  a different success condition

## Current Conclusion

Remote Codex invocation on the lab appliance is viable, but it is not yet
fully smooth.

The main risk is not Codex availability itself. The main risk is the appliance
shell behavior and the need for disciplined relaunch handling.

For ADF, the right current posture is:

- keep using remote Codex
- keep PackFactory target prep and staging as the default control path
- keep guided remote Codex authoring separate from the bounded autonomy loop
  when the work needs investigative source edits and appliance-backed artifact
  regeneration
- keep launch scripts explicit and bounded when guided remote Codex is the
  active path
- record retries and stale-process cleanup as normal orchestration work

## Controlled Mutation Experiments

The next ADF phase now includes a narrower kind of remote work:

- lab-only, tightly bounded mutation experiments at a proven control seam

Use these rules for that mode:

- treat read-only investigation as the default until the likely seam is already
  narrowed
- mutate one surface at a time
- prefer a temporary Apache override file over editing the base config inline
- prepare rollback before applying the mutation
- use one bounded browser reproduction after each mutation
- capture same-minute Apache and downstream logs before interpreting the
  result
- revert immediately after the one experiment slice completes

Canonical references:

- reusable pattern:
  `docs/specs/adf-controlled-lab-mutation-experiment-pattern-v1.md`
- current ASMS seam plan:
  `docs/specs/asms-ui-apache-metro-proxy-isolation-plan-v1.md`
