# 📋 Oracle Loans Schema - Complete Feature List

## 🎯 Overview
**seed_loans_schema.py** creates a comprehensive Loan Processing System in Oracle with **22+ database objects** for migration testing.

---

## 📊 Database Objects Created

### 1. **📋 TABLES (5 Tables)**

#### **STG_LOAN_APPS** - Staging Table
- `stg_id` (NUMBER, PK) - Staging ID
- `payload` (CLOB) - JSON payload with loan application data
- `created_on` (TIMESTAMP) - Record creation timestamp

**Purpose:** Receives raw JSON loan applications for batch processing

---

#### **LOANS** - Main Loan Table
- `loan_id` (NUMBER, PK) - Unique loan identifier
- `external_app_id` (VARCHAR2) - External application reference
- `customer_id` (NUMBER) - Customer identifier
- `principal` (NUMBER) - Loan amount
- `annual_rate` (NUMBER) - Interest rate (%)
- `term_months` (NUMBER) - Loan duration in months
- `start_date` (DATE) - Loan start date
- `status` (VARCHAR2) - Loan status (ACTIVE, CLOSED, etc.)
- `outstanding_balance` (NUMBER) - Current balance owed
- `created_on` (TIMESTAMP) - Record creation

**Purpose:** Stores active and historical loan records

---

#### **LOAN_SCHEDULE** - Amortization Schedule
- `schedule_id` (NUMBER, PK) - Schedule entry ID
- `loan_id` (NUMBER, FK) - References loans
- `due_date` (DATE) - Payment due date
- `period_no` (NUMBER) - Period number (1, 2, 3...)
- `principal_amt` (NUMBER) - Principal portion of payment
- `interest_amt` (NUMBER) - Interest portion of payment
- `outstanding` (NUMBER) - Balance after payment

**Purpose:** Stores monthly payment schedule (amortization table)

---

#### **LOAN_PAYMENTS** - Payment History
- `payment_id` (NUMBER, PK) - Payment identifier
- `loan_id` (NUMBER, FK) - References loans
- `paid_on` (DATE) - Payment date
- `amount` (NUMBER) - Total payment amount
- `applied_to_principal` (NUMBER) - Principal portion
- `applied_to_interest` (NUMBER) - Interest portion

**Purpose:** Records all customer payments

---

#### **LOAN_AUDIT** - Audit Trail
- `audit_id` (NUMBER, PK) - Audit entry ID
- `stg_id` (NUMBER, FK) - References staging
- `status` (VARCHAR2) - Event status
- `message` (VARCHAR2) - Audit message
- `processed_on` (TIMESTAMP) - Event timestamp

**Purpose:** Tracks all loan processing events and changes

---

### 2. **🔢 SEQUENCES (4 Sequences)**

1. **LOAN_SEQ** - Starts at 500,000
   - Used for: `loan_id`, `schedule_id`

2. **APP_SEQ** - Starts at 1
   - Used for: `stg_id`, `audit_id`

3. **PAYMENT_SEQ** - Starts at 1,000
   - Used for: `payment_id`

4. **AUDIT_SEQ** - Starts at 100
   - Used for: `audit_id`

**Purpose:** Generate unique IDs for all primary keys

---

### 3. **⚙️ STANDALONE PROCEDURES (3 Procedures)**

#### **APPLY_LATE_FEE**(p_loan_id, p_fee_amount)
- **Parameters:**
  - `p_loan_id IN NUMBER` - Loan to charge
  - `p_fee_amount IN NUMBER DEFAULT 25` - Fee amount
- **Features:**
  - Adds late fee to outstanding balance
  - Creates audit record
  - Handles loan not found errors
  - Uses COMMIT
- **Use Case:** Charge late payment fees

---

#### **CLOSE_LOAN**(p_loan_id)
- **Parameters:**
  - `p_loan_id IN NUMBER` - Loan to close
- **Features:**
  - Validates balance is zero
  - Updates status to 'CLOSED'
  - Creates audit record
  - Uses FOR UPDATE (row locking)
  - Error handling for non-zero balance
- **Use Case:** Close fully paid loans

---

#### **GENERATE_MONTHLY_REPORT**(p_month_year)
- **Parameters:**
  - `p_month_year IN VARCHAR2` - Format: 'YYYY-MM'
- **Features:**
  - Counts active loans
  - Sums disbursed amount
  - Sums collected payments
  - Uses DBMS_OUTPUT for reporting
  - Date-based aggregation
- **Use Case:** Monthly financial reporting

---

### 4. **🔧 STANDALONE FUNCTIONS (4 Functions)**

#### **GET_LOAN_STATUS**(p_loan_id) RETURN VARCHAR2
- **Parameters:** Loan ID
- **Returns:** Loan status or 'NOT_FOUND' / 'ERROR'
- **Features:**
  - Exception handling
  - NULL-safe
- **Use Case:** Quick status lookup

---

#### **CALCULATE_TOTAL_INTEREST**(p_loan_id) RETURN NUMBER
- **Parameters:** Loan ID
- **Returns:** Total interest amount
- **Features:**
  - Sums from loan_schedule
  - Returns 0 on error
  - Uses NVL for NULL safety
- **Use Case:** Calculate total interest charged

---

#### **GET_OVERDUE_COUNT**(p_customer_id) RETURN NUMBER
- **Parameters:** Customer ID (optional, NULL = all customers)
- **Returns:** Count of overdue loans
- **Features:**
  - Conditional logic (IF NULL)
  - JOIN between loans and schedule
  - Date comparison with SYSDATE
  - Customer-specific or global count
- **Use Case:** Identify delinquent loans

---

#### **VALIDATE_PAYMENT_AMOUNT**(p_loan_id, p_amount) RETURN VARCHAR2
- **Parameters:**
  - Loan ID
  - Payment amount
- **Returns:** 'VALID', 'INSUFFICIENT', 'OVERPAYMENT', or 'LOAN_NOT_FOUND'
- **Features:**
  - Business rule: Min payment = max($10, 1% of balance)
  - Prevents overpayment
  - Detailed error messages
- **Use Case:** Validate payment before processing

---

### 5. **📦 PACKAGE (1 Package)**

#### **PKG_LOAN_PROCESSOR** - Comprehensive Loan Processing Package

**Package Spec (2 Public Procedures):**
- `PROCESS_BATCH(p_batch_size)` - Process loan applications
- `DRY_RUN(p_batch_size)` - Test processing without commits

**Package Body (7 Internal Components):**

##### **Private Procedure: AUDIT_WRITE**
- Parameters: stg_id, status, message
- Features:
  - PRAGMA AUTONOMOUS_TRANSACTION
  - Independent audit logging
  - Never fails (exception handler)

##### **Private Function: PERFORM_CREDIT_CHECK**
- Parameters: customer_id, payload
- Returns: 'PASS', 'REVIEW', or 'FAIL'
- Features:
  - Mock credit scoring (uses MOD)
  - Business rules for approval

##### **Private Function: CALC_MONTHLY_PAYMENT**
- Parameters: principal, annual_rate, term_months
- Returns: Monthly payment amount (EMI)
- Features:
  - Full EMI formula: P * (r / (1 - (1+r)^-n))
  - Handles zero interest
  - Input validation
  - Precise rounding

##### **Private Procedure: CREATE_SCHEDULE**
- Parameters: loan_id, principal, rate, term, start_date
- Features:
  - Generates full amortization schedule
  - PL/SQL collections (TYPE...TABLE OF)
  - Bulk insert with FORALL
  - Interest calculation per period
  - Compound interest logic
  - Outstanding balance tracking

##### **Private Procedure: PARSE_PAYLOAD**
- Parameters: CLOB payload → OUT parameters
- Features:
  - **JSON_TABLE** parsing
  - Extracts: external_app_id, customer_id, principal, rate, term, start_date
  - Date parsing (TO_DATE)
  - Validation of required fields
  - Error handling

##### **Private Procedure: PROCESS_SINGLE**
- Parameters: stg_id, payload
- Features:
  - Complete loan workflow:
    1. Parse JSON
    2. Credit check
    3. Handle rejection/review
    4. Check duplicate (SELECT...INTO)
    5. INSERT or UPDATE loan
    6. DELETE old schedule
    7. CREATE new schedule
    8. Audit success/failure
  - SAVEPOINT and ROLLBACK
  - Exception handling

##### **Public Procedure: PROCESS_BATCH**
- Parameters: batch_size (default 50)
- Features:
  - Cursor with FOR UPDATE SKIP LOCKED
  - Batch processing
  - SAVEPOINT per row
  - Periodic COMMIT (every 20 rows)
  - DELETE processed records
  - Error isolation (one failure doesn't stop batch)

##### **Public Procedure: DRY_RUN**
- Parameters: batch_size (default 20)
- Features:
  - Test mode (no commits)
  - Validates JSON parsing
  - DBMS_OUTPUT for results
  - No database changes

---

### 6. **⚡ TRIGGERS (3 Triggers)**

#### **TRG_LOAN_AUDIT**
- **Type:** AFTER INSERT OR UPDATE OR DELETE
- **On:** LOANS
- **Level:** FOR EACH ROW
- **Features:**
  - Automatic audit trail
  - Detects operation type (INSERTING, UPDATING, DELETING)
  - Creates audit record
  - Uses :NEW and :OLD

---

#### **TRG_PAYMENT_VALIDATION**
- **Type:** BEFORE INSERT
- **On:** LOAN_PAYMENTS
- **Level:** FOR EACH ROW
- **Features:**
  - Validates loan is ACTIVE
  - Validates amount > 0
  - Prevents invalid payments
  - RAISE_APPLICATION_ERROR

---

#### **TRG_AUTO_PAYMENT_ID**
- **Type:** BEFORE INSERT
- **On:** LOAN_PAYMENTS
- **Level:** FOR EACH ROW
- **Condition:** WHEN (NEW.payment_id IS NULL)
- **Features:**
  - Auto-generates payment_id
  - Uses sequence
  - Conditional execution

---

### 7. **👁️ VIEWS (2 Views)**

#### **VW_ACTIVE_LOANS**
- **Columns:**
  - loan_id, external_app_id, customer_id
  - principal, annual_rate, term_months
  - outstanding_balance, start_date
  - total_periods (COUNT of schedule entries)
  - payment_count (COUNT of payments)
  - total_paid (SUM of payments)
- **Features:**
  - LEFT JOINs (includes loans with no schedule/payments)
  - Aggregation with GROUP BY
  - Filters WHERE status = 'ACTIVE'
- **Use Case:** Active loan dashboard

---

#### **VW_LOAN_SUMMARY**
- **Columns:**
  - month (YYYY-MM format)
  - status
  - loan_count
  - total_principal
  - avg_rate
  - total_outstanding
- **Features:**
  - Time-series aggregation
  - TO_CHAR for month extraction
  - GROUP BY month + status
  - ORDER BY month DESC
- **Use Case:** Monthly loan analytics

---

## 📊 Sample Data Loaded

### **Staging Records (5 rows)**
- APP-1001: $25,000 @ 12% for 36 months
- APP-1002: $55,000 @ 10% for 48 months
- APP-1003: $15,000 @ 14% for 24 months
- APP-1004: $90,000 @ 8.5% for 60 months
- APP-1005: $8,000 @ 15.5% for 18 months

### **Manual Loan (1 row)**
- MANUAL-0001: $10,000 @ 11% for 24 months
  - With 1 schedule entry
  - With 1 payment ($480)

### **Audit Record**
- "Seed data loaded" entry

---

## 🎯 Testing Scenarios Enabled

### **Basic Migration:**
- 5 Tables with data
- 4 Sequences
- 3 Standalone procedures
- 4 Standalone functions
- 1 Package (with 7 internal components)
- 3 Triggers
- 2 Views

### **Advanced Features:**
1. **PL/SQL Collections** - TYPE...TABLE OF in CREATE_SCHEDULE
2. **Bulk Operations** - FORALL for performance
3. **Autonomous Transactions** - PRAGMA in AUDIT_WRITE
4. **JSON Processing** - JSON_TABLE parsing
5. **Cursor Processing** - FOR UPDATE SKIP LOCKED
6. **Error Handling** - Exception blocks everywhere
7. **Business Logic** - EMI calculation, credit scoring
8. **Triggers** - Auto-audit, validation, auto-ID
9. **Views** - Complex JOINs and aggregations
10. **Sequences** - Primary key generation

### **SQL Server Migration Challenges:**
1. **PRAGMA AUTONOMOUS_TRANSACTION** → T-SQL alternative needed
2. **JSON_TABLE** → OPENJSON in SQL Server
3. **FOR UPDATE SKIP LOCKED** → WITH (ROWLOCK, READPAST)
4. **SYSTIMESTAMP** → GETDATE() or SYSDATETIME()
5. **NUMBER** → DECIMAL/NUMERIC
6. **VARCHAR2** → VARCHAR/NVARCHAR
7. **CLOB** → VARCHAR(MAX) or NVARCHAR(MAX)
8. **Package Body** → Multiple stored procedures
9. **Collections (TYPE)** → Table variables
10. **RAISE_APPLICATION_ERROR** → THROW

---

## 🚀 How to Use

### **1. Edit Credentials (Lines 29-31):**
```python
USER = "app"          # Your Oracle username
PASSWORD = "app"      # Your Oracle password
DSN = "localhost:1521/FREEPDB1"  # Your Oracle DSN
```

### **2. Run the Script:**
```bash
python oracle_Database/seed_loans_schema.py
```

### **3. Expected Output:**
```
======================================================================
ORACLE COMPREHENSIVE SCHEMA LOADER
======================================================================
Connecting to Oracle...
✓ Connected.

[1/8] Dropping existing objects...
✓ Old objects dropped

[2/8] Creating tables...
✓ Created 5 tables

[3/8] Creating sequences...
✓ Created 4 sequences

[4/8] Creating standalone procedures...
✓ Created 3 procedures

[5/8] Creating standalone functions...
✓ Created 4 functions

[6/8] Creating package PKG_LOAN_PROCESSOR...
✓ Package compiled (SPEC + BODY)

[7/8] Creating triggers...
✓ Created 3 triggers

[8/8] Creating views...
✓ Created 2 views

✓ Sample data loaded

======================================================================
DATABASE OBJECT SUMMARY
======================================================================
  Tables                        :  5
  Sequences                     :  4
  Procedures (standalone)       :  3
  Functions (standalone)        :  4
  Packages                      :  1
  Triggers                      :  3
  Views                         :  2
  ----------------------------------
  TOTAL OBJECTS                 : 22

TABLE ROW COUNTS:
  STG_LOAN_APPS       : 5
  LOANS               : 1
  LOAN_SCHEDULE       : 1
  LOAN_PAYMENTS       : 1
  LOAN_AUDIT          : 1
======================================================================
✓ DONE — Oracle schema fully loaded
✓ 22 objects ready for migration testing
======================================================================
```

---

## ✅ What This Enables

### **For Migration Testing:**
- ✅ Full suite of Oracle features
- ✅ Complex package with multiple internal procedures/functions
- ✅ Real-world business logic
- ✅ Triggers with DML operations
- ✅ Views with aggregations
- ✅ JSON processing
- ✅ Error handling patterns
- ✅ Transaction control

### **For Verification:**
- ✅ Sample data to verify migration
- ✅ Complex queries to test views
- ✅ Procedures to test execution
- ✅ Package calls to test conversion

---

## 🎓 Summary

**Total Database Objects: 22**
- Tables: 5
- Sequences: 4
- Procedures: 3
- Functions: 4
- Packages: 1 (with 7 internal components)
- Triggers: 3
- Views: 2

**Sample Data Rows: 9 total**
- STG_LOAN_APPS: 5
- LOANS: 1
- LOAN_SCHEDULE: 1
- LOAN_PAYMENTS: 1
- LOAN_AUDIT: 1

**This schema provides a comprehensive, production-like Oracle database for thorough migration testing!** 🎯
