# Codex Personal Assistant Template Pack

PackFactory-native template pack `codex-personal-assistant-template-pack`.

This is the reusable source line for Codex-native personal assistants.
Keep reusable assistant behavior, operator-model structure, and partnership
policy here. Save operator-specific goals, preferences, and local memory for
derived build-packs.

## Commands

```bash
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack --help
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack validate-project-pack --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack benchmark-smoke --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack show-profile --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack show-alignment --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack show-operator-intake --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack check-ambiguity --project-root . --scenario "I have a few ideas and maybe should do some side work today." --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack route-context --project-root . --topic goals --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack record-memory --project-root . --memory-id first-note --category preference --summary "The operator prefers concrete next steps." --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack record-operator-intake --project-root . --intake-id first-intake --category communication_pattern --summary "The operator wants clear, business-like guidance." --refine-profile-json '{"working_preferences":["Translate intent into concrete next steps."]}' --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack read-memory --project-root . --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack delete-memory --project-root . --memory-id first-note --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack bootstrap-workspace --project-root . --target-dir ./dist/exports/preview --output json
PYTHONPATH=src python3 -m codex_personal_assistant_template_pack doctor --project-root . --output json
```
