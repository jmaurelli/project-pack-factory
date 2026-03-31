# Role/Domain Template Overlay Adversarial Review

Date: 2026-03-31

Target spec:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-ROLE-DOMAIN-TEMPLATE-OVERLAY-TECH-SPEC.md`

## Findings

### 1. Fake-authority risk from example role names

Severity: high

The earliest draft used example entries that could be read as literal
professional authority rather than a framing lens. In V1, PackFactory should
avoid shipping examples that sound like regulated or credential-bearing roles
unless the spec explicitly says the overlay is guidance-only and not a claim of
licensure, certification, or external authority.

Disposition:

- tightened the spec wording around credentials
- removed the strongest risky example from the recommended initial catalog

### 2. Precedence was implied rather than explicit

Severity: medium

The draft said role/domain and personality should compose, but it did not make
instruction precedence explicit enough. V1 needs a clear order so generated
surfaces do not leave agents guessing when pack-local contracts, role/domain
framing, and personality tone point in different directions.

Disposition:

- added explicit precedence rules to the spec

### 3. Dual-overlay instruction surfaces could become noisy

Severity: medium

If both overlays show up as long sections in generated `AGENTS.md` and
`project-context.md`, the result will dilute the actual pack handoff. V1 should
keep generated overlay sections short and asymmetrical: concrete selected
overlay guidance in `AGENTS.md`, generic composability notes in
`project-context.md`.

Disposition:

- added a bounded generated-surface rule to the spec
- tightened the V1 rule so generated `AGENTS.md` uses one combined overlay
  header with fixed `Personality` and `Role/Domain` sublabels
- added a dedupe rule so tone/collaboration language stays personality-only and
  framing/heuristic language stays role/domain-only

### 4. Boundary blur with personality remained too soft

Severity: medium

The later draft still described role/domain as shaping "recommendation style"
in a few places, which drifted back toward the personality layer. V1 needs a
cleaner boundary: personality should own tone and collaboration posture, while
role/domain should own problem framing, domain lens, and default task
heuristics.

Disposition:

- removed the lingering "recommendation style" framing from the role/domain
  spec and generated-surface guidance
- tightened the spec to explicitly ban credential-implying example names in
  V1 guidance

## Result

The spec remains viable for implementation after the tightening above. The
bounded V1 shape is now:

- optional
- guidance-only
- distinct from personality
- explicit about precedence
- explicit about tone-vs-framing ownership
- conservative about role names and generated-surface verbosity
