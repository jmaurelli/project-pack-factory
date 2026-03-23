# Config Drift Checker

`config-drift-checker-build-pack` packages a deterministic JSON/YAML config
drift checker.

Its primary user-facing command is `check-drift`. Given a baseline config and a
candidate config, it emits a machine-readable result with:

- a policy status: `pass`, `review_required`, or `fail`
- a short summary
- a normalized list of findings
- per-finding severity and reason fields

## Install

From source:

```bash
python3 -m pip install .
```

From a built wheel:

```bash
python3 -m pip install dist/exports/config_drift_checker_build_pack-0.1.0-py3-none-any.whl
```

## Use

Basic comparison:

```bash
check-drift --baseline ./baseline.json --candidate ./candidate.yaml --output json
```

With rules:

```bash
check-drift \
  --baseline ./baseline.json \
  --candidate ./candidate.yaml \
  --rules ./rules.yaml \
  --fail-on blocking \
  --output json
```

Rules file shape:

```yaml
ignore_paths:
  - metadata.last_updated
allowed_exceptions:
  - services.api.image_tag
severity_overrides:
  services.api.replicas: informational
  feature_flags.new_checkout: blocking
```

Exit codes:

- `0`: `pass`
- `2`: `review_required`
- `1`: `fail`

Example JSON fields:

```json
{
  "status": "review_required",
  "summary": "Drift check found 2 warning changes and 0 blocking changes.",
  "findings": [
    {
      "path": "services.api.replicas",
      "change_type": "changed",
      "severity": "warning",
      "reason": "Changed value at services.api.replicas."
    }
  ],
  "counts": {
    "informational": 0,
    "warning": 2,
    "blocking": 0,
    "total_findings": 2
  }
}
```

## PackFactory

This repository also carries the tool as a PackFactory build-pack, so it keeps
pack-local validation and benchmark entrypoints:

```bash
PYTHONPATH=src python3 -m config_drift_checker_build_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m config_drift_checker_build_pack benchmark-smoke --project-root . --output json
```
