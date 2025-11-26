# SQL Server TABLE: STG_LOAN_APPS

**Source**: SQL Server (Converted)  
**Captured**: 2025-11-25 22:23:18  

## Source Code

```sql
CREATE TABLE [dbo].[STG_LOAN_APPS] 
(
    [STG_ID] DECIMAL(38,0) NOT NULL,
    [PAYLOAD] NVARCHAR(MAX),
    [CREATED_ON] DATETIME2(6),
    CONSTRAINT [PK_STG_LOAN_APPS] PRIMARY KEY ([STG_ID])
);
```
