# Python CLI Click Profile

Approved default profile for this pack.

## Purpose

Use this profile when the package is building a small Python command-line tool with `click`.

## What This Means

This profile is the approved framework baseline for this pack. It keeps the structure small, agent-friendly, and easy to validate.

## Approved Stack

- Language: `python`
- Framework: `click`
- Project shape: `cli`

## Documentation Expectations

- explain command behavior in plain language
- keep runtime inputs explicit
- update `README.md`, `project-context.md`, and `AGENTS.md` when command behavior changes
- generate a `docs/doc-update-record.json` entry with code changes

## Validation Expectations

- keep tests minimal and high-signal
- run `make validate`
- keep `ruff` and `mypy` clean
