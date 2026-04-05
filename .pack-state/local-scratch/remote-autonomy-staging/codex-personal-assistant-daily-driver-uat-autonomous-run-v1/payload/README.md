# Codex Personal Assistant Daily Driver Build Pack

PackFactory build-pack `codex-personal-assistant-daily-driver-build-pack-v1`.

This is the current daily-driver runtime instance for the Codex personal
assistant line. The active baseline focuses on:

- assistant identity and mission
- operator profile and partnership policy
- local context routing
- relationship and restart-memory read and write
- portable workspace bootstrap
- small deterministic health checks

## Commands

```bash
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack --help
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack benchmark-smoke --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack show-profile --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack show-alignment --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack route-context --project-root . --topic goals --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack record-memory --project-root . --memory-id first-note --category preference --summary "The operator prefers concrete next steps." --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack read-memory --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack bootstrap-workspace --project-root . --target-dir ./dist/candidates/preview --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack doctor --project-root . --output json
```

## Human Testing

For user-facing testing on the staged remote workspace, use:

- `docs/specs/user-acceptance-playbook.md`
