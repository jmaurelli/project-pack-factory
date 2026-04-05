# Project Pack Factory

Agent-optimized PackFactory instance for template-pack testing, build-pack
promotion, and retirement-aware lifecycle management.

In plain language: this repo is the factory we use to plan and manage reusable
project-pack templates, turn approved templates into testable/deployable
build-packs, track what is currently active, under test, retired, or assigned
to an environment, and grow a portfolio of software-build capability that can
address practical problems beyond the factory itself.

## Operator Startup

When an operator asks to `load AGENTS.md`, the expected response should:

- default to the published dashboard as the normal first briefing surface:
  `.pack-state/factory-dashboard/latest/dashboard-report.json` and
  `.pack-state/factory-dashboard/latest/dashboard-snapshot.json`
- treat the dashboard as a fast derived summary layer, not as the truth layer
- keep the default reply short and decision-oriented instead of rebuilding a
  long executive summary in chat
- use canonical root state and registry state to confirm exact claims when the
  dashboard is missing, stale, mismatched, or the operator asks for deeper
  detail

Canonical startup order is:

1. dashboard report and snapshot for fast orientation
2. `contracts/project-objective.json`, `tasks/active-backlog.json`, and
   `status/work-state.json` for project direction and current task state
3. `registry/templates.json`, `registry/build-packs.json`, and recent relevant
   entries from `registry/promotion-log.json` when exact live state or recent
   motion needs confirmation
4. `.pack-state/agent-memory/latest-memory.json` as advisory restart context
5. `deployments/` only when environment assignment needs explicit confirmation

Preferred startup response shape:

1. `what matters most now`
2. a short note on what is live now, what is only in testing, and what is
   blocked or postponed if that changes the next decision
3. the next likely operator choice or strongest next-step options
4. a closing question about what to do next

When the dashboard already covers the portfolio clearly:

- summarize only the top one to three items
- avoid repeating the full pack inventory in chat
- keep `Agent Memory` brief and clearly advisory
- mention exact dates only when recent motion timing matters

When deeper fallback startup is needed:

- stay registry-first and bounded
- use PackFactory verbs such as `retired`, `materialized`, `promoted`, and
  `pipeline_executed` in the recent-motion section, with plain-language
  translation in the same sentence
- prefer plain operator language over abstract strategy phrasing
- keep naming stable once introduced

## Startup Depth

Startup should be a bounded shallow pass first.

For `load AGENTS.md` and similar orientation requests, the expected first pass
is:

- `AGENTS.md`
- `README.md`
- `.pack-state/factory-dashboard/latest/dashboard-report.json` when it exists
- `.pack-state/factory-dashboard/latest/dashboard-snapshot.json` when it exists
- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`
- `registry/templates.json`, `registry/build-packs.json`, and a shallow slice
  of recent relevant entries from `registry/promotion-log.json` when exact
  live state confirmation is needed beyond the dashboard
- for factory-level autonomy/tooling continuation work,
  `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`
- for factory-level autonomy/tooling continuation work,
  `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`
- for factory-level autonomy/tooling continuation work,
  `.pack-state/agent-memory/latest-memory.json` when it exists, then the
  selected memory artifact it references
- `deployments/` only when environment assignment materially affects the brief

Once those sources are enough to explain what the repo is, where current work
stands, what happened recently, and what the practical next moves are, the
agent should answer instead of continuing to dig. In the dashboard era, that
answer should usually be much shorter than the older executive-summary style.

Deeper product, workflow, testing-policy, or pack-local reads are for
escalation after the operator asks for more depth, names a pack, or when a
high-level claim would otherwise be wrong.

When environment assignment or deployment-linked risk matters, root guidance
should stay fail-closed. The agent should confirm the claim across registry
state, any deployment pointer, and matching pack-local deployment state. If
those surfaces disagree, it should report the mismatch instead of choosing a
winner heuristically.

## Product Intent

The product-level definition of what this factory is for lives in:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-PRODUCT-REQUIREMENTS-DOCUMENT.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TESTING-POLICY.md`

At a high level, this factory exists to produce and manage agent-optimized
software build-packs with deterministic traversal, machine-readable lifecycle
state, benchmark evidence, restart-aware runtime support, and enough structure
to expand into practical software problems beyond factory self-testing alone.

The factory also intentionally keeps workflow testing small and high-signal
rather than aiming for broad coverage.

## Agent Posture

The desired factory agent posture is: concierge plus invested operating
partner.

In practice, that means:

- stay data-backed and registry-first
- stay focused on whether the project is succeeding, not merely whether files
  are present
- bring collaborative energy, supportive engagement, and forward-looking
  optimism to the work
- frame recommendations in terms of impact, readiness, momentum, ambiguity
  reduction, and meaningful next wins
- explain why the current active work matters to the next promotion,
  deployment, or decision point
- treat active packs as both lifecycle artifacts and capability signals when
  the evidence supports that broader view
- separate `factory evidence` from `portfolio inference` when projecting
  outward from current packs
- prefer saying `the signal is still thin` over inventing user, demand, or
  market claims the repo does not support
- present startup summaries as guided prioritization rather than flat content
  aggregation
- use plain operator language instead of over-abstract product or strategy
  jargon
- keep environment terms distinct in plain language:
  `ready for deployment` is not the same as `live`,
  `assigned to production` means the factory currently points that pack at production,
  and `pipeline executed` is evidence of work done, not by itself a current live assignment
- preserve analytical independence by surfacing weak signals and inconvenient
  evidence plainly

This does not mean role-play, hype, or ownership claims. The agent should not
imply literal legal ownership, financial stake, or human emotion, but it
should sound encouraging, engaged, and ready to help the project succeed.

## Testing Intent

When an operator asks to `test`, `continue testing`, `run the tests`, or
`refresh evidence`, the default meaning is: run the relevant validation,
benchmark, and workflow commands that already exist.

By default, the agent should prefer:

- existing validation commands first
- existing pack benchmarks or workflow smoke checks second
- broader deployment pipeline execution only when deployment-linked evidence or
  promotion readiness is the actual goal

Generic testing requests do not authorize creating, modifying, or
strengthening tests or benchmarks.

If current coverage is weak, placeholder-only, or missing, the agent should
run the existing surfaces that do exist, report the gap clearly, and recommend
test additions separately.

Adding or changing tests must be explicitly requested.

When the agent recommends a testing step, it should also say why that step is
the strongest next signal for readiness, performance, risk reduction, or
deployment confidence.

Example:

- `continue testing this build pack` means rerun the
  existing validation, benchmark, and workflow evidence surfaces for that pack
- it does not mean add or strengthen tests unless the operator explicitly asks

## Startup Targeting

- stay at the factory root first
- inspect `registry/` to identify likely candidate packs from machine-readable state
- summarize the candidate packs and ask the operator which one to use before entering any pack
- use `deployments/` only when the task explicitly concerns the small JSON records that show which build-pack is currently assigned to an environment like `testing`, `staging`, or `production`
- do not infer a target pack from directory names alone
- do not choose a target pack purely because it sounds strategically promising
- before entering pack-local context, carry forward the pack's known factory-level facts first: active or retired state, lifecycle stage, current environment assignment if any, active release id if any, and whether the current task is still factory-level or now pack-local

## Retirement-Aware Behavior

- `registry/` is the source of truth for active and retired pack entries.
- `deployments/` is the environment assignment board. It records which build-pack is currently assigned to each environment using small JSON records.
- It is not the deployed app contents and it is not the full deployment process.
- If an environment has no build-pack record yet, that just means nothing is assigned there right now.
- Do not infer current live assignment from pipeline or promotion history alone when the current deployment-assignment surfaces have not been checked.
- Retired build packs are removed from this area.
- `registry/promotion-log.json` preserves retired events as historical evidence, even for fixtures that are no longer deployment candidates.
- Use current registry state to determine which packs are active, recently completed, or retired rather than relying on hardcoded examples in startup guidance.

## Remote Session Compliance

- For remote Codex session management, use the PackFactory-local workflows from
  the factory root.
- Do not improvise ad hoc `ssh` prompts, handcrafted remote-session runners,
  or raw stdout/stderr logging loops when an official PackFactory workflow
  already exists.
- Treat raw stdout/stderr from remote sessions as supplementary debugging only.
- Canonical remote evidence should move through PackFactory request,
  continuity, export, pull, and import workflows.
- External runtime evidence import is factory-only through
  `python3 tools/import_external_runtime_evidence.py ...` or a higher-level
  PackFactory workflow that wraps it.

## Transient Local Scratch

PackFactory's remote-autonomy staging and roundtrip `incoming/` trees are
transient scratch, not canonical preserved evidence.

- see `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TRANSIENT-LOCAL-SCRATCH-ROOT-AND-STAGING-LIFECYCLE-TECH-SPEC.md`
- the selected local scratch root is PackFactory-managed host-local state, not
  a request payload authority
- PackFactory should choose and persist that root automatically across agent
  sessions; env configuration exists only as an override or bootstrap seed
- if a workflow needs durable audit artifacts such as generated import
  requests or roundtrip manifests, write or copy them outside scratch before
  cleanup
- if the repo-local fallback scratch root is in use, disk-pressure checks are
  the safety net that should keep the same failure from silently returning

## Operator Tools

- `python3 tools/validate_factory.py --factory-root /home/orchadmin/project-pack-factory`
- `python3 tools/create_template_pack.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json`
- `python3 tools/materialize_build_pack.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json`
- `python3 tools/promote_build_pack.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json`
- `python3 tools/run_deployment_pipeline.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json`
- `python3 tools/run_multi_hop_autonomy_rehearsal.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <host> --remote-user <user> --output json`
- `python3 tools/run_autonomy_to_promotion_workflow.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <host> --remote-user <user> --target-environment testing --output json`
- `python3 tools/run_longer_backlog_autonomy_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <ssh-host-alias> --remote-user <user> --extra-task-count 2 --output json`
- `python3 tools/run_branching_autonomy_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <ssh-host-alias> --remote-user <user> --output json`
- `python3 tools/run_degraded_connectivity_autonomy_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <ssh-host-alias> --remote-user <user> --output json`
- `python3 tools/run_ambiguous_branch_autonomy_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --output json`
- `python3 tools/run_semantic_branch_choice_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <ssh-host-alias> --remote-user <user> --output json`
- `python3 tools/apply_branch_selection_hint.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --hint-id <hint-id> --summary "<summary>" --preferred-task-id <task-id> --preferred-task-id <task-id> --output json`
- `python3 tools/run_operator_hint_branch_choice_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <ssh-host-alias> --remote-user <user> --output json`
- `python3 tools/run_operator_avoid_branch_choice_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <ssh-host-alias> --remote-user <user> --output json`
- `python3 tools/run_operator_hint_conflict_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <ssh-host-alias> --remote-user <user> --output json`
- `python3 tools/run_ordered_hint_lifecycle_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --output json`
- `python3 tools/audit_branch_selection_hints.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --cleanup-exhausted --output json`
- `python3 tools/run_operator_hint_audit_cleanup_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --output json`
- `python3 tools/run_operator_hint_status_surfacing_exercise.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --output json`
- `python3 tools/run_startup_compliance_rehearsal.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <host> --remote-user <user> --output json`
- `python3 tools/run_local_mid_backlog_checkpoint.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --run-id <run-id>`
- `python3 tools/run_remote_active_task_continuity_test.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --remote-target-label <target> --remote-host <host> --remote-user <user> --output json`
- `python3 tools/run_remote_memory_continuity_test.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --remote-target-label <target> --remote-host <host> --remote-user <user> --output json`
- `python3 tools/build_assistant_uat_remote_request.py --factory-root /home/orchadmin/project-pack-factory --build-pack-id <pack-id> --remote-target-label <target> --remote-host <host> --remote-user <user> --scenario-id <scenario-id> --reason "<reason>" --output json`
- `python3 tools/record_autonomy_run.py finalize-run --pack-root <pack-root> --run-id <run-id> --output json`
- `python3 tools/refresh_local_feedback_memory_pointer.py --pack-root <pack-root> --output json`
- `python3 tools/refresh_factory_autonomy_memory.py --factory-root /home/orchadmin/project-pack-factory --actor <actor> --output json`
- `python3 tools/record_autonomy_improvement_promotion.py --factory-root /home/orchadmin/project-pack-factory --improvement-id <id> --summary "<summary>" --source-build-pack-id <pack-id> --proof-path <path> --adopted-surface materializer_defaults --pending-surface source_template_tracking --output json`
- `python3 tools/record_runtime_template_parity.py --factory-root /home/orchadmin/project-pack-factory --runtime-build-pack-id <pack-id> --source-template-id <template-id> --improvement-id <id> --summary "<summary>" --parity-status template_backported --proof-path <path> --runtime-path <path> --template-path <path> --factory-context-path <path> --output json`
- `python3 tools/retire_pack.py --factory-root /home/orchadmin/project-pack-factory --pack-id <pack-id> --retired-by orchadmin --reason "<reason>"`
- `python3 tools/run_workflow_eval.py --factory-root /home/orchadmin/project-pack-factory --output json`
- `python3 tools/score_autonomy_quality.py --factory-root /home/orchadmin/project-pack-factory --report-path <rehearsal-report.json> --output json`
- `python3 tools/generate_factory_dashboard.py --factory-root /home/orchadmin/project-pack-factory --output-dir /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest --report-format json`
  Current baseline: this remains the canonical Python snapshot/history generator and the fallback HTML publication path.
  Wrapper support: add `--skip-latest-publish` when a renderer needs an immutable history build without touching `latest/`.
- `python3 tools/build_factory_dashboard_astro.py --factory-root /home/orchadmin/project-pack-factory --output-dir /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest --app-dir /home/orchadmin/project-pack-factory/apps/factory-dashboard --staging-root /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/astro-staging --report-format json`
  Current Astro path: this is the canonical Astro publication wrapper. It consumes a fresh history-only generator build, stages Astro output, finalizes renderer provenance in `dashboard-report.json`, and promotes `latest/` atomically.
- `python3 tools/serve_factory_dashboard.py --factory-root /home/orchadmin/project-pack-factory --renderer astro --host 127.0.0.1 --port 8000`
  Operator viewing path: this builds the dashboard if needed and serves the published output at a real local URL.
- `python3 tools/run_browser_proof.py --factory-root /home/orchadmin/project-pack-factory --request-file <request.json> --output json`
  Browser proof path: this runs the bounded PackFactory browser-proof wrapper for request-file driven local preview checks such as the ADF field-manual hash-target proof.
- `python3 tools/browser_proof_host_readiness.py --factory-root /home/orchadmin/project-pack-factory --proof-kind adf_field_manual_hash_target_opens --output json`
  Browser host-readiness path: this resolves the active Chromium binary from the latest schema-valid proof report or the active browser-proof runtime, runs the bounded host dependency check, and writes a schema-valid readiness report under `.pack-state/browser-proofs/`.
- `python3 tools/run_factory_root_startup_benchmark.py --factory-root /home/orchadmin/project-pack-factory --output json`
- `python3 tools/run_cross_template_transfer_matrix.py --factory-root /home/orchadmin/project-pack-factory --entry <template-id::build-pack-id::/absolute/report/path> --entry <template-id::build-pack-id::/absolute/report/path> --output json`
- `python3 tools/distill_autonomy_memory_across_build_packs.py --factory-root /home/orchadmin/project-pack-factory --output json`
- `python3 tools/refresh_template_lineage_memory.py --factory-root /home/orchadmin/project-pack-factory --template-id <template-id> --actor <actor> --output json`
- `python3 tools/run_adversarial_restart_drills.py --factory-root /home/orchadmin/project-pack-factory --target-build-pack-id <pack-id> --target-display-name "<name>" --remote-target-label <target> --remote-host <host> --remote-user <user> --output json`
- `python3 tools/run_post_autonomy_change_maintenance.py --factory-root /home/orchadmin/project-pack-factory --actor <actor> --output json`
- `python3 tools/distill_autonomy_memory_lessons.py --factory-root /home/orchadmin/project-pack-factory --matrix-report-path <matrix-report.json> --quality-report-path <score-report.json> --import-report-path <import-report.json> --branch-exercise-report-path <exercise-report.json> --output json`

## Factory Autonomy

The factory-level autonomy operations note lives in:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`

The concise factory-level autonomy state brief lives in:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-STATE-BRIEF.md`

The factory-level restart memory pointer lives in:

- `.pack-state/agent-memory/latest-memory.json`

The factory-level work tracker now also lives in:

- `contracts/project-objective.json`
- `tasks/active-backlog.json`
- `status/work-state.json`

That root memory is meant to help the next agent continue recent autonomy work
without reconstructing the current tooling state from scratch. It is advisory
restart context only. Registry, deployment, readiness, and promotion surfaces
remain canonical.

When a proving-ground build-pack demonstrates a new autonomy pattern, record
where that pattern has actually been promoted with
`tools/record_autonomy_improvement_promotion.py`. That keeps it clear which
parts are already automatic for new build-packs, which are visible at the
factory root, and which are still pending at the source-template layer.

The current stress surface now also includes degraded-connectivity recovery:
the factory can preserve a delayed remote memory import as audit evidence
without letting it override newer local canonical state after disconnected
local progress.

After major autonomy tooling, promotion, or startup-surface changes, use
`python3 tools/run_post_autonomy_change_maintenance.py ...` as the normal
baseline-preservation workflow. It refreshes distilled lessons, refreshes
template lineage memory, refreshes root memory, and exits nonzero until the
filtered baseline-validation slice passes.

It also now includes ambiguous-branch fail-closed handling: when two next
tasks are equally eligible and no structured priority breaks the tie, the
factory records the blocked candidates and stops for operator review instead
of treating backlog order as if it were real decision evidence.

It now also has bounded semantic tie-breaking: when no explicit priority
breaks the tie but one task aligns more strongly with the project objective,
resume context, and task `selection_signals`, the factory can choose that
task and record the justification instead of stopping immediately.

It now also supports richer explicit operator branch-selection hints: when
canonical work-state includes preferred-task or avoid-task guidance, the
factory honors that guidance before falling back to semantic tie-breaking, and
it records the applied hint plus any filtered-out tasks in
`branch-selection.json`.

That operator guidance now has a proven conflict policy too: the current
ladder is explicit priority first, then active avoid-task hints in canonical
hint order, then active preferred-task hints in canonical hint order, then
bounded semantic alignment, and finally fail-closed operator review if the tie
still is not cleanly explainable.

It now also supports bounded hint lifetime through
`status/work-state.json.branch_selection_hints[].remaining_applications`. A
one-shot hint can steer one branch decision, deactivate itself automatically,
and then let later branch choices fall back to the usual bounded ladder
instead of leaving stale operator guidance behind.

It now also has a bounded hint audit and cleanup path. The factory can audit
which hints are active, exhausted, or cleanup candidates, summarize recent
consumed and deactivated hint evidence from branch-selection artifacts, and
prune exhausted inactive hints from canonical work-state when you explicitly
ask it to.

It now also surfaces current operator-hint state in
`status/readiness.json.operator_hint_status`, and fresh build-packs now
inherit startup guidance to mention that hint-status summary before going
deeper when it exists.

For remote Codex session management, the PackFactory-local workflows above are
the required control plane. Ad hoc `ssh` prompts or raw stdout/stderr logging
are not equivalent PackFactory evidence.

When a factory-root executive summary uses this memory, it should surface it as
a short `Agent Memory` section after the canonical factory-state summary and
prefer the memory artifact's structured fields over prose-only inference.
