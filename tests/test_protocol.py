import secrets

import pytest

from eve import flip
from protocol.crypto import decrypt, encrypt
from protocol.errors import ProtocolError
from protocol.kdf import hkdf, derive, confirmation, verify_confirmation
from protocol.messages import header, expect
from protocol.replay import ReplayStore


def inputs():
    return (b"\x02", b"\x08", b"\x13", secrets.token_bytes(32), secrets.token_bytes(32), secrets.token_bytes(32))


@pytest.mark.case("T01", "HKDF 일치·문맥 결합·역할별 키 분리")
def test_rfc5869_vector_and_kdf():
    # RFC 5869 Appendix A.1, SHA-256 고정 검증 벡터.
    output = hkdf(bytes.fromhex("0b" * 22), bytes.fromhex("000102030405060708090a0b0c"),
                  bytes.fromhex("f0f1f2f3f4f5f6f7f8f9"), 42)
    assert output.hex() == "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865"
    args = inputs()
    ka, kb = derive(*args), derive(*args)
    assert ka == kb
    assert len({ka.session, ka.confirm_alice, ka.confirm_bob, ka.app_ab, ka.app_ba}) == 5
    for index in range(len(args)):
        modified = list(args)
        modified[index] = modified[index] + b"x"
        assert derive(*modified).session != ka.session


@pytest.mark.case("T10", "역할별 HMAC 키 확인 성공·변조 거부")
def test_key_confirmation():
    args = inputs()
    keys = derive(*args)
    head = header("confirm", "Alice", secrets.token_hex(16), "toy23", 1, args[3], args[4])
    packet = confirmation(keys.confirm_alice, head, args[5])
    verify_confirmation(packet, head, keys.confirm_alice, args[5])
    for key, transcript in [(keys.confirm_bob, args[5]), (keys.confirm_alice, b"wrong")]:
        with pytest.raises(ProtocolError, match="키 확인"):
            verify_confirmation(packet, head, key, transcript)
    packet["mac"] = flip(packet["mac"])
    with pytest.raises(ProtocolError) as raised:
        verify_confirmation(packet, head, keys.confirm_alice, args[5])
    assert raised.value.code == "KEY_CONFIRM"


@pytest.mark.case("T09", "영속 세션 ID·메시지 순번 재전송 거부")
def test_replay_store_and_sequence(tmp_path):
    path = tmp_path / "state.sqlite"
    sid = secrets.token_hex(16)
    ReplayStore(path).claim(sid)
    with pytest.raises(ProtocolError) as raised:
        ReplayStore(path).claim(sid)  # 새 객체·같은 DB에서도 거부
    assert raised.value.code == "REPLAY"
    args = inputs()
    old = header("app", "Alice", sid, "toy23", 2, args[3], args[4])
    packet = encrypt(secrets.token_bytes(32), b"payload", old)
    expected = {**old, "sequence": 3}
    with pytest.raises(ProtocolError) as raised:
        expect(packet, expected)
    assert raised.value.code == "CONTEXT"


@pytest.mark.case("T11", "방향별 세션 응용 메시지 암복호화")
def test_bidirectional_keys():
    args = inputs()
    keys = derive(*args)
    sid = secrets.token_hex(16)
    for sender, key, text in [("Alice", keys.app_ab, "안녕하세요 Bob"), ("Bob", keys.app_ba, "안녕하세요 Alice")]:
        packet = encrypt(key, text.encode(), header("app", sender, sid, "toy23", 2, args[3], args[4]))
        assert decrypt(key, packet).decode() == text
        wrong = keys.app_ba if sender == "Alice" else keys.app_ab
        with pytest.raises(ProtocolError):
            decrypt(wrong, packet)
