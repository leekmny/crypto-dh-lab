"""각 역할은 자신의 지수 하나만 보유한다. 역할 간 상태 공유 없이 TCP로 교환한다."""
import secrets
import socket

from .crypto import encrypt, decrypt
from .dh import Group
from .errors import ProtocolError
from .events import Events
from .kdf import derive, transcript_hash, confirmation, verify_confirmation
from .messages import header, expect, unb64, validate_packet, MAX_MESSAGE
from .replay import ReplayStore
from .transport import send, receive

ALICE_MESSAGE = "안녕하세요 Bob. 이것은 암호화된 메시지입니다."
BOB_MESSAGE = "안녕하세요 Alice. 복호화에 성공했습니다."


def send_logged(sock, packet, events):
    events.emit("sending", "인증된 패킷을 TCP로 전송합니다.", packet=packet)
    send(sock, packet)
    events.emit("sent", "TCP 패킷 전송을 완료했습니다.", kind=packet["header"]["type"])


def receive_logged(sock, events):
    packet = receive(sock)
    validate_packet(packet)
    events.emit("received", "TCP 패킷을 수신했습니다. 아직 인증 전입니다.", packet=packet)
    return packet


def public_for_role(group: Group, role: str, events: Events):
    private = group.private(role)
    events.emit("private", "DH 개인 비밀 지수를 준비했습니다.",
                value=private if group.name == "toy23" else None, bits=private.bit_length())
    public = group.public(private)
    events.emit("public", "모듈러 거듭제곱으로 DH 공개값을 계산했습니다.",
                value=str(public) if group.name == "toy23" else group.encode(public).hex(),
                formula=f"{group.g}^{private} mod {group.p} = {public}" if group.name == "toy23" else "g^개인비밀 mod p (2048비트)")
    return private, public


def key_material(group, private, peer, pub_a, pub_b, na, nb, pa, pb, events):
    shared = group.shared(peer, private)
    events.emit("shared", "자신의 비밀 지수와 검증된 상대 공개값으로 공유 비밀을 계산했습니다.",
                value=shared if group.name == "toy23" else None,
                formula=f"{peer}^{private} mod {group.p} = {shared}" if group.name == "toy23" else "상대공개값^개인비밀 mod p")
    transcript = transcript_hash(pa, pb)
    keys = derive(group.encode(shared), group.encode(pub_a), group.encode(pub_b), na, nb, transcript)
    events.emit("derived", "HKDF-SHA-256으로 세션 루트·역할별 확인 키·방향별 응용 키를 유도했습니다.",
                transcript=transcript.hex(), keys_hidden=True)
    return keys, transcript


def decode_message(raw: bytes) -> str:
    if len(raw) > MAX_MESSAGE:
        raise ProtocolError("MESSAGE_SIZE", "응용 메시지가 크기 제한을 초과했습니다.")
    try:
        return raw.decode("utf-8")
    except UnicodeError:
        raise ProtocolError("MESSAGE_ENCODING", "응용 메시지가 올바른 UTF-8이 아닙니다.") from None


def prepare_alice(group: Group, psk: bytes, events: Events, message: str):
    if not isinstance(message, str) or not 1 <= len(message.encode("utf-8")) <= MAX_MESSAGE:
        raise ProtocolError("MESSAGE_SIZE", "메시지는 UTF-8 기준 1–4096바이트여야 합니다.")
    sid, na = secrets.token_hex(16), secrets.token_bytes(32)
    events.emit("initialized", "새 세션 식별자와 Alice 세션 난수를 생성했습니다.", session=sid, group=group.name)
    a, public_a = public_for_role(group, "Alice", events)
    pa = encrypt(psk, group.encode(public_a), header("dh", "Alice", sid, group.name, 0, na))
    events.emit("encrypted", "공개값 A를 사전 공유 AES-256 키로 암호화했습니다.", nonce=pa["nonce"])
    return sid, na, a, public_a, pa


def run_alice(sock: socket.socket, group: Group, psk: bytes, events: Events,
              prepared: tuple, message: str = ALICE_MESSAGE) -> None:
    sid, na, a, public_a, pa = prepared
    send_logged(sock, pa, events)
    pb = receive_logged(sock, events)
    # Bob 난수는 최초 응답에서 수신하되 나머지 문맥은 기존 상태와 일치해야 한다.
    nb = unb64(pb["header"]["nonce_b"], 32)
    expect(pb, header("dh", "Bob", sid, group.name, 0, na, nb))
    public_b = group.decode_public(decrypt(psk, pb))
    events.emit("decrypted", "Bob 공개값 B의 GCM 인증·고정 길이·범위·그룹 검증을 완료했습니다.",
                value=str(public_b) if group.name == "toy23" else group.encode(public_b).hex())
    keys, transcript = key_material(group, a, public_b, public_a, public_b, na, nb, pa, pb, events)
    send_logged(sock, confirmation(keys.confirm_alice, header("confirm", "Alice", sid, group.name, 1, na, nb), transcript), events)
    verify_confirmation(receive_logged(sock, events), header("confirm", "Bob", sid, group.name, 1, na, nb), keys.confirm_bob, transcript)
    events.emit("key_confirmed", "Bob의 역할별 HMAC 키 확인값을 상수 시간 비교로 검증했습니다.")
    events.emit("established", "상호 키 확인 후 세션을 수립했습니다. 키 원문은 공개하지 않습니다.", transcript=transcript.hex())
    app = encrypt(keys.app_ab, message.encode("utf-8"), header("app", "Alice", sid, group.name, 2, na, nb))
    send_logged(sock, app, events)
    reply = receive_logged(sock, events)
    expect(reply, header("app", "Bob", sid, group.name, 2, na, nb))
    text = decode_message(decrypt(keys.app_ba, reply))
    events.emit("app_received", "Bob의 응용 메시지를 방향별 키로 인증·복호화했습니다.", text=text)
    events.emit("complete", "Alice의 암호화 메시지 왕복이 정상 완료되었습니다.")


def run_bob(sock: socket.socket, group: Group, psk: bytes, events: Events, replay: ReplayStore) -> None:
    pa = receive_logged(sock, events)
    h = pa["header"]
    sid, na = h["session"], unb64(h["nonce_a"], 32)
    expect(pa, header("dh", "Alice", sid, group.name, 0, na))
    public_a = group.decode_public(decrypt(psk, pa))
    events.emit("decrypted", "Alice 공개값 A의 GCM 인증·고정 길이·범위·그룹 검증을 완료했습니다.",
                value=str(public_a) if group.name == "toy23" else group.encode(public_a).hex())
    replay.claim(sid)
    events.emit("replay_checked", "인증된 세션 식별자를 영속 저장하고 중복을 검사했습니다.", session=sid)
    nb = secrets.token_bytes(32)
    b, public_b = public_for_role(group, "Bob", events)
    pb = encrypt(psk, group.encode(public_b), header("dh", "Bob", sid, group.name, 0, na, nb))
    events.emit("encrypted", "공개값 B를 사전 공유 AES-256 키로 암호화했습니다.", nonce=pb["nonce"])
    send_logged(sock, pb, events)
    keys, transcript = key_material(group, b, public_a, public_a, public_b, na, nb, pa, pb, events)
    verify_confirmation(receive_logged(sock, events), header("confirm", "Alice", sid, group.name, 1, na, nb), keys.confirm_alice, transcript)
    events.emit("key_confirmed", "Alice의 역할별 HMAC 키 확인값을 상수 시간 비교로 검증했습니다.")
    send_logged(sock, confirmation(keys.confirm_bob, header("confirm", "Bob", sid, group.name, 1, na, nb), transcript), events)
    events.emit("established", "상호 키 확인 후 세션을 수립했습니다. 키 원문은 공개하지 않습니다.", transcript=transcript.hex())
    app = receive_logged(sock, events)
    expect(app, header("app", "Alice", sid, group.name, 2, na, nb))
    text = decode_message(decrypt(keys.app_ab, app))
    events.emit("app_received", "Alice의 응용 메시지를 방향별 키로 인증·복호화했습니다.", text=text)
    reply = encrypt(keys.app_ba, BOB_MESSAGE.encode("utf-8"), header("app", "Bob", sid, group.name, 2, na, nb))
    send_logged(sock, reply, events)
    events.emit("complete", "Bob의 암호화 메시지 수신과 응답이 정상 완료되었습니다.")
