from ...util import N_BYTES_PROGRAM_COUNTER
from ..instruction import Instruction, Transition
from ..opcode import Opcode


def push(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)
    num_pushed = opcode - Opcode.PUSH1 + 1
    code_length = instruction.bytecode_length(instruction.curr.code_hash)
    code_length_left = code_length - instruction.curr.program_counter - 1
    is_out_of_bound, _ = instruction.compare(code_length_left, num_pushed, N_BYTES_PROGRAM_COUNTER)
    num_padding = is_out_of_bound * (num_pushed - code_length_left)

    value = instruction.stack_push()
    value_le_bytes = value.to_le_bytes()
    is_pushed = instruction.continuous_selectors(num_pushed, 32)
    is_padding = instruction.continuous_selectors(num_padding, 32)

    for idx in range(32):
        index = instruction.curr.program_counter + num_pushed - idx
        if is_pushed[idx] * (1 - is_padding[idx]) == 1:
            instruction.constrain_equal(
                value_le_bytes[idx], instruction.opcode_lookup_at(index, False)
            )
        else:
            instruction.constrain_zero(value_le_bytes[idx])

    instruction.step_state_transition_in_same_context(
        opcode,
        rw_counter=Transition.delta(1),
        program_counter=Transition.delta(1 + num_pushed),
        stack_pointer=Transition.delta(-1),
    )
