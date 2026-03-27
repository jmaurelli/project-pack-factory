# ADF Language Standard V1

## Purpose

This note defines the default language pattern for ADF diagnostic playbooks.

The goal is not to turn the playbooks into training material. The goal is to
give junior support engineers a repeatable Linux-style troubleshooting flow
with plain language they can reuse with customers and teammates.

## Why We Are Standardizing

ADF playbooks should feel familiar to engineers who work with Linux systems and
Linux-based applications.

The Linux ecosystem does not enforce one universal page-label standard, but the
strong recurring pattern in enterprise Linux docs is:

- a stepwise procedure
- a verification step
- exact use of native tool terms from command output

References:

- Red Hat documentation repeatedly uses `Procedure` and `Verification` in
  troubleshooting and configuration flows:
  - https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html-single/configuring_and_managing_linux_virtual_machines/index
  - https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html-single/security_hardening/security_hardening
- Ubuntu Server documentation describes `How-to guides` as step-by-step guides
  for common operational tasks:
  - https://documentation.ubuntu.com/server/
  - https://documentation.ubuntu.com/server/how-to/
- `systemctl status` output uses exact field labels such as `Loaded`,
  `Active`, and `Main PID`, so ADF should keep those terms unchanged in output
  examples and verification guidance:
  - https://man7.org/linux/man-pages/man1/systemctl.1.html

## Core ADF Flow

Each playbook step should follow this order:

1. `Check`
2. `Run`
3. `Verification`
4. `Linux note` when needed
5. `Known working example`

This keeps the flow stepwise and predictable.

## Standard Labels

Use these labels by default:

- `Check`
  Short plain-language step title.
  Example: `Check Apache service`

- `Run`
  The exact command to run.

- `Verification`
  What the engineer should confirm in the output.
  This replaces more casual variants like `Healthy signal` when we want a more
  Linux-standard wording.

- `Linux note`
  A short explanation only when a Linux term may be unfamiliar.
  Keep this to one or two short sentences.

- `Known working example`
  A real or representative output example that shows what working output looks
  like.

## Wording Rules

- Keep sentences short and direct.
- Prefer basic English over abstract technical phrasing.
- Keep Linux terms consistent across all playbooks.
- Reuse the same term every time for the same concept.
- Keep native CLI labels exact when quoting or explaining command output.
- Do not add long theory sections inside a playbook step.

## Linux Clarification Pattern

When a Linux concept may be unfamiliar, define it briefly in the `Linux note`
section.

Examples:

- `Memory pressure means the server is low on available memory. The server may slow down, use more swap, or kill a process.`
- `Disk pressure means the filesystem is close to full. Services may fail to write logs, temp files, or runtime data.`
- `Inode pressure means the server has too many files or directory entries. A filesystem can fail even when free disk space still exists.`
- `OOM means Out Of Memory. Linux may kill a process to protect the server.`

## What To Avoid

- do not switch between multiple labels for the same idea
- do not alternate between `good`, `healthy`, `valid`, and `normal` unless the
  distinction truly matters
- do not replace native Linux output terms with softer paraphrases
- do not turn a support step into a long technical lesson

## Current Application

This standard should be applied first to:

- `Appliance UI is down`

Then extend to:

- `FireFlow Backend`
- `Microservice Platform`
- `Messaging and Data`
