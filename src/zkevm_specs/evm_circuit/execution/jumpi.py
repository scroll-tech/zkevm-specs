from ..instruction import Instruction, Transition
from ..opcode import Opcode
from zkevm_specs.util import FQ


def jumpi(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)
    instruction.constrain_equal(opcode, Opcode.JUMPI)

    # Do not check 'dest' is within MaxCodeSize(24576) range in successful case
    # as byte code lookup can ensure it.
    dest_word = instruction.stack_pop()
    instruction.constrain_zero(dest_word.hi.expr())
    dest = dest_word.lo.expr()

    cond = instruction.stack_pop()

    # check `cond` is zero or not
    if instruction.is_zero_word(cond):
        pc_diff = FQ(1)
    else:
        pc_diff = dest - instruction.curr.program_counter
        # assert Opcode.JUMPDEST == instruction.opcode_lookup_at(dest_value, True)
        instruction.constrain_equal(Opcode.JUMPDEST, instruction.opcode_lookup_at(dest, True))

    instruction.step_state_transition_in_same_context(
        opcode,
        rw_counter=Transition.delta(2),
        program_counter=Transition.delta(pc_diff),
        stack_pointer=Transition.delta(2),
    )
