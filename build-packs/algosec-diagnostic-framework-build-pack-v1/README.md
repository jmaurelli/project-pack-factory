# AlgoSec Diagnostic Framework Template Pack

PackFactory-native template pack `algosec-diagnostic-framework-template-pack`.

## Commands

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack --help
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack benchmark-smoke --project-root . --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack generate-support-baseline --project-root . --target-label algosec-lab --output json
PYTHONPATH=src python3 -m algosec_diagnostic_framework_template_pack generate-support-baseline --project-root . --target-label algosec-lab --use-target-connection --output json
```

## First ADF Slice

The first ADF slice generates machine-readable baseline artifacts under
`dist/candidates/adf-baseline/`:

- `runtime-evidence.json`
- `service-inventory.json`
- `support-baseline.json`
- `support-baseline.html`

JSON remains canonical. The HTML file is a thin support-facing render of the
same baseline data.

When you use `--use-target-connection`, the target-backed baseline now defaults
to `dist/candidates/adf-target-profile-baseline/` so local-host and real-target
artifacts do not get mixed together.
