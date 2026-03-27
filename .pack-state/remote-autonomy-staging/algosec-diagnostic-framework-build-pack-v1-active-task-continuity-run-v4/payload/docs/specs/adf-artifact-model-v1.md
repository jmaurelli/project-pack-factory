# ADF Artifact Model v1

ADF v1 keeps JSON as the source of truth and treats rendered documentation as a
view of the same baseline artifacts.

## Generated Artifacts

- `runtime-evidence.json`
  Read-only collection output for runtime identity, service-manager output,
  TCP listeners, process inventory, and observation boundaries.

- `service-inventory.json`
  Canonical service records derived from runtime evidence, with observed facts,
  bounded support-priority inference, and explicit unknowns.

- `support-baseline.json`
  Support-facing baseline summary for customer-side diagnosis, including domain
  flows, symptom lookup, and decision playbooks with explicit failure points,
  next decisions, and read-only diagnostic commands tied back to the canonical
  JSON artifacts. Command entries should carry the operator-facing `Linux note`
  and `Known working example` data in the JSON itself so rendered views do not
  become the only place those references exist.

- `support-baseline.html`
  Thin human-facing render of `support-baseline.json` for live remote support
  sessions.

- `starlight-site/`
  Generated Astro Starlight site source derived from `support-baseline.json`,
  including `package.json`, `astro.config.mjs`, content collection files,
  markdown playbook pages, and renderer assets.

## Boundary Rules

- Observed facts stay separate from inferred hints.
- Unknowns stay explicit instead of being silently filled in.
- Config paths, log paths, and deeper dependency mapping remain out of scope
  for this first slice unless later evidence justifies them.
