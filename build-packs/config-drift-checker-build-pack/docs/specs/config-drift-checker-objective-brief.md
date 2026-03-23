# Config Drift Checker Objective Brief

## Purpose

This build-pack is intended to produce a deterministic pre-promotion config drift check.

In plain language: given a declared baseline config and a candidate config, the build-pack should identify meaningful differences, summarize their impact, and help an operator decide whether promotion should proceed.

## Current State

The current build-pack now implements the first useful runtime.

Today it can:

- compare baseline and candidate JSON or YAML documents
- emit deterministic findings with path, change type, severity, and reason
- apply a small rules surface for ignored paths, allowed exceptions, and
  severity overrides
- classify results as `pass`, `review_required`, or `fail`

What remains is polish and deepening, not basic existence.

## Intended Inputs

The first useful version of this build-pack should accept:

- one baseline configuration file
- one candidate configuration file
- JSON or YAML input formats
- an optional rules surface for ignored fields, severity overrides, or environment-specific exceptions

## Intended Output

The core output should be a deterministic drift report with:

- input summary: which files were compared and how they were parsed
- normalized comparison summary: added, removed, and changed fields
- severity classification: informational, warning, or blocking drift
- policy result: pass, review_required, or fail
- operator summary: short plain-language explanation of why the result matters

The first operator-facing success case is not just "differences found." It is "differences found and explained well enough to support a promotion decision."

## First-Pass Success Criteria

The build-pack is useful when it can do all of the following reliably:

- detect expected changes between baseline and candidate files
- ignore configured non-meaningful differences
- fail closed on malformed or unreadable input
- produce the same result for the same inputs
- give an operator a short explanation of whether the drift should block promotion

## Initial Metrics

The first metric set should stay small and practical:

- detection accuracy: expected drift is identified correctly
- false-positive control: allowed or ignored differences do not trigger blocking results
- report usefulness: the output makes the reason for pass or fail easy to understand
- runtime cost: the check is fast enough to run before promotion without feeling expensive
- deterministic behavior: repeated runs on the same inputs produce the same result

## Suggested Evaluation Shape

The first benchmarkable scenarios should include:

- no drift: baseline and candidate are equivalent after normalization
- safe drift: expected non-blocking change is reported as informational or warning
- blocking drift: a required field changes, disappears, or appears unexpectedly
- malformed input: invalid JSON or YAML fails cleanly
- ignored-field behavior: configured exceptions suppress expected noise

## Optimization Direction

Once the basic check exists, improvements should be judged against a few explicit goals:

- improve signal quality by reducing noisy findings
- improve operator usefulness by making the summary shorter and clearer
- improve policy usefulness by making pass, review_required, and fail decisions consistent
- improve runtime so the check stays practical in pre-promotion workflows

## What Still Needs Definition

Before this build-pack can be treated as a fully specified release-safety tool, we still need:

- richer normalization and comparison policy for edge cases
- more benchmark scenarios beyond the current smoke coverage
- tighter operator-facing documentation and examples
- sharper guidance on what should default to warning versus blocking
- optional downstream integration surfaces beyond the standalone CLI

## Working Objective

The current working objective for this build-pack is:

Create a small, deterministic config drift checker that compares a baseline JSON or YAML configuration against a candidate version and returns an operator-usable result that is accurate enough, clear enough, and fast enough to support pre-promotion decisions.
