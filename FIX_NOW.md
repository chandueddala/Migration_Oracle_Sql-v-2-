# 🔥 FIX NOW - Tables Already Exist

## Your Error

```
❌ DDL execution failed: There is already an object named 'LOANS' in the database
```

The tables exist from a previous run. You have **3 options**:

---

## Option 1: PowerShell Script (EASIEST) ⭐

```powershell
# Run this in PowerShell
.\cleanup_tables.ps1
```

Then run migration:
```powershell
python main.py
```

**This script will:**
- Ask for your SQL Server credentials
- Drop all 5 tables
- Report success/failure

---

## Option 2: Python Script (ALTERNATIVE)

```powershell
# Run this
python auto_cleanup.py
```

Then run migration:
```powershell
python main.py
```

---

## Option 3: Manual SQL (FASTEST if you have SSMS)

**Open SQL Server Management Studio or Azure Data Studio**

Run this:

```sql
USE master;
GO

-- Drop all tables
DROP TABLE IF EXISTS [LOANS];
DROP TABLE IF EXISTS [LOAN_AUDIT];
DROP TABLE IF EXISTS [LOAN_PAYMENTS];
DROP TABLE IF EXISTS [LOAN_SCHEDULE];
DROP TABLE IF EXISTS [STG_LOAN_APPS];
GO

-- Verify they're gone
SELECT TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('LOANS', 'LOAN_AUDIT', 'LOAN_PAYMENTS', 'LOAN_SCHEDULE', 'STG_LOAN_APPS');
-- Should return no rows
```

Then run migration:
```powershell
python main.py
```

---

## After Cleanup

Your migration should work:

```
[1/5] Table: LOANS
  🔄 Orchestrating: LOANS
    📥 Step 1/5: Fetching Oracle DDL...
    🔄 Step 2/5: Converting to SQL Server...
    👁️ Step 3/5: Reviewing conversion...
    🚀 Step 4/5: Deploying to SQL Server...
    ✅ Table migration successful  ← SUCCESS!

    📊 Migrating data for table: LOANS
       📥 Fetching data from Oracle...
       ✅ Fetched 100 rows
       📤 Inserting into SQL Server...
       ✅ Successfully migrated 100 rows  ← SUCCESS!
```

---

## Why This Happens

1. Previous migration created the table structure ✅
2. Data migration failed (fetch_table_data error) ❌
3. Tables remained in SQL Server
4. New run tries to CREATE again → Error!

---

## Permanent Fix

To prevent this in the future, we need to modify the converter to add DROP statements.

See [COMPREHENSIVE_FIX_PLAN.md](COMPREHENSIVE_FIX_PLAN.md) for the complete solution.

---

## Troubleshooting

### Script says "Connection failed"
**Check:**
- Is SQL Server running?
- Are credentials correct?
- Is TrustServerCertificate setting correct?

### Script says "Permission denied"
**Solution:**
- Use 'sa' account or account with DROP TABLE permission
- Check database name is correct

### Tables still not dropping
**Try:**
- Check if there are foreign key constraints
- Run this first:
```sql
-- Drop all foreign keys first
DECLARE @sql NVARCHAR(MAX) = '';
SELECT @sql += 'ALTER TABLE ' + QUOTENAME(OBJECT_SCHEMA_NAME(parent_object_id)) + '.' +
               QUOTENAME(OBJECT_NAME(parent_object_id)) +
               ' DROP CONSTRAINT ' + QUOTENAME(name) + ';'
FROM sys.foreign_keys
WHERE referenced_object_id IN (
    OBJECT_ID('LOANS'),
    OBJECT_ID('LOAN_AUDIT'),
    OBJECT_ID('LOAN_PAYMENTS'),
    OBJECT_ID('LOAN_SCHEDULE'),
    OBJECT_ID('STG_LOAN_APPS')
);
EXEC sp_executesql @sql;
```

---

## Quick Command Reference

```powershell
# Option 1: PowerShell script
.\cleanup_tables.ps1
python main.py

# Option 2: Python script
python auto_cleanup.py
python main.py

# Option 3: Check if tables exist
sqlcmd -S localhost -d master -Q "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'LOAN%'"
```

---

## ✅ Expected Timeline

1. **Run cleanup script:** 30 seconds
2. **Run migration:** 3-5 minutes
3. **Total time:** 5-6 minutes to complete migration

---

**Choose your option and fix it now!** 🚀

**Recommended:** Use Option 1 (PowerShell script) - it's the easiest!
