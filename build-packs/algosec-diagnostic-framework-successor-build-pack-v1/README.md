# AlgoSec Diagnostic Framework Successor Template Pack

PackFactory-native template pack `algosec-diagnostic-framework-successor-template-pack`.

## Commands

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack --help
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack benchmark-smoke --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack create-backup-snapshot --project-root . --backup-root /tmp/adf-successor-backups --retain-count 2 --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack install-backup-cron --project-root . --backup-root ~/.local/share/packfactory-backups/algosec-diagnostic-framework-successor-build-pack-v1 --schedule '17 3 * * *' --retain-count 7 --dry-run --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack import-docpack-hints --project-root . --ssh-destination adf-dev --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack generate-shallow-surface-map --project-root . --target-label local-host --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack generate-shallow-surface-map --project-root . --target-label rocky8-lab --mirror-into-run-id <run-id> --output json
```

## First ADF Successor Slice

The first bounded successor slice writes artifacts under
`dist/candidates/adf-shallow-surface-map-first-pass/`:

- `shallow-surface-map.json`
- `shallow-surface-summary.md`
- `diagnostic-playbook.md`
- `runtime-cookbook-guide.md`

The JSON map is the canonical first-wave product layer. The Markdown summary is
derived from that map for fast operator review.

The additional engineer-consumable views keep the machine-readable-first
contract intact while making the content easier to use under support pressure:

- `diagnostic-playbook.md`
  fast triage guidance that turns the current bounded packets into route-owner
  hints, first checks, stop rules, and next-step choices
- `runtime-cookbook-guide.md`
  slower learning guidance that preserves the richer runtime story, product to
  runtime translation, and packet-backed interpretation for future reuse

## ASMS Doc-Pack Hint Layer

The build-pack can also import a bounded local hint artifact under
`dist/candidates/adf-docpack-hints/`:

- `asms-docpack-hints.json`

That artifact is distilled from the remote ASMS doc pack on `adf-dev` and is
meant only to improve term recognition, product-area hinting, and port-aware
prioritization during the shallow surface map pass.

The imported doc-pack hint layer does not replace runtime evidence. If the hint
artifact exists at the default path, `generate-shallow-surface-map` loads it
automatically.

## Remote-Owned Runtime

The successor now uses a remote-owned runtime, thin local canonical return
model. The reviewed contract is in:

- `docs/specs/adf-successor-remote-owned-runtime-thin-local-canonical-return-contract-v1.md`

In practice that means:

- `adf-dev` is the operational runtime home
- the Rocky 8 or appliance lab at `10.167.2.150` is the downstream inspection target
- `adf-dev` is currently reachable at `10.167.2.151` and the same host serves
  the support-facing diagnostic pages for successor-generated content
- PackFactory root remains canonical for source, tracker, readiness, and
  runtime-evidence import
- the normal return path is bounded exported proof, not the whole staged remote
  workspace

For target-backed shallow-surface-map runs tied to a PackFactory `run_id`, use
`--mirror-into-run-id <run-id>` so the generated JSON and Markdown artifacts
are copied into `.pack-state/autonomy-runs/<run-id>/artifacts/...`
before export.

The current lab posture is intentionally permissive for discovery:

- `10.167.2.150` is a quickly redeployable lab
- bounded misconfiguration or temporary breakage is acceptable there
- later distributed-architecture labs are expected as future expansion targets

## Basic Remote Backup Surface

The successor build-pack now carries a small remote backup surface for the
staged `adf-dev` copy. The pack can create timestamped tarball snapshots and
install a marked user-level cron block that runs a backup daily.

Recommended remote defaults:

- backup root:
  `~/.local/share/packfactory-backups/algosec-diagnostic-framework-successor-build-pack-v1`
- schedule: `17 3 * * *`
- retention: `7`
- backup-bootstrap staging request:
  `docs/remote-targets/adf-dev/remote-autonomy-run-request.json`
- target-backed shallow-surface-map request:
  `docs/remote-targets/adf-dev/remote-autonomy-shallow-surface-map-run-request.json`

The backup job protects the staged remote runtime copy. It is not a substitute
for returning bounded runtime evidence to PackFactory root.
