## Deepen Dependency Checkpoint: same-window shell gate versus Metro bootstrap — 2026-03-28

Purpose:
Refine the earlier shell-versus-Metro comparison so support engineers compare one shell-transition minute instead of two independent tails.

What changed:
- The Step 4 shell-versus-Metro command in `runtime_baseline.py` now derives one shell-transition minute and shows the Apache shell gate and Metro bootstrap clues for that same minute.
- A dedicated Linux note now gives the stop rule directly in operator language.

Why this checkpoint matters:
- It makes the stop rule more defensible:
  - validation without `home.php` means pre-shell stop
  - `home.php` with missing or unhealthy same-minute Metro clues means Metro-backed home-shell stop
  - healthy on both sides means branch out of `GUI down`
- It is a tighter support checkpoint than two unrelated recent tails.

Plain-language conclusion:
`deepen_dependency_aware_playbooks` now has a stronger first-shell checkpoint. The ASMS UI playbook compares one same-window shell transition against the nearest Metro bootstrap evidence and states the support stop rule explicitly.
