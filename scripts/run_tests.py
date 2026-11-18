"""pytest 실제 출력·JSON·JUnit 결과를 남기고 실패 종료 코드를 그대로 전달한다."""
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from runtime import DATA_ROOT, RESOURCE_ROOT, ensure_streams, pytest_command

ROOT = DATA_ROOT


def main():
    ensure_streams()
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    print("실제 암호 연산·독립 프로세스·TCP·공격 검증을 실행합니다.", flush=True)
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    (ROOT / "tests").mkdir(parents=True, exist_ok=True)
    arguments = [str(RESOURCE_ROOT / "tests"), "-c", str(RESOURCE_ROOT / "pytest.ini"), "-q",
                 "--junitxml=" + str(ROOT / "tests/results.xml"), "-o", "cache_dir=" + str(ROOT / ".pytest_cache")]
    with (ROOT / "tests/output.txt").open("w", encoding="utf-8") as output:
        process = subprocess.Popen(pytest_command(arguments),
                                   cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", creationflags=flags)
        try:
            for line in process.stdout:
                print(line, end="", flush=True)
                output.write(line)
                output.flush()
            code = process.wait()
        except KeyboardInterrupt:
            process.terminate()
            process.wait(timeout=10)
            return 2
    print(f"검증 종료 코드: {code}. 상세 기록: tests/output.txt, tests/results.json, tests/results.xml")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
