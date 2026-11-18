param(
    [ValidateSet('small','group14')][string]$Mode = 'group14',
    [int]$Port = 8765,
    [switch]$NoBrowser,
    [switch]$NoAutoRun
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts/environment.ps1')
try {
    $labPython = Initialize-LabEnvironment -ProjectRoot $PSScriptRoot
    & $labPython scripts/generate_keys.py
    if ($LASTEXITCODE -ne 0) { throw '공유키 초기화에 실패했습니다.' }
    $launchArgs = @('main.py','--port', "$Port", '--mode', $Mode)
    if (-not $NoBrowser) { $launchArgs += '--open' }
    if (-not $NoAutoRun) { $launchArgs += '--auto-run' }
    & $labPython @launchArgs
    exit $LASTEXITCODE
} catch {
    Write-Host ('실행 실패: ' + $_.Exception.Message) -ForegroundColor Red
    exit 2
}
