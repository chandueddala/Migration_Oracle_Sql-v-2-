# Package Parser Fix - PKG_LOAN_PROCESSOR Migration Issue

## Problem Summary

The package migration for `PKG_LOAN_PROCESSOR` was **finding 0 procedures and 0 functions**, even though:
- The package code was successfully retrieved (9809 characters)
- The package contained procedures and functions
- The migration reported "success" but nothing was actually migrated

## Root Cause

The issue was in [utils/package_decomposer_enhanced.py](utils/package_decomposer_enhanced.py). The regex patterns used to extract procedures and functions from the package body were **too strict** and **not robust enough** to handle real-world Oracle package code.

### Specific Issues with the Original Parser:

1. **Nested Parentheses Not Handled**
   ```python
   # This pattern fails with parameters like VARCHAR2(100)
   proc_pattern = r'PROCEDURE\s+([\w$#]+)\s*(\([^)]*\)|)\s+(?:IS|AS)(.*?)END\s+\1\s*;'
   ```
   The `[^)]*` part doesn't handle nested parentheses in data types like `VARCHAR2(100)` or `NUMBER(10,2)`.

2. **Strict END Matching**
   ```python
   # Requires exact procedure name after END
   END\s+\1\s*;
   ```
   Oracle allows `END;` without the procedure/function name, making this pattern fail.

3. **Greedy Regex Matching**
   ```python
   # Non-greedy (.*?) can fail with nested BEGIN/END blocks
   (?:IS|AS)(.*?)END\s+\1\s*;
   ```
   Doesn't properly handle nested BEGIN/END blocks within procedures.

4. **Single Complex Regex**
   - Trying to match the entire procedure/function structure in one regex is brittle
   - Different formatting styles break the pattern
   - Comments and whitespace variations cause failures

## Solution

Created **[utils/package_decomposer_fixed.py](utils/package_decomposer_fixed.py)** with a **multi-stage parsing approach**:

### Key Improvements:

1. **Balanced Block Extraction**
   ```python
   def extract_balanced_block(text: str, start_pos: int) -> tuple[str, int]:
       """Extract a balanced BEGIN...END block using depth tracking"""
   ```
   - Tracks BEGIN/END depth counter
   - Handles string literals properly (ignores BEGIN/END in quotes)
   - Works with nested blocks

2. **Step-by-Step Parsing**
   Instead of one complex regex, the parser:
   - Finds PROCEDURE/FUNCTION keywords
   - Extracts the name
   - Finds parameter list (handles nested parentheses)
   - Locates IS/AS keyword
   - Uses balanced extraction for the body
   - No strict END name matching required

3. **Robust Parameter Parsing**
   ```python
   def parse_parameters_robust(params_str: str) -> List[str]:
       """Parse parameter list handling nested parentheses"""
   ```
   - Handles `VARCHAR2(100)`, `NUMBER(10,2)`, etc.
   - Respects parenthesis depth when splitting on commas

4. **Flexible Pattern Matching**
   ```python
   # Find PROCEDURE keywords first
   for match in re.finditer(r'\bPROCEDURE\s+([\w$#]+)', body_text, re.IGNORECASE):
       # Then extract details for each one
   ```
   - Simple regex to find candidates
   - Manual parsing for extraction
   - More resilient to formatting variations

### What the Fixed Parser Handles:

✅ Nested parentheses in parameters: `VARCHAR2(100)`, `NUMBER(10,2)`
✅ Procedures/functions with or without parameters
✅ `END;` or `END procedure_name;`
✅ Nested BEGIN/END blocks
✅ Multi-line declarations
✅ Comments in code
✅ Different whitespace formatting
✅ Public vs private members
✅ Overloaded procedures/functions

## Test Results

### Test with Sample Package:
```
Package Name: PKG_LOAN_PROCESSOR
Total Procedures: 2 ✅
Total Functions: 2 ✅
Total Members: 4 ✅

MEMBERS FOUND:
1. PROCEDURE: PROCESS_LOAN (PUBLIC)
2. PROCEDURE: VALIDATE_APPLICATION (PUBLIC)
3. FUNCTION: GET_LOAN_STATUS (PUBLIC)
4. FUNCTION: CALCULATE_INTEREST (PUBLIC)
```

**Result:** Parser correctly extracted all procedures and functions!

## How to Use

The fixed parser is **automatically loaded** by the orchestrator:

```python
# In agents/orchestrator_agent.py
try:
    from utils.package_decomposer_fixed import decompose_oracle_package
    logger.info("✅ Using FIXED robust package decomposer")
except ImportError:
    # Fallback to enhanced, then basic
```

## Files Modified

1. **Created:**
   - [`utils/package_decomposer_fixed.py`](utils/package_decomposer_fixed.py) - New robust parser
   - [`test_fixed_parser.py`](test_fixed_parser.py) - Test script
   - [`migrate_package_only.py`](migrate_package_only.py) - Test migration script

2. **Updated:**
   - [`agents/orchestrator_agent.py`](agents/orchestrator_agent.py) - Import fixed parser first

3. **Diagnostic Tools:**
   - [`extract_package_code.sql`](extract_package_code.sql) - SQL script to extract package manually
   - [`debug_package_simple.py`](debug_package_simple.py) - Python debug script

## Next Steps

1. **Run the full migration** to verify the package is now parsed correctly:
   ```bash
   python main.py
   ```

2. **Or test just the package**:
   ```bash
   python migrate_package_only.py
   ```

3. **Check the migration output** for:
   - Number of procedures found
   - Number of functions found
   - Each member being migrated individually

## Expected Output

Instead of:
```
Found 0 members to migrate:
- 0 procedures
- 0 functions
```

You should now see:
```
Found N members to migrate:
- X procedures
- Y functions

[1/N] PROCEDURE: PKG_LOAN_PROCESSOR_procedure_name
  Status: SUCCESS
[2/N] FUNCTION: PKG_LOAN_PROCESSOR_function_name
  Status: SUCCESS
...
```

## Technical Details

### Parser Architecture:

```
decompose_oracle_package()
├── Separate spec and body using regex
├── Parse specification (public interface)
│   ├── Find procedure declarations
│   └── Find function declarations
├── Parse body (implementations)
│   ├── parse_package_body_procedures()
│   │   ├── Find PROCEDURE keywords
│   │   ├── Extract name and parameters
│   │   ├── Find IS/AS
│   │   └── extract_balanced_block() for body
│   └── parse_package_body_functions()
│       ├── Find FUNCTION keywords
│       ├── Extract name, parameters, RETURN type
│       ├── Find IS/AS
│       └── extract_balanced_block() for body
└── Match spec with body implementations
```

### Why This Approach Works:

1. **Separation of Concerns** - Each parsing step has one responsibility
2. **Iterative Matching** - Find candidates first, then extract details
3. **Balanced Counting** - Use depth tracking instead of regex for blocks
4. **Defensive Parsing** - Continue on errors, log warnings, don't fail entirely
5. **Flexible Patterns** - Simple regex for discovery, manual parsing for extraction

## Comparison

| Feature | Original Enhanced Parser | Fixed Parser |
|---------|-------------------------|--------------|
| Nested parentheses | ❌ Fails | ✅ Works |
| Flexible END syntax | ❌ Requires name | ✅ Optional |
| Nested BEGIN/END | ⚠️ Sometimes | ✅ Always |
| Error handling | ❌ Fails completely | ✅ Continues |
| Logging | ⚠️ Minimal | ✅ Detailed |
| Parsing approach | Regex only | Hybrid (regex + manual) |
| Complexity | Single complex regex | Multi-stage simple steps |

## Conclusion

The package parser has been **completely rewritten** with a robust, multi-stage approach that handles real-world Oracle package code correctly. Testing shows it successfully extracts procedures and functions that the original parser missed.

**The PKG_LOAN_PROCESSOR migration should now work correctly!**
