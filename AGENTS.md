# Project Pack Factory Agent Context

This directory is the PackFactory instance for template-pack testing and
build-pack promotion.

## First Reads

1. `AGENTS.md`
2. `README.md`
3. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md` when the task needs product intent or scope
4. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TESTING-POLICY.md` when the task changes workflow tests
5. `registry/templates.json` and `registry/build-packs.json` to identify candidate packs from machine-readable state
6. `deployments/` only when the task explicitly concerns the small JSON records that show which build-pack is currently assigned to an environment like `testing`, `staging`, or `production`
7. after the operator confirms the intended pack, that pack's `AGENTS.md`
8. after the operator confirms the intended pack, that pack's `project-context.md`
9. after the operator confirms the intended pack, that pack's `pack.json`

## Working Rules

- treat `templates/` as canonical source templates
- treat `build-packs/` as deployable derivatives, including retired fixtures that remain traversable for history
- treat `registry/` as the factory index for active and retired packs
- treat `deployments/` as the environment assignment board, not as the deployed app contents or the full deployment workflow; retired build packs should not keep files there
- do not auto-select a target pack from directory contents alone
- inspect machine-readable state first, summarize likely candidate packs, and ask the operator to confirm the intended target before entering a pack
- only bypass confirmation when the operator has already named the pack explicitly
- prefer `tools/validate_factory.py` for whole-factory validation and `tools/retire_pack.py` for lifecycle retirement mutations
- keep workflow tests minimal and follow the hard cap in `PROJECT-PACK-FACTORY-TESTING-POLICY.md`
