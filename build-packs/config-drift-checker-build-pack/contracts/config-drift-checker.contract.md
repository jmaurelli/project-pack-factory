# Config Drift Checker Build-Pack Contract

## Contract Status

This contract defines the intended behavior of `config-drift-checker-build-pack`.

It is the target contract for the next implementation phase. The current build-pack does not yet satisfy this contract end to end.

## Purpose

The build-pack must compare a declared baseline configuration against a candidate configuration and produce a deterministic result that helps an operator decide whether promotion should proceed.

## Packaging And Integration Posture

This build-pack is `standalone-first, modular-core, integration-ready`.

That means:

- the first supported interface is a CLI command
- the core comparison logic should live in reusable Python functions behind the CLI
- the output must be machine-readable so a larger workflow or promotion gate can consume it later
- direct integration into a broader system is a downstream use case, not the first delivery requirement

## Supported Inputs

The first implemented version must accept:

- one baseline configuration file
- one candidate configuration file
- JSON or YAML input
- an optional rules file for ignored paths, severity overrides, and allowed exceptions

The contract assumes local file inputs first. Remote fetch, service mode, and repository-wide scanning are out of scope for the first version.

## Primary Command Contract

The build-pack should expose a command shaped like:

```bash
PYTHONPATH=src python3 -m config_drift_checker_build_pack check-drift \
  --baseline path/to/baseline.yaml \
  --candidate path/to/candidate.yaml \
  --output json
```

Optional first-pass arguments may include:

- `--rules path/to/rules.json`
- `--fail-on warning|blocking`

The command must:

- exit `0` for `pass`
- exit `2` for `review_required`
- exit `1` for `fail`
- exit `1` for malformed input or unreadable files

## Output Contract

The primary output must be JSON and must contain:

- `status`: `pass`, `review_required`, or `fail`
- `baseline_path`
- `candidate_path`
- `input_format`: `json`, `yaml`, or `mixed`
- `summary`
- `findings`
- `counts`

The `findings` array should contain entries shaped like:

```json
{
  "path": "services.api.timeout",
  "change_type": "changed",
  "baseline_value": 30,
  "candidate_value": 60,
  "severity": "warning",
  "reason": "Timeout changed from baseline."
}
```

The `counts` object should include at least:

- `informational`
- `warning`
- `blocking`
- `total_findings`

The `summary` field should be a short plain-language explanation suitable for an operator reading a promotion check result.

## Policy Semantics

The first policy meanings are:

- `pass`: no blocking drift and no review-worthy drift after rules are applied
- `review_required`: non-blocking drift exists and should be acknowledged before promotion
- `fail`: blocking drift exists or the input could not be trusted

The contract is fail-closed on malformed, unreadable, or ambiguous input.

## Normalization Rules

The first implementation may normalize only what it can do deterministically and explain clearly.

Acceptable first-pass normalization includes:

- object key ordering differences
- equivalent JSON and YAML parsing into the same internal representation

The first version should not silently normalize away semantically meaningful changes.

## First Required Scenarios

The build-pack must eventually support benchmarkable scenarios for:

- equivalent baseline and candidate files
- a safe non-blocking change
- a blocking change to a required field
- malformed input
- ignored-path behavior through rules

Each scenario should have an expected result and expected status.

## Non-Goals For First Version

The first version does not need to support:

- live environment discovery
- multi-file repository scanning
- policy learning
- remote configuration sources
- automatic remediation

## Implementation Boundaries

The implementation should separate:

- file loading and parsing
- normalization
- diff generation
- policy classification
- operator summary rendering

That separation matters because it keeps the standalone CLI useful now while making later workflow integration easier.

## Acceptance Boundary

This build-pack should be considered ready for deeper workflow use when it can:

- satisfy the CLI contract above
- emit the JSON output contract above
- pass a small benchmark suite covering the required scenarios
- produce deterministic results across repeated runs with identical inputs
