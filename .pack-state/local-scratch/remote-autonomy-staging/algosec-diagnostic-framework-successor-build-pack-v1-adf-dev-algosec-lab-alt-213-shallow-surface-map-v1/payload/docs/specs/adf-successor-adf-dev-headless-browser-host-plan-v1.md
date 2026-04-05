# ADF Successor adf-dev Headless Browser Host Plan v1

## Purpose

Define the concrete review-only plan for making `adf-dev` capable of bounded
headless browser review.

This is a host-readiness and review-surface plan. It is not an approval to
install packages yet, and it does not replace the existing PackFactory-local
browser-proof wrapper.

## Current Host State

Observed on `2026-04-04`:

- host: `adf-dev`
- host IP: `10.167.2.151`
- OS: Ubuntu `24.04.4 LTS`
- package manager: `apt`
- privilege path: `sudo` available to user `adf`
- Node: `v22.22.1`
- npm: `11.12.1`
- Chromium: not currently installed
- Playwright: not currently installed
- live review page already serving on-host at
  `http://127.0.0.1:18082/playbooks/asms-ui-is-down/`

That means `adf-dev` is already a working review host, but not yet a browser
automation host.

## Design Rule

Keep the boundaries explicit:

- host package installation is a host-management action
- browser proof remains bounded and explicit
- do not install global npm browser tooling when a workspace-local install will
  do
- do not weaken proofs into screenshot-only or curl-only substitutes

## Target End State

`adf-dev` should be able to do all of the following:

- launch a Chromium-capable Playwright runtime on-host
- open the locally served Starlight review page at `127.0.0.1:18082`
- prove that the successor review shell loads and basic page interactions work

## Phase 1: Host Shared-Library Provisioning

Use the same Ubuntu 24.04 package-family mapping already recorded in the
PackFactory host-readiness spec.

Current confirmed `apt` candidates:

- `libatk1.0-0t64`
- `libatk-bridge2.0-0t64`
- `libatspi2.0-0t64`
- `libxcomposite1`
- `libxdamage1`
- `libxfixes3`
- `libxrandr2`
- `libgbm1`
- `libasound2t64`

Review-only operator command shape:

```bash
sudo apt-get update
sudo apt-get install -y \
  libatk1.0-0t64 \
  libatk-bridge2.0-0t64 \
  libatspi2.0-0t64 \
  libxcomposite1 \
  libxdamage1 \
  libxfixes3 \
  libxrandr2 \
  libgbm1 \
  libasound2t64
```

This command shape is a concrete proposal for review. It is not yet recorded
as canonical execution truth.

## Phase 2: Chromium-Capable Runtime

After the host libraries are installed, ensure a Chromium-capable runtime is
present on-host.

The practical target is not a system-global browser workflow. The target is a
bounded Playwright Chromium runtime that can launch successfully.

Recommended review posture:

- prefer Playwright-managed Chromium in a bounded workspace
- do not depend on a manually curated desktop-browser setup

## Phase 3: Workspace-Local Playwright Install

Install Playwright in a bounded review workspace on `adf-dev`, not globally.

Recommended workspace rule:

- keep the runtime next to the staged successor or PackFactory review workspace
- keep the npm dependency local to that workspace
- avoid `npm install -g`

Review-only command shape:

```bash
mkdir -p ~/packfactory-browser-review
cd ~/packfactory-browser-review
npm init -y
npm install playwright@1.58.2
npx playwright install chromium
```

The version is aligned to the current PackFactory-local wrapper pin.

## Phase 4: On-Host Readiness Check

Before blaming page behavior, confirm the host can launch Chromium.

Minimum readiness checks:

- `node -e "require('playwright')"` succeeds
- `npx playwright install chromium` has completed
- a tiny script can launch Chromium headlessly and load a page

## Phase 5: First On-Host Review Proof

The first bounded proof on `adf-dev` should stay small:

- open `http://127.0.0.1:18082/`
- open the first playbook route
- confirm page title
- confirm one expected heading
- confirm one expected route or anchor exists

That is enough to prove the remote review-host browser path without dragging in
full workflow automation on day one.

## Suggested First Proof Target

Once the successor shell exists, the preferred first proof target should be:

- overview page loads
- `Service State` playbook route loads

Before the successor shell exists, the current live older-ADF route remains a
usable host-readiness target:

- `http://127.0.0.1:18082/playbooks/asms-ui-is-down/`

## Follow-Up After Host Provisioning

If host provisioning succeeds, the next follow-up should be separate and
bounded:

- decide whether successor should borrow the PackFactory root browser-proof
  wrapper directly
- or add one successor-local preview-proof helper that stays compatible with
  the PackFactory root proof contract

That follow-up should happen only after the successor shell exists.

## Why This Matters

Local PackFactory already has a passing browser-proof path. Extending that
readiness to `adf-dev` matters because it gives the successor line a real
remote review loop:

- publish on `adf-dev`
- open on `adf-dev`
- review language and interaction on the same host

That reduces ambiguity before we spend time building a successor shell that
looks fine in theory but has not been exercised in its real review home.
