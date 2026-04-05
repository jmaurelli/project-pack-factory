#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PACK_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
PACK_ID="$(basename "$PACK_ROOT")"

BACKUP_ROOT="${BACKUP_ROOT:-$HOME/packfactory-backups/$PACK_ID}"
RETENTION_COUNT="${RETENTION_COUNT:-7}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
HOSTNAME_VALUE="$(hostname 2>/dev/null || echo unknown-host)"

mkdir -p "$BACKUP_ROOT"

TEMP_ARCHIVE="$(mktemp "$BACKUP_ROOT/.${PACK_ID}-${TIMESTAMP}-XXXXXX.tar.gz")"
ARCHIVE_PATH="$BACKUP_ROOT/${PACK_ID}-${TIMESTAMP}.tar.gz"
LATEST_METADATA_PATH="$BACKUP_ROOT/${PACK_ID}-latest.json"

tar \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='.ruff_cache' \
  --exclude='.mypy_cache' \
  --exclude='.venv' \
  --exclude='*.egg-info' \
  -czf "$TEMP_ARCHIVE" \
  -C "$(dirname "$PACK_ROOT")" \
  "$PACK_ID"

mv "$TEMP_ARCHIVE" "$ARCHIVE_PATH"

ARCHIVE_SHA256=""
if command -v sha256sum >/dev/null 2>&1; then
  ARCHIVE_SHA256="$(sha256sum "$ARCHIVE_PATH" | awk '{print $1}')"
fi

cat >"$LATEST_METADATA_PATH" <<EOF
{
  "pack_id": "$PACK_ID",
  "created_at": "$TIMESTAMP",
  "hostname": "$HOSTNAME_VALUE",
  "archive_path": "$ARCHIVE_PATH",
  "archive_sha256": "$ARCHIVE_SHA256",
  "retention_count": $RETENTION_COUNT
}
EOF

if [[ "$RETENTION_COUNT" =~ ^[0-9]+$ ]] && (( RETENTION_COUNT > 0 )); then
  mapfile -t ARCHIVES < <(
    find "$BACKUP_ROOT" -maxdepth 1 -type f -name "${PACK_ID}-*.tar.gz" -printf '%f\n' | sort -r
  )
  if (( ${#ARCHIVES[@]} > RETENTION_COUNT )); then
    for OLD_ARCHIVE in "${ARCHIVES[@]:RETENTION_COUNT}"; do
      rm -f "$BACKUP_ROOT/$OLD_ARCHIVE"
    done
  fi
fi

printf '%s\n' "$ARCHIVE_PATH"
