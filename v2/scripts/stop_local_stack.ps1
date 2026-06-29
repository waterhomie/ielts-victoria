param(
    [string]$Ports = "8000,5173"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")
$tmpRoot = Join-Path $repoRoot "tmp"
$pidFile = Join-Path $tmpRoot "v2_server_pids.txt"
$portList = $Ports -split "[,\s;]+" |
    Where-Object { $_ } |
    ForEach-Object { [int]$_ }

Write-Host "Stopping Examiner Victoria V2 local stack..." -ForegroundColor Cyan
Write-Host "Ports: $($portList -join ', ')"

function Stop-ListenersOnPort {
    param([int]$Port)

    for ($attempt = 1; $attempt -le 5; $attempt++) {
        $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        if (-not $connections) {
            return
        }

        foreach ($connection in $connections) {
            Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped process $($connection.OwningProcess) listening on port $Port"
        }

        Start-Sleep -Milliseconds 500
    }

    $remaining = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($remaining) {
        Write-Host "Port $Port is still in use. You may need to close it manually." -ForegroundColor Yellow
    }
}

if (Test-Path -LiteralPath $pidFile) {
    $pidLines = Get-Content -LiteralPath $pidFile
    foreach ($line in $pidLines) {
        if ($line -match "=(\d+)$") {
            $pidValue = [int]$Matches[1]
            Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
            Write-Host "Stopped recorded process $pidValue"
        }
    }
}

Start-Sleep -Seconds 1

foreach ($port in $portList) {
    Stop-ListenersOnPort -Port $port
}

Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
Write-Host "Local stack stop command finished." -ForegroundColor Green
