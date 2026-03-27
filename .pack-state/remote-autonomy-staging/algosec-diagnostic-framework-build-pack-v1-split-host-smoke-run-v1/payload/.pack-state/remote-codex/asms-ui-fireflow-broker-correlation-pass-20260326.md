# ASMS UI FireFlow Broker Correlation Pass 2026-03-26

## PackFactory-Staged Context

This pass was anchored to the PackFactory remote staging request:

- local request:
  `.pack-state/remote-autonomy-requests/algosec-lab/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-guided-investigation-run-v1/remote-run-request.json`
- remote pack dir:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1`
- remote manifest:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1/.packfactory-remote/target-manifest.json`

## What Became Clear

- The reproduced FireFlow-auth minute was still dominated by auth, session, and
  AFA-facing REST activity.
- FireFlow logs and access logs in that minute showed auth/session handling plus
  REST calls such as allowed devices, session lookup, and brand-config work.
- Broker-side minute logs were empty for that same window.
- The live `aff-boot` runtime still holds established connections to
  `127.0.0.1:61616`, and the packaged code still includes concrete ActiveMQ and
  JMS classes.

## Current Working Rule

For the current `ASMS UI is down` trajectory:

- ActiveMQ is now proven as a concrete supporting dependency behind the
  FireFlow seam.
- It still does not belong inside the immediate ASMS login or first home-shell
  handoff on current evidence.
- The login-handoff minute stays centered on auth, session, and REST work.
- Broker theory should stay behind the closer FireFlow checks unless a failing
  reproduced minute shows JMS or queue activity.

## Best Next Seam

If FireFlow grows into a separate later workflow branch, the next useful broker
question is no longer the login handoff.

The better future seam is:

- a FireFlow job or queue-driven workflow minute
- correlated across `aff-boot`, broker activity, and any later queue-backed
  module behavior
