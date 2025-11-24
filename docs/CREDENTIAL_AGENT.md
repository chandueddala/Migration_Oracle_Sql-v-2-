# Credential Agent Documentation

## Overview

The **Credential Agent** is an intelligent agentic system that handles database credential collection, validation, and retry logic for the Oracle to SQL Server migration system.

### Key Features

✅ **Intelligent Retry Logic** - Up to 5 retry attempts (configurable)
✅ **Error Categorization** - Identifies authentication, network, and configuration issues
✅ **User-Friendly Feedback** - Provides actionable suggestions based on error patterns
✅ **Secure by Design** - Never sends credentials to LLMs
✅ **Flexible Credential Keys** - Supports both 'user' and 'username' keys

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Credential Agent                         │
│                                                              │
│  ┌────────────┐    ┌─────────────┐    ┌────────────────┐  │
│  │  Collect   │───▶│  Normalize  │───▶│   Validate     │  │
│  │ Credentials│    │ Credentials │    │  Connections   │  │
│  └────────────┘    └─────────────┘    └────────────────┘  │
│                                              │              │
│                                              ▼              │
│                                        ┌──────────┐        │
│                                        │ Success? │        │
│                                        └──────────┘        │
│                                         Yes │ │ No         │
│                                             │ │            │
│                                      Return │ │ Retry      │
│                                             │ │ (Max 5x)   │
│                                             │ │            │
│                                             ▼ ▼            │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Environment Variables

Edit [`.env`](.env) to configure retry attempts:

```env
# Maximum credential retry attempts (1-10)
MAX_CREDENTIAL_ATTEMPTS=5
```

### Code Configuration

In [`config/config_enhanced.py`](config/config_enhanced.py:50):

```python
MAX_CREDENTIAL_ATTEMPTS = int(os.getenv("MAX_CREDENTIAL_ATTEMPTS", "5"))
```

---

## Usage

### 1. Standalone Testing

Test the credential agent independently:

```bash
python test_credential_agent.py
```

This will:
- Prompt for Oracle and SQL Server credentials
- Validate connections
- Retry up to 5 times on failure
- Provide intelligent feedback

### 2. Integration with Migration Workflow

The agent is automatically used in the main migration workflow:

```python
from agents.credential_agent import CredentialAgent

# Initialize agent
credential_agent = CredentialAgent()

# Run credential collection with retry logic
oracle_creds, sqlserver_creds = credential_agent.run()

# Check success
if oracle_creds and sqlserver_creds:
    print("✅ Credentials validated")
else:
    print("❌ Validation failed after retries")
```

### 3. Custom Retry Attempts

Override the default retry count:

```python
# Use 3 attempts instead of default
credential_agent = CredentialAgent(max_attempts=3)
oracle_creds, sqlserver_creds = credential_agent.run()
```

---

## Error Handling

### Error Categories

The agent intelligently categorizes errors:

| Category | Description | Suggestion |
|----------|-------------|------------|
| `authentication` | Login failed | Check username and password |
| `password` | Password issue | Verify password (case-sensitive) |
| `username` | Username issue | Verify username (case-sensitive) |
| `network` | Connection timeout | Check server is running and accessible |
| `service_name` | Oracle service not found | Verify service name (e.g., XEPDB1, ORCL) |
| `database` | Database not found | Verify database name exists |
| `port` | Port issue | Check port (Oracle: 1521, SQL Server: 1433) |
| `timeout` | Connection timeout | Server may be slow or unreachable |
| `permission` | Access denied | User account may lack permissions |
| `missing_field` | Missing credential | Provide all required fields |

### Example Error Flow

```
Attempt 1/5: User enters incorrect password

❌ Oracle Connection Issues:
   Error Type: authentication
   💡 Check that your username and password are correct

🔄 Retry with different credentials? (y/n): y
```

---

## Security Features

### 1. No LLM Exposure

**The credential agent NEVER sends credentials to LLMs.** All validation is done through direct database connections only.

```python
def _validate_credentials(self, oracle_creds, sqlserver_creds):
    """
    Validate credentials WITHOUT LLM involvement.
    Only error patterns (not credentials) are analyzed.
    """
    # Direct database connection attempt
    oracle_conn = OracleConnector(oracle_creds)
    if oracle_conn.connect():
        # Success - no LLM involved
        return {'success': True}
```

### 2. Credential Masking

All credentials are masked in logs:

```python
SecurityLogger.log_credential_usage(
    "oracle",
    SecurityLogger.mask_credential(password)  # "Yo*****************rd"
)
```

### 3. Secure Storage

Credentials are:
- Never written to disk
- Never sent over network (except to target databases)
- Cleared from memory after validation

---

## Key Mismatch Fix

### The Problem

Previous versions had a key mismatch:

```python
# Collection used 'username'
oracle_creds = {"username": "scott", ...}

# But connectors expected 'user'
oracledb.connect(user=creds['user'])  # ❌ KeyError!
```

### The Solution

The agent normalizes credentials:

```python
def _normalize_oracle_credentials(self, creds):
    """Map 'username' -> 'user' for compatibility"""
    normalized = creds.copy()
    if 'username' in normalized:
        normalized['user'] = normalized.pop('username')
    return normalized
```

Connectors now support both keys:

```python
# Support both 'user' and 'username'
username = self.credentials.get('user') or self.credentials.get('username')
if not username:
    raise ValueError("Missing 'user' or 'username' in credentials")
```

---

## Files Modified

### New Files

1. [`agents/credential_agent.py`](agents/credential_agent.py) - Main agent implementation
2. [`test_credential_agent.py`](test_credential_agent.py) - Standalone test script
3. [`docs/CREDENTIAL_AGENT.md`](docs/CREDENTIAL_AGENT.md) - This documentation

### Modified Files

1. [`database/oracle_connector.py`](database/oracle_connector.py:26-49)
   - Added support for both 'user' and 'username' keys
   - Improved error handling with specific error types

2. [`database/sqlserver_connector.py`](database/sqlserver_connector.py:26-55)
   - Added support for both 'user' and 'username' keys
   - Improved error handling with specific error types

3. [`utils/migration_workflow.py`](utils/migration_workflow.py:162-175)
   - Replaced manual credential collection with CredentialAgent
   - Deprecated old `collect_credentials()` and `validate_credentials()`

4. [`config/config_enhanced.py`](config/config_enhanced.py:50)
   - Added `MAX_CREDENTIAL_ATTEMPTS` configuration

5. [`.env`](.env:48-49)
   - Added `MAX_CREDENTIAL_ATTEMPTS=5` setting

---

## API Reference

### `CredentialAgent`

Main agent class for credential management.

#### Constructor

```python
CredentialAgent(max_attempts: int = None)
```

**Parameters:**
- `max_attempts` (int, optional): Maximum retry attempts. Defaults to `MAX_CREDENTIAL_ATTEMPTS` from config.

**Example:**
```python
agent = CredentialAgent()  # Uses default from config
agent = CredentialAgent(max_attempts=3)  # Custom retry count
```

#### Methods

##### `run() -> Tuple[Optional[Dict], Optional[Dict]]`

Execute credential collection and validation loop.

**Returns:**
- `(oracle_creds, sqlserver_creds)` on success
- `(None, None)` on failure after max attempts

**Example:**
```python
oracle_creds, sqlserver_creds = agent.run()
if oracle_creds and sqlserver_creds:
    print("Success!")
```

---

## Troubleshooting

### Issue: "Missing 'user' or 'username' in credentials"

**Solution:** Make sure you're entering a username when prompted.

### Issue: "Oracle connection failed: 'user'"

**Solution:** This was the old bug. Update to the latest version with the credential agent.

### Issue: Agent exits after 5 failed attempts

**Solution:**
1. Verify database servers are running
2. Check connection parameters (host, port, service name)
3. Test credentials using database clients (SQL*Plus, SSMS)
4. Increase `MAX_CREDENTIAL_ATTEMPTS` in `.env`

### Issue: Credentials are correct but still failing

**Check:**
- Oracle listener is running: `lsnrctl status`
- SQL Server is accepting connections
- Firewall allows database ports (1521, 1433)
- User has necessary permissions

---

## Testing

### Manual Test

```bash
# Run standalone test
python test_credential_agent.py

# Expected output:
# ✅ Oracle connection successful
# ✅ SQL Server connection successful
# 🎉 All database connections validated successfully!
```

### Integration Test

```bash
# Run full migration (uses credential agent automatically)
python main.py
```

### Unit Test Example

```python
def test_credential_agent():
    """Test credential agent with valid credentials"""
    agent = CredentialAgent(max_attempts=1)

    # Mock input with valid credentials
    with patch('builtins.input', side_effect=[
        'localhost', '1521', 'XEPDB1', 'scott', 'tiger',  # Oracle
        'localhost', 'master', 'sa', 'YourStrong(!)Password'  # SQL Server
    ]):
        oracle_creds, sqlserver_creds = agent.run()
        assert oracle_creds is not None
        assert sqlserver_creds is not None
```

---

## Future Enhancements

Potential improvements for future versions:

1. **Credential Caching** - Securely cache validated credentials during session
2. **Connection Pooling** - Reuse validated connections
3. **Multi-Database Support** - Extend to PostgreSQL, MySQL, etc.
4. **Async Validation** - Validate Oracle and SQL Server in parallel
5. **Integration Testing** - Test schema/table access permissions
6. **Credential Import** - Load from secure credential stores (Azure Key Vault, AWS Secrets Manager)

---

## Summary

The Credential Agent provides:

✅ **Robust Error Handling** - Categorizes and explains errors
✅ **User-Friendly Interface** - Clear prompts and feedback
✅ **Security First** - Never exposes credentials to LLMs
✅ **Configurable Retries** - Up to 10 retry attempts
✅ **Backward Compatible** - Works with existing migration workflow

For support, see [logs/migration.log](logs/migration.log) or create an issue.
