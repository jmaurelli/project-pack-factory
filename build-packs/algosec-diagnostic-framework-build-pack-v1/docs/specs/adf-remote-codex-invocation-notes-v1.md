# ADF Remote Codex Invocation Notes V1

## Context

These notes capture what happened while invoking the remote Codex runtime on
the AlgoSec lab appliance during the first `Support Cockpit` implementation
cycle.

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

## Current Conclusion

Remote Codex invocation on the lab appliance is viable, but it is not yet
fully smooth.

The main risk is not Codex availability itself. The main risk is the appliance
shell behavior and the need for disciplined relaunch handling.

For ADF, the right current posture is:

- keep using remote Codex
- keep launch scripts explicit and bounded
- record retries and stale-process cleanup as normal orchestration work
