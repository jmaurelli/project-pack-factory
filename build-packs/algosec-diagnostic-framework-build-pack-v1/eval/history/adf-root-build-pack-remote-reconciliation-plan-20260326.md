# ADF Root Build Pack Remote Reconciliation Plan

Date: 2026-03-26

Pack: `algosec-diagnostic-framework-build-pack-v1`

Purpose: record the current reconciliation model between `Root`, the
`ADF Build Pack`, and `ADF Remote` so we do not treat PackFactory as a
minute-by-minute Git substitute while the live remote workspace is reachable.

This note itself and the local planner task
`define_adf_checkpointed_sync_model` are pack-local planning artifacts. They
help the `ADF Build Pack` decide how to checkpoint accepted remote progress,
but they are not by themselves evidence that `ADF Remote` changed.

## Working Conclusion

Continuous full synchronization is probably not needed.

In plain language:

- `ADF Remote` can remain the active ADF working copy while it is reachable
  and useful for live ADF investigation and review.
- `Root` remains the authority for PackFactory autonomy loops, memory
  infrastructure, workflow control, evidence import, and promotion surfaces.
- The `ADF Build Pack` should behave more like a canonical checkpoint snapshot
  than a live twin.

Remote changes are not automatically canonical just because they happened on
the live remote host. They become accepted ADF truth only after a bounded
checkpoint, import, or explicit reconciliation decision.

The intent is to preserve what PackFactory is good at without forcing it to
shadow every remote task movement or every remote content experiment.

## Why This Exists

The overhead concern is real.

If we force the `ADF Build Pack` to mirror `ADF Remote` all the time, we make
PackFactory do source-control work and remote-workspace mirroring work at the
same time. That is useful only when the resulting local copy is needed for:

- recovery if the remote host drifts or breaks
- auditability and promotion readiness inside PackFactory
- preserving accepted remote progress outside the live server
- pulling reusable logic back into PackFactory or a template later

That is not the same as keeping a perfect minute-by-minute shadow copy.

## Current Observations

As of this review:

- `Root`, the `ADF Build Pack`, and `ADF Remote` are aligned on the shipped
  autonomy and memory helper bundle under `.packfactory-runtime/`.
- `ADF Remote` is ahead of the `ADF Build Pack` on accepted ADF task state in
  `status/work-state.json`.
- `ADF Remote` and the `ADF Build Pack` both carry stale pack-local readiness
  wording in `status/readiness.json`.
- `ADF Remote` and the `ADF Build Pack` both still point
  `.pack-state/agent-memory/latest-memory.json` at v3 restart memory.
- The `ADF Build Pack` is ahead of `ADF Remote` on some later local source and
  planning changes, including the local-only Keycloak and Metro clue additions
  in `src/algosec_diagnostic_framework_template_pack/runtime_baseline.py`.
- The preserved rendered ASMS UI page is the same between the two ADF copies,
  so the visible page has not yet caught up to the later local-only source
  changes.

## March 30 Live Friction Addendum

The March 30, 2026 Keycloak content review on `adf-dev` exposed a more concrete
version of the synchronization friction this note is trying to avoid.

Observed during the live review loop:

- the plain `adf-dev` preview URL was reachable, but it initially served stale
  Keycloak page content from an older staged copy of the build pack
- the first live preview process was still running from a deleted working
  directory, which produced `404 File not found` responses even though the
  current pack files still existed on disk in the replacement path
- the older generic remote run request under
  `docs/remote-targets/adf-dev/remote-autonomy-run-request.json` had drifted
  out of the current PackFactory schema because it no longer carried
  `local_scratch_root`, so the official restage path only worked cleanly after
  switching to the newer request surface
- after the official restage, the remote Starlight source under
  `dist/candidates/adf-baseline/starlight-site/src/` still needed a fresh
  `generate-starlight-site` run before the remote review surface reflected the
  current local source changes
- that same restage replaced the generated `starlight-site` tree on `adf-dev`,
  which removed the previously installed `node_modules/` and built `dist/`
  output, so the review surface still needed `pnpm install`, `pnpm build`, and
  a clean preview restart from the live path before the expected page appeared

In plain language:

- a healthy-looking `adf-dev` URL is not enough to prove the remote review
  surface matches the current local accepted pack state
- under the current local-canonical restage model, one content review can
  require: pick the right request file, restage, regenerate the review source,
  reinstall remote Starlight dependencies, rebuild the static site, and make
  sure the preview server is not still pinned to a deleted workspace

### What This Adds To The Sync Model

The earlier checkpointed-sync argument was mostly about not treating PackFactory
as minute-by-minute Git. The March 30 live review adds a separate operator pain
point:

- review-surface freshness is now part of the sync problem, not just source and
  state reconciliation

That means the current checkpointed-sync model should carry these additional
working rules:

- treat remote preview freshness as a named checkpoint concern instead of an
  implicit side effect of restaging
- keep only one current request surface per common remote workflow, or mark
  legacy request files fail-closed so schema drift does not waste operator time
- after a restage that is supposed to refresh operator-visible Starlight
  content, verify the remote page from the rendered HTML, not only from staged
  markdown files
- when the remote review surface is built under `starlight-site/`, expect the
  build outputs and `node_modules/` to be disposable remote runtime state, not
  durable accepted ADF truth
- treat a preview process whose cwd points at a deleted tree as a stale runtime
  failure, not as a valid review surface

### Near-Term Workflow Consequence

Before any future remote-canonical mode is activated, the current local-first
workflow still needs a cleaner one-shot "refresh adf-dev review surface"
operation that does all of the following in order:

1. validate the current request surface
2. restage the current accepted pack
3. regenerate the selected Starlight artifact root
4. install or refresh remote Starlight dependencies if needed
5. rebuild the static site
6. restart the preview server from the live pack path
7. verify the rendered route content, not just the source tree

## Ownership Model

### Carry From Root

These are `Root`-owned infrastructure surfaces. They should be refreshed from
`Root` when PackFactory evolves, rather than invented independently inside
ADF:

- `.packfactory-runtime/tools/factory_ops.py`
- `.packfactory-runtime/tools/record_autonomy_run.py`
- `.packfactory-runtime/tools/run_build_pack_readiness_eval.py`
- `.packfactory-runtime/schemas/autonomy-feedback-memory.schema.json`
- `.packfactory-runtime/schemas/autonomy-feedback-memory-pointer.schema.json`
- `.packfactory-runtime/schemas/autonomy-run-summary.schema.json`
- `.packfactory-runtime/schemas/readiness.schema.json`
- `.packfactory-runtime/manifest.json`
- inherited build-pack startup and runtime contract surfaces in `AGENTS.md`
  and `pack.json` when they are part of the materialized PackFactory baseline

These are infrastructure hygiene surfaces, not ADF product truth.

### Carry From ADF Remote

These are the surfaces that should normally follow `ADF Remote` once a remote
change is explicitly accepted as real ADF progress:

- accepted ADF source/content under `src/`
- accepted ADF domain docs and notes under `docs/` when they describe the live
  ADF understanding rather than generic PackFactory inheritance
- accepted ADF source-backed task/content decisions after checkpoint review,
  not raw remote control-plane files copied blindly
- accepted appliance-backed generated artifacts when they are preserved as the
  live reviewable ADF output under `dist/candidates/algosec-lab-baseline/`

This bucket is about ADF truth, not PackFactory helper mechanics.

### Regenerate Or Import Through Workflow

These are not normal content-truth files and should not be copied
bidirectionally between the `ADF Build Pack` and `ADF Remote`:

- `status/readiness.json`
- `.pack-state/agent-memory/latest-memory.json`
- `.pack-state/agent-memory/autonomy-feedback-*.json`
- `eval/latest/index.json`
- selected `dist/candidates/` outputs when they are generated artifacts rather
  than accepted source-backed content

Use one of these bounded actions instead:

- regenerate locally from the accepted checkpoint state
- preserve and import through PackFactory evidence workflows
- leave unchanged and escalate if the accepted source boundary is unclear

### Reconcile Carefully

These files mix PackFactory control-plane behavior with ADF-local state. They
should not be copied blindly in either direction:

- `status/work-state.json`
- `tasks/active-backlog.json`

These files need selective review because they can mix:

- accepted ADF task truth
- local-only planning notes
- remote-only task movement
- PackFactory-owned control semantics

Do not copy these files wholesale in either direction when the fields disagree.

## Checkpoint Model

Use checkpointed synchronization instead of continuous mirroring.

Recommended checkpoint moments:

- after accepted remote ADF progress
- before a promotion or readiness decision
- before risky remote experimentation
- after a meaningful remote autonomy run that should be preserved
- when a reusable improvement should be harvested back into PackFactory

Outside those checkpoints, `ADF Remote` does not need to be mirrored locally
just because it changed.

For this document, `accepted remote ADF progress` means a bounded checkpoint
bundle rather than a vague feeling that the remote copy is ahead. The bundle
must name:

- the accepted `status/work-state.json` boundary
- the accepted `tasks/active-backlog.json` boundary
- any accepted remote-backed artifact provenance
- any control-plane surfaces that must be regenerated after the checkpoint

Until that bundle is chosen, mixed-file reconciliation should stay read-only.

## Where Git Helps

Git or another source-control workflow is a better fit than constant
PackFactory mirroring for:

- source files
- docs
- accepted backlog edits
- normal authoring changes that behave like code

PackFactory is still the better fit for:

- bounded remote request/staging/import workflows
- runtime evidence bundles
- readiness and promotion control-plane records
- autonomy memory activation and preservation
- audit trails tied to PackFactory workflows

## Immediate Reconciliation Buckets

### Carry From Root Now

- keep the current `.packfactory-runtime/` baseline as the PackFactory-owned
  authority
- keep `Root` as the authority for autonomy-memory semantics and workflow
  mechanics

### Carry From ADF Remote Now

- treat remote ADF task progression as the current candidate ADF content/work
  truth when deciding the next checkpoint bundle
- treat the live remote page and remote appliance-backed output as the accepted
  review surface until a newer remote-backed render replaces it

### Regenerate Or Import Now

- `status/readiness.json`
  reason: this is a generated control-plane surface and both copies are stale
- `.pack-state/agent-memory/latest-memory.json`
  reason: this pointer should be regenerated only after the accepted
  `work-state` boundary is chosen and only if the selected memory matches that
  accepted boundary
- `.pack-state/agent-memory/autonomy-feedback-*.json`
  reason: preserve or import as evidence; do not merge them field-by-field
- `eval/latest/index.json`
  reason: regenerate from accepted evidence; do not copy a stale `latest`
  pointer between workspaces

### Reconcile Carefully Now

- `status/work-state.json`
  reason: local records later local-only completions, remote records the live
  active ADF boundary, so the accepted checkpoint has to be chosen field by
  field instead of copied wholesale
- `tasks/active-backlog.json`
  reason: local added loop-boundary planning and later completion claims that
  are not yet remote-accepted ADF truth

## First Checkpoint Bundle Proposal

Bundle intent: capture the currently accepted remote ADF task boundary without
importing later local-only completions or later local-only content changes.

This first bundle is decision-only.

In plain language: the first bundle freezes one accepted checkpoint pair and
its proof surfaces. It does not yet authorize blind writes to mixed files.

### First Bundle Scope

This first checkpoint is narrow on purpose.

It is meant to preserve the current accepted ADF task boundary, not to settle
every later local ADF experiment.

### Ordered Steps For The First Bundle

1. Preserve the local-only planner task and this working note as local planning
   artifacts before any mixed-file reconciliation starts.
   Preservation target:
   keep this note under `eval/history/` and keep the local planner task record
   in the `ADF Build Pack` backlog and work-state until a later explicit
   cleanup decision says otherwise.
2. Freeze one coherent accepted checkpoint pair:
   `status/work-state.json` plus `tasks/active-backlog.json`.
3. Freeze the proof surfaces that justify that checkpoint pair.
4. Leave generated control-plane files unchanged until the accepted checkpoint
   pair and proof bundle are recorded.
5. Only after those steps, decide whether a later write bundle is safe.
   Any later mixed-file write bundle must name an explicit field-level
   allowlist for `status/work-state.json` and `tasks/active-backlog.json`.

### Carry From Root In This First Bundle

- no `.packfactory-runtime/` copy is needed in the first bundle because
  `Root`, the `ADF Build Pack`, and `ADF Remote` already match on the shipped
  helper bundle and schemas
- no `AGENTS.md`, `pack.json`, or `project-context.md` refresh is needed in
  the first bundle because those files already match between the `ADF Build
  Pack` and `ADF Remote`

### Carry From ADF Remote In This First Bundle

Accept the current remote task boundary as the candidate checkpoint:

- `status/work-state.json`
  accepted candidate boundary:
  `active_task_id=deepen_asms_ui_service_command_packs`
  `next_recommended_task_id=deepen_asms_ui_service_command_packs`
  `autonomy_state=actively_building`
  `last_outcome_at=2026-03-26T15:20:13Z`
- `tasks/active-backlog.json`
  accepted candidate task statuses:
  `deepen_asms_ui_service_command_packs=in_progress`
  `map_asms_ui_subsystem_and_validate_core_scenarios=pending`
- `dist/candidates/algosec-lab-baseline/**`
  accepted candidate review surface only:
  keep the currently served remote-backed ASMS UI page as the accepted operator
  review surface reference until a newer remote-backed render replaces it, but
  do not copy this artifact tree in the first bundle
  pinned reference:
  URL `http://10.167.2.150:18082/playbooks/asms-ui-is-down/`
  remote host `adf-dev`
  page source path
  `dist/candidates/algosec-lab-baseline/starlight-site/src/content/docs/playbooks/asms-ui-is-down.md`
  page source sha256 `32fb28d38a991b5d8c7a6bf2a3c95b286b7d7a147fed21c195b6d6c098da6aa0`

### Proof Surfaces Required For This First Bundle

Freeze these proof surfaces together with the accepted checkpoint pair:

- remote `status/work-state.json`
- remote `tasks/active-backlog.json`
- remote v4 autonomy memory artifact
  `.pack-state/agent-memory/autonomy-feedback-algosec-diagnostic-framework-build-pack-v1-active-task-continuity-run-v4.json`
- remote v4 run summary
  `.pack-state/autonomy-runs/algosec-diagnostic-framework-build-pack-v1-active-task-continuity-run-v4/run-summary.json`

The point is to preserve the evidence that the remote active boundary moved to
`deepen_asms_ui_service_command_packs` before we let any later regeneration or
pointer changes depend on it.

### Keep Local-Only In This First Bundle

Do not treat these local-only changes as accepted ADF truth in the first
bundle:

- the local planner task `define_adf_checkpointed_sync_model`
- this working note
- the local-only completion of `deepen_asms_ui_service_command_packs`
- the local-only completion of
  `clarify_adf_iteration_loop_completion_boundary`
- the local-only source additions
  `Check Keycloak recent auth and startup clues`
  and
  `Check Metro JVM error clues`

These can stay preserved in the `ADF Build Pack` as local planning or local
experiments until a later explicit checkpoint accepts them.

### Regenerate Or Import After Choosing This First Bundle

- `.pack-state/agent-memory/latest-memory.json`
  next action:
  preserve or import the exact remote v4 memory artifact first, then verify
  that its run id, active task, next recommended task, and generation timing
  all match the frozen accepted checkpoint pair, and only then consider
  regenerating the pointer
  pinned memory candidate:
  run id `algosec-diagnostic-framework-build-pack-v1-active-task-continuity-run-v4`
  artifact path
  `.pack-state/agent-memory/autonomy-feedback-algosec-diagnostic-framework-build-pack-v1-active-task-continuity-run-v4.json`
- `status/readiness.json`
  next action:
  leave unchanged in the first bundle; only a later write bundle may regenerate
  it from the accepted checkpoint state and accepted evidence surfaces
- `eval/latest/index.json`
  next action:
  leave unchanged in the first bundle; only a later write bundle may regenerate
  it from accepted evidence
- `.pack-state/agent-memory/autonomy-feedback-*.json`
  next action:
  preserve or import as evidence only; do not merge them field-by-field

### No Mixed-File Writes In This First Bundle

Do not write these files in the first bundle:

- `status/work-state.json`
- `tasks/active-backlog.json`
- `status/readiness.json`
- `.pack-state/agent-memory/latest-memory.json`
- `eval/latest/index.json`

The first bundle is complete when the accepted checkpoint pair, local-only
exceptions, and required proof surfaces are frozen together.

It is not complete when a mixed file has been rewritten.

### Future Write Bundle Allowlist

If a later write bundle is approved, it must stay inside this allowlist.

#### `status/work-state.json`

Allowed remote-led candidate fields:

- `active_task_id`
- `autonomy_state`
- `blocked_task_ids`
- `escalation_state`
- `last_agent_action`
- `last_outcome`
- `last_outcome_at`
- `next_recommended_task_id`

Allowed remote-led candidate list deltas:

- `completed_task_ids`
  no new completion claim is allowed in the first future write bundle unless a
  dedicated proof bundle exists for that exact completion boundary
- `pending_task_ids`
  may restore `deepen_asms_ui_service_command_packs` as pending/in-progress if
  that remains part of the accepted remote checkpoint pair

No-write fields in the first future write bundle:

- `resume_instructions`
- `stop_conditions`
- `last_validation_results`
- `branch_selection_hints`

Reason:
those fields currently mix local planning overlays, older remote guidance,
and PackFactory control semantics too tightly for a safe first write.

Explicit exclusions from remote-led write:

- do not import local-only completion claims for
  `clarify_adf_iteration_loop_completion_boundary`
  `deepen_asms_ui_service_command_packs`
  or
  `define_adf_checkpointed_sync_model`
- do not erase the local planner task and this working note without an
  explicit preservation or archive decision first

#### `tasks/active-backlog.json`

Allowed remote-led candidate task records in the first future write bundle:

- `deepen_asms_ui_service_command_packs`
  only its remote-backed `status=in_progress` checkpoint state
- `map_asms_ui_subsystem_and_validate_core_scenarios`
  only its remote-backed `status=pending` checkpoint state

Allowed fields inside those task records in the first future write bundle:

- `status`
- `summary`
- `blocked_by`
- `dependencies`
- `selection_priority`

No-write task records in the first future write bundle:

- `build_adf_autonomous_iteration_loop`
- `clarify_adf_iteration_loop_completion_boundary`
- `define_adf_checkpointed_sync_model`

Reason:
those are local planning artifacts and should remain local-only until a later
explicit checkpoint decides otherwise.

No-write task-record fields in the first future write bundle:

- any task not named above
- acceptance-criteria expansions added only locally after the remote checkpoint
- completion-signals expansions added only locally after the remote checkpoint
- files-in-scope expansions added only locally after the remote checkpoint
- `validation_commands`

If the write bundle needs any field outside this allowlist, stop and escalate
instead of widening the write implicitly.

### First Future Write Bundle Draft Status

Current status: blocked after adversarial review.

The first concrete draft write bundle is not safe to execute as written.

Why it is blocked:

- restoring the remote `deepen_asms_ui_service_command_packs` boundary would
  make that task active again, so the write would also have to remove it from
  any local completed set at the same time
- rewinding `last_agent_action` and `last_outcome_at` to the older remote
  checkpoint would conflict with later local planning and later local
  validation chronology unless those later local surfaces were handled
  explicitly
- leaving `resume_instructions`, `stop_conditions`, `last_validation_results`,
  and task `validation_commands` untouched would make the resulting state
  misleading for restart and audit purposes
- the remote `build_adf_autonomous_iteration_loop` completion claim still does
  not have a safe paired proof bundle for a write that would keep the current
  local loop-boundary discipline intact

So the draft patch set remains useful as analysis, but it is not an approved
write bundle.

### Preconditions For Any Safe Future Write Bundle

Before any mixed-file write bundle is approved, the plan must first define:

1. how later local-only planning artifacts stay preserved when an earlier
   accepted remote checkpoint is written into canonical state
2. whether canonical state is allowed to roll back `last_agent_action`,
   `last_outcome_at`, and similar chronology fields, or whether a separate
   checkpoint marker is needed instead of overwrite
3. how `completed_task_ids`, `pending_task_ids`, and task-record `status`
   move atomically when a task is restored from local `completed` back to
   remote `in_progress`
4. whether `resume_instructions`, `stop_conditions`, `last_validation_results`,
   and task `validation_commands` must be regenerated, archived separately, or
   moved with the accepted checkpoint
5. the exact archive or overlay destination for local-only planner tasks and
   local-only notes if canonical task state is rewound

### Narrowest Plausible Later Write Candidate

The safest later write bundle is likely narrower than the blocked draft.

Most likely safe candidate, pending the prerequisites above:

- `status/work-state.json`
  only the atomic active-boundary set:
  `active_task_id`
  `autonomy_state`
  `blocked_task_ids`
  `escalation_state`
  `next_recommended_task_id`
- `tasks/active-backlog.json`
  only the single task record
  `deepen_asms_ui_service_command_packs`
  and only if its status move is paired with matching
  `completed_task_ids` / `pending_task_ids` treatment

Everything else should stay no-write until the rollback and preservation rules
are explicit.

### No-Write Escalation In This First Bundle

Stop and escalate instead of writing if any of these checks fail:

- the remote v4 memory artifact no longer matches the accepted remote
  `work-state` boundary
- the remote-backed artifact provenance for `dist/candidates/algosec-lab-baseline/**`
  is unclear
- a proposed `tasks/active-backlog.json` or `status/work-state.json` write
  would erase the local-only planner task and note before we intentionally
  preserve them elsewhere
- the exact remote v4 run summary and memory artifact are not preserved together
  with the chosen checkpoint pair
- a proposed readiness regeneration path cannot produce correct
  `recommended_next_actions` from the accepted checkpoint boundary

## Fail-Closed File Rules

Use these actions only:

- `copy from Root`
- `checkpoint from ADF Remote into the ADF Build Pack`
- `regenerate from accepted state`
- `preserve/import as evidence only`
- `no write; escalate`

Current file rules:

- `.packfactory-runtime/**`: copy from `Root`
- `AGENTS.md` and `pack.json` inheritance surfaces: refresh from `Root` only
  when PackFactory baseline changes justify it
- `src/**`: checkpoint from `ADF Remote` into the `ADF Build Pack` only when
  the remote source change is accepted
- `docs/**` ADF domain notes: checkpoint from `ADF Remote` into the
  `ADF Build Pack` only when the note reflects accepted ADF understanding
- `status/work-state.json`: no blind copy; choose the accepted remote or local
  field values explicitly, otherwise no write and escalate
- `tasks/active-backlog.json`: no blind copy; choose the accepted remote or
  local field values explicitly, otherwise no write and escalate
- `status/readiness.json`: regenerate from accepted backlog/work-state and
  validation/eval surfaces only
- `.pack-state/agent-memory/latest-memory.json`: regenerate only after the
  accepted `work-state` boundary is chosen and only if the selected memory
  matches the accepted run/task boundary
- `.pack-state/agent-memory/autonomy-feedback-*.json`: preserve/import as
  evidence only; never merge or overwrite them casually
- `eval/latest/index.json`: regenerate only
- `dist/candidates/algosec-lab-baseline/**`: preserve/import only when host,
  run or request id, and timestamp provenance all match the accepted remote
  checkpoint; otherwise no write and escalate

## Review Questions

- Which mixed files should be remote-led, local-led, or regenerated?
- Should remote backlog and work-state be pulled back first before any further
  local ADF planning edits are accepted?
- Should stale readiness and latest-memory state be refreshed from the current
  accepted ADF boundary before any new ADF task work continues?
- Which ADF-local changes made only in the `ADF Build Pack` should be kept as
  local experiments rather than treated as accepted ADF truth?
