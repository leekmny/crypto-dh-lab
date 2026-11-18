"""키 파일 원문을 출력하지 않는 초기화 명령."""
import argparse
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runtime import DATA_ROOT, ensure_streams

ROOT = DATA_ROOT


def generate(directory: Path, *, force=False):
    directory.mkdir(parents=True, exist_ok=True)
    paths = [directory / "alice.key", directory / "bob.key"]
    existing = [path.exists() for path in paths]
    if any(existing) and not force:
        if not all(existing) or any(len(path.read_bytes()) != 32 for path in paths):
            raise ValueError("키 파일 일부가 없거나 길이가 잘못되었습니다. --force로 새 키 쌍을 생성하세요.")
        return False
    key = secrets.token_bytes(32)
    for path in paths:
        # POSIX에서는 소유자 전용. Windows ACL은 사용자 프로필 권한을 상속한다.
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "wb") as output:
            output.write(key)
    return True


if __name__ == "__main__":
    ensure_streams()
    parser = argparse.ArgumentParser(description="Alice/Bob의 무작위 AES-256 공유키 초기화")
    parser.add_argument("--directory", type=Path, default=ROOT / ".local/keys")
    parser.add_argument("--force", action="store_true", help="기존 키를 새 키로 교체")
    args = parser.parse_args()
    try:
        created = generate(args.directory, force=args.force)
        print("새 256비트 공유키 파일 두 개를 생성했습니다. 키 원문은 출력하지 않습니다." if created else "기존 키 파일을 유지합니다.")
    except (OSError, ValueError) as error:
        print(f"키 초기화 실패: {error}")
        raise SystemExit(2)
