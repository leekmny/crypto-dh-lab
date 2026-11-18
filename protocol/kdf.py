from dataclasses import dataclass
import hashlib
import hmac

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .errors import ProtocolError
from .messages import PROTOCOL, b64, unb64, canonical, expect


@dataclass(frozen=True)
class Keys:
    session: bytes
    confirm_alice: bytes
    confirm_bob: bytes
    app_ab: bytes
    app_ba: bytes


def hkdf(ikm: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


def transcript_hash(packet_a: dict, packet_b: dict) -> bytes:
    return hashlib.sha256(canonical({"alice_dh": packet_a, "bob_dh": packet_b})).digest()


def derive(shared: bytes, public_a: bytes, public_b: bytes, nonce_a: bytes, nonce_b: bytes, transcript: bytes) -> Keys:
    salt = hashlib.sha256(nonce_a + nonce_b).digest()
    context = canonical({"protocol": PROTOCOL, "version": 1, "A": b64(public_a), "B": b64(public_b),
                         "transcript": b64(transcript)})
    master = hkdf(shared, salt, b"edh/session/" + context)
    def sub(label):
        return hkdf(master, salt, b"edh/" + label + b"/" + context)
    return Keys(master, sub(b"confirm/Alice"), sub(b"confirm/Bob"), sub(b"app/Alice-Bob"), sub(b"app/Bob-Alice"))


def confirmation(key: bytes, head: dict, transcript: bytes) -> dict:
    mac = hmac.digest(key, b"edh/key-confirm/v1/" + canonical(head) + transcript, "sha256")
    return {"header": head.copy(), "mac": b64(mac)}


def verify_confirmation(packet: dict, expected: dict, key: bytes, transcript: bytes) -> None:
    expect(packet, expected)
    actual = unb64(packet["mac"], 32)
    wanted = unb64(confirmation(key, expected, transcript)["mac"], 32)
    if not hmac.compare_digest(actual, wanted):
        raise ProtocolError("KEY_CONFIRM", "상대방의 HMAC 키 확인값이 일치하지 않아 세션 수립을 중단했습니다.")
