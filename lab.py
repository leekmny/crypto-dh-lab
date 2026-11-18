"""독립 프로세스를 기동하고 실제 이벤트·종료 코드로만 실험을 판정한다."""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time

from protocol.cli import ROOT
from runtime import process_command
from protocol.events import Events, read_events
from protocol.messages import canonical
from protocol.session import ALICE_MESSAGE, BOB_MESSAGE
from scripts.generate_keys import generate

SCENARIOS = {
    "normal": (None, None, "정상 통신"),
    "mismatch": (None, "AUTH", "사전 공유키 불일치"),
    "cipher": ("cipher", "AUTH", "암호문 비트 변조"),
    "tag": ("tag", "AUTH", "인증 태그 변조"),
    "invalid_public": ("invalid_public", "PUBLIC_VALUE", "잘못된 공개값"),
    "malformed": ("malformed", "FORMAT", "잘못된 패킷 형식"),
    "replay": ("replay", "REPLAY", "이전 패킷 재전송"),
    "confirm": ("confirm", "KEY_CONFIRM", "키 확인값 변조"),
    "drop": ("drop", "DISCONNECT", "연결 끊김"),
    "timeout": ("timeout", "TIMEOUT", "수신 시간 초과"),
    "eve": ("none", None, "공유키 없는 Eve 도청"),
    "eve_key": ("none", None, "Eve에게 공유키 제공"),
}


def start_process(script: str, arguments: list[str], output: Path):
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    ROOT.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        return subprocess.Popen(process_command(script, arguments),
                                cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=stream,
                                stderr=subprocess.STDOUT, creationflags=flags)


def wait_listening(process, path: Path, timeout=6) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for event in read_events(path):
            if event["event"] == "listening":
                return event["data"]["port"]
        if process.poll() is not None:
            raise RuntimeError("서버 프로세스가 TCP 수신 준비 전에 종료되었습니다.")
        time.sleep(0.02)
    raise RuntimeError("서버 프로세스의 TCP 수신 준비 시간이 초과되었습니다.")


def _exchange(directory: Path, state: Path, mode: str, scenario: str, message: str, timeout: float, replay_file=None):
    directory.mkdir(parents=True, exist_ok=True)
    processes = {}
    common = ["--mode", mode, "--timeout", str(timeout)]
    try:
        bob_key = state / "keys/bob.key"
        if scenario == "mismatch":
            bob_key = state / "mismatch.key"
            bob_key.write_bytes(secrets.token_bytes(32))
        processes["Bob"] = start_process("bob.py", [*common, "--port", "0", "--key", bob_key,
                "--events", directory / "bob.jsonl", "--replay-db", state / "replay.sqlite"], directory / "bob.out.txt")
        port = wait_listening(processes["Bob"], directory / "bob.jsonl")
        attack = SCENARIOS[scenario][0]
        if attack is not None:
            args = [*common, "--port", "0", "--target-port", str(port), "--attack", attack,
                    "--events", directory / "eve.jsonl"]
            if replay_file:
                args += ["--replay-file", replay_file]
            if scenario == "eve_key":
                args += ["--reveal-key", state / "keys/alice.key"]
            if scenario == "invalid_public":
                args += ["--attack-key", state / "keys/alice.key"]
            processes["Eve"] = start_process("eve.py", args, directory / "eve.out.txt")
            port = wait_listening(processes["Eve"], directory / "eve.jsonl")
        processes["Alice"] = start_process("alice.py", [*common, "--port", str(port), "--key", state / "keys/alice.key",
                "--events", directory / "alice.jsonl", "--message", message], directory / "alice.out.txt")
        deadline = time.monotonic() + timeout * 8 + 10
        for process in processes.values():
            process.wait(timeout=max(0.1, deadline - time.monotonic()))
    finally:
        for process in processes.values():
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)
    events = sorted([event for role in processes for event in read_events(directory / f"{role.lower()}.jsonl")], key=lambda e: e["time_ns"])
    return events, {role: process.returncode for role, process in processes.items()}


def summarize(events, codes, scenario, message):
    def find(role, name):
        return [e for e in events if e["actor"] == role and e["event"] == name]
    alice_ready, bob_ready = find("Alice", "established"), find("Bob", "established")
    key_match = bool(alice_ready and bob_ready and alice_ready[-1]["data"]["transcript"] == bob_ready[-1]["data"]["transcript"])
    ar, br = find("Alice", "app_received"), find("Bob", "app_received")
    roundtrip = bool(ar and br and ar[-1]["data"]["text"] == BOB_MESSAGE and br[-1]["data"]["text"] == message)
    success = all(value == 0 for value in codes.values()) and key_match and roundtrip
    failures = [{"actor": e["actor"], "code": e["data"]["code"], "reason": e["message"]} for e in events if e["event"] == "failed"]
    expected = SCENARIOS[scenario][1]
    rejected = bool(expected and any(f["code"] == expected and f["actor"] in ("Alice", "Bob") for f in failures))
    pids = {role: next((e["pid"] for e in events if e["actor"] == role), None) for role in codes}
    return dict(success=success, passed=success if expected is None else rejected and not success,
                status="success" if success else "blocked" if rejected else "error",
                key_match=key_match, roundtrip=roundtrip, failures=failures, return_codes=codes,
                pids=pids, independent_processes=bool(pids.get("Alice") and pids.get("Bob") and pids["Alice"] != pids["Bob"]),
                expected_error=expected, packet_count=sum(e["event"] == "sent" for e in events if e["actor"] in ("Alice", "Bob")))


def run_experiment(workspace: Path = ROOT, *, mode="group14", scenario="normal", message=ALICE_MESSAGE,
                   run_id=None, timeout=3.0) -> dict:
    if mode not in ("small", "group14") or scenario not in SCENARIOS:
        raise ValueError("계산 모드 또는 실험 시나리오가 잘못되었습니다.")
    if not isinstance(message, str) or not 1 <= len(message.encode("utf-8")) <= 4096:
        raise ValueError("메시지는 UTF-8 기준 1–4096바이트여야 합니다.")
    run_id = run_id or secrets.token_hex(12)
    if len(run_id) != 24 or any(c not in "0123456789abcdef" for c in run_id):
        raise ValueError("실행 식별자가 잘못되었습니다.")
    directory = workspace / "logs" / run_id
    state = workspace / ".local/runs" / run_id
    if directory.exists() or state.exists():
        raise ValueError("이미 사용한 실행 식별자입니다.")
    directory.mkdir(parents=True)
    generate(state / "keys")
    manager = Events("실험관리자", directory / "manager.jsonl")
    manager.emit("started", "독립 Python 프로세스로 실제 TCP 실험을 시작합니다.", mode=mode, scenario=scenario)
    summary = dict(id=run_id, mode=mode, scenario=scenario, scenario_name=SCENARIOS[scenario][2])
    try:
        replay_file = None
        if scenario == "replay":
            previous, codes = _exchange(directory / "baseline", state, mode, "normal", message, timeout)
            if not summarize(previous, codes, "normal", message)["success"]:
                raise RuntimeError("재전송 대상 정상 통신을 준비하지 못했습니다.")
            original = next(e["data"]["packet"] for e in previous if e["actor"] == "Alice" and e["event"] == "sending")
            replay_file = directory / "previous-packet.json"
            replay_file.write_bytes(canonical(original))
            manager.emit("replay_prepared", "동일 키·동일 영속 DB로 완료된 이전 실제 실행의 패킷을 준비했습니다.")
        events, codes = _exchange(directory, state, mode, scenario, message, timeout, replay_file)
        summary.update(summarize(events, codes, scenario, message))
    except (RuntimeError, subprocess.TimeoutExpired, OSError) as error:
        manager.emit("failed", "실험 프로세스 관리 오류: " + str(error), level="error", code="RUNNER")
        summary.update(success=False, passed=False, status="error", key_match=False, roundtrip=False,
                       failures=[dict(actor="실험관리자", code="RUNNER", reason=str(error))], return_codes={}, pids={}, independent_processes=False, packet_count=0)
    manager.emit("finished", "실제 이벤트와 프로세스 종료 코드에 따른 실험 판정을 기록했습니다.", passed=summary["passed"], status=summary["status"])
    (directory / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def experiment_events(workspace: Path, run_id: str):
    directory = workspace / "logs" / run_id
    return sorted([event for name in ("manager", "alice", "bob", "eve") for event in read_events(directory / f"{name}.jsonl")], key=lambda e: e["time_ns"])
