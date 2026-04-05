# Config Drift Checker Build Pack

This is a PackFactory-native build-pack materialized from the Config Drift Checker template.

## Bootstrap Order

1. `AGENTS.md`
2. `project-context.md`
3. `pack.json`
4. `status/lifecycle.json`
5. `status/readiness.json`
6. `status/retirement.json`
7. `status/deployment.json`
8. `benchmarks/active-set.json`
9. `eval/latest/index.json`

## Optional Overlays

Treat this line-level overlay as composable guidance. It shapes how this pack
frames drift evidence and recommendations, but it does not override canonical
pack state or PackFactory truth.

### Role/Domain

This build-pack currently carries the optional role/domain overlay
`research-analyst` (Research Analyst).
A disciplined framing lens for evidence review, synthesis, and careful
distinction between signal, gap, and inference.
- Separate observed evidence from inference and keep the distinction visible.
- Favor careful synthesis over confident speculation when the signal is thin.
- Call out what is still missing before recommending a stronger conclusion.

## Working Rules

- Treat this pack as an active build-pack.
- Use `validate-project-pack` before trusting local state.
- Use `benchmark-smoke` as the smallest bounded benchmark for this build-pack.
- Keep this build-pack easy for a fresh agent to inspect and adapt.
- Prefer the standalone `check-drift` CLI and machine-readable JSON output.
