# Quick Start: SQLite Tutorial Parity

**Feature**: 004-sqlitch-tutorial-parity  
**Purpose**: Validate that SQLitch can complete the full Sqitch SQLite tutorial

---

## Validation Scenarios

### Scenario 1: Project Initialization
**Goal**: Initialize a new SQLitch project with proper configuration

```bash
# Create project directory
mkdir flipr && cd flipr
git init .

# Initialize SQLitch project
sqlitch init flipr --uri https://github.com/example/flipr/ --engine sqlite

# Verify files created
ls -la  # Should see sqitch.conf, sqitch.plan, deploy/, revert/, verify/

# Configure user settings
sqlitch config --user user.name 'Test User'
sqlitch config --user user.email 'test@example.com'

# Verify configuration
cat sqitch.conf     # Should show [core] engine = sqlite
cat sqitch.plan     # Should show project pragmas
cat ~/.sqitch/sqitch.conf  # Should show user settings
```

**Success Criteria**:
- ✅ sqitch.conf created with correct engine
- ✅ sqitch.plan created with pragmas
- ✅ deploy/, revert/, verify/ directories created
- ✅ User config saved to ~/.sqitch/sqitch.conf

---

### Scenario 2: First Change - Users Table
**Goal**: Add, deploy, and verify first database change

```bash
# Add users table change
sqlitch add users -n 'Creates table to track our users.'

# Verify files created
ls deploy/   # Should see users.sql
ls revert/   # Should see users.sql
ls verify/   # Should see users.sql
cat sqitch.plan  # Should list users change

# Edit deploy/users.sql (manually add CREATE TABLE)
# Edit revert/users.sql (manually add DROP TABLE)
# Edit verify/users.sql (manually add SELECT query)

# Deploy to database
sqlitch deploy db:sqlite:flipr_test.db

# Verify deployment
sqlitch verify db:sqlite:flipr_test.db

# Check status
sqlitch status db:sqlite:flipr_test.db

# Verify database files
ls -la  # Should see flipr_test.db and sqitch.db
sqlite3 flipr_test.db '.tables'  # Should show users
```

**Success Criteria**:
- ✅ Three script files created with proper headers
- ✅ Plan file updated with change entry
- ✅ Registry database (sqitch.db) created
- ✅ Change deployed to flipr_test.db
- ✅ Verify script passes
- ✅ Status shows deployed change

---

### Scenario 3: Dependent Change - Flips Table
**Goal**: Add change with dependency on previous change

```bash
# Add flips table with dependency
sqlitch add flips --requires users -n 'Adds table for storing flips.'

# Verify plan shows dependency
cat sqitch.plan  # Should show: flips [users]

# Edit scripts (add CREATE TABLE referencing users)

# Deploy
sqlitch deploy db:sqlite:flipr_test.db

# Verify
sqlitch verify db:sqlite:flipr_test.db

# Check tables
sqlite3 flipr_test.db '.tables'  # Should show users, flips
```

**Success Criteria**:
- ✅ Dependency recorded in plan file
- ✅ Deploy validates dependency exists
- ✅ Foreign key constraints work
- ✅ Both tables exist in database

---

### Scenario 4: View Creation - UserFlips
**Goal**: Create database view depending on multiple tables

```bash
# Add view with multiple dependencies
sqlitch add userflips --requires users --requires flips \
  -n 'Creates userflips view.'

# Edit deploy script (add CREATE VIEW)
# Edit revert script (add DROP VIEW)
# Edit verify script (add SELECT from view)

# Deploy
sqlitch deploy db:sqlite:flipr_test.db

# Verify
sqlitch verify db:sqlite:flipr_test.db

# Check view exists
sqlite3 flipr_test.db '.schema userflips'
```

**Success Criteria**:
- ✅ Multiple dependencies recorded
- ✅ View created successfully
- ✅ View query works
- ✅ Verify script validates view structure

---

### Scenario 5: Tagging Release - v1.0.0-dev1
**Goal**: Tag current state as release version

```bash
# Create release tag
sqlitch tag v1.0.0-dev1 -n 'Tag v1.0.0-dev1.'

# Verify plan
cat sqitch.plan  # Should show @v1.0.0-dev1 tag after userflips

# Deploy tag (should be no-op if already deployed)
sqlitch deploy db:sqlite:flipr_test.db

# Check status
sqlitch status db:sqlite:flipr_test.db  # Should show tag
```

**Success Criteria**:
- ✅ Tag added to plan file
- ✅ Tag recorded in registry
- ✅ Status displays tag information

---

### Scenario 6: Revert Changes
**Goal**: Revert deployed changes and re-deploy

```bash
# Check current status
sqlitch status db:sqlite:flipr_test.db

# Revert one change
sqlitch revert db:sqlite:flipr_test.db --to @HEAD^

# Verify change reverted
sqlitch status db:sqlite:flipr_test.db  # Should show one less change
sqlite3 flipr_test.db '.tables'  # Verify table/view removed

# Re-deploy
sqlitch deploy db:sqlite:flipr_test.db

# Verify restored
sqlitch status db:sqlite:flipr_test.db
```

**Success Criteria**:
- ✅ Revert script executes successfully
- ✅ Registry updated (change removed)
- ✅ Database object removed
- ✅ Re-deploy works correctly

---

### Scenario 7: Change History
**Goal**: View deployment history log

```bash
# Show all events
sqlitch log db:sqlite:flipr_test.db

# Show events for specific change
sqlitch log db:sqlite:flipr_test.db users

# Verify log shows:
# - Deploy events
# - Revert events (if any)
# - Timestamps
# - User information
```

**Success Criteria**:
- ✅ Log displays all deployment events
- ✅ Events shown in chronological order
- ✅ Change-specific filtering works
- ✅ Output format matches Sqitch

---

### Scenario 8: Rework Change - Add Column
**Goal**: Create modified version of existing change

```bash
# Create second dev tag
sqlitch tag v1.0.0-dev2 -n 'Tag before rework.'

# Rework the userflips view
sqlitch rework userflips -n 'Add twitter column to userflips view.'

# Verify new script files created
ls deploy/  # Should see userflips@v1.0.0-dev2.sql
ls revert/  # Should see userflips@v1.0.0-dev2.sql
ls verify/  # Should see userflips@v1.0.0-dev2.sql

# Edit new scripts (modify view definition)

# Deploy reworked change
sqlitch deploy db:sqlite:flipr_test.db

# Verify new version
sqlitch verify db:sqlite:flipr_test.db
sqlite3 flipr_test.db '.schema userflips'  # Should show new column
```

**Success Criteria**:
- ✅ Reworked scripts created with @tag suffix
- ✅ Plan file shows rework entry
- ✅ Original scripts preserved
- ✅ New version deploys over old version
- ✅ Database object updated correctly

---

## Full Tutorial Test Script

```bash
#!/bin/bash
# Complete tutorial validation script

set -e  # Exit on error

echo "=== SQLitch Tutorial Validation ==="

# Setup
rm -rf /tmp/flipr_tutorial
mkdir -p /tmp/flipr_tutorial
cd /tmp/flipr_tutorial

# Scenario 1: Initialize
echo ">>> Scenario 1: Initialize project"
git init .
sqlitch init flipr --uri https://github.com/example/flipr/ --engine sqlite
sqlitch config --user user.name 'Tutorial Test'
sqlitch config --user user.email 'test@tutorial.local'

# Scenario 2: First change
echo ">>> Scenario 2: Add users table"
sqlitch add users -n 'Creates table to track our users.'
cat > deploy/users.sql << 'EOF'
-- Deploy flipr:users to sqlite

BEGIN;

CREATE TABLE users (
    nickname  TEXT      PRIMARY KEY,
    password  TEXT      NOT NULL,
    fullname  TEXT      NOT NULL,
    twitter   TEXT      NOT NULL,
    timestamp DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
EOF

cat > revert/users.sql << 'EOF'
-- Revert flipr:users from sqlite

BEGIN;

DROP TABLE users;

COMMIT;
EOF

cat > verify/users.sql << 'EOF'
-- Verify flipr:users

SELECT nickname, password, fullname, twitter
  FROM users
 WHERE 0;
EOF

sqlitch deploy db:sqlite:flipr_test.db
sqlitch verify db:sqlite:flipr_test.db
sqlitch status db:sqlite:flipr_test.db

# Scenario 3: Dependent change
echo ">>> Scenario 3: Add flips table"
sqlitch add flips --requires users -n 'Adds table for storing flips.'
# ... (similar script editing)
sqlitch deploy db:sqlite:flipr_test.db
sqlitch verify db:sqlite:flipr_test.db

# Continue with scenarios 4-8...

echo "=== All scenarios completed successfully! ==="
```

---

## Success Metrics

To consider Feature 004 complete, ALL scenarios must:
1. Execute without errors
2. Produce output matching Sqitch (within acceptable variations)
3. Create correct database state (verified via sqlite3 queries)
4. Maintain valid plan and registry databases
5. Pass automated tests with ≥90% coverage

---

## Common Issues & Troubleshooting

### Issue: Registry database not created
**Symptoms**: Error about missing sqitch.db
**Fix**: Ensure deploy command creates registry on first run

### Issue: Deploy script fails
**Symptoms**: SQL syntax error
**Fix**: Check transaction wrapper, validate SQL

### Issue: Dependency not satisfied
**Symptoms**: Error about missing required change
**Fix**: Verify plan order, ensure dependencies deployed first

### Issue: Verify script fails
**Symptoms**: Table/column not found
**Fix**: Check deploy executed successfully, verify script matches deployed state

### Issue: Revert leaves orphaned data
**Symptoms**: Objects still exist after revert
**Fix**: Ensure revert script properly drops all deployed objects

---

## Notes

- All scenarios should work with both relative and absolute database paths
- Registry database (sqitch.db) should be reusable across multiple target databases
- Plan file should remain valid throughout all operations
- Git operations (commit, branch, merge) are manual and not validated by SQLitch
- Timestamp variations are acceptable in log output
- User-specific paths in config are acceptable variations

