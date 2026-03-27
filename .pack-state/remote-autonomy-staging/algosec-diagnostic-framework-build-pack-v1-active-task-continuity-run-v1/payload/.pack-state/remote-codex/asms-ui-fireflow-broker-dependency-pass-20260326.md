# ASMS UI FireFlow Broker Dependency Pass 2026-03-26

## PackFactory-Staged Context

This pass was anchored to the PackFactory remote staging request:

- local request:
  `.pack-state/remote-autonomy-requests/algosec-lab/algosec-diagnostic-framework-build-pack-v1/algosec-diagnostic-framework-build-pack-v1-guided-investigation-run-v1/remote-run-request.json`
- remote pack dir:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1`
- remote manifest:
  `~/packfactory-source__algosec-lab__autonomous-build-packs/algosec-diagnostic-framework-build-pack-v1/.packfactory-remote/target-manifest.json`

## What Became Clear

- `aff-boot.service` on `1989` bundles real JMS and ActiveMQ libraries inside
  `aff-boot.jar`, not only generic framework code.
- The packaged FireFlow application content also includes app-level broker and
  queue classes, including ActiveMQ listener, producer, configuration, and
  broker model code.
- The live `aff-boot` Java PID currently holds established local connections to
  ActiveMQ on `127.0.0.1:61616`.
- The same live PID also holds PostgreSQL connections, which keeps the current
  FireFlow seam grounded in both DB and broker-backed runtime behavior.

## Current Working Rule

For the backward dependency map behind `ASMS UI is down`:

- BusinessFlow still stays earlier than FireFlow in the customer-visible path.
- FireFlow still stays later than the first named BusinessFlow checkpoint.
- Within the FireFlow seam, Apache proxying, `aff-boot`, and database-backed
  runtime behavior are still closer first checks than broker theory.
- ActiveMQ is no longer only a rumor or edge-case platform dependency here.
  It is now a concrete later supporting dependency for the FireFlow seam.

## What This Does Not Prove Yet

- This pass does not prove that ActiveMQ is part of the first login handoff or
  the first usable ASMS shell.
- This pass does not prove that broker health is the first thing a support
  engineer should check during `ASMS UI is down`.

## Best Next Seam

Correlate one reproduced ASMS login-handoff minute against:

- FireFlow access and runtime signals
- `aff-boot` activity
- broker-side connection or destination activity

That next pass should decide whether the FireFlow broker tie belongs inside the
later ASMS auth handoff or only in later FireFlow workflow branches.
