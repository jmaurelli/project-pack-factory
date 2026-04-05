# AlgoSec Lab Target Profile

This directory holds the successor build-pack's read-only SSH target profile
for `adf-dev` to inspect the current lab target.

Current pinned target:

- `10.167.2.150`

The successor pack can use the profile in this directory to run
`generate-shallow-surface-map` over SSH instead of only against the local host:

```bash
PYTHONPATH=src python3 -m algosec_diagnostic_framework_successor_template_pack generate-shallow-surface-map --project-root . --target-label 10.167.2.150 --target-connection-profile docs/remote-targets/algosec-lab/target-connection-profile.json --output json
```

The profile is intentionally read-only. It is only for bounded observation of
the target lab and should not be treated as a general-purpose automation
surface.
