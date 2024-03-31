import pytest
from zkevm_specs.evm_circuit import (
    ExecutionState,
    StepState,
    Opcode,
    verify_steps,
    Tables,
    RWDictionary,
    Block,
    Bytecode,
)
from zkevm_specs.util import (
    Word,
    get_int_abs,
    get_int_neg,
    int_is_neg,
)
from common import generate_nasty_tests, rand_word

TESTING_DATA = [
    (Opcode.SDIV, 0xFFFFFF, 0xABC),
    (Opcode.SDIV, 0xABC, 0xFFFFFF),
    (Opcode.SDIV, 0xFFFFFF, 0xFFFFFFF),
    (Opcode.SDIV, 0xABC, 0),
    (Opcode.SDIV, (1 << 255) + (7 << 128), 0x1234),
    (Opcode.SDIV, (1 << 256) - 1, 0xABCDEF),
    (Opcode.SDIV, 0xABCDEF, (1 << 256) - 1),
    (Opcode.SDIV, 1 << 255, (1 << 256) - 1),
    (Opcode.SMOD, 0xFFFFFF, 0xABC),
    (Opcode.SMOD, 0xABC, 0xFFFFFF),
    (Opcode.SMOD, 0xFFFFFF, 0xFFFFFFF),
    (Opcode.SMOD, 0xABC, 0),
    (Opcode.SMOD, (1 << 255) + (7 << 128), 0x1234),
    (Opcode.SMOD, (1 << 256) - 1, 0xABCDEF),
    (Opcode.SMOD, 0xABCDEF, (1 << 256) - 1),
    (Opcode.SMOD, 1 << 255, (1 << 256) - 1),
    (Opcode.SDIV, rand_word(), rand_word()),
    (Opcode.SMOD, rand_word(), rand_word()),
]

generate_nasty_tests(TESTING_DATA, (Opcode.SDIV, Opcode.SMOD))


@pytest.mark.parametrize("opcode, a, b", TESTING_DATA)
def test_sdiv_smod(opcode: Opcode, a: int, b: int):
    a_abs = get_int_abs(a)
    b_abs = get_int_abs(b)
    a_is_neg = int_is_neg(a)
    b_is_neg = int_is_neg(b)
    if opcode == Opcode.SDIV:
        if b == 0:
            c = 0
        elif a_is_neg == b_is_neg:
            c = a_abs // b_abs
        else:
            c = get_int_neg(a_abs // b_abs)
    else:  # Opcode.SMOD
        if b == 0:
            c = 0
        elif a_is_neg:
            c = get_int_neg(a_abs % b_abs)
        else:
            c = a_abs % b_abs

    a = Word(a)
    b = Word(b)
    c = Word(c)

    bytecode = Bytecode().sdiv(a, b) if opcode == Opcode.SDIV else Bytecode().smod(a, b)
    bytecode_hash = Word(bytecode.hash())

    tables = Tables(
        block_table=set(Block().table_assignments()),
        tx_table=set(),
        bytecode_table=set(bytecode.table_assignments()),
        rw_table=set(
            RWDictionary(9)
            .stack_read(1, 1022, a)
            .stack_read(1, 1023, b)
            .stack_write(1, 1023, c)
            .rws
        ),
    )

    verify_steps(
        tables=tables,
        steps=[
            StepState(
                execution_state=ExecutionState.SDIV_SMOD,
                rw_counter=9,
                call_id=1,
                is_root=True,
                is_create=False,
                code_hash=bytecode_hash,
                program_counter=66,
                stack_pointer=1022,
                gas_left=5,
            ),
            StepState(
                execution_state=ExecutionState.STOP,
                rw_counter=12,
                call_id=1,
                is_root=True,
                is_create=False,
                code_hash=bytecode_hash,
                program_counter=67,
                stack_pointer=1023,
                gas_left=0,
            ),
        ],
    )
