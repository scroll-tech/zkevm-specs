# Copy Proof

The copy proof checks the values in the copy table and applies the lookup arguments to the corresponding tables to check if the value read from and write to data source is correct.
It also checks the padding behavior that the value read from an out-of-boundary address is 0.

**Sources:** Memory, TX calldata, Bytecode.

**Destinations:** Memory, TX Log, RLC.

## Circuit Layout

First, copy circuit contains 9 columns from the [copy table](./tables.md#copy_table) with the same witness assignment.
A valid entry in the table that represents a copy event is a row with `is_first = 1`. The existence of a copy event must imply the existence of state operations, containing the correct state or read-only data.

Every two rows in the copy circuit represent a copy step where the first row is a read operation (`q_step = 1`) and the second is a write operation (`q_step = 0`), with `q_step` a fixed selector.
A copy event consists of multiple copy steps, which the first row in the copy event has `is_first` assigned to 1 and the last row has `is_last` assigned to 1.

In addition to the columns in the copy table, copy circuit adds a few auxiliary columns to help check the constraints.

- `is_memory`: indicates if `tag` is `Memory` using `IsZero` gadget.
- `is_bytecode`: indicates if `tag` is `Bytecode` using `IsZero` gadget.
- `is_tx_calldata`: indicates if `tag` is `TxCalldata` using `IsZero` gadget.
- `is_tx_log`: indicates if `tag` is `TxLog` using `IsZero` gadget.
- `is_rlc_acc`: indicates if `tag` is `rlc_acc` using `IsZero` gadget.

*Note*: We use `IsZero` gadget in the specs for simplicity. In the actual circuit implementation, we make use of `BinaryGadget`.


## Requirements

- If there is an entry in the Copy table with `is_first = 1` and the destination `Memory` or `TxLog`, the circuit will verify that the appropriate memory or log write operations exist in the RW table.

- If there is an entry with `is_first = 1` and the tag is `rlc_acc`, then the RLC value in the entry will be verified.

- The data written or RLC’d will be verified to exist in the source tables (RW, Bytecode, or Calldata).

- The RW operations happen in a deterministic order with consecutive RW counter values, starting with the `rw_counter` given in the entry.

- All RW operations happen, based on the `rwc_inc_left` counter in the entry.

- The user of the Copy table *should* calculate `rwc_inc_left` independently and deterministically, for defense-in-depth.

- The State circuit is responsible for checking that the RW addresses are multiple of the word size (32B). This is easy because the State circuit already decomposes addresses into bytes. It must check that:

     least_significant_byte == a * 128 + b * 64 + c * 32
        with a, b, c three witnessed bits.


## Circuit Constraints

The constraints are divided into four groups.

First, the circuit adds common constraints that applied to every rows in the circuit:

- Boolean check for `is_first`, and `is_last`.
- Check `is_first == 0` when `q_step == 0`.
- Check `is_last == 0` when `q_step == 1`.
- Construct the `IsZero` gadget and constrain `is_memory`, `is_bytecode`, `is_tx_calldata`, `is_tx_log` and `is_rlc_acc`.
- The transition constraints from a copy step to the next step (with 2-row rotation), applied to all rows except the last two rows (the last step) in a copy event:
    - `id`, `tag`, `src_addr_end` should be same between two steps.
    - `addr` increase by 1 in the next copy step.
- The transition constraints for `rw_counter` and `rwc_inc_left` column.
    - define `rw_diff` to be 1 if the `tag` is `Memory` or `TxLog` and `Padding` is 0 in the current row; otherwise 0.
    - when it's not the last row in a copy event (`is_last == 0`), `rw_counter` increases by `rw_diff` and `rwc_inc_left` decrases by `rw_diff`.
    - over all rows, the `rlc_acc` remains the same.
    - when it's the last row in a copy event (`is_last == 1`), `rwc_inc_left` is equal to `rw_diff`.
    - when it's the last row of a copy event (`is_last == 1`) and `is_rlc_acc == 1`, the row `value` should equal the row `rlc_acc`.

Second, the circuit adds the constraints for every copy step in the circuit, when `q_step` is 1.

- Look up the copy type pair `(Type, Type[1])` in a fixed table to make sure it's a valid copy step.
- Constrain the transition for `bytes_left`.
    - when it's not the last step (`is_last[1] != 1`), decrease by 1 in the next step.
    - otherwise, equals to 1.
- For all cases except `is_rlc_acc == 1`, we have `Value[0] == Value[1]`, meaning that read `value` equates write `value`.
- For `is_rlc_acc == 1`, we have `Value[0] == Value[1]` only for the first row, i.e. `is_first == 1`.
- Constrain `Value == 0` when `Padding == 1`.
- Construct the LT gadget to compare `addr` and `src_addr_end` in the read operation. If `addr >= src_addr_end`, constrain `Padding == 1`.
- Constrain `Padding[1] == 0` as the write operation is never padded.

Third, the circuit adds constraints for every copy step in the circuit, when `q_step == 0` (write row). These constraints are only added for the `is_rlc_acc == 1` case, for all except the last row, i.e. `is_last == 0`.

- Constraint the next write `value` by:
    - `Value[2] == Value[0] * r + Value[1]`.

Fourth, the circuit adds the lookup arguments to the corresponding tables.

- When `tag` is `Memory` or `is_memory == 1` and `Padding == 0`, look up the `Value` to `rw_table` with `Memory` tag.
- When `tag` is `TxCalldata` or `is_tx_calldata == 1` and `Padding == 0`, look up the `Value` to `tx_table`.
- When `tag` is `Bytecode` or `is_bytecode == 1` and `Padding == 0`, look up the `Value` and `IsCode` to `bytecode_table`.
- When `tag` is `TxLog` or `is_tx_log == 1`, look up the `Value` to `rw_table` with `TxLog` tag.

## Code

Please refer to `src/zkevm-specs/copy_circuit.py`
