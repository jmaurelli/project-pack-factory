# Project Pack Factory Headless Browser Host Dependency Provisioning Tech Spec

## Purpose

Define the host-level dependency boundary for the root browser-proof wrapper so
PackFactory can distinguish:

- a real wrapper or proof-logic defect
- from a host that cannot launch the Playwright Chromium runtime yet

This spec is adjacent to:

- [PROJECT-PACK-FACTORY-HEADLESS-BROWSER-PROOF-TOOL-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-HEADLESS-BROWSER-PROOF-TOOL-TECH-SPEC.md)

## Why This Matters

The wrapper now works through the bounded PackFactory-controlled layers:

- it validates request and report schemas
- it provisions its own Node and Playwright runtime under `.pack-state/`
- it emits a schema-valid browser-proof report
- it fails closed when Chromium cannot launch

That distinction mattered because the original blocker was host readiness, not
PackFactory logic and not ADF page behavior.

That blocker has now been cleared on this host. The browser-proof path is no
longer stopping at launch failure; it now reaches live page navigation and
page-level assertions for the bounded ADF proving-ground recipe.

## Current Evidence

PackFactory now has both historical blocker evidence and current passing
evidence for this boundary.

Historical blocker evidence:

1. the original fail-closed proof report that first captured the launch failure:
   [.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260331t201817z/proof-report.json](/home/orchadmin/project-pack-factory/.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260331t201817z/proof-report.json)
2. the latest schema-valid proof report for the active proving-ground request:
   [.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260401t122001z/proof-report.json](/home/orchadmin/project-pack-factory/.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260401t122001z/proof-report.json)
3. the latest schema-valid host-readiness report for that same proof kind:
   [.pack-state/browser-proofs/browser-proof-host-readiness-adf_field_manual_hash_target_opens-20260401t122014z/host-readiness-report.json](/home/orchadmin/project-pack-factory/.pack-state/browser-proofs/browser-proof-host-readiness-adf_field_manual_hash_target_opens-20260401t122014z/host-readiness-report.json)

PackFactory also retains the direct shared-library inspection note:

- [headless-browser-proof-host-dependency-evidence-20260331.md](/home/orchadmin/project-pack-factory/eval/history/headless-browser-proof-host-dependency-evidence-20260331.md)

Those sources prove slightly different things:

- the original March 31 proof report captures the first surfaced missing shared
  library from the actual Playwright run
- the latest April 1 proof report records the exact active headless-shell
  binary PackFactory is trying to launch now
- the latest April 1 host-readiness report runs `ldd` against that same active
  binary and records the broader current missing-library set
- the direct inspection note remains the earlier audit trail that first expanded
  the blocker beyond the one surfaced launch error

Together those historical sources showed the host was missing at least:

- `libatk-1.0.so.0`
- `libatk-bridge-2.0.so.0`
- `libatspi.so.0`
- `libXcomposite.so.1`
- `libXdamage.so.1`
- `libXfixes.so.3`
- `libXrandr.so.2`
- `libgbm.so.1`
- `libasound.so.2`

Current post-provisioning passing evidence:

1. the latest schema-valid host-readiness report showing the active Chromium
   binary is now ready:
   [.pack-state/browser-proofs/browser-proof-host-readiness-adf_field_manual_hash_target_opens-20260401t141715z/host-readiness-report.json](/home/orchadmin/project-pack-factory/.pack-state/browser-proofs/browser-proof-host-readiness-adf_field_manual_hash_target_opens-20260401t141715z/host-readiness-report.json)
2. the latest schema-valid passing browser proof for the same bounded ADF
   request:
   [.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260401t141715z/proof-report.json](/home/orchadmin/project-pack-factory/.pack-state/browser-proofs/browser-proof-adf_field_manual_hash_target_opens-20260401t141715z/proof-report.json)
3. the matching post-provisioning validation note:
   [headless-browser-proof-post-provisioning-validation-20260401.md](/home/orchadmin/project-pack-factory/eval/history/headless-browser-proof-post-provisioning-validation-20260401.md)

Those current sources show:

- `readiness_status`: `ready`
- `missing_shared_libraries`: `[]`
- browser launch succeeds
- the proof reaches live page navigation and page-level assertions
- the overview-link-to-step-card interaction now passes end to end

## Decision

These are host prerequisites.

They are not:

- build-pack dependencies
- browser-proof request fields
- PackFactory registry state
- deployment state
- or runtime evidence that should be imported into a build-pack

PackFactory should keep proving this boundary cleanly:

- the wrapper owns browser runtime under `.pack-state/browser-proof-runtime/`
- the host owns the OS-level shared libraries Chromium needs to launch

## Canonical Evidence Selection

When diagnosing host readiness, PackFactory should prefer:

1. the latest schema-valid browser-proof report for the relevant proof kind
2. the Chromium binary path referenced by that report or by the active browser-proof runtime
3. a direct `ldd` inspection against that same binary

One recorded report may be used as a concrete example, but the durable rule is
to prefer the latest matching proof artifact rather than anchoring diagnosis to
one historical run forever.

## Provisioning Boundary

The provisioning responsibility is host-local and out of band from PackFactory.

PackFactory may:

- detect the missing libraries
- record them in proof reports and evidence notes
- define a readiness-check path
- and point operators at the exact rerun command once the host is ready

PackFactory must not:

- silently install host packages on its own
- smuggle OS packages into a build-pack
- hide missing libraries behind fallback browsers
- or downgrade the proof into a weaker static-only success path

## Host Provisioning Non-Goals

The browser-proof wrapper and its runtime helpers must not:

- execute package-manager commands
- branch into distro-specific package installation logic at runtime
- emit guessed package-manager instructions as if they were canonical PackFactory truth

Host package installation, if needed, is an operator or host-management action
outside the wrapper itself.

## Readiness Check Path

Before treating a browser-proof failure as a wrapper or page defect, the host
should be able to pass a bounded readiness check:

1. the Playwright Chromium binary exists under `.pack-state/browser-proof-runtime/playwright-browsers/`
2. the readiness check targets the active Chromium binary referenced by the latest schema-valid report or the active browser-proof runtime, not an arbitrary older revision directory
3. `ldd` on that active binary returns no `not found` entries
4. rerunning the same validated request, or a regenerated equivalent request, no longer fails during browser launch

The bounded helper path for that readiness check is:

```bash
python3 tools/browser_proof_host_readiness.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --proof-kind adf_field_manual_hash_target_opens \
  --output json
```

## Transient Request Artifact Rule

`.pack-state/tmp/` request files are convenience artifacts only. They are not a
durable contract surface.

For reruns, operators should prefer:

- the same validated request file if it has been preserved as part of a proof run
- or a regenerated equivalent request that matches the request schema and target intent

The request schema plus the latest proof report are the durable PackFactory
surfaces for reconstructing an equivalent rerun, not one transient temp path.

For the current ADF proving ground, one valid rerun example is:

```bash
python3 tools/run_browser_proof.py \
  --factory-root /home/orchadmin/project-pack-factory \
  --request-file /home/orchadmin/project-pack-factory/.pack-state/tmp/browser-proof-request.json \
  --output json
```

## Host Package Guidance

The exact package names are distribution-specific.

This spec intentionally stays at the shared-library level first because that is
the stable cross-host evidence surface PackFactory can record without guessing
the operator's package manager.

Shared-library names are the canonical PackFactory evidence surface. Distro
package names are host-local translation only.

Typical package families behind the current missing libraries include:

- ATK and AT-SPI accessibility libraries
- X11 composite, damage, fixes, and randr libraries
- GBM graphics buffer support
- ALSA audio support

If PackFactory later needs a broader distro-specific helper or operator note,
that should remain a separate bounded follow-up, versioned separately, and keyed
first by shared-library names rather than by guessed package names.

### Ubuntu 24.04 Host Research

The current host is Ubuntu 24.04.4 LTS (`noble`) with `apt` available.

This section is host-specific advisory guidance, not new canonical PackFactory
truth. The canonical PackFactory evidence surface remains the shared-library
names recorded in proof and readiness artifacts.

For this host at the time of review, the shared-library evidence maps to these
confirmed `apt` install candidates:

- `libatk-1.0.so.0` -> `libatk1.0-0t64`
- `libatk-bridge-2.0.so.0` -> `libatk-bridge2.0-0t64`
- `libatspi.so.0` -> `libatspi2.0-0t64`
- `libXcomposite.so.1` -> `libxcomposite1`
- `libXdamage.so.1` -> `libxdamage1`
- `libXfixes.so.3` -> `libxfixes3`
- `libXrandr.so.2` -> `libxrandr2`
- `libgbm.so.1` -> `libgbm1`
- `libasound.so.2` -> `libasound2t64`

The important Ubuntu 24.04 nuance is that several accessibility and audio
packages are now `t64`-suffixed. On this host, the older package names without
that suffix are not the confirmed install candidates for the browser-proof
dependency path, even though the shared-library names themselves are unchanged.
That statement is host-local, not a timeless Ubuntu rule.

### Ubuntu 24.04 Research Evidence

The Ubuntu 24.04 package mapping above was verified from two surfaces:

1. host-local `apt-cache` metadata on this machine
2. official Ubuntu package pages for the `noble` release

Host-local verification showed valid Noble candidates for:

- `libatk1.0-0t64`
- `libatk-bridge2.0-0t64`
- `libatspi2.0-0t64`
- `libxcomposite1`
- `libxdamage1`
- `libxfixes3`
- `libxrandr2`
- `libgbm1`
- `libasound2t64`

It also showed no install candidate for the older non-`t64` package names
`libatk1.0-0`, `libatk-bridge2.0-0`, and `libatspi2.0-0` on this host.

For Ubuntu host-package translation, host-local `apt` candidate metadata wins
over cross-host inference and over package-name memory. If an operator later
installs these dependencies, the install target should be confirmed on the same
host with local package metadata before treating any package name as final.

The Ubuntu 24.04 translation should be read in three categories:

1. exact confirmed install candidate on this host
2. package name that may be satisfied through `Provides` or transition behavior
3. no candidate on this host

This spec only treats the first and third categories as confirmed evidence on
this machine. It does not treat possible `Provides` or transition behavior as
canonical PackFactory truth unless that behavior is directly observed on the
host.

Official Ubuntu package references used for cross-checking:

- `https://packages.ubuntu.com/noble/libatk1.0-0t64`
- `https://packages.ubuntu.com/noble/libatk-bridge2.0-0t64`
- `https://packages.ubuntu.com/noble/libatspi2.0-0t64`
- `https://packages.ubuntu.com/noble/libasound2t64`

Those references were used to cross-check the `t64` package family. The full
Ubuntu 24.04 mapping above was confirmed primarily from host-local `apt-cache`
metadata on this machine.

Ubuntu host-package guidance remains advisory only. PackFactory must not emit a
canonical one-line install command from this section alone.

## Success Condition

This follow-up is complete when PackFactory has a stable operational story:

- wrapper failures caused by missing host libraries are explicit
- host readiness can be checked before deeper debugging
- operators can rerun the same validated request or a regenerated equivalent request after host provisioning
- and at least one rerun progresses past browser launch into page-level assertions, even if those later assertions fail for unrelated page reasons

That success condition is now satisfied on this host for the bounded ADF field-
manual proving-ground recipe.
