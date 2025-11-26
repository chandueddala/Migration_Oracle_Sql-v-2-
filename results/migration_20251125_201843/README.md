# Migration Documentation Session

**Created**: 2025-11-25 20:18:43

## Purpose
This folder contains Oracle source code and SQL Server output for development verification and debugging.

## Structure

### oracle/
Contains original Oracle database objects extracted from source:
- `tables/` - Table DDL
- `procedures/` - Stored procedures
- `functions/` - Functions
- `packages/` - Package code (spec + body)
- `triggers/` - Trigger definitions
- `views/` - View definitions

### sql/
Contains converted SQL Server code:
- `tables/` - Converted table DDL
- `procedures/` - Converted stored procedures
- `functions/` - Converted UDFs
- `packages/` - Decomposed package members
- `triggers/` - Converted triggers
- `views/` - Converted views

## Usage

1. **Verification**: Compare Oracle source with SQL Server output
2. **Debugging**: Review conversion quality and identify issues
3. **Performance Testing**: Use as reference for optimization
4. **Production**: Remove this folder before deployment

## Notes

- Each object is stored in a separate markdown file
- File names follow the pattern: `ObjectName.md`
- Metadata is included at the top of each file
- This is a development-only feature
