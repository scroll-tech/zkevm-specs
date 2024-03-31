# ErrorInvalidOpcode state

## Procedure

`ErrorInvalidOpcode` may occur when an invalid opcode is encountered in any step during the execution.

### EVM behavior

1. If it's a root call, it ends the execution.
2. Otherwise, it restores caller's context and switch to it.

### Constraints

1. Do a fixed lookup for `FixedTableTag.ResponsibleOpcode`.
2. Current call must be failed. Do a call context lookup for `CallContextFieldTag.IsSuccess`.
3. If it's a root call, it transits to `EndTx`.
4. If it is not root call, it restores caller's context by reading to `rw_table`, then does step state transition to it.

## Code

Please refer to `src/zkevm_specs/evm/execution/error_invalid_opcode.py`.
