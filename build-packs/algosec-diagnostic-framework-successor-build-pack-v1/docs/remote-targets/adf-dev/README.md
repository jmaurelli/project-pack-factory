# ADF Successor Remote Codex Host

This directory stores the reviewed remote request surfaces for running the ADF
successor build-pack on `adf-dev`.

## Current Role

- Remote Codex host: `adf-dev`
- Remote Codex user: `adf`
- `adf-dev` host IP: `10.167.2.151`
- PackFactory remote target label: `adf-dev`
- Current lab target IP: `10.167.2.150`

In this model, PackFactory stages and runs the successor build-pack on
`adf-dev`, while the downstream Rocky 8 or appliance target remains a separate
observed runtime source.

Operational ownership is:

- PackFactory root = canonical source, tracker, readiness, and import authority
- `adf-dev` = operational runtime home
- target lab `10.167.2.150` = downstream runtime facts
- `adf-dev` at `10.167.2.151` also serves the successor-generated diagnostic
  pages consumed by support engineers

The normal return path is bounded exported runtime evidence, not a full copy of
the staged remote workspace.

## Request Files

- `remote-autonomy-run-request.json`
  backup-bootstrap staging request for the `adf-dev` runtime home
- `remote-autonomy-shallow-surface-map-run-request.json`
  target-backed shallow-surface-map request for the first real successor slice
- `remote-autonomy-test-request.json`
  PackFactory roundtrip wrapper that pulls and imports the target-backed
  shallow-surface-map evidence bundle
- `target-connection-profile.json`
  compatibility copy of the read-only target profile for the current lab target
  `10.167.2.150`

The canonical lab target profile lives at:

- `../algosec-lab/target-connection-profile.json`

Use the factory-root remote control plane to prepare and push the successor
build-pack for the target-backed run:

```bash
python3 tools/prepare_remote_autonomy_target.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-successor-build-pack-v1/docs/remote-targets/adf-dev/remote-autonomy-shallow-surface-map-run-request.json --output json
python3 tools/push_build_pack_to_remote.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-successor-build-pack-v1/docs/remote-targets/adf-dev/remote-autonomy-shallow-surface-map-run-request.json --output json
```

After the remote run creates or resumes the matching `.pack-state/autonomy-runs/<run-id>/`
tree, generate the shallow surface artifacts with mirrored return copies:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack generate-shallow-surface-map --project-root . --target-label 10.167.2.150 --target-connection-profile docs/remote-targets/algosec-lab/target-connection-profile.json --mirror-into-run-id algosec-diagnostic-framework-successor-build-pack-v1-adf-dev-shallow-surface-map-v1 --output json
```

That mirrored copy path is what lets the pack's bounded runtime-evidence
exporter return the target-backed `shallow-surface-map.json` and
`shallow-surface-summary.md` back to PackFactory root without copying the whole
remote workspace.

The target-backed CLI shape is intentionally explicit here so the official
remote request can be executed without local reinterpretation. The runner stays
read-only and bounded.

## Basic Backup Default

After the build-pack is staged on `adf-dev`, install the backup cron from the
staged pack root:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack install-backup-cron --project-root . --backup-root ~/.local/share/packfactory-backups/algosec-diagnostic-framework-successor-build-pack-v1 --schedule '17 3 * * *' --retain-count 7 --output json
```

That default keeps a second host-local backup outside the staged build-pack
directory so restaging the remote pack does not erase the backups.

The backup job is operational resilience only. It is not the canonical
PackFactory evidence-return path.

## Roundtrip Wrapper

Use the wrapper request when you want the PackFactory pull/import roundtrip to
bring bounded evidence back from the target-backed shallow-surface-map run:

```bash
python3 tools/run_remote_autonomy_test.py --factory-root /home/orchadmin/project-pack-factory --request-file build-packs/algosec-diagnostic-framework-successor-build-pack-v1/docs/remote-targets/adf-dev/remote-autonomy-test-request.json --output json
```

## Lab Posture

For this successor line, the current lab posture is operator-approved for more
aggressive discovery than a fragile customer environment would allow:

- `10.167.2.150` is a quickly deployable lab target
- bounded misconfiguration or lab breakage is not a material concern
- future distributed-architecture labs are expected and should be treated as
  likely later discovery surfaces
