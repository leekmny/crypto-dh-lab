$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts/environment.ps1')
try {
    $labPython = Initialize-LabEnvironment -ProjectRoot $PSScriptRoot
    & $labPython scripts/run_tests.py
    exit $LASTEXITCODE
} catch {
    Write-Host ('검증 실행 실패: ' + $_.Exception.Message) -ForegroundColor Red
    exit 2
}
