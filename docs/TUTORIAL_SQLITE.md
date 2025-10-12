# SQLitch Tutorial: SQLite Change Management

A comprehensive tutorial for using SQLitch to manage database changes on SQLite.

## Overview

This tutorial explains how to create a SQLitch-enabled SQLite project, use Git for deployment planning, and collaborate with other developers to keep database changes in sync and properly ordered.

We'll build a fictional anti-social networking site called **Flipr** from scratch. All examples use [Git](https://git-scm.com/) as the VCS and [SQLite](https://www.sqlite.org/) as the storage engine.

> **Note**: This tutorial is adapted from the Sqitch tutorial. SQLitch is a Python implementation that maintains behavioral parity with Sqitch while providing a Pythonic interface.

## Prerequisites

- Python 3.11 or higher
- SQLite3 command-line client
- Git
- SQLitch installed (`pip install sqlitch`)

## Table of Contents

1. [Starting a New Project](#starting-a-new-project)
2. [Our First Change](#our-first-change)
3. [Trust, But Verify](#trust-but-verify)
4. [Status, Revert, Log, Repeat](#status-revert-log-repeat)
5. [On Target](#on-target)
6. [Deploy with Dependency](#deploy-with-dependency)
7. [View to a Thrill](#view-to-a-thrill)
8. [Ship It!](#ship-it)
9. [Making a Hash of Things](#making-a-hash-of-things)
10. [In Place Changes](#in-place-changes)

---

## Starting a New Project

First, create a source code repository:

```bash
mkdir flipr
cd flipr
git init .
touch README.md
git add .
git commit -m 'Initialize project, add README.'
```

Now initialize SQLitch. Every SQLitch project needs a name and optionally a unique URI (recommended for preventing deployment conflicts):

```bash
sqlitch init flipr --uri https://github.com/yourname/flipr --engine sqlite
```

Output:
```
Created sqitch.conf
Created sqitch.plan
Created deploy/
Created revert/
Created verify/
```

### Configuration File

Inspect the generated `sqitch.conf`:

```bash
cat sqitch.conf
```

```ini
[core]
    engine = sqlite
    # plan_file = sqitch.plan
    # top_dir = .
# [engine "sqlite"]
    # target = db:sqlite:
    # registry = sqitch
    # client = sqlite3
```

SQLitch picked up the `--engine sqlite` option and configured the appropriate engine settings.

### User Configuration

Set your user information (applies to all projects):

```bash
sqlitch config --user user.name 'Your Name'
sqlitch config --user user.email 'you@example.com'
```

If `sqlite3` is not in your PATH, configure its location:

```bash
sqlitch config --user engine.sqlite.client /usr/bin/sqlite3
```

Check your user configuration:

```bash
cat ~/.sqitch/sqitch.conf
```

### The Plan File

Inspect the plan file:

```bash
cat sqitch.plan
```

```
%syntax-version=1.0.0
%project=flipr
%uri=https://github.com/yourname/flipr
```

The plan file tracks:
- **%syntax-version**: Ensures SQLitch can parse the plan format
- **%project**: Your project name
- **%uri**: Unique project identifier

Commit these initial files:

```bash
git add .
git commit -m 'Initialize SQLitch configuration.'
```

---

## Our First Change

Let's create a users table:

```bash
sqlitch add users -n 'Creates table to track our users.'
```

Output:
```
Created deploy/users.sql
Created revert/users.sql
Created verify/users.sql
Added "users" to sqitch.plan
```

The `add` command creates three scripts:
- **deploy**: Creates the table
- **revert**: Removes the table
- **verify**: Confirms the table exists

### Deploy Script

Edit `deploy/users.sql`:

```sql
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
```

### Revert Script

Edit `revert/users.sql`:

```sql
-- Revert flipr:users from sqlite

BEGIN;

DROP TABLE users;

COMMIT;
```

### Deploy the Change

Deploy using a [database URI](https://github.com/libwww-perl/uri-db/):

```bash
sqlitch deploy db:sqlite:flipr_test.db
```

Output:
```
Adding registry tables to db:sqlite:sqitch.db
Deploying changes to db:sqlite:flipr_test.db
  + users .. ok
```

SQLitch creates:
- **sqitch.db**: Registry database tracking deployment history
- **flipr_test.db**: Your application database

Verify the table exists:

```bash
sqlite3 flipr_test.db '.tables'
```

Output: `users`

---

## Trust, But Verify

Rather than manually checking tables after every deploy, use verify scripts.

Edit `verify/users.sql`:

```sql
-- Verify flipr:users on sqlite

BEGIN;

SELECT nickname, password, fullname, twitter
  FROM users
 WHERE 0;

ROLLBACK;
```

This query:
- Selects all columns (ensuring they exist)
- Uses `WHERE 0` (returns no rows but validates schema)
- Rolls back (doesn't modify data)

Run verification:

```bash
sqlitch verify db:sqlite:flipr_test.db
```

Output:
```
Verifying db:sqlite:flipr_test.db
  * users .. ok
Verify successful
```

### Testing Verify Failure

Temporarily break the verify script to test error handling:

```sql
-- Change users to users_nonesuch
SELECT nickname, password, timestamp
  FROM users_nonesuch
 WHERE 0;
```

Run verify:

```bash
sqlitch verify db:sqlite:flipr_test.db
```

Output:
```
Verifying db:sqlite:flipr_test.db
  * users .. Error: near line 5: no such table: users_nonesuch
# Verify script "verify/users.sql" failed.
not ok

Verify Summary Report
---------------------
Changes: 1
Errors:  1
Verify failed
```

**Don't forget to fix the table name!**

---

## Status, Revert, Log, Repeat

### Check Status

View deployment status:

```bash
sqlitch status db:sqlite:flipr_test.db
```

Output:
```
# On database db:sqlite:flipr_test.db
# Project:  flipr
# Change:   f30fe47f5f99501fb8d481e910d9112c5ac0a676
# Name:     users
# Deployed: 2025-10-12 10:26:59 -0800
# By:       Your Name <you@example.com>
# 
Nothing to deploy (up-to-date)
```

### Revert Changes

Test reverting:

```bash
sqlitch revert db:sqlite:flipr_test.db
```

Output:
```
Revert all changes from db:sqlite:flipr_test.db? [Yes]
  - users .. ok
```

Notes:
- Prompts for confirmation (use `-y` to skip)
- The `-` indicates removal

Verify the table is gone:

```bash
sqlite3 flipr_test.db '.tables'
```

(No output)

Check status:

```bash
sqlitch status db:sqlite:flipr_test.db
```

Output: `No changes deployed`

### View History

Even with nothing deployed, the log shows history:

```bash
sqlitch log db:sqlite:flipr_test.db
```

Output:
```
On database db:sqlite:flipr_test.db
Revert f30fe47f5f99501fb8d481e910d9112c5ac0a676
Name:      users
Committer: Your Name <you@example.com>
Date:      2025-10-12 10:53:25 -0800

    Creates table to track our users.

Deploy f30fe47f5f99501fb8d481e910d9112c5ac0a676
Name:      users
Committer: Your Name <you@example.com>
Date:      2025-10-12 10:26:59 -0800

    Creates table to track our users.
```

### Redeploy with Verification

Commit changes and redeploy with automatic verification:

```bash
echo '*.db' > .gitignore
git add .
git commit -m 'Add users table.'
sqlitch deploy db:sqlite:flipr_test.db --verify
```

Output:
```
Deploying changes to db:sqlite:flipr_test.db
  + users .. ok
```

---

## On Target

Typing `db:sqlite:flipr_test.db` repeatedly gets tedious. Let's configure a named target:

```bash
sqlitch target add flipr_test db:sqlite:flipr_test.db
```

Set it as the default:

```bash
sqlitch engine add sqlite flipr_test
```

Now commands use this target by default:

```bash
sqlitch status
```

Output:
```
# On database flipr_test
# Project:  flipr
# Change:   f30fe47f5f99501fb8d481e910d9112c5ac0a676
# Name:     users
# Deployed: 2025-10-12 10:57:55 -0800
# By:       Your Name <you@example.com>
# 
Nothing to deploy (up-to-date)
```

### Enable Automatic Verification

Configure SQLitch to always verify after deploying:

```bash
sqlitch config --bool deploy.verify true
sqlitch config --bool rebase.verify true
```

Commit the configuration:

```bash
git commit -am 'Set default target and always verify.'
```

---

## Deploy with Dependency

Add a table for status messages ("flips"):

```bash
sqlitch add flips --requires users -n 'Adds table for storing flips.'
```

Output:
```
Created deploy/flips.sql
Created revert/flips.sql
Created verify/flips.sql
Added "flips [users]" to sqitch.plan
```

Note the `--requires users` flag. This declares an explicit dependency.

### Deploy Script

Edit `deploy/flips.sql`:

```sql
-- Deploy flipr:flips to sqlite
-- requires: users

BEGIN;

CREATE TABLE flips (
    id        INTEGER   PRIMARY KEY AUTOINCREMENT,
    nickname  TEXT      NOT NULL REFERENCES users(nickname),
    body      TEXT      NOT NULL DEFAULT '' CHECK ( length(body) <= 180 ),
    timestamp DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
```

The `-- requires: users` comment documents the dependency (helpful for reference).

### Verify Script

Edit `verify/flips.sql`:

```sql
-- Verify flipr:flips on sqlite

BEGIN;

SELECT id, nickname, body, timestamp
  FROM flips
 WHERE 0;

ROLLBACK;
```

### Revert Script

Edit `revert/flips.sql`:

```sql
-- Revert flipr:flips from sqlite

BEGIN;

DROP TABLE flips;

COMMIT;
```

### Deploy and Test

Deploy:

```bash
sqlitch deploy
```

Output:
```
Deploying changes to flipr_test
  + flips .. ok
```

Verify both tables:

```bash
sqlitch verify
```

Output:
```
Verifying flipr_test
  * users .. ok
  * flips .. ok
Verify successful
```

Check status:

```bash
sqlitch status
```

Output:
```
# On database flipr_test
# Project:  flipr
# Change:   32ee57069c0d7fec52b6f86f453dc0c16bc1090a
# Name:     flips
# Deployed: 2025-10-12 11:02:51 -0800
# By:       Your Name <you@example.com>
# 
Nothing to deploy (up-to-date)
```

### Test Reverting

Revert to the previous change using symbolic references:

```bash
sqlitch revert --to @HEAD^ -y
```

Output:
```
Reverting changes to users from flipr_test
  - flips .. ok
```

Symbolic references:
- **@HEAD**: Last deployed change
- **@HEAD^**: Change before HEAD
- **@ROOT**: First change in plan

Verify only `users` remains:

```bash
sqlite3 flipr_test.db '.tables'
```

Output: `users`

Check status:

```bash
sqlitch status
```

Output:
```
# On database flipr_test
# Project:  flipr
# Change:   f30fe47f5f99501fb8d481e910d9112c5ac0a676
# Name:     users
# Deployed: 2025-10-12 10:57:55 -0800
# By:       Your Name <you@example.com>
# 
Undeployed change:
  * flips
```

### Commit and Redeploy

```bash
git add .
git commit -am 'Add flips table.'
sqlitch deploy
```

---

## View to a Thrill

Add a view combining users and flips:

```bash
sqlitch add userflips --requires users --requires flips \
    -n 'Creates the userflips view.'
```

Output:
```
Created deploy/userflips.sql
Created revert/userflips.sql
Created verify/userflips.sql
Added "userflips [users flips]" to sqitch.plan
```

### Deploy Script

Edit `deploy/userflips.sql`:

```sql
-- Deploy flipr:userflips to sqlite
-- requires: users
-- requires: flips

BEGIN;

CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, f.body, f.timestamp
  FROM users u
  JOIN flips f ON u.nickname = f.nickname;

COMMIT;
```

### Verify Script

Edit `verify/userflips.sql`:

```sql
-- Verify flipr:userflips on sqlite

BEGIN;

SELECT id, nickname, fullname, body, timestamp
  FROM userflips
 WHERE 0;

ROLLBACK;
```

### Revert Script

Edit `revert/userflips.sql`:

```sql
-- Revert flipr:userflips from sqlite

BEGIN;

DROP VIEW userflips;

COMMIT;
```

### Test Deploy, Revert, and Redeploy

```bash
sqlitch deploy
sqlitch revert -y
sqlitch deploy
```

Output:
```
Deploying changes to flipr_test
  + userflips .. ok
Reverting all changes from flipr_test
  - userflips .. ok
  - flips ...... ok
  - users ...... ok
Deploying changes to flipr_test
  + users ...... ok
  + flips ...... ok
  + userflips .. ok
```

Commit:

```bash
git add .
git commit -m 'Add the userflips view.'
```

---

## Ship It!

Tag the first development release:

```bash
sqlitch tag v1.0.0-dev1 -n 'Tag v1.0.0-dev1.'
git commit -am 'Tag the database with v1.0.0-dev1.'
git tag v1.0.0-dev1 -am 'Tag v1.0.0-dev1'
```

Output:
```
Tagged "userflips" with @v1.0.0-dev1
```

### Test Deployment to New Database

```bash
mkdir dev
sqlitch deploy db:sqlite:dev/flipr.db
```

Output:
```
Adding registry tables to db:sqlite:dev/sqitch.db
Deploying changes to db:sqlite:dev/flipr.db
  + users ................... ok
  + flips ................... ok
  + userflips @v1.0.0-dev1 .. ok
```

Check status:

```bash
sqlitch status db:sqlite:dev/flipr.db
```

Output:
```
# On database db:sqlite:dev/flipr.db
# Project:  flipr
# Change:   60ee3aba0445bf3287f9dc1dd97b1877523fa139
# Name:     userflips
# Tag:      @v1.0.0-dev1
# Deployed: 2025-10-12 11:19:15 -0800
# By:       Your Name <you@example.com>
# 
Nothing to deploy (up-to-date)
```

### Bundle for Distribution

Create a deployment bundle:

```bash
rm -rf dev
sqlitch bundle
```

Output:
```
Bundling into bundle
Writing config
Writing plan
Writing scripts
  + users
  + flips
  + userflips @v1.0.0-dev1
```

Test the bundle:

```bash
cd bundle
sqlitch deploy db:sqlite:flipr_prod.db
```

Package for distribution:

```bash
rm *.db
cd ..
mv bundle flipr-v1.0.0-dev1
tar -czf flipr-v1.0.0-dev1.tgz flipr-v1.0.0-dev1
```

---

## Making a Hash of Things

Let's add hashtag support. Work on a branch to avoid conflicts:

```bash
git checkout -b hashtags
```

Add the hashtags table:

```bash
sqlitch add hashtags --requires flips -n 'Adds table for storing hashtags.'
```

### Deploy Script

Edit `deploy/hashtags.sql`:

```sql
-- Deploy flipr:hashtags to sqlite
-- requires: flips

BEGIN;

CREATE TABLE hashtags (
    flip_id   INTEGER   NOT NULL REFERENCES flips(id),
    hashtag   TEXT      NOT NULL CHECK ( length(hashtag) > 0 ),
    PRIMARY KEY (flip_id, hashtag)
);

COMMIT;
```

### Verify Script

Edit `verify/hashtags.sql`:

```sql
-- Verify flipr:hashtags on sqlite

BEGIN;

SELECT flip_id, hashtag FROM hashtags WHERE 0;

ROLLBACK;
```

### Revert Script

Edit `revert/hashtags.sql`:

```sql
-- Revert flipr:hashtags from sqlite

BEGIN;

DROP TABLE hashtags;

COMMIT;
```

### Test

```bash
sqlitch deploy
sqlitch status --show-tags
sqlitch revert --to @HEAD^ -y
sqlitch deploy
```

Commit:

```bash
git add .
git commit -m 'Add hashtags table.'
```

### Emergency: Handling Merges

Switch back to main and discover other changes were merged:

```bash
git checkout main
git pull
```

Output shows a "lists" feature was added. Now merge our hashtags branch:

```bash
git merge --no-ff hashtags
```

**CONFLICT in sqitch.plan!**

### The Problem

Both branches added changes to the plan file. We need a strategy.

### The Solution: Union Merge

Git's "union" merge driver appends lines from all merging files, perfect for `sqitch.plan`.

First, abort the failed merge:

```bash
git reset --hard HEAD
```

Configure union merge for the plan file:

```bash
git checkout hashtags
echo 'sqitch.plan merge=union' > .gitattributes
git rebase main
```

Output:
```
First, rewinding head to replay your work on top of it...
Applying: Add hashtags table.
Using index info to reconstruct a base tree...
M	sqitch.plan
Falling back to patching base and 3-way merge...
Auto-merging sqitch.plan
```

Check the plan:

```bash
cat sqitch.plan
```

```
%syntax-version=1.0.0
%project=flipr
%uri=https://github.com/yourname/flipr

users 2025-10-12T18:06:04Z Your Name <you@example.com> # Creates table to track our users.
flips [users] 2025-10-12T19:01:40Z Your Name <you@example.com> # Adds table for storing flips.
userflips [users flips] 2025-10-12T19:11:11Z Your Name <you@example.com> # Creates the userflips view.
@v1.0.0-dev1 2025-10-12T19:13:02Z Your Name <you@example.com> # Tag v1.0.0-dev1.

lists [users] 2025-10-12T19:28:05Z Your Name <you@example.com> # Adds table for storing lists.
hashtags [flips] 2025-10-12T19:30:13Z Your Name <you@example.com> # Adds table for storing hashtags.
```

Perfect! Changes are properly ordered.

### Test with Rebase

```bash
sqlitch rebase -y
```

Output:
```
Reverting all changes from flipr_test
  - hashtags ................ ok
  - userflips @v1.0.0-dev1 .. ok
  - flips ................... ok
  - users ................... ok
Deploying changes to flipr_test
  + users ................... ok
  + flips ................... ok
  + userflips @v1.0.0-dev1 .. ok
  + lists ................... ok
  + hashtags ................ ok
```

The `rebase` command combines revert and deploy in one operation.

Commit the `.gitattributes` file:

```bash
git add .
git commit -m 'Add `.gitattributes` with union merge for `sqitch.plan`.'
```

### Merges Mastered

Now merge into main:

```bash
git checkout main
git merge --no-ff hashtags -m "Merge branch 'hashtags'"
```

Verify the plan:

```bash
cat sqitch.plan
```

Perfect! Tag and release:

```bash
sqlitch tag v1.0.0-dev2 -n 'Tag v1.0.0-dev2.'
git commit -am 'Tag the database with v1.0.0-dev2.'
git tag v1.0.0-dev2 -am 'Tag v1.0.0-dev2'
sqlitch bundle --dest-dir flipr-1.0.0-dev2
```

---

## In Place Changes

Need to modify an existing change? Use `rework`.

### The Problem

The product team wants Twitter usernames in the userflips view. We need to update the view definition.

### Traditional Approach (Don't Do This)

Normally, you'd:
1. Copy deploy script to a new name
2. Edit new script to drop and recreate view
3. Copy original deploy to new revert
4. Copy verify script and update
5. Test everything

**That's a lot of work!**

### The SQLitch Way

SQLitch automates most of this with the `rework` command. Requirements:
- A tag must exist between the two instances of the change
- We have `@v1.0.0-dev2`, so we're good!

```bash
sqlitch rework userflips -n 'Adds userflips.twitter.'
```

Output:
```
Added "userflips [userflips@v1.0.0-dev2]" to sqitch.plan.
Modify these files as appropriate:
  * deploy/userflips.sql
  * revert/userflips.sql
  * verify/userflips.sql
```

Check what happened:

```bash
git status
```

Output shows:
- **Untracked files**: `deploy/userflips@v1.0.0-dev2.sql`, etc.
- **Modified**: `revert/userflips.sql`, `sqitch.plan`

SQLitch:
1. Copied original scripts to `@v1.0.0-dev2` versions
2. Replaced revert script with original deploy script
3. Now you can edit the main scripts in place

### Edit the Scripts

Modify `deploy/userflips.sql`:

```sql
-- Deploy flipr:userflips to sqlite
-- requires: users
-- requires: flips

BEGIN;

DROP VIEW IF EXISTS userflips;
CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, u.twitter, f.body, f.timestamp
  FROM users u
  JOIN flips f ON u.nickname = f.nickname;

COMMIT;
```

Changes:
- Added `DROP VIEW IF EXISTS` (makes it idempotent)
- Added `u.twitter` column

Modify `verify/userflips.sql`:

```sql
-- Verify flipr:userflips on sqlite

BEGIN;

SELECT id, nickname, fullname, twitter, body, timestamp
  FROM userflips
 WHERE 0;

ROLLBACK;
```

Modify `revert/userflips.sql`:

```sql
-- Revert flipr:userflips from sqlite

BEGIN;

DROP VIEW IF EXISTS userflips;
CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, f.body, f.timestamp
  FROM users u
  JOIN flips f ON u.nickname = f.nickname;

COMMIT;
```

### Test

Deploy:

```bash
sqlitch deploy
```

Output:
```
Deploying changes to flipr_test
  + userflips .. ok
```

Verify the change:

```bash
sqlite3 flipr_test.db '.schema userflips'
```

Output shows the view now includes `twitter`.

Test reverting:

```bash
sqlitch revert --to @HEAD^ -y
```

Output:
```
Reverting changes to hashtags @v1.0.0-dev2 from flipr_test
  - userflips .. ok
```

Verify the twitter column is gone:

```bash
sqlite3 flipr_test.db '.schema userflips'
```

Output shows the original view without `twitter`.

Success! Commit:

```bash
git add .
git commit -m 'Add the twitter column to the userflips view.'
```

---

## Summary

You've learned:

✅ **Initialize** projects with `sqlitch init`  
✅ **Add changes** with deploy/revert/verify scripts  
✅ **Deploy** to databases with automatic verification  
✅ **Revert** changes safely with transaction protection  
✅ **Use targets** to simplify database connections  
✅ **Declare dependencies** between changes  
✅ **Tag releases** for version management  
✅ **Bundle deployments** for distribution  
✅ **Handle merges** with Git union merge strategy  
✅ **Rework changes** in place without duplication  

## Next Steps

- Explore [SQLitch CLI reference](../README.md#cli-commands)
- Review [architecture documentation](architecture/)
- Check out [testing strategies](../tests/README.md)
- Read about [Sqitch compatibility](../specs/004-sqlitch-tutorial-parity/)

## Getting Help

- 📖 **Documentation**: Check `docs/` directory
- 🐛 **Issues**: Report bugs on GitHub
- 💬 **Questions**: Open a discussion on GitHub

---

## License

This tutorial is adapted from the Sqitch tutorial.

Copyright (c) 2012-2025 David E. Wheeler (original Sqitch tutorial)  
Copyright (c) 2025 SQLitch Contributors (Python adaptation)

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
