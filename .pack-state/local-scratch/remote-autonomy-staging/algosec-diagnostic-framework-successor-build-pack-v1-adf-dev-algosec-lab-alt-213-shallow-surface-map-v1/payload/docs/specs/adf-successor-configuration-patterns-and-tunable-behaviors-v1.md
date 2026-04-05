# ADF Successor Configuration Patterns And Tunable Behaviors v1

## Purpose

Record the first bounded configuration-pattern and tunable-behavior readout from
the successor's current imported ASMS evidence on `10.167.2.150`.

This is not a full configuration map and it is not vendor-authoritative tuning
guidance. It is a support-oriented note that separates:

- observed config or log surfaces
- repeated runtime patterns that look real
- still-unproven behavior hints worth treating cautiously

## Evidence Base

- Latest canonical imported proof bundle:
  `eval/history/import-external-runtime-evidence-20260403t113653z/`
- Machine-readable map:
  `eval/history/import-external-runtime-evidence-20260403t113653z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- Operator summary:
  `eval/history/import-external-runtime-evidence-20260403t113653z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`
- Supporting architecture readout:
  `docs/specs/adf-successor-asms-runtime-architecture-review-v1.md`

## Boundary

This note stays bounded to:

- unit fragments, drop-ins, environment files, working-directory roots
- command-line runtime options already surfaced by the successor
- repeated runtime-root patterns across visible service families
- cautious support-facing behavior hints derived from those observed patterns

This note does not claim:

- full config-file semantics
- exact vendor-recommended values
- safe change advice
- full dependency order or complete product bootstrap logic

## Observed Configuration Patterns

### 1. Systemd Is The First Reliable Control Layer

Observed:

- `httpd`, `ms-metro`, `ms-bflow`, `algosec-ms`, `aff-boot`, `activemq`, and
  failed `keycloak` all expose at least one systemd fragment path.
- Several central services also expose systemd drop-ins, especially `httpd`,
  `ms-metro`, and `ms-bflow`.
- `keycloak` exposes an environment file:
  `/usr/share/keycloak/keycloak_service.conf`

What looks real:

- For support and diagnostic work, systemd unit metadata is now a dependable
  first place to look before deeper product-local config guessing.
- Drop-ins appear to be part of the operational tuning story, not just the
  base fragment files.

Confidence:

- high

### 2. The AFA-Adjacent Java Families Follow A Shared Runtime-Root Pattern

Observed:

- `ms-metro` exposes:
  - `-Dcatalina.base=/data/ms-metro`
  - `-Dcatalina.home=/opt/apache-tomcat`
  - `/home/afa/.fa/logback-afa.xml`
  - `/data/ms-metro/logs/`
- `ms-bflow` exposes:
  - `-Dcatalina.base=/data/ms-bflow`
  - `-Dcatalina.home=/opt/apache-tomcat`
  - `/data/ms-bflow/logs/`
- Both families also expose:
  - systemd drop-in `limits.conf`
  - working-directory root candidate `/home/afa`

What looks real:

- `ms-metro` and `ms-bflow` are separate runtime families, but they follow a
  common packaging pattern:
  - shared Tomcat home
  - service-local catalina base
  - service-local `/data/.../logs`
  - likely service-local `/data/.../conf`
- `/home/afa` is probably an operator-relevant shared root for this family,
  even if not every file under it is configuration.

Tunable behavior hints:

- heap sizing differs materially by family (`ms-metro` much larger than
  `ms-bflow`), which suggests capacity or role-specific tuning rather than one
  uniform Java profile
- shared `limits.conf` drop-ins suggest some cross-family operational tuning is
  centralized at the unit level

Confidence:

- high on the shared runtime-root pattern
- medium on which exact knobs are intentionally tuned versus merely inherited

### 3. `algosec-ms` Looks Like A Smaller Wrapper-Owned Service Family

Observed:

- unit fragment `/etc/systemd/system/algosec-ms.service`
- working-directory candidate `/home/afa`
- log root `/data/algosec-ms/logs/`
- runtime flag `-Dms-configuration.port=8185`
- jar-backed runtime lineage already identified earlier

What looks real:

- `algosec-ms` does not currently look like the Tomcat-family pattern used by
  `ms-metro` and `ms-bflow`
- it looks more like a smaller wrapper-owned Java service with a clearer
  single-port role and a dedicated log root

Tunable behavior hints:

- the visible port flag makes listener identity look more directly tunable than
  the Tomcat families
- the smaller heap profile suggests this family is meant to stay narrower in
  footprint than the large application containers

Confidence:

- medium to high

### 4. Apache Is Config-Family Rich And Likely Drives Much Of The Support Surface

Observed:

- systemd fragment plus drop-ins for `httpd`
- many concrete Apache config families under `/etc/httpd/conf.d`, including:
  - `aff.conf`
  - `fireflow.conf`
  - `keycloak.conf`
  - many `algosec-ms.*.conf` files

What looks real:

- Apache configuration is highly segmented by route family or owner family
- support-facing behavior is likely influenced heavily by Apache config splits,
  not only by the local owners behind them

Tunable behavior hints:

- one of the most practical future support surfaces will be config-family
  grouping under `conf.d`, because that is where many browser-facing ownership
  distinctions become visible first

Confidence:

- high

### 5. ActiveMQ Exposes A Cleaner Service-Local Config Story

Observed:

- systemd fragment `/etc/systemd/system/activemq.service`
- config directory `/opt/apache-activemq-6.1.7/conf`
- config file `/opt/apache-activemq-6.1.7/conf/jolokia-access.xml`
- wrapper start script `/opt/activemq/bin/algosec_activemq_start.sh`

What looks real:

- `activemq` has a more traditional service-local config home than the
  broader AFA-facing application families
- this makes it a better candidate for later bounded configuration-pattern
  inference than some of the more layered wrapper-driven services

Tunable behavior hints:

- access and instrumentation behavior may be partly governed through the
  Jolokia config surface

Confidence:

- medium

### 6. Failed Keycloak Still Exposes A Real Config Entry Surface

Observed:

- unit fragment `/usr/lib/systemd/system/keycloak.service`
- environment file `/usr/share/keycloak/keycloak_service.conf`
- wrapper start script `/usr/share/keycloak/algosec_keycloak_start.sh`
- bounded journal entrypoint candidate

What looks real:

- even while failed, `keycloak` now has a credible first inspection surface
  instead of only "service failed, owner unclear"
- the environment file is the strongest visible candidate for later bounded
  identity-side configuration inference

Confidence:

- medium to high

## Cross-Cutting Pattern Readout

The strongest current pattern is:

- systemd metadata plus runtime-root hints together explain more of the suite
  than command lines alone

The second strongest pattern is:

- the ASMS families do not all share the same configuration style

In plain language:

- Apache looks route-family rich
- `ms-metro` and `ms-bflow` look like parallel Tomcat families with shared
  packaging and distinct runtime roots
- `algosec-ms` looks smaller and more direct
- `activemq` looks more traditional and service-local
- `keycloak` is failed but no longer opaque

## What Looks Potentially Tunable But Not Yet Proven

- heap sizing and memory behavior across the Java families
- systemd drop-in operational limits for the Tomcat families
- route-family behavior driven from Apache `conf.d`
- identity-side behavior driven from `keycloak_service.conf`
- logging behavior split between explicit log roots and bounded journal entry
  points

These are not yet safe change recommendations. They are bounded candidates for
later interpretation.

## Best Next Follow-On

The strongest next step is now `extend_distributed_and_external_knowledge_mapping`.

Why that now makes sense:

- the successor already has one-node runtime topology
- it now has bounded support pain points
- it now has bounded config and log inspection surfaces
- and it now has enough local-node pattern structure to plan how future
  distributed-node or external-integration reasoning should stay evidence-first
  instead of turning into folklore
