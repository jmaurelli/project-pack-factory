# ADF Support Cockpit Direction V1

## Decision

`Support Cockpit` is the selected prototype direction for the next ADF
publishing cycle.

This choice came from operator review of the three fresh Starlight prototypes:

- `Triage Console`
- `Mission Board`
- `Support Cockpit`

The key reason for the decision is navigability during a live support session.
The sticky quick-jump section in `Support Cockpit` stays available while the
engineer reads commands lower on the page, which reduces scroll friction and
helps the engineer move between steps quickly without losing place.

## Why It Matters

ADF is not trying to teach Linux from scratch. It is trying to help a support
engineer move through a bounded diagnostic path while the customer is waiting.

The selected interface direction should therefore optimize for:

- second-screen use during a live remote session
- persistent quick navigation while reading command details
- fast return to another step without scrolling back to the top
- clear checkpoint progression for triage work
- compact command-first presentation

## Current Guidance

For the next implementation cycle:

- treat `Support Cockpit` as the primary Starlight interface direction
- preserve the sticky quick-jump behavior
- keep collapsible checkpoint sections
- keep command blocks and healthy-output references close together
- keep the content plain, short, and explicit for junior support engineers
- use consistent Linux-standard terms across playbooks so engineers build a
  repeatable troubleshooting vocabulary
- when a term may be unfamiliar, add a short plain-language clarification near
  the command rather than turning the page into training material
- keep the JSON-first artifact model intact

## Working Well

The current collapsible `Linux note` pattern is a strong fit for ADF.

It gives engineers optional context without slowing down the operational flow:

- engineers who already know the concept can skip it quickly
- engineers who are less familiar with the term can open it and learn just
  enough to continue
- the playbook stays command-first instead of turning into a long training page

This is a good place to keep adding short educational context over time, as
long as the notes stay optional, brief, and directly tied to the check in
front of the engineer

## Current Winner Pattern

The current winning ADF implementation pattern is:

- discover from live lab evidence
- validate the checks against the real appliance behavior
- render the result back into the Support Cockpit output

This is the first pattern that clearly feels like the right ADF operating
model instead of a hand-shaped documentation page.

Why this matters:

- it produces commands that are tied to the real appliance, not guessed from
  generic service assumptions
- it gives the engineer checks that are operationally useful, not just
  descriptive
- it creates a reusable service-pack model that can be repeated across other
  subsystems

One especially strong signal in this cycle is the use of local `curl` checks
against real service and application paths.

Examples now proven useful in ADF:

- Keycloak readiness
- Keycloak OIDC path
- ms-metro heartbeat

These checks are more valuable than simple process or port presence because
they prove the service is answering a real local path, not only that it has
started.

One important boundary remains:

- the service-pack pattern is now a winner
- the exact ASMS UI dependency order is not fully proven yet

So the current ASMS UI path should be treated as a strong working sequence,
not as a final strict dependency chain, until bounded lab experiments confirm
the real upstream and downstream service order.

Current evidence-backed working model:

- host health first
- Apache edge second
- then parallel first-pass service gates:
  - Keycloak for auth and login-path checks
  - ms-metro for the main application and API path checks
- ActiveMQ remains a supporting dependency, not a first-pass UI-down gate

Why this is the current best fit:

- Apache proxies Keycloak and application paths separately
- Keycloak answers its own local readiness and OIDC paths
- ms-metro answers its own local heartbeat and application paths
- the current lab evidence does not yet prove that ms-metro sits strictly
  behind Keycloak for every UI-down scenario

## Captured Insight

ADF should not think only in terms of isolated services.

The more useful operator model is:

- a playbook such as `FireFlow Backend` represents a subsystem-level
  dependency path
- that path can include multiple services, ports, scripts, logs, Java
  processes, and supporting Linux components
- the same pattern should apply across the appliance as we learn the real
  module boundaries

This means the command-coverage surface should be able to expand and contract
around the subsystem being diagnosed.

In practice:

- command coverage is not just a flat service inventory
- playbooks should group related checks into bounded dependency paths
- those dependency paths may map to product modules and their internal
  supporting services rather than one service at a time

This is still a bounded support model, not full system reverse engineering.
The aim is to model the reduced Rocky Linux footprint and the important
application subsystems that support engineers actually diagnose.

## System-Thinking Theme

ADF should deliberately teach and reinforce system thinking through the
playbook structure.

That means the playbooks should not stop at:

- `is the process up`
- `is the port open`

They should move the engineer toward questions like:

- can this component do useful work
- can this subsystem do useful work
- can the system as a whole do productive work for the current scenario

Examples:

- a service can be running but not functionally healthy
- a port can be open but the application path can still fail
- a multi-component subsystem can be partially up but unable to serve useful
  customer work

This is a strong ADF design direction because it helps the engineer reason
about systems instead of memorizing isolated checks.

## Engineer-Effort Direction

ADF should optimize for the engineer's effort during a live customer session.

That means the playbook should help the engineer answer:

- what is the current assessment of the system
- where is the first meaningful pressure or failure signal
- what should be checked next

This is especially important for the shared host pre-check.

The host pre-check should not only show resource values. It should help the
engineer see the pressure signal behind those values.

Examples:

- disk checks should emphasize pressure on important filesystems, not only raw
  used space
- inode checks should emphasize inode pressure, not only whether the command
  returned output
- memory checks should emphasize available memory, swap growth, and the
  processes that explain memory pressure
- CPU checks should emphasize sustained load and the processes consuming the
  most CPU

The aim is to help the engineer join a call, run the shared checks quickly,
and reach a current system assessment without having to translate raw output
into meaning alone.

## ASMS UI Reset Direction

`ASMS UI is down` should now be treated as a rebuild-from-scratch path, not an
incremental patching exercise on top of the current page shape.

Why this reset matters:

- the current playbook proved several valuable patterns, including the shared
  host health pre-check, Apache edge checks, and the first useful Keycloak and
  `ms-metro` service packs
- but the overall playbook still reflects too much service thinking
- the next real ADF win is to rebuild that playbook around useful-work
  questions instead of adding more checks to the current structure

The next ASMS UI implementation cycle should start from these questions:

1. can the host support useful work
2. can Apache/HTTPD serve the UI
3. can the auth branch do useful work
4. can the app branch do useful work
5. where does useful work stop

That means:

- Keycloak should be framed as an auth and login-path branch, not just a
  running service
- `ms-metro` should be framed as an application branch that must show useful
  traffic or useful JVM work, not just a listener and a log tail
- logs should stay as supporting clue surfaces after the functional checks, not
  as the main diagnostic destination

The current page is still valuable as a discovery milestone, but it is no
longer the desired final structure for the ASMS UI path.

## Autonomous Iteration Direction

As ADF moves deeper into system thinking, the build-pack should carry more of
the iteration logic itself instead of depending on case-by-case operator
steering for each new scenario.

Desired direction:

- much of the memory and feedback-loop surface already exists in the build-pack
- the next question is what should stay pack-local versus what should be
  imported or inherited from the factory itself
- the build-pack should preserve the right memory surfaces for the remote agent
- the build-pack should make it easier for the agent to learn from prior runs,
  prior scenario evidence, and prior playbook revisions
- the build-pack should increasingly encode how discovery, validation, and
  playbook refinement loop together

Why this matters:

- system-thinking playbooks are harder to improve one scenario at a time by
  hand
- the agent needs pack-local context, prior evidence, and explicit iteration
  rules so it can refine the playbooks with less manual orchestration
- this is how ADF starts to become a durable diagnostic system instead of a
  sequence of one-off agent sessions

Keep the boundary clear:

- do not turn this into uncontrolled autonomous exploration
- keep the loop bounded to the pack's saved memory, explicit planning state,
  and approved lab evidence surfaces
- keep human review in the loop for the major design and scope decisions

## Shared Host Pre-Check Rule

Every major ADF playbook should begin with the same host health pre-check
before it moves into subsystem-specific diagnostics.

This applies even when the reported problem sounds application-specific.

Examples:

- `ASMS UI is down`
- `FireFlow Backend`
- `Messaging and Data`

Each of these should begin by checking core Linux host resources such as:

- disk space
- inode usage when relevant
- memory availability
- OOM pressure
- CPU or load pressure when it helps explain the symptom

Why this matters:

- support engineers troubleshoot the Linux host and the application together
- host-resource failures are common, fast to check, and often explain multiple
  higher-level symptoms at once
- this gives every playbook the same operational starting point, which builds
  consistency and confidence across cases

The fixed command set and wording for that shared pack now live in
`docs/specs/adf-host-health-precheck-pack-v1.md`.

## Deliberate Non-Goals

- do not treat the current prototype copy as final operator content
- do not broaden scope into full product navigation or account features
- do not replace the machine-readable ADF model with hand-authored page logic
- do not expand tests beyond the current bounded validation and smoke surfaces

## Next Implementation Focus

The next work should convert the current Starlight publishing path toward the
`Support Cockpit` interaction model and use that chassis for the next real ADF
playbook iteration.

## Future Direction To Keep In View

ADF may eventually become more than a documentation page that an engineer
reads.

There is a plausible future direction where ADF behaves more like the support
engineer's support engineer:

- scenario-based starting points
- a small number of clickable diagnostic paths
- collapsible operational sections that feel more like a working dashboard
  than a long article
- enough guidance for the engineer to decide whether the current path fits the
  live case and then continue or switch paths

If this direction is explored later, keep it bounded:

- do not turn the page into a crowded control panel
- keep the number of starting scenarios intentionally small
- preserve the command-first troubleshooting flow
- treat this as an operator-assistance surface, not a full case-management
  product
