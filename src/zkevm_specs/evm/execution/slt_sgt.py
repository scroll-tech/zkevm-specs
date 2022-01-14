from typing import Sequence, Tuple

from ..instruction import Instruction, Transition
from ..opcode import Opcode


def scmp(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)

    is_sgt, _ = instruction.pair_select(opcode, Opcode.SGT, Opcode.SLT)

    a = instruction.stack_pop()
    b = instruction.stack_pop()
    c = instruction.stack_push()

    # decode RLC to bytes for a and b
    # Note: `rlc_to_bytes` returns the bytes in big endian form. In order to
    # match the specs and circuit implementation, we transform them to
    # little endian form (which is the default form returned by `query_word`
    a8s = instruction.rlc_to_bytes(a, 32)
    b8s = instruction.rlc_to_bytes(b, 32)
    c8s = instruction.rlc_to_bytes(c, 32)
    a8s.reverse()
    b8s.reverse()
    c8s.reverse()

    cc = int.from_bytes(c8s, "little")
    a_hi = int.from_bytes(a8s[16:32], "little")
    a_lo = int.from_bytes(a8s[0:16], "little")
    b_hi = int.from_bytes(b8s[16:32], "little")
    b_lo = int.from_bytes(b8s[0:16], "little")

    a_lt_b = (a_hi < b_hi) or ((a_hi == b_hi) and (a_lo < b_lo))
    b_lt_a = (b_hi < a_hi) or ((b_hi == a_hi) and (b_lo < a_lo))

    # c should be boolean, i.e. binary result of (a < b)
    instruction.constrain_bool(cc)

    # a >=0 and b < 0
    if a8s[31] < 128 and b8s[31] >= 128:
        instruction.constrain_equal(
            instruction.select(is_sgt, 1, 0),
            cc,
        )
    # b >= 0 and a < 0
    elif b8s[31] < 128 and a8s[31] >= 128:
        instruction.constrain_equal(
            instruction.select(is_sgt, 0, 1),
            cc,
        )
    # (a < 0 and b < 0) or (a >= 0 and b >= 0)
    else:
        instruction.constrain_equal(
            instruction.select(is_sgt, b_lt_a, a_lt_b),
            cc,
        )

    instruction.constrain_same_context_state_transition(
        opcode,
        rw_counter=Transition.delta(3),
        program_counter=Transition.delta(1),
        stack_pointer=Transition.delta(1),
    )
