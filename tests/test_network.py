import json
import os

import pytest

from lab import run_experiment, experiment_events
from protocol.session import ALICE_MESSAGE, BOB_MESSAGE


@pytest.mark.case("T03", "독립 프로세스·실제 TCP·키 확인·메시지 왕복")
@pytest.mark.parametrize("mode", ["small", "group14", "group14"])
def test_actual_processes(tmp_path, mode):
    result = run_experiment(tmp_path, mode=mode, timeout=4)
    assert result["success"] and result["passed"]
    assert result["return_codes"] == {"Bob": 0, "Alice": 0}
    assert result["independent_processes"] and os.getpid() not in result["pids"].values()
    assert result["key_match"] and result["roundtrip"] and result["packet_count"] == 6
    events = experiment_events(tmp_path, result["id"])
    sent = [e["data"]["packet"] for e in events if e["event"] == "sending"]
    received = [e["data"]["packet"] for e in events if e["event"] == "received"]
    assert len(sent) == len(received) == 6
    assert all(packet in received for packet in sent)
    assert len({p["nonce"] for p in sent if "nonce" in p}) == 4
    for role in ("Alice", "Bob"):
        own = [e for e in events if e["actor"] == role]
        names = [e["event"] for e in own]
        assert names.index("decrypted") < names.index("shared") < names.index("derived") < names.index("key_confirmed") < names.index("established") < names.index("app_received")
        if role == "Alice":
            assert names.index("public") < names.index("encrypted") < names.index("connected") < names.index("sending")
        else:
            assert names.index("decrypted") < names.index("public")
    if mode == "small":
        assert [e["data"]["value"] for e in events if e["event"] == "shared"] == [2, 2]
    else:
        assert all(e["data"].get("value") is None for e in events if e["event"] in ("shared", "private"))
    serialized = json.dumps(events)
    key = (tmp_path / ".local/runs" / result["id"] / "keys/alice.key").read_bytes()
    assert key.hex() not in serialized
    assert BOB_MESSAGE in [e["data"]["text"] for e in events if e["event"] == "app_received"]


@pytest.mark.case("T11", "사용자 응용 메시지 실제 왕복")
def test_custom_message(tmp_path):
    message = "사용자 메시지 <script>표시용 문자</script> 🔐"
    result = run_experiment(tmp_path, mode="small", message=message)
    events = experiment_events(tmp_path, result["id"])
    assert result["roundtrip"]
    assert any(e["actor"] == "Bob" and e["event"] == "app_received" and e["data"]["text"] == message for e in events)
