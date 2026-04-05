# ASMS UI Dependency Order Validation v1

Date: 2026-03-26

## Purpose

Validate whether the ASMS UI path should be described as a strict serial chain:

`host -> httpd -> keycloak -> ms-metro`

or whether some of those services should remain peer first-pass checks inside a
bounded support map.

## Conclusion

The current lab evidence is strong enough to reject the strict serial chain.

The stronger current model is:

- host health
- Apache UI edge
- split into auth and app branches
- legacy auth/session-validation hop on the auth side
- first usable `/afa/php/home.php` shell
- immediate shell bootstrap
- later Metro-backed data-plane and module traffic

In plain terms:

- Apache proves useful work before Keycloak or Metro need to be claimed as the
  next strict step.
- Keycloak is a real auth-chain member, but it is later than the first named
  auth checkpoint.
- Metro is a real subsystem dependency, but it is not proven as a single
  strict next step after Keycloak.

## Evidence That Rejects The Strict Chain

### Apache proves useful work first

From [asms-ui-systems-pass-20260325.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/.pack-state/remote-codex/asms-ui-systems-pass-20260325.md):

- Apache serves `/algosec-ui/login` directly.
- The practical edge is already useful before Keycloak or Metro are tested.
- The evidence there explicitly supports `host -> Apache edge -> parallel
  first-pass auth and app neighbors` more strongly than a strict
  `Apache -> Keycloak -> Metro` story.

### Keycloak is not the first auth checkpoint

From [asms-ui-authenticated-flow-pass-20260325.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/.pack-state/remote-codex/asms-ui-authenticated-flow-pass-20260325.md):

- the first proven legacy auth-triggering request is
  `POST /afa/php/SuiteLoginSessionValidation.php?clean=false`
- Keycloak appears later in the observed authenticated chain
- BusinessFlow is reached before the later Keycloak and FireFlow handoff in
  that reproduced authenticated minute

So Keycloak should stay as a later auth-branch member, not the first strict
post-Apache step.

### Metro is not proven as a strict next step after Keycloak

From [asms-ui-bounded-dependency-map-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/asms-ui-bounded-dependency-map-v1.md) plus the accepted delegated seam bundles:

- the hard first-shell Metro dependency is the backend login/session-bootstrap
  config fetch through
  `HandleConfigParams() -> GetConfigurationSettings() -> RestClient::getAllConfig()`
- that is narrower than “Metro as the next serial step after Keycloak”
- Metro also appears as a post-entry data plane after the first usable shell

So Metro is clearly in the subsystem, but not in the way the strict chain
claims.

### Family-wide Apache-to-Metro blocking did not break the shell

From [asms-ui-apache-metro-proxy-isolation-plan-v1.md](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/docs/specs/asms-ui-apache-metro-proxy-isolation-plan-v1.md):

- blocking `/afa/external` did not stop a fully usable `AlgoSec - Home` shell
- blocking top-level `/afa/api/v1` also did not stop a fully usable shell

That demotes a simple “Apache then Metro” gate model and pushes the evidence
toward deeper branch-specific ownership instead.

## Stronger Replacement Model

Use this as the current evidence-backed order statement:

1. host can support useful work
2. Apache serves the practical UI edge
3. the path splits into auth and app branches
4. the auth side reaches a legacy setup and session-validation checkpoint
   before later Keycloak and FireFlow handoff
5. the first usable AFA shell is `/afa/php/home.php`
6. immediate shell bootstrap follows
7. Metro-backed data and later module traffic populate the shell after entry

## What This Means For ADF

ADF should not claim:

- `host -> httpd -> keycloak -> ms-metro`

ADF should claim:

- Apache is the first real UI edge
- Keycloak is a later auth-branch dependency
- Metro is an app-branch and bootstrap dependency with both pre-shell and
  post-shell roles, not a single strict next rung after Keycloak

## Next Useful Move

The dependency-order question is now answered well enough for the top-level
ASMS path.

The next high-value step is to use this validated order to deepen the
dependency-aware playbooks rather than continuing to re-prove the same top-level
ordering claim.
