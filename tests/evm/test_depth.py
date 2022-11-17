import pytest
from collections import namedtuple
from itertools import chain

from zkevm_specs.evm import (
    Block,
    Bytecode,
    CallContextFieldTag,
    ExecutionState,
    Opcode,
    RWDictionary,
    StepState,
    Tables,
    Transaction,
    verify_steps,
)
from zkevm_specs.util import rand_fq, RLC

BYTECODE = Bytecode().call()
TESTING_DATA_IS_ROOT = ((Transaction(), BYTECODE),)


@pytest.mark.parametrize("tx, bytecode", TESTING_DATA_IS_ROOT)
def test_depth(tx: Transaction, bytecode: Bytecode):
    randomness = rand_fq()

    block = Block()

    bytecode_hash = RLC(bytecode.hash(), randomness)

    tables = Tables(
        block_table=set(block.table_assignments(randomness)),
        tx_table=set(
            chain(
                tx.table_assignments(randomness),
                Transaction(id=tx.id + 1).table_assignments(randomness),
            )
        ),
        bytecode_table=set(bytecode.table_assignments(randomness)),
        rw_table=set(
            RWDictionary(24)
            .call_context_read(1, CallContextFieldTag.Depth, 1025)
            .rws
        ),
    )

    verify_steps(
        randomness=randomness,
        tables=tables,
        steps=[
            StepState(
                execution_state=ExecutionState.ErrorDepth,
                rw_counter=24,
                call_id=1,
                is_root=True,
                is_create=False,
                code_hash=bytecode_hash,
                program_counter=0,
                stack_pointer=1023,
                gas_left=2,
                reversible_write_counter=2,
            )
        ],
    )
