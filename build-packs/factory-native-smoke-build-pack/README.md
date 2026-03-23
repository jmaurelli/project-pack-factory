# Factory Native Smoke Build Pack

PackFactory-native build pack `factory-native-smoke-build-pack`, materialized
from `factory-native-smoke-template-pack`.

This build pack exists as a deliberately small workflow check: validate the
pack contract, run one tiny smoke benchmark, and keep the resulting readiness
and eval surfaces easy for the next agent to inspect.

## Commands

```bash
PYTHONPATH=src python3 -m factory_smoke_pack --help
PYTHONPATH=src python3 -m factory_smoke_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m factory_smoke_pack benchmark-smoke --output json
```
