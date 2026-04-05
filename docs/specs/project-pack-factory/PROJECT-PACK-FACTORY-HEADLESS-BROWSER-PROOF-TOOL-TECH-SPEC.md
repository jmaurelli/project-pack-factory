# Project Pack Factory Headless Browser Proof Tool Tech Spec

## Purpose

Give PackFactory one shared headless-browser proof tool under `tools/` so
agents can validate one bounded class of real browser behavior on an
operator-facing preview surface without turning that capability into a
build-pack or a broad default test suite.

## Why This Matters

PackFactory can already prove:

- generated HTML shape
- served assets
- script syntax
- static route and content presence

But some important operator-facing behaviors only become real inside a browser.

Example from ADF:

- the page serves the correct step links
- the page serves the helper script
- the script is syntactically valid
- but the final question is still browser-native:
  does clicking `Step 3` actually open the targeted collapsed step card?

That is the gap this tool is meant to close.

## Decision

This capability should live at the factory root as a shared PackFactory tool.

It should not be modeled as:

- a new build-pack
- a build-pack-local one-off helper
- a mandatory broad UI test framework

## Scope

V1 is intentionally narrow.

V1 should provide one bounded browser-proof path for:

- PackFactory-served local preview pages for the ADF Starlight proving-ground
  case

V1 should not yet generalize to:

- multiple proof recipes
- dashboard interaction proof
- deployment-surface proof
- arbitrary preview-site matrices

## Primary Use Cases

The V1 proof case is:

1. `adf_field_manual_hash_target_opens`
   Proof target:
   - the ADF local preview page for `ASMS UI is down`
   Required checks:
   - the top overview link for a chosen step is clickable
   - navigation lands on the matching `#manual-...` target
   - the matching collapsed `<details>` step card is open after navigation
   - the collapsed summary shows the expected command-count cue

## Non-Goals

V1 should not:

- become the default validation path for every build-pack
- replace existing PackFactory validators or workflow proofs
- introduce a large frontend regression suite
- require broad new test matrices
- treat browser screenshots as canonical truth by default

This stays aligned with `docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-TESTING-POLICY.md`.

## Tooling Model

The factory should provide one shared tool entrypoint under `tools/`.

Working name:

- `tools/run_browser_proof.py`

V1 may use Playwright as the backing runtime.

Why Playwright is the default recommendation:

- strong headless-browser support
- reliable selector and navigation APIs
- direct assertions on DOM state like `details.open`
- bounded screenshots or console capture when needed

The spec does not require Playwright forever, but it does require one stable
PackFactory-facing wrapper instead of exposing raw browser-framework usage as
the operator interface.

## Wrapper Boundary

The wrapper must stay bounded and schema-driven.

V1 should expose one schema-versioned request and response contract for the one
named proof recipe above.

The wrapper must not act as:

- a raw Playwright passthrough
- a generic arbitrary script runner
- an arbitrary `eval` surface
- a free-form browser automation shell

Adding a new built-in proof recipe, broader assertion matrix, or larger target
set is follow-on work and requires separate operator approval.

## Operator Contract

The PackFactory-facing surface should stay task-oriented.

V1 should accept one bounded proof request for
`adf_field_manual_hash_target_opens`.

The operator or agent should not need to handwrite browser scripts for the
routine proof case.

This wrapper is an opt-in CLI proof surface only.

V1 must not be added to:

- `tools/validate_factory.py`
- pack-local validator commands
- benchmark or smoke commands
- deployment pipelines
- CI defaults
- generic `run the tests` or `continue testing` flows

without a separate operator-approved spec.

## Runtime And Storage Boundary

Browser binaries, caches, and other heavy runtime state should be treated as
factory-managed tool runtime, not as build-pack content.

V1 should keep that state outside build-pack roots and outside canonical
registry or deployment truth surfaces.

V1 should use explicit factory-owned locations:

- browser runtime root:
  `.pack-state/browser-proof-runtime/`
- proof output root:
  `.pack-state/browser-proofs/`

V1 should fail closed rather than falling back to:

- user-home browser profiles
- global Playwright caches
- ad hoc temp directories outside the factory-owned runtime root

The tool should make it obvious which artifacts are:

- transient browser runtime state
- bounded proof output
- canonical validation evidence

## Control-Plane Boundary

`tools/run_browser_proof.py` is read-only against canonical PackFactory state.

It must not write to:

- `registry/`
- `deployments/`
- `status/`
- `eval/latest/`
- canonical build-pack readiness or deployment records

Its own proof report is supplementary evidence only unless a separate workflow
explicitly imports or records it elsewhere.

## Target Provenance Rule

V1 target URLs must come from a PackFactory-managed local preview surface.

For the initial ADF proving-ground case, that means a local PackFactory-served
preview URL for the generated ADF Starlight output.

V1 should not treat these as valid proof targets:

- arbitrary external URLs
- stale manual localhost URLs with no PackFactory provenance
- live deployment URLs

Deployment-surface browser proof, if needed later, must be specified through a
separate workflow that cross-checks canonical deployment pointers.

## Proof Output

The wrapper should produce a bounded machine-readable result.

V1 proof output should include:

- `schema_version`
- `proof_kind`
- `target_kind`
- target URL
- pass/fail status
- PackFactory provenance for the served surface
- checked selector or command-count assertions for the bounded proof case
- bounded console summary when requested
- browser runtime version
- recorded timestamp

When a served local preview is the target, the proof output should also record:

- the served-from artifact root or published root
- enough local provenance to distinguish a fresh PackFactory-served preview from
  an unrelated local page

The goal is auditable proof, not a full browser trace archive.

Screenshots, if requested, are debug artifacts only.

V1 must not treat screenshots as:

- assertion inputs
- golden baselines
- canonical validation evidence by default

## Validation Philosophy

This tool is an on-demand proof surface first.

Default usage should be:

- targeted local preview proof when browser behavior matters
- targeted operator-review support for the one named proving-ground case
- bounded evidence for a specific interaction claim that static inspection
  cannot settle

It should not become an automatic required gate for unrelated PackFactory work
without a later explicit decision.

## ADF Proving Ground

The first motivating proof case is the ADF field-manual shell:

- click a top step link
- navigate to `#manual-...`
- confirm the matching collapsed `<details>` step card is open
- confirm the collapsed summary shows the expected command-count cue

This is the whole V1 proving-ground case, not just one example in a broader
initial matrix.

## Follow-On Possibilities

Later follow-on work may expand the tool to:

- dashboard interaction proof
- additional bounded preview-site proof recipes
- deployment-surface browser proof with canonical deployment cross-checks

Those are explicitly out of scope for this V1 spec.

## Escalation Conditions

Stop and escalate if:

- the design starts to look like a broad always-on UI testing framework
- the wrapper would weaken the existing testing-policy boundary
- browser runtime state cannot be kept outside build-pack truth surfaces
- the tool would require agents to bypass PackFactory wrappers and run raw
  browser framework commands as the normal path
- the implementation widens V1 beyond the single named ADF proof recipe

## Success Signal

PackFactory has one root-level browser-proof wrapper plus one bounded ADF proof
recipe that can confirm real operator-facing browser behavior where static HTML
or plain `curl` checks are not enough.
