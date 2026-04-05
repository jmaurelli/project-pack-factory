## Summary

The `adf-dev` contract-safe shell-versus-Metro v3 slice succeeded as the first remote checkpoint that returned a concrete support-useful evidence minute instead of a measurement-only boundary.

## Exact checkpoint

- Evidence window: `2026-03-26 05:29:53-05:29:56 EDT`
- Shell transition: `SuiteLoginSessionValidation.php -> /afa/php/home.php`
- Same-window Metro clues: Metro `config` and `session/extend` activity from the preserved same-session request-correlation bundle
- Support stop-point judgment: if the shell transition reaches `home.php` and the same-window Metro clues are present, stop calling the case top-level `GUI down` and branch into a later shell or content issue instead

## Control-plane outcome

- The remote run wrote `run-summary.json`, `loop-events.jsonl`, and `adf-remote-checkpoint-bundle.json` under the staged run root
- The exported runtime-evidence bundle existed on `adf-dev`, but `execution-manifest.json` was missing, so the first pullback failed
- `tools/pull_remote_runtime_evidence.py` was updated to recover a finished export bundle when `execution-manifest.json` is absent but a matching runtime-evidence bundle is present
- `tools/import_external_runtime_evidence.py` was updated so canonical import accepts `artifacts/adf-remote-checkpoint-bundle.json`

## Residual gap

The imported bundle now preserves the checkpoint artifact itself, but it still does not carry the delegated target-bundle evidence files named inside the checkpoint bundle. That is a narrower later autonomy/export-completeness follow-up, not the blocker for proving this contract-safe slice.
