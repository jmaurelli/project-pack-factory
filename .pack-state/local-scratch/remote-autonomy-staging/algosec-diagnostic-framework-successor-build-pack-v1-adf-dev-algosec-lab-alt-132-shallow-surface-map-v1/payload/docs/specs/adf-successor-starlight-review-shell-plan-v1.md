# ADF Successor Starlight Review Shell Plan v1

## Purpose

Define the first concrete review-only publication shell for the ADF successor
line.

This plan keeps the current successor content review in the design phase. It
does not authorize implementation yet. The goal is to make the next shell
decision concrete enough that we can review language, page shape, and visual
behavior before code moves.

## Current Evidence

The current publication and browser surfaces split cleanly into three layers:

- the older ADF line already has a real Astro/Starlight publisher under
  `build-packs/algosec-diagnostic-framework-build-pack-v1/src/.../starlight_site.py`
- the older ADF line also has multiple prototype review shells under
  `build-packs/algosec-diagnostic-framework-build-pack-v1/dist/prototypes/starlight/`
- the successor line currently has reviewed playbook and cookbook contracts,
  but no successor-local publisher yet

The strongest reusable operator-facing reference is still the lighter
`triage-console` prototype shape, not the darker cockpit-style shells.

The current live host evidence on `adf-dev` also matters:

- `adf-dev` currently serves the older ADF Starlight output at
  `http://10.167.2.151:18082/playbooks/asms-ui-is-down/`
- that proves the remote review-host model already works
- the successor can therefore treat Starlight as a practical review surface,
  not just a design idea

## Design Rule

The successor shell should publish the current reviewed split directly:

- `playbooks` are the first-responder triage surface
- `cookbooks` are the deeper foundation surface

The shell must not flatten those two layers back together.

It must also preserve the current frontline contract in
`adf-successor-triage-playbook-path-model-v1.md`:

- path-first, not symptom-story-first
- title plus `Steps`, `Branch to`, and `Related cookbook foundations`
- no coaching headers such as `Use this path when`

## Review Shell Scope

The first shell should stay intentionally small.

It should publish only:

- one overview page
- the first five reviewed playbook paths
- a small first cookbook set that supports those paths

It should not try to become:

- a full ADF portal
- a generated deep-link maze
- a dashboard with many competing widgets
- a second truth layer independent from successor canonical artifacts

## Proposed Information Architecture

Top-level navigation:

- `Overview`
- `Playbooks`
- `Cookbooks`

Initial playbook routes:

- `/playbooks/service-state/`
- `/playbooks/host-health/`
- `/playbooks/logs/`
- `/playbooks/data-collection-and-processing/`
- `/playbooks/distributed-node-role/`

Initial cookbook routes:

- `/cookbooks/core-service-groups-by-node-role/`
- `/cookbooks/log-entry-points/`
- `/cookbooks/data-flow-foundations/`
- `/cookbooks/distributed-role-foundations/`

Overview route:

- `/`

## Overview Page Role

The overview page should act as the entry map, not as a narrative landing
page.

It should show:

- one short statement about what ADF successor is for
- the five current playbook paths as the main entry cards
- one smaller cookbook section beneath them
- one small note that cookbook pages provide the deeper runtime foundation

It should not open with marketing language, maturity language, or a long
product essay.

## Playbook Page Layout

Each playbook page should use one main reading lane and one narrow sticky rail.

Main lane:

- title
- short one-line path description
- `Steps`
- `Branch to`
- `Related cookbook foundations`

Sticky rail:

- step jump links
- branch jump links
- related cookbook links

The shell should keep commands, expected evidence, and branch directions close
together. The page should feel procedural and calm.

## Cookbook Page Layout

Cookbook pages can carry more explanation, but still need a controlled shape.

Main lane:

- title
- short foundation summary
- sectioned runtime explanation
- node-role or service-group tables where useful
- behavior notes
- explicit proven versus not-proven markers
- related playbook links

Sticky rail:

- section jump links
- related playbook links

The cookbook should feel like a field guide, not like vendor docs.

## Visual Direction

The shell should move toward a light field-manual look:

- light background
- strong text contrast
- teal or slate accent family
- compact spacing
- minimal decoration
- repeated blocks with fixed meaning

Use the older `triage-console` prototype as the closest visual starting
direction for:

- one main lane
- sticky rail
- route-card entry behavior
- restrained accent treatment

Do not inherit these older-shell traits directly into successor:

- symptom-led page framing
- dark default presentation
- coaching prose above every step
- high-ceremony field-manual language from the older proving-ground pages

## Reuse Plan From The Older ADF Line

Reusable first:

- Starlight content collections and route generation patterns
- bounded local serving path
- bounded review-host publication model
- targeted step navigation behavior if it still helps on long playbook pages

Replace or remove first:

- symptom-story page titles and descriptions
- beginner-facing rationale blocks
- dark-theme-first output
- older field-manual wording such as `working rule`, `why this matters`, or
  similar coaching scaffolding

## Review Sequence

The review sequence should stay narrow:

1. stand up a successor shell with static review content only
2. publish `Service State` as the first playbook page
3. publish `Core Service Groups by Node Role` as the first cookbook page
4. review language and visual density on `adf-dev`
5. adjust shell behavior before widening to the other path pages

## Non-Goals

This shell plan does not yet authorize:

- full successor renderer implementation
- browser-proof automation for successor pages
- automatic generation of all playbooks and cookbooks from successor JSON
- broad navigation taxonomies beyond the current five-path first release

## Why This Matters

The shell decision now matters because the successor already has a reviewed
content split, but the engineers still need a concrete review surface before
we can judge whether the language and look actually support live support work.

If the shell is wrong, later content refinement will be noisy.
If the shell is right, later content review will move faster and stay grounded.
