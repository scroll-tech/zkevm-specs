from ..instruction import Instruction, Transition
from zkevm_specs.util import FQ, RLC


def sha3(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)

    # byte offset in memory.
    offset = instruction.stack_pop()
    # byte size to read in memory.
    size = instruction.stack_pop()

    # convert RLC encoded stack elements to FQ.
    memory_offset, length = instruction.memory_offset_and_length(offset, size)

    # calculate memory expansion gas costs.
    next_memory_size, memory_expansion_gas_cost = instruction.memory_expansion_dynamic_length(
        memory_offset, length
    )
    gas_cost = instruction.memory_copier_gas_cost(length, memory_expansion_gas_cost)

    # TODO(rohit): lookup copy table (copy_rwc_inc and rlc_acc)
    copy_rwc_inc = FQ(0)
    # TODO(rohit): lookup keccak table (keccak-256 of rlc_acc)
    keccak256_rlc_acc = FQ(0)

    instruction.constrain_equal(
        keccak256_rlc_acc,
        instruction.stack_push(),
    )

    instruction.step_state_transition_in_same_context(
        opcode,
        rw_counter=Transition.delta(instruction.rw_counter_offset + copy_rwc_inc),
        program_counter=Transition.delta(1),
        stack_pointer=Transition.delta(2),
        memory_size=Transition.to(next_memory_size),
        dynamic_gas_cost=gas_cost,
    )
