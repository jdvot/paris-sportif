#!/bin/bash
# =============================================================================
# WinRate AI - Database Restore Script
# =============================================================================
# This script restores a Supabase PostgreSQL database from a backup.
#
# Usage:
#   ./scripts/restore-database.sh <backup_file> [options]
#
# Options:
#   --dry-run     Show what would be restored without making changes
#   --force       Skip confirmation prompt
#   --target-url  Restore to a different database (default: DATABASE_URL)
#
# Requirements:
#   - psql (PostgreSQL client)
#
# WARNING: This script will DROP and recreate all tables in the target database!
# =============================================================================

set -euo pipefail

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
DRY_RUN=false
FORCE=false
TARGET_URL=""
BACKUP_FILE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --target-url)
            TARGET_URL="$2"
            shift 2
            ;;
        -*)
            log_error "Unknown option: $1"
            exit 1
            ;;
        *)
            if [[ -z "$BACKUP_FILE" ]]; then
                BACKUP_FILE="$1"
            else
                log_error "Too many arguments"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate backup file argument
if [[ -z "$BACKUP_FILE" ]]; then
    log_error "Usage: $0 <backup_file> [--dry-run] [--force] [--target-url URL]"
    exit 1
fi

# Check if backup file exists
if [[ ! -f "$BACKUP_FILE" ]]; then
    log_error "Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Determine target database
if [[ -z "$TARGET_URL" ]]; then
    TARGET_URL="${DATABASE_URL:-}"
fi

if [[ -z "$TARGET_URL" ]]; then
    log_error "No database URL specified. Set DATABASE_URL or use --target-url"
    exit 1
fi

# Check for psql
if ! command -v psql &> /dev/null; then
    log_error "psql command not found. Please install PostgreSQL client."
    exit 1
fi

# Extract connection info for display (hide password)
DISPLAY_URL=$(echo "$TARGET_URL" | sed 's/:\/\/[^:]*:[^@]*@/:\/\/***:***@/')

# Show restore plan
echo ""
log_warn "========================================="
log_warn "DATABASE RESTORE - DESTRUCTIVE OPERATION"
log_warn "========================================="
log_info "Backup file: $BACKUP_FILE"
log_info "Target database: $DISPLAY_URL"
log_info "Dry run: $DRY_RUN"
echo ""

# Get backup info
if [[ "$BACKUP_FILE" == *.gz ]]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    TABLE_COUNT=$(gzip -dc "$BACKUP_FILE" | grep -c "^CREATE TABLE" || echo "0")
    log_info "Compressed backup size: $BACKUP_SIZE"
else
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    TABLE_COUNT=$(grep -c "^CREATE TABLE" "$BACKUP_FILE" || echo "0")
    log_info "Backup size: $BACKUP_SIZE"
fi
log_info "Tables to restore: ~$TABLE_COUNT"

# Confirmation prompt
if [[ "$FORCE" != "true" && "$DRY_RUN" != "true" ]]; then
    echo ""
    log_warn "This will DROP and RECREATE all tables in the target database!"
    read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM
    if [[ "$CONFIRM" != "yes" ]]; then
        log_info "Restore cancelled."
        exit 0
    fi
fi

# Dry run mode
if [[ "$DRY_RUN" == "true" ]]; then
    log_info "Dry run mode - no changes will be made"
    log_info "Would restore from: $BACKUP_FILE"
    log_info "Would restore to: $DISPLAY_URL"
    echo ""
    log_info "First 50 lines of backup:"
    echo "---"
    if [[ "$BACKUP_FILE" == *.gz ]]; then
        gzip -dc "$BACKUP_FILE" | head -50
    else
        head -50 "$BACKUP_FILE"
    fi
    echo "---"
    exit 0
fi

# Perform restore
log_info "Starting database restore..."
START_TIME=$(date +%s)

if [[ "$BACKUP_FILE" == *.gz ]]; then
    # Compressed backup
    if gzip -dc "$BACKUP_FILE" | psql "$TARGET_URL" --quiet --set ON_ERROR_STOP=1 2>&1; then
        log_info "Restore completed successfully!"
    else
        log_error "Restore failed!"
        exit 1
    fi
else
    # Plain SQL backup
    if psql "$TARGET_URL" --quiet --set ON_ERROR_STOP=1 < "$BACKUP_FILE" 2>&1; then
        log_info "Restore completed successfully!"
    else
        log_error "Restore failed!"
        exit 1
    fi
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Verify restore
log_info "Verifying restored database..."
TABLE_COUNT_RESTORED=$(psql "$TARGET_URL" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | tr -d ' ')
log_info "Tables in restored database: $TABLE_COUNT_RESTORED"

# Summary
echo ""
log_info "========================================="
log_info "Restore completed successfully!"
log_info "========================================="
log_info "Backup file: $BACKUP_FILE"
log_info "Target database: $DISPLAY_URL"
log_info "Duration: ${DURATION}s"
log_info "Tables restored: $TABLE_COUNT_RESTORED"
echo ""

exit 0
