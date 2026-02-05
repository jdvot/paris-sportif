#!/bin/bash
# =============================================================================
# WinRate AI - Database Backup Script
# =============================================================================
# This script creates backups of the Supabase PostgreSQL database.
#
# Usage:
#   ./scripts/backup-database.sh [options]
#
# Options:
#   --local       Store backup locally only (default)
#   --s3          Upload backup to S3
#   --gcs         Upload backup to Google Cloud Storage
#   --retention N Keep last N backups (default: 30)
#
# Requirements:
#   - pg_dump (PostgreSQL client)
#   - aws cli (for S3 uploads)
#   - gcloud cli (for GCS uploads)
#
# Environment variables:
#   DATABASE_URL      - Supabase PostgreSQL connection string
#   BACKUP_S3_BUCKET  - S3 bucket for backups (optional)
#   BACKUP_GCS_BUCKET - GCS bucket for backups (optional)
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_RETENTION=${BACKUP_RETENTION:-30}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Default options
UPLOAD_S3=false
UPLOAD_GCS=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --s3)
            UPLOAD_S3=true
            shift
            ;;
        --gcs)
            UPLOAD_GCS=true
            shift
            ;;
        --retention)
            BACKUP_RETENTION="$2"
            shift 2
            ;;
        --local)
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check for required environment variables
if [[ -z "${DATABASE_URL:-}" ]]; then
    log_error "DATABASE_URL environment variable is not set"
    log_info "Set DATABASE_URL to your Supabase PostgreSQL connection string"
    log_info "Example: export DATABASE_URL='postgresql://postgres:password@db.xxx.supabase.co:5432/postgres'"
    exit 1
fi

# Check for pg_dump
if ! command -v pg_dump &> /dev/null; then
    log_error "pg_dump command not found. Please install PostgreSQL client."
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"
log_info "Backup directory: $BACKUP_DIR"

# Generate backup filename
BACKUP_FILENAME="winrate_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"

# Create backup
log_info "Starting database backup..."
log_info "Timestamp: $TIMESTAMP"

if pg_dump "$DATABASE_URL" \
    --no-owner \
    --no-privileges \
    --format=plain \
    --clean \
    --if-exists \
    | gzip > "$BACKUP_PATH"; then

    BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
    log_info "Backup created successfully: $BACKUP_FILENAME ($BACKUP_SIZE)"
else
    log_error "Backup failed!"
    rm -f "$BACKUP_PATH"
    exit 1
fi

# Upload to S3 if requested
if [[ "$UPLOAD_S3" == "true" ]]; then
    if [[ -z "${BACKUP_S3_BUCKET:-}" ]]; then
        log_error "BACKUP_S3_BUCKET environment variable is not set"
        exit 1
    fi

    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found. Please install aws-cli."
        exit 1
    fi

    log_info "Uploading to S3: s3://${BACKUP_S3_BUCKET}/${BACKUP_FILENAME}"
    if aws s3 cp "$BACKUP_PATH" "s3://${BACKUP_S3_BUCKET}/${BACKUP_FILENAME}"; then
        log_info "S3 upload successful"
    else
        log_error "S3 upload failed"
        exit 1
    fi
fi

# Upload to GCS if requested
if [[ "$UPLOAD_GCS" == "true" ]]; then
    if [[ -z "${BACKUP_GCS_BUCKET:-}" ]]; then
        log_error "BACKUP_GCS_BUCKET environment variable is not set"
        exit 1
    fi

    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI not found. Please install Google Cloud SDK."
        exit 1
    fi

    log_info "Uploading to GCS: gs://${BACKUP_GCS_BUCKET}/${BACKUP_FILENAME}"
    if gcloud storage cp "$BACKUP_PATH" "gs://${BACKUP_GCS_BUCKET}/${BACKUP_FILENAME}"; then
        log_info "GCS upload successful"
    else
        log_error "GCS upload failed"
        exit 1
    fi
fi

# Cleanup old backups (local)
log_info "Cleaning up old backups (keeping last $BACKUP_RETENTION)..."
cd "$BACKUP_DIR"
ls -t winrate_backup_*.sql.gz 2>/dev/null | tail -n +$((BACKUP_RETENTION + 1)) | xargs -r rm -f
REMAINING_BACKUPS=$(ls -1 winrate_backup_*.sql.gz 2>/dev/null | wc -l)
log_info "Local backups remaining: $REMAINING_BACKUPS"

# Verify backup integrity
log_info "Verifying backup integrity..."
if gzip -t "$BACKUP_PATH" 2>/dev/null; then
    log_info "Backup integrity check: PASSED"
else
    log_error "Backup integrity check: FAILED"
    exit 1
fi

# Summary
echo ""
log_info "========================================="
log_info "Backup completed successfully!"
log_info "========================================="
log_info "File: $BACKUP_PATH"
log_info "Size: $BACKUP_SIZE"
log_info "Timestamp: $TIMESTAMP"
[[ "$UPLOAD_S3" == "true" ]] && log_info "S3: s3://${BACKUP_S3_BUCKET}/${BACKUP_FILENAME}"
[[ "$UPLOAD_GCS" == "true" ]] && log_info "GCS: gs://${BACKUP_GCS_BUCKET}/${BACKUP_FILENAME}"
echo ""

exit 0
