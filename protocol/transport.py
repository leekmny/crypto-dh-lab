import socket
import struct
import time

from .errors import ProtocolError
from .messages import canonical, decode_json, MAX_FRAME


def recv_exact(sock: socket.socket, count: int) -> bytes:
    parts = bytearray()
    original = sock.gettimeout()
    deadline = time.monotonic() + (original if original is not None else 5)
    try:
        while len(parts) < count:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ProtocolError("TIMEOUT", "TCP 프레임 전체 수신 제한 시간을 초과했습니다.")
            sock.settimeout(remaining)
            part = sock.recv(count - len(parts))
            if not part:
                raise ProtocolError("DISCONNECT", "상대방이 TCP 연결을 종료했습니다.")
            parts.extend(part)
    except (socket.timeout, TimeoutError):
        raise ProtocolError("TIMEOUT", "TCP 수신 제한 시간을 초과했습니다.") from None
    except OSError:
        raise ProtocolError("NETWORK", "TCP 수신 중 연결 오류가 발생했습니다.") from None
    finally:
        sock.settimeout(original)
    return bytes(parts)


def receive(sock: socket.socket) -> dict:
    size = struct.unpack("!I", recv_exact(sock, 4))[0]
    if not 0 < size <= MAX_FRAME:
        raise ProtocolError("FRAME_SIZE", "TCP 프레임 크기가 허용 범위(1–16384바이트)를 벗어났습니다.")
    return decode_json(recv_exact(sock, size))


def send(sock: socket.socket, packet: dict) -> None:
    data = canonical(packet)
    if not 0 < len(data) <= MAX_FRAME:
        raise ProtocolError("FRAME_SIZE", "송신 프레임이 크기 제한을 초과했습니다.")
    try:
        sock.sendall(struct.pack("!I", len(data)) + data)
    except (socket.timeout, TimeoutError):
        raise ProtocolError("TIMEOUT", "TCP 송신 제한 시간을 초과했습니다.") from None
    except OSError:
        raise ProtocolError("NETWORK", "TCP 송신 중 연결이 끊어졌습니다.") from None
