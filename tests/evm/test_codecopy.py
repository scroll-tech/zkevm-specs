import pytest

from zkevm_specs.evm_circuit import (
    Bytecode,
    ExecutionState,
    Opcode,
    StepState,
    Tables,
    verify_steps,
    CopyCircuit,
    CopyDataTypeTag,
    RWDictionary,
)
from zkevm_specs.copy_circuit import verify_copy_table
from zkevm_specs.util import (
    GAS_COST_COPY,
    MEMORY_EXPANSION_LINEAR_COEFF,
    MEMORY_EXPANSION_QUAD_DENOMINATOR,
    Word,
    U64,
)
from common import rand_fq


CALL_ID = 1
TESTING_DATA = (
    # single step
    (0x00, 0x00, 54),
    # multi step
    (0x00, 0x40, 123),
    # out of bounds
    (0x10, 0x20, 200),
)


def to_word_size(addr: int) -> int:
    return (addr + 31) // 32


def memory_gas_cost(memory_word_size: int) -> int:
    quad_cost = memory_word_size * memory_word_size // MEMORY_EXPANSION_QUAD_DENOMINATOR
    linear_cost = memory_word_size * MEMORY_EXPANSION_LINEAR_COEFF
    return quad_cost + linear_cost


def memory_copier_gas_cost(
    curr_memory_word_size: int, next_memory_word_size: int, length: int
) -> int:
    curr_memory_cost = memory_gas_cost(curr_memory_word_size)
    next_memory_cost = memory_gas_cost(next_memory_word_size)
    return to_word_size(length) * GAS_COST_COPY + next_memory_cost - curr_memory_cost


@pytest.mark.parametrize("src_addr, dst_addr, length", TESTING_DATA)
def test_codecopy(src_addr: U64, dst_addr: U64, length: U64):
    randomness_keccak = rand_fq()

    length_word = Word(length)
    src_addr_word = Word(src_addr)
    dst_addr_word = Word(dst_addr)

    code = (
        Bytecode().push32(length_word).push32(src_addr_word).push32(dst_addr_word).codecopy().stop()
    )

    code_hash = Word(code.hash())
    next_memory_word_size = to_word_size(dst_addr + length)

    gas_cost_push32 = Opcode.PUSH32.constant_gas_cost()
    gas_cost_codecopy = Opcode.CODECOPY.constant_gas_cost() + memory_copier_gas_cost(
        0, next_memory_word_size, length
    )
    total_gas_cost = gas_cost_codecopy + (3 * gas_cost_push32)

    rw_dictionary = (
        RWDictionary(1)
        .stack_write(CALL_ID, 1023, length_word)
        .stack_write(CALL_ID, 1022, src_addr_word)
        .stack_write(CALL_ID, 1021, dst_addr_word)
        .stack_read(CALL_ID, 1021, dst_addr_word)
        .stack_read(CALL_ID, 1022, src_addr_word)
        .stack_read(CALL_ID, 1023, length_word)
    )
    # rw counter before memory writes
    rw_counter_interim = rw_dictionary.rw_counter

    steps = [
        StepState(
            execution_state=ExecutionState.PUSH,
            rw_counter=1,
            call_id=CALL_ID,
            is_root=True,
            code_hash=code_hash,
            program_counter=0,
            stack_pointer=1024,
            gas_left=total_gas_cost,
        ),
        StepState(
            execution_state=ExecutionState.PUSH,
            rw_counter=2,
            call_id=CALL_ID,
            is_root=True,
            code_hash=code_hash,
            program_counter=33,
            stack_pointer=1023,
            gas_left=total_gas_cost - gas_cost_push32,
        ),
        StepState(
            execution_state=ExecutionState.PUSH,
            rw_counter=3,
            call_id=CALL_ID,
            is_root=True,
            code_hash=code_hash,
            program_counter=66,
            stack_pointer=1022,
            gas_left=total_gas_cost - 2 * gas_cost_push32,
        ),
        StepState(
            execution_state=ExecutionState.CODECOPY,
            rw_counter=4,
            call_id=CALL_ID,
            is_root=True,
            code_hash=code_hash,
            program_counter=99,
            stack_pointer=1021,
            gas_left=gas_cost_codecopy,
        ),
    ]

    src_data = dict([(i, (code.code[i], code.is_code[i])) for i in range(len(code.code))])
    copy_circuit = CopyCircuit().copy(
        randomness_keccak,
        rw_dictionary,
        code_hash,
        CopyDataTypeTag.Bytecode,
        CALL_ID,
        CopyDataTypeTag.Memory,
        src_addr,
        len(code.code),
        dst_addr,
        length,
        src_data,
    )

    # rw counter post memory writes
    rw_counter_final = rw_dictionary.rw_counter
    assert rw_counter_final - rw_counter_interim == length

    steps.append(
        StepState(
            execution_state=ExecutionState.STOP,
            rw_counter=rw_dictionary.rw_counter,
            call_id=CALL_ID,
            is_root=True,
            code_hash=code_hash,
            program_counter=100,
            stack_pointer=1024,
            memory_word_size=next_memory_word_size,
            gas_left=0,
        )
    )

    tables = Tables(
        block_table=set(),
        tx_table=set(),
        bytecode_table=set(code.table_assignments()),
        rw_table=set(rw_dictionary.rws),
        copy_circuit=copy_circuit.rows,
    )

    verify_copy_table(copy_circuit, tables, randomness_keccak)

    verify_steps(
        tables=tables,
        steps=steps,
    )
