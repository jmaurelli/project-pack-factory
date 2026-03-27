# Project Pack Factory Astro Dashboard Upgrade Spec

## Status

Implemented and installation-verified on 2026-03-26 for the Astro-based
PackFactory dashboard presentation layer.

This spec assumes the Python dashboard snapshot generator remains the canonical
state-preparation layer. Astro becomes the operator-facing web UI layer that
consumes the generated snapshot and produces a more intentional web dashboard.

Current repo evidence:

- Astro app checked in at `apps/factory-dashboard/`
- canonical Astro publication wrapper checked in at
  `tools/build_factory_dashboard_astro.py`
- local operator serving wrapper checked in at
  `tools/serve_factory_dashboard.py`
- installation verified with `npm ci --no-fund --no-audit`
- publication verified with
  `python3 tools/build_factory_dashboard_astro.py --factory-root /home/orchadmin/project-pack-factory --output-dir /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest --app-dir /home/orchadmin/project-pack-factory/apps/factory-dashboard --staging-root /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/astro-staging --report-format json`

## Purpose

Define the installation and build plan for moving the PackFactory dashboard
from a plain pre-rendered static page into an Astro-authored static web
dashboard.

The goal is not to replace the dashboard snapshot contract. The goal is to
replace the presentation layer with something that feels more like a real web
dashboard to a human operator.

The operator-facing reason for this upgrade is narrower than "use Astro":

- make quality, automation, self-improvement, and next-step decisions easier
  to scan
- reduce the feeling that the dashboard is a generated document shell
- preserve the same canonical PackFactory truth while improving human reading
  speed and confidence

## Why This Planning Change Exists

The earlier Python-first dashboard path proved the data contract and static
publication model, but it did not fully match the operator expectation of a
web-based dashboard by default.

In plain language:

- the snapshot/report generator is still useful
- the operator wants a clearer web UI path
- Astro is the next bounded step because it improves page composition without
  forcing a live backend or a separate control plane
- the upgrade is only justified if it makes operator decisions faster or
  clearer than the current static page

## Review Direction

This spec has now been tightened by adversarial review around three failure
areas:

- accidental drift between the Python snapshot contract and Astro rendering
- ambiguous ownership of build publication into `history/` and `latest/`
- confusion between the Astro dev server and the canonical published dashboard

## Spec Link Tags

```json
{
  "spec_id": "astro-dashboard-upgrade",
  "depends_on": [
    "python-generated-static-dashboard",
    "autonomy-planning-list"
  ],
  "integrates_with": [
    "factory-dashboard-snapshot-contract",
    "factory-dashboard-publication-model"
  ],
  "supersedes_in_presentation_layer": [
    "python-generated-static-dashboard-html-rendering"
  ],
  "adjacent_work": [
    "operator dashboard for factory state",
    "agent-instruction performance review and optimization"
  ]
}
```

## Core Decision

PackFactory should keep one canonical dashboard data pipeline and swap only the
presentation layer.

Required boundary:

- Python remains the canonical state collector
- `dashboard-snapshot.json` remains the canonical dashboard data contract
- Astro consumes `dashboard-snapshot.json`
- Astro produces static HTML/CSS/JS output
- the final site keeps the same local-first serving model
- one PackFactory-controlled publication step remains responsible for promoting
  a completed dashboard build into `latest/`
- Python remains the single canonical publisher for PackFactory dashboard
  artifacts, even when Astro becomes the renderer

This means we are not planning a Node backend, API server, database, or
browser-side mutation layer.

## Preconditions And Decision Gates

This upgrade should not be treated as unconditional.

Required decision gates before implementation starts:

- the operator confirms Astro is the preferred presentation direction
- the current dashboard snapshot contract is stable enough to be consumed by a
  second frontend
- the team accepts a bounded Node toolchain at the factory root for dashboard
  UI work
- the team reviews at least three options before committing to Astro:
  improve the current Python-rendered page, adopt a lighter templating/static
  path, or adopt Astro
- that three-option review is recorded by updating the dashboard item in
  `PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md` with the alternatives
  considered, the selected direction, and the decision date before scaffold
  work begins

If those gates are not true, the correct action is to pause the Astro
implementation rather than blur the boundary between planning and commitment.

Required go/no-go criteria before scaffold work:

- expected operator benefit is named explicitly
- added maintenance cost is accepted explicitly
- rollback path back to the Python-rendered page remains straightforward

## Install Model

The Astro app should live in a bounded root-level app directory:

- `apps/factory-dashboard/`

Recommended tool choice:

- `npm`

Recommended runtime expectation:

- a supported Node LTS runtime available locally when working on the Astro UI
- one lockfile-owned package manager only; do not mix `npm`, `pnpm`, and
  `yarn` in the same dashboard app
- pin one exact Node LTS major before implementation begins; initial planning
  recommendation is Node 22 LTS

Planned install shape:

```bash
mkdir -p /home/orchadmin/project-pack-factory/apps
cd /home/orchadmin/project-pack-factory/apps
npm create astro@<pinned-version> factory-dashboard
cd /home/orchadmin/project-pack-factory/apps/factory-dashboard
npm install
```

Install guardrails:

- do not use `@latest` in the implementation PR
- commit the generated `package-lock.json`
- declare the pinned Node major in `package.json.engines`
- record the scaffold answers if interactive setup is used

Expected Astro app characteristics:

- static output only
- no SSR adapter
- no external CDN dependency requirement
- local assets and local fonts only
- small client-side enhancement where useful, but no heavy client state model
- explicit Astro static configuration checked into the app rather than implied
  by defaults

## Planned App Structure

The Astro app should start small and intentional:

- `apps/factory-dashboard/src/pages/index.astro`
- `apps/factory-dashboard/src/layouts/DashboardLayout.astro`
- `apps/factory-dashboard/src/components/`
- `apps/factory-dashboard/src/styles/`
- `apps/factory-dashboard/src/lib/loadDashboardSnapshot.ts`

Suggested initial component split:

- `WhatMattersHero.astro`
- `EnvironmentBoard.astro`
- `SectionCards.astro`
- `FocusedPortfolio.astro`
- `RecentMotion.astro`
- `TruthLayerLegend.astro`

The first Astro build should preserve the same section model already proven in
the snapshot:

- `What matters most now`
- `Environment Board`
- `Quality Now`
- `Automation Now`
- `Factory Learning`
- `Agent Memory`
- `Ideas Lab`
- `Recent Motion`
- `Focused Portfolio`

## Data Integration Model

Astro should not discover PackFactory state directly.

Instead, Astro should read one generated snapshot file supplied explicitly by
the PackFactory build wrapper.

Canonical publication-time input:

- `.pack-state/factory-dashboard/history/<dashboard-build-id>/dashboard-snapshot.json`

Allowed local development shortcut:

- `.pack-state/factory-dashboard/latest/dashboard-snapshot.json`

The intended direction is:

1. Python generates a versioned dashboard build root first
2. Astro reads the immutable snapshot for that same build id
3. Astro emits the operator-facing site assets for that same build id
4. PackFactory publishes the completed build to `latest/` only after snapshot,
   report, and site assets are all present

Required rule:

- no parallel Astro-only data contract

If Astro needs new fields, those fields must be added to the shared dashboard
snapshot contract rather than hidden inside Astro-only logic.

The Astro layer must not become a second source of truth for ranking rules,
truth layers, environment labels, or section identity.

Preferred dev-mode strategy:

- ship one checked-in fixture snapshot for UI work inside the Astro app, or
- explicitly document the Vite filesystem allowlist and manual refresh flow for
  reading `.pack-state/` outside the app root

The implementation should choose one of those strategies rather than leaving
dev-mode file access implicit.

## Build Model

The Astro build should remain static and local-first.

Preferred build behavior:

- Astro outputs static files only
- the build consumes one explicit immutable snapshot path
- the final built page can still be served from a small HTTP server
- the publication model keeps the PackFactory `history/<dashboard-build-id>`
  and `latest/` pattern
- the Astro build itself does not own final publication into `latest/`
- the same `dashboard_build_id` must appear in the consumed snapshot, the
  generated report, and the emitted site

Planned build inputs:

- `PACK_FACTORY_DASHBOARD_SNAPSHOT_PATH`
- `PACK_FACTORY_DASHBOARD_BUILD_ID`
- `PACK_FACTORY_DASHBOARD_OUTPUT_DIR`

Planned build output target:

- a staged Astro output directory for one dashboard build id, later promoted by
  PackFactory into `.pack-state/factory-dashboard/history/<dashboard-build-id>/`

That preserves compatibility with the current publication model and avoids
inventing a second dashboard deployment path.

Current generator compatibility note:

- `tools/generate_factory_dashboard.py` currently creates the versioned
  `history/<dashboard-build-id>/` root and then promotes that completed build
  into `latest/`
- before Astro publication starts, PackFactory should extend the current
  generator with a history-only mode so one canonical Python tool still owns
  immutable snapshot and history-build creation
- the Astro wrapper must not depend on a partially published `latest/` tree as
  its canonical input

Required publication rule:

- raw Astro output is a build artifact
- PackFactory publication is a separate atomic step
- `latest/` must never be rewritten piecemeal by Astro alone

Required Astro config contract:

- `output: "static"`
- an explicit `outDir` used only as a staged build artifact
- relative asset behavior suitable for both `history/<dashboard-build-id>/`
  and `latest/`
- one explicit trailing-slash/linking rule recorded in the app config

The implementation must not rely on Astro defaults for those publication-
sensitive behaviors.

## Build Modes

The spec should treat the three dashboard modes as distinct:

### Design Preview

- powered by the Astro dev server
- non-canonical
- used for layout and interaction work only

### Publication Build

- powered by one PackFactory wrapper command
- canonical for generated dashboard output
- responsible for snapshot generation, Astro invocation, validation, and atomic
  promotion

### Published Viewing

- powered by static serving of the completed published output
- the normal operator-facing local viewing path
- must work without Astro dev tooling

## Planned Commands

During UI development:

```bash
cd /home/orchadmin/project-pack-factory/apps/factory-dashboard
npm run dev -- --host 127.0.0.1 --port 4321
```

During static site generation, the intended canonical publication command
should be wrapper-first:

```bash
python3 tools/build_factory_dashboard_astro.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --output-dir /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest \
  --app-dir /home/orchadmin/project-pack-factory/apps/factory-dashboard \
  --staging-root /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/astro-staging \
  --report-format json
```

That wrapper is expected to obtain the immutable snapshot input by calling
`tools/generate_factory_dashboard.py --skip-latest-publish --report-format json`
first, parsing that generator report, and refusing to continue unless the
fresh report says `publication_mode: "history_only"` and
`latest_published: false`.

Optional debug-only replay mode is acceptable for wrapper development, but it
should reuse a generator-authored `dashboard-report.json` rather than taking
manual `--snapshot-path` and `--dashboard-build-id` arguments in the normal
operator path.

Raw `npm --prefix ... run build` remains an app-local development command only.

The planning recommendation is stronger than "eventually":

- the Python wrapper should be the canonical publication command
- raw `npm run build` is acceptable for local UI iteration only
- operator-facing instructions should prefer the wrapper rather than raw Astro
  environment wiring

Raw `npm run build` must not be documented as a supported publication path.

## Wrapper Responsibilities

The PackFactory wrapper owns the cross-runtime contract.

Required wrapper responsibilities:

- generate or verify the target dashboard snapshot first
- do so through one explicit contract: invoke
  `tools/generate_factory_dashboard.py --skip-latest-publish --report-format json`
  so the completed immutable `history/<dashboard-build-id>/` root exists
  before Astro runs
- use the generator-authored report as the handoff contract instead of
  operator-supplied snapshot or build-id flags in the normal publication path
- validate the snapshot schema before invoking Astro
- validate the generator report and confirm it is a fresh history-only build
- pass only validated build-time inputs into Astro
- ensure the snapshot build id and Astro target build id match
- verify required emitted site artifacts exist after the Astro build
- stage Astro output outside `latest/` and outside the canonical history build
  until validation succeeds
- overwrite the generator-authored fallback `index.html` and site assets only
  inside the finalized versioned history build after Astro succeeds
- finalize and validate `dashboard-report.json` after Astro publication so the
  report reflects the actual published renderer outputs
- preserve `dashboard-report.json` ownership on the PackFactory side
- promote a completed build into `latest/` atomically
- surface subprocess failures clearly and leave partial publication out of
  `latest/`

Astro should be treated as the site renderer, not as the owner of
`dashboard-report.json` semantics.

Renderer-status rule:

- the Python-authored `index.html` is fallback-only once the Astro path is
  adopted
- the Astro-rendered `index.html` becomes the normal published page
- fallback rendering should remain available until the Astro path has passed
  its keep-or-stop review gate

## Serving Model

Local operator use should stay simple.

Expected local options:

- Astro dev server during design work
- static HTTP server against the built output for normal local viewing

Required distinction:

- the Astro dev server is a design and debugging surface
- the static built dashboard remains the canonical operator-facing output
- dev-server behavior must not be treated as proof that publication works
- normal operator instructions should prefer static viewing of published output,
  not the dev server

Example static serving path after build:

```bash
python3 -m http.server --directory /home/orchadmin/project-pack-factory/.pack-state/factory-dashboard/latest 8000
```

This spec still does not require a persistent backend server.

If the Astro app uses runtime fetches for optional enhancements, those fetches
must target local generated artifacts only and the core operator summary must
remain fully understandable from the built HTML alone.

## UI Direction

The Astro dashboard should feel more like a real web control room and less
like a generated document shell.

Design goals:

- stronger visual hierarchy for the operator goals
- reusable components for repeated card and board patterns
- more intentional layout and typography
- better mobile and desktop behavior
- clear truth-layer visibility without clutter
- room for richer interaction later without rewriting the data contract

Guardrails:

- do not hide truth-layer provenance behind decorative UI
- do not bury mismatch warnings or evidence staleness below purely visual
  polish
- do not turn the first Astro pass into a pack-by-pack deep-link maze

The page should still stay grounded in PackFactory reality:

- canonical facts remain visually distinct from advisory memory
- the top banner must remain evidence-traceable
- environment and quality claims must stay fail-closed

## Migration Plan

### Phase 1. Install Astro And Prove Snapshot Loading

- create the Astro app scaffold
- configure Astro for static output explicitly
- load one explicit `dashboard-snapshot.json`
- render one page with the current section set
- prove that the page can render from a fixture snapshot as well as a live
  generated snapshot
- keep the Python-generated HTML path untouched during this proof

Phase 1 exit criteria:

- one Astro page builds successfully from a fixture snapshot
- one Astro page builds successfully from a live generated snapshot
- the current section set renders without introducing a second data contract

### Phase 2. Build Static Astro Output Into PackFactory Dashboard History

- wire staged Astro build output into the existing dashboard history layout
- keep `dashboard-snapshot.json` and `dashboard-report.json` alongside the
  built site
- verify the built output can replace the Python-authored `index.html`
- verify publication into `latest/` remains atomic

Phase 2 exit criteria:

- one versioned dashboard build contains `index.html`,
  `dashboard-snapshot.json`, `dashboard-report.json`,
  `assets/dashboard.css`, and `assets/dashboard.js`
- the same build can be promoted to `latest/` without partial overwrite
- static serving of the published output works without Astro dev tooling

### Phase 3. Add A Small Factory Wrapper Command

- add a PackFactory-root command that runs the snapshot generation step and the
  Astro build step together
- preserve one operator-facing command for dashboard publication
- make the wrapper fail closed when the snapshot build id, report build id, and
  Astro build target do not match
- treat the generator report as the canonical wrapper handoff and preserve
  renderer provenance in the final report

Phase 3 exit criteria:

- one documented PackFactory command performs the full publication build
- the wrapper rejects mismatched build ids and missing required artifacts
- operator instructions no longer need raw Astro environment wiring
- ownership of `dashboard-snapshot.json`, `dashboard-report.json`, and
  published `index.html` is unambiguous in the command contract

### Phase 4. Review Whether The Astro Layer Actually Helps

- confirm the operator experience is materially better
- confirm the extra Node/Astro toolchain feels worth carrying
- keep the Python snapshot generator untouched even if the Astro layer changes

Phase 4 exit criteria:

- one explicit keep-or-stop decision is recorded
- the decision names operator UX wins, maintenance cost, and rollback posture
- if Astro is not clearly worth carrying, the Python-rendered page remains the
  fallback publication path
- the keep-or-stop decision is recorded by updating the dashboard item in
  `PROJECT-PACK-FACTORY-AUTONOMY-PLANNING-LIST.md` with the dated outcome

## Success Criteria

This planning path is successful when:

- the PackFactory dashboard has a clear Astro installation path
- the build flow is still static and local-first
- the Python snapshot contract remains canonical
- the operator can run a real web UI development server during dashboard work
- the final built dashboard can still publish into the existing PackFactory
  dashboard output location
- the dashboard feels like a deliberate web application rather than a raw
  generated page
- the dev-server path and the published static path are clearly separated in
  both tooling and documentation
- Astro publication does not weaken the existing fail-closed dashboard build
  semantics
- the operator can more quickly answer the same core questions the dashboard is
  supposed to support: what is healthy, what is risky, what is improving, and
  what should happen next

## Out Of Scope

This spec does not define:

- hosted production deployment
- public internet exposure
- browser-side editing of PackFactory state
- a backend API server
- real-time websocket updates
- replacing the canonical Python dashboard snapshot generator
- granting the Astro dev server any canonical status in PackFactory evidence or
  publication workflows

## Next Planning Follow-Through

The next planning move after this spec should be:

1. update the autonomy planning list so the Astro path points here directly
2. confirm that `apps/factory-dashboard/` is the intended bounded app root
   before installation starts
3. define the wrapper command contract before implementation begins
4. use a checked-in fixture snapshot as the default dev-mode starting point for
   UI work, and treat direct `.pack-state/` reads through a Vite allowlist as
   an optional later optimization only if the fixture path proves too limiting
