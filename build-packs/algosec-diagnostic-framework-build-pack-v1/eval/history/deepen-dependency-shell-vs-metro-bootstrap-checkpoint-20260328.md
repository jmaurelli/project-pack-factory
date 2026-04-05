## Deepen Dependency Checkpoint: shell gate versus Metro bootstrap — 2026-03-28

Purpose:
Record one more small accepted `deepen_dependency_aware_playbooks` checkpoint on the ASMS UI path.

What changed:
- Step 4 in `runtime_baseline.py` now includes a bounded comparison check between the shell gate and the nearest Metro bootstrap clues.
- The new command compares Apache lines for `SuiteLoginSessionValidation.php` and `/afa/php/home.php` against nearby Metro lines such as `/afa/getStatus`, `config`, `session/extend`, and `config/all/noauth`.

Why this checkpoint matters:
- It gives support engineers a cleaner stop rule:
  - if `SuiteLoginSessionValidation.php` appears but `/afa/php/home.php` does not, stop before the shell
  - if `/afa/php/home.php` appears but the nearby Metro bootstrap clues are missing or unhealthy, stop on the Metro-backed shell path
  - if both are healthy, branch out of `GUI down`
- It keeps the dependency deepening bounded and support-useful instead of widening into generic Metro theory.

Plain-language conclusion:
`deepen_dependency_aware_playbooks` is still active, but the ASMS UI path now has a clearer first-shell comparison checkpoint. The playbook can separate a pre-shell stop from a Metro-backed post-shell stop more explicitly than before.
