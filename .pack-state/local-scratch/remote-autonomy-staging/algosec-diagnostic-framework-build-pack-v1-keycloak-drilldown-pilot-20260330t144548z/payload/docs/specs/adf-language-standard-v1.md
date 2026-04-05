# ADF Language Standard V1

## Purpose

This note defines how ADF should present diagnostic steps to frontline support
engineers.

The target reader is:

- working live with a customer over Teams or Zoom
- using copy-paste CLI commands
- often reading English as a second language
- trying to triage quickly, not study architecture

ADF should help the engineer do three things fast:

1. run the next command
2. read the result
3. decide whether to continue or switch to a narrower diagnosis

## Operator Context

ADF playbooks are not training guides and not design documents.

Most support cases take more than one session. The first session is often a
triage session:

- gather evidence
- identify the likely failing area
- record what was observed
- continue offline research or lab reproduction later

Because of that, the playbook language must stay explicit and operational.
It should not introduce new concepts during the live session unless the concept
is required to read the command output.

## Core Presentation Pattern

Use this order for frontline playbook steps:

1. Step title
2. Run
3. Expected result
4. Check output for
5. If result is different
6. Example

This pattern is faster to scan than explanatory prose.

## Step Title Rules

Step titles should be short verb phrases.

Use forms like:

- `Check host pressure`
- `Check Apache and login page`
- `Check core services`
- `Check shell access`

Do not use step titles like:

- `Decide whether this is still really GUI down`
- `Start by confirming what the customer actually sees`
- `Branch into the narrower failing workflow`

Those phrases describe hidden reasoning instead of the operator action.

## Standard Labels

Use these labels by default for frontline pages:

- `Run`
- `Expected result`
- `Check output for`
- `If result is different`
- `Example`

These labels are short, literal, and easier for multilingual readers.

Avoid replacing them with softer or more abstract labels such as:

- `Why this matters`
- `When to use this`
- `Stop rule`
- `Avoid first`
- `Operator note`
- `Field note`
- `Healthy signal`
- `Useful work`

## Wording Rules

- Keep sentences short.
- Use basic English.
- Use literal service and route names.
- Use the exact Linux or HTTP term when the command output uses it.
- Prefer one instruction per sentence.
- Prefer direct verbs: `check`, `run`, `save`, `restart`, `continue`.
- Keep branching language explicit.

## Command Readability Rules

Frontline commands should also be easy to scan.

- Prefer human-readable flags when the tool supports them.
- Prefer output that avoids mental unit conversion during a live session.
- Prefer one readable command over a denser command that saves only a few characters.

Use forms like:

- `free -h`
- `df -h`
- `systemctl status httpd --no-pager`
- `ps -p <pid> -o pid,etime,%cpu,%mem,cmd --cols 160`

Avoid forms like:

- `free -m` when `free -h` is enough for the decision
- paged output that forces the engineer to scroll inside `less`
- commands that require the engineer to translate bytes or kilobytes manually

The main rule is simple:

- if a flag makes the output easier for a support engineer to read quickly, use it by default

Good examples:

- `If httpd is not active, diagnose Apache/HTTPD.`
- `If port 443 is missing, save the output and continue with Apache diagnosis.`
- `If /afa/php/home.php appears, continue with shell or workflow diagnosis.`

Weak examples:

- `Stop at the UI edge.`
- `Branch out of GUI down.`
- `The path is no longer doing useful work.`
- `The session crossed into a later content branch.`

## Branching Language

Branching text should tell the engineer what the result means in plain support
language.

Prefer:

- `If result is different: diagnose Apache/HTTPD.`
- `If result is different: diagnose the failed service.`
- `If result is different: continue with Reports diagnosis.`

Avoid:

- `Stop here.`
- `Stop at this boundary.`
- `Branch out.`
- `Escalate the seam.`
- `Treat this as the terminal node.`

The engineer already understands that a different result changes the next step.
ADF should name that next step directly.

## Learning Content

Frontline pages should not teach architecture during the live session.

Optional Linux explanation is allowed only when needed to interpret command
output, and it should stay outside the fastest reading path.

If a concept is not required to read the current command result, do not explain
it in the main operator flow.

## Current Application

Apply this standard first to:

- `ASMS UI is down`

Then carry the same style into:

- `FireFlow Backend`
- `Microservice Platform`
- `Messaging and Data`
