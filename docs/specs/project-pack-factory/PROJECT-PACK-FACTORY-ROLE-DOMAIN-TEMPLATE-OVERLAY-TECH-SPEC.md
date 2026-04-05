# Project Pack Factory Role/Domain Template Overlay Tech Spec

## Status

Draft specification for a PackFactory-root overlay system that adds reusable
role/domain framing without collapsing template reuse or operator-specific
runtime state.

## Goal

PackFactory should support a second optional overlay layer alongside
personality templates:

- `personality_template`: how the agent tends to sound and collaborate
- `role_domain_template`: what problem-framing lens or functional perspective
  the agent should bring to the work

The role/domain layer should stay:

- optional
- composable with personality overlays
- explicit in template creation and build-pack materialization
- guidance-only rather than a claim of literal credentials

## Problem

The current personality-template system is useful for tone and recommendation
framing, but it is not a clean home for role/domain prompts such as:

- `startup operator`
- `research analyst`
- `product strategy advisor`
- `grounded startup partner`
- `operator coach`

Those examples are not only about tone. They mix:

- role
- domain lens
- problem-framing defaults
- task heuristics

Putting that all into personality blurs two distinct concerns and makes the
catalog less reusable over time.

## Desired Model

PackFactory should add a separate `role_domain_template` overlay that can be
selected during:

- template creation
- build-pack materialization

The overlay should describe:

- the role/domain identifier and human-readable name
- a short summary
- agent-context lines that shape problem framing
- project-context lines that describe when the overlay fits

V1 should treat the overlay as a framing lens, not as literal job-title
authority.

Safe catalog growth should prefer reusable framing lenses like
`grounded-startup-partner` and `operator-coach` over regulated, credentialed,
or title-heavy roles. Those additions stay useful because they shape problem
framing and operator support style without implying licensure, managerial
authority, or therapy.

When a candidate label risks sounding like a relationship or authority claim,
the stored summary and context lines must stay heuristic-centric:

- explain what decisions the lens changes
- keep guidance in terms like `frame`, `prefer`, `keep visible`, or `shape`
- avoid turning the entry into a tone, relationship, therapy, or management
  authority claim
- make the lens distinguishable from adjacent entries by its decision
  heuristic, not by adjectives alone

The overlay should not:

- rewrite pack identity
- replace canonical lifecycle, readiness, or deployment truth
- replace runtime operator profiles or memory
- imply literal credentials, licensure, certification, or external authority

## Evidence

The current personality overlay system already exists and proves the control
plane shape we should mirror:

- catalog: [agent-personality-template-catalog.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/agent-personality-template-catalog.json)
- schema: [agent-personality-template-catalog.schema.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/schemas/agent-personality-template-catalog.schema.json)
- template creation support: [create_template_pack.py](/home/orchadmin/project-pack-factory/tools/create_template_pack.py)
- build-pack materialization support: [materialize_build_pack.py](/home/orchadmin/project-pack-factory/tools/materialize_build_pack.py)
- validation support: [validate_factory.py](/home/orchadmin/project-pack-factory/tools/validate_factory.py)

The current personality catalog is intentionally small and communication-first,
which is the right sign that role/domain framing should be split out instead of
overloaded into personality:

- [agent-personality-template-catalog.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/agent-personality-template-catalog.json)
- [PROJECT-PACK-FACTORY-AGENT-BUSINESS-PARTNER-PERSONALITY-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AGENT-BUSINESS-PARTNER-PERSONALITY-SPEC.md)

The Codex personal assistant runtime also shows why the split matters. Its
runtime contracts now mix:

- partner tone and startup feel
- MVP/POC framing
- grounded business-direction thinking
- ambiguity fail-closed behavior

Those behaviors live in:

- [assistant-profile.json](/home/orchadmin/project-pack-factory/build-packs/codex-personal-assistant-daily-driver-build-pack-v1/contracts/assistant-profile.json)
- [partnership-policy.json](/home/orchadmin/project-pack-factory/build-packs/codex-personal-assistant-daily-driver-build-pack-v1/contracts/partnership-policy.json)
- [operator-profile.json](/home/orchadmin/project-pack-factory/build-packs/codex-personal-assistant-daily-driver-build-pack-v1/contracts/operator-profile.json)

That runtime is a good proving ground, but it is not the right canonical home
for a general PackFactory role/domain overlay system.

## Proposed Control-Plane Changes

### 1. Add A Canonical Catalog

Create:

- `docs/specs/project-pack-factory/agent-role-domain-template-catalog.json`
- `docs/specs/project-pack-factory/schemas/agent-role-domain-template-catalog.schema.json`

Each entry should minimally contain:

- `template_id`
- `display_name`
- `summary`
- `agent_context_lines`
- `project_context_lines`

V1 should stay parallel to the personality catalog rather than adding a more
complex field model.

The shared control-plane expectation is also parallel:

- one canonical catalog loader in `tools/factory_ops.py`
- one canonical resolver in `tools/factory_ops.py`
- whole-factory catalog validation through `tools/validate_factory.py`

### 2. Add Template-Creation Selection

Extend `planning_summary` in template-creation requests with optional:

- `role_domain_template_selection`

Required fields:

- `role_domain_template_id`
- `selection_reason`
- `apply_to_derived_build_packs_by_default`

Resolved selections should be stored in:

- `pack.json.role_domain_template`
- template-creation report fields such as `resolved_role_domain_template`

When no role/domain overlay is selected, the request may omit the field and the
result should omit both `pack.json.role_domain_template` and
`resolved_role_domain_template`.

### 3. Add Materialization Selection

Extend materialization requests with optional:

- `role_domain_template_selection`

Selection modes should mirror the existing personality system:

- `inherit_template_default`
- `catalog_template`
- `no_role_domain_template`

Resolved selections should be stored in:

- `pack.json.role_domain_template`
- materialization reports via `resolved_role_domain_template`

If materialization inherits the template default but the template has no
default role/domain overlay, the build-pack should omit the field rather than
writing a placeholder object.

The carried manifest/report fields should stay parallel to the personality
system:

- `template_id`
- `display_name`
- `summary`
- `selection_origin`
- `selection_reason`
- `catalog_path`
- `apply_to_derived_build_packs_by_default`

### 4. Generated Instruction Surfaces

When present, the role/domain overlay should appear in generated `AGENTS.md`
and template `project-context.md` / build-pack agent context as:

- a guidance layer for problem framing and default task heuristics
- explicitly subordinate to canonical PackFactory control-plane truth

Suggested language:

- treat the overlay as a reusable framing lens
- do not treat it as literal credentials
- do not let it override lifecycle, readiness, or deployment facts

V1 generated-surface rule:

- render overlays under one combined generated `AGENTS.md` header with fixed
  sublabels such as `Personality` and `Role/Domain`
- keep the selected overlay concrete in generated `AGENTS.md`
- keep `project-context.md` limited to generic composability guidance rather
  than repeating full selected-overlay detail
- do not duplicate the same behavioral line across personality and role/domain
  generated sections; personality owns tone/collaboration language, while
  role/domain owns framing/heuristic language
- keep overlay sections short enough that the pack handoff remains primary

## Precedence

If guidance conflicts, use this order:

1. canonical PackFactory control-plane truth and pack-local contracts
2. explicit role/domain overlay framing for problem interpretation
3. personality overlay guidance for tone and recommendation framing

The role/domain overlay may shape how a problem is framed, but it must not
override canonical pack state, operator-specific runtime truth, or explicit
pack-local objectives.

For V1 boundary clarity:

- personality owns tone, collaboration feel, and operator-facing interaction
  posture
- role/domain owns problem framing, domain lens, and default task heuristics
- role/domain must not be used to imply regulated titles, licensed authority,
  or hidden credentials

## Inheritance Boundary

Default inheritance is allowed, but it should stay explicit and reversible.

The intended meaning of `apply_to_derived_build_packs_by_default` is:

- the source template suggests a default framing lens for descendants
- materialization can still inherit, override, or clear that lens
- the overlay must never become a silent identity lock on the template family

## Example Catalog Entries

V1 should stay bounded. A small initial catalog is enough to prove the model.

Recommended initial entries:

- `startup-operator`
- `research-analyst`
- `product-strategy-advisor`

These are examples of perspective lenses, not claims of certification,
licensure, or external credentials.

More authority-laden role names can be added later, but V1 should start with
safer non-credentialed examples.

V1 should explicitly avoid regulated, licensed, or credential-implying titles
in the initial catalog and example naming guidance.

## Validation

The bounded validation slice should be:

- `python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory --output json`
- schema validation through the existing factory validator

No broad new tests or benchmark expansion are required for V1.

## Risks

### Risk: Role/domain becomes identity lock-in

Mitigation:

- keep selection optional
- keep catalog separate from templates
- keep build-pack materialization able to inherit, override, or clear it

### Risk: Role/domain implies fake authority

Mitigation:

- require the spec and generated docs to say the overlay is framing guidance,
  not literal credentials

### Risk: Role/domain duplicates personality

Mitigation:

- keep personality for tone and collaboration posture
- keep role/domain for problem-framing lens, domain perspective, and default
  task heuristics
- render both overlays under one combined generated header so coexistence stays
  readable instead of feeling like two competing mini-identities

## Implementation Surfaces

- [agent-role-domain-template-catalog.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/agent-role-domain-template-catalog.json)
- [agent-role-domain-template-catalog.schema.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/schemas/agent-role-domain-template-catalog.schema.json)
- [factory_ops.py](/home/orchadmin/project-pack-factory/tools/factory_ops.py)
- [create_template_pack.py](/home/orchadmin/project-pack-factory/tools/create_template_pack.py)
- [materialize_build_pack.py](/home/orchadmin/project-pack-factory/tools/materialize_build_pack.py)
- [validate_factory.py](/home/orchadmin/project-pack-factory/tools/validate_factory.py)
- [pack.schema.json](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/schemas/pack.schema.json)
- request/report schemas for template creation and materialization

## Success Signal

PackFactory can now carry both of these, independently or together:

- a personality overlay for how the agent sounds
- a role/domain overlay for how the agent frames work

That gives future assistants and product lines a cleaner composition model than
trying to stuff everything into one `personality` field.
