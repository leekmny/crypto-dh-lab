"""실제 TCP 프레임을 관찰·변조하는 로컬 실험용 중계 프로세스."""
import argparse
import copy
from pathlib import Path
import secrets
import socket

from protocol.cli import parser, execute
from protocol.crypto import decrypt, encrypt, load_key
from protocol.errors import ProtocolError
from protocol.messages import b64, unb64, decode_json
from protocol.transport import send, receive


def flip(value: str) -> str:
    raw = bytearray(unb64(value))
    if not raw:
        raise ProtocolError("ATTACK", "변조할 바이트가 없습니다.")
    raw[0] ^= 1
    return b64(raw)


def observe(packet, events, key=None):
    events.emit("observed", "중계 소켓에서 실제 네트워크 패킷을 관찰했습니다.", packet=packet)
    if packet.get("header", {}).get("type") != "dh":
        return
    try:
        plaintext = decrypt(key if key is not None else secrets.token_bytes(32), packet)
        events.emit("eve_decrypted", "교육용으로 제공한 공유키로 공개값만 복호화했습니다. 개인 지수·공유 비밀은 얻지 못했습니다.",
                    public_value=int.from_bytes(plaintext, "big"), psk_provided=key is not None)
    except ProtocolError as error:
        events.emit("eve_blocked", "K_AB 없이 시도한 GCM 복호화가 실제 인증 검증에서 실패했습니다.", code=error.code, psk_provided=False)


def main():
    argp = parser("Eve")
    argp.set_defaults(port=8767)
    argp.add_argument("--target-port", type=int, default=8766)
    argp.add_argument("--attack", choices=("none", "cipher", "tag", "replay", "confirm", "invalid_public", "malformed", "drop", "timeout"), default="none")
    argp.add_argument("--replay-file", type=Path)
    argp.add_argument("--reveal-key", type=Path, help="교육용 공개값 복호화 비교에만 제공")
    argp.add_argument("--attack-key", type=Path, help="잘못된 공개값을 정상 GCM으로 만드는 검증 전용 키")
    args = argp.parse_args()
    def action(events):
        key = load_key(args.reveal_key) if args.reveal_key else None
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", args.port))
            listener.listen(1)
            listener.settimeout(args.accept_timeout)
            events.emit("listening", "Eve 로컬 TCP 중계기가 연결을 기다립니다.", port=listener.getsockname()[1])
            try:
                alice, _ = listener.accept()
            except TimeoutError:
                raise ProtocolError("TIMEOUT", "중계기 접속 대기 시간이 초과되었습니다.") from None
            with alice, socket.create_connection(("127.0.0.1", args.target_port), timeout=args.timeout) as bob:
                alice.settimeout(args.timeout)
                bob.settimeout(args.timeout)
                # 현재 프로토콜은 여섯 메시지를 번갈아 교환한다. 응답 대기를 제한한다.
                for index in range(6):
                    source, target = (alice, bob) if index % 2 == 0 else (bob, alice)
                    packet = receive(source)
                    observe(packet, events, key)
                    changed = copy.deepcopy(packet)
                    if index == 0:
                        if args.attack in ("cipher", "tag"):
                            field = "ciphertext" if args.attack == "cipher" else "tag"
                            changed[field] = flip(changed[field])
                        elif args.attack == "replay":
                            if not args.replay_file:
                                raise ProtocolError("ATTACK", "이전 실제 패킷 파일이 필요합니다.")
                            changed = decode_json(args.replay_file.read_bytes())
                        elif args.attack == "invalid_public":
                            if not args.attack_key:
                                raise ProtocolError("ATTACK", "공개값 의미 검증 실험에는 테스트 키가 필요합니다.")
                            size = 1 if packet["header"]["group"] == "toy23" else 256
                            changed = encrypt(load_key(args.attack_key), (1).to_bytes(size, "big"), packet["header"])
                        elif args.attack == "malformed":
                            changed = {"header": {"type": "지원하지 않는 형식"}}
                        elif args.attack == "drop":
                            events.emit("modified", "첫 패킷을 전달하지 않고 실제 연결을 종료했습니다.", attack=args.attack)
                            return
                        elif args.attack == "timeout":
                            events.emit("modified", "첫 패킷 전달을 중단하여 실제 소켓 제한 시간을 유발합니다.", attack=args.attack)
                            try:
                                bob.recv(1)
                            except TimeoutError:
                                pass
                            return
                    if index == 2 and args.attack == "confirm":
                        changed["mac"] = flip(changed["mac"])
                    if changed != packet:
                        events.emit("modified", "실제 전송할 패킷 바이트를 변경했습니다.", attack=args.attack, packet=changed)
                    send(target, changed)
                events.emit("complete", "실제 패킷 여섯 개의 양방향 중계를 완료했습니다.")
    return execute("Eve", args, action)


if __name__ == "__main__":
    raise SystemExit(main())
