## Deepen Dependency Checkpoint: FireFlow AFF route ownership — 2026-03-28

Purpose:
Record one small accepted `deepen_dependency_aware_playbooks` checkpoint so the task has a concrete content gain, not only autonomy-loop continuity evidence.

What changed:
- FireFlow step 2 in `runtime_baseline.py` now includes an operator-facing route-ownership check that compares the Apache-fronted `/FireFlow/api/session` path with the direct `aff-boot` `/aff/api/external/session` path on `1989`.

Why this checkpoint matters:
- It gives support engineers one clearer stop point before widening into later FireFlow workflow theory.
- It matches the existing AFF route-ownership note scaffolding already present in the playbook.
- It is a bounded dependency deepening step: one readable seam, one concrete comparison, one support-useful decision boundary.

Plain-language conclusion:
`deepen_dependency_aware_playbooks` is still in progress, but it now has one accepted checkpoint. The FireFlow AFF seam no longer stops at service-up and port-up only; it now asks the operator to prove Apache still owns the session hop into `aff-boot` before going deeper.
