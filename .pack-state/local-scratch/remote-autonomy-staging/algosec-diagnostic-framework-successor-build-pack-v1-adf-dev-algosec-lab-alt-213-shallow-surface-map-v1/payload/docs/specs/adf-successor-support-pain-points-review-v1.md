# ADF Successor Support Pain Points Review v1

## Purpose

Record the most likely support-engineer pain points from the current successor evidence. This is not a support playbook. It is a bounded explanation of why the observed runtime seams would feel confusing, expensive, or easy to misread during triage.

## Evidence Base

- Architecture review: `docs/specs/adf-successor-asms-runtime-architecture-review-v1.md`
- Failure-seam review: `docs/specs/adf-successor-asms-failure-seam-review-v1.md`
- Latest imported proof: `eval/history/import-external-runtime-evidence-20260403t110310z/`
- Latest successor summary: `eval/history/import-external-runtime-evidence-20260403t110310z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-summary.md`

## Bounded Support Pain Points

### 1. One Browser-Facing Symptom Can Cross Several Owners

Why it hurts:

- A support engineer can start from one fronted URL and still need to reason across Apache, `aff-boot`, FireFlow `UserSession`, the AFF bridge surface, and `ms-metro`.
- That means one “session is broken” symptom can actually belong to several different local owners.

Observed basis:

- Apache fronts `/FireFlow/api/session`.
- That path is bounded to `aff-boot` on `1989`.
- The current proof then continues through FireFlow `UserSession` markers, reused FA-session evidence, and `/afa/external//bridge/storeFireflowCookie`.
- The AFA-side landing surface is route-hinted to `ms-metro` on `8080`.

Support effect:

- incidents can look like one API issue while actually spanning several families
- ownership handoff is easy to misstate without the packet chain

### 2. Route Ownership Is Clear For Some Paths And Still Broad Or Concentrated For Others

Why it hurts:

- Some routes are now cleanly bounded, but the overall edge still concentrates a lot of visible ownership under `algosec-ms`.
- That creates a trap where support can over-assign symptoms to the broad wrapper family or under-assign them to the deeper owner actually failing behind it.

Observed basis:

- `/BusinessFlow` maps cleanly to `ms-bflow`.
- `/afa/external` and `/afa/api/v1` map cleanly to `ms-metro`.
- `/FireFlow/api` and `/aff/api` map cleanly to `aff-boot`.
- But the route-hint surface is still heavily concentrated under `algosec-ms`.

Support effect:

- route triage can become “too broad to be useful”
- engineers can see a browser-facing path and still not know whether they are looking at an edge problem, wrapper-family problem, or deeper owner problem

### 3. Identity Can Fail While Much Of The Runtime Still Looks Alive

Why it hurts:

- Failed identity is one of the classic support-confusion seams: the user symptom is often “other things stopped working,” not “identity is down.”
- The current proof shows many active services and bounded route families around a failed `keycloak`.

Observed basis:

- `keycloak.service` is failed.
- Apache, `ms-metro`, `ms-bflow`, `algosec-ms`, `aff-boot`, `activemq`, `elasticsearch`, and `logstash` are still visible as active or alive runtime surfaces.

Support effect:

- engineers can spend time on downstream feature symptoms before checking identity
- the runtime can look broadly up while auth-related symptoms still dominate the real incident

### 4. Shared Substrates Blur Feature-Local Problems Versus System-Wide Problems

Why it hurts:

- Shared messaging and search substrates make it harder to tell whether the incident belongs to one feature family or to the wider platform.
- When those substrates are healthy-looking but adjacent to many families, support still has to decide whether they are a root cause, amplifier, or red herring.

Observed basis:

- `activemq` is present as messaging adjacency on `61616`.
- `elasticsearch` and `logstash` are clearly present as separate Java-heavy substrate services.
- The current review keeps them as shared substrates or adjacencies, not feature-local owners.

Support effect:

- root cause can be over-broadened too early
- or shared substrate issues can be missed because the first symptom appears inside one feature family

### 5. The Runtime Has Both Product-Named Families And Generic Service Surfaces

Why it hurts:

- Some families are easy to speak about in product language like `BusinessFlow` or `FireFlow`.
- Others are visible as `ms-*` or jar-backed service names, which are more implementation-shaped than operator-shaped.
- That gap makes support explanations harder to keep consistent.

Observed basis:

- Product-facing names exist at the edge: `/BusinessFlow`, `/FireFlow/api`, `/afa/external`.
- Runtime-facing owners are `ms-metro`, `ms-bflow`, `algosec-ms`, and `aff-boot`.

Support effect:

- one engineer may explain the incident in product language
- another may explain it in runtime-owner language
- both can be correct but still confuse the handoff

### 6. Failed Operational Seams May Matter Most During Recovery, Not First Triage

Why it hurts:

- `ms-backuprestore` is failed, but it is not the first thing a support engineer will usually inspect from a route symptom.
- That makes it easy to underweight until recovery or remediation depends on it.

Observed basis:

- `ms-backuprestore.service` is failed.
- The current proof does not show it as a major browser-facing edge owner.

Support effect:

- operational recovery can become harder than initial triage suggests
- “everything except restore” stories can hide a meaningful second-order problem

## Plain-Language Readout

The current runtime would probably feel hard from support for three main reasons:

- the same user-visible symptom can cross several owners
- route ownership is partly clean and partly still broad or concentrated
- some of the most important seams are not the noisiest ones at first glance, especially identity and operational recovery

## What This Review Does Not Claim

- It does not claim actual ticket history.
- It does not claim customer-frequency ranking.
- It does not replace a support playbook.
- It does not say these are the only hard support seams.

## Best Next Follow-On

The strongest next follow-on is now `expand_config_and_log_surface_discovery`, because the pain points are clear enough that the next useful gain is not another high-level review. It is better path and log discovery so support-facing follow-ups can say where to inspect next for each bounded family.
