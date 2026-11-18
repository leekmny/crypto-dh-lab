import secrets
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .errors import ProtocolError
from .messages import b64, unb64, canonical, validate_header, validate_packet, MAX_MESSAGE


def load_key(path: str | Path) -> bytes:
    key = Path(path).read_bytes()
    if len(key) != 32:
        raise ProtocolError("KEY", "키 파일은 정확히 32바이트여야 합니다. 초기화 명령을 실행하세요.")
    return key


def encrypt(key: bytes, plaintext: bytes, head: dict) -> dict:
    validate_header(head)
    if len(key) != 32 or len(plaintext) > MAX_MESSAGE:
        raise ProtocolError("KEY_OR_SIZE", "AES-256 키 길이 또는 평문 크기가 잘못되었습니다.")
    nonce = secrets.token_bytes(12)
    sealed = AESGCM(key).encrypt(nonce, plaintext, canonical(head))
    return {"header": head.copy(), "nonce": b64(nonce), "ciphertext": b64(sealed[:-16]), "tag": b64(sealed[-16:])}


def decrypt(key: bytes, packet: dict) -> bytes:
    validate_packet(packet)
    if packet["header"]["type"] == "confirm":
        raise ProtocolError("FORMAT", "키 확인 패킷은 AES 복호화 대상이 아닙니다.")
    if len(key) != 32:
        raise ProtocolError("KEY", "AES-256 키 길이가 잘못되었습니다.")
    try:
        return AESGCM(key).decrypt(unb64(packet["nonce"], 12),
                                   unb64(packet["ciphertext"]) + unb64(packet["tag"], 16),
                                   canonical(packet["header"]))
    except InvalidTag:
        raise ProtocolError("AUTH", "AES-GCM 인증 복호화 실패: 공유키 불일치 또는 패킷 변조를 탐지했습니다.") from None
