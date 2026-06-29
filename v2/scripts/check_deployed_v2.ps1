param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,
    [Parameter(Mandatory = $true)]
    [string]$FrontendUrl
)

$ErrorActionPreference = "Stop"

function Normalize-Url {
    param([string]$Url)
    return $Url.Trim().TrimEnd("/")
}

$backend = Normalize-Url $BackendUrl
$frontend = Normalize-Url $FrontendUrl

Write-Host "Checking Examiner Victoria V2 deployment..." -ForegroundColor Cyan
Write-Host "Backend:  $backend"
Write-Host "Frontend: $frontend"

$health = Invoke-RestMethod -Uri "$backend/api/health" -TimeoutSec 20
if ($health.status -ne "ok") {
    throw "Backend health check returned unexpected status: $($health | ConvertTo-Json -Compress)"
}
Write-Host "Backend health: ok" -ForegroundColor Green

$bank = Invoke-RestMethod -Uri "$backend/api/question-bank" -TimeoutSec 20
if ($bank.part2_total_cards -ne 73) {
    throw "Unexpected Part 2 card count: $($bank.part2_total_cards)"
}
if ($bank.part3_reference_questions -lt 300) {
    throw "Unexpected Part 3 reference question count: $($bank.part3_reference_questions)"
}
Write-Host "Question bank: $($bank.part1_total_questions) Part 1 questions, $($bank.part2_total_cards) Part 2 cards, $($bank.part3_reference_questions) Part 3 references" -ForegroundColor Green

$frontendResponse = Invoke-WebRequest -UseBasicParsing -Uri $frontend -TimeoutSec 20
if ($frontendResponse.StatusCode -lt 200 -or $frontendResponse.StatusCode -ge 400) {
    throw "Frontend returned HTTP $($frontendResponse.StatusCode)"
}
if ($frontendResponse.Content -notmatch "Examiner Victoria") {
    throw "Frontend HTML does not look like Examiner Victoria."
}
Write-Host "Frontend status: HTTP $($frontendResponse.StatusCode)" -ForegroundColor Green

Write-Host "Deployment smoke check passed." -ForegroundColor Green
