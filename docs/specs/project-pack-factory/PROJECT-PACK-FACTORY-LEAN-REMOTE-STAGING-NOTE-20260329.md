# Project Pack Factory Lean Remote Staging Note

Date: 2026-03-29

## Summary

The ADF proving ground showed that the remote build-pack staging workflow was
copying far more data than the remote autonomy and review workflows actually
needed.

Two changes were promoted into the PackFactory staging defaults:

- exclude `dist/candidates/algosec-lab-baseline`
- fix dot-prefixed exclusion matching so paths like `.pack-state/autonomy-runs`
  and `.packfactory-remote` are actually excluded

## Before

Latest measured ADF payload under the old policy:

- `12,609` staged file entries
- `244,583,811` bytes
- about `233.25 MiB`

Largest payload contributors:

- `dist`: about `195.96 MiB`
- `.pack-state`: about `36.26 MiB`

The biggest single avoidable payload was
`dist/candidates/algosec-lab-baseline`, and the dot-path exclusion bug allowed
`.pack-state/autonomy-runs` to leak into the remote payload.

## After

Measured ADF payload under the new policy:

- `224` staged file entries
- `2,535,708` bytes
- about `2.42 MiB`

Largest remaining payload contributors:

- `dist`: about `1.08 MiB`
- `src`: about `0.54 MiB`
- `.pack-state`: about `0.31 MiB`

## What Still Syncs

The remote build-pack still receives the PackFactory and ADF data it actually
needs to continue work:

- `AGENTS.md`, `project-context.md`, `pack.json`
- `contracts/`, `tasks/`, `status/`, `lineage/`
- `docs/`, `src/`, `.packfactory-runtime/`
- lightweight `.pack-state` surfaces like agent memory
- small `dist` inputs that support ADF review and validation

## What Does Not Sync

- historical evidence under `eval/history`
- runtime export bundles under `dist/exports/runtime-evidence`
- heavy autonomy-run preservation under `.pack-state/autonomy-runs`
- the bulky appliance-backed candidate snapshot under
  `dist/candidates/algosec-lab-baseline`

## Why This Matters

This keeps remote autonomy staging aligned with what the ADF host actually
needs: PackFactory state plus the build-pack content required to continue
authoring and review. It reduces transfer volume, shortens restaging time, and
avoids treating lab snapshot artifacts as if they were required runtime inputs.
