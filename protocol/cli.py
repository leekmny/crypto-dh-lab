import argparse
from pathlib import Path
import sqlite3
import sys

from runtime import DATA_ROOT
from .errors import ProtocolError
from .events import Events

ROOT = DATA_ROOT


def parser(role):
    result = argparse.ArgumentParser(description=f"{role} — 로컬 교육용 암호화 DH TCP 프로세스")
    result.add_argument("--mode", choices=("small", "group14"), default="group14", help="계산 모드")
    result.add_argument("--port", type=int, default=8766, help="127.0.0.1 TCP 포트 (Bob은 0으로 자동 할당 가능)")
    result.add_argument("--key", type=Path, default=ROOT / ".local/keys" / f"{role.lower()}.key", help="256비트 키 파일")
    result.add_argument("--events", type=Path, default=ROOT / "logs" / f"{role.lower()}.jsonl", help="구조화 이벤트 경로")
    result.add_argument("--timeout", type=float, default=5, help="소켓 제한 시간(초)")
    result.add_argument("--accept-timeout", type=float, default=10, help="프로세스 기동을 고려한 최초 접속 대기 시간(초)")
    return result


def execute(role, args, action):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    events = Events(role, args.events)
    try:
        if not 0.1 <= args.timeout <= 30 or not 0.1 <= args.accept_timeout <= 60 or not 0 <= args.port <= 65535:
            raise ProtocolError("CONFIG", "포트 또는 제한 시간 설정이 올바르지 않습니다.")
        action(events)
        return 0
    except ProtocolError as error:
        events.emit("failed", str(error), level="error", code=error.code)
    except (OSError, ValueError, sqlite3.Error):
        events.emit("failed", "파일·소켓·상태 저장소 처리에 실패했습니다. 경로와 포트, 초기화를 확인하세요.", level="error", code="LOCAL_IO")
    return 2
