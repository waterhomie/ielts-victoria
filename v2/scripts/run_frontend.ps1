param(
    [int]$Port = 5173
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_common.ps1")

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")
$frontendRoot = Join-Path $repoRoot "v2\frontend"
$pnpm = Resolve-V2Pnpm

Write-Host "Examiner Victoria V2 frontend" -ForegroundColor Cyan
Write-Host "Frontend: $frontendRoot"

Set-Location $frontendRoot
Invoke-V2Native $pnpm install
Invoke-V2Native $pnpm run dev -- --port $Port
