param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_common.ps1")

$repoRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..")
Set-Location $repoRoot
$python = Resolve-V2Python
$pnpm = Resolve-V2Pnpm
Add-V2PythonPath -RepoRoot $repoRoot

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

$scriptFiles = @(
    ".\v2\scripts\_common.ps1",
    ".\v2\scripts\check_v2.ps1",
    ".\v2\scripts\run_backend.ps1",
    ".\v2\scripts\run_frontend.ps1",
    ".\v2\scripts\run_local_stack.ps1",
    ".\v2\scripts\stop_local_stack.ps1",
    ".\v2\scripts\check_deployed_v2.ps1"
)
foreach ($scriptFile in $scriptFiles) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile(
        (Resolve-Path -LiteralPath $scriptFile),
        [ref]$tokens,
        [ref]$parseErrors
    ) | Out-Null
    if ($parseErrors.Count -gt 0) {
        throw "PowerShell parse failed for ${scriptFile}: $($parseErrors[0].Message)"
    }
}

Invoke-V2Native $python .\validate_question_bank.py
Invoke-V2Native $python -m v2.backend.smoke_test

Push-Location .\v2\frontend
Invoke-V2Native $pnpm run build
Pop-Location

Write-Host "All V2 checks passed." -ForegroundColor Green
