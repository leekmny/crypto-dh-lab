# 기여 안내

이 프로젝트는 Diffie–Hellman 키 교환, 인증 암호, 키 확인을 실제 로컬 TCP 통신으로 학습하는 실험실입니다. 수식 설명과 화면의 판정이 실제 Python 프로세스·이벤트·종료 코드와 일치하도록 개선해 주세요.

## 개발 환경

현재 직접 검증한 소스 환경은 Windows x64와 Python 3.14입니다. 프로젝트 폴더에서 PowerShell로 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe scripts/run_tests.py
```

화면은 `powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1`로 실행합니다. [기술 참고 문서](docs/REFERENCE.md)에 개별 Alice·Bob 실행 방법과 시나리오 설명이 있습니다.

## 변경과 검증

- 버그 수정에는 문제를 재현하는 테스트를 먼저 추가하고 전체 테스트를 실행해 주세요.
- 실험은 `127.0.0.1`에서 수행하며, 예제용 메시지를 사용해 주세요.
- 화면의 성공·거부 판정은 실제 결과를 따르고, 미실행 검사를 통과로 표시하지 않아야 합니다.
- 키 파일, `.local/`, 개인 실험 로그, 실제 기밀 메시지와 개인정보를 커밋하거나 Issue에 첨부하지 마세요.
- 의존성이나 프로토콜을 바꾸면 재현 가능한 설치 방법, 테스트, 관련 설명도 함께 갱신해 주세요.

Pull Request에는 문제와 바뀐 동작, 재현 단계, 실행한 테스트와 환경을 적어 주세요. 화면을 바꾸었다면 해당 화면과 작은 창에서의 확인 결과도 포함해 주세요. 실패하거나 실행하지 못한 검사는 그대로 밝혀 주세요.

GitHub Actions 설정은 Windows·Python 3.14에서 소스 전체 테스트를 실행하고 결과 파일을 보관합니다. 원격 실행 결과는 해당 실행의 Actions 기록으로 확인합니다. EXE의 실제 실행과 화면 확인은 별도 검증이 필요합니다.

## 문제 제보

일반 문제는 사용한 버전 또는 커밋, Windows·Python 버전, 계산 모드, 시나리오, 재현 단계, 기대한 결과와 실제 결과를 포함해 Issue로 남겨 주세요. 민감한 정보가 있는 보안 문제는 [SECURITY.md](SECURITY.md)를 따라 주세요.
