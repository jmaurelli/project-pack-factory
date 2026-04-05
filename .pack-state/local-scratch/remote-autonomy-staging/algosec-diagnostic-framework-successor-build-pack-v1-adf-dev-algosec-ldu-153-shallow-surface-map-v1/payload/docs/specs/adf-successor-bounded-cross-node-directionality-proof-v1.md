# ADF Successor Bounded Cross-Node Directionality Proof v1

## Purpose

Record one explicit post-frontier widening step for the current
`standalone + remote agent` architecture without inflating a few retained
cross-node clues into a complete east-west dependency story.

This proof only answers a narrower question:

- can the successor now say anything honest about how provider-facing and
  adjacent coordination work is divided across the CM node `10.167.2.150`
  and the remote-agent node `10.167.2.153`?

## Evidence Base

The bounded readout is grounded in the fresh imported node-local bundles:

- `eval/history/import-external-runtime-evidence-20260403t183026z/import-report.json`
- `eval/history/import-external-runtime-evidence-20260403t183106z/import-report.json`

with the corresponding imported maps at:

- `eval/history/import-external-runtime-evidence-20260403t183026z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`
- `eval/history/import-external-runtime-evidence-20260403t183106z/external-runtime-evidence/artifacts/artifacts/dist/candidates/adf-shallow-surface-map-first-pass/shallow-surface-map.json`

## Strongest Retained Signals

### 1. One explicit CM-to-RA ingress clue is now visible

The remote-agent import retains one real non-loopback established connection:

- local `10.167.2.153:443`
- owner `httpd`
- remote peer `10.167.2.150:52212`

That is the cleanest direct cross-node clue in the current proof set.

### 2. The CM import does not retain a reciprocal peer clue in the same bounded window

The fresh CM import does not retain matching `httpd` peer targets to
`10.167.2.153`, and it does not retain provider-family or management-family
peer-IP clues in the same bounded capture.

That matters because the current readout should stay asymmetric where the
evidence is asymmetric.

### 3. RA-side provider and management families retain repeated refresh or broadcast-consumer markers

The remote-agent import now retains repeated journal-side coordination terms for:

- `ms-devicemanager`
- `ms-devicedriver-aws`
- `ms-devicedriver-azure`

The strongest repeated markers include:

- `LegacyContextRefresher`
- `ContextRefresher`
- `ConfigurationChangeListener`
- `ActiveMQService`
- `DefaultMessageListenerContainer`

Those lines are consistent with the remote-agent side behaving like a
configuration-refresh or broadcast-consumer surface, not just a passive local
package placement.

### 4. The CM-side provider journals still do not close full directionality

The fresh CM import still retains local runtime-failure evidence for the AWS
and Azure driver families, but it does not retain comparable peer-IP or
broadcast-consumer markers in the same bounded readout.

That means the CM side is still stronger as the observed cross-node ingress
origin, not as a fully proven provider-driver orchestrator.

## Bounded Readout

The current honest directionality readout is:

- `CM-led` at the observed cross-node ingress edge
  because the remote-agent import now shows the CM connecting into
  `10.167.2.153:443`, owned by RA `httpd`
- `RA-leaning` on local refresh or consumer behavior
  because the remote-agent provider and management journals now retain the
  strongest `ConfigurationChangeListener` and `ActiveMQService` broadcast or
  refresh markers
- `shared` for local provider-driver trouble
  because both nodes still retain the same bounded AWS and Azure local
  degradation pattern
- `unresolved` for exact provider orchestration direction
  because the current proof still does not show which node is the durable
  producer, coordinator, or authoritative owner for provider-facing work

## What This Proof Does Not Claim

This proof does not claim:

- cloud-side provider success
- credential correctness
- full east-west dependency order
- exact ActiveMQ producer versus consumer ownership across the pair
- that all provider-facing work is owned by only one node

## Why This Matters

The successor now says more than "both nodes have AWS and Azure families."

It can now separate:

- one directly observed CM-to-RA ingress clue
- RA-side refresh or broadcast-consumer hints
- shared local driver degradation
- still-unresolved deeper orchestration direction

That is enough to close this widening step honestly without inventing a
cleaner cross-node story than the imported proof supports.

## Next Options

The next widening move should now be chosen explicitly from:

- `standalone + LDU`
- `high availability`
- `disaster recovery with a remote agent`

Deeper directionality work on the current CM-plus-remote-agent pair is still
possible later, but it should be a consciously selected follow-on rather than
the default next seam.
