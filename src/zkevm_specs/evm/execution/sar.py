from ...util import FQ, RLC, int_is_neg
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

    # Function `mul_add_words` constrains `|b| * divisor (2**shf0) + |remainder| = |a|`.
    overflow = instruction.mul_add_words(b_abs, divisor, remainder_abs, a_abs)
    # Constrain overflow == 0.
    instruction.constrain_zero(overflow)

    if divisor_is_zero:
        instruction.constrain_equal(b.expr(), instruction.select(a_is_neg, 2**256 - 1, 0))

    if 1 - divisor_is_zero:
        # Constrain shift == shift.cells[0] when divisor != 0.
        instruction.constrain_equal(shift.expr() - shift.le_bytes[0])

        divisor_lt_a_abs, divisor_eq_a_abs = instruction.compare_word(divisor, a_abs)
        instruction.constrain_zero(1 - divisor_lt_a_abs - divisor_eq_a_abs)

        # Constrain abs(remainder) < divisor when divisor != 0.
        remainder_abs_lt_divisor, _ = instruction.compare_word(remainder_abs, divisor)
        instruction.constrain_zero((1 - remainder_abs_lt_divisor_abs))

        # Constrain divisor_lo == 2^shf0 when shf0 < 128, and
        # divisor_hi == 2^(128 - shf0) otherwise.
        divisor_lo = instruction.bytes_to_fq(divisor.le_bytes[:16])
        divisor_hi = instruction.bytes_to_fq(divisor.le_bytes[16:])
        instruction.pow2_lookup(shf0, divisor_lo, divisor_hi)

    if 1 - remainder_is_zero:
        # Constrain sign(a) == sign(remainder) when remainder != 0.
        instruction.constrain_equal(dividend_is_neg, remainder_is_neg)

    # Constrain sign(a) == sign(b).
    instruction.constrain_equal(a_is_neg, b_is_neg)


def gen_witness(shift: RLC, a: RLC, b: RLC):
    a_is_neg = int_is_neg(a.int_value)
    a_abs = get_int_abs(a.int_value)
    b_abs = get_int_abs(b.int_value)

    shf0 = shift.le_bytes[0]
    shf_pow = 2**shf0 if shf0 == shift.int_value else 0
    divisor = RLC(0 if a_abs < shf_pow else shf_pow)
    remainder = RLC(get_int_neg(a_abs - b_abs * divisor) if a_is_neg else a_abs - b_abs * divisor)

    return (divisor, remainder, shf0)
