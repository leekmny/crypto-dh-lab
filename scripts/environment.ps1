$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

function Initialize-LabEnvironment {
    param([string]$ProjectRoot)
    Set-Location -LiteralPath $ProjectRoot
    $venvPython = Join-Path $ProjectRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $candidates = @(
            @{Name='python'; Prefix=@()},
            @{Name='python3'; Prefix=@()},
            @{Name='py'; Prefix=@('-3.14')},
            @{Name='py'; Prefix=@('-3.13')},
            @{Name='py'; Prefix=@('-3.12')},
            @{Name='py'; Prefix=@('-3.11')}
        )
        $selected = $null
        foreach ($candidate in $candidates) {
            if (Get-Command $candidate.Name -ErrorAction SilentlyContinue) {
                $prefixArgs = $candidate.Prefix
                $previousPreference = $ErrorActionPreference
                $ErrorActionPreference = 'Continue'
                & $candidate.Name @prefixArgs -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>$null
                $candidateExit = $LASTEXITCODE
                $ErrorActionPreference = $previousPreference
                if ($candidateExit -eq 0) { $selected = $candidate; break }
            }
        }
        if ($null -eq $selected) { throw 'Python 3.11 이상을 설치하고 다시 실행하세요.' }
        $prefixArgs = $selected.Prefix
        & $selected.Name @prefixArgs -m venv .venv | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Python 가상환경 생성에 실패했습니다.' }
    }
    & $venvPython -c 'import sys; assert sys.version_info >= (3,11)' 2>$null
    if ($LASTEXITCODE -ne 0) { throw '기존 .venv의 Python 버전이 너무 낮습니다. 3.11 이상으로 가상환경을 다시 만드세요.' }
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $venvPython -c "import cryptography, pytest; from packaging.version import Version; assert Version(cryptography.__version__) >= Version('46.0.0'); assert Version(pytest.__version__) >= Version('8.4')" 2>$null
    $dependencyExit = $LASTEXITCODE
    $ErrorActionPreference = $previousPreference
    if ($dependencyExit -ne 0) {
        Write-Host '필요한 암호 라이브러리와 검증 도구를 설치합니다.'
        & $venvPython -m pip install -r requirements.txt | Out-Host
        if ($LASTEXITCODE -ne 0) { throw '라이브러리 설치에 실패했습니다. 인터넷 연결과 pip 설정을 확인하세요.' }
    }
    return $venvPython
}
