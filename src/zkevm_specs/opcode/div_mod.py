from typing import Sequence

from ..encoding import U8, is_circuit_code, U256, u8s_to_u64s


def div_mod_common(
    dividend8s: Sequence[U8],
    divisor8s: Sequence[U8],
    quotient8s: Sequence[U8],
    remainder8s: Sequence[U8],
    v0: Sequence[U8],
):
    assert len(dividend8s) == len(divisor8s) == len(quotient8s) == len(remainder8s) == 32
    assert len(v0) == 9
    dividend64s = u8s_to_u64s(dividend8s)
    divisor64s = u8s_to_u64s(divisor8s)
    quotient64s = u8s_to_u64s(quotient8s)
    remainder64s = u8s_to_u64s(remainder8s)

    v0m = U256(0)
    for i, u8 in enumerate(v0):
        assert 0 <= u8 <= 255
        v0m += u8 * (2 ** (8 * i))

    t0 = divisor64s[0] * quotient64s[0]
    t1 = divisor64s[0] * quotient64s[1] + divisor64s[1] * quotient64s[0]
    t2 = divisor64s[0] * quotient64s[2] + divisor64s[1] * quotient64s[1] + divisor64s[2] * quotient64s[0]
    t3 = divisor64s[0] * quotient64s[3] + divisor64s[1] * quotient64s[2] + divisor64s[2] * quotient64s[1] + divisor64s[3] * quotient64s[0]
    assert v0m * (2 ** 128) == t0 + t1 * (2 ** 64) + remainder64s[0] + remainder64s[1] * (2 ** 64) - dividend64s[0] - dividend64s[1] * (2 ** 64)
    assert 0 == v0m + t2 + t3 * (2 ** 64) +remainder64s[2] + remainder64s[3] * (2 ** 64) - dividend64s[2] - dividend64s[3] * (2 ** 64)


@is_circuit_code
def check_div_mod(dividend8s, divisor8s, quotient8s, remainder8s, v0):
    div_mod_common(dividend8s, divisor8s, quotient8s, remainder8s, v0)
