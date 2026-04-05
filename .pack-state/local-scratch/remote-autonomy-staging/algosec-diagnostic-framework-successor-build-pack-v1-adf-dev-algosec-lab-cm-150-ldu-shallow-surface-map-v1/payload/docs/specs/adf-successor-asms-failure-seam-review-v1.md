# ADF Successor ASMS Failure Seam Review v1

## Purpose

Rank the most likely ASMS failure seams and choke points from the current bounded runtime evidence on `10.167.2.150`. This is not a production reliability claim. It is a lab-grounded support and diagnostic ranking meant to focus the next investigations.

## Evidence Base

- Architecture readout: `docs/specs/adf-successor-asms-runtime-architecture-review-v1.md`
- Latest canonical imported proof bundle: `eval/history/import-external-runtime-evidence-20260403t110310z/`
- Machine-readable map: `eval/history/import-external-runtime-evidence-20260403t110310z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- Operator summary: `eval/history/import-external-runtime-evidence-20260403t110310z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`

## Ranking Method

This ranking prefers seams that are:

- already failed in the observed runtime
- concentrated behind one visible owner or bridge
- likely to confuse support because one browser-facing path crosses multiple local families
- shared by more than one feature family
- important enough to hurt diagnosis even if they are not the first hard outage

The ranking stays bounded to observed seams. It does not assume full product dependency order.

## Ranked Failure Seams

### 1. Identity Failure Seam: `keycloak`

Why it ranks first:

- `keycloak.service` is already failed in the observed runtime.
- Identity sits close to the support boundary because authentication and authorization failures can make many other symptoms look secondary or misleading.
- The current proof treats Keycloak as a real visible identity seam, not just a theoretical dependency.

Observed signals:

- `keycloak.service` is failed.
- No active listener or current runtime command line was linked in this pass.
- The broader runtime still exposes product-facing routes and service families around it, which raises the chance that some operator-visible symptoms could present as downstream breakage while the real root is identity.

Support visibility:

- high

Architecture risk:

- high

Confidence:

- high that this is a real failure seam
- medium on exact blast radius, because the current proof does not fully map identity dependencies

### 2. Cross-Family Session Bridge Seam: `Apache -> aff-boot -> FireFlow UserSession -> AFF bridge -> ms-metro`

Why it ranks second:

- The current proof shows a real multi-hop session chain rather than a single-owner request path.
- Multi-hop session bridges are support-expensive because symptoms can appear at the browser edge, the AFF boundary, the FireFlow bridge, or the AFA-side extension path.
- This seam already required several bounded packets to explain cleanly, which is itself a support signal.

Observed signals:

- Apache `/FireFlow/api/session` and direct `aff-boot` session probes match.
- FireFlow `UserSession` markers are visible.
- Reused FA-session pairs are visible.
- Bootstrap anchor `bcbefc00d0` crosses `/afa/external//bridge/storeFireflowCookie`.
- The same token family later appears on `/afa/external//session/extend`.
- The AFA-side landing surface is route-hinted to `ms-metro` on `8080`.

Support visibility:

- high

Architecture risk:

- high

Confidence:

- high that this is a real choke-point family
- medium on which hop is most failure-prone, because the current proof is still bounded and read-only

### 3. Edge Concentration Seam: Apache Route Splitter And Heavy `algosec-ms` Route Ownership

Why it ranks third:

- Apache is the visible edge for the runtime.
- The route-hint surface is highly concentrated, and `algosec-ms` currently owns by far the largest visible route count in the shallow map.
- A concentrated edge-to-owner split can turn one local family issue into many apparently unrelated API or UI symptoms.

Observed signals:

- `httpd.service` fronts `80` and `443`.
- Visible route-owner counts are heavily concentrated, with `algosec-ms` carrying the largest observed share, followed by `ms-metro`, `aff-boot`, and `ms-bflow`.
- `algosec-ms` fronts a broad `swagger` and service-facing surface on `8185`.

Support visibility:

- high

Architecture risk:

- medium to high

Confidence:

- high that route concentration exists
- medium on which `algosec-ms` sub-surface is the most fragile, because the current proof does not yet fully separate every `ms-*` owner behind that wrapper family

### 4. Shared Messaging And Async Coordination Seam: `activemq`

Why it ranks fourth:

- `activemq` is clearly separate from the application families, which makes it easier to see as a shared substrate.
- Shared messaging layers often create cross-feature symptoms when they degrade, especially when the visible application families remain up.
- This seam matters even without current failure because it sits between families rather than inside one feature island.

Observed signals:

- `activemq.service` is active on `61616`.
- ActiveMQ home, base, config, and data hints are visible in the command line.
- The Java-cluster packet keeps `activemq` as messaging adjacency rather than as part of the AFA, BusinessFlow, or AFF families.

Support visibility:

- medium

Architecture risk:

- high

Confidence:

- medium to high

### 5. Search, Logging, And Runtime-Visibility Substrate: `elasticsearch` + `logstash`

Why it ranks fifth:

- These are not the first seams I would blame for a login or route failure, but they can amplify diagnosis difficulty and operational confusion.
- If search or logging substrates degrade while core application families remain partially alive, support can lose the clean trail needed to explain symptoms quickly.

Observed signals:

- `elasticsearch.service` is active on `9200` and `9300`.
- `logstash.service` is active on `9600`.
- Both are clearly present as separate Java-heavy services, not just incidental processes.

Support visibility:

- medium

Architecture risk:

- medium

Confidence:

- medium

### 6. Failed Operational Side Seam: `ms-backuprestore`

Why it still matters:

- It is already failed, even though it is not the main product-facing edge seam.
- Backup or restore failures can matter a lot during recovery, maintenance, or post-incident handling, even if they are not the first symptom support sees.

Observed signals:

- `ms-backuprestore.service` is failed.
- The current proof does not yet expose a listener or stronger route family for it.

Support visibility:

- medium

Architecture risk:

- medium

Confidence:

- medium that it is a real operational failure seam
- low to medium on its live runtime blast radius

## Plain-Language Readout

If I had to brief support or delivery in one paragraph, the biggest current seams are:

- identity is already visibly broken (`keycloak`)
- the FireFlow/AFF-to-AFA session bridge is real and crosses several owners
- Apache plus the broad `algosec-ms` route surface creates route concentration risk
- shared messaging and search substrates can spread symptoms or obscure root cause even when the main feature families are still up

## What This Review Does Not Claim

- It does not claim production-grade reliability ranking.
- It does not claim exact dependency order between all families.
- It does not say every failed unit is equally important.
- It does not say the highest route count is automatically the highest outage source.
- It does not replace deeper per-seam debugging.

## Best Next Follow-On

The strongest next support-facing follow-on is now likely `capture_support_engineer_pain_points`, because we can finally explain not just what is running and what looks risky, but why certain incidents would feel confusing from the support side:

- identity can fail while many services still look alive
- browser-facing routes can mask local ownership
- one session symptom can span Apache, AFF, FireFlow, and AFA-facing surfaces
- shared substrates can blur whether the real problem is feature-local or system-wide
