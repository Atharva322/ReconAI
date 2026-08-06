$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$sqlFiles = Get-ChildItem -LiteralPath (Join-Path $root "migrations") -Filter "*.sql" | Sort-Object Name

if ($sqlFiles.Count -eq 0) {
  throw "No migration files found"
}

$commands = ($sqlFiles | ForEach-Object { "psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f /workspace/migrations/$($_.Name)" }) -join " && "

docker run --rm `
  -v "${root}:/workspace:ro" `
  -e POSTGRES_HOST_AUTH_METHOD=trust `
  postgres:16-alpine `
  sh -c "docker-entrypoint.sh postgres -c listen_addresses='localhost' > /tmp/postgres.log 2>&1 & until pg_isready -U postgres > /dev/null 2>&1; do sleep 1; done; $commands"

Write-Host "Migration syntax checks OK"
