from ...util import (
    FQ,
    MAX_U256,
    RLC,
    get_int_abs,
    get_int_neg,
    int_is_neg,
)
from ..instruction import Instruction, Transition


def sar(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)

    shift = instruction.stack_pop()
    a = instruction.stack_pop()
    b = instruction.stack_push()

    (
        divisor,
        remainder,
        shf0,
    ) = gen_witness(shift, a, b)
    check_witness(
        instruction,
        shift,
        a,
        b,
        divisor,
        remainder,
        shf0,
    )

    instruction.step_state_transition_in_same_context(
        opcode,
        rw_counter=Transition.delta(3),
        program_counter=Transition.delta(1),
        stack_pointer=Transition.delta(1),
    )


def check_witness(
    instruction: Instruction,
    shift: RLC,
    a: RLC,
    b: RLC,
    divisor: RLC,
    remainder: RLC,
    shf0: FQ,
):
    a_abs, a_is_neg = instruction.abs_word(a)
    b_abs, b_is_neg = instruction.abs_word(b)
    remainder_abs, remainder_is_neg = instruction.abs_word(remainder)

    divisor_is_zero = instruction.word_is_zero(divisor)
    remainder_is_zero = instruction.word_is_zero(remainder)

    # Function `mul_add_words` constrains `|b| * divisor + |remainder| = |a|`, divisor is considered
    # as an unsigned word.
    overflow = instruction.mul_add_words(b_abs, divisor, remainder_abs, a_abs)
    # Constrain overflow == 0.
    instruction.constrain_zero(overflow)

    # Constrain sign(a) == sign(b).
    instruction.constrain_equal(a_is_neg, b_is_neg)

    # When divisor == 0 (cb.condition).
    if divisor_is_zero.n:
        # If b < 0, then `b == 2**256 - 1`. Otherwise b == 0.
        instruction.constrain_equal(b.expr(), instruction.select(b_is_neg, RLC(MAX_U256), RLC(0)))

    # When divisor != 0.
    if 1 - divisor_is_zero.n:
        # Constrain shift == shift.cells[0].
        instruction.constrain_zero(shift.expr() - shift.le_bytes[0])

        # Constrain `divisor == 2**shf0`.
        # If shf0 < 128, then `divisor_lo == 2**shf0`.
        # If shf0 >= 128, then `divisor_hi == 2**(128 - shf0)`.
        divisor_lo = instruction.bytes_to_fq(divisor.le_bytes[:16])
        divisor_hi = instruction.bytes_to_fq(divisor.le_bytes[16:])
        instruction.pow2_lookup(shf0, divisor_lo, divisor_hi)

        # Constrain divisor <= a_abs.
        divisor_lt_a_abs, divisor_eq_a_abs = instruction.compare_word(divisor, a_abs)
        instruction.constrain_zero(1 - divisor_lt_a_abs - divisor_eq_a_abs)

        # Constrain abs(remainder) < divisor.
        remainder_abs_lt_divisor, _ = instruction.compare_word(remainder_abs, divisor)
        instruction.constrain_zero((1 - remainder_abs_lt_divisor))

    # When remainder != 0.
    if 1 - remainder_is_zero:
        # Constrain sign(a) == sign(remainder)
        instruction.constrain_equal(remainder_is_neg, a_is_neg)


def gen_witness(shift: RLC, a: RLC, b: RLC):
    a_is_neg = int_is_neg(a.int_value)
    a_abs = get_int_abs(a.int_value)
    b_abs = get_int_abs(b.int_value)

    # Set divisor = 0 for following conditions.
    # 1. If shift >= 256 (shift right for 256-bit), cannot calculate divisor (2**shift) as u256.
    # 2. If a_abs < 2**shift (and a < 0), `a` (quotient), `b` (dividend) and divisor (2**shift)
    #    cannot be constrained by `MulAddWords`. e.g.
    #
    #    For SAR, a == -1 (2**256 - 1) and shift = 1, then b == -1.
    #    PUSH32 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
    #    PUSH1 1
    #    SAR
    #
    #    For SDIV, dividend == -1 and divisor = 2, then quotient == 0.
    #    PUSH32 2
    #    PUSH32 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
    #    SDIV
    #
    # For both conditions, set divisor = 0 and constrain `b` as:
    # When divisor == 0, if b < 0, then `b == 2**256 - 1`. Otherwise b == 0.
    shf0 = shift.le_bytes[0]
    divisor = 2**shf0 if shf0 == shift.int_value else 0
    divisor = 0 if a_abs < divisor else divisor

    remainder = get_int_neg(a_abs - b_abs * divisor) if a_is_neg else a_abs - b_abs * divisor

    print(f'a = {a}')
    print(f'b = {b}')
    print(f'a_abs = {a_abs}')
    print(f'b_abs = {b_abs}')
    print(f'divisor = {divisor}')
    print(f'remainder = {remainder}')

    return (RLC(divisor), RLC(remainder), FQ(shf0))
