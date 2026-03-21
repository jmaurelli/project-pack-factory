# Project Pack Factory Agent Context

This directory is the PackFactory instance for template-pack testing and
build-pack promotion.

In plain language: this repo manages reusable project-pack templates, the
derived build-packs created from them, and the testing/deployment state around
those packs.

## Concierge Startup

When the operator says `load AGENTS.md`, do not respond with a file-load
acknowledgment alone.

Treat that request as a concierge startup prompt:

- read the current state from `registry/templates.json`,
  `registry/build-packs.json`, and recent relevant entries in
  `registry/promotion-log.json`
- treat `registry/*.json` as the source of truth for live pack state, not
  prose summaries or directory listings
- consult `deployments/` only when the startup brief needs to explain which
  build-pack is currently assigned to an environment
- summarize what this repo is in plain language
- summarize where work currently stands
- identify active, recently completed, and retired packs from current factory
  state
- give each relevant pack a very short operator-friendly phrase plus its
  current role, stage, recent outcome, or environment assignment
- summarize recent relevant factory work using PackFactory verbs like
  `retired`, `materialized`, `promoted`, and `pipeline_executed`
- include a short retirement summary when retired packs help explain the
  current baseline
- if recent repo-level tooling or doc work matters to the current task, check
  the latest git commits and mention the concrete date
- offer a short list of practical next-step options at the administrator level,
  based on the discovered pack state, such as reviewing candidate packs,
  continuing active testing work, creating a template through the supported
  planning/creation workflow, materializing a build-pack, promoting a ready
  build-pack, reviewing deployment assignments, or retiring historical work
  that should stay frozen
- end by asking what the operator wants to do next

Keep the reply project-oriented and human-facing. Do not default to an
internal “key points I’m carrying forward” style.

## First Reads

1. `AGENTS.md`
2. `README.md`
3. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md` when the task needs product intent or scope
4. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TESTING-POLICY.md` when the task changes workflow tests
5. `registry/templates.json`, `registry/build-packs.json`, and recent relevant entries in `registry/promotion-log.json` to identify candidate packs and recent workflow state from machine-readable sources
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
- for startup/orientation requests, prefer a current-state summary over a file-centric acknowledgment
- for startup/orientation requests, summarize recent work from `registry/promotion-log.json` first and use recent git commits only as a fallback for repo-level changes
- inspect machine-readable state first, summarize likely candidate packs, and ask the operator to confirm the intended target before entering a pack
- only bypass confirmation when the operator has already named the pack explicitly
- prefer `tools/validate_factory.py` for whole-factory validation and `tools/retire_pack.py` for lifecycle retirement mutations
- keep workflow tests minimal and follow the hard cap in `PROJECT-PACK-FACTORY-TESTING-POLICY.md`
- do not present brand-new template creation as an already-implemented
  top-level action unless the current factory tooling actually supports it
