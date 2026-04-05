#!/bin/bash
set -euo pipefail
BUNDLE_ROOT=".pack-state/delegated-codex-runs/asms-home-shell-config-observe-v1"
PROMPT_PATH=".pack-state/delegated-codex-runs/asms-home-shell-config-observe-v1/codex-prompt.txt"
LOG_PATH=".pack-state/delegated-codex-runs/asms-home-shell-config-observe-v1/codex-launch.log"
mkdir -p "$BUNDLE_ROOT/artifacts"
if command -v pkill >/dev/null 2>&1; then
  pkill -f 'codex exec .*codex-prompt.txt' || true
fi
if command -v timeout >/dev/null 2>&1; then
  timeout 900 codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox - < "$PROMPT_PATH" >> "$LOG_PATH" 2>&1
else
  codex exec --skip-git-repo-check --dangerously-bypass-approvals-and-sandbox - < "$PROMPT_PATH" >> "$LOG_PATH" 2>&1
fi
