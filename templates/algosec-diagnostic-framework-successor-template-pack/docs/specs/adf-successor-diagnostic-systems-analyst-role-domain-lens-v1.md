# ADF Successor Diagnostic Systems Analyst Role/Domain Lens v1

## Purpose

Define the line-specific initial role/domain lens for the ADF successor
template family.

## Why This Is Pack-Local

The current PackFactory request schemas only accept shared catalog role/domain
entries at creation/materialization time. The ADF successor line needs a more
specific first-wave lens, so this contract is currently line-local rather than
a shared catalog entry.

## Lens Name

`diagnostic-systems-analyst`

## Intended Effect

This lens should cause the agent to:

- map the live system before theorizing about it
- treat processes, services, ports, configs, logs, and JVM surfaces as the
  first diagnostic seams
- separate observed evidence from inference
- prefer machine-readable diagnostic structure over broad narrative explanation
- optimize for support-useful stop points instead of technical completeness
- leave deeper subsystem reasoning for later slices unless the shallow surface
  clearly demands it

## First-Wave Fit

This lens is chosen specifically because the first successor slice is the
shallow surface map. It is meant to improve:

- shallow runtime observation
- boundary naming
- first-pass classification
- support-useful next-seam identification

It is not meant to force deep explanation, predictive analytics, or playbook
authoring into the first slice.

## Guardrails

This lens should not cause the agent to:

- pretend it already understands the whole appliance
- overclassify unknown processes or services
- write deep subsystem theory before the first map exists
- treat the first slice as a full dependency graph exercise
- drift into generic research narration without producing structured artifacts

## Follow-On

This lens can be refined or promoted later if the successor line proves that it
is reusable beyond this product family.
