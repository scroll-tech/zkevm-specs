import secrets

from src.zkevm_specs.encoding import u256_to_u8s, U256, U8
from src.zkevm_specs.opcode.slt_sgt import check_slt, check_sgt


def generate(input_type):
    if input_type == 2:
        a = secrets.randbelow(2 ** 256)
        return a, a
    else:
        a = secrets.randbelow(2 ** 256)
        random_add = secrets.randbelow(2 ** 256)
        a8s = u256_to_u8s(U256(a))
        # a > 0
        if a8s[31] <= 127:
            b = a + random_add % (2 ** 255 - a)
        else:
            b = a + random_add % (2 ** 256 - a)
        if input_type == 1:
            return a, b
        else:
            return b, a


def subtract(a, b):
    a8s = u256_to_u8s(a)
    b8s = u256_to_u8s(b)
    if a8s[31] >= 128:
        sign_a = 1
    else:
        sign_a = 0
    if b8s[31] >= 128:
        sign_b = 1
    else:
        sign_b = 0
    sub_carry = 0
    carry = 0
    c8s = [U8(0)] * 32
    for idx in range(32):
        tmp = b8s[idx] - a8s[idx] - sub_carry
        if tmp < 0:
            c8s[idx] = tmp + (1 << 8)
            sub_carry = 1
        else:
            c8s[idx] = tmp
            sub_carry = 0

    for idx in range(16):
        tmp = a8s[idx] + c8s[idx] + carry
        carry = (tmp >= (1 << 8))

    if sign_a != sign_b:
        if sign_a == 1:
            result = 1
        else:
            result = 0
    else:
        if a < b:
            result = 1
        else:
            result = 0
    sumc = 0
    for idx in range(32):
        sumc += c8s[idx]
    return c8s, carry, result, sumc, sign_a, sign_b

def test_slt_sgt():
    print()
    print("slt: a < b, result = 1")
    # a < b
    a, b = generate(1)
    c8s, carry, result, sumc, sign_a, sign_b = subtract(a, b)
    a8s = u256_to_u8s(a)
    b8s = u256_to_u8s(b)
    check_slt(a8s, b8s, u256_to_u8s(U256(result)), c8s, carry, sumc, sign_a, sign_b, False)

    print("sgt: b > a, result = 1")
    # b > a
    check_sgt(b8s, a8s, u256_to_u8s(U256(result)), c8s, carry, sumc, sign_b, sign_a, True)

    print("slt: a = b, result = 0")
    # a = b
    a, b = generate(2)
    c8s, carry, result, sumc, sign_a, sign_b = subtract(a, b)
    a8s = u256_to_u8s(a)
    b8s = u256_to_u8s(b)
    check_slt(a8s, b8s, u256_to_u8s(U256(result)), c8s, carry, sumc, sign_a, sign_b, False)
    print("sgt: b = a, result = 0")
    check_sgt(b8s, a8s, u256_to_u8s(U256(result)), c8s, carry, sumc, sign_b, sign_a, True)

    print("slt: a > b, result = 0")
    # a > b
    a, b = generate(3)
    c8s, carry, result, sumc, sign_a, sign_b = subtract(a, b)
    a8s = u256_to_u8s(a)
    b8s = u256_to_u8s(b)
    check_slt(a8s, b8s, u256_to_u8s(U256(result)), c8s, carry, sumc, sign_a, sign_b, False)
    print("sgt: b < a, result = 0")
    check_sgt(b8s, a8s, u256_to_u8s(U256(result)), c8s, carry, sumc, sign_b, sign_a, True)
