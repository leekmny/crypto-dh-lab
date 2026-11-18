"""Bob TCP 서버: 기본 한 연결을 처리하고 정상(0) 또는 안전한 거부(2)로 종료."""
import socket

from protocol.cli import parser, execute, ROOT
from protocol.crypto import load_key
from protocol.dh import get_group
from protocol.errors import ProtocolError
from protocol.replay import ReplayStore
from protocol.session import run_bob


def main():
    argp = parser("Bob")
    argp.add_argument("--replay-db", default=ROOT / ".local/replay.sqlite", help="영속 재전송 검사 DB")
    args = argp.parse_args()
    def action(events):
        key, group = load_key(args.key), get_group(args.mode)
        replay = ReplayStore(args.replay_db)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("127.0.0.1", args.port))
            server.listen(1)
            server.settimeout(args.accept_timeout)
            events.emit("listening", "Bob 서버가 127.0.0.1에서 TCP 연결을 기다립니다.", port=server.getsockname()[1])
            try:
                client, address = server.accept()
            except TimeoutError:
                raise ProtocolError("TIMEOUT", "Alice의 접속 대기 시간이 초과되었습니다.") from None
            with client:
                client.settimeout(args.timeout)
                events.emit("connected", "Alice의 실제 TCP 연결을 수락했습니다.", peer=address[0])
                run_bob(client, group, key, events, replay)
    return execute("Bob", args, action)


if __name__ == "__main__":
    raise SystemExit(main())
