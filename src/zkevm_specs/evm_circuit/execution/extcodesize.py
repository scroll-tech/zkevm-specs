from ...util import (
    EXTRA_GAS_COST_ACCOUNT_COLD_ACCESS,
    FQ,
    Word,
)
from ..instruction import Instruction, Transition
from ..opcode import Opcode
from ..table import AccountFieldTag, CallContextFieldTag


def extcodesize(instruction: Instruction):
    opcode = instruction.opcode_lookup(True)
    instruction.constrain_equal(opcode, Opcode.EXTCODESIZE)

    address = instruction.word_to_address(instruction.stack_pop())

    tx_id = instruction.call_context_lookup(CallContextFieldTag.TxId)
    is_warm = instruction.add_account_to_access_list(tx_id, address, instruction.reversion_info())

    code_hash = instruction.account_read_word(address, AccountFieldTag.CodeHash)
    # Check account existence with code_hash != 0
    exists = FQ(1) - instruction.is_zero_word(code_hash)

    if exists == 1:
        code_size = instruction.bytecode_length(code_hash)
    else:  # exists == 0
        code_size = FQ(0)

    instruction.constrain_equal_word(
        Word.from_lo(instruction.select(exists, code_size, FQ(0))),
        instruction.stack_push(),
    )

    instruction.step_state_transition_in_same_context(
        opcode,
        rw_counter=Transition.delta(7),
        program_counter=Transition.delta(1),
        stack_pointer=Transition.same(),
        dynamic_gas_cost=instruction.select(is_warm, FQ(0), FQ(EXTRA_GAS_COST_ACCOUNT_COLD_ACCESS)),
        reversible_write_counter=Transition.delta(1),
    )
