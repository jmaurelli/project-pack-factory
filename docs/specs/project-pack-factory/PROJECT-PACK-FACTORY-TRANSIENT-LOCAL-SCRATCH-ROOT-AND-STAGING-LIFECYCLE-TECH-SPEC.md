# Project Pack Factory Transient Local Scratch Root And Staging Lifecycle Tech Spec

## Status

Proposed explicit specification on 2026-03-29.

This spec exists because PackFactory-local remote-autonomy workflows generated
large transient local payload trees under the slash-backed repository root and
filled `/` close to exhaustion. The fix in scope is more fundamental than
manual cleanup: the factory should classify transient local staging as scratch,
route it through an agent-managed local scratch root that can live on another
directory or partition, and then apply cleanup and disk-pressure guardrails on
top of that boundary.

## Purpose

Define the PackFactory-local design for:

- identifying which remote-autonomy workflows write transient local payloads
- classifying those payloads as scratch rather than canonical preserved
  evidence
- moving those writes behind an agent-managed local scratch-root abstraction
- allowing that scratch root to live on another mounted directory or partition
- preserving deterministic path contracts and fail-closed validation
- adding automatic cleanup, bounded retention, and disk-pressure checks so the
  same failure does not silently recur

## Spec Link Tags

```json
{
  "spec_id": "transient-local-scratch-root-and-staging-lifecycle",
  "depends_on": [
    "remote-autonomous-build-pack-execution",
    "remote-autonomy-end-to-end-roundtrip",
    "external-runtime-evidence-import",
    "autonomy-planning-list"
  ],
  "integrates_with": [
    "remote-autonomy-staging-common",
    "remote-autonomy-roundtrip-common",
    "push-build-pack-to-remote",
    "pull-remote-runtime-evidence",
    "factory-root-work-tracker"
  ],
  "adjacent_work": [
    "lean-remote-staging-note-20260329",
    "disk-pressure guardrails for transient factory artifacts"
  ],
  "followed_by": [
    "automatic cleanup on successful remote-autonomy completion",
    "bounded retention sweeper for stale scratch payloads",
    "dashboard or validation surfacing for local scratch pressure"
  ]
}
```

## Problem

PackFactory currently writes transient remote-autonomy staging data under the
slash-backed factory root. That makes temporary staging payload growth compete
with source, registry, deployments, and other root-local artifacts for the
same filesystem capacity.

On 2026-03-29, that design caused an urgent disk-pressure incident:

- `/` was at `97%` usage on `/dev/mapper/ubuntu--vg-ubuntu--lv`
- filesystem capacity was `58G` total, `53G` used, `1.9G` free
- `/home/orchadmin/project-pack-factory` was about `13G`
- `/home/orchadmin/project-pack-factory/.pack-state` was about `13G`
- `/home/orchadmin/project-pack-factory/.pack-state/remote-autonomy-staging`
  alone was about `12G`

The main pressure came from repeated transient ADF-heavy payload trees under
`remote-autonomy-staging/`, including many directories around `251M` and many
more around `533M` to `534M` each. These were local scratch copies created by
PackFactory workflows, not the canonical long-term evidence surfaces that the
factory actually relies on for preserved history.

After removing only the pre-2026-03-29 transient staging directories:

- `remote-autonomy-staging` dropped from about `12G` to `541M`
- `/` dropped from `97%` used to `76%` used
- filesystem usage became `42G` used with `14G` free

That recovery confirms the main issue was transient local staging placement
and lifecycle, not broad root-system growth.

## Why Existing Payload Slimming Was Not Enough

PackFactory already improved the size of each staged remote payload through:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-LEAN-REMOTE-STAGING-NOTE-20260329.md`

That note records a real improvement:

- before: about `233.25 MiB` staged payload size for a representative ADF
  payload
- after: about `2.42 MiB`

That fix mattered and should remain in place. But it did not solve the
underlying local-disk problem by itself. Repeated local staging runs still
accumulated enough transient payload state to fill `/` because the scratch
location remained under the factory root and the lifecycle remained too
preserve-by-default.

In plain language: slimmer payloads helped, but PackFactory still treated
transient local scratch like if it belonged beside the factory’s durable
control-plane state.

## Evidence Summary

### Disk-usage evidence from the 2026-03-29 cleanup

Observed before cleanup:

- `/`: `58G` total, `53G` used, `1.9G` free, `97%`
- `/home/orchadmin/project-pack-factory`: about `13G`
- `.pack-state`: about `13G`
- `.pack-state/remote-autonomy-staging`: about `12G`

Observed after deleting only older transient staging directories:

- `.pack-state/remote-autonomy-staging`: `541M`
- `/`: `58G` total, `42G` used, `14G` free, `76%`

Important contrast surfaces from the same investigation:

- systemd journals: `72M`
- `.git`: about `94M`
- `.pack-state/remote-autonomy-roundtrips`: `189M`
- `.pack-state/remote-runtime-imports`: `14M`
- `.pack-state/remote-runtime-pulls`: `6.9M`
- `.pack-state/agent-memory`: `1.5M`

This supports the conclusion that local transient remote-autonomy staging was
the dominant root-cause pressure, not logging, Git history, or the smaller
local orchestration and preserved-evidence-adjacent surfaces examined during
the same cleanup pass.

Interpretation note:

- `remote-runtime-imports/` is the clearest durable preserved evidence line in
  this comparison
- `remote-autonomy-roundtrips/`, `remote-runtime-pulls/`, and `agent-memory/`
  are PackFactory-managed support surfaces that may preserve useful local
  state, but they were not the dominant slash-partition pressure source in the
  measured incident

### Code-path evidence

PackFactory currently hard-wires transient local staging under the factory
root:

- `tools/remote_autonomy_staging_common.py`
  - `LOCAL_STAGING_ROOT = Path(".pack-state") / "remote-autonomy-staging"`
- `tools/push_build_pack_to_remote.py`
  - `_local_stage_root(factory_root, run_id) -> factory_root / LOCAL_STAGING_ROOT / run_id`
  - payload snapshot and target manifest are written there before remote push
- `tools/run_remote_autonomy_loop.py`
  - reads the local target manifest from the same staging root

PackFactory also hard-wires pulled roundtrip bundles under the factory root:

- `tools/remote_autonomy_roundtrip_common.py`
  - `LOCAL_ROUNDTRIP_ROOT = Path(".pack-state") / "remote-autonomy-roundtrips"`
  - `canonical_local_bundle_staging_dir(...)` resolves to
    `.pack-state/remote-autonomy-roundtrips/<target>/<pack>/<run>/incoming`
- `tools/run_remote_active_task_continuity_test.py`
  - builds wrapper requests using that deterministic local bundle staging dir
- `tools/run_remote_memory_continuity_test.py`
  - does the same for memory continuity runs
- `tools/pull_remote_runtime_evidence.py`
  - requires the local staging directory to stay under the selected factory
    root

So the current design is not merely “using a default path.” For
`remote-autonomy-staging`, the local location is hard-wired under the factory
root. For pulled roundtrip bundles, the local location is both hard-wired and
explicitly validated to stay under the factory root.

## Root Cause

The main root cause is not just missing cleanup. It is a control-plane design
decision:

1. PackFactory classifies transient local staging by directory convention but
   still places it under the same slash-backed root as the durable repo.
2. The shared helpers and request validators require those transient paths to
   live under the factory root.
3. Successful runs preserve too much local staging by default instead of
   cleaning scratch immediately after the durable outputs exist.
4. Disk pressure is not surfaced early enough to stop or redirect new staging
   runs before `/` becomes urgent.

## Decision

PackFactory should introduce a first-class local scratch-root abstraction for
transient local workflow artifacts and route remote-autonomy staging through
that abstraction.

Required decision boundary:

- transient local staging is scratch
- transient local roundtrip `incoming/` payload trees are scratch
- canonical evidence import and durable control-plane state are not scratch
- the scratch root may live on another directory or partition
- the scratch root must still be PackFactory-managed and deterministic
- the selected scratch root is PackFactory-managed host-local state, not a
  request-file authority chosen by a remote run payload
- cleanup and retention apply only to scratch, not to canonical history

## Design Goals

- allow transient remote-autonomy local writes to live outside the slash-backed
  repo root
- preserve deterministic path construction for staging and roundtrip workflows
- keep fail-closed validation instead of allowing arbitrary free-form paths
- keep canonical preserved evidence inside PackFactory control-plane surfaces
- make cleanup safe by scoping deletion to PackFactory scratch paths only
- preserve enough manifest and reporting information to debug failures
- keep the operator workflow simple
- avoid breaking existing workflows when no alternate scratch partition exists

## Non-Goals

This spec does not require:

- moving registry state, deployments, templates, build-packs, or imported
  evidence out of the repo
- rewriting remote target path contracts
- adding a daemon, database, or long-running cleanup service
- treating every `.pack-state` subtree as scratch
- deleting failed-run scratch before the operator has a bounded chance to
  inspect it

## Canonical Surface Classification

### Scratch surfaces in scope

The following local surfaces should be treated as transient scratch:

- local payload snapshots under `remote-autonomy-staging`
- local target manifests stored only to support a pending or just-finished
  remote run
- local pulled bundle trees under remote-autonomy roundtrip `incoming/`
  directories
- generated import requests and roundtrip manifests that are currently written
  inside those same scratch directories
- other tool-generated local payload copies whose only role is to bridge a
  remote push, pull, import, or roundtrip handshake

### Durable or canonical surfaces out of scope

The following must not be treated as scratch by this spec:

- `registry/`
- `deployments/`
- `build-packs/`
- imported runtime evidence preserved under `eval/history/`
- root or pack-local memory pointers and selected memory artifacts
- other machine-readable control-plane state whose job is to preserve the
  canonical factory history or current truth

Important clarification:

- this spec does not treat the entire current
  `remote-autonomy-roundtrips/` tree as durable by default
- the current `incoming/` subtree is transient local scratch
- imported runtime evidence preserved under `eval/history/` remains the
  canonical durable evidence line
- if PackFactory wants to preserve roundtrip manifests or related audit
  artifacts durably, it must copy or write them outside scratch before scratch
  cleanup runs

### Important boundary note

Some current paths mix transient and durable meanings too closely. The design
change should preserve the durable meaning and relocate only the genuinely
transient local payload content.

## Required Technical Design

### 1. Introduce a PackFactory-managed local scratch-root resolver

PackFactory should expose one shared resolver for transient local storage.

Required behavior:

- if an agent-managed persisted selection already exists, reuse it so the
  chosen scratch root stays stable across sessions
- if no persisted selection exists, let PackFactory choose a writable
  alternate mounted location on a different filesystem when one is available
- if no alternate filesystem candidate is available, use a deterministic
  fallback under the factory root so current workflows still work
- if an explicit emergency seed or override is supplied, allow an absolute
  path outside the factory root so PackFactory can be steered without editing
  requests by hand
- resolve symlinks and normalize the selected path
- create the root on demand when needed
- reject dangerous or ambiguous values fail-closed
- treat the selected root as local factory configuration only; remote run
  requests, wrapper requests, pulled manifests, and imported bundles must not
  be allowed to override it directly

Required authority rule:

- the local PackFactory runtime selects the scratch root
- the selection should be persisted in PackFactory-local state so later agent
  sessions see the same chosen root without requiring operator re-entry
- request payloads may record the resolved selected root for auditability and
  replay consistency
- request payloads must not be allowed to choose a different scratch root than
  the one selected by the local resolver
- later workflow steps must validate against the persisted resolved root from
  request creation time so a changed CLI flag, environment variable, or host
  default does not make an existing request ambiguous

Recommended precedence:

1. already-persisted PackFactory-local selection state
2. explicit CLI override when present
3. environment variable such as `PACKFACTORY_LOCAL_SCRATCH_ROOT` as an
   emergency seed or manual override
4. agent-managed auto-selection of an alternate mounted filesystem
5. default repo-local scratch root

Recommended default root:

- `/home/orchadmin/project-pack-factory/.pack-state/local-scratch`

The exact default path can remain under `.pack-state` for backward
compatibility, but the abstraction must make alternate mounted storage a real
supported option rather than an ad hoc patch, and the normal operator
experience should not depend on remembering to set an environment variable.

Required agent-first behavior:

- PackFactory should attempt to choose and persist a suitable scratch root on
  its own before falling back to repo-local storage
- the persisted selection should be a host-local PackFactory state artifact,
  not a chat-only memory or an operator shell habit
- explicit environment configuration should remain available, but it should be
  an exception surface rather than the default control plane

An operator may also satisfy the same storage goal through a mount point
beneath the factory root, but the code contract should support an explicit
configured scratch root rather than depending on mount tricks alone.

Important limitation:

- the repo-local default is a compatibility fallback, not a complete
  recurrence-prevention answer for slash-backed hosts
- on hosts that keep the default scratch root under `/`, the disk-pressure
  guard in this spec must remain mandatory before PackFactory stages new large
  transient payloads
- active hosts should have an operator-visible migration path toward an
  alternate partition or mounted scratch location rather than treating the
  fallback default as the final steady state

### 2. Move transient local staging paths behind the shared resolver

Required migrated surfaces:

- current `remote-autonomy-staging`
- current local pulled-bundle roundtrip `incoming/` trees

Recommended canonical scratch layout:

- `<scratch-root>/remote-autonomy-staging/<run-id>/...`
- `<scratch-root>/remote-autonomy-roundtrips/<target>/<pack>/<run>/incoming/...`

The path layout should remain deterministic so manifests and operators can
predict where the scratch for a given run will live.

Request-persistence rule:

- when a run request or wrapper request is created, PackFactory must record
  the resolved scratch root selected by the local resolver at that moment
- later workflow steps must derive the expected per-run scratch path from that
  persisted resolved root, not from a newly re-read ambient default
- if a later process sees a different currently configured scratch root than
  the one persisted in the request, PackFactory must fail closed with a clear
  scratch-root mismatch error unless the operator uses an explicit migration or
  rewrite workflow

### 3. Update validators to anchor against the selected scratch root

Current validation rules require local bundle staging to remain under the
factory root. That should change to:

- require the path to resolve under the selected PackFactory scratch root
- still reject arbitrary paths outside that root
- still require the deterministic canonical per-run path beneath that root

In plain language: this should become “must stay under the configured scratch
root,” not “must stay under the repo.”

The validator change must preserve the current fail-closed behavior:

- requests may continue to record deterministic resolved scratch paths for
  auditability
- those request fields must not become operator-selectable authority that can
  redirect PackFactory scratch to arbitrary locations
- the authoritative scratch root comes from the local PackFactory resolver,
  and request-time paths must match the deterministic path derived from that
  resolver
- replaying an existing request must continue to use the resolved scratch root
  locked into that request rather than silently reinterpreting the request
  through a newer ambient configuration

### 4. Record the selected scratch root in operator-visible outputs

Result manifests and reports should record:

- the resolved scratch root
- the resolved transient staging path used for the run
- whether agent-managed auto-selection, repo fallback, or an explicit seed or
  override selected it

This matters for auditability, support, cleanup, and confirming which
agent-managed selection path a host is currently using.

### 5. Separate durable reporting from scratch before cleanup

Current code writes some operator-visible artifacts inside the same scratch
trees that hold the pulled bundle payloads:

- `generated-import-request.json`
- `roundtrip-manifest.json`

Those currently live under `local_bundle_staging_dir` in both:

- `tools/run_remote_active_task_continuity_test.py`
- `tools/run_remote_autonomy_test.py`

That means a naive cleanup-on-success implementation would delete artifacts the
operator may still need to inspect.

Required design rule:

- any manifest, request, report, or audit artifact that must survive scratch
  cleanup must be written directly to a durable path outside scratch or copied
  there before cleanup
- scratch-local copies may remain for convenience, but only as redundant
  transient mirrors
- imported evidence under `eval/history/` remains the canonical durable
  evidence destination
- wrapper-level roundtrip audit artifacts that operators still need after
  cleanup must be promoted into a durable PackFactory-managed location outside
  scratch before cleanup runs

### 6. Add cleanup-on-success for scratch

Redirecting scratch off the repo root is the structural fix, but PackFactory
should still clean scratch aggressively once the durable outputs exist.

Required baseline:

- successful remote push/pull/import workflows should be able to remove their
  transient local staging payloads automatically
- preserve failed or incomplete runs by default unless the cleanup policy says
  they are stale enough to prune safely
- if a run requests explicit preservation for debugging, honor that bounded
  preserve mode

Cleanup precondition:

- cleanup-on-success must not run until every manifest, request, report, or
  audit artifact that needs to survive the run has already been written or
  copied outside scratch

### 7. Add a bounded retention sweeper

PackFactory should support a local scratch sweeper that prunes old transient
scratch by deterministic policy.

Recommended baseline policy:

- age-based pruning for completed scratch older than a configured threshold
- optional size-based pruning when total scratch exceeds a configured budget
- do not prune paths marked active or in-progress
- log what was deleted and why

Required lifecycle marker:

- each scratch run root must carry a small PackFactory-written lifecycle
  manifest or equivalent marker
- at minimum that marker must distinguish `active`, `completed`, `failed`,
  `preserved_for_debug`, `abandoned`, and `cleanup_eligible`
- the sweeper must use that marker, plus bounded freshness signals such as the
  last update time, instead of guessing state from directory names alone
- after a crash or interrupted run, PackFactory must prefer preserving scratch
  until the lifecycle state can be reconciled explicitly

### 8. Add preflight disk-pressure guards

Before materializing large transient payloads, PackFactory should:

- check free space on the filesystem backing the selected scratch root
- check current scratch-root size
- fail closed or require explicit operator acknowledgement when the selected
  thresholds are exceeded

This is the layer that turns a future recurrence into a bounded operator
decision instead of a surprise.

## Services And Files In Scope

The implementation driven by this spec should start with these surfaces:

- `tools/remote_autonomy_staging_common.py`
- `tools/remote_autonomy_roundtrip_common.py`
- `tools/push_build_pack_to_remote.py`
- `tools/run_remote_autonomy_loop.py`
- `tools/pull_remote_runtime_evidence.py`
- `tools/run_remote_active_task_continuity_test.py`
- `tools/run_remote_memory_continuity_test.py`
- `tools/run_remote_autonomy_test.py`
- `docs/specs/project-pack-factory/schemas/remote-autonomy-run-request.schema.json`
- `docs/specs/project-pack-factory/schemas/remote-autonomy-test-request.schema.json`
- `docs/specs/project-pack-factory/schemas/remote-roundtrip-manifest.schema.json`
- `docs/specs/project-pack-factory/schemas/external-runtime-evidence-import-request.schema.json`
- any schema or manifest surface added to record the resolved scratch root or
  scratch lifecycle marker
- any higher-level exercise or wrapper tool that assumes the current
  repo-local transient path contract

Likely adjacent docs to update:

- `AGENTS.md`
- `README.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-OPERATIONS-NOTE.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMY-END-TO-END-ROUNDTRIP-TECH-SPEC.md`
- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-REMOTE-AUTONOMOUS-BUILD-PACK-EXECUTION-TECH-SPEC.md`

## Safety Constraints

- scratch-root deletion logic must never target arbitrary user paths
- registry, deployment, promotion, imported evidence, and memory truth
  surfaces must remain outside scratch cleanup
- active or in-flight run paths must be protected from retention pruning
- request payloads and pulled manifests must never be allowed to select an
  arbitrary scratch root outside the locally configured PackFactory boundary
- if PackFactory cannot prove a path is scratch, it must preserve it
- the system should stay fail-closed when configuration is missing,
  contradictory, or dangerous

## Migration Plan

### Phase 1: scratch-root abstraction

- add the shared scratch-root resolver
- move transient local staging and roundtrip incoming paths behind it
- update validators, request builders, and schemas
- separate durable report or manifest outputs from scratch-only payload trees

### Phase 2: lifecycle cleanup

- add cleanup-on-success
- add preserve-for-debug mode

### Phase 3: retention and disk guard

- add the bounded sweeper
- add preflight free-space and scratch-size checks
- surface the selected scratch root and pressure status in reports or
  validation outputs

## Success Criteria

- PackFactory can place transient local remote-autonomy payloads on another
  directory or partition without breaking deterministic workflow contracts
- the shared validators no longer require these transient paths to live under
  the repo root
- durable manifests, requests, or audit artifacts that operators still need
  survive scratch cleanup because they are written or copied outside scratch
- successful workflows no longer preserve large transient payload trees by
  default when durable outputs already exist elsewhere
- the design clearly separates scratch from canonical preserved evidence
- the 2026-03-29 slash-partition failure mode becomes either impossible or a
  bounded fail-closed operator decision instead of a silent accumulation path

## Why This Matters

This is a factory-quality issue, not just a one-time cleanup chore.

PackFactory itself generated the local payload trees that filled `/`. The
correct response is not only to delete them faster. The correct response is to
make the factory explicit about what is scratch, write scratch to a managed
scratch root that can live on another partition, and preserve only the durable
surfaces that actually need to stay in the repo.
