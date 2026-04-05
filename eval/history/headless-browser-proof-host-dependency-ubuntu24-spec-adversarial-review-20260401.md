# Headless Browser Host Dependency Ubuntu 24.04 Spec Adversarial Review

Date: 2026-04-01
Scope:
- [PROJECT-PACK-FACTORY-HEADLESS-BROWSER-HOST-DEPENDENCY-PROVISIONING-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-HEADLESS-BROWSER-HOST-DEPENDENCY-PROVISIONING-TECH-SPEC.md)

## Review Intent

Pressure-test the new Ubuntu 24.04 package-mapping research section for:

- package-name accuracy
- canonical-versus-advisory boundary clarity
- operator-install risk
- evidence sufficiency

## Swarm Findings

### Finding 1

The Ubuntu 24.04 package mapping is directionally correct, but the sentence
stating that older non-`t64` package names "are not valid install candidates"
is too strong for the evidence currently recorded.

Why this matters:
- host-local `apt` behavior depends on enabled repos, architecture, and
  `Provides` or transitional-package behavior
- the current evidence demonstrates that point clearly for the three
  accessibility packages, but not as a universal rule for every package family

Recommended follow-up:
- weaken that statement to "not the confirmed install candidates on this host"
- explicitly say host-local `apt` metadata wins over cross-host inference

### Finding 2

The spec now embeds Ubuntu-specific package mapping inside the main canonical
tech spec immediately after reiterating that distro-specific helpers should be
separate and bounded.

Why this matters:
- the canonical shared-library evidence surface remains correct
- but the Ubuntu-specific mapping can read more normative than intended if it
  stays in the main flow without a stronger "host-specific advisory guidance"
  label

Recommended follow-up:
- either tighten the advisory label in place
- or move the Ubuntu-specific mapping into a bounded adjunct note later

### Finding 3

The evidence section is slightly stale relative to the newest active runtime
artifact. The spec still foregrounds the earlier March 31 fail-closed report
and note, while the current active browser binary and latest host-readiness
artifact now live under the April 1 proof and readiness runs.

Why this matters:
- the implementation now proves the exact headless-shell binary path
- the newest readiness artifact better reflects the binary that PackFactory is
  actually launching now

Recommended follow-up:
- refresh `Current Evidence` to mention the latest proof and host-readiness
  report alongside the earlier note

### Finding 4

The Ubuntu package section should more clearly distinguish:

1. exact installable package on this host
2. package name satisfied through `Provides` or transition behavior
3. no candidate on this host

Why this matters:
- Ubuntu 24.04 package-name transitions are where operator mistakes are most
  likely
- `libasound2t64` and the accessibility package names are the clearest cases
  where that nuance matters

Recommended follow-up:
- add a short "host-local apt candidate check wins" rule
- avoid wording that treats package names as timeless Ubuntu truth

## Bottom Line

The Ubuntu 24.04 research section is useful and substantially correct, but the
swarm does not recommend treating it as final install guidance yet.

The main remaining risk is not wrong shared-library evidence. It is wording
that could overstate how definitive the distro-specific package names are
without a stronger host-local `apt` candidate caveat.
