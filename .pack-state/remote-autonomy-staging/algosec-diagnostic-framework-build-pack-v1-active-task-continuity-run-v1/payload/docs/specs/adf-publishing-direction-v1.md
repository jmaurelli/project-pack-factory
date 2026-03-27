# ADF Publishing Direction v1

ADF keeps machine-readable JSON as the source of truth and treats every human
view as a render of the same runtime-derived content.

## Current Direction

- Collect runtime evidence on the controlled AlgoSec lab appliance.
- Generate canonical ADF artifacts from that evidence.
- Publish human-facing diagnostic playbooks through renderer layers instead of
  hand-authoring support pages.

## Renderer Strategy

- `support-baseline.html`
  The current fast iteration surface for operator review and playbook tuning.

- `Astro Starlight`
  The durable publishing surface for support-friendly navigation, search,
  built-in documentation structure, and a more maintainable community-shaped
  documentation shell.

- `Confluence export`
  A later distribution target for teams that already live in Confluence and
  need a known documentation home.

## Environment Split

- `Rocky 8 AlgoSec lab appliance`
  Best place to test runtime discovery, generate target-backed playbook
  content, and prove the renderer against real appliance evidence.

- `Ubuntu publishing server`
  Likely long-term home for the published docs site after the content and
  renderer pattern are stable.

This means the long-term architecture can decouple collection from publishing:

- appliance-side collection and baseline generation near the real target
- site build and hosting on a separate server later

## Near-Term Goal

Prototype `Astro Starlight` on the lab appliance first, using the generated
ADF baseline as the source input, then keep the publishing layer portable so
the same generated site can move to Ubuntu later without changing the
collection logic.
