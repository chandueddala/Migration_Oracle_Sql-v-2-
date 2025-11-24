# Fix migration_engine.py - Replace fetch_table_data with get_table_data
$filePath = "utils\migration_engine.py"
$content = Get-Content $filePath -Raw
$content = $content -replace 'oracle_conn\.fetch_table_data\(', 'oracle_conn.get_table_data('
Set-Content -Path $filePath -Value $content -NoNewline
Write-Host "✅ Fixed migration_engine.py - replaced fetch_table_data with get_table_data"
