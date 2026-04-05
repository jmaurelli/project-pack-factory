# ASMS UI GUI-Up Classification Note 2026-03-26

## Operator Rule

For the current ADF trajectory, stop classifying the case as `ASMS UI is down`
once the customer can do the following core GUI actions:

- navigate the devices tree
- click `REPORTS` and view a report
- optionally click `Analyze` and reach the analyze surface

At that point, the GUI is considered up for support-classification purposes.

## What Changes After That

If one of those later surfaces fails or does not produce the expected result:

- do not keep calling the case `GUI down`
- branch into a more specific problem set
- describe the case by the failing branch instead

Examples:

- device-content loading problem
- reports-view problem
- analyze-workflow problem

## Why This Matters For ADF

This keeps the `ASMS UI is down` playbook bounded around basic GUI
availability.

It prevents later device-content, report, or analyze failures from being mixed
back into the first usable-shell gate.
