# JSON Health Checker Template Pack

PackFactory-native template pack `json-health-checker-template-pack`.

This template is aimed at a tiny task-shaped runtime surface: read one JSON
object, verify that required fields exist, and return a clear pass/fail result.

## Commands

```bash
PYTHONPATH=src python3 -m json_health_checker_template_pack --help
PYTHONPATH=src python3 -m json_health_checker_template_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m json_health_checker_template_pack benchmark-smoke --project-root . --output json
PYTHONPATH=src python3 -m json_health_checker_template_pack check-json --input ./sample.json --require id --require status --output json
```
