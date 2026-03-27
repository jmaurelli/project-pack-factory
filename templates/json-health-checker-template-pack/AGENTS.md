# JSON Health Checker Template Pack

This is a PackFactory-native template created through the template creation workflow.

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

## Factory Autonomy Baseline

This template inherits the PackFactory autonomy baseline from the factory root.

Read these factory-level surfaces when the task concerns inherited agent
memory, feedback loops, autonomy rehearsal, stop-and-restart behavior, or
branch-choice policy:

1. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`
2. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`
3. `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md`
4. `.pack-state/agent-memory/latest-memory.json`

Treat the factory-level autonomy baseline as canonical for inherited default
behavior. Use this template only for template-specific source guidance and
runtime shape.

When `.pack-state/template-lineage-memory/latest-memory.json` exists, read it
after the factory-level baseline when you need a compact view of what this
template family has already taught the factory across derived build-packs.
Treat that template lineage memory as advisory template-family context, not as
canonical factory truth.

For remote Codex session management and external runtime-evidence handling,
follow the factory-root control plane rather than inventing template-local
remote workflows:

- use PackFactory-local remote-session, continuity, rehearsal, export, pull,
  and import workflows from the factory root when an official workflow exists
- do not improvise ad hoc `ssh` prompts, handcrafted remote-session runners,
  or raw stdout/stderr logging loops as substitutes for PackFactory evidence
- treat external runtime-evidence import as factory-only through
  `tools/import_external_runtime_evidence.py` or a higher-level PackFactory
  workflow that wraps that import

## Working Rules

- Treat this pack as an active source template.
- Use `validate-project-pack` before trusting local state.
- Use `benchmark-smoke` as the smallest bounded benchmark for this template.
- Keep this template easy for a fresh agent to inspect and adapt.
- Treat this template as source-only. It is not directly deployable.
