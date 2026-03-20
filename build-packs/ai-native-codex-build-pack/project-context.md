# Project Context

## Mission

`ai-native-codex-build-pack` is the deployable PackFactory example derived
from the canonical `ai-native-codex-package-template` source pack.

## Current Intent

- keep the derived build pack structurally similar to the template source
- make readiness and deployment state machine-readable
- preserve benchmark evidence under `eval/history/`
- support testing-first promotion through the PackFactory deployment model

## Package Standards

- build-pack deployment state must remain explicit in `status/deployment.json`
- lineage must always point back to the canonical template source
- environment pointers are projections, not separate truth
- copied benchmark evidence is the current validation anchor
