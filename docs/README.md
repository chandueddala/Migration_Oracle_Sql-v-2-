# Oracle to SQL Server Migration System v2.0

Enterprise-grade, AI-powered database migration platform with SSMA integration, LLM agents, and shared memory learning.

## 🌟 Features

### Core Capabilities
- **Multi-Agent Architecture**: Orchestrator, SSMA, Converter, Reviewer, Debugger, Researcher
- **SSMA Primary Conversion**: Microsoft SSMA as first-line converter with LLM fallback
- **Automatic Error Repair**: Self-healing migration with up to 3 repair attempts per object
- **Shared Memory System**: Cross-agent learning from successful patterns and errors
- **Web Search Integration**: Automatic solutions lookup for SQL Server errors
- **Metadata Refresh**: Automatic SQL Server metadata sync after successful deployments
- **Security Compliance**: Never sends table data to LLMs, comprehensive audit logging

### Migration Support
- ✅ Tables (structure + data)
- ✅ Procedures
- ✅ Functions  
- ✅ Triggers
- ✅ Views (planned)
- ✅ Sequences (planned)
- ✅ Packages (planned)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                        │
│  - Workflow management                                       │
│  - Agent coordination                                        │
│  - Memory updates                                            │
└──────────────┬──────────────────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼─────┐         ┌─────▼────┐
│  SSMA   │         │   LLM    │
│  AGENT  │────────>│ CONVERTER│
│(Primary)│  Falls  │(Fallback)│
└─────────┘  back   └──────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼─────┐         ┌─────▼────┐
│REVIEWER │         │ DEBUGGER │
│ AGENT   │<────────│  AGENT   │
└─────────┘  Review └──────────┘
               │
         ┌─────▼──────┐
         │ RESEARCHER │
         │   AGENT    │
         │(Web Search)│
         └────────────┘
               │
         ┌─────▼──────┐
         │   SHARED   │
         │   MEMORY   │
         └────────────┘
```

## 📋 Prerequisites

### Required
1. **Python 3.9+**
2. **Oracle Database** (11g or higher)
3. **SQL Server 2022** (or 2019/2017)
4. **Anthropic API Key** (for Claude models)
5. **LangSmith API Key** (for tracing, optional but recommended)

### Optional but Recommended
6. **Tavily API Key** (for web search error solutions)
7. **Microsoft SSMA for Oracle** (for primary conversion)
8. **OpenAI API Key** (for GPT models)

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone <repository-url>
cd oracle-sqlserver-migration

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```env
# Required
ANTHROPIC_API_KEY=sk-ant-xxxxx
LANGCHAIN_API_KEY=ls__xxxxx

# Optional
TAVILY_API_KEY=tvly-xxxxx
OPENAI_API_KEY=sk-xxxxx

# SSMA (if installed)
SSMA_ENABLED=true
SSMA_CONSOLE_PATH=C:\Program Files\Microsoft SQL Server Migration Assistant for Oracle\bin\SSMAforOracleConsole.exe
```

### 3. Run Migration

```bash
# With orchestrator (recommended)
python main_v2.py

# Legacy mode
python main.py
```

### 4. Interactive Workflow

The system will guide you through:

1. **Database Connection**: Enter Oracle and SQL Server credentials
2. **Schema Discovery**: System discovers all objects
3. **Object Selection**: Choose tables, procedures, functions, triggers
4. **Data Migration**: Optionally migrate table data
5. **Automated Migration**: System handles conversion, review, deployment, repair
6. **Report Generation**: Comprehensive migration report

## 📁 Project Structure

```
oracle-sqlserver-migration/
├── main_v2.py                 # Entry point with orchestrator
├── orchestrator.py            # Main orchestrator agent
├── ssma_agent.py              # SSMA integration
├── ai_converter.py            # LLM conversion agents
├── migration_engine_v2.py     # Enhanced migration workflow
├── config_enhanced.py         # Configuration with security
├── database.py                # Database connections & tools
├── shared_memory.py           # Shared memory system
├── web_search_helper.py       # Web search integration
├── oracle_memory_builder.py   # Oracle metadata extraction
├── migration_memory.py        # Memory data structures
├── requirements.txt           # Python dependencies
├── .env                       # API keys (create this)
├── output/                    # Migration reports
├── logs/                      # System logs
│   ├── migration.log
│   ├── security.log
│   ├── ssma.log
│   └── unresolved/           # Unresolved error logs
└── README.md
```

## 🔒 Security Features

### Data Protection
- **No Table Data to LLMs**: Actual row data NEVER sent to AI models
- **Credential Masking**: Passwords masked in all log files
- **Security Audit Log**: Separate log for all data access events

### Compliance Logging
```python
# All data operations are logged
SecurityLogger.log_data_access("migrate", "EMPLOYEES", 1000)
# Output: DATA_ACCESS: operation=migrate, table=EMPLOYEES, rows=1000, llm_involved=False
```

## 🧠 Shared Memory System

The system learns from every migration:

### What It Stores
- ✅ Successful conversion patterns
- ❌ Failed patterns to avoid
- 🔍 Error solutions that worked
- 📊 Schema structures (Oracle + SQL Server)
- 🔑 Identity column mappings
- 🗺️ Table name mappings

### Example Usage
```python
from shared_memory import get_shared_memory

memory = get_shared_memory()

# Check if error solution is known
solutions = memory.get_error_solutions("IDENTITY_INSERT is set to OFF")
# Returns previously successful fixes

# Get similar successful patterns
patterns = memory.get_similar_patterns("PROCEDURE", limit=5)
# Returns recent successful procedure migrations
```

## 🔧 Configuration Options

### config_enhanced.py

```python
# Migration Settings
MAX_REPAIR_ATTEMPTS = 3         # Repair loops per object
ENABLE_WEB_SEARCH = True        # Search web for error solutions
MAX_SEARCH_RESULTS = 5          # Top N search results

# SSMA Integration
SSMA_ENABLED = True             # Use SSMA if available
USE_SSMA_FIRST = True           # Try SSMA before LLM
LLM_FALLBACK_ON_SSMA_WARNINGS = True  # Fallback if >5 warnings

# Security
ALLOW_TABLE_DATA_TO_LLM = False  # NEVER change this
LOG_SECURITY_EVENTS = True
MASK_CREDENTIALS_IN_LOGS = True

# Orchestration
USE_ORCHESTRATOR = True         # Use orchestrator workflow
REFRESH_METADATA_AFTER_DEPLOY = True  # Update memory after success
LOG_UNRESOLVED_ERRORS = True    # Log failed migrations
```

## 📊 Migration Workflow

### For Each Object

1. **Discovery**: Fetch Oracle source code/DDL
2. **Primary Conversion**: 
   - Try SSMA first (if available)
   - Fallback to LLM if SSMA fails/warns
3. **Review**: Claude Opus reviews quality
4. **Deployment**: Deploy to SQL Server
5. **Repair Loop** (if deployment fails):
   - Analyze SQL Server error
   - Search web for solutions
   - Get AI-generated fix
   - Retry deployment (up to 3 times)
6. **Metadata Refresh**: Update shared memory with SQL Server metadata
7. **Pattern Storage**: Store success/failure for future learning

### Unresolved Errors

If migration fails after all attempts:
- Complete error log saved to `logs/unresolved/<object>_<timestamp>.json`
- Includes: error history, Oracle code, attempted fixes, memory context
- Can be manually reviewed or used for future improvements

## 🎯 Use Cases

### 1. Full Database Migration
```bash
python main_v2.py
# Select "all" for tables, procedures, functions, triggers
```

### 2. Table Structure Only
```bash
python main_v2.py
# Select tables, answer "N" to data migration
```

### 3. Specific Objects
```bash
python main_v2.py
# Type specific object names when prompted
# Example: "EMPLOYEE_PKG GET_SALARY UPDATE_EMPLOYEE"
```

### 4. Retry Failed Migrations
Check `logs/unresolved/` for failed objects, fix Oracle code or manually adjust T-SQL, then rerun.

## 📈 Cost Tracking

Real-time cost tracking for all API calls:

```
💰 Cost summary (approx):
  - anthropic/claude-sonnet-4-20250514: 15000 in tok, 8000 out tok, $0.165
  - anthropic/claude-opus-4-20250514: 5000 in tok, 3000 out tok, $0.300
  => GRAND TOTAL ≈ $0.465
```

## 🐛 Troubleshooting

### SSMA Not Found
```bash
# Set path manually in .env
SSMA_ENABLED=false
# System will use LLM for all conversions
```

### Web Search Disabled
```bash
# Get free Tavily API key: https://tavily.com
# Add to .env:
TAVILY_API_KEY=tvly-xxxxx
```

### Connection Errors
```bash
# Oracle: Check TNS, service name, credentials
# SQL Server: Check ODBC driver, TrustServerCertificate

# Test connections manually:
python -c "import oracledb; print(oracledb.version)"
python -c "import pyodbc; print(pyodbc.drivers())"
```

### High LLM Costs
```python
# In config_enhanced.py, reduce quality:
MAX_REFLECTION_ITERATIONS = 1  # Reduce reviews
MAX_REPAIR_ATTEMPTS = 2        # Reduce repair loops
```

## 🔮 Future Enhancements

### Planned Features
- [ ] MySQL source support
- [ ] PostgreSQL source/target support
- [ ] Snowflake target support
- [ ] DB2 source support
- [ ] Package migration
- [ ] View migration
- [ ] Sequence migration
- [ ] Advanced UI (web interface)
- [ ] Parallel object migration
- [ ] Pre-migration validation reports

### Architecture Extensions
- Pluggable source connectors
- Pluggable target connectors
- Custom conversion rules
- User-defined repair strategies

## 📝 License

[Your License Here]

## 🤝 Contributing

[Contribution Guidelines]

## 📧 Support

For issues or questions:
- GitHub Issues: [link]
- Email: [email]
- Documentation: [link]

## 🙏 Acknowledgments

- Microsoft SSMA for Oracle
- Anthropic Claude API
- LangChain Framework
- Tavily Search API

---

**Version**: 2.0  
**Last Updated**: 2025-01-17  
**Status**: Production Ready
