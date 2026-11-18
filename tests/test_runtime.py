"""Portable builds must launch real workers and keep writable data outside resources."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


SOURCE = Path(__file__).resolve().parent.parent


def runtime_module():
    assert importlib.util.find_spec("runtime") is not None, "portable runtime support is missing"
    import runtime
    return runtime


@pytest.mark.case("T15", "배포 실행기의 독립 프로세스·저장 경로 검증")
def test_runtime_command_launches_real_bob(tmp_path):
    runtime = runtime_module()
    from scripts.generate_keys import generate
    generate(tmp_path / "keys")
    events = tmp_path / "bob.jsonl"
    command = runtime.process_command("bob.py", ["--key", tmp_path / "keys/bob.key", "--events", events,
        "--replay-db", tmp_path / "replay.sqlite", "--port", "0", "--accept-timeout", "0.1"])
    process = subprocess.run(command, cwd=tmp_path, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5)
    assert process.returncode == 2, process.stdout
    records = [json.loads(line) for line in events.read_text(encoding="utf-8").splitlines()]
    assert records[0]["event"] == "listening"
    assert records[-1]["data"]["code"] == "TIMEOUT"
    assert records[0]["pid"] != os.getpid()


@pytest.mark.case("T15", "배포 실행기의 독립 프로세스·저장 경로 검증")
@pytest.mark.skipif(getattr(sys, "frozen", False), reason="source interpreter path simulation; frozen paths are exercised by packaged workers")
def test_frozen_paths_keep_data_outside_read_only_resources(tmp_path):
    runtime = runtime_module()
    code = """import json, runpy, sys
sys.frozen = True
sys._MEIPASS = sys.argv[2]
r = runpy.run_path(sys.argv[1])
print(json.dumps([str(r['RESOURCE_ROOT']), str(r['DATA_ROOT'])]))
"""
    resources = tmp_path / "resources"
    local = tmp_path / "profile"
    env = {**os.environ, "LOCALAPPDATA": str(local)}
    env.pop("DH_LAB_DATA_DIR", None)
    process = subprocess.run([sys.executable, "-c", code, runtime.__file__, str(resources)], env=env,
                             stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True)
    assert json.loads(process.stdout) == [str(resources), str(local / "CryptoDHLab")]


@pytest.mark.case("T15", "배포 실행기의 독립 프로세스·저장 경로 검증")
def test_explicit_data_directory_is_shared_with_child_processes(tmp_path):
    runtime = runtime_module()
    from scripts.generate_keys import generate
    data = tmp_path / "별도 데이터"
    generate(data / ".local/keys")
    env = {**os.environ, "DH_LAB_DATA_DIR": str(data), "PYTHONUTF8": "1"}
    process = subprocess.run(runtime.process_command("bob.py", ["--port", "0", "--accept-timeout", "0.1"]),
                             cwd=tmp_path, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert process.returncode == 2, process.stderr
    records = [json.loads(line) for line in (data / "logs/bob.jsonl").read_text(encoding="utf-8").splitlines()]
    assert records[0]["event"] == "listening"
    assert records[-1]["data"]["code"] == "TIMEOUT"


@pytest.mark.case("T15", "배포 실행기의 독립 프로세스·저장 경로 검증")
def test_frozen_children_use_worker_dispatch_instead_of_python_flags(monkeypatch):
    runtime = runtime_module()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert runtime.process_command("alice.py", ["--mode", "small"]) == [sys.executable, "--worker", "alice.py", "--mode", "small"]
    assert runtime.pytest_command(["-q"]) == [sys.executable, "--pytest", "-q"]


@pytest.mark.case("T15", "배포 실행기의 독립 프로세스·저장 경로 검증")
def test_worker_rejects_unrecognized_scripts(tmp_path):
    entry = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(SOURCE / "frozen_entry.py")]
    process = subprocess.run([*entry, "--worker", "../other.py"],
                             cwd=tmp_path, stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert process.returncode == 2


@pytest.mark.case("T15", "배포 실행기의 독립 프로세스·저장 경로 검증")
def test_worker_dispatch_executes_actual_script_from_any_working_directory(tmp_path):
    entry = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, str(SOURCE / "frozen_entry.py")]
    process = subprocess.run([*entry, "--worker", "bob.py", "--help"],
                             cwd=tmp_path, stdin=subprocess.DEVNULL, capture_output=True, timeout=5)
    assert process.returncode == 0, process.stderr
    assert b"--replay-db" in process.stdout


@pytest.mark.case("T15", "배포 실행기의 독립 프로세스·저장 경로 검증")
def test_windowless_streams_allow_logging_without_console(monkeypatch):
    runtime = runtime_module()
    streams = []
    with monkeypatch.context() as context:
        for name in ("stdin", "stdout", "stderr"):
            context.setattr(sys, name, None)
        runtime.ensure_streams()
        print("worker can log", flush=True)
        sys.stderr.write("diagnostic")
        streams.extend((sys.stdin, sys.stdout, sys.stderr))
        assert all(stream is not None for stream in streams)
    for stream in streams:
        stream.close()


@pytest.mark.skipif(os.name != "nt", reason="Windows console-handle regression")
@pytest.mark.case("T15", "배포 실행기의 독립 프로세스·저장 경로 검증")
def test_worker_launch_does_not_inherit_broken_console_input(tmp_path):
    import ctypes
    from ctypes import wintypes
    from lab import start_process
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.SetStdHandle.argtypes = [wintypes.DWORD, wintypes.HANDLE]
    original = kernel.GetStdHandle(-10 & 0xFFFFFFFF)
    output = tmp_path / "bob-help.txt"
    try:
        assert kernel.SetStdHandle(-10 & 0xFFFFFFFF, wintypes.HANDLE(-1))
        process = start_process("bob.py", ["--help"], output)
        assert process.wait(timeout=5) == 0
    finally:
        kernel.SetStdHandle(-10 & 0xFFFFFFFF, original)
    assert "--replay-db" in output.read_text(encoding="utf-8")
