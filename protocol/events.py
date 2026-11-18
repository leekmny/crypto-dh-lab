from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time


class Events:
    def __init__(self, actor: str, path: str | Path):
        self.actor = actor
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, message: str, *, level: str = "info", **data):
        record = dict(time=datetime.now(timezone.utc).isoformat(timespec="milliseconds"), time_ns=time.time_ns(),
                      actor=self.actor, pid=os.getpid(), event=event, level=level, message=message, data=data)
        with self.path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record, ensure_ascii=False) + "\n")
            output.flush()
        print(f"[{self.actor}] {message}", flush=True)


def read_events(path: str | Path) -> list[dict]:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            # 프로세스가 마지막 줄을 기록하는 순간 읽은 경우 다음 polling에서 읽는다.
            continue
    return result
