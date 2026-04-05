# ADF Successor Bounded Dependency Graph v1

## Purpose

Record the first dependency-focused successor artifact after the thin
multi-node topology surface became available.

This graph stays fail-closed. It separates:

- directly evidenced runtime edges
- strong inferred edges
- unresolved edges that still need better proof

It is not a full suite graph.

## Evidence Base

- `docs/specs/adf-successor-thin-multi-node-topology-map-v1.md`
- `eval/history/import-external-runtime-evidence-20260403t172733z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172733z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t172516z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t110310z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t110310z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t105216z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t105216z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`

## Directly Evidenced Edges

These edges have direct route, packet, or exact listener-ownership support.

### Apache To AFF

- `httpd -> aff-boot`

Evidence:

- `/FireFlow/api` and `/aff/api` route through Apache `aff.conf`
- both routes point to local `1989`
- local `1989` is bounded to `aff-boot`
- AFF session parity confirms the Apache-fronted and direct local session path
  behave the same at the current boundary

Why this is a dependency edge:

- the front-door AFF or FireFlow API path depends on `aff-boot` as the current
  local route owner on the CM node

### Apache To BusinessFlow

- `httpd -> ms-bflow`

Evidence:

- `/BusinessFlow` and related `algosec-ms.ms-bflow.conf` route hints point to
  local `8081`
- local `8081` is bounded to `ms-bflow`

Why this is a dependency edge:

- the CM-side BusinessFlow route family currently depends on `ms-bflow` as its
  local owner

### Apache To Metro

- `httpd -> ms-metro`

Evidence:

- `/afa/external` and `/afa/api/v1` route through Apache to local `8080`
- local `8080` is bounded to `ms-metro`
- this route family remains visible on both the CM and remote-agent nodes

Why this is a dependency edge:

- the AFA-facing bridge and API entry surfaces currently depend on `ms-metro`
  as their visible local owner

### Apache To AlgoSec-MS

- `httpd -> algosec-ms`

Evidence:

- Apache rewrite and route families point to local `8185`
- local `8185` is bounded to `algosec-ms`
- the same family remains visible on both the CM and remote-agent nodes

Why this is a dependency edge:

- the local configuration and API-facing route family currently depends on
  `algosec-ms` as the visible runtime owner

## Strong Inferred Edges

These edges are stronger than loose adjacency but still depend on bounded
interpretation rather than a single direct route-owner packet.

### FireFlow Or AFF To Metro

- `aff-boot or FireFlow session path -> ms-metro`

Inference basis:

- the AFF cookie-handoff packet shows FireFlow session `bcbefc00d0` carrying an
  FA-session token through `/afa/external//bridge/storeFireflowCookie`
- the same carried token family later appears on `/afa/external//session/extend`
- `/afa/external` is route-hinted to `ms-metro` on local `8080`

Why this is strong but not fully direct:

- the bridge surface is clear and the route hint is strong, but the graph still
  stops short of claiming full end-to-end browser or orchestration flow

### FireFlow UserSession To AFA Session Context

- `aff-boot or FireFlow UserSession flow -> reused FA-session context`

Inference basis:

- retained UserSession packets show concrete `ff-session -> reused FA-session`
  pairs
- retained windows also keep `UserSession::isUserSessionValid` markers visible
- the upstream origin clue and bootstrap-versus-polling packet show that at
  least one bounded bootstrap anchor later collapses into shared polling and
  reuse behavior

Why this is strong but not fully direct:

- the successor can show reuse and bounded carry-forward, but it still does not
  reconstruct the full original external action that created the session

### Provider Driver Families To Node-Local Service Units

- `Apache provider config families -> ms-devicedriver-aws`
- `Apache provider config families -> ms-devicedriver-azure`

Inference basis:

- provider packets on both CM and RA show matching Apache config families,
  local service units, local listener ports, jar paths, and journal entrypoints
- the same AWS and Azure driver families appear on both nodes

Why this is strong but not fully direct:

- the provider packets prove bounded activation and local placement, but they do
  not yet prove deeper call order, health, or whether `algosec-ms` is acting as
  a mediator, a peer, or only a naming family

### Shared Runtime Spine Across CM And Remote Agent

- `CM node <-> shared suite base`
- `RA node <-> shared suite base`

Inference basis:

- both nodes repeat `httpd`, `ms-metro`, `algosec-ms`, `activemq`, and the
  provider-driver families
- the two nodes are on the same `A33.10.260` line

Why this is strong but not fully direct:

- the repeated family set is enough to treat these as shared distributed
  runtime layers, but not enough to claim exact east-west direction or
  authority

## Explicitly Unresolved Edges

These edges remain out of scope or not yet proven strongly enough.

### Cross-Node Directionality

Still unresolved:

- whether the CM initiates provider-driver work on the RA
- whether the RA initiates work back toward the CM
- whether some repeated families are active-active, primary-secondary, or only
  co-installed

### Metro Versus AlgoSec-MS Internal Dependency Order

Still unresolved:

- whether `ms-metro -> algosec-ms`
- whether `algosec-ms -> ms-metro`
- whether they are peers behind Apache with only partial overlap

The repeated cross-node presence makes this an important next area, but the
current proof does not justify picking a winner yet.

### ActiveMQ Direction And Role

Still unresolved:

- which services depend on `activemq`
- whether `activemq` is central messaging for both nodes or a repeated local
  substrate with different functional weight

### Keycloak Placement Beyond CM-Local Visibility

Still unresolved:

- whether identity traffic is CM-local only
- whether the RA consumes identity surfaces indirectly
- whether Keycloak absence on the RA means role difference, route absence, or
  simply lack of evidence in this bounded pass

### Provider Health And External API Reachability

Still unresolved:

- whether AWS or Azure integrations are actually healthy
- whether credentials are valid
- whether sync or inventory is current

Those are integration-health questions, not dependency-graph questions.

## Operator Readout

The current bounded dependency graph says:

- Apache is the clearest front-door dependency hub
- `aff-boot`, `ms-bflow`, `ms-metro`, and `algosec-ms` are the strongest
  directly evidenced local owners behind that hub on the CM node
- FireFlow or AFF behavior has a strong bounded dependency on the AFA or Metro
  bridge surface
- AWS and Azure driver families are repeated and real on both nodes, but their
  deeper service ordering is still unresolved
- the CM-plus-RA pair now supports dependency work, but not a complete suite
  graph

## Next Step

Advance to `capture_health_validated_integration_model` and focus first on the
already-visible AWS and Azure driver families plus the AFA-facing bridge
surfaces.
