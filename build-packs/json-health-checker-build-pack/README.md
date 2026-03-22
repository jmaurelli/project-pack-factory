# JSON Health Checker Build Pack

PackFactory-native build pack `json-health-checker-build-pack`, materialized
from `json-health-checker-template-pack`.

This build pack is aimed at a tiny task-shaped runtime surface: read one JSON
object, verify that required fields exist, and return a clear pass/fail result.
It is the deployable/testing derivative of the source template, not the source
template itself.

## Commands

```bash
PYTHONPATH=src python3 -m json_health_checker_template_pack check-json --input ./sample.json --require id --require status --output json
PYTHONPATH=src python3 -m json_health_checker_template_pack --help
PYTHONPATH=src python3 -m json_health_checker_template_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m json_health_checker_template_pack benchmark-smoke --project-root . --output json
```

The internal Python module path still uses the inherited template lineage name
`json_health_checker_template_pack`, but the PackFactory object represented here
is the build pack `json-health-checker-build-pack`.
