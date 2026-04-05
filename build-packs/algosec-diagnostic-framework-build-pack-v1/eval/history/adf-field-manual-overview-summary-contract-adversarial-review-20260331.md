# ADF Field-Manual Overview Summary Contract Adversarial Review

Date: 2026-03-31

## Scope

Review target:

- `docs/specs/adf-field-manual-overview-summary-contract-v1.md`

Review method:

- multi-agent adversarial review with one language-focused pass and one
  implementation-focused pass

## Main Findings

1. The first draft still allowed the old failure mode to survive by letting the
   renderer publish first-sentence `action` fallbacks as normal operator-facing
   overview text.
2. The first draft did not make `overview_summary` mandatory for newly
   generated field-manual steps, which would have let the old experience remain
   indefinitely.
3. The first draft did not explicitly name all operator-facing navigation
   surfaces that should use the overview-summary field.
4. The first draft did not state strongly enough that overview summaries must
   use the same noun-source and natural-language rules as the main frontline
   language contract.
5. The first draft needed harder reject conditions so lightly trimmed analytical
   prose could not pass as an overview summary.

## Tightenings Applied

The contract was tightened to:

- require `steps[].overview_summary` for newly generated field-manual content
- make `overview_summary` the source of truth for operator-facing overview
  labels
- limit fallback behavior to legacy artifacts only
- reject automatic sentence-splitting as the normal publication path for new
  content
- add hard checks such as a 10-word cap, one-clause rule, and live-call
  phrasing test
- reject trivial copies of the fuller `action` text
- name the affected operator-facing navigation surfaces explicitly
- declare the field as a backward-compatible additive artifact change for
  field-manual step records

## Result

After the tightened pass, the specification is stronger, more fail-closed, and
better aligned with the actual support-review goal: the top step list should be
a fast human scan surface, not a lightly disguised backend-analysis surface.
