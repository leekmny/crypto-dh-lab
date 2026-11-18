"""제한된 JSON 스키마, 정규 Base64, 인증할 header."""
import base64
import binascii
import json
import re

from .errors import ProtocolError

PROTOCOL = "encrypted-dh-lab"
VERSION = 1
MAX_FRAME = 16384
MAX_MESSAGE = 4096
HEADER_FIELDS = {"protocol", "version", "type", "sender", "session", "group", "sequence", "nonce_a", "nonce_b"}


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def unb64(value: str, size: int | None = None, *, maximum: int = MAX_FRAME) -> bytes:
    if not isinstance(value, str) or len(value) > maximum * 2:
        raise ProtocolError("BASE64", "Base64 문자열 형식 또는 크기가 잘못되었습니다.")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ProtocolError("BASE64", "Base64 인코딩이 올바르지 않습니다.") from None
    if b64(decoded) != value or len(decoded) > maximum or (size is not None and len(decoded) != size):
        raise ProtocolError("BASE64", "Base64 길이 또는 정규 인코딩이 올바르지 않습니다.")
    return decoded


def _unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ProtocolError("FORMAT", "중복된 JSON 키를 거부했습니다.")
        value[key] = item
    return value


def decode_json(data: bytes) -> dict:
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, ValueError, RecursionError):
        raise ProtocolError("FORMAT", "올바른 UTF-8 JSON 패킷이 아닙니다.") from None
    if not isinstance(value, dict):
        raise ProtocolError("FORMAT", "최상위 패킷은 JSON 객체여야 합니다.")
    return value


def header(kind: str, sender: str, sid: str, group: str, sequence: int,
           nonce_a: bytes, nonce_b: bytes = b"") -> dict:
    value = dict(protocol=PROTOCOL, version=VERSION, type=kind, sender=sender,
                 session=sid, group=group, sequence=sequence,
                 nonce_a=b64(nonce_a), nonce_b=b64(nonce_b))
    validate_header(value)
    return value


def validate_header(value: dict) -> None:
    if not isinstance(value, dict) or value.keys() != HEADER_FIELDS:
        raise ProtocolError("FORMAT", "인증 header 필드가 잘못되었습니다.")
    if value["protocol"] != PROTOCOL or type(value["version"]) is not int or value["version"] != VERSION:
        raise ProtocolError("VERSION", "지원하지 않는 프로토콜 버전입니다.")
    if value["type"] not in ("dh", "confirm", "app") or value["sender"] not in ("Alice", "Bob"):
        raise ProtocolError("FORMAT", "메시지 유형 또는 송신자가 잘못되었습니다.")
    if not isinstance(value["session"], str) or not re.fullmatch(r"[0-9a-f]{32}", value["session"]):
        raise ProtocolError("FORMAT", "세션 식별자 형식이 잘못되었습니다.")
    if value["group"] not in ("toy23", "modp14") or type(value["sequence"]) is not int or not 0 <= value["sequence"] <= 2**32 - 1:
        raise ProtocolError("FORMAT", "그룹 또는 메시지 순번이 잘못되었습니다.")
    unb64(value["nonce_a"], 32)
    unb64(value["nonce_b"], 0 if value["type"] == "dh" and value["sender"] == "Alice" else 32)


def validate_packet(packet: dict) -> None:
    if not isinstance(packet, dict) or "header" not in packet:
        raise ProtocolError("FORMAT", "패킷에 인증 header가 없습니다.")
    validate_header(packet["header"])
    if packet["header"]["type"] == "confirm":
        if packet.keys() != {"header", "mac"}:
            raise ProtocolError("FORMAT", "키 확인 패킷 형식이 잘못되었습니다.")
        unb64(packet["mac"], 32)
    else:
        if packet.keys() != {"header", "nonce", "ciphertext", "tag"}:
            raise ProtocolError("FORMAT", "암호화 패킷 형식이 잘못되었습니다.")
        unb64(packet["nonce"], 12)
        unb64(packet["ciphertext"], maximum=MAX_MESSAGE)
        unb64(packet["tag"], 16)


def expect(packet: dict, expected: dict) -> None:
    validate_packet(packet)
    if packet["header"] != expected:
        raise ProtocolError("CONTEXT", "세션·역할·순번·난수 문맥이 예상 상태와 다릅니다. 재전송 또는 순서 오류를 거부했습니다.")
