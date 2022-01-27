import pytest

from zkevm_specs.evm import (
    ExecutionState,
    StepState,
    verify_steps,
    Tables,
    RWTableTag,
    TxLogFieldTag,
    RW,
    Block,
    Bytecode,
)
from zkevm_specs.util import rand_address, rand_fp, RLC, U160


TESTING_DATA = (0x030201, rand_address())


@pytest.mark.parametrize("log", TESTING_DATA)
def test_log():
    randomness = rand_fp()
    mstart = 100
    msize = 20
    # for now only test first topic log scenario
    topic1 = 0x030201

    block = Block()

    bytecode = Bytecode().log1()
    bytecode_hash = RLC(bytecode.hash(), randomness)

    tables = Tables(
        block_table=set(block.table_assignments(randomness)),
        tx_table=set(),
        bytecode_table=set(bytecode.table_assignments(randomness)),
        rw_table=set(
            [
                (1, RW.Read, RWTableTag.Stack, 1, 1023, 0, RLC(mstart, randomness, 8), 0, 0, 0),
                (2, RW.Read, RWTableTag.Stack, 1, 1022, 0, RLC(msize, randomness, 2), 0, 0, 0),
                # read topic
                (3, RW.Read, RWTableTag.Stack, 1, 1021, 0, RLC(topic1, randomness, 32), 0, 0, 0),
                (4, RW.Read, RWTableTag.Memory, 1, 9, 0, 10, 0, 0, 0),
                (5, RW.Read, RWTableTag.Memory, 1, 10, 0, 20, 0, 0, 0),
                # write tx log with topic and data
                (6, RW.Write, RWTableTag.TxLog, 0, 0, TxLogFieldTag.Topics, RLC(topic1, randomness, 32), 0, 0, 0),
                (7, RW.Write, RWTableTag.TxLog, 0, 0, TxLogFieldTag.Data, 10, 0, 0, 0),
                (8, RW.Write, RWTableTag.TxLog, 0, 1, TxLogFieldTag.Date, 20, 0, 0, 0),
                # TODO: add contract address
            ]
        ),
    )

    verify_steps(
        randomness=randomness,
        tables=tables,
        steps=[
            StepState(
                execution_state=ExecutionState.COINBASE,
                rw_counter=1,
                call_id=1,
                is_root=True,
                is_create=False,
                code_source=bytecode_hash,
                program_counter=0,
                stack_pointer=1024,
                gas_left=2,
            ),
            StepState(
                execution_state=ExecutionState.STOP,
                rw_counter=4,
                call_id=1,
                is_root=True,
                is_create=False,
                code_source=bytecode_hash,
                program_counter=1,
                stack_pointer=1023,
                gas_left=0,
            ),
        ],
    )
