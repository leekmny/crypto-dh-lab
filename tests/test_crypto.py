import copy
import secrets

import pytest

from eve import flip
from protocol.crypto import encrypt, decrypt, load_key
from protocol.errors import ProtocolError
from protocol.messages import header, unb64
from scripts.generate_keys import generate


@pytest.fixture
def encrypted():
    key = secrets.token_bytes(32)
    h = header("dh", "Alice", secrets.token_hex(16), "toy23", 0, secrets.token_bytes(32))
    return key, h, encrypt(key, b"\x08", h)


@pytest.mark.case("T02", "AES-256-GCM 암복호화·새 nonce·키 초기화")
def test_encrypt_decrypt_nonce(encrypted):
    key, h, packet = encrypted
    assert decrypt(key, packet) == b"\x08"
    assert len(unb64(packet["nonce"])) == 12
    assert len(unb64(packet["tag"])) == 16
    nonces = {encrypt(key, b"\x08", h)["nonce"] for _ in range(128)}
    assert len(nonces) == 128  # 샘플에서의 중복 검사이며 모든 미래 nonce의 유일성 증명은 아니다.


@pytest.mark.case("T02", "AES-256-GCM 암복호화·새 nonce·키 초기화")
def test_key_initialization(tmp_path):
    assert generate(tmp_path)
    key = load_key(tmp_path / "alice.key")
    assert len(key) == 32 and key == load_key(tmp_path / "bob.key")
    assert not generate(tmp_path)
    assert load_key(tmp_path / "alice.key") == key
    assert generate(tmp_path, force=True)
    assert load_key(tmp_path / "alice.key") != key


@pytest.mark.case("T04", "잘못된 사전 공유키 인증 실패")
def test_wrong_key(encrypted):
    with pytest.raises(ProtocolError) as raised:
        decrypt(secrets.token_bytes(32), encrypted[2])
    assert raised.value.code == "AUTH"


@pytest.mark.case("T05", "암호문 비트·AAD 변조 탐지")
@pytest.mark.parametrize("field", ["ciphertext", "aad"])
def test_cipher_and_aad_tamper(encrypted, field):
    key, _, packet = encrypted
    packet = copy.deepcopy(packet)
    if field == "aad":
        packet["header"]["session"] = secrets.token_hex(16)
    else:
        packet[field] = flip(packet[field])
    with pytest.raises(ProtocolError) as raised:
        decrypt(key, packet)
    assert raised.value.code == "AUTH"


@pytest.mark.case("T06", "GCM 인증 태그 변조 거부")
def test_tag_tamper(encrypted):
    key, _, packet = encrypted
    packet["tag"] = flip(packet["tag"])
    with pytest.raises(ProtocolError) as raised:
        decrypt(key, packet)
    assert raised.value.code == "AUTH"
