# ADF Successor Daily Reader Content Grammar v1

## Purpose

Define the reusable reading grammar for support-engineer-facing ADF content.

This note turns the current playbook and cookbook review work into a stable
template method for how engineers should read ADF every day.

The goal is not just readable pages.
The goal is repeated-use pages that become familiar, fast, and low-friction
for engineers who read technical content all day and learn to spot key signals
through consistent visual and structural patterns.

## Reader Model

The intended reader is an experienced ASMS support engineer who:

- reads technical material all day
- learns recurring page structure quickly
- builds scan memory over time
- wants explicit triage flow, not coaching
- can handle dense technical content when it is structured cleanly

ADF should take advantage of that reader strength.

That means the shell and content should optimize for:

- repeated scanning
- fast recognition of the important block
- familiar section order
- stable label meaning
- low navigation friction

It should not optimize for:

- one-time tutorial reading
- beginner coaching
- marketing-style narrative landing pages
- decorative navigation modules that compete with the main reading task

## Core Design Rule

ADF support content should behave like a reading system.

Engineers should learn the page grammar once, then reuse that same reading
motion across playbooks and cookbooks.

The main design rule is:

- keep page archetypes few
- keep section order stable
- keep labels stable
- keep visual meaning stable

Once a label or block meaning is chosen, it should not drift casually between
pages.

## Visible Naming Rule

Engineer-facing pages should use:

- `AlgoSec Diagnostic Framework`
- `ADF`

Do not show `successor` in visible shell labels, overview copy, or page titles.

Internal specs, template ids, and pack ids may still use `successor` where the
factory needs the distinction.

## Fixed Reading Pattern

The page should support the same scan path every time:

1. confirm page identity
2. read the main operating block
3. read the next movement block
4. deepen only if needed

This is the daily ADF reading rhythm.

In practical terms:

- the top of the page answers `where am I`
- the main body answers `what do I do now`
- the next block answers `where do I go next`
- the lower or supporting section answers `what foundation supports this`

## Page Archetypes

ADF should keep the visible support surface to three page archetypes:

### 1. Playbook Path Page

This is the frontline triage page.

Its visible structure should stay strict:

- title
- `Steps`
- `Branch to`
- `Related cookbook foundations`

This page exists to move the engineer through triage, not to explain the whole
product.

### 2. Cookbook Foundation Page

This is the deeper product and runtime understanding page.

Its visible structure should stay stable:

- title
- compact summary
- matrix or flow view where useful
- `Validated behavior`
- `Observed practice`
- `Operator theory`
- `Not proven`
- `Related playbooks`

This page exists to deepen understanding without weakening the evidence
boundary.

### 3. Index Or Entry Page

This is the short route-selection page.

Its visible structure should stay simple:

- title
- compact one-line purpose statement
- route cards or route list

It should route the engineer quickly and should not become a narrative landing
page.

## Information Weight

ADF should use the same information weight on every page:

1. action
2. movement
3. foundation

For playbooks:

- `Steps` is the highest-weight block
- `Branch to` is the second-highest block
- `Related cookbook foundations` is the lowest-weight block

For cookbooks:

- summary plus matrix or flow view is the highest-weight block
- evidence-state sections are the second-highest block
- `Related playbooks` is the lowest-weight block

Do not let side modules or decorative navigation outrank the main operating
block.

## Block Semantics

Each visible block should have one job only.

### `Steps`

Use `Steps` only for explicit operating actions.

Rules:

- ordered list only
- one action per step
- keep the opening verb explicit
- avoid rationale sentences inside the step unless the action becomes unclear
- prefer short lines over compound instructions

### `Branch to`

Use `Branch to` only for next movement.

Rules:

- each branch starts with an observed condition
- each branch ends with one clear destination
- keep the phrasing compact and repeatable
- avoid essay-like explanation inside the branch list

Preferred shape:

- `<observed state>` -> `<route or anchor>`

### `Related cookbook foundations`

Use this only for supporting depth.

Rules:

- short list only
- stable page names only
- no explanation paragraphs here

### `Validated behavior`

Use only for behavior supported by current lab-backed or repeated evidence.

### `Observed practice`

Use for repeated support or lab practice that looks real but is narrower than
validated behavior.

### `Operator theory`

Use for useful but not-yet-proven interpretation.

### `Not proven`

Use for explicit uncertainty.

This block matters because it prevents ADF from sounding more certain than the
evidence supports.

## Writing Contract

The writing contract should stay blunt, technical, and calm.

Use:

- short sentences
- stable product naming
- direct verbs
- explicit technical nouns
- line-level clarity

Avoid:

- coaching phrases
- reassurance language
- tutorial tone
- marketing language
- soft symptom storytelling
- abstract builder language on support pages

Examples of rejected support-page drift:

- `Use this path when`
- `What this path helps confirm`
- `Why this matters`
- `What these signals usually mean`
- `Evidence to capture`

Those phrases belong to review notes or deeper design thinking, not to the
daily operating page.

## Visual Contract

The visual shell should support long daily reading sessions.

Use:

- one main reading lane
- compact vertical spacing
- strong heading contrast
- repeated block styling with fixed meaning
- restrained accent color
- light field-manual direction

Avoid:

- large empty spacing bands
- dark cockpit styling by default
- tutorial-style helper boxes above every section
- high-noise card layouts
- persistent `On this page` furniture that steals width from the reading lane

## Navigation Rule

Everyday engineer pages should favor reading space over intra-page navigation.

That means:

- no default `On this page` division
- no persistent table-of-contents rail on normal playbook pages
- no side module that visually outranks `Steps` or the main cookbook block

If a future page truly becomes long enough to need more navigation, that
should be reviewed as an exception instead of becoming the default shell
behavior.
- side navigation that steals too much width
- `On this page` style table-of-contents modules on playbook pages

The page should feel efficient, not ornamental.

## Navigation Rule

Navigation should stay shallow and predictable.

The main navigation is enough:

- `Overview`
- `Playbooks`
- `Cookbooks`

Inside pages, navigation should support movement without dominating the screen.

That means:

- keep route and related-page links available
- do not spend valuable width on large local navigation divisions
- prefer content recognition over navigation chrome

## Template Method

ADF should build new support-facing pages by reusing the same template method:

1. choose the page archetype
2. fill only the approved blocks for that archetype
3. keep section order unchanged
4. keep labels unchanged
5. keep block meaning unchanged
6. review the page by scan path, not just by prose quality

That last rule matters.
An ADF page can be well written and still fail if the eye does not land on the
right information quickly.

## Review Checklist

When reviewing a new ADF page, check:

- does the page archetype match the page purpose
- is the section order still standard
- do the labels still mean what they meant on prior pages
- does the top of the page expose the main operating block fast
- does the page avoid coaching drift
- does the page avoid R&D-depth drift on frontline playbooks
- does the page avoid decorative layout that competes with reading
- does the page help a repeat reader move faster than the last time

## Current First-Wave Mapping

This grammar applies directly to the current reviewed first-wave shell:

- playbook paths:
  `Service State`,
  `Host Health`,
  `Logs`,
  `Data Collection and Processing`,
  `Distributed Node Role`
- cookbook foundations:
  `Core Service Groups by Node Role`,
  `Log Entry Points`,
  `Data Flow Foundations`,
  `Distributed Role Foundations`

This note does not replace the existing playbook-path or site-map contracts.
It provides the shared reading grammar those contracts should now follow.

## Why This Matters

ADF is trying to improve the daily effectiveness of engineers who already know
how to work a case.

The win is not just better content.
The win is faster recognition, lower reading friction, and stronger pattern
memory across repeated use.

If ADF keeps changing the page grammar, engineers have to relearn the shell.
If ADF keeps the grammar stable, engineers can spend their attention on the
diagnostic work itself.
