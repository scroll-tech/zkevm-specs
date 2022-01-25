from ..instruction import Instruction, Transition
from ..table import CallContextFieldTag
from ..opcode import Opcode


def caller(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)

    # constrain op in [log0, log4] range
    instruction.range_lookup(opcode - Opcode.LOG0, 5)
    # pop `mstart`, `msize` from stack
    mstart = instruction.stack_pop()
    msize = instruction.stack_pop()
    topics = []
    for _ in range(opcode - Opcode.LOG0):
        topics.append(instruction.stack_pop())

    # check memory copy
    memory_data = []
    call_id = instruction.call_context_lookup(CallContextFieldTag.CallerId)
    for address in range(mstart, msize + 1):
        memory_data.append(instruction.memory_read(address, call_id))

    # TODO: check log data added in state

    # calculate dynamic gas cost
    _, memory_expansion_cost = instruction.memory_expansion_constant_length(mstart, msize)
    log_static_gas = 375
    dynamic_gas = log_static_gas * (opcode - Opcode.LOG0) + 8 * msize + memory_expansion_cost

    rw_counter_diff = 2 + opcode - Opcode.LOG0 + 1
    instruction.step_state_transition_in_same_context(
        opcode,
        rw_counter=Transition.delta(rw_counter_diff),
        program_counter=Transition.delta(1),
        stack_pointer=Transition.delta(2 + opcode - Opcode.LOG0),
        state_write_counter=Transition.delta(1),
        dynamic_gas_cost=dynamic_gas,
    )
