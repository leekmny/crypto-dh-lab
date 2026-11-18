import socket
import struct

import pytest

from lab import run_experiment, experiment_events, start_process, wait_listening
from protocol.events import read_events
from scripts.generate_keys import generate


@pytest.mark.parametrize("scenario, code", [
    pytest.param("mismatch", "AUTH", marks=pytest.mark.case("T04", "사전 공유키 불일치 실제 통신 거부")),
    pytest.param("cipher", "AUTH", marks=pytest.mark.case("T05", "실제 네트워크 암호문 비트 변조 탐지")),
    pytest.param("tag", "AUTH", marks=pytest.mark.case("T06", "실제 네트워크 인증 태그 변조 탐지")),
    pytest.param("invalid_public", "PUBLIC_VALUE", marks=pytest.mark.case("T07", "GCM 인증 후 잘못된 DH 공개값 거부")),
    pytest.param("malformed", "FORMAT", marks=pytest.mark.case("T08", "실제 네트워크 잘못된 패킷 거부")),
    pytest.param("replay", "REPLAY", marks=pytest.mark.case("T09", "프로세스 재기동 후 이전 실제 패킷 거부")),
    pytest.param("confirm", "KEY_CONFIRM", marks=pytest.mark.case("T10", "실제 네트워크 키 확인값 변조 거부")),
    pytest.param("drop", "DISCONNECT", marks=pytest.mark.case("T12", "실제 연결 끊김·제한 시간 안전 종료")),
    pytest.param("timeout", "TIMEOUT", marks=pytest.mark.case("T12", "실제 연결 끊김·제한 시간 안전 종료")),
])
def test_actual_attacks(tmp_path, scenario, code):
    result = run_experiment(tmp_path, mode="small", scenario=scenario, timeout=1.2)
    assert result["passed"] and not result["success"], result
    assert any(f["actor"] == "Bob" and f["code"] == code for f in result["failures"]), result
    assert all(value in (0, 2) for value in result["return_codes"].values())
    events = experiment_events(tmp_path, result["id"])
    assert not any(e["event"] == "established" for e in events)
    if scenario not in ("mismatch",):
        assert any(e["actor"] == "Eve" and e["event"] == "modified" for e in events)


@pytest.mark.case("T08", "프레임 크기·잘못된 JSON·중복 키·UTF-8 안전 거부")
@pytest.mark.parametrize("payload, code", [
    (struct.pack("!I", 16385), "FRAME_SIZE"),
    (struct.pack("!I", 0), "FRAME_SIZE"),
    (struct.pack("!I", 1) + b"{", "FORMAT"),
    (struct.pack("!I", 13) + b'{"x":1,"x":2}', "FORMAT"),
    (struct.pack("!I", 1) + b"\xff", "FORMAT"),
    (struct.pack("!I", 20) + b"{", "DISCONNECT"),
])
def test_malformed_tcp_frames(tmp_path, payload, code):
    keys = tmp_path / "keys"
    generate(keys)
    path = tmp_path / "bob.jsonl"
    process = start_process("bob.py", ["--mode", "small", "--key", keys / "bob.key", "--events", path,
            "--replay-db", tmp_path / "replay.sqlite", "--port", "0", "--timeout", "1"], tmp_path / "bob.out.txt")
    try:
        port = wait_listening(process, path)
        with socket.create_connection(("127.0.0.1", port), timeout=1) as client:
            client.sendall(payload)
        assert process.wait(timeout=4) == 2
        assert read_events(path)[-1]["data"]["code"] == code
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)


@pytest.mark.case("T12", "서버 접속 대기 제한 시간 안전 종료")
def test_no_client_timeout(tmp_path):
    generate(tmp_path / "keys")
    process = start_process("bob.py", ["--key", tmp_path / "keys/bob.key", "--port", "0", "--timeout", "0.3", "--accept-timeout", "0.3",
            "--events", tmp_path / "bob.jsonl", "--replay-db", tmp_path / "replay.sqlite"], tmp_path / "out.txt")
    try:
        assert process.wait(timeout=4) == 2
        assert read_events(tmp_path / "bob.jsonl")[-1]["data"]["code"] == "TIMEOUT"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)


@pytest.mark.case("T13", "Eve 실제 도청·키 제공 전후 공개값 접근 비교")
@pytest.mark.parametrize("provided", [False, True])
def test_eve_capture(tmp_path, provided):
    result = run_experiment(tmp_path, mode="small", scenario="eve_key" if provided else "eve")
    assert result["success"]
    events = [e for e in experiment_events(tmp_path, result["id"]) if e["actor"] == "Eve"]
    assert len([e for e in events if e["event"] == "observed"]) == 6
    if provided:
        assert {e["data"]["public_value"] for e in events if e["event"] == "eve_decrypted"} == {8, 19}
    else:
        assert [e["data"]["code"] for e in events if e["event"] == "eve_blocked"] == ["AUTH", "AUTH"]
        assert not any(e["event"] == "eve_decrypted" for e in events)
