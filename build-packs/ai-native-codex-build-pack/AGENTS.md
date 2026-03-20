# ai-native-codex-build-pack Agent Context

This build pack is the deployable PackFactory derivative of the
canonical `ai-native-codex-package-template`.

## First Reads

1. `AGENTS.md`
2. `project-context.md`
3. `pack.json`
4. `status/lifecycle.json`
5. `status/readiness.json`
6. `status/deployment.json`
7. `lineage/source-template.json`
8. `benchmarks/active-set.json`
9. `eval/latest/index.json`

## Working Rules

- Treat `status/deployment.json` as the canonical deployment record.
- Treat `deployments/testing/ai-native-codex-build-pack.json` as the factory-root-relative projection and
  `../../deployments/testing/ai-native-codex-build-pack.json` as the pack-root-relative path.
- Use `eval/history/` for copied benchmark evidence and `eval/latest/index.json`
  for the current result surface.
- Keep deployability explicit in `status/readiness.json` and
  `status/deployment.json`.
- Do not mutate the source template under `templates/` when working here.
