# Project Pack Factory

Agent-optimized PackFactory instance for template-pack testing, build-pack
promotion, and retirement-aware lifecycle management.

In plain language: this repo is the factory we use to plan and manage reusable
project-pack templates, turn approved templates into testable/deployable
build-packs, and track what is currently active, under test, retired, or
assigned to an environment.

## Operator Startup

When an operator asks to `load AGENTS.md`, the expected response should:

- explain the repo in plain language
- summarize the current live state from `registry/`, `deployments/`, and recent
  relevant activity
- treat `registry/*.json` as source of truth for live pack state, not prose
  summaries or directory listings
- consult `deployments/` only when the startup brief needs to explain which
  build-pack is currently assigned to an environment
- name the active template packs and active build-packs
- give each active pack a short human-friendly phrase plus its current role,
  stage, or environment assignment
- summarize recent relevant work using PackFactory workflow verbs such as
  `retired`, `materialized`, `promoted`, and `pipeline_executed`
- include a short retirement summary when it helps explain why only certain
  packs are currently active
- if recent repo-level tooling or doc work matters, also check the latest git
  commits and mention the concrete date
- offer a few practical next-step options at the administrator level, such as
  starting a new project planning session, continuing the active testing
  build, reviewing recent results before deciding, choosing between a small
  script/component and a larger project, or freezing older work through
  retirement

The startup response should feel like a project concierge briefing, not a file
acknowledgment.

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
- `python3 tools/create_template_pack.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json`
- `python3 tools/materialize_build_pack.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json`
- `python3 tools/promote_build_pack.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json`
- `python3 tools/run_deployment_pipeline.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json`
- `python3 tools/retire_pack.py --factory-root /home/orchadmin/project-pack-factory --pack-id <pack-id> --retired-by orchadmin --reason "<reason>"`
- `python3 tools/run_workflow_eval.py --factory-root /home/orchadmin/project-pack-factory --output json`
