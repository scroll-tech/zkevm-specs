# ErrorOutOfGasSHA3 state for SHA3 OOG error

## Procedure

Handle the corresponding out of gas error for `SHA3`.

### EVM behavior

For `SHA3`, the out of gas error may occur in conditions:

1. `memory_offset + memory_length > 0x1FFFFFFFE0 ((2^32 - 1) * 32)` if `memory_length` is non-zero.
2. Gas left is less than a constant gas cost of `30`.
3. Gas left is less than the sum of both constant and dynamic gas costs. The dynamic gas cost is calculated for memory expansion and copying (variable depending on the memory size copied to memory).

### Constraints

1. Constrain either `memory_offset + memory_length > 0x1FFFFFFFE0` or `gas_left < gas_cost` must be true.
2. Current call must fail.
3. If it's a root call, it transits to `EndTx`.
4. If it isn't a root call, it restores caller's context by reading to `rw_table`, then does step state transition to it.
5. Constrain `rw_counter_end_of_reversion = rw_counter_end_of_step + reversible_counter`.

### Lookups

`4` basic bus-mapping lookups:

. `2` stack pop `offset` and `size`.
. `2` call context lookups for `is_success` and `rw_counter_end_of_reversion`.

And restore context lookups for non-root call.
