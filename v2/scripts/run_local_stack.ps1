param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_common.ps1")

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")
$frontendRoot = Join-Path $repoRoot "v2\frontend"
$tmpRoot = Join-Path $repoRoot "tmp"
$python = Resolve-V2Python
$pnpm = Resolve-V2Pnpm

if (-not (Test-Path -LiteralPath $tmpRoot)) {
    New-Item -ItemType Directory -Path $tmpRoot | Out-Null
}

function Test-PortFree {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return -not $connection
}

if (-not (Test-PortFree $BackendPort)) {
    throw "Backend port $BackendPort is already in use. Stop that process or choose another -BackendPort."
}

if (-not (Test-PortFree $FrontendPort)) {
    throw "Frontend port $FrontendPort is already in use. Stop that process or choose another -FrontendPort."
}

Write-Host "Examiner Victoria V2 local stack" -ForegroundColor Cyan
Write-Host "Repository: $repoRoot"
Write-Host "Backend:   http://127.0.0.1:$BackendPort"
Write-Host "Frontend:  http://127.0.0.1:$FrontendPort"

if (-not $SkipInstall) {
    Write-Host "Installing backend/frontend dependencies..." -ForegroundColor Cyan
    Set-Location $repoRoot
    Invoke-V2Native $python -m pip install -r .\v2\backend\requirements.txt
    Set-Location $frontendRoot
    Invoke-V2Native $pnpm install
}

$backendOut = Join-Path $tmpRoot "v2_backend.out.log"
$backendErr = Join-Path $tmpRoot "v2_backend.err.log"
$frontendOut = Join-Path $tmpRoot "v2_frontend.out.log"
$frontendErr = Join-Path $tmpRoot "v2_frontend.err.log"
$pidFile = Join-Path $tmpRoot "v2_server_pids.txt"

Remove-Item -LiteralPath $backendOut, $backendErr, $frontendOut, $frontendErr -Force -ErrorAction SilentlyContinue

$localDeps = Join-Path $tmpRoot "v2_backend_deps"
$pythonPathParts = @($repoRoot)
if (Test-Path -LiteralPath $localDeps) {
    $pythonPathParts = @($localDeps) + $pythonPathParts
}
$pythonPath = $pythonPathParts -join ";"

$backendCommand = @"
`$env:PYTHONPATH = '$pythonPath'
Set-Location -LiteralPath '$repoRoot'
& '$python' -m uvicorn v2.backend.app:app --host 127.0.0.1 --port $BackendPort
"@

$backendProcess = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $backendCommand) `
    -RedirectStandardOutput $backendOut `
    -RedirectStandardError $backendErr `
    -WindowStyle Hidden `
    -PassThru

$nodeBin = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin"
$frontendCommand = @"
if (Test-Path -LiteralPath '$nodeBin') {
    `$env:PATH = '$nodeBin;' + `$env:PATH
}
Set-Location -LiteralPath '$frontendRoot'
& '$pnpm' run dev -- --host 127.0.0.1 --port $FrontendPort
"@

$frontendProcess = Start-Process `
    -FilePath "powershell.exe" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $frontendCommand) `
    -RedirectStandardOutput $frontendOut `
    -RedirectStandardError $frontendErr `
    -WindowStyle Hidden `
    -PassThru

@(
    "backend=$($backendProcess.Id)",
    "frontend=$($frontendProcess.Id)"
) | Set-Content -LiteralPath $pidFile -Encoding UTF8

Write-Host "Started backend PID $($backendProcess.Id), frontend PID $($frontendProcess.Id)."
Write-Host "Logs:"
Write-Host "  $backendErr"
Write-Host "  $frontendOut"

Start-Sleep -Seconds 3

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 8
    Write-Host "Backend health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "Backend did not become healthy yet. Check $backendErr" -ForegroundColor Yellow
}

try {
    $frontend = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort" -TimeoutSec 8
    Write-Host "Frontend status: $($frontend.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Frontend did not respond yet. Check $frontendErr or $frontendOut" -ForegroundColor Yellow
}

Write-Host "Open http://127.0.0.1:$FrontendPort"
