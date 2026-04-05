## Deepen Dependency Checkpoint: later content-branch classification — 2026-03-28

Purpose:
Record one more small accepted `deepen_dependency_aware_playbooks` checkpoint that helps support engineers branch out of top-level `GUI down` at the right time.

What changed:
- ASMS UI Step 4 in `runtime_baseline.py` now includes an operator-facing check for later content-branch markers such as `GET_REPORTS`, `GET_POLICY_TAB`, `GET_DEVICE_POLICY`, `GET_MONITORING_CHANGES`, and `GET_ANALYSIS_OPTIONS`.
- A dedicated Linux note now states that `tree/create` alone is still shell-context evidence, but later content markers mean the case has already moved beyond top-level `GUI down`.

Why this checkpoint matters:
- It turns an existing advisory rule into a first-class playbook stop rule.
- It is more support-friendly than keeping the engineer inside shell or Metro theory after the customer has clearly reached later content.
- It keeps the ASMS UI playbook fail-closed: top-level GUI outages stop at the first usable shell, while later content failures branch into narrower workflows.

Plain-language conclusion:
`deepen_dependency_aware_playbooks` is still in progress, but the ASMS UI playbook now has a clearer branch-out checkpoint. Once later content markers appear after the first usable shell, the operator should stop calling the case `GUI down` and move to the narrower failing workflow.
