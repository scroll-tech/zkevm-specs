import pytest

from zkevm_specs.evm import (
    ExecutionState,
    StepState,
    verify_steps,
    Tables,
    RWTableTag,
    RW,
    CallContextFieldTag,
    Transaction,
    Block,
    Bytecode,
)
from zkevm_specs.evm.execution.params import (
    COLD_SLOAD_COST,
    WARM_STORAGE_READ_COST,
    SLOAD_GAS,
    SSTORE_SET_GAS,
    SSTORE_RESET_GAS,
    SSTORE_CLEARS_SCHEDULE,
)
from zkevm_specs.util import RLCStore, rand_address


def gen_test_cases():
    value_cases = [
        [bytes([i for i in range(0, 32, 1)]), 0, -1],  # value_prev == value
        # "value_prev != value, original_value == value_prev, original_value == 0" case is skipped because inconvenient to generate for now
        [
            bytes([i for i in range(0, 32, 1)]),
            -1,
            -1,
        ],  # value_prev != value, original_value == value_prev, original_value != 0
        [bytes([i for i in range(0, 32, 1)]), -1, -2],  # value_prev != value, original_value != value_prev
        [
            bytes([i for i in range(0, 32, 1)]),
            -1,
            0,
        ],  # value_prev != value, original_value != value_prev, value == original_value
    ]
    warm_cases = [False, True]
    persist_cases = [True, False]

    test_cases = []
    for value_case in value_cases:
        for warm_case in warm_cases:
            for persist_case in persist_cases:
                test_cases.append(
                    (
                        Transaction(caller_address=rand_address(), callee_address=rand_address()),  # tx
                        bytes([i for i in range(32, 0, -1)]),  # storage_slot
                        value_case[0],  # new_value
                        value_case[1],  # value_prev_diff
                        value_case[2],  # original_value_diff
                        warm_case,  # is_warm_storage_slot
                        persist_case,  # is_not_reverted
                    )
                )
    return test_cases


TESTING_DATA = gen_test_cases()


@pytest.mark.parametrize(
    "tx, slot_be_bytes, value_be_bytes, value_prev_diff, original_value_diff, warm, result", TESTING_DATA
)
def test_sstore(
    tx: Transaction,
    slot_be_bytes: bytes,
    value_be_bytes: bytes,
    value_prev_diff: int,
    original_value_diff: int,
    warm: bool,
    result: bool,
):
    rlc_store = RLCStore()

    storage_slot = rlc_store.to_rlc(bytes(reversed(slot_be_bytes)))
    value = rlc_store.to_rlc(bytes(reversed(value_be_bytes)))
    value_prev = value + value_prev_diff
    original_value = value + original_value_diff

    block = Block()

    # PUSH32 STORAGE_SLOT PUSH32 VALUE SSTORE STOP
    bytecode = Bytecode(f"7f{slot_be_bytes.hex()}7f{value_be_bytes.hex()}5500")
    bytecode_hash = rlc_store.to_rlc(bytecode.hash, 32)

    if value_prev == value:
        expected_gas_cost = SLOAD_GAS
    else:
        if original_value == value_prev:
            if original_value == 0:
                expected_gas_cost = SSTORE_SET_GAS
            else:
                expected_gas_cost = SSTORE_RESET_GAS
        else:
            expected_gas_cost = SLOAD_GAS
    if not warm:
        expected_gas_cost = expected_gas_cost + COLD_SLOAD_COST

    old_gas_refund = 15000
    gas_refund = old_gas_refund
    if value_prev != value:
        if original_value == value_prev:
            if original_value != 0 and value == 0:
                gas_refund = gas_refund + SSTORE_CLEARS_SCHEDULE
        else:
            if original_value != 0:
                if value_prev == 0:
                    gas_refund = gas_refund - SSTORE_CLEARS_SCHEDULE
                if value == 0:
                    gas_refund = gas_refund + SSTORE_CLEARS_SCHEDULE
            if original_value == value:
                if original_value == 0:
                    gas_refund = gas_refund + SSTORE_SET_GAS - SLOAD_GAS
                else:
                    gas_refund = gas_refund + SSTORE_RESET_GAS - SLOAD_GAS

    tables = Tables(
        block_table=set(block.table_assignments(rlc_store)),
        tx_table=set(tx.table_assignments(rlc_store)),
        bytecode_table=set(bytecode.table_assignments(rlc_store)),
        rw_table=set(
            [
                (1, RW.Read, RWTableTag.CallContext, 1, CallContextFieldTag.TxId, 0, tx.id, 0, 0, 0),
                (
                    2,
                    RW.Read,
                    RWTableTag.CallContext,
                    1,
                    CallContextFieldTag.RWCounterEndOfReversion,
                    0,
                    0 if result else 16,
                    0,
                    0,
                    0,
                ),
                (3, RW.Read, RWTableTag.CallContext, 1, CallContextFieldTag.IsPersistent, 0, result, 0, 0 ,0),
                (4, RW.Read, RWTableTag.Stack, 1, 1022, 0, storage_slot, 0, 0, 0),
                (5, RW.Read, RWTableTag.Stack, 1, 1023, 0, value, 0, 0, 0),
                (
                    6,
                    RW.Read,
                    RWTableTag.TxAccessListStorageSlot,
                    tx.id,
                    tx.callee_address,
                    storage_slot,
                    1 if warm else 0,
                    0,
                    0,
                    0,
                ),
                (
                    7,
                    RW.Read,
                    RWTableTag.AccountStorage,
                    tx.callee_address,
                    storage_slot,
                    0,
                    value_prev,
                    original_value,
                    tx.id,
                    original_value,
                ),
                (8, RW.Read, RWTableTag.TxRefund, tx.id, 0, 0, old_gas_refund, 0, 0, 0),
                (
                    9,
                    RW.Write,
                    RWTableTag.AccountStorage,
                    tx.callee_address,
                    storage_slot,
                    0,
                    value,
                    value_prev,
                    tx.id,
                    original_value,
                ),
                (
                    10,
                    RW.Write,
                    RWTableTag.TxAccessListStorageSlot,
                    tx.id,
                    tx.callee_address,
                    storage_slot,
                    1,
                    1 if warm else 0,
                    0,
                    0,
                ),
                (11, RW.Write, RWTableTag.TxRefund, tx.id, 0, 0, gas_refund, old_gas_refund, 0, 0),
            ]
            + (
                []
                if result
                else [
                    (
                        14,
                        RW.Write,
                        RWTableTag.TxRefund,
                        tx.id,
                        0,
                        0,
                        old_gas_refund,
                        gas_refund,
                        0,
                        0,
                    ),
                    (
                        15,
                        RW.Write,
                        RWTableTag.TxAccessListStorageSlot,
                        tx.id,
                        tx.callee_address,
                        storage_slot,
                        1 if warm else 0,
                        1,
                        0,
                        0,
                    ),
                    (
                        16,
                        RW.Write,
                        RWTableTag.AccountStorage,
                        tx.callee_address,
                        storage_slot,
                        0,
                        value_prev,
                        value,
                        tx.id,
                        original_value,
                    ),
                ]
            )
        ),
    )

    verify_steps(
        rlc_store=rlc_store,
        tables=tables,
        steps=[
            StepState(
                execution_state=ExecutionState.SSTORE,
                rw_counter=1,
                call_id=1,
                is_root=True,
                is_create=False,
                opcode_source=bytecode_hash,
                program_counter=66,
                stack_pointer=1022,
                state_write_counter=0,
                gas_left=expected_gas_cost,
            ),
            StepState(
                execution_state=ExecutionState.STOP if result else ExecutionState.REVERT,
                rw_counter=9,
                call_id=1,
                is_root=True,
                is_create=False,
                opcode_source=bytecode_hash,
                program_counter=67,
                stack_pointer=1024,
                state_write_counter=3,
                gas_left=0,
            ),
        ],
    )
