# 암호화된 Diffie–Hellman 프로토콜 실험실

이 문서는 기존 README의 전체 내용을 보관한 기술 참고 문서다. 처음 시작한다면 [프로젝트 소개](../README.md)와 [학습 순서](LEARNING.md)를 먼저 읽는다. 아래 상대 경로와 명령어는 모두 `docs` 폴더가 아닌 **프로젝트 루트**를 기준으로 한다. 로컬 바탕화면 바로가기는 배포 ZIP에 자동 생성되지 않는다. 공개 배포 파일은 저장소의 Releases에서 받는다. 검증 환경과 공개 범위는 [공개 검증 요약](VERIFICATION.md)을 참고한다. 본문에 등장하는 `VALIDATION.md`는 이전 로컬 작업 기록의 파일명이다.

Alice와 Bob이 **서로 다른 Python 프로세스**에서 실제 DH 계산을 하고, **127.0.0.1 TCP 소켓**으로 암호화한 공개값을 교환하는 교육용 프로젝트다. 웹 화면은 프로세스가 기록한 실제 이벤트를 보여준다. JavaScript로 공유 비밀이나 성공 결과를 만들어 내지 않는다.

소스 실행은 Python 3.11 이상, `cryptography`, `pytest`가 필요하다. 아래 Windows 배포본은 실행 환경을 포함한다. 실험에는 외부 서비스나 API 키를 사용하지 않는다.

## Windows에서 바로 실행

`dist/CryptoDHLab/CryptoDHLab.exe` 또는 바탕화면의 **암호 프로토콜 실험실** 바로가기를 더블클릭한다. 작은 Windows 실행 창과 기본 브라우저가 자동으로 열린다. Python 설치나 명령어 입력은 필요하지 않다. 프로젝트 루트의 `실험실 실행.cmd`도 같은 EXE를 실행한다.

ZIP으로 받은 경우 폴더 전체를 압축 해제한 뒤 실행한다. `CryptoDHLab.exe`와 `_internal` 폴더를 함께 보관한다. 종료는 작은 실행 창의 **종료** 버튼 또는 창 닫기로 한다. 브라우저 탭만 닫으면 서버는 계속 실행된다. 다시 더블클릭하면 기존 실습 화면이 열린다. 기본 포트가 사용 중이면 다른 로컬 포트를 자동 선택한다.

배포본 실행 기록·키·검증 결과는 `%LOCALAPPDATA%\CryptoDHLab`에 저장한다. **기록 폴더 열기** 버튼은 그 아래 `logs` 폴더를 연다. 배포물에 기존 실험 키와 로그를 넣지 않는다. 코드 서명이 없는 Windows x64 배포본이다.

개발 환경에서 다시 빌드하려면 `powershell -NoProfile -ExecutionPolicy Bypass -File .\build-windows.ps1`을 실행한다. `requirements-build.txt`의 PyInstaller와 현재 환경의 런타임을 묶어 `dist/CryptoDHLab-Windows-x64.zip`을 생성한다. 개발 의존성 재현에는 `requirements-lock.txt`를 사용한다.

## 빠른 실행 — Windows PowerShell

현재 프로젝트 폴더에서 실행한다.

```powershell
.\run.ps1
```

Python 버전 확인 → `.venv` 준비 → 필요한 라이브러리 설치 → 공유키 파일 준비 → Python 로컬 웹 서버 시작 → 실제 Alice/Bob 자동 실험 → 브라우저 열기 순서로 진행한다. 기본은 2048비트 그룹 14다.

대시보드 주소: **http://127.0.0.1:8765**

스크립트 실행 정책에 의해 차단된 경우 다음 명령으로 해당 실행만 허용한다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
```

다른 옵션:

```powershell
.\run.ps1 -Mode small                     # 고정 작은 수 예제
.\run.ps1 -NoBrowser -NoAutoRun            # 자동 실행·브라우저 열기 없이 준비
.\run.ps1 -Port 8875                      # 대시보드 포트 변경
```

종료는 실행한 PowerShell 창에서 `Ctrl+C`. 실행 중인 실험 또는 테스트가 있으면 자식 프로세스가 제한 시간 내에 정리될 때까지 기다린다. Bob/Eve의 실험 포트는 운영체제가 자동 할당하므로 고정 포트 충돌을 피한다.

`py -3`이 구형 Python을 선택하는 컴퓨터가 있어 실행 스크립트가 버전을 확인한다. 검증 환경에서는 `python`이 3.14, `py -3`은 3.9였다. 기존 `.venv`가 3.11보다 오래된 버전이면 올바른 Python으로 가상환경을 다시 만들어야 한다.

## 자동 검증

```powershell
.\test.ps1
# 또는
powershell -NoProfile -ExecutionPolicy Bypass -File .\test.ps1
```

실제 pytest를 실행하고 종료 코드를 반환한다. 단위 테스트와 별도 프로세스 TCP 통합 테스트를 구분하며, 고정 수학 예제와 안전한 난수 실험을 모두 검사한다. 성공한 검사에만 `[PASS]`가 표시된다.

- `tests/output.txt`: 실제 콘솔 출력
- `tests/results.json`: 한국어 항목·환경·성공/실패·시간·오류 이유
- `tests/results.xml`: JUnit 결과
- `VALIDATION.md`: 수행한 검증과 보안상 한계

웹의 **전체 검증 실행**도 같은 테스트 실행기를 사용한다. 테스트 중에는 새 웹 실험을 받지 않는다. 마지막 실행의 시각과 결과를 보여주며 미실행 항목에 통과 표시를 하지 않는다.

검증 환경을 같은 버전으로 설치하려면:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

## 개별 프로세스 실행

최초 `run.ps1`이 가상환경과 키 파일을 준비한다. 수동으로 준비할 수도 있다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/generate_keys.py
```

첫 번째 PowerShell 창:

```powershell
.\.venv\Scripts\python.exe bob.py
```

두 번째 창에서 10초 안에:

```powershell
.\.venv\Scripts\python.exe alice.py
```

기본 포트는 8766, 기본 모드는 `group14`다. 두 역할에 같은 모드와 포트를 사용해야 한다. Bob은 한 연결을 처리한 뒤 종료한다. Bob을 먼저 실행하며, 창 사이 이동 시간이 더 필요하면 `--accept-timeout 60`을 사용한다.

```powershell
.\.venv\Scripts\python.exe bob.py --mode small --accept-timeout 60
.\.venv\Scripts\python.exe alice.py --mode small --message "사용자 메시지"
```

Eve 중계기를 따로 실행할 때는 Bob → Eve → Alice 순서로 실행한다.

```powershell
# 창 1
.\.venv\Scripts\python.exe bob.py --mode small --port 8766 --accept-timeout 60
# 창 2
.\.venv\Scripts\python.exe eve.py --mode small --port 8767 --target-port 8766 --accept-timeout 60
# 창 3
.\.venv\Scripts\python.exe alice.py --mode small --port 8767
```

Eve의 `--attack cipher`, `--attack tag`, `--attack confirm`, `--attack malformed`, `--attack drop`, `--attack timeout`으로 실제 패킷 변경 또는 전달 중단을 실험할 수 있다. 정상 도청은 기본 `--attack none`. 교육용 키 제공 비교는 `--reveal-key .local/keys/alice.key`. 공개값 의미 검증은 `--attack invalid_public --attack-key .local/keys/alice.key`다. 공격용 모든 접속은 코드에서 127.0.0.1로 제한한다.

웹 없이 전체 실험을 자동 실행하려면:

```powershell
.\.venv\Scripts\python.exe main.py --cli --mode small
.\.venv\Scripts\python.exe main.py --cli --mode group14 --scenario cipher
.\.venv\Scripts\python.exe main.py --cli --mode group14 --scenario replay
```

정상 실험 성공 또는 공격 실험의 기대 거부 성공이면 종료 코드 0, 기대와 다른 결과이면 2다. 개별 Alice/Bob은 정상 완료 0, 안전한 입력 거부·통신 실패 2로 종료한다.

## 화면 사용법

1. **프로토콜 실습**에서 계산 모드와 시나리오를 선택하고 메시지를 입력한 뒤 **실험 시작**을 누른다. 실행마다 새 자식 프로세스와 새 무작위 키 파일을 만든다.
2. 중앙 화살표는 실제 `sending` 이벤트를 재생한다. 송신 시도, TCP 송신 완료, 수신, GCM 인증 성공을 별도 이벤트로 구분한다. **기록 일시정지·이전·다음·재생 속도**는 기록 탐색에만 적용된다. 실제 TCP 실행을 중간에 멈추거나 암호 연산을 되돌리지 않는다.
3. Alice/Bob 패널에서 공개값, 수신한 공개값, 공유 비밀 계산, 세션 상태를 확인한다. **작은 수 계산값 공개**는 고정 예제의 a·b·S만 보여준다. 큰 수 개인 지수, 사전 공유키, 실제 세션키는 공개 버튼으로도 노출하지 않는다.
4. **단계별 연산 해설**은 목적·수식·보안 속성을 설명한다. **패킷 검사기**에서는 실제 송신 시도의 AAD, nonce, 암호문, 태그 또는 HMAC을 선택·복사한다.
5. **실행 검증**은 최종 프로세스 종료 코드, 상호 키 확인, 원문 왕복을 기준으로 판정한다. 상단 실제 완료 상태와 아래 기록 재생 위치는 서로 구분된다.
6. **보안 실험실**에서 키 불일치·암호문/태그/HMAC 변조·잘못된 공개값/형식·재전송·도청·연결 오류를 실행한다. 기대한 거부는 공격 방어 검증의 성공이며, 세션 수립 성공과 구별한다.
7. **실행 기록 저장**은 공개 패킷과 결과 이벤트 JSON을 내려받는다. **화면 기록 초기화**는 표시와 재생 상태만 지운다. 디스크의 감사 기록과 Bob의 재전송 DB는 삭제하지 않는다. 새 실행은 이전 세션키를 재사용하지 않는다.

## 구현한 프로토콜

원본의 두 공개값 교환:

```text
Alice: A = pow(g, a, p)
Alice → Bob: AES-256-GCM(K_AB, 고정길이(A), AAD_A)
Bob:   B = pow(g, b, p)
Bob → Alice: AES-256-GCM(K_AB, 고정길이(B), AAD_B)

Alice: S_A = pow(B, a, p)
Bob:   S_B = pow(A, b, p)
```

여기에 별도로 **HKDF, 역할별 HMAC 키 확인 두 메시지, 방향별 암호 응용 메시지 두 개**를 추가한다. 정상 TCP 세션은 총 6개의 프레임을 교환한다.

- 작은 수: p=23, g=5, a=6, b=15. 실제 `pow` 결과 A=8, B=19, S_A=S_B=2.
- 큰 수: RFC 3526 §3의 2048비트 MODP Group 14, g=2, q=(p−1)/2. 지수는 `secrets.randbelow`로 균일 범위에서 선택하고 공개값 범위를 확인한다. 수신 공개값은 `2 ≤ Y ≤ p−2`, `pow(Y,q,p)==1`을 모두 검사한다.
- DH 정수는 big-endian 고정 길이(작은 수 1바이트, 그룹 14 256바이트)다. 길이와 범위가 다르면 거부한다. 작은 수는 전체 곱셈군의 교육용 예시이며 큰 수의 q 부분군 검증과 다르다.
- K_AB: 32바이트 무작위 AES 키, 하드코딩 없음. AES-GCM은 매 암호화에 새 12바이트 무작위 nonce와 16바이트 태그를 사용한다.
- AAD: 정렬된 ASCII JSON header 전체. protocol/version/type/sender/session/group/sequence/nonce_a/nonce_b를 인증한다.
- KDF: S의 고정 길이 바이트를 입력으로, SHA-256(nonce_a∥nonce_b)를 salt로 사용한다. info에 프로토콜·버전·A·B·두 DH 패킷 전체의 transcript hash를 결합한다. transcript 안에 session ID·역할·그룹·양측 난수와 암호문이 포함된다.
- 루트에서 서로 다른 label로 Alice 확인 키, Bob 확인 키, A→B 응용 키, B→A 응용 키를 유도한다. 역할별 HMAC-SHA-256은 header와 transcript를 보호하며 `hmac.compare_digest`로 확인한다.
- 패킷 순서는 각 역할의 코드 상태와 기대 header로 제한한다. DH 순번 0 → 키 확인 1 → 응용 2. 앱 메시지는 한 방향당 한 개이며, 교환 후 연결을 닫는다.
- Bob은 **GCM 인증·공개값 검증 후** 세션 ID를 SQLite에 원자적으로 등록한다. 동일 DB에 이미 있는 ID를 거부한다. 재전송 실험은 같은 키·DB로 정상 실행을 먼저 수행한 후 새 Bob 프로세스에 그 실제 패킷을 주입한다.

### 패킷 형식

```text
4바이트 unsigned big-endian 길이 + UTF-8 JSON

암호화 패킷: { header, nonce, ciphertext, tag }
키 확인 패킷: { header, mac }
header: { protocol, version, type, sender, session, group,
          sequence, nonce_a, nonce_b }
```

바이너리는 정규 Base64다. 세션 ID는 무작위 128비트 hex, 양측 세션 난수는 각각 256비트다. Alice 첫 패킷의 nonce_b만 비어 있다. header와 패킷의 정확한 필드를 검증하고 중복 JSON 키·잘못된 UTF-8·비정규 Base64를 거부한다.

프레임 최대 16KiB, 응용 평문 최대 4096바이트. 최초 접속 대기 기본 10초, 개별 CLI의 연결 후 I/O 기본 5초다. 웹 오케스트레이터 I/O는 3초다. 부분 수신을 반복해도 각 헤더/본문 수신의 전체 제한 시간을 넘기지 못한다.

## 파일 역할

| 파일 | 역할 |
|---|---|
| `alice.py`, `bob.py` | 별도 OS 프로세스의 TCP 클라이언트·서버 |
| `eve.py` | 실제 TCP 프레임 중계·관찰·변조 |
| `lab.py` | 프로세스 기동·정리, 실제 이벤트·종료 코드 기반 판정 |
| `main.py` | 127.0.0.1 전용 HTTP 서버·실험/테스트 API |
| `protocol/dh.py` | 표준 그룹·개인 지수·pow·공개값 검증 |
| `protocol/crypto.py`, `kdf.py` | AES-GCM·HKDF·HMAC |
| `protocol/messages.py`, `transport.py` | 스키마·AAD·Base64·길이 프레이밍·타임아웃 |
| `protocol/session.py` | 두 역할의 독립 상태 진행·키 확인·응용 통신 |
| `protocol/replay.py`, `events.py` | SQLite 중복 세션 검사·구조화 이벤트 |
| `web/` | 한국어 반응형 UI·실제 기록 재생, 암호 연산 없음 |
| `scripts/generate_keys.py` | 공유키 초기화·명시적 교체 `--force` |
| `tests/` | T01–T14 자동 검증, 공식 그룹 고정 fixture |

## 데이터·키 보관

- 개별 CLI 키: `.local/keys/alice.key`, `.local/keys/bob.key`
- 웹/자동 실험 키와 상태: `.local/runs/<실행ID>/keys/`, `replay.sqlite`
- 개별 Bob 재전송 상태: `.local/replay.sqlite`
- 자동 실험 기록: `logs/<실행ID>/{alice,bob,eve,manager}.jsonl`, `summary.json`
- 재전송 실험의 준비 정상 실행: 같은 로그 폴더의 `baseline/`
- 키 파일, `.local`, 로그, 생성된 테스트 결과는 `.gitignore`로 제외한다. 키를 출력하거나 HTTP로 제공하지 않는다. POSIX 키 생성 권한은 0600이며, Windows는 사용자 프로필의 상속 ACL을 사용한다.
- 응용 메시지의 **복호화된 원문은 학습용 이벤트에 저장**한다. 기밀 메시지를 입력하지 않는다. 큰 수 a·b·S와 모든 실제 키 원문은 기록하지 않는다. Python 메모리의 안전한 영구 삭제는 보장하지 않는다.

## 보안상 한계

이 설계는 수업용 모델이며 표준 EKE·PAKE 또는 검증된 상용 인증 키 교환과 동일하지 않다. 공식 보안 증명·전문 감사·상수 시간 DH 구현을 제공하지 않는다. Python 정수 `pow`는 상수 시간 연산으로 보장되지 않는다. 개인 지수는 매번 새로 생성하지만 완전한 전방향 안전성을 인증받은 구현이라고 주장하지 않는다.

AES의 키 길이가 256비트라는 사실은 2048비트 DH를 포함한 전체 설계가 256비트 보안 강도를 가진다는 뜻이 아니다.

K_AB를 아는 Eve는 과거 패킷에서 A·B를 복호화할 수 있다. 이것만으로 큰 수 DH의 a·b·S가 자동 복구되지는 않지만 능동 위장·변조는 가능하다. 작은 수의 이산로그는 쉽게 풀 수 있다. `eve` 실험의 임의 키 한 번 실패를 공격 불가능성의 증명으로 해석하면 안 된다.

재전송 DB를 삭제·교체하거나 여러 서버가 공유하지 않으면 기존 세션 ID 중복 검사는 사라진다. 새로운 Bob 난수·transcript·HMAC도 과거 전체 세션의 단순 재사용을 방해하지만, DB가 없는 모든 공격에 안전하다는 주장은 하지 않는다. 저장소의 수명·용량·복제·정리는 실서비스 수준으로 설계하지 않았다.

localhost는 같은 PC의 악성 프로그램이나 사용자로부터 비밀을 보호하는 경계가 아니다. 웹 API는 Host·Origin·JSON 형식과 경로를 제한하지만 사용자 인증·TLS·운영용 키 관리·서비스 거부 방어는 제공하지 않는다. 배포하거나 외부 주소에 바인딩하지 말고 실제 서비스에는 TLS 1.3 등 검토된 표준과 감사된 구현을 사용한다.

## 공식 근거

- [RFC 3526 §3 — 그룹 14의 소수와 생성원](https://www.rfc-editor.org/rfc/rfc3526.html#section-3)
- [RFC 2785 §3.1 — 공개값 범위·부분군 검증](https://www.rfc-editor.org/rfc/rfc2785.html#section-3.1)
- [RFC 5869 — HKDF와 부록 A.1 검증 벡터](https://www.rfc-editor.org/rfc/rfc5869.html)
- [cryptography — 인증 암호 AES-GCM](https://cryptography.io/en/latest/hazmat/primitives/aead/)
- [Python secrets — 안전한 난수 생성](https://docs.python.org/3/library/secrets.html)
