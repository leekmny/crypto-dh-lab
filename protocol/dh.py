"""RFC 3526 §3 그룹 14와 의도적으로 작은 수학 예제."""
from dataclasses import dataclass
import secrets

from .errors import ProtocolError

# 공식 원문: https://www.rfc-editor.org/rfc/rfc3526.html#section-3
MODP14_HEX = """
FFFFFFFF FFFFFFFF C90FDAA2 2168C234 C4C6628B 80DC1CD1
29024E08 8A67CC74 020BBEA6 3B139B22 514A0879 8E3404DD
EF9519B3 CD3A431B 302B0A6D F25F1437 4FE1356D 6D51C245
E485B576 625E7EC6 F44C42E9 A637ED6B 0BFF5CB6 F406B7ED
EE386BFB 5A899FA5 AE9F2411 7C4B1FE6 49286651 ECE45B3D
C2007CB8 A163BF05 98DA4836 1C55D39A 69163FA8 FD24CF5F
83655D23 DCA3AD96 1C62F356 208552BB 9ED52907 7096966D
670C354E 4ABC9804 F1746C08 CA18217C 32905E46 2E36CE3B
E39E772C 180E8603 9B2783A2 EC07A28F B5C55DF0 6F4C52C9
DE2BCBF6 95581718 3995497C EA956AE5 15D22618 98FA0510
15728E5A 8AACAA68 FFFFFFFF FFFFFFFF
"""


@dataclass(frozen=True)
class Group:
    name: str
    p: int
    g: int
    q: int | None = None

    @property
    def size(self) -> int:
        return (self.p.bit_length() + 7) // 8

    def encode(self, value: int) -> bytes:
        if not isinstance(value, int) or not 0 <= value < self.p:
            raise ProtocolError("PUBLIC_VALUE", "DH 정수가 허용 범위를 벗어났습니다.")
        return value.to_bytes(self.size, "big")

    def decode_public(self, data: bytes) -> int:
        if len(data) != self.size:
            raise ProtocolError("PUBLIC_LENGTH", "DH 공개값의 고정 길이 인코딩이 잘못되었습니다.")
        value = int.from_bytes(data, "big")
        self.validate_public(value)
        return value

    def validate_public(self, value: int) -> None:
        if type(value) is not int or not 2 <= value <= self.p - 2:
            raise ProtocolError("PUBLIC_VALUE", "DH 공개값은 2 이상 p−2 이하여야 합니다.")
        if self.q is not None and pow(value, self.q, self.p) != 1:
            raise ProtocolError("PUBLIC_SUBGROUP", "DH 공개값이 q 차수 부분군에 속하지 않습니다.")

    def private(self, role: str, *, fixed: bool = True) -> int:
        if self.name == "toy23" and fixed:
            return 6 if role == "Alice" else 15
        upper = self.q if self.q is not None else self.p - 1
        while True:
            value = secrets.randbelow(upper - 2) + 2
            if 2 <= pow(self.g, value, self.p) <= self.p - 2:
                return value

    def public(self, private: int) -> int:
        upper = self.q if self.q is not None else self.p - 1
        if type(private) is not int or not 2 <= private < upper:
            raise ProtocolError("PRIVATE_VALUE", "DH 비밀 지수가 허용 범위를 벗어났습니다.")
        value = pow(self.g, private, self.p)
        self.validate_public(value)
        return value

    def shared(self, peer: int, private: int) -> int:
        self.validate_public(peer)
        # 비밀 지수 검증도 계산 경로에서 강제한다.
        self.public(private)
        return pow(peer, private, self.p)


P14 = int("".join(MODP14_HEX.split()), 16)
GROUP14 = Group("modp14", P14, 2, (P14 - 1) // 2)
TOY = Group("toy23", 23, 5)


def get_group(mode: str) -> Group:
    if mode == "small":
        return TOY
    if mode == "group14":
        return GROUP14
    raise ProtocolError("GROUP", "지원하지 않는 DH 계산 모드입니다.")
