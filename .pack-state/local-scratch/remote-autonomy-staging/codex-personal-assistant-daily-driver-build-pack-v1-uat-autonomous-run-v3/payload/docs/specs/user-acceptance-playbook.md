# User Acceptance Playbook

Use this playbook when the goal is to test the assistant experience with a
human, not to test PackFactory internals.

## What This Playbook Is For

This is a user-facing acceptance test for the staged daily-driver assistant on
`adf-dev`.

It is meant to answer questions like:

- does the assistant understand its own identity and role
- does it understand the operator's goals and grounding principles
- does it guide the user to the right local context
- does its memory surface feel understandable and useful
- does the assistant feel like something worth iterating on

It is not a promotion workflow and it is not a code-validation session.

## Test Target

- build-pack id:
  `codex-personal-assistant-daily-driver-build-pack-v1`
- remote target:
  `adf@adf-dev`
- staged remote pack path:
  `~/packfactory-source__adf-dev__autonomous-build-packs/codex-personal-assistant-daily-driver-build-pack-v1`
- staged UAT run id:
  `codex-personal-assistant-daily-driver-uat-run-v1`
- assistant workspace preview:
  `~/packfactory-source__adf-dev__autonomous-build-packs/codex-personal-assistant-daily-driver-build-pack-v1/dist/candidates/uat-preview/codex-personal-assistant`

## Terminal Setup

Use two terminals.

### Terminal A: remote shell

```bash
ssh adf@adf-dev
cd ~/packfactory-source__adf-dev__autonomous-build-packs/codex-personal-assistant-daily-driver-build-pack-v1
pwd
```

### Terminal B: remote Codex session

```bash
ssh adf@adf-dev
cd ~/packfactory-source__adf-dev__autonomous-build-packs/codex-personal-assistant-daily-driver-build-pack-v1
codex
```

Use Terminal A only as a helper shell. Do the actual assistant-experience test
inside Terminal B in Codex.

## Before You Start

In Terminal A, confirm these surfaces are present:

```bash
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack show-profile --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack show-alignment --project-root . --output json
ls dist/candidates/uat-preview/codex-personal-assistant
```

You do not need to inspect the JSON deeply. This is only a quick sanity check
that the staged remote workspace is the right one.

## Codex Prompts To Try

Paste these prompts into the Codex session one at a time.

### Prompt 1: identity and operator-fit check

```text
You are operating inside a PackFactory assistant build-pack. Read the local instruction and identity surfaces you need, then tell me who you are, what mission you are serving, and what you understand about the operator you are meant to support. Keep it short and concrete.
```

Pass signal:

- the answer sounds like the assistant described in the local profile
- it reflects the operator goals or grounding model rather than a generic assistant persona
- it reflects bounded, inspectable behavior rather than generic AI boilerplate

### Prompt 2: ambiguity handling check

```text
My request is vague on purpose: I want to work on the assistant, but I have not told you whether I mean the template, the runtime build-pack, or user testing. Do not guess. Show me how you would clarify that using the local alignment and workflow surfaces.
```

Pass signal:

- the answer does not guess
- it asks for the minimum clarifying information needed
- it reflects the assistant's fail-closed ambiguity stance

### Prompt 3: grounding check

```text
Use the local operator-alignment surfaces to tell me what long-term direction this assistant thinks I am pursuing, what grounding principles it should use, and how it should keep me aligned when I drift.
```

Pass signal:

- the answer reflects the operator profile and partnership policy
- it feels like a grounded business partner rather than a generic helper

### Prompt 4: memory usefulness check

```text
I prefer concise answers, I often switch contexts, and I want you to keep me grounded in my larger business goals. Use the local assistant memory surface to record that in a way that fits this assistant model, then read it back and tell me how you would use it in future sessions.
```

Pass signal:

- the assistant can use the pack's memory tools or surfaces coherently
- the explanation makes clear that memory is advisory and inspectable, not hidden magic

### Prompt 5: bootstrap usefulness check

```text
Bootstrap the assistant workspace preview for me, inspect what was created, and explain how I would use that preview bundle in plain language.
```

Pass signal:

- the assistant recognizes the exported preview bundle
- the explanation connects the bundle contents to practical usage

### Prompt 6: health and trust check

```text
Run the local doctor or equivalent health surface, then tell me whether anything about this assistant baseline would make you cautious about daily use as a grounded business partner.
```

Pass signal:

- the assistant reports the health result honestly
- it distinguishes what is implemented now from what is still missing

## What To Notice As A Human

During the session, ignore whether the code is elegant.
Focus on these human questions:

- Did the assistant feel grounded in the local pack, or generic?
- Did it seem to understand who it is supposed to help and why?
- Did it understand your intent without wandering?
- Did it handle ambiguity by clarifying instead of guessing?
- Did its memory behavior make sense?
- Did it overclaim what the assistant can currently do?
- Would you want to keep refining this into your actual daily-driver assistant?

## Record Your Reactions

Write short notes, not a full report.

Capture:

- one thing that felt promising
- one thing that felt confusing
- one thing that felt missing
- whether you want the next iteration to focus on:
  - better identity/personality
  - better operator grounding and alignment
  - better memory behavior
  - better workspace bootstrap
  - better day-to-day usability inside Codex

## Pass Criteria

Call this a successful user-acceptance pass if:

- the assistant feels recognizably different from a generic Codex session
- it can explain its identity, operator fit, and mission clearly
- it can handle ambiguity without guessing
- it can handle the memory and bootstrap tasks without feeling fake or opaque
- you come away with a clear next improvement direction

## Failure Criteria

Call this a failed user-acceptance pass if:

- the assistant feels generic and not shaped by the pack
- it guesses through ambiguity instead of clarifying
- it cannot use or explain the local memory surface coherently
- it overstates what is implemented
- the workflow feels too indirect to be worth iterating on

## What To Send Back After The Session

Send back:

- whether the session felt like a pass or fail
- the single most useful behavior you saw
- the single biggest mismatch between your intention and what the assistant did
- the next thing you want built
