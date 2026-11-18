# Windows 빌드와 Release 준비

[프로젝트 소개로 돌아가기](../README.md)

관리자가 로컬에서 배포 파일을 준비하는 절차입니다. 명령은 **프로젝트 루트**의 Windows PowerShell에서 실행합니다. 로컬 준비와 GitHub 게시를 구분하고, 게시할 소스와 ZIP을 만든 소스가 같은 버전인지 확인합니다.

## 환경 준비와 검증

Python 3.11 이상이 필요합니다. 고정 의존성 목록은 Windows·Python 3.14에서 검증한 버전이며, 최초 설치에는 인터넷 연결이 필요합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\test.ps1
```

`run.ps1`이나 `test.ps1`로 이미 `.venv`를 준비했다면 다시 만들 필요가 없습니다. 테스트 종료 코드와 `tests/results.json`, `tests/output.txt`, `tests/results.xml`을 확인하고, 실패를 해결한 뒤 빌드합니다.

## 빌드와 압축 해제 검수

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-windows.ps1
```

스크립트가 PyInstaller 설치, 외부 구성요소 고지 수집, EXE·문서 복사, ZIP 생성을 수행합니다. 기존 배포본의 작은 실행 창은 먼저 종료하세요.

- 실행 파일: `dist/CryptoDHLab/CryptoDHLab.exe`
- 함께 필요한 파일: `dist/CryptoDHLab/_internal/` 전체
- Release에 첨부할 파일: `dist/CryptoDHLab-Windows-x64.zip`

배포 전 확인:

- ZIP을 새 폴더에 풀고 그 안의 EXE로 실행 창과 브라우저를 엽니다.
- 작은 수와 Group 14의 정상 통신, 변조 거부, **전체 검증 실행**을 확인합니다.
- 중복 실행이 기존 화면을 열고, 실행 창을 닫으면 서버도 종료되는지 확인합니다.
- ZIP에 기존 키·`.local`·로그·사용자 메시지·과거 테스트 결과가 포함되지 않았는지 확인합니다.
- 사용법, README와 연결한 문서, 외부 구성요소 고지가 배포물에 있는지 확인합니다.
- 가능하면 개발 환경이 없는 별도 Windows PC나 깨끗한 가상 머신에서도 확인합니다. 같은 PC에서만 확인했다면 그 범위를 [공개 검증 요약](VERIFICATION.md)과 Release 설명에 적습니다.
- 프로젝트의 MIT `LICENSE`와 외부 구성요소 고지를 배포물에 포함합니다. 외부 구성요소에는 각자의 라이선스가 적용됩니다.

최종 ZIP의 SHA256을 계산합니다. 문서나 ZIP을 변경했다면 다시 계산하세요.

```powershell
Get-FileHash -LiteralPath .\dist\CryptoDHLab-Windows-x64.zip -Algorithm SHA256
```

## 첫 Release 설명 초안

제안 태그: `v0.1.0`
제안 제목: **v0.1.0 — 눈으로 배우는 암호 통신 · 학습 프리뷰**

아래 빈칸은 이번 배포에서 확인한 결과로 채웁니다. 존재하지 않는 다운로드 주소나 검증하지 않은 환경은 기재하지 않습니다.

```text
Crypto DH Lab의 첫 학습용 프리뷰입니다.

- 작은 수로 DH 계산을 따라가고 2048비트 Group 14와 비교합니다.
- 독립 Alice·Bob 프로세스의 실제 로컬 TCP 통신을 관찰합니다.
- 패킷 변조와 키 불일치를 감지하는 단계를 비교합니다.

실행: CryptoDHLab-Windows-x64.zip 다운로드 → 폴더 전체 압축 해제
      → CryptoDHLab.exe 더블클릭

Windows x64용이며 Python을 따로 설치할 필요가 없습니다.
EXE와 _internal 폴더를 함께 보관하세요. 코드 서명은 없습니다.

검증 환경·결과: [실제 확인한 환경, 결과, 미확인 범위 입력]
SHA256: [최종 ZIP에서 계산한 값 입력]

교육용 모델이며 표준 EKE·PAKE 또는 상용 암호 통신 구현이 아닙니다.
복호화한 예문이 로컬 로그에 남습니다. 민감한 정보는 입력하지 마세요.
```

Release 자산으로 ZIP을 첨부하고 SHA256을 설명 또는 별도 텍스트 파일로 제공합니다. 저장소와 Release가 정해진 뒤 README의 Windows 실행 안내에 실제 다운로드 링크를 연결합니다. `dist/`를 소스 Git 이력에 넣지는 않습니다.

## GitHub Pages에서 실행할 수 있나요?

이 앱의 Python 백엔드는 독립 프로세스와 로컬 TCP 소켓을 사용합니다. GitHub Pages의 정적 파일 호스팅만으로는 백엔드나 실제 실험을 실행할 수 없습니다. `web/`만 올리면 `/api/...` 요청을 처리할 서버가 없어 실습이 동작하지 않습니다.

GitHub에서는 소스·학습 문서를 읽고 Releases에서 Windows ZIP을 받아 **자신의 PC에서 실행**하도록 안내합니다. Pages를 추가한다면 소개·스크린샷·학습 자료·다운로드 안내에 사용합니다. 로컬 실험 백엔드는 공개 인터넷 서버로 노출하지 않습니다.
