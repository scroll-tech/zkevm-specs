from typing import Sequence, List

import random

from zkevm_specs.encoding import u256_to_u8s, U256, u8s_to_u64s
from zkevm_specs.opcode.div_mod import check_div_mod

def test_div_mod():
    dividend = random.randint(0, 2 ** 256)
    divisor = random.randint(1, dividend)
    quotient = dividend // divisor
    remainder = dividend - divisor * quotient
    
    # a->divisor b->quotient c->dividend d->remainder
    a8s = u256_to_u8s(U256(divisor))
    b8s = u256_to_u8s(U256(quotient))
    c8s = u256_to_u8s(U256(dividend))
    d8s = u256_to_u8s(U256(remainder))
    a64s = u8s_to_u64s(a8s)
    b64s = u8s_to_u64s(b8s)
    c64s = u8s_to_u64s(c8s)
    d64s = u8s_to_u64s(d8s)
    # t0 t1 t2 t3
    t = [U256(0)] * 4
    for total_idx in range(2):
        rhs_sum = U256(0)
        for a_id in range(0, total_idx + 1):
            a_idx, b_idx = a_id, total_idx - a_id
            tmp_a = a64s[a_idx] if len(a64s) >= a_idx + 1 else 0
            tmp_b = b64s[b_idx] if len(b64s) >= b_idx + 1 else 0
            t[total_idx] += tmp_a * tmp_b

    # v0, v1
    v = [U256(0)] * 2
    v[0] = U256((t[0] + t[1] * (2 ** 64) + d64s[0] + d64s[1] * (2 ** 64) - c64s[0] - c64s[1] * (2 ** 64)) // (2 ** 128))
    assert 0 <= v[0] <= (2 ** 66)

    v0 = u256_to_u8s(v[0])[:9]

    check_div(c8s, a8s, b8s, d8s, v0)
