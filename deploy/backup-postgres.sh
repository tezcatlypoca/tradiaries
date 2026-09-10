#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/tradiaries}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="${BACKUP_DIR}/tradiaries-${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"
pg_dump --format=custom --no-owner --file="${BACKUP_FILE}" "${DATABASE_URL}"
sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"
find "${BACKUP_DIR}" -type f -name 'tradiaries-*.dump*' -mtime "+${RETENTION_DAYS}" -delete

printf 'Backup created: %s\n' "${BACKUP_FILE}"
