# AlgoSec Diagnostic Framework Successor Template Pack

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

## Agent-Native Initialization

This template declares a default agent-native posture for future derived build-packs.
It does not claim active pack-local tracker files here; build-pack materialization is where live activation can happen.
Profile: `packfactory_tracker_backed_agent_native` (PackFactory Tracker-Backed Agent-Native).
Activation state: `template_declared`.
Work management model: `objective_backlog_work_state` / `tracker_backed_advisory_planning`.
When a derived build-pack activates this profile, discover tracker surfaces through `pack.json.directory_contract` and `pack.json.post_bootstrap_read_order`.
Default for derived build-packs: `true`.
Treat this profile as declaration-only until a derived build-pack activates it.

## Optional Overlays

Treat these overlays as composable guidance layers. Personality shapes tone and collaboration posture; role/domain shapes problem framing and default task heuristics.

### Personality
This template currently carries the optional personality overlay `calm-delivery-lead` (Calm Delivery Lead).
Steady delivery-lead posture for concise operator briefings, release coordination, and practical next-step framing.
Derived build-packs inherit this overlay by default unless materialization explicitly clears it or selects another personality template.
Treat the overlay as briefing and recommendation-framing guidance only. It does not override canonical factory policy, lifecycle state, deployment truth, or pack-local control-plane files.
- Keep startup and continuation briefings concise, operational, and release-oriented.
- Favor direct release, support, deployment, and delivery language over broad strategic narration.
- Escalate risks plainly when environment state, evidence freshness, or operator decisions are unclear.

## Line-Specific Role/Domain Lens

This template family currently carries a line-specific role/domain contract even though it is not yet represented in `pack.json.role_domain_template`.
Use `docs/specs/adf-successor-diagnostic-systems-analyst-role-domain-lens-v1.md` as the current framing lens for future derived build-packs in this family.
Treat it as the active ADF-specific problem-framing contract until the line either promotes that lens into the shared PackFactory catalog or replaces it with a later family-specific revision.


## Working Rules

- Treat this pack as an active source template.
- Use `validate-project-pack` before trusting local state.
- Use `benchmark-smoke` as the smallest bounded benchmark for this template.
- Keep this template easy for a fresh agent to inspect and adapt.
- Treat this template as source-only. It is not directly deployable.
