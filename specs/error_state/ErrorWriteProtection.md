# ErrorWriteProtection state

## Procedure
State modifying opcodes, which include `[SSTORE, CREATE, CREATE2, CALL, SELFDESTRUCT, LOG0, LOG1, LOG2, LOG3, LOG4]`, throw write protection errors when executed in a read-only call context (static call). See [EIP-214](https://eips.ethereum.org/EIPS/eip-214).

### EVM behavior
A write protection error is thrown if all the following conditions are met:
- State modifying opcodes run in a read-only context.
- If the opcode is `CALL` and the `value` argument is non-zero.

### Constraints
1. constrain this error happens in one of op codes `[SSTORE, CREATE, CREATE2, CALL, SELFDESTRUCT, LOG0, LOG1, LOG2, LOG3, LOG4]`
2. current call context must be readonly (this call must be a internal call since it requires at least one `staticcall` ahead).
3. for `CALL` op code, do stack read & check `value` is not zero.
4. common error steps constraints:
   - current call must be failed.
   - rw_counter_end_of_reversion constraint
   - it restores caller's context by reading to `rw_table`, then does step state transition to it.

## Code
  Please refer to `src/zkevm_specs/evm/execution/error_write_protection.py`.