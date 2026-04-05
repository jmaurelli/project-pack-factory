# ADF Controlled Lab Mutation Experiment Pattern V1

## Purpose

This pattern defines how ADF should run lab-only mutation experiments when the
normal read-only investigation loop has already narrowed the likely control
seam and the next question requires one bounded, reversible change.

The goal is not generic chaos testing.

The goal is to reduce support-engineer effort by proving which component,
proxy seam, or dependency surface actually changes the customer-visible
stop point.

## When To Use This Pattern

Use this pattern only when all of the following are already true:

- the target is a non-production lab system
- a bounded browser or request reproduction already exists
- same-minute log correlation already narrowed the candidate control seam
- the next question cannot be answered cleanly with read-only evidence alone
- the mutation can be rolled back quickly and confidently

Do not use this pattern for broad exploration, permanent config changes, or
open-ended “break it and see” work.

## Core Rules

- mutate one control surface at a time
- keep the mutation temporary and reversible
- prefer a temporary override file over editing the base config inline
- prepare rollback before applying the mutation
- capture the exact start and end timestamps of the mutation window
- reproduce the same bounded browser flow after each mutation
- correlate the same minute in the owning logs before interpreting the result
- revert immediately after the single experiment slice is complete

## Preferred Mutation Shapes

Prefer the smallest surface that can answer the question:

1. temporary Apache include or override file
2. temporary Apache proxy-family deny or divert rule
3. temporary service-level stop only when the seam cannot be isolated higher up

Avoid broader host, network, or application-wide mutations when a proxy or
module seam can answer the same question with less collateral change.

## Safety Checklist

Before applying a mutation:

- confirm the target is still the intended lab host
- record the exact file to touch
- record the exact rollback command
- run a syntax check for the mutated service before reload or restart
- verify the current healthy baseline with the bounded browser flow or control
  curl
- start a note file for the experiment before the mutation begins

## Standard Experiment Template

Use this template for future ADF mutation plans.

### 1. Hypothesis

- What exact question are we trying to answer?
- What specific customer-visible checkpoint should change if the hypothesis is
  true?

### 2. Control Seam

- What is the smallest config or runtime seam that can be mutated?
- Why is this seam better than a browser-only or service-wide change?

### 3. Target File Or Surface

- Exact file path or service name
- Exact block, include, or route family involved

### 4. Preflight

- baseline request or browser flow
- syntax check command
- log paths to capture
- rollback command prepared but not yet run

### 5. Mutation

- exact temporary change
- exact reload or restart command

### 6. Reproduction

- one fresh incognito or bounded browser flow
- success markers
- failure markers

### 7. Evidence

- Apache lines
- downstream service lines
- fresh session id if relevant
- final URL, title, and visible markers if browser-backed

### 8. Rollback

- remove the temporary change
- syntax check
- reload or restart
- confirm the baseline behavior is restored

### 9. Interpretation

- what moved
- what did not move
- whether the seam is now proven, demoted, or still ambiguous

## Default Apache Pattern

When the experiment lives at an Apache seam, prefer this operational shape:

- create a temporary file under `/etc/httpd/conf.d/zzzz_adf_*.conf`
- keep the override scoped to one route family
- run `apachectl -t`
- run `systemctl reload httpd`
- run one bounded reproduction
- remove the temporary file
- run `apachectl -t`
- run `systemctl reload httpd`

Why this pattern matters:

- it avoids hand-editing the base config under pressure
- it makes rollback explicit
- it keeps the mutation diff small and reviewable

## Evidence Standard

A mutation result is only good enough for ADF if it includes:

- the exact mutation window
- the exact control seam touched
- the exact reproduction method
- the exact customer-visible checkpoint that changed or did not change
- the exact same-minute server-side evidence that supports the conclusion

If any of those are missing, the result should be treated as partial rather
than canonical.
