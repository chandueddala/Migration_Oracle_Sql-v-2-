# Quick Reference Card
## Oracle → SQL Server Migration System v2.0

---

## 🚀 Quick Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Run
python main_v2.py

# Check logs
tail -f logs/migration.log
tail -f logs/security.log

# View reports
cat output/migration_report_*.json
cat logs/unresolved/*.json
```

---

## 🔑 Required API Keys

```env
ANTHROPIC_API_KEY=sk-ant-xxxxx
LANGCHAIN_API_KEY=ls__xxxxx
TAVILY_API_KEY=tvly-xxxxx  # Optional
```

---

## 📊 File Quick Reference

| File | Purpose | When to Use |
|------|---------|-------------|
| `main_v2.py` | Entry point | Always (run this) |
| `orchestrator.py` | Workflow manager | Auto-invoked |
| `ssma_agent.py` | SSMA integration | Auto if SSMA installed |
| `config_enhanced.py` | Settings | Customize behavior |
| `.env` | API keys | Configure keys |

---

## 🔧 Configuration Tweaks

### Reduce Costs
```python
# config_enhanced.py
MAX_REPAIR_ATTEMPTS = 2          # Default: 3
MAX_REFLECTION_ITERATIONS = 1    # Default: 2
ENABLE_WEB_SEARCH = False        # Default: True
```

### Enable SSMA
```env
# .env
SSMA_ENABLED=true
SSMA_CONSOLE_PATH=/path/to/SSMA
```

### Increase Repair Attempts
```python
# config_enhanced.py
MAX_REPAIR_ATTEMPTS = 5  # Default: 3
```

---

## 🎯 Migration Workflow

```
1. Connect DB → 2. Discover → 3. Select → 4. Convert → 5. Deploy
                                           ↓
                                     Repair Loop (×3)
                                           ↓
                                     Update Memory
```

---

## 🐛 Common Issues

### SSMA Not Found
```bash
# Disable SSMA
SSMA_ENABLED=false
```

### Connection Error
```bash
# Oracle: Check service name
# SQL Server: Check ODBC driver
pyodbc.drivers()  # List installed drivers
```

### High API Costs
```python
# Reduce repair attempts
MAX_REPAIR_ATTEMPTS = 2
```

---

## 📁 Important Directories

```
output/              # Migration reports
logs/                # System logs
logs/unresolved/     # Failed migrations
.env                 # Your API keys (create this)
```

---

## 🔒 Security Rules

❌ **NEVER** send table data to LLMs  
✅ **ALWAYS** use direct DB-to-DB transfer  
✅ **ALWAYS** mask credentials in logs  
✅ **ALWAYS** review security.log  

---

## 📈 Success Metrics

- **High Success Rate**: >90% objects migrated
- **Low Repair Rate**: <30% need repairs
- **Reasonable Cost**: <$2 per 100 objects
- **Fast Execution**: <10 sec per object

---

## 🆘 Getting Help

1. Check `README.md` - Full documentation
2. Check `ARCHITECTURE.md` - Technical details
3. Review `logs/migration.log` - Error details
4. Check `logs/unresolved/` - Failed objects

---

## 🎓 Learning Path

**Beginner**: README.md → Quick Start  
**User**: Run main_v2.py → Review reports  
**Developer**: ARCHITECTURE.md → Code review  
**Architect**: System design → Extensions  

---

## 📝 Example Session

```bash
$ python main_v2.py

🚀 ORACLE TO SQL SERVER MIGRATION SYSTEM v2.0

STEP 1: DATABASE CONNECTION
Oracle Host: localhost
Oracle Port: 1521
...
✅ Connected

STEP 2: INITIALIZING ORCHESTRATOR
✅ Orchestrator initialized

STEP 3: DISCOVERING TABLES
Tables (5): EMPLOYEES, DEPARTMENTS, ...
Select Tables: all
Migrate data? [y/N]: y

STEP 4: MIGRATING
[1/5] EMPLOYEES ✅ Success
[2/5] DEPARTMENTS ✅ Success
...

📊 SUMMARY
Tables: ✅ 5 | ❌ 0
Rows: 1,234
Cost: $0.85
```

---

## 🔗 Key Links

- **LangSmith**: https://smith.langchain.com/
- **Anthropic**: https://console.anthropic.com/
- **Tavily**: https://tavily.com/
- **SSMA Download**: https://aka.ms/ssma-oracle

---

## 📞 Support Checklist

Before asking for help:
- [ ] Checked README.md
- [ ] Reviewed logs/migration.log
- [ ] Checked .env configuration
- [ ] Tested database connections
- [ ] Reviewed error details

---

**Version**: 2.0  
**Status**: Production Ready  
**Last Updated**: 2025-01-17
