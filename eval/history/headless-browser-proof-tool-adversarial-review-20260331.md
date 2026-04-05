# Headless Browser Proof Tool Adversarial Review

Date: 2026-03-31

## Scope

Review target:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-HEADLESS-BROWSER-PROOF-TOOL-TECH-SPEC.md`

Review method:

- multi-agent adversarial review with one pass focused on testing-policy and
  scope drift
- one pass focused on runtime-state, target-provenance, and control-plane
  boundaries

## Main Findings

1. The first draft was too broad for V1 and read more like a generic browser
   assertion framework than one bounded proof tool with one proving-ground use
   case.
2. The first draft did not fence the tool off explicitly enough from default
   validation commands, benchmark flows, CI, or deployment pipelines.
3. The first draft left target provenance too loose, which could have allowed
   arbitrary URLs or stale local pages to masquerade as PackFactory proof.
4. The first draft did not define runtime-state placement strictly enough for
   browser binaries, profiles, and caches.
5. The first draft did not state strongly enough that the wrapper is read-only
   against canonical PackFactory control-plane state.
6. The first draft still left too much room for a raw Playwright passthrough
   or a vague non-auditable proof report.

## Tightenings Applied

The spec was tightened to:

- narrow V1 to one named proof recipe:
  `adf_field_manual_hash_target_opens`
- keep dashboard and broader browser-proof adoption explicitly out of scope for
  V1
- state plainly that the wrapper is opt-in only and must not be added to
  `validate_factory.py`, pack validators, smoke commands, CI, deployment
  pipelines, or generic testing flows without a separate operator-approved spec
- require factory-owned runtime and proof roots under `.pack-state/`
- fail closed instead of falling back to global user-home browser caches or ad
  hoc temp paths
- make the wrapper read-only against canonical PackFactory state
- constrain V1 targets to PackFactory-managed local preview surfaces
- require schema-versioned proof output with provenance
- demote screenshots to debug artifacts only

## Result

After the tightened pass, the spec now matches the intended factory-root role:
one bounded shared browser-proof helper for a real interactive gap, without
quietly becoming a general UI test framework or a control-plane side channel.
