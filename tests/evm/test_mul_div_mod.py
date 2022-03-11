import pytest

from typing import Optional
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
from zkevm_specs.util import rand_fp, rand_word, RLC


TESTING_DATA = (
    (Opcode.MUL, 0x030201, 0x060504, None),
    (
        Opcode.MUL,
        3402823669209384634633746074317682114560,
        34028236692093846346337460743176821145600,
        None,
    ),
    (
        Opcode.MUL,
        3402823669209384634633746074317682114560,
        34028236692093846346337460743176821145500,
        None,
    ),
    (Opcode.DIV, 0xFFFFFF, 0xABC, None),
    (Opcode.DIV, 0xABC, 0xFFFFFF, None),
    (Opcode.DIV, 0xFFFFFF, 0xFFFFFFF, None),
    (Opcode.DIV, 0xABC, 0, None),
    (Opcode.DIV, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF, 0, None),
    (Opcode.MOD, 0xFFFFFF, 0xABC, None),
    (Opcode.MOD, 0xABC, 0xFFFFFF, None),
    (Opcode.MOD, 0xFFFFFF, 0xFFFFFFF, None),
    (Opcode.MOD, 0xABC, 0, None),
    (Opcode.MOD, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF, 0, None),
    (Opcode.MUL, rand_word(), rand_word(), None),
    (Opcode.DIV, rand_word(), rand_word(), None),
    (Opcode.MOD, rand_word(), rand_word(), None),
)


@pytest.mark.parametrize("opcode, a, b, c", TESTING_DATA)
def test_mul_div_mod(opcode: Opcode, a: int, b: int, c: Optional[int]):
    randomness = rand_fp()

    c = (
        RLC(c, randomness)
        if c is not None
        else RLC(
            a * b % 2**256
            if opcode == Opcode.MUL
            else 0
            if b == 0
            else a // b
            if opcode == Opcode.DIV
            else a % b,
            randomness,
        )
    )
    a = RLC(a, randomness)
    b = RLC(b, randomness)

    bytecode = (
        Bytecode().mul(a, b)
        if opcode == Opcode.MUL
        else Bytecode().div(a, b)
        if opcode == Opcode.DIV
        else Bytecode().mod(a, b)
    )
    bytecode_hash = RLC(bytecode.hash(), randomness)

    tables = Tables(
        block_table=set(Block().table_assignments(randomness)),
        tx_table=set(),
        bytecode_table=set(bytecode.table_assignments(randomness)),
        rw_table=set(
            [
                (9, RW.Read, RWTableTag.Stack, 1, 1022, 0, a, 0, 0, 0),
                (10, RW.Read, RWTableTag.Stack, 1, 1023, 0, b, 0, 0, 0),
                (11, RW.Write, RWTableTag.Stack, 1, 1023, 0, c, 0, 0, 0),
            ]
        ),
    )

    verify_steps(
        randomness=randomness,
        tables=tables,
        steps=[
            StepState(
                execution_state=ExecutionState.MUL,
                rw_counter=9,
                call_id=1,
                is_root=True,
                is_create=False,
                code_source=bytecode_hash,
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
                code_source=bytecode_hash,
                program_counter=67,
                stack_pointer=1023,
                gas_left=0,
            ),
        ],
    )
