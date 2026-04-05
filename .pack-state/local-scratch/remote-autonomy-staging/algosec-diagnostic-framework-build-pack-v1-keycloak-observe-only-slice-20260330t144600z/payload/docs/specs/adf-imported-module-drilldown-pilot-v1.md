# ADF Imported-Module Drilldown Pilot v1

## Purpose

Record the current ADF trial direction for imported-module diagnosis.

The goal is not to create one playbook per Keycloak issue or one playbook per
open source module symptom. The goal is to test whether ADF can use one live
module failure to improve a more general support method.

## Current Pilot

Current pilot:

- treat imported modules such as Keycloak as reusable service-boundary examples
  inside ADF
- keep the scenario playbook responsible for finding the first useful stop
  point
- add a reusable drilldown pattern that helps the engineer classify why the
  named module cannot do useful work
- stop before ADF turns into a long catalog of use-case-specific playbooks

This is a pilot or trial, not a locked long-term ADF shape.

If the method starts to produce too much module-specific branching, too much
maintenance, or too little support value, ADF should pivot quickly instead of
treating the pattern as permanent.

## Current Validation Opportunity

Current operator-reported opportunity:

- Keycloak is down on target lab `10.167.2.150`

Use that as a bounded validation opportunity for the method above.

Do not treat the current live condition as already accepted ADF evidence until
it is captured through the normal PackFactory and ADF evidence path.

## Pilot Validation Result

Latest pilot result from the official staged `adf-dev` observe-only slice:

- run id:
  `algosec-diagnostic-framework-build-pack-v1-keycloak-observe-only-slice-20260330t144600z`
- remote run summary ended at `2026-03-30T14:55:50Z`
- observed failure minute on the target lab:
  `2026-03-30 10:10:55 EDT`
- pilot judgment recorded by the remote slice:
  `proves_reusable_module_boundary_packet`

What the live slice proved:

- the target lab `10.167.2.150` was reachable through the official `adf-dev`
  split-host path
- Apache still served `https://127.0.0.1/algosec-ui/login` with `200`
- the proxied Keycloak OIDC path returned `503`
- `keycloak.service` was failed with `Result=exit-code`
- port `8443` was not listening during the observed slice
- Metro still reported `isAlive: true`
- the journal tail showed a repeated Quarkus startup trace ending in
  `java.io.EOFException`

What this means for the pilot:

- the reusable imported-module drilldown shape is now backed by one live,
  bounded validation slice, not just a proposed structure
- the validated support value came from classifying the boundary and producing
  an escalation-ready evidence packet, not from enumerating Keycloak-specific
  fixes
- this remains a pilot because one case is not enough to lock the pattern in

Current workflow caveat:

- this slice produced a real remote checkpoint bundle and remote run-summary
  evidence, but the current wrapper/export path did not emit a local
  `execution-manifest.json` or runtime-evidence bundle
- treat the preserved local review copy under
  `.pack-state/local-scratch/remote-autonomy-roundtrips/.../incoming/remote-run-audit-only/`
  as audit-only scratch, not imported canonical ADF evidence
- if this export gap repeats, classify it as a PackFactory roundtrip gap, not
  as uncertainty about the Keycloak boundary itself

## Validation Contract Reminder

This pilot is governed by the existing ADF validation surfaces, not by an
ad hoc new rule set.

Use these notes as the current contract:

- `docs/specs/adf-diagnostic-mapping-framework-v1.md`
- `docs/specs/adf-playbook-validation-standard-v1.md`
- `docs/specs/adf-frontline-playbook-testing-workflow-v1.md`
- `docs/specs/adf-frontline-testing-decision-model-v1.md`

Practical meaning:

1. prove the failure boundary on the appliance first
2. validate that the playbook helps the engineer stop at the right boundary
3. only then deepen the branch with bounded evidence-backed checks
4. record what is proven, what is inferred, and what remains unresolved
5. keep the method general enough that the same drilldown shape can apply to
   later imported modules

## Writing Rule For This Pilot

For imported-module drilldowns, prefer this structure:

1. observed boundary on this appliance
2. what that boundary means in ASMS
3. generic failure classes
4. bounded next checks
5. escalation-ready evidence packet
6. upstream references

The page should teach the engineer how to classify the failure, not try to
enumerate every possible resolution.

## Upstream References

Imported modules such as Keycloak are allowed to use upstream open source
repositories and official documentation as supplementary cited guidance.

Use them in this order:

1. local runtime evidence on this appliance
2. ASMS integration evidence for how the module participates in the path
3. official upstream documentation or repository material for bounded deeper
   interpretation

Upstream references may explain what a failure clue means or which deeper
checks are reasonable, but they must not override live appliance evidence about
where the current support boundary actually is.
