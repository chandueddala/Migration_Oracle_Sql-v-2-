# Web Application Troubleshooting Guide

## Common Issue: Migration Shows 0 Objects

### Problem
You completed all 5 steps but the migration results show:
```
Total Objects: 0
Successful: 0
Failed: 0
```

### Root Cause
**Selections were not properly saved** in Step 3.

---

## ✅ Solution: How to Properly Select Objects

### Step 3: Selection - CRITICAL STEP!

This is where most users have issues. Here's how to do it correctly:

#### 1. **Tables Section**

**What you should see:**
```
Tables
[✓ Select All Tables] [✗ Deselect All Tables]

☐ CUSTOMERS      15,678 rows | 12.50 MB    ☐ Include Data
☐ ORDERS         48,923 rows | 45.23 MB    ☐ Include Data
☐ PRODUCTS        1,234 rows |  2.10 MB    ☐ Include Data
```

**What to do:**
1. **Check the box** next to each table name (left checkbox)
2. **Check "Include Data"** if you want data migrated (right checkbox)
3. **OR click "✓ Select All Tables"** to select all at once

**After selection, you should see:**
```
☑ CUSTOMERS      15,678 rows | 12.50 MB    ☑ Include Data  ← Both checked!
☑ ORDERS         48,923 rows | 45.23 MB    ☑ Include Data  ← Both checked!
☑ PRODUCTS        1,234 rows |  2.10 MB    ☐ Include Data  ← Table selected, no data
```

#### 2. **Packages Section**

**What you should see:**
```
Packages
[✓ Select All Packages] [✗ Deselect All Packages]

☐ PKG_LOAN_PROCESSOR     (5 members) ✅
☐ PKG_ACCOUNT_MANAGER    (8 members) ✅
```

**What to do:**
1. **Check the box** next to each package
2. **OR click "✓ Select All Packages"**

**After selection:**
```
☑ PKG_LOAN_PROCESSOR     (5 members) ✅  ← Checked!
☑ PKG_ACCOUNT_MANAGER    (8 members) ✅  ← Checked!
```

#### 3. **Other Objects (Tabs)**

Click each tab and select objects:

**Procedures Tab:**
```
[✓ Select All] [✗ Deselect All]

☐ PROC_CALCULATE_INTEREST ✅
☐ PROC_VALIDATE_USER ✅
```

**Functions Tab:**
```
☐ FUNC_GET_STATUS ✅
☐ FUNC_FORMAT_DATE ✅
```

**Triggers Tab:**
```
☐ TRG_AUDIT_CUSTOMERS
```

---

## 🔍 How to Verify Your Selection

### Before Clicking "Next: Migration Options"

**Look for the selection count at the bottom of Step 3:**

You should see something like:
```
Selection Summary:
  Tables: 3
  Tables with Data: 2
  Tables Schema Only: 1

  Code Objects:
    Packages: 2
    Procedures: 5
    Functions: 3
    Triggers: 1

  TOTAL OBJECTS TO MIGRATE: 14  ← Should NOT be 0!
```

**If you see "TOTAL OBJECTS TO MIGRATE: 0":**
- ❌ You didn't check any boxes!
- Go back and check boxes in each section

---

## 📋 Step-by-Step Checklist

### ✅ Step 1: Credentials
- [ ] Entered Oracle host, port, service name
- [ ] Entered Oracle username and password
- [ ] Entered SQL Server host and database
- [ ] Entered SQL Server username and password
- [ ] Clicked "Test Connections" and got success ✓
- [ ] Clicked "Next: Discovery"

### ✅ Step 2: Discovery
- [ ] Clicked "Start Discovery"
- [ ] Waited for discovery to complete
- [ ] Saw object counts (Tables: X, Packages: Y, etc.)
- [ ] Clicked "Next: Select Objects"

### ✅ Step 3: Selection ⚠️ CRITICAL!
- [ ] **CHECKED BOXES** next to tables I want
- [ ] **CHECKED "Include Data"** for tables that need data
- [ ] **CHECKED BOXES** next to packages I want
- [ ] Clicked through **ALL TABS** (Procedures, Functions, Triggers)
- [ ] **CHECKED BOXES** for objects I want in each tab
- [ ] **VERIFIED** total objects count is > 0
- [ ] Clicked "Next: Migration Options"

### ✅ Step 4: Options
- [ ] Selected conflict resolution strategy
- [ ] Set batch size
- [ ] Configured error handling
- [ ] Enabled LLM options
- [ ] Clicked "Start Migration"

### ✅ Step 5: Migration
- [ ] Watched progress bar
- [ ] Saw migration log with actual objects being migrated
- [ ] Downloaded results

---

## 🐛 Common Mistakes

### Mistake 1: Not Checking Boxes
**Problem:** Clicked through Step 3 without checking any boxes

**Solution:** Go back to Step 3 and actually check the boxes!

### Mistake 2: Only Selecting Tables, Not Data
**Problem:** Checked table names but didn't check "Include Data"

**Result:** Only schema migrated, no data

**Solution:** Check BOTH boxes:
- Left box = migrate table
- Right box = include data

### Mistake 3: Missing Objects in Tabs
**Problem:** Selected tables and packages but forgot to click Procedures/Functions tabs

**Result:** Only tables and packages migrated

**Solution:** Click ALL tabs and select what you need

### Mistake 4: Clicking "Next" Too Fast
**Problem:** Rushed through Step 3 without reviewing selections

**Solution:** Take time to verify your selections before proceeding

---

## 💡 Pro Tips

### 1. Use "Select All" Buttons
Fastest way to select everything:
```
Step 3 → Tables Section → Click "✓ Select All Tables"
Step 3 → Packages Section → Click "✓ Select All Packages"
Step 3 → Procedures Tab → Click "✓ Select All"
Step 3 → Functions Tab → Click "✓ Select All"
...etc
```

### 2. Check the Summary
Always look at the selection summary before clicking "Next":
```
TOTAL OBJECTS TO MIGRATE: 14  ← This should be > 0!
```

### 3. Start Small
For first test, just select 1-2 tables:
```
☑ TEST_TABLE_1    100 rows    ☑ Include Data
```

### 4. Review Before Migration
Step 4 shows your selections. Verify before starting migration!

---

## 🔄 If You Already Started with 0 Objects

### Quick Fix:

1. **In the web app, click "🔄 Start New Migration"** (at bottom of Step 5)
2. OR **Refresh the browser page**
3. Start over from Step 1
4. **This time, actually check boxes in Step 3!**

---

## 📊 What Success Looks Like

### After Step 3 (Selection):
```
Selection Summary:
  Tables: 3              ← NOT 0!
  Tables with Data: 2    ← Some or all tables

  Code Objects:
    Packages: 2          ← If you selected packages
    Procedures: 5        ← If you selected procedures

  TOTAL OBJECTS: 12     ← MUST BE > 0!
```

### After Step 5 (Migration):
```
Total Objects: 12       ← Same as selection
Successful: 11          ← Most should succeed
Failed: 1               ← Some might fail

💰 Cost: $2.50          ← Shows actual cost
```

**NOT:**
```
Total Objects: 0   ❌ This means nothing was selected!
```

---

## 🆘 Still Having Issues?

### Debug Steps:

1. **Check discovery worked:**
   - Step 2 should show: "Tables: 45, Packages: 12" etc.
   - If all zeros, database connection might have failed

2. **Check selection saved:**
   - Look in `output/migration_selection.json`
   - Should contain your selected objects
   - If empty, selections didn't save

3. **Check migration log:**
   - Look in `logs/migration_webapp.log`
   - Search for "User selected X objects"

4. **Try the CLI version:**
   ```bash
   python migrate_upfront.py
   ```
   - This has more verbose output
   - Easier to see what's happening

---

## ✅ Quick Test Migration

### 5-Minute Test:

1. **Step 1:** Enter credentials → Test Connections ✓
2. **Step 2:** Start Discovery → Wait for completion
3. **Step 3:**
   - Select JUST ONE table
   - Check both boxes (table + data)
   - Verify "TOTAL: 1"
4. **Step 4:** Use defaults → Start Migration
5. **Step 5:** Watch it migrate that 1 table!

If this works, you understand the process. Then select more objects!

---

## 📝 Summary

**The key issue:** Not checking boxes in Step 3

**The solution:**
1. Actually click checkboxes
2. Verify total > 0
3. Then proceed to Step 4

**Remember:**
- Boxes unchecked = nothing selected = 0 objects migrated
- Boxes checked = objects selected = successful migration

---

**Need more help?**
- Check `logs/migration_webapp.log` for errors
- See `WEB_APP_README.md` for detailed guide
- The web app is still running at http://localhost:8501

**Try again and remember to CHECK THOSE BOXES!** ✓
