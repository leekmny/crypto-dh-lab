"""Alice 클라이언트: 자신의 비밀 지수만 사용한다."""
import socket

from protocol.cli import parser, execute
from protocol.crypto import load_key
from protocol.dh import get_group
from protocol.errors import ProtocolError
from protocol.session import prepare_alice, run_alice, ALICE_MESSAGE


def main():
    argp = parser("Alice")
    argp.add_argument("--message", default=ALICE_MESSAGE, help="Bob에게 보낼 메시지")
    args = argp.parse_args()
    def action(events):
        key = load_key(args.key)
        group = get_group(args.mode)
        prepared = prepare_alice(group, key, events, args.message)
        try:
            sock = socket.create_connection(("127.0.0.1", args.port), timeout=args.timeout)
        except (TimeoutError, OSError):
            raise ProtocolError("CONNECT", "Bob에게 TCP 연결을 만들지 못했습니다. 서버 포트와 기동 상태를 확인하세요.") from None
        with sock:
            sock.settimeout(args.timeout)
            events.emit("connected", "127.0.0.1의 Bob 서버에 실제 TCP로 연결했습니다.", peer_port=args.port)
            run_alice(sock, group, key, events, prepared, args.message)
    return execute("Alice", args, action)


if __name__ == "__main__":
    raise SystemExit(main())
