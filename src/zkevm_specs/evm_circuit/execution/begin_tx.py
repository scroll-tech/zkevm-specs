from ...util import (
    GAS_COST_TX,
    GAS_COST_CREATION_TX,
    EMPTY_CODE_HASH,
    FQ,
    Word,
    WordOrValue,
)
from ..execution_state import ExecutionState
from ..instruction import Instruction, Transition
from ..precompile import Precompile
from ..table import CallContextFieldTag, TxContextFieldTag, AccountFieldTag, CopyDataTypeTag


def begin_tx(instruction: Instruction):
    call_id = instruction.curr.rw_counter

    tx_id = instruction.call_context_lookup(CallContextFieldTag.TxId, call_id=call_id)
    reversion_info = instruction.reversion_info(call_id=call_id)
    instruction.constrain_equal(
        instruction.call_context_lookup(CallContextFieldTag.IsSuccess, call_id=call_id),
        reversion_info.is_persistent,
    )

    if instruction.is_first_step:
        instruction.constrain_equal(tx_id, FQ(1))

    tx_caller_address_word = instruction.tx_context_lookup_word(
        tx_id, TxContextFieldTag.CallerAddress
    )
    tx_caller_address = instruction.word_to_address(tx_caller_address_word)
    tx_callee_address_word = instruction.tx_context_lookup_word(
        tx_id, TxContextFieldTag.CalleeAddress
    )
    tx_callee_address = instruction.word_to_address(tx_callee_address_word)
    tx_is_create = instruction.tx_context_lookup(tx_id, TxContextFieldTag.IsCreate)
    tx_value = instruction.tx_context_lookup_word(tx_id, TxContextFieldTag.Value)
    tx_call_data_length = instruction.tx_context_lookup(tx_id, TxContextFieldTag.CallDataLength)

    # CallerAddress != 0 (not a padding tx)
    instruction.constrain_not_zero(tx_caller_address)

    # Verify nonce
    # TODO: Document that the TxInvalid feature is required to add invalid Tx
    #   to a block.  In regular Ethereum this is not possible because such Txs
    #   are rejected and never included in a Block.  But in a zkRollup setting,
    #   where the queueing of Txs is decoupled from block formation, there's a
    #   chance that a Tx is scheduled to be included in a block but it's invalid,
    #   so the circuit must prove that the Tx in that block is invalid.

    is_tx_invalid = instruction.tx_context_lookup(tx_id, TxContextFieldTag.TxInvalid)
    tx_nonce = instruction.tx_context_lookup(tx_id, TxContextFieldTag.Nonce)
    nonce, nonce_prev = instruction.account_write(tx_caller_address, AccountFieldTag.Nonce)
    is_nonce_valid = instruction.is_zero(tx_nonce.expr() - nonce_prev.expr())
    # bump the account nonce if the tx is valid
    instruction.constrain_equal(nonce, nonce_prev.expr() + 1 - is_tx_invalid.expr())

    # TODO: Implement EIP 1559 (currently it supports legacy transaction format)
    # Calculate gas fee
    tx_gas = instruction.tx_context_lookup(tx_id, TxContextFieldTag.Gas)
    tx_gas_price = instruction.tx_gas_price(tx_id)
    gas_fee = instruction.mul_word_by_u64(tx_gas_price, tx_gas)

    # intrinsic gas
    # G_0 = sum([G_txdatazero if CallData[i] == 0 else G_txdatanonzero for i in len(CallData)]) +
    #       (G_txcreate if tx_to == 0 or 0) +
    #       G_transaction +
    #       sum([G_accesslistaddress + G_accessliststorage * len(TA[j]) for j in len(TA)])
    tx_calldata_gas_cost = instruction.tx_context_lookup(tx_id, TxContextFieldTag.CallDataGasCost)
    tx_cost_gas = GAS_COST_CREATION_TX if tx_is_create == 1 else GAS_COST_TX
    # TODO: Handle gas cost of tx level access list (EIP 2930)
    tx_accesslist_gas = instruction.tx_context_lookup(tx_id, TxContextFieldTag.AccessListGasCost)
    tx_intrinsic_gas = tx_calldata_gas_cost.expr() + tx_cost_gas + tx_accesslist_gas.expr()

    # check instrinsic gas
    MAX_N_BYTES = 31
    gas_not_enough, _ = instruction.compare(tx_gas, tx_intrinsic_gas, MAX_N_BYTES)
    gas_left = tx_gas.expr() if gas_not_enough == 1 else tx_gas.expr() - tx_intrinsic_gas

    # Calculate new contract address if tx_is_create
    contract_address = instruction.generate_contract_address(tx_caller_address, tx_nonce)
    contract_address_word = instruction.address_to_word(contract_address)

    callee_address = contract_address if tx_is_create == 1 else tx_callee_address

    # Prepare access list of caller and callee
    instruction.constrain_zero(instruction.add_account_to_access_list(tx_id, tx_caller_address))
    instruction.constrain_zero(instruction.add_account_to_access_list(tx_id, callee_address))

    # Verify transfer
    sender_balance_pair, _ = instruction.transfer_with_gas_fee(
        tx_caller_address,
        callee_address,
        Word(0) if (is_tx_invalid.expr() == 1) else tx_value,
        Word(0) if (is_tx_invalid.expr() == 1) else gas_fee,
        reversion_info,
    )
    sender_balance_prev = sender_balance_pair[1]
    balance_not_enough, _ = instruction.compare(
        instruction.word_to_fq(sender_balance_prev, MAX_N_BYTES),
        instruction.word_to_fq(tx_value, MAX_N_BYTES)
        + instruction.word_to_fq(gas_fee, MAX_N_BYTES),
        MAX_N_BYTES,
    )
    invalid_tx = 1 - (1 - balance_not_enough) * (1 - gas_not_enough) * (is_nonce_valid)

    # prover should not give incorrect is_tx_invalid flag.
    instruction.constrain_equal(is_tx_invalid, invalid_tx)

    if tx_is_create == 1:
        if is_tx_invalid == FQ(1) or tx_call_data_length == 0:
            # Make sure tx is persistent
            instruction.constrain_equal(reversion_info.is_persistent, FQ(1))

            # Do step state transition
            instruction.constrain_equal(instruction.next.execution_state, ExecutionState.EndTx)
            instruction.constrain_step_state_transition(
                rw_counter=Transition.delta(9), call_id=Transition.to(call_id)
            )
        else:
            # Expected behabeur
            # - If initcode does not RETRUN, contract is created empty and value transferred
            # - If initcode is invalid bytecode or reverts, contract is not created and value not transferred

            # Get code hash of tx calldata

            copy_rwc_inc, tx_calldata_rlc = instruction.copy_lookup(
                tx_id,  # src_id
                CopyDataTypeTag.TxCalldata,  # src_type
                call_id,  # dst_id
                CopyDataTypeTag.RlcAcc,  # dst_type
                FQ.zero(),  # src_addr
                tx_call_data_length,  # src_addr_boundary
                FQ.zero(),  # dst_addr
                tx_call_data_length,  # length
                instruction.curr.rw_counter + instruction.rw_counter_offset,
            )

            assert copy_rwc_inc == FQ.zero()
            # no memory involved, no rw counter incremented

            code_hash = instruction.keccak_lookup(tx_call_data_length, tx_calldata_rlc)

            # Copy tx calldata to bytecode table

            copy_rwc_inc, _ = instruction.copy_lookup(
                tx_id,  # src_id
                CopyDataTypeTag.TxCalldata,  # src_type
                code_hash,  # dst_id
                CopyDataTypeTag.Bytecode,  # dst_type
                FQ.zero(),  # src_addr
                tx_call_data_length,  # src_addr_boundary
                FQ(0),  # dst_addr
                tx_call_data_length,  # length
                instruction.curr.rw_counter + instruction.rw_counter_offset,
            )
            assert copy_rwc_inc == FQ.zero()
            # no memory involved, no rw counter incremented

            # Setup next call's context

            for tag, word_or_value in [
                (CallContextFieldTag.Depth, FQ(1)),
                (CallContextFieldTag.CallerAddress, tx_caller_address_word),
                (CallContextFieldTag.CalleeAddress, contract_address_word),
                (CallContextFieldTag.CallDataOffset, FQ(0)),
                (CallContextFieldTag.CallDataLength, tx_call_data_length),
                (CallContextFieldTag.Value, tx_value),
                (CallContextFieldTag.IsStatic, FQ(False)),
                (CallContextFieldTag.LastCalleeId, FQ(0)),
                (CallContextFieldTag.LastCalleeReturnDataOffset, FQ(0)),
                (CallContextFieldTag.LastCalleeReturnDataLength, FQ(0)),
                (CallContextFieldTag.IsRoot, FQ(True)),
                (CallContextFieldTag.IsCreate, FQ(True)),
                (CallContextFieldTag.CodeHash, code_hash),
            ]:
                instruction.constrain_equal_word(
                    instruction.call_context_lookup_word(tag, call_id=call_id),
                    WordOrValue(word_or_value),
                )

            instruction.step_state_transition_to_new_context(
                rw_counter=Transition.delta(22),
                call_id=Transition.to(call_id),
                is_root=Transition.to(True),
                is_create=Transition.to(True),
                code_hash=Transition.to_word(code_hash),
                gas_left=Transition.to(gas_left),
                reversible_write_counter=Transition.to(2),
                log_id=Transition.to(0),
            )

    elif tx_callee_address in list(Precompile):
        # TODO: Handle precompile
        raise NotImplementedError
    else:
        code_hash = instruction.account_read_word(tx_callee_address, AccountFieldTag.CodeHash)
        is_empty_code_hash = instruction.is_equal_word(code_hash, Word(EMPTY_CODE_HASH))

        if is_empty_code_hash == FQ(1) or is_tx_invalid == FQ(1):
            # Make sure tx is persistent
            instruction.constrain_equal(reversion_info.is_persistent, FQ(1))

            # Do step state transition
            instruction.constrain_equal(instruction.next.execution_state, ExecutionState.EndTx)
            instruction.constrain_step_state_transition(
                rw_counter=Transition.delta(10), call_id=Transition.to(call_id)
            )
        else:
            # Setup next call's context
            # Note that:
            # - CallerId, ReturnDataOffset, ReturnDataLength
            #   should never be used in root call, so unnecessary to be checked
            # - TxId is checked from previous step or constraint to 1 if is_first_step
            # - IsSuccess, IsPersistent will be verified in the end of tx
            for tag, word_or_value in [
                (CallContextFieldTag.Depth, FQ(1)),
                (CallContextFieldTag.CallerAddress, tx_caller_address_word),
                (CallContextFieldTag.CalleeAddress, tx_callee_address_word),
                (CallContextFieldTag.CallDataOffset, FQ(0)),
                (CallContextFieldTag.CallDataLength, tx_call_data_length),
                (CallContextFieldTag.Value, tx_value),
                (CallContextFieldTag.IsStatic, FQ(False)),
                (CallContextFieldTag.LastCalleeId, FQ(0)),
                (CallContextFieldTag.LastCalleeReturnDataOffset, FQ(0)),
                (CallContextFieldTag.LastCalleeReturnDataLength, FQ(0)),
                (CallContextFieldTag.IsRoot, FQ(True)),
                (CallContextFieldTag.IsCreate, FQ(False)),
                (CallContextFieldTag.CodeHash, code_hash),
            ]:
                assert isinstance(word_or_value, FQ) or isinstance(word_or_value, Word)
                instruction.constrain_equal_word(
                    instruction.call_context_lookup_word(tag, call_id=call_id),
                    WordOrValue(word_or_value),
                )

            instruction.step_state_transition_to_new_context(
                rw_counter=Transition.delta(23),
                call_id=Transition.to(call_id),
                is_root=Transition.to(True),
                is_create=Transition.to(False),
                code_hash=Transition.to_word(code_hash),
                gas_left=Transition.to(gas_left),
                reversible_write_counter=Transition.to(2),
                log_id=Transition.to(0),
            )
