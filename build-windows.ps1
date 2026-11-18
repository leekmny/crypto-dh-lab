$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$labExePath = Join-Path $PSScriptRoot 'dist/CryptoDHLab/CryptoDHLab.exe'
$labRunning = Get-Process -Name CryptoDHLab -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $labExePath }
if ($labRunning) { throw '실험실 실행 창을 먼저 닫은 뒤 다시 빌드하세요.' }
$labPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $labPython)) { throw '먼저 run.ps1로 개발 환경을 준비하세요.' }
& $labPython -m pip install -r (Join-Path $PSScriptRoot 'requirements-build.txt')
if ($LASTEXITCODE -ne 0) { throw '빌드 도구 설치 실패' }
& $labPython scripts/collect_notices.py
if ($LASTEXITCODE -ne 0) { throw '라이선스 문서 수집 실패' }
& $labPython -m PyInstaller --noconfirm CryptoDHLab.spec
if ($LASTEXITCODE -ne 0) { throw 'Windows EXE 빌드 실패' }
$labDistribution = Join-Path $PSScriptRoot 'dist/CryptoDHLab'
foreach ($labDocument in @('WINDOWS-사용법.txt', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.txt')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $labDocument) -Destination $labDistribution
}
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'docs') -Destination $labDistribution -Recurse -Force
Compress-Archive -LiteralPath $labDistribution -DestinationPath (Join-Path $PSScriptRoot 'dist/CryptoDHLab-Windows-x64.zip') -Force
Write-Host '완료: dist/CryptoDHLab/CryptoDHLab.exe'
