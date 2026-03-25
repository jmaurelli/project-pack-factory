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

## Deliberate Non-Goals

- do not treat the current prototype copy as final operator content
- do not broaden scope into full product navigation or account features
- do not replace the machine-readable ADF model with hand-authored page logic
- do not expand tests beyond the current bounded validation and smoke surfaces

## Next Implementation Focus

The next work should convert the current Starlight publishing path toward the
`Support Cockpit` interaction model and use that chassis for the next real ADF
playbook iteration.
