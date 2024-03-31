from ...util import Word
from ..instruction import Instruction, Transition
from ..table import CallContextFieldTag
from ..opcode import Opcode


def calldatasize(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)
    instruction.constrain_equal(opcode, Opcode.CALLDATASIZE)

    # check [rw_table, call_context] table for call data length and compare
    # against stack top after push.
    instruction.constrain_equal_word(
        Word.from_lo(instruction.call_context_lookup(CallContextFieldTag.CallDataLength)),
        instruction.stack_push(),
    )

    instruction.step_state_transition_in_same_context(
        opcode,
        rw_counter=Transition.delta(2),
        program_counter=Transition.delta(1),
        stack_pointer=Transition.delta(-1),
    )
