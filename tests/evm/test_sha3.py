import pytest

from zkevm_specs.evm import (
    Block,
    Bytecode,
    CopyCircuit,
    CopyDataTypeTag,
    ExecutionState,
    KeccakCircuit,
    RWDictionary,
    Tables,
)
from zkevm_specs.copy_circuit import verify_copy_table
from zkevm_specs.util import rand_bytes, rand_fq, FQ, RLC, U64


CALL_ID = 1
TESTING_DATA = ((0x20, 0x40),)


@pytest.mark.parametrize("offset, length", TESTING_DATA)
def test_sha3(offset: int, length: int):
    randomness = rand_fq()

    offset_rlc = RLC(offset, randomness)
    length_rlc = RLC(length, randomness)

    # divide rand memory into chunks of 32 which we will push and mstore.
    memory_snapshot = rand_bytes(offset + length)
    memory_chunks = list()
    for i in range(0, len(memory_snapshot), 32):
        memory_chunks.append(memory_snapshot[i : i + 32])
    src_data = dict(
        [
            (i, memory_snapshot[i] if i < len(memory_snapshot) else 0)
            for i in range(offset, offset + length)
        ]
    )

    bytecode = Bytecode()
    for i, chunk in enumerate(memory_chunks):
        bytecode.push(32 * i, n_bytes=32).push(chunk, n_bytes=32).mstore()
    bytecode.push(offset_rlc, n_bytes=32).push(length_rlc, n_bytes=32).sha3().stop()
    bytecode_hash = RLC(bytecode.hash(), randomness)

    rw_dictionary = (
        RWDictionary(1)
        .stack_write(CALL_ID, 1023, length_rlc)
        .stack_write(CALL_ID, 1022, offset_rlc)
        .stack_read(CALL_ID, 1022, offset_rlc)
        .stack_read(CALL_ID, 1023, length_rlc)
    )

    copy_circuit = CopyCircuit().copy(
        randomness,
        rw_dictionary,
        CALL_ID,
        CopyDataTypeTag.Memory,
        FQ.zero(),
        CopyDataTypeTag.RlcAcc,
        offset,
        offset + length,
        FQ.zero(),
        length,
        src_data,
    )

    keccak_circuit = KeccakCircuit().add(memory_snapshot[offset : offset + length], randomness)

    tables = Tables(
        block_table=set(Block().table_assignments(randomness)),
        tx_table=set(),
        bytecode_table=set(bytecode.table_assignments(randomness)),
        rw_table=set(rw_dictionary.rws),
        copy_circuit=copy_circuit.rows,
        keccak_table=keccak_circuit.rows,
    )

    verify_copy_table(copy_circuit, tables, randomness)
