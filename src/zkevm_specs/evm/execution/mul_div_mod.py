from ..instruction import Instruction, Transition
from ..opcode import Opcode
from ...util import FQ


def mul_add(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)

    is_mul, is_div = instruction.pair_select(opcode, Opcode.MUL, Opcode.DIV)
    is_mod, _ = instruction.pair_select(opcode, Opcode.MOD, Opcode.DIV)
    if is_mul:
        a = instruction.stack_pop()
        b = instruction.stack_pop()
        c = instruction.int_to_rlc(0, 32)
        d = instruction.stack_push()
    elif is_div:
        d = instruction.stack_pop()
        b = instruction.stack_pop()
        a = instruction.stack_push()
        a_lo, a_hi = instruction.word_to_lo_hi(a)
        b_lo, b_hi = instruction.word_to_lo_hi(b)
        d_lo, d_hi = instruction.word_to_lo_hi(d)
        ai = a_lo.n + a_hi.n * (1 << 128)
        bi = b_lo.n + b_hi.n * (1 << 128)
        di = d_lo.n + d_hi.n * (1 << 128)
        c = instruction.int_to_rlc(di - ai * bi, 32)
        c_lo, c_hi = instruction.word_to_lo_hi(c)
    elif is_mod:
        d = instruction.stack_pop()
        b = instruction.stack_pop()
        c = instruction.stack_push()
        b_lo, b_hi = instruction.word_to_lo_hi(b)
        d_lo, d_hi = instruction.word_to_lo_hi(d)
        bi = b_lo.n + b_hi.n * (1 << 128)
        di = d_lo.n + d_hi.n * (1 << 128)
        if bi == 0:
            a = instruction.int_to_rlc(0, 32)
            c = d  # when b == 0 the gadget will construct c for check instead of 0
        else:
            a = di // bi
            a = instruction.int_to_rlc(a, 32)
        c_lo, c_hi = instruction.word_to_lo_hi(c)
    a64s = instruction.word_to_64s(a)
    b64s = instruction.word_to_64s(b)
    c64s = instruction.word_to_64s(c)
    d64s = instruction.word_to_64s(d)

    t = [FQ(0)] * 4
    for total_idx in range(4):
        for a_id in range(0, total_idx + 1):
            a_idx, b_idx = a_id, total_idx - a_id
            t[total_idx] += a64s[a_idx] * b64s[b_idx]

    v = [0] * 2
    v[0] = (
        t[0] + t[1] * (2**64) + c64s[0] + c64s[1] * (2**64) - d64s[0] - d64s[1] * (2**64)
    ).n // (2**128)
    v[1] = (
        v[0]
        + t[2]
        + t[3] * (2**64)
        + c64s[2]
        + c64s[3] * (2**64)
        - d64s[2]
        - d64s[3] * (2**64)
    ).n // (2**128)

    v0 = instruction.int_to_rlc(v[0], 9)
    v1 = instruction.int_to_rlc(v[1], 9)

    instruction.mul_add_words(a, b, c, d, v0, v1, is_mul)

    if (is_div or is_mod) and bi != 0:
        c_lt_b_lo, c_eq_b_lo = instruction.compare(c_lo, b_lo, 16)
        c_lt_b_hi, c_eq_b_hi = instruction.compare(c_hi, b_hi, 16)
        c_lt_b = instruction.select(c_lt_b_hi, 1, instruction.select(c_eq_b_hi * c_lt_b_lo, 1, 0))
        instruction.constrain_equal(c_lt_b, FQ(1))

    instruction.step_state_transition_in_same_context(
        opcode,
        rw_counter=Transition.delta(3),
        program_counter=Transition.delta(1),
        stack_pointer=Transition.delta(1),
    )
