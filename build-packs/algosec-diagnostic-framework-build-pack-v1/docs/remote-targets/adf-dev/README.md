# ADF Dev Remote Codex Host

This directory stores the current PackFactory remote-runtime request surfaces
for ADF in the split-host model.

## Current Role

- Remote Codex host: `adf-dev`
- Remote Codex user: `adf`
- PackFactory remote target label: `adf-dev`

In this model, PackFactory stages and runs the ADF build pack on `adf-dev`.

The downstream appliance is still separate:

- Downstream target label: `algosec-lab`
- Downstream target host: `10.167.2.150`
- Downstream target user: `root`

In plain language:

- `adf-dev` is where Codex runs
- `algosec-lab` is what the remote ADF runtime investigates

## Downstream Target Connection Rule

The staged build pack on `adf-dev` is expected to connect onward to the target
server with the existing target-side tooling and SSH key authentication.

Current expectation:

- `adf-dev` can reach the target appliance through key-based SSH
- target SSH details are resolved through the configured SSH aliases and keys,
  not by storing secrets in the build pack
- target-facing connectivity belongs to the ADF runtime on `adf-dev`, not to
  PackFactory root

Important target nuance:

- the AlgoSec appliance can drop into an interactive menu on login
- target-facing shell work should prefer a non-login shell pattern such as
  `env -i ... /bin/bash --noprofile --norc`
- if the target session needs a launcher script, write a small bounded script
  and run that instead of relying on long inline SSH quoting

Connection stability rule:

- the `adf-dev -> target` hop should fail closed rather than hang
- use non-interactive key auth, bounded timeouts, and small bounded retries
- do not let one target-facing shell or browser wait stall the whole remote
  loop indefinitely
- when target reachability degrades, record the event, checkpoint, and either
  recover or stop at a named boundary

Secondary target-local Codex rule:

- direct `adf-dev -> target` SSH remains the default target communication path
- target-local Codex on the appliance may be used as a bounded delegated worker
  when local crawling is more natural than many remote shell calls
- `adf-dev` still owns the ADF runtime, generated-content server, checkpoints,
  and return path to PackFactory root
- target-local Codex does not become the canonical build-pack home or the
  PackFactory-facing source of truth

Delegation tiers:

- `observe_only`
  Use this as the default. The target-local worker gathers evidence and
  findings without intentionally changing target state.
- `guided_change_lab`
  Use this only because the target is a disposable lab environment. The
  target-local worker may make bounded local changes, restart services, compare
  before-and-after results, and must explicitly report any mutations back to
  `adf-dev`.

Use `docs/remote-targets/algosec-lab/README.md` and
`docs/specs/adf-remote-codex-invocation-notes-v1.md` for the detailed target
menu and shell-behavior notes.

## Current Request Files

- `remote-autonomy-run-request.json`
  The current PackFactory root to `adf-dev` remote run request.
- `remote-autonomy-test-request.json`
  The current bounded roundtrip wrapper request for pullback testing.

The wrapper request ships with `import_bundle=false` on purpose so the default
path stays fail-closed while local PackFactory still has precedence.

## Current Use Rules

Use the current PackFactory remote control plane:

- `tools/prepare_remote_autonomy_target.py`
- `tools/push_build_pack_to_remote.py`
- `tools/run_remote_autonomy_loop.py`
- `tools/pull_remote_runtime_evidence.py`
- `tools/import_external_runtime_evidence.py`
- `tools/reconcile_imported_runtime_state.py`

Important boundary:

- `run_remote_autonomy_loop.py` is still a bounded starter-backlog loop
- it will treat source or doc edits outside its allowed writable surfaces as
  boundary violations
- that makes it appropriate for continuity proofs and bounded remote smoke
  runs
- it is not yet the full authoring loop for open-ended ADF subsystem work

For guided ADF investigative authoring, still reuse the PackFactory request,
staging, pull, import, and reconcile workflow, but do not pretend the current
bounded loop runner already authorizes the whole ADF source-authoring cycle.

## Typical Commands

Prepare and stage the remote workspace:

```bash
python3 tools/prepare_remote_autonomy_target.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-build-pack-v1/docs/remote-targets/adf-dev/remote-autonomy-run-request.json --output json
python3 tools/push_build_pack_to_remote.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-build-pack-v1/docs/remote-targets/adf-dev/remote-autonomy-run-request.json --output json
```

Run the bounded remote loop when the task fits the current starter-backlog
boundary:

```bash
python3 tools/run_remote_autonomy_loop.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-build-pack-v1/docs/remote-targets/adf-dev/remote-autonomy-run-request.json --output json
```

Run the bounded roundtrip wrapper and pull the bundle back without importing
it into local canonical state:

```bash
python3 tools/run_remote_autonomy_test.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-build-pack-v1/docs/remote-targets/adf-dev/remote-autonomy-test-request.json --output json
```

Generate and serve the current human-facing content directly from `adf-dev`:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack generate-support-baseline --project-root . --target-label algosec-lab --use-target-connection --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack generate-starlight-site --project-root . --artifact-root dist/candidates/adf-target-profile-baseline --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack serve-generated-content --project-root . --artifact-root dist/candidates/adf-target-profile-baseline --host 0.0.0.0 --port 18082
```

Serving rule:

- if a built `starlight-site/dist/` exists under the selected artifact root,
  serve that static site
- otherwise serve the artifact root itself and route `/` to
  `support-baseline.html` when no `index.html` exists

Run the pack-local target connection helpers from the staged build pack on
`adf-dev`:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-preflight --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-heartbeat --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-shell-command --project-root . --command "hostname" --output json
```

Those helpers read the default target profile from:

- `docs/remote-targets/algosec-lab/target-connection-profile.json`

Use them to keep target reachability, menu-safe shell launch, and bounded
command timing inside the build pack rather than in ad hoc terminal history.

Important generation rule:

- `generate-support-baseline` only targets the downstream AlgoSec appliance
  when `--use-target-connection --target-profile-path docs/remote-targets/algosec-lab/target-connection-profile.json`
  is supplied
- without those flags, it baselines the host where the command is running

If a task slice is delegated to target-local Codex instead, treat that as a
secondary mode:

- start from `adf-dev`
- keep the delegated slice bounded
- choose the delegation tier explicitly
- pull the returned evidence back to `adf-dev`
- review and checkpoint it on `adf-dev` before it is exported or imported

Preferred delegated result bundle on the target:

- `.pack-state/delegated-codex-runs/<delegation-run-id>/`
- `delegated-task-request.json`
- `delegated-task-result.json`
- `commands.jsonl`
- `findings.md`
- `artifacts/`
- `candidate-diffs/` only when the delegated slice explicitly allows changes

Current staged-pack command flow for that delegated mode:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-delegation-request --project-root . --run-id <run-id> --task-id <task-id> --delegation-tier observe_only --scope-summary "..." --allowed-target /etc/httpd --expected-output delegated-task-result.json --expected-output commands.jsonl --expected-output findings.md --generated-by <actor> --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-delegation-launch-codex --project-root . --run-id <run-id> --delegation-run-id <delegation-run-id> --timeout-seconds 900 --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-delegation-pull --project-root . --run-id <run-id> --delegation-run-id <delegation-run-id> --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack target-delegation-review --project-root . --run-id <run-id> --delegation-run-id <delegation-run-id> --checkpoint-reason evidence_ready --review-outcome accepted --generated-by <actor> --output json
```

That flow keeps PackFactory root as the orchestrator for staging and return,
keeps `adf-dev` as the ADF runtime and delegation owner, and uses target-local
`codex exec` only inside the bounded delegated bundle contract.

## Checkpoint Note

When the remote ADF runtime reaches a named checkpoint, it should emit
`adf-remote-checkpoint-bundle.json` into the run root and copy that file into
the runtime-evidence export bundle. That ADF checkpoint bundle is supplementary
review metadata on top of the existing PackFactory request, staging, execution,
pull, import, and reconcile manifests.
