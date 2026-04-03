# AlgoSec Diagnostic Framework Successor Template Pack

PackFactory-native template pack `algosec-diagnostic-framework-successor-template-pack`.

## Commands

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack --help
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack benchmark-smoke --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack import-docpack-hints --project-root . --ssh-destination adf-dev --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack generate-shallow-surface-map --project-root . --target-label local-host --output json
```

## First ADF Successor Slice

The first bounded successor slice writes artifacts under
`dist/candidates/adf-shallow-surface-map-first-pass/`:

- `shallow-surface-map.json`
- `shallow-surface-summary.md`

The JSON map is the canonical first-wave product layer. The Markdown summary is
derived from that map for fast operator review.

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
