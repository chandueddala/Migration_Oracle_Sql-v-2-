# SQL Server Table Cleanup Script
# Drops existing tables before migration

Write-Host "=" * 70
Write-Host "SQL SERVER TABLE CLEANUP"
Write-Host "=" * 70

Write-Host "`n⚠️  This will DROP the following tables:"
Write-Host "   • LOANS"
Write-Host "   • LOAN_AUDIT"
Write-Host "   • LOAN_PAYMENTS"
Write-Host "   • LOAN_SCHEDULE"
Write-Host "   • STG_LOAN_APPS"

$confirm = Read-Host "`nConfirm cleanup? (yes/no)"

if ($confirm -ne "yes") {
    Write-Host "❌ Cleanup cancelled"
    exit
}

# Get credentials
Write-Host "`n📊 SQL Server Credentials:"
$server = Read-Host "  Server (default: localhost)"
if ([string]::IsNullOrWhiteSpace($server)) { $server = "localhost" }

$database = Read-Host "  Database (default: master)"
if ([string]::IsNullOrWhiteSpace($database)) { $database = "master" }

$username = Read-Host "  Username"
$password = Read-Host "  Password" -AsSecureString
$passwordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
)

Write-Host "`n🔗 Connecting to SQL Server..."

# Build connection string
$connectionString = "Server=$server;Database=$database;User Id=$username;Password=$passwordPlain;TrustServerCertificate=True;"

try {
    # Load SQL Server assembly
    Add-Type -AssemblyName "System.Data"

    $connection = New-Object System.Data.SqlClient.SqlConnection($connectionString)
    $connection.Open()

    Write-Host "   ✅ Connected to $server/$database"

    # Tables to drop
    $tables = @("LOANS", "LOAN_AUDIT", "LOAN_PAYMENTS", "LOAN_SCHEDULE", "STG_LOAN_APPS")

    Write-Host "`n🗑️  Dropping $($tables.Count) tables..."

    foreach ($table in $tables) {
        try {
            $dropSQL = "DROP TABLE IF EXISTS [$table]"
            $command = $connection.CreateCommand()
            $command.CommandText = $dropSQL
            $command.ExecuteNonQuery() | Out-Null
            Write-Host "   ✅ Dropped: $table"
        }
        catch {
            Write-Host "   ⚠️  Could not drop $table: $($_.Exception.Message.Substring(0, [Math]::Min(100, $_.Exception.Message.Length)))"
        }
    }

    $connection.Close()

    Write-Host "`n✅ Cleanup complete!"
    Write-Host "   You can now run: python main.py"
}
catch {
    Write-Host "`n❌ Cleanup failed: $($_.Exception.Message)"
    exit 1
}
