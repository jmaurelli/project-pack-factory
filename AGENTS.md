# Project Pack Factory Agent Context

This directory is the PackFactory instance for template-pack testing and
build-pack promotion.

## First Reads

1. `AGENTS.md`
2. `README.md`
3. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md` when the task needs product intent or scope
4. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TESTING-POLICY.md` when the task changes workflow tests
5. the target pack's `AGENTS.md`
6. the target pack's `project-context.md`
7. the target pack's `pack.json`

## Working Rules

- treat `templates/` as canonical source templates
- treat `build-packs/` as deployable derivatives, including retired fixtures that remain traversable for history
- treat `registry/` as the factory index for active and retired packs
- treat `deployments/` as the active environment pointer index only; retired build packs should not keep pointer files there
- prefer machine-readable state over arbitrary directory scans
- prefer `tools/validate_factory.py` for whole-factory validation and `tools/retire_pack.py` for lifecycle retirement mutations
- keep workflow tests minimal and follow the hard cap in `PROJECT-PACK-FACTORY-TESTING-POLICY.md`
