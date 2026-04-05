# Headless Browser Proof Host Dependency Spec Adversarial Review

Recorded at: `2026-04-01T12:00:00Z`

## Review Scope

Reviewed:

- [PROJECT-PACK-FACTORY-HEADLESS-BROWSER-HOST-DEPENDENCY-PROVISIONING-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-HEADLESS-BROWSER-HOST-DEPENDENCY-PROVISIONING-TECH-SPEC.md)
- [headless-browser-proof-host-dependency-evidence-20260331.md](/home/orchadmin/project-pack-factory/eval/history/headless-browser-proof-host-dependency-evidence-20260331.md)
- [.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260331t201817z/proof-report.json](/home/orchadmin/project-pack-factory/.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260331t201817z/proof-report.json)

VocoSwarm reviewers:

- `Hilbert`
- `Socrates`

## Main Findings

1. The rerun path was too brittle because it leaned on one transient temp request file.
2. The spec overstated the current proof state by implying end-to-end browser behavior was already proven on this host.
3. The readiness check did not clearly say which Chromium binary path is canonical when multiple Playwright revisions exist.
4. The evidence section did not clearly separate what the live proof report proves from what `ldd` adds.
5. The distro/package guidance needed a tighter fail-closed rule so shared-library names stay canonical and package mappings remain advisory.
6. The success condition needed a stronger requirement that at least one rerun advances past browser launch into real page assertions.

## Findings Rolled Into The Spec

The spec now includes:

- `Canonical Evidence Selection`
- `Host Provisioning Non-Goals`
- `Transient Request Artifact Rule`
- a narrowed statement of what is actually proven on this host
- an active-browser-binary rule for `ldd`
- a stronger success condition requiring one post-provisioning rerun to clear the launch boundary

## Outcome

The adversarial review tightened the spec without changing its core boundary:

- PackFactory owns the browser-proof wrapper and runtime isolation
- the host owns the shared-library prerequisites Chromium needs to launch
- shared-library names remain the canonical PackFactory evidence surface
