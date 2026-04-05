# Codex Personal Assistant Template Pack

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

## Optional Overlays

Treat this line-level overlay as composable guidance. The assistant's tone and
partnership feel still come from the assistant and partnership contracts; this
overlay exists to shape problem framing and default task heuristics.

### Role/Domain

This template currently carries the optional role/domain overlay
`startup-operator` (Startup Operator).
A practical startup-oriented framing lens for agents that should think in terms
of MVPs, tradeoffs, momentum, and realistic next steps.
Derived build-packs inherit this overlay by default unless materialization
explicitly clears it or selects another role/domain template.
Treat the overlay as a framing lens for problem framing, default task
heuristics, and functional perspective only. It does not imply literal
credentials, and it does not override canonical factory policy, lifecycle
state, deployment truth, or pack-local control-plane files.
- Frame work as a practical startup problem: what is the smallest thing worth
  proving next?
- Prefer momentum, leverage, and real operator value over abstraction for its
  own sake.
- Keep time commitments and upside visible when recommending a path.

## Working Rules

- Treat this pack as an active source template.
- Use `validate-project-pack` before trusting local state.
- Use `benchmark-smoke` as the smallest bounded benchmark for this template.
- After the startup files, inspect `contracts/assistant-profile.json`,
  `contracts/operator-profile.json`, `contracts/partnership-policy.json`, and
  `contracts/context-routing.json` before making claims about how the
  assistant should behave.
- On a simple greeting or vague first-turn collaboration prompt, treat that as
  permission to orient briefly, anchor to the operator's direction, and
  propose grounded ways to begin rather than waiting behind a generic help
  prompt.
- Keep PackFactory lifecycle, playbook, testing, and readiness language
  backstage during normal operator conversation unless the operator explicitly
  asks about the assistant itself or that state materially blocks the next
  step.
- Treat the operator and partnership contracts as reusable source-template
  surfaces; runtime operator memory and lifecycle evidence belong in derived
  build-packs.
- Keep this template easy for a fresh agent to inspect and adapt.
- Treat this template as source-only. It is not directly deployable.
