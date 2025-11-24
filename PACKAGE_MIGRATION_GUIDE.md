# Oracle Package Migration Guide

## Overview

**IMPORTANT**: SQL Server does **NOT** support Oracle-style packages directly.

This migration tool automatically **decomposes** Oracle packages into individual SQL Server objects (stored procedures and functions).

## What Are Oracle Packages?

Oracle packages are containers that group related procedures, functions, variables, and types together:

```sql
-- Oracle Package Specification
CREATE OR REPLACE PACKAGE pkg_loans AS
    -- Global variables
    g_max_interest_rate NUMBER := 15.5;

    -- Public procedures
    PROCEDURE calculate_interest(p_loan_id NUMBER);

    -- Public functions
    FUNCTION get_loan_status(p_loan_id NUMBER) RETURN VARCHAR2;
END pkg_loans;

-- Oracle Package Body
CREATE OR REPLACE PACKAGE BODY pkg_loans AS
    PROCEDURE calculate_interest(p_loan_id NUMBER) IS
        -- Implementation
    END;

    FUNCTION get_loan_status(p_loan_id NUMBER) RETURN VARCHAR2 IS
        -- Implementation
    END;
END pkg_loans;
```

## SQL Server Equivalent

SQL Server does **NOT** have packages. Each procedure and function must be a standalone object:

```sql
-- Becomes separate stored procedure
CREATE PROCEDURE dbo.pkg_loans_calculate_interest
    @p_loan_id INT
AS
BEGIN
    -- Implementation
END;

-- Becomes separate function
CREATE FUNCTION dbo.pkg_loans_get_loan_status
    (@p_loan_id INT)
RETURNS VARCHAR(255)
AS
BEGIN
    -- Implementation
    RETURN @status;
END;
```

## Migration Strategy

### Automatic Decomposition Process

When you migrate an Oracle package, the tool automatically:

1. **Fetches** the complete package code (spec + body) from Oracle
2. **Parses** the package to identify:
   - All procedures
   - All functions
   - Global variables
   - Initialization blocks
3. **Decomposes** each member into a standalone object
4. **Converts** each member from PL/SQL to T-SQL
5. **Deploys** each as a separate SQL Server object

### Naming Convention

Decomposed objects follow this naming pattern:

```
{PackageName}_{MemberName}
```

**Examples:**
- `pkg_loans.calculate_interest` → `pkg_loans_calculate_interest`
- `pkg_loans.get_loan_status` → `pkg_loans_get_loan_status`
- `hr_pkg.get_employee` → `hr_pkg_get_employee`

This preserves the logical grouping while making objects standalone.

## Example Migration

### Source: Oracle Package

```sql
CREATE OR REPLACE PACKAGE pkg_customer AS
    -- Public constant
    c_default_credit_score CONSTANT NUMBER := 600;

    -- Public procedures
    PROCEDURE add_customer(
        p_name VARCHAR2,
        p_email VARCHAR2
    );

    PROCEDURE update_credit_score(
        p_customer_id NUMBER,
        p_score NUMBER
    );

    -- Public function
    FUNCTION get_customer_name(p_customer_id NUMBER) RETURN VARCHAR2;
END pkg_customer;

CREATE OR REPLACE PACKAGE BODY pkg_customer AS
    -- Private variable
    v_audit_enabled BOOLEAN := TRUE;

    PROCEDURE add_customer(p_name VARCHAR2, p_email VARCHAR2) IS
    BEGIN
        INSERT INTO customers (name, email, credit_score)
        VALUES (p_name, p_email, c_default_credit_score);
    END;

    PROCEDURE update_credit_score(p_customer_id NUMBER, p_score NUMBER) IS
    BEGIN
        UPDATE customers
        SET credit_score = p_score
        WHERE customer_id = p_customer_id;
    END;

    FUNCTION get_customer_name(p_customer_id NUMBER) RETURN VARCHAR2 IS
        v_name VARCHAR2(100);
    BEGIN
        SELECT name INTO v_name
        FROM customers
        WHERE customer_id = p_customer_id;
        RETURN v_name;
    END;
END pkg_customer;
```

### Result: SQL Server Objects

**Procedure 1:**
```sql
CREATE PROCEDURE dbo.pkg_customer_add_customer
    @p_name NVARCHAR(255),
    @p_email NVARCHAR(255)
AS
BEGIN
    DECLARE @c_default_credit_score INT = 600;

    INSERT INTO customers (name, email, credit_score)
    VALUES (@p_name, @p_email, @c_default_credit_score);
END;
```

**Procedure 2:**
```sql
CREATE PROCEDURE dbo.pkg_customer_update_credit_score
    @p_customer_id INT,
    @p_score INT
AS
BEGIN
    UPDATE customers
    SET credit_score = @p_score
    WHERE customer_id = @p_customer_id;
END;
```

**Function:**
```sql
CREATE FUNCTION dbo.pkg_customer_get_customer_name
    (@p_customer_id INT)
RETURNS NVARCHAR(100)
AS
BEGIN
    DECLARE @v_name NVARCHAR(100);

    SELECT @v_name = name
    FROM customers
    WHERE customer_id = @p_customer_id;

    RETURN @v_name;
END;
```

## Special Considerations

### 1. Global Package Variables

Oracle packages can have global variables that persist across calls:

```sql
-- Oracle
PACKAGE pkg_example AS
    g_counter NUMBER := 0;  -- Persists across calls
END;
```

**SQL Server Options:**
- **Context Info**: `CONTEXT_INFO()` for session-level state
- **Temp Tables**: `#temp_table` for session data
- **Application Variables**: Application-level caching
- **Database Variables**: Custom configuration tables

**Example:**
```sql
-- Option 1: Session context
EXEC sp_set_session_context 'counter', 0;
SELECT CAST(SESSION_CONTEXT('counter') AS INT);

-- Option 2: Temp table
CREATE TABLE #package_state (counter INT);
INSERT INTO #package_state VALUES (0);
```

### 2. Package Initialization Blocks

Oracle packages can have initialization code:

```sql
-- Oracle
PACKAGE BODY pkg_example AS
    -- ... procedures and functions ...

    -- Initialization (runs when package is first loaded)
    BEGIN
        DBMS_OUTPUT.PUT_LINE('Package initialized');
        -- Setup code here
    END;
END;
```

**SQL Server Solution:**
Create a setup stored procedure:

```sql
CREATE PROCEDURE dbo.pkg_example_initialize
AS
BEGIN
    -- Initialization logic here
    PRINT 'Package initialized';
    -- Setup code
END;

-- Call it once after deployment
EXEC dbo.pkg_example_initialize;
```

### 3. Private vs Public Members

Oracle distinguishes between:
- **Spec**: Public interface (visible to callers)
- **Body**: Private implementations

**SQL Server:**
- All procedures/functions are public by default
- Use naming conventions for "private" objects: `_internal_`, `_private_`
- Document which objects are meant to be internal

**Example:**
```sql
-- Public procedure (intended for external use)
CREATE PROCEDURE dbo.pkg_customer_add_customer ...

-- Internal procedure (intended for package use only)
CREATE PROCEDURE dbo.pkg_customer__internal_validate ...
```

### 4. Overloaded Procedures/Functions

Oracle allows multiple procedures with the same name but different parameters:

```sql
-- Oracle - both are valid
PROCEDURE process(p_id NUMBER);
PROCEDURE process(p_name VARCHAR2);
```

**SQL Server does NOT support overloading.**

**Solution:** Use distinct names:
```sql
CREATE PROCEDURE dbo.pkg_example_process_by_id @p_id INT ...
CREATE PROCEDURE dbo.pkg_example_process_by_name @p_name NVARCHAR(255) ...
```

## Migration Output

When migrating a package, you'll see output like this:

```
📦 PACKAGE DECOMPOSITION: PKG_CUSTOMER
⚠️  SQL Server does not support packages - decomposing into individual objects

  📥 Step 1/4: Fetching package code from Oracle...
  ✅ Retrieved package code: 2450 chars

  🔧 Step 2/4: Decomposing package into procedures/functions...
     Found 5 members to migrate:
     - 3 procedures
     - 2 functions
     ⚠️  2 global variables detected

  🚀 Step 3/4: Migrating individual members...

     [1/5] Migrating: add_customer (PROCEDURE)
                      → SQL Server name: PKG_CUSTOMER_add_customer
                      ✅ Success

     [2/5] Migrating: update_credit_score (PROCEDURE)
                      → SQL Server name: PKG_CUSTOMER_update_credit_score
                      ✅ Success

     [3/5] Migrating: get_customer_name (FUNCTION)
                      → SQL Server name: PKG_CUSTOMER_get_customer_name
                      ✅ Success

  📊 Step 4/4: Package decomposition summary
     ✅ Successfully migrated: 5/5
     ❌ Failed: 0/5
```

## Calling Migrated Code

### Oracle Call Pattern

```sql
-- Oracle
BEGIN
    pkg_customer.add_customer('John Doe', 'john@example.com');

    DBMS_OUTPUT.PUT_LINE(
        pkg_customer.get_customer_name(123)
    );
END;
```

### SQL Server Call Pattern

```sql
-- SQL Server
EXEC dbo.pkg_customer_add_customer
    @p_name = 'John Doe',
    @p_email = 'john@example.com';

DECLARE @customer_name NVARCHAR(100);
SET @customer_name = dbo.pkg_customer_get_customer_name(123);
PRINT @customer_name;
```

## Best Practices

### 1. Document Package Groupings

Create a documentation file listing which objects belong to each logical package:

```sql
-- Package: PKG_CUSTOMER
-- Original Oracle package decomposed into:
--   - pkg_customer_add_customer (PROCEDURE)
--   - pkg_customer_update_credit_score (PROCEDURE)
--   - pkg_customer_get_customer_name (FUNCTION)
--   - pkg_customer_delete_customer (PROCEDURE)
```

### 2. Use SQL Server Schemas

Consider using SQL Server schemas to maintain logical grouping:

```sql
-- Create schema for customer-related objects
CREATE SCHEMA customer_pkg;

-- Create objects in schema
CREATE PROCEDURE customer_pkg.add_customer ...
CREATE PROCEDURE customer_pkg.update_credit_score ...
CREATE FUNCTION customer_pkg.get_customer_name ...
```

Then call as:
```sql
EXEC customer_pkg.add_customer @p_name = 'John', @p_email = 'john@example.com';
```

### 3. Create Wrapper Procedures (Optional)

For frequently used package calls, create wrapper procedures:

```sql
CREATE PROCEDURE dbo.customer_operations
    @operation VARCHAR(50),
    @param1 NVARCHAR(255) = NULL,
    @param2 NVARCHAR(255) = NULL
AS
BEGIN
    IF @operation = 'ADD'
        EXEC dbo.pkg_customer_add_customer @param1, @param2;
    ELSE IF @operation = 'UPDATE_SCORE'
        EXEC dbo.pkg_customer_update_credit_score @param1, @param2;
END;
```

## Troubleshooting

### Issue: Package has global variables

**Symptom:** Warning message about global variables

**Solution:**
- Review the global variables in the output
- Decide on SQL Server equivalent (context info, temp tables, etc.)
- Manually update affected procedures to use the new approach

### Issue: Package has initialization block

**Symptom:** Warning about initialization code

**Solution:**
- Review the initialization code
- Create a separate setup stored procedure
- Execute it once after deployment
- Document the requirement

### Issue: Overloaded procedures

**Symptom:** Multiple procedures with same name fail to deploy

**Solution:**
- The decomposer will attempt to create distinct names
- Review the generated names and adjust if needed
- Update calling code to use new names

## Summary

✅ **Automatic**: Package decomposition is fully automated

✅ **Preserves Logic**: All procedures and functions are migrated

✅ **Clear Naming**: Consistent naming convention for easy identification

⚠️ **Manual Steps**: Global variables and initialization may require manual intervention

⚠️ **Schema Changes**: Consider using SQL Server schemas for better organization

📝 **Documentation**: Keep track of package-to-objects mappings for maintenance
