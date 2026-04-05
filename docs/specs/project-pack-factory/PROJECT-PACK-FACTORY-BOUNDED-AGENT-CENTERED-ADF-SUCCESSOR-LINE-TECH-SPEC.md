# Project Pack Factory Bounded Agent-Centered ADF Successor Line Tech Spec

## Status

Draft v1 planning specification for a fresh ADF successor line that uses the
agent as the operating center from initialization instead of treating the agent
as a helper attached after the fact.

## Goal

Define a clean PackFactory path for a new AlgoSec Diagnostic Framework
build-pack that:

- starts as an agent-native project from day one
- uses a custom ADF-oriented role/domain lens
- carries explicit goals, objectives, memory, and task tracking
- can ingest incomplete but agent-optimized technical documentation
- can perform bounded live system discovery on the Rocky 8 target
- produces early tangible machine-readable and engineer-facing artifacts
- stays aggressively bounded so the operator gets useful evidence early rather
  than waiting through long speculative build phases

## Why A Fresh Line

The current ADF build-pack has valuable domain progress, but it also records a
repeated lesson: broad ambition without tight slice boundaries delays useful
feedback.

The successor line should preserve the current ADF learning while changing the
operating model:

- the agent is the core operating surface
- the canonical product is machine-readable diagnostic content
- engineer-facing playbooks and guides are derived outputs
- scope deepens only after a smaller artifact is accepted as useful

## Problem

The operator has already attempted multiple ADF-style lines and the hardest
failure mode has not been raw technical impossibility. The harder failure mode
has been delayed feedback and insufficient bounding:

- the agent had too much open problem space
- the operator could not supply enough perfect direction to compensate
- long cycles produced large revisions instead of early visible wins
- the work often became more conceptually interesting than support-useful

The successor line therefore needs to optimize for:

- bounded extraction over broad exploration
- evidence-first learning over speculative reconstruction
- early reviewable outputs over long blind architecture phases
- layered growth over one-shot intelligence claims

## Desired Product Shape

The new line should behave like an agent-centered diagnostic factory for a
virtual appliance running on Rocky Linux 8.

### Core operating model

- The agent reads available technical documentation, even when incomplete.
- The agent performs bounded live discovery on the target host and appliance.
- The agent builds or refines machine-readable diagnostic content.
- The agent derives support playbooks and engineer-oriented guides from that
  machine-readable layer.
- The agent writes for support engineers who are capable but not deeply
  specialized.
- The agent keeps deeper dependency reasoning behind explicit stop points.

### Layered build order

1. runtime evidence and bounded system discovery
2. machine-readable system, boundary, and dependency model
3. frontline support playbooks and guides
4. deeper dependency-aware troubleshooting content
5. predictive failure hints only after earlier layers are trustworthy

## Hard Bounding Rules

The successor line should treat these as product rules, not preferences.

### Rule 1: every meaningful slice must produce a reviewable artifact

If a task cannot produce something tangible early, it is too large.

Valid early artifacts include:

- one machine-readable boundary record
- one bounded dependency map
- one small support playbook fragment
- one safe command pack with healthy and failure interpretation
- one rendered review surface derived from canonical structured content

### Rule 2: evidence before inference

The line should prefer:

- observed services, ports, processes, logs, configs, JVM surfaces, and runtime
  state

over:

- broad architectural theory unsupported by current evidence

### Rule 3: shallow-first for support usefulness

The line should stop early when the current support question is already narrow
enough. Deeper subsystem explanation is only justified when the shallow path
stays ambiguous or the reproduced journey reaches a deeper boundary clearly.

### Rule 4: one bounded content shape at a time

The line should not try to evolve:

- system map
- dependency map
- support language
- predictive hints
- and publication shell

all at once in one slice.

### Rule 5: prediction is earned, not assumed

AI-assisted predictive failure analysis remains a later candidate layer.
It should not shape the first implementation slices until the structured
diagnostic model is already useful and trusted.

## Inputs For The Successor Line

The successor line should explicitly plan to use three kinds of input.

### Input A: incomplete but agent-optimized technical documentation

The operator already has technical material that is incomplete but optimized for
agent traversal. That is valuable and should be treated as a first-class input,
not as a failure because it is not complete.

### Input B: live target discovery

The target environment is unusually favorable for bounded discovery:

- Rocky Linux 8 host
- live virtual appliance on top
- direct command execution
- Java runtime and JVM processes
- Linux services
- accessible logs, ports, files, configs, and process state
- Java-adjacent CLI introspection opportunities where safe and available

The line should treat this observability as a reason to favor extraction and
synthesis over speculative reverse engineering.

### Input C: inherited ADF lessons and artifacts

The current ADF build-pack already contains product and method learning that
the successor line should reuse.

## Evidence From The Current ADF Line

### Evidence A: the current ADF line already has the right canonical control plane

The current build-pack already carries:

- objective: [contracts/project-objective.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/contracts/project-objective.json)
- backlog: [tasks/active-backlog.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/tasks/active-backlog.json)
- work-state: [status/work-state.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/status/work-state.json)
- restart memory: [latest-memory.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/.pack-state/agent-memory/latest-memory.json)

That proves PackFactory can already support the goals/objectives/memory/tracker
shape required for a successor line.

### Evidence B: ADF already records multiple bounded-support lessons

The current ADF work-state records proven lessons such as:

- healthy-path trial first
- symptom-classification trial second
- shallow-fault trial third
- keep frontline flows shallow before deeper subsystem branches
- treat useful work as a stop rule
- keep remote autonomy contract-safe and bounded

Those lessons are visible through validation summaries and restart notes in
[status/work-state.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/status/work-state.json).

### Evidence C: ADF already has reviewable generated artifacts

The current line already produces tangible candidate outputs under
[dist/candidates](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/dist/candidates),
including target-backed baseline and Starlight review surfaces. That proves the
line can generate inspectable artifacts early enough to anchor operator review.

### Evidence D: the objective already captures the right product direction

The current objective already emphasizes:

- machine-readable truth first
- support-facing playbooks and HTML as derived layers
- bounded runtime evidence
- minimal test expansion
- promotion and autonomy boundaries

See
[contracts/project-objective.json](/home/orchadmin/project-pack-factory/build-packs/algosec-diagnostic-framework-build-pack-v1/contracts/project-objective.json).

## Recommended Successor-Line Framing

The new line should begin with:

- one custom ADF role/domain lens
- one optional personality overlay chosen deliberately
- one explicit agent-native project profile

### Role/domain recommendation

Do not force the successor line into a generic catalog lens if a better ADF
shape is needed.

The likely right move is a pack-specific role/domain lens such as:

- `diagnostic-systems-analyst`
- or `support-playbook-architect`

The chosen lens should emphasize:

- system and dependency mapping from live evidence
- clear separation of observed facts and inference
- support-useful stop points
- machine-readable intermediate knowledge
- plain-language derived guidance

### Personality recommendation

Use a practical operator-facing personality overlay, not a grandiose one.
The line should sound:

- plain
- grounded
- review-oriented
- useful to a busy operator

### Agent-native recommendation

Use the new declaration model from
[PROJECT-PACK-FACTORY-AGENT-NATIVE-PROJECT-INITIALIZATION-TECH-SPEC.md](/home/orchadmin/project-pack-factory/docs/specs/project-pack-factory/PROJECT-PACK-FACTORY-AGENT-NATIVE-PROJECT-INITIALIZATION-TECH-SPEC.md)
so the new line starts with explicit tracker, memory, tooling-awareness, and
bounded autonomy expectations.

## First Implementation Wave

The first wave should stay intentionally small.

### Wave 1 objective

Produce one accepted bounded proof loop:

- one live runtime evidence slice
- one small machine-readable diagnostic artifact
- one derived support-facing artifact
- one explicit operator judgment about usefulness

### Wave 1 suggested focus

Good first-slice candidates:

- host and appliance boundary map
- one Java or service boundary with safe CLI inspection
- one dependency checkpoint that support engineers can actually use

### Wave 1 non-goals

Do not make these first-wave requirements:

- broad predictive analytics
- broad failure forecasting
- full appliance reverse engineering
- full documentation completion
- deep multi-boundary publication architecture

## Proposed Control-Plane Next Step

This planning slice should be followed by a bounded creation request for:

- one fresh ADF successor template or directly one fresh build-pack line
- explicit role/domain selection
- explicit personality selection
- explicit agent-native profile declaration
- explicit first-wave objective centered on early tangible evidence

The new line should inherit lessons from current ADF, but it should not be a
mechanical clone of the current build-pack.

## Out Of Scope

- rewriting the current active ADF build-pack in place
- claiming predictive AI value before the structured evidence base is useful
- requiring complete documentation before the successor line can start
- assuming the operator must provide deep software expertise up front

## Decision

It is feasible to create a new ADF build-pack that includes:

- a custom role/domain agent
- goals and objectives
- task tracking
- restart memory
- incomplete but useful technical documentation
- bounded live system discovery on Rocky 8
- derived support playbooks from machine-readable diagnostic content

The core design requirement is not more ambition. It is tighter bounding and
earlier tangible proof.
