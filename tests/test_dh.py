import pytest

from protocol.dh import TOY, GROUP14, get_group
from protocol.errors import ProtocolError


@pytest.mark.case("T01", "DH 수학 계산·표준 그룹·공유 비밀 일치")
def test_fixed_example():
    a, b = 6, 15
    public_a, public_b = TOY.public(a), TOY.public(b)
    shared_a, shared_b = TOY.shared(public_b, a), TOY.shared(public_a, b)
    assert (public_a, public_b, shared_a, shared_b) == (8, 19, 2, 2)
    assert shared_a == shared_b == pow(TOY.g, a * b, TOY.p)


@pytest.mark.case("T01", "DH 수학 계산·표준 그룹·공유 비밀 일치")
@pytest.mark.parametrize("group, repetitions", [(TOY, 30), (GROUP14, 4)])
def test_randomized_shared(group, repetitions):
    for _ in range(repetitions):
        a, b = group.private("Alice", fixed=False), group.private("Bob", fixed=False)
        assert group.shared(group.public(b), a) == group.shared(group.public(a), b)


@pytest.mark.case("T01", "DH 수학 계산·표준 그룹·공유 비밀 일치")
def test_official_group_fixture():
    import hashlib
    from pathlib import Path
    reference = (Path(__file__).parent / "fixtures/rfc3526-group14.txt").read_text(encoding="ascii")
    assert GROUP14.p == int("".join(reference.split()), 16)
    # 개발 시 RFC 공식 원문에서 추출한 전체 256바이트의 독립 SHA-256 대조값.
    assert hashlib.sha256(GROUP14.p.to_bytes(256, "big")).hexdigest() == "d66436f79bbd6b2e38c0ffbd079be904d2641415e2e67140e09448be9a60890e"
    assert GROUP14.p.bit_length() == 2048
    assert GROUP14.size == 256 and GROUP14.g == 2
    assert GROUP14.q == (GROUP14.p - 1) // 2
    assert pow(GROUP14.g, GROUP14.q, GROUP14.p) == 1
    assert get_group("group14") == GROUP14


@pytest.mark.case("T07", "DH 공개값 범위·부분군·인코딩 거부")
@pytest.mark.parametrize("value", [0, 1, -1, GROUP14.p - 1, GROUP14.p, GROUP14.p - 2, True])
def test_invalid_public(value):
    with pytest.raises(ProtocolError):
        GROUP14.validate_public(value)


@pytest.mark.case("T07", "DH 공개값 범위·부분군·인코딩 거부")
def test_fixed_width_and_bad_private():
    assert len(GROUP14.encode(2)) == 256 and GROUP14.encode(2)[-1] == 2
    with pytest.raises(ProtocolError, match="고정 길이"):
        GROUP14.decode_public(b"\x02")
    with pytest.raises(ProtocolError):
        TOY.public(0)
    with pytest.raises(ProtocolError):
        TOY.public(11)  # p−1 공개값 생성도 거부
