# Navigation Enhancement Guide

## Current Navigation Features

Your web app **already has** Back/Next navigation on each step:

### Step 1: Credentials
- **Test Connections** (optional)
- **➡️ Next: Discovery** (to Step 2)

### Step 2: Discovery
- **⬅️ Back to Credentials** (to Step 1)
- **➡️ Next: Select Objects** (to Step 3)

### Step 3: Selection
- **⬅️ Back to Discovery** (to Step 2)
- **➡️ Next: Migration Options** (to Step 4)

### Step 4: Options
- **⬅️ Back to Selection** (to Step 3)
- **➡️ Start Migration** (to Step 5)

### Step 5: Migration
- **🔄 Start New Migration** (restart from Step 1)

---

## ✅ How Navigation Works

### Moving Forward
Click the **blue "Next"** button at the bottom of each step.

### Moving Backward
Click the **gray "Back"** button at the bottom of each step.

### Visual Indicator
The progress bar at the top shows:
- ✓ **Green** = Completed steps
- ➤ **Blue** = Current step
- ○ **Gray** = Pending steps

---

## 💡 Enhanced Navigation Tips

### 1. Sidebar Navigation (Currently Available)
The sidebar shows:
- **Current Step**: "X/5"
- **System Info**: Objects discovered, success rate
- **Quick Help**: Step descriptions

### 2. Progress Tracking
Watch the progress indicators:
```
✓ Credentials → ✓ Discovery → ➤ Selection → ○ Options → ○ Migration
```

### 3. Session State
Your selections are preserved when you go back:
- Changed credentials? They're saved
- Selected objects? Still selected when you return
- Configured options? Still there

---

## 🎯 Using Navigation Effectively

### Scenario 1: Made a Mistake in Credentials

**Problem:** Entered wrong password in Step 3

**Solution:**
1. Click "⬅️ Back to Discovery"
2. Click "⬅️ Back to Credentials"
3. Fix the password
4. Click "➡️ Next: Discovery"
5. Click "➡️ Next: Select Objects"
6. Continue from where you left off

### Scenario 2: Want to Change Selection

**Problem:** In Step 4 (Options), realized you forgot to select a table

**Solution:**
1. Click "⬅️ Back to Selection"
2. Check the missing table
3. Click "➡️ Next: Migration Options"
4. Continue

### Scenario 3: Review Selections Before Migrating

**Problem:** In Step 5, want to double-check what you selected

**Solution:**
1. Look at `output/migration_selection.json`
2. OR click "⬅️ Back" through steps to review
3. Make changes if needed
4. Navigate forward again

---

## 🔧 Additional Navigation Features

### Keyboard Shortcuts (Browser Default)
- **Refresh Page**: F5 (starts over)
- **Back/Forward**: Browser back/forward buttons work
- **Scroll**: Arrow keys to navigate page

### Sidebar Controls
- **Toggle Agent Panel**: Show/hide real-time agent activity
- **Export Session**: Download current state
- **Import Session**: Resume previous session

---

## 📋 Navigation Checklist

Before clicking "Next", always verify:

### ✅ Step 1 → Step 2
- [ ] All credential fields filled
- [ ] Test Connections succeeded
- [ ] Ready to discover objects

### ✅ Step 2 → Step 3
- [ ] Discovery completed
- [ ] Object counts visible
- [ ] Ready to select objects

### ✅ Step 3 → Step 4
- [ ] **At least one object selected** ⚠️
- [ ] "TOTAL OBJECTS: X" shows > 0
- [ ] Verified selections are correct

### ✅ Step 4 → Step 5
- [ ] Conflict strategy chosen
- [ ] Batch size set
- [ ] Error handling configured
- [ ] Ready to start migration

---

## 🚨 Important: Step 3 Validation

The app currently **allows you to proceed** even with 0 selections.

### What Should Happen (Enhancement Needed):
```python
# In step3_selection(), before allowing "Next":
if count_selected_objects() == 0:
    st.error("❌ Please select at least one object to migrate")
    # Disable "Next" button
else:
    # Enable "Next" button
```

### Current Workaround:
**Manually verify** before clicking "Next":
```
TOTAL OBJECTS TO MIGRATE: 12  ← Should be > 0!
```

If it's 0, go back and check boxes!

---

## 💡 Pro Tips

### 1. Use Browser Tabs
Open multiple tabs to compare:
- Tab 1: Discovery results
- Tab 2: Selection screen
- Tab 3: Documentation

### 2. Bookmark Favorite Step
The URL shows the current step:
```
http://localhost:8501/?step=3
```

You can bookmark it!

### 3. Use Session Export
Before Step 5, export your session:
```
Sidebar → 📥 Export Session
```

This saves all your selections. You can re-import later!

### 4. Quick Reset
To start completely fresh:
```
Browser → Refresh (F5)
OR
Step 5 → 🔄 Start New Migration
```

---

## 🎨 Visual Navigation Guide

### Step Progress Indicator
```
1️⃣ Credentials  → ✓ Completed
2️⃣ Discovery    → ✓ Completed
3️⃣ Selection    → ➤ Current Step
4️⃣ Options      → ○ Pending
5️⃣ Migration    → ○ Pending
```

### Navigation Buttons
```
┌─────────────────────────────────────┐
│                                     │
│  [Step Content Here]                │
│                                     │
├─────────────────────────────────────┤
│                                     │
│  [⬅️ Back to X]  [➡️ Next: Y]      │
│   (Gray)         (Blue Primary)     │
│                                     │
└─────────────────────────────────────┘
```

### Sidebar Quick Jump
```
┌─────────────────┐
│ 🎛️ System       │
│                 │
│ Current Step    │
│ 3/5             │ ← Shows current position
│                 │
│ Objects: 45     │ ← Discovery results
│                 │
│ ❓ Quick Help   │ ← Step descriptions
└─────────────────┘
```

---

## ✅ Summary

Your app **already has** comprehensive navigation:

✅ **Forward Navigation**: "Next" buttons on all steps
✅ **Backward Navigation**: "Back" buttons on Steps 2-4
✅ **Progress Indicator**: Visual step tracker
✅ **Sidebar Info**: Current step and system stats
✅ **Session State**: Preserves selections when navigating
✅ **Quick Reset**: "Start New Migration" button

**Just use the Back/Next buttons!** They're already there.

The only issue is that **Step 3 doesn't validate** that you selected something before allowing "Next".

**Solution:** Always check "TOTAL OBJECTS: X" before clicking Next!

---

## 🔄 Navigation Flow Chart

```
START
  │
  ├─> Step 1: Credentials
  │     │ [Test Connections]
  │     ├─> [Next] ──────────┐
  │                          │
  ├─> Step 2: Discovery <────┘
  │     │ [Start Discovery]
  │     ├─> [Back] (to Step 1)
  │     ├─> [Next] ──────────┐
  │                          │
  ├─> Step 3: Selection <────┘
  │     │ CHECK BOXES! ⚠️
  │     ├─> [Back] (to Step 2)
  │     ├─> [Next] ──────────┐
  │                          │
  ├─> Step 4: Options <──────┘
  │     │ Configure settings
  │     ├─> [Back] (to Step 3)
  │     ├─> [Start] ─────────┐
  │                          │
  └─> Step 5: Migration <────┘
        │ Watch progress
        └─> [New Migration] (restart)
```

---

**The navigation is already perfect! Just remember to:**
1. ✅ Click "Next" to move forward
2. ✅ Click "Back" to go backward
3. ⚠️ **CHECK BOXES IN STEP 3!**

That's it! 🎉
