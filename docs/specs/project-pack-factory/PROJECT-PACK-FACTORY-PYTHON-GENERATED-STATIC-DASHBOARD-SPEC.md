# Project Pack Factory Python-Generated Static Dashboard Spec

## Status

Proposed specification for the first PackFactory dashboard implementation.

This spec intentionally defines a Python-native, local-first first release.
It does not block a later Astro presentation upgrade, but it does require the
first useful dashboard to prove itself without adding a full frontend toolchain
at the factory root.

## Purpose

Define a simple dashboard that helps a human operator answer four questions
quickly:

- are we building quality software
- are we automating more of the factory
- is the factory actually self-improving
- what ideas or experiments look worth trying next

The dashboard should reduce repeated `load AGENTS.md` startup cost while still
staying grounded in canonical PackFactory state.

## Spec Link Tags

```json
{
  "spec_id": "python-generated-static-dashboard",
  "depends_on": [
    "autonomy-planning-list",
    "shallow-startup-and-initialization"
  ],
  "integrates_with": [
    "registry-state",
    "deployment-pointers",
    "factory-root-memory",
    "startup-benchmarking"
  ],
  "followed_by": [
    "optional-astro-dashboard-upgrade"
  ],
  "adjacent_work": [
    "operator dashboard for factory state",
    "agent-instruction performance review and optimization"
  ]
}
```

## Problem

PackFactory already has the data needed to brief an operator, but the current
path is chat-heavy.

Today, a useful executive summary often requires reading:

- registry state
- deployment pointers when assignment matters
- pack-local deployment and readiness state when current environment or quality
  claims matter
- recent promotion and retirement motion
- advisory root memory
- active planning items when the next frontier matters

That is valuable, but it is expensive to reconstruct in prompt space every
time.

The operator also needs a more human-facing view than a registry dump. A good
dashboard should not stop at control-plane state. It should connect that state
to the operator's actual goals:

- build quality software
- automate as much as possible
- self-improve
- keep room for playful ideas and experiments

## Design Goals

- keep the first release local-first and easy to run
- stay Python-native at the factory root
- generate deterministic output from canonical local state
- make the operator's goals visible, not just the factory's internals
- keep advisory memory separate from canonical truth
- preserve a clean later upgrade path to a richer presentation layer
- avoid introducing a long-running web backend for v1
- prefer structured inputs over reverse-engineering prose when both exist
- keep testing intentionally small

## Out Of Scope

This spec does not define:

- a live mutating control plane that edits registry state from the browser
- multi-user authentication or hosted access control
- realtime websocket updates
- a Node-based frontend requirement for v1
- pack-local deep dive pages for every build-pack
- replacing `load AGENTS.md` entirely

## Operator Model

The dashboard is for a human operator who wants a fast, useful control room.

The operator does not primarily want to inspect raw JSON. The operator wants
to answer:

- what is healthy and useful right now
- what still looks risky or noisy
- where automation is genuinely improving
- what the factory learned recently
- what should happen next
- which ideas are still candidates versus which are becoming real bets

That means the dashboard should feel like a project control room, not a
registry browser.

The page should also separate:

- canonical facts
- advisory memory
- generated or inferred summaries

The operator should be able to tell which kind of statement they are reading
without guesswork.

## Runtime Model

The first dashboard release should run on:

- Python 3.12 at the factory root
- static HTML, CSS, and small vanilla JavaScript
- a generated JSON snapshot for the page to read

The canonical implementation path is:

1. a Python tool reads canonical PackFactory state
2. the tool writes a deterministic snapshot plus static web assets
3. the page is served locally from disk or through a tiny static HTTP server

Recommended local serving model:

```bash
python3 -m http.server --directory /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest 8000
```

The first release must not require:

- a Node install
- an Astro build
- a React/Vite/Next runtime
- a database
- a persistent application server

## Canonical Inputs

The dashboard generator should read these structured surfaces first:

- `registry/templates.json`
- `registry/build-packs.json`
- `registry/promotion-log.json`
- `deployments/` deployment pointer files when assignment matters
- pack-local `status/deployment.json` for every pack that is shown as assigned
  to an environment or used to support an environment claim
- pack-local `status/readiness.json` for every pack surfaced in `Quality Now`
- pack-local `eval/latest/index.json` for every pack surfaced in `Quality Now`
  when the dashboard claims evidence freshness, validation status, benchmark
  status, workflow status, or recent regressions
- `.pack-state/agent-memory/latest-memory.json`
- the selected root memory artifact it points to

The dashboard may use these bounded supporting inputs for advisory content:

- `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md`
- recent git commits when repo-level tooling or doc work materially affects the
  operator view
- startup benchmark artifacts when the dashboard compares itself against the
  current startup path

Canonical truth rules:

- pack-local deployment and readiness state remain the authoritative truth for
  environment and readiness claims
- registry and deployment pointers remain canonical control-plane witnesses and
  consistency checks
- root memory is advisory
- if memory and canonical state disagree, the page must say so plainly

The v1 dashboard should avoid parsing free-form prose when a structured
machine-readable surface already exists for the same claim.

## Required Generator Command

The intended future tool is:

```bash
python3 tools/generate_factory_dashboard.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output-dir /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest \
  --report-format json
```

The exact tool does not need to exist yet for this spec to be useful, but the
command contract should stay small and deterministic.

The tool should treat `--output-dir` as the normal `latest/` publication target
and the base anchor for the sibling versioned `history/` build directory.
The report format flag should control only the machine-readable generation
report, not the dashboard page itself.

Optional wrapper-support mode:

```bash
python3 tools/generate_factory_dashboard.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output-dir /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest \
  --skip-latest-publish \
  --report-format json
```

That mode should leave `.pack-state/factory-dashboard/latest/` untouched while
still generating the full immutable
`.pack-state/factory-dashboard/history/<dashboard-build-id>/` build for a
future renderer or wrapper to consume.

## Required Output Artifacts

The generator should write, at minimum:

- `.pack-state/factory-dashboard/latest/index.html`
- `.pack-state/factory-dashboard/latest/dashboard-snapshot.json`
- `.pack-state/factory-dashboard/latest/assets/dashboard.css`
- `.pack-state/factory-dashboard/latest/assets/dashboard.js`
- `.pack-state/factory-dashboard/latest/dashboard-report.json`

Recommended optional history layout:

- `.pack-state/factory-dashboard/history/<dashboard-build-id>/...`

Required publication behavior:

- generate each dashboard build in a versioned build directory first
- write `index.html`, `dashboard-snapshot.json`, assets, and
  `dashboard-report.json` into that build directory
- promote the completed build to `latest` only after all required artifacts are
  written successfully
- record the same `dashboard_build_id` in `index.html`,
  `dashboard-snapshot.json`, and `dashboard-report.json`

Optional wrapper-support behavior:

- the generator may support a bounded history-only mode that writes the same
  completed versioned build under `history/<dashboard-build-id>/` without
  promoting it to `latest/`
- that mode is for wrapper or renderer support, not the default operator
  viewing path

The dashboard report should record for new runs:

- `dashboard_build_id`
- generated timestamp
- whether this run published `latest/` or left the build in history-only mode
- renderer identity such as `python` or `astro`
- renderer output provenance for the site artifacts that were actually
  published
- source files used
- any canonical-versus-advisory mismatches found
- summary counts used by the page
- freshness thresholds and ranking rules used by the generator
- whether startup-benchmark comparison was available and, if so, the baseline
  artifact used

Backward-compatibility note:

- historical `factory-dashboard-report/v1` artifacts may not carry the newer
  publication-mode or renderer-provenance fields
- wrapper flows should require those fields from freshly generated reports they
  consume rather than assuming older history builds already contain them

## Required Snapshot Contract

`dashboard-snapshot.json` must follow one stable machine-readable contract.

Required top-level fields:

- `schema_version`
- `dashboard_build_id`
- `generated_at`
- `source_trace`
- `what_matters_most`
- `environment_board`
- `quality_now`
- `automation_now`
- `factory_learning`
- `agent_memory`
- `ideas_lab`
- `recent_motion`
- `focused_portfolio`
- `mismatch_warnings`

The snapshot must contain structured data only.

It must not contain:

- pre-rendered HTML
- markdown blobs meant for direct rendering
- presentation-specific CSS classes
- copy that only exists in one frontend implementation

Each surfaced item in the snapshot should carry:

- a stable `id`
- a `source_kind`
- a `source_path` or source-path list
- a `truth_layer`

Allowed `truth_layer` values:

- `canonical`
- `advisory`
- `derived`

Allowed normalized environment values:

- `production`
- `staging`
- `testing`
- `ready_unassigned`
- `not_assigned`
- `mismatch`
- `unknown`

If a later Astro frontend is introduced, it must consume this snapshot
contract rather than inventing a parallel one.

## Required Information Architecture

The landing page should answer the operator's four goal areas directly while
keeping canonical state separate from advisory memory.

### 1. Quality Now

This section should help answer whether PackFactory is building quality
software.

Required signals:

- latest validation status for surfaced packs
- latest benchmark or workflow evidence status for surfaced packs when present
- evidence age for the latest surfaced quality artifacts
- missing-readiness warnings
- recent regressions or mismatches worth operator attention
- what looks risky or stale according to explicit heuristics

Suggested cards:

- validation summary
- benchmark/workflow summary
- evidence freshness summary
- missing-readiness warnings
- recent quality regressions
- evidence freshness warnings

Environment assignment may support this section, but environment assignment is
not by itself a proxy for software quality.

### 2. Automation Now

This section should help answer whether the factory is automating more of the
work in a way that is actually useful.

Required signals:

- strongest current proven autonomy surfaces with explicit source artifacts
- recent automation-related promotions or rehearsals
- manual boundaries that still exist
- explicit blocker or known-limit statements worth surfacing

Suggested cards:

- proven workflow capabilities
- latest autonomy proof
- current blockers and known limits
- automation gaps still requiring human review

If a signal comes only from advisory root memory rather than canonical
evidence, the card must be labeled as advisory.

### 3. Factory Learning

This section should help answer whether the factory is self-improving rather
than repeating isolated one-off experiments.

Required signals:

- promoted root memory highlights
- repeated capabilities that became defaults
- recent planning completions relevant to factory improvement
- the current recommended next improvement

Suggested cards:

- current focus
- latest promoted improvement themes
- recently completed frontier work
- recommended next step

This section should explicitly distinguish:

- promoted improvements evidenced in tooling or canonical state
- advisory planning direction from root memory

### 4. Agent Memory

This section should remain visually distinct from canonical state.

Required advisory fields when present:

- `current_focus`
- `next_action_items`
- `pending_items`
- `overdue_items`
- `blockers`
- `known_limits`
- `latest_autonomy_proof`
- `recommended_next_step`

If the selected root memory artifact is missing, unreadable, or lacks one of
these fields, the dashboard should omit the missing field or show a bounded
fallback such as `not available in current root memory`.

Memory-derived cards must be labeled `advisory` in both the rendered page and
the snapshot contract.

### 5. Ideas Lab

This section should preserve the operator's intentionally ambiguous idea space.

The dashboard should not force every idea into a fully formal build-pack or
tooling project immediately.

The first release should use simpler advisory buckets rather than pretending
that inferred idea states are canonical lifecycle truth.

Allowed v1 idea buckets:

- `candidate`
- `active_experiment`
- `adopted`
- `retired`

The v1 page may derive those buckets from existing planning and lifecycle
surfaces only when the derivation is explicit and repeatable.

Suggested sources for the Ideas Lab:

- unchecked items from the autonomy planning list
- near-future design tasks from root memory
- recently completed improvements that moved from idea to adopted baseline
- retired or superseded work that is useful as creative history

The Ideas Lab should make room for:

- serious next bets
- experiments
- playful concepts
- ideas that are intentionally not yet proven

Required v1 labeling rules:

- every Ideas Lab item must be labeled `advisory` unless it maps directly to a
  canonical lifecycle artifact
- each item must include its source path
- `adopted` should be used only when the improvement is evidenced in canonical
  tooling, registry state, or another machine-readable promoted surface
- `retired` should be used only when a canonical retirement or superseded state
  exists
- if a deterministic mapping is not available, the generator should omit the
  item rather than guess

## Required Page Sections

The first dashboard page should include:

- a `What matters most now` banner
- an environment board
- `Quality Now`
- `Automation Now`
- `Factory Learning`
- `Agent Memory`
- `Ideas Lab`
- recent motion
- a focused portfolio section

The page should not default to a flat list of every pack. It should visibly
prioritize.

## What Matters Most Now Rules

The top banner is the page's main decision aid, so it must be deterministic.

Required ranking order:

1. production mismatch or production assignment
2. staging mismatch or staging assignment
3. testing assignment with active blocker or stale evidence
4. ready-but-unassigned pack with missing or stale quality evidence
5. strongest recent proven improvement

Tie-break rules:

- prefer the newest canonical evidence
- if still tied, prefer the lexicographically smaller stable id

The banner should surface at most one primary item and may optionally name one
secondary item.

## Environment Board Rules

The page must distinguish clearly between:

- `live now`
- `staging now`
- `testing now`
- `ready for the next step`
- `not currently assigned`

The page must not imply that a historical promotion means a pack is still live
if the current deployment pointer no longer says so.

Required reconciliation rules:

- use pack-local `status/deployment.json` as the authoritative deployment state
  for an individual pack
- use deployment pointer files as the current environment assignment board
- use registry deployment fields as consistency witnesses, not as the sole
  source of live-environment truth
- if pack-local deployment state, deployment pointer, and registry state agree,
  the environment card may be shown as canonical
- if any of those surfaces disagree, the environment card must be shown as
  `mismatch` with a source trace
- if a pointer is missing for an environment, the dashboard may state only that
  nothing is currently assigned there from the environment board
- if more than one pointer claims the same environment, the environment card
  must fail closed as `mismatch`
- if a required pointer or pack-local deployment file is malformed or
  unreadable, the environment card must fail closed as `unknown` or `mismatch`

## Snapshot And Mismatch Rules

The generator should compute one bounded dashboard snapshot from canonical
state.

Required behavior:

- prefer structured canonical surfaces over prose sources
- use pack-local deployment and readiness state for deployment and quality
  claims
- use root memory only as an advisory layer
- annotate mismatches instead of silently resolving them
- keep the generated page deterministic for the same source snapshot

The generator should also define explicit heuristics for derived summaries.

Required derived-summary rules:

- freshness windows, stale thresholds, and recent-motion windows must be
  recorded in `dashboard-report.json`
- any value described as risky, stale, strongest, freshest, or top-priority
  must be backed by a deterministic rule or omitted
- if a deterministic derivation is not available, the generator should omit the
  claim rather than invent a narrative summary

## Frontend Constraints

The first dashboard frontend should use:

- semantic HTML
- one local CSS file
- one small local JavaScript file
- no external CDN dependencies
- no client-side framework requirement

The JavaScript should be optional for core understanding. If JavaScript is
disabled, the page should still render the main operator summary.

`index.html` must be fully pre-rendered with the core summary already present.
`dashboard.js` may only add progressive enhancement such as filtering, hiding,
or expanding cards. It must not be required to fetch core content.

## Relationship To Later Astro Upgrade

This spec intentionally leaves room for a later Astro presentation layer.

Required boundary:

- the Python generator remains the canonical state-collection and snapshot
  generation layer
- a later Astro frontend may consume `dashboard-snapshot.json`
- the first useful dashboard must not be blocked on that upgrade

In plain language: prove usefulness first, then decide whether richer page
composition is worth the extra tooling.

## Success Criteria

This spec is successful when:

- an operator can open one local page and understand current quality,
  automation, self-improvement, and ideas status quickly
- the page is built from canonical PackFactory state rather than hand-edited
  prose
- the dashboard reduces the need to reconstruct the same executive summary in
  chat repeatedly
- the first release stays simple enough that it does not become its own
  tooling tax
- a later Astro upgrade remains possible without discarding the snapshot
  contract
- when the latest startup benchmark artifact is available, the dashboard report
  records the comparison baseline and whether the dashboard reduced repeated
  source reconstruction for the same operator summary task
- the top banner and focused portfolio are traceable to explicit evidence
  rather than narrative guesswork

## Testing And Validation

Keep the validation slice small.

For the eventual generator:

- validate that required input files exist
- fail clearly when canonical sources cannot be loaded
- record mismatch warnings in `dashboard-report.json`
- validate that `dashboard-snapshot.json` follows one stable schema version
- keep volatile metadata such as timestamps and build ids in explicit metadata
  fields and `dashboard-report.json`, not mixed into core structured content
- include at least one fixture-based acceptance test with fixed input artifacts
  and expected environment board, top-banner id, and section presence
- keep any snapshot tests bounded to core counts, assignments, and section
  presence rather than pixel-perfect UI locking

The dashboard should be treated as a summarized operator surface, not as a
replacement truth layer.
