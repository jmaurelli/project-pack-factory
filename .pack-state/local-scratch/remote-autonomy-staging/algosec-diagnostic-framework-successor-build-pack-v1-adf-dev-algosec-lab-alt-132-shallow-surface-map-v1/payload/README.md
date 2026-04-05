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
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack record-idea-note --project-root . --title "<title>" --summary "<summary>" --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack update-idea-note --project-root . --note-id "<note-id>" --review-state in_review --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack list-idea-notes --project-root . --limit 20 --output json
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
  fast triage guidance for frontline support work
- `runtime-cookbook-guide.md`
  slower learning guidance that preserves the richer runtime story, product to
  runtime translation, and packet-backed interpretation for future reuse

The current reviewed frontline playbook shape is also recorded in:

- `docs/specs/adf-successor-triage-playbook-path-model-v1.md`

That note captures the operator-reviewed rule that the CLI service dashboard is
only a front-door filter for core `ms-*` service `up/down/not responding`
state, and that real diagnostic depth usually starts in `Logs` rather than in
service-state interpretation alone.

The current review-only publication planning surfaces are:

- `docs/specs/adf-successor-starlight-review-shell-plan-v1.md`
- `docs/specs/adf-successor-adf-dev-headless-browser-host-plan-v1.md`
- `docs/specs/adf-successor-site-map-and-wireframe-review-v1.md`

Together those notes capture the first concrete successor Starlight shell
direction, the current `adf-dev` browser-host installation plan, and the
initial site map plus wireframe-level page skeletons before code moves.

## Collaborative Idea Log

The successor now also carries one machine-readable collaborative note surface:

- `notes/idea-log.json`

Use this for product ideas, behavioral notes, operator theories, and cookbook
candidates that should stay attached to the build-pack without becoming active
backlog items yet.

This log is meant to stay compatible with the current tracking and memory
model:

- backlog and work-state remain execution truth
- `.pack-state/agent-memory/` remains restart memory
- `notes/idea-log.json` is the collaborative note layer for later review

Use `update-idea-note` when a note moves from `unreviewed` to `in_review`,
`reviewed`, `converted_to_task`, or when its lifecycle should be archived
without deleting it.

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

## Parallel Standalone Deepening

While new distributed architectures are still being built, the successor can
keep learning from stable standalone targets through the existing
PackFactory-owned `adf-dev` roundtrip path.

The concrete plan is recorded in:

- `docs/specs/adf-successor-parallel-standalone-deepening-autonomy-loop-plan-v1.md`

That plan separates:

- live standalone knowledge capture on the long-lived successor pack
- active-task continuity and checkpoint use on the same pack
- fresh-pack proving-ground autonomy exercises used only for autonomy
  hardening, not as standalone runtime truth
