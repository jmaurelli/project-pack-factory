# ADF Human-Readable Command Standard

Date: 2026-03-29

## Summary

ADF now treats human-readable command output as a default operator-facing standard
for diagnostic playbooks. When a command supports a flag that makes output easier
for a support engineer to scan quickly, that flag should be used in the published
playbook unless a more precise machine-oriented unit is required for the decision.

## Adopted Rule

- Prefer flags like `-h`, `--human-readable`, and `--no-pager` when they improve
  live-session readability.
- Prefer output that avoids mental unit conversion during customer triage.
- Keep operator commands short and copy-paste friendly.

## Applied Example

The ASMS UI host-pressure check now uses:

```bash
uptime && free -h && df -h /
```

instead of the less readable MB-based variant.

## Review Surface

The current operator review page reflects this standard at:

- `http://10.167.2.151:18082/playbooks/asms-ui-is-down/`

## Supporting Implementation Note

The Starlight site generator now preserves `node_modules` during regeneration so
wording or command updates do not unnecessarily break the remote review surface
between edits and restarts.
