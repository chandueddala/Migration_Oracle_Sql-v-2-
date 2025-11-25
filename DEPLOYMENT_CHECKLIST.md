# Production Deployment Checklist

## ✅ Pre-Deployment Checklist

### 1. Environment Setup

#### Python Environment
- [ ] Python 3.8 or higher installed
- [ ] Virtual environment created (recommended)
- [ ] All dependencies installed from `requirements_streamlit.txt`

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements_streamlit.txt
```

#### Database Connectivity
- [ ] Oracle database is accessible from application server
- [ ] SQL Server database is accessible from application server
- [ ] Network ports are open (Oracle: 1521, SQL Server: 1433)
- [ ] Firewall rules configured
- [ ] Oracle client installed (if required)

#### API Keys
- [ ] Anthropic API key obtained and configured
- [ ] OpenAI API key obtained (optional)
- [ ] API keys added to `config/config_enhanced.py`
- [ ] API keys NOT committed to version control

### 2. Directory Structure

- [ ] `logs/` directory exists
- [ ] `output/` directory exists
- [ ] `config/` directory exists with configuration files
- [ ] All required Python modules are present

```bash
# Create required directories
mkdir -p logs output config
```

### 3. Configuration Files

#### `config/config_enhanced.py`
```python
# Required configurations
ANTHROPIC_API_KEY = "your-api-key"  # ✓ Configured
OPENAI_API_KEY = "your-api-key"     # ✓ Configured (optional)
CLAUDE_SONNET_MODEL = "claude-sonnet-4-20250514"  # ✓ Set
MAX_REFLECTION_ITERATIONS = 2       # ✓ Set
MAX_REPAIR_ATTEMPTS = 3            # ✓ Set
```

#### `.streamlit/config.toml` (Optional)
```toml
[server]
port = 8501
headless = false
enableCORS = false

[browser]
gatherUsageStats = false
```

### 4. Security Checks

- [ ] Database credentials stored securely (not in code)
- [ ] API keys stored securely (environment variables or config file)
- [ ] `.gitignore` includes sensitive files:
  ```
  config/config_enhanced.py
  .env
  *.log
  output/*.json
  ```
- [ ] SSL/TLS enabled for database connections (if required)
- [ ] User authentication implemented (if multi-user)

---

## 🚀 Deployment Steps

### Step 1: Test Locally

```bash
# Start application
streamlit run app.py

# Test each workflow step:
# 1. Enter credentials
# 2. Test connections
# 3. Run discovery
# 4. Select objects
# 5. Execute migration
```

**Verify:**
- [ ] All 5 steps work correctly
- [ ] Database connections successful
- [ ] Discovery finds objects
- [ ] Selection UI responds
- [ ] Migration executes without errors

### Step 2: Performance Testing

**Test with sample data:**
- [ ] Small dataset (< 10 tables)
- [ ] Medium dataset (10-50 tables)
- [ ] Large dataset (> 50 tables)

**Monitor:**
- [ ] Response time acceptable
- [ ] Memory usage within limits
- [ ] No memory leaks
- [ ] Error handling works correctly

### Step 3: Production Deployment

#### Option A: Local Server

```bash
# Windows
start_webapp.bat

# Linux/Mac
./start_webapp.sh
```

#### Option B: Remote Server

```bash
# Install as service (systemd on Linux)
sudo nano /etc/systemd/system/migration-webapp.service
```

```ini
[Unit]
Description=Oracle to SQL Server Migration Web App
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/migration-app
ExecStart=/path/to/venv/bin/streamlit run app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable migration-webapp
sudo systemctl start migration-webapp
sudo systemctl status migration-webapp
```

#### Option C: Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements_streamlit.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_streamlit.txt

# Copy application
COPY . .

# Create directories
RUN mkdir -p logs output

# Expose port
EXPOSE 8501

# Run application
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
```

Build and run:

```bash
# Build image
docker build -t migration-webapp .

# Run container
docker run -d \
  -p 8501:8501 \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  --name migration-app \
  migration-webapp
```

### Step 4: Access Configuration

**Local Access:**
```
http://localhost:8501
```

**Remote Access:**
```
http://<server-ip>:8501
```

**Production Domain:**
```
https://migration.yourdomain.com
```

**Reverse Proxy (Nginx):**

```nginx
server {
    listen 80;
    server_name migration.yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🔒 Security Hardening

### 1. Authentication

Add authentication to Streamlit app:

```python
# Add to top of app.py
import streamlit_authenticator as stauth

# Configure authentication
authenticator = stauth.Authenticate(
    {'usernames': {'admin': {'name': 'Admin', 'password': 'hashed_password'}}},
    'cookie_name',
    'signature_key',
    30
)

name, authentication_status, username = authenticator.login('Login', 'main')

if not authentication_status:
    st.stop()
```

### 2. Network Security

- [ ] Application runs behind firewall
- [ ] VPN required for remote access
- [ ] IP whitelisting configured
- [ ] HTTPS enabled (SSL certificate)

### 3. Database Security

- [ ] Use least-privilege database accounts
- [ ] Separate read/write permissions
- [ ] Enable audit logging
- [ ] Encrypt connections (TLS)

### 4. Monitoring

- [ ] Log rotation configured
- [ ] Disk space monitoring
- [ ] CPU/Memory monitoring
- [ ] Error alerting configured

---

## 📊 Monitoring & Maintenance

### Log Files

**Application Logs:**
```
logs/migration_webapp.log
```

**View logs:**
```bash
# Real-time
tail -f logs/migration_webapp.log

# Last 100 lines
tail -n 100 logs/migration_webapp.log

# Search for errors
grep ERROR logs/migration_webapp.log
```

### Disk Space

**Monitor output directory:**
```bash
du -sh output/
```

**Clean old results:**
```bash
# Keep last 30 days
find output/ -name "*.json" -mtime +30 -delete
```

### Performance Metrics

**Key metrics to monitor:**
- Memory usage during migrations
- API call counts and costs
- Average migration time per object
- Success/failure rates

### Backup

**Important files to backup:**
- `config/config_enhanced.py`
- `output/migration_results_*.json`
- `logs/migration_webapp.log`

```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf backup_$DATE.tar.gz config/ output/ logs/
```

---

## 🆘 Troubleshooting

### Common Issues

#### 1. Streamlit won't start

**Symptom:** `streamlit: command not found`

**Solution:**
```bash
pip install streamlit
# or
python -m streamlit run app.py
```

#### 2. Port already in use

**Symptom:** `Port 8501 is already in use`

**Solution:**
```bash
# Use different port
streamlit run app.py --server.port 8502

# Or kill existing process
# Windows:
netstat -ano | findstr :8501
taskkill /PID <pid> /F

# Linux:
lsof -ti:8501 | xargs kill
```

#### 3. Database connection fails

**Symptom:** `Failed to connect to Oracle/SQL Server`

**Solution:**
1. Verify credentials
2. Check network connectivity: `ping <database-host>`
3. Test database is running
4. Check firewall: `telnet <host> <port>`
5. Verify Oracle client installed

#### 4. Out of memory

**Symptom:** `MemoryError` during data migration

**Solution:**
1. Reduce batch size in migration options
2. Migrate tables in smaller groups
3. Increase system memory
4. Use data-only migration separately

#### 5. LLM API errors

**Symptom:** `API key invalid` or `Rate limit exceeded`

**Solution:**
1. Verify API key is correct in config
2. Check API quota and billing
3. Reduce concurrent requests
4. Add retry logic with backoff

---

## 📋 Post-Deployment Verification

### 1. Functional Testing

- [ ] Login/authentication works
- [ ] All 5 steps accessible
- [ ] Discovery completes successfully
- [ ] Object selection UI responsive
- [ ] Migration executes correctly
- [ ] Results downloadable

### 2. Data Validation

After migration:
- [ ] Row counts match between Oracle and SQL Server
- [ ] Data types converted correctly
- [ ] Primary keys and indexes created
- [ ] Foreign key relationships maintained
- [ ] Triggers functioning correctly

```sql
-- Verify row counts
SELECT COUNT(*) FROM Oracle.CUSTOMERS;  -- Oracle
SELECT COUNT(*) FROM dbo.CUSTOMERS;      -- SQL Server

-- Verify objects
SELECT name, type_desc FROM sys.objects
WHERE name LIKE 'PKG_%';
```

### 3. Performance Testing

- [ ] Query performance acceptable
- [ ] Index usage optimized
- [ ] Statistics updated
- [ ] Execution plans reviewed

### 4. User Acceptance Testing

- [ ] Users can access application
- [ ] UI is intuitive
- [ ] Migrations complete successfully
- [ ] Results meet expectations
- [ ] Documentation is clear

---

## 🎓 Training & Documentation

### User Training

**Topics to cover:**
1. How to start the application
2. 5-step migration workflow
3. Object selection best practices
4. Conflict resolution options
5. Interpreting results
6. Troubleshooting common issues

### Administrator Training

**Topics to cover:**
1. Installation and configuration
2. Security hardening
3. Monitoring and logging
4. Backup and recovery
5. Performance tuning
6. Incident response

### Documentation

**Provide users with:**
- [ ] WEB_APP_README.md
- [ ] QUICK_START.md
- [ ] Troubleshooting guide
- [ ] FAQ document
- [ ] Contact information for support

---

## ✅ Go-Live Checklist

### Final Pre-Launch

- [ ] All dependencies installed and tested
- [ ] Configuration files reviewed and validated
- [ ] Security hardening complete
- [ ] Monitoring configured
- [ ] Backups configured
- [ ] Documentation complete
- [ ] User training complete
- [ ] Rollback plan prepared

### Launch

- [ ] Start application
- [ ] Verify accessibility
- [ ] Test with real data (small dataset)
- [ ] Monitor logs for errors
- [ ] Verify performance metrics
- [ ] User feedback collected

### Post-Launch

- [ ] Monitor for 24 hours
- [ ] Review logs daily for first week
- [ ] Address any issues immediately
- [ ] Collect user feedback
- [ ] Plan improvements

---

## 📞 Support & Maintenance

### Support Plan

**Contact Information:**
- Technical Support: support@yourdomain.com
- Administrator: admin@yourdomain.com
- Emergency: +1-XXX-XXX-XXXX

**Response Times:**
- Critical (P1): 1 hour
- High (P2): 4 hours
- Medium (P3): 1 business day
- Low (P4): 3 business days

### Maintenance Schedule

**Weekly:**
- Review logs for errors
- Check disk space
- Verify backups

**Monthly:**
- Review performance metrics
- Update dependencies
- Clean old output files
- Review and update documentation

**Quarterly:**
- Security audit
- Performance optimization
- User feedback review
- Feature planning

---

## 🎉 Congratulations!

Your Oracle to SQL Server Migration Web Application is now **production-ready**!

**Key Features Deployed:**
- ✅ Professional web interface
- ✅ Upfront selection workflow
- ✅ LLM-powered package decomposition
- ✅ Automatic error repair
- ✅ Real-time progress tracking
- ✅ Production-grade security
- ✅ Comprehensive logging
- ✅ Industry best practices

**Access your application at:**
```
http://localhost:8501
```

**Need help?**
- See: WEB_APP_README.md
- Logs: logs/migration_webapp.log
- Documentation: docs/ folder

**Happy migrating!** 🚀
