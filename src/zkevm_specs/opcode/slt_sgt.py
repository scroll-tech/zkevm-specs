from typing import Sequence
from src.zkevm_specs.encoding import U8, is_circuit_code


def generate_polynomial(cell_1, cell_2, cell_3, c1, c2, c3):
    c1, c2, c3 = c1 ^ 1, c2 ^ 1, c3 ^ 3
    if c1 == 0:
        poly1 = cell_1
    else:
        poly1 = 1 - cell_1
    if c2 == 0:
        poly2 = cell_2
    else:
        poly2 = 1 - cell_2
    if c3 == 0:
        poly3 = cell_3
    else:
        poly3 = 1 - cell_3

    return poly1 * poly2 * poly3


def slt_circuit(a8s: Sequence[U8],
                b8s: Sequence[U8],
                result: Sequence[U8],
                c8s: Sequence[U8],
                carry,
                sumc,
                sign_a,
                sign_b):
    assert len(a8s) == len(b8s) == len(c8s) == 32
    assert result[0] in [0, 1]
    for i in range(1, 32):
        assert result[i] == 0
    assert carry * (1 - carry) == 0

    # slt_constrants
    exponent = 1
    lhs = rhs = 0
    for idx in range(16):
        lhs += (a8s[idx] + c8s[idx]) * exponent
        rhs += b8s[idx] * exponent
        exponent *= 256
    rhs += carry * exponent
    assert lhs == rhs

    exponent = 1
    lhs = carry
    rhs = 0
    for idx in range(16, 32):
        lhs += (a8s[idx] + c8s[idx]) * exponent
        rhs += b8s[idx] * exponent
        exponent *= 256
    rhs += exponent * (sumc != 0) * (generate_polynomial(sign_a, sign_b, result[0], 1, 0, 1) +
                                     generate_polynomial(sign_a, sign_b, result[0], 0, 0, 0) +
                                     generate_polynomial(sign_a, sign_b, result[0], 1, 1, 0)
                                     )
    assert lhs == rhs
    print("PASSED")


@is_circuit_code
def check_slt(a8s: Sequence[U8],
              b8s: Sequence[U8],
              result: Sequence[U8],
              c8s: Sequence[U8],
              carry,
              sumc,
              sign_a,
              sign_b,
              is_sgt: bool):
    assert not is_sgt
    slt_circuit(a8s, b8s, result, c8s, carry, sumc, sign_a, sign_b)


@is_circuit_code
def check_sgt(b8s: Sequence[U8],
              a8s: Sequence[U8],
              result: Sequence[U8],
              c8s: Sequence[U8],
              carry,
              sumc,
              sign_b,
              sign_a,
              is_sgt: bool):
    assert is_sgt
    slt_circuit(a8s, b8s, result, c8s, carry, sumc, sign_a, sign_b)
