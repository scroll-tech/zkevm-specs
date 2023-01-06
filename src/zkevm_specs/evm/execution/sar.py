from ...util import (
    FQ,
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
        dividend,
        divisor,
        remainder,
        quotient,
        shf0,
    ) = gen_witness(shift, a, b)
    check_witness(
        instruction,
        shift,
        a,
        b,
        dividend,
        divisor,
        remainder,
        quotient,
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
    dividend: RLC,
    divisor: RLC,
    remainder: RLC,
    quotient: RLC,
    shf0: FQ,
):
    dividend_abs, dividend_is_neg = instruction.abs_word(dividend)
    quotient_abs, quotient_is_neg = instruction.abs_word(quotient)
    remainder_abs, remainder_is_neg = instruction.abs_word(remainder)

    divisor_is_zero = instruction.word_is_zero(divisor)
    remainder_is_zero = instruction.word_is_zero(remainder)

    # Function `mul_add_words` constrains `|quotient| * divisor + |remainder| = |dividend|`, divisor
    # is considered as an unsigned word.
    overflow = instruction.mul_add_words(quotient_abs, divisor, remainder_abs, dividend_abs)
    # Constrain overflow == 0.
    instruction.constrain_zero(overflow)

    # Constrain sign(a) == sign(b).
    # instruction.constrain_equal(a_is_neg, b_is_neg)

    # When divisor == 0 (cb.condition).
    if divisor_is_zero.n:
        # If b < 0, then `b == 2**256 - 1`. Otherwise b == 0.
        # instruction.constrain_equal(b.expr(), instruction.select(b_is_neg, RLC(MAX_U256), RLC(0)))
        pass

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

        # Constrain abs(remainder) < divisor.
        remainder_abs_lt_divisor, _ = instruction.compare_word(remainder_abs, divisor)
        instruction.constrain_zero((1 - remainder_abs_lt_divisor))

    # When remainder != 0.
    # if 1 - remainder_is_zero:
    # Constrain sign(a) == sign(remainder)
    # instruction.constrain_equal(remainder_is_neg, a_is_neg)

    if dividend_is_neg.n * (1 - remainder_is_zero.n):
        val, q_overflow = instruction.add_words([b, RLC(1)])
        # instruction.constrain_equal(quotient.expr(), instruction.select(q_overflow.expr(), RLC(0), val).expr())


def gen_witness(shift: RLC, a: RLC, b: RLC):
    a_is_neg = int_is_neg(a.int_value)
    a_abs = get_int_abs(a.int_value)
    b_abs = get_int_abs(b.int_value)

    dividend = a

    # If shift >= 256, set divisor = 0. Since divisor (2**shift) is overflow for u256. Otherwise
    # divisor != 0 (even if `2**0`). So should constrain `b` when divisor == 0:
    # If b < 0, then `b == 2**256 - 1`. Otherwise b == 0.
    shf0 = shift.le_bytes[0]
    divisor = 2**shf0 if shf0 == shift.int_value else 0

    # TODO: comment
    quotient = b
    remainder = a_abs - b_abs * divisor
    if a_is_neg:
        if remainder:  # recomander != 0
            quotient = RLC(get_int_neg(b_abs - 1))
            remainder += divisor
        remainder = get_int_neg(remainder)

    # TODO
    print(f"a = {a}")
    print(f"b = {b}")
    print(f"a_abs = {a_abs}")
    print(f"b_abs = {b_abs}")
    print(f"divisor = {divisor}")
    print(f"remainder = {remainder}")

    return (dividend, RLC(divisor), RLC(remainder), quotient, FQ(shf0))
