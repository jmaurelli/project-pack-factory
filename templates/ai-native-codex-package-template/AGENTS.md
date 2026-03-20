# ai-native-codex-package-template Agent Context

This template pack is the canonical PackFactory source template for
AI-assisted software building.

## First Reads

1. `AGENTS.md`
2. `project-context.md`
3. `pack.json`
4. `status/lifecycle.json`
5. `status/readiness.json`
6. `benchmarks/active-set.json`
7. `eval/latest/index.json`
8. `docs/benchmark-first-task.md` when benchmark startup guidance is needed
9. `src/ai_native_package/USAGE.md` when exact CLI examples are needed

## Working Rules

- Treat `pack.json`, `status/`, `benchmarks/active-set.json`, and
  `eval/latest/index.json` as the PackFactory state surface.
- Keep this pack non-deployable. It is a source template, not a live build.
- Keep contracts mirrored at the root-level `contracts/` directory for
  deterministic PackFactory traversal.
- Use copied benchmark evidence under `eval/history/` as the current
  local validation anchor.
- Preserve agent-oriented restart-state support and benchmark ergonomics.
