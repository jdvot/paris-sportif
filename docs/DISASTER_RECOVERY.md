# Disaster Recovery Runbook - WinRate AI

## Overview

This document outlines the disaster recovery procedures for the WinRate AI platform. It covers database backups, restoration procedures, and incident response protocols.

## Table of Contents

1. [Backup Strategy](#backup-strategy)
2. [Backup Procedures](#backup-procedures)
3. [Restoration Procedures](#restoration-procedures)
4. [Disaster Scenarios](#disaster-scenarios)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [Testing Schedule](#testing-schedule)

---

## Backup Strategy

### Overview

| Component | Backup Method | Frequency | Retention | Location |
|-----------|--------------|-----------|-----------|----------|
| PostgreSQL (Supabase) | pg_dump | Daily | 30 days | Local + S3/GCS |
| User uploads | Supabase Storage | Real-time | 90 days | Supabase CDN |
| ML Models | Git + S3 | On change | Indefinite | Git LFS + S3 |
| Configuration | Git | On change | Indefinite | GitHub |

### Data Classification

| Data Type | Priority | RTO | RPO |
|-----------|----------|-----|-----|
| User accounts | Critical | 1 hour | 1 hour |
| Predictions history | High | 4 hours | 24 hours |
| ML model weights | Medium | 24 hours | 7 days |
| Analytics/logs | Low | 48 hours | 7 days |

**RTO** = Recovery Time Objective (maximum downtime)
**RPO** = Recovery Point Objective (maximum data loss)

---

## Backup Procedures

### Automated Daily Backup

The `backup-database.sh` script runs daily via cron or GitHub Actions.

```bash
# Manual backup (local)
./scripts/backup-database.sh

# Backup with S3 upload
./scripts/backup-database.sh --s3

# Backup with GCS upload
./scripts/backup-database.sh --gcs

# Custom retention (keep 60 backups)
./scripts/backup-database.sh --retention 60
```

### Environment Setup

```bash
# Required environment variables
export DATABASE_URL="postgresql://postgres:PASSWORD@db.xxx.supabase.co:5432/postgres"

# Optional for cloud uploads
export BACKUP_S3_BUCKET="winrate-backups"
export BACKUP_GCS_BUCKET="winrate-backups"
```

### GitHub Actions Automation

Add to `.github/workflows/backup.yml`:

```yaml
name: Database Backup

on:
  schedule:
    - cron: '0 3 * * *'  # Daily at 3 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install PostgreSQL client
        run: sudo apt-get install -y postgresql-client

      - name: Run backup
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
          BACKUP_S3_BUCKET: ${{ secrets.BACKUP_S3_BUCKET }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          chmod +x ./scripts/backup-database.sh
          ./scripts/backup-database.sh --s3
```

### Supabase PITR (Point-in-Time Recovery)

For Pro/Team plans, enable PITR in Supabase Dashboard:

1. Go to **Project Settings** > **Database**
2. Enable **Point-in-Time Recovery**
3. Configure retention period (7-28 days)

PITR allows recovery to any point within the retention window.

---

## Restoration Procedures

### Quick Restore from Local Backup

```bash
# List available backups
ls -la backups/

# Restore latest backup
./scripts/restore-database.sh backups/winrate_backup_YYYYMMDD_HHMMSS.sql.gz

# Dry run (preview without changes)
./scripts/restore-database.sh backups/winrate_backup_YYYYMMDD_HHMMSS.sql.gz --dry-run

# Force restore (skip confirmation)
./scripts/restore-database.sh backups/winrate_backup_YYYYMMDD_HHMMSS.sql.gz --force

# Restore to different database
./scripts/restore-database.sh backups/winrate_backup_YYYYMMDD_HHMMSS.sql.gz \
  --target-url "postgresql://postgres:pass@new-db.supabase.co:5432/postgres"
```

### Restore from S3

```bash
# Download backup from S3
aws s3 cp s3://winrate-backups/winrate_backup_20260203_120000.sql.gz ./

# Restore
./scripts/restore-database.sh winrate_backup_20260203_120000.sql.gz
```

### Restore from Supabase PITR

1. Go to Supabase Dashboard > **Database** > **Backups**
2. Select **Point-in-Time Recovery**
3. Choose the target timestamp
4. Click **Restore**
5. Wait for restoration (can take 10-30 minutes)

### Post-Restore Checklist

- [ ] Verify user authentication works
- [ ] Check prediction history loads correctly
- [ ] Verify ML model data integrity
- [ ] Test API endpoints return correct data
- [ ] Check frontend displays latest data
- [ ] Verify subscription/payment status (if applicable)

---

## Disaster Scenarios

### Scenario 1: Accidental Data Deletion

**Severity**: Medium
**RTO**: 1 hour

1. Identify the scope of deletion
2. Stop write operations if ongoing
3. Restore from latest backup OR use PITR to specific timestamp
4. Verify data integrity
5. Resume operations

### Scenario 2: Database Corruption

**Severity**: High
**RTO**: 2 hours

1. Take database offline (update DNS/maintenance mode)
2. Create backup of corrupted state for analysis
3. Restore from last known good backup
4. Run data validation scripts
5. Resume operations
6. Post-incident analysis

### Scenario 3: Complete Supabase Outage

**Severity**: Critical
**RTO**: 4 hours

1. Activate maintenance mode on frontend
2. Spin up new Supabase project OR alternative PostgreSQL
3. Restore from S3/GCS backup
4. Update environment variables
5. Redeploy backend services
6. Verify all integrations
7. Resume operations

### Scenario 4: Security Breach

**Severity**: Critical
**RTO**: Immediate containment

1. **Contain**: Revoke all API keys and tokens
2. **Assess**: Determine scope of breach
3. **Rotate**: Generate new credentials
4. **Restore**: If data compromised, restore from pre-breach backup
5. **Notify**: Inform affected users if required
6. **Document**: Full incident report

---

## Monitoring & Alerting

### Backup Monitoring

Set up alerts for:

- [ ] Backup job failure (Slack/email notification)
- [ ] Backup size anomaly (>50% change from previous)
- [ ] Backup age > 25 hours (missing daily backup)
- [ ] S3/GCS upload failure

### Database Health Monitoring

Monitor via Supabase Dashboard or external tools:

- Connection pool utilization
- Query performance (slow query log)
- Storage utilization
- Replication lag (if applicable)

### Example Alert (Slack Webhook)

```bash
# Add to backup script on failure
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"ALERT: WinRate AI database backup failed!"}' \
  $SLACK_WEBHOOK_URL
```

---

## Testing Schedule

### Quarterly Restore Test

Every 3 months, perform a full restore test:

1. Create isolated test environment
2. Restore from production backup
3. Verify data integrity
4. Test critical user flows
5. Document results and timing

### Annual DR Drill

Once per year, simulate full disaster recovery:

1. Pretend production is unavailable
2. Follow runbook procedures
3. Time the recovery process
4. Identify bottlenecks
5. Update documentation

### Test Log

| Date | Test Type | Duration | Result | Notes |
|------|-----------|----------|--------|-------|
| YYYY-MM-DD | Quarterly Restore | XX min | Pass/Fail | Notes |

---

## Contact Information

### Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| Tech Lead | TBD | email@company.com |
| DevOps | TBD | email@company.com |
| Supabase Support | - | support@supabase.io |

### External Resources

- [Supabase Status](https://status.supabase.com)
- [Supabase Documentation](https://supabase.com/docs)
- [AWS S3 Console](https://s3.console.aws.amazon.com)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Claude | Initial documentation |
