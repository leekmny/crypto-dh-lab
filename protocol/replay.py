from pathlib import Path
import sqlite3
import time

from .errors import ProtocolError


class ReplayStore:
    """같은 DB 파일이 유지되는 동안 인증된 Alice session ID의 재사용을 거부."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=3) as db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (sid TEXT PRIMARY KEY, seen INTEGER NOT NULL)")

    def claim(self, sid: str) -> None:
        try:
            with sqlite3.connect(self.path, timeout=3) as db:
                db.execute("INSERT INTO sessions(sid, seen) VALUES (?, ?)", (sid, int(time.time())))
        except sqlite3.IntegrityError:
            raise ProtocolError("REPLAY", "이미 처리한 세션 식별자입니다. 저장된 상태에 따라 재전송 패킷을 거부했습니다.") from None
