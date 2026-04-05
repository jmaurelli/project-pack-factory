#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACK_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PACK_ID="$(basename "$PACK_ROOT")"

SCHEDULE="${1:-${BACKUP_SCHEDULE:-17 2 * * *}}"
BACKUP_SCRIPT="$PACK_ROOT/tools/backup_remote_pack.sh"
LOG_DIR="${BACKUP_LOG_DIR:-$HOME/packfactory-backups/$PACK_ID/logs}"
MARKER_BEGIN="# BEGIN packfactory-${PACK_ID}-backup"
MARKER_END="# END packfactory-${PACK_ID}-backup"

mkdir -p "$LOG_DIR"

COMMAND="$BACKUP_SCRIPT >> \"$LOG_DIR/backup.log\" 2>&1"
printf -v CRON_LINE '%s /bin/bash -lc %q' "$SCHEDULE" "$COMMAND"

CURRENT_CRONTAB="$(mktemp)"
FILTERED_CRONTAB="$(mktemp)"
FINAL_CRONTAB="$(mktemp)"
trap 'rm -f "$CURRENT_CRONTAB" "$FILTERED_CRONTAB" "$FINAL_CRONTAB"' EXIT

if ! crontab -l >"$CURRENT_CRONTAB" 2>/dev/null; then
  : >"$CURRENT_CRONTAB"
fi

awk -v begin="$MARKER_BEGIN" -v end="$MARKER_END" '
  $0 == begin { skipping = 1; next }
  $0 == end { skipping = 0; next }
  !skipping { print }
' "$CURRENT_CRONTAB" >"$FILTERED_CRONTAB"

cat "$FILTERED_CRONTAB" >"$FINAL_CRONTAB"
{
  echo "$MARKER_BEGIN"
  echo "$CRON_LINE"
  echo "$MARKER_END"
} >>"$FINAL_CRONTAB"

crontab "$FINAL_CRONTAB"

printf '%s\n' "$CRON_LINE"
