# Frontend Integration Guide

## Overview

This migration system is **frontend-ready** with a complete **upfront selection workflow**. All user selections happen at the start, then migration runs without interruption.

Perfect for building a web UI, REST API, or desktop application!

## Key Features for Frontend

### 1. **Upfront Selection Pattern**
- ✅ Discover ALL database objects first
- ✅ User selects EVERYTHING before migration starts
- ✅ NO interruptions during migration
- ✅ Structured JSON output at every step

### 2. **JSON-Based Communication**
All data structures export to JSON:
- `discovery_result.json` - All discovered objects
- `migration_selection.json` - User's selections
- `migration_results.json` - Migration outcomes

### 3. **Stateless Design**
- Each step can be run independently
- Selections can be saved and loaded
- Perfect for REST API architecture

## Workflow

```
┌─────────────────────────────────────────────────────────┐
│  STEP 1: CREDENTIALS                                    │
│  Input: Oracle & SQL Server connection details         │
│  Output: Validated credentials                         │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  STEP 2: COMPREHENSIVE DISCOVERY                        │
│  - Scans entire Oracle database                         │
│  - Returns ALL objects (tables, packages, etc.)         │
│  - Includes metadata (row counts, sizes, status)        │
│  Output: discovery_result.json                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  STEP 3: USER SELECTION (Frontend displays options)    │
│  - Which tables to migrate                              │
│  - Which tables to include data                         │
│  - Which packages/procedures/functions                  │
│  - Optional: views, sequences, triggers                 │
│  Output: migration_selection.json                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  STEP 4: MIGRATION EXECUTION (No user interaction!)    │
│  - Migrates all selected objects                        │
│  - Real-time progress updates                           │
│  - Automatic error handling & repair                    │
│  Output: migration_results.json                         │
└─────────────────────────────────────────────────────────┘
```

## JSON Data Structures

### 1. Discovery Result (`output/discovery_result.json`)

```json
{
  "summary": {
    "total_objects": 156,
    "discovery_time": "3.45s",
    "errors": []
  },
  "counts": {
    "tables": 45,
    "packages": 12,
    "procedures": 28,
    "functions": 35,
    "triggers": 18,
    "views": 10,
    "sequences": 8,
    "types": 0,
    "synonyms": 0
  },
  "objects": {
    "tables": [
      {
        "name": "CUSTOMERS",
        "type": "TABLE",
        "status": "VALID",
        "row_count": 15678,
        "size_mb": 12.5,
        "created": "2024-01-15",
        "last_modified": "2024-11-20",
        "metadata": {}
      }
    ],
    "packages": [
      {
        "name": "PKG_LOAN_PROCESSOR",
        "type": "PACKAGE",
        "status": "VALID",
        "created": "2024-03-10",
        "metadata": {
          "member_count": 5
        }
      }
    ]
  }
}
```

### 2. Migration Selection (`output/migration_selection.json`)

```json
{
  "tables": {
    "selected": ["CUSTOMERS", "ORDERS", "PRODUCTS"],
    "with_data": ["CUSTOMERS", "ORDERS"],
    "schema_only": ["PRODUCTS"],
    "count": 3
  },
  "packages": {
    "selected": ["PKG_LOAN_PROCESSOR", "PKG_ACCOUNT_MANAGER"],
    "count": 2
  },
  "procedures": {
    "selected": ["PROC_CALCULATE_INTEREST", "PROC_VALIDATE_USER"],
    "count": 2
  },
  "functions": {
    "selected": ["FUNC_GET_STATUS", "FUNC_FORMAT_DATE"],
    "count": 2
  },
  "triggers": {
    "selected": ["TRG_AUDIT_CUSTOMERS"],
    "count": 1
  },
  "views": {
    "selected": [],
    "count": 0
  },
  "sequences": {
    "selected": ["SEQ_CUSTOMER_ID"],
    "count": 1
  },
  "totals": {
    "objects": 11,
    "tables_with_data": 2,
    "tables_schema_only": 1
  },
  "options": {
    "migrate_all_tables": false,
    "migrate_all_data": false,
    "migrate_all_packages": false,
    "migrate_all_code": false
  }
}
```

### 3. Migration Results (`output/migration_results.json`)

```json
{
  "selection": { /* same as migration_selection.json */ },
  "results": {
    "tables": [
      {
        "object_name": "CUSTOMERS",
        "object_type": "TABLE",
        "status": "success",
        "message": "Table migrated successfully",
        "oracle_code": "...",
        "tsql_code": "...",
        "data_migration": {
          "status": "success",
          "rows_migrated": 15678,
          "message": "Successfully migrated 15678 rows"
        }
      }
    ],
    "packages": [
      {
        "object_name": "PKG_LOAN_PROCESSOR",
        "object_type": "PACKAGE",
        "status": "success",
        "components_migrated": 5,
        "components": [
          {
            "name": "PKG_LOAN_PROCESSOR_PROCESS_LOAN",
            "type": "PROCEDURE",
            "status": "success"
          }
        ]
      }
    ]
  },
  "summary": {
    "total": 11,
    "success": 10,
    "failed": 1
  },
  "cost": "Total Cost: $0.42 | Anthropic: $0.38 (Claude Sonnet 4) | OpenAI: $0.04"
}
```

## Frontend Implementation Examples

### Example 1: REST API Endpoints

```python
# api.py - Flask REST API wrapper
from flask import Flask, request, jsonify
from migrate_upfront import *
import json

app = Flask(__name__)

@app.route('/api/discovery', methods=['POST'])
def discover_database():
    """
    POST /api/discovery
    Body: { "oracle_creds": {...}, "sqlserver_creds": {...} }
    Returns: discovery_result.json
    """
    oracle_creds = request.json['oracle_creds']

    oracle_conn = OracleConnector(oracle_creds)
    if not oracle_conn.connect():
        return jsonify({"error": "Connection failed"}), 400

    discovery = ComprehensiveDiscovery(oracle_conn)
    result = discovery.discover_all()

    oracle_conn.disconnect()

    return jsonify(discovery.to_json(result))


@app.route('/api/migrate', methods=['POST'])
def start_migration():
    """
    POST /api/migrate
    Body: {
        "oracle_creds": {...},
        "sqlserver_creds": {...},
        "selection": { ... migration_selection.json ... }
    }
    Returns: migration_results.json
    """
    oracle_creds = request.json['oracle_creds']
    sqlserver_creds = request.json['sqlserver_creds']
    selection_data = request.json['selection']

    # Convert JSON to MigrationSelection object
    selection = MigrationSelection(
        selected_tables=selection_data['tables']['selected'],
        tables_with_data=selection_data['tables']['with_data'],
        selected_packages=selection_data['packages']['selected'],
        # ... etc
    )

    # Run migration (background task recommended)
    orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, CostTracker())

    results = {
        "tables": [],
        "packages": [],
        # ... migrate each object
    }

    return jsonify(results)


@app.route('/api/migrate/status/<task_id>', methods=['GET'])
def migration_status(task_id):
    """
    GET /api/migrate/status/{task_id}
    Returns: Real-time migration progress
    """
    # Use Celery, RQ, or background tasks
    return jsonify({
        "task_id": task_id,
        "status": "in_progress",
        "progress": {
            "current": 5,
            "total": 11,
            "current_object": "PKG_LOAN_PROCESSOR"
        }
    })
```

### Example 2: React Frontend Component

```jsx
// MigrationWizard.jsx
import React, { useState } from 'react';

export default function MigrationWizard() {
  const [step, setStep] = useState(1);
  const [discovery, setDiscovery] = useState(null);
  const [selection, setSelection] = useState({
    tables: { selected: [], with_data: [] },
    packages: { selected: [] }
  });

  // Step 1: Connect & Discover
  const handleDiscovery = async (credentials) => {
    const response = await fetch('/api/discovery', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ oracle_creds: credentials })
    });

    const data = await response.json();
    setDiscovery(data);
    setStep(2);
  };

  // Step 2: User Selection
  const handleTableSelection = (selectedTables) => {
    setSelection({
      ...selection,
      tables: { ...selection.tables, selected: selectedTables }
    });
  };

  // Step 3: Start Migration
  const handleMigration = async () => {
    const response = await fetch('/api/migrate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        oracle_creds: credentials,
        sqlserver_creds: credentials,
        selection: selection
      })
    });

    const results = await response.json();
    // Display results
  };

  return (
    <div>
      {step === 1 && <CredentialsForm onSubmit={handleDiscovery} />}
      {step === 2 && (
        <SelectionPanel
          discovery={discovery}
          selection={selection}
          onTableSelect={handleTableSelection}
          onProceed={() => setStep(3)}
        />
      )}
      {step === 3 && (
        <MigrationProgress onStart={handleMigration} />
      )}
    </div>
  );
}
```

### Example 3: Desktop Application (Electron)

```javascript
// main.js - Electron main process
const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');

ipcMain.handle('discover-database', async (event, credentials) => {
  // Spawn Python process
  const python = spawn('python', ['migrate_upfront.py', '--discover-only']);

  // Capture JSON output
  let output = '';
  python.stdout.on('data', (data) => {
    output += data.toString();
  });

  return new Promise((resolve) => {
    python.on('close', () => {
      // Parse output/discovery_result.json
      const fs = require('fs');
      const result = JSON.parse(
        fs.readFileSync('output/discovery_result.json', 'utf8')
      );
      resolve(result);
    });
  });
});
```

## Running the System

### Command Line (Interactive)

```bash
# Full interactive workflow
python migrate_upfront.py
```

### Python API (Programmatic)

```python
from migrate_upfront import *
from utils.comprehensive_discovery import ComprehensiveDiscovery
from utils.interactive_selection import MigrationSelection

# Step 1: Credentials
oracle_creds = {
    "host": "localhost",
    "port": 1521,
    "service_name": "XEPDB1",
    "username": "your_user",
    "password": "your_pass"
}

sqlserver_creds = {
    "server": "localhost",
    "database": "MigrationTarget",
    "username": "sa",
    "password": "your_pass"
}

# Step 2: Discovery
oracle_conn = OracleConnector(oracle_creds)
oracle_conn.connect()

discovery = ComprehensiveDiscovery(oracle_conn)
result = discovery.discover_all()

# Save to JSON
import json
with open('discovery.json', 'w') as f:
    json.dump(discovery.to_json(result), f, indent=2)

oracle_conn.disconnect()

# Step 3: Build selection programmatically (or load from frontend)
selection = MigrationSelection(
    selected_tables=["CUSTOMERS", "ORDERS"],
    tables_with_data=["CUSTOMERS"],
    tables_schema_only=["ORDERS"],
    selected_packages=["PKG_LOAN_PROCESSOR"]
)

# Step 4: Run migration
cost_tracker = CostTracker()
orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, cost_tracker)

# Migrate each selected object
for table_name in selection.selected_tables:
    result = orchestrator.orchestrate(table_name, "TABLE")

    # Migrate data if selected
    if table_name in selection.tables_with_data:
        data_result = migrate_table_data(oracle_creds, sqlserver_creds, table_name)
        print(f"Data migration: {data_result['rows_migrated']} rows")
```

## Real-Time Progress Updates

For frontend progress bars, use callbacks or websockets:

```python
# progress_tracker.py
class ProgressTracker:
    def __init__(self, websocket=None):
        self.websocket = websocket
        self.current = 0
        self.total = 0

    def set_total(self, total):
        self.total = total
        self.emit_progress()

    def increment(self, object_name, status):
        self.current += 1
        self.emit_progress(object_name, status)

    def emit_progress(self, object_name=None, status=None):
        data = {
            "current": self.current,
            "total": self.total,
            "percentage": (self.current / self.total * 100) if self.total > 0 else 0
        }

        if object_name:
            data["current_object"] = object_name
            data["status"] = status

        if self.websocket:
            self.websocket.send(json.dumps(data))

# Use in migration loop
tracker = ProgressTracker(websocket=ws)
tracker.set_total(selection.total_objects())

for table_name in selection.selected_tables:
    result = orchestrator.orchestrate(table_name, "TABLE")
    tracker.increment(table_name, result['status'])
```

## Advanced: Background Task Processing

For production frontends, use background task queues:

```python
# tasks.py - Celery tasks
from celery import Celery
import json

celery = Celery('migration_tasks', broker='redis://localhost:6379')

@celery.task(bind=True)
def migrate_database_task(self, oracle_creds, sqlserver_creds, selection_json):
    """
    Background task for migration
    Updates state for real-time progress
    """
    selection = MigrationSelection(**selection_json)

    # Update task state
    self.update_state(
        state='PROGRESS',
        meta={'current': 0, 'total': selection.total_objects()}
    )

    orchestrator = MigrationOrchestrator(oracle_creds, sqlserver_creds, CostTracker())

    results = []
    for i, table_name in enumerate(selection.selected_tables):
        result = orchestrator.orchestrate(table_name, "TABLE")
        results.append(result)

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i + 1,
                'total': selection.total_objects(),
                'current_object': table_name
            }
        )

    return {'status': 'completed', 'results': results}

# Frontend polls task status
# GET /api/migrate/status/{task_id}
# Returns: {"state": "PROGRESS", "current": 5, "total": 11}
```

## Testing

### Unit Test Discovery

```python
# test_frontend_integration.py
import pytest
from utils.comprehensive_discovery import ComprehensiveDiscovery

def test_discovery_json_output():
    # Mock Oracle connector
    discovery = ComprehensiveDiscovery(mock_oracle_conn)
    result = discovery.discover_all()

    json_output = discovery.to_json(result)

    assert 'summary' in json_output
    assert 'counts' in json_output
    assert 'objects' in json_output
    assert json_output['summary']['total_objects'] > 0
```

### Integration Test Selection

```python
def test_migration_selection_json():
    selection = MigrationSelection(
        selected_tables=["TEST_TABLE"],
        tables_with_data=["TEST_TABLE"]
    )

    json_output = selection.to_json()

    assert json_output['tables']['count'] == 1
    assert json_output['totals']['objects'] == 1
```

## Production Deployment Checklist

### Backend
- ✅ Set up REST API (Flask/FastAPI/Django)
- ✅ Configure background task queue (Celery/RQ)
- ✅ Add authentication & authorization
- ✅ Set up database for storing migration history
- ✅ Configure logging & monitoring
- ✅ Add rate limiting for LLM API calls

### Frontend
- ✅ Build discovery results UI
- ✅ Create object selection interface
- ✅ Implement progress tracking
- ✅ Add error handling & retry logic
- ✅ Store user credentials securely
- ✅ Display migration results & reports

### Infrastructure
- ✅ Secure API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY)
- ✅ Network access to Oracle & SQL Server
- ✅ Sufficient disk space for logs & results
- ✅ Redis/RabbitMQ for task queue
- ✅ WebSocket support for real-time updates

## Summary

This migration system is **100% frontend-ready**:

1. ✅ **Upfront selection** - No interruptions during migration
2. ✅ **JSON everywhere** - Perfect for REST APIs
3. ✅ **Stateless design** - Easy to scale
4. ✅ **Real-time progress** - WebSocket/polling support
5. ✅ **Background tasks** - Non-blocking execution
6. ✅ **Comprehensive metadata** - Row counts, sizes, status

**Start building your frontend now!**

The migration engine handles all the complexity - your frontend just needs to:
- Display discovery results
- Collect user selections
- Show migration progress
- Display results

All the heavy lifting (LLM conversion, error repair, validation) is handled automatically!
