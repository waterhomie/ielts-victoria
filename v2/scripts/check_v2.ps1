param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_common.ps1")

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot
$python = Resolve-V2Python
$pnpm = Resolve-V2Pnpm

Write-Host "Running Examiner Victoria V2 checks..." -ForegroundColor Cyan

if (-not $SkipInstall) {
    Invoke-V2Native $python -m pip install -r .\v2\backend\requirements.txt
    Push-Location .\v2\frontend
    Invoke-V2Native $pnpm install
    Pop-Location
}

Invoke-V2Native $python -m py_compile `
    .\v2\backend\schemas.py `
    .\v2\backend\engine.py `
    .\v2\backend\app.py `
    .\v2\backend\smoke_test.py `
    .\question_bank.py `
    .\pdf_recall_question_bank.py `
    .\validate_question_bank.py

Invoke-V2Native $python .\validate_question_bank.py
Invoke-V2Native $python -m v2.backend.smoke_test

Push-Location .\v2\frontend
Invoke-V2Native $pnpm run build
Pop-Location

Write-Host "All V2 checks passed." -ForegroundColor Green
