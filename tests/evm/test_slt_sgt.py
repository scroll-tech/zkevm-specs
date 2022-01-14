import pytest

from zkevm_specs.evm import (
    ExecutionState,
    StepState,
    Opcode,
    verify_steps,
    Tables,
    RWTableTag,
    RW,
    Block,
    Bytecode,
)
from zkevm_specs.util import hex_to_word, rand_bytes, RLCStore

RAND_1 = rand_bytes()

RAND_2 = rand_bytes()

TESTING_DATA = (
    # a >= 0 and b >= 0
    (
        Opcode.SLT,
        hex_to_word("00"),
        hex_to_word("01"),
        hex_to_word("01"),
    ),
    (
        Opcode.SGT,
        hex_to_word("00"),
        hex_to_word("01"),
        hex_to_word("00"),
    ),
    (
        Opcode.SLT,
        hex_to_word("01"),
        hex_to_word("00"),
        hex_to_word("00"),
    ),
    (
        Opcode.SGT,
        hex_to_word("01"),
        hex_to_word("00"),
        hex_to_word("01"),
    ),

    # a < 0 and b >= 0
    (
        Opcode.SLT,
        hex_to_word("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        hex_to_word("00"),
        hex_to_word("01"),
    ),
    (
        Opcode.SGT,
        hex_to_word("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        hex_to_word("00"),
        hex_to_word("00"),
    ),
    (
        Opcode.SLT,
        hex_to_word("00"),
        hex_to_word("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        hex_to_word("00"),
    ),
    (
        Opcode.SGT,
        hex_to_word("00"),
        hex_to_word("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        hex_to_word("01"),
    ),

    # a < 0 and b < 0
    (
        Opcode.SLT,
        hex_to_word("fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe"),
        hex_to_word("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        hex_to_word("01"),
    ),
    (
        Opcode.SGT,
        hex_to_word("fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe"),
        hex_to_word("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        hex_to_word("00"),
    ),
    (
        Opcode.SLT,
        hex_to_word("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        hex_to_word("fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe"),
        hex_to_word("00"),
    ),
    (
        Opcode.SGT,
        hex_to_word("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"),
        hex_to_word("fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe"),
        hex_to_word("01"),
    ),

    # a_hi == b_hi and a_lo < b_lo and a < 0 and b < 0
    (
        Opcode.SLT,
        hex_to_word("ffffffffffffffffffffffffffffffff11111111111111111111111111111111"),
        hex_to_word("ffffffffffffffffffffffffffffffff22222222222222222222222222222222"),
        hex_to_word("01"),
    ),
    (
        Opcode.SGT,
        hex_to_word("ffffffffffffffffffffffffffffffff11111111111111111111111111111111"),
        hex_to_word("ffffffffffffffffffffffffffffffff22222222222222222222222222222222"),
        hex_to_word("00"),
    ),
    (
        Opcode.SLT,
        hex_to_word("ffffffffffffffffffffffffffffffff22222222222222222222222222222222"),
        hex_to_word("ffffffffffffffffffffffffffffffff11111111111111111111111111111111"),
        hex_to_word("00"),
    ),
    (
        Opcode.SGT,
        hex_to_word("ffffffffffffffffffffffffffffffff22222222222222222222222222222222"),
        hex_to_word("ffffffffffffffffffffffffffffffff11111111111111111111111111111111"),
        hex_to_word("01"),
    ),

    # a_hi == b_hi and a_lo < b_lo and a >= 0 and b >= 0
    (
        Opcode.SLT,
        hex_to_word("1111111111111111111111111111111144444444444444444444444444444443"),
        hex_to_word("1111111111111111111111111111111144444444444444444444444444444444"),
        hex_to_word("01"),
    ),
    (
        Opcode.SGT,
        hex_to_word("1111111111111111111111111111111144444444444444444444444444444443"),
        hex_to_word("1111111111111111111111111111111144444444444444444444444444444444"),
        hex_to_word("00"),
    ),
    (
        Opcode.SLT,
        hex_to_word("1111111111111111111111111111111144444444444444444444444444444444"),
        hex_to_word("1111111111111111111111111111111144444444444444444444444444444443"),
        hex_to_word("00"),
    ),
    (
        Opcode.SGT,
        hex_to_word("1111111111111111111111111111111144444444444444444444444444444444"),
        hex_to_word("1111111111111111111111111111111144444444444444444444444444444443"),
        hex_to_word("01"),
    ),

    # both equal
    (
        Opcode.SLT,
        RAND_1,
        RAND_1,
        hex_to_word("00"),
    ),
    (
        Opcode.SGT,
        RAND_2,
        RAND_2,
        hex_to_word("00"),
    ),

    # more cases where contiguous bytes are different
    (
        Opcode.SLT,
        hex_to_word("1234567812345678123456781234567812345678123456781234567812345678"),
        hex_to_word("2345678123456781234567812345678123456781234567812345678123456781"),
        hex_to_word("01"),
    ),
    (
        Opcode.SGT,
        hex_to_word("1234567812345678123456781234567812345678123456781234567812345678"),
        hex_to_word("2345678123456781234567812345678123456781234567812345678123456781"),
        hex_to_word("00"),
    ),
    (
        Opcode.SLT,
        hex_to_word("2345678123456781234567812345678123456781234567812345678123456781"),
        hex_to_word("1234567812345678123456781234567812345678123456781234567812345678"),
        hex_to_word("00"),
    ),
    (
        Opcode.SGT,
        hex_to_word("2345678123456781234567812345678123456781234567812345678123456781"),
        hex_to_word("1234567812345678123456781234567812345678123456781234567812345678"),
        hex_to_word("01"),
    ),
)

@pytest.mark.parametrize("opcode, a_bytes, b_bytes, res_bytes", TESTING_DATA)
def test_slt_sgt(opcode: Opcode, a_bytes: bytes, b_bytes: bytes, res_bytes: bytes):
    rlc_store = RLCStore()

    a = rlc_store.to_rlc(a_bytes)
    b = rlc_store.to_rlc(b_bytes)
    res = rlc_store.to_rlc(res_bytes)

    block = Block()
    bytecode = Bytecode(f"7f{b_bytes.hex()}7f{a_bytes.hex()}{opcode.hex()}00")
    bytecode_hash = rlc_store.to_rlc(bytecode.hash, 32)

    tables = Tables(
        block_table=set(block.table_assignments(rlc_store)),
        tx_table=set(),
        bytecode_table=set(bytecode.table_assignments(rlc_store)),
        rw_table=set(
            [
                (9, RW.Read, RWTableTag.Stack, 1, 1022, a, 0, 0),
                (10, RW.Read, RWTableTag.Stack, 1, 1023, b, 0, 0),
                (11, RW.Write, RWTableTag.Stack, 1, 1023, res, 0, 0),
            ]
        ),
    )

    verify_steps(
        rlc_store=rlc_store,
        tables=tables,
        steps=[
            StepState(
                execution_state=ExecutionState.SCMP,
                rw_counter=9,
                call_id=1,
                is_root=True,
                is_create=False,
                opcode_source=bytecode_hash,
                program_counter=66,
                stack_pointer=1022,
                gas_left=3,
            ),
            StepState(
                execution_state=ExecutionState.STOP,
                rw_counter=12,
                call_id=1,
                is_root=True,
                is_create=False,
                opcode_source=bytecode_hash,
                program_counter=67,
                stack_pointer=1023,
                gas_left=0,
            ),
        ],
    )
