# Project Pack Factory

Agent-optimized PackFactory instance for template-pack testing, build-pack
promotion, and retirement-aware lifecycle management.

## Product Intent

The product-level definition of what this factory is for lives in:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TESTING-POLICY.md`

At a high level, this factory exists to produce and manage agent-optimized
software build-packs with deterministic traversal, machine-readable lifecycle
state, benchmark evidence, and restart-aware runtime support.

The factory also intentionally keeps workflow testing small and high-signal
rather than aiming for broad coverage.

## Startup Targeting

- stay at the factory root first
- inspect `registry/` to identify likely candidate packs from machine-readable state
- summarize the candidate packs and ask the operator which one to use before entering any pack
- use `deployments/` only when the task explicitly concerns the small JSON records that show which build-pack is currently assigned to an environment like `testing`, `staging`, or `production`
- do not infer a target pack from directory names alone

## Retirement-Aware Behavior

- `registry/` is the source of truth for active and retired pack entries.
- `deployments/` is the environment assignment board. It records which build-pack is currently assigned to each environment using small JSON records.
- It is not the deployed app contents and it is not the full deployment process.
- If an environment has no build-pack record yet, that just means nothing is assigned there right now.
- Retired build packs are removed from this area.
- `registry/promotion-log.json` preserves retired events as historical evidence, even for fixtures that are no longer deployment candidates.
- The initial retired build-pack fixtures are `ai-native-codex-build-pack` and `agent-memory-first-build-pack`.

## Operator Tools

- `python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory`
- `python3 tools/retire_pack.py --factory-root /home/orchadmin/project-pack-factory --pack-id <pack-id> --retired-by orchadmin --reason "<reason>"`
- `python3 tools/run_workflow_eval.py --factory-root /home/orchadmin/project-pack-factory --output json`
