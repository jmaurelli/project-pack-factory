# ADF Successor ASMS Runtime Architecture Review v1

## Purpose

Record one bounded architecture readout for the observed ASMS lab runtime on `10.167.2.150` using successor evidence only. This review is meant to help later diagnostic and support-facing mapping start from visible seams instead of folklore.

## Evidence Base

- Canonical imported proof bundle: `eval/history/import-external-runtime-evidence-20260403t110310z/`
- Canonical machine-readable map: `eval/history/import-external-runtime-evidence-20260403t110310z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- Canonical operator summary: `eval/history/import-external-runtime-evidence-20260403t110310z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`
- Runtime host posture: `adf-dev` at `10.167.2.151` remains the runtime owner and support-facing publication host; target `10.167.2.150` remains the observed lab appliance.

## Runtime Frame

Observed target identity:

- Hostname: `algosec`
- OS: `Rocky Linux 8.10 (Green Obsidian)`
- Kernel: `4.18.0-553.89.1.el8_10.x86_64`
- Collection mode: read-only SSH through the target connection profile

This is enough to treat the current review as an appliance-style single-node runtime readout, not a generic Linux inventory and not a distributed-suite topology map.

## Observed Runtime Families

### 1. Edge And Request Steering

Observed:

- `httpd.service` is active and owns edge listeners on `80` and `443`.
- Apache config hints route browser-facing paths inward to distinct local owners.
- The clearest named route families in the current proof are:
  - `/BusinessFlow` -> `ms-bflow` on `8081`
  - `/afa/external` and `/afa/api/v1` -> `ms-metro` on `8080`
  - `/algosec/swagger/...` -> `algosec-ms` on `8185`
  - `/FireFlow/api` and `/aff/api` -> `aff-boot` on `1989`

Interpretation:

- Apache is the visible outer edge and the main route-separation layer.
- The route hints are now strong enough to treat the edge as a real architecture seam, not just a front door.

### 2. AFA-Service Family

Observed:

- `ms-metro.service` is active.
- It is a Tomcat-backed Java family with `catalina.base=/data/ms-metro`.
- Visible listeners: `5701`, `8080`, `8082`.
- Visible config clue: `/home/afa/.fa/logback-afa.xml`.
- Apache routes `/afa/external`, `/afa/api/v1`, `/afa/swagger-resources`, and `/afa/v2/api-docs` toward it.

Interpretation:

- `ms-metro` currently looks like the main AFA-side application family and one of the strongest local owners behind the browser-facing edge.
- It is also the visible landing surface for the bounded `storeFireflowCookie` handoff packet, so it matters both architecturally and diagnostically.

### 3. BusinessFlow Family

Observed:

- `ms-bflow.service` is active.
- It is a separate Tomcat-backed Java family with `catalina.base=/data/ms-bflow`.
- Visible listeners: `8081`, `8083`.
- Apache routes `/BusinessFlow` toward it.
- The current session-origin chain repeatedly touches BusinessFlow-side health and session markers before crossing into the AFF and AFA-facing seam.

Interpretation:

- `ms-bflow` is not just another Java process near AFA. It is a separate runtime family with its own container base, listener set, and edge-facing route family.
- In the current proof it acts as a strong upstream participant in the FireFlow/AFF session story rather than as a generic sidecar.

### 4. AlgoSec Microservice Wrapper Family

Observed:

- `algosec-ms.service` is active.
- It is a standalone jar-backed Java service rather than a Tomcat container.
- Visible listener: `8185`.
- Main jar clue: `/usr/share/fa/mslib/ms-configuration.jar`.
- Apache routes a large `swagger` and API-facing surface toward it.
- Additional Apache config families also point many `ms-*` routes at nearby local ports owned under the `algosec-ms` naming surface.

Interpretation:

- `algosec-ms` currently reads as a distinct configuration or service-wrapper family, not part of the `ms-metro` or `ms-bflow` Tomcat bases.
- It likely acts as a broad local API and microservice exposure layer, but this review stops short of claiming full ownership for every `ms-*` route family.

### 5. AFF And FireFlow Bridge Family

Observed:

- `aff-boot.service` is active.
- It is a standalone jar-backed Java family on local port `1989`.
- Apache `aff.conf` routes `/FireFlow/api` and `/aff/api` toward it.
- Fronted `/FireFlow/api/session` and direct `http://localhost:1989/aff/api/external/session` probes still match on `HTTP 200` and `INVALID_SESSION_KEY`.
- Retained FireFlow/UserSession markers and reused FA-session pairs remain visible behind this seam.

Interpretation:

- `aff-boot` is the bounded local owner for the AFF or FireFlow API seam in the current proof.
- The session path is no longer an architecture blind spot. We now have a bounded bridge from Apache to `aff-boot`, then into UserSession-style validation and reused FA-session evidence.

### 6. Shared Messaging And Data Substrates

Observed:

- `activemq.service` is active on `61616`, with visible ActiveMQ home/base/config/data command-line hints.
- `elasticsearch.service` is active on `9200` and `9300`.
- `logstash.service` is active on `9600`.

Interpretation:

- These services look like shared substrates around the application families, especially on the messaging and search side.
- The current proof supports calling them important runtime neighbors, but not yet naming exact dependency order between them and the AFA, BusinessFlow, or AFF families.

### 7. Identity Surface

Observed:

- `keycloak.service` is visible but failed.
- No listener or main runtime command was linked in this pass.
- `/keycloak/` remains a known route-facing seam from earlier bounded route work, but the current architecture review keeps it as a visible identity problem surface rather than a fully mapped family.

Interpretation:

- Identity remains architecturally relevant and operationally concerning.
- The current proof is strong enough to treat Keycloak as a real failed seam, but not yet strong enough to describe its full local runtime boundary.

## Cross-Family Bridges Visible Right Now

### Edge To Local Owners

Observed handoffs:

- Apache -> `ms-bflow` for `/BusinessFlow`
- Apache -> `ms-metro` for `/afa/external` and `/afa/api/v1`
- Apache -> `algosec-ms` for `/algosec/swagger/...`
- Apache -> `aff-boot` for `/FireFlow/api` and `/aff/api`

This is the clearest currently observed architecture spine: one edge layer splitting traffic into several named local owners.

### FireFlow And AFF Session Chain

Observed bounded chain:

- Apache `/FireFlow/api/session`
- `aff-boot` on `1989`
- FireFlow `UserSession` bridge markers
- reused FA-session pairs
- bootstrap anchor `bcbefc00d0`
- `storeFireflowCookie`
- `/afa/external//bridge/storeFireflowCookie`
- later `/afa/external//session/extend`
- route owner `ms-metro` on `8080`

Interpretation:

- The current runtime is not just a set of isolated services. It contains a visible cross-family session bridge from the FireFlow/AFF side into the AFA-side bridge surface.
- That bridge is still bounded and shallow, but it is now real enough to support operator-facing architecture language.

## Current Architecture Readout In Plain Language

The observed lab runtime currently looks like:

- one Apache edge layer
- one AFA-side Tomcat family (`ms-metro`)
- one BusinessFlow-side Tomcat family (`ms-bflow`)
- one separate AlgoSec microservice wrapper family (`algosec-ms`)
- one separate AFF or FireFlow bridge family (`aff-boot`)
- shared messaging and search substrates (`activemq`, `elasticsearch`, `logstash`)
- one identity seam that is currently failed (`keycloak`)

That is a useful bounded architecture picture. It is not a complete product diagram, but it is much stronger than “many Java services are running.”

## Observed Fact Vs Inference

Observed facts:

- local ports, service states, command-line JVM hints, `catalina.base` values, jar paths, route hints, retained session markers, and failed Keycloak state

Inferences kept bounded:

- `ms-metro` is the strongest currently observed AFA-side application family
- `ms-bflow` is a distinct BusinessFlow family rather than just another Java process in the same container surface
- `algosec-ms` acts like a separate wrapper or API exposure family
- `activemq`, `elasticsearch`, and `logstash` are shared substrates around the visible service families

Not claimed here:

- full dependency order
- full login flow reconstruction
- exact ownership for every `ms-*` route
- distributed or multi-node topology
- complete identity topology
- production-grade architecture quality judgment

## Future Questions

- Which shared substrates are true choke points versus simply adjacent infrastructure?
- How much of the broad `algosec-ms` route surface is one real family versus many nearby microservice owners?
- What is the cleanest bounded explanation for the currently failed Keycloak identity seam?
- Which browser-facing routes remain only shallowly owned and still need a stronger route-to-service proof?

## Why This Review Matters

This review gives the successor a stable architecture baseline built from observed runtime seams. That reduces future support and diagnostic ambiguity because the next analyses can now start from named runtime families and known bridges rather than re-discovering the same owners on every pass.
