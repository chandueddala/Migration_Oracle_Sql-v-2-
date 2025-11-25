# Oracle to SQL Server Migration - Web Application

## 🌟 Professional-Grade Web Interface

A production-ready Streamlit web application for migrating Oracle databases to SQL Server with:

- ✅ **Intuitive UI** - User-friendly interface with progress tracking
- ✅ **Upfront Selection** - Select all objects before migration starts
- ✅ **Conflict Resolution** - Choose how to handle existing objects
- ✅ **Real-time Progress** - Live migration status and logging
- ✅ **Industry Standards** - Production-ready code with best practices

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Windows
pip install -r requirements_streamlit.txt

# Linux/Mac
pip3 install -r requirements_streamlit.txt
```

### 2. Configure API Keys

Edit `config/config_enhanced.py`:

```python
ANTHROPIC_API_KEY = "your-anthropic-api-key-here"
OPENAI_API_KEY = "your-openai-api-key-here"  # Optional
```

### 3. Start the Web Application

#### Windows:
```bash
start_webapp.bat
```

#### Linux/Mac:
```bash
chmod +x start_webapp.sh
./start_webapp.sh
```

#### Manual Start:
```bash
streamlit run app.py
```

### 4. Access the Application

Open your browser and navigate to:
```
http://localhost:8501
```

---

## 📋 5-Step Workflow

### Step 1: Database Credentials
- Enter Oracle and SQL Server connection details
- Test connections before proceeding
- Secure password input

### Step 2: Database Discovery
- Automatic discovery of ALL database objects
- Real-time progress tracking
- Summary metrics dashboard

### Step 3: Object Selection
- Checkbox selection for each object type
- Select All / Deselect All buttons
- Data migration toggle per table
- Organized tabs for different object types

### Step 4: Migration Options
- **Conflict Resolution**: Drop/Skip/Alter/Fail
- **Data Options**: Batch size, truncate settings
- **Error Handling**: Stop on error, retry attempts
- **LLM Options**: Package decomposition, auto-repair

### Step 5: Migration Execution
- Real-time progress bar
- Live migration log
- Success/failure indicators
- Downloadable results

---

## 🎯 Key Features

### Upfront Selection Workflow
```
1. Discover ALL objects → 2. Select EVERYTHING → 3. Configure options → 4. Migrate (no interruptions!)
```

### Intelligent Package Decomposition
- LLM analyzes Oracle packages
- Decomposes into individual procedures/functions
- Creates separate SQL Server objects
- Maintains naming convention

### Automatic Error Repair
- Captures deployment errors
- LLM analyzes and fixes issues
- Automatic retry with fixes
- Up to 3 retry attempts

### Conflict Resolution Options
1. **Drop and Create** (Recommended) - Clean migration
2. **Skip Existing** - For incremental migrations
3. **Create or Alter** - Minimal disruption
4. **Fail on Conflict** - Strict validation

---

## 📁 Output Files

After migration, find results in `output/`:

- `discovery_result.json` - All discovered objects
- `migration_selection.json` - Your selections (auto-saved)
- `migration_results.json` - Complete migration results

---

## 🛡️ Production Best Practices

### Error Handling
- Try-catch blocks throughout
- Graceful degradation
- Detailed error logging

### Logging
- File logging to `logs/migration_webapp.log`
- Console output for debugging
- Structured log format

### Session State
- Persistent across page reloads
- Saved to JSON for reproducibility
- Reset option for new migrations

### Input Validation
- Required field checks
- Connection testing
- Selection validation

---

## 🔧 Configuration

### Required API Keys

Edit `config/config_enhanced.py`:

```python
ANTHROPIC_API_KEY = "sk-ant-api03-..."  # Required
OPENAI_API_KEY = "sk-..."               # Optional
```

### Streamlit Configuration (Optional)

Create `.streamlit/config.toml`:

```toml
[server]
port = 8501
address = "localhost"

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
```

---

## 🆘 Troubleshooting

### Streamlit not installed
```bash
pip install streamlit
```

### Port already in use
```bash
streamlit run app.py --server.port 8502
```

### Connection failed
1. Verify credentials
2. Check database is running
3. Verify network connectivity
4. Check firewall settings

### Migration hangs
1. Check logs: `logs/migration_webapp.log`
2. Verify network connection
3. Reduce batch size
4. Restart application

---

## 💡 Tips for Success

### 1. Test First
Always test on staging environment before production

### 2. Incremental Migration
For large databases:
- Migrate schema first (no data)
- Verify schema correctness
- Run separate data migration
- Migrate in batches of 10-20 tables

### 3. Review Results
After migration:
- Download results JSON
- Review failed objects
- Test critical procedures
- Verify data integrity

### 4. Monitor Costs
- LLM costs displayed in real-time
- Typical: $2-5 per 100 objects
- Saved in results JSON

---

## 📊 Example Session

**Database:** HR System
- 25 tables (500-50,000 rows each)
- 5 packages (15-20 members each)
- 15 procedures, 10 functions, 8 triggers

**Time Breakdown:**
- Credentials: 30 seconds
- Discovery: 45 seconds
- Selection: 2 minutes
- Options: 1 minute
- Migration: 15 minutes

**Results:**
- 88 objects created in SQL Server
- 98% success rate (86/88)
- Cost: $4.50

---

## ✅ Summary

Professional-grade web interface with:

✅ **User-Friendly** - 5-step wizard
✅ **Upfront Selection** - No interruptions
✅ **Intelligent** - LLM-powered conversion
✅ **Configurable** - Full control
✅ **Production-Ready** - Error handling, logging
✅ **Real-time** - Live progress tracking

**Start now:**

```bash
# Windows
start_webapp.bat

# Linux/Mac
./start_webapp.sh
```

Open http://localhost:8501 and migrate your database!

---

**Built with:** Streamlit, Python, Claude Sonnet 4
**Documentation:** See QUICK_START.md, SYSTEM_COMPLETE.md
