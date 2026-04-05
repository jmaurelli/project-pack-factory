# ASMS DocPack Reference Note v1

Date: 2026-03-27

## Purpose

Record the available ASMS docpack on `adf-dev` as a supplementary reference
surface for ADF, while explicitly preserving the working rule that live
runtime evidence remains the stronger source for subsystem mapping.

## Current Remote Location

Package root on `adf-dev`:

- `/ai-workflow/packages/asms-docpack-v1`

Verified generated docpack:

- `/ai-workflow/out/asms/A33.10/asms-docpack`

Related generated export:

- `/ai-workflow/out/asms/A33.10/asms-knowledge-export`

## Important Limitation

This docpack should not be treated as complete technical truth for ASMS.

Current operator guidance is:

- the ASMS technical documentation is grossly incomplete
- much of it is common configuration guidance and simple operator help
- it is useful as a high-level reference point, but not as a substitute for
  runtime correlation or subsystem proof

So the working authority rule is:

- live ADF target-backed evidence wins for runtime ownership, dependency order,
  and real stop-point logic
- the docpack is supplementary and mainly useful for naming, broad product
  boundaries, and official surface vocabulary

## Safe Uses

Use the docpack for:

- high-level product subdivision such as AFA, FireFlow, and AppViz
- official names for modules, APIs, and major admin areas
- conceptual cross-checks when a live runtime seam needs a likely product label
- cautious candidate branch ideas for later investigation

Do not use the docpack by itself to prove:

- real request ownership on this lab appliance
- current runtime dependency order
- whether a service is actually first-pass, later-supporting, or inactive
- whether a documented flow still matches the observed appliance behavior

## Agent Read Order

Follow the docpack's own agent guidance on `adf-dev`:

1. `/ai-workflow/out/asms/A33.10/asms-docpack/README_FOR_AGENT.md`
2. `/ai-workflow/out/asms/A33.10/asms-docpack/manifest.json`
3. `/ai-workflow/out/asms/A33.10/asms-docpack/toc.json`
4. `/ai-workflow/out/asms/A33.10/asms-docpack/reports/validation_report.json`
5. `/ai-workflow/out/asms/A33.10/asms-docpack/bundles/*.md`

Use `pages.jsonl` and `chunks.jsonl` only for targeted lookup.

## Current High-Level Value

The verified docpack is still useful because it gives a cleaner official
topology outline than ad hoc browsing:

- `AFA components`
- `Welcome to FireFlow`
- `Welcome to AppViz`
- `System management`
- `Authentication`
- `Workflow`
- `AFA REST web services`
- `AFA SOAP web services`
- `ASMS API reference`

That makes it useful for conceptual subsystem naming, but not enough to replace
the current ADF system-thinking method:

1. reproduce one bounded real flow
2. correlate the same minute in Apache and downstream evidence
3. only then update the subsystem map or playbook

## Local Handling Rule

For now, keep the docpack as an external remote reference on `adf-dev`.

Do not copy the full generated docpack into the local canonical ADF build pack
unless a later task explicitly needs a local snapshot for offline reuse or
pack-local artifact generation.
